#!/usr/bin/env python3
import base64
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent))
import spot_shadow_output as p


class StopFixture(BaseException):pass


class OutputTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.root.chmod(0o700)
        for target,value in [(p.shadow.work,'process_start'),(p.shadow.os,'readlink')]:
            mock=patch.object(target,value,return_value=77 if value=='process_start' else 'pid:[42]')
            mock.start();self.addCleanup(mock.stop)
        self.store=p.shadow.Store(self.root,os.geteuid());self.binding={'boot_id':'fixture','instance':'i-0123456789abcdef0'}
        self.store.initialize(self.binding);self.lease=self.store.create(self.binding,['synthetic output'])
        self.spool=p.Output(self.store,self.lease)
        self.space=patch.object(p.acp,'space',return_value=p.acp.RESERVE+10000000);self.space.start();self.addCleanup(self.space.stop)
    def test_complete_binary_both_channels_retained_before_bridge(self):
        self.spool.retain('stdout',b'\x00synthetic\xff');self.spool.retain('stderr',b'fixture-error');self.spool.finish()
        result=p.bridge_output(self.store,self.lease['id'])
        self.assertEqual(base64.b64decode(result['stdout']),b'\x00synthetic\xff')
        self.assertEqual(base64.b64decode(result['stderr']),b'fixture-error')
        self.assertEqual(self.lease['output_delivery'],'unverified');self.assertFalse(self.store.status()['all_work_idle'])
    def test_no_bridge_before_explicit_EOF_completion(self):
        self.spool.retain('stdout',b'not complete')
        with self.assertRaises(RuntimeError):p.bridge_output(self.store,self.lease['id'])
    def test_corrupt_payload_is_never_returned_as_consumer_output(self):
        self.spool.retain('stdout',b'original');self.spool.finish()
        (self.spool.segments.directory/'000000000000.bin').write_bytes(b'tampered')
        with self.assertRaises(RuntimeError):p.bridge_output(self.store,self.lease['id'])
    def test_cumulative_bridge_limit_not_independent_channel_limits(self):
        self.spool.retain('stdout',b'123');self.spool.retain('stderr',b'456');self.spool.finish()
        with patch.object(p,'BRIDGE_BYTES',5),self.assertRaisesRegex(RuntimeError,'NOT truncated'):
            p.bridge_output(self.store,self.lease['id'])
        self.assertEqual(len(list(self.spool.segments.directory.glob('*.bin'))),2)
    def test_space_backpressure_before_any_write_then_continues_without_replay(self):
        values=iter([0,p.acp.RESERVE+100,p.acp.RESERVE+100])
        with patch.object(p.acp,'space',side_effect=lambda *_:next(values)),patch.object(p.time,'sleep'):
            self.spool.retain('stdout',b'one')
        self.assertTrue(self.spool.pressure);self.assertEqual(self.spool.segments.count,1)
        self.assertEqual(self.lease['state'],'helper_output_backpressure')
        self.assertFalse(self.lease['output_complete'])
    def test_quota_never_deletes_or_closes_accepted_output(self):
        self.spool.retain('stdout',b'123')
        with patch.object(p.acp,'MAX_BYTES',3),patch.object(p.time,'sleep',side_effect=StopFixture):
            with self.assertRaises(StopFixture):self.spool.retain('stderr',b'4')
        self.assertEqual(self.spool.segments.count,1);self.assertFalse(self.spool.uncertain)
        self.assertTrue((self.spool.segments.directory/'000000000000.bin').exists())
    def test_uncertain_append_receipt_is_not_retried_or_followed_by_exposure(self):
        saved=self.spool.segments.append
        def committed_then_error(*args,**kw):saved(*args,**kw);raise OSError('synthetic lost write receipt')
        with patch.object(self.spool.segments,'append',side_effect=committed_then_error) as append,patch.object(self.spool,'hold',side_effect=StopFixture):
            with self.assertRaises(StopFixture):self.spool.retain('stdout',b'once')
        self.assertEqual(append.call_count,1);self.assertEqual(self.spool.segments.count,1)
        self.assertFalse((self.spool.segments.directory/'000000000000.exposed').exists())
        self.assertTrue(self.spool.uncertain);self.assertFalse(self.lease['output_complete'])
    def test_uncertain_exposure_is_not_retried(self):
        saved=self.spool.segments.expose
        def committed_then_error(*args):saved(*args);raise OSError('synthetic lost exposure receipt')
        with patch.object(self.spool.segments,'expose',side_effect=committed_then_error) as expose,patch.object(self.spool,'hold',side_effect=StopFixture):
            with self.assertRaises(StopFixture):self.spool.retain('stdout',b'once')
        self.assertEqual(expose.call_count,1);self.assertTrue(self.spool.uncertain)
    def test_reader_uses_bounded_chunks_and_waits_for_both_EOFs(self):
        streams={'stdout':io.BytesIO(b'a'*(p.CHUNK+17)),'stderr':io.BytesIO(b'err')}
        self.spool.start(streams);self.spool.finish()
        self.assertEqual(self.lease['output_bytes'],p.CHUNK+20)
        self.assertEqual(self.lease['output_segments'],3)
        self.assertTrue(all(s.closed for s in streams.values()))
    def test_capacity_check_and_append_are_serialized_across_readers(self):
        self.spool.start({'stdout':io.BytesIO(b'out'),'stderr':io.BytesIO(b'err')});self.spool.finish()
        rows=[p.acp.Segments.read(self.spool.segments.directory,n,self.store.owner) for n in range(2)]
        self.assertEqual({r['channel'] for r in rows},{'stdout','stderr'})
        self.assertEqual(self.lease['output_bytes'],6)
    def test_no_read_retry_or_close_after_uncertain_stream_error(self):
        class Broken:
            closed=False;reads=0
            def read1(self,_):self.reads+=1;raise OSError('synthetic uncertain read')
            def close(self):self.closed=True
        stream=Broken()
        with patch.object(self.spool,'hold',side_effect=StopFixture):
            with self.assertRaises(StopFixture):self.spool.reader('stdout',stream)
        self.assertEqual(stream.reads,1);self.assertFalse(stream.closed);self.assertTrue(self.spool.uncertain)
    def test_output_count_tamper_does_not_return_a_short_success(self):
        self.spool.retain('stdout',b'full');self.spool.finish()
        path=self.store.job(self.lease['id'])/'record.json';value=p.shadow.read(path,self.store.owner)
        value['output_segments']=0;p.shadow.publish(path,value)
        with self.assertRaises(RuntimeError):p.bridge_output(self.store,self.lease['id'])


if __name__=='__main__':unittest.main()
