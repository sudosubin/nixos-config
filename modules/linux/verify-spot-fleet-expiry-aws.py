#!/usr/bin/env python3
"""Bounded readonly ORIGINAL-host observer, not work/idle/validation authority.

Records a single empty-workload Fleet/ASG trial on retained home. Never mutates
AWS, signals CFN, changes protection or treats missing EC2 history as dead.
Native-expiry causality is deliberately left for independent raw-history audit.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.request

ACCOUNT='537112465379';REGION='ap-northeast-2';ORIGINAL='i-0c39eff85c4286b38'
ALLOWED={('ec2',a) for a in ['describe-spot-fleet-requests','describe-spot-fleet-instances','describe-spot-fleet-request-history','describe-instances','describe-volumes']}|{('autoscaling','describe-auto-scaling-groups')}


def require(value,message):
    if not value:raise RuntimeError(message)


def call(service,action,*args):
    require((service,action) in ALLOWED,'readonly observer API roster violated')
    env={k:v for k,v in os.environ.items() if not k.startswith(('AWS_','AMAZON_'))}
    env.update(AWS_CONFIG_FILE='/dev/null',AWS_SHARED_CREDENTIALS_FILE='/dev/null',AWS_EC2_METADATA_DISABLED='false',AWS_MAX_ATTEMPTS='1',HOME='/var/empty')
    p=subprocess.run(['/run/current-system/sw/bin/aws',service,action,*args,'--region',REGION,'--output','json'],capture_output=True,text=True,timeout=30,env=env)
    if p.returncode:
        code=re.search(r'An error occurred \(([A-Za-z0-9_.-]+)\)',p.stderr)
        raise RuntimeError(service+':'+action+':'+(code[1] if code else 'unknown_transport'))
    return json.loads(p.stdout) if p.stdout.strip() else {}


def identity():
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));url='http://169.254.169.254/latest/'
    with opener.open(urllib.request.Request(url+'api/token',method='PUT',headers={'X-aws-ec2-metadata-token-ttl-seconds':'60'}),timeout=3) as f:token=f.read().decode()
    with opener.open(urllib.request.Request(url+'dynamic/instance-identity/document',headers={'X-aws-ec2-metadata-token':token}),timeout=3) as f:value=json.load(f)
    require(value['accountId']==ACCOUNT and value['instanceId']==ORIGINAL and value['region']==REGION,'not the retained original observer')
    require(subprocess.check_output(['findmnt','-n','-o','TARGET,UUID','--mountpoint','/home'],text=True).split()==['/home','e47b82eb-22d2-4b12-9e58-92d5aabfbc65'],'retained home differs')


def budget(scope):
    expected='/system.slice/spot-fleet-expiry-observe-'+scope+'.service';rows=Path('/proc/self/cgroup').read_text().splitlines()
    require(rows==['0::'+expected],'observer not in its exact one-shot resource group')
    group=Path('/sys/fs/cgroup')/expected.lstrip('/');require(str(os.getpid()) in (group/'cgroup.procs').read_text().split(),'observer PID membership unknown')
    require((group/'memory.max').read_text().strip()=='268435456' and (group/'memory.swap.max').read_text().strip()=='0','observer memory/swap budget unknown')
    quota,period=(group/'cpu.max').read_text().split();require(quota!='max' and int(quota)/int(period)<=0.5,'observer CPU budget unknown')
    require(Path('/proc/self/oom_score_adj').read_text().strip()=='1000' and re.search(r'^NoNewPrivs:\s+1$',Path('/proc/self/status').read_text(),re.M),'observer OOM/NNP differs')
    available=int(re.search(r'^MemAvailable:\s+(\d+) kB$',Path('/proc/meminfo').read_text(),re.M)[1])*1024;require(available>=2*1024**3,'insufficient observer headroom; never idle authority')
    (group/'memory.oom.group').write_text('1');require((group/'memory.oom.group').read_text().strip()=='1','owned shared OOM not confirmed')
    return group


def publish(path,value):
    tmp=path.with_suffix('.partial');fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as f:json.dump(value,f,indent=2);f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)


def capture_complete(value):
    known=value['instances']
    return (bool(known) and value['seen_protected_running'] and value['seen_zero_requested_but_protected_running']
            and all(i.get('state')=='terminated' and i.get('root_absent') is True for i in known.values())
            and value.get('last_fleet_state') in {'cancelled','cancelled_terminating'}
            and value.get('after_native_expiry') is True)


def observe(scope,fid,expires,directory,group):
    require(not directory.exists(),'observation destination exists');directory.mkdir(mode=0o700)
    value={'scope':scope,'FleetId':fid,'expires':expires,'instances':{},'seen_protected_running':False,
           'seen_zero_requested_but_protected_running':False,'capture_complete':False,'native_cause_verified':False,
           'scope_note':'API evidence only; not OS/home/work tracking or production expiry authority',
           'work_tracking_verified':False,'armed':False,'goal_complete':False,'errors':[]}
    log=directory/'observations.jsonl';deadline=expires+180
    with log.open('x') as stream:
        log.chmod(0o600)
        while time.time()<deadline:
            try:
                rows=call('ec2','describe-spot-fleet-requests','--spot-fleet-request-ids',fid)['SpotFleetRequestConfigs'];require(len(rows)==1 and rows[0]['SpotFleetRequestId']==fid,'unknown Fleet')
                c=rows[0]['SpotFleetRequestConfig'];require(c['TerminateInstancesWithExpiration'] is True and datetime.fromisoformat(c['ValidUntil']).timestamp()==expires and c.get('OnDemandTargetCapacity',0)==0 and c['IamFleetRole']=='arn:aws:iam::'+ACCOUNT+':role/nixos-fleet-expiry-'+scope+'-fleet','native expiry was changed')
                value['last_fleet_state']=rows[0]['SpotFleetRequestState'];active=call('ec2','describe-spot-fleet-instances','--spot-fleet-request-id',fid)['ActiveInstances'];groups=call('autoscaling','describe-auto-scaling-groups','--auto-scaling-group-names','nixos-fleet-expiry-'+scope)['AutoScalingGroups'];require(len(groups)<=1,'unknown group roster');g=groups[0] if groups else None
                if g:require({x['ProcessName'] for x in g['SuspendedProcesses']}=={'Launch'},'ASG non-fleet replacement containment lost')
                members={i['InstanceId']:i for i in g['Instances']} if g else {};ids=set(value['instances'])|{i['InstanceId'] for i in active}|set(members);require(len(ids)<=8 and ORIGINAL not in ids,'observer instance roster invalid')
                observation={'time':time.time(),'fleet':rows[0],'group':g,'instances':[]}
                for iid in sorted(ids):
                    reservations=call('ec2','describe-instances','--instance-ids',iid)['Reservations'];require(len(reservations)==1 and reservations[0]['OwnerId']==ACCOUNT and len(reservations[0]['Instances'])==1,'EC2 absence is not termination proof');i=reservations[0]['Instances'][0];require(i['InstanceId']==iid and {t['Key']:t['Value'] for t in i.get('Tags',[])}.get('ScopeId')==scope,'foreign instance')
                    record=value['instances'].setdefault(iid,{});record['state']=i['State']['Name'];record.setdefault('first_observed_'+record['state'],time.time());observation['instances'].append(i)
                    if i['State']['Name'] in {'running','pending'}:
                        require(i['InstanceLifecycle']=='spot' and not i.get('PublicIpAddress') and not i.get('IamInstanceProfile') and len(i['BlockDeviceMappings'])==1 and i['BlockDeviceMappings'][0]['Ebs']['DeleteOnTermination'] is True,'not contained empty guest')
                        record['root_volume']=i['BlockDeviceMappings'][0]['Ebs']['VolumeId']
                    member=members.get(iid)
                    if member and member.get('ProtectedFromScaleIn') is True and member['LifecycleState']=='InService' and record['state']=='running':
                        value['seen_protected_running']=True;record['seen_protected_running']=True;record['last_protected_running_observed']=time.time()
                        if g['DesiredCapacity']==0 and g['MaxSize']==0:value['seen_zero_requested_but_protected_running']=True;record['seen_zero_requested_but_protected_running']=True
                    if record['state']=='terminated' and record.get('root_volume'):
                        try:call('ec2','describe-volumes','--volume-ids',record['root_volume'])
                        except RuntimeError as error:
                            if str(error)=='ec2:describe-volumes:InvalidVolume.NotFound':record['root_absent']=True
                            else:raise
                stream.write(json.dumps(observation)+'\n');stream.flush();os.fsync(stream.fileno());value['after_native_expiry']=time.time()>=expires;value['capture_complete']=capture_complete(value);publish(directory/'result.json',value)
                if value['capture_complete']:break
            except Exception as error:
                value['errors'].append({'time':time.time(),'type':type(error).__name__,'message':str(error)});publish(directory/'result.json',value)
            time.sleep(10)
    try:
        history=call('ec2','describe-spot-fleet-request-history','--spot-fleet-request-id',fid,'--start-time',datetime.fromtimestamp(expires-720,timezone.utc).isoformat());publish(directory/'native-history.json',history)
    except Exception as error:value['errors'].append({'type':type(error).__name__,'message':str(error)})
    value['memory_peak']=(group/'memory.peak').read_text();value['memory_events']=(group/'memory.events').read_text();publish(directory/'result.json',value);print(json.dumps(value),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--scope',required=True);p.add_argument('--fleet-id',required=True);p.add_argument('--expires',required=True);p.add_argument('--expected-sha256',required=True);a=p.parse_args()
    require(os.geteuid()==0 and re.fullmatch('[0-9a-f]{12}',a.scope) and re.fullmatch('sfr-[0-9a-f-]{36}',a.fleet_id),'observer scope invalid');require(hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==a.expected_sha256,'executed observer source differs');expiry=datetime.fromisoformat(a.expires).timestamp();require(0<expiry-time.time()<=720,'observer native lifetime invalid');identity();g=budget(a.scope);observe(a.scope,a.fleet_id,expiry,Path('/home/persist/root')/('fleet-expiry-proof-'+a.scope),g)


if __name__=='__main__':main()
