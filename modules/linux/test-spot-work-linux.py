"""Root-only Linux integration tests, using an isolated /run directory.

Never changes real admission, services, AWS state, home, or user configuration.
Only tiny test-owned commands run as UID 1001; all have finite sleep durations.
"""
import importlib.util
import json
import os
from pathlib import Path
import pwd
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch
import unittest

spec=importlib.util.spec_from_file_location('work',Path(__file__).with_name('spot_work.py'))
work=importlib.util.module_from_spec(spec);spec.loader.exec_module(work)


@unittest.skipUnless(sys.platform=='linux' and os.geteuid()==0,'requires isolated root Linux verification')
class LinuxAdmissionTests(unittest.TestCase):
    def setUp(self):
        try:self.user=pwd.getpwuid(1001)
        except KeyError:self.skipTest('test UID 1001 not present')
        self.base=Path(tempfile.mkdtemp(prefix='spot-work-validation-',dir='/run'));self.base.chmod(0o755)
        self.module=self.base/'spot_work.py'
        for name in ['spot_work.py','spot_drain.py']:
            target=self.base/name;shutil.copyfile(Path(__file__).with_name(name),target);target.chmod(0o644)
        self.protocol=work.Protocol(self.base/'runtime',uid=1001,gid=self.user.pw_gid);self.protocol.initialize()
        self.clients=[]

    def tearDown(self):
        for child in self.clients:
            if child.poll() is None:child.kill()
            child.wait(timeout=5)
            for stream in [child.stdout,child.stderr]:
                if stream is not None and not stream.closed:stream.close()
        # Background descendants in these fixtures sleep at most 1.5 seconds.
        time.sleep(1.6)
        shutil.rmtree(self.base)

    def client(self,*args):
        code="import importlib.util,sys;spec=importlib.util.spec_from_file_location('work',sys.argv[1]);w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w);p=w.Protocol(sys.argv[2],uid=1001,gid=int(sys.argv[3]));sys.argv=['spot-work']+sys.argv[4:];sys.exit(w.main(p))"
        def user():os.initgroups(self.user.pw_name,self.user.pw_gid);os.setgid(self.user.pw_gid);os.setuid(1001)
        env=os.environ.copy();env.update(HOME=self.user.pw_dir,BASH_ENV='/dev/null',ENV='/dev/null')
        child=subprocess.Popen([sys.executable,'-c',code,str(self.module),str(self.protocol.runtime),str(self.user.pw_gid),*args],env=env,cwd='/',preexec_fn=user,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
        self.clients.append(child);return child

    def wait_lease(self):
        for i in range(100):
            records=self.protocol.blockers()
            if records:return records
            time.sleep(0.02)
        self.fail('test command never published its lease')

    def test_cross_uid_existing_job_finishes_but_new_job_cannot_enter_fence(self):
        child=self.client('run','--',sys.executable,'-c','import time;time.sleep(1.2)')
        self.assertEqual(self.wait_lease()[0]['reason'],'running_job')
        # Existing work now refuses a normal fresh seal. Inject a closed
        # boundary only to retain this private fault/continuation regression.
        with self.protocol.locked():self.protocol.write_state('draining')
        with self.assertRaises(RuntimeError):
            with self.protocol.commit():self.fail('must not release while job runs')
        rejected=self.client('run','--',sys.executable,'-c','raise RuntimeError("SHOULD_NOT_RUN")')
        out,err=rejected.communicate(timeout=5);self.assertNotEqual(rejected.returncode,0)
        self.assertNotIn('SHOULD_NOT_RUN',err)
        child.communicate(timeout=5);self.assertEqual(child.returncode,0)
        self.assertEqual(self.protocol.blockers(),[])
        self.protocol.unseal()

    def test_cross_uid_admitted_job_wins_and_refused_seal_keeps_new_work_open(self):
        child=self.client('run','--',sys.executable,'-c','import time;time.sleep(1.2)')
        self.wait_lease()
        with self.assertRaises(work.SealBlocked):self.protocol.seal()
        self.assertEqual(self.protocol.state(),'open')
        another=self.client('run','--',sys.executable,'-c','pass')
        out,err=another.communicate(timeout=5);self.assertEqual(another.returncode,0,err)
        child.communicate(timeout=5);self.assertEqual(child.returncode,0)
        self.assertEqual(self.protocol.blockers(),[])

    def test_cross_uid_job_cannot_enter_between_locked_seal_check_and_publication(self):
        checked=threading.Event();release=threading.Event();results=[];original=self.protocol.blockers_unlocked
        def blockers():
            found=original();checked.set()
            if not release.wait(5):raise RuntimeError('test seal barrier expired')
            return found
        def seal():
            try:self.protocol.seal();results.append('sealed')
            except Exception as error:results.append(type(error).__name__)
        thread=threading.Thread(target=seal);child=None
        with patch.object(self.protocol,'blockers_unlocked',side_effect=blockers):
            try:
                thread.start();self.assertTrue(checked.wait(2))
                child=self.client('run','--',sys.executable,'-c','raise RuntimeError("MUST_NOT_START")')
                time.sleep(.08);self.assertIsNone(child.poll())
            finally:release.set();thread.join(5)
        self.assertFalse(thread.is_alive());self.assertEqual(results,['sealed'])
        out,err=child.communicate(timeout=5);self.assertNotEqual(child.returncode,0)
        self.assertIn('admission closed',err);self.assertNotIn('MUST_NOT_START',err)
        self.assertEqual(self.protocol.state(),'draining');self.assertEqual(self.protocol.blockers(),[])

    def test_SIGKILL_preaction_controller_recovers_without_refencing_admitted_work(self):
        spec=importlib.util.spec_from_file_location('drain',self.base/'spot_drain.py')
        drain=importlib.util.module_from_spec(spec);spec.loader.exec_module(drain)
        cfg={'account':'537112465379','region':'ap-northeast-2','asg':'isolated-test-only',
             'instance_id':'i-0123456789abcdef0','home_volume':'vol-0123456789abcdef0',
             'home_uuid':'00000000-0000-0000-0000-000000000000','uid':1001}
        journal=self.base/'private/drain.json'
        code='import json,sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import spot_work,spot_drain;p=spot_work.Protocol(sys.argv[2]);t=spot_drain.Transaction(json.loads(sys.argv[4]),p,Path(sys.argv[3]));t.begin({"user@1001.service":"inactive","docker.service":"inactive"})'
        with self.protocol.locked():
            controller=subprocess.Popen([sys.executable,'-c',code,str(self.base),str(self.protocol.runtime),str(journal),json.dumps(cfg)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
            self.clients.append(controller)
            deadline=time.monotonic()+3
            while not journal.exists():
                self.assertIsNone(controller.poll());self.assertLess(time.monotonic(),deadline);time.sleep(.01)
            saved=json.loads(journal.read_text());self.assertEqual(saved['phase'],'created')
            self.assertEqual(saved['owner']['pid'],controller.pid)
            self.assertEqual(saved['owner']['pid_start'],work.process_start(controller.pid))
            os.kill(controller.pid,signal.SIGKILL);controller.communicate(timeout=5)
            self.assertEqual(controller.returncode,-signal.SIGKILL)
        child=self.client('run','--',sys.executable,'-c','import time;time.sleep(1.2)');self.wait_lease()
        events=[]
        class Operations:
            def group(ops):events.append('group');return {'Instances':[{'InstanceId':cfg['instance_id'],'LifecycleState':'InService','ProtectedFromScaleIn':True}]}
            def protect(ops):events.append('protection_readback_injected')
            def home(ops):raise AssertionError('no pre-action home IO')
            def services(ops,units):raise AssertionError('no pre-action service control')
            def gateway(ops,*args):raise AssertionError('no pre-action Gateway control')
            def verified(ops,*args):raise AssertionError('no pre-action app probe')
        tx=drain.Transaction(cfg,self.protocol,journal)
        try:
            with patch.object(self.protocol,'write_state',wraps=self.protocol.write_state) as write:
                self.assertEqual(tx.recover(Operations()),'recovered')
            write.assert_not_called();self.assertEqual(self.protocol.state(),'open')
            self.assertTrue(self.protocol.blockers());self.assertEqual(events,['group','protection_readback_injected'])
            self.assertEqual(tx.read()['recovery_outcome'],'no_actions_started')
        finally:tx.close()
        child.communicate(timeout=5);self.assertEqual(child.returncode,0);self.assertEqual(self.protocol.blockers(),[])

    def test_double_fork_setsid_descendant_keeps_lease_after_main_exit(self):
        code='import os,time;pid=os.fork();\nif pid==0:\n os.setsid();pid=os.fork();\n if pid==0:time.sleep(1.2)\n os._exit(0)\nos._exit(0)'
        started=time.monotonic();child=self.client('run','--',sys.executable,'-c',code)
        self.wait_lease();time.sleep(0.2)
        self.assertIsNone(child.poll());self.assertTrue(self.protocol.blockers())
        child.communicate(timeout=5);self.assertEqual(child.returncode,0)
        self.assertGreaterEqual(time.monotonic()-started,1.1)
        self.assertEqual(self.protocol.blockers(),[])

    def test_manual_extension_during_drain_acknowledged_and_cancels_commit(self):
        self.protocol.seal();child=self.client('extend','--seconds','60')
        out,err=child.communicate(timeout=5);self.assertEqual(child.returncode,0,err)
        ident=json.loads(out)['id']
        with self.assertRaises(RuntimeError):
            with self.protocol.commit():self.fail('must not release after acknowledged extension')
        cancel=self.client('cancel',ident);cancel.communicate(timeout=5);self.assertEqual(cancel.returncode,0)
        with self.protocol.commit():pass
        late=self.client('extend','--seconds','60');late.communicate(timeout=5)
        self.assertNotEqual(late.returncode,0);self.assertEqual(self.protocol.blockers(),[])

    def test_killed_wrapper_does_not_make_child_idle(self):
        child=self.client('run','--',sys.executable,'-c','import time;time.sleep(1.5)')
        self.wait_lease();child.kill();child.communicate(timeout=5)
        self.assertTrue(self.protocol.blockers())
        # Even after the finite fixture exits, missing cleanup is unknown, not
        # permission to terminate a real possibly-orphaned workload.
        time.sleep(1.6);self.assertTrue(self.protocol.blockers())


if __name__=='__main__':unittest.main()
