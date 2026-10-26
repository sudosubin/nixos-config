"""Real cross-UID stdio tests with a model-free fake ACP backend.

All state is in a unique /run sandbox. No user session, service, AWS API,
credential, external connection or real model is used.
"""
import importlib.util
import json
import os
from pathlib import Path
import pwd
import select
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

spec=importlib.util.spec_from_file_location('work',Path(__file__).with_name('spot_work.py'))
work=importlib.util.module_from_spec(spec);spec.loader.exec_module(work)

FAKE='''import json,os,sys,threading,time
from pathlib import Path
log=Path(sys.argv[1]);lock=threading.Lock()
def emit(out):
 b=(json.dumps(out)+'\\n').encode()
 with lock:
  for i in range(0,len(b),3):sys.stdout.buffer.write(b[i:i+3]);sys.stdout.buffer.flush()
def prompt(d):
 time.sleep(0.6)
 log.with_name('completed').write_text('model-free-work-completed')
 if d.get('params',{}).get('ackOnly'):result={'accepted':True}
 else:result={'stopReason':'end_turn'}
 emit({'jsonrpc':'2.0','id':d['id'],'result':result})
def close_output():
 while not log.with_name('close-output').exists():time.sleep(0.01)
 os.close(1)
threading.Thread(target=close_output,daemon=True).start()
for raw in sys.stdin.buffer:
 d=json.loads(raw)
 with log.open('a') as f:f.write(d.get('method','response')+'\\n')
 if d.get('method')=='initialize':emit({'jsonrpc':'2.0','id':d['id'],'result':{'protocolVersion':1,'agentCapabilities':{}}})
 elif d.get('method')=='session/prompt':threading.Thread(target=prompt,args=(d,),daemon=True).start()
# Deliberately emulate a backend that exits immediately on input EOF. The
# admission proxy must not deliver EOF while acknowledged work is running.
os._exit(0)
'''


