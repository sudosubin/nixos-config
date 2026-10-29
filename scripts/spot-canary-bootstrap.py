#!/usr/bin/env python3
"""Prepare ZERO-capacity native-ASG autonomous bootstrap; never production rollout.

NixOS amazon-init executes the fixed shell UserData. Every new ASG Spot member
gets fresh source/software/authority and a boot-specific immutable artifact run.
This is an unprotected, empty, single-root BUILD trial, NOT protected OS recovery.
This command deliberately has NO paid activate action: original-host autonomous
receipt/discovery admission must be implemented/proven before requesting capacity.
"""
import argparse
import base64
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
import zlib

spec=importlib.util.spec_from_file_location('bootstrap_build',Path(__file__).with_name('spot-build-canary.py'))
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
PUBLIC_SHA='b66b47495348028b98565b76925e722518827e5f9d1c9cbae76a18fa64d27e21'
PUBLIC_BYTES=272580380


def require(condition,message):
    if not condition:raise RuntimeError(message)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()


# No imports from an unverified source tree. Only pinned public data is fetched
# here. This 128MiB transport is NOT verification/build authority. The existing
# spot_validation actual-API attestation owns admission of ALL larger budgets.
RUNTIME=r'''from pathlib import Path
from datetime import datetime
import os,sys,json,hashlib,subprocess,urllib.request,tarfile,time,re

def require(ok,message):
 if not ok:raise RuntimeError(message)
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
def new(path,value):
 with path.open('x') as f:json.dump(value,f,indent=2);f.flush();os.fsync(f.fileno())
CONTEXT={}
def status(context,name,value):
 folder=context['folder'];path=folder/(name+'.json');new(path,value);digest=sha(path);key='results/bootstrap/'+context['config']['scope']+'/'+context['run']+'/'+name+'.json';api=context['api'];bucket=context['config']['bucket']
 api('s3api','put-object','--bucket',bucket,'--key',key,'--body',str(path),'--if-none-match','*','--expected-bucket-owner','537112465379','--server-side-encryption','AES256','--checksum-algorithm','SHA256','--metadata','sha256='+digest)
 back=folder/(name+'-readback.json');meta=api('s3api','get-object','--bucket',bucket,'--key',key,'--expected-bucket-owner','537112465379',str(back));require(sha(back)==digest==meta['Metadata']['sha256'],'bootstrap status body differs')
def entry(config):
 failure=None
 try:run(config)
 except Exception as error:
  failure={'error_type':type(error).__name__,'error':str(error)[:2000],'bootstrap_success':False,'work_tracking_verified':False,'armed':False,'goal_complete':False};error.__traceback__=None
 if failure is not None:
  import gc;gc.collect()
  if CONTEXT:
   try:status(CONTEXT,'failure',failure)
   except Exception as error:print('bootstrap failure publication unconfirmed: '+type(error).__name__,flush=True)
  raise RuntimeError(json.dumps(failure))
def run(config):
 require(sys.platform=='linux' and os.geteuid()==0,'root Linux required')
 boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
 require(re.fullmatch('[0-9a-f-]{36}',boot),'boot identity unknown')
 group=Path('/sys/fs/cgroup')/Path('/proc/self/cgroup').read_text().strip().split('::')[-1].lstrip('/')
 require(group.name=='spot-autobootstrap-'+config['scope']+'.service','foreign bootstrap cgroup')
 require((group/'memory.max').read_text().strip()=='134217728' and (group/'memory.swap.max').read_text().strip()=='0','bootstrap memory/swap unknown')
 require(Path('/proc/self/oom_score_adj').read_text().strip()=='1000' and 'NoNewPrivs:\t1' in Path('/proc/self/status').read_text(),'bootstrap priority/NNP unknown')
 require(Path('/proc/self/status').read_text().count('NoNewPrivs:')==1,'ambiguous process status')
 (group/'memory.oom.group').write_text('1');require((group/'memory.oom.group').read_text().strip()=='1','bootstrap OOM fence unavailable')
 cpu=(group/'cpu.max').read_text().split();require(len(cpu)==2 and all(x.isdecimal() for x in cpu) and 0<int(cpu[0])<=int(cpu[1])//10,'transport CPU exceeds10pct')
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with opener.open(urllib.request.Request('http://169.254.169.254/latest/api/token',method='PUT',headers={'X-aws-ec2-metadata-token-ttl-seconds':'60'}),timeout=3) as response:token=response.read(4096).decode()
 with opener.open(urllib.request.Request('http://169.254.169.254/latest/dynamic/instance-identity/document',headers={'X-aws-ec2-metadata-token':token}),timeout=3) as response:doc=json.loads(response.read(16384))
 require(doc.get('accountId')=='537112465379' and doc.get('region')=='ap-northeast-2' and doc.get('imageId')=='ami-0d44956a8229b0dad' and re.fullmatch('i-[0-9a-f]{17}',doc.get('instanceId','')) and doc['instanceId']!='i-0c39eff85c4286b38','production/foreign boot forbidden')
 iid=doc['instanceId'];env={k:v for k,v in os.environ.items() if not k.startswith(('AWS_','AMAZON_'))}
 env.update(AWS_CONFIG_FILE='/dev/null',AWS_SHARED_CREDENTIALS_FILE='/dev/null',AWS_EC2_METADATA_DISABLED='false',AWS_MAX_ATTEMPTS='1',HOME='/var/empty')
 def api(service,operation,*args):
  result=subprocess.run(['aws',service,operation,*args,'--region','ap-northeast-2','--output','json'],env=env,capture_output=True,text=True,timeout=90)
  require(result.returncode==0,'bootstrap API refused: '+service+':'+operation);return json.loads(result.stdout) if result.stdout.strip() else {}
 require(0<datetime.fromisoformat(config['expires']).timestamp()-time.time()<=7200,'bootstrap expired/unbounded')
 caller=api('sts','get-caller-identity');require(caller.get('Account')==doc['accountId'] and caller.get('Arn')=='arn:aws:sts::537112465379:assumed-role/nixos-spot-proof-'+config['scope']+'/'+iid,'foreign bootstrap role')
 reservations=api('ec2','describe-instances','--instance-ids',iid)['Reservations']
 require(len(reservations)==1 and reservations[0]['OwnerId']==doc['accountId'] and len(reservations[0]['Instances'])==1,'EC2 roster ambiguous')
 instance=reservations[0]['Instances'][0];tags={r['Key']:r['Value'] for r in instance.get('Tags',[])}
 require(len(tags)==len(instance.get('Tags',[])) and all(tags.get(k)==v for k,v in {'ScopeId':config['scope'],'ManagedBy':'nixos-spot-validation','Purpose':'artifact-test','Disposable':'true','DisposableUntil':config['expires'],'aws:autoscaling:groupName':'nixos-spot-proof-'+config['scope']}.items()),'bootstrap scope tags differ')
 require(instance.get('InstanceId')==iid and instance.get('InstanceLifecycle')=='spot' and instance.get('ImageId')==doc['imageId'] and instance.get('InstanceType')=='r7g.large' and not instance.get('KeyName') and instance['State']['Name']=='running' and instance.get('IamInstanceProfile',{}).get('Arn')=='arn:aws:iam::537112465379:instance-profile/nixos-spot-proof-'+config['scope'],'not the empty Spot builder')
 mappings=instance.get('BlockDeviceMappings',[]);require(len(mappings)==1 and mappings[0]['DeviceName']=='/dev/xvda' and mappings[0]['Ebs']['DeleteOnTermination'] is True,'retained/unknown storage attached')
 volume=mappings[0]['Ebs']['VolumeId'];require(volume not in {'vol-065729ef75553a7ec','vol-09fea2ff4615b1088','vol-0b529abe51df1eca1'},'retained volume forbidden')
 volumes=api('ec2','describe-volumes','--volume-ids',volume)['Volumes'];require(len(volumes)==1 and volumes[0]['VolumeId']==volume and volumes[0]['Encrypted'] is True and volumes[0]['Size']==32 and len(volumes[0]['Attachments'])==1 and volumes[0]['Attachments'][0]['InstanceId']==iid,'root encryption/custody differs')
 # New native members can be Pending during amazon-init. Bounded read-only
 # waiting is NOT an attachment/protection mutation or replay of a launch.
 for attempt in range(31):
  members=api('autoscaling','describe-auto-scaling-instances','--instance-ids',iid)['AutoScalingInstances']
  if len(members)==1 and members[0]['LifecycleState']=='InService':break
  require(len(members)<=1 and attempt<30,'ASG membership did not settle');time.sleep(2)
 require(members[0]['AutoScalingGroupName']=='nixos-spot-proof-'+config['scope'] and members[0]['ProtectedFromScaleIn'] is False,'protected/foreign builder forbidden')
 actions=api('autoscaling','describe-scheduled-actions','--auto-scaling-group-name',members[0]['AutoScalingGroupName'])['ScheduledUpdateGroupActions']
 require(len(actions)==1 and actions[0]['ScheduledActionName']==members[0]['AutoScalingGroupName']+'-off' and actions[0]['AutoScalingGroupName']==members[0]['AutoScalingGroupName'] and not actions[0].get('Recurrence') and datetime.fromisoformat(actions[0]['StartTime']).timestamp()==datetime.fromisoformat(config['expires']).timestamp() and all(type(actions[0].get(k)) is int and actions[0][k]==0 for k in ['MinSize','MaxSize','DesiredCapacity']),'native expiry differs')
 require(subprocess.run(['findmnt','-n','--mountpoint','/home'],capture_output=True).returncode==1,'bootstrap never writes a mounted retained home')
 base=Path('/var/lib/spot-autobootstrap');base.mkdir(mode=0o700,exist_ok=True);require(not base.is_symlink() and base.stat().st_uid==0 and not base.stat().st_mode&0o077,'bootstrap storage untrusted')
 folder=base/boot;folder.mkdir(mode=0o700) # existing boot custody is NEVER reset/retried
 identity={**doc,'root_volume':volume,'scope':config['scope'],'expires':config['expires'],'boot':boot,'not_test_success':True};new(folder/'identity.json',identity)
 run_id=hashlib.sha256((iid+':'+boot).encode()).hexdigest()[:32];CONTEXT.update(folder=folder,api=api,config=config,run=run_id)
 status(CONTEXT,'started',{'identity':identity,'authority_sha256':config['artifacts']['authority']['sha256'],'source_revision':config['revision'],'goal_complete':False})
 for name in ['source','authority','runtime']:
  item=config['artifacts'][name];path=folder/(name+'.body');reply=api('s3api','get-object','--bucket',config['bucket'],'--key',item['key'],'--expected-bucket-owner','537112465379','--checksum-mode','ENABLED',str(path))
  require(path.stat().st_size==item['bytes'] and sha(path)==item['sha256']==reply['Metadata']['sha256'],'bootstrap artifact body differs: '+name);path.chmod(0o600)
 source=folder/'source';source.mkdir(mode=0o700)
 with tarfile.open(folder/'source.body') as archive:archive.extractall(source,filter='data')
 authority=folder/'authority.body';expected=json.loads(authority.read_text());require(isinstance(expected,dict) and expected,'empty source authority')
 for name,digest in expected.items():
  part=Path(name);require(not part.is_absolute() and '..' not in part.parts and re.fullmatch('[0-9a-f]{64}',digest),'invalid source path/digest');require(sha(source/part)==digest,'source body differs')
 git=next(p for p in Path('/nix/store').glob('*-git-*/bin/git') if p.is_file())
 require(subprocess.check_output([str(git),'-C',str(source),'rev-parse','HEAD'],text=True).strip()==config['revision'],'source commit differs')
 tracked=subprocess.check_output([str(git),'-C',str(source),'ls-files','-z']).decode().split('\0');require(set(filter(None,tracked))==set(expected),'incomplete tracked source authority')
 subprocess.run([str(git),'-C',str(source),'diff','--exit-code','--quiet','HEAD','--'],check=True)
 # Public software ONLY. No home/config/key archive; never extract through a
 # symlink or into a mounted home. This path is local to the disposable root.
 destination=Path('/home/sudosubin/.local/share')
 for parent in [Path('/home'),Path('/home/sudosubin'),Path('/home/sudosubin/.local'),destination]:
  require(not parent.is_symlink(),'public runtime destination untrusted')
 destination.mkdir(mode=0o755,parents=True,exist_ok=True)
 require(not any((destination/name).exists() or (destination/name).is_symlink() for name in ['kiro-cli','openclaw-npm']),'existing runtime custody is never overwritten')
 # Archive extraction is separate private ARTIFACT work, not verification.
 # Neither a nested Python/AWS launcher nor44k TarInfo objects may expand the
 #128MiB network transport's budget or create unbounded allocation pressure.
 import importlib.util
 spec=importlib.util.spec_from_file_location('bootstrap_validation',source/'modules/linux/spot_validation.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
 extracted=folder/'public-runtime-extracted.json';receipt=v.launch([sys.executable,'-B','-I',str(source/'scripts/spot-runtime-extract.py'),'--archive',str(folder/'runtime.body'),'--output',str(extracted)],extracted,purpose='build');new(folder/'extract-launch-not-success.json',receipt)
 while not extracted.exists():
  require(time.time()<datetime.fromisoformat(config['expires']).timestamp()-900,'native lifetime too short for remaining build')
  leaf=Path('/sys/fs/cgroup')/receipt['slice'];require(leaf.exists() and 'populated 0' not in (leaf/'cgroup.events').read_text(),'owned extraction exited without result');time.sleep(.2)
 require(json.loads(extracted.read_text()).get('extracted') is True,'public extraction failed; no launch')
 leaf=Path('/sys/fs/cgroup')/receipt['slice'];settle=time.monotonic()+30
 while leaf.exists() and 'populated 0' not in (leaf/'cgroup.events').read_text():require(time.monotonic()<settle,'extractor did not settle');time.sleep(.1)
 run_id=hashlib.sha256((iid+':'+boot).encode()).hexdigest()[:32];new(folder/'bootstrap-verified-not-tests.json',{'identity':identity,'source':str(source),'authority':str(authority),'artifact_run':run_id,'memory_peak':(group/'memory.peak').read_text(),'memory_events':(group/'memory.events').read_text(),'full_regression_verified':False,'goal_complete':False})
 # The maintained launcher performs fresh actual disposable/API/memory
 # attestation, creates its OWN256MiB coordinator, then separate6GiB build and
 # private2GiB verification. No build/verification runs in this transport cage.
 result=subprocess.run(['systemd-run','--quiet','--pipe','--wait','--collect','--unit=spot-bootstrap-launch-'+config['scope'],'--property=Type=exec','--property=MemoryMax=256M','--property=MemorySwapMax=0','--property=CPUQuota=25%','--property=OOMPolicy=kill','--property=OOMScoreAdjust=1000','--property=Nice=19','--property=NoNewPrivileges=yes','--property=ProtectControlGroups=no','--setenv=PATH=/run/current-system/sw/bin','--setenv=HOME=/var/empty',sys.executable,'-B','-I',str(source/'scripts/spot-canary-pipeline.py'),'launch','--source',str(source),'--authority',str(authority),'--artifact-run',run_id],env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=120)
 new(folder/'pipeline-launch-reply-not-success.json',{'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'goal_complete':False});require(result.returncode==0,'pipeline launch refused; failure retained')
 status(CONTEXT,'staged',{'identity':identity,'artifact_run':run_id,'pipeline_launched_not_verified':True,'goal_complete':False})
 print(json.dumps({'bootstrap_staged':True,'instance':iid,'boot':boot,'artifact_run':run_id,'folder':str(folder),'launch_is_test_success':False,'goal_complete':False}))
'''


