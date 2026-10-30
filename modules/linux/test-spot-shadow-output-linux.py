#!/usr/bin/env python3
"""Kernel/native-helper output custody faults in an owned private verify cage.

Only NEW UID1001 Python fixtures, fake HOME, no model/key/network. Artificial
small quota is restored only inside its synthetic wrapper, never production.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import pwd
import signal
import subprocess
import sys
import tempfile
import time
import unittest
sys.path.insert(0,str(Path(__file__).parent))
import spot_shadow_ui as p
import spot_validation as validation


class OutputLinuxTests(unittest.TestCase):
    def setUp(self):
        self.budget=validation.current();self.assertTrue(self.budget and self.budget['purpose'] in {'verify','canary-verify'})
        self.assertEqual(os.geteuid(),0);p.work.subreaper()
        self.temp=tempfile.TemporaryDirectory(prefix='warmoutput-',dir='/tmp');self.base=Path(self.temp.name);self.base.chmod(0o755)
        self.root=self.base/'store';self.root.mkdir(mode=0o700);self.home=self.base/'home';self.home.mkdir(mode=0o700)
        os.chown(self.home,1001,pwd.getpwuid(1001).pw_gid);self.binding={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'instance':'i-00000000000000000'}
        self.store=p.shadow.Store(self.root);self.store.initialize(self.binding);self.child=None;self.logs=[]
        self.native_meta=self.base/'native.json';self.release=self.base/'release-quota';self.child_start=None

    def wait(self,predicate,label,seconds=12):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            if predicate():return
            time.sleep(.02)
        self.fail('synthetic helper condition missing: '+label)

    def records(self):return [p.shadow.read(path/'record.json') for path in (self.root/'jobs').iterdir()]

    def launch(self,program,mode='normal',lost_consumer=False):
        fake=self.base/'native.py';fake.write_text(program);fake.chmod(0o444)
        code=('from pathlib import Path;import os,sys,json,time;sys.path.insert(0,'+repr(str(Path(p.__file__).parent))+');'
              'import spot_shadow_ui as p;store=p.shadow.Store('+repr(str(self.root))+');binding='+repr(self.binding)+';'
              'meta=Path('+repr(str(self.native_meta))+');release=Path('+repr(str(self.release))+');real=p.subprocess.Popen\n')
        if mode=='lost-spawn':
            code+='''def observed(argv,**kwargs):
 pid=os.fork()
 if pid==0:
  os.setsid();os.execv(argv[0],argv)
 p.shadow.publish(meta,{'pid':pid,'start':p.work.process_start(pid)},new=True)
 raise OSError('SYNTHETIC Popen receipt lost AFTER fork, never retry')
'''
        else:
            code+='''def observed(argv,**kwargs):
 child=real(argv,**kwargs);p.shadow.publish(meta,{'pid':child.pid,'start':p.work.process_start(child.pid)},new=True);return child
'''
        code+='p.subprocess.Popen=observed\n'
        if mode=='quota':
            code+='''original_max=p.acp.MAX_BYTES;p.acp.MAX_BYTES=131072;real_sleep=time.sleep
def quota_wait(seconds):
 if release.exists():p.acp.MAX_BYTES=original_max
 real_sleep(seconds)
p.output.time.sleep=quota_wait
'''
        if mode=='write-uncertain':
            code+='''append=p.acp.Segments.append
def uncertain(self,*args,**kwargs):
 row=append(self,*args,**kwargs);raise OSError('SYNTHETIC committed write lost receipt')
p.acp.Segments.append=uncertain
'''
        code+='result=p.opaque_run(store,binding,sys.executable,["-B","-I",'+repr(str(fake))+'],'+repr(str(self.home))+');print(json.dumps(result))\n'
        err=(self.base/'wrapper.stderr').open('x');self.logs.append(err)
        out=subprocess.PIPE if lost_consumer else (self.base/'wrapper.stdout').open('x')
        if not lost_consumer:self.logs.append(out)
        self.child=subprocess.Popen([sys.executable,'-B','-I','-c',code],stdout=out,stderr=err,start_new_session=True)
        self.child_start=p.work.process_start(self.child.pid)
        if lost_consumer:self.child.stdout.close()
        self.wait(lambda:self.native_meta.exists(),'owned native identity')
        self.wait(lambda:bool(self.records()),'lease exists before native')
        return self

    def finish(self,metadata_reply=True):
        self.child.wait(timeout=15)
        if metadata_reply:
            self.assertEqual(self.child.returncode,0,(self.base/'wrapper.stderr').read_text())
            result=json.loads((self.base/'wrapper.stdout').read_text());self.assertEqual(result['output_delivery'],'unverified')
        self.assertEqual(len(self.records()),1);record=self.records()[0]
        self.assertTrue(record['output_complete']);self.assertEqual(record['output_delivery'],'unverified')
        self.assertFalse(self.store.status()['all_work_idle']);return record

    def test_real_uid_home_nnp_binary_output_both_channels(self):
        program='''import os,sys,json
from pathlib import Path
v={'uid':os.getuid(),'home_matches_cwd':str(Path.cwd())==os.environ['HOME'],'groups':os.getgroups(),'nnp':next(x for x in Path('/proc/self/status').read_text().splitlines() if x.startswith('NoNewPrivs:')).split()[-1]}
os.write(1,json.dumps(v).encode());os.write(2,b'opaque_binary_\\x00_\\xff')
'''
        self.launch(program);r=self.finish();body=p.output.bridge_output(self.store,r['id']);identity=json.loads(base64.b64decode(body['stdout']))
        self.assertEqual(identity,{'uid':1001,'home_matches_cwd':True,'groups':[],'nnp':'1'})
        self.assertEqual(base64.b64decode(body['stderr']),b'opaque_binary_\x00_\xff')

    def test_concurrent_large_stdout_stderr_retained_not_truncated_by_bridge_limit(self):
        self.launch('import os,threading\ndef write(fd,byte):\n for _ in range(12):os.write(fd,byte*65536)\na=threading.Thread(target=write,args=(1,b"a"));a.start();write(2,b"b");a.join()\n')
        r=self.finish();self.assertEqual(r['output_bytes'],24*65536)
        with self.assertRaisesRegex(RuntimeError,'NOT truncated'):p.output.bridge_output(self.store,r['id'])
        sizes={'stdout':0,'stderr':0}
        for number in range(r['output_segments']):
            row=p.acp.Segments.read(self.store.job(r['id'])/'output',number);sizes[row['channel']]+=row['bytes']
        self.assertEqual(sizes,{'stdout':12*65536,'stderr':12*65536})

    def test_quota_backpressures_live_native_then_naturally_completes_without_reexecution(self):
        self.launch('import os\nfrom pathlib import Path\nh=Path(os.environ["HOME"]);(h/"began-once").write_text("once")\nfor _ in range(32):os.write(1,b"q"*65536)\n(h/"completed").write_text("natural")\n',mode='quota')
        self.wait(lambda:any(r.get('state')=='helper_output_backpressure' for r in self.records()),'actual pipe backpressure')
        d=json.loads(self.native_meta.read_text());self.assertEqual(p.work.process_start(d['pid']),d['start'])
        self.assertEqual(p.work.process_uid(d['pid']),1001)
        self.assertEqual(Path('/proc/'+str(d['pid'])+'/cgroup').read_text().strip(),'0::'+self.budget['cgroup'])
        self.assertFalse((self.home/'completed').exists());self.assertIsNone(self.child.poll())
        before=self.records()[0];self.assertLessEqual(before['output_bytes'],131072);self.assertFalse(before['output_complete'])
        self.release.write_text('ONLY restore artificial fixture quota to policy64MiB')
        r=self.finish();self.assertEqual(r['output_bytes'],32*65536);self.assertEqual((self.home/'completed').read_text(),'natural')
        self.assertEqual((self.home/'began-once').read_text(),'once')

    def test_lost_spawn_receipt_keeps_parent_pipe_and_late_child_output_without_retry(self):
        self.launch('import os,time\nfrom pathlib import Path\ntime.sleep(.25);os.write(1,b"LATE_SYNTHETIC_OUTPUT");Path(os.environ["HOME"],"completed").write_text("natural")\n',mode='lost-spawn')
        r=self.finish();self.assertEqual(r['exit_status'],75);self.assertEqual(r['spawn_outcome'],'unknown_no_replay')
        self.assertEqual(base64.b64decode(p.output.bridge_output(self.store,r['id'])['stdout']),b'LATE_SYNTHETIC_OUTPUT')
        self.assertEqual((self.home/'completed').read_text(),'natural')

    def test_metadata_consumer_disconnect_does_not_close_native_output_or_kill_work(self):
        self.launch('import os,time\nfrom pathlib import Path\ntime.sleep(.25);os.write(1,b"OUTPUT_AFTER_CONSUMER_EXIT");Path(os.environ["HOME"],"completed").write_text("natural")\n',lost_consumer=True)
        r=self.finish(metadata_reply=False);self.assertEqual((self.home/'completed').read_text(),'natural')
        self.assertEqual(base64.b64decode(p.output.bridge_output(self.store,r['id'])['stdout']),b'OUTPUT_AFTER_CONSUMER_EXIT')

    def test_uncertain_output_write_holds_without_retry_completion_or_delivery(self):
        self.launch('import os\nfrom pathlib import Path\nos.write(1,b"COMMITTED_ONCE");Path(os.environ["HOME"],"completed").write_text("natural")\n',mode='write-uncertain')
        self.wait(lambda:any(r.get('state')=='helper_output_write_uncertain_no_retry' for r in self.records()),'uncertain write held')
        self.wait(lambda:(self.home/'completed').exists(),'native naturally finished')
        self.assertIsNone(self.child.poll());r=self.records()[0];self.assertFalse(r['output_complete'])
        files=list((self.store.job(r['id'])/'output').glob('*.bin'));self.assertEqual(len(files),1);self.assertEqual(files[0].read_bytes(),b'COMMITTED_ONCE')
        self.assertEqual(list(files[0].parent.glob('*.exposed')),[])

    def tearDown(self):
        # Every signal below is fixture-only and PID-start/cgroup bound. No host
        # services, user apps, real models or old shadow jobs are touched.
        self.release.touch(exist_ok=True)
        if self.child and self.child.poll() is None:
            try:self.child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.assertEqual(p.work.process_start(self.child.pid),self.child_start)
                self.assertEqual(Path('/proc/'+str(self.child.pid)+'/cgroup').read_text().strip(),'0::'+self.budget['cgroup'])
                fd=os.pidfd_open(self.child.pid,0)
                try:signal.pidfd_send_signal(fd,signal.SIGTERM,None,0)
                finally:os.close(fd)
                self.child.wait(timeout=5)
        for stream in self.logs:stream.close()
        evidence=os.environ.get('SPOT_WARM_OUTPUT_TEST_EVIDENCE_DIR')
        if evidence:
            folder=Path(evidence);p.shadow.directory(folder);snapshot={'fixture_only':True,'case':self._testMethodName,'records':{},'logs':{}}
            total=0
            for path in self.root.rglob('*'):
                if not path.is_file() or path.is_symlink() or path.name=='lock':continue
                data=path.read_bytes();total+=len(data);self.assertLessEqual(total,8*1024**2)
                snapshot['records'][str(path.relative_to(self.root))]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'body_base64':base64.b64encode(data).decode()}
            for name in ['wrapper.stdout','wrapper.stderr']:
                path=self.base/name
                if path.exists():snapshot['logs'][name]=path.read_text()
            with (folder/(self._testMethodName+'.json')).open('x') as out:json.dump(snapshot,out,indent=2)
        self.temp.cleanup()


if __name__=='__main__':unittest.main()
