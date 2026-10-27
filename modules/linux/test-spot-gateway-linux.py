"""Real vendor gateway in disposable private systemd/mount/network namespaces.

No production HOME/config/credentials, channels, models, network routes, IAM or
production service control are available inside the canary. Only this test's
unique service is started/stopped. No additional EC2/EBS/controller is created.
"""
import importlib.util
import json
import multiprocessing
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
import uuid
import spot_validation

spec=importlib.util.spec_from_file_location('gateway',Path(__file__).with_name('spot_gateway.py'))
gw=importlib.util.module_from_spec(spec);spec.loader.exec_module(gw)
VENDOR=Path('/home/sudosubin/.local/share/openclaw-npm/lib/node_modules/openclaw')
_dspec=importlib.util.spec_from_file_location('drain',Path(__file__).with_name('spot_drain.py'))
drain=importlib.util.module_from_spec(_dspec);_dspec.loader.exec_module(drain)


def systemctl(*args,timeout=20,check=True):
    return subprocess.run(['systemctl',*args],capture_output=True,text=True,timeout=timeout,check=check).stdout


class CanaryRPC(gw.LocalRPC):
    def __init__(self,config,uid,base,unit):super().__init__(config,uid);self.base=base;self.unit=unit
    def environment(self):
        return {'HOME':str(self.base/'home'),'USER':self.user.pw_name,'LOGNAME':self.user.pw_name,
                'OPENCLAW_CONFIG_PATH':str(self.base/'home/openclaw.json'),
                'OPENCLAW_STATE_DIR':str(self.base/'home/state'),
                'PATH':'/run/current-system/sw/bin','OPENCLAW_NO_RESPAWN':'1'}
    def namespace_command(self,argv,timeout=20):
        pid=systemctl('show',self.unit,'--property=MainPID','--value').strip()
        if not pid.isdigit() or int(pid)==0:raise gw.Unsafe('private canary is not running')
        command=['nsenter','--target',pid,'--mount','--net','--','setpriv','--reuid='+str(self.uid),
                 '--regid='+str(self.user.pw_gid),'--init-groups','--no-new-privs',*argv]
        return subprocess.run(command,capture_output=True,text=True,timeout=timeout,env=self.environment())
    def user_command(self,argv,timeout=20):
        if argv[:2]==['systemctl','--user']:
            # UserService's state/condition/PID verification is unchanged; only
            # the test's dedicated SYSTEM service replaces the real user unit.
            return systemctl(*argv[2:],timeout=timeout)
        argv=list(argv)
        if len(argv)>1 and argv[1]==str(Path(gw.__file__).with_name('spot-gateway-rpc.mjs')):
            argv[1]=str(self.base/'source/spot-gateway-rpc.mjs')
        result=self.namespace_command(argv,timeout)
        if result.returncode:raise gw.Unsafe('private canary control failed')
        return result.stdout


