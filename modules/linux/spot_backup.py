#!/usr/bin/env python3
"""Cold encrypted EBS backups. Completion, ownership and retention are separate.

A create response is NEVER a successful backup. Pending/unknown/errors cannot
release scale-in protection. The caller supplies an independently verified cold
storage predicate and a cancellable shutdown check; neither is a CPU heuristic.
"""
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import re
import time
import uuid

import spot_work as work

MANAGED = 'nixos-spot-schedule'
SCHEMA = '1'
SNAPSHOT = re.compile(r'^snap-[0-9a-f]{8,17}$')
VOLUME = re.compile(r'^vol-[0-9a-f]{8,17}$')
ATTEMPT = re.compile(r'^backup-[0-9a-f]{32}$')


class Unsafe(RuntimeError):
    pass


class AWSFailure(RuntimeError):
    """Never include credential-bearing vendor stderr in logs/records."""
    def __init__(self, service, action, code):
        self.service, self.action, self.code = service, action, code
        super().__init__(service + ':' + action + ':' + code)


def tags(row):
    values = row.get('Tags')
    if not isinstance(values, list): raise Unsafe('snapshot tags unknown')
    result = {}
    for item in values:
        if (not isinstance(item, dict) or not isinstance(item.get('Key'), str)
                or not isinstance(item.get('Value'), str) or item['Key'] in result):
            raise Unsafe('snapshot tags malformed')
        result[item['Key']] = item['Value']
    return result


def started(row):
    value = row.get('StartTime')
    if not isinstance(value, str): raise Unsafe('snapshot time unknown')
    date = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if date.tzinfo is None: raise Unsafe('snapshot time lacks timezone')
    return date.astimezone(timezone.utc)


class Journal:
    def __init__(self, path, owner=0):
        self.path, self.owner = Path(path), owner

    def read(self):
        try:
            value, _ = work.read_record(self.path, {self.owner}, limit=65536)
            return value
        except FileNotFoundError:
            return None

    def write(self, value):
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = self.path.parent.lstat()
        if (not self.path.parent.is_dir() or self.path.parent.is_symlink()
                or info.st_uid != self.owner or info.st_mode & 0o077):
            raise Unsafe('backup journal directory is untrusted')
        work.Protocol().publish(self.path, value, durable=True)


