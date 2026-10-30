#!/usr/bin/env python3
"""Pure shadow-custody tests: no real production admission/approval/idle."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

s = importlib.util.spec_from_file_location('shadow_test_module', Path(__file__).with_name('spot_shadow.py'))
p = importlib.util.module_from_spec(s); s.loader.exec_module(p)


class ShadowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.root.chmod(0o700)
        self.store = p.Store(self.root, os.geteuid())
        self.binding = {'instance': 'i-0123456789abcdef0', 'boot_id': 'test-boot'}
        self.store.initialize(self.binding)
        self.start = patch.object(p.work, 'process_start', return_value=777); self.start.start()
        self.ns = patch.object(p.os, 'readlink', return_value='pid:[123]'); self.ns.start()

    def tearDown(self):
        self.ns.stop(); self.start.stop(); self.temp.cleanup()

    def create(self):
        return self.store.create(self.binding, ['/immutable/test', 'private argument NOT stored'])

    def test_seed_is_never_empty_idle_authority(self):
        value = self.store.status()
        self.assertFalse(value['all_work_idle']); self.assertFalse(value['work_tracking_verified'])
        self.assertEqual(value['unknown'], p.UNKNOWN)
        self.assertFalse(value['termination_capable']); self.assertFalse(value['armed'])

    def test_no_reseed_existing_namespace(self):
        with self.assertRaises(RuntimeError): self.store.initialize(self.binding)

    def test_partial_namespace_not_reseeded(self):
        (self.root/'seed.json').unlink()
        with self.assertRaises(RuntimeError): self.store.initialize(self.binding)

    def test_unknown_seed_refuses_not_reset(self):
        (self.root/'seed.json').write_text('{}')
        with self.assertRaises(RuntimeError): self.create()
        self.assertEqual((self.root/'seed.json').read_text(), '{}')

    def test_private_directory_required(self):
        self.root.chmod(0o755)
        with self.assertRaises(RuntimeError): self.create()

    def test_symlink_record_not_followed(self):
        record = self.create(); path = self.store.job(record['id'])/'record.json'
        target = self.root/'elsewhere'; path.rename(target); path.symlink_to(target)
        self.assertEqual(self.store.status()['jobs'][0]['state'], 'invalid_or_partial_unknown')

    def test_job_traversal_refused(self):
        with self.assertRaises(RuntimeError): self.store.job('../seed.json')

    def test_argv_is_digest_not_private_contents(self):
        record = self.create()
        self.assertNotIn('private argument', json.dumps(record))
        self.assertEqual(len(record['argv_sha256']), 64)
        self.assertEqual(record['spawn_outcome'], 'unknown_until_local_reap')

    def test_changed_record_never_overwritten_by_heartbeat(self):
        record = self.create(); path = self.store.job(record['id'])/'record.json'
        changed = dict(record, boot_id='different'); p.publish(path, changed)
        with self.assertRaises(RuntimeError): self.store.update(record, heartbeat_at=42)
        self.assertEqual(p.read(path, os.geteuid()), changed)

    def test_local_reap_keeps_output_and_external_custody(self):
        a = p.Adapter(self.store, self.binding, ['/immutable/test']); record = a.create('job')
        a.finish_job(record)
        value = p.read(self.store.job(record['id'])/'record.json', os.geteuid())
        self.assertEqual(value['state'], 'local_children_reaped_output_pending')
        self.assertEqual(value['output_delivery'], 'unverified')
        self.assertEqual(value['external_work'], 'unknown')
        self.assertTrue(self.store.status()['jobs'][0]['always_blocks_termination'])

    def test_completion_cannot_use_copied_receipt(self):
        a = p.Adapter(self.store, self.binding, ['/immutable/test']); record = a.create('job')
        with self.assertRaises(RuntimeError): a.finish_job(dict(record))

    def test_namespace_and_owner_bound_before_spawn(self):
        record = self.create()
        self.assertEqual(record['pid'], os.getpid()); self.assertEqual(record['pid_start'], 777)
        self.assertEqual(record['pid_namespace'], 'pid:[123]')
        self.assertEqual(record['instance'], self.binding['instance'])

    def test_restart_preserves_lease_not_adopt_or_clear(self):
        record = self.create()
        restarted = p.Store(self.root, os.geteuid()).status()
        self.assertEqual(restarted['jobs'][0]['id'], record['id'])
        self.assertTrue(restarted['jobs'][0]['always_blocks_termination'])

    def test_old_boot_record_remains_unknown(self):
        record = self.create(); self.store.update(record, boot_id='old-boot')
        self.assertEqual(self.store.status()['jobs'][0]['boot_id'], 'old-boot')
        self.assertFalse(self.store.status()['all_work_idle'])

    def test_stale_heartbeat_never_expires_into_idle(self):
        record = self.create(); self.store.update(record, heartbeat_at=1)
        self.assertTrue(self.store.status()['jobs'][0]['always_blocks_termination'])

    def test_uncertain_spawn_keeps_record(self):
        a = p.Adapter(self.store, self.binding, ['/immutable/test'])
        with patch.object(p.work, 'subreaper'), patch.object(p.work.subprocess, 'Popen', side_effect=OSError('receipt unknown')):
            with self.assertRaises(OSError): p.work.run_job(a, ['/immutable/test'])
        self.assertEqual(self.store.status()['jobs'][0]['state'], 'lease_before_possible_spawn')

    def test_lease_is_durable_before_Popen(self):
        a = p.Adapter(self.store, self.binding, ['/immutable/test'])
        def spawn(*args, **kwargs):
            self.assertEqual(len(self.store.status()['jobs']), 1)
            raise OSError('preacceptance-or-unknown: retain')
        with patch.object(p.work, 'subreaper'), patch.object(p.work.subprocess, 'Popen', side_effect=spawn):
            with self.assertRaises(OSError): p.work.run_job(a, ['/immutable/test'])

    def test_output_spool_full_hash_is_not_delivery(self):
        record = self.create(); path = self.store.job(record['id'])/'stdout'; path.write_bytes(b'fixture output')
        self.assertEqual(p.spool_hash(path)['bytes'], 14)
        self.assertEqual(record['output_delivery'], 'unverified')

    def test_config_rejects_foreign_path_and_bool_uid(self):
        value = {'schema': 1, 'deployment_id': 'a'*12, 'directory': '/foreign', 'uid': 1001}
        with self.assertRaises(RuntimeError): p.config(value)
        value.update(directory=str(p.BASE/('a'*12)), uid=True)
        with self.assertRaises(RuntimeError): p.config(value)

    def test_config_accepts_exact_shadow_only_scope(self):
        value = {'schema': 1, 'deployment_id': 'a'*12, 'directory': str(p.BASE/('a'*12)), 'uid': 1001}
        self.assertEqual(p.config(value), value)

    def test_no_canonical_startup_or_delete_ack_API(self):
        text = Path(p.__file__).read_text()
        self.assertNotIn('work.Protocol(', text)
        self.assertNotIn('.startup_ready(', text)
        self.assertNotIn('.unlink(', text)
        self.assertNotIn("add_parser('ack')", text)

    def test_failed_directory_fsync_is_not_success_or_retry(self):
        with patch.object(p, 'sync_directory', side_effect=OSError('uncertain persistence')):
            with self.assertRaises(OSError): self.create()
        self.assertEqual(len(list((self.root/'jobs').iterdir())), 1)
        self.assertFalse(self.store.status()['all_work_idle'])


if __name__ == '__main__': unittest.main()
