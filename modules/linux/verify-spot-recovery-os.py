#!/usr/bin/env python3
"""Disposable-only bounded readonly OS/EBS observer, never work/idle authority.

A real boot and native source services supply every fact. No readiness override,
service/control/storage mutation, arbitrary command, model/config or private-key
read is permitted. Results exclude real HM, EIP and missing-root restoration.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import tarfile
import time
import urllib.request

ACCOUNT='537112465379';REGION='ap-northeast-2';ORIGINAL='i-0c39eff85c4286b38'
UNITS=['spot-work-admission-ready','spot-scale-in-protection-ready','attach-home-volume','spot-profile-cache-restore','spot-workload-startup-ready','home-manager-sudosubin','docker','user@1001','amazon-ssm-agent']
API={('ec2','describe-instances'),('ec2','describe-volumes'),('autoscaling','describe-auto-scaling-groups'),('s3api','put-object'),('s3api','get-object')}


def require(value,message):
    if not value:raise RuntimeError(message)


def trusted(path):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd) as f:
        info=os.fstat(f.fileno());require(stat.S_ISREG(info.st_mode) and info.st_uid==0 and not info.st_mode&0o022 and info.st_size<=65536,'untrusted observer input');return json.load(f)


def command(args):
    p=subprocess.run(args,capture_output=True,text=True,timeout=60)
    require(p.returncode==0,'fixed metadata command failed: '+args[0]);return p.stdout


def api(service,action,*args):
    require((service,action) in API,'observer API roster violated');env={k:v for k,v in os.environ.items() if not k.startswith(('AWS_','AMAZON_'))}
    env.update(AWS_CONFIG_FILE='/dev/null',AWS_SHARED_CREDENTIALS_FILE='/dev/null',AWS_EC2_METADATA_DISABLED='false',AWS_MAX_ATTEMPTS='1',HOME='/var/empty')
    p=subprocess.run(['aws',service,action,*args,'--region',REGION,'--output','json'],env=env,capture_output=True,text=True,timeout=120)
    require(p.returncode==0,'observer API failed: '+service+':'+action);return json.loads(p.stdout) if p.stdout.strip() else {}


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()


def identity(scope,expected):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));url='http://169.254.169.254/latest/'
    with opener.open(urllib.request.Request(url+'api/token',method='PUT',headers={'X-aws-ec2-metadata-token-ttl-seconds':'60'}),timeout=3) as f:token=f.read().decode()
    with opener.open(urllib.request.Request(url+'dynamic/instance-identity/document',headers={'X-aws-ec2-metadata-token':token}),timeout=3) as f:i=json.load(f)
    require(i['instanceId']==expected and expected!=ORIGINAL and i['accountId']==ACCOUNT and i['region']==REGION and i['imageId']=='ami-0d44956a8229b0dad','not the isolated recovery guest')
    rows=api('ec2','describe-instances','--instance-ids',expected)['Reservations'];require(len(rows)==1 and rows[0]['OwnerId']==ACCOUNT and len(rows[0]['Instances'])==1,'instance ambiguous');instance=rows[0]['Instances'][0]
    require(instance['InstanceLifecycle']=='spot' and instance.get('IamInstanceProfile',{}).get('Arn')=='arn:aws:iam::'+ACCOUNT+':instance-profile/nixos-spot-proof-'+scope
            and {t['Key']:t['Value'] for t in instance['Tags']}.get('ScopeId')==scope,'foreign Spot/profile')
    return i


def budget():
    group='/system.slice/spot-recovery-os-observer.service';require(Path('/proc/self/cgroup').read_text().splitlines()==['0::'+group],'wrong observer cgroup');cg=Path('/sys/fs/cgroup')/group.lstrip('/')
    require((cg/'memory.max').read_text().strip()=='268435456' and (cg/'memory.swap.max').read_text().strip()=='0','unknown metadata budget');q,p=(cg/'cpu.max').read_text().split();require(q!='max' and 0<int(q)/int(p)<=.5,'unknown CPU quota')
    require(re.search(r'^NoNewPrivs:\s+1$',Path('/proc/self/status').read_text(),re.M) and Path('/proc/self/oom_score_adj').read_text().strip()=='1000','NNP/OOM differs');(cg/'memory.oom.group').write_text('1');require((cg/'memory.oom.group').read_text().strip()=='1','owned shared OOM unavailable')
    available=int(re.search(r'^MemAvailable:\s+(\d+) kB$',Path('/proc/meminfo').read_text(),re.M)[1])*1024;require(available>=2*1024**3,'insufficient metadata headroom');return cg


def ready(row):
    try:
        return (row['startup']['state']=='ready' and row['home_uuid']==row['expected_home_uuid'] and row['protected'] is True
                and all(row['units'][u]['ActiveState']=='active' and row['units'][u]['Result']=='success' for u in ['spot-scale-in-protection-ready','attach-home-volume','spot-profile-cache-restore','spot-workload-startup-ready','home-manager-sudosubin'])
                and all(row['units'][u]['ActiveState']=='active' and int(row['units'][u]['MainPID'])>0 for u in ['docker','user@1001'])
                and row['HM_fixture_started'] is True)
    except (KeyError,TypeError,ValueError):return False


def closed(row):
    try:return row['startup']['state']=='starting' and not row['home_uuid'] and all(int(row['units'][u]['MainPID'])==0 for u in ['docker','user@1001']) and row['HM_fixture_started'] is False
    except (KeyError,TypeError,ValueError):return False


def complete(case,rows,elapsed):
    if not rows:return False
    if case=='wrong':return elapsed>=160 and closed(rows[-1]) and rows[-1].get('attach_failed') is True
    if case=='positive':return ready(rows[-1])
    if case=='delayed':return any(closed(r) for r in rows[:-1]) and ready(rows[-1])
    return False


def observe(plan,cfg,folder,boot):
    start=time.monotonic();rows=[];errors=[]
    while time.monotonic()-start<600:
        try:
            units={u:dict(line.split('=',1) for line in command(['systemctl','show',u+'.service','-p','LoadState','-p','ActiveState','-p','SubState','-p','MainPID','-p','Result','-p','ExecMainStatus']).splitlines()) for u in UNITS}
            require(all(v['LoadState']=='loaded' for v in units.values()),'required unit not loaded');startup=trusted('/run/spot-work/startup');require(startup['boot_id']==boot,'startup epoch differs')
            mounted=subprocess.run(['findmnt','-n','-o','UUID','--mountpoint','/home'],capture_output=True,text=True,timeout=10);require(mounted.returncode in {0,1},'mount state unknown')
            groups=api('autoscaling','describe-auto-scaling-groups','--auto-scaling-group-names','nixos-spot-proof-'+cfg['scope'])['AutoScalingGroups'];require(len(groups)==1 and groups[0]['AutoScalingGroupARN']==plan['asg_arn'],'ASG identity differs');members=[m for m in groups[0]['Instances'] if m['InstanceId']==plan['instance']];require(len(members)==1,'member ambiguous')
            volume=api('ec2','describe-volumes','--volume-ids',cfg['homeVolume'])['Volumes'];require(len(volume)==1 and volume[0]['Encrypted'] is True and volume[0]['Size']==16,'fixture volume unknown');attachments=volume[0]['Attachments'];require(len(attachments)<=1,'ambiguous fixture attachment')
            if attachments:require(attachments[0]['InstanceId']==plan['instance'] and attachments[0]['DeleteOnTermination'] is False,'fixture custody differs')
            marker=Path('/run/spot-recovery-HM-fixture-started');row={'time':time.time(),'boot':boot,'units':units,'startup':startup,'home_uuid':mounted.stdout.strip(),'expected_home_uuid':plan['actual_home_uuid'],'protected':members[0]['ProtectedFromScaleIn'],'volume':volume[0],'HM_fixture_started':marker.exists() and marker.read_text().strip()==cfg['scope'],'attach_failed':units['attach-home-volume']['ActiveState']=='failed'}
            rows.append(row)
            with (folder/'observations.jsonl').open('a') as f:f.write(json.dumps(row)+'\n');f.flush();os.fsync(f.fileno())
            if complete(plan['case'],rows,time.monotonic()-start):break
        except Exception as error:
            errors.append({'time':time.time(),'type':type(error).__name__,'message':str(error)})
        time.sleep(5)
    return rows,errors,complete(plan['case'],rows,time.monotonic()-start)


def main():
    require(os.geteuid()==0,'root metadata observer required');cfg=trusted(os.path.realpath('/etc/spot-recovery-fixture.json'));plan=trusted('/var/lib/spot-recovery-os-plan.json');require(re.fullmatch('[0-9a-f]{12}',cfg['scope']) and plan['scope']==cfg['scope'] and plan['case'] in {'positive','wrong','delayed'} and re.fullmatch('[0-9a-f]{32}',plan['nonce']),'bad fixture plan');require(digest(__file__)==cfg['probe_sha256'],'observer bytes differ')
    cg=budget();doc=identity(cfg['scope'],plan['instance']);boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();require(boot!=plan['prior_boot'] and str(Path('/run/current-system').resolve())==plan['expected_system'],'not a new expected OS boot')
    folder=Path('/var/lib/spot-recovery-os-results')/(plan['case']+'-'+plan['nonce']+'-'+boot);folder.mkdir(mode=0o700,parents=True);rows,errors,passed=observe(plan,cfg,folder,boot)
    journal=command(['journalctl','-b','--no-pager','-o','json']);require(len(journal.encode())<=16*1024**2,'complete boot journal exceeds bound');(folder/'full-boot-journal.jsonl').write_text(journal)
    definitions=command(['systemctl','cat','--no-pager',*[u+'.service' for u in UNITS]]);(folder/'actual-units.txt').write_text(definitions)
    result={'scope':cfg['scope'],'case':plan['case'],'nonce':plan['nonce'],'boot':boot,'prior_boot':plan['prior_boot'],'current_system':str(Path('/run/current-system').resolve()),'profile_system':str(Path('/nix/var/nix/profiles/system').resolve()),'identity':doc,'expected_case_observed':passed,'errors':errors,'observations':len(rows),'last':rows[-1] if rows else None,'probe_sha256':digest(__file__),'memory_peak':(cg/'memory.peak').read_text(),'memory_events':(cg/'memory.events').read_text(),'scope_note':'real isolated OS/home/cache/user-manager/Docker; inert HM only; no EIP/missing-store/cross-root/whole tracking proof','work_tracking_verified':False,'armed':False,'goal_complete':False}
    (folder/'result.json').write_text(json.dumps(result,indent=2));archive=folder/'complete-proof.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:
        for p in folder.iterdir():
            if p.is_file() and p!=archive:tar.add(p,arcname=p.name,recursive=False)
        tar.add(__file__,arcname='observer.py',recursive=False)
    prefix='results/recovery-os/'+plan['case']+'-'+plan['nonce']+'/';bucket='nixos-spot-proof-'+ACCOUNT+'-'+cfg['scope'];body=digest(archive);api('s3api','put-object','--bucket',bucket,'--key',prefix+'complete-proof.tar.gz','--body',str(archive),'--if-none-match','*','--server-side-encryption','AES256','--checksum-algorithm','SHA256','--metadata','sha256='+body)
    read=folder/'readback-proof';reply=api('s3api','get-object','--bucket',bucket,'--key',prefix+'complete-proof.tar.gz','--checksum-mode','ENABLED',str(read));require(digest(read)==body and reply['Metadata']['sha256']==body,'boot proof body readback differs');read.unlink()
    commit={'scope':cfg['scope'],'case':plan['case'],'nonce':plan['nonce'],'boot':boot,'archive_key':prefix+'complete-proof.tar.gz','archive_sha256':body,'archive_bytes':archive.stat().st_size,'body_readback_verified':True,'expected_case_observed':passed,'errors':errors,'work_tracking_verified':False,'armed':False,'goal_complete':False};p=folder/'commit.json';p.write_text(json.dumps(commit,indent=2));api('s3api','put-object','--bucket',bucket,'--key',prefix+'commit.json','--body',str(p),'--if-none-match','*','--server-side-encryption','AES256','--checksum-algorithm','SHA256','--metadata','sha256='+digest(p));print(json.dumps(commit),flush=True)


if __name__=='__main__':main()
