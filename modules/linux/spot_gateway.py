#!/usr/bin/env python3
"""Non-forcing, process-bound OpenClaw suspend control for the resident guard.

A readonly status is NOT a complete idle proof. Only a preserve/drain=false
prepare, verified ownership/custody, and the resident's atomic stop commitment
can authorize stopping its service. Unknown outcomes keep the outer fence shut.
"""
import json
import math
import os
from pathlib import Path
import pwd
import re
import subprocess
import threading
import time
import uuid

import spot_work as work


class Unsafe(RuntimeError):
    pass


class Busy(Unsafe):
    """A verified non-forcing rejection, not an unknown outcome."""


def integer(value):
    return type(value) is int and value >= 0


def custody(value):
    if not isinstance(value, list) or len(value) > 64:
        raise Unsafe('gateway write custody unknown')
    if any(not isinstance(row, dict) or not isinstance(row.get('phase'), str)
           or not integer(row.get('count')) for row in value):
        raise Unsafe('gateway write custody malformed')
    if any(row['count'] != 0 for row in value):
        raise Unsafe('gateway still owns writes')


def busy(data):
    return (isinstance(data, dict) and data.get('status') == 'busy'
            and data.get('reason') in {'active-work', 'gateway-draining'}
            and integer(data.get('activeCount')) and isinstance(data.get('blockers'), list)
            and isinstance(data.get('writeCustody'), list) and 'suspensionId' not in data
            and all(isinstance(x, dict) and isinstance(x.get('phase'), str)
                    and integer(x.get('count')) for x in data['writeCustody']))


class LocalRPC:
    def __init__(self, config, uid):
        self.config = config
        self.uid = uid
        self.user = pwd.getpwuid(uid)
        self.boot_id = None

    def environment(self):
        # Never inherit a Mac/operator's AWS credentials or remote gateway URL.
        return {'HOME': self.user.pw_dir, 'USER': self.user.pw_name,
                'LOGNAME': self.user.pw_name, 'XDG_RUNTIME_DIR': f'/run/user/{self.uid}',
                'DBUS_SESSION_BUS_ADDRESS': f'unix:path=/run/user/{self.uid}/bus',
                'PATH': '/run/current-system/sw/bin:/etc/profiles/per-user/'+self.user.pw_name+'/bin',
                'AWS_CONFIG_FILE': '/dev/null', 'AWS_SHARED_CREDENTIALS_FILE': '/dev/null'}

    def user_command(self, argv, timeout=20):
        return subprocess.check_output(argv, text=True, timeout=timeout,
            stderr=subprocess.DEVNULL, env=self.environment(), user=self.uid,
            group=self.user.pw_gid, extra_groups=os.getgrouplist(self.user.pw_name, self.user.pw_gid))

    def __call__(self, method, params):
        raw = self.user_command([self.config['node'], str(Path(__file__).with_name('spot-gateway-rpc.mjs')),
             self.config['vendor_dir'], method, json.dumps(params, separators=(',', ':')), self.boot_id or ''])
        data = json.loads(raw)
        boot = data.get('boot_id')
        if not isinstance(boot, str) or not boot or (self.boot_id and boot != self.boot_id):
            raise Unsafe('gateway connection changed')
        self.boot_id = boot
        if not isinstance(data.get('result'), dict):
            raise Unsafe('gateway control response unknown')
        return data['result']


