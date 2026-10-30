#!/usr/bin/env python3
"""Resident READ-ONLY production observation; not the termination guard.

Never runs work.Protocol or the guard. Never changes protection/capacity,
services/home/EIP/IAM, initializes custody or publishes arming approvals.
Parent256MiB/CPU25/private net; each metadata/AWS read128MiB/CPU10.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import uuid
sys.path.insert(0,str(Path(__file__).parent))
import spot_protection as core

ALLOWED={('sts','get-caller-identity'),('autoscaling','describe-auto-scaling-groups'),('ec2','describe-volumes'),('ssm','describe-sessions')}


def version(folder):
    return hashlib.sha256(''.join(hashlib.sha256((Path(folder)/name).read_bytes()).hexdigest() for name in ['spot_protection.py','spot_observer.py']).encode()).hexdigest()[:12]


def settings(config):
    core.require(set(config)=={'schema','account','region','asg','asg_arn','deployment_id','state_directory'} and type(config['schema']) is int and config['schema']==1,'unknown observer configuration')
    core.require(re.fullmatch('[0-9]{12}',config['account']) and re.fullmatch('[a-z]{2}-[a-z]+-[0-9]',config['region']) and re.fullmatch('[a-zA-Z0-9_-]{1,255}',config['asg']) and re.fullmatch('[0-9a-f]{12}',config['deployment_id']),'invalid observer identity')
    prefix='arn:aws:autoscaling:'+config['region']+':'+config['account']+':autoScalingGroup:'
    core.require(config['asg_arn'].startswith(prefix) and re.fullmatch('[0-9a-f-]{36}',config['asg_arn'][len(prefix):].split(':',1)[0]) and config['asg_arn'].endswith(':autoScalingGroupName/'+config['asg']),'exact observer ASG ARN required')
    core.require(config['state_directory']=='/var/lib/spot-protection-observer/'+config['deployment_id'],'foreign diagnostic output path');return config


def kernel(memory,cpu,*,private=False):
    text=Path('/proc/self/cgroup').read_text().strip();core.require(text.startswith('0::/'),'unknown cgroup');group=Path('/sys/fs/cgroup')/text.split('::',1)[1].lstrip('/')
    core.require((group/'memory.max').read_text().strip()==str(memory) and (group/'memory.swap.max').read_text().strip()=='0' and (group/'memory.oom.group').read_text().strip()=='1','observer kernel memory/swap/OOM fence missing')
    values=(group/'cpu.max').read_text().split();core.require(len(values)==2 and all(x.isdecimal() for x in values) and 0<int(values[0])*100<=int(values[1])*cpu,'observer CPU fence missing')
    core.require('NoNewPrivs:\t1' in Path('/proc/self/status').read_text() and Path('/proc/self/oom_score_adj').read_text().strip()=='1000','observer privilege/OOM priority fence missing')
    core.require(os.getpriority(os.PRIO_PROCESS,0)==19,'observer nice priority missing')
    if private:core.require(Path('/proc/self/ns/net').stat().st_ino!=Path('/proc/1/ns/net').stat().st_ino,'observer parent must have private network')
    return {'cgroup':str(group),'memory_max':memory,'swap_max':0,'oom_group':1,'cpu_max':(group/'cpu.max').read_text().strip(),'no_new_privileges':True,'oom_score_adjust':1000}


# This standalone gate is exec-replaced by AWS: no Python parent inside128MiB.
GATE=r'''from pathlib import Path
import os,sys,json,urllib.request
p=Path('/sys/fs/cgroup')/Path('/proc/self/cgroup').read_text().strip().split('::')[-1].lstrip('/');assert (p/'memory.max').read_text().strip()=='134217728' and (p/'memory.swap.max').read_text().strip()=='0' and (p/'memory.oom.group').read_text().strip()=='1';cpu=(p/'cpu.max').read_text().split();assert cpu[0].isdigit() and int(cpu[0])*10<=int(cpu[1]);assert 'NoNewPrivs:\t1' in Path('/proc/self/status').read_text() and Path('/proc/self/oom_score_adj').read_text().strip()=='1000';assert os.getpriority(os.PRIO_PROCESS,0)==19
for key in list(os.environ):
 if key.startswith(('AWS_','AMAZON_')):os.environ.pop(key)
os.environ.update(AWS_CONFIG_FILE='/dev/null',AWS_SHARED_CREDENTIALS_FILE='/dev/null',AWS_EC2_METADATA_DISABLED='false',AWS_MAX_ATTEMPTS='1',AWS_PAGER='',HOME='/var/empty',PATH='/run/current-system/sw/bin')
if sys.argv[1]=='identity':
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://169.254.169.254/latest/'
 with opener.open(urllib.request.Request(base+'api/token',method='PUT',headers={'X-aws-ec2-metadata-token-ttl-seconds':'60'}),timeout=3) as f:token=f.read(4096).decode()
 with opener.open(urllib.request.Request(base+'dynamic/instance-identity/document',headers={'X-aws-ec2-metadata-token':token}),timeout=3) as f:value=json.loads(f.read(16384))
 print(json.dumps(value))
else:os.execvp('aws',['aws',*sys.argv[1:]])
'''


class Reads:
    def __init__(self,config):self.config=config
    def run(self,args):
        command=['systemd-run','--quiet','--pipe','--wait','--collect','--unit=spot-observer-read-'+uuid.uuid4().hex,'-p','Type=exec','-p','MemoryMax=128M','-p','MemorySwapMax=0','-p','CPUQuota=10%','-p','OOMPolicy=kill','-p','OOMScoreAdjust=1000','-p','Nice=19','-p','NoNewPrivileges=yes','-p','ProtectControlGroups=yes','-p','RuntimeMaxSec=45',sys.executable,'-B','-I','-c',GATE,*args]
        result=subprocess.run(command,capture_output=True,text=True,timeout=55);core.require(result.returncode==0,'bounded observer read failed; no action authorized');core.require(len(result.stdout)<=1048576,'observer metadata response too large');return json.loads(result.stdout)
    def identity(self):return self.run(['identity'])
    def __call__(self,service,operation,*args):
        core.require((service,operation) in ALLOWED,'observer mutation/unknown API forbidden before execution');return self.run([service,operation,*args,'--region',self.config['region'],'--output','json','--no-cli-pager'])


def observe(config,api,runtime):
    doc=api.identity();iid=doc.get('instanceId');core.require(doc.get('accountId')==config['account'] and doc.get('region')==config['region'] and re.fullmatch('i-[0-9a-f]{17}',iid or ''),'observer instance identity unknown')
    caller=api('sts','get-caller-identity');core.require(caller.get('Account')==config['account'] and caller.get('Arn','').endswith('/'+iid),'observer role/instance custody differs')
    before=api('autoscaling','describe-auto-scaling-groups','--auto-scaling-group-names',config['asg'])['AutoScalingGroups'];core.require(len(before)==1 and before[0].get('AutoScalingGroupARN')==config['asg_arn'] and any(i.get('InstanceId')==iid for i in before[0].get('Instances',[])),'not expected live ASG member')
    home=core.fields(runtime,'/etc/spot-schedule-guard.json').get('home_volume');volumes=None
    if home and re.fullmatch('vol-[0-9a-f]{17}',home):volumes=api('ec2','describe-volumes','--volume-ids',home)['Volumes']
    sessions=api('ssm','describe-sessions','--state','Active','--filters','key=Target,value='+iid)['Sessions'];after=api('autoscaling','describe-auto-scaling-groups','--auto-scaling-group-names',config['asg'])['AutoScalingGroups'];core.require(len(after)==1 and after[0]['AutoScalingGroupARN']==config['asg_arn'],'ASG identity changed')
    diagnosis=core.diagnose(before[0],runtime,iid,after=after[0]);return {'schema':1,'observed_at':time.time(),'boot_id':runtime['boot_id'],'instance':iid,'deployment_id':config['deployment_id'],'classification':diagnosis['classification'],'diagnosis':diagnosis,'runtime':runtime,'ASG':after[0],'home_volume_observation':volumes,'active_SSM_session_count_NOT_idle_proof':len(sessions),'observation_only':True,'termination_capable':False,'work_tracking_verified':False,'armed':False,'goal_complete':False}


def publish(config,value):
    folder=Path(config['state_directory']);st=folder.lstat();core.require(stat.S_ISDIR(st.st_mode) and st.st_uid==0 and stat.S_IMODE(st.st_mode)==0o700,'untrusted observer diagnostic directory')
    data=json.dumps(value,sort_keys=True,separators=(',',':')).encode();core.require(len(data)<=1048576,'observer status too large');temporary=folder/('.pending-'+uuid.uuid4().hex);fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    os.replace(temporary,folder/'status.json');fd=os.open(folder,os.O_DIRECTORY|os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',type=Path,required=True);args=parser.parse_args();core.require(os.geteuid()==0,'observer requires root metadata access');config=settings(json.loads(args.config.read_text()));core.require(version(Path(__file__).parent)==config['deployment_id'],'observer source version mismatch');budget=kernel(268435456,25,private=True)
    try:value=observe(config,Reads(config),core.collect())
    except Exception as error:value={'schema':1,'observed_at':time.time(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'classification':'observation_unknown','error_type':type(error).__name__,'error':str(error)[:256],'observation_only':True,'termination_capable':False,'work_tracking_verified':False,'armed':False,'goal_complete':False}
    value['resource_budget']=budget;group=Path(budget['cgroup']);value['memory_peak']=(group/'memory.peak').read_text().strip();value['memory_events']=(group/'memory.events').read_text();publish(config,value);print(json.dumps({'classification':value['classification'],'observation_only':True,'termination_capable':False,'status':config['state_directory']+'/status.json'}))


if __name__=='__main__':main()