@unittest.skipUnless(sys.platform=='linux' and os.geteuid()==0, 'requires root Linux')
class GatewayCanaryTests(unittest.TestCase):
    def setUp(self):
        self.resources=spot_validation.fixture_directives()  # fail before creating/spawning an unbounded fixture
        self.assertTrue(VENDOR.is_dir(), 'real vendor code is required, not a skipped proof')
        self.user=pwd.getpwuid(1001)
        self.base=Path(tempfile.mkdtemp(prefix='spot-gateway-validation-',dir='/run'));self.base.chmod(0o755)
        self.unit='spot-gateway-validation-'+uuid.uuid4().hex[:12]+'.service'
        self.unitfile=Path('/run/systemd/system')/self.unit
        self.gateway=None
        self.addCleanup(self.cleanup)
        self.home=self.base/'home';self.home.mkdir();os.chown(self.home,1001,self.user.pw_gid);self.home.chmod(0o700)
        self.mount=self.base/'vendor';self.mount.mkdir()
        public_source=self.base/'source';public_source.mkdir();public_source.chmod(0o755)
        for name in ['spot_work.py','spot_gateway.py','spot-gateway-rpc.mjs']:
            p=public_source/name;shutil.copyfile(Path(__file__).with_name(name),p);p.chmod(0o644)
        config=self.home/'openclaw.json'
        config.write_text(json.dumps({'gateway':{'mode':'local','port':18791,'bind':'loopback','auth':{'mode':'none'}},'channels':{}}))
        os.chown(config,1001,self.user.pw_gid);config.chmod(0o600)
        self.protocol=gw.work.Protocol(self.base/'runtime',uid=1001,gid=self.user.pw_gid);self.protocol.initialize()
        self.check=self.base/'service-check'
        self.check.write_text('#!'+sys.executable+'\nimport sys\nsys.path.insert(0,'+repr(str(public_source))+')\nimport spot_work\np=spot_work.Protocol('+repr(str(self.protocol.runtime))+',uid=1001,gid='+str(self.user.pw_gid)+')\nsys.exit(spot_work.main(p))\n')
        self.check.chmod(0o755)
        # Bind the app's compatible persisted runtime read-only into the private
        # namespace. The old base Node has a known SQLite bug; do not use it.
        node=Path('/home/sudosubin/.local/share/openclaw-npm/node-v26.4.0-linux-arm64/bin/node')
        self.assertTrue(node.is_file(), 'the supported persisted Node runtime is required, not a skipped proof')
        runtime_mount=self.base/'node-runtime';runtime_mount.mkdir()
        self.node=str(runtime_mount/'bin/node')
        self.unitfile.write_text('[Unit]\nDescription=Disposable model-free gateway admission validation\n[Service]\n'+self.resources+'Type=exec\nUser='+self.user.pw_name+'\nGroup='+str(self.user.pw_gid)+'\nEnvironment=HOME='+str(self.home)+'\nEnvironment=OPENCLAW_CONFIG_PATH='+str(config)+'\nEnvironment=OPENCLAW_STATE_DIR='+str(self.home/'state')+'\nEnvironment=OPENCLAW_NO_RESPAWN=1\nWorkingDirectory='+str(self.home)+'\nExecCondition='+str(self.check)+' check-service-open '+self.unit+'\nExecStart='+self.node+' '+str(self.mount/'openclaw.mjs')+' gateway run --allow-unconfigured --bind loopback --port 18791 --auth none\nRestart=on-failure\nTimeoutStopSec=infinity\nSendSIGKILL=no\nNoNewPrivileges=yes\nCapabilityBoundingSet=\nPrivateNetwork=yes\nPrivateMounts=yes\nPrivateTmp=yes\nProtectHome=yes\nProtectSystem=strict\nBindReadOnlyPaths='+str(VENDOR)+':'+str(self.mount)+' '+str(node.parent.parent)+':'+str(runtime_mount)+'\nReadWritePaths='+str(self.home)+' '+str(self.protocol.runtime)+'\n')
        systemctl('daemon-reload');systemctl('start',self.unit)
        self.rpc=CanaryRPC({'node':self.node,'vendor_dir':str(self.mount/'dist')},1001,self.base,self.unit)
        self.manager=gw.UserService(self.rpc,self.unit,str(self.check))
        self.gateway=gw.Gateway(self.rpc,self.manager,lambda:self.protocol.state()=='draining')
        deadline=time.monotonic()+50
        while True:
            try:self.gateway.observe();break
            except Exception:
                if self.manager.show().get('ActiveState')=='failed' or time.monotonic()>=deadline:raise
                time.sleep(0.5)
        self.assertTrue(self.manager.fence_verified())

    def cleanup(self):
        if self.gateway:self.gateway.close()
        if self.unitfile.exists():
            try:systemctl('stop',self.unit,timeout=10)
            except (subprocess.SubprocessError,gw.Unsafe):
                # Only a UNIQUE, isolated, model-free test service may be force
                # cleaned. Production work never receives this test deadline.
                assert self.unit.startswith('spot-gateway-validation-')
                systemctl('kill','--signal=KILL','--kill-whom=all',self.unit,check=False)
                systemctl('stop',self.unit,timeout=10,check=False)
            self.unitfile.unlink();systemctl('daemon-reload');systemctl('reset-failed',self.unit,check=False)
        shutil.rmtree(self.base)

    def acquire_when_idle(self):
        # RPC readiness is not whole-gateway idle. Bootstrap writes can still be
        # settling; only retry an explicit BUSY rejection, never unknown errors.
        deadline=time.monotonic()+35
        while True:
            try:self.gateway.acquire();return
            except gw.Busy:
                if time.monotonic()>=deadline:raise
                time.sleep(0.5)

    def mutate_session(self):
        return self.rpc.namespace_command([self.node,str(self.mount/'openclaw.mjs'),'gateway','call','sessions.patch',
            '--params',json.dumps({'key':'agent:main:spot-control-canary','label':'model-free-control-canary'}),'--json','--timeout','8000'],timeout=20)

    def interrupted_controller(self, mode):
        # Actual child death + actual vendor RPC/systemd; the AWS and EBS
        # observations alone are injected. This is NOT a production API test.
        config={'account':'537112465379','region':'ap-northeast-2','asg':'isolated-test-only',
                'instance_id':'i-0123456789abcdef0','home_volume':'vol-0123456789abcdef0',
                'home_uuid':'00000000-0000-0000-0000-000000000000','uid':1001,
                'gateway':{'unit':self.unit,'node':self.node,'vendor_dir':str(self.mount/'dist'),
                           'startup_check':str(self.check)}}
        journal=self.base/'journal/drain.json';ready=self.base/'controller-ready'
        before={'user@1001.service':'inactive','docker.service':'inactive'}
        unit=self.unit
        class DroppingRPC(CanaryRPC):
            dropped=False
            def __call__(rpc,method,params):
                value=super().__call__(method,params)
                wanted='gateway.suspend.prepare' if mode=='lost_prepare' else 'gateway.suspend.handoff'
                if mode in {'lost_prepare','lost_commit'} and method==wanted and not rpc.dropped:
                    rpc.dropped=True
                    raise TimeoutError('test-only lost reply AFTER real vendor dispatch')
                return value
        def coordinator():
            try:
                tx=drain.Transaction(config,self.protocol,journal)
                tx.begin(before)
                self.rpc.__class__=DroppingRPC
                gateway=gw.Gateway(self.rpc,self.manager,lambda:self.protocol.state()=='draining',tx.gateway)
                deadline=time.monotonic()+45
                while True:
                    try:gateway.acquire();break
                    except gw.Busy:
                        if time.monotonic()>=deadline:raise
                        time.sleep(0.3)
                    except TimeoutError:
                        if mode!='lost_prepare':raise
                        break
                if mode in {'lost_commit','committed_permit'}:
                    try:gateway.stop()
                    except TimeoutError:
                        if mode!='lost_commit':raise
                def waiting():
                    ready.write_text('ready')
                    while True:time.sleep(1)
                if mode=='committed_permit':
                    authority={**tx.owner,'units':[unit],'id':uuid.uuid4().hex}
                    tx.update(service_authority=authority)
                    with self.protocol.recover_services([unit],authority_id=authority['id']):waiting()
                else:waiting()
            except BaseException as error:
                ready.write_text('failed:'+type(error).__name__)
                raise
        child=multiprocessing.get_context('fork').Process(target=coordinator)
        child.start()
        try:
            deadline=time.monotonic()+60
            while not ready.exists():
                self.assertTrue(child.is_alive(),'isolated coordinator exited before the crash checkpoint')
                self.assertLess(time.monotonic(),deadline,'isolated crash checkpoint was not reached')
                time.sleep(0.05)
            self.assertEqual(ready.read_text(),'ready')
            saved=json.loads(journal.read_text())
            self.assertEqual(saved['owner']['pid'],child.pid)
            self.assertEqual(gw.work.process_start(child.pid),saved['owner']['pid_start'])
            os.kill(child.pid,signal.SIGKILL)
            child.join(timeout=5)
            self.assertEqual(child.exitcode,-signal.SIGKILL)
            if mode=='committed_permit':
                self.assertTrue((self.protocol.runtime/'recover-services').exists())
                systemctl('start',unit,check=False)
                self.assertEqual(systemctl('show',unit,'--property=MainPID','--value').strip(),'0')
            # A NEW controller, reconstructed exclusively from its durable
            # journal, never from the dead Python object's in-memory flags.
            events=[];protected=[False];outer=self
            class Operations:
                def group(ops):return {'DesiredCapacity':0,'Instances':[{'InstanceId':config['instance_id'],'LifecycleState':'InService','ProtectedFromScaleIn':protected[0]}]}
                def request_current(ops,group):return False
                def protect(ops):protected[0]=True;events.append('protection_readback')
                def home(ops):
                    if not protected[0]:raise AssertionError('home before protection')
                    outer.assertTrue(outer.home.is_dir());events.append('home_observed')
                def services(ops,units):raise AssertionError('must not control production user/Docker units')
                def gateway(ops,snapshot,boot_changed,authority,publish):
                    if not protected[0]:raise AssertionError('gateway before protection')
                    gateway=gw.Gateway(outer.rpc,outer.manager,lambda:outer.protocol.state()=='draining',publish)
                    gateway.restore_snapshot(snapshot,boot_changed=boot_changed,authority=authority)
                    events.append('gateway_verified')
                def verified(ops,before):
                    outer.assertEqual(outer.protocol.state(),'draining')
                    outer.assertTrue(outer.manager.current()['pid']>0)
                    events.append('restored')
            recovered=drain.Transaction(config,self.protocol,journal)
            try:
                deadline=time.monotonic()+100
                while True:
                    try:outcome=recovered.recover(Operations());break
                    except (gw.Unsafe,subprocess.SubprocessError):
                        if time.monotonic()>=deadline:raise
                        recovered.close();time.sleep(0.5)
                self.assertEqual(outcome,'recovered')
                self.assertEqual(self.protocol.state(),'open')
                self.assertEqual(recovered.read()['phase'],'recovered')
                self.assertFalse((self.protocol.runtime/'recover-services').exists())
                self.assertLess(events.index('protection_readback'),events.index('gateway_verified'))
                self.assertEqual(self.mutate_session().returncode,0)
            finally:recovered.close()
        finally:
            if child.is_alive():child.kill();child.join(timeout=5)

    def test_killed_held_controller_recovers_from_durable_owner(self):
        self.interrupted_controller('held')

    def test_killed_controller_lost_prepare_reply_resumes_same_owned_lease(self):
        self.interrupted_controller('lost_prepare')

    def test_killed_controller_lost_commit_reply_never_blindly_stops(self):
        self.interrupted_controller('lost_commit')

    def test_killed_committed_controller_retires_exact_dead_startup_permit(self):
        self.interrupted_controller('committed_permit')

    def test_vendor_busy_expiry_and_scheduler_recovery_fail_closed(self):
        # A separate process imports the exact installed vendor coordinator;
        # its injected counters simulate work without a model or live mutation.
        script=r'''import assert from 'node:assert/strict';
const dir=process.argv[1];
const c=await import('file://'+dir+'/gateway-suspend-coordinator-CvUFNpPI.mjs');
const a=await import('file://'+dir+'/gateway-work-admission-rc4ZgKq_.mjs');
let active=1,paused=false,failResume=false,now=Date.now();
const p={requestId:'model-free-vendor-contract',terminalPolicy:'preserve',drain:false,
 inspect:{getRootRequests:()=>active},nowMs:()=>now,pauseScheduling:()=>{paused=true},
 resumeScheduling:()=>{if(failResume)throw Error('test-only scheduler failure');paused=false}};
assert.equal(c.s(p).status,'busy');assert.equal(paused,false);
let work=a.k('model-free-test');assert.ok(work);work.release();
active=0;let first=c.s(p);assert.equal(first.status,'ready');assert.equal(a.k('late-work'),null);
now+=1000;let renewed=c.s(p);assert.equal(renewed.suspensionId,first.suspensionId);assert.ok(renewed.expiresAtMs>first.expiresAtMs);
assert.equal(c.i(first.suspensionId,true).ownerId,p.requestId);
now+=121000;assert.equal(c.i(first.suspensionId,true).status,'running');assert.equal(paused,false);
active=1;failResume=true;assert.equal(c.s(p).status,'recovering');assert.equal(a.k('must-stay-closed'),null);
assert.equal(c.l(first.suspensionId).ok,false);failResume=false;
await new Promise(resolve=>setTimeout(resolve,1200));assert.equal(c.i('none',true).status,'running');
work=a.k('recovered');assert.ok(work);work.release();
console.log('ACTUAL_VENDOR_BUSY_EXPIRY_AND_RECOVERY_PASSED');'''
        result=self.rpc.namespace_command([self.node,'--input-type=module','--eval',script,str(self.mount/'dist')],timeout=15)
        self.assertEqual(result.returncode,0);self.assertIn('ACTUAL_VENDOR_BUSY_EXPIRY_AND_RECOVERY_PASSED',result.stdout)

    def test_actual_prepare_renew_rejects_late_mutation_and_resume_restores_it(self):
        before=self.mutate_session();self.assertEqual(before.returncode,0)
        self.protocol.seal();self.acquire_when_idle();lease=self.gateway.lease_id;self.gateway.renew()
        self.assertEqual(lease,self.gateway.lease_id)
        rejected=self.mutate_session();self.assertNotEqual(rejected.returncode,0)
        # The CLI deliberately redacts errors. Prove causality with the same
        # mutation before/held/resumed AND a healthy, owned control lease while
        # held, not a brittle error string or an unrelated connection failure.
        self.gateway.check()
        self.gateway.rollback();self.protocol.unseal()
        self.assertEqual(self.mutate_session().returncode,0)

    def test_actual_committed_stop_and_protected_rollback_restart(self):
        original=self.gateway.target['pid'];self.protocol.seal();self.acquire_when_idle();self.gateway.stop()
        self.assertTrue(self.gateway.stopped);self.manager.assert_stopped()
        # A manual/restart request cannot bypass the loaded condition.
        systemctl('start',self.unit,check=False)
        self.assertEqual(systemctl('show',self.unit,'--property=MainPID','--value').strip(),'0')
        with self.protocol.recover_services([self.unit]):
            self.gateway.rollback()
        self.protocol.unseal()
        self.assertNotEqual(self.gateway.target['pid'],original)
        self.assertTrue(self.gateway.observe()['observable'])


if __name__=='__main__':unittest.main()
