#!/usr/bin/env python3
"""Private actual pinned Bun/native TUI test, NEW synthetic actors only.

No production UI activation. No canonical admission/ready state. Existing real
home/keys/services/model work are never restarted or signalled. Test-only owned
backend uses stable pidfd pause/resume; model output is mocked without network.
"""
import argparse
import base64
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pty
import pwd
import re
import select
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import threading
import time
sys.path.insert(0,str(Path(__file__).parent))
import spot_validation as validation
import spot_shadow_ui as ui

PUBLIC_FILES=['spot_work.py','spot_shadow.py','spot_acp.py','spot_shadow_acp.py','spot_frontend.py',
              'spot_shadow_frontend.py','spot_shadow_ui.py','spot_shadow_output.py','spot-kiro-frontend.mjs','spot-shadow-kiro-frontend.mjs']
NATIVE_ROOT=Path('/nix/store/bn6yjl0rgrd0yqxk3cbkkamjcxg9h47x-kiro-cli-2.10.0/bin')


def copy_verified(source,target,expected):
    h=hashlib.sha256()
    with Path(source).open('rb') as inp,Path(target).open('xb') as out:
        while data:=inp.read(65536):h.update(data);out.write(data)
        out.flush();os.fsync(out.fileno())
    ui.shadow.require(h.hexdigest()==expected,'public software bytes differ; no fallback')
    Path(target).chmod(0o555 if Path(target).name=='bun' else 0o444)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--evidence',type=Path,required=True);args=parser.parse_args()
    budget=validation.current();ui.shadow.require(budget and budget['purpose'] in {'verify','canary-verify'},'owned private verify budget required')
    evidence=args.evidence;evidence.mkdir(mode=0o700);temporary=tempfile.TemporaryDirectory(prefix='warmtui-',dir='/tmp')
    base=Path(temporary.name);base.chmod(0o755);public=base/'public';public.mkdir(mode=0o755)
    for name in PUBLIC_FILES:
        target=public/name;target.write_bytes((Path(__file__).parent/name).read_bytes());target.chmod(0o444)
    copy_verified('/home/sudosubin/.local/share/kiro-cli/bun',public/'bun',ui.front.BUN_SHA)
    copy_verified('/home/sudosubin/.local/share/kiro-cli/tui.js',public/'tui.js',ui.front.BUNDLE_SHA)
    user=pwd.getpwuid(1001);home=base/'home';home.mkdir(mode=0o700);os.chown(home,1001,user.pw_gid)
    for relative in ['.runtime','.kiro/agents','.kiro/settings','.local/bin','.local/share/kiro-cli']:(home/relative).mkdir(parents=True,exist_ok=True)
    for path in home.rglob('*'):os.chown(path,1001,user.pw_gid)
    for name in ['kiro-cli','kiro-cli-chat']:(home/'.local/bin'/name).symlink_to(NATIVE_ROOT/name)
    for name in ['bun','tui.js']:(home/'.local/share/kiro-cli'/name).symlink_to(public/name)
    agent=home/'.kiro/agents/spot-canary.json';agent.write_text(json.dumps({'name':'spot-canary','description':'ONLY private TUI mock',
         'tools':[],'allowedTools':[],'mcpServers':{},'resources':[],'hooks':{}}));agent.chmod(0o644)
    mock=base/'mock.json';mock.write_text(json.dumps([['SHADOW_TUI_MOCK_OUTPUT'],['SHADOW_TUI_QUEUED_OUTPUT'],['MUST_NOT_RUN_THIRD_MODEL']]));mock.chmod(0o644)
    root=base/'store';root.mkdir(mode=0o700);store=ui.shadow.Store(root);binding=ui.shadow.protected_observation();store.initialize(binding)
    python=sys.executable
    front_tool=public/'spot-shadow-front';front_tool.write_text('#!'+python+' -I\nimport sys;sys.dont_write_bytecode=True;sys.path.insert(0,'+repr(str(public))+');import spot_shadow_frontend as f;f.main()\n');front_tool.chmod(0o555)
    proxy=public/'spot-shadow-ui-proxy';proxy.write_text('#!'+python+' -I\nimport sys;sys.dont_write_bytecode=True;sys.path.insert(0,'+repr(str(public))+');import spot_shadow_ui as u;u.main()\n');proxy.chmod(0o555)
    entry=public/'entry.mjs';entry.write_text('import {pathToFileURL} from "node:url";\nimport {installWarmFrontend} from '+json.dumps(str(public/'spot-shadow-kiro-frontend.mjs'))+';\n'
        +'process.env.KIRO_CHAT_CLI_BIN='+json.dumps(str(proxy))+';\ninstallWarmFrontend('+json.dumps(str(front_tool))+');\n'
        +'process.argv[1]='+json.dumps(str(public/'tui.js'))+';\n'
        +'import {writeFileSync} from "node:fs";const probe=setInterval(()=>{try{const s=globalThis[Symbol.for("nixos.spot.kiro.frontend.v1")].store?.getState();if(s)writeFileSync('
        +json.dumps(str(home/'fixture-input-shape.json'))+',JSON.stringify({lines:s.input.lines.map(x=>x.length),command:s.commandInputValue.length,images:s.pendingImages.length,files:s.attachedFiles.length,pendingFile:s.pendingFileAttachment!=null,voice:s.pendingVoiceText!=null||s.voicePartialText!=null,restore:s.queuedInputRestore!=null,queue:s.activeInterruptMode==="queue"}));}catch{}},100);probe.unref();\n'
        +'await import(pathToFileURL(process.argv[1]).href);\n');entry.chmod(0o444)
    env={'KIRO_API_KEY':'test-only-nonfunctional-no-network-key','KIRO_MOCK_CHAT_RESPONSE':str(mock),
         'PATH':str(public)+':'+str(home/'.local/bin')+':'+str(NATIVE_ROOT)+':/run/current-system/sw/bin',
         'TERM':'xterm-256color','KIRO_CHAT_CLI_BIN':str(NATIVE_ROOT/'kiro-cli-chat')}
    ui.shadow.require(ui.acp.binary(NATIVE_ROOT/'kiro-cli-chat')==ui.acp.NATIVE_SHA,'pinned native changed')
    descriptor=base/'keeper-descriptor.json'
    code=('from pathlib import Path;import sys;sys.path.insert(0,'+repr(str(Path(__file__).parent))+');import spot_shadow_acp as p;'
          'store=p.shadow.Store('+repr(str(root))+');binding=p.shadow.protected_observation();k=p.Keeper(store,binding,'
          +repr([str(NATIVE_ROOT/'kiro-cli-chat'),'acp','--agent','spot-canary'])+',p.shadow.protected_observation);'
          'sys.exit(k.serve(p.drop_command('+repr(str(NATIVE_ROOT/'kiro-cli-chat'))+',["acp","--agent","spot-canary"],'
          +repr(str(home))+','+repr(env)+'),'+repr(str(descriptor))+'))')
    keeper_out=(evidence/'keeper.stdout').open('x');keeper_err=(evidence/'keeper.stderr').open('x')
    keeper=subprocess.Popen([python,'-B','-I','-c',code],stdout=keeper_out,stderr=keeper_err,start_new_session=True)
    frontend_process=None;broker=None;master=None;paused=None;console=bytearray();success=False
    try:
        deadline=time.monotonic()+15
        while not descriptor.exists() and time.monotonic()<deadline:
            ui.shadow.require(keeper.poll() is None,'fixture keeper exited');time.sleep(.01)
        d=ui.shadow.read(descriptor);session=store.job(d['session'])
        startup=store.create(binding,['explicit NEW pinned native TUI startup'])
        store.update(startup,kind='shadow_tui_startup',state='frontend_leased_before_native_spawn')
        io_dir=base/'io';io_dir.mkdir(mode=0o711);endpoint=io_dir/'broker.sock'
        broker=ui.Broker(store,binding,startup,d,entry,budget['cgroup'],home,NATIVE_ROOT/'kiro-cli-chat',
                         {'frontend':front_tool,'proxy':proxy},env);broker.open(endpoint)
        master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',40,120,0,0))
        frontend_env=dict(env,HOME=str(home),USER=user.pw_name,LOGNAME=user.pw_name,LANG='C.UTF-8',XDG_RUNTIME_DIR=str(home/'.runtime'),
                          KIRO_TEST_TUI_JS_PATH=str(entry),SPOT_KIRO_STARTUP=startup['id'],SPOT_SHADOW_TUI_ENDPOINT=str(endpoint),
                          KIRO_DISABLE_TELEMETRY='true',KIRO_NO_AUTO_UPDATE='1',AWS_EC2_METADATA_DISABLED='true')
        gate=('import os,sys,json,ctypes,fcntl,termios;fcntl.ioctl(0,termios.TIOCSCTTY,0);'
              'assert ctypes.CDLL(None).prctl(38,1,0,0,0)==0;os.setgroups([]);os.setgid(int(sys.argv[1]));os.setuid(1001);'
              'env=json.loads(sys.argv[2]);os.chdir(env["HOME"]);os.execvpe(sys.argv[3],sys.argv[3:],env)')
        frontend_process=subprocess.Popen([python,'-B','-I','-c',gate,str(user.pw_gid),json.dumps(frontend_env),str(NATIVE_ROOT/'kiro-cli'),
                           'chat','--tui','--agent-engine','v2','--agent','spot-canary'],stdin=slave,stdout=slave,stderr=slave,start_new_session=True)
        os.close(slave);broker.ancestor=frontend_process.pid
        thread=threading.Thread(target=broker.serve,daemon=True);thread.start()
        def read_console():
            while select.select([master],[],[],0)[0]:
                try:data=os.read(master,65536)
                except OSError:break
                if not data:break
                console.extend(data)
                if b'\x1b[6n' in data:os.write(master,b'\x1b[1;1R')
                ui.shadow.require(len(console)<=2*1024**2,'fixture console exceeds bound')
            return re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]',b'',bytes(console))
        def wait(predicate,label,seconds=35):
            deadline=time.monotonic()+seconds
            while time.monotonic()<deadline:
                read_console()
                if predicate():return
                ui.shadow.require(frontend_process.poll() is None,'native fixture UI exited before '+label)
                time.sleep(.02)
            raise RuntimeError('private TUI condition missing: '+label)
        wait(lambda:broker.census.record and broker.census.record.get('initialized') and not (termios.tcgetattr(master)[3]&termios.ICANON),'initialized real pinned TUI')
        time.sleep(.5);read_console()
        draft=b'ONLY_SYNTHETIC_DRAFT'
        os.write(master,draft);wait(lambda:broker.census.record.get('counters',{}).get('draft') is True,'draft custody')
        draft_record=dict(broker.census.record)
        # Each control key gets a fixture-only length acknowledgement. A fixed
        # sleep can still coalesce keys under CPU throttling; never retry one
        # whose outcome is unknown, and never clear the vendor store directly.
        def input_shape():
            try:return json.loads((home/'fixture-input-shape.json').read_text())
            except (OSError,ValueError):return {}
        def input_length():
            value=input_shape()
            return sum(value['lines'])+value['command'] if value else None
        wait(lambda:input_length()==len(draft),'actual typed draft length')
        for remaining in range(len(draft)-1,-1,-1):
            os.write(master,b'\x7f')
            wait(lambda:input_length()==remaining,'one acknowledged backspace event')
        wait(lambda:broker.census.record.get('counters',{}).get('draft') is False,'draft cleared but custody retained')
        native=ui.shadow.read(session/'record.json');pid=native['backend_pid'];start=native['backend_start']
        ui.shadow.require(Path('/proc/'+str(pid)+'/cgroup').read_text().strip()=='0::'+budget['cgroup'] and work_start(pid)==start,'not owned mock backend')
        fd=os.pidfd_open(pid,0);signal.pidfd_send_signal(fd,signal.SIGSTOP,None,0);paused=(fd,pid,start)
        parse_before_model=broker.census.record.get('parsed_output_count',0)
        os.write(master,b'ONLY synthetic TUI model prompt.\r')
        def pending_request():
            for path in (root/'jobs').iterdir():
                try:record=ui.shadow.read(path/'record.json')
                except FileNotFoundError:continue
                if record.get('parent_session')==d['session'] and record.get('provider_terminal_observed') is False:return True
            return False
        wait(pending_request,'leased native request')
        # A real queued second turn is accepted BEFORE the private fault fence;
        # its later same-stack handoff must continue without a new admission.
        queued_input=b'ONLY accepted queued fixture';os.write(master,queued_input)
        wait(lambda:input_length()==len(queued_input),'actual queued draft length')
        os.write(master,b'\x13')  # Ctrl+S selects queue mode; fixture probe only observes.
        wait(lambda:input_shape().get('queue') is True,'native queue mode selected')
        os.write(master,b'\r')  # Enter accepts that draft into the real queue.
        wait(lambda:broker.census.record.get('counters',{}).get('queued')==1,'accepted queued turn')
        queued_record=dict(broker.census.record)
        broker.census.protection=lambda:(_ for _ in ()).throw(RuntimeError('PRIVATE fixture admission fault'))
        rejected_before=broker.census.record['admission_rejections']
        os.write(master,b'MUST_NOT_ACCEPT_THIRD_PROMPT\r')
        wait(lambda:broker.census.record['admission_rejections']>rejected_before,'synchronous pre-mutation rejection')
        signal.pidfd_send_signal(fd,signal.SIGCONT,None,0);os.close(fd);paused=None
        wait(lambda:b'SHADOW_TUI_MOCK_OUTPUT' in read_console(),'actual PTY output')
        wait(lambda:b'SHADOW_TUI_QUEUED_OUTPUT' in read_console(),'accepted queue continuation behind fault fence')
        wait(lambda:broker.census.record.get('parsed_output_count',0)>parse_before_model
             and broker.census.record.get('parsed_output_count',0)==len(broker.census.offered),
             'new model output parse watermark caught up, not just initialization')
        ui.shadow.require(b'MUST_NOT_RUN_THIRD_MODEL' not in read_console(),'third model started')
        success=True
        proof={'actual_pinned_TUI_draft_native_turn_and_pre_mutation_denial_passed':True,'draft_snapshot':draft_record,
               'accepted_queued_snapshot':queued_record,'parsed_before_model':parse_before_model,
               'parsed_after_models':broker.census.record['parsed_output_count'],'offered_stdout_segments':len(broker.census.offered),
               'positive_queue_continuation_and_new_model_parse_prefix_verified':True,
               'frontend_record':broker.census.record,'retained_store_status':store.status(),'keeper_session':d['session'],
               'bun_sha256':ui.front.BUN_SHA,'bundle_sha256':ui.front.BUNDLE_SHA,'native_sha256':ui.acp.NATIVE_SHA,
               'parsed_receipt_is_NOT_UI_delivery':True,'all_work_tracking_verified':False,'armed':False,'goal_complete':False}
        with (evidence/'proof.json').open('x') as out:json.dump(proof,out,indent=2)
    finally:
        if paused:
            fd,_,_=paused
            try:signal.pidfd_send_signal(fd,signal.SIGCONT,None,0)
            except ProcessLookupError:pass
            finally:os.close(fd)
        # These are exclusively new, model-free, exact owned fixture processes.
        # Preserve ALL failed fixture records/output before cleanup; never infer
        # real-user work completion or stop any host application/service.
        if frontend_process and frontend_process.poll() is None:
            frontend_process.terminate()
            try:frontend_process.wait(timeout=4)
            except subprocess.TimeoutExpired:frontend_process.kill();frontend_process.wait(timeout=4)
        if broker:
            broker.close()
            if broker.actor:
                actor=broker.actor
                try:
                    pid=actor['pid']
                    if work_start(pid)==actor['pid_start'] and Path('/proc/'+str(pid)+'/cgroup').read_text().strip()=='0::'+budget['cgroup']:
                        fd=os.pidfd_open(pid,0)
                        try:signal.pidfd_send_signal(fd,signal.SIGTERM,None,0)
                        finally:os.close(fd)
                except (FileNotFoundError,ProcessLookupError):pass
        if keeper.poll() is None:
            try:ui.rpc(json.loads(descriptor.read_text())['socket'],{'op':'finish-input'})
            except (OSError,ValueError,RuntimeError):pass
            try:keeper.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if descriptor.exists():
                    record=ui.shadow.read(store.job(json.loads(descriptor.read_text())['session'])/'record.json')
                    pid=record.get('backend_pid');start=record.get('backend_start')
                    try:
                        if pid and work_start(pid)==start and Path('/proc/'+str(pid)+'/cgroup').read_text().strip()=='0::'+budget['cgroup']:
                            nfd=os.pidfd_open(pid,0)
                            try:signal.pidfd_send_signal(nfd,signal.SIGTERM,None,0)
                            finally:os.close(nfd)
                    except (FileNotFoundError,ProcessLookupError):pass
                keeper.terminate()
                try:keeper.wait(timeout=4)
                except subprocess.TimeoutExpired:keeper.kill();keeper.wait(timeout=4)
        keeper_out.close();keeper_err.close()
        if master is not None:os.close(master)
        (evidence/'full-pty-console.bin').write_bytes(console)
        snapshot={'success':success,'fixture_only':True,'records':{},'source_runtime_hashes':{'bun':ui.front.BUN_SHA,'tui':ui.front.BUNDLE_SHA}}
        for path in root.rglob('*'):
            if not path.is_file() or path.is_symlink():continue
            if path.name=='lock':continue
            data=path.read_bytes();ui.shadow.require(len(data)<=2*1024**2,'fixture evidence file exceeds bound')
            snapshot['records'][str(path.relative_to(root))]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'body_base64':base64.b64encode(data).decode()}
        if broker and broker.census.record:snapshot['frontend_final']=broker.census.record
        shape=home/'fixture-input-shape.json'
        if shape.exists():snapshot['fixture_only_primitive_input_shape']=json.loads(shape.read_text())
        with (evidence/'complete-owned-fixture-snapshot.json').open('x') as out:json.dump(snapshot,out,indent=2)
        temporary.cleanup()


def work_start(pid):return ui.work.process_start(pid)


if __name__=='__main__':main()
