#!/usr/bin/env python3
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent))
import spot_shadow_review as r


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
        self.addCleanup(patch.stopall)
        patch.object(r,'boot',return_value='fixture').start();patch.object(r,'namespace',return_value='pid:[fixture]').start()
        patch.object(r.shadow.os,'readlink',return_value='pid:[fixture]').start()
        def start(pid):
            if pid in {30001,30002}:raise FileNotFoundError()
            return 10
        patch.object(r.work,'process_start',side_effect=start).start()
        root=self.base/'store';root.mkdir(mode=0o700);self.store=r.shadow.Store(root,os.getuid())
        self.binding={'boot_id':'fixture','instance':'i-'+'1'*17};self.store.initialize(self.binding)
        startup=self.store.create(self.binding,['metadata only']);self.store.update(startup,kind='shadow_tui_startup',
            pid=30001,pid_start=7,pid_namespace='pid:[fixture]')
        keeper=self.store.create(self.binding,['metadata only']);self.store.update(keeper,kind='acp_keeper',
            pid=30003,pid_start=9,output_segments=0)
        self.startup,self.keeper=startup,keeper
        actor=self.store.create(self.binding,['metadata only']);self.store.update(actor,kind='shadow_kiro_frontend',
            parent_startup=startup['id'],actor={'pid':30002,'pid_start':8,'uid':1001,'pid_namespace':'pid:[fixture]'})
        self.actor=actor;self.folder=self.base/('a'*32);self.folder.mkdir(mode=0o711)
        d={'session':keeper['id'],'pid':30003,'pid_start':9,'boot_id':'fixture'}
        for name,value in [('session.json',{'id':self.folder.name,'binding':self.binding}),('keeper.json',d),
            ('frontend.json',{'startup':startup['id'],'keeper':d}),
            ('keeper-start-intent.json',{'startup':startup['id'],'boot_id':'fixture'})]:r.shadow.publish(self.folder/name,value,new=True)
        self.segments=r.acp.Segments(self.store.job(keeper['id'])/'output',self.store.owner)

    def append(self,data=b'ONLY synthetic response\n',channel='stdout',visible=True):
        row=self.segments.append(channel,data,visible=visible)
        self.store.update(self.keeper,output_segments=self.segments.count)
        return row

    def review(self):
        r.provision(self.store,r.selected(self.store,self.folder));v=r.Review(self.store,self.folder);self.addCleanup(v.close);return v

    def test_explicit_provision_never_reseeds_partial_or_existing_namespace(self):
        value=r.selected(self.store,self.folder);r.provision(self.store,value)
        with self.assertRaises(RuntimeError):r.provision(self.store,value)
        (self.store.job(self.keeper['id'])/'output-review/seed.json').unlink()
        with self.assertRaises((FileNotFoundError,RuntimeError)):r.Review(self.store,self.folder)

    def test_missing_review_seed_is_not_empty_or_implicitly_created(self):
        with self.assertRaises(FileNotFoundError):r.Review(self.store,self.folder)

    def test_live_original_controller_refused(self):
        with patch.object(r.work,'process_start',return_value=7):
            with self.assertRaisesRegex(RuntimeError,'controller still alive'):r.selected(self.store,self.folder)

    def test_live_original_actor_refused(self):
        def start(pid):
            if pid==30001:raise FileNotFoundError()
            return 8
        with patch.object(r.work,'process_start',side_effect=start):
            with self.assertRaisesRegex(RuntimeError,'actor still alive'):r.selected(self.store,self.folder)

    def test_old_boot_or_PID_namespace_is_not_takeover_authority(self):
        for value in [dict(self.startup,boot_id='previous'),dict(self.startup,pid_namespace='other')]:
            with self.assertRaisesRegex(RuntimeError,'epoch/namespace'):r.exited(value)

    def test_reused_PID_proves_only_exact_old_consumer_exit(self):
        with patch.object(r.work,'process_start',return_value=999):self.assertTrue(r.exited(self.startup))
        self.assertFalse(self.store.status()['all_work_idle'])

    def test_missing_or_multiple_actor_records_are_unknown(self):
        self.store.update(self.actor,parent_startup='other')
        with self.assertRaisesRegex(RuntimeError,'binding missing/conflicting'):r.selected(self.store,self.folder)

    def test_partial_job_header_is_not_an_empty_actor_roster(self):
        (self.store.root/'jobs'/('job-'+'f'*32)).mkdir(mode=0o700)
        with self.assertRaises(FileNotFoundError):r.selected(self.store,self.folder)

    def test_conflicting_viewer_cannot_attach_or_create_a_second_lease(self):
        view=self.review();before=len(list((self.store.root/'jobs').iterdir()))
        with self.assertRaises(r.ReviewConflict):r.Review(self.store,self.folder)
        self.assertEqual(before,len(list((self.store.root/'jobs').iterdir())))
        view.close()
        second=r.Review(self.store,self.folder);self.addCleanup(second.close)
        self.assertNotEqual(second.lease['id'],view.lease['id'])

    def test_explicit_new_output_review_retains_all_previous_views_and_original_record(self):
        self.append();before=(self.store.job(self.keeper['id'])/'record.json').read_bytes();view=self.review();writes=[]
        self.assertEqual(r.terminal(view,writes.append,lambda:'q'),0);old=view.lease.copy();view.close()
        second=r.Review(self.store,self.folder);self.addCleanup(second.close)
        self.assertTrue((view.root/'views'/old['id']).exists());self.assertEqual(old['consumer_delivery'],'unverified')
        self.assertEqual((self.store.job(self.keeper['id'])/'record.json').read_bytes(),before)

    def test_actual_exposed_segment_length_and_SHA_verified(self):
        expected=self.append(b'\x00\xffbinary\n');view=self.review();row=view.read(0)
        self.assertEqual(base64.b64decode(row['data_base64']),b'\x00\xffbinary\n');self.assertEqual(row['sha256'],expected['sha256'])

    def test_missing_output_inventory_is_not_zero_or_empty(self):
        view=self.review();record=dict(self.keeper);record.pop('output_segments');r.shadow.publish(self.store.job(record['id'])/'record.json',record)
        with self.assertRaisesRegex(RuntimeError,'inventory unknown'):view.read(0)

    def test_incomplete_actor_identity_refused(self):
        self.store.update(self.actor,actor={'pid':30002,'pid_start':8,'pid_namespace':'pid:[fixture]'})
        with self.assertRaisesRegex(RuntimeError,'identity incomplete'):r.selected(self.store,self.folder)

    def test_unexposed_committed_body_is_not_rendered_or_marked_delivered(self):
        self.append(visible=False);view=self.review();self.assertIsNone(view.read(0))
        self.assertEqual(view.lease['consumer_delivery'],'unverified')

    def test_tampered_exposure_refused_before_page_effect(self):
        self.append();view=self.review();path=self.store.job(self.keeper['id'])/'output/000000000000.bin';path.write_bytes(b'tampered')
        writes=[]
        with self.assertRaises(RuntimeError):r.terminal(view,writes.append,lambda:'q')
        self.assertEqual(writes,[])

    def test_replaced_spool_refused(self):
        self.append();view=self.review();path=self.store.job(self.keeper['id'])/'output';path.rename(path.with_name('old-output'));path.mkdir(mode=0o700)
        with self.assertRaisesRegex(RuntimeError,'spool replaced'):view.read(0)

    def test_uncertain_terminal_write_is_not_retried_or_followed_by_next_read(self):
        self.append();self.append(b'second');view=self.review();calls=[]
        def fail(text):calls.append(text);raise OSError('fixture write receipt lost')
        with patch.object(view,'read',wraps=view.read) as read:
            with self.assertRaises(OSError):r.terminal(view,fail,lambda:'n')
            self.assertEqual(read.call_count,1)
        self.assertEqual(len(calls),1);self.assertEqual(view.lease['rendered_pages'],0)
        self.assertEqual(view.lease['state'],'review_presentation_or_custody_uncertain_no_retry')

    def test_page_and_EOF_are_not_delivery_ack_or_retirement(self):
        self.append(b'x'*(r.PAGE+1));view=self.review();keys=iter(['n','']);writes=[]
        self.assertEqual(r.terminal(view,writes.append,lambda:next(keys)),0)
        self.assertEqual(view.lease['rendered_pages'],2);self.assertEqual(view.lease['consumer_delivery'],'unverified')
        self.assertIn('NOT delivery acknowledgement',writes[-1]);self.assertFalse(self.store.status()['all_work_idle'])

    def test_all_terminal_control_and_bidi_invalid_bytes_are_literal_not_executed(self):
        text=r.safe_text('한글\n\x1b]52;c;secret\x07\r\u202e\\'.encode()+b'\xff')
        self.assertIn('한글\n',text)
        for char in ['\x1b','\x07','\r','\u202e']:self.assertNotIn(char,text)
        self.assertIn('\\xff',text);self.assertIn('\\u202e',text)

    def test_build_budget_cannot_authorize_review_verification(self):
        for purpose in ['build','canary-build']:
            with patch.object(r.validation,'current',return_value={'purpose':purpose}):
                with self.assertRaisesRegex(RuntimeError,'borrow build'):r.resource_gate()

    def test_source_has_no_provider_input_or_implicit_keeper_finish_or_delivery_authority(self):
        text=Path(r.__file__).read_text()
        for token in ['.input(',"{'op':",'startup_ready(','.initialize(','SIGKILL','SIGTERM']:
            self.assertNotIn(token,text)
        self.assertIn('LOCK_EX|fcntl.LOCK_NB',text);self.assertIn("consumer_delivery='unverified'",text)


if __name__=='__main__':unittest.main()
