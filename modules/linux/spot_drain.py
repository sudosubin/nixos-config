#!/usr/bin/env python3
"""Durable drain ownership and protected recovery, outside the removable home.

Recovery NEVER continues an interrupted backup/scale-in as if it were fresh.
It restores service under confirmed ASG protection, or observes an already
issued release without reopening admission. Unknown jobs/leases are not erased.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import threading
import uuid

import spot_work as work

PHASES = {'created', 'fenced', 'services_stop_requested', 'services_stopped',
          'home_unmount_requested', 'home_unmounted', 'backing_up', 'backup_completed',
          'release_requested', 'released', 'recovering', 'recovered'}
IDENTITY = ('account', 'region', 'asg', 'instance_id', 'home_volume', 'home_uuid', 'uid')


class Unsafe(RuntimeError):
    pass


def owner(boot_id):
    return {'boot_id': boot_id, 'pid': os.getpid(), 'pid_start': work.process_start(os.getpid()),
            'pid_namespace': os.readlink('/proc/self/ns/pid')}


def valid_owner(value):
    return (isinstance(value, dict) and type(value.get('pid')) is int and value['pid'] > 0
            and type(value.get('pid_start')) is int and value['pid_start'] > 0
            and all(isinstance(value.get(k), str) and 0 < len(value[k]) <= 128
                    for k in ('boot_id', 'pid_namespace')))


class Transaction:
    def __init__(self, config, protocol, path, owner_uid=0, current_owner=None, ledger=None):
        self.config, self.protocol, self.path = config, protocol, Path(path)
        self.owner_uid = owner_uid
        self.owner = current_owner or owner(protocol.boot_id)
        if not valid_owner(self.owner):
            raise Unsafe('drain controller identity unknown')
        self.identity = {k: config[k] for k in IDENTITY}
        if (type(self.identity['uid']) is not int or self.identity['uid'] <= 0
                or any(not isinstance(self.identity[k], str) or not 0 < len(self.identity[k]) <= 256
                       for k in IDENTITY if k != 'uid')):
            raise Unsafe('drain deployment identity unknown')
        self.identity['gateway_config_sha256'] = hashlib.sha256(
            json.dumps(config.get('gateway'), sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.units = ['user@%d.service' % config['uid'], 'docker.service']
        self.fd = None
        self.mutex = threading.RLock()
        self.record = None
        self.ledger, self.remote_record = ledger, None

    def read(self):
        if self.ledger is not None:
            record = self.ledger.stream('drain')
            if record is not None:
                self.validate(record, foreign=True)
            self.remote_record = record
            return record  # local files are diagnostic caches, not absence/idle authority
        try:
            record, _ = work.read_record(self.path, {self.owner_uid}, limit=65536)
        except FileNotFoundError:
            return None
        return self.validate(record)

    def validate(self, record, foreign=False):
        if not isinstance(record, dict):
            raise Unsafe('drain record is not an object')
        if 'origin_instance_id' in record and not re.fullmatch(r'i-[0-9a-f]{8,17}', record['origin_instance_id']):
            raise Unsafe('drain origin instance unknown')
        identity = record.get('identity')
        if foreign and isinstance(identity, dict):
            identity = {**identity, 'instance_id': self.config['instance_id']}
            if not re.fullmatch(r'i-[0-9a-f]{8,17}', record['identity'].get('instance_id', '')):
                raise Unsafe('durable origin instance unknown')
        if (type(record.get('schema')) is not int or record['schema'] != 1
                or identity != self.identity
                or not isinstance(record.get('id'), str)
                or not re.fullmatch(r'drain-[0-9a-f]{32}', record['id'])
                or not isinstance(record.get('phase'), str) or record['phase'] not in PHASES
                or not valid_owner(record.get('owner'))
                or not isinstance(record.get('origin_boot'), str)
                or not record['origin_boot'] or type(record.get('services_may_be_stopped')) is not bool
                or not isinstance(record.get('services_before'), dict)
                or set(record['services_before']) != set(self.units)
                or any(not isinstance(v, str) or v not in {'active', 'inactive'}
                       for v in record['services_before'].values())
                or (record.get('gateway') is not None and not isinstance(record['gateway'], dict))):
            raise Unsafe('unfinished drain record is malformed or belongs to another deployment')
        if record['phase'] == 'created' and (record['services_may_be_stopped']
                or record.get('gateway') is not None or record.get('service_authority') is not None
                or record.get('snapshot_id') is not None):
            raise Unsafe('pre-action drain intent contradicts recorded side effects')
        authority = record.get('service_authority')
        allowed = self.units + ([self.config['gateway']['unit']] if self.config.get('gateway') else [])
        if authority is not None and (not valid_owner(authority)
                                      or not isinstance(authority.get('id'), str)
                                      or not re.fullmatch(r'[0-9a-f]{32}', authority['id'])
                                      or not isinstance(authority.get('units'), list)
                                      or not authority['units'] or any(u not in allowed for u in authority['units'])):
            raise Unsafe('drain service authority unknown')
        if record['phase'] in {'backup_completed', 'release_requested', 'released'}:
            if (record['services_may_be_stopped'] is not True
                    or not isinstance(record.get('snapshot_id'), str) or not record['snapshot_id']):
                raise Unsafe('drain release record lacks a completed backup boundary')
            if self.config.get('gateway') and (not record.get('gateway') or record['gateway'].get('stopped') is not True):
                raise Unsafe('drain release record lacks a confirmed Gateway stop')
        return record

    def acquire(self):
        if self.fd is not None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        info = self.path.parent.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != self.owner_uid or info.st_mode & 0o077):
            raise Unsafe('drain journal directory untrusted')
        fd = os.open(self.path.with_suffix('.lock'), os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != self.owner_uid or info.st_mode & 0o077:
                raise Unsafe('drain ownership lock untrusted')
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            os.close(fd)
            raise
        self.fd = fd

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def update(self, phase=None, **values):
        with self.mutex:
            if self.fd is None or self.record is None:
                raise Unsafe('drain journal has no exclusive controller')
            candidate = {**self.record, **values}
            if phase is not None:
                if not isinstance(phase, str) or phase not in PHASES:
                    raise Unsafe('unknown drain phase')
                candidate['phase'] = phase
            self.validate(candidate)
            if self.ledger is not None:
                self.ledger.write('drain', self.remote_record, candidate)
                self.remote_record = candidate
            self.protocol.publish(self.path, candidate, durable=True)
            self.record = candidate

    def begin(self, services):
        self.acquire()
        if self.ledger is not None:
            self.ledger.claim()
        previous = self.read()
        if previous is not None and previous['phase'] != 'recovered':
            raise Unsafe('previous drain must be reconciled before another attempt')
        if self.protocol.state() != 'open' or set(services) != set(self.units) or any(
                value not in {'active', 'inactive'} for value in services.values()):
            raise Unsafe('workload baseline or admission unknown')
        self.record = {'schema': 1, 'id': 'drain-' + uuid.uuid4().hex, 'identity': self.identity,
                       'owner': self.owner, 'origin_boot': self.owner['boot_id'], 'phase': 'created',
                       'services_before': services, 'services_may_be_stopped': False,
                       'gateway': None, 'service_authority': None, 'snapshot_id': None}
        self.update()  # Intent and owner are durable BEFORE the outer fence.
        self.protocol.seal(self.record['id'])
        self.update('fenced')

    def cancel_unstarted(self, protected=False):
        # begin() must durably advance beyond created BEFORE returning to code
        # that can prepare Gateway/stop services/unmount/backup/release. A same-
        # boot created intent therefore owns no such actions, even if its seal
        # reply or subsequent journal write was lost. Do not close open work
        # admission merely to roll that intent back. Other boots still need the
        # full startup/home/service verification path.
        if (self.record is None or self.record['phase'] != 'created'
                or self.record['origin_boot'] != self.owner['boot_id']
                or self.record.get('origin_instance_id', self.config['instance_id']) != self.config['instance_id']):
            return False
        if self.fd is None:
            raise Unsafe('pre-action cancellation has no exclusive controller')
        self.validate(self.record)
        self.protocol.reopen_unstarted(self.record['id'], protected=protected)
        self.update('recovered', recovery_outcome='no_actions_started')
        return True

    def gateway(self, value):
        self.update(gateway=value)

    def claim(self):
        self.acquire()
        if self.ledger is not None:
            self.ledger.claim()
        record = self.read()
        if record is None:
            raise Unsafe('no durable drain to reconcile')
        replaced = record['identity']['instance_id'] != self.config['instance_id']
        if replaced:
            if self.ledger is None:
                raise Unsafe('replacement recovery requires authoritative off-root intent')
            self.ledger.confirm_terminal(record['identity']['instance_id'])
        old = record['owner']
        if not replaced and old != self.owner and old['boot_id'] == self.owner['boot_id']:
            if old['pid_namespace'] != self.owner['pid_namespace']:
                raise Unsafe('cannot prove controller exit across PID namespaces')
            try:
                if work.process_start(old['pid']) == old['pid_start']:
                    raise Unsafe('original drain controller is still alive')
            except (FileNotFoundError, ProcessLookupError):
                pass
        self.record = record
        values = {'owner': self.owner}
        if replaced:
            values.update(identity=self.identity, origin_instance_id=record.get('origin_instance_id', record['identity']['instance_id']))
        self.update(**values)
        return record

    @contextmanager
    def authority(self, units):
        old = self.record.get('service_authority')
        self.protocol.retire_recovery(old)
        value = {**self.owner, 'units': units, 'id': uuid.uuid4().hex}
        self.update(service_authority=value)  # BEFORE granting startup permission.
        with self.protocol.recover_services(units, authority_id=value['id']):
            yield
        self.update(service_authority=None)

    def recover(self, operations, force=False):
        """operations is the guard's bounded AWS/storage/service adapter."""
        self.claim()
        record = self.record
        attempt = record['id']
        same_boot = (record['origin_boot'] == self.owner['boot_id']
                     and record.get('origin_instance_id', self.config['instance_id']) == self.config['instance_id'])
        group = operations.group()
        members = [i for i in group['Instances'] if i.get('InstanceId') == self.config['instance_id']]
        if len(members) != 1 or members[0].get('LifecycleState') != 'InService':
            raise Unsafe('instance no longer safely recoverable; do not restart workloads')
        protected = members[0].get('ProtectedFromScaleIn')
        if type(protected) is not bool:
            raise Unsafe('instance protection unknown')
        # A durable release + still-closed matching fence is an irreversible
        # boundary, not a logging failure to undo. Explicitly superseded wake/
        # SSM/window requests may recover ONLY after protection is reconfirmed.
        if (record['phase'] in {'release_requested', 'released'} and same_boot and not force
                and protected is False and self.protocol.state() in {'releasing', 'released'}
                and self.protocol.attempt_id() == attempt and operations.request_current(group) is True):
            self.protocol.reconcile_fence(attempt, released=True)
            self.update('released')
            return 'released'
        operations.protect()  # Must include authoritative readback, not just ACK.
        if self.cancel_unstarted(protected=True):
            return 'recovered'
        self.protocol.reconcile_fence(attempt, protected=True)
        old_boot = not same_boot
        self.update('recovering')
        self.protocol.retire_recovery(record.get('service_authority'))
        self.update(service_authority=None)
        if self.ledger is not None:
            operations.backup(self.ledger.backup_journal())  # unknown create must settle BEFORE mounting or accepting work
        operations.home()
        restore = [u for u, state in record['services_before'].items() if state == 'active']
        if restore and (record['services_may_be_stopped'] or old_boot):
            with self.authority(restore):
                operations.services(restore)
        # Gateway grants a separate, narrow permit only when it has established
        # that an owned idle/commit transition needs an actual service startup.
        operations.gateway(record.get('gateway'), old_boot, self.authority, self.gateway)
        operations.verified(record['services_before'])
        self.protocol.unseal(attempt)
        self.update('recovered', service_authority=None)
        return 'recovered'
