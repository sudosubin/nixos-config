"""Offline lifecycle/admission tests. No real gateway, service or AWS API."""
import importlib.util
from pathlib import Path
import time
import unittest

spec=importlib.util.spec_from_file_location('gateway',Path(__file__).with_name('spot_gateway.py'))
gw=importlib.util.module_from_spec(spec);spec.loader.exec_module(gw)


class Manager:
    unit='test.service'
    def __init__(self):self.identity={'pid':42,'pid_start':7};self.fenced=True;self.events=[]
    def current(self):return dict(self.identity)
    def fence_verified(self):return self.fenced
    def stop(self,target):self.events.append('stop');self.identity={'pid':0,'pid_start':0}
    def assert_stopped(self):assert self.identity['pid']==0
    def start(self):self.events.append('start');self.identity={'pid':43,'pid_start':8}


class RPC:
    def __init__(self,manager):self.manager=manager;self.calls=[];self.override={};self.owner=None;self.boot_id='boot';self.expiry=None
    def __call__(self,method,params):
        self.calls.append((method,dict(params)))
        if method in self.override:
            value=self.override[method]
            if isinstance(value,Exception):raise value
            return value
        if method=='system.info':return {'pid':self.manager.identity['pid'],'processInstanceId':'process-'+str(self.manager.identity['pid'])}
        if method=='status':return {'pid':self.manager.identity['pid'],'runtimeVersion':'2026.10.3','shutdownBudget':{'nativeStopBudget':True,'activeWork':dict.fromkeys(['rootRequests','cronRuns','sessionMutations','terminalPersistence','lifecycleWrites'],0)}}
        if method=='gateway.suspend.prepare':
            self.owner=params['requestId'];self.expiry=time.time()*1000+120000
            return {'status':'ready','suspensionId':'lease','expiresAtMs':self.expiry,'activeCount':0,'blockers':[],'writeCustody':[]}
        if method=='gateway.suspend.status':
            if self.owner is None:return {'status':'running'}
            return {'status':'ready','ownerId':self.owner,'expiresAtMs':self.expiry,'writeCustody':[]}
        if method=='gateway.suspend.resume':self.owner=None;return {'ok':True,'status':'running'}
        if method=='gateway.suspend.handoff':self.manager.events.append('commit');return {'status':'committed','suspensionId':'lease','expiresAtMs':self.expiry}
        raise AssertionError(method)


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.manager=Manager();self.rpc=RPC(self.manager);self.records=[];self.fenced=True
        self.g=gw.Gateway(self.rpc,self.manager,lambda:self.fenced,lambda record:self.records.append(dict(record)))
        self.addCleanup(self.g.close)

    def test_projection_never_claims_complete_idle(self):
        self.assertFalse(self.g.observe()['complete_idle_proof'])
        self.assertFalse(any(m.startswith('gateway.suspend') for m,p in self.rpc.calls))

    def test_infinite_native_stop_budget_is_not_mistaken_for_missing_capability(self):
        status=self.rpc('status',{});status['shutdownBudget']['nativeStopBudget']=False
        self.rpc.override['status']=status
        self.assertFalse(self.g.observe()['complete_idle_proof'])
        self.g.acquire()  # still requires loaded infinite timeout + no SIGKILL
        self.assertEqual(self.g.effect,'held')

    def test_acquire_uses_preserve_and_never_forced_drain(self):
        self.g.acquire()
        p=next(p for m,p in self.rpc.calls if m=='gateway.suspend.prepare')
        self.assertIs(p['drain'],False);self.assertEqual(p['terminalPolicy'],'preserve')

    def test_outer_fence_required_before_any_mutating_rpc(self):
        self.fenced=False
        with self.assertRaises(gw.Unsafe):self.g.acquire()
        self.assertEqual(self.rpc.calls,[])

    def test_loaded_restart_and_stop_safety_policy_required(self):
        self.manager.fenced=False
        with self.assertRaises(gw.Unsafe):self.g.acquire()
        self.assertEqual(self.rpc.calls,[])

    def test_busy_acquire_leaves_existing_work_and_no_stop(self):
        self.rpc.override['gateway.suspend.prepare']={'status':'busy','reason':'active-work','activeCount':1,'blockers':[{'kind':'agent-run','count':1}],'writeCustody':[]}
        with self.assertRaises(gw.Unsafe):self.g.acquire()
        self.g.rollback();self.assertEqual(self.manager.events,[])
        self.assertFalse(any(m=='gateway.suspend.resume' for m,p in self.rpc.calls))

    def test_malformed_busy_not_treated_as_clean_rejection(self):
        self.rpc.override['gateway.suspend.prepare']={'status':'busy'}
        with self.assertRaises(gw.Unsafe):self.g.acquire()
        with self.assertRaises(gw.Unsafe):self.g.rollback()

    def test_pid_mismatch_prevents_suspend(self):
        self.rpc.override['system.info']={'pid':99,'processInstanceId':'other'}
        with self.assertRaises(gw.Unsafe):self.g.acquire()
        self.assertFalse(any(m=='gateway.suspend.prepare' for m,p in self.rpc.calls))

    def test_changed_worker_prevents_renewal(self):
        self.g.acquire();self.manager.identity={'pid':99,'pid_start':88}
        with self.assertRaises(gw.Unsafe):self.g.renew()

    def test_unknown_owner_prevents_stop(self):
        self.g.acquire();self.rpc.override['gateway.suspend.status']={'status':'ready','ownerId':'other','expiresAtMs':self.rpc.expiry,'writeCustody':[]}
        with self.assertRaises(gw.Unsafe):self.g.stop()
        self.assertEqual(self.manager.events,[])

    def test_stop_commit_is_bound_to_process_and_lease(self):
        self.g.acquire();self.g.stop()
        p=next(p for m,p in self.rpc.calls if m=='gateway.suspend.handoff')
        self.assertEqual(p['target'],{'pid':42,'processInstanceId':'process-42'});self.assertIs(p['commit'],True)
        self.assertEqual(self.manager.events,['commit','stop']);self.assertTrue(self.g.stopped)

    def test_failed_commit_cannot_fall_back_to_systemctl_stop(self):
        self.g.acquire();self.rpc.override['gateway.suspend.handoff']=RuntimeError('uncertain')
        with self.assertRaises(RuntimeError):self.g.stop()
        self.assertEqual(self.manager.events,[])

    def test_mismatched_commit_ack_not_authority_to_stop(self):
        self.g.acquire();self.rpc.override['gateway.suspend.handoff']={'status':'committed','suspensionId':'other','expiresAtMs':self.rpc.expiry}
        with self.assertRaises(gw.Unsafe):self.g.stop()
        self.assertEqual(self.manager.events,[])

    def test_failed_renewal_state_cannot_authorize_stop(self):
        self.g.acquire();self.g.failed=True
        with self.assertRaises(gw.Unsafe):self.g.stop()
        self.assertEqual(self.manager.events,[])

    def test_lease_expiry_is_not_permission_to_stop(self):
        self.g.acquire();self.rpc.expiry=time.time()*1000-1
        with self.assertRaises(gw.Unsafe):self.g.stop()
        self.assertEqual(self.manager.events,[])

    def test_positive_or_unknown_custody_blocks(self):
        self.g.acquire()
        for value in [None,{},[{'phase':'backup','count':1}],[{'phase':'backup','count':True}],[{'phase':'backup','count':-1}]]:
            with self.subTest(value=value):
                self.rpc.override['gateway.suspend.status']={'status':'ready','ownerId':self.rpc.owner,'expiresAtMs':self.rpc.expiry,'writeCustody':value}
                with self.assertRaises(gw.Unsafe):self.g.stop()
        self.assertEqual(self.manager.events,[])

    def test_ready_label_cannot_override_contradictory_active_work(self):
        self.g.acquire()
        self.rpc.override['gateway.suspend.status']={'status':'ready','ownerId':self.rpc.owner,
            'expiresAtMs':self.rpc.expiry,'writeCustody':[],'activeCount':1}
        with self.assertRaises(gw.Unsafe):self.g.stop()
        self.assertEqual(self.manager.events,[])

    def test_unknown_or_draining_status_blocks(self):
        self.g.acquire()
        for status in ['draining','running','recovering','conflict']:
            with self.subTest(status=status):
                self.rpc.override['gateway.suspend.status']={'status':status,'ownerId':self.rpc.owner,'expiresAtMs':self.rpc.expiry,'writeCustody':[]}
                with self.assertRaises(gw.Unsafe):self.g.stop()

    def test_nonfinite_expiry_blocks(self):
        self.g.acquire()
        for expiry in [True,float('nan'),float('inf'),'later']:
            with self.subTest(expiry=expiry):
                self.rpc.expiry=expiry
                with self.assertRaises(gw.Unsafe):self.g.stop()

    def test_changed_lease_blocks_renewal(self):
        self.g.acquire();self.rpc.override['gateway.suspend.prepare']={'status':'ready','suspensionId':'other','expiresAtMs':self.rpc.expiry,'activeCount':0,'blockers':[],'writeCustody':[]}
        with self.assertRaises(gw.Unsafe):self.g.renew()

    def test_live_rollback_resumes_then_confirms_running(self):
        self.g.acquire();self.g.rollback();self.assertEqual(self.g.effect,'resumed')
        self.assertEqual(self.manager.events,[])

    def test_scheduler_recovery_failure_cannot_claim_reopened(self):
        self.g.acquire();self.rpc.override['gateway.suspend.resume']={'ok':False,'reason':'scheduler-resume-failed'}
        with self.assertRaises(gw.Unsafe):self.g.rollback()

    def test_committed_rollback_restarts_and_verifies_rpc(self):
        self.g.acquire();self.g.stop();self.g.rollback()
        self.assertEqual(self.manager.events,['commit','stop','start']);self.assertEqual(self.g.effect,'restored')
        self.assertEqual(self.g.target['pid'],43)

    def test_lost_prepare_response_recovered_by_same_request_id(self):
        self.rpc.override['gateway.suspend.prepare']=RuntimeError('lost reply')
        with self.assertRaises(RuntimeError):self.g.acquire()
        del self.rpc.override['gateway.suspend.prepare'];self.g.rollback()
        ids=[p['requestId'] for m,p in self.rpc.calls if m=='gateway.suspend.prepare']
        self.assertEqual(len(set(ids)),1);self.assertEqual(self.g.effect,'resumed')

    def test_request_id_journaled_before_mutation(self):
        self.g.acquire();self.assertEqual(self.records[0]['effect'],'uncertain')
        self.assertEqual(self.records[0]['request_id'],self.g.request_id)

    def test_maintenance_projection_malformed_not_idle(self):
        self.rpc.override['status']={'pid':42,'runtimeVersion':'2026.10.3','shutdownBudget':{'nativeStopBudget':True,'activeWork':{}}}
        with self.assertRaises(gw.Unsafe):self.g.observe()


class LoadedPolicyTests(unittest.TestCase):
    def manager(self,condition,timeout='infinity',kill='no'):
        class Service(gw.UserService):
            def show(self):return {'ExecCondition':condition,'TimeoutStopUSec':timeout,'SendSIGKILL':kill}
        return Service(None,'test.service','/nix/store/example/bin/spot-work')

    def test_only_enforced_non_ignoring_condition_is_accepted(self):
        row='{ path=/nix/store/example/bin/spot-work ; argv[]=/nix/store/example/bin/spot-work check-service-open test.service ; ignore_errors=no ; }'
        self.assertTrue(self.manager(row).fence_verified())
        self.assertFalse(self.manager(row.replace('ignore_errors=no','ignore_errors=yes')).fence_verified())
        self.assertFalse(self.manager(row,timeout='1min').fence_verified())
        self.assertFalse(self.manager(row,kill='yes').fence_verified())

    def test_different_condition_cannot_authorize_service_start(self):
        row='{ argv[]=/nix/store/other/bin/spot-work check-service-open test.service ; ignore_errors=no ; }'
        self.assertFalse(self.manager(row).fence_verified())


if __name__=='__main__':unittest.main()
