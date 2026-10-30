"""Pure observer deployment rendering/owned-file rollback; no production calls."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

s=importlib.util.spec_from_file_location('observer_deployment',Path(__file__).with_name('spot-deploy-observer.py'));p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
SOURCE=Path(__file__).parent.parent
PYTHON='/nix/store/'+'a'*32+'-python3/bin/python3'
ARN='arn:aws:autoscaling:ap-northeast-2:537112465379:autoScalingGroup:12345678-1234-1234-1234-123456789abc:autoScalingGroupName/nixos-ec2-asg'


class DeployTests(unittest.TestCase):
    def test_rendered_service_is_resource_bounded_read_only(self):
        plan=p.render(SOURCE,PYTHON,ARN)
        for value in ['Type=exec','MemoryMax=256M','MemorySwapMax=0','CPUQuota=25%','OOMPolicy=kill','PrivateNetwork=yes','NoNewPrivileges=yes','ProtectControlGroups=yes']:self.assertIn(value,plan['service'])
        self.assertFalse(plan['marker']['termination_capable']);self.assertTrue(plan['no_full_guard_install_or_arming'])
    def test_persistent_lower_priority_path_does_not_replace_Nix_managed_etc(self):
        plan=p.render(SOURCE,PYTHON,ARN);self.assertEqual(plan['unit_directory'],'/usr/local/lib/systemd/system');self.assertIn('WantedBy=timers.target',plan['timer']);self.assertIn('OnBootSec=2min',plan['timer']);self.assertIn('Persistent=false',plan['timer'])
    def test_config_rejects_nonimmutable_interpreter(self):
        with self.assertRaises(RuntimeError):p.render(SOURCE,'/usr/bin/python3',ARN)
    def test_exclusive_owned_file_never_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'file';p.write_new(path,'first')
            with self.assertRaises(FileExistsError):p.write_new(path,'second')
            self.assertEqual(path.read_text(),'first')
    def test_directory_symlink_is_not_adopted(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'real').mkdir();(root/'link').symlink_to(root/'real')
            with self.assertRaises(RuntimeError):p.directory(root/'link',0o755)
    def test_no_global_reload_enable_switch_or_real_service_restart(self):
        text=Path(p.__file__).read_text()
        for value in ["['systemctl','daemon-reload'","['systemctl','enable'","['systemctl','restart'","['nixos-rebuild'","'set-instance-protection'","'set-desired-capacity'"]:self.assertNotIn(value,text)
    def test_unknown_rollback_id_refuses_before_any_command(self):
        with patch.object(p.os,'geteuid',return_value=0),patch.object(p.subprocess,'run') as run,self.assertRaises(RuntimeError):p.rollback({'id':'../../foreign'})
        run.assert_not_called()
    def fixture(self,d):
        root=Path(d);units=root/'units';units.mkdir();(units/'timers.target.wants').mkdir();marker=root/'current.json';gc=root/'gc';gc.mkdir();plan=p.render(SOURCE,PYTHON,ARN)
        for suffix in ['service','timer']:(units/plan[suffix+'_name']).write_text(plan[suffix])
        (units/'timers.target.wants'/plan['timer_name']).symlink_to('../'+plan['timer_name']);(gc/('spot-protection-observer-'+plan['id']+'-python')).symlink_to(plan['python_store_root']);marker.write_text(json.dumps(plan['marker']));return root,units,marker,gc,plan
    def test_foreign_marker_blocks_rollback_before_stop(self):
        with tempfile.TemporaryDirectory() as d:
            root,units,marker,gc,plan=self.fixture(d);marker.write_text('{}')
            with patch.object(p,'UNITS',units),patch.object(p,'MARKER',marker),patch.object(p,'GCROOTS',gc),patch.object(p.os,'geteuid',return_value=0),patch.object(p.subprocess,'run') as run,self.assertRaises(RuntimeError):p.rollback(plan)
            run.assert_not_called();self.assertTrue((units/plan['service_name']).exists())
    def test_foreign_GC_root_blocks_rollback_before_stop(self):
        with tempfile.TemporaryDirectory() as d:
            root,units,marker,gc,plan=self.fixture(d);link=gc/('spot-protection-observer-'+plan['id']+'-python');link.unlink();link.symlink_to('/nix/store/foreign')
            with patch.object(p,'UNITS',units),patch.object(p,'MARKER',marker),patch.object(p,'GCROOTS',gc),patch.object(p.os,'geteuid',return_value=0),patch.object(p.subprocess,'run') as run,self.assertRaises(RuntimeError):p.rollback(plan)
            run.assert_not_called()
    def test_exact_owned_rollback_only_stops_owned_names_preserves_diagnostics(self):
        with tempfile.TemporaryDirectory() as d:
            root,units,marker,gc,plan=self.fixture(d);evidence=root/'keep-log';evidence.write_text('retained')
            with patch.object(p,'UNITS',units),patch.object(p,'MARKER',marker),patch.object(p,'GCROOTS',gc),patch.object(p.os,'geteuid',return_value=0),patch.object(p.subprocess,'run') as run:result=p.rollback(plan)
            self.assertTrue(result['only_owned_read_only_observer_removed']);self.assertEqual(run.call_args.args[0],['systemctl','stop',plan['timer_name'],plan['service_name']]);self.assertFalse(marker.exists());self.assertTrue(evidence.exists())


if __name__=='__main__':unittest.main()
