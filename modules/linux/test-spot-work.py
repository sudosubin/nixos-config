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

    def test_job_published_before_fence_blocks_commit(self):
        self.job(); self.p.seal()
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

    def test_no_command_or_arguments_stored_in_lease(self):
        data=self.job()
        self.assertEqual(set(data),{'schema','id','kind','uid','boot_id','created_at','state','pid','pid_start','heartbeat_at'})


if __name__=='__main__':unittest.main()
