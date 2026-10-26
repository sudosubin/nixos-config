#!/usr/bin/env python3
"""Local EC2 work admission. No AWS credentials, external service, or CPU heuristics.

Job leases never expire into permission to terminate. A dead wrapper, malformed
record, or stale heartbeat remains a blocker until explicitly reconciled.
"""
from contextlib import contextmanager
import argparse
import ctypes
import fcntl
import json
import math
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import threading
import time
import uuid

RUNTIME = Path('/run/spot-schedule-guard')
NAME = re.compile(r'^(job|manual)-[0-9a-f]{32}$')


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def process_start(pid):
    return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19])


def process_uid(pid):
    return Path(f'/proc/{pid}').stat().st_uid


def read_record(path, owners, limit=4096):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid not in owners
                or info.st_mode & 0o022 or info.st_size > limit):
            raise ValueError('untrusted admission record')
        data = json.load(stream)
        if not isinstance(data, dict):
            raise ValueError('admission record must be an object')
        return data, info.st_uid


class Protocol:
    def __init__(self, runtime=RUNTIME, uid=1001, gid=100, root_uid=0, boot_id=None):
        self.runtime = Path(runtime)
        self.uid, self.gid, self.root_uid = uid, gid, root_uid
        self._boot_id = boot_id

    @property
    def boot_id(self):
        return self._boot_id or Path('/proc/sys/kernel/random/boot_id').read_text().strip()

    @property
    def leases(self):
        return self.runtime / 'leases'

    def initialize(self):
        if os.geteuid() != self.root_uid:
            raise PermissionError('only root initializes work admission')
        for path, mode in [(self.runtime, 0o755), (self.leases, 0o1733), (self.runtime / 'participants', 0o1733)]:
            path.mkdir(mode=mode, exist_ok=True)
            info = path.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != self.root_uid:
                raise ValueError('untrusted admission directory')
            os.chmod(path, mode)
        fd = os.open(self.runtime / 'admission.lock', os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o660)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != self.root_uid:
                raise ValueError('untrusted admission lock')
            os.fchown(fd, self.root_uid, self.gid)
            os.fchmod(fd, 0o660)
        finally:
            os.close(fd)

    @contextmanager
    def locked(self, timeout=5):
        info = self.runtime.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != self.root_uid or info.st_mode & 0o022:
            raise ValueError('untrusted admission runtime')
        fd = os.open(self.runtime / 'admission.lock', os.O_WRONLY | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != self.root_uid
                    or info.st_gid != self.gid or info.st_mode & 0o007):
                raise ValueError('untrusted admission lock')
            deadline = time.monotonic() + timeout
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise RuntimeError('admission busy; request NOT acknowledged')
                    time.sleep(0.02)
            yield
        finally:
            os.close(fd)

    def state(self):
        try:
            data, _ = read_record(self.runtime / 'draining', {self.root_uid})
        except FileNotFoundError:
            return 'open'
        if (type(data.get('schema')) is not int or data['schema'] != 1
                or data.get('boot_id') != self.boot_id
                or data.get('state') not in {'draining', 'releasing', 'released'}):
            raise ValueError('unknown admission state')
        return data['state']

    def publish(self, path, record):
        temp = path.parent / ('.pending-' + uuid.uuid4().hex)
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(record, stream, separators=(',', ':'))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)

    def write_state(self, state):
        if os.geteuid() != self.root_uid:
            raise PermissionError('only root may fence admission')
        self.publish(self.runtime / 'draining', {'schema': 1, 'state': state, 'boot_id': self.boot_id})
        # Clients may read the fence but cannot replace/write it. This happens
        # under the admission lock, before another client can inspect the state.
        os.chmod(self.runtime / 'draining', 0o644)

    def seal(self):
        with self.locked():
            if self.state() != 'open':
                raise RuntimeError('previous drain needs reconciliation')
            self.write_state('draining')

    def unseal(self):
        with self.locked():
            if os.geteuid() != self.root_uid:
                raise PermissionError('only root may reopen admission')
            if os.path.lexists(self.runtime / 'recover-services'):
                raise RuntimeError('service recovery must finish before admission reopens')
            (self.runtime / 'draining').unlink(missing_ok=True)

    def service_start_allowed(self, unit):
        with self.locked():
            state = self.state()
            if state == 'open':
                return True
            if state != 'draining':
                return False
            try:
                data, _ = read_record(self.runtime / 'recover-services', {self.root_uid})
                pid = data.get('pid')
                return (data.get('schema') == 1 and type(data.get('schema')) is int
                        and data.get('boot_id') == self.boot_id
                        and isinstance(data.get('units'), list) and unit in data['units']
                        and type(pid) is int and pid > 0
                        and type(data.get('pid_start')) is int
                        and process_uid(pid) == self.root_uid
                        and process_start(pid) == data['pid_start'])
            except (OSError, ValueError, TypeError):
                return False

    @contextmanager
    def recover_services(self, units):
        # Caller must first reconfirm ASG protection. This grants only service
        # startup during rollback, NEVER admission for new jobs or extensions
        # after release. A dead recovery controller cannot authorize startup.
        if os.geteuid() != self.root_uid or not units or any(not isinstance(x, str) for x in units):
            raise PermissionError('root recovery service allowlist required')
        path = self.runtime / 'recover-services'
        recovery_id = uuid.uuid4().hex
        with self.locked():
            if self.state() != 'draining' or os.path.lexists(path):
                raise RuntimeError('unknown recovery state')
            self.publish(path, {'schema': 1, 'id': recovery_id, 'boot_id': self.boot_id, 'units': units,
                                'pid': os.getpid(), 'pid_start': process_start(os.getpid())})
            os.chmod(path, 0o644)
        try:
            yield
        finally:
            with self.locked():
                data, _ = read_record(path, {self.root_uid})
                if data.get('id') != recovery_id:
                    raise RuntimeError('service recovery authority changed')
                path.unlink()

    def blockers_unlocked(self, now=None):
        now = time.time() if now is None else now
        blocked = []
        for path in self.leases.iterdir():
            try:
                if not NAME.fullmatch(path.name):
                    raise ValueError('unknown lease entry')
                data, owner = read_record(path, {self.root_uid, self.uid})
                if (type(data.get('schema')) is not int or data['schema'] != 1
                        or type(data.get('uid')) is not int or data['uid'] != owner
                        or data.get('id') != path.name or data.get('boot_id') != self.boot_id
                        or not finite(data.get('created_at')) or data['created_at'] > now + 60):
                    raise ValueError('unknown lease schema or identity')
                kind = data.get('kind')
                if kind == 'manual' and path.name.startswith('manual-'):
                    if not finite(data.get('expires_at')) or data['expires_at'] < data['created_at']:
                        raise ValueError('invalid manual expiry')
                    if data['expires_at'] > now:
                        blocked.append({'id': path.name, 'reason': 'manual_extension'})
                elif kind == 'job' and path.name.startswith('job-'):
                    if (data.get('state') != 'running' or type(data.get('pid')) is not int
                            or data['pid'] <= 0 or type(data.get('pid_start')) is not int
                            or data['pid_start'] <= 0 or not finite(data.get('heartbeat_at'))
                            or data['heartbeat_at'] > now + 60):
                        raise ValueError('invalid job identity')
                    # Missing heartbeat is UNKNOWN, never proof that work ended.
                    reason = 'running_job' if now - data['heartbeat_at'] <= 90 else 'stale_job_unknown'
                    blocked.append({'id': path.name, 'reason': reason})
                else:
                    raise ValueError('unknown lease kind')
            except (OSError, ValueError, KeyError, TypeError):
                blocked.append({'id': path.name, 'reason': 'invalid_lease_unknown'})
        if os.path.lexists(self.runtime / 'recover-services'):
            blocked.append({'id': 'recover-services', 'reason': 'service_recovery_in_progress'})
        # A participant record alone never grants authority to exempt a worker.
        # Until the workload coordinator verifies its live PID/protocol/fence,
        # even an apparent idle record remains unverified (fail closed).
        try:
            for path in (self.runtime / 'participants').iterdir():
                blocked.append({'id': path.name, 'reason': 'participant_unverified'})
        except OSError:
            blocked.append({'id': 'participants', 'reason': 'participant_registry_unknown'})
        return blocked

    def blockers(self, now=None):
        with self.locked():
            return self.blockers_unlocked(now)

    def create(self, kind, seconds=None):
        owner = os.geteuid()
        if owner not in {self.root_uid, self.uid}:
            raise PermissionError('unexpected work owner')
        with self.locked():
            state = self.state()
            if state in {'releasing', 'released'} or (kind == 'job' and state != 'open'):
                raise RuntimeError('shutdown admission closed; request NOT acknowledged')
            now = time.time()
            data = {'schema': 1, 'id': kind + '-' + uuid.uuid4().hex, 'kind': kind,
                    'uid': owner, 'boot_id': self.boot_id, 'created_at': now}
            if kind == 'manual':
                if not finite(seconds) or seconds <= 0 or not finite(now + seconds):
                    raise ValueError('extension duration must be positive and finite')
                data['expires_at'] = now + seconds
            elif kind == 'job':
                data.update(state='running', pid=os.getpid(), pid_start=process_start(os.getpid()), heartbeat_at=now)
            else:
                raise ValueError('unknown work kind')
            self.publish(self.leases / data['id'], data)
            return data

    def heartbeat(self, data):
        with self.locked():
            old, owner = read_record(self.leases / data['id'], {os.geteuid()})
            if old['id'] != data['id'] or old['kind'] != 'job' or owner != data['uid']:
                raise ValueError('job lease changed unexpectedly')
            data['heartbeat_at'] = time.time()
            self.publish(self.leases / data['id'], data)

    def remove(self, ident, job_finished=False):
        if not NAME.fullmatch(ident):
            raise ValueError('invalid lease id')
        with self.locked():
            data, owner = read_record(self.leases / ident, {os.geteuid()})
            if data.get('id') != ident or (data.get('kind') != 'manual' and not job_finished):
                raise ValueError('running/unknown job cannot be cancelled as an extension')
            (self.leases / ident).unlink()

    @contextmanager
    def commit(self):
        # Acknowledged extensions before this lock cancel shutdown. During/after
        # release, clients cannot falsely acknowledge a successful extension.
        with self.locked(timeout=30):
            if self.state() != 'draining' or self.blockers_unlocked():
                raise RuntimeError('shutdown cancelled by work or extension')
            self.write_state('releasing')
            yield
            self.write_state('released')


