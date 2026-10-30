#!/usr/bin/env python3
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

s=importlib.util.spec_from_file_location('warm_front_test',Path(__file__).with_name('spot_shadow_frontend.py'))
p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
IDLE={'initialized':True,'queued':0,'pending_steer':False,'processing':False,'actions':0,'draft':False}


class CensusTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.root.chmod(0o700)
        self.store=p.shadow.Store(self.root,os.geteuid());self.binding={'boot_id':'private','instance':'i-0123456789abcdef0'}
        self.store.initialize(self.binding)
        self.start=patch.object(p.work,'process_start',return_value=77);self.start.start()
        self.ns=patch.object(p.os,'readlink',return_value='pid:[42]');self.ns.start()
        self.startup=self.store.create(self.binding,['explicit new frontend startup'])
        self.c=p.Census(self.store,self.binding,self.startup,lambda:dict(self.binding))
        self.actor={'pid':123,'pid_start':88,'uid':1001,'cgroup':'private','entry':'/immutable/entry'}
        self.attached=self.c.attach({'startup':self.startup['id']},self.actor);self.seq=0
    def tearDown(self):self.ns.stop();self.start.stop();self.temp.cleanup()
    def invoke(self,action,**kwargs):
        self.seq+=1;return self.c.invoke(action,{'id':self.attached['id'],'seq':self.seq,**kwargs},self.actor)
    def test_attach_retains_startup_and_creates_distinct_bound_record(self):
        self.assertEqual(len(self.store.status()['jobs']),2)
        self.assertEqual(self.c.record['actor'],self.actor)
        self.assertTrue(self.attached['accepted']);self.assertFalse(self.store.status()['all_work_idle'])
    def test_duplicate_attach_never_rebinds_or_resets(self):
        with self.assertRaises(RuntimeError):self.c.attach({'startup':self.startup['id']},self.actor)
    def test_wrong_startup_not_attached(self):
        c=p.Census(self.store,self.binding,self.startup,lambda:dict(self.binding))
        with self.assertRaises(RuntimeError):c.attach({'startup':'job-'+'f'*32},self.actor)
    def test_actor_change_refuses_before_counter_mutation(self):
        before=dict(self.c.record)
        with self.assertRaises(RuntimeError):self.c.invoke('heartbeat',{'id':self.attached['id'],'seq':1},dict(self.actor,pid_start=99))
        self.assertEqual(self.c.record,before)
    def test_draft_queue_actions_remain_explicit_local_work(self):
        self.invoke('state',counters=dict(IDLE,draft=True,queued=2,actions=1))
        self.assertEqual(self.c.record['state'],'frontend_local_work_unverified')
        self.assertTrue(self.c.record['counters']['draft'])
        self.assertFalse(self.store.status()['all_work_idle'])
    def test_empty_counters_never_retire_epoch_or_prove_idle(self):
        self.invoke('state',counters=IDLE)
        self.assertEqual(self.c.record['state'],'frontend_local_quiescent_NOT_idle')
        self.invoke('close');self.assertEqual(len(self.store.status()['jobs']),2)
        self.assertEqual(self.c.record['output_delivery'],'unverified')
    def test_busy_close_refused_without_deleting_custody(self):
        self.invoke('state',counters=dict(IDLE,queued=1))
        with self.assertRaises(RuntimeError):self.invoke('close')
        self.assertTrue((self.store.job(self.c.record['id'])/'record.json').exists())
    def test_unknown_counters_are_not_published_as_idle(self):
        with self.assertRaises(ValueError):self.invoke('state',counters=dict(IDLE,queued=True))
        self.assertNotIn('counters',self.c.record)
    def test_fresh_protection_required_for_new_admission(self):
        self.c.protection=lambda:{'boot_id':'different','instance':self.binding['instance']}
        self.assertFalse(self.invoke('admit')['accepted'])
        self.assertEqual(self.c.record['admission_rejections'],1)
    def test_state_continuation_allowed_behind_protection_fault(self):
        self.c.protection=lambda:(_ for _ in ()).throw(RuntimeError('unknown'))
        self.assertFalse(self.invoke('admit')['accepted'])
        self.assertTrue(self.invoke('state',counters=dict(IDLE,processing=True))['accepted'])
    def test_wrong_sequence_does_not_replay_state(self):
        with self.assertRaises(RuntimeError):self.c.invoke('state',{'id':self.attached['id'],'seq':9,'counters':IDLE},self.actor)
        self.assertEqual(self.c.record['seq'],0)
    def test_root_actor_loss_keeps_sequence_and_custody_without_rearming(self):
        self.invoke('state',counters=dict(IDLE,draft=True));seq=self.c.record['seq']
        self.c.actor_unknown();self.c.actor_unknown()
        self.assertEqual(self.c.record['seq'],seq);self.assertFalse(self.c.record['healthy'])
        self.assertEqual(self.c.record['state'],'frontend_actor_exit_or_identity_unknown')
        self.assertEqual(len(self.store.status()['jobs']),2)
        self.assertFalse(self.invoke('admit')['accepted'])
        self.invoke('state',counters=IDLE);self.assertFalse(self.c.record['healthy'])
        self.assertEqual(self.c.record['output_delivery'],'unverified')
    def test_fault_is_sticky_but_does_not_clear_record(self):
        self.invoke('fault');self.assertFalse(self.invoke('admit')['accepted'])
        self.invoke('state',counters=IDLE)
        self.assertFalse(self.c.record['healthy']);self.assertFalse(self.store.status()['all_work_idle'])
    def test_parse_prefix_watermark_matches_offered_stdout_only(self):
        rows=[{'sequence':2,'channel':'stdout','sha256':'a'*64},{'sequence':4,'channel':'stdout','sha256':'b'*64}]
        chain=hashlib.sha256(b'').hexdigest()
        for row in rows:self.c.offer(row);chain=hashlib.sha256((chain+':'+str(row['sequence'])+':'+row['sha256']).encode()).hexdigest()
        self.invoke('parsed',output={'sequence':4,'chain':chain,'count':2})
        self.assertEqual(self.c.record['parsed_output_count'],2)
        self.assertEqual(self.c.record['parsed_output_stage'],'JSON_parsed_before_dispatch_NOT_UI_delivery')
        self.assertEqual(self.c.record['output_delivery'],'unverified')
    def test_fake_or_regressed_parse_watermark_refused(self):
        self.c.offer({'sequence':0,'channel':'stdout','sha256':'a'*64})
        with self.assertRaises(RuntimeError):self.invoke('parsed',output={'sequence':0,'chain':'b'*64,'count':1})
        self.assertEqual(self.c.record['parsed_output_count'],0)
    def test_same_output_offer_idempotent_but_changed_digest_refused(self):
        row={'sequence':0,'channel':'stdout','sha256':'a'*64};self.c.offer(row);self.c.offer(row)
        self.assertEqual(len(self.c.offered),1)
        with self.assertRaises(RuntimeError):self.c.offer(dict(row,sha256='b'*64))
    def test_stderr_is_not_false_JSON_parse_receipt(self):
        with self.assertRaises(RuntimeError):self.c.offer({'sequence':1,'channel':'stderr','sha256':'a'*64})
    def test_unknown_ack_clear_takeover_operations_refused(self):
        for action in ['ack','clear','takeover','ready']:
            with self.assertRaises(RuntimeError):self.invoke(action)
    def test_metadata_no_private_prompt_text_interface(self):
        self.invoke('state',counters=dict(IDLE,draft=True))
        self.assertEqual(set(self.c.record['counters']),set(IDLE))
        text=Path(p.__file__).read_text();self.assertNotIn('work.Protocol(',text)
        self.assertNotIn('startup_ready(',text);self.assertNotIn('.unlink(',text)


if __name__=='__main__':unittest.main()
