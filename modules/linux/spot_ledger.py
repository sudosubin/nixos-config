#!/usr/bin/env python3
"""Small authoritative S3 drain/backup journal, independent of disposable root.

No TTL takeover, deletion, implicit initialization, unconditional overwrite or
retry of a lost PUT. Root files are diagnostic caches, never remote authority.
A new instance may claim only after exact EC2 termination of the old writer;
same-boot recovery must establish process exit without crossing PID namespaces.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import threading

import spot_work as work

LIMIT = 196608
DEPLOYMENT = ('account', 'region', 'asg', 'home_volume', 'home_uuid', 'uid')
STREAMS = ('drain', 'backup')
INSTANCE = re.compile(r'i-[0-9a-f]{8,17}\Z')


class Unsafe(RuntimeError):
    pass


def require(value, message):
    if not value:
        raise Unsafe(message)


def encode(value):
    data = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    require(len(data) <= LIMIT, 'durable journal exceeds its bounded record size')
    return data


def decode(data):
    require(type(data) is bytes and len(data) <= LIMIT, 'durable journal body size unknown')
    def unique(pairs):
        out = {}
        for key, value in pairs:
            require(key not in out, 'duplicate durable journal fields')
            out[key] = value
        return out
    return json.loads(data, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(Unsafe('nonfinite journal value')))


def deployment(config):
    value = {k: config[k] for k in DEPLOYMENT}
    require(re.fullmatch(r'[0-9]{12}', value['account']) and type(value['uid']) is int and value['uid'] > 0
            and all(isinstance(value[k], str) and 0 < len(value[k]) <= 256 for k in DEPLOYMENT if k != 'uid'),
            'durable deployment identity unknown')
    value['gateway_config_sha256'] = hashlib.sha256(encode(config.get('gateway'))).hexdigest()
    return value


def writer(config, protocol):
    value = {'instance_id': config['instance_id'], 'boot_id': protocol.boot_id, 'pid': os.getpid(),
             'pid_start': work.process_start(os.getpid()), 'pid_namespace': os.readlink('/proc/self/ns/pid')}
    require(valid_writer(value), 'durable writer identity unknown')
    return value


def valid_writer(value):
    return (isinstance(value, dict) and set(value) == {'instance_id', 'boot_id', 'pid', 'pid_start', 'pid_namespace'}
            and isinstance(value['instance_id'], str) and INSTANCE.fullmatch(value['instance_id'])
            and all(isinstance(value[k], str) and 0 < len(value[k]) <= 128 for k in ('boot_id', 'pid_namespace'))
            and type(value['pid']) is int and value['pid'] > 0
            and type(value['pid_start']) is int and value['pid_start'] > 0)


class S3:
    """call uses the guard's bounded instance-role-only AWS adapter.

    The caller must set AWS_MAX_ATTEMPTS=1 for PUT; GET can be retried by the
    adapter. A confirmed body/metadata GET, not a PUT receipt, establishes state.
    """
    def __init__(self, settings, call, scratch, account, uid=0):
        self.settings, self.call, self.scratch, self.uid = settings, call, Path(scratch), uid
        require(isinstance(account, str) and re.fullmatch(r'[0-9]{12}', account), 'bucket owner unknown')
        self.account = account
        require(set(settings) == {'bucket', 'key'} and re.fullmatch(r'[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]', settings['bucket'])
                and re.fullmatch(r'journal/[a-zA-Z0-9_.-]{1,100}/state.json', settings['key']),
                'durable S3 namespace must be exact and bounded')

    def directory(self):
        self.scratch.mkdir(parents=True, exist_ok=True, mode=0o700)
        info = self.scratch.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == self.uid and not info.st_mode & 0o077,
                'durable journal scratch is untrusted')
        return tempfile.TemporaryDirectory(prefix='ledger-', dir=self.scratch)

    def get(self):
        with self.directory() as folder:
            path = Path(folder) / 'body'
            # Missing/denied/error is NEVER a virgin/empty journal.
            reply = self.call('s3api', 'get-object', '--expected-bucket-owner', self.account, '--bucket', self.settings['bucket'], '--key', self.settings['key'],
                              '--checksum-mode', 'ENABLED', str(path))
            require(path.is_file() and not path.is_symlink() and path.stat().st_size <= LIMIT, 'journal body missing or excessive')
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            require(reply.get('Metadata', {}).get('sha256') == digest
                    and reply.get('ContentLength') == len(data)
                    and reply.get('ChecksumSHA256') == base64.b64encode(bytes.fromhex(digest)).decode(),
                    'durable journal checksum/body readback differs')
            tag = reply.get('ETag')
            require(isinstance(tag, str) and re.fullmatch(r'"[0-9a-f]{32}"', tag), 'durable journal ETag unknown')
            return decode(data), tag

    def put(self, value, tag):
        with self.directory() as folder:
            path = Path(folder) / 'body'; data = encode(value); path.write_bytes(data); path.chmod(0o600)
            digest = hashlib.sha256(data).hexdigest()
            args = ['--if-none-match', '*'] if tag is None else ['--if-match', tag]
            return self.call('s3api', 'put-object', '--expected-bucket-owner', self.account, '--bucket', self.settings['bucket'], '--key', self.settings['key'],
                             '--body', str(path), '--server-side-encryption', 'AES256', '--checksum-algorithm', 'SHA256',
                             '--checksum-sha256', base64.b64encode(bytes.fromhex(digest)).decode(),
                             '--metadata', 'sha256='+digest, *args)


class Ledger:
    def __init__(self, config, protocol, backend, call):
        self.identity, self.me = deployment(config), writer(config, protocol)
        self.backend, self.call = backend, call
        self.mutex = threading.RLock()
        self.value = self.tag = None

    def validate(self, value):
        require(isinstance(value, dict) and set(value) == {'schema', 'deployment', 'revision', 'writer', 'drain', 'backup'}
                and type(value['schema']) is int and value['schema'] == 1 and value['deployment'] == self.identity
                and type(value['revision']) is int and 0 <= value['revision'] < 2**63
                and (value['writer'] is None or valid_writer(value['writer']))
                and all(value[s] is None or isinstance(value[s], dict) for s in STREAMS),
                'durable journal is malformed or belongs to another deployment')
        require(value['writer'] is not None or (value['revision'] == 0 and all(value[s] is None for s in STREAMS)),
                'unowned durable state is not an explicit virgin seed')
        require(value['drain'] is not None or value['backup'] is None, 'backup without durable drain ownership')
        if value['backup'] is not None:
            require(value['backup'].get('drain_id') == value['drain'].get('id'), 'backup belongs to a different drain')
        encode(value)
        return value

    def read(self):
        value, tag = self.backend.get()
        self.value, self.tag = self.validate(value), tag
        return self.value

    def seed(self):
        """Explicit operator bootstrap ONLY; runtime never calls this method.

        No reset/force flag: If-None-Match rejects any existing object. Merely
        missing runtime state is not evidence that seeding is safe for real data.
        """
        value = {'schema': 1, 'deployment': self.identity, 'revision': 0, 'writer': None, 'drain': None, 'backup': None}
        self.backend.put(value, None)
        require(self.read() == value, 'virgin seed readback differs')

    def terminal(self, instance):
        require(isinstance(instance, str) and INSTANCE.fullmatch(instance), 'old EC2 owner identity unknown')
        reply = self.call('ec2', 'describe-instances', '--instance-ids', instance)
        reservations = reply.get('Reservations', [])
        require(isinstance(reservations, list) and len(reservations) == 1
                and reservations[0].get('OwnerId') == self.identity['account'], 'old EC2 account identity unknown')
        rows = reservations[0].get('Instances', [])
        require(isinstance(rows, list) and not reply.get('NextToken') and len(rows) == 1 and rows[0].get('InstanceId') == instance
                and rows[0].get('State', {}).get('Name') == 'terminated',
                'old EC2 writer not conclusively terminated; no takeover')

    def exited(self, old):
        if old['instance_id'] != self.me['instance_id']:
            self.terminal(old['instance_id'])
        elif old['boot_id'] == self.me['boot_id']:
            require(old['pid_namespace'] == self.me['pid_namespace'], 'cannot prove writer exit across PID namespaces')
            try:
                require(work.process_start(old['pid']) != old['pid_start'], 'durable journal writer is still alive')
            except (FileNotFoundError, ProcessLookupError):
                pass
        # Same EC2 instance with a different actual kernel boot cannot still run
        # the old kernel's process. Deployment main binds IMDS + /proc boot first.

    def commit(self, candidate):
        self.validate(candidate)
        error = None
        try:
            self.backend.put(candidate, self.tag)
        except Exception as exc:
            error = exc  # no retry or fresh ETag overwrite after an uncertain PUT
        actual = self.read()
        require(actual == candidate, 'conditional journal commit not confirmed; no action may proceed')
        # A lost receipt may be resolved ONLY by exact fresh body identity. An
        # old/competing body cannot confirm the caller's proposed revision.
        return error is None

    def current(self):
        require(os.getpid() == self.me['pid'] and work.process_start(os.getpid()) == self.me['pid_start']
                and os.readlink('/proc/self/ns/pid') == self.me['pid_namespace'],
                'forked or changed process cannot use writer authority')

    def claim(self):
        with self.mutex:
            self.current()
            self.read()
            old = self.value['writer']
            if old == self.me:
                return
            if old is not None:
                self.exited(old)
            self.commit({**self.value, 'revision': self.value['revision']+1, 'writer': self.me})

    def stream(self, name):
        require(name in STREAMS, 'unknown journal stream')
        with self.mutex:
            value = self.read()[name]
            return decode(encode(value))  # callers cannot mutate the expected authority in place

    def write(self, name, expected, value):
        require(name in STREAMS and isinstance(value, dict), 'unknown journal stream/value')
        with self.mutex:
            self.read()
            require(self.value['writer'] == self.me, 'durable writer ownership changed')
            self.current()
            require(self.value[name] == expected, 'durable stream changed; stale update refused')
            candidate = {**self.value, 'revision': self.value['revision']+1, name: value}
            old = self.value['drain']
            if name == 'drain' and old is not None and old.get('id') != value.get('id'):
                require(old.get('phase') == 'recovered' and value.get('phase') == 'created',
                        'unfinished drain cannot be replaced')
                backup = self.value['backup']
                require(backup is None or backup.get('phase') in {'successful', 'aborted', 'rejected', 'aborted_reconciled'},
                        'unfinished backup cannot be replaced by a fresh drain')
                candidate['backup'] = None  # only a known terminal previous attempt, never a force-clear
            self.commit(candidate)

    def backup_journal(self):
        return BackupJournal(self)


class BackupJournal:
    def __init__(self, ledger):
        self.ledger, self.previous = ledger, None

    def read(self):
        self.previous = self.ledger.stream('backup')
        return decode(encode(self.previous))

    def write(self, value):
        state = self.ledger.read()
        require(state['drain'] is not None, 'no drain owns this backup intent')
        value = {**value, 'drain_id': state['drain']['id']}
        self.ledger.write('backup', self.previous, value)
        self.previous = value


def configured(config, protocol, call):
    settings = config.get('durable_journal')
    if settings is None:
        return None
    return Ledger(config, protocol, S3(settings, call, config.get('journal_scratch', '/var/lib/spot-schedule-guard/remote'), config['account']), call)
