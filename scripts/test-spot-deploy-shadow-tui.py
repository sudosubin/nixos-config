#!/usr/bin/env python3
import importlib.util
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

s=importlib.util.spec_from_file_location('tui_installer_test',Path(__file__).with_name('spot-deploy-shadow-tui.py'))
p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
SOURCE=Path(__file__).parent.parent


class DeployTests(unittest.TestCase):
    def plan(self):return p.render(SOURCE,'/nix/store/'+'a'*32+'-python/bin/python3')
    def test_uses_existing_shadow_store_not_new_ready_registry(self):
        plan=self.plan();self.assertEqual(plan['config']['shadow_deployment_id'],'498e2c5726a5')
        self.assertEqual(plan['config']['store_directory'],'/var/lib/spot-work-shadow/498e2c5726a5')
    def test_all_source_dependencies_and_public_vendor_hashes_pinned(self):
        plan=self.plan();self.assertEqual(len(plan['source_hashes']),12)
        self.assertIn('spot_shadow_output.py',plan['source_hashes']);self.assertIn('spot_validation.py',plan['source_hashes'])
        self.assertEqual(plan['config']['bun_sha256'],'67892bb6734ef352f90a964f0a2a680d5f6e6d15bdb5510e56b8065ac4d599ae')
        self.assertEqual(plan['config']['tui_sha256'],'67cec0aace08d9bef505ea135b908333edfb7e5ad049c3ffa678ed7bcb133384')
    def test_interpreter_is_immutable_and_ignores_user_hooks(self):
        with self.assertRaises(RuntimeError):p.render(SOURCE,'/usr/bin/python3')
        self.assertIn('python3 -I',self.plan()['entry']);self.assertIn('dont_write_bytecode=True',self.plan()['entry'])
    def test_public_entry_loads_owned_bundle_not_user_mutable_bundle(self):
        plan=self.plan();entry=plan['artifacts']['entry.mjs']
        self.assertIn(plan['config']['tui'],entry);self.assertNotIn('process.env.HOME',entry)
        self.assertIn('installWarmFrontend(',entry)
    def test_install_never_starts_stops_restarts_reloads_or_seeds(self):
        text=inspect.getsource(p.install)
        for word in ['initialize(',"'start'","'stop'","'restart'",'daemon-reload','nixos-rebuild','run_session(']:
            self.assertNotIn(word,text)
    def test_disable_is_only_discovery_and_refuses_Nix_symlink(self):
        text=inspect.getsource(p.disable);self.assertEqual(text.count('.unlink()'),1)
        self.assertNotIn('kill(',text);self.assertNotIn('systemctl',text)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);target=root/'nix';target.write_text(json.dumps(self.plan()['marker']));marker=root/'marker';marker.symlink_to(target)
            with patch.object(p,'MARKER',marker),patch.object(p.os,'geteuid',return_value=0):
                with self.assertRaises(RuntimeError):p.disable(self.plan())
            self.assertTrue(marker.is_symlink())
    def test_declarative_package_requires_public_vendor_inputs_and_does_not_auto_start(self):
        text=(SOURCE/'modules/linux/spot-work-shadow-tui.nix').read_text()
        self.assertIn('vendorBun',text);self.assertIn('vendorTui',text)
        self.assertIn('consumer_delivery_verified = false;',text)
        self.assertIn('MUST be retested',text)
        self.assertNotIn('wantedBy =',text);self.assertNotIn('ExecStart =',text)
        configuration=(SOURCE/'modules/linux/configuration.nix').read_text()
        self.assertIn('services.spotWorkShadowTui.enable = false;',configuration)
    def test_public_copy_is_exclusive_and_digest_bound(self):
        import hashlib
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'source';source.write_bytes(b'public fixture software');target=root/'target'
            p.copy_public(source,target,hashlib.sha256(source.read_bytes()).hexdigest(),0o444)
            self.assertEqual(target.read_bytes(),source.read_bytes())
            with self.assertRaises(FileExistsError):p.copy_public(source,target,'a'*64,0o444)
            with self.assertRaises(RuntimeError):p.copy_public(source,root/'changed','b'*64,0o444)
            self.assertTrue((root/'changed').exists(),'uncertain/failed copy must be retained')


if __name__=='__main__':unittest.main()
