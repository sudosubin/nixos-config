#!/usr/bin/env python3
import inspect
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent))
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
    def test_config_requires_exact_fields_hashes_and_original_lineage(self):
        spec=importlib.util.spec_from_file_location('deploy_for_runtime_test',Path(__file__).parents[2]/'scripts/spot-deploy-shadow-tui.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        cfg=module.render(Path(__file__).parents[2],'/nix/store/'+'a'*32+'-python/bin/python3')['config']
        self.assertEqual(p.settings(cfg),cfg)
        for changes in [{'backend':'/bin/sh'},{'bun_sha256':'f'*64},{'schema':True},{'consumer_delivery':True}]:
            with self.assertRaises(RuntimeError):p.settings(dict(cfg,**changes))


if __name__=='__main__':unittest.main()
