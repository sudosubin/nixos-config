#!/usr/bin/env python3
"""Explicit post-install NATIVE MOCK proof in an owned private verify envelope.

Only a NEW synthetic backend in THIS exact cgroup may be paused/resumed. Never
restart/signal existing user/SSM/Docker/Kiro/Herdr/OS. No real credentials/models.
Use actual installed bytes and production shadow/protection, retaining records.
"""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import signal
import socket
import subprocess
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).parent))
import spot_validation as validation


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--proof-directory',type=Path,required=True)
    args=parser.parse_args();budget=validation.current()
    if not budget or budget['purpose'] not in {'verify','canary-verify'}:raise RuntimeError('owned verification budget required')
    folder=args.proof_directory;folder.mkdir(mode=0o700)
    marker=json.loads(Path('/etc/spot-work-shadow-acp-current.json').read_text());cli=Path(marker['cli']);installed=cli.parent
    spec=importlib.util.spec_from_file_location('installed_warm_acp',installed/'spot_shadow_acp.py')
    p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
    cfg=p.settings(p.shadow.read(installed/'config.json'));p.shadow.require(p.version(installed)==cfg['deployment_id']==marker['deployment_id'],'installed source changed')
    p.shadow.require(p.binary(cfg['backend'])==p.NATIVE_SHA==cfg['backend_sha256'],'untested native bytes')
    binding=p.shadow.protected_observation();store=p.shadow.Store(cfg['store_directory']);store.check()
    old={path.name:hashlib.sha256((path/'record.json').read_bytes()).hexdigest() for path in (store.root/'jobs').iterdir()}
    help_reply=subprocess.run([str(cli),'--help'],capture_output=True,text=True,check=True)
    (folder/'installed-entry-help.txt').write_text(help_reply.stdout)
    user=pwd.getpwuid(1001);temporary=tempfile.TemporaryDirectory(prefix='warm-acp-owned-op-',dir='/tmp')
    base=Path(temporary.name);base.chmod(0o755);home=base/'home';home.mkdir(mode=0o700);os.chown(home,1001,user.pw_gid)
    for name in ['.runtime','.kiro/settings','.kiro/agents']:(home/name).mkdir(parents=True,exist_ok=True)
    for path in home.rglob('*'):os.chown(path,1001,user.pw_gid)
    agent=home/'.kiro/agents/spot-canary.json';agent.write_text(json.dumps({'name':'spot-canary','description':'ONLY isolated native mock',
           'tools':[],'allowedTools':[],'mcpServers':{},'resources':[],'hooks':{}}));agent.chmod(0o644)
    mock=base/'mock.json';mock.write_text(json.dumps([['OPERATING_NATIVE_MOCK_ONLY'],['MUST_NOT_RUN_SECOND_MODEL']]));mock.chmod(0o644)
    env={'KIRO_API_KEY':'test-only-nonfunctional-no-network-key','KIRO_MOCK_CHAT_RESPONSE':str(mock),
         'PATH':str(Path(cfg['backend']).parent)+':/run/current-system/sw/bin','TERM':'xterm-256color'}
    descriptor=folder/'keeper-descriptor.json'
    server=('from pathlib import Path;import sys,json;sys.path.insert(0,'+repr(str(installed))+');'
            'import spot_shadow_acp as p;cfg=p.settings(p.shadow.read(Path('+repr(str(installed/'config.json'))+')));'
            'store=p.shadow.Store(cfg["store_directory"]);binding=p.shadow.protected_observation();'
            'k=p.Keeper(store,binding,[cfg["backend"],"acp","--agent","spot-canary"],p.shadow.protected_observation);'
            'command=p.drop_command(cfg["backend"],["acp","--agent","spot-canary"],'+repr(str(home))+','+repr(env)+');'
            'sys.exit(k.serve(command,'+repr(str(descriptor))+'))')
    out=(folder/'keeper-full.stdout').open('x');err=(folder/'keeper-full.stderr').open('x')
    keeper=subprocess.Popen([sys.executable,'-B','-I','-c',server],stdout=out,stderr=err,start_new_session=True)
    paused=None;messages=[];sequence=0
    try:
        deadline=time.monotonic()+20
        while not descriptor.exists() and time.monotonic()<deadline:
            p.shadow.require(keeper.poll() is None,'keeper exited before descriptor; no replay');time.sleep(.01)
        d=p.shadow.read(descriptor);session=store.job(d['session'])
        p.shadow.require(d['pid']==keeper.pid and d['pid_start']==p.work.process_start(keeper.pid),'keeper owner differs')
        def wire(message,lose_ack=False):
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
                client.settimeout(12);client.connect(d['socket']);client.sendall((json.dumps(message,separators=(',',':'))+'\n').encode())
                if lose_ack:return None
                with client.makefile('rb') as stream:
                    raw=stream.readline(2*1024**2);p.shadow.require(raw.endswith(b'\n'),'keeper RPC truncated; never repeat input')
                    return json.loads(raw)
        def send(ident,method,params):return wire({'op':'input','frame':{'jsonrpc':'2.0','id':ident,'method':method,'params':params}})
        def reply(ident):
            nonlocal sequence
            deadline=time.monotonic()+35
            while time.monotonic()<deadline:
                response=wire({'op':'read','sequence':sequence});row=response['segment']
                if row is None:time.sleep(.01);continue
                sequence+=1;data=base64.b64decode(row['data_base64'])
                p.shadow.require(hashlib.sha256(data).hexdigest()==row['sha256'] and row['bytes']==len(data),'output body mismatch')
                if row['channel']!='stdout':continue
                for line in data.splitlines():
                    message=json.loads(line);messages.append(message)
                    if 'method' not in message and message.get('id')==ident:return message
            raise RuntimeError('native fixture response missing; never replay input')
        p.shadow.require(send(0,'initialize',{'protocolVersion':1,'clientCapabilities':{}})['admitted'] is True,'initialize refused')
        p.shadow.require(reply(0)['result']['protocolVersion']==1,'native initialize response unknown')
        p.shadow.require(send(1,'session/new',{'cwd':str(home),'mcpServers':[]})['admitted'] is True,'session/new refused')
        native_session=reply(1)['result']['sessionId'];record=p.shadow.read(session/'record.json')
        native_pid=record['backend_pid'];native_start=record['backend_start']
        expected_group='0::'+budget['cgroup']
        p.shadow.require(p.work.process_start(native_pid)==native_start and Path('/proc/'+str(native_pid)).stat().st_uid==1001
                         and Path('/proc/'+str(native_pid)+'/cgroup').read_text().strip()==expected_group
                         and os.getpgid(native_pid)==native_pid,'native mock is not exclusively owned by this verification')
        native_pidfd=os.pidfd_open(native_pid,0)
        p.shadow.require(p.work.process_start(native_pid)==native_start,'native identity changed before fixture pause')
        signal.pidfd_send_signal(native_pidfd,signal.SIGSTOP,None,0);paused=(native_pidfd,native_pid,native_start)
        # A separate CONSUMER process exits after sending input without receiving
        # its ACK. The cloud keeper stays independent; no model input is replayed.
        prompt={'jsonrpc':'2.0','id':2,'method':'session/prompt','params':{'sessionId':native_session,
                'prompt':[{'type':'text','text':'ONLY explicit model-free operating fixture'}]}}
        first_client=('import socket,json;msg='+repr({'op':'input','frame':prompt})+';s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);'
                      's.connect('+repr(d['socket'])+');s.sendall((json.dumps(msg)+"\\n").encode());s.close()')
        first=subprocess.run([sys.executable,'-B','-I','-c',first_client],capture_output=True,text=True)
        p.shadow.require(first.returncode==0,'consumer did not finish; inspect, no replay')
        deadline=time.monotonic()+10;requests=[]
        while time.monotonic()<deadline:
            requests=[p.shadow.read(path/'record.json') for path in (store.root/'jobs').iterdir()
                      if path.name not in old and path.name!=d['session']]
            if len(requests)==3:break
            time.sleep(.01)
        p.shadow.require(len(requests)==3 and keeper.poll() is None,'keeper/session/request missing after consumer exit')
        before_keeper_start=p.work.process_start(keeper.pid)
        refused=wire({'op':'input','frame':prompt});p.shadow.require(refused['admitted'] is False,'lost ACK caused duplicate model input')
        # Restart ONLY the already installed metadata collector, never keeper,
        # backend, user manager, SSM or Docker. Paused backend is synthetic only.
        unit='spot-work-shadow-498e2c5726a5.service'
        before_inv=subprocess.check_output(['systemctl','show',unit,'-p','InvocationID','--value'],text=True).strip()
        subprocess.run(['systemctl','restart',unit],check=True,timeout=10)
        deadline=time.monotonic()+10
        while subprocess.check_output(['systemctl','show',unit,'-p','MainPID','--value'],text=True).strip()!='0' and time.monotonic()<deadline:time.sleep(.01)
        after_inv=subprocess.check_output(['systemctl','show',unit,'-p','InvocationID','--value'],text=True).strip()
        status=p.shadow.read(store.root/'status.json')
        p.shadow.require(before_inv!=after_inv and any(x['id']==d['session'] for x in status['jobs'])
                         and p.work.process_start(keeper.pid)==before_keeper_start and keeper.poll() is None
                         and p.work.process_start(native_pid)==native_start,'metadata restart disrupted owned session or lost custody')
        signal.pidfd_send_signal(native_pidfd,signal.SIGCONT,None,0);os.close(native_pidfd);paused=None
        p.shadow.require(reply(2)['result']['stopReason']=='end_turn','native mock terminal result missing')
        p.shadow.require(any('OPERATING_NATIVE_MOCK_ONLY' in json.dumps(m) for m in messages),'actual native mock output absent')
        p.shadow.require(send(3,'_kiro.dev/message/send',prompt['params'])['admitted'] is False,'unverified async route forwarded')
        wire({'op':'finish-input'});keeper.wait(timeout=15);p.shadow.require(keeper.returncode==0,'keeper did not naturally complete')
        records={path.name:p.shadow.read(path/'record.json') for path in (store.root/'jobs').iterdir() if path.name not in old}
        p.shadow.require(len(records)==4 and all(x['output_delivery']=='unverified' for x in records.values()),'new custody missing or falsely delivered')
        for ident,digest in old.items():p.shadow.require(hashlib.sha256((store.job(ident)/'record.json').read_bytes()).hexdigest()==digest,'old shadow record changed')
        rows={};native_bytes=b''
        for path in sorted((session/'output').glob('*.json')):
            row=p.Segments.read(session/'output',int(path.stem));rows[path.stem]=row;native_bytes+=base64.b64decode(row['data_base64'])
        p.shadow.require(b'MUST_NOT_RUN_SECOND_MODEL' not in native_bytes,'second model work was started')
        proof={'schema':1,'actual_installed_keeper_native_mock_passed':True,'installed_deployment':cfg['deployment_id'],
               'source_hashes':{name:hashlib.sha256((installed/name).read_bytes()).hexdigest() for name in p.SOURCES},
               'native_backend_sha256':cfg['backend_sha256'],'existing_shadow_store':str(store.root),'session':d['session'],
               'keeper_pid':keeper.pid,'keeper_start':d['pid_start'],'new_records':records,'segments':rows,
               'consumer_process_exited_without_ACK':True,'new_consumer_read_retained_output_without_input_replay':True,
               'metadata_collector_restart_while_owned_synthetic_backend_paused':True,'collector_invocations':[before_inv,after_inv],
               'pause_is_fixture_fault_injection_NOT_real_model_latency':True,'no_real_credentials_models_network_or_private_home':True,
               'all_existing_shadow_record_hashes_preserved':old,'budget':budget,
               'real_existing_user_SSM_Docker_Kiro_Herdr_or_OS_restarted':False,'consumer_delivery_verified':False,
               'full_producer_tracking_verified':False,'actual_OS_reboot_or_updated_flake_reapply':False,'armed':False,'goal_complete':False}
        with (folder/'complete-operating-native-keeper-proof.json').open('x') as stream:
            json.dump(proof,stream,indent=2);stream.flush();os.fsync(stream.fileno())
    finally:
        if paused:
            pidfd,pid,start=paused
            try:signal.pidfd_send_signal(pidfd,signal.SIGCONT,None,0)
            except ProcessLookupError:pass
            finally:os.close(pidfd)
        out.close();err.close()
        # Do not remove a still-live/unknown keeper, accepted work or its home.
        if keeper.poll() is None:temporary._finalizer.detach()
        else:temporary.cleanup()


if __name__=='__main__':main()
