#!/usr/bin/env python3
"""One-shot validation resource cage; never production work/idle authority.

Only a fresh root-owned test slice is configured. No limits, OOM preferences,
network settings or lifecycle operations are applied to the production agent,
apps, Nix daemon, root/home devices or ASG. A launch receipt is NOT test success.
"""
import hashlib
from datetime import datetime,timezone
import urllib.request
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import uuid

MEMORY_MAX = 1024**3
MIN_AVAILABLE = 2*1024**3
POLICIES = {'verify':(MEMORY_MAX,MIN_AVAILABLE),'build':(2*1024**3,4*1024**3),
            'canary-build':(6*1024**3,10*1024**3),'canary-verify':(2*1024**3,10*1024**3)}
PRODUCTION_INSTANCE = 'i-0c39eff85c4286b38'
PROTECTED_VOLUMES = {'vol-065729ef75553a7ec','vol-09fea2ff4615b1088','vol-0b529abe51df1eca1'}
RUNTIME = Path('/run/spot-validation')
UNITS = Path('/run/systemd/system')
CGROUP = Path('/sys/fs/cgroup')
# No dashes: systemd therefore creates NO shared/intermediate parent slices.
SLICE = re.compile(r'spotvalidation([0-9a-f]{32})\.slice\Z')


class Unsafe(RuntimeError):
    pass


def available_memory(text):
    rows=re.findall(r'^MemAvailable:\s+(\d+) kB$',text,re.M)
    if len(rows)!=1:raise Unsafe('available memory is unknown; validation not admitted')
    return int(rows[0])*1024


def policy(purpose):
    if not isinstance(purpose,str) or purpose not in POLICIES:raise Unsafe('unknown resource purpose; no admission')
    return POLICIES[purpose]


def private_network(purpose):
    policy(purpose)
    # Only the independently attested, disposable artifact builder may fetch
    # public pinned sources/signed substitutes. Verification is always offline.
    return 'no' if purpose=='canary-build' else 'yes'


def memory_gate(purpose='verify'):
    available=available_memory(Path('/proc/meminfo').read_text())
    if available<policy(purpose)[1]:raise Unsafe('insufficient memory headroom; validation deferred, not skipped or passed')
    return available


def disposable_identity(document,instance,caller,scheduled,member,now=None):
    """A larger build budget is ONLY for a tagged, expiring, empty Spot canary.

    API/IMDS failures refuse. No environment/CLI attestation or production
    instance, role, ASG, source/home volume is a valid substitute.
    """
    now=time.time() if now is None else now
    ident=document.get('instanceId');account='537112465379';region='ap-northeast-2'
    if (ident==PRODUCTION_INSTANCE or not isinstance(ident,str) or not re.fullmatch('i-[0-9a-f]{17}',ident)
            or document.get('accountId')!=account or document.get('region')!=region
            or document.get('imageId')!='ami-0d44956a8229b0dad' or instance.get('InstanceId')!=ident
            or instance.get('ImageId')!=document['imageId'] or instance.get('State',{}).get('Name')!='running'
            or instance.get('InstanceLifecycle')!='spot'):
        raise Unsafe('larger build budget refused outside exact disposable Spot identity')
    tags={}
    for row in instance.get('Tags',[]):
        if row.get('Key') in tags:raise Unsafe('ambiguous disposable tags')
        tags[row.get('Key')]=row.get('Value')
    scope=tags.get('ScopeId','')
    if (not re.fullmatch('[0-9a-f]{12}',scope) or tags.get('ManagedBy')!='nixos-spot-validation'
            or tags.get('Purpose')!='artifact-test' or tags.get('Disposable')!='true'
            or tags.get('aws:autoscaling:groupName')!='nixos-spot-proof-'+scope
            or caller.get('Account')!=account
            or not caller.get('Arn','').startswith('arn:aws:sts::'+account+':assumed-role/nixos-spot-proof-'+scope+'/')):
        raise Unsafe('disposable scope, role or ASG not confirmed')
    try:
        deadline=datetime.fromisoformat(tags['DisposableUntil'])
        if deadline.utcoffset() is None:raise ValueError('timezone required')
        expires=deadline.timestamp()
    except (KeyError,TypeError,ValueError):raise Unsafe('disposable deadline unknown') from None
    if not 0<expires-now<=7200:raise Unsafe('disposable build deadline expired or unbounded')
    group='nixos-spot-proof-'+scope
    if (member.get('InstanceId')!=ident or member.get('AutoScalingGroupName')!=group
            or member.get('ProtectedFromScaleIn') is not False or member.get('LifecycleState')!='InService'):
        raise Unsafe('disposable ASG membership or automatic expiry protection is unknown')
    valid=[]
    for action in scheduled:
        try:
            when=datetime.fromisoformat(action['StartTime'])
            if when.utcoffset() is None:continue
            valid.append(action.get('AutoScalingGroupName')==group and action.get('ScheduledActionName')==group+'-off'
                         and action.get('Recurrence') in (None,'') and now<when.timestamp()<=expires
                         and all(type(action.get(key)) is int and action[key]==0 for key in ('MinSize','MaxSize','DesiredCapacity')))
        except (KeyError,TypeError,ValueError):continue
    if not any(valid):raise Unsafe('native one-shot canary expiry is not installed')
    devices=instance.get('BlockDeviceMappings',[])
    if len(devices)!=1:raise Unsafe('disposable host has unknown attached storage')
    ebs=devices[0].get('Ebs',{});volume=ebs.get('VolumeId','')
    if (devices[0].get('DeviceName')!='/dev/xvda' or volume in PROTECTED_VOLUMES
            or not re.fullmatch('vol-[0-9a-f]{17}',volume) or ebs.get('DeleteOnTermination') is not True):
        raise Unsafe('disposable root is not isolated from retained storage')
    return {'account':account,'region':region,'instance':ident,'scope':scope,'expires':expires,
            'root_volume':volume,'image':document['imageId'],'production':False}