class UserService:
    def __init__(self, rpc, unit, startup_check):
        if not re.fullmatch(r'[a-zA-Z0-9@_.-]+\.service', unit):
            raise Unsafe('invalid gateway service identity')
        self.rpc, self.unit, self.startup_check = rpc, unit, startup_check

    def show(self):
        raw = self.rpc.user_command(['systemctl', '--user', 'show', self.unit,
            '--property=MainPID,ActiveState,ExecCondition,TimeoutStopUSec,SendSIGKILL'])
        return dict(line.split('=', 1) for line in raw.splitlines() if '=' in line)

    def current(self):
        data = self.show()
        pid = int(data.get('MainPID', '0'))
        if data.get('ActiveState') != 'active' or pid <= 0 or work.process_uid(pid) != self.rpc.uid:
            raise Unsafe('gateway service is not a verified active workload')
        return {'pid': pid, 'pid_start': work.process_start(pid)}

    def fence_verified(self):
        # Must be a loaded condition, not merely a file we intended to install.
        data = self.show()
        expected = self.startup_check+' check-service-open '+self.unit
        conditions = re.findall(r'\{([^{}]*)\}', data.get('ExecCondition', ''))
        checked = any('argv[]='+expected+' ;' in row and 'ignore_errors=no' in row for row in conditions)
        return checked and data.get('TimeoutStopUSec') == 'infinity' and data.get('SendSIGKILL') == 'no'

    def assert_stopped(self):
        data = self.show()
        if data.get('ActiveState') != 'inactive' or data.get('MainPID') != '0':
            raise Unsafe('gateway service stop not confirmed')

    def stop(self, target):
        data = self.show()
        pid = int(data.get('MainPID', '0'))
        if pid and (pid != target['pid'] or work.process_start(pid) != target['pid_start']):
            raise Unsafe('refusing to stop a replacement gateway')
        if not self.fence_verified():
            raise Unsafe('gateway restart/stop safety policy changed')
        self.rpc.user_command(['systemctl', '--user', 'stop', self.unit], timeout=100)
        self.assert_stopped()

    def start(self):
        self.rpc.user_command(['systemctl', '--user', 'start', self.unit], timeout=100)


