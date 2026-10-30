#!/usr/bin/env python3
import importlib.util
import inspect
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).parent.parent;sys.path.insert(0,str(ROOT/'modules/linux'))
s=importlib.util.spec_from_file_location('deploy_review',Path(__file__).with_name('spot-deploy-shadow-review.py'))
p=importlib.util.module_from_spec(s);s.loader.exec_module(p)


class Tests(unittest.TestCase):
    def test_installer_never_starts_models_review_namespaces_or_changes_services(self):
        source=inspect.getsource(p.install)
        for word in ['subprocess','daemon-reload','startup_ready','initialize(','provision(','systemctl','systemd-run']:
            self.assertNotIn(word,source)
    def test_root_existing_shadow_and_runtime_lineage_pinned(self):
        plan=p.render(ROOT,'/nix/store/fixture-python/bin/python3')
        self.assertEqual(plan['shadow_id'],'498e2c5726a5');self.assertEqual(len(plan['source_hashes']),6)
        self.assertEqual(plan['marker']['store_directory'],'/var/lib/spot-work-shadow/498e2c5726a5')
        self.assertFalse(plan['marker']['consumer_delivery_verified']);self.assertFalse(plan['marker']['termination_capable'])
    def test_interpreter_must_be_immutable_isolated(self):
        with self.assertRaises(RuntimeError):p.render(ROOT,'/tmp/python')
        self.assertIn(' -I\n',p.render(ROOT,'/nix/store/fixture/bin/python3')['entry'])
    def test_disable_refuses_Nix_or_foreign_discovery_and_retains_data(self):
        source=inspect.getsource(p.disable)
        self.assertIn('MARKER.is_symlink()',source);self.assertNotIn('rmtree',source)
        self.assertNotIn('systemctl',source);self.assertIn('all_data_code_views_pins_retained',source)
    def test_declarative_module_is_explicit_no_auto_start_and_no_new_seed(self):
        text=(ROOT/'modules/linux/spot-output-review.nix').read_text()
        self.assertIn('mkEnableOption',text)
        for word in ['wantedBy','initialize(','provision(','systemd.services']:self.assertNotIn(word,text)
        self.assertIn('spot-output-review',text)


if __name__=='__main__':unittest.main()
