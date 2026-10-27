#!/usr/bin/env python3
"""Verify ONLY a newly restored, tagged canary EBS copy. Never run applications.

Does not create/attach/detach/delete storage. Metadata/device/UUID are checked
before making this COPY readonly; compatible fsck is read-only, and mounting is
ro,noload in a private mount namespace. No credentials or personal file content
are printed. Original root/home/candidate volumes are explicitly prohibited.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

PROHIBITED={'vol-065729ef75553a7ec','vol-09fea2ff4615b1088','vol-0b529abe51df1eca1'}


def output(argv,**kwargs):return subprocess.check_output(argv,text=True,**kwargs).strip()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['volume','snapshot','set','uuid','output']:p.add_argument('--'+name,required=True)
    a=p.parse_args()
    assert os.geteuid()==0 and a.set.startswith('canary-')
    assert re.fullmatch(r'vol-[0-9a-f]{17}',a.volume) and a.volume not in PROHIBITED
    assert re.fullmatch(r'snap-[0-9a-f]{17}',a.snapshot)
    env=os.environ.copy()
    for key in ['AWS_PROFILE','AWS_ACCESS_KEY_ID','AWS_SECRET_ACCESS_KEY','AWS_SESSION_TOKEN']:env.pop(key,None)
    env.update(AWS_CONFIG_FILE='/dev/null',AWS_SHARED_CREDENTIALS_FILE='/dev/null',AWS_PAGER='')
    rows=json.loads(output(['aws','ec2','describe-volumes','--region','ap-northeast-2','--volume-ids',a.volume,'--output','json'],env=env))['Volumes']
    assert len(rows)==1
    row=rows[0];tags={x['Key']:x['Value'] for x in row['Tags']}
    assert row['VolumeId']==a.volume and row['SnapshotId']==a.snapshot and row['Encrypted'] is True
    assert tags['Purpose']=='backup-restore-canary' and tags['BackupSet']==a.set
    assert row['State']=='in-use' and len(row['Attachments'])==1 and row['Attachments'][0]['State']=='attached'
    devices=[]
    for attempt in range(30):
        devices=[Path('/dev')/q.parent.parent.name for q in Path('/sys/class/block').glob('nvme*n1/device/serial')
                 if q.read_text().strip().replace('-','')==a.volume.replace('-','')]
        if devices:break
        time.sleep(1)
    assert len(devices)==1
    device=devices[0]
    assert output(['blkid','-s','UUID','-o','value',str(device)])==a.uuid
    mounted=subprocess.run(['findmnt','-rn','-S',str(device)],capture_output=True)
    assert mounted.returncode==1
    subprocess.run(['blockdev','--setro',str(device)],check=True)
    assert output(['blockdev','--getro',str(device)])=='1'
    checker=next((q for q in Path('/nix/store').glob('*-e2fsprogs-1.47.4*/bin/e2fsck')
                  if q.is_file() and re.search(r'-e2fsprogs-1\.47\.4(?:-bin)?$',q.parent.parent.name)),None)
    assert checker is not None,'previously verified compatible e2fsck required'
    check=subprocess.run([str(checker),'-f','-n',str(device)],capture_output=True,text=True,timeout=600)
    assert check.returncode==0,'restored copy failed read-only filesystem check'
    # Only public cache metadata and ownership are inspected, never app startup,
    # user transcripts, secrets, credential contents or production mounts.
    code=r'''import json,os,subprocess,sys
from pathlib import Path
root=Path(sys.argv[2]);subprocess.run(['mount','-o','ro,noload',sys.argv[1],str(root)],check=True)
try:
 user=root/'sudosubin';assert user.is_dir() and user.stat().st_uid==1001
 assert (root/'persist').is_dir() and (root/'docker-data').is_dir()
 cache=json.loads((root/'persist/manifests/profile-cache.json').read_text());assert cache['schema']==1
 assert isinstance(cache['roots'],list) and cache['roots']
 print(json.dumps({'uid1001_home_verified':True,'persistent_docker_directory_present':True,'cache_manifest_schema':cache['schema'],'cache_roots_count':len(cache['roots']),'private_content_not_logged':True}))
finally:subprocess.run(['umount',str(root)],check=True)
'''
    with tempfile.TemporaryDirectory(prefix='spot-backup-restore-',dir='/run') as temp:
        metadata=json.loads(output(['unshare','--mount','--propagation','private',sys.executable,'-c',code,str(device),temp],timeout=60))
    record={'schema':1,'restored_volume':a.volume,'snapshot':a.snapshot,'set':a.set,'encrypted':True,
            'exact_NVMe_serial_and_UUID_verified':True,'read_only_fsck_passed':True,'private_ro_noload_mount_verified':True,
            'no_application_or_model_started':True,'production_storage_not_modified':True,**metadata,
            'production_backup_rollout_verified':False,'goal_complete':False}
    destination=Path(a.output);temp=destination.with_suffix('.tmp');fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:json.dump(record,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    os.replace(temp,destination);print(json.dumps(record))


if __name__=='__main__':main()