class Gateway:
    def __init__(self, rpc, manager, fence, publish=lambda value: None,
                 wall=time.time, monotonic=time.monotonic):
        self.rpc, self.manager, self.fence, self.publish = rpc, manager, fence, publish
        self.wall, self.monotonic = wall, monotonic
        self.lock = threading.RLock()
        self.request_id = 'spot-' + uuid.uuid4().hex
        self.target = None
        self.lease_id = None
        self.expires = None
        self.deadline = 0
        self.effect = 'not_attempted'
        self.failed = False
        self.committed = False
        self.stopped = False
        self.done = threading.Event()
        self.thread = None

    def journal(self):
        self.publish({'schema': 1, 'request_id': self.request_id, 'target': self.target,
                      'suspension_id': self.lease_id, 'expires_at_ms': self.expires,
                      'effect': self.effect, 'committed': self.committed, 'stopped': self.stopped,
                      'unknown': self.failed, 'connection_boot_id': self.rpc.boot_id})

    def bind(self):
        local = self.manager.current()
        remote = self.rpc('system.info', {})
        if (type(remote.get('pid')) is not int or remote['pid'] != local['pid']
                or not isinstance(remote.get('processInstanceId'), str) or not remote['processInstanceId']):
            raise Unsafe('gateway process identity mismatch')
        self.target = {**local, 'processInstanceId': remote['processInstanceId']}
        return self.target

    def assert_current(self):
        if not self.target or self.manager.current() != {k: self.target[k] for k in ('pid', 'pid_start')}:
            raise Unsafe('gateway process changed')

    def observe(self):
        self.bind()
        status = self.rpc('status', {'includeChannelSummary': False})
        if status.get('pid') != self.target['pid'] or status.get('runtimeVersion') != '2026.10.3':
            raise Unsafe('unverified gateway runtime')
        budget = status.get('shutdownBudget')
        # nativeStopBudget means a FINITE supervisor deadline, not capability
        # or idle. It is correctly false for our required infinite stop policy.
        if not isinstance(budget, dict) or type(budget.get('nativeStopBudget')) is not bool:
            raise Unsafe('gateway lifecycle budget unavailable')
        counts = budget.get('activeWork')
        required = {'rootRequests', 'cronRuns', 'sessionMutations', 'terminalPersistence', 'lifecycleWrites'}
        if not isinstance(counts, dict) or not required.issubset(counts) or any(not integer(counts[k]) for k in required):
            raise Unsafe('gateway maintenance projection malformed')
        # Other agent/queue/background work is intentionally NOT inferred idle.
        return {'observable': True, 'maintenance_busy': any(counts[k] for k in required),
                'pid': self.target['pid'], 'complete_idle_proof': False}

    def accept(self, data, started, initial=False):
        if not isinstance(data, dict) or data.get('status') != 'ready':
            raise Unsafe('gateway not ready without interrupting work')
        ident, expiry = data.get('suspensionId', self.lease_id), data.get('expiresAtMs')
        if not isinstance(ident, str) or not 0 < len(ident) <= 128 or (self.lease_id and ident != self.lease_id):
            raise Unsafe('gateway suspension identity changed')
        # Remember an identifiable lease BEFORE validating the rest: malformed
        # custody/expiry must not make rollback forget an already held fence.
        self.lease_id = ident
        if type(expiry) not in (int, float) or not math.isfinite(expiry):
            raise Unsafe('gateway lease expiry unknown')
        remaining = expiry / 1000 - self.wall()
        if not 30 < remaining <= 125:
            raise Unsafe('gateway suspension expired or implausible')
        custody(data.get('writeCustody'))
        if ((initial or 'activeCount' in data)
                and (data.get('activeCount') != 0 or type(data.get('activeCount')) is not int)):
            raise Unsafe('gateway reports active or unknown work')
        if (initial or 'blockers' in data) and data.get('blockers') != []:
            raise Unsafe('gateway reports blockers')
        self.expires = expiry
        self.deadline = started + min(remaining, 120)
        self.effect = 'held'
        self.journal()

    def renew(self):
        with self.lock:
            if self.committed or self.done.is_set(): return
            if not self.fence(): raise Unsafe('outer work fence is not closed')
            self.assert_current()
            started = self.monotonic()
            data = self.rpc('gateway.suspend.prepare', {'requestId': self.request_id,
                       'terminalPolicy': 'preserve', 'drain': False})
            self.accept(data, started, initial=True)
            self.check()

    def check(self):
        with self.lock:
            if self.failed or self.committed or not self.fence():
                raise Unsafe('gateway suspend ownership unknown')
            self.assert_current()
            started = self.monotonic()
            data = self.rpc('gateway.suspend.status', {'suspensionId': self.lease_id, 'includeLifecycle': True})
            if data.get('ownerId') != self.request_id or 'phase' in data:
                raise Unsafe('gateway suspension owner/lifecycle changed')
            self.accept(data, started)
            if self.monotonic() >= self.deadline - 15:
                raise Unsafe('gateway suspension no longer fresh')

    def acquire(self):
        with self.lock:
            if not self.fence() or not self.manager.fence_verified():
                raise Unsafe('gateway restart admission is not installed')
            self.observe()
            self.effect = 'uncertain'
            self.journal()  # persist request ID before any mutating RPC
            started = self.monotonic()
            data = self.rpc('gateway.suspend.prepare', {'requestId': self.request_id,
                         'terminalPolicy': 'preserve', 'drain': False})
            if busy(data):
                self.effect = 'busy'; self.journal()
                raise Busy('gateway busy; existing work preserved')
            self.accept(data, started, initial=True)
            self.check()
        def pulse():
            while not self.done.wait(20):
                try: self.renew()
                except Exception:
                    with self.lock:
                        self.failed = True
                        try: self.journal()
                        except Exception: pass
                    return
        self.thread = threading.Thread(target=pulse, daemon=True)
        self.thread.start()

    def stop(self):
        # Atomic resident commit validates both PID + process-start identity and
        # live suspension. No time-of-check/systemctl-stop race against expiry.
        with self.lock:
            self.check()
            original = self.expires
            self.effect = 'commit_uncertain'; self.journal()
            result = self.rpc('gateway.suspend.handoff', {'suspensionId': self.lease_id, 'commit': True,
                       'target': {k: self.target[k] for k in ('pid', 'processInstanceId')}})
            if (result.get('status') != 'committed' or result.get('suspensionId') != self.lease_id
                    or result.get('expiresAtMs') != original):
                raise Unsafe('gateway stop commitment unknown')
            self.committed = True; self.journal()
        self.close()
        # The loaded ExecCondition prevents a failed exit from starting a new
        # gateway behind the outer fence. Only now may systemd settle the unit.
        self.manager.stop(self.target)
        self.stopped = True; self.journal()

    def close(self):
        self.done.set()
        if self.thread is not None: self.thread.join()

    def restore_snapshot(self, snapshot, boot_changed=False, authority=None):
        """Recover a dead controller, without treating an unknown commit as stop.

        Exact retired handoff commits are idempotent in the pinned vendor ABI.
        They are retried ONLY after lifecycle status proves that same lease is
        already retiring, never against a live prepared lease. Otherwise resume
        our own lease, observe running, or wait for an owned process to exit.
        """
        self.close()
        if not self.fence() or not self.manager.fence_verified():
            raise Unsafe('protected recovery requires the enforced startup fence')
        if snapshot is not None:
            if (not isinstance(snapshot, dict) or type(snapshot.get('schema')) is not int
                    or snapshot['schema'] != 1 or not isinstance(snapshot.get('request_id'), str)
                    or not re.fullmatch(r'spot-[0-9a-f]{32}', snapshot['request_id'])
                    or not isinstance(snapshot.get('effect'), str)
                    or snapshot['effect'] not in {'uncertain', 'busy', 'held', 'commit_uncertain',
                                                       'restored', 'resumed'}
                    or any(type(snapshot.get(k)) is not bool for k in ('committed', 'stopped', 'unknown'))):
                raise Unsafe('Gateway recovery record unknown')
            target = snapshot.get('target')
            if (not isinstance(target, dict) or type(target.get('pid')) is not int or target['pid'] <= 0
                    or type(target.get('pid_start')) is not int or target['pid_start'] <= 0
                    or not isinstance(target.get('processInstanceId'), str) or not target['processInstanceId']
                    or not isinstance(snapshot.get('connection_boot_id'), str)
                    or not snapshot['connection_boot_id']):
                raise Unsafe('Gateway recovery process/connection identity unknown')
            lease = snapshot.get('suspension_id')
            if ((lease is not None and (not isinstance(lease, str) or not 0 < len(lease) <= 128))
                    or (snapshot['effect'] in {'held', 'commit_uncertain'} and lease is None)):
                raise Unsafe('Gateway recovery lease identity unknown')
            self.request_id, self.target, self.lease_id = snapshot['request_id'], target, lease
            self.expires, self.effect = snapshot.get('expires_at_ms'), snapshot['effect']
            self.committed, self.stopped = snapshot['committed'], snapshot['stopped']
            self.rpc.boot_id = snapshot['connection_boot_id']
        data = self.manager.show()
        state, pid = data.get('ActiveState'), data.get('MainPID')
        old_target = self.target
        def old_alive():
            if boot_changed or old_target is None:
                return False
            try:
                return work.process_start(old_target['pid']) == old_target['pid_start']
            except (FileNotFoundError, ProcessLookupError):
                return False
        def running():
            self.observe()
            result = self.rpc('gateway.suspend.status', {'suspensionId': self.lease_id or self.request_id,
                                                        'includeLifecycle': True})
            if result != {'status': 'running'}:
                raise Unsafe('Gateway scheduling/admission has not recovered')
            self.committed = self.stopped = self.failed = False
            self.lease_id = self.expires = None
            self.effect = 'restored'
            self.journal()
        def start():
            if authority is None:
                raise Unsafe('Gateway startup recovery authority unavailable')
            with authority([self.manager.unit]):
                self.manager.start()
                self.rpc.boot_id = None
                deadline = self.monotonic() + 90
                while True:
                    try:
                        running()
                        break
                    except Exception:
                        if self.monotonic() >= deadline:
                            raise
                        time.sleep(1)
        if state in {'inactive', 'failed'} and pid == '0':
            if old_alive():
                raise Unsafe('old Gateway still exists outside the inactive service')
            if not (boot_changed or self.committed or self.effect in {'held', 'commit_uncertain', 'restored'}):
                raise Unsafe('no owned idle/commit transition authorizes a new Gateway')
            start()
            return
        if state != 'active':
            raise Unsafe('Gateway is transitioning; retry without forcing a stop')
        local = self.manager.current()
        if boot_changed or old_target is None or local != {k: old_target[k] for k in ('pid', 'pid_start')}:
            if old_alive():
                raise Unsafe('refusing to replace a still-live original Gateway')
            self.rpc.boot_id = None
            running()  # Observe a replacement; never stop/restart it.
            return
        # A held vendor fence intentionally rejects system.info. The persisted
        # connection boot ID is checked by the RPC helper BEFORE dispatch, in
        # addition to this local PID/start check. Rebind system.info only AFTER
        # confirmed resume; handoff additionally checks processInstanceId itself.
        self.assert_current()
        if self.lease_id is None:
            if self.effect in {'busy', 'restored', 'resumed'}:
                running()
                return
            data = self.rpc('gateway.suspend.prepare', {'requestId': self.request_id,
                            'terminalPolicy': 'preserve', 'drain': False})
            if busy(data):
                running()
                return
            self.accept(data, self.monotonic(), initial=True)
        data = self.rpc('gateway.suspend.status', {'suspensionId': self.lease_id, 'includeLifecycle': True})
        if data == {'status': 'running'}:
            running()
            return
        if data.get('ownerId') != self.request_id:
            raise Unsafe('Gateway recovery must not take over another suspension')
        phase = data.get('phase')
        if data.get('status') == 'draining' and phase in {'interrupting', 'exiting'}:
            if not (self.committed or self.effect == 'commit_uncertain'):
                raise Unsafe('external Gateway teardown; do not manufacture a stop')
            result = self.rpc('gateway.suspend.handoff', {'suspensionId': self.lease_id, 'commit': True,
                          'target': {k: old_target[k] for k in ('pid', 'processInstanceId')}})
            if (result.get('status') != 'committed' or result.get('suspensionId') != self.lease_id
                    or result.get('expiresAtMs') != self.expires):
                raise Unsafe('retired Gateway commitment still unknown')
            self.committed = True
            self.journal()
            self.manager.stop(old_target)  # Only after the exact idempotent ACK.
            self.stopped = True
            self.journal()
            start()
            return
        if data.get('status') not in {'ready', 'draining'} or phase not in {None, 'draining'}:
            raise Unsafe('Gateway recovery lifecycle unknown')
        result = self.rpc('gateway.suspend.resume', {'suspensionId': self.lease_id})
        if result.get('ok') is not True or result.get('status') != 'running':
            raise Unsafe('Gateway scheduler recovery unconfirmed')
        running()

    def rollback(self):
        self.close()
        with self.lock:
            if self.committed:
                if not self.stopped:
                    # Acknowledged atomic commit authorizes settling this unit;
                    # startup is still fenced, so it cannot be a new worker.
                    self.manager.stop(self.target); self.stopped = True
                self.manager.start()
                self.rpc.boot_id = None
                deadline = self.monotonic() + 90
                while True:
                    try:
                        self.observe()  # new gateway must actually be RPC-ready
                        break
                    except Exception:
                        if self.monotonic() >= deadline: raise
                        time.sleep(1)
                self.effect = 'restored'; self.journal()
                return
            if self.effect in {'not_attempted', 'busy'}:
                return  # Busy prepare explicitly rolled its own admission back.
            self.assert_current()
            if self.lease_id is None:
                # A lost prepare reply may have left a lease. Same request ID
                # recovers it without taking over another maintenance owner.
                data = self.rpc('gateway.suspend.prepare', {'requestId': self.request_id,
                               'terminalPolicy': 'preserve', 'drain': False})
                if busy(data):
                    self.effect = 'busy'; self.journal(); return
                self.accept(data, self.monotonic(), initial=True)
            result = self.rpc('gateway.suspend.resume', {'suspensionId': self.lease_id})
            if result.get('ok') is not True or result.get('status') != 'running':
                raise Unsafe('gateway scheduler/admission recovery unconfirmed')
            result = self.rpc('gateway.suspend.status', {'suspensionId': self.lease_id, 'includeLifecycle': True})
            if result != {'status': 'running'}:
                raise Unsafe('gateway admission did not reopen')
            self.effect = 'resumed'; self.journal()


def configured(config, protocol, publish=None):
    cfg = config.get('gateway')
    if cfg is None:
        return None
    if not isinstance(cfg, dict):
        raise Unsafe('gateway configuration unknown')
    rpc = LocalRPC(cfg, config['uid'])
    manager = UserService(rpc, cfg['unit'], cfg['startup_check'])
    return Gateway(rpc, manager, lambda: protocol.state() == 'draining',
                   publish or (lambda value: protocol.publish(protocol.runtime / 'gateway-control.json', value)))
