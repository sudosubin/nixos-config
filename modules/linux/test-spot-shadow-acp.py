#!/usr/bin/env python3
"""Pure keeper/custody/retention tests; never production startup readiness."""
import base64
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

s=importlib.util.spec_from_file_location('warm_acp_test',Path(__file__).with_name('spot_shadow_acp.py'))
p=importlib.util.module_from_spec(s);s.loader.exec_module(p)


class Child:
    def __init__(self): self.stdin=io.BytesIO()
    def poll(self): return None


class KeeperTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name); self.root.chmod(0o700)
        self.binding={'boot_id':'private-boot','instance':'i-0123456789abcdef0'}
        self.store=p.shadow.Store(self.root,os.geteuid()); self.store.initialize(self.binding)
        self.start=patch.object(p.work,'process_start',return_value=777);self.start.start()
        self.ns=patch.object(p.os,'readlink',return_value='pid:[42]');self.ns.start()
        self.disk=patch.object(p,'space',return_value=4*1024**3);self.disk.start()
        self.k=p.Keeper(self.store,self.binding,['/immutable/native','acp'],lambda:dict(self.binding))
        self.k.child=Child();self.k.receipt_confirmed=True
    def tearDown(self):
        self.disk.stop();self.ns.stop();self.start.stop();self.temp.cleanup()
    def request(self,ident,method,params=None):
        return {'jsonrpc':'2.0','id':ident,'method':method,'params':params or {}}
    def initialize(self):
        self.assertTrue(self.k.input(self.request(0,'initialize'))['admitted'])
        self.k.tracker.backend({'jsonrpc':'2.0','id':0,'result':{'protocolVersion':1,'agentCapabilities':{}}})
    def record(self,lease): return p.shadow.read(self.store.job(lease['id'])/'record.json',os.geteuid())

    def test_session_lease_precedes_any_backend_effect(self):
        self.assertEqual(self.record(self.k.lease)['state'],'keeper_leased_before_backend_spawn')
        self.assertFalse(self.record(self.k.lease)['termination_capable'])
    def test_request_lease_exists_before_forward(self):
        def write(raw):
            self.assertEqual(len(self.k.protocol.leases),1)
            lease=next(iter(self.k.protocol.leases.values()))
            self.assertEqual(self.record(lease)['state'],'request_leased_before_forward')
            return len(raw)
        with patch.object(self.k.child.stdin,'write',side_effect=write):
            self.assertTrue(self.k.input(self.request(0,'initialize'))['admitted'])
    def test_metadata_contains_no_prompt_or_RPC_ids(self):
        self.initialize();self.k.input(self.request('SENSITIVE_RPC_ID','session/prompt',{'text':'SENSITIVE_PROMPT'}))
        text=''.join((path/'record.json').read_text() for path in (self.root/'jobs').iterdir())
        self.assertNotIn('SENSITIVE_RPC_ID',text);self.assertNotIn('SENSITIVE_PROMPT',text)
    def test_spooled_or_read_output_is_never_delivery_or_custody_retirement(self):
        self.initialize();row=self.k.segments.append('stdout',b'private-output\n')
        result=self.k.handle({'op':'read','sequence':0})
        self.assertEqual(base64.b64decode(result['segment']['data_base64']),b'private-output\n')
        self.assertEqual(row['consumer_delivery'],'unverified')
        for lease in self.k.protocol.leases.values():self.assertEqual(self.record(lease)['output_delivery'],'unverified')
        self.assertFalse(self.store.status()['all_work_idle'])
    def test_terminal_response_is_pending_delivery_and_record_never_removed(self):
        self.initialize();self.k.input(self.request(1,'session/prompt'))
        self.k.tracker.backend({'jsonrpc':'2.0','id':1,'result':{'stopReason':'end_turn'}})
        entry=self.k.tracker.pending[('number',1)]
        self.assertTrue(entry['completed']);self.assertFalse(entry['response_delivered'])
        self.assertEqual(self.record(entry['lease'])['state'],'provider_terminal_observed_output_pending')
    def test_unknown_async_route_rejected_before_lease_and_forward(self):
        self.initialize();before=len(self.k.protocol.leases);sent=self.k.child.stdin.getvalue()
        reply=self.k.input(self.request(1,'_kiro.dev/session/steer'))
        self.assertFalse(reply['admitted']);self.assertEqual(len(self.k.protocol.leases),before)
        self.assertEqual(self.k.child.stdin.getvalue(),sent)
    def test_lost_ack_does_not_authorize_replaying_input(self):
        self.initialize();self.assertTrue(self.k.input(self.request(1,'session/prompt'))['admitted'])
        before=self.k.child.stdin.getvalue()
        self.assertFalse(self.k.input(self.request(1,'session/prompt'))['admitted'])
        self.assertEqual(self.k.child.stdin.getvalue(),before)
    def test_even_terminal_request_id_cannot_be_replayed(self):
        self.initialize();before=self.k.child.stdin.getvalue()
        self.assertFalse(self.k.input(self.request(0,'initialize'))['admitted'])
        self.assertEqual(self.k.child.stdin.getvalue(),before)
    def test_uncertain_input_write_keeps_lease_and_refuses_replay(self):
        self.initialize()
        with patch.object(self.k.child.stdin,'write',side_effect=OSError('unknown write receipt')):
            self.assertIsNone(self.k.input(self.request(1,'session/prompt'))['admitted'])
        self.assertFalse(self.k.admitting)
        self.assertFalse(self.k.input(self.request(1,'session/prompt'))['admitted'])
        self.assertTrue(self.store.status()['jobs'])
    def test_input_eof_is_explicit_and_waits_for_existing_terminal_work(self):
        self.initialize();self.k.input(self.request(1,'session/prompt'))
        self.k.handle({'op':'finish-input'});self.assertFalse(self.k.child.stdin.closed)
        self.k.tracker.backend({'jsonrpc':'2.0','id':1,'result':{'stopReason':'end_turn'}})
        self.k.maybe_close_input();self.assertTrue(self.k.child.stdin.closed)
        self.assertFalse(self.store.status()['all_work_idle'])
    def test_existing_server_response_continues_when_new_admission_closed(self):
        self.initialize();self.k.input(self.request(1,'session/prompt'))
        self.k.tracker.backend({'jsonrpc':'2.0','id':'permission','method':'session/request_permission','params':{}})
        self.k.admitting=False;before=len(self.k.protocol.leases)
        result=self.k.input({'jsonrpc':'2.0','id':'permission','result':{'outcome':'allowed'}})
        self.assertTrue(result['admitted']);self.assertEqual(len(self.k.protocol.leases),before)
    def test_low_reserve_rejects_new_input_not_existing_work(self):
        self.initialize()
        with patch.object(p,'space',return_value=1):result=self.k.input(self.request(1,'session/prompt'))
        self.assertFalse(result['admitted']);self.assertFalse(self.k.child.stdin.closed)
    def test_boot_instance_change_rejects_new_request(self):
        self.k.protection=lambda:{'boot_id':'other','instance':self.binding['instance']}
        self.assertFalse(self.k.input(self.request(0,'initialize'))['admitted'])
        self.assertEqual(self.k.child.stdin.getvalue(),b'')
    def test_unconfirmed_native_receipt_cannot_accept_or_forward(self):
        self.k.receipt_confirmed=False
        self.assertFalse(self.k.input(self.request(0,'initialize'))['admitted'])
        self.assertEqual(self.k.child.stdin.getvalue(),b'')
    def test_ack_only_provider_result_never_becomes_terminal(self):
        self.initialize();self.k.input(self.request(1,'session/prompt'))
        self.k.tracker.backend({'jsonrpc':'2.0','id':1,'result':{'accepted':True}})
        entry=self.k.tracker.pending[('number',1)]
        self.assertFalse(entry['completed']);self.assertFalse(self.k.tracker.healthy)
        self.assertFalse(self.record(entry['lease'])['provider_terminal_observed'])
    def test_unsupported_clear_kill_ack_and_resume_actions_refused(self):
        for operation in ['clear','kill','ack','takeover','resume','replay']:
            with self.assertRaises(RuntimeError):self.k.handle({'op':operation})
    def test_incomplete_oversized_input_not_forwarded(self):
        before=self.k.child.stdin.getvalue()
        with self.assertRaises(RuntimeError):self.k.input(self.request(0,'initialize',{'text':'x'*p.acp.MAX_FRAME}))
        self.assertEqual(self.k.child.stdin.getvalue(),before);self.assertEqual(self.k.protocol.leases,{})
    def test_modified_request_custody_never_overwritten(self):
        self.initialize();lease=next(iter(self.k.protocol.leases.values()));path=self.store.job(lease['id'])/'record.json'
        changed=dict(lease,boot_id='other');p.shadow.publish(path,changed)
        with self.assertRaises(RuntimeError):self.k.protocol.heartbeat(lease)
        self.assertEqual(p.shadow.read(path,os.geteuid()),changed)
    def test_segments_reject_tampered_body(self):
        self.k.segments.append('stderr',b'fixture')
        (self.k.path/'output/000000000000.bin').write_bytes(b'changed')
        with self.assertRaises(RuntimeError):p.Segments.read(self.k.path/'output',0,os.geteuid())
    def test_segments_reject_symlink_payload(self):
        self.k.segments.append('stdout',b'fixture');path=self.k.path/'output/000000000000.bin'
        target=self.k.path/'elsewhere';path.rename(target);path.symlink_to(target)
        with self.assertRaises(OSError):p.Segments.read(self.k.path/'output',0,os.geteuid())
    def test_no_uncommitted_payload_exposed_after_uncertain_fsync(self):
        with patch.object(p.os,'fsync',side_effect=OSError('uncertain fsync')):
            with self.assertRaises(OSError):self.k.segments.append('stdout',b'fixture')
        self.assertEqual(self.k.segments.count,0)
        with self.assertRaises(FileNotFoundError):p.Segments.read(self.k.path/'output',0,os.geteuid())
        with self.assertRaises(FileExistsError):self.k.segments.append('stdout',b'NOT a retry')
        self.assertEqual((self.k.path/'output/000000000000.bin').read_bytes(),b'fixture')
    def test_output_quota_rejects_before_write_without_deleting_existing_data(self):
        with patch.object(p,'MAX_BYTES',3):
            with self.assertRaises(RuntimeError):self.k.segments.append('stdout',b'four')
        self.assertEqual(list((self.k.path/'output').iterdir()),[])
    def test_no_canonical_startup_or_delivery_API(self):
        text=Path(p.__file__).read_text()
        self.assertNotIn('work.Protocol(',text);self.assertNotIn('startup_ready(',text)
        self.assertNotIn('.unlink(',text);self.assertNotIn('kill(',text)
        with self.assertRaises(RuntimeError):self.k.protocol.remove('not-an-admin-clear')
        with self.assertRaises(RuntimeError):self.k.tracker.backend_output_delivered()
    def test_uncertain_child_wait_uses_kernel_child_set_not_process_absence(self):
        with patch.object(p.os,'waitpid',side_effect=[(123,0),(0,0)]):self.assertIsNone(p.UncertainChild().poll())
        with patch.object(p.os,'waitpid',side_effect=ChildProcessError):self.assertEqual(p.UncertainChild().poll(),75)


if __name__=='__main__':unittest.main()
