#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

s=importlib.util.spec_from_file_location('shadow_deploy_test',Path(__file__).with_name('spot-deploy-shadow.py'))
p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
SOURCE=Path(__file__).parent.parent


class DeployTests(unittest.TestCase):
    def plan(self): return p.render(SOURCE,'/nix/store/'+'a'*32+'-python/bin/python3')
    def test_pinned_package_and_no_default_user_launcher_replacement(self):
        plan=self.plan();self.assertEqual(plan['config']['uid'],1001)
        self.assertIn('/var/lib/spot-work-shadow/',plan['cli'])
        self.assertEqual(set(plan['source_hashes']),{'spot_work.py','spot_shadow.py'})
        self.assertFalse(plan['marker']['work_tracking_verified'])
    def test_reject_mutable_interpreter(self):
        with self.assertRaises(RuntimeError):p.render(SOURCE,'/usr/bin/python3')
    def test_collector_budget_and_no_worker_exec(self):
        service=self.plan()['service']
        for value in ['MemoryMax=256M','MemorySwapMax=0','CPUQuota=25%','OOMPolicy=kill','NoNewPrivileges=yes','PrivateNetwork=yes','ProtectControlGroups=yes',' collect']:
            self.assertIn(value,service)
        self.assertNotIn(' run',service)
    def test_never_global_reload_switch_enable_or_existing_service_restart(self):
        text=Path(p.__file__).read_text()
        for value in ["'daemon-reload'","'enable'","'restart'",'nixos-rebuild',"'Protocol('"]:
            self.assertNotIn(value,text)
    def test_disable_preserves_job_data_and_runtime_pins(self):
        import inspect
        text=inspect.getsource(p.disable)
        self.assertNotIn('rmtree',text);self.assertNotIn('GCROOTS',text)
        self.assertNotIn('kill',text);self.assertIn('FragmentPath',text)
    def test_Nix_marker_refuses_before_unit_stop(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);target=root/'nix-marker';target.write_text(json.dumps(self.plan()['marker']));marker=root/'marker';marker.symlink_to(target)
            with patch.object(p,'MARKER',marker),patch.object(p.os,'geteuid',return_value=0),patch.object(p.subprocess,'run') as run:
                with self.assertRaises(RuntimeError):p.disable(self.plan())
                run.assert_not_called()
    def test_static_timer_not_a_paid_scheduler_or_force_deadline(self):
        text=self.plan()['timer']
        self.assertIn('OnUnitInactiveSec=1min',text);self.assertIn('Persistent=false',text)
        self.assertNotIn('StopWhenUnneeded',text)
    def test_seed_and_existing_work_are_explicitly_not_ready(self):
        text=Path(p.__file__).read_text()
        self.assertIn("value['all_work_idle'] is False",text)
        self.assertIn("'legacy_Kiro_Herdr_launchers_modified':False",text)
        self.assertIn('before == after',text)


if __name__=='__main__':unittest.main()
