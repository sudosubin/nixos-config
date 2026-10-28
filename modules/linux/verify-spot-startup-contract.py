#!/usr/bin/env python3
"""Inspect evaluated startup declarations. NOT OS boot, AWS/EBS, or HM/app proof.

Run in the existing verification cage. Never loads/restarts a unit, imports a
store archive, calls AWS, changes a profile, or grants arming/work authority.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import types


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(value, message):
    if not value:
        raise RuntimeError(message)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--expected-source',type=Path,required=True)
    parser.add_argument('--contract',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    check(sys.platform=='linux' and os.geteuid()==0,'root Linux verification required')
    fd=os.open(args.expected_source,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd) as stream:
        st=os.fstat(stream.fileno())
        check(stat.S_ISREG(st.st_mode) and st.st_uid==0 and not st.st_mode&0o022 and st.st_size<=1048576,'untrusted source map')
        expected=json.load(stream)
    root=args.source.resolve(strict=True)
    check(isinstance(expected,dict) and bool(expected),'empty source map')
    for name,value in expected.items():
        p=Path(name)
        check(not p.is_absolute() and '..' not in p.parts and re.fullmatch(r'[0-9a-f]{64}',value) is not None,'invalid source identity')
        check(sha(root/name)==value,'source bytes changed: '+name)
    check(Path(__file__).read_bytes()==(root/'modules/linux/verify-spot-startup-contract.py').read_bytes(),'executed inspector differs')
    resource=root/'modules/linux/spot_validation.py'
    check(sha(resource)==expected['modules/linux/spot_validation.py'],'resource code differs')
    validation=types.ModuleType('spot_validation');exec(compile(resource.read_bytes(),str(resource),'exec'),validation.__dict__)
    budget=validation.current()
    check(budget is not None and budget['purpose'] in {'verify','canary-verify'},'a verified test cage is required, not a build budget')
    validation.memory_gate(budget['purpose'])
    directory=args.contract.resolve(strict=True)
    check(re.fullmatch(r'/nix/store/[0-9a-df-np-sv-z]{32}-spot-startup-contract',str(directory)) is not None,'not the declared immutable contract')
    data=json.loads((directory/'contract.json').read_text());checks=[]
    check(data['schema']==1 and data['minimal_module_evaluation'] is True and data['actual_HM_activation_or_OS_boot_verified'] is False,'scope is not the minimal declaration proof')
    check(data['production_armed'] is False,'contract must remain disarmed')
    for name,value in data['module_sha256'].items():
        check(value==expected['modules/linux/'+name],'evaluated declaration source differs: '+name)
    check(len(data['module_sha256'])==6,'incomplete declaration source binding');checks.append('six_actual_declaration_module_hashes')
    tool=(directory/'spot-work/bin/spot-work').resolve(strict=True);script=tool.read_text()
    check(script.splitlines()[0].endswith('/bin/python3 -I'),'CLI is not direct isolated Python')
    target=re.findall(r'runpy\.run_path\("(/nix/store/[^"/]+-spot_work\.py)"',script)
    check(len(target)==1 and sha(Path(target[0]))==expected['modules/linux/spot_work.py'],'declared CLI module differs')
    tool_path=str(tool);checks.append('actual_declared_immutable_CLI')
    services=data['services'];gate='spot-workload-startup-ready.service'
    def deps(name,required):
        check(set(required)<=set(services[name]['requires']) and set(required)<=set(services[name]['after']),'missing hard ordering for '+name)
    def commands(name,field):
        value=services[name]['serviceConfig'].get(field,[])
        return [value] if isinstance(value,str) else value
    for name in ['user@1001','docker','home-manager-sudosubin']:
        deps(name,[gate,'home.mount' if name!='home-manager-sudosubin' else 'spot-profile-cache-restore.service'])
        check(commands(name,'ExecCondition')==[tool_path+' check-service-open '+name+'.service'],'missing non-ignoring startup condition for '+name)
    check(services['user@1001']['overrideStrategy']=='asDropin','user manager must augment its template');checks.append('hard_workload_dependencies_and_conditions')
    gate_unit=services['spot-workload-startup-ready']
    deps('spot-workload-startup-ready',['spot-work-admission-ready.service','spot-scale-in-protection-ready.service','home.mount','spot-profile-cache-restore.service'])
    check({'user@1001.service','docker.service','home-manager-sudosubin.service'}<=set(gate_unit['before']),'startup preflight must precede workloads')
    sc=gate_unit['serviceConfig']
    check(sc['Type']=='oneshot' and sc['RemainAfterExit'] is True and sc['TimeoutStartSec']=='infinity','invalid startup coordinator lifetime')
    check(sc['StateDirectory']=='spot-schedule-guard' and sc['StateDirectoryMode']=='0700','startup journal not root private')
    check(len(commands('spot-workload-startup-ready','ExecStart'))==1 and commands('spot-workload-startup-ready','ExecStart')[0].endswith('/bin/spot-schedule-guard --startup-only'),'preflight is not startup-only');checks.append('preflight_protection_home_restore_order')
    check(commands('spot-work-admission-ready','ExecStart')==[tool_path+' initialize'],'boot initialization has a bypass or wrong CLI')
    deps('spot-scale-in-protection-ready',['spot-work-admission-ready.service'])
    deps('attach-home-volume',['spot-scale-in-protection-ready.service'])
    check('home.mount' in services['attach-home-volume']['before'],'attach does not precede mount');checks.append('initialization_protection_attachment_order')
    for name in ['nix-gc','nix-optimise','docker-prune']:
        deps(name,['spot-work-admission-ready.service',gate])
        check(commands(name,'ExecCondition')==[tool_path+' check-open'],'maintenance bypasses admission: '+name)
    checks.append('maintenance_stays_gated')
    deps('spot-profile-cache-restore',['home.mount'])
    check({'user@1001.service','docker.service'}<=set(services['spot-profile-cache-restore']['before']),'profile restoration order lost')
    checks.append('profile_restoration_before_user_and_Docker')
    forbidden={'home.mount',gate,'spot-profile-cache-restore.service','spot-work-admission-ready.service'}
    check(not forbidden.intersection(services['amazon-ssm-agent']['requires']+services['amazon-ssm-agent']['after']),'SSM recovery depends on the failing home/work gate')
    check(gate not in services['spot-schedule-guard']['requires'],'recovery must not require its own workload preflight')
    checks.append('SSM_and_recovery_independent_of_workload_failure')
    check(data['home']['fsType']=='ext4' and data['home']['device'].startswith('/dev/disk/by-uuid/') and 'nofail' in data['home']['options'],'unexpected home declaration')
    checks.append('explicit_home_uuid_no_root_fallback')
    graph={name+'.service':set() for name in services};graph['home.mount']=set()
    for name,unit in services.items():
        key=name+'.service';graph[key].update(x for x in unit['after']+unit['requires'] if x in graph)
        for target_name in unit['before']:
            if target_name in graph:graph[target_name].add(key)
    active=set();done=set()
    def visit(node):
        check(node not in active,'startup dependency cycle: '+node)
        if node in done:return
        active.add(node)
        for dependency in graph[node]:visit(dependency)
        active.remove(node);done.add(node)
    for name in graph:visit(name)
    checks.append('selected_evaluated_startup_graph_acyclic')
    result={'schema':1,'checks_passed':checks,'actual_check_count':len(checks),'contract':str(directory),'contract_sha256':sha(directory/'contract.json'),
            'CLI_sha256':sha(tool),'CLI_source_sha256':sha(Path(target[0])),'declaration_sha256':data['module_sha256'],'resource_budget':budget,
            'scope':'minimal NixOS evaluation of actual startup modules plus fake HM activation, NOT full production configuration or OS/AWS/EBS boot',
            'all_passed':True,'OS_boot_verified':False,'full_regression_verified':False,'production_rollout':False,'work_tracking_verified':False,'armed':False,'goal_complete':False}
    st=args.output.parent.stat();check(st.st_uid==0 and not st.st_mode&0o022,'untrusted result directory')
    fd=os.open(args.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as stream:json.dump(result,stream,indent=2);stream.flush();os.fsync(stream.fileno())
    fd=os.open(args.output.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
