"""Pure observation completeness tests; no cloud or work/idle authority."""
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

file=Path(__file__).parents[1]/'modules/linux/verify-spot-fleet-expiry-aws.py'
spec=importlib.util.spec_from_file_location('observer',file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def complete():
    return {'instances':{'i-test':{'state':'terminated','root_absent':True}},'seen_protected_running':True,'seen_zero_requested_but_protected_running':True,'last_fleet_state':'cancelled_terminating','after_native_expiry':True}


class ObserverTests(unittest.TestCase):
    def test_explicit_terminal_and_root_absence_can_complete_capture_only(self):self.assertTrue(m.capture_complete(complete()))
    def test_missing_EC2_history_or_unknown_state_is_not_terminal(self):
        for state in ['running','shutting-down','stopped',None]:
            v=complete();v['instances']['i-test']['state']=state;self.assertFalse(m.capture_complete(v))
    def test_no_instances_or_root_still_present_cannot_complete(self):
        for changes in [{'instances':{}},{'instances':{'i-test':{'state':'terminated','root_absent':False}}}]:self.assertFalse(m.capture_complete({**complete(),**changes}))
    def test_protected_and_zero_request_facts_are_both_required(self):
        for key in ['seen_protected_running','seen_zero_requested_but_protected_running','after_native_expiry']:
            v=complete();v[key]=False;self.assertFalse(m.capture_complete(v))
    def test_active_fleet_cannot_be_replaced_by_termination_ack(self):
        v=complete();v['last_fleet_state']='active';self.assertFalse(m.capture_complete(v))
    def test_all_seen_instances_are_required_not_just_latest(self):
        v=complete();v['instances']['i-other']={'state':'running'};self.assertFalse(m.capture_complete(v))
    def test_cloud_mutation_or_other_observation_API_never_spawns(self):
        for pair in [('ec2','terminate-instances'),('autoscaling','set-instance-protection'),('ssm','send-command'),('s3api','put-object')]:
            with self.subTest(pair=pair),patch.object(m.subprocess,'run') as run,self.assertRaises(RuntimeError):m.call(*pair)
            run.assert_not_called()


if __name__=='__main__':unittest.main()
