#!/usr/bin/env python3
"""Explicit cloud-only integration test. Never targets live mounted storage.

Assumes a temporary least-privilege role. Only snapshots in a unique canary set
are created; no instance, attachment, EIP, ASG, user service or volume is mutated.
Credential values stay in memory and are never written to files or arguments.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import time

import spot_backup as backup


def aws(env, region, service, action, *args):
    env = env.copy()
    if service=='ec2' and action=='create-snapshot':env['AWS_MAX_ATTEMPTS']='1'
    result = subprocess.run(['aws', service, action, '--region', region, '--output', 'json', *args],
                            env=env, capture_output=True, text=True, timeout=40)
    if result.returncode:
        match = re.search(r'An error occurred \(([A-Za-z0-9_.-]+)\)', result.stderr)
        raise backup.AWSFailure(service, action, match.group(1) if match else 'UnknownTransportOrCliError')
    return json.loads(result.stdout) if result.stdout.strip() else {}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for field in ['role','account','region','volume','set','protected-snapshot','ami-snapshot','output']:
        p.add_argument('--'+field, required=True)
    a = p.parse_args()
    if (os.geteuid()!=0 or not a.set.startswith('canary-')
            or not re.fullmatch(r'arn:aws:iam::'+a.account+r':role/nixos-spot-backup-canary-[a-zA-Z0-9-]+',a.role)):
        raise ValueError('explicit root-owned isolated canary configuration required')
    base = os.environ.copy()
    for key in ['AWS_PROFILE','AWS_ACCESS_KEY_ID','AWS_SECRET_ACCESS_KEY','AWS_SESSION_TOKEN']:base.pop(key,None)
    base.update(AWS_CONFIG_FILE='/dev/null',AWS_SHARED_CREDENTIALS_FILE='/dev/null',AWS_PAGER='',AWS_MAX_ATTEMPTS='2')
    # The instance role can assume only this temporary test role. No local AWS
    # session or long-running Mac process participates after service launch.
    for attempt in range(15):
        try:
            assumed=aws(base,a.region,'sts','assume-role','--role-arn',a.role,
                        '--role-session-name','cold-backup-validation','--duration-seconds','3600');break
        except backup.AWSFailure:
            if attempt==14:raise
            time.sleep(5)
    credentials=assumed['Credentials'];env=base.copy();env.update(AWS_ACCESS_KEY_ID=credentials['AccessKeyId'],
        AWS_SECRET_ACCESS_KEY=credentials['SecretAccessKey'],AWS_SESSION_TOKEN=credentials['SessionToken'],AWS_EC2_METADATA_DISABLED='true')
    def call(service,action,*args):return aws(env,a.region,service,action,*args)
    identity=call('sts','get-caller-identity')
    assert identity['Account']==a.account and ':assumed-role/nixos-spot-backup-canary-' in identity['Arn']
    start=time.monotonic()
    def checkpoint():
        # A test infrastructure deadline, not a production work/backup deadline.
        if time.monotonic()-start>1800:raise RuntimeError('canary test infrastructure deadline')
    def cold():
        row=call('ec2','describe-volumes','--volume-ids',a.volume)['Volumes'][0]
        assert row['VolumeId']==a.volume and row['Encrypted'] is True
        assert row['State']=='available' and row['Attachments']==[]
    cold()
    cfg={'account':a.account,'home_volume':a.volume,'backup':{'set':a.set,'keep':3}}
    journal=backup.Journal(Path('/var/lib/spot-backup-canary')/a.set/'journal.json')
    obj=backup.Backup(cfg,call,cold,checkpoint,journal)
    request_tags=obj.base_tags('backup-'+'a'*32)
    spec=json.dumps([{'ResourceType':'snapshot','Tags':[{'Key':k,'Value':v} for k,v in request_tags.items()]}])
    def dry(action,expected,*args):
        for attempt in range(15):
            try:call('ec2',action,*args,'--dry-run')
            except backup.AWSFailure as error:
                # IAM grants can propagate after AssumeRole itself already
                # succeeds. Never relax the final expected permission decision.
                if expected=='DryRunOperation' and error.code=='UnauthorizedOperation' and attempt<14:
                    time.sleep(5);continue
                assert error.code==expected,(action,error.code);return
            raise AssertionError('dry run did not return a verifiable permission decision')
    dry('create-snapshot','DryRunOperation','--volume-id',a.volume,'--tag-specifications',spec)
    dry('create-snapshot','UnauthorizedOperation','--volume-id','vol-09fea2ff4615b1088','--tag-specifications',spec)
    dry('delete-snapshot','UnauthorizedOperation','--snapshot-id',a.protected_snapshot)
    sequence=[]
    for number in range(4):
        while True:
            try:snapshot=obj.capture();break
            except backup.AWSFailure as error:
                if error.code not in {'SnapshotCreationPerVolumeRateExceeded','ConcurrentSnapshotLimitExceeded','RequestLimitExceeded','Throttling','ThrottlingException'}:raise
                checkpoint();time.sleep(30)  # only confirmed NOT-accepted requests
        sequence.append(snapshot['SnapshotId']);time.sleep(1)
    rows=obj.list_owned();ordinary=[row for row in rows if row['SnapshotId']!=a.ami_snapshot]
    assert len(ordinary)==3 and set(row['SnapshotId'] for row in ordinary)==set(sequence[-3:])
    assert sequence[0] not in set(row['SnapshotId'] for row in rows)
    assert a.ami_snapshot in set(row['SnapshotId'] for row in rows)
    # Even matching source/set tags cannot grant deletion of Protected=true or
    # authority to change identity/protection tags after snapshot creation.
    dry('create-tags','UnauthorizedOperation','--resources',sequence[-1],
        '--tags',json.dumps([{'Key':'Protected','Value':'true'}]))
    keep=call('ec2','describe-snapshots','--snapshot-ids',a.protected_snapshot)['Snapshots'][0]
    assert backup.tags(keep)['Protected']=='true' and keep['State']=='completed'
    latest=obj.successful(sequence[-1]);assert latest['Encrypted'] is True
    record={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'scope':'isolated encrypted AVAILABLE candidate volume; no production workload/storage control',
        'role':a.role,'set':a.set,'source_volume':a.volume,'sequence':sequence,'retained_three':sequence[-3:],
        'protected_snapshot_preserved':a.protected_snapshot,'AMI_referenced_snapshot_preserved':a.ami_snapshot,
        'latest':latest['SnapshotId'],'all_snapshots_encrypted_completed_and_cold_verified':True,
        'real_retention_three_verified':True,'create_source_boundary_denied':True,'protected_delete_denied':True,
        'protection_tag_mutation_denied':True,'original_home_EIP_ASG_or_services_mutated':False,
        'production_armed':False,'full_work_tracking_verified':False,'goal_complete':False}
    output=Path(a.output);temp=output.with_suffix('.tmp');fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:json.dump(record,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    os.replace(temp,output)
    print(json.dumps(record),flush=True)


if __name__=='__main__':main()
