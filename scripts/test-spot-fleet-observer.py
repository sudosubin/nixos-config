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
    def recovery(self):
        scope='a'*12;name=m.subject(scope,'recovery');root='vol-'+'b'*17;home='vol-'+'c'*17
        instance={'InstanceLifecycle':'spot','ImageId':'ami-0d44956a8229b0dad','PublicIpAddress':'192.0.2.1','IamInstanceProfile':{'Arn':'arn:aws:iam::'+m.ACCOUNT+':instance-profile/'+name},'BlockDeviceMappings':[{'DeviceName':'/dev/xvda','Ebs':{'VolumeId':root,'DeleteOnTermination':True}}]}
        def volume(size,purpose):return {'Volumes':[{'Size':size,'Encrypted':True,'Tags':[{'Key':'ScopeId','Value':scope},{'Key':'ManagedBy','Value':'nixos-spot-validation'},{'Key':'Purpose','Value':purpose}]}]}
        return scope,instance,home,volume
    def test_recovery_is_metadata_only_exact_profile_image_and_single_root(self):
        scope,i,home,volume=self.recovery()
        with patch.object(m,'call',return_value=volume(32,'artifact-test')):self.assertEqual(m.live_identity(scope,i,'recovery'),i['BlockDeviceMappings'][0]['Ebs']['VolumeId'])
        i['IamInstanceProfile']['Arn']='arn:aws:iam::'+m.ACCOUNT+':instance-profile/nixos-ec2-ssm-profile'
        with self.assertRaises(RuntimeError):m.live_identity(scope,i,'recovery')
    def test_recovery_may_observe_only_its_owned_encrypted16GiB_test_home(self):
        scope,i,home,volume=self.recovery();i['BlockDeviceMappings'].append({'DeviceName':'/dev/sdf','Ebs':{'VolumeId':home,'DeleteOnTermination':False}})
        with patch.object(m,'call',side_effect=[volume(32,'artifact-test'),volume(16,'recovery-home')]):m.live_identity(scope,i,'recovery')
        bad=volume(16,'daily-home')
        with patch.object(m,'call',side_effect=[volume(32,'artifact-test'),bad]),self.assertRaises(RuntimeError):m.live_identity(scope,i,'recovery')
    def test_retained_storage_or_unknown_purpose_never_obtains_observation_approval(self):
        scope,i,home,volume=self.recovery();i['BlockDeviceMappings'][0]['Ebs']['VolumeId']='vol-09fea2ff4615b1088'
        with self.assertRaises(RuntimeError):m.live_identity(scope,i,'recovery')
        with self.assertRaises(RuntimeError):m.subject(scope,'general-networked-validation')

    def test_cloud_mutation_or_other_observation_API_never_spawns(self):
        for pair in [('ec2','terminate-instances'),('autoscaling','set-instance-protection'),('ssm','send-command'),('s3api','put-object')]:
            with self.subTest(pair=pair),patch.object(m.subprocess,'run') as run,self.assertRaises(RuntimeError):m.call(*pair)
            run.assert_not_called()


if __name__=='__main__':unittest.main()
