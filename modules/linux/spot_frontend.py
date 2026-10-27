#!/usr/bin/env python3
"""Synchronous, content-free frontend custody. No idle authority for the server.

The native launcher closes inherited extra FDs. A short-lived CLI invoked by
Bun therefore acknowledges transitions through the same admission flock. Calls
carry only counters/opaque registry IDs, never input, commands or session IDs.
"""
import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import threading
import time
import uuid

import spot_work as work

FRONT = re.compile(r'^frontend-[0-9a-f]{32}$')
COUNTERS = {'queued', 'pending_steer', 'processing', 'actions', 'draft', 'initialized'}


def descendant(pid, ancestor):
    for _ in range(64):
        if pid == ancestor:
            return True
        if pid <= 1:
            break
        pid = int(Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()[1])
    return False


def counters(value):
    if (not isinstance(value, dict) or set(value) != COUNTERS
            or any(type(value[k]) is not bool for k in COUNTERS - {'queued', 'actions'})
            or any(type(value[k]) is not int or not 0 <= value[k] <= 1000000 for k in ['queued', 'actions'])):
        raise ValueError('unknown frontend counters')
    return value


def busy(value):
    return (not value['initialized'] or value['queued'] > 0 or value['pending_steer']
            or value['processing'] or value['actions'] > 0 or value['draft'])


class Frontend:
    def __init__(self, protocol, parent=None):
        self.protocol = protocol
        self.uid = os.geteuid()
        pid = os.getppid() if parent is None else parent
        self.pid, self.start = pid, work.process_start(pid)
        if self.uid not in {protocol.uid, protocol.root_uid} or work.process_uid(pid) != self.uid:
            raise PermissionError('frontend owner unavailable')

    def new_job(self):
        # Caller holds admission.lock. Unlike an ephemeral CLI PID, the real
        # Bun PID/start owns this epoch; its death/staleness never means idle.
        if self.protocol.state() != 'open':
            raise RuntimeError('frontend admission closed; request not acknowledged')
        now = time.time()
        job = {'schema': 1, 'id': 'job-' + uuid.uuid4().hex, 'kind': 'job', 'uid': self.uid,
               'boot_id': self.protocol.boot_id, 'created_at': now, 'state': 'running',
               'pid': self.pid, 'pid_start': self.start, 'heartbeat_at': now}
        self.protocol.publish(self.protocol.leases / job['id'], job)
        return job['id']

    def job(self, ident):
        if not isinstance(ident, str) or not work.NAME.fullmatch(ident) or not ident.startswith('job-'):
            raise ValueError('frontend epoch identity unknown')
        job, _ = work.read_record(self.protocol.leases / ident, {self.uid})
        if (job.get('id') != ident or job.get('kind') != 'job' or job.get('uid') != self.uid
                or job.get('boot_id') != self.protocol.boot_id or job.get('pid') != self.pid
                or job.get('pid_start') != self.start or job.get('state') != 'running'):
            raise ValueError('frontend epoch owner changed')
        return job

    def attach(self, startup):
        with self.protocol.locked():
            if not isinstance(startup, str) or not work.NAME.fullmatch(startup) or not startup.startswith('job-'):
                raise ValueError('frontend startup custody missing')
            initial, _ = work.read_record(self.protocol.leases / startup, {self.uid})
            pid = initial.get('pid')
            if (initial.get('id') != startup or initial.get('uid') != self.uid
                    or initial.get('kind') != 'job' or initial.get('state') != 'running'
                    or initial.get('boot_id') != self.protocol.boot_id or type(pid) is not int or pid <= 0
                    or work.process_uid(pid) != self.uid or work.process_start(pid) != initial.get('pid_start')
                    or not descendant(self.pid, pid)):
                raise ValueError('unowned frontend startup custody')
            epoch = self.new_job()
            ident = 'frontend-' + uuid.uuid4().hex
            record = {'schema': 1, 'kind': 'kiro_frontend', 'id': ident, 'uid': self.uid,
                      'boot_id': self.protocol.boot_id, 'pid': self.pid, 'pid_start': self.start,
                      'healthy': True, 'initialized': False, 'epoch': epoch, 'seq': 0,
                      'admission_rejections': 0, 'reason': 'initializing', 'updated_at': time.time()}
            self.protocol.publish(self.protocol.runtime / 'participants' / ident, record)
            # All three overlap under ONE lock: bootstrap -> Bun epoch + still
            # unverified participant. This is not whole-process/idle approval.
            (self.protocol.leases / startup).unlink()
            return {'id': ident, 'seq': 0, 'accepted': True}

    def invoke(self, ident, seq, action, values=None):
        if not isinstance(ident, str) or not FRONT.fullmatch(ident):
            raise ValueError('frontend participant identity unknown')
        with self.protocol.locked():
            path = self.protocol.runtime / 'participants' / ident
            record, _ = work.read_record(path, {self.uid})
            if (record.get('schema') != 1 or record.get('kind') != 'kiro_frontend'
                    or record.get('id') != ident or record.get('uid') != self.uid
                    or record.get('boot_id') != self.protocol.boot_id
                    or record.get('pid') != self.pid or record.get('pid_start') != self.start
                    or type(seq) is not int or type(record.get('seq')) is not int
                    or (seq != record['seq'] + 1 and not (action == 'fault' and seq == record['seq']))
                    or type(record.get('healthy')) is not bool):
                raise ValueError('frontend binding or sequence changed')
            epoch = record.get('epoch')
            job = self.job(epoch) if epoch is not None else None
            accepted = True
            if action == 'admit':
                if not record['healthy'] or self.protocol.state() != 'open':
                    accepted = False
                    record['admission_rejections'] += 1
                elif epoch is None:
                    record['epoch'] = self.new_job()
            elif action == 'state':
                value = counters(values)
                if busy(value) and epoch is None:
                    # State arising outside a reviewed producer is uncertain;
                    # preserve vendor updates/output, but never claim idle.
                    try:
                        record['epoch'] = self.new_job()
                    except RuntimeError:
                        record['healthy'] = False
                        accepted = False
                if not busy(value) and record['healthy'] and epoch is not None:
                    (self.protocol.leases / epoch).unlink()
                    record['epoch'] = None
                record['initialized'] = value['initialized']
                record['counters'] = value
            elif action == 'heartbeat':
                if job is not None:
                    job['heartbeat_at'] = time.time()
                    self.protocol.publish(self.protocol.leases / epoch, job)
            elif action == 'fault':
                record['healthy'] = False
            elif action == 'close':
                if (not record['healthy'] or not record.get('initialized') or epoch is not None):
                    raise RuntimeError('frontend exit has unresolved custody')
                path.unlink()
                return {'seq': seq, 'accepted': True}
            else:
                raise ValueError('unknown frontend operation')
            record.update(seq=seq, updated_at=time.time(), reason=(
                'unknown' if not record['healthy'] else 'local_work' if record.get('epoch') else 'local_quiescent_unverified'))
            self.protocol.publish(path, record)
            return {'seq': seq, 'accepted': accepted}


