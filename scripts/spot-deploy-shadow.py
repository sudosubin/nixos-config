#!/usr/bin/env python3
"""Warm, isolated SHADOW pilot only. No restart/reload of existing work/guard.

Install ON original using its pinned runtime; no Mac/controller is required.
Does NOT replace Kiro/Herdr launchers or claim producer/delivery coverage.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).parent
s = importlib.util.spec_from_file_location('shadow_deploy_shared', HERE/'spot-deploy-observer.py')
bridge = importlib.util.module_from_spec(s); s.loader.exec_module(bridge)
ROOT = Path('/var/lib/spot-work-shadow')
MARKER = Path('/etc/spot-work-shadow-current.json')


def module(source):
    s = importlib.util.spec_from_file_location('deploy_shadow_module', Path(source)/'modules/linux/spot_shadow.py')
    value = importlib.util.module_from_spec(s); s.loader.exec_module(value); return value


def render(source, python):
    p = module(source); identifier = p.version(Path(source)/'modules/linux')
    root = ROOT/identifier; code = root/'source'; name = 'spot-work-shadow-'+identifier
    bridge.require(str(python).startswith('/nix/store/') and all(c.isalnum() or c in '/-._' for c in str(python)), 'immutable runtime required')
    config = p.config({'schema': 1, 'deployment_id': identifier, 'directory': str(root), 'uid': 1001})
    cli = code/'spot-work-shadow'
    entry = '#!'+str(python)+' -I\nimport sys,runpy\nsys.dont_write_bytecode=True\nsys.argv[1:1]='+repr(['--config',str(code/'config.json')])+'\nrunpy.run_path('+repr(str(code/'spot_shadow.py'))+',run_name="__main__")\n'
    service = '\n'.join(['[Unit]', 'Description=Read-only shadow status; NEVER work readiness or termination', '[Service]', 'Type=exec', 'ExecStart='+str(cli)+' collect', 'MemoryMax=256M', 'MemorySwapMax=0', 'CPUQuota=25%', 'OOMPolicy=kill', 'OOMScoreAdjust=1000', 'Nice=19', 'NoNewPrivileges=yes', 'PrivateNetwork=yes', 'ProtectControlGroups=yes', 'RuntimeMaxSec=120', 'UMask=0077', ''])
    timer = '\n'.join(['[Unit]', 'Description=Shadow metadata every minute; not admission/termination', '[Timer]', 'OnBootSec=3min', 'OnUnitInactiveSec=1min', 'AccuracySec=10s', 'Persistent=false', '[Install]', 'WantedBy=timers.target', ''])
    return {'id': identifier, 'directory': str(root), 'source_directory': str(code), 'cli': str(cli),
            'config': config, 'entry': entry, 'service_name': name+'.service', 'timer_name': name+'.timer',
            'service': service, 'timer': timer, 'python_store_root': str(Path(python).parent.parent),
            'source_hashes': {f: hashlib.sha256((Path(source)/'modules/linux'/f).read_bytes()).hexdigest()
                              for f in ['spot_work.py','spot_shadow.py']},
            'marker': {'deployment_id': identifier, 'cli': str(cli), 'status_path': str(root/'status.json'),
                       'shadow_only': True, 'termination_capable': False, 'work_tracking_verified': False}}


def install(source, python, expected_boot, expected_system):
    p = module(source); p.collector_gate()
    bridge.require(os.geteuid() == 0 and Path('/sys/devices/virtual/dmi/id/board_asset_tag').read_text().strip() == bridge.ORIGINAL,
                   'warm pilot only targets original instance')
    before = bridge.baseline(); bridge.require(before['boot'] == expected_boot and before['system'] == before['profile'] == expected_system,
                                              'original epoch/profile changed')
    bridge.require(json.loads(Path('/etc/spot-schedule-guard.json').read_text()).get('armed') is False, 'must stay disarmed')
    binding = p.protected_observation(); plan = render(source, python)
    bridge.require(not os.path.lexists(MARKER) and not os.path.lexists(plan['directory']), 'existing/partial pilot; no installation replay/reset')
    bridge.require(str(bridge.UNITS) in subprocess.check_output(['systemd-analyze','unit-paths'],text=True).splitlines(), 'persistent unit path unavailable')
    for name in [plan['service_name'],plan['timer_name']]:
        bridge.require(subprocess.check_output(['systemctl','show',name,'-p','LoadState','--value'],text=True).strip() == 'not-found', 'foreign unit')
    bridge.directory(ROOT, 0o755); Path(plan['directory']).mkdir(mode=0o700)
    code = Path(plan['source_directory']); code.mkdir(mode=0o755)
    for name, digest in plan['source_hashes'].items():
        data = (Path(source)/'modules/linux'/name).read_bytes()
        bridge.require(hashlib.sha256(data).hexdigest() == digest, 'source bytes changed')
        bridge.write_new(code/name, data, 0o444)
    bridge.write_new(code/'config.json', json.dumps(plan['config'],sort_keys=True),0o444)
    bridge.write_new(plan['cli'], plan['entry'], 0o555)
    bridge.write_new(Path(plan['directory'])/'install-intent.json',json.dumps({'plan':plan,'baseline':before,'binding':binding},indent=2))
    package = Path(python).parent.parent
    import sqlite3
    with sqlite3.connect('file:/nix/var/nix/db/db.sqlite?mode=ro',uri=True) as db:
        bridge.require(db.execute('SELECT count(*) FROM ValidPaths WHERE path=?',(str(package),)).fetchone()[0] == 1,'runtime not registered')
    gcroot = bridge.GCROOTS/('spot-work-shadow-'+plan['id']+'-python')
    bridge.require(not os.path.lexists(gcroot), 'foreign runtime pin'); gcroot.symlink_to(package)
    # Explicit UNKNOWN seed only. Canonical work.Protocol is NEVER initialized.
    result = subprocess.run([plan['cli'],'seed'],capture_output=True,text=True,timeout=30)
    bridge.require(result.returncode == 0, 'shadow seed uncertain; no replay: '+result.stderr[-300:])
    value = json.loads(result.stdout); bridge.require(value['all_work_idle'] is False and value['unknown'] == p.UNKNOWN, 'shadow seed falsely ready')
    for path in [Path('/usr/local'),Path('/usr/local/lib'),Path('/usr/local/lib/systemd'),bridge.UNITS]: bridge.directory(path,0o755)
    for suffix in ['service','timer']: bridge.write_new(bridge.UNITS/plan[suffix+'_name'],plan[suffix],0o644)
    wants = bridge.UNITS/'timers.target.wants'; bridge.directory(wants,0o755)
    (wants/plan['timer_name']).symlink_to('../'+plan['timer_name'])
    subprocess.run(['systemctl','start',plan['timer_name']],check=True,timeout=20)
    subprocess.run(['systemctl','start',plan['service_name']],check=True,timeout=20)
    deadline = time.monotonic()+30; status = Path(plan['marker']['status_path'])
    while not status.exists() and time.monotonic()<deadline: time.sleep(.1)
    value = p.read(status)
    bridge.require(value['all_work_idle'] is False and value['termination_capable'] is False
                   and value['unknown'] == p.UNKNOWN and 0<=time.time()-value['observed_at']<60,'fresh shadow status missing')
    for suffix in ['service','timer']:
        bridge.require(subprocess.check_output(['systemctl','show',plan[suffix+'_name'],'-p','FragmentPath','--value'],text=True).strip() == str(bridge.UNITS/plan[suffix+'_name']), 'unit shadowed')
    bridge.require(subprocess.check_output(['systemctl','is-active',plan['timer_name']],text=True).strip() == 'active','timer inactive')
    after = bridge.baseline(); bridge.require(before == after, 'existing workload/epoch/approval/OOM state changed')
    bridge.write_new(MARKER,json.dumps(plan['marker'],sort_keys=True))
    receipt = {'actual_shadow_pilot_installed':True,'deployment_id':plan['id'],'cli':plan['cli'],
               'timer':plan['timer_name'],'service':plan['service_name'],'before':before,'after':after,
               'legacy_Kiro_Herdr_launchers_modified':False,'existing_work_restarted':False,
               'provider_or_output_delivery_verified':False,'full_work_tracking_verified':False,
               'actual_reboot_verified':False,'replacement_root_image_updated':False,'armed':False,'goal_complete':False}
    bridge.write_new(Path(plan['directory'])/'install-verified.json',json.dumps(receipt,indent=2)); return receipt


def disable(plan):
    bridge.require(os.geteuid() == 0 and __import__('re').fullmatch('[0-9a-f]{12}',plan['id']), 'invalid ownership')
    bridge.require(not MARKER.is_symlink() and json.loads(MARKER.read_text()) == plan['marker'], 'marker replaced/Nix-managed; no stop')
    for suffix in ['service','timer']:
        name = plan[suffix+'_name']
        bridge.require(name == 'spot-work-shadow-'+plan['id']+'.'+suffix and (bridge.UNITS/name).read_text() == plan[suffix]
                       and subprocess.check_output(['systemctl','show',name,'-p','FragmentPath','--value'],text=True).strip() == str(bridge.UNITS/name), 'unit ownership changed')
    bridge.require(os.readlink(bridge.UNITS/'timers.target.wants'/plan['timer_name']) == '../'+plan['timer_name'], 'boot link changed')
    subprocess.run(['systemctl','stop',plan['timer_name'],plan['service_name']],check=True,timeout=30)
    for suffix in ['service','timer']: (bridge.UNITS/plan[suffix+'_name']).unlink()
    (bridge.UNITS/'timers.target.wants'/plan['timer_name']).unlink(); MARKER.unlink()
    return {'only_owned_metadata_timer_disabled':True,'jobs_outputs_source_CLI_and_runtime_pin_preserved':True}


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('action',choices=['plan','install','disable'])
    parser.add_argument('--source',type=Path,default=HERE.parent); parser.add_argument('--python',default=sys.executable)
    parser.add_argument('--expected-boot'); parser.add_argument('--expected-system'); args=parser.parse_args()
    if args.action == 'plan': value=render(args.source,args.python)
    elif args.action == 'disable': value=disable(render(args.source,args.python))
    else: value=install(args.source,args.python,args.expected_boot,args.expected_system)
    print(json.dumps(value,indent=2))


if __name__ == '__main__': main()
