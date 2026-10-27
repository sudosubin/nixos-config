"""Root-only Linux integration tests, using an isolated /run directory.

Never changes real admission, services, AWS state, home, or user configuration.
Only tiny test-owned commands run as UID 1001; all have finite waits. The CLI
entry creates private PID/mount/network namespaces and empty homes/run before
executing cases. No production process/service/config/credential is inherited.
"""
import argparse
import ctypes
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
        except KeyError:self.fail('test UID 1001 required; no skip-as-proof')
        self.base=Path(tempfile.mkdtemp(prefix='spot-work-validation-',dir='/run'));self.base.chmod(0o755)
        self.module=self.base/'spot_work.py'
        for name in ['spot_work.py','spot_drain.py']:
            target=self.base/name;shutil.copyfile(Path(__file__).with_name(name),target);target.chmod(0o644)
        self.protocol=work.Protocol(self.base/'runtime',uid=1001,gid=self.user.pw_gid);self.protocol.initialize()
        self.clients=[]
        self.home=self.base/'home';self.home.mkdir();os.chown(self.home,1001,self.user.pw_gid);self.home.chmod(0o700)
        self.data=self.base/'data';self.data.mkdir();os.chown(self.data,1001,self.user.pw_gid);self.data.chmod(0o700)

    def tearDown(self):
        for child in self.clients:
            if child.poll() is None:child.kill()
            child.wait(timeout=5)
            for stream in [child.stdout,child.stderr]:
                if stream is not None and not stream.closed:stream.close()
        # Non-barrier descendants sleep at most 1.5s; private barriers are released in finally.
        time.sleep(1.6)
        shutil.rmtree(self.base)

    def user_command(self,argv):
        # Do not fork a Python preexec_fn while a seal/barrier thread is live.
        return ['setpriv','--reuid=1001','--regid='+str(self.user.pw_gid),'--init-groups','--no-new-privs',*argv]

    def environment(self):
        return {'PATH':'/run/current-system/sw/bin','HOME':str(self.home),'USER':self.user.pw_name,
                'LOGNAME':self.user.pw_name,'BASH_ENV':'/dev/null','ENV':'/dev/null',
                'PYTHONDONTWRITEBYTECODE':'1','PYTHONWARNINGS':'error::ResourceWarning'}

    def client(self,*args,inject=''):
        code="import ctypes,importlib.util,json,os,sys,time\nfrom pathlib import Path\nspec=importlib.util.spec_from_file_location('work',sys.argv[1]);w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w);p=w.Protocol(sys.argv[2],uid=1001,gid=int(sys.argv[3]))\n"+inject+"\nsys.argv=['spot-work']+sys.argv[4:];sys.exit(w.main(p))"
        child=subprocess.Popen(self.user_command([sys.executable,'-I','-c',code,str(self.module),str(self.protocol.runtime),str(self.user.pw_gid),*args]),env=self.environment(),cwd='/',stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
        self.clients.append(child);return child

    def wait_file(self,path):
        deadline=time.monotonic()+5
        while not path.exists():
            self.assertLess(time.monotonic(),deadline,'private fixture marker missing');time.sleep(.01)

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

    def barrier_body(self,started,release,finished):
        return ('import os,time\nfrom pathlib import Path\n'
                +f'Path({str(started)!r}).write_text(str(os.getpid()))\n'
                +'limit=time.monotonic()+10\n'
                +f'while not Path({str(release)!r}).exists():\n'
                +' if time.monotonic()>limit:raise RuntimeError("private fixture release missing")\n time.sleep(.01)\n'
                +f'Path({str(finished)!r}).write_text("finished")\n')

    def test_uncertain_spawn_receipt_preserves_actual_live_work_and_sticky_custody(self):
        started=self.data/'started';release=self.data/'release';finished=self.data/'finished'
        inject='''
def uncertain_spawn(argv,**kwargs):
 pid=os.fork()
 if pid==0:
  os.setsid();os.execv(argv[0],argv)
 raise OSError('private fixture receipt lost AFTER real fork')
w.subprocess.Popen=uncertain_spawn
'''
        child=self.client('run','--',sys.executable,'-I','-c',self.barrier_body(started,release,finished),inject=inject)
        try:
            self.wait_file(started);child.wait(timeout=5);self.assertNotEqual(child.returncode,0)
            self.assertFalse(finished.exists());self.assertTrue(self.protocol.blockers())
            with self.assertRaises(work.SealBlocked):self.protocol.seal()
            self.assertEqual(self.protocol.state(),'open')
            self.assertEqual(self.protocol.blockers(now=time.time()+1000)[0]['reason'],'stale_job_unknown')
        finally:release.touch()
        out,err=child.communicate(timeout=5);self.wait_file(finished)
        self.assertIn('receipt lost AFTER real fork',err);self.assertNotIn('ResourceWarning',err)
        self.assertTrue(self.protocol.blockers())  # dead wrapper is never retrospectively trusted

    def test_missing_executable_is_not_an_automatic_unknown_lease_clear(self):
        child=self.client('run','--','/does-not-exist/spot-private-job-fixture')
        out,err=child.communicate(timeout=5);self.assertNotEqual(child.returncode,0)
        self.assertTrue(self.protocol.blockers())
        with self.assertRaises(work.SealBlocked):self.protocol.seal()
        self.assertEqual(self.protocol.state(),'open')

    def test_real_non_SIGCHLD_clone_child_is_waited_before_job_retirement(self):
        started=self.data/'clone-started';release=self.data/'clone-release';finished=self.data/'clone-finished'
        body=self.barrier_body(started,release,finished)
        inject='''
original=w.subprocess.Popen
def extra_clone(argv,**kwargs):
 child=original(argv,**kwargs)
 machine=os.uname().machine
 number={'aarch64':220,'x86_64':56}.get(machine)
 if number is None:raise RuntimeError('native clone ABI required; not a skipped proof')
 libc=ctypes.CDLL(None,use_errno=True);pid=libc.syscall(number,0,0,0,0,0)
 if pid<0:raise OSError(ctypes.get_errno(),'fixture clone failed')
 if pid==0:os.execv(sys.executable,[sys.executable,'-I','-c',BODY])
 return child
w.subprocess.Popen=extra_clone
'''.replace('BODY',repr(body))
        child=self.client('run','--',sys.executable,'-I','-c','pass',inject=inject)
        try:
            self.wait_file(started);time.sleep(.15)
            self.assertIsNone(child.poll());self.assertTrue(self.protocol.blockers());self.assertFalse(finished.exists())
            with self.assertRaises(work.SealBlocked):self.protocol.seal()
        finally:release.touch()
        out,err=child.communicate(timeout=5);self.assertEqual(child.returncode,0,err)
        self.assertTrue(finished.exists());self.assertEqual(self.protocol.blockers(),[])

    def test_finished_job_does_not_delete_changed_boot_bound_custody(self):
        started=self.data/'bound-started';release=self.data/'bound-release';finished=self.data/'bound-finished'
        child=self.client('run','--',sys.executable,'-I','-c',self.barrier_body(started,release,finished))
        try:
            self.wait_file(started);records=self.wait_lease();ident=records[0]['id']
            data,_=work.read_record(self.protocol.leases/ident,{1001});data['boot_id']='private-fixture-other-boot'
            self.protocol.publish(self.protocol.leases/ident,data);os.chown(self.protocol.leases/ident,1001,self.user.pw_gid)
        finally:release.touch()
        out,err=child.communicate(timeout=5);self.assertNotEqual(child.returncode,0)
        self.assertTrue(finished.exists());self.assertIn('record changed',err)
        self.assertEqual(self.protocol.blockers()[0]['reason'],'invalid_lease_unknown')

    def test_actual_immutable_CLI_ignores_shell_and_python_startup_hooks_before_fenced_acceptance(self):
        self.assertIsNotNone(TOOL,'compiled CLI is required, not a skipped proof')
        default=work.Protocol();subprocess.run([str(TOOL),'initialize'],env=self.environment(),check=True,capture_output=True)
        default.seal()
        startup=self.data/'startup-marker';payload=self.data/'payload-marker';module=self.data/'sitecustomize.py'
        module.write_text('from pathlib import Path\nPath('+repr(str(startup))+').write_text("MUST_NOT_RUN")\n')
        bash=self.data/'bash-hook';bash.write_text('printf forbidden > '+str(startup)+'\n')
        env=self.environment();env.update(PYTHONPATH=str(self.data),BASH_ENV=str(bash))
        child=subprocess.Popen(self.user_command([str(TOOL),'run','--','/bin/sh','-c','printf forbidden > '+str(payload)]),env=env,
                               cwd='/',stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        self.clients.append(child);out,err=child.communicate(timeout=5)
        self.assertEqual(child.returncode,75,err);self.assertIn('admission closed',err)
        self.assertFalse(startup.exists());self.assertFalse(payload.exists());self.assertEqual(default.blockers(),[])
        default.unseal()

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


TOOL=None


def main():
    global TOOL
    parser=argparse.ArgumentParser();parser.add_argument('--inside',action='store_true')
    parser.add_argument('--tool',type=Path,required=True);parser.add_argument('-v',action='store_true')
    args=parser.parse_args()
    if sys.platform!='linux' or os.geteuid()!=0:raise RuntimeError('root Linux required; no skip-as-proof')
    TOOL=args.tool.resolve(strict=True)
    if not str(TOOL).startswith('/nix/store/'):raise RuntimeError('immutable compiled CLI required')
    here=Path(__file__).parent
    names=[Path(__file__).name,'spot_work.py','spot_drain.py']
    if not args.inside:
        with tempfile.TemporaryDirectory(prefix='spot-work-public-',dir='/run') as tmp:
            target=Path(tmp)
            for name in names:shutil.copyfile(here/name,target/name)
            env={'PATH':'/run/current-system/sw/bin','HOME':'/root','PYTHONDONTWRITEBYTECODE':'1','PYTHONWARNINGS':'error::ResourceWarning'}
            result=subprocess.run(['unshare','--mount','--pid','--fork','--mount-proc','--net',sys.executable,
                                   str(target/Path(__file__).name),'--inside','--tool',str(TOOL)],env=env,cwd='/run')
            raise SystemExit(result.returncode)
    sources={name:(here/name).read_bytes() for name in names};system=Path('/run/current-system').resolve(strict=True)
    subprocess.run(['mount','--make-rprivate','/'],check=True)
    for path,mode in [('/home','0700'),('/root','0700'),('/tmp','1777'),('/run','0755')]:
        subprocess.run(['mount','-t','tmpfs','-o','mode='+mode+',size=128M','tmpfs',path],check=True)
    Path('/run/current-system').symlink_to(system);here.mkdir(parents=True,mode=0o755)
    for name,data in sources.items():(here/name).write_bytes(data)
    if ctypes.CDLL(None,use_errno=True).prctl(38,1,0,0,0)!=0:raise RuntimeError('NoNewPrivileges failed')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LinuxAdmissionTests))
    print(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
                      'private_PID_mount_network_and_empty_homes':True,'production_rollout':False,'all_producers_verified':False}))
    raise SystemExit(0 if result.wasSuccessful() and not result.skipped and result.testsRun==12 else 1)


if __name__=='__main__':main()