def validate_config(config):
    require(set(config)=={'scope','bucket','revision','expires','artifacts'},'unknown bootstrap configuration fields')
    require(re.fullmatch('[0-9a-f]{12}',config['scope']) and re.fullmatch('[0-9a-f]{40}',config['revision']),'exact scope/revision required')
    require(config['bucket']=='nixos-spot-proof-'+b.ACCOUNT+'-'+config['scope'],'foreign bootstrap bucket')
    deadline=datetime.fromisoformat(config['expires']);require(deadline.utcoffset() is not None,'aware bootstrap expiry required')
    require(set(config['artifacts'])=={'source','authority','runtime'},'exact public artifacts required')
    for name,item in config['artifacts'].items():
        require(set(item)=={'key','bytes','sha256'} and item['key']=='artifacts/autobootstrap-'+name and type(item['bytes']) is int
                and 0<item['bytes']<=(PUBLIC_BYTES if name=='runtime' else 16777216) and re.fullmatch('[0-9a-f]{64}',item['sha256']),'untrusted artifact pin')
    require(config['artifacts']['runtime']['sha256']==PUBLIC_SHA and config['artifacts']['runtime']['bytes']==PUBLIC_BYTES,'private/changed public runtime forbidden')


def user_data(config):
    validate_config(config)
    program=RUNTIME+'\nentry('+repr(config)+')\n';compressed=base64.b64encode(zlib.compress(program.encode(),9)).decode()
    code="import base64,zlib;exec(compile(zlib.decompress(base64.b64decode("+repr(compressed)+")),'<pinned-canary-bootstrap>','exec'))"
    import shlex
    script=('#!/bin/sh\nset -eu\nPY="";for p in /nix/store/*-python3-*/bin/python3;do if [ -x "$p" ];then PY="$p";break;fi;done\n[ -n "$PY" ]\nexec systemd-run --quiet --wait --collect --unit=spot-autobootstrap-'+config['scope']+
            ' -p Type=exec -p MemoryMax=128M -p MemorySwapMax=0 -p CPUQuota=10% -p OOMPolicy=kill -p OOMScoreAdjust=1000 -p Nice=19 -p NoNewPrivileges=yes -p ProtectControlGroups=no -p StandardOutput=journal+console -p StandardError=journal+console --setenv=PATH=/run/current-system/sw/bin --setenv=HOME=/var/empty "$PY" -B -I -c '+shlex.quote(code)+'\n')
    require(len(script.encode())<=16384,'EC2 decoded UserData exceeds16KiB')
    return base64.b64encode(script.encode()).decode()


