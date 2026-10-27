"""Offline admission tests; never call AWS or start/stop a host service."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('work', Path(__file__).with_name('spot_work.py'))
work = importlib.util.module_from_spec(spec); spec.loader.exec_module(work)


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.p = work.Protocol(Path(self.temp.name)/'runtime', uid=os.geteuid(), gid=os.getegid(), root_uid=os.geteuid(), boot_id='test-boot')
        self.p.initialize()

    def job(self):
        with patch.object(work, 'process_start', return_value=123):
            return self.p.create('job')

    def rewrite(self, data):
        self.p.publish(self.p.leases/data['id'], data)

    def test_empty_protocol_is_open(self):
        self.assertEqual(self.p.state(), 'open'); self.assertEqual(self.p.blockers(), [])

    def test_service_start_defaults_to_closed_during_drain(self):
        self.assertTrue(self.p.service_start_allowed('app.service'))
        self.p.seal();self.assertFalse(self.p.service_start_allowed('app.service'))

    def test_recovery_authorizes_only_named_service_not_jobs(self):
        self.p.seal()
        with patch.object(work,'process_start',return_value=123), patch.object(work,'process_uid',return_value=os.geteuid()):
            with self.p.recover_services(['app.service']):
                self.assertTrue(self.p.service_start_allowed('app.service'))
                self.assertFalse(self.p.service_start_allowed('other.service'))
                with self.assertRaises(RuntimeError):self.p.create('job')
            self.assertFalse(self.p.service_start_allowed('app.service'))

    def test_dead_recovery_controller_cannot_authorize_start(self):
        self.p.seal()
        with patch.object(work,'process_start',return_value=123), patch.object(work,'process_uid',return_value=os.geteuid()):
            with self.p.recover_services(['app.service']):
                with patch.object(work,'process_start',side_effect=ProcessLookupError):
                    self.assertFalse(self.p.service_start_allowed('app.service'))

    def test_recovery_does_not_grant_permission_after_release(self):
        self.p.seal()
        with patch.object(work,'process_start',return_value=123), patch.object(work,'process_uid',return_value=os.geteuid()):
            with self.p.recover_services(['app.service']):
                self.p.write_state('releasing');self.assertFalse(self.p.service_start_allowed('app.service'))

    def test_recovery_blocks_release_and_early_unseal(self):
        self.p.seal()
        with patch.object(work,'process_start',return_value=123):
            with self.p.recover_services(['app.service']):
                with self.assertRaises(RuntimeError):
                    with self.p.commit():self.fail('recovery is not idle')
                with self.assertRaises(RuntimeError):self.p.unseal()
        self.p.unseal();self.assertEqual(self.p.state(),'open')

    def test_stale_recovery_authority_never_overwritten(self):
        self.p.seal();(self.p.runtime/'recover-services').write_text('{}')
        with self.assertRaises(RuntimeError):
            with self.p.recover_services(['app.service']):self.fail('must not replace unknown authority')

    def test_manual_extension_blocks_until_expiry(self):
        data = self.p.create('manual', 100)
        self.assertEqual(self.p.blockers(data['created_at']+99)[0]['reason'], 'manual_extension')
        self.assertEqual(self.p.blockers(data['expires_at']), [])

    def test_invalid_durations_never_acknowledge(self):
        for seconds in [0,-1,float('inf'),float('nan'),True,'100']:
            with self.subTest(seconds=seconds), self.assertRaises(ValueError): self.p.create('manual', seconds)
        self.assertEqual(list(self.p.leases.iterdir()), [])

    def test_manual_extension_can_cancel_an_in_progress_drain(self):
        self.p.seal(); self.p.create('manual', 100)
        with self.assertRaises(RuntimeError):
            with self.p.commit(): self.fail('must not release')
        self.assertEqual(self.p.state(), 'draining')

    def test_job_rejected_after_fence_without_starting(self):
        self.p.seal()
        with patch.object(work, 'subreaper'), patch.object(work.subprocess, 'Popen') as spawn, self.assertRaises(RuntimeError):
            work.run_job(self.p, ['not-executed'])
        spawn.assert_not_called()

    def test_job_published_before_fence_blocks_seal_and_commit(self):
        self.job()
        with self.assertRaises(work.SealBlocked):self.p.seal()
        self.assertEqual(self.p.state(),'open')
        self.assertFalse((self.p.runtime/'draining').exists())
        with self.assertRaises(RuntimeError):
            with self.p.commit(): self.fail('must not release')

    def test_stale_job_never_expires_into_idle(self):
        data=self.job()
        self.assertEqual(self.p.blockers(data['heartbeat_at']+1000000)[0]['reason'], 'stale_job_unknown')

    def test_heartbeat_refreshes_diagnostic_not_permission_to_stop(self):
        data=self.job(); data['heartbeat_at']-=1000; self.rewrite(data)
        self.assertEqual(self.p.blockers()[0]['reason'], 'stale_job_unknown')
        self.p.heartbeat(data)
        self.assertEqual(self.p.blockers()[0]['reason'], 'running_job')

    def test_job_cannot_be_cancelled_as_an_extension(self):
        data=self.job()
        with self.assertRaises(ValueError): self.p.remove(data['id'])
        self.assertTrue(self.p.blockers())

    def test_completed_wrapper_can_remove_own_job(self):
        data=self.job(); self.p.remove(data['id'], job_finished=True); self.assertEqual(self.p.blockers(), [])

    def test_cancel_manual(self):
        data=self.p.create('manual', 100); self.p.remove(data['id']); self.assertEqual(self.p.blockers(), [])

    def test_path_traversal_cancel_rejected(self):
        with self.assertRaises(ValueError): self.p.remove('../draining')

    def test_unknown_entries_block(self):
        (self.p.leases/'unexpected').write_text('')
        self.assertEqual(self.p.blockers()[0]['reason'], 'invalid_lease_unknown')

    def test_symlink_lease_never_followed(self):
        target=Path(self.temp.name)/'private';target.write_text('{}')
        (self.p.leases/('manual-'+'a'*32)).symlink_to(target)
        self.assertEqual(self.p.blockers()[0]['reason'], 'invalid_lease_unknown')

    def test_world_writable_lease_unknown(self):
        data=self.p.create('manual',100);os.chmod(self.p.leases/data['id'],0o666)
        self.assertEqual(self.p.blockers()[0]['reason'], 'invalid_lease_unknown')

    def test_non_object_records_block_instead_of_crashing_status(self):
        path=self.p.leases/('manual-'+'a'*32)
        for data in [None,[],True,'not an object']:
            with self.subTest(data=data):
                self.p.publish(path,data)
                self.assertEqual(self.p.blockers()[0]['reason'],'invalid_lease_unknown')

    def test_maintenance_condition_skips_when_fenced(self):
        with patch('sys.argv',['spot-work','check-open']):
            self.assertEqual(work.main(self.p),0)
            self.p.seal()
            self.assertEqual(work.main(self.p),1)

    def test_foreign_boot_fence_cannot_admit_work(self):
        self.p.publish(self.p.runtime/'draining',{'schema':1,'state':'draining','boot_id':'other'})
        with self.assertRaises(ValueError):self.p.create('manual',100)

    def test_bad_job_records_block_instead_of_ignoring(self):
        base=self.job()
        for change in [{'schema':True},{'uid':True},{'boot_id':'another-boot'},{'pid':True},{'pid_start':0},{'state':'done'},{'heartbeat_at':float('nan')},{'heartbeat_at':time.time()+1000}]:
            with self.subTest(change=change):
                self.rewrite({**base,**change})
                self.assertEqual(self.p.blockers()[0]['reason'], 'invalid_lease_unknown')

    def test_bad_manual_records_block(self):
        base=self.p.create('manual',100)
        for change in [{'expires_at':True},{'expires_at':float('inf')},{'expires_at':0},{'id':'other'}]:
            with self.subTest(change=change):
                self.rewrite({**base,**change})
                self.assertEqual(self.p.blockers()[0]['reason'], 'invalid_lease_unknown')

    def test_release_rejects_late_extensions_without_false_ack(self):
        self.p.seal()
        with self.p.commit(): self.assertEqual(self.p.state(), 'releasing')
        self.assertEqual(self.p.state(), 'released')
        with self.assertRaises(RuntimeError): self.p.create('manual',100)

    def test_concurrent_extension_cannot_slip_through_commit(self):
        self.p.seal(); result=[]
        def extend():
            try:self.p.create('manual',100);result.append('acknowledged')
            except RuntimeError:result.append('not_acknowledged')
        with self.p.commit():
            thread=threading.Thread(target=extend);thread.start();time.sleep(0.04)
        thread.join();self.assertEqual(result,['not_acknowledged'])

    def test_failed_commit_stays_closed_until_protection_reconfirmed(self):
        self.p.seal()
        with self.assertRaises(RuntimeError):
            with self.p.commit():raise RuntimeError('AWS timeout')
        self.assertEqual(self.p.state(),'releasing')
        with self.assertRaises(RuntimeError):self.p.create('manual',100)
        self.p.unseal();self.assertEqual(self.p.state(),'open')

    def test_old_drain_cannot_be_silently_replaced(self):
        self.p.seal()
        with self.assertRaises(RuntimeError):self.p.seal()

    def test_runtime_symlink_refused(self):
        root=Path(self.temp.name)/'alias';root.symlink_to(self.p.runtime)
        bad=work.Protocol(root,uid=os.geteuid(),gid=os.getegid(),root_uid=os.geteuid(),boot_id='test-boot')
        with self.assertRaises(ValueError):bad.initialize()

    def test_lock_symlink_refused(self):
        p=self.p.runtime/'admission.lock';p.unlink();p.symlink_to(Path(self.temp.name)/'missing')
        with self.assertRaises(OSError):
            with self.p.locked():pass

    def test_unknown_fence_fails_closed(self):
        self.p.publish(self.p.runtime/'draining',{'state':'nonsense'})
        with self.assertRaises(ValueError):self.p.create('manual',100)

    def test_wrapper_failure_keeps_running_child_lease(self):
        class Child:
            pid=123
            def wait(self):raise RuntimeError('wrapper failed while work still alive')
        with patch.object(work,'subreaper'),patch.object(work,'process_start',return_value=123),patch.object(work.subprocess,'Popen',return_value=Child()),self.assertRaises(RuntimeError):
            work.run_job(self.p,['not-executed'])
        self.assertTrue(self.p.blockers())

    def test_spawn_failure_releases_only_unstarted_job(self):
        with patch.object(work,'subreaper'),patch.object(work,'process_start',return_value=123),patch.object(work.subprocess,'Popen',side_effect=OSError('no binary')),self.assertRaises(OSError):
            work.run_job(self.p,['not-executed'])
        self.assertEqual(self.p.blockers(),[])

    def test_seal_refuses_live_manual_extension_without_closing_admission(self):
        self.p.create('manual',100)
        with self.assertRaises(work.SealBlocked):self.p.seal()
        self.assertEqual(self.p.state(),'open')

    def test_seal_does_not_turn_stale_jobs_into_permission(self):
        data=self.job();data['heartbeat_at']-=1000;self.rewrite(data)
        with self.assertRaises(work.SealBlocked):self.p.seal()
        self.assertEqual(self.p.state(),'open')
        self.assertEqual(self.p.blockers()[0]['reason'],'stale_job_unknown')

    def test_seal_refuses_malformed_lease_without_mutating_it(self):
        p=self.p.leases/'unknown';p.write_text('malformed')
        with self.assertRaises(work.SealBlocked):self.p.seal()
        self.assertEqual(p.read_text(),'malformed');self.assertEqual(self.p.state(),'open')

    def test_seal_refuses_even_apparently_idle_unverified_participant(self):
        self.p.publish(self.p.runtime/'participants/acp-fixture',{'healthy':True,'active_requests':0})
        with self.assertRaises(work.SealBlocked):self.p.seal()
        self.assertEqual(self.p.state(),'open')

    def test_seal_refuses_unavailable_participant_registry(self):
        (self.p.runtime/'participants').rmdir()
        with self.assertRaises(work.SealBlocked):self.p.seal()
        self.assertEqual(self.p.state(),'open')

    def test_seal_refuses_unknown_recovery_authority(self):
        (self.p.runtime/'recover-services').write_text('{}')
        with self.assertRaises(work.SealBlocked):self.p.seal()
        self.assertEqual(self.p.state(),'open')

    def test_expired_valid_extension_does_not_permanently_prevent_seal(self):
        data=self.p.create('manual',100);data['created_at']-=200;data['expires_at']-=200;self.rewrite(data)
        self.p.seal();self.assertEqual(self.p.state(),'draining')
        self.assertTrue((self.p.leases/data['id']).exists())

    def test_nonroot_seal_cannot_read_blockers_or_publish_fence(self):
        with patch.object(work.os,'geteuid',return_value=os.geteuid()+1),patch.object(self.p,'blockers_unlocked') as blockers:
            with self.assertRaises(PermissionError):self.p.seal()
        blockers.assert_not_called();self.assertEqual(self.p.state(),'open')

    def test_job_admitted_under_lock_wins_over_concurrent_seal(self):
        entered=threading.Event();release=threading.Event();result=[];original=self.p.publish
        def publish(path,data,**kwargs):
            if path.parent==self.p.leases:
                entered.set()
                if not release.wait(5):raise RuntimeError('fixture publication barrier expired')
            return original(path,data,**kwargs)
        def job():
            try:self.job();result.append('job_admitted')
            except Exception as error:result.append(type(error).__name__)
        def seal():
            try:self.p.seal();result.append('sealed')
            except work.SealBlocked:result.append('seal_deferred')
        creator=threading.Thread(target=job);sealer=threading.Thread(target=seal)
        with patch.object(self.p,'publish',side_effect=publish):
            try:
                creator.start();self.assertTrue(entered.wait(2));sealer.start()
            finally:
                release.set();creator.join(5)
                if sealer.ident is not None:sealer.join(5)
        self.assertFalse(creator.is_alive());self.assertFalse(sealer.is_alive())
        self.assertCountEqual(result,['job_admitted','seal_deferred']);self.assertEqual(self.p.state(),'open')

    def test_seal_check_and_publication_cannot_be_split_by_new_job(self):
        checked=threading.Event();release=threading.Event();result=[];original=self.p.blockers_unlocked
        def blockers():
            found=original();checked.set()
            if not release.wait(5):raise RuntimeError('fixture seal barrier expired')
            return found
        def seal():
            try:self.p.seal();result.append('sealed')
            except Exception as error:result.append(type(error).__name__)
        def job():
            try:self.job();result.append('job_admitted')
            except RuntimeError:result.append('job_rejected')
        sealer=threading.Thread(target=seal);creator=threading.Thread(target=job)
        with patch.object(self.p,'blockers_unlocked',side_effect=blockers):
            try:
                sealer.start();self.assertTrue(checked.wait(2));creator.start()
            finally:
                release.set();sealer.join(5)
                if creator.ident is not None:creator.join(5)
        self.assertFalse(sealer.is_alive());self.assertFalse(creator.is_alive())
        self.assertCountEqual(result,['sealed','job_rejected']);self.assertEqual(self.p.state(),'draining')
        self.assertEqual(self.p.blockers(),[])

    def test_preaction_reopen_requires_true_confirmed_protection(self):
        for value in [False,None,1,'true']:
            with self.subTest(value=value),self.assertRaises(PermissionError):
                self.p.reopen_unstarted('drain-'+'a'*32,protected=value)
        self.assertEqual(self.p.state(),'open')

    def test_preaction_recovery_never_fences_open_work_or_removes_its_lease(self):
        data=self.job()
        with patch.object(self.p,'write_state',wraps=self.p.write_state) as write:
            self.p.reopen_unstarted('drain-'+'a'*32,protected=True)
        write.assert_not_called();self.assertEqual(self.p.state(),'open')
        self.assertTrue((self.p.leases/data['id']).exists())

    def test_preaction_recovery_only_reopens_matching_draining_attempt(self):
        attempt='drain-'+'a'*32;other='drain-'+'b'*32
        self.p.seal(attempt);self.p.reopen_unstarted(attempt,protected=True)
        self.assertEqual(self.p.state(),'open')
        for state,ident in [('draining',other),('releasing',attempt),('released',attempt)]:
            with self.subTest(state=state,ident=ident):
                with self.p.locked():self.p.write_state(state,ident)
                with self.assertRaises(RuntimeError):self.p.reopen_unstarted(attempt,protected=True)
                self.assertEqual(self.p.state(),state);self.assertEqual(self.p.attempt_id(),ident)

    def test_preaction_recovery_does_not_retire_unknown_startup_authority(self):
        attempt='drain-'+'a'*32;self.p.seal(attempt)
        path=self.p.runtime/'recover-services';path.write_text('{}')
        with self.assertRaises(RuntimeError):self.p.reopen_unstarted(attempt,protected=True)
        self.assertTrue(path.exists());self.assertEqual(self.p.state(),'draining')

    def test_no_command_or_arguments_stored_in_lease(self):
        data=self.job()
        self.assertEqual(set(data),{'schema','id','kind','uid','boot_id','created_at','state','pid','pid_start','heartbeat_at'})


if __name__=='__main__':unittest.main()