def launch(protocol, argv):
    if not argv:
        raise ValueError('native frontend command required')
    startup = protocol.create('job')
    done = threading.Event()
    child = None
    previous = {}
    pending_signals = []

    def heartbeat():
        while not done.wait(15):
            try:
                protocol.heartbeat(startup)
            except (OSError, ValueError, RuntimeError):
                return  # Handoff or uncertainty; never delete custody here.

    def forward(signum, frame):
        if child is not None:
            try:
                child.send_signal(signum)
            except ProcessLookupError:
                pass
        else:
            pending_signals.append(signum)

    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            previous[signum] = signal.signal(signum, forward)
        if pending_signals:
            return 128 + pending_signals[-1]
        env = {**os.environ, 'SPOT_KIRO_STARTUP': startup['id']}
        child = subprocess.Popen(argv, env=env)
        for signum in pending_signals:
            forward(signum, None)
        code = child.wait()
        return code if code >= 0 else 128 - code
    finally:
        # A failed/unknown native startup or dead frontend is NOT completion.
        # Only the exact synchronous Bun attach may retire the bootstrap lease.
        done.set(); thread.join()
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['launch', 'attach', 'admit', 'state', 'heartbeat', 'fault', 'close'])
    parser.add_argument('args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    protocol = work.Protocol()
    if args.action == 'launch':
        return launch(protocol, args.args[1:] if args.args[:1] == ['--'] else args.args)
    raw = sys.stdin.buffer.read(2049)
    if len(raw) > 2048:
        raise ValueError('frontend frame too large')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('frontend frame unknown')
    frontend = Frontend(protocol)
    if args.action == 'attach':
        if set(value) != {'startup'}:
            raise ValueError('frontend attach frame unknown')
        result = frontend.attach(value['startup'])
    else:
        keys = {'id', 'seq', 'counters'} if args.action == 'state' else {'id', 'seq'}
        if set(value) != keys:
            raise ValueError('frontend frame unknown')
        result = frontend.invoke(value['id'], value['seq'], args.action, value.get('counters'))
    print(json.dumps(result, separators=(',', ':')))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError):
        print('Frontend admission unavailable; no new work acknowledged', file=sys.stderr)
        sys.exit(75)
