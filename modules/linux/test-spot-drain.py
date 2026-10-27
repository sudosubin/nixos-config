"""Durable transaction/ownership tests. AWS/storage/service observations are injected.

These exercise real admission locks/files but are NOT production API/boot proof.
"""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('drain', Path(__file__).with_name('spot_drain.py'))
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


class Operations:
    def __init__(self, config):
        self.config = config
        self.events = []
        self.protected = True
        self.current = True
        self.failure = None
        self.gateway_snapshot = None
        self.boot_changed = None

    def event(self, name):
        self.events.append(name)
        if self.failure == name:
            raise RuntimeError('injected observation/action failure')

    def group(self):
        self.event('group')
        return {'DesiredCapacity': 0, 'Instances': [{'InstanceId': self.config['instance_id'],
                'LifecycleState': 'InService', 'ProtectedFromScaleIn': self.protected}]}

    def request_current(self, group):
        self.event('current')
        return self.current

    def protect(self):
        self.event('protect')
        self.protected = True

    def home(self):
        self.event('home')

    def services(self, units):
        self.event('services')
        self.units = units

    def gateway(self, snapshot, boot_changed, authority, publish):
        self.event('gateway')
        self.gateway_snapshot, self.boot_changed = snapshot, boot_changed

    def verified(self, before):
        self.event('verify')


class DrainTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.protocol = d.work.Protocol(self.root/'runtime', uid=os.geteuid(), gid=os.getegid(),
                                        root_uid=os.geteuid(), boot_id='boot')
        self.protocol.initialize()
        self.cfg = {'account': '537112465379', 'region': 'ap-northeast-2', 'asg': 'test-only',
                    'instance_id': 'i-0123456789abcdef0', 'home_volume': 'vol-0123456789abcdef0',
                    'home_uuid': '00000000-0000-0000-0000-000000000000', 'uid': 1001}
        self.old = {'boot_id': 'boot', 'pid': 110, 'pid_start': 10, 'pid_namespace': 'test-pidns'}
        self.new = {**self.old, 'pid': 111, 'pid_start': 11}
        self.before = {'user@1001.service': 'active', 'docker.service': 'inactive'}
        self.tx = self.transaction(self.old)
        self.tx.begin(self.before)
        self.ops = Operations(self.cfg)
        patcher = patch.object(d.work, 'process_start', return_value=999)
        self.pid = patcher.start()
        self.addCleanup(patcher.stop)

    def transaction(self, owner):
        t = d.Transaction(self.cfg, self.protocol, self.root/'private/drain.json',
                          owner_uid=os.geteuid(), current_owner=owner)
        self.addCleanup(t.close)
        return t

    def abandon(self, phase='services_stop_requested'):
        self.tx.update(phase, services_may_be_stopped=True)
        self.tx.close()
        return self.transaction(self.new)

    def release(self, phase='release_requested'):
        self.tx.update('backup_completed', services_may_be_stopped=True, snapshot_id='snap-0123456789abcdef0')
        with self.protocol.locked():
            self.protocol.write_state('releasing')
        self.tx.update(phase)
        self.tx.close()
        self.ops.protected = False
        return self.transaction(self.new)

    def test_intent_and_attempt_are_durable_before_further_actions(self):
        record = self.tx.read()
        self.assertEqual(record['phase'], 'fenced')
        self.assertEqual(self.protocol.attempt_id(), record['id'])
        self.assertEqual(record['owner'], self.old)
        self.assertEqual(self.tx.path.stat().st_mode & 0o777, 0o600)

    def test_other_live_owner_cannot_be_claimed(self):
        self.tx.close()
        self.pid.return_value = 10
        with self.assertRaises(d.Unsafe):
            self.transaction(self.new).recover(self.ops)
        self.assertEqual(self.ops.events, [])

    def test_exclusive_journal_lock_prevents_parallel_controllers(self):
        with self.assertRaises(BlockingIOError):
            self.transaction(self.new).claim()
        self.assertEqual(self.ops.events, [])

    def test_different_pid_namespace_is_not_assumed_dead(self):
        self.tx.close()
        with self.assertRaises(d.Unsafe):
            self.transaction({**self.new, 'pid_namespace': 'another-pidns'}).recover(self.ops)
        self.assertEqual(self.ops.events, [])

    def test_recovery_protects_then_mounts_then_starts_then_verifies_then_opens(self):
        t = self.abandon()
        self.assertEqual(t.recover(self.ops), 'recovered')
        self.assertEqual(self.ops.events, ['group', 'protect', 'home', 'services', 'gateway', 'verify'])
        self.assertEqual(self.ops.units, ['user@1001.service'])  # no forced Docker startup
        self.assertEqual(self.protocol.state(), 'open')
        self.assertEqual(t.read()['phase'], 'recovered')

    def test_every_failed_recovery_step_keeps_admission_closed(self):
        # Separate attempts avoid using a recovered record as another drain.
        for failure in ['protect', 'home', 'services', 'gateway', 'verify']:
            with self.subTest(failure=failure):
                t = self.abandon()
                self.ops.failure = failure
                with self.assertRaises(RuntimeError):
                    t.recover(self.ops)
                self.assertNotEqual(self.protocol.state(), 'open')
                t.close()
                self.tx = self.transaction(self.old)
                self.tx.record = self.tx.read()
                self.tx.acquire()

    def test_unknown_jobs_and_extensions_are_never_deleted_by_recovery(self):
        lease = self.protocol.create('manual', 100)
        t = self.abandon()
        t.recover(self.ops)
        self.assertTrue((self.protocol.leases/lease['id']).exists())
        self.assertTrue(self.protocol.blockers())

    def test_already_released_matching_fence_is_not_reprotected_for_logging_failure(self):
        t = self.release('released')
        self.assertEqual(t.recover(self.ops), 'released')
        self.assertEqual(self.ops.events, ['group', 'current'])
        self.assertEqual(self.protocol.state(), 'released')
        self.assertFalse(self.ops.protected)
        with self.assertRaises(RuntimeError):
            self.protocol.create('manual', 100)

    def test_lost_release_reply_is_observed_without_reissuing_release(self):
        t = self.release()
        self.assertEqual(t.recover(self.ops), 'released')
        self.assertEqual(self.ops.events, ['group', 'current'])
        self.assertEqual(t.read()['phase'], 'released')

    def test_superseded_wake_session_or_window_reprotects_before_restore(self):
        t = self.release()
        self.ops.current = False
        self.assertEqual(t.recover(self.ops), 'recovered')
        self.assertLess(self.ops.events.index('protect'), self.ops.events.index('home'))
        self.assertEqual(self.protocol.state(), 'open')

    def test_still_protected_release_intent_is_not_reissued(self):
        t = self.release()
        self.ops.protected = True
        self.assertEqual(t.recover(self.ops), 'recovered')
        self.assertNotIn('current', self.ops.events)
        self.assertTrue(self.ops.protected)

    def test_missing_fence_cannot_authorize_an_old_release(self):
        t = self.release('released')
        self.protocol.unseal()
        self.assertEqual(t.recover(self.ops), 'recovered')
        self.assertIn('protect', self.ops.events)

    def test_other_attempt_fence_is_not_cleared(self):
        t = self.abandon()
        with self.protocol.locked():
            self.protocol.write_state('draining', 'drain-'+'f'*32)
        with self.assertRaises(RuntimeError):
            t.recover(self.ops)
        self.assertEqual(self.protocol.attempt_id(), 'drain-'+'f'*32)
        self.assertNotIn('home', self.ops.events)

    def test_pre_fence_controller_death_can_recover_without_stopping_work(self):
        self.protocol.unseal()
        self.tx.update('created')
        self.tx.close()
        t = self.transaction(self.new)
        t.recover(self.ops)
        self.assertNotIn('services', self.ops.events)
        self.assertEqual(self.protocol.state(), 'open')

    def test_new_boot_does_not_trust_old_release_or_pid_numbers(self):
        self.release('released').close()
        self.protocol.unseal()
        self.protocol._boot_id = 'new-boot'
        t = self.transaction({**self.new, 'boot_id': 'new-boot', 'pid_namespace': 'new-pidns'})
        self.pid.return_value = 10  # old PID/start happens to exist in the new boot
        self.assertEqual(t.recover(self.ops), 'recovered')
        self.assertTrue(self.ops.boot_changed)
        self.assertIn('protect', self.ops.events)

    def test_exact_dead_service_authority_is_retired_before_new_start(self):
        authority = {**self.old, 'units': ['user@1001.service'], 'id': 'a'*32}
        self.tx.update(service_authority=authority)
        path = self.protocol.runtime/'recover-services'
        self.protocol.publish(path, {'schema': 1, 'id': 'a'*32,
                                    **{k: authority[k] for k in ['pid', 'pid_start', 'boot_id', 'units']}})
        t = self.abandon()
        t.recover(self.ops)
        self.assertFalse(path.exists())
        self.assertEqual(t.read()['service_authority'], None)

    def test_unowned_service_authority_is_not_overwritten(self):
        path = self.protocol.runtime/'recover-services'
        self.protocol.publish(path, {'schema': 1, 'id': 'a'*32, 'pid': 9999,
                                    'pid_start': 777, 'boot_id': 'boot', 'units': ['unrelated.service']})
        t = self.abandon()
        with self.assertRaises(RuntimeError):
            t.recover(self.ops)
        self.assertTrue(path.exists())
        self.assertNotIn('home', self.ops.events)

    def test_same_owner_but_changed_authority_id_is_not_retired(self):
        authority = {**self.old, 'units': ['user@1001.service'], 'id': 'a'*32}
        self.tx.update(service_authority=authority)
        path = self.protocol.runtime/'recover-services'
        self.protocol.publish(path, {'schema': 1, 'id': 'b'*32,
                                    **{k: authority[k] for k in ['pid', 'pid_start', 'boot_id', 'units']}})
        t = self.abandon()
        with self.assertRaises(RuntimeError):
            t.recover(self.ops)
        self.assertEqual(json.loads(path.read_text())['id'], 'b'*32)
        self.assertNotEqual(self.protocol.state(), 'open')
        self.assertNotIn('home', self.ops.events)

    def test_record_identity_change_cannot_be_recovered(self):
        self.tx.close()
        cfg = {**self.cfg, 'home_volume': 'vol-fffffffffffffffff'}
        t = d.Transaction(cfg, self.protocol, self.tx.path, owner_uid=os.geteuid(), current_owner=self.new)
        with self.assertRaises(d.Unsafe):
            t.recover(self.ops)
        t.close()
        self.assertEqual(self.ops.events, [])

    def test_malformed_or_truthy_journal_fields_fail_closed(self):
        original = self.tx.read()
        for delta in [{'schema': True}, {'owner': {}}, {'phase': []}, {'services_may_be_stopped': 1},
                      {'services_before': {'docker.service': 'active'}}, {'origin_boot': ''}]:
            with self.subTest(delta=delta):
                self.protocol.publish(self.tx.path, {**original, **delta})
                with self.assertRaises(d.Unsafe):
                    self.tx.read()
        self.protocol.publish(self.tx.path, original)

    def test_release_journal_requires_backup_and_stop_boundary(self):
        with self.assertRaises(d.Unsafe):
            self.tx.update('release_requested')
        self.assertEqual(self.tx.read()['phase'], 'fenced')

    def test_journal_directory_and_symlink_records_are_not_trusted(self):
        self.tx.close()
        self.tx.path.parent.chmod(0o755)
        with self.assertRaises(d.Unsafe):
            self.transaction(self.new).claim()
        self.tx.path.parent.chmod(0o700)
        other = self.tx.path.with_suffix('.saved')
        self.tx.path.rename(other)
        self.tx.path.symlink_to(other)
        with self.assertRaises(OSError):
            self.tx.read()

    def test_recovery_does_not_call_backup_or_destroy_an_uncertain_attempt(self):
        t = self.abandon('backing_up')
        t.recover(self.ops)
        self.assertEqual(set(self.ops.events), {'group', 'protect', 'home', 'services', 'gateway', 'verify'})
        self.assertEqual(t.read()['snapshot_id'], None)


if __name__ == '__main__':
    unittest.main()
