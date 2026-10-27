"""Pinned Gateway recovery contracts; pure fake RPC, no model/service/AWS calls."""
from contextlib import contextmanager
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('fixtures', Path(__file__).with_name('test-spot-gateway.py'))
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
gw = f.gw


class Manager(f.Manager):
    state = None
    def show(self):
        return {'MainPID': str(self.identity['pid']),
                'ActiveState': self.state or ('active' if self.identity['pid'] else 'inactive')}
    def start(self):
        super().start()
        self.rpc.owner = None
        self.rpc.override.pop('gateway.suspend.status', None)


class RPC(f.RPC):
    def __init__(self, manager):
        super().__init__(manager)
        self.drop_after = set()
        self.drop_before = set()
        self.connection = self.boot_id
    def __call__(self, method, params):
        if self.boot_id is None:
            self.connection = self.boot_id = 'connection-' + str(self.manager.identity['pid'])
        if self.boot_id != self.connection:
            raise gw.Unsafe('connection changed before dispatch')
        if method in self.drop_before:
            raise TimeoutError('injected pre-dispatch failure')
        result = super().__call__(method, params)
        if method in self.drop_after:
            self.drop_after.remove(method)
            raise TimeoutError('injected lost response AFTER the server action')
        return result


class GatewayRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.manager = Manager()
        self.rpc = RPC(self.manager)
        self.manager.rpc = self.rpc
        self.records = []
        self.fenced = True
        self.g = gw.Gateway(self.rpc, self.manager, lambda: self.fenced, self.records.append)
        self.addCleanup(self.g.close)
        patcher = patch.object(gw.work, 'process_start', return_value=7)
        self.pid = patcher.start()
        self.addCleanup(patcher.stop)
        self.permits = []

    @contextmanager
    def authority(self, units):
        self.permits.append(units)
        yield

    def replacement(self):
        self.g.close()
        other = gw.Gateway(self.rpc, self.manager, lambda: self.fenced, self.records.append)
        self.addCleanup(other.close)
        return other

    def snapshot(self):
        return copy.deepcopy(self.records[-1])

    def test_dead_controller_owned_held_fence_is_resumed_not_stopped(self):
        self.g.acquire()
        other = self.replacement()
        other.restore_snapshot(self.snapshot(), authority=self.authority)
        self.assertEqual(other.effect, 'restored')
        self.assertEqual(self.manager.events, [])
        self.assertEqual(self.rpc.owner, None)

    def test_lost_prepare_response_recovers_exact_request_then_resumes(self):
        self.rpc.drop_after.add('gateway.suspend.prepare')
        with self.assertRaises(TimeoutError):
            self.g.acquire()
        self.assertIsNotNone(self.rpc.owner)
        original = self.g.request_id
        self.replacement().restore_snapshot(self.snapshot(), authority=self.authority)
        owners = [p['requestId'] for m,p in self.rpc.calls if m == 'gateway.suspend.prepare']
        self.assertEqual(set(owners), {original})
        self.assertEqual(self.manager.events, [])

    def test_expired_or_already_resumed_lease_is_observed_without_new_prepare(self):
        self.g.acquire()
        self.rpc.owner = None
        count = sum(m == 'gateway.suspend.prepare' for m,p in self.rpc.calls)
        self.replacement().restore_snapshot(self.snapshot(), authority=self.authority)
        self.assertEqual(sum(m == 'gateway.suspend.prepare' for m,p in self.rpc.calls), count)
        self.assertEqual(self.manager.events, [])

    def test_commit_not_received_resumes_live_prepared_lease_without_committing(self):
        self.g.acquire()
        self.rpc.drop_before.add('gateway.suspend.handoff')
        with self.assertRaises(TimeoutError):
            self.g.stop()
        self.rpc.drop_before.clear()
        self.replacement().restore_snapshot(self.snapshot(), authority=self.authority)
        self.assertEqual(self.manager.events, [])
        self.assertIsNone(self.rpc.owner)

    def retired(self):
        self.rpc.override['gateway.suspend.status'] = {'status': 'draining', 'phase': 'interrupting',
            'ownerId': self.g.request_id, 'expiresAtMs': self.g.expires,
            'activeCount': 0, 'blockers': [], 'writeCustody': []}

    def test_lost_commit_ack_is_resolved_only_against_exact_retired_handoff(self):
        self.g.acquire()
        self.rpc.drop_after.add('gateway.suspend.handoff')
        with self.assertRaises(TimeoutError):
            self.g.stop()
        self.retired()
        self.replacement().restore_snapshot(self.snapshot(), authority=self.authority)
        self.assertEqual(self.manager.events, ['commit', 'commit', 'stop', 'start'])
        self.assertEqual(self.permits, [[self.manager.unit]])
        targets = [p['target'] for m,p in self.rpc.calls if m == 'gateway.suspend.handoff']
        self.assertEqual(targets[0], targets[1])

    def test_ambiguous_retired_commit_never_falls_back_to_systemctl_stop(self):
        self.g.acquire()
        self.rpc.drop_before.add('gateway.suspend.handoff')
        with self.assertRaises(TimeoutError):
            self.g.stop()
        self.retired()
        with self.assertRaises(TimeoutError):
            self.replacement().restore_snapshot(self.snapshot(), authority=self.authority)
        self.assertEqual(self.manager.events, [])
        self.assertEqual(self.permits, [])

    def test_external_teardown_is_not_promoted_to_our_commit(self):
        self.g.acquire()
        self.retired()  # record effect still held, never attempted commit
        with self.assertRaises(gw.Unsafe):
            self.replacement().restore_snapshot(self.snapshot(), authority=self.authority)
        self.assertFalse(any(m == 'gateway.suspend.handoff' for m,p in self.rpc.calls))
        self.assertEqual(self.manager.events, [])

    def test_another_owner_is_never_resumed(self):
        self.g.acquire()
        self.rpc.override['gateway.suspend.status'] = {'status': 'ready', 'ownerId': 'someone-else'}
        with self.assertRaises(gw.Unsafe):
            self.replacement().restore_snapshot(self.snapshot(), authority=self.authority)
        self.assertFalse(any(m == 'gateway.suspend.resume' for m,p in self.rpc.calls))

    def test_scheduler_resume_failure_is_not_recovered(self):
        self.g.acquire()
        self.rpc.override['gateway.suspend.resume'] = {'ok': False, 'reason': 'scheduler-resume-failed'}
        with self.assertRaises(gw.Unsafe):
            self.replacement().restore_snapshot(self.snapshot(), authority=self.authority)
        self.assertEqual(self.manager.events, [])

    def test_owned_inactive_service_requires_narrow_authority_and_ready_new_rpc(self):
        self.g.acquire()
        self.manager.identity = {'pid': 0, 'pid_start': 0}
        self.pid.side_effect = FileNotFoundError()
        other = self.replacement()
        other.restore_snapshot(self.snapshot(), authority=self.authority)
        self.assertEqual(self.manager.events, ['start'])
        self.assertEqual(self.permits, [[self.manager.unit]])
        self.assertEqual(other.target['pid'], 43)
        self.assertEqual(other.effect, 'restored')

    def test_no_startup_without_authority(self):
        self.g.acquire()
        self.manager.identity = {'pid': 0, 'pid_start': 0}
        self.pid.side_effect = FileNotFoundError()
        with self.assertRaises(gw.Unsafe):
            self.replacement().restore_snapshot(self.snapshot())
        self.assertEqual(self.manager.events, [])

    def test_old_process_outside_inactive_unit_is_not_duplicated(self):
        self.g.acquire()
        self.manager.identity = {'pid': 0, 'pid_start': 0}
        with self.assertRaises(gw.Unsafe):
            self.replacement().restore_snapshot(self.snapshot(), authority=self.authority)
        self.assertEqual(self.manager.events, [])

    def test_replacement_is_observed_without_stop_when_original_gone(self):
        self.g.acquire()
        self.manager.identity = {'pid': 99, 'pid_start': 8}
        self.rpc.owner = None
        self.pid.side_effect = FileNotFoundError()
        other = self.replacement()
        other.restore_snapshot(self.snapshot(), authority=self.authority)
        self.assertEqual(other.target['pid'], 99)
        self.assertEqual(self.manager.events, [])

    def test_live_original_plus_replacement_stays_unknown(self):
        self.g.acquire()
        self.manager.identity = {'pid': 99, 'pid_start': 8}
        with self.assertRaises(gw.Unsafe):
            self.replacement().restore_snapshot(self.snapshot(), authority=self.authority)
        self.assertEqual(self.manager.events, [])

    def test_new_boot_does_not_confuse_reused_old_pid_with_original_work(self):
        self.g.acquire()
        self.manager.identity = {'pid': 99, 'pid_start': 8}
        self.rpc.owner = None
        other = self.replacement()
        other.restore_snapshot(self.snapshot(), boot_changed=True, authority=self.authority)
        self.assertEqual(self.manager.events, [])
        self.assertEqual(other.target['pid'], 99)

    def test_transitioning_unit_is_retried_not_forced(self):
        self.g.acquire()
        self.manager.state = 'deactivating'
        with self.assertRaises(gw.Unsafe):
            self.replacement().restore_snapshot(self.snapshot(), authority=self.authority)
        self.assertEqual(self.manager.events, [])

    def test_readiness_record_cannot_stop_replacement_process_instance(self):
        self.g.acquire()
        self.rpc.connection = 'different-server-boot'
        with self.assertRaises(gw.Unsafe):
            self.replacement().restore_snapshot(self.snapshot(), authority=self.authority)
        self.assertEqual(self.manager.events, [])

    def test_already_restored_snapshot_does_not_suspend_it_again(self):
        self.g.acquire()
        other = self.replacement()
        other.restore_snapshot(self.snapshot(), authority=self.authority)
        count = sum(m == 'gateway.suspend.prepare' for m,p in self.rpc.calls)
        self.replacement().restore_snapshot(self.snapshot(), authority=self.authority)
        self.assertEqual(sum(m == 'gateway.suspend.prepare' for m,p in self.rpc.calls), count)

    def test_malformed_identity_or_truthy_ack_never_authorizes_service_control(self):
        self.g.acquire()
        snapshot = self.snapshot()
        for delta in [{'schema': True}, {'request_id': 'invalid'}, {'target': {}},
                      {'connection_boot_id': None}, {'committed': 1}, {'suspension_id': None}]:
            with self.subTest(delta=delta), self.assertRaises(gw.Unsafe):
                self.replacement().restore_snapshot({**snapshot, **delta}, authority=self.authority)
        self.assertEqual(self.manager.events, [])


if __name__ == '__main__':
    unittest.main()