def attest_disposable():
    # Explicit IMDSv2, no proxy; never read or print instance-role credentials.
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request=urllib.request.Request('http://169.254.169.254/latest/api/token',method='PUT',
                                   headers={'X-aws-ec2-metadata-token-ttl-seconds':'60'})
    with opener.open(request,timeout=3) as reply:token=reply.read(4096).decode()
    request=urllib.request.Request('http://169.254.169.254/latest/dynamic/instance-identity/document',
                                   headers={'X-aws-ec2-metadata-token':token})
    with opener.open(request,timeout=3) as reply:document=json.loads(reply.read(16384))
    if document.get('instanceId')==PRODUCTION_INSTANCE:raise Unsafe('production cannot obtain the canary build budget')
    env={k:v for k,v in os.environ.items() if not k.startswith(('AWS_','AMAZON_'))}
    env.update({'AWS_DEFAULT_REGION':'ap-northeast-2','AWS_CONFIG_FILE':'/dev/null',
                'AWS_SHARED_CREDENTIALS_FILE':'/dev/null','AWS_EC2_METADATA_DISABLED':'false'})
    def query(service,operation,*args):
        result=subprocess.run(['aws',service,operation,*args,'--region','ap-northeast-2','--output','json'],
                              env=env,capture_output=True,text=True,timeout=20)
        if result.returncode:raise Unsafe('disposable API attestation unavailable')
        return json.loads(result.stdout)
    caller=query('sts','get-caller-identity')
    result=query('ec2','describe-instances','--instance-ids',document['instanceId'])
    rows=[row for reservation in result.get('Reservations',[]) for row in reservation.get('Instances',[])]
    if len(rows)!=1:raise Unsafe('disposable instance result ambiguous')
    tags={row['Key']:row['Value'] for row in rows[0].get('Tags',[])}
    group=tags.get('aws:autoscaling:groupName','')
    if not re.fullmatch('nixos-spot-proof-[0-9a-f]{12}',group):raise Unsafe('disposable group unknown')
    scheduled=query('autoscaling','describe-scheduled-actions','--auto-scaling-group-name',group)['ScheduledUpdateGroupActions']
    members=query('autoscaling','describe-auto-scaling-instances','--instance-ids',document['instanceId'])['AutoScalingInstances']
    if len(members)!=1:raise Unsafe('disposable ASG instance result ambiguous')
    return disposable_identity(document,rows[0],caller,scheduled,members[0])


