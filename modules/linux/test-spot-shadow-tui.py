#!/usr/bin/env python3
import inspect
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
HERE=Path(__file__).parent
sys.path.insert(0,str(HERE))
import spot_shadow_tui as p


class RuntimeTests(unittest.TestCase):
    def test_agent_names_are_not_arbitrary_command_or_legacy_route(self):
        self.assertEqual(p.arguments('spot-canary'),['--agent','spot-canary'])
        for value in ['../../old','--legacy-ui','a b','a\x00b','a'*65,'']:
            with self.assertRaises(RuntimeError):p.arguments(value)
    def test_vendor_entry_uses_pinned_copied_runtime_and_not_user_bundle(self):
        artifacts=p.artifacts('/owned/source','/nix/store/fixture/bin/python3','/owned/runtime/bun','/owned/runtime/tui.js')
        self.assertIn('/owned/runtime/tui.js',artifacts['entry.mjs'])
        self.assertIn('installWarmFrontend(',artifacts['entry.mjs'])
        self.assertNotIn('KIRO_ACP_RECORD_PATH',artifacts['entry.mjs'])
    def test_private_verification_inherits_exact_budget_no_application_elevation(self):
        budget={'purpose':'verify','slice':'spotvalidation'+'a'*32+'.slice','memory_max':1024**3}
        with patch.object(p.validation,'current',return_value=budget):
            value=p.app_budget('/unused');self.assertTrue(value['fixture']);self.assertEqual(value['memory_max'],1024**3)
        for purpose in ['build','canary-build']:
            with patch.object(p.validation,'current',return_value=dict(budget,purpose=purpose)):
                with self.assertRaises(RuntimeError):p.app_budget('/unused')
    def test_keeper_fixture_namespace_alone_is_not_authority(self):
        folder=Path('/owned/'+'b'*32);name=p.keeper_unit(folder,{'fixture':True})
        self.assertEqual(name,'spot-resource-validation-'+'b'*12+'.service')
        # Actual v.current still demands root owner, current boot and all
        # kernel memory/swap/CPU/OOM fences; this string alone grants nothing.
        self.assertIn('validation.current()',inspect.getsource(p.app_budget))
    def test_no_backend_deadline_stop_restart_or_EOF_when_frontend_exits(self):
        text=inspect.getsource(p.run_session)
        for value in ['RuntimeMaxSec','systemctl\',\'stop','finish-input','kill(','terminate(']:self.assertNotIn(value,text)
        self.assertIn('broker.close()',text);self.assertIn('Resident keeper',text)
    def test_service_limits_and_network_never_widen_private_fixture(self):
        props=p.properties({'slice':'owned.slice','memory_max':1024**3,'fixture':True})
        self.assertIn('--property=PrivateNetwork=yes',props);self.assertIn('--property=MemoryMax=1073741824',props)
        self.assertIn('--property=MemorySwapMax=0',props);self.assertIn('--property=CPUQuota=100%',props)
        self.assertNotIn('--property=RuntimeMaxSec=0',props)
    def test_normal_application_budget_is_not_build_permission(self):
        self.assertEqual(p.APP_MAX,2*1024**3);self.assertEqual(p.APP_MIN,4*1024**3)
        text=inspect.getsource(p.launch_application)
        self.assertIn('nested application authority refused',text);self.assertNotIn('daemon-reload',text)
        self.assertIn("memory.oom.group",text);self.assertIn('unknown processes',text)
    def test_initializer_accepts_only_same_owned_root_metadata_and_exact_gate(self):
        before={10:{'start':1,'uid':0,'cgroup':'owned/client'}}
        after=dict(before)
        after[20]={'start':2,'uid':0,'cgroup':'owned/keeper'}
        p.initializer_members(before,after,10,20,'owned/client','owned/keeper')
    def test_initializer_refuses_any_live_UID1001_before_or_during_sibling_start(self):
        root={10:{'start':1,'uid':0,'cgroup':'owned/client'}}
        user={30:{'start':3,'uid':1001,'cgroup':'owned/client'}}
        with self.assertRaisesRegex(RuntimeError,'live user participant'):
            p.initializer_members(root|user,root,10,20,'owned/client','owned/keeper')
        with self.assertRaisesRegex(RuntimeError,'live user participant'):
            p.initializer_members(root,root|user,10,20,'owned/client','owned/keeper')
    def test_initializer_does_not_repair_unknown_or_foreign_metadata_cages(self):
        before={10:{'start':1,'uid':0,'cgroup':'owned/client'}}
        after={10:before[10],99:{'start':9,'uid':0,'cgroup':'foreign/root'}}
        with self.assertRaisesRegex(RuntimeError,'unknown participant'):
            p.initializer_members(before,after,10,20,'owned/client','owned/keeper')
        text=inspect.getsource(p.initialize_keeper_budget)
        self.assertLess(text.index('initializer_members('),text.index("write_text('1')"))
        self.assertIn('definition_sha256',text);self.assertIn('current_group()',text)
    def test_unix_kernel_path_bound_is_checked_before_any_native_effect(self):
        p.unix_endpoint(Path('/tmp/stui-'+'a'*32+'/store/jobs/job-'+'b'*32+'/keeper.sock'))
        p.unix_endpoint(Path('/var/lib/spot-work-shadow/498e2c5726a5/jobs/job-'+'a'*32+'/keeper.sock'))
        with self.assertRaisesRegex(RuntimeError,'AF_UNIX'):
            p.unix_endpoint(Path('/tmp/spotshadowtuifixture-'+'a'*32+'/store/jobs/job-'+'b'*32+'/keeper.sock'))
        self.assertLess(inspect.getsource(p.prepare).index('unix_endpoint('),inspect.getsource(p.prepare).index('folder.mkdir('))
    def test_exited_keeper_metadata_is_not_unrealized_while_frontend_is_live(self):
        self.assertIn('--property=RemainAfterExit=yes',inspect.getsource(p.run_session))
        text=inspect.getsource(p.collect_empty_metadata)
        self.assertLess(text.index('scope_members('),text.index("['systemctl','stop',name]"))
        self.assertIn("ui.shadow.require(pid=='0'",text);self.assertIn('fragment_sha256',text)
        self.assertNotIn('.unlink(',text);self.assertNotIn('kill(',text)
    def test_metadata_collector_refuses_live_cage_without_any_stop(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'unit';path.write_bytes(b'owned exited metadata')
            folder=Path('/owned/'+'a'*32);budget={'slice':'owned.slice','fixture':True}
            receipt={'unit':p.keeper_unit(folder,budget),'boot_id':'fixture','fragment':str(path),
                     'fragment_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
            values=iter([{'budget':budget},receipt,{'pid':42,'pid_start':77,'boot_id':'fixture'}])
            fields=iter([b'42\n',b'active\n',b'running\n',(str(path)+'\n').encode()])
            with patch.object(p,'session',return_value={'binding':{'boot_id':'fixture'}}),patch.object(p.ui.shadow,'read',side_effect=lambda *_:next(values)),\
                 patch.object(p.subprocess,'check_output',side_effect=lambda *a,**kw:next(fields).decode()),\
                 patch.object(p,'scope_members',return_value={123:{'uid':1001}}),patch.object(p.ui.work,'process_start',return_value=77),patch.object(p.subprocess,'run') as run:
                with self.assertRaisesRegex(RuntimeError,'live/foreign/uncertain'):p.collect_empty_metadata({'session_directory':d},folder)
                run.assert_not_called()
    def test_verifier_partial_header_is_explicit_pending_NOT_empty(self):
        spec=importlib.util.spec_from_file_location('entry_proof',HERE/'verify-spot-shadow-tui-entry.py')
        proof=importlib.util.module_from_spec(spec);spec.loader.exec_module(proof)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);old=root/'job-old';old.mkdir();new=root/'job-new';new.mkdir()
            reader=lambda path:json.loads(path.read_text())
            with self.assertRaises(proof.PublicationPending):proof.new_records(root,{'job-old'},reader)
            (new/'record.json').write_text('{"positive":"durable header"}')
            self.assertEqual(proof.new_records(root,{'job-old'},reader),[{'positive':'durable header'}])
    def test_verifier_does_not_hide_malformed_header_as_transient_or_empty(self):
        spec=importlib.util.spec_from_file_location('entry_proof',HERE/'verify-spot-shadow-tui-entry.py')
        proof=importlib.util.module_from_spec(spec);spec.loader.exec_module(proof)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'job-new').mkdir();(root/'job-new/record.json').write_text('malformed')
            with self.assertRaises(json.JSONDecodeError):proof.new_records(root,{},lambda path:json.loads(path.read_text()))
    def test_config_requires_exact_fields_hashes_and_original_lineage(self):
        spec=importlib.util.spec_from_file_location('deploy_for_runtime_test',Path(__file__).parents[2]/'scripts/spot-deploy-shadow-tui.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        cfg=module.render(Path(__file__).parents[2],'/nix/store/'+'a'*32+'-python/bin/python3')['config']
        self.assertEqual(p.settings(cfg),cfg)
        for changes in [{'backend':'/bin/sh'},{'bun_sha256':'f'*64},{'schema':True},{'consumer_delivery':True}]:
            with self.assertRaises(RuntimeError):p.settings(dict(cfg,**changes))


if __name__=='__main__':unittest.main()
