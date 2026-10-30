#!/usr/bin/env python3
"""Warm, read-only observer bridge; no NixOS switch/reboot/global reload.

Persistent lower-priority /usr/local unit load path bridges the existing old
NixOS root until the maintained Nix module is activated. NOT replacement-root
persistence: bake/promote the Nix module separately after recovery gates.
Run install ON the original via standard-role SSM/CloudShell, not a Mac daemon.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time

ROOT=Path('/var/lib/spot-protection-observer')
UNITS=Path('/usr/local/lib/systemd/system')
MARKER=Path('/etc/spot-protection-observer-current.json')
GCROOTS=Path('/nix/var/nix/gcroots')
ORIGINAL='i-0c39eff85c4286b38'


def require(ok,msg):
    if not ok:raise RuntimeError(msg)


def observer(source):
    s=importlib.util.spec_from_file_location('observer_deploy_module',Path(source)/'modules/linux/spot_observer.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p);return p


def render(source,python,asg_arn):
    p=observer(source);identifier=p.version(Path(source)/'modules/linux');directory=ROOT/identifier;code=directory/'source';name='spot-protection-observer-'+identifier;config=p.settings({'schema':1,'account':'537112465379','region':'ap-northeast-2','asg':'nixos-ec2-asg','asg_arn':asg_arn,'deployment_id':identifier,'state_directory':str(directory)})
    require(str(python).startswith('/nix/store/') and all(c.isalnum() or c in '/-._' for c in str(python)),'immutable cloud interpreter required')
    service='\n'.join(['[Unit]','Description=Read-only protection observation; NEVER unprotects/initializes work','After=network-online.target','Wants=network-online.target','[Service]','Type=exec','ExecStart='+str(python)+' -B -I '+str(code/'spot_observer.py')+' --config '+str(code/'config.json'),'MemoryMax=256M','MemorySwapMax=0','CPUQuota=25%','OOMPolicy=kill','OOMScoreAdjust=1000','Nice=19','NoNewPrivileges=yes','PrivateNetwork=yes','ProtectControlGroups=yes','RuntimeMaxSec=180','UMask=0077','Environment=PATH=/run/current-system/sw/bin',''])
    timer='\n'.join(['[Unit]','Description=Read-only observation every5min; no termination authority','[Timer]','OnBootSec=2min','OnUnitInactiveSec=5min','AccuracySec=15s','Persistent=false','[Install]','WantedBy=timers.target',''])
    marker={'deployment_id':identifier,'observer_unit':name+'.service','observer_timer':name+'.timer','status_path':str(directory/'status.json'),'observation_only':True,'termination_capable':False}
    return {'id':identifier,'directory':str(directory),'source_directory':str(code),'config':config,'service_name':name+'.service','timer_name':name+'.timer','service':service,'timer':timer,'marker':marker,'unit_directory':str(UNITS),'python_store_root':str(Path(python).parent.parent),'source_hashes':{f:hashlib.sha256((Path(source)/'modules/linux'/f).read_bytes()).hexdigest() for f in ['spot_protection.py','spot_observer.py']},'no_full_guard_install_or_arming':True}


def write_new(path,data,mode=0o600):
    path=Path(path);data=data.encode() if isinstance(data,str) else data;fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
    with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())


def directory(path,mode):
    path=Path(path)
    if not os.path.lexists(path):path.mkdir(mode=mode)
    st=path.lstat();require(stat.S_ISDIR(st.st_mode) and st.st_uid==0 and not st.st_mode&0o022,'foreign/writable deployment parent: '+str(path))


def baseline():
    def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).exists() else None
    return {'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'system':str(Path('/run/current-system').resolve()),'profile':str(Path('/nix/var/nix/profiles/system').resolve()),'guard_config_sha256':digest('/etc/spot-schedule-guard.json'),'operational_status_sha256':digest('/home/persist/manifests/deployment-status.json'),'protocol_exists':Path('/run/spot-schedule-guard').exists(),'approval_exists':Path('/home/persist/manifests/active.json').exists(),'service_PIDs':{u:subprocess.check_output(['systemctl','show',u,'-p','MainPID','--value'],text=True).strip() for u in ['amazon-ssm-agent.service','docker.service','user@1001.service']},'live_validation_OOM_fences':{str(p):p.read_text() for p in Path('/sys/fs/cgroup').glob('spotvalidation*.slice/memory.oom.group')}}


def read_state(plan):
    path=Path(plan['marker']['status_path']);require(path.is_file() and not path.is_symlink(),'observer has no confirmed diagnostic output');value=json.loads(path.read_text());require(value.get('deployment_id')==plan['id'] and value.get('termination_capable') is False and value.get('observation_only') is True and value.get('instance')==ORIGINAL and value.get('boot_id')==Path('/proc/sys/kernel/random/boot_id').read_text().strip() and 0<=time.time()-value.get('observed_at',0)<=180,'observer diagnostic stale/unknown');return value


def install(source,python,asg_arn,expected_boot,expected_system):
    p=observer(source);p.kernel(268435456,25,private=True);require(os.geteuid()==0 and Path('/sys/devices/virtual/dmi/id/board_asset_tag').read_text().strip()==ORIGINAL,'warm bridge only targets original instance');before=baseline();require(before['boot']==expected_boot and before['system']==before['profile']==expected_system,'original epoch/profile changed')
    require(json.loads(Path('/etc/spot-schedule-guard.json').read_text()).get('armed') is False,'warm observer never arms a guard');plan=render(source,python,asg_arn);require(not os.path.lexists(MARKER) and not os.path.lexists(plan['directory']),'existing observer/partial deployment requires inspection, never reset/replay');paths=subprocess.check_output(['systemd-analyze','unit-paths'],text=True).splitlines();require(str(UNITS) in paths,'persistent lower-priority unit load path unsupported')
    for unit in [plan['service_name'],plan['timer_name']]:require(subprocess.check_output(['systemctl','show',unit,'-p','LoadState','--value'],text=True).strip()=='not-found','foreign unit already loaded')
    # All unit names are NEW. No global reload, enable, switch or service restart.
    directory(ROOT,0o755);Path(plan['directory']).mkdir(mode=0o700);code=Path(plan['source_directory']);code.mkdir(mode=0o755)
    for name,digest in plan['source_hashes'].items():
        data=(Path(source)/'modules/linux'/name).read_bytes();require(hashlib.sha256(data).hexdigest()==digest,'source changed');write_new(code/name,data,0o444)
    write_new(code/'config.json',json.dumps(plan['config'],sort_keys=True),0o444);write_new(Path(plan['directory'])/'install-intent.json',json.dumps({'plan':plan,'baseline':before},indent=2))
    # Direct GC root protects the immutable cloud interpreter through local GC.
    package=Path(python).parent.parent;require(package.parent==Path('/nix/store') and (package/'bin/python3').is_file(),'invalid runtime package')
    import sqlite3
    with sqlite3.connect('file:/nix/var/nix/db/db.sqlite?mode=ro',uri=True) as db:require(db.execute('SELECT count(*) FROM ValidPaths WHERE path=?',(str(package),)).fetchone()[0]==1,'interpreter runtime is not registered in local store')
    gcroot=GCROOTS/('spot-protection-observer-'+plan['id']+'-python');require(not os.path.lexists(gcroot),'foreign runtime GC root');gcroot.symlink_to(package)
    for path in [Path('/usr/local'),Path('/usr/local/lib'),Path('/usr/local/lib/systemd'),UNITS]:directory(path,0o755)
    for suffix in ['service','timer']:write_new(UNITS/(plan[suffix+'_name']),plan[suffix],0o644)
    wants=UNITS/'timers.target.wants';directory(wants,0o755);(wants/plan['timer_name']).symlink_to('../'+plan['timer_name'])
    subprocess.run(['systemctl','start',plan['timer_name']],check=True,timeout=20);subprocess.run(['systemctl','start',plan['service_name']],check=True,timeout=20);end=time.monotonic()+175
    while time.monotonic()<end:
        if Path(plan['marker']['status_path']).exists():break
        time.sleep(1)
    first=read_state(plan);require(first['ASG']['AutoScalingGroupARN']==asg_arn and any(i['InstanceId']==ORIGINAL and i['ProtectedFromScaleIn'] is True for i in first['ASG']['Instances']),'protection not confirmed by read-only observer')
    while subprocess.check_output(['systemctl','show',plan['service_name'],'-p','MainPID','--value'],text=True).strip()!='0' and time.monotonic()<end:time.sleep(.2)
    require(subprocess.check_output(['systemctl','show',plan['service_name'],'-p','MainPID','--value'],text=True).strip()=='0','first observer read still running; no replay')
    write_new(MARKER,json.dumps(plan['marker'],sort_keys=True));stamp=time.time();subprocess.run(['systemctl','start',plan['service_name']],check=True,timeout=20);end=time.monotonic()+175
    while time.monotonic()<end:
        value=read_state(plan)
        if value['observed_at']>=stamp:break
        time.sleep(1)
    require(value['observed_at']>=stamp,'second observer pass not confirmed')
    while subprocess.check_output(['systemctl','show',plan['service_name'],'-p','MainPID','--value'],text=True).strip()!='0' and time.monotonic()<end:time.sleep(.2)
    require(subprocess.check_output(['systemctl','show',plan['service_name'],'-p','MainPID','--value'],text=True).strip()=='0','observer read not settled');after=baseline();require(before==after,'original service/epoch/config/OOM state changed; inspect, never force rollback user state');require(subprocess.check_output(['systemctl','is-active',plan['timer_name']],text=True).strip()=='active','observer timer inactive');require(subprocess.check_output(['systemctl','is-enabled',plan['timer_name']],text=True).strip()=='enabled','persistent timer target link not recognized')
    for suffix in ['service','timer']:require(subprocess.check_output(['systemctl','show',plan[suffix+'_name'],'-p','FragmentPath','--value'],text=True).strip()==str(UNITS/plan[suffix+'_name']),'observer unit is shadowed')
    value={'deployed_read_only_observer':True,'deployment_id':plan['id'],'service':plan['service_name'],'timer':plan['timer_name'],'status':plan['marker']['status_path'],'observed_classification':value['classification'],'before':before,'after':after,'persistent_unit_path_and_timer_boot_link_verified':True,'interpreter_GC_root':str(gcroot),'actual_reboot_performed':False,'replacement_root_image_updated':False,'full_termination_guard_deployed':False,'work_tracking_verified':False,'armed':False,'goal_complete':False};write_new(Path(plan['directory'])/'install-verified.json',json.dumps(value,indent=2));return value


def rollback(plan):
    """Only this observer's files/units. Preserve source, diagnostics and intent."""
    require(os.geteuid()==0,'root required');identifier=plan['id'];require(__import__('re').fullmatch('[0-9a-f]{12}',identifier),'invalid rollback ID');require(plan['directory']==str(ROOT/identifier) and plan['service_name']=='spot-protection-observer-'+identifier+'.service' and plan['timer_name']=='spot-protection-observer-'+identifier+'.timer','foreign rollback plan')
    for suffix in ['service','timer']:require((UNITS/plan[suffix+'_name']).read_text()==plan[suffix],'observer definition changed; no rollback')
    if os.path.lexists(MARKER):require(json.loads(MARKER.read_text())==plan['marker'],'observer marker changed; no rollback')
    else:require((Path(plan['directory'])/'install-intent.json').is_file(),'unknown partial observer custody')
    gcroot=GCROOTS/('spot-protection-observer-'+identifier+'-python');require(gcroot.is_symlink() and os.readlink(gcroot)==plan['python_store_root'],'observer runtime GC root changed');require(os.readlink(UNITS/'timers.target.wants'/plan['timer_name'])=='../'+plan['timer_name'],'observer boot link changed')
    subprocess.run(['systemctl','stop',plan['timer_name'],plan['service_name']],check=True,timeout=30)
    for suffix in ['service','timer']:(UNITS/plan[suffix+'_name']).unlink()
    (UNITS/'timers.target.wants'/plan['timer_name']).unlink()
    if os.path.lexists(MARKER):MARKER.unlink()
    gcroot.unlink();return {'only_owned_read_only_observer_removed':True,'source_and_diagnostics_preserved':True,'no_global_reload':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['plan','install','rollback']);parser.add_argument('--source',type=Path,default=Path(__file__).parent.parent);parser.add_argument('--python',default=sys.executable);parser.add_argument('--asg-arn',required=True);parser.add_argument('--expected-boot');parser.add_argument('--expected-system');args=parser.parse_args()
    if args.action=='plan':value=render(args.source,args.python,args.asg_arn)
    elif args.action=='rollback':value=rollback(render(args.source,args.python,args.asg_arn))
    else:require(args.expected_boot and args.expected_system,'exact current epoch/profile required');value=install(args.source,args.python,args.asg_arn,args.expected_boot,args.expected_system)
    print(json.dumps(value,indent=2))


if __name__=='__main__':main()
