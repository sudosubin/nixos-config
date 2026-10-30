#!/usr/bin/env python3
"""Install a NEW explicit TUI entry, never replace defaults or start a session.

Original-only warm deployment via cloud role/SSM. Existing shadow store and old
ACP keeper bytes remain intact. Public Bun/TUI software only, no user state,
credentials, approvals, canonical initialization or service reload/restart.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys

HERE=Path(__file__).parent
s=importlib.util.spec_from_file_location('tui_deploy_shared',HERE/'spot-deploy-observer.py')
bridge=importlib.util.module_from_spec(s);s.loader.exec_module(bridge)
ROOT=Path('/var/lib/spot-work-shadow-tui')
MARKER=Path('/etc/spot-work-shadow-tui-current.json')
NATIVE='/nix/store/bn6yjl0rgrd0yqxk3cbkkamjcxg9h47x-kiro-cli-2.10.0/bin/kiro-cli-chat'


def module(source):
    s=importlib.util.spec_from_file_location('tui_deploy_runtime',Path(source)/'modules/linux/spot_shadow_tui.py')
    p=importlib.util.module_from_spec(s);s.loader.exec_module(p);return p


def render(source,python):
    p=module(source);folder=Path(source)/'modules/linux';ident=p.version(folder);base=ROOT/ident
    bridge.require(str(python).startswith('/nix/store/') and all(c.isalnum() or c in '/-._' for c in str(python)),
                   'immutable Python runtime required')
    code=base/'source';vendor=base/'runtime';cli=code/'spot-work-shadow-tui';shadow_id=p.ui.shadow.version(folder)
    cfg=p.settings({'schema':1,'deployment_id':ident,'shadow_deployment_id':shadow_id,
        'store_directory':'/var/lib/spot-work-shadow/'+shadow_id,'source_directory':str(code),'fixture_only':False,
        'session_directory':str(base/'sessions'),'backend':NATIVE,'frontend':str(Path(NATIVE).with_name('kiro-cli')),
        'backend_sha256':p.ui.acp.NATIVE_SHA,'bun':str(vendor/'bun'),'tui':str(vendor/'tui.js'),
        'bun_sha256':p.ui.front.BUN_SHA,'tui_sha256':p.ui.front.BUNDLE_SHA})
    entry='#!'+str(python)+' -I\nimport sys,runpy\nsys.dont_write_bytecode=True\nsys.argv[1:1]='+repr(['--config',str(code/'config.json')])+'\nrunpy.run_path('+repr(str(code/'spot_shadow_tui.py'))+',run_name="__main__")\n'
    return {'id':ident,'directory':str(base),'source_directory':str(code),'vendor_directory':str(vendor),
        'cli':str(cli),'entry':entry,'config':cfg,'artifacts':p.artifacts(code,python,cfg['bun'],cfg['tui']),
        'source_hashes':{n:hashlib.sha256((folder/n).read_bytes()).hexdigest() for n in p.SOURCES},
        'python_store_root':str(Path(python).parent.parent),'native_store_root':str(Path(NATIVE).parent.parent),
        'marker':{'deployment_id':ident,'cli':str(cli),'store_directory':cfg['store_directory'],
                  'shadow_only':True,'termination_capable':False,'consumer_delivery_verified':False,'work_tracking_verified':False}}


def copy_public(source,target,expected,mode):
    # Exact known public software bytes only. A mutable source changing during
    # the copy fails its full digest; preserve the partial attempt, never retry.
    h=hashlib.sha256();fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
    with Path(source).open('rb') as inp,os.fdopen(fd,'wb') as out:
        while data:=inp.read(65536):h.update(data);out.write(data)
        out.flush();os.fsync(out.fileno())
    bridge.require(h.hexdigest()==expected,'vendor software changed; installation incomplete, no fallback/replay')
    os.chmod(target,mode)


def install(source,python,expected_boot,expected_system,bun,tui):
    p=module(source);p.ui.shadow.collector_gate()
    bridge.require(os.geteuid()==0 and Path('/sys/devices/virtual/dmi/id/board_asset_tag').read_text().strip()==bridge.ORIGINAL,
                   'warm deployment only targets original')
    before=bridge.baseline();bridge.require(before['boot']==expected_boot and before['system']==before['profile']==expected_system,
        'original epoch/profile changed')
    bridge.require(json.loads(Path('/etc/spot-schedule-guard.json').read_text()).get('armed') is False,'must remain disarmed')
    plan=render(source,python);bridge.require(not os.path.lexists(MARKER) and not os.path.lexists(plan['directory']),
        'existing/uncertain TUI installation; inspect, never replay/reset')
    store=p.ui.shadow.Store(plan['config']['store_directory']);store.check();binding=p.ui.shadow.protected_observation()
    shadow_marker=p.ui.shadow.read(Path('/etc/spot-work-shadow-current.json'))
    bridge.require(shadow_marker['deployment_id']==plan['config']['shadow_deployment_id']
                   and shadow_marker['status_path']==str(store.root/'status.json'),'existing shadow lineage required; no new seed')
    old={path.name:hashlib.sha256((path/'record.json').read_bytes()).hexdigest() for path in (store.root/'jobs').iterdir()}
    bridge.require(p.ui.acp.binary(NATIVE)==p.ui.acp.NATIVE_SHA,'native changed; no unverified fallback')
    with sqlite3.connect('file:/nix/var/nix/db/db.sqlite?mode=ro',uri=True) as db:
        for path in [plan['python_store_root'],plan['native_store_root']]:
            bridge.require(db.execute('SELECT count(*) FROM ValidPaths WHERE path=?',(path,)).fetchone()[0]==1,'runtime not registered')
    bridge.directory(ROOT,0o755);base=Path(plan['directory']);base.mkdir(mode=0o711)
    code=Path(plan['source_directory']);code.mkdir(mode=0o755);vendor=Path(plan['vendor_directory']);vendor.mkdir(mode=0o755)
    Path(plan['config']['session_directory']).mkdir(mode=0o711)
    bridge.write_new(base/'install-intent.json',json.dumps({'plan':plan,'before':before,'binding':binding,'old_jobs':old},indent=2))
    for name,digest in plan['source_hashes'].items():
        data=(Path(source)/'modules/linux'/name).read_bytes();bridge.require(hashlib.sha256(data).hexdigest()==digest,'source changed')
        bridge.write_new(code/name,data,0o444)
    copy_public(bun,Path(plan['config']['bun']),p.ui.front.BUN_SHA,0o555)
    copy_public(tui,Path(plan['config']['tui']),p.ui.front.BUNDLE_SHA,0o444)
    for name,text in plan['artifacts'].items():bridge.write_new(code/name,text,0o444 if name.endswith('.mjs') else 0o555)
    bridge.write_new(code/'config.json',json.dumps(plan['config'],sort_keys=True),0o444)
    bridge.write_new(plan['cli'],plan['entry'],0o555)
    pins={}
    for kind,target in [('python',plan['python_store_root']),('native',plan['native_store_root'])]:
        pin=bridge.GCROOTS/('spot-work-shadow-tui-'+plan['id']+'-'+kind)
        bridge.require(not os.path.lexists(pin),'foreign runtime pin');pin.symlink_to(target);pins[kind]=str(pin)
    after=bridge.baseline();bridge.require(before==after,'existing workload/epoch/config/OOM state changed')
    current={path.name:hashlib.sha256((path/'record.json').read_bytes()).hexdigest() for path in (store.root/'jobs').iterdir()}
    bridge.require(current==old,'old custody changed; never restore/reset over it')
    bridge.write_new(MARKER,json.dumps(plan['marker'],sort_keys=True))
    receipt={'actual_explicit_NEW_TUI_entry_installed':True,'deployment_id':plan['id'],'cli':plan['cli'],
        'before':before,'after':after,'retained_job_record_hashes':current,'runtime_pins':pins,
        'vendor_software_only_copied':True,'native_or_model_sessions_started_by_install':False,
        'existing_launchers_sessions_or_services_modified':False,'canonical_custody_initialized':False,
        'consumer_delivery_verified':False,'all_producer_tracking_verified':False,'actual_OS_reboot_verified':False,
        'replacement_root_image_updated':False,'armed':False,'goal_complete':False}
    bridge.write_new(base/'install-verified.json',json.dumps(receipt,indent=2));return receipt


def disable(plan):
    bridge.require(os.geteuid()==0 and not MARKER.is_symlink() and json.loads(MARKER.read_text())==plan['marker'],
                   'foreign/Nix-owned discovery marker; no disable')
    MARKER.unlink()
    return {'only_owned_discovery_removed':True,'sessions_keepers_output_source_vendor_and_pins_retained':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['plan','install','disable'])
    parser.add_argument('--source',type=Path,default=HERE.parent);parser.add_argument('--python',default=sys.executable)
    parser.add_argument('--expected-boot');parser.add_argument('--expected-system')
    parser.add_argument('--bun',type=Path,default=Path('/home/sudosubin/.local/share/kiro-cli/bun'))
    parser.add_argument('--tui',type=Path,default=Path('/home/sudosubin/.local/share/kiro-cli/tui.js'));args=parser.parse_args()
    if args.action=='plan':result=render(args.source,args.python)
    elif args.action=='disable':result=disable(render(args.source,args.python))
    else:result=install(args.source,args.python,args.expected_boot,args.expected_system,args.bun,args.tui)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