@unittest.skipUnless(sys.platform=='linux' and os.geteuid()==0,'requires root Linux sandbox verification')
class ACPStdioTests(unittest.TestCase):
    def setUp(self):
        try:self.user=pwd.getpwuid(1001)
        except KeyError:self.skipTest('test UID 1001 not present')
        self.base=Path(tempfile.mkdtemp(prefix='spot-acp-validation-',dir='/run'));self.base.chmod(0o755)
        for name in ['spot_acp.py','spot_work.py']:
            p=self.base/name;shutil.copyfile(Path(__file__).with_name(name),p);p.chmod(0o644)
        self.fake=self.base/'fake.py';self.fake.write_text(FAKE);self.fake.chmod(0o644)
        scratch=self.base/'scratch';scratch.mkdir();os.chown(scratch,1001,self.user.pw_gid);scratch.chmod(0o700)
        self.log=scratch/'forwarded-methods'
        self.protocol=work.Protocol(self.base/'runtime',uid=1001,gid=self.user.pw_gid);self.protocol.initialize()
        code="import sys;sys.path.insert(0,sys.argv[1]);import spot_acp,spot_work;p=spot_work.Protocol(sys.argv[2],uid=1001,gid=int(sys.argv[3]));sys.exit(spot_acp.bridge(p,[sys.executable,'-u',sys.argv[4],sys.argv[5]]))"
        def user():os.initgroups(self.user.pw_name,self.user.pw_gid);os.setgid(self.user.pw_gid);os.setuid(1001)
        self.child=subprocess.Popen([sys.executable,'-u','-c',code,str(self.base),str(self.protocol.runtime),str(self.user.pw_gid),str(self.fake),str(self.log)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,preexec_fn=user,cwd='/',start_new_session=True,bufsize=0)
        self.buffer=b'';self.messages=[]
        self.send({'jsonrpc':'2.0','id':0,'method':'initialize','params':{}})
        self.assertEqual(self.reply(0)['result']['protocolVersion'],1)
        self.wait_idle()

    def tearDown(self):
        if self.child.poll() is None:
            self.child.stdin.close()
            try:self.child.wait(timeout=5)
            except subprocess.TimeoutExpired:self.child.terminate();self.child.wait(timeout=5)
        for stream in [self.child.stdout,self.child.stderr]:stream.close()
        shutil.rmtree(self.base)

    def send(self,message,fragment=False):
        raw=(json.dumps(message,ensure_ascii=False)+'\n').encode()
        if fragment:
            for i in range(0,len(raw),3):self.child.stdin.write(raw[i:i+3])
        else:self.child.stdin.write(raw)

    def reply(self,ident):
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            while b'\n' in self.buffer:
                raw,self.buffer=self.buffer.split(b'\n',1);m=json.loads(raw)
                if m.get('id')==ident:return m
                self.messages.append(m)
            if select.select([self.child.stdout],[],[],0.05)[0]:
                raw=os.read(self.child.stdout.fileno(),65536)
                if not raw:self.fail('proxy closed unexpectedly')
                self.buffer+=raw
        self.fail('no ACP response')

    def jobs(self):return [x for x in self.protocol.blockers() if x['reason']!='participant_unverified']

    def wait_idle(self):
        for i in range(100):
            if not self.jobs():return
            time.sleep(0.02)
        self.fail('fixture did not reach request completion')

    def test_busy_turn_finishes_but_fenced_prompt_never_reaches_backend(self):
        self.send({'jsonrpc':'2.0','id':1,'method':'session/prompt','params':{'content':[{'text':'FAKE_PROMPT'}]}})
        for i in range(100):
            if self.jobs():break
            time.sleep(0.01)
        self.assertTrue(self.jobs());self.protocol.seal()
        self.send({'jsonrpc':'2.0','id':2,'method':'session/prompt','params':{'content':[{'text':'MUST_NOT_FORWARD'}]}})
        self.assertEqual(self.reply(2)['error']['code'],-32074)
        self.assertEqual(self.reply(1)['result']['stopReason'],'end_turn');self.wait_idle()
        self.assertEqual(self.log.read_text().splitlines(),['initialize','session/prompt'])
        # Idle metadata is not yet authority to bypass the guard's process check.
        self.assertEqual(self.protocol.blockers()[0]['reason'],'participant_unverified')

    def test_fragmented_unicode_transparent_without_transcript_files(self):
        self.send({'jsonrpc':'2.0','id':'text-id','method':'session/prompt','params':{'content':[{'text':'PRIVATE_PROMPT_🙂'}]}},fragment=True)
        time.sleep(0.1)
        records=''.join(p.read_text() for directory in ['leases','participants'] for p in (self.protocol.runtime/directory).iterdir())
        self.assertNotIn('PRIVATE_PROMPT',records);self.assertNotIn('text-id',records)
        self.assertEqual(self.reply('text-id')['result']['stopReason'],'end_turn');self.wait_idle()
        records=[json.loads(p.read_text()) for p in (self.protocol.runtime/'participants').iterdir()]
        self.assertTrue(records[0]['healthy']);self.assertTrue(records[0]['initialized']);self.assertEqual(records[0]['active_requests'],0)

    def test_ack_only_reply_never_makes_model_work_idle(self):
        self.send({'jsonrpc':'2.0','id':1,'method':'session/prompt','params':{'ackOnly':True}})
        self.assertTrue(self.reply(1)['result']['accepted'])
        self.assertTrue(self.jobs())
        record=json.loads(next((self.protocol.runtime/'participants').iterdir()).read_text())
        self.assertFalse(record['healthy']);self.assertEqual(record['reason'],'prompt_response_not_terminal')

    def test_oversized_late_input_does_not_abort_an_existing_turn(self):
        self.send({'jsonrpc':'2.0','id':1,'method':'session/prompt','params':{}})
        for i in range(100):
            if self.jobs():break
            time.sleep(0.01)
        self.child.stdin.write(b'x'*(1024*1024+64)+b'\n')
        self.assertEqual(self.reply(1)['result']['stopReason'],'end_turn')
        self.assertTrue(self.log.with_name('completed').exists())
        self.assertEqual(self.log.read_text().splitlines(),['initialize','session/prompt'])
        self.assertTrue(self.jobs())  # malformed input remains unknown

    def test_frontend_crash_keeps_backend_alive_until_work_finished(self):
        self.send({'jsonrpc':'2.0','id':1,'method':'session/prompt','params':{}})
        for i in range(100):
            if self.jobs():break
            time.sleep(0.01)
        self.child.stdin.close();self.child.stdout.close()
        self.child.wait(timeout=6)
        self.assertTrue(self.log.with_name('completed').exists())
        self.assertTrue(self.jobs())
        record=json.loads(next((self.protocol.runtime/'participants').iterdir()).read_text())
        self.assertFalse(record['healthy'])

    def test_backend_output_eof_is_unknown_even_while_backend_still_alive(self):
        self.log.with_name('close-output').touch()
        record=None
        for i in range(100):
            record=json.loads(next((self.protocol.runtime/'participants').iterdir()).read_text())
            if not record['healthy']:break
            time.sleep(0.02)
        self.assertFalse(record['healthy']);os.kill(record['backend_pid'],0)

    def test_eof_does_not_drop_existing_work(self):
        self.send({'jsonrpc':'2.0','id':1,'method':'session/prompt','params':{}})
        self.child.stdin.close()
        self.assertEqual(self.reply(1)['result']['stopReason'],'end_turn')
        self.child.wait(timeout=5);self.assertEqual(self.child.returncode,0)
        self.assertEqual(self.protocol.blockers(),[])


if __name__=='__main__':unittest.main()