def own_group(text):
    rows=text.splitlines()
    if len(rows)!=1 or not rows[0].startswith('0::/'):raise Unsafe('unified cgroup identity unknown')
    path=rows[0][3:]
    if path=='/':return None
    parts=path.split('/')[1:]
    if any(not p or p in ('.','..') for p in parts):raise Unsafe('invalid validation cgroup path')
    matches=[(i,SLICE.fullmatch(p)) for i,p in enumerate(parts) if SLICE.fullmatch(p)]
    if not matches:return None
    if len(matches)!=1:raise Unsafe('ambiguous validation slice')
    index,match=matches[0];ident=match[1]
    if index!=0 or len(parts)!=2:
        raise Unsafe('validation is not in its dedicated service cgroup')
    unit=parts[-1]
    if not (unit=='spot-validation-'+ident+'.service'
            or re.fullmatch(r'spot-(?:gateway|resource)-validation-[0-9a-f]{12}\.service',unit)):
        raise Unsafe('unexpected member of validation slice')
    return ident,path,'/'+'/'.join(parts[:index+1]),unit


def limits(memory,swap,oom_group,cpu,score,purpose='verify'):
    if memory.strip()!=str(policy(purpose)[0]) or swap.strip()!='0' or oom_group.strip()!='1' or score.strip()!='1000':
        raise Unsafe('kernel validation memory/swap/OOM isolation not applied: '+repr((memory.strip(),swap.strip(),oom_group.strip(),score.strip())))
    fields=cpu.split()
    if (len(fields)!=2 or not all(v.isdecimal() for v in fields)
            or int(fields[0])<=0 or int(fields[1])<=0 or int(fields[0])>int(fields[1])):
        raise Unsafe('validation CPU quota is missing or exceeds one CPU')


def trusted_json(path):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd) as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=0 or info.st_mode&0o077 or info.st_size>65536:
            raise Unsafe('validation owner record untrusted')
        value=json.load(stream)
    if not isinstance(value,dict):raise Unsafe('validation owner record unknown')
    return value


def current():
    group=own_group(Path('/proc/self/cgroup').read_text())
    if group is None:return None
    ident,path,slice_path,unit=group
    owner=trusted_json(RUNTIME/ident/'owner.json')
    if (type(owner.get('schema')) is not int or owner['schema']!=2 or owner.get('id')!=ident or owner.get('slice')!='spotvalidation'+ident+'.slice'
            or owner.get('driver')!='spot-validation-'+ident+'.service'
            or owner.get('boot_id')!=Path('/proc/sys/kernel/random/boot_id').read_text().strip()):
        raise Unsafe('validation owner identity does not match kernel cgroup')
    purpose=owner.get('purpose');maximum,minimum=policy(purpose)
    if purpose in ('canary-build','canary-verify'):
        identity=owner.get('disposable',{})
        if (identity.get('instance')==PRODUCTION_INSTANCE or identity.get('production') is not False
                or not re.fullmatch('i-[0-9a-f]{17}',identity.get('instance',''))
                or identity.get('account')!='537112465379' or identity.get('region')!='ap-northeast-2'
                or identity.get('image')!='ami-0d44956a8229b0dad' or not re.fullmatch('[0-9a-f]{12}',identity.get('scope',''))
                or identity.get('root_volume') in PROTECTED_VOLUMES
                or not re.fullmatch('vol-[0-9a-f]{17}',identity.get('root_volume',''))
                or not 0<identity.get('expires',0)-time.time()<=7200):
            raise Unsafe('disposable build authority expired or changed')
    leaf=CGROUP/slice_path.lstrip('/')
    limits((leaf/'memory.max').read_text(),(leaf/'memory.swap.max').read_text(),
           (leaf/'memory.oom.group').read_text(),(leaf/'cpu.max').read_text(),Path('/proc/self/oom_score_adj').read_text(),purpose)
    if str(os.getpid()) not in (CGROUP/path.lstrip('/')/'cgroup.procs').read_text().split():
        raise Unsafe('current process membership not confirmed')
    return {'id':ident,'slice':owner['slice'],'driver':owner['driver'],'cgroup':path,'slice_cgroup':slice_path,
            'purpose':purpose,'memory_max':maximum,'minimum_available':minimum,'swap_max':0,'oom_group':True,'oom_score_adjust':1000,'cpu_quota_max_cpus':1,
            'external_Nix_daemon_builds_covered':False,'production_memory_or_idle_verified':False}


