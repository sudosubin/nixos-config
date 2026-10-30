#!/usr/bin/env python3
"""Warm SHADOW custody for explicit, NEW non-interactive jobs only.

Not work.Protocol.initialize, not a startup/idle/termination authority. Existing
sessions/queues, direct execution, external work and delivery remain UNKNOWN.
Local records survive wrapper/collector restarts, but are NOT an off-root journal.
No delete/clear/ack/replay/takeover API. No implicit resource/build authority.
"""
from contextlib import contextmanager
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import stat
import sys
import time
import uuid
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))
import spot_work as work

BASE = Path('/var/lib/spot-work-shadow')
OBSERVER = Path('/etc/spot-protection-observer-current.json')
UNKNOWN = ['legacy_sessions_and_outputs_unknown', 'unwrapped_entrypoints_unknown',
           'provider_tool_MCP_subagent_coverage_unknown', 'Docker_SSM_external_work_unknown',
           'off_root_work_journal_unconfigured', 'output_delivery_unverified']


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def read(path, owner=0, limit=1048576):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        st = os.fstat(stream.fileno())
        require(stat.S_ISREG(st.st_mode) and st.st_uid == owner and not st.st_mode & 0o022,
                'untrusted shadow record')
        data = stream.read(limit + 1)
    require(len(data) <= limit, 'shadow record exceeds bound')
    value = json.loads(data)
    require(isinstance(value, dict), 'shadow record must be an object')
    return value


def directory(path, owner=0):
    st = Path(path).lstat()
    require(stat.S_ISDIR(st.st_mode) and st.st_uid == owner and not st.st_mode & 0o077,
            'shadow directory must be private and owned')


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def publish(path, value, *, new=False):
    data = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
    require(len(data) <= 1048576, 'shadow state too large')
    temporary = path if new else path.parent / ('.pending-' + uuid.uuid4().hex)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as out:
        out.write(data)
        out.flush()
        os.fsync(out.fileno())
    if not new:
        os.replace(temporary, path)
    sync_directory(path.parent)


def version(folder):
    return hashlib.sha256(''.join(hashlib.sha256((Path(folder) / f).read_bytes()).hexdigest()
                                  for f in ['spot_work.py', 'spot_shadow.py']).encode()).hexdigest()[:12]


def config(value):
    require(set(value) == {'schema', 'deployment_id', 'directory', 'uid'} and type(value['schema']) is int
            and value['schema'] == 1 and isinstance(value['deployment_id'], str)
            and re.fullmatch('[0-9a-f]{12}', value['deployment_id'])
            and value['directory'] == str(BASE / value['deployment_id'])
            and type(value['uid']) is int and value['uid'] == 1001, 'unknown shadow configuration')
    return value


def protected_observation(now=None):
    marker = read(OBSERVER)
    require(re.fullmatch('[0-9a-f]{12}', marker.get('deployment_id', '')) and
            marker.get('status_path') == '/var/lib/spot-protection-observer/' + marker['deployment_id'] + '/status.json'
            and marker.get('observation_only') is True and marker.get('termination_capable') is False,
            'unknown read-only observer marker')
    value = read(Path(marker['status_path']))
    now = time.time() if now is None else now
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    require(value.get('boot_id') == boot and type(value.get('observed_at')) in (int, float)
            and 0 <= now - value['observed_at'] <= 900 and value.get('observation_only') is True
            and value.get('termination_capable') is False, 'protection observation stale/unknown')
    iid = value.get('instance')
    require(isinstance(iid, str) and re.fullmatch('i-[0-9a-f]{17}', iid)
            and any(i.get('InstanceId') == iid and i.get('ProtectedFromScaleIn') is True
                    and i.get('LifecycleState') == 'InService' for i in value.get('ASG', {}).get('Instances', [])),
            'protected live membership not observed; no new shadow job')
    return {'instance': iid, 'boot_id': boot}


def legacy_snapshot(uid=1001):
    observations = []
    for path in Path('/proc').iterdir():
        if not path.name.isdecimal():
            continue
        try:
            if path.stat().st_uid == uid:
                require(len(observations) < 512, 'legacy metadata bound exceeded; still unknown')
                observations.append({'pid': int(path.name), 'uid': uid,
                                     'pid_start': work.process_start(int(path.name)),
                                     'pid_namespace': os.readlink(path/'ns/pid')})
        except (FileNotFoundError, ProcessLookupError):
            observations.append({'pid': int(path.name), 'state': 'changed_during_observation_unknown'})
    return {'process_metadata_NOT_work_authority': observations, 'inventory_complete': False,
            'private_argv_environment_or_prompt_read': False}