def guest_policy(state):
    policy=b.scoped_policy(state)
    policy['Statement'].append({'Effect':'Allow','Action':'ec2:DescribeVolumes','Resource':'*',
                                'Condition':{'StringEquals':{'aws:RequestedRegion':b.REGION}}})
    return policy


def source_snapshot(source,revision,directory):
    """One-off public source packaging; the cloud guest never needs this path."""
    source=Path(source).resolve(strict=True);directory=Path(directory)
    require(subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==revision,'checkout is not pinned HEAD')
    require(not subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=normal'],text=True),'source checkout not clean')
    clone=directory/'tree';env={**os.environ,'GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_SYSTEM':'/dev/null','GIT_TERMINAL_PROMPT':'0'}
    subprocess.run(['git','-c','core.hooksPath=/dev/null','clone','--quiet','--template=','--no-hardlinks','--depth','1','--no-local','file://'+str(source),str(clone)],check=True,env=env)
    require(subprocess.check_output(['git','-C',str(clone),'rev-parse','HEAD'],text=True).strip()==revision,'snapshot changed during clone')
    subprocess.run(['git','-C',str(clone),'remote','set-url','origin','https://github.com/sudosubin/nixos-config'],check=True,env=env)
    # Reflogs are not source/commit authority and contain the creator's file://
    # checkout path. Do not export those or any caller Git hooks/configuration.
    if (clone/'.git/logs').exists():shutil.rmtree(clone/'.git/logs')
    names=list(filter(None,subprocess.check_output(['git','-C',str(clone),'ls-files','-z']).decode().split('\0')))
    expected={name:sha(clone/name) for name in names};authority=directory/'authority.json';authority.write_text(json.dumps(expected,sort_keys=True));authority.chmod(0o600)
    archive=directory/'source.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:
        for child in sorted(clone.iterdir()):tar.add(child,arcname=child.name)
    return {'source':archive,'authority':authority}


def upload_new(api,state,name,path):
    """One conditional PUT, metadata AND exact full body readback before capacity."""
    path=Path(path);key='artifacts/autobootstrap-'+name;digest=sha(path)
    api('s3api','put-object','--bucket',state['bucket'],'--key',key,'--body',str(path),'--if-none-match','*','--expected-bucket-owner',b.ACCOUNT,
        '--server-side-encryption','AES256','--checksum-algorithm','SHA256','--metadata','sha256='+digest)
    with tempfile.TemporaryDirectory(prefix='bootstrap-body-') as d:
        back=Path(d)/'readback';metadata=api('s3api','get-object','--bucket',state['bucket'],'--key',key,'--expected-bucket-owner',b.ACCOUNT,str(back))
        require(back.stat().st_size==path.stat().st_size and sha(back)==digest==metadata['Metadata']['sha256'],'uploaded bootstrap body differs')
    return {'key':key,'sha256':digest,'bytes':path.stat().st_size}


def create_zero(api,state):
    api.account();b.create(api,state,activate=False)
    return {'state':state,'capacity_requested':False,'paid_activation_authorized':False,'goal_complete':False}


def read_state(api,state):
    with tempfile.TemporaryDirectory(prefix='bootstrap-control-') as d:
        path=Path(d)/'state';meta=api('s3api','get-object','--bucket',state['bucket'],'--key','control/infra-ledger-current.json','--expected-bucket-owner',b.ACCOUNT,str(path))
        require(path.stat().st_size<=65536 and sha(path)==meta['Metadata']['sha256'],'cloud state body differs');stored=json.loads(path.read_text())
        require(all(stored.get(k)==state[k] for k in ['scope','name','bucket','source_revision']) and stored.get('stage')=='native-zero-ready-no-capacity-requested','foreign/nonzero cloud bootstrap state')
        return stored


def prepare(api,state,source,public_runtime=None):
    api.account()
    with tempfile.TemporaryDirectory(prefix='canary-public-source-') as directory:
        files=source_snapshot(source,state['source_revision'],directory)
        # The original cloud host may have uploaded its retained PUBLIC archive
        # after create-zero. No copy to a laptop or private credential export is
        # needed: configure-zero can run in CloudShell using standard roles.
        if public_runtime is None:
            public_runtime=Path(directory)/'public-runtime'
            meta=api('s3api','get-object','--bucket',state['bucket'],'--key','artifacts/public-runtime.tar.gz','--expected-bucket-owner',b.ACCOUNT,str(public_runtime))
            require(meta['Metadata']['sha256']==PUBLIC_SHA,'public archive metadata differs')
        require(sha(public_runtime)==PUBLIC_SHA and Path(public_runtime).stat().st_size==PUBLIC_BYTES,'pinned PUBLIC-only runtime required')
        artifacts={name:upload_new(api,state,name,path) for name,path in {**files,'runtime':Path(public_runtime)}.items()}
        config={'scope':state['scope'],'bucket':state['bucket'],'revision':state['source_revision'],'expires':state['expires'],'artifacts':artifacts};data=user_data(config)
        version=api('ec2','create-launch-template-version','--launch-template-id',state['LT'],'--source-version','1','--client-token',state['name']+'-autobootstrap',
                    '--launch-template-data',json.dumps({'UserData':data}))['LaunchTemplateVersion']
        require(version['VersionNumber']==2 and version['LaunchTemplateId']==state['LT'],'unexpected bootstrap LT version')
        group=api('autoscaling','describe-auto-scaling-groups','--auto-scaling-group-names',state['name'])['AutoScalingGroups'];require(len(group)==1 and not group[0]['Instances'] and group[0]['DesiredCapacity']==0,'scope no longer zero')
        state['asg_arn']=group[0]['AutoScalingGroupARN'];mixed=group[0]['MixedInstancesPolicy'];mixed['LaunchTemplate']['LaunchTemplateSpecification']={'LaunchTemplateId':state['LT'],'Version':'2'}
        api('autoscaling','update-auto-scaling-group','--auto-scaling-group-name',state['name'],'--mixed-instances-policy',json.dumps(mixed))
        api('iam','put-role-policy','--role-name',state['name'],'--policy-name','DisposableAttestationAndArtifacts','--policy-document',json.dumps(guest_policy(state)))
        result={'state':state,'config':config,'UserData_sha256':hashlib.sha256(base64.b64decode(data)).hexdigest(),'numeric_LT':'2','capacity_requested':False,
                'receiver_admission_implemented':False,'paid_activation_authorized':False,'automatic_replacement_bootstrap_verified':False,'goal_complete':False}
        validate_prepared(api,result)
        control=Path(directory)/'control.json';control.write_text(json.dumps(result,sort_keys=True));upload_new(api,state,'prepared-control',control)
        return result


def validate_prepared(api,value,now=None):
    state=value['state'];validate_config(value['config']);require(value['config']['expires']==state['expires'] and value['config']['revision']==state['source_revision'],'stale bootstrap config')
    remaining=datetime.fromisoformat(state['expires']).timestamp()-(time.time() if now is None else now)
    require(300<remaining<=6600,'native bootstrap window exhausted or unbounded')
    rows=api('ec2','describe-launch-template-versions','--launch-template-id',state['LT'],'--versions','2')['LaunchTemplateVersions'];require(len(rows)==1,'bootstrap LT ambiguous')
    data=rows[0]['LaunchTemplateData'];require(data.get('UserData')==user_data(value['config']) and data.get('ImageId')==b.AMI
            and data.get('InstanceType')=='r7g.large' and data.get('IamInstanceProfile')=={'Name':state['name']} and not data.get('KeyName')
            and data.get('SecurityGroupIds')==['sg-065aa5f3bd3cac988'] and data.get('MetadataOptions',{}).get('HttpTokens')=='required'
            and data.get('InstanceInitiatedShutdownBehavior')=='terminate'
            and data.get('BlockDeviceMappings')==[{'DeviceName':'/dev/xvda','Ebs':{'VolumeSize':32,'VolumeType':'gp3','Encrypted':True,'DeleteOnTermination':True}}],'bootstrap launch data changed')
    groups=api('autoscaling','describe-auto-scaling-groups','--auto-scaling-group-names',state['name'])['AutoScalingGroups'];require(len(groups)==1,'bootstrap group ambiguous');g=groups[0]
    require(g.get('AutoScalingGroupName')==state['name'] and g['AutoScalingGroupARN']==state['asg_arn'] and all(type(g.get(k)) is int for k in ['DesiredCapacity','MinSize','MaxSize'])
            and g['DesiredCapacity']==g['MinSize']==0 and g['MaxSize']==1 and not g['Instances']
            and g['NewInstancesProtectedFromScaleIn'] is False and g['CapacityRebalance'] is False and not g['SuspendedProcesses'],'zero/unprotected scope changed')
    spec=g['MixedInstancesPolicy']['LaunchTemplate']['LaunchTemplateSpecification'];dist=g['MixedInstancesPolicy']['InstancesDistribution']
    require(spec['LaunchTemplateId']==state['LT'] and spec['Version']=='2' and g['MixedInstancesPolicy']['LaunchTemplate']['Overrides']==[{'InstanceType':'r7g.large'}]
            and all(type(dist.get(k)) is int for k in ['OnDemandBaseCapacity','OnDemandPercentageAboveBaseCapacity','SpotInstancePools'])
            and dist['OnDemandBaseCapacity']==dist['OnDemandPercentageAboveBaseCapacity']==0 and dist['SpotAllocationStrategy']=='lowest-price' and dist['SpotInstancePools']==1
            and float(dist['SpotMaxPrice'])==.020,'numeric LT/100percentSpot changed')
    actions=api('autoscaling','describe-scheduled-actions','--auto-scaling-group-name',state['name'])['ScheduledUpdateGroupActions'];require(len(actions)==1 and actions[0]['AutoScalingGroupName']==state['name'] and actions[0]['ScheduledActionName']==state['name']+'-off'
            and not actions[0].get('Recurrence') and datetime.fromisoformat(actions[0]['StartTime']).timestamp()==datetime.fromisoformat(state['expires']).timestamp()
            and all(type(actions[0].get(k)) is int and actions[0][k]==0 for k in ['MinSize','MaxSize','DesiredCapacity']),'native zero expiry changed')
    require(api('iam','get-role-policy','--role-name',state['name'],'--policy-name','DisposableAttestationAndArtifacts')['PolicyDocument']==guest_policy(state),'bootstrap guest authority changed')
    require(api('iam','list-role-policies','--role-name',state['name'])['PolicyNames']==['DisposableAttestationAndArtifacts'],'foreign inline guest policy')
    require(api('iam','list-attached-role-policies','--role-name',state['name'])['AttachedPolicies']==[{'PolicyName':'AmazonSSMManagedInstanceCore','PolicyArn':b.CORE}],'foreign managed guest authority')
    profile=api('iam','get-instance-profile','--instance-profile-name',state['name'])['InstanceProfile']
    require(profile['Arn']==state['profile_arn'] and len(profile['Roles'])==1 and profile['Roles'][0]['Arn']==state['role_arn'],'guest profile role changed')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['plan','create-zero','configure-zero']);parser.add_argument('--scope',required=True);parser.add_argument('--source-revision',required=True)
    parser.add_argument('--source',type=Path);parser.add_argument('--public-runtime',type=Path);parser.add_argument('--profile');args=parser.parse_args();state=b.plan(args.scope,args.source_revision)
    state['creator_script_sha256']=sha(b.__file__)
    if args.action=='plan':print(json.dumps(state,indent=2));return
    # Single attempts for unknown provisioning/PUT responses; never replay.
    os.environ['AWS_MAX_ATTEMPTS']='1';api=b.API(args.profile)
    if args.action=='create-zero':result=create_zero(api,state)
    else:
        require(args.source is not None,'explicit pinned public source required')
        result=prepare(api,read_state(api,state),args.source,args.public_runtime)
    # No implicit local AWS profile. CloudShell/EC2 use standard role providers.
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