def subreaper():
    # Keep background/double-forked descendants leased after the main command
    # exits. No forced runtime deadline and no dependence on process names.
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'cannot enable child subreaper')


def run_job(protocol, argv):
    if not argv:
        raise ValueError('a command is required')
    subreaper()
    lease = protocol.create('job')
    child = None
    done = threading.Event()
    completed = False
    previous = {}
    pending_signals = []

    def forward(signum, frame):
        if child is None:
            pending_signals.append(signum)
        else:
            try:
                os.killpg(child.pid, signum)
            except ProcessLookupError:
                pass

    def heartbeat():
        while not done.wait(15):
            try:
                protocol.heartbeat(lease)
            except Exception:
                # Leave the original lease in place. Staleness must block.
                return
    try:
        for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            previous[signum] = signal.signal(signum, forward)
        # The lease was published before spawn. A drain starting now observes it
        # and cancels; a drain preceding create() rejects the command entirely.
        if pending_signals:
            return 128 + pending_signals[-1]
        child = subprocess.Popen(argv, start_new_session=True)
        for signum in pending_signals:
            forward(signum, None)
        thread = threading.Thread(target=heartbeat, daemon=True)
        thread.start()
        result = child.wait()
        while True:
            try:
                os.waitpid(-1, 0)
            except ChildProcessError:
                break
        completed = True
        return result if result >= 0 else 128 - result
    finally:
        done.set()
        if 'thread' in locals():
            thread.join()
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        if completed or child is None:
            protocol.remove(lease['id'], job_finished=True)


def main(protocol=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('initialize')
    sub.add_parser('status')
    sub.add_parser('check-open')
    service_start = sub.add_parser('check-service-open'); service_start.add_argument('unit')
    extend = sub.add_parser('extend'); extend.add_argument('--seconds', type=float, default=7200)
    cancel = sub.add_parser('cancel'); cancel.add_argument('id')
    run = sub.add_parser('run'); run.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    protocol = protocol or Protocol()
    if args.action == 'initialize':
        protocol.initialize()
    elif args.action == 'status':
        with protocol.locked():
            print(json.dumps({'state': protocol.state(), 'blockers': protocol.blockers_unlocked()}))
    elif args.action == 'check-open':
        with protocol.locked():
            return 0 if protocol.state() == 'open' else 1
    elif args.action == 'check-service-open':
        return 0 if protocol.service_start_allowed(args.unit) else 1
    elif args.action == 'extend':
        print(json.dumps(protocol.create('manual', args.seconds)))
    elif args.action == 'cancel':
        protocol.remove(args.id)
    else:
        argv = args.command[1:] if args.command[:1] == ['--'] else args.command
        return run_job(protocol, argv)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(75)
