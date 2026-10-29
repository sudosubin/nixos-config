#!/usr/bin/env python3
"""Independent private1GiB EMPTY image inspection/content hashes/cold FD custody.

Not a production idle or all-privileged-raw-I/O fence. Never starts target
services, repairs/resets data, freezes, forces unmount, or changes device flags.
"""
import argparse
import array
from datetime import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time


def require(ok,message):
    if not ok:raise RuntimeError(message)


def inside(root,relative):
    """Resolve target-absolute symlinks INSIDE the offline image, not the host."""
    root=Path(root);todo=list(Path(relative).parts);done=[];links=0
    while todo:
        part=todo.pop(0)
        if part in {'/','.'}:continue
        if part=='..':
            require(done,'target path escapes image');done.pop();continue
        current=root.joinpath(*done,part)
        if current.is_symlink():
            links+=1;require(links<=40,'target symlink loop');link=os.readlink(current)
            if link.startswith('/'):done=[]
            todo=list(Path(link).parts)+todo
        else:done.append(part)
    return root.joinpath(*done)


def closure_rows(value):
    require(isinstance(value,(dict,list)) and value,'complete canonical closure authority required');rows={}
    source=[dict(meta,path=path) for path,meta in value.items()] if isinstance(value,dict) else value
    for row in source:
        path=row['path'];digest=row['narHash'];require(path.startswith('/nix/store/') and '/..' not in path and path not in rows and digest.startswith('sha256-'),'invalid/duplicate closure authority');rows[path]=digest
    return rows


