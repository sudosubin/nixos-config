#!/usr/bin/env python3
"""Offline EMPTY image-root installer, never a production disk/migration tool.

Only a separately native-expiring, fresh32GiB encrypted tagged volume is touched.
The build is private2GiB: attached extra storage NEVER obtains canary6GiB authority.
No keys/home/agent registration/machine ID are copied from the running host.
"""
from datetime import datetime
import argparse
import array
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import urllib.request

ACCOUNT='537112465379';REGION='ap-northeast-2';ORIGINAL='i-0c39eff85c4286b38'
PROTECTED={'vol-065729ef75553a7ec','vol-09fea2ff4615b1088','vol-0b529abe51df1eca1'}


def require(ok,message):
    if not ok:raise RuntimeError(message)


def validate(doc,instance,caller,member,actions,volumes,target,scope,expires,now=None):
    now=time.time() if now is None else now;require(re.fullmatch('[0-9a-f]{12}',scope) and re.fullmatch('vol-[0-9a-f]{17}',target) and target not in PROTECTED,'invalid image target/scope')
    iid=doc.get('instanceId');require(iid!=ORIGINAL and re.fullmatch('i-[0-9a-f]{17}',iid or '') and doc.get('accountId')==ACCOUNT and doc.get('region')==REGION and doc.get('imageId')=='ami-0d44956a8229b0dad','foreign/production image builder')
    require(caller.get('Account')==ACCOUNT and caller.get('Arn')=='arn:aws:sts::'+ACCOUNT+':assumed-role/nixos-spot-proof-'+scope+'/'+iid,'foreign builder role')
    tags={r['Key']:r['Value'] for r in instance.get('Tags',[])};require(len(tags)==len(instance.get('Tags',[])) and tags.get('ScopeId')==scope and tags.get('Disposable')=='true' and tags.get('DisposableUntil')==expires and tags.get('ManagedBy')=='nixos-spot-validation' and tags.get('Purpose')=='artifact-test' and tags.get('aws:autoscaling:groupName')=='nixos-spot-proof-'+scope,'unknown builder tags')
    require(instance.get('InstanceId')==iid and instance.get('InstanceLifecycle')=='spot' and instance.get('ImageId')==doc['imageId'] and instance.get('InstanceType')=='r7g.large' and instance.get('IamInstanceProfile',{}).get('Arn')=='arn:aws:iam::'+ACCOUNT+':instance-profile/nixos-spot-proof-'+scope and instance['State']['Name']=='running','not running empty Spot')
    require(member.get('InstanceId')==iid and member.get('AutoScalingGroupName')=='nixos-spot-proof-'+scope and member.get('ProtectedFromScaleIn') is False and member.get('LifecycleState')=='InService','builder expiry not unprotected')
    deadline=datetime.fromisoformat(expires);require(deadline.utcoffset() is not None and 300<deadline.timestamp()-now<=7200,'image build native lifetime exhausted')
    require(len(actions)==1 and actions[0].get('AutoScalingGroupName')==member['AutoScalingGroupName'] and actions[0].get('ScheduledActionName')==member['AutoScalingGroupName']+'-off' and not actions[0].get('Recurrence') and datetime.fromisoformat(actions[0]['StartTime']).timestamp()==deadline.timestamp() and all(type(actions[0].get(k)) is int and actions[0][k]==0 for k in ['MinSize','MaxSize','DesiredCapacity']),'native expiry changed')
    mappings=instance.get('BlockDeviceMappings',[]);require(len(mappings)==2 and len(volumes)==2,'only source root plus one blank image root allowed')
    roots=[m for m in mappings if m.get('DeviceName')=='/dev/xvda'];require(len(roots)==1 and roots[0]['Ebs']['DeleteOnTermination'] is True,'source root differs');root=roots[0]['Ebs']['VolumeId'];require(root!=target and root not in PROTECTED,'retained/ambiguous source root')
    require({m['Ebs']['VolumeId'] for m in mappings}=={root,target} and {v['VolumeId'] for v in volumes}=={root,target},'foreign/duplicate attached storage')
    for volume in volumes:
        require(volume['VolumeId'] in {root,target} and volume['Encrypted'] is True and volume['Size']==32 and len(volume['Attachments'])==1 and volume['Attachments'][0]['InstanceId']==iid and volume['Attachments'][0]['State']=='attached','volume encryption/custody differs')
        if volume['VolumeId']==target:
            vt={r['Key']:r['Value'] for r in volume.get('Tags',[])};require(len(vt)==len(volume.get('Tags',[])) and vt.get('ScopeId')==scope and vt.get('Purpose')=='image-root' and vt.get('ManagedBy')=='nixos-spot-validation' and not volume.get('SnapshotId') and volume['Attachments'][0]['DeleteOnTermination'] is False,'not the fresh blank image root')
    return {'instance':iid,'scope':scope,'expires':expires,'root_volume':root,'target_volume':target,'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'attested_monotonic':time.monotonic(),'account':ACCOUNT,'region':REGION,'not_production_or_idle_authority':True}


def api(service,operation,*args):
    env={k:v for k,v in os.environ.items() if not k.startswith(('AWS_','AMAZON_'))};env.update(AWS_CONFIG_FILE='/dev/null',AWS_SHARED_CREDENTIALS_FILE='/dev/null',AWS_EC2_METADATA_DISABLED='false',AWS_MAX_ATTEMPTS='1',HOME='/var/empty')
    p=subprocess.run(['aws',service,operation,*args,'--region',REGION,'--output','json'],env=env,capture_output=True,text=True,timeout=30);require(p.returncode==0,'image metadata API unavailable');return json.loads(p.stdout)


def device(volume):
    found=[Path('/dev')/p.parent.parent.name for p in Path('/sys/class/block').glob('nvme*n1/device/serial') if p.read_text().strip()==volume.replace('-','')]
    require(len(found)==1,'target NVMe serial ambiguous');path=found[0];require(stat.S_ISBLK(path.stat().st_mode),'target is not block device');fd=os.open(path,os.O_RDONLY|os.O_EXCL|os.O_CLOEXEC)
    try:
        seq=array.array('Q',[0]);fcntl.ioctl(fd,0x80081280,seq,True);return path,os.fstat(fd).st_rdev,seq[0]
    finally:os.close(fd)


def attest(scope,target,expires,output):
    group=Path('/sys/fs/cgroup')/Path('/proc/self/cgroup').read_text().strip().split('::')[-1].lstrip('/');require((group/'memory.max').read_text().strip()=='134217728' and (group/'memory.swap.max').read_text().strip()=='0','image attestation needs narrow128MiB metadata budget');(group/'memory.oom.group').write_text('1')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://169.254.169.254/latest/'
    with opener.open(urllib.request.Request(base+'api/token',method='PUT',headers={'X-aws-ec2-metadata-token-ttl-seconds':'60'}),timeout=3) as f:token=f.read(4096).decode()
    with opener.open(urllib.request.Request(base+'dynamic/instance-identity/document',headers={'X-aws-ec2-metadata-token':token}),timeout=3) as f:doc=json.loads(f.read(16384))
    require(doc.get('instanceId')!=ORIGINAL,'original cannot authorize an image disk');iid=doc['instanceId'];rows=api('ec2','describe-instances','--instance-ids',iid)['Reservations'];require(len(rows)==1 and rows[0]['OwnerId']==ACCOUNT and len(rows[0]['Instances'])==1,'EC2 image-builder result ambiguous');instance=rows[0]['Instances'][0];members=api('autoscaling','describe-auto-scaling-instances','--instance-ids',iid)['AutoScalingInstances'];require(len(members)==1,'ASG member ambiguous');actions=api('autoscaling','describe-scheduled-actions','--auto-scaling-group-name','nixos-spot-proof-'+scope)['ScheduledUpdateGroupActions'];ids=[m['Ebs']['VolumeId'] for m in instance['BlockDeviceMappings']];volumes=api('ec2','describe-volumes','--volume-ids',*ids)['Volumes'];evidence=validate(doc,instance,api('sts','get-caller-identity'),members[0],actions,volumes,target,scope,expires)
    path,rdev,seq=device(target);evidence.update(device=str(path),rdev=rdev,diskseq=seq)
    with Path(output).open('x') as f:json.dump(evidence,f,indent=2);f.flush();os.fsync(f.fileno())
    Path(output).chmod(0o600);return evidence


def tool(pattern,name):
    paths=list(Path('/nix/store').glob(pattern+'/bin/'+name));require(paths,'immutable image tool missing: '+name);return str(paths[0])


def install(evidence,system,output):
    import spot_validation as v
    budget=v.current();require(budget is not None and budget['purpose']=='build','offline image install needs private2GiB build budget, never canary/verify');v.memory_gate('build')
    require(Path('/proc/self/ns/net').stat().st_ino!=Path('/proc/1/ns/net').stat().st_ino and 'NoNewPrivs:\t1' in Path('/proc/self/status').read_text(),'private image network/NNP required')
    path=Path(evidence);st=path.lstat();require(stat.S_ISREG(st.st_mode) and st.st_uid==0 and not st.st_mode&0o077 and st.st_size<=65536,'untrusted image API evidence');e=json.loads(path.read_text());require(e['instance']!=ORIGINAL and e['target_volume'] not in PROTECTED and e['boot']==Path('/proc/sys/kernel/random/boot_id').read_text().strip() and 0<=time.monotonic()-e['attested_monotonic']<120,'stale/foreign image custody')
    require(datetime.fromisoformat(e['expires']).timestamp()-time.time()>300,'native image window exhausted');target,rdev,seq=device(e['target_volume']);require((str(target),rdev,seq)==(e['device'],e['rdev'],e['diskseq']),'target device changed')
    system=Path(system);require(re.fullmatch('/nix/store/[0-9a-df-np-sv-z]{32}-nixos-system-[^/]+',str(system)) and system.is_dir() and json.loads((system/'etc/spot-schedule-guard.json').read_text())['armed'] is False,'unverified/armed image system')
    require(subprocess.run(['findmnt','-n','--mountpoint','/home'],capture_output=True).returncode==1,'never image a mounted user home')
    # This process must already be in its OWN unshare --mount namespace. It is
    # forbidden to alter host mount propagation to make an install succeed.
    require(Path('/proc/self/ns/mnt').stat().st_ino!=Path('/proc/1/ns/mnt').stat().st_ino,'private image mount namespace required')
    require(subprocess.run(['blkid','-p','-c','/dev/null',str(target)],capture_output=True).returncode==2,'target not virgin; no format/reset retry')
    require(not list((Path('/sys/class/block')/target.name).glob(target.name+'p*')),'target already partitioned; no replay')
    gpt=tool('*-gptfdisk-*','sgdisk');fat=tool('*-dosfstools-*','mkfs.fat');ext=tool('*-e2fsprogs-*-bin','mkfs.ext4');original_installer=Path(tool('*-nixos-install','nixos-install'))
    # NixOS's stock auto substituter may select the external Nix daemon even
    # with a private target store. This exact audited one-line copy uses the
    # SOURCE LOCAL store directly; no daemon export/build escapes the cage.
    program=original_installer.read_bytes();require(program.count(b'sub="auto?trusted=1"')==1,'unknown nixos-install transport contract')
    derived=program.replace(b'sub="auto?trusted=1"',b'sub="local?trusted=1"');installer=Path(output).with_name('nixos-install-local-only')
    with installer.open('xb') as f:f.write(derived)
    installer.chmod(0o700)
    log=Path(output).with_suffix('.complete.log');mount=Path('/mnt')/('spot-image-'+e['scope']);mount.mkdir(mode=0o755)
    env={**os.environ,'NIX_REMOTE':'local','HOME':'/var/empty','PATH':'/run/current-system/sw/bin','NIX_CONFIG':'builders =\nsubstituters = https://cache.nixos.org\nrequire-sigs = true\n'}
    with log.open('x') as out:
        def call(*args):subprocess.run(list(args),env=env,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=600)
        call(gpt,'--clear','--new=1:2048:+512M','--typecode=1:EF00','--new=2:0:0','--typecode=2:8300',str(target));call('udevadm','settle')
        esp=Path(str(target)+'p1');root=Path(str(target)+'p2');require(esp.exists() and root.exists(),'target partition nodes missing')
        call(fat,'-F','32',str(esp));call(ext,'-F',str(root));post_format=device(e['target_volume']);require(post_format[:2]==(target,rdev),'target changed during owned partitioning');seq=post_format[2];call('mount',str(root),str(mount));(mount/'boot').mkdir();call('mount',str(esp),str(mount/'boot'))
        try:call(str(installer),'--root',str(mount),'--system',str(system),'--no-root-passwd','--no-channel-copy','--option','builders','','--option','require-sigs','true')
        finally:
            # Normal unmount ONLY; busy/uncertain remains a failed install, not
            # a force/lazy detach or a claim of snapshot eligibility.
            call('umount',str(mount/'boot'));call('umount',str(mount))
        call(tool('*-e2fsprogs-*-bin','e2label'),str(root),'nixos');call(tool('*-dosfstools-*','fatlabel'),str(esp),'ESP')
    require(device(e['target_volume'])==(target,rdev,seq),'image device epoch changed after install')
    result={'installed':True,'target_volume':e['target_volume'],'system':str(system),'boot':e['boot'],'private2GiB_budget':budget,'source_keys_home_machineid_or_agent_registration_copied':False,'original_installer_sha256':hashlib.sha256(program).hexdigest(),'local_only_installer_sha256':hashlib.sha256(derived).hexdigest(),'normal_unmount_complete':True,'snapshot_or_AMI_verified':False,'goal_complete':False,'memory_peak':(v.CGROUP/budget['slice']/'memory.peak').read_text(),'memory_events':(v.CGROUP/budget['slice']/'memory.events').read_text()}
    with Path(output).open('x') as f:json.dump(result,f,indent=2);f.flush();os.fsync(f.fileno())
    v.cleanup_definition();return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['attest','install']);parser.add_argument('--scope');parser.add_argument('--target');parser.add_argument('--expires');parser.add_argument('--evidence',type=Path);parser.add_argument('--system');parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();require(sys.platform=='linux' and os.geteuid()==0,'root Linux image helper required')
    if args.action=='attest':require(args.scope and args.target and args.expires,'exact target/scope/native expiry required');value=attest(args.scope,args.target,args.expires,args.output)
    else:require(args.evidence and args.system,'API evidence/system required');value=install(args.evidence,args.system,args.output)
    print(json.dumps(value))


if __name__=='__main__':main()