def fixture_properties():
    budget=current()
    if budget is None or budget['purpose'] not in ('verify','canary-verify'):raise Unsafe('fixture requires a verified test budget, never a build scope')
    return {'Slice':budget['slice'],'Nice':'19','OOMScoreAdjust':'1000','OOMPolicy':'stop','ProtectControlGroups':'yes',
            'MemoryMax':str(budget['memory_max']),'MemorySwapMax':'0'}


def fixture_directives():
    return ''.join(key+'='+value+'\n' for key,value in fixture_properties().items())


def write_new(path,data,mode=0o600):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
    with os.fdopen(fd,'wb') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())
    fd=os.open(Path(path).parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


GATE = '''import os,stat,sys,time
from pathlib import Path
p=Path(sys.argv[1]);deadline=time.monotonic()+30
while not p.exists():
 if time.monotonic()>deadline:raise RuntimeError("budget initialization incomplete; no verification admitted")
 time.sleep(.02)
s=p.lstat()
if not stat.S_ISREG(s.st_mode) or s.st_uid!=0 or s.st_mode&0o077 or p.read_text()!=sys.argv[2]:raise RuntimeError("budget initializer identity unknown")
os.execv(sys.argv[3],sys.argv[3:])
'''


def configure_slice(ident):
    if not re.fullmatch('[0-9a-f]{32}',ident):raise Unsafe('invalid resource initializer identity')
    owner=trusted_json(RUNTIME/ident/'owner.json')
    name='spotvalidation'+ident+'.slice';driver='spot-validation-'+ident+'.service'
    if (type(owner.get('schema')) is not int or owner['schema']!=2 or owner.get('id')!=ident or owner.get('slice')!=name or owner.get('driver')!=driver
            or owner.get('boot_id')!=Path('/proc/sys/kernel/random/boot_id').read_text().strip()):
        raise Unsafe('resource initializer owner is unknown')
    purpose=owner.get('purpose');policy(purpose)
    actual=subprocess.run(['systemctl','show',name,'--property=ControlGroup','--value'],check=True,capture_output=True,text=True).stdout.strip()
    if actual!='/'+name:raise Unsafe('resource initializer must not touch a foreign cgroup')
    pid=subprocess.run(['systemctl','show',driver,'--property=MainPID','--value'],check=True,capture_output=True,text=True).stdout.strip()
    if not pid.isdecimal() or int(pid)<=1:raise Unsafe('gated initializer process unknown')
    leaf=CGROUP/name
    if (sorted(p.name for p in leaf.iterdir() if p.is_dir())!=[driver]
            or (leaf/'cgroup.procs').read_text().strip()
            or (leaf/driver/'cgroup.procs').read_text().split()!=[pid]
            or own_group(Path('/proc/'+pid+'/cgroup').read_text())!=(ident,'/'+name+'/'+driver,'/'+name,driver)):
        raise Unsafe('resource initializer contains unknown participants; no admission')
    # systemd 260 has NO MemoryOOMGroup= slice directive. Configure only this
    # fresh, UUID-owned, gated scope; never the SSM/production/parent cgroup.
    (leaf/'memory.oom.group').write_text('1')
    limits((leaf/'memory.max').read_text(),(leaf/'memory.swap.max').read_text(),
           (leaf/'memory.oom.group').read_text(),(leaf/'cpu.max').read_text(),Path('/proc/'+pid+'/oom_score_adj').read_text(),purpose)


def launch(argv,output,purpose='verify'):
    if sys.platform!='linux' or os.geteuid()!=0:raise Unsafe('root Linux required for validation resource isolation')
    if current() is not None:raise Unsafe('nested validation launch refused')
    maximum,minimum=policy(purpose);memory_gate(purpose)
    disposable=attest_disposable() if purpose in ('canary-build','canary-verify') else None
    output=Path(output)
    if output.exists() or output.is_symlink():raise Unsafe('choose a fresh validation output; previous evidence is never overwritten')
    parent=output.parent.lstat()
    if not stat.S_ISDIR(parent.st_mode) or parent.st_uid!=0 or parent.st_mode&0o022:
        raise Unsafe('validation output directory is not root controlled')
    RUNTIME.mkdir(mode=0o700,exist_ok=True)
    info=RUNTIME.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=0 or info.st_mode&0o077:raise Unsafe('validation runtime untrusted')
    ident=uuid.uuid4().hex;folder=RUNTIME/ident;folder.mkdir(mode=0o700)
    slice_name='spotvalidation'+ident+'.slice';driver='spot-validation-'+ident+'.service'
    definition=('[Unit]\nDescription=Disposable isolated verification budget\nStopWhenUnneeded=yes\n'
                '[Slice]\nMemoryAccounting=yes\nMemoryMax='+str(maximum)+
                '\nMemorySwapMax=0\nCPUQuota=100%\nIOWeight=10\n').encode()
    unitfile=UNITS/slice_name;write_new(unitfile,definition)
    owner={'schema':2,'purpose':purpose,'id':ident,'slice':slice_name,'driver':driver,'created_at':time.time(),
           'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
           'definition_sha256':hashlib.sha256(definition).hexdigest(),'output':str(output)}
    if disposable is not None:owner['disposable']=disposable
    write_new(folder/'owner.json',json.dumps(owner,sort_keys=True).encode())
    log=output.parent/(output.stem+'-'+ident+'.log');write_new(log,b'')
    # This never-used UUID unit is loaded on demand by systemd-run. A global
    # daemon-reload can reset manually initialized OOM fences in OTHER active
    # validation slices; neither launch nor cleanup may issue it.
    command=['systemd-run','--unit='+driver,'--slice='+slice_name,'--collect','--property=Type=exec',
             '--property=Nice=19','--property=OOMScoreAdjust=1000','--property=OOMPolicy=stop',
             '--property=NoNewPrivileges=yes','--property=PrivateNetwork='+private_network(purpose),'--property=ProtectControlGroups=yes',
             '--property=StandardOutput=append:'+str(log),'--property=StandardError=inherit',
             '--setenv=PATH=/run/current-system/sw/bin','--setenv=HOME=/var/empty',
             '--setenv=PYTHONDONTWRITEBYTECODE=1','--setenv=PYTHONWARNINGS=error::ResourceWarning',
             '--setenv=AWS_EC2_METADATA_DISABLED=true',sys.executable,'-I','-c',GATE,str(folder/'ready'),ident,*argv]
    # Lost launch replies retain the exact owner/definition/log. Never stop an
    # uncertain unit or mistake systemd's acceptance for executed test counts.
    subprocess.run(command,check=True,capture_output=True,text=True)
    configure_slice(ident)
    write_new(folder/'ready',ident.encode())  # only now may the requested verification execute
    return {'verification_started':True,'all_passed':False,'run_id':ident,'unit':driver,'slice':slice_name,
            'result':str(output),'log':str(log),'purpose':purpose,'memory_max':maximum,'minimum_available':minimum,'swap_max':0,'cpu_quota_max_cpus':1,
            'launch_receipt_is_test_success':False,'production_rollout':False}


def cleanup_definition():
    budget=current()
    if budget is None:raise Unsafe('cannot clean an unknown validation scope')
    owner=trusted_json(RUNTIME/budget['id']/'owner.json');path=UNITS/budget['slice']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=owner['definition_sha256']:
        raise Unsafe('validation definition changed; preserve unknown state')
    path.unlink()
    # Do NOT daemon-reload here: reloading a deleted active definition drops
    # StopWhenUnneeded (and may reset limits). Keep the in-memory policy until
    # --collect releases its last private service; PID1 then disposes the slice.
    # No running task is stopped and no production unit is reloaded/restarted.
