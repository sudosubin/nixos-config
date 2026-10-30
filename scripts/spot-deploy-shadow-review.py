#!/usr/bin/env python3
"""Install ONLY an explicit read-only output recovery console, no session start.

Existing TUI/ACP/observer/collector/code/data/GC roots and discovery remain intact.
Never initializes a review namespace, canonical state or delivery/idle authority.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
s=importlib.util.spec_from_file_location('shared_review_deploy',Path(__file__).with_name('spot-deploy-observer.py'))
bridge=importlib.util.module_from_spec(s);s.loader.exec_module(bridge)
ROOT=Path('/var/lib/spot-output-review');MARKER=Path('/etc/spot-output-review-current.json')


def module(source):
    s=importlib.util.spec_from_file_location('review_deploy_runtime',Path(source)/'modules/linux/spot_shadow_review.py')
    p=importlib.util.module_from_spec(s);s.loader.exec_module(p);return p


def render(source,python):
    p=module(source);folder=Path(source)/'modules/linux';ident=p.version(folder);base=ROOT/ident;code=base/'source'
    bridge.require(str(python).startswith('/nix/store/') and all(c.isalnum() or c in '/-._' for c in str(python)),
                   'immutable isolated interpreter required')
    shadow=p.shadow.version(folder);store='/var/lib/spot-work-shadow/'+shadow;cli=code/'spot-output-review'
    entry='#!'+str(python)+' -I\nimport sys,runpy\nsys.dont_write_bytecode=True\nsys.argv[1:1]='+repr([
        '--expected-version',ident,'--store',store])+'\nrunpy.run_path('+repr(str(code/'spot_shadow_review.py'))+',run_name="__main__")\n'
    marker={'deployment_id':ident,'cli':str(cli),'store_directory':store,'readonly_output_only':True,
            'consumer_delivery_verified':False,'work_tracking_verified':False,'termination_capable':False}
    return {'id':ident,'directory':str(base),'source_directory':str(code),'cli':str(cli),'entry':entry,'marker':marker,
            'source_hashes':{name:hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in p.SOURCES},
            'python_store_root':str(Path(python).parent.parent),'shadow_id':shadow}


def install(source,python,expected_boot,expected_system):
    p=module(source);p.shadow.collector_gate();before=bridge.baseline()
    bridge.require(os.geteuid()==0 and Path('/sys/devices/virtual/dmi/id/board_asset_tag').read_text().strip()==bridge.ORIGINAL
        and before['boot']==expected_boot and before['system']==before['profile']==expected_system,'original epoch changed')
    bridge.require(json.loads(Path('/etc/spot-schedule-guard.json').read_text()).get('armed') is False,'must remain disarmed')
    plan=render(source,python);bridge.require(not os.path.lexists(MARKER) and not os.path.lexists(plan['directory']),
                                          'existing/uncertain review deployment; no replay/reset')
    marker=p.shadow.read(Path('/etc/spot-work-shadow-current.json'));bridge.require(marker['deployment_id']==plan['shadow_id'],
                                                                                 'existing shadow lineage required')
    store=p.shadow.Store(plan['marker']['store_directory']);store.check()
    old={path.name:hashlib.sha256((path/'record.json').read_bytes()).hexdigest() for path in (store.root/'jobs').iterdir()}
    tui=Path('/etc/spot-work-shadow-tui-current.json');old_tui=hashlib.sha256(tui.read_bytes()).hexdigest()
    with sqlite3.connect('file:/nix/var/nix/db/db.sqlite?mode=ro',uri=True) as db:
        bridge.require(db.execute('SELECT count(*) FROM ValidPaths WHERE path=?',(plan['python_store_root'],)).fetchone()[0]==1,
                       'unregistered interpreter')
    bridge.directory(ROOT,0o755);base=Path(plan['directory']);base.mkdir(mode=0o755);code=Path(plan['source_directory']);code.mkdir(mode=0o755)
    bridge.write_new(base/'install-intent.json',json.dumps({'plan':plan,'before':before,'old_records':old,'old_TUI_marker_SHA':old_tui},indent=2))
    for name,digest in plan['source_hashes'].items():
        data=(Path(source)/'modules/linux'/name).read_bytes();bridge.require(hashlib.sha256(data).hexdigest()==digest,'source changed')
        bridge.write_new(code/name,data,0o444)
    bridge.write_new(plan['cli'],plan['entry'],0o555)
    pin=bridge.GCROOTS/('spot-output-review-'+plan['id']+'-python');bridge.require(not os.path.lexists(pin),'foreign interpreter pin')
    pin.symlink_to(plan['python_store_root'])
    after=bridge.baseline();bridge.require(before==after and hashlib.sha256(tui.read_bytes()).hexdigest()==old_tui,'old runtime changed')
    bridge.require({path.name:hashlib.sha256((path/'record.json').read_bytes()).hexdigest() for path in (store.root/'jobs').iterdir()}==old,
                   'old custody changed; no reset')
    bridge.write_new(MARKER,json.dumps(plan['marker'],sort_keys=True))
    value={'explicit_readonly_output_review_installed':True,'deployment_id':plan['id'],'cli':plan['cli'],
           'before':before,'after':after,'retained_old_records':old,'old_TUI_marker_SHA':old_tui,
           'review_namespaces_or_model_sessions_started_by_install':False,'old_services_or_launchers_modified':False,
           'trusted_delivery_verified':False,'armed':False,'goal_complete':False}
    bridge.write_new(base/'install-verified.json',json.dumps(value,indent=2));return value


def disable(plan):
    bridge.require(os.geteuid()==0 and not MARKER.is_symlink() and json.loads(MARKER.read_text())==plan['marker'],
                   'foreign or Nix-owned review marker; no disable')
    MARKER.unlink();return {'only_discovery_removed':True,'all_data_code_views_pins_retained':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['plan','install','disable'])
    parser.add_argument('--source',type=Path,default=Path(__file__).parent.parent);parser.add_argument('--python',default=sys.executable)
    parser.add_argument('--expected-boot');parser.add_argument('--expected-system');args=parser.parse_args()
    value=render(args.source,args.python) if args.action=='plan' else disable(render(args.source,args.python)) if args.action=='disable' else install(
        args.source,args.python,args.expected_boot,args.expected_system)
    print(json.dumps(value,indent=2))


if __name__=='__main__':main()