def privacy(root):
    checked={}
    for name in ['etc/machine-id','var/lib/dbus/machine-id']:
        path=inside(root,name);require(not path.exists() or (path.is_file() and path.read_bytes() in {b'',b'uninitialized\n'}),'image has preexisting machine identity');checked[name]='absent-or-uninitialized'
    for pattern in ['etc/ssh/ssh_host_*_key','root/.ssh/id_*','root/.aws/credentials','home/*/.ssh/id_*','home/*/.aws/credentials','home/*/.local/share/kiro-cli','home/*/.local/share/openclaw-npm','var/lib/amazon/ssm/registration','var/lib/amazon/ssm/i-*','home/persist/root/nix-cache-key.sec']:
        require(not list(Path(root).glob(pattern)),'image has runtime/secret custody: '+pattern);checked[pattern]='absent'
    return checked


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--install-result',type=Path,required=True);parser.add_argument('--closure',type=Path,required=True);parser.add_argument('--folder',type=Path,required=True);args=parser.parse_args();sys.path.insert(0,str(args.source/'modules/linux'));import spot_validation as v;import spot_image as image
    budget=v.current();require(budget and budget['purpose']=='verify','independent private1GiB verification required');v.memory_gate('verify');require(Path('/proc/self/ns/mnt').stat().st_ino!=Path('/proc/1/ns/mnt').stat().st_ino and Path('/proc/self/ns/net').stat().st_ino!=Path('/proc/1/ns/net').stat().st_ino,'private inspection namespaces missing')
    e=json.loads(args.evidence.read_text());installed=json.loads(args.install_result.read_text());require(installed['installed'] is True and installed['normal_unmount_complete'] is True and installed['target_volume']==e['target_volume'] and e['target_volume'] not in image.PROTECTED and e['instance']!=image.ORIGINAL and e['boot']==Path('/proc/sys/kernel/random/boot_id').read_text().strip() and 0<=time.monotonic()-e['attested_monotonic']<120,'stale/foreign image custody')
    target,rdev,seq=image.device(e['target_volume']);require((str(target),rdev,seq)==(e['device'],e['rdev'],e['diskseq']),'image device changed');rows=closure_rows(json.loads(args.closure.read_text()));require(installed['system'] in rows,'prepared system absent from source closure');mount=Path('/mnt')/('spot-image-inspect-'+e['scope']+'-'+budget['id']);mount.mkdir(mode=0o755);folder_stat=args.folder.lstat();require(stat.S_ISDIR(folder_stat.st_mode) and folder_stat.st_uid==0 and stat.S_IMODE(folder_stat.st_mode)==0o700 and not args.folder.is_symlink() and all(p.name=='verified-and-held-'+budget['id']+'.log' and p.is_file() and not p.is_symlink() and p.stat().st_uid==0 for p in args.folder.iterdir()),'caller must precreate a private output directory containing only this owned launcher log')
    log=args.folder/'full-content-verification.jsonl';root=Path(str(target)+'p2');esp=Path(str(target)+'p1');subprocess.run(['mount','-o','ro',str(root),str(mount)],check=True)
    try:
        require(str(inside(mount,'nix/var/nix/profiles/system'))==str(mount)+installed['system'],'offline profile points to wrong system');secrets=privacy(mount);subprocess.run(['mount','-o','ro',str(esp),str(mount/'boot')],check=True)
        try:
            efi=mount/'boot/EFI/BOOT/BOOTAA64.EFI';require(efi.is_file() and efi.stat().st_size>0,'arm64 UEFI removable boot entry missing');efi_sha=hashlib.sha256(efi.read_bytes()).hexdigest()
        finally:subprocess.run(['umount',str(mount/'boot')],check=True)
        with log.open('x') as out:
            for path,expected in sorted(rows.items()):
                actual_path=mount/path.lstrip('/');require(actual_path.exists() or actual_path.is_symlink(),'missing actual offline store path');result=subprocess.run(['nix','--extra-experimental-features','nix-command','hash','path','--type','sha256','--sri',str(actual_path)],env={**os.environ,'NIX_REMOTE':'local','HOME':'/var/empty'},capture_output=True,text=True,timeout=120);actual=result.stdout.strip();out.write(json.dumps({'path':path,'expected':expected,'actual':actual,'returncode':result.returncode,'stderr':result.stderr})+'\n');out.flush();require(result.returncode==0 and actual==expected,'offline NAR content differs')
    finally:subprocess.run(['umount',str(mount)],check=True)
    fd=os.open(target,os.O_RDONLY|os.O_EXCL|os.O_CLOEXEC);current=array.array('Q',[0]);fcntl.ioctl(fd,0x80081280,current,True);require(os.fstat(fd).st_rdev==rdev and current[0]==seq,'cold image epoch changed');group=v.CGROUP/budget['slice']
    value={'verified_and_cold_FD_held':True,'scope':e['scope'],'instance':e['instance'],'boot':e['boot'],'target_volume':e['target_volume'],'system':installed['system'],'pid':os.getpid(),'pid_start':Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19],'fd':fd,'rdev':rdev,'diskseq':seq,'source_closure_paths':len(rows),'all_NAR_hashes_match':True,'privacy':secrets,'efi_sha256':efi_sha,'full_log_bytes':log.stat().st_size,'full_log_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'budget':budget,'memory_peak':(group/'memory.peak').read_text(),'memory_events':(group/'memory.events').read_text(),'not_all_privileged_raw_IO_fence_or_production_idle_proof':True,'AMI_boot_or_production_approved':False,'goal_complete':False}
    with (args.folder/'verified-and-held.json').open('x') as f:json.dump(value,f,indent=2);f.flush();os.fsync(f.fileno())
    # Bounded ONLY because these are empty-trial public image bytes, never user
    # work. Snapshot completion is independently read from AWS before release.
    while time.time()<datetime.fromisoformat(e['expires']).timestamp()-60:
        release=args.folder/'snapshot-completed.json'
        if release.exists():
            done=json.loads(release.read_text());require(done['volume']==e['target_volume'] and done['state']=='completed' and done['owner']==image.ACCOUNT and done['snapshot'].startswith('snap-'),'unknown snapshot release custody');break
        time.sleep(2)
    else:raise RuntimeError('empty image claim deadline reached without independently observed snapshot completion')
    os.close(fd);v.cleanup_definition();print(json.dumps({'snapshot_claim_normally_released':True,'image_volume':e['target_volume'],'goal_complete':False}))


if __name__=='__main__':main()
