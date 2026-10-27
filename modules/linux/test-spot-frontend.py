"""Content-free frontend epoch tests; no app, credential, model or AWS calls."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('frontend',Path(__file__).with_name('spot_frontend.py'))
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
IDLE={'initialized':True,'queued':0,'pending_steer':False,'processing':False,'actions':0,'draft':False}


class FrontendTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.p=f.work.Protocol(Path(self.tmp.name)/'runtime',uid=os.geteuid(),gid=os.getegid(),root_uid=os.geteuid(),boot_id='test')
        self.p.initialize()
        for name,value in [('process_start',123),('process_uid',os.geteuid())]:
            p=patch.object(f.work,name,return_value=value);p.start();self.addCleanup(p.stop)
        p=patch.object(f,'descendant',return_value=True);self.descendant=p.start();self.addCleanup(p.stop)
        self.startup=self.p.create('job')
        self.front=f.Frontend(self.p,parent=os.getpid())
        self.seq=0;self.ident=None

    def attach(self):
        r=self.front.attach(self.startup['id']);self.ident=r['id'];return r

    def call(self,action,values=None):
        self.seq+=1;return self.front.invoke(self.ident,self.seq,action,values)

    def record(self):return json.loads((self.p.runtime/'participants'/self.ident).read_text())

    def fault_fence(self):
        with self.p.locked():self.p.write_state('draining')  # private fixture, not a fresh seal

    def test_bootstrap_epoch_and_participant_overlap_before_handoff(self):
        original=self.p.publish;seen=[]
        def publish(path,data,**kwargs):
            original(path,data,**kwargs)
            if path.parent==self.p.runtime/'participants':
                seen.append((self.p.leases/self.startup['id']).exists())
                self.assertEqual(len(list(self.p.leases.iterdir())),2)
        with patch.object(self.p,'publish',side_effect=publish):self.attach()
        self.assertEqual(seen,[True]);self.assertFalse((self.p.leases/self.startup['id']).exists())
        self.assertEqual(len(list(self.p.leases.iterdir())),1)
        self.assertFalse(self.record()['initialized'])

    def test_unknown_or_foreign_startup_is_not_adopted(self):
        self.descendant.return_value=False
        with self.assertRaises(ValueError):self.attach()
        self.assertTrue((self.p.leases/self.startup['id']).exists())
        self.assertEqual(list((self.p.runtime/'participants').iterdir()),[])

    def test_closed_admission_does_not_create_frontend_epoch(self):
        self.fault_fence()
        with self.assertRaises(RuntimeError):self.attach()
        self.assertEqual(len(list(self.p.leases.iterdir())),1)

    def test_local_idle_retires_only_own_epoch_not_participant_or_other_work(self):
        self.attach();other=self.p.create('job');self.call('state',IDLE)
        self.assertIsNone(self.record()['epoch']);self.assertTrue((self.p.leases/other['id']).exists())
        self.assertTrue(any(b['reason']=='participant_unverified' for b in self.p.blockers()))

    def test_each_frontend_busy_source_keeps_epoch(self):
        self.attach()
        for change in [{'initialized':False},{'queued':1},{'pending_steer':True},{'processing':True},{'actions':1},{'draft':True}]:
            with self.subTest(change=change):
                self.call('state',{**IDLE,**change});self.assertIsNotNone(self.record()['epoch'])

    def test_new_input_lease_is_present_before_admission_ack(self):
        self.attach();self.call('state',IDLE)
        self.assertTrue(self.call('admit')['accepted'])
        self.assertTrue((self.p.leases/self.record()['epoch']).exists())

    def test_new_input_behind_fence_is_rejected_without_cancelling_existing_epoch(self):
        self.attach();epoch=self.record()['epoch'];self.fault_fence()
        self.assertFalse(self.call('admit')['accepted'])
        self.assertEqual(self.record()['epoch'],epoch);self.assertEqual(self.record()['admission_rejections'],1)
        self.assertTrue((self.p.leases/epoch).exists())

    def test_unexpected_busy_state_behind_fence_is_unknown_not_idle(self):
        self.attach();self.call('state',IDLE);self.fault_fence()
        self.assertFalse(self.call('state',{**IDLE,'processing':True})['accepted'])
        self.assertFalse(self.record()['healthy']);self.assertTrue(self.p.blockers())

    def test_fault_cannot_be_erased_by_later_empty_state(self):
        self.attach();epoch=self.record()['epoch'];self.call('fault');self.call('state',IDLE)
        self.assertFalse(self.record()['healthy']);self.assertEqual(self.record()['epoch'],epoch)
        with self.assertRaises(RuntimeError):self.call('close')

    def test_fault_after_lost_ack_can_only_add_unknown_not_release(self):
        self.attach();self.call('state',{**IDLE,'queued':1})
        self.front.invoke(self.ident,self.seq,'fault')
        self.assertFalse(self.record()['healthy']);self.assertIsNotNone(self.record()['epoch'])

    def test_heartbeat_never_completes_work(self):
        self.attach();epoch=self.record()['epoch'];self.call('heartbeat')
        self.assertEqual(self.record()['epoch'],epoch)

    def test_stale_or_duplicate_nonfault_sequence_cannot_release_epoch(self):
        self.attach();self.call('admit')
        with self.assertRaises(ValueError):self.front.invoke(self.ident,self.seq,'state',IDLE)
        self.assertIsNotNone(self.record()['epoch'])

    def test_wrong_owner_or_boot_cannot_change_participant(self):
        self.attach();path=self.p.runtime/'participants'/self.ident;original=self.record()
        for change in [{'pid':99999},{'pid_start':999},{'boot_id':'other'},{'uid':-1}]:
            with self.subTest(change=change):
                self.p.publish(path,{**original,**change})
                with self.assertRaises(ValueError):self.front.invoke(self.ident,1,'state',IDLE)
        self.p.publish(path,original)

    def test_changed_epoch_owner_blocks_release(self):
        self.attach();path=self.p.leases/self.record()['epoch'];data=json.loads(path.read_text());data['pid_start']=999
        self.p.publish(path,data)
        with self.assertRaises(ValueError):self.call('state',IDLE)
        self.assertTrue(path.exists())

    def test_malformed_or_extra_counters_never_release(self):
        self.attach()
        for change in [{'queued':True},{'actions':-1},{'processing':0},{'initialized':'true'},{'queued':float('nan')},{'secret':'not a counter'}]:
            with self.subTest(change=change),self.assertRaises(ValueError):
                self.front.invoke(self.ident,self.seq+1,'state',{**IDLE,**change})
        self.assertIsNotNone(self.record()['epoch'])

    def test_quiescent_close_removes_only_this_frontend_participant(self):
        self.attach();self.call('state',IDLE);self.call('close')
        self.assertEqual(self.p.blockers(),[])

    def test_exit_before_initialization_or_with_queue_is_not_completion(self):
        self.attach()
        with self.assertRaises(RuntimeError):self.call('close')
        self.assertIsNotNone(self.record()['epoch'])

    def test_runtime_records_exclude_payload_and_native_command(self):
        self.attach();self.call('state',{**IDLE,'queued':1})
        data=''.join(p.read_text() for d in ['leases','participants'] for p in (self.p.runtime/d).iterdir())
        for text in ['prompt','sessionId','content','command','API_KEY']:self.assertNotIn(text,data)

    def test_uncertain_native_spawn_retains_bootstrap_without_killing_work(self):
        # This creates a separate bootstrap, then injects an uncertain Popen outcome.
        with patch.object(f.subprocess,'Popen',side_effect=OSError('uncertain spawn')):
            with self.assertRaises(OSError):f.launch(self.p,['not-recorded-command'])
        self.assertEqual(len(list(self.p.leases.iterdir())),2)

    def test_failed_attach_publication_keeps_bootstrap_and_epoch(self):
        original=self.p.publish
        def publish(path,data,**kwargs):
            if path.parent==self.p.runtime/'participants':raise OSError('fixture publication failure')
            return original(path,data,**kwargs)
        with patch.object(self.p,'publish',side_effect=publish),self.assertRaises(OSError):self.attach()
        self.assertTrue((self.p.leases/self.startup['id']).exists())
        self.assertEqual(len(list(self.p.leases.iterdir())),2)


if __name__=='__main__':unittest.main()
