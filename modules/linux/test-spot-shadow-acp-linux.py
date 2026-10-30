#!/usr/bin/env python3
"""Actual keeper IPC/kernel + pinned native Kiro mock, owned private1GiB only.

No real credentials/models/network/private home/host admission registry. Native
mock and fake outputs are SYNTHETIC; a file/pipe read is NOT delivery authority.
"""
import base64
import json
import os
from pathlib import Path
import select
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
sys.path.insert(0,str(Path(__file__).parent))
import spot_shadow_acp as p
import spot_validation as validation

NATIVE=Path('/nix/store/bn6yjl0rgrd0yqxk3cbkkamjcxg9h47x-kiro-cli-2.10.0/bin/kiro-cli-chat')
FAKE=r'''import json,os,sys,threading,time
from pathlib import Path
home=Path(os.environ['HOME']); lock=threading.Lock();threads=[]
def emit(value):
 raw=(json.dumps(value,ensure_ascii=False)+'\n').encode()
 with lock:
  for n in range(0,len(raw),3):os.write(1,raw[n:n+3])
def prompt(value):
 time.sleep(.35);(home/'synthetic-completed').write_text('completed')
 if value.get('params',{}).get('ackOnly'):
  emit({'jsonrpc':'2.0','id':value['id'],'result':{'accepted':True}});time.sleep(.1);os._exit(0)
 emit({'jsonrpc':'2.0','method':'session/update','params':{'sessionId':'fixture','update':{'sessionUpdate':'agent_message_chunk','content':{'type':'text','text':'SYNTHETIC_🙂_OUTPUT'}}}})
 emit({'jsonrpc':'2.0','id':value['id'],'result':{'stopReason':'end_turn'}})
for raw in sys.stdin.buffer:
 value=json.loads(raw)
 with (home/'forwarded-methods').open('a') as f:f.write(value.get('method','client-response')+'\n')
 if value.get('method')=='initialize':emit({'jsonrpc':'2.0','id':value['id'],'result':{'protocolVersion':1,'agentCapabilities':{}}})
 elif value.get('method')=='session/new':emit({'jsonrpc':'2.0','id':value['id'],'result':{'sessionId':'fixture'}})
 elif value.get('method')=='session/prompt':
  t=threading.Thread(target=prompt,args=(value,));threads.append(t);t.start()
for t in threads:t.join()
if (home/'detach-after-eof').exists():
 pid=os.fork()
 if pid==0:
  os.setsid();pid=os.fork()
  if pid==0:time.sleep(.35);os.write(1,b'detached synthetic output\n')
  os._exit(0)
 os._exit(0)
'''


