#!/usr/bin/env python3
"""Install opt-in ACP keeper ONLY; no session creation/restart or default route.

Reuse the existing shadow namespace/collector and keep every old job/output.
Run on original via standard-role SSM; no local runtime/controller is needed.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).parent
s=importlib.util.spec_from_file_location('acp_warm_shared',HERE/'spot-deploy-observer.py')
bridge=importlib.util.module_from_spec(s);s.loader.exec_module(bridge)
ROOT=Path('/var/lib/spot-work-shadow-acp')
MARKER=Path('/etc/spot-work-shadow-acp-current.json')
NATIVE='/nix/store/bn6yjl0rgrd0yqxk3cbkkamjcxg9h47x-kiro-cli-2.10.0/bin/kiro-cli-chat'


def module(source):
    s=importlib.util.spec_from_file_location('acp_warm_module',Path(source)/'modules/linux/spot_shadow_acp.py')
    p=importlib.util.module_from_spec(s);s.loader.exec_module(p);return p


def render(source,python):
    p=module(source);identifier=p.version(Path(source)/'modules/linux');shadow_id=p.shadow.version(Path(source)/'modules/linux')
    directory=ROOT/identifier;code=directory/'source';cli=code/'spot-work-shadow-acp'
    bridge.require(str(python).startswith('/nix/store/') and all(c.isalnum() or c in '/-._' for c in str(python)),'immutable runtime required')
    config=p.settings({'schema':1,'deployment_id':identifier,'shadow_deployment_id':shadow_id,
                       'store_directory':str(p.shadow.BASE/shadow_id),'backend':NATIVE,'backend_sha256':p.NATIVE_SHA})
    entry='#!'+str(python)+' -I\nimport sys,runpy\nsys.dont_write_bytecode=True\nsys.argv[1:1]='+repr(['--config',str(code/'config.json')])+'\nrunpy.run_path('+repr(str(code/'spot_shadow_acp.py'))+',run_name="__main__")\n'
    return {'id':identifier,'directory':str(directory),'source_directory':str(code),'cli':str(cli),'entry':entry,
            'config':config,'source_hashes':{n:hashlib.sha256((Path(source)/'modules/linux'/n).read_bytes()).hexdigest() for n in p.SOURCES},
            'python_store_root':str(Path(python).parent.parent),'native_store_root':str(Path(NATIVE).parent.parent),
            'marker':{'deployment_id':identifier,'cli':str(cli),'store_directory':config['store_directory'],
                      'shadow_only':True,'termination_capable':False,'consumer_delivery_verified':False}}


def install(source,python,expected_boot,expected_system):
    p=module(source);p.shadow.collector_gate()
    bridge.require(os.geteuid()==0 and Path('/sys/devices/virtual/dmi/id/board_asset_tag').read_text().strip()==bridge.ORIGINAL,'only original warm bridge')
    before=bridge.baseline();bridge.require(before['boot']==expected_boot and before['system']==before['profile']==expected_system,'epoch/profile changed')
    bridge.require(json.loads(Path('/etc/spot-schedule-guard.json').read_text()).get('armed') is False,'guard must remain disarmed')
    plan=render(source,python);bridge.require(not os.path.lexists(MARKER) and not os.path.lexists(plan['directory']),'existing/partial ACP install: inspect, no replay/reset')
    binding=p.shadow.protected_observation();store=p.shadow.Store(plan['config']['store_directory']);store.check()
    old_marker=p.shadow.read(Path('/etc/spot-work-shadow-current.json'))
    bridge.require(old_marker['deployment_id']==plan['config']['shadow_deployment_id'] and old_marker['status_path']==str(store.root/'status.json'),'shadow lineage mismatch; never seed another empty registry')
    before_jobs={path.name:hashlib.sha256((path/'record.json').read_bytes()).hexdigest() for path in (store.root/'jobs').iterdir()}
    bridge.require(p.binary(NATIVE)==p.NATIVE_SHA,'native backend differs; no fallback')
    import sqlite3
    with sqlite3.connect('file:/nix/var/nix/db/db.sqlite?mode=ro',uri=True) as db:
        for path in [plan['python_store_root'],plan['native_store_root']]:
            bridge.require(db.execute('SELECT count(*) FROM ValidPaths WHERE path=?',(path,)).fetchone()[0]==1,'runtime/native package not registered')
    bridge.directory(ROOT,0o755);Path(plan['directory']).mkdir(mode=0o700);code=Path(plan['source_directory']);code.mkdir(mode=0o755)
    for name,digest in plan['source_hashes'].items():
        data=(Path(source)/'modules/linux'/name).read_bytes();bridge.require(hashlib.sha256(data).hexdigest()==digest,'source changed')
        bridge.write_new(code/name,data,0o444)
    bridge.write_new(code/'config.json',json.dumps(plan['config'],sort_keys=True),0o444)
    bridge.write_new(plan['cli'],plan['entry'],0o555)
    bridge.write_new(Path(plan['directory'])/'install-intent.json',json.dumps({'plan':plan,'before':before,'binding':binding,'retained_jobs':before_jobs},indent=2))
    pins={}
    for kind,target in [('python',plan['python_store_root']),('native',plan['native_store_root'])]:
        pin=bridge.GCROOTS/('spot-work-shadow-acp-'+plan['id']+'-'+kind)
        bridge.require(not os.path.lexists(pin),'foreign runtime pin');pin.symlink_to(target);pins[kind]=str(pin)
    after=bridge.baseline();bridge.require(before==after,'existing workload/epoch/canonical approval changed')
    after_jobs={path.name:hashlib.sha256((path/'record.json').read_bytes()).hexdigest() for path in (store.root/'jobs').iterdir()}
    bridge.require(before_jobs==after_jobs,'existing shadow custody changed; inspect, never restore/reset over it')
    bridge.write_new(MARKER,json.dumps(plan['marker'],sort_keys=True))
    receipt={'actual_opt_in_ACP_keeper_installed':True,'deployment_id':plan['id'],'cli':plan['cli'],
             'existing_shadow_store':str(store.root),'existing_job_record_hashes_preserved':after_jobs,
             'runtime_pins':pins,'native_backend_sha256':p.NATIVE_SHA,'before':before,'after':after,
             'native_or_model_session_started_by_install':False,'existing_launchers_or_sessions_modified':False,
             'canonical_custody_initialized':False,'all_producer_or_consumer_delivery_verified':False,
             'off_root_work_journal_configured':False,'actual_OS_reboot_or_flake_reapply':False,'armed':False,'goal_complete':False}
    bridge.write_new(Path(plan['directory'])/'install-verified.json',json.dumps(receipt,indent=2));return receipt


def disable(plan):
    # Discovery only: NEVER terminate a keeper/native session or delete output.
    bridge.require(os.geteuid()==0 and not MARKER.is_symlink() and json.loads(MARKER.read_text())==plan['marker'],
                   'foreign/Nix-owned marker; no disable')
    MARKER.unlink()
    return {'only_owned_discovery_marker_removed':True,'all_sessions_data_source_and_runtime_pins_preserved':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['plan','install','disable'])
    parser.add_argument('--source',type=Path,default=HERE.parent);parser.add_argument('--python',default=sys.executable)
    parser.add_argument('--expected-boot');parser.add_argument('--expected-system');args=parser.parse_args()
    if args.action=='plan':value=render(args.source,args.python)
    elif args.action=='disable':value=disable(render(args.source,args.python))
    else:value=install(args.source,args.python,args.expected_boot,args.expected_system)
    print(json.dumps(value,indent=2))


if __name__=='__main__':main()
