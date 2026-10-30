#!/usr/bin/env python3
import base64
import hashlib
import importlib.util
import inspect
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch

s=importlib.util.spec_from_file_location('warm_ui_test',Path(__file__).with_name('spot_shadow_ui.py'))
p=importlib.util.module_from_spec(s);s.loader.exec_module(p)


class BrokerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.root.chmod(0o700)
        self.store=p.shadow.Store(self.root,os.geteuid());self.binding={'boot_id':'fixture','instance':'i-0123456789abcdef0'}
        self.store.initialize(self.binding)
        self.start=patch.object(p.work,'process_start',return_value=77);self.start.start()
        self.ns=patch.object(p.os,'readlink',return_value='pid:[42]');self.ns.start()
        startup=self.store.create(self.binding,['new fixture UI'])
        self.b=p.Broker(self.store,self.binding,startup,{'pid':99,'pid_start':77,'socket':'/private/keeper'},
                        '/immutable/entry','/owned/cgroup','/owned/isolated-home','/immutable/native',
                        {'frontend':'/immutable/front','proxy':'/immutable/proxy'})
        self.b.check_parent=Mock(return_value={'pid':100,'pid_start':77})
    def tearDown(self):self.ns.stop();self.start.stop();self.temp.cleanup()
    def test_output_digest_verified_before_any_offer(self):
        self.b.keeper_rpc=Mock(return_value={'segment':{'channel':'stdout','sequence':0,'bytes':4,'sha256':'a'*64,'data_base64':base64.b64encode(b'fake').decode()}})
        with self.assertRaises(RuntimeError):self.b.handle(123,{'op':'acp-read','sequence':0})
        self.assertEqual(self.b.census.offered,{})
    def test_verified_stdout_offer_precedes_return_to_actor(self):
        body=b'fixture';row={'channel':'stdout','sequence':0,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'data_base64':base64.b64encode(body).decode()}
        self.b.keeper_rpc=Mock(return_value={'segment':row})
        self.assertEqual(self.b.handle(123,{'op':'acp-read','sequence':0}),{'segment':row})
        self.assertEqual(self.b.census.offered,{0:row['sha256']})
    def test_unverified_proxy_rebind_does_not_resume_or_replay_input(self):
        self.b.keeper_rpc=Mock(return_value={'admitted':True})
        self.b.handle(123,{'op':'acp-input','frame':{'method':'initialize'}})
        with self.assertRaises(RuntimeError):self.b.handle(124,{'op':'acp-input','frame':{'method':'initialize'}})
        self.assertEqual(self.b.keeper_rpc.call_count,1)
    def test_native_helper_cannot_select_another_backend_or_unbound_empty_route(self):
        with self.assertRaises(RuntimeError):self.b.handle(123,{'op':'native-once','arguments':[]})
        with self.assertRaises(RuntimeError):self.b.handle(123,{'op':'native-once','arguments':['acp']})
        with self.assertRaises(RuntimeError):self.b.handle(123,{'op':'exec','backend':'/bin/sh'})
    def test_opaque_wrapper_uses_explicit_home_after_lease_not_host_default(self):
        text=inspect.getsource(p.Broker.handle)
        self.assertIn('self.home',text);self.assertIn('u.opaque_run',text)
        self.assertNotIn('value=s.run(',text)
        text=inspect.getsource(p.opaque_run);self.assertIn('acp.drop_command(backend,arguments,home',text)
        self.assertIn('work.run_job(adapter,command)',text)
    def test_no_full_admission_readiness_or_delivery_authority(self):
        text=Path(p.__file__).read_text()
        self.assertNotIn('work.Protocol(',text);self.assertNotIn('startup_ready(',text)
        self.assertNotIn('.unlink(',text);self.assertNotIn('kill(',text)
        self.assertIn('no automatic input replay',text)


if __name__=='__main__':unittest.main()
