#!/usr/bin/env python3
"""Original-host bounded autonomous proof discovery; no production work authority.

Run before the only empty-ASG capacity request. Exact kernel/process/source/home
admission is read back by the creator. A complete receipt means opaque bodies
were retained, NOT production readiness, AMI approval, or safe termination.
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
import subprocess
import time
import uuid


def sibling(name,filename):
    path=Path(__file__).with_name(filename);s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);m.__file__=str(path);exec(compile(path.read_bytes(),str(path),'exec'),m.__dict__);return m


r=sibling('receiver','spot-canary-receive.py')
p=sibling('pipeline','spot-canary-pipeline.py')
require=r.require


def runs(scope,listing):
    r.key_for(scope)
    require(not listing.get('IsTruncated'),'partial discovery is not a complete roster')
    prefix='results/final/'+scope+'/'
    result=set()
    for row in listing.get('Contents',[]):
        key=row.get('Key','');require(isinstance(key,str) and key.startswith(prefix),'foreign discovery object')
        tail=key[len(prefix):];parts=tail.split('/')
        require(len(parts)==2 and re.fullmatch('[0-9a-f]{32}',parts[0]) and parts[1] in {'pipeline.json','proof.tar.gz','missing-from-base.nix-export.gz','package-result.json','full-tests.json'},'malformed final artifact key')
        if parts[1]=='pipeline.json':result.add(parts[0])
    require(len(result)<=3,'too many boots; no unbounded artifact acceptance')
    return sorted(result)


def kernel(scope):
    require(os.geteuid()==0,'root metadata receiver required')
    text=Path('/proc/self/cgroup').read_text().strip();wanted='/system.slice/spot-autoreceive-'+scope+'.service'
    require(text=='0::'+wanted,'foreign receiver service cgroup')
    group=Path('/sys/fs/cgroup')/wanted.lstrip('/')
    require((group/'memory.max').read_text().strip()=='268435456' and (group/'memory.swap.max').read_text().strip()=='0','receiver memory/swap unknown')
    (group/'memory.oom.group').write_text('1')
    cpu=(group/'cpu.max').read_text().split();require(len(cpu)==2 and all(x.isdecimal() for x in cpu) and 0<int(cpu[0])<=int(cpu[1])//4,'receiver CPU exceeds25pct')
    require('NoNewPrivs:\t1' in Path('/proc/self/status').read_text() and Path('/proc/self/oom_score_adj').read_text().strip()=='1000','receiver NNP/priority unknown')
    return group


def put(bucket,key,path):
    digest=r.sha(path);r.aws('s3api','put-object','--bucket',bucket,'--key',key,'--body',str(path),'--if-none-match','*','--checksum-algorithm','SHA256','--server-side-encryption','AES256','--metadata','sha256='+digest)
    target=path.with_name(path.name+'-s3-readback');r.get(bucket,key,target,{'sha256':digest,'bytes':path.stat().st_size})
    return digest


def save(path,value):
    with path.open('x') as f:json.dump(value,f,indent=2);f.flush();os.fsync(f.fileno())


def initialize(scope,expires,authority,home_uuid,ready_file=None):
    r.key_for(scope);r.identity();deadline=datetime.fromisoformat(expires).timestamp();require(0<deadline-time.time()<=8400,'receiver lifetime expired/unbounded')
    require(subprocess.check_output(['findmnt','-n','-o','UUID','--mountpoint','/home'],text=True).strip()==home_uuid,'retained home differs')
    authority=Path(authority);st=authority.lstat();require(st.st_uid==0 and not st.st_mode&0o022 and not authority.is_symlink() and st.st_size<=1048576,'untrusted source authority')
    expected=json.loads(authority.read_text())
    for name in ['spot-canary-auto-receive.py','spot-canary-receive.py','spot-canary-pipeline.py']:
        require(r.sha(Path(__file__).with_name(name))==expected.get('scripts/'+name),'receiver executed source differs')
    group=kernel(scope);folder=Path('/home/persist/root')/('autoreceived-'+scope+'-'+uuid.uuid4().hex);folder.mkdir(mode=0o700)
    ready={'scope':scope,'expires':expires,'pid':os.getpid(),'pid_start':Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19],'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
           'cgroup':str(group), 'source':str(Path(__file__).resolve()),'source_sha256':r.sha(__file__),'authority':str(authority),'authority_sha256':r.sha(authority),'home_uuid':home_uuid,'folder':str(folder),
           'memory_max':(group/'memory.max').read_text().strip(),'memory_swap_max':(group/'memory.swap.max').read_text().strip(),'oom_group':(group/'memory.oom.group').read_text().strip(),'cpu_max':(group/'cpu.max').read_text().strip(),
           'admission_is_test_success':False,'work_tracking_verified':False,'armed':False,'goal_complete':False}
    save(folder/'ready.json',ready);bucket='nixos-spot-proof-'+r.ACCOUNT+'-'+scope
    for prefix in ['results/final/'+scope+'/','results/bootstrap/'+scope+'/']:
        require(not r.aws('s3api','list-objects-v2','--bucket',bucket,'--prefix',prefix,'--max-keys','100').get('IsTruncated'),'initial discovery incomplete')
    require(not r.aws('ec2','describe-instances','--filters','Name=tag:ScopeId,Values='+scope)['Reservations'],'receiver admission requires zero test instances')
    put(bucket,'artifacts/autoreceiver-ready.json',folder/'ready.json')
    if ready_file is not None:
        require(Path(ready_file)==Path('/home/persist/root')/('autoreceive-'+scope)/'admitted.json','foreign admission path');save(Path(ready_file),ready)
    return folder,deadline,expected,ready


def validate_binding(scope,run,commit,binding,authority_sha256):
    identity=binding['identity']
    require(identity.get('scope')==scope and re.fullmatch('i-[0-9a-f]{17}',identity.get('instanceId','')) and identity['instanceId']!=r.ORIGINAL
            and re.fullmatch('[0-9a-f-]{36}',identity.get('boot',''))
            and hashlib.sha256((identity['instanceId']+':'+identity['boot']).encode()).hexdigest()[:32]==run and commit.get('instance')==identity['instanceId'],
            'bootstrap instance/boot/run binding differs')
    require(re.fullmatch('vol-[0-9a-f]{17}',identity.get('root_volume','')) and identity['root_volume'] not in {'vol-065729ef75553a7ec','vol-09fea2ff4615b1088','vol-0b529abe51df1eca1'},'retained/unknown root in receipt')
    require(binding.get('authority_sha256')==authority_sha256,'bootstrap source binding differs')
    return identity


def observe(scope,deadline,folder,expected):
    bucket='nixos-spot-proof-'+r.ACCOUNT+'-'+scope;completed={};errors=[];seen_failure=set();console_seen={}
    while time.time()<deadline:
        # Pre-custody bootstrap failures cannot safely PUT a status. Preserve
        # the native console independently before the disposable root expires.
        reservations=r.aws('ec2','describe-instances','--filters','Name=tag:ScopeId,Values='+scope)['Reservations']
        instances=[i for row in reservations for i in row.get('Instances',[])];require(len(instances)<=3,'unbounded test instance roster')
        for instance in instances:
            iid=instance['InstanceId'];require(iid!=r.ORIGINAL and {t['Key']:t['Value'] for t in instance.get('Tags',[])}.get('ScopeId')==scope,'foreign console target')
            try:
                response=r.aws('ec2','get-console-output','--instance-id',iid,'--latest');encoded=response.get('Output','');require(isinstance(encoded,str) and len(encoded)<=2097152,'oversized console data')
                if encoded:
                    data=base64.b64decode(encoded,validate=True);digest=hashlib.sha256(data).hexdigest()
                    if console_seen.get(iid)!=digest:
                        path=folder/('console-'+iid+'-'+uuid.uuid4().hex+'.log')
                        with path.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
                        console_seen[iid]=digest
            except Exception as error:
                marker='console-error-'+iid
                if marker not in seen_failure:save(folder/(marker+'.json'),{'error':type(error).__name__+':'+str(error),'not_console_success':True});seen_failure.add(marker)
        listing=r.aws('s3api','list-objects-v2','--bucket',bucket,'--prefix','results/final/'+scope+'/','--max-keys','100')
        for run in runs(scope,listing):
            if run in completed:continue
            directory=folder/('run-'+run+'-'+uuid.uuid4().hex)
            try:
                receipt=r.receive(scope,min(deadline,time.time()+2),directory,p,expected,run)
                started=directory/'bootstrap-started.json';r.get(bucket,'results/bootstrap/'+scope+'/'+run+'/started.json',started);binding=json.loads(started.read_text());commit=json.loads((Path(receipt['received'])/'pipeline.json').read_text())
                identity=validate_binding(scope,run,commit,binding,json.loads((folder/'ready.json').read_text())['authority_sha256'])
                receipt.update(instance=identity['instanceId'],boot=identity['boot'],root_volume=identity['root_volume'],bootstrap_started_sha256=r.sha(started))
                save(folder/('retained-'+run+'.json'),receipt);put(bucket,'artifacts/retained-'+run+'.json',folder/('retained-'+run+'.json'));completed[run]=receipt
            except Exception as error:
                # Preserve every bad attempt, never classify missing/denied as
                # success or replay effects. Future data uses a fresh directory.
                errors.append({'run':run,'error':type(error).__name__+':'+str(error)});save(folder/('failure-'+uuid.uuid4().hex+'.json'),errors[-1])
        failures=r.aws('s3api','list-objects-v2','--bucket',bucket,'--prefix','results/bootstrap/'+scope+'/','--max-keys','100')
        require(not failures.get('IsTruncated'),'partial bootstrap evidence roster')
        for row in failures.get('Contents',[]):
            key=row['Key'];require(re.fullmatch('results/bootstrap/'+scope+'/[0-9a-f]{32}/(started|staged|failure)\.json',key),'malformed bootstrap status')
            if key in seen_failure:continue
            r.get(bucket,key,folder/('bootstrap-'+uuid.uuid4().hex+'.json'));seen_failure.add(key)
        # This is an expiring test receiver, not an always-on controller. Two
        # independently delivered boot results suffice for a replacement trial.
        if len(completed)>=2:break
        time.sleep(10)
    result={'scope':scope,'retained_runs':completed,'bootstrap_status_objects':len(seen_failure),'failed_attempts':errors,'work_tracking_verified':False,'armed':False,'goal_complete':False}
    save(folder/'finished.json',result);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--scope',required=True);parser.add_argument('--expires',required=True);parser.add_argument('--expected-source',type=Path,required=True);parser.add_argument('--home-uuid',default='e47b82eb-22d2-4b12-9e58-92d5aabfbc65');parser.add_argument('--ready-file',type=Path);args=parser.parse_args()
    folder,deadline,expected,ready=initialize(args.scope,args.expires,args.expected_source,args.home_uuid,args.ready_file);print(json.dumps(ready),flush=True);print(json.dumps(observe(args.scope,deadline,folder,expected)),flush=True)


if __name__=='__main__':main()