class KeeperLinuxTests(unittest.TestCase):
    def setUp(self):
        b=validation.current();self.assertTrue(b and b['purpose'] in {'verify','canary-verify'})
        self.assertEqual(os.geteuid(),0);p.work.subreaper()
        self.temp=tempfile.TemporaryDirectory(prefix='warmacp-',dir='/tmp');self.base=Path(self.temp.name);self.base.chmod(0o755)
        self.root=self.base/'store';self.root.mkdir(mode=0o700);self.home=self.base/'home';self.home.mkdir(mode=0o700)
        os.chown(self.home,1001,__import__('pwd').getpwuid(1001).pw_gid)
        for name in ['.runtime','.kiro/settings','.kiro/agents']:
            path=self.home/name;path.mkdir(parents=True,exist_ok=True)
        for path in self.home.rglob('*'):os.chown(path,1001,__import__('pwd').getpwuid(1001).pw_gid)
        self.binding={'instance':'i-00000000000000000','boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
        self.store=p.shadow.Store(self.root);self.store.initialize(self.binding);self.child=None
        self.descriptor=self.base/'descriptor.json';self.next=0;self.frames=[]
        self.fake=self.base/'fake.py';self.fake.write_text(FAKE);self.fake.chmod(0o644)
        self.logs=[]

    def tearDown(self):
        # Normal fixtures finish naturally. Only exact PID/start-bound, model-free
        # fixture descendants may be stopped on a TEST failure, never host work.
        if self.child and self.child.poll() is None:
            try:self.wire({'op':'finish-input'})
            except (OSError,ValueError,RuntimeError):pass
            try:self.child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                if self.descriptor.exists():
                    d=json.loads(self.descriptor.read_text());record=p.shadow.read(self.store.job(d['session'])/'record.json')
                    pid=record.get('backend_pid');start=record.get('backend_start')
                    try:
                        if pid and p.work.process_start(pid)==start and os.getpgid(pid)==pid:os.killpg(pid,signal.SIGTERM)
                    except (FileNotFoundError,ProcessLookupError):pass
                self.child.terminate()
                try:self.child.wait(timeout=3)
                except subprocess.TimeoutExpired:self.child.kill();self.child.wait(timeout=3)
        for stream in self.logs:stream.close()
        self.temp.cleanup()

    def start(self,native=False,uncertain=False,startup_exit=False):
        env={};backend=str(sys.executable);args=['-B','-I',str(self.fake)]
        if native:
            self.assertTrue(NATIVE.is_file(),'pinned native backend missing; not a skipped proof')
            self.assertEqual(p.binary(NATIVE),p.NATIVE_SHA,'native bytes differ; no unverified test fallback')
            agent=self.home/'.kiro/agents/spot-canary.json'
            agent.write_text(json.dumps({'name':'spot-canary','description':'model-free private canary','tools':[],
                                         'allowedTools':[],'mcpServers':{},'resources':[],'hooks':{}}));agent.chmod(0o644)
            mock=self.base/'mock.json';mock.write_text(json.dumps([['ONLY_NATIVE_MOCK_OUTPUT'],['MUST_NOT_RUN_SECOND_MODEL']]));mock.chmod(0o644)
            env={'KIRO_API_KEY':'test-only-nonfunctional-no-network-key','KIRO_MOCK_CHAT_RESPONSE':str(mock),
                 'PATH':str(NATIVE.parent)+':/run/current-system/sw/bin','TERM':'xterm-256color'}
            backend=str(NATIVE);args=['acp','--agent','spot-canary']
        if startup_exit:
            args=['-B','-I','-c','import time,os;time.sleep(.5);os.write(1,b"late uncertain startup output\\n")']
        code=('from pathlib import Path;import sys,os,json;sys.path.insert(0,'+repr(str(Path(p.__file__).parent))+');'
              'import spot_shadow_acp as p;store=p.shadow.Store('+repr(str(self.root))+');'
              'binding='+repr(self.binding)+';k=p.Keeper(store,binding,'+repr([backend,*args])+',lambda:dict(binding));'
              'command=p.drop_command('+repr(backend)+','+repr(args)+','+repr(str(self.home))+','+repr(env)+')\n')
        if uncertain:
            code+='''def lost(argv,**kwargs):
 pid=os.fork()
 if pid==0:
  os.setsid()
  for name,target in [('stdin',0),('stdout',1),('stderr',2)]:os.dup2(kwargs[name],target)
  os.execv(argv[0],argv)
 raise OSError('private fixture native receipt lost AFTER fork')
p.subprocess.Popen=lost
'''
        code+='sys.exit(k.serve(command,'+repr(str(self.descriptor))+'))\n'
        out=(self.base/'keeper.stdout').open('w');err=(self.base/'keeper.stderr').open('w');self.logs=[out,err]
        self.child=subprocess.Popen([sys.executable,'-B','-I','-c',code],stdout=out,stderr=err,start_new_session=True)
        deadline=time.monotonic()+12
        while not self.descriptor.exists() and time.monotonic()<deadline:
            if self.child.poll() is not None:self.fail('keeper exited before descriptor: '+(self.base/'keeper.stderr').read_text())
            time.sleep(.01)
        self.assertTrue(self.descriptor.exists(),'keeper descriptor missing')
        self.d=json.loads(self.descriptor.read_text());self.session=self.store.job(self.d['session'])
        return self

    def wire(self,message,fragment=False,lose_ack=False):
        endpoint=json.loads(self.descriptor.read_text())['socket']
        raw=(json.dumps(message,ensure_ascii=False)+'\n').encode()
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
            client.settimeout(10);client.connect(endpoint)
            if fragment:
                for n in range(0,len(raw),3):client.sendall(raw[n:n+3])
            else:client.sendall(raw)
            if lose_ack:return None
            with client.makefile('rb') as stream:
                data=stream.readline(2*1024**2)
                self.assertTrue(data.endswith(b'\n'),'keeper RPC truncated')
                return json.loads(data)

    def send(self,ident,method,params=None,**kwargs):
        return self.wire({'op':'input','frame':{'jsonrpc':'2.0','id':ident,'method':method,'params':params or {}}},**kwargs)

    def reply(self,ident,timeout=25):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            try:row=p.Segments.read(self.session/'output',self.next)
            except FileNotFoundError:time.sleep(.01);continue
            self.next+=1
            if row['channel']!='stdout':continue
            raw=base64.b64decode(row['data_base64'])
            for line in raw.splitlines():
                message=json.loads(line);self.frames.append(message)
                if 'method' not in message and message.get('id')==ident:return message
        self.fail('retained synthetic/native RPC response missing; keeper='+ (self.base/'keeper.stderr').read_text())

    def initialize(self):
        self.assertTrue(self.send(0,'initialize',{'protocolVersion':1,'clientCapabilities':{}})['admitted'])
        self.assertEqual(self.reply(0)['result']['protocolVersion'],1)

    def finish(self,expected=0):
        if self.child.poll() is None:self.wire({'op':'finish-input'})
        self.child.wait(timeout=12)
        self.assertEqual(self.child.returncode,expected,(self.base/'keeper.stderr').read_text())
        state=p.shadow.read(self.session/'record.json');self.assertEqual(state['consumer_delivery'],'unverified')
        self.assertFalse(self.store.status()['all_work_idle'])

    def test_fragmented_unicode_kept_private_before_read_and_still_not_delivery(self):
        self.start();self.initialize();self.assertTrue(self.send('PRIVATE_ID','session/prompt',{'text':'PRIVATE_PROMPT'},fragment=True)['admitted'])
        self.assertEqual(self.reply('PRIVATE_ID')['result']['stopReason'],'end_turn')
        self.assertTrue(any('SYNTHETIC_🙂_OUTPUT' in json.dumps(x,ensure_ascii=False) for x in self.frames))
        metadata=''.join((path/'record.json').read_text() for path in (self.root/'jobs').iterdir())
        self.assertNotIn('PRIVATE_PROMPT',metadata);self.assertNotIn('PRIVATE_ID',metadata)
        first=p.Segments.read(self.session/'output',0)
        self.assertEqual(first,self.wire({'op':'read','sequence':0})['segment'])
        self.assertEqual(first['consumer_delivery'],'unverified');self.finish()

    def test_lost_ack_and_consumer_reconnect_do_not_repeat_model_work(self):
        self.start();self.initialize();self.send(1,'session/prompt',lose_ack=True)
        self.assertEqual(self.reply(1)['result']['stopReason'],'end_turn')
        self.assertFalse(self.send(1,'session/prompt')['admitted'])
        self.assertEqual((self.home/'forwarded-methods').read_text().splitlines().count('session/prompt'),1)
        self.assertIsNone(self.child.poll());self.finish()

    def test_finish_input_while_busy_waits_for_work_and_output(self):
        self.start();self.initialize();self.send(1,'session/prompt')
        self.wire({'op':'finish-input'});self.assertIsNone(self.child.poll())
        self.child.wait(timeout=12);self.assertTrue((self.home/'synthetic-completed').exists())
        self.assertEqual(self.reply(1)['result']['stopReason'],'end_turn');self.finish()

    def test_ack_only_is_unknown_and_never_provider_terminal(self):
        self.start();self.initialize();self.send(1,'session/prompt',{'ackOnly':True})
        self.assertTrue(self.reply(1)['result']['accepted']);self.child.wait(timeout=12)
        records=[p.shadow.read(path/'record.json') for path in (self.root/'jobs').iterdir()]
        self.assertTrue(any(x.get('kind')=='acp_request' and x.get('provider_terminal_observed') is False for x in records))
        self.assertFalse(self.store.status()['all_work_idle'])

    def test_uncertain_real_spawn_keeps_pipes_and_waits_without_replay(self):
        self.start(uncertain=True,startup_exit=True)
        # No input is ever accepted when native receipt is unknown.
        result=self.send(0,'initialize');self.assertFalse(result['admitted'])
        self.child.wait(timeout=12);self.assertEqual(self.child.returncode,75)
        rows=sorted((self.session/'output').glob('*.json'));self.assertTrue(rows)
        data=b''.join(base64.b64decode(p.Segments.read(self.session/'output',int(row.stem))['data_base64']) for row in rows)
        self.assertIn(b'late uncertain startup output',data)
        self.assertFalse(self.store.status()['all_work_idle'])

    def test_detached_descendant_output_survives_native_exit(self):
        (self.home/'detach-after-eof').write_text('private fixture only')
        self.start();self.initialize();before=time.monotonic();self.wire({'op':'finish-input'})
        self.child.wait(timeout=12);self.assertGreaterEqual(time.monotonic()-before,.3)
        rows=sorted((self.session/'output').glob('*.json'))
        data=b''.join(base64.b64decode(p.Segments.read(self.session/'output',int(row.stem))['data_base64']) for row in rows)
        self.assertIn(b'detached synthetic output',data);self.finish()

    def test_pinned_native_mock_turn_and_output_retention(self):
        self.start(native=True);self.initialize()
        self.assertTrue(self.send(1,'session/new',{'cwd':str(self.home),'mcpServers':[]})['admitted'])
        session=self.reply(1)['result']['sessionId']
        params={'sessionId':session,'prompt':[{'type':'text','text':'ONLY model-free native fixture'}]}
        self.assertTrue(self.send(2,'session/prompt',params)['admitted'])
        self.assertEqual(self.reply(2,35)['result']['stopReason'],'end_turn')
        self.assertTrue(any('ONLY_NATIVE_MOCK_OUTPUT' in json.dumps(x) for x in self.frames))
        self.finish()

    def test_pinned_native_duplicate_and_async_route_never_forwarded(self):
        self.start(native=True);self.initialize()
        self.assertTrue(self.send(1,'session/new',{'cwd':str(self.home),'mcpServers':[]})['admitted'])
        session=self.reply(1)['result']['sessionId'];params={'sessionId':session,'prompt':[{'type':'text','text':'ONLY fixture'}]}
        self.assertTrue(self.send(2,'session/prompt',params)['admitted'])
        self.assertEqual(self.reply(2,35)['result']['stopReason'],'end_turn')
        self.assertFalse(self.send(2,'session/prompt',params)['admitted'])
        self.assertFalse(self.send(3,'_kiro.dev/message/send',params)['admitted'])
        self.finish()
        data=b''.join(base64.b64decode(p.Segments.read(self.session/'output',int(row.stem))['data_base64']) for row in sorted((self.session/'output').glob('*.json')))
        self.assertNotIn(b'MUST_NOT_RUN_SECOND_MODEL',data)


if __name__=='__main__':unittest.main()
