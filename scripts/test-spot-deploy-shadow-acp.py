#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

s=importlib.util.spec_from_file_location('acp_install_test',Path(__file__).with_name('spot-deploy-shadow-acp.py'))
p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
SOURCE=Path(__file__).parent.parent


class DeployTests(unittest.TestCase):
    def plan(self):return p.render(SOURCE,'/nix/store/'+'a'*32+'-python/bin/python3')
    def test_reuses_existing_shadow_namespace_not_empty_new_registry(self):
        plan=self.plan();self.assertEqual(plan['config']['shadow_deployment_id'],'498e2c5726a5')
        self.assertEqual(plan['config']['store_directory'],'/var/lib/spot-work-shadow/498e2c5726a5')
    def test_pinned_four_sources_and_native_sha(self):
        plan=self.plan();self.assertEqual(set(plan['source_hashes']),{'spot_work.py','spot_shadow.py','spot_acp.py','spot_shadow_acp.py'})
        self.assertEqual(plan['config']['backend_sha256'],'1c2a36ec26bae2bdd8d5d7cbb77606f4d072b8bc1a5cfcc6b582ae4a047ce479')
    def test_mutable_interpreter_refused(self):
        with self.assertRaises(RuntimeError):p.render(SOURCE,'/usr/bin/python3')
    def test_installer_never_starts_restarts_stops_or_reloads_any_app(self):
        text=Path(p.__file__).read_text()
        for value in ["'start'","'restart'","'stop'","'daemon-reload'",'nixos-rebuild','initialize(']:
            self.assertNotIn(value,text)
    def test_no_environment_hook_before_boundary(self):
        entry=self.plan()['entry'];self.assertIn('python3 -I',entry)
        self.assertNotIn('/bin/sh',entry);self.assertIn('dont_write_bytecode=True',entry)
    def test_disable_preserves_sessions_data_source_and_pins(self):
        import inspect
        text=inspect.getsource(p.disable)
        self.assertEqual(text.count('.unlink()'),1)
        self.assertNotIn('systemctl',text);self.assertNotIn('rmtree',text)
        self.assertNotIn('kill(',text)
    def test_Nix_marker_replacement_refuses_disable(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);target=root/'nix-marker';target.write_text(json.dumps(self.plan()['marker']));marker=root/'marker';marker.symlink_to(target)
            with patch.object(p,'MARKER',marker),patch.object(p.os,'geteuid',return_value=0):
                with self.assertRaises(RuntimeError):p.disable(self.plan())
            self.assertTrue(marker.is_symlink())
    def test_future_Nix_config_never_auto_starts_a_provider(self):
        text=(SOURCE/'modules/linux/spot-work-shadow-acp.nix').read_text()
        self.assertNotIn('wantedBy =',text);self.assertNotIn('ExecStart =',text)
        self.assertIn('consumer_delivery_verified = false;',text)
        self.assertIn('expectedBackendSHA',text);self.assertIn('MUST be retested',text)


if __name__=='__main__':unittest.main()