def collector_gate():
    group = Path('/sys/fs/cgroup') / Path('/proc/self/cgroup').read_text().strip().split('::', 1)[1].lstrip('/')
    require((group/'memory.max').read_text().strip() == '268435456'
            and (group/'memory.swap.max').read_text().strip() == '0'
            and (group/'memory.oom.group').read_text().strip() == '1', 'shadow collector memory fence missing')
    cpu = (group/'cpu.max').read_text().split()
    require(cpu[0].isdecimal() and int(cpu[0])*4 <= int(cpu[1])
            and Path('/proc/self/oom_score_adj').read_text().strip() == '1000'
            and 'NoNewPrivs:\t1' in Path('/proc/self/status').read_text()
            and os.getpriority(os.PRIO_PROCESS, 0) == 19
            and Path('/proc/self/ns/net').stat().st_ino != Path('/proc/1/ns/net').stat().st_ino,
            'shadow collector CPU/priority/private-network fence missing')
    return {'memory_max': 268435456, 'swap_max': 0, 'oom_group': 1,
            'cpu_max': (group/'cpu.max').read_text().strip()}


class Store:
    def __init__(self, root, owner=0):
        self.root = Path(root)
        self.owner = owner

    def check(self):
        directory(self.root, self.owner)
        directory(self.root / 'jobs', self.owner)
        seed = read(self.root / 'seed.json', self.owner)
        require(seed.get('schema') == 1 and seed.get('mode') == 'shadow_only'
                and seed.get('unknown') == UNKNOWN and seed.get('termination_capable') is False,
                'shadow seed unknown; never initialize/reset over it')
        return seed

    def initialize(self, binding):
        # Explicit one-time seed of an ISOLATED shadow namespace; never ready.
        directory(self.root, self.owner)
        require(not os.path.lexists(self.root / 'seed.json') and not os.path.lexists(self.root / 'jobs'),
                'existing/partial shadow namespace; inspection required, no reseed')
        (self.root / 'jobs').mkdir(mode=0o700)
        publish(self.root / 'seed.json', {'schema': 1, 'mode': 'shadow_only', 'unknown': UNKNOWN,
                'binding': binding, 'created_at': time.time(), 'termination_capable': False}, new=True)
        self.check()

    def job(self, ident):
        require(isinstance(ident, str) and re.fullmatch('job-[0-9a-f]{32}', ident), 'invalid shadow job ID')
        path = self.root / 'jobs' / ident
        directory(path, self.owner)
        return path

    @contextmanager
    def locked(self, ident):
        self.check()
        path = self.job(ident)
        fd = os.open(path / 'lock', os.O_WRONLY | os.O_NOFOLLOW)
        try:
            st = os.fstat(fd)
            require(stat.S_ISREG(st.st_mode) and st.st_uid == self.owner and stat.S_IMODE(st.st_mode) == 0o600,
                    'untrusted shadow lock')
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield path
        finally:
            os.close(fd)

    def create(self, binding, argv):
        self.check()
        require(isinstance(argv, list) and argv and all(isinstance(x, str) and '\x00' not in x for x in argv),
                'nonempty command argv required')
        ident = 'job-' + uuid.uuid4().hex
        path = self.root / 'jobs' / ident
        path.mkdir(mode=0o700)
        fd = os.open(path / 'lock', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        now = time.time()
        record = {'schema': 1, 'id': ident, 'mode': 'shadow_only', 'uid': os.geteuid(),
                  'boot_id': binding['boot_id'], 'instance': binding['instance'], 'pid': os.getpid(),
                  'pid_start': work.process_start(os.getpid()),
                  'pid_namespace': os.readlink('/proc/self/ns/pid'), 'created_at': now, 'heartbeat_at': now,
                  'state': 'lease_before_possible_spawn', 'spawn_outcome': 'unknown_until_local_reap',
                  'argv_sha256': hashlib.sha256(json.dumps(argv, ensure_ascii=True).encode()).hexdigest(),
                  'output_delivery': 'unverified', 'external_work': 'unknown', 'termination_capable': False}
        publish(path / 'record.json', record, new=True)
        return record

    def update(self, old, **changes):
        with self.locked(old['id']) as path:
            require(read(path / 'record.json', self.owner) == old, 'changed shadow custody; no overwrite/replay')
            value = dict(old, **changes)
            publish(path / 'record.json', value)
            old.clear()
            old.update(value)

    def status(self):
        seed = self.check()
        jobs = []
        for path in (self.root / 'jobs').iterdir():
            require(len(jobs) < 1024, 'shadow listing bound exceeded; outcome unknown')
            try:
                self.job(path.name)
                value = read(path / 'record.json', self.owner)
                require(value.get('id') == path.name and value.get('mode') == 'shadow_only'
                        and value.get('termination_capable') is False, 'invalid shadow custody')
                jobs.append({'id': path.name, 'state': value.get('state'), 'boot_id': value.get('boot_id'),
                             'output_delivery': value.get('output_delivery'), 'always_blocks_termination': True})
            except (OSError, ValueError, RuntimeError):
                jobs.append({'id': path.name, 'state': 'invalid_or_partial_unknown', 'always_blocks_termination': True})
        return {'schema': 1, 'mode': 'shadow_only', 'unknown': seed['unknown'], 'jobs': jobs,
                'legacy_inventory_complete': False, 'local_only_not_off_root_custody': True,
                'all_work_idle': False, 'work_tracking_verified': False,
                'armed': False, 'termination_capable': False, 'goal_complete': False}


class Adapter:
    """Use tested subreaper/signal/uncertain-spawn path WITHOUT canonical startup."""
    def __init__(self, store, binding, argv):
        self.store, self.binding, self.argv = store, binding, argv
        self.lease = None

    def create(self, kind):
        require(kind == 'job', 'no shadow extension/approval API')
        self.lease = self.store.create(self.binding, self.argv)
        return self.lease

    def heartbeat(self, lease):
        self.store.update(lease, heartbeat_at=time.time())

    def finish_job(self, lease):
        require(lease is self.lease and lease['pid'] == os.getpid()
                and lease['pid_start'] == work.process_start(os.getpid()), 'completion owner changed')
        # run_job's local wait proof is NOT provider/external/output completion.
        self.store.update(lease, state='local_children_reaped_output_pending', spawn_outcome='local_wait_returned')


def spool_hash(path):
    h = hashlib.sha256()
    size = 0
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), 'unknown output spool')
        while data := stream.read(65536):
            h.update(data)
            size += len(data)
    return {'bytes': size, 'sha256': h.hexdigest()}


