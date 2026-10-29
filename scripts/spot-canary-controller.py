#!/usr/bin/env python3
"""One-shot cloud-only EMPTY build activation with LIVE original receiver admission.

No production desired-capacity/protection/OS/storage changes. A candidate image or
LT is NOT approved by an artifact receipt. Native unprotected ASG expiry remains
fixed; this is never accepted-user-work or protected OS-recovery authority.
"""
import argparse
import base64
from datetime import datetime
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import time

spec=importlib.util.spec_from_file_location('bootstrap',Path(__file__).with_name('spot-canary-bootstrap.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
b=p.b
require=p.require


def original_policy(state):
    arn='arn:aws:s3:::'+state['bucket']
    condition={'DateLessThan':{'aws:CurrentTime':state['permission_expires']},'ArnEquals':{'ec2:SourceInstanceARN':'arn:aws:ec2:'+b.REGION+':'+b.ACCOUNT+':instance/'+b.PRODUCTION}}
    return {'Version':'2012-10-17','Statement':[
        {'Effect':'Allow','Action':['s3:GetObject','s3:PutObject'],'Resource':[arn+'/artifacts/*',arn+'/results/*',arn+'/control/infra-ledger-current.json'],'Condition':condition},
        {'Effect':'Allow','Action':'s3:ListBucket','Resource':arn,'Condition':{**condition,'StringLike':{'s3:prefix':['results/final/'+state['scope']+'/*','results/bootstrap/'+state['scope']+'/*']}}},
        {'Effect':'Allow','Action':'ec2:DescribeInstances','Resource':'*','Condition':{**condition,'StringEquals':{'aws:RequestedRegion':b.REGION}}},
        {'Effect':'Allow','Action':'ec2:GetConsoleOutput','Resource':'arn:aws:ec2:'+b.REGION+':'+b.ACCOUNT+':instance/*','Condition':{**condition,'StringEquals':{'aws:RequestedRegion':b.REGION,'ec2:ResourceTag/ScopeId':state['scope']}}}]}


def read(api,state,key):
    with tempfile.TemporaryDirectory(prefix='cloud-control-') as d:
        path=Path(d)/'value';reply=api('s3api','get-object','--bucket',state['bucket'],'--key',key,'--expected-bucket-owner',b.ACCOUNT,str(path))
        require(path.stat().st_size<=1048576 and p.sha(path)==reply['Metadata']['sha256'],'cloud control body differs');return json.loads(path.read_text())


def transport(scope):
    require(os.geteuid()==0,'original root transport required')
    expected='/system.slice/spot-autopublish-'+scope+'.service';require(Path('/proc/self/cgroup').read_text().strip()=='0::'+expected,'foreign publishing cgroup')
    group=Path('/sys/fs/cgroup')/expected.lstrip('/');require((group/'memory.max').read_text().strip()=='134217728' and (group/'memory.swap.max').read_text().strip()=='0','publishing budget missing')
    require('NoNewPrivs:\t1' in Path('/proc/self/status').read_text() and Path('/proc/self/oom_score_adj').read_text().strip()=='1000','publishing NNP/priority missing')
    cpu=(group/'cpu.max').read_text().split();require(len(cpu)==2 and all(x.isdecimal() for x in cpu) and 0<int(cpu[0])<=int(cpu[1])//10,'publishing CPU exceeds10pct');(group/'memory.oom.group').write_text('1');return group


def publish_original(api,state,source,runtime):
    # Only public code/software goes into this test bucket, not user state or keys.
    s=importlib.util.spec_from_file_location('receiver',Path(__file__).with_name('spot-canary-receive.py'));r=importlib.util.module_from_spec(s);s.loader.exec_module(r);r.identity();api.account();group=transport(state['scope'])
    require(subprocess.check_output(['findmnt','-n','-o','UUID','--mountpoint','/home'],text=True).strip()=='e47b82eb-22d2-4b12-9e58-92d5aabfbc65','original retained home differs')
    require(p.sha(runtime)==p.PUBLIC_SHA and Path(runtime).stat().st_size==p.PUBLIC_BYTES,'public runtime identity differs')
    git=next(x for x in Path('/nix/store').glob('*-git-*/bin/git') if x.is_file());os.environ['PATH']=str(git.parent)+':/run/current-system/sw/bin'
    folder=Path('/home/persist/root')/('autopublished-'+state['scope']);folder.mkdir(mode=0o700)
    files=p.source_snapshot(source,state['source_revision'],folder);files['runtime']=Path(runtime)
    artifacts={name:p.upload_new(api,state,name,path) for name,path in files.items()}
    value={'scope':state['scope'],'revision':state['source_revision'],'source_path':str(Path(source).resolve()),'authority_path':str(files['authority']),'artifacts':artifacts,
           'all_bodies_read_back':True,'memory_peak':(group/'memory.peak').read_text(),'memory_events':(group/'memory.events').read_text(),'goal_complete':False}
    path=folder/'published.json'
    with path.open('x') as f:json.dump(value,f,indent=2);f.flush();os.fsync(f.fileno())
    p.upload_new(api,state,'published-control',path);return value


def configure(api,state):
    api.account();published=read(api,state,'artifacts/autobootstrap-published-control')
    require(published.get('scope')==state['scope'] and published.get('revision')==state['source_revision'] and published.get('all_bodies_read_back') is True,'foreign/unverified publication')
    config={'scope':state['scope'],'bucket':state['bucket'],'revision':state['source_revision'],'expires':state['expires'],'artifacts':published['artifacts']};p.validate_config(config);data=p.user_data(config)
    # Fresh metadata/SHA agreement supplements the ORIGINAL-host complete body
    # readbacks, never requires a laptop copy of the270MiB public software.
    for item in config['artifacts'].values():
        head=api('s3api','head-object','--bucket',state['bucket'],'--key',item['key'],'--checksum-mode','ENABLED');require(head['ContentLength']==item['bytes'] and head['Metadata']['sha256']==item['sha256'],'published artifact changed')
    groups=api('autoscaling','describe-auto-scaling-groups','--auto-scaling-group-names',state['name'])['AutoScalingGroups'];require(len(groups)==1 and not groups[0]['Instances'] and groups[0]['DesiredCapacity']==0,'configuration lost zero custody')
    state['asg_arn']=groups[0]['AutoScalingGroupARN']
    version=api('ec2','create-launch-template-version','--launch-template-id',state['LT'],'--source-version','1','--client-token',state['name']+'-autobootstrap','--launch-template-data',json.dumps({'UserData':data}))['LaunchTemplateVersion'];require(version['VersionNumber']==2 and version['LaunchTemplateId']==state['LT'],'unexpected numeric bootstrap LT')
    mixed=groups[0]['MixedInstancesPolicy'];mixed['LaunchTemplate']['LaunchTemplateSpecification']={'LaunchTemplateId':state['LT'],'Version':'2'}
    api('autoscaling','update-auto-scaling-group','--auto-scaling-group-name',state['name'],'--mixed-instances-policy',json.dumps(mixed));api('iam','put-role-policy','--role-name',state['name'],'--policy-name','DisposableAttestationAndArtifacts','--policy-document',json.dumps(p.guest_policy(state)))
    value={'state':state,'config':config,'publication':published,'capacity_requested':False,'paid_activation_authorized':False,'goal_complete':False};p.validate_prepared(api,value)
    with tempfile.TemporaryDirectory(prefix='prepared-control-') as d:
        path=Path(d)/'control';path.write_text(json.dumps(value));p.upload_new(api,state,'prepared-control',path)
    return value


def command(api,script,comment):
    require(len(script.encode())<63000 and len(comment)<=100,'SSM payload/comment exceeds API limit')
    # A lost SendCommand response is NOT retried. All subsequent calls are reads.
    ident=api('ssm','send-command','--document-name','AWS-RunShellScript','--instance-ids',b.PRODUCTION,'--comment',comment,'--timeout-seconds','180','--parameters',json.dumps({'commands':[script]}))['Command']['CommandId']
    end=time.monotonic()+180
    while time.monotonic()<end:
        try:reply=api('ssm','get-command-invocation','--command-id',ident,'--instance-id',b.PRODUCTION)
        except RuntimeError as error:
            if 'InvocationDoesNotExist' not in str(error):raise
            time.sleep(2);continue
        if reply['Status'] not in {'Pending','Delayed','InProgress'}:
            require(reply['Status']=='Success','original admission command failed: '+ident+' '+reply.get('StandardErrorContent','')[:1000]);return json.loads(reply['StandardOutputContent'].strip())
        time.sleep(2)
    raise RuntimeError('original command uncertain; no replay: '+ident)


def shell(code):
    import uuid
    gate="from pathlib import Path\ncg=Path('/sys/fs/cgroup')/Path('/proc/self/cgroup').read_text().strip().split('::')[-1].lstrip('/');assert (cg/'memory.max').read_text().strip()=='134217728';(cg/'memory.oom.group').write_text('1')\n"
    return ('set -eu\nPY="";for p in /nix/store/*-python3-*/bin/python3;do if [ -x "$p" ];then PY="$p";break;fi;done\nsystemd-run --quiet --pipe --wait --collect --unit=spot-admission-'+uuid.uuid4().hex+
            ' -p Type=exec -p MemoryMax=128M -p MemorySwapMax=0 -p CPUQuota=10% -p NoNewPrivileges=yes -p OOMScoreAdjust=1000 -p OOMPolicy=kill -p Nice=19 -p PrivateNetwork=yes -p ProtectControlGroups=no "$PY" -B -I -c '+shlex.quote(gate+code))


def admission_code(value):
    state=value['state'];pub=value['publication'];scope=state['scope'];require(re.fullmatch('[0-9a-f]{12}',scope),'invalid admission scope')
    source=Path(pub['source_path']);authority=Path(pub['authority_path']);require(source==Path('/home/persist/nixos-rollout-source-'+state['source_revision']) and authority==Path('/home/persist/root')/('autopublished-'+scope)/'authority.json','foreign original source paths')
    return r'''from pathlib import Path
import os,json,hashlib,subprocess
scope=__SCOPE__;source=Path(__SOURCE__);authority=Path(__AUTH__)
ready=json.loads(Path('/home/persist/root/autoreceive-'+scope+'/admitted.json').read_text());expected=json.loads(authority.read_text())
def require(ok,msg):
 if not ok:raise RuntimeError(msg)
require(ready['scope']==scope and ready['expires']==__EXPIRES__,'stale receiver')
require(ready['boot']==Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'old boot receiver')
pid=ready['pid'];require(type(pid) is int and pid>1,'unknown receiver PID');proc=Path('/proc')/str(pid)
require(proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==ready['pid_start'],'receiver PID reused')
argv=proc.joinpath('cmdline').read_bytes().split(bytes([0]));require(str(source/'scripts/spot-canary-auto-receive.py').encode() in argv and scope.encode() in argv and __EXPIRES__.encode() in argv and str(authority).encode() in argv,'receiver process changed after admission')
require(proc.joinpath('ns/pid').stat().st_ino==Path('/proc/1/ns/pid').stat().st_ino,'receiver PID namespace unknown')
unit='spot-autoreceive-'+scope+'.service';require(subprocess.check_output(['systemctl','show',unit,'-p','MainPID','--value'],text=True).strip()==str(pid),'receiver unit owner differs')
require(proc.joinpath('cgroup').read_text().strip()=='0::/system.slice/'+unit,'receiver foreign cgroup')
group=Path('/sys/fs/cgroup/system.slice')/unit
require(group.joinpath('memory.max').read_text().strip()=='268435456' and group.joinpath('memory.swap.max').read_text().strip()=='0' and group.joinpath('memory.oom.group').read_text().strip()=='1','receiver actual memory fence missing')
cpu=group.joinpath('cpu.max').read_text().split();require(len(cpu)==2 and all(x.isdecimal() for x in cpu) and 0<int(cpu[0])<=int(cpu[1])//4,'receiver CPU unknown')
require('NoNewPrivs:\t1' in proc.joinpath('status').read_text() and proc.joinpath('oom_score_adj').read_text().strip()=='1000','receiver NNP/OOM priority unknown')
require(hashlib.sha256(authority.read_bytes()).hexdigest()==__AUTH_SHA__==ready['authority_sha256'],'receiver authority changed')
for name in ['spot-canary-auto-receive.py','spot-canary-receive.py','spot-canary-pipeline.py']:
 require(hashlib.sha256((source/'scripts'/name).read_bytes()).hexdigest()==expected['scripts/'+name],'receiver source changed')
require(ready['source_sha256']==expected['scripts/spot-canary-auto-receive.py'],'receiver executed different source')
require(subprocess.check_output(['findmnt','-n','-o','UUID','--mountpoint','/home'],text=True).strip()=='e47b82eb-22d2-4b12-9e58-92d5aabfbc65','original home changed')
print(json.dumps({'live_original_receiver_admitted':True,'scope':scope,'pid':pid,'boot':ready['boot'],'ready':ready,'goal_complete':False}))
'''.replace('__SCOPE__',repr(scope)).replace('__SOURCE__',repr(str(source))).replace('__AUTH__',repr(str(authority))).replace('__EXPIRES__',repr(state['permission_expires'])).replace('__AUTH_SHA__',repr(value['config']['artifacts']['authority']['sha256']))


def launch_receiver(api,value):
    state=value['state'];pub=value['publication'];root='/home/persist/root/autoreceive-'+state['scope'];source=Path(pub['source_path'])
    code="from pathlib import Path;import subprocess,json\nfolder=Path("+repr(root)+");folder.mkdir(mode=0o700)\nargv="+repr(['systemd-run','--unit=spot-autoreceive-'+state['scope'],'--collect','--property=Type=exec','--property=MemoryMax=256M','--property=MemorySwapMax=0','--property=CPUQuota=25%','--property=OOMScoreAdjust=1000','--property=OOMPolicy=kill','--property=Nice=19','--property=NoNewPrivileges=yes','--property=ProtectControlGroups=no','--property=StandardOutput=append:'+root+'/receiver.log','--property=StandardError=append:'+root+'/receiver.log','--setenv=PATH=/run/current-system/sw/bin','--setenv=HOME=/var/empty'])+"\nimport sys;argv += [sys.executable,'-B','-I',"+repr(str(source/'scripts/spot-canary-auto-receive.py'))+",'--scope',"+repr(state['scope'])+",'--expires',"+repr(state['permission_expires'])+",'--expected-source',"+repr(pub['authority_path'])+",'--ready-file',"+repr(root+'/admitted.json')+"];subprocess.run(argv,check=True,capture_output=True,text=True);print(json.dumps({'launched_not_admitted':True}))"
    command(api,shell(code),'launch-native-autoreceiver-'+state['scope'])
    for _ in range(30):
        try:return command(api,shell(admission_code(value)),'admit-native-autoreceiver-'+state['scope'])
        except RuntimeError as error:
            # Reads may race startup; never re-launch or mutate/retry capacity.
            if 'original admission command failed:' not in str(error):raise
            time.sleep(2)
    raise RuntimeError('receiver not admitted; no capacity')


def verify_original(api,state):
    role='nixos-ec2-ssm-role';require(set(api('iam','list-role-policies','--role-name',role)['PolicyNames'])==set(b.BASELINE)|{state['primary_policy_name']},'unknown original inline policy')
    for name,digest in b.BASELINE.items():require(b.digest(api('iam','get-role-policy','--role-name',role,'--policy-name',name)['PolicyDocument'])==digest,'original baseline IAM changed')
    require(api('iam','get-role-policy','--role-name',role,'--policy-name',state['primary_policy_name'])['PolicyDocument']==original_policy(state),'original temporary receiver policy changed')


def activate(api,value):
    api.account();p.validate_prepared(api,value);state=value['state'];verify_original(api,state);require(datetime.fromisoformat(state['expires']).timestamp()-time.time()>1800,'too little fixed lifetime for a new build')
    admitted=command(api,shell(admission_code(value)),'fresh-preadmission-'+state['scope']);require(admitted.get('live_original_receiver_admitted') is True and admitted.get('scope')==state['scope'],'receiver admission failed')
    # One exact paid mutation, no retries on ambiguous response. The fixed
    # native ASG off has already been reread and is never extended.
    api('autoscaling','set-desired-capacity','--auto-scaling-group-name',state['name'],'--desired-capacity','1')
    return {'state':state,'receiver_admission':admitted,'capacity_requested':True,'bootstrap_build_OS_or_goal_success':False,'goal_complete':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['install-publisher-policy','publish','configure','launch-receiver','activate']);parser.add_argument('--scope',required=True);parser.add_argument('--source-revision',required=True);parser.add_argument('--source',type=Path);parser.add_argument('--runtime',type=Path,default=Path('/home/persist/root/disposable-public-runtime-20261028.tar.gz'));parser.add_argument('--profile');args=parser.parse_args();os.environ['AWS_MAX_ATTEMPTS']='1';api=b.API(args.profile);api.account();state=p.read_state(api,b.plan(args.scope,args.source_revision))
    if args.action=='install-publisher-policy':
        require(api('iam','get-role-policy','--role-name','nixos-ec2-ssm-role','--policy-name',state['primary_policy_name'])['PolicyDocument']==b.primary_policy(state),'foreign original temporary policy')
        api('iam','put-role-policy','--role-name','nixos-ec2-ssm-role','--policy-name',state['primary_policy_name'],'--policy-document',json.dumps(original_policy(state)));result={'installed_scoped_original_policy':True,'capacity_requested':False}
    elif args.action=='publish':
        require(args.source is not None and args.profile is None,'original cloud role and source required; no operator profile')
        result=publish_original(api,state,args.source,args.runtime)
    elif args.action=='configure':result=configure(api,state)
    else:
        value=read(api,state,'artifacts/autobootstrap-prepared-control');result=launch_receiver(api,value) if args.action=='launch-receiver' else activate(api,value)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
