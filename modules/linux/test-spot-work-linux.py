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
import time
import unittest

spec=importlib.util.spec_from_file_location('work',Path(__file__).with_name('spot_work.py'))
work=importlib.util.module_from_spec(spec);spec.loader.exec_module(work)


@unittest.skipUnless(sys.platform=='linux' and os.geteuid()==0,'requires isolated root Linux verification')
class LinuxAdmissionTests(unittest.TestCase):
    def setUp(self):
        try:self.user=pwd.getpwuid(1001)
        except KeyError:self.skipTest('test UID 1001 not present')
        self.base=Path(tempfile.mkdtemp(prefix='spot-work-validation-',dir='/run'));self.base.chmod(0o755)
        self.module=self.base/'spot_work.py';shutil.copyfile(Path(__file__).with_name('spot_work.py'),self.module);self.module.chmod(0o644)
        self.protocol=work.Protocol(self.base/'runtime',uid=1001,gid=self.user.pw_gid);self.protocol.initialize()
        self.clients=[]

    def tearDown(self):
        for child in self.clients:
            if child.poll() is None:child.kill()
            child.wait(timeout=5)
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
        self.protocol.seal()
        with self.assertRaises(RuntimeError):
            with self.protocol.commit():self.fail('must not release while job runs')
        rejected=self.client('run','--',sys.executable,'-c','raise RuntimeError("SHOULD_NOT_RUN")')
        out,err=rejected.communicate(timeout=5);self.assertNotEqual(rejected.returncode,0)
        self.assertNotIn('SHOULD_NOT_RUN',err)
        child.communicate(timeout=5);self.assertEqual(child.returncode,0)
        self.assertEqual(self.protocol.blockers(),[])
        self.protocol.unseal()

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