class Backup:
    def __init__(self, config, call, cold, checkpoint, journal, sleep=time.sleep, now=None):
        self.config, self.call = config, call
        self.cold, self.checkpoint, self.journal = cold, checkpoint, journal
        self.sleep = sleep
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.volume, self.account = config['home_volume'], config['account']
        self.settings = config['backup']
        self.backup_set = self.settings['set']
        if (not VOLUME.fullmatch(self.volume) or not re.fullmatch(r'[0-9]{12}', self.account)
                or not re.fullmatch(r'[a-zA-Z0-9_.-]{1,100}', self.backup_set)
                or type(self.settings.get('keep')) is not int or self.settings['keep'] != 3):
            raise Unsafe('invalid backup identity/retention policy')
        self.record = None

    def save(self, phase, **values):
        self.record.update(phase=phase, **values)
        self.journal.write(self.record)

    def base_tags(self, attempt):
        return {'ManagedBy': MANAGED, 'Purpose': 'daily-home', 'BackupSchema': SCHEMA,
                'BackupSet': self.backup_set, 'SourceVolume': self.volume,
                'AttemptId': attempt, 'Protected': 'false',
                'ColdCapture': 'unverified', 'BackupStatus': 'pending'}

    def identify(self, row):
        if (not isinstance(row, dict) or not SNAPSHOT.fullmatch(row.get('SnapshotId', ''))
                or row.get('OwnerId') != self.account or row.get('VolumeId') != self.volume
                or row.get('Encrypted') is not True):
            raise Unsafe('snapshot source/owner/encryption unknown')
        t = tags(row)
        for key, value in self.base_tags(t.get('AttemptId', '')).items():
            if key not in {'ColdCapture', 'BackupStatus'} and t.get(key) != value:
                raise Unsafe('snapshot ownership tags do not match')
        if not ATTEMPT.fullmatch(t['AttemptId']): raise Unsafe('invalid backup attempt identity')
        if t.get('ColdCapture') not in {'unverified', 'verified'} or t.get('BackupStatus') not in {'pending', 'successful'}:
            raise Unsafe('snapshot lifecycle tags unknown')
        if started(row) > self.now() + timedelta(minutes=2): raise Unsafe('snapshot starts in the future')
        return t

    def snapshot(self, ident):
        if not isinstance(ident, str) or not SNAPSHOT.fullmatch(ident):
            raise Unsafe('invalid snapshot lookup identity')
        result = self.call('ec2', 'describe-snapshots', '--snapshot-ids', ident)
        rows = result.get('Snapshots')
        if not isinstance(rows, list) or len(rows) != 1 or rows[0].get('SnapshotId') != ident:
            raise Unsafe('snapshot lookup not exact')
        self.identify(rows[0])
        return rows[0]

    def list_owned(self, attempt=None):
        expected = {'ManagedBy': MANAGED, 'Purpose': 'daily-home', 'BackupSchema': SCHEMA,
                    'BackupSet': self.backup_set, 'SourceVolume': self.volume}
        if attempt: expected['AttemptId'] = attempt
        filters = [{'Name': 'tag:' + k, 'Values': [v]} for k, v in expected.items()]
        result = self.call('ec2', 'describe-snapshots', '--owner-ids', self.account,
                           '--filters', json.dumps(filters))
        rows = result.get('Snapshots')
        if not isinstance(rows, list) or result.get('NextToken'): raise Unsafe('snapshot listing incomplete')
        # Protected snapshots are outside routine control, including inspection
        # for promotion. Never treat them as permission to delete another copy.
        owned = []
        for row in rows:
            t = tags(row)
            if t.get('Protected') == 'true': continue
            if t.get('Protected') != 'false': raise Unsafe('snapshot protection status unknown')
            self.identify(row)
            if row.get('State') not in {'pending', 'completed', 'error'}:
                raise Unsafe('owned snapshot state unknown')
            owned.append(row)
        if len({row['SnapshotId'] for row in owned}) != len(owned):
            raise Unsafe('duplicate snapshot identities in listing')
        return owned

    def set_tags(self, ident, **values):
        self.call('ec2', 'create-tags', '--resources', ident, '--tags',
                  json.dumps([{'Key': k, 'Value': v} for k, v in values.items()]))

    def prepare(self):
        """Reconcile an unknown create without blindly creating duplicates."""
        previous = self.journal.read()
        if previous is None: return
        if (previous.get('schema') != 1 or type(previous.get('schema')) is not int
                or previous.get('volume') != self.volume or previous.get('set') != self.backup_set
                or not ATTEMPT.fullmatch(previous.get('attempt', ''))):
            raise Unsafe('previous backup journal unknown')
        if previous.get('phase') in {'creating', 'uncertain'}:
            rows = self.list_owned(previous['attempt'])
            if len(rows) != 1:
                raise Unsafe('unknown create outcome; do not issue another create')
            # It is NOT a fresh backup for a later shutdown, nor cold-verified
            # merely because it became visible. A new capture is still required.
            previous.update(phase='aborted_reconciled', snapshot_id=rows[0]['SnapshotId'])
            self.journal.write(previous)
        elif previous.get('phase') == 'pending':
            row = self.snapshot(previous.get('snapshot_id'))
            if tags(row)['AttemptId'] != previous['attempt']:
                raise Unsafe('unfinished backup identity changed')
            previous.update(phase='aborted_reconciled')
            self.journal.write(previous)
        elif previous.get('phase') not in {'successful', 'aborted', 'rejected', 'aborted_reconciled'}:
            raise Unsafe('unfinished backup needs explicit recovery')

    def source(self):
        result = self.call('ec2', 'describe-volumes', '--volume-ids', self.volume)
        rows = result.get('Volumes')
        if (not isinstance(rows, list) or len(rows) != 1 or rows[0].get('VolumeId') != self.volume
                or rows[0].get('Encrypted') is not True):
            raise Unsafe('encrypted source volume not verified')
        return rows[0]

    def successful(self, ident):
        row = self.snapshot(ident); t = tags(row)
        if (row.get('State') != 'completed' or t.get('ColdCapture') != 'verified'
                or t.get('BackupStatus') != 'successful'):
            raise Unsafe('backup is not a completed verified cold success')
        return row

    def images_using(self, ids):
        if not ids: return set()
        result = self.call('ec2', 'describe-images', '--owners', self.account,
            '--include-deprecated', '--include-disabled', '--filters',
            json.dumps([{'Name': 'block-device-mapping.snapshot-id', 'Values': ids}]))
        images = result.get('Images')
        if not isinstance(images, list) or result.get('NextToken'): raise Unsafe('AMI references unknown')
        references = set()
        for image in images:
            devices = image.get('BlockDeviceMappings')
            if not isinstance(devices, list): raise Unsafe('AMI mapping unknown')
            image_refs = set()
            for device in devices:
                if not isinstance(device, dict): raise Unsafe('AMI mapping malformed')
                ebs = device.get('Ebs')
                if ebs is not None:
                    if not isinstance(ebs, dict) or not isinstance(ebs.get('SnapshotId'), str):
                        raise Unsafe('AMI snapshot identity unknown')
                    references.add(ebs['SnapshotId']); image_refs.add(ebs['SnapshotId'])
            if not image_refs.intersection(ids):
                raise Unsafe('filtered AMI response did not expose its matching snapshot')
        return references

    def retention(self, anchor):
        self.successful(anchor)
        rows = self.list_owned()
        # Previously cancelled captures are still valid recovery points ONLY if
        # cold verification was acknowledged before home/services reopened.
        for row in rows:
            t = tags(row)
            if row.get('State') == 'completed' and t['ColdCapture'] == 'verified' and t['BackupStatus'] == 'pending':
                self.checkpoint(); self.set_tags(row['SnapshotId'], BackupStatus='successful')
        rows = self.list_owned()
        refs = self.images_using([row['SnapshotId'] for row in rows])
        ordinary = [row for row in rows if row['SnapshotId'] not in refs
                    and row.get('State') == 'completed' and tags(row)['ColdCapture'] == 'verified'
                    and tags(row)['BackupStatus'] == 'successful']
        ordinary.sort(key=lambda row: (started(row), row['SnapshotId']), reverse=True)
        expired = [row['SnapshotId'] for row in ordinary[3:]]
        # Only old failed/unverified attempts can be garbage-collected, and only
        # after a fresh successful backup exists. Pending copies are untouched.
        for row in rows:
            t = tags(row)
            if (row['SnapshotId'] not in refs and started(row) < self.now()-timedelta(hours=24)
                    and (row.get('State') == 'error' or (row.get('State') == 'completed' and t['ColdCapture'] == 'unverified'))):
                expired.append(row['SnapshotId'])
        deleted = []
        for ident in dict.fromkeys(expired):
            self.checkpoint(); self.successful(anchor)
            current = self.snapshot(ident); t = tags(current)
            if self.images_using([ident]): continue
            fresh = self.list_owned()
            fresh_refs = self.images_using([x['SnapshotId'] for x in fresh])
            good = [x for x in fresh if x['SnapshotId'] not in fresh_refs and x.get('State') == 'completed'
                    and tags(x)['ColdCapture'] == 'verified' and tags(x)['BackupStatus'] == 'successful']
            good.sort(key=lambda row: (started(row), row['SnapshotId']), reverse=True)
            excess = ident in [x['SnapshotId'] for x in good[3:]]
            orphan = started(current) < self.now()-timedelta(hours=24) and (
                current.get('State') == 'error' or (current.get('State') == 'completed' and t['ColdCapture'] == 'unverified'))
            if ident != anchor and (excess or orphan):
                # IAM independently requires exact owner tags + Protected=false
                # at deletion time; EC2 independently rejects AMI-in-use copies.
                self.call('ec2', 'delete-snapshot', '--snapshot-id', ident); deleted.append(ident)
        self.successful(anchor)
        final = self.list_owned()
        final_refs = self.images_using([x['SnapshotId'] for x in final])
        remaining = [x for x in final if x['SnapshotId'] not in final_refs and x.get('State') == 'completed'
                     and tags(x)['ColdCapture'] == 'verified' and tags(x)['BackupStatus'] == 'successful']
        if len(remaining) > 3:
            raise Unsafe('retention completion not observed; do not release protection')
        return deleted

    def capture(self):
        self.prepare()
        self.checkpoint(); self.source(); self.cold()
        attempt = 'backup-' + uuid.uuid4().hex
        self.record = {'schema': 1, 'volume': self.volume, 'set': self.backup_set,
                       'attempt': attempt, 'snapshot_id': None, 'phase': 'creating'}
        self.journal.write(self.record)  # before any non-idempotent create
        try:
            try:
                response = self.call('ec2', 'create-snapshot', '--volume-id', self.volume,
                    '--description', 'Verified cold persistent home before guarded scale-in',
                    '--tag-specifications', json.dumps([{'ResourceType': 'snapshot', 'Tags':
                        [{'Key': k, 'Value': v} for k, v in self.base_tags(attempt).items()]}]))
                ident = response.get('SnapshotId')
                if not isinstance(ident, str) or not SNAPSHOT.fullmatch(ident):
                    raise Unsafe('create response has no safe snapshot identity')
                self.record['snapshot_id'] = ident
            except Exception as error:
                if getattr(error, 'code', None) in {'UnauthorizedOperation', 'AccessDenied', 'InvalidVolume.NotFound', 'InvalidParameterValue',
                        'SnapshotCreationPerVolumeRateExceeded', 'ConcurrentSnapshotLimitExceeded',
                        'RequestLimitExceeded', 'Throttling', 'ThrottlingException'}:
                    self.save('rejected'); raise
                matches = self.list_owned(attempt)
                if len(matches) != 1:
                    self.save('uncertain'); raise Unsafe('snapshot create outcome unknown') from error
                ident = matches[0]['SnapshotId']; self.record['snapshot_id'] = ident
            row = self.snapshot(ident)
            if tags(row)['AttemptId'] != attempt: raise Unsafe('snapshot attempt changed')
            self.cold()  # attest only after the create point is known
            self.set_tags(ident, ColdCapture='verified')
            self.save('pending')
            while True:
                self.checkpoint(); self.cold()
                row = self.snapshot(ident)
                state = row.get('State')
                if state == 'completed': break
                if state != 'pending': raise Unsafe('snapshot failed or state unknown')
                self.sleep(10)  # no forced completion/termination deadline
            self.set_tags(ident, BackupStatus='successful')
            self.successful(ident)
            deleted = self.retention(ident)
            self.save('successful', deleted=deleted)
            return self.successful(ident)
        except Exception:
            if self.record['phase'] not in {'uncertain', 'rejected'}:
                self.save('aborted')
            raise


def configured(config, call, cold, checkpoint):
    if not isinstance(config.get('backup'), dict):
        raise Unsafe('verified backup policy is required before a drain')
    return Backup(config, call, cold, checkpoint, Journal(config['backup']['journal']))
