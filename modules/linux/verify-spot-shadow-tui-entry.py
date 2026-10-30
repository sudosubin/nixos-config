#!/usr/bin/env python3
"""Actual NEW entry + independent PID1 keeper; synthetic fixtures only.

--installed tests the installed bytes/store, never changes any old record.
No actual keys/models/network or host app/service restarts. Root fixture client
loss is fault injection, NOT keeper takeover, UI recovery or delivery evidence.
"""
import argparse
import base64
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import pty
import re
import select
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
import uuid
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).parent))
import spot_validation as validation

NATIVE=Path('/nix/store/bn6yjl0rgrd0yqxk3cbkkamjcxg9h47x-kiro-cli-2.10.0/bin/kiro-cli-chat')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--installed',action='store_true');args=parser.parse_args()
    budget=validation.current()
    if not budget or budget['purpose'] not in {'verify','canary-verify'}:raise RuntimeError('exact private verification budget required')
    args.evidence.mkdir(mode=0o700)
    if args.installed:
        marker=json.loads(Path('/etc/spot-work-shadow-tui-current.json').read_text());code=Path(marker['cli']).parent
    else:code=Path(__file__).parent
    sys.path.insert(0,str(code));import spot_shadow_tui as p
    base=Path('/tmp/stui-'+uuid.uuid4().hex);base.mkdir(mode=0o755)
    if args.installed:
        config=code/'config.json';cfg=p.check_config(config)
        p.ui.shadow.require(cfg['deployment_id']==marker['deployment_id'],'installed marker/source mismatch')
    else:
        source=base/'source';source.mkdir(mode=0o755);vendor=base/'runtime';vendor.mkdir(mode=0o755)
        for name in p.SOURCES:shutil.copyfile(code/name,source/name);(source/name).chmod(0o444)
        for name,expected in [('bun',p.ui.front.BUN_SHA),('tui.js',p.ui.front.BUNDLE_SHA)]:
            target=vendor/name;h=hashlib.sha256()
            with Path('/home/sudosubin/.local/share/kiro-cli',name).open('rb') as inp,target.open('xb') as out:
                while data:=inp.read(65536):h.update(data);out.write(data)
            p.ui.shadow.require(h.hexdigest()==expected,'public vendor bytes changed');target.chmod(0o555 if name=='bun' else 0o444)
        (base/'sessions').mkdir(mode=0o711);(base/'store').mkdir(mode=0o700)
        p.ui.shadow.Store(base/'store').initialize(p.ui.shadow.protected_observation())
        cfg={'schema':1,'deployment_id':p.version(source),'shadow_deployment_id':p.ui.shadow.version(source),
             'store_directory':str(base/'store'),'source_directory':str(source),'session_directory':str(base/'sessions'),
             'backend':str(NATIVE),'frontend':str(NATIVE.with_name('kiro-cli')),'backend_sha256':p.ui.acp.NATIVE_SHA,
             'bun':str(vendor/'bun'),'tui':str(vendor/'tui.js'),'bun_sha256':p.ui.front.BUN_SHA,
             'tui_sha256':p.ui.front.BUNDLE_SHA,'fixture_only':True}
        for name,text in p.artifacts(source,sys.executable,cfg['bun'],cfg['tui']).items():
            (source/name).write_text(text);(source/name).chmod(0o444 if name.endswith('.mjs') else 0o555)
        config=source/'config.json';p.ui.shadow.publish(config,cfg,new=True);code=source
    store=p.ui.shadow.Store(cfg['store_directory'])
    old={path.name:hashlib.sha256((path/'record.json').read_bytes()).hexdigest() for path in (store.root/'jobs').iterdir()}
    cases=[];folders=[]
    try:
        for case in ['queue','client-loss']:
            home=base/('home-'+case);home.mkdir(mode=0o700);gid=pwd.getpwuid(1001).pw_gid;os.chown(home,1001,gid)
            for name in ['.runtime','.kiro/agents','.kiro/settings']:(home/name).mkdir(parents=True,exist_ok=True)
            for path in home.rglob('*'):os.chown(path,1001,gid)
            agent=home/'.kiro/agents/spot-canary.json';agent.write_text(json.dumps({'name':'spot-canary','description':'ONLY private entry proof','tools':[],'allowedTools':[],'resources':[],'mcpServers':{},'hooks':{}}));agent.chmod(0o644)
            (home/'fixture-attachment.txt').write_text('ONLY_SYNTHETIC_ENTRY_ATTACHMENT\n')
            mock=base/('mock-'+case+'.json');mock.write_text(json.dumps([['ENTRY_FIRST_MOCK_OUTPUT'],['ENTRY_QUEUE_MOCK_OUTPUT'],['MUST_NOT_REPLAY_MODEL']]))
            environment={'KIRO_API_KEY':'test-only-nonfunctional-no-network-key','KIRO_MOCK_CHAT_RESPONSE':str(mock),
                         'PATH':str(Path(cfg['bun']).parent)+':'+str(NATIVE.parent)+':/run/current-system/sw/bin','TERM':'xterm-256color'}
            folder=p.prepare(cfg,home,'spot-canary',fixture_env=environment);folders.append(folder)
            master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',40,120,0,0))
            gate='import os,sys,fcntl,termios;fcntl.ioctl(0,termios.TIOCSCTTY,0);os.execv(sys.argv[1],sys.argv[1:])'
            client=subprocess.Popen([sys.executable,'-B','-I','-c',gate,sys.executable,'-B','-I',str(code/'spot_shadow_tui.py'),
                 '--config',str(config),'client','--session',str(folder)],stdin=slave,stdout=slave,stderr=slave,start_new_session=True)
            client_start=p.ui.work.process_start(client.pid);os.close(slave);console=bytearray();paused=None;d=None;done=False
            def read_console():
                while select.select([master],[],[],0)[0]:
                    try:data=os.read(master,65536)
                    except OSError:break
                    if not data:break
                    console.extend(data)
                    if b'\x1b[6n' in data:os.write(master,b'\x1b[1;1R')
                    p.ui.shadow.require(len(console)<2*1024**2,'fixture console bound exceeded')
                return re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]',b'',bytes(console))
            def wait(predicate,label,seconds=35,alive=True):
                deadline=time.monotonic()+seconds
                while time.monotonic()<deadline:
                    read_console()
                    if predicate():return
                    if alive:p.ui.shadow.require(client.poll() is None,'fixture client exited before '+label)
                    time.sleep(.02)
                raise RuntimeError('entry fixture condition missing: '+label)
            def records():
                return [p.ui.shadow.read(path/'record.json') for path in (store.root/'jobs').iterdir() if path.name not in old]
            def front():
                for value in records():
                    if value.get('kind')=='shadow_kiro_frontend' and value.get('parent_startup')==startup:return value
                return {}
            def owned_fd(pid,start,uid,group):
                def check():
                    p.ui.shadow.require(p.ui.work.process_start(pid)==start and p.ui.work.process_uid(pid)==uid
                        and Path('/proc/'+str(pid)+'/cgroup').read_text().strip()=='0::'+group
                        and Path('/proc/'+str(pid)+'/ns/pid').stat().st_ino==Path('/proc/self/ns/pid').stat().st_ino,'not exact owned fixture process')
                check();fd=os.pidfd_open(pid,0)
                try:check()
                except BaseException:os.close(fd);raise
                return fd
            try:
                wait(lambda:(folder/'frontend.json').exists(),'resident descriptor and frontend binding')
                descriptor=p.ui.shadow.read(folder/'frontend.json');startup=descriptor['startup'];d=descriptor['keeper'];keeper_group='/'+budget['slice']+'/'+p.keeper_unit(folder,{'fixture':True})
                p.ui.shadow.require(Path('/proc/'+str(d['pid'])+'/cgroup').read_text().strip()=='0::'+keeper_group,
                                    'keeper escaped exact owned parent budget')
                wait(lambda:front().get('initialized') is True,'installed real TUI initialized')
                os.write(master,b'@fixture-attachment');wait(lambda:b'fixture-attachment.txt' in read_console(),'actual @ picker')
                time.sleep(.6);os.write(master,b'\r')
                wait(lambda:re.search(rb'fixture-attachment\.txt\s+2 lines',read_console()) is not None,'actual file-only chip')
                p.ui.shadow.require(front()['counters']['draft'] is True,'file-only draft not tracked')
                native=p.ui.shadow.read(store.job(d['session'])/'record.json');pid=native['backend_pid'];start=native['backend_start']
                p.ui.shadow.require(os.getpgid(pid)==pid,'mock backend process group changed')
                fd=owned_fd(pid,start,1001,keeper_group);signal.pidfd_send_signal(fd,signal.SIGSTOP,None,0);paused=fd
                os.write(master,b' ONLY synthetic entry prompt.\r')
                def pending():return any(v.get('parent_session')==d['session'] and v.get('provider_terminal_observed') is False for v in records())
                wait(pending,'leased accepted request')
                if case=='queue':
                    os.write(master,b'\x13');wait(lambda:b'Switched to Queue mode' in read_console(),'actual queue mode')
                    os.write(master,b'ONLY accepted entry queue');wait(lambda:front().get('counters',{}).get('draft') is True,'queued draft')
                    os.write(master,b'\r');wait(lambda:front()['counters']['queued']==1,'accepted queue')
                    signal.pidfd_send_signal(fd,signal.SIGCONT,None,0);os.close(fd);paused=None
                    wait(lambda:b'ENTRY_QUEUE_MOCK_OUTPUT' in read_console(),'two actual PTY mock replies')
                    def complete_parse_prefix():
                        record=p.ui.shadow.read(store.job(d['session'])/'record.json')
                        count=record.get('output_segments',0);stdout=0
                        for number in range(count):
                            try:row=p.ui.acp.Segments.read(store.job(d['session'])/'output',number)
                            except FileNotFoundError:return False
                            if row['channel']=='stdout':stdout+=1
                        state=front();counters=state.get('counters',{})
                        return stdout>8 and state.get('parsed_output_count')==stdout and counters.get('processing') is False and counters.get('actions')==0
                    wait(complete_parse_prefix,'ALL new model stdout parsed and local actions complete, not first-turn prefix')
                else:
                    fd_client=owned_fd(client.pid,client_start,0,budget['cgroup'])
                    try:
                        signal.pidfd_send_signal(fd_client,signal.SIGKILL,None,0)
                        wait(lambda:bool(select.select([fd_client],[],[],0)[0]),'exact client pidfd exit',alive=False)
                    finally:os.close(fd_client)
                    client.wait(timeout=5)
                    p.ui.shadow.require(p.ui.work.process_start(d['pid'])==d['pid_start'] and pending(),'client death lost keeper or work')
                    signal.pidfd_send_signal(fd,signal.SIGCONT,None,0);os.close(fd);paused=None
                    rows=[]
                    def late():
                        while True:
                            row=p.ui.rpc(d['socket'],{'op':'read','sequence':len(rows)}).get('segment')
                            if row is None:break
                            rows.append(row)
                        return b'ENTRY_FIRST_MOCK_OUTPUT' in b''.join(base64.b64decode(row['data_base64']) for row in rows) and not pending()
                    wait(late,'independent PID1 keeper late output after whole client loss',alive=False)
                p.ui.shadow.require(p.ui.work.process_start(d['pid'])==d['pid_start'],'resident keeper not alive after consumer work')
                p.ui.rpc(d['socket'],{'op':'finish-input'})  # Explicit fixture finish, not implicit UI exit.
                wait(lambda:p.ui.shadow.read(store.job(d['session'])/'record.json').get('state')=='backend_and_local_children_reaped_output_pending',
                     'natural keeper finish',alive=False)
                wait(lambda:(folder/'keeper-metadata-hold.json').exists(),
                     'native reaped; only trusted metadata holder remains',alive=False)
                p.ui.shadow.require(p.ui.work.process_start(d['pid'])==d['pid_start'],
                                    'metadata holder must keep budget stable while frontends exist')
                done=True;cases.append({'case':case,'resident_keeper_unit':p.keeper_unit(folder,{'fixture':True}),
                    'keeper_group':keeper_group,'client_group':budget['cgroup'],'session_folder':str(folder),'frontend':front(),
                    'consumer_or_root_read_is_NOT_delivery':True,'all_work_idle':False})
            finally:
                if paused is not None:
                    try:signal.pidfd_send_signal(paused,signal.SIGCONT,None,0)
                    except ProcessLookupError:pass
                    os.close(paused)
                # Only the NEW synthetic controller/actor, never host work.
                actor=front().get('actor') if 'startup' in locals() else None
                if actor:
                    try:
                        fd=owned_fd(actor['pid'],actor['pid_start'],1001,budget['cgroup'])
                        try:signal.pidfd_send_signal(fd,signal.SIGTERM,None,0)
                        finally:os.close(fd)
                    except (FileNotFoundError,ProcessLookupError):pass
                if client.poll() is None:client.terminate();client.wait(timeout=5)
                if d and not done:
                    try:p.ui.rpc(d['socket'],{'op':'finish-input'})
                    except (OSError,ValueError,RuntimeError):pass
                if done:
                    wait(lambda:all(row['uid']==0 for row in p.scope_members(budget['slice']).values()),
                         'all owned synthetic user processes ended before another empty gate',alive=False)
                os.close(master);(args.evidence/(case+'-full-pty.bin')).write_bytes(console)
        current={path.name:hashlib.sha256((path/'record.json').read_bytes()).hexdigest() for path in (store.root/'jobs').iterdir() if path.name in old}
        p.ui.shadow.require(current==old,'old records changed; never reset over them')
        proof={'installed_path':args.installed,'deployment_id':cfg['deployment_id'],'config':str(config),'fixture_base':str(base),
            'metadata_holders_retained_until_own_driver_and_frontends_exit':True,'actual_cases':cases,
            'old_records_preserved':old,'new_records':sorted(path.name for path in (store.root/'jobs').iterdir() if path.name not in old),
            'all_passed':True,'consumer_delivery_verified':False,'work_tracking_verified':False,'armed':False,'goal_complete':False}
        p.ui.shadow.publish(args.evidence/'proof.json',proof,new=True)
    finally:
        snapshot={'fixture_only':True,'installed_path':args.installed,'records':{}}
        for path in (store.root/'jobs').rglob('*'):
            if not path.is_file() or path.is_symlink() or path.parts[len(store.root.parts)+1] in old or path.name=='lock':continue
            data=path.read_bytes();p.ui.shadow.require(len(data)<=2*1024**2,'fixture body bound exceeded')
            snapshot['records'][str(path.relative_to(store.root))]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'body_base64':base64.b64encode(data).decode()}
        for folder in folders:
            for name in ['session.json','keeper.json','frontend.json','keeper-start-intent.json','keeper-budget-intent.json','keeper-budget-verified.json',
                         'keeper-initialize-release.json','keeper-unit-verified.json','keeper-metadata-hold.json','metadata-collected.json',*[path.name for path in folder.glob('controller-error-*.json')]]:
                path=folder/name
                if path.exists():
                    data=path.read_bytes();snapshot['records']['sessions/'+folder.name+'/'+name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'body_base64':base64.b64encode(data).decode()}
        p.ui.shadow.publish(args.evidence/'complete-owned-fixture-snapshot.json',snapshot,new=True)
        # Keep service/session evidence on a failure. Remove only unused public
        # copies/fake homes AFTER all synthetic fixture services ended naturally.
        # Root metadata holders are intentionally still present. The external
        # owned coordinator collects them ONLY after this driver exits; preserve
        # their exact config/close paths, source and all output until then.


if __name__=='__main__':main()
