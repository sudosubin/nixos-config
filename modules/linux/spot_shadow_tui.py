#!/usr/bin/env python3
"""Explicit NEW tracked TUI, independent resident keeper, never idle authority.

No default launcher replacement, canonical initialization, input replay, TTL,
takeover, output retirement, service stop or implicit finish-input on UI exit.
Normal sessions use an owned 2GiB/one-CPU application cage, NOT build/test
permission. Verification inherits its exact existing private validation budget.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import subprocess
import sys
import threading
import time
import uuid
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).parent))
import spot_shadow_ui as ui
import spot_validation as validation

SOURCES=['spot_work.py','spot_shadow.py','spot_acp.py','spot_shadow_acp.py','spot_frontend.py',
         'spot_shadow_frontend.py','spot_shadow_output.py','spot_shadow_ui.py',
         'spot-kiro-frontend.mjs','spot-shadow-kiro-frontend.mjs','spot_validation.py','spot_shadow_tui.py']
APP_MAX=2*1024**3
APP_MIN=4*1024**3
CGROUP=Path('/sys/fs/cgroup')
UNITS=Path('/run/systemd/system')


def version(folder):
    return hashlib.sha256(''.join(hashlib.sha256((Path(folder)/n).read_bytes()).hexdigest() for n in SOURCES).encode()).hexdigest()[:12]


def artifacts(code,python,bun,tui):
    code=Path(code)
    return {'spot-shadow-front':'#!'+str(python)+' -I\nimport sys;sys.dont_write_bytecode=True;sys.path.insert(0,'+repr(str(code))+');import spot_shadow_frontend as p;p.main()\n',
            'spot-shadow-ui-proxy':'#!'+str(python)+' -I\nimport sys;sys.dont_write_bytecode=True;sys.path.insert(0,'+repr(str(code))+');import spot_shadow_ui as p;p.main()\n',
            'entry.mjs':'import {pathToFileURL} from "node:url";\nimport {installWarmFrontend} from '+json.dumps(str(code/'spot-shadow-kiro-frontend.mjs'))+';\n'
                +'process.env.KIRO_CHAT_CLI_BIN='+json.dumps(str(code/'spot-shadow-ui-proxy'))+';\n'
                +'installWarmFrontend('+json.dumps(str(code/'spot-shadow-front'))+');\n'
                +'process.argv[1]='+json.dumps(str(tui))+';await import(pathToFileURL(process.argv[1]).href);\n'}


def settings(value):
    required={'schema','deployment_id','shadow_deployment_id','store_directory','source_directory','session_directory',
              'backend','frontend','backend_sha256','bun','tui','bun_sha256','tui_sha256','fixture_only'}
    ui.shadow.require(set(value)==required and type(value['schema']) is int and value['schema']==1
        and re.fullmatch('[0-9a-f]{12}',value['deployment_id'])
        and re.fullmatch('[0-9a-f]{12}',value['shadow_deployment_id'])
        and type(value['fixture_only']) is bool
        and (value['store_directory']=='/var/lib/spot-work-shadow/'+value['shadow_deployment_id']
             or value['fixture_only'] and re.fullmatch('/tmp/spotshadowtuifixture-[0-9a-f]{32}/store',value['store_directory']))
        and all(Path(value[n]).is_absolute() for n in ['source_directory','session_directory','backend','frontend','bun','tui'])
        and Path(value['backend']).parent==Path(value['frontend']).parent
        and value['backend'].startswith('/nix/store/') and value['backend'].endswith('/bin/kiro-cli-chat')
        and value['frontend'].endswith('/bin/kiro-cli')
        and value['backend_sha256']==ui.acp.NATIVE_SHA and value['bun_sha256']==ui.front.BUN_SHA
        and value['tui_sha256']==ui.front.BUNDLE_SHA,'unverified TUI configuration')
    return value


def check_config(path):
    ui.shadow.require(os.geteuid()==0,'root-owned new TUI launcher required')
    cfg=settings(ui.shadow.read(path));code=Path(cfg['source_directory'])
    if cfg['fixture_only']:
        budget=validation.current()
        ui.shadow.require(budget and budget['purpose'] in {'verify','canary-verify'},'fixture config has no private verification authority')
    ui.shadow.require(version(code)==cfg['deployment_id'] and ui.shadow.version(code)==cfg['shadow_deployment_id'],
                      'TUI source lineage changed; no fallback')
    ui.shadow.require(ui.acp.binary(cfg['backend'])==cfg['backend_sha256']
        and ui.acp.binary(cfg['bun'])==cfg['bun_sha256'] and ui.acp.binary(cfg['tui'])==cfg['tui_sha256'],
        'pinned native/vendor bytes changed; no fallback')
    ui.shadow.Store(cfg['store_directory']).check()
    return cfg


def arguments(agent):
    ui.shadow.require(isinstance(agent,str) and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,63}',agent),'explicit NEW agent name required')
    return ['--agent',agent]


def current_group():
    raw=Path('/proc/self/cgroup').read_text().strip()
    ui.shadow.require(raw.startswith('0::/') and '\n' not in raw,'unified owned cgroup required')
    return raw[3:]


def app_budget(folder,keeper=False):
    """Applications only; never permits a build or elevates a verify budget."""
    test=validation.current()
    if test is not None:
        ui.shadow.require(test['purpose'] in {'verify','canary-verify'},'TUI fixture cannot use build authority')
        return dict(test,fixture=True)
    value=ui.shadow.read(Path(folder)/'application-budget.json')
    ident=value['id'];name='spotshadowapp'+ident+'.slice'
    unit='spotshadowtui-keeper-'+ident+'.service' if keeper else 'spotshadowapp-client-'+ident+'.service'
    ui.shadow.require(re.fullmatch('[0-9a-f]{32}',ident) and value['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        and current_group()=='/'+name+'/'+unit and value['slice']==name
        and hashlib.sha256((UNITS/name).read_bytes()).hexdigest()==value['definition_sha256'],
        'application budget owner/epoch changed')
    leaf=CGROUP/name;cpu=(leaf/'cpu.max').read_text().split()
    ui.shadow.require((leaf/'memory.max').read_text().strip()==str(APP_MAX)
        and (leaf/'memory.swap.max').read_text().strip()=='0' and (leaf/'memory.oom.group').read_text().strip()=='1'
        and len(cpu)==2 and cpu[0]!='max' and 0<int(cpu[0])<=int(cpu[1])
        and Path('/proc/self/oom_score_adj').read_text().strip()=='1000','application kernel limits unknown')
    return {'slice':name,'cgroup':current_group(),'fixture':False,'memory_max':APP_MAX,
            'external_build_authority':False,'production_idle_verified':False}


def properties(budget):
    return ['--slice='+budget['slice'],'--property=Type=exec','--property=MemoryMax='+str(budget['memory_max']),
            '--property=MemorySwapMax=0','--property=CPUQuota=100%','--property=OOMPolicy=stop',
            '--property=OOMScoreAdjust=1000','--property=Nice=19','--property=NoNewPrivileges=yes',
            '--property=ProtectControlGroups=yes','--property=UMask=0077',
            '--property=PrivateNetwork='+('yes' if budget['fixture'] else 'no')]


def launch_application(cfg,config,folder):
    ui.shadow.require(validation.current() is None,'nested application authority refused')
    ui.shadow.require(validation.available_memory(Path('/proc/meminfo').read_text())>=APP_MIN,
                      'application needs4GiB MemAvailable for separate2GiB cage; no session started')
    ui.shadow.require(os.isatty(0) and os.isatty(1),'interactive cloud TTY required; no session started')
    ident=folder.name;name='spotshadowapp'+ident+'.slice';unit='spotshadowapp-client-'+ident+'.service'
    definition=('[Unit]\nDescription=Explicit new shadow TUI application budget, NOT build authority\nStopWhenUnneeded=yes\n'
                '[Slice]\nMemoryAccounting=yes\nMemoryMax='+str(APP_MAX)+'\nMemorySwapMax=0\nCPUQuota=100%\nIOWeight=10\n').encode()
    validation.write_new(UNITS/name,definition)
    ui.shadow.publish(folder/'application-budget.json',{'schema':1,'id':ident,'slice':name,
        'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'definition_sha256':hashlib.sha256(definition).hexdigest(),'external_build_authority':False},new=True)
    command=['systemd-run','--pty','--wait','--collect','--unit='+unit,*properties({'slice':name,'memory_max':APP_MAX,'fixture':False}),
        sys.executable,'-B','-I','-c',validation.GATE,str(folder/'budget-ready'),ident,
        sys.executable,'-B','-I',str(Path(cfg['source_directory'])/'spot_shadow_tui.py'),'--config',str(config),'client','--session',str(folder)]
    # Exactly one native systemd start. Lost receipt retains manifest/definition;
    # never stop, repeat or reset a possibly accepted application session.
    child=subprocess.Popen(command);deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        pid=subprocess.check_output(['systemctl','show',unit,'-p','MainPID','--value'],text=True).strip()
        if pid.isdecimal() and int(pid)>1:break
        ui.shadow.require(child.poll() is None,'application start outcome unknown; no replay');time.sleep(.05)
    leaf=CGROUP/name;ui.shadow.require(pid.isdecimal() and int(pid)>1 and (leaf/'cgroup.procs').read_text().strip()==''
        and sorted(p.name for p in leaf.iterdir() if p.is_dir())==[unit]
        and (leaf/unit/'cgroup.procs').read_text().split()==[pid], 'fresh application gate contains unknown processes')
    (leaf/'memory.oom.group').write_text('1')
    ui.shadow.require((leaf/'memory.max').read_text().strip()==str(APP_MAX)
        and (leaf/'memory.swap.max').read_text().strip()=='0' and (leaf/'memory.oom.group').read_text().strip()=='1',
        'application fence initialization failed; no user session admitted')
    validation.write_new(folder/'budget-ready',ident.encode())
    # No RuntimeMaxSec, forced deadline, stop/kill or automatic backend EOF.
    return child.wait()


def prepare(cfg,home,agent,*,fixture_env=None):
    ui.shadow.require(os.geteuid()==0,'root launcher required');arguments(agent)
    home=Path(home);st=home.stat();ui.shadow.require(st.st_uid==1001 and home.is_dir() and not st.st_mode&0o022,'owned UID1001 HOME required')
    binding=ui.shadow.protected_observation();ui.shadow.Store(cfg['store_directory']).check()
    if fixture_env is not None:
        budget=validation.current();ui.shadow.require(budget and budget['purpose'] in {'verify','canary-verify'},'fixture env requires private owned verification')
    root=Path(cfg['session_directory']);ui.shadow.require(root.is_dir() and root.stat().st_uid==0 and not root.stat().st_mode&0o022,'session namespace untrusted')
    folder=root/uuid.uuid4().hex;folder.mkdir(mode=0o711)
    # Private controller configuration; never archive actual user sessions.
    ui.shadow.publish(folder/'session.json',{'schema':1,'id':folder.name,'deployment_id':cfg['deployment_id'],
        'home':str(home),'agent':agent,'binding':binding,'fixture_env':fixture_env},new=True)
    return folder


def session(cfg,folder):
    folder=Path(folder);ui.shadow.require(folder.parent==Path(cfg['session_directory']) and re.fullmatch('[0-9a-f]{32}',folder.name),
        'unknown session namespace; no takeover')
    value=ui.shadow.read(folder/'session.json')
    ui.shadow.require(value['id']==folder.name and value['deployment_id']==cfg['deployment_id']
        and value['binding']==ui.shadow.protected_observation(),'session epoch changed; no replay')
    return value


def keeper_unit(folder,budget):
    # Existing validation.current() permits precisely this owned fixture role;
    # a namespace alone never supplies authority or a larger budget.
    return ('spot-resource-validation-'+folder.name[:12] if budget['fixture'] else 'spotshadowtui-keeper-'+folder.name)+'.service'


def scope_members(slice_name):
    rows={}
    for path in (CGROUP/slice_name).rglob('cgroup.procs'):
        for text in path.read_text().split():
            pid=int(text)
            try:rows[pid]={'start':ui.work.process_start(pid),'uid':ui.work.process_uid(pid),
                           'cgroup':str(path.parent.relative_to(CGROUP))}
            except (FileNotFoundError,ProcessLookupError):pass
    return rows


def initializer_members(before,after,client,expected_gate,client_group,keeper_group):
    # Resource admission for THIS fresh owned cage, never server/work idle.
    # A new sibling can make PID1 reset the slice OOM flag. No accepted UID1001
    # work may exist when that sibling is started or while the gate initializes.
    ui.shadow.require(all(row['uid']==0 for row in before.values()) and all(row['uid']==0 for row in after.values()),
                      'live user participant; sibling start/fence reinitialization forbidden')
    for pid,row in after.items():
        original=before.get(pid)
        allowed=original==row or pid==expected_gate and row['cgroup']==keeper_group
        if not allowed:
            allowed=row['cgroup']==client_group and ui.front.frontend.descendant(pid,client)
        ui.shadow.require(allowed,'unknown participant in owned budget initializer')


def initialize_keeper_budget(cfg,folder):
    intent=ui.shadow.read(folder/'keeper-budget-intent.json');budget=intent['budget']
    ui.shadow.require(intent['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        and ui.work.process_start(intent['client_pid'])==intent['client_start']
        and Path('/proc/'+str(intent['client_pid'])+'/cgroup').read_text().strip()=='0::'+budget['cgroup'],
        'budget initializer owner/epoch changed')
    if budget['fixture']:
        owner=validation.trusted_json(validation.RUNTIME/budget['id']/'owner.json')
        ui.shadow.require(owner.get('schema')==2 and owner['id']==budget['id']
            and owner['boot_id']==intent['boot_id'] and owner['slice']==budget['slice']
            and validation.policy(owner['purpose'])[0]==budget['memory_max']
            and owner['driver']=='spot-validation-'+budget['id']+'.service'
            and owner['purpose'] in {'verify','canary-verify'}
            and hashlib.sha256((UNITS/budget['slice']).read_bytes()).hexdigest()==owner['definition_sha256'],
            'verification initializer is not its original owner')
    else:
        owner=ui.shadow.read(folder/'application-budget.json')
        ui.shadow.require(owner['id']==folder.name and budget['memory_max']==APP_MAX
            and owner['boot_id']==intent['boot_id'] and owner['slice']==budget['slice']
            and hashlib.sha256((UNITS/budget['slice']).read_bytes()).hexdigest()==owner['definition_sha256'],
            'application initializer is not its original owner')
    keeper_group=budget['slice']+'/'+keeper_unit(folder,budget)
    ui.shadow.require(current_group()=='/'+keeper_group,'initializer outside its exact new keeper unit')
    before={int(pid):row for pid,row in intent['before_members'].items()}
    after=scope_members(budget['slice'])
    initializer_members(before,after,intent['client_pid'],os.getpid(),budget['cgroup'].lstrip('/'),keeper_group)
    leaf=CGROUP/budget['slice'];cpu=(leaf/'cpu.max').read_text().split()
    ui.shadow.require((leaf/'memory.max').read_text().strip()==str(budget['memory_max'])
        and (leaf/'memory.swap.max').read_text().strip()=='0' and cpu[0]!='max' and 0<int(cpu[0])<=int(cpu[1])
        and Path('/proc/self/oom_score_adj').read_text().strip()=='1000','initializer limits changed')
    (leaf/'memory.oom.group').write_text('1')  # ONLY this ownership-checked empty-of-user-work cage.
    ui.shadow.require((leaf/'memory.oom.group').read_text().strip()=='1','owned OOM fence not confirmed')
    ui.shadow.publish(folder/'keeper-budget-verified.json',{'boot_id':intent['boot_id'],'slice':budget['slice'],
        'gate_pid':os.getpid(),'gate_start':ui.work.process_start(os.getpid()),'memory_max':budget['memory_max'],
        'oom_group':1,'no_UID1001_work_before_or_during_initialization':True,
        'NOT_work_idle_or_build_authority':True},new=True)


def serve(cfg,folder):
    value=session(cfg,folder);budget=app_budget(folder,keeper=True)
    # Fixture service is a sibling within the SAME owned validation slice.
    # Normal resident service must remain within its original application slice.
    ui.shadow.require(current_group()=='/'+budget['slice']+'/'+keeper_unit(folder,budget),
                      'keeper service identity differs; no unbounded standalone serve')
    store=ui.shadow.Store(cfg['store_directory']);extra=arguments(value['agent'])
    keeper=ui.acp.Keeper(store,value['binding'],[cfg['backend'],'acp',*extra],ui.shadow.protected_observation)
    environment=value['fixture_env']
    if environment is not None:ui.shadow.require(budget['fixture'],'no production env override')
    return keeper.serve(ui.acp.drop_command(cfg['backend'],['acp',*extra],value['home'],environment),folder/'keeper.json')


def run_session(cfg,config,folder):
    value=session(cfg,folder);budget=app_budget(folder);store=ui.shadow.Store(cfg['store_directory'])
    ui.shadow.require(not os.path.lexists(folder/'keeper-start-intent.json') and not os.path.lexists(folder/'keeper.json'),
                      'session start previously attempted; no replay or replacement frontend')
    startup=store.create(value['binding'],['explicit NEW TUI startup; parameters omitted'])
    store.update(startup,kind='shadow_tui_startup',state='resident_keeper_start_intent_unknown')
    name=keeper_unit(folder,budget)
    ui.shadow.publish(folder/'keeper-start-intent.json',{'unit':name,'startup':startup['id'],'boot_id':value['binding']['boot_id']},new=True)
    before_members=scope_members(budget['slice'])
    ui.shadow.require(all(row['uid']==0 for row in before_members.values()),
                      'live user participant; cannot start sibling that may reset owned OOM fence')
    ui.shadow.publish(folder/'keeper-budget-intent.json',{'budget':budget,'boot_id':value['binding']['boot_id'],
        'client_pid':os.getpid(),'client_start':ui.work.process_start(os.getpid()),'before_members':before_members},new=True)
    keeper_properties=[prop for prop in properties(budget) if prop!='--property=ProtectControlGroups=yes']
    command=['systemd-run','--quiet','--collect','--unit='+name,*keeper_properties,'--property=ProtectControlGroups=no',
        '--property=KillMode=process','--property=TimeoutStopSec=infinity',
        sys.executable,'-B','-I',str(Path(cfg['source_directory'])/'spot_shadow_tui.py'),'--config',str(config),'serve','--session',str(folder)]
    ui.shadow.require(subprocess.check_output(['systemctl','show',name,'-p','LoadState','--value'],text=True).strip()=='not-found',
                      'foreign/partial keeper unit; no start replay')
    subprocess.run(command,check=True,capture_output=True,text=True)
    deadline=time.monotonic()+20
    while not (folder/'keeper.json').exists() and time.monotonic()<deadline:time.sleep(.02)
    ui.shadow.require((folder/'keeper.json').exists(),'keeper start outcome unknown; inspect intent, never replay')
    d=ui.shadow.read(folder/'keeper.json');code=Path(cfg['source_directory']);broker=ui.Broker(store,value['binding'],startup,d,
        code/'entry.mjs',current_group(),value['home'],cfg['backend'],
        {'frontend':code/'spot-shadow-front','proxy':code/'spot-shadow-ui-proxy'},value['fixture_env'])
    broker.open(folder/'broker.sock')
    extra=arguments(value['agent']);env={'PATH':str(Path(cfg['bun']).parent)+':'+str(Path(cfg['backend']).parent)+':/run/current-system/sw/bin',
        'TERM':os.environ.get('TERM','xterm-256color'),'KIRO_TEST_TUI_JS_PATH':str(code/'entry.mjs'),
        'SPOT_KIRO_STARTUP':startup['id'],'SPOT_SHADOW_TUI_ENDPOINT':str(folder/'broker.sock'),
        'KIRO_CHAT_CLI_BIN':cfg['backend']}
    if value['fixture_env'] is not None:env.update(value['fixture_env'])
    child=subprocess.Popen(ui.acp.drop_command(cfg['frontend'],['chat','--tui','--agent-engine','v2',*extra],value['home'],env))
    broker.ancestor=child.pid
    thread=threading.Thread(target=broker.serve,daemon=True);thread.start()
    ui.shadow.publish(folder/'frontend.json',{'startup':startup['id'],'pid':child.pid,'pid_start':ui.work.process_start(child.pid),
                      'cgroup':current_group(),'keeper':d,'consumer_delivery':'unverified'},new=True)
    try:return child.wait()
    finally:
        broker.close();thread.join(timeout=2)
        # Consumer loss/exit never means provider EOF, cancellation or delivery.
        # Resident keeper/source/records/output are left intact and protected.


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('action',choices=['launch','client','serve','finish-input']);parser.add_argument('--home',type=Path)
    parser.add_argument('--agent',default='kiro_default');parser.add_argument('--session',type=Path);args=parser.parse_args()
    if args.action=='serve':
        # All code/config remain root-owned. Initialize the exact owned sibling
        # gate BEFORE any native effect or v.current() readiness assertion.
        ui.shadow.require(args.session is not None,'exact owned session required')
        preliminary=settings(ui.shadow.read(args.config))
        ui.shadow.require(version(preliminary['source_directory'])==preliminary['deployment_id'],'initializer source changed')
        ui.shadow.require(args.session.parent==Path(preliminary['session_directory']),'foreign initializer session')
        initialize_keeper_budget(preliminary,args.session)
    cfg=check_config(args.config)
    if args.action=='launch':
        folder=prepare(cfg,args.home or Path(pwd.getpwuid(1001).pw_dir),args.agent)
        if validation.current() is None:result=launch_application(cfg,args.config,folder)
        else:result=run_session(cfg,args.config,folder)
    else:
        ui.shadow.require(args.session is not None,'exact owned session required')
        if args.action=='client':result=run_session(cfg,args.config,args.session)
        elif args.action=='serve':result=serve(cfg,args.session)
        else:
            value=session(cfg,args.session);d=ui.shadow.read(args.session/'keeper.json')
            ui.shadow.require(d['boot_id']==value['binding']['boot_id'] and ui.work.process_start(d['pid'])==d['pid_start'],
                              'keeper owner changed; no finish/replay')
            print(json.dumps(ui.rpc(d['socket'],{'op':'finish-input'})));return
    sys.exit(result)


if __name__=='__main__':
    try:main()
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError):
        print('New TUI outcome unknown/admission refused; inspect retained intent, no replay or forced cleanup',file=sys.stderr);sys.exit(75)
