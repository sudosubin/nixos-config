#!/usr/bin/env python3
"""Private2GiB PUBLIC artifact extraction, never a verifier/build authority grant."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tarfile

PUBLIC_SHA='b66b47495348028b98565b76925e722518827e5f9d1c9cbae76a18fa64d27e21'
PUBLIC_BYTES=272580380


def require(ok,message):
    if not ok:raise RuntimeError(message)


def member_allowed(member):
    path=Path(member.name)
    require(not path.is_absolute() and '..' not in path.parts and path.parts and path.parts[0] in {'kiro-cli','openclaw-npm'},'nonpublic runtime archive path')
    require(member.isfile() or member.isdir() or member.issym() or member.islnk(),'nonpublic/special runtime entry')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--archive',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    source=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(source/'modules/linux'));import spot_validation as v
    budget=v.current();require(budget and budget['purpose']=='build','public extraction needs its private2GiB artifact budget, never a verify/canary scope');v.memory_gate('build')
    require(Path('/proc/self/ns/net').stat().st_ino!=Path('/proc/1/ns/net').stat().st_ino,'public extraction network must be private')
    parent=args.archive.parent;require(args.archive.name=='runtime.body' and parent.parent==Path('/var/lib/spot-autobootstrap'),'unknown extraction namespace');identity=parent/'identity.json';info=identity.lstat();require(stat.S_ISREG(info.st_mode) and info.st_uid==0 and not info.st_mode&0o022 and info.st_size<=65536,'untrusted bootstrap identity');value=json.loads(identity.read_text())
    require(value.get('instanceId')!='i-0c39eff85c4286b38' and value.get('accountId')=='537112465379' and value.get('region')=='ap-northeast-2' and value.get('boot')==Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'foreign/old original bootstrap custody')
    require(subprocess.run(['findmnt','-n','--mountpoint','/home'],capture_output=True).returncode==1,'never extract into a mounted home');destination=Path('/home/sudosubin/.local/share')
    for path in [Path('/home/sudosubin'),Path('/home/sudosubin/.local'),destination]:require(not path.is_symlink(),'untrusted public destination')
    require(destination.is_dir() and not any((destination/name).exists() or (destination/name).is_symlink() for name in ['kiro-cli','openclaw-npm']),'existing public runtime is never overwritten')
    digest=hashlib.sha256()
    with args.archive.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):digest.update(block)
    require(args.archive.stat().st_size==PUBLIC_BYTES and digest.hexdigest()==PUBLIC_SHA,'public runtime bytes differ')
    count=0
    with tarfile.open(args.archive) as archive:
        for member in archive.getmembers():member_allowed(member);count+=1
        archive.extractall(destination,filter='data')
    group=v.CGROUP/budget['slice'];result={'extracted':True,'members':count,'public_runtime_sha256':PUBLIC_SHA,'resource_budget':budget,'memory_peak':(group/'memory.peak').read_text(),'memory_events':(group/'memory.events').read_text(),'not_verification_or_production_authority':True,'goal_complete':False}
    require(not args.output.exists(),'extraction result custody changed');temporary=args.output.with_name('.complete-'+args.output.name)
    with temporary.open('x') as f:json.dump(result,f,indent=2);f.flush();os.fsync(f.fileno())
    os.replace(temporary,args.output)
    v.cleanup_definition();print(json.dumps(result))


if __name__=='__main__':main()
