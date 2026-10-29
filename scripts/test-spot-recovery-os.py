"""Pure metadata predicates. NOT real OS/home recovery evidence."""
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('recovery_os',Path(__file__).parents[1]/'modules/linux/verify-spot-recovery-os.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)


def ready():
    units={u:{'ActiveState':'active','Result':'success','MainPID':'123'} for u in p.UNITS}
    return {'startup':{'state':'ready'},'home_uuid':'fixture','expected_home_uuid':'fixture','protected':True,'units':units,'HM_fixture_started':True}


def closed():
    row=ready();row.update(startup={'state':'starting'},home_uuid='',HM_fixture_started=False,attach_failed=True)
    for name in ['docker','user@1001']:row['units'][name]['MainPID']='0'
    return row


class Predicates(unittest.TestCase):
    def test_positive_requires_real_ready_mount_protection_cache_and_live_services(self):
        self.assertTrue(p.ready(ready()))
        for change in [lambda r:r.update(home_uuid='wrong'),lambda r:r.update(protected=False),lambda r:r['units']['spot-profile-cache-restore'].update(Result='failed'),lambda r:r['units']['docker'].update(MainPID='0')]:
            row=ready();change(row);self.assertFalse(p.ready(row))
    def test_closed_is_not_idle_or_production_approval(self):
        self.assertTrue(p.closed(closed()));self.assertFalse(p.ready(closed()))
    def test_wrong_home_needs_timeout_and_actual_attach_failure(self):
        self.assertFalse(p.complete('wrong',[closed()],30));self.assertTrue(p.complete('wrong',[closed()],160));row=closed();row['attach_failed']=False;self.assertFalse(p.complete('wrong',[row],160))
    def test_delayed_requires_both_prior_closed_and_later_actual_ready(self):
        self.assertFalse(p.complete('delayed',[ready()],200));self.assertTrue(p.complete('delayed',[closed(),ready()],200))
    def test_unknown_or_empty_observation_does_not_complete(self):
        for case in ['positive','wrong','delayed','unknown']:self.assertFalse(p.complete(case,[],999))
        self.assertFalse(p.ready({}));self.assertFalse(p.closed({}))
    def test_observer_reads_the_real_protocol_startup_location(self):
        import inspect
        protocol=Path(__file__).parents[1]/'modules/linux/spot_work.py';spec=importlib.util.spec_from_file_location('real_work',protocol);work=importlib.util.module_from_spec(spec);spec.loader.exec_module(work)
        text=inspect.getsource(p.observe);self.assertIn(str(work.RUNTIME/'startup'),text);self.assertNotIn("trusted('/run/spot-work/startup')",text)

    def test_storage_or_service_mutations_never_spawn(self):
        for action in [('ec2','attach-volume'),('ec2','terminate-instances'),('autoscaling','set-instance-protection'),('ssm','send-command')]:
            with patch.object(p.subprocess,'run') as run,self.assertRaises(RuntimeError):p.api(*action)
            run.assert_not_called()


if __name__=='__main__':unittest.main()