def run(store, binding, argv, uid=1001):
    require(os.geteuid() == 0 and uid == 1001, 'root-owned pilot launches only the configured user')
    require(argv and Path(argv[0]).is_absolute(), 'absolute executable required; no pre-lease shell hook')
    user = pwd.getpwuid(uid)
    space = os.statvfs(store.root)
    require(space.f_bavail * space.f_frsize >= 2 * 1024**3, 'shadow spool reserve insufficient; no new job')
    # Child-only privilege drop is itself leased, with isolated Python before hooks.
    gate = 'import os,sys,ctypes;libc=ctypes.CDLL(None,use_errno=True);assert libc.prctl(38,1,0,0,0)==0;os.setgroups([]);os.setgid(int(sys.argv[1]));os.setuid(int(sys.argv[2]));os.execvpe(sys.argv[3],sys.argv[3:],dict(PATH="/run/current-system/sw/bin",HOME=sys.argv[4],USER="sudosubin",LOGNAME="sudosubin",LANG="C.UTF-8"))'
    # HOME is supplied via the environment AFTER privilege drop, not in argv.
    gate = gate.replace('HOME=sys.argv[4]', 'HOME=' + repr(user.pw_dir))
    command = [sys.executable, '-B', '-I', '-c', gate, str(user.pw_gid), str(uid), *argv]
    adapter = Adapter(store, binding, argv)
    # A generic pilot is NON-INTERACTIVE. Never silently replace a Kiro/Herdr PTY.
    # Regular-file spooling is local-only; no delivery/idle claim even on exit0.
    original = [os.dup(n) for n in [0, 1, 2]]
    saved_create = adapter.create
    opened = []
    def create(kind):
        lease = saved_create(kind)
        path = store.job(lease['id'])
        for number, name in [(1, 'stdout'), (2, 'stderr')]:
            fd = os.open(path / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            opened.append(fd)
            os.dup2(fd, number)
        return lease
    adapter.create = create
    try:
        null = os.open('/dev/null', os.O_RDONLY)
        try:
            os.dup2(null, 0)
        finally:
            os.close(null)
        result = work.run_job(adapter, command)
        for fd in opened:
            os.fsync(fd)
    finally:
        for number, fd in zip([0, 1, 2], original):
            os.dup2(fd, number)
            os.close(fd)
        for fd in opened:
            os.close(fd)
    require(adapter.lease is not None, 'shadow lease not confirmed')
    lease = adapter.lease
    store.update(lease, exit_status=result, output_spool={name: spool_hash(store.job(lease['id']) / name)
                                                       for name in ['stdout', 'stderr']})
    return {'job': lease['id'], 'exit_status': result, 'output_spool': lease['output_spool'],
            'output_delivery': 'unverified', 'all_work_idle': False, 'termination_capable': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('seed')
    sub.add_parser('status')
    sub.add_parser('collect')
    job = sub.add_parser('run'); job.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    require(os.geteuid() == 0, 'root-owned shadow metadata only')
    cfg = config(read(args.config))
    require(version(Path(__file__).parent) == cfg['deployment_id'], 'shadow source bytes changed')
    store = Store(cfg['directory'])
    if args.action == 'seed':
        if os.path.lexists(store.root/'seed.json'):
            store.check()  # Validate old custody, NEVER reset across boot/restart.
        else:
            binding = protected_observation()
            binding['legacy_metadata'] = legacy_snapshot()
            store.initialize(binding)
        value = store.status()
    elif args.action == 'collect':
        budget = collector_gate()
        value = store.status()
        value.update(observed_at=time.time(), boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                     collector_budget=budget)
        publish(store.root/'status.json', value)
    elif args.action == 'status':
        value = store.status()
    else:
        argv = args.command[1:] if args.command[:1] == ['--'] else args.command
        value = run(store, protected_observation(), argv, cfg['uid'])
    print(json.dumps(value, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(75)
