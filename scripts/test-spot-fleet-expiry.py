"""Pure native Fleet containment tests. Never creates AWS or guest work."""
from datetime import datetime, timezone
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

spec=importlib.util.spec_from_file_location('fleet',Path(__file__).with_name('spot-fleet-expiry.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
NOW=datetime(2026,10,29,tzinfo=timezone.utc)


def state():
    s=p.plan('afe012345678','ami-'+'a'*17,'b'*40,NOW);s.update(LT='lt-'+'a'*17,FleetId='sfr-test');return s


def ready():
    s=state();config=p.config(s);request={'SpotFleetRequestState':'active','SpotFleetRequestConfig':config}
    group={'AutoScalingGroupName':s['name'],'DesiredCapacity':0,'Instances':[],'MinSize':0,'MaxSize':1,
           'NewInstancesProtectedFromScaleIn':True,'CapacityRebalance':False,'DeletionProtection':'none',
           'SuspendedProcesses':[{'ProcessName':'Launch'}],
           'MixedInstancesPolicy':{'LaunchTemplate':{'LaunchTemplateSpecification':{'LaunchTemplateId':s['LT'],'Version':'1'}},
                                  'InstancesDistribution':{'OnDemandBaseCapacity':0,'OnDemandPercentageAboveBaseCapacity':0}}}
    actions=[{'MinSize':0,'MaxSize':0,'DesiredCapacity':0,'StartTime':s['off_at']}]
    return s,request,group,actions


class FleetTests(unittest.TestCase):
    def valid(self,change=None):
        args=ready()
        if change:change(*args)
        with patch.object(p.time,'time',return_value=NOW.timestamp()+30):p.validate_zero(*args)
    def test_fixed_native_expiry_not_local_process_deadline(self):
        s=state();self.assertEqual((datetime.fromisoformat(s['expires'])-NOW).total_seconds(),720);self.assertEqual((datetime.fromisoformat(s['off_at'])-NOW).total_seconds(),240)
    def test_fleet_starts_zero_100percent_spot_and_native_terminate(self):
        c=p.config(state());self.assertEqual(c['TargetCapacity'],0);self.assertEqual(c['OnDemandTargetCapacity'],0);self.assertTrue(c['TerminateInstancesWithExpiration']);self.assertEqual(c['Type'],'maintain');self.assertEqual(c['InstanceInterruptionBehavior'],'terminate')
    def test_no_guest_profile_keys_userdata_or_public_IP(self):
        d=p.b.launch_data(state());self.assertFalse({'IamInstanceProfile','UserData','KeyName'}&d.keys());self.assertFalse(d['NetworkInterfaces'][0]['AssociatePublicIpAddress']);self.assertEqual(d['CreditSpecification']['CpuCredits'],'standard')
    def test_mandatory_launch_tags_precede_tag_scoped_termination(self):
        s=state();policy=p.fleet_policy(s);run=policy['Statement'][2];self.assertEqual(run['Resource'],['arn:aws:ec2:'+p.b.REGION+':'+p.b.ACCOUNT+':instance/*','arn:aws:ec2:'+p.b.REGION+':'+p.b.ACCOUNT+':volume/*']);self.assertEqual(run['Condition']['StringEquals']['aws:RequestTag/ScopeId'],s['scope']);self.assertEqual(run['Condition']['StringEquals']['aws:RequestTag/ManagedBy'],'nixos-spot-validation');terminate=policy['Statement'][3];self.assertEqual(terminate['Condition']['StringEquals']['ec2:ResourceTag/ScopeId'],s['scope'])
    def test_no_general_tag_existing_foreign_resources_authority(self):
        rows=[r for r in p.fleet_policy(state())['Statement'] if r['Effect']=='Allow' and r['Action']=='ec2:CreateTags'];self.assertEqual(len(rows),2);self.assertTrue(all('ec2:CreateAction' in r['Condition']['StringEquals'] or 'ec2:ResourceTag/ScopeId' in r['Condition']['StringEquals'] for r in rows))
    def test_original_termination_and_storage_eip_mutations_explicitly_denied(self):
        rows=[r for r in p.fleet_policy(state())['Statement'] if r['Effect']=='Deny'];self.assertEqual(rows[0]['Action'],'ec2:TerminateInstances');self.assertTrue(rows[0]['Resource'].endswith('/i-0c39eff85c4286b38'));self.assertIn('ec2:AttachVolume',rows[1]['Action']);self.assertIn('iam:PassRole',rows[1]['Action'])
    def test_exact_native_zero_readback(self):self.valid()
    def test_no_expiry_no_terminate_or_nonzero_capacity_refuses(self):
        for key,bad in [('TerminateInstancesWithExpiration',False),('TargetCapacity',1),('OnDemandTargetCapacity',1),('InstanceInterruptionBehavior','stop')]:
            with self.subTest(key=key),self.assertRaises(RuntimeError):self.valid(lambda s,r,g,a:r['SpotFleetRequestConfig'].update({key:bad}))
    def test_asg_launch_must_stay_suspended_to_prevent_unbounded_replacement(self):
        with self.assertRaises(RuntimeError):self.valid(lambda s,r,g,a:g.update(SuspendedProcesses=[]))
        with self.assertRaises(RuntimeError):self.valid(lambda s,r,g,a:g.update(Instances=[{'InstanceId':'unexpected'}]))
    def test_protection_and_numeric_LT_cannot_be_substituted(self):
        with self.assertRaises(RuntimeError):self.valid(lambda s,r,g,a:g.update(NewInstancesProtectedFromScaleIn=False))
        with self.assertRaises(RuntimeError):self.valid(lambda s,r,g,a:g['MixedInstancesPolicy']['LaunchTemplate']['LaunchTemplateSpecification'].update(Version='$Latest'))
    def test_native_zero_action_must_match_original_absolute_deadline(self):
        with self.assertRaises(RuntimeError):self.valid(lambda s,r,g,a:a[0].update(MaxSize=1))
        with self.assertRaises(RuntimeError):self.valid(lambda s,r,g,a:a[0].update(StartTime='2026-10-29T01:00:00+00:00'))
    def test_fixed_single_pool_no_weighted_or_attribute_based_extra_capacity(self):
        for key,bad in [('WeightedCapacity',0.5),('InstanceRequirements',{'MemoryMiB':{'Min':1}}),('InstanceType','m8g.large')]:
            with self.subTest(key=key),self.assertRaises(RuntimeError):self.valid(lambda s,r,g,a:r['SpotFleetRequestConfig']['LaunchTemplateConfigs'][0]['Overrides'][0].update({key:bad}))
    def test_service_returned_LT_name_and_default_weight_are_not_false_failures(self):
        self.valid(lambda s,r,g,a:(r['SpotFleetRequestConfig']['LaunchTemplateConfigs'][0]['LaunchTemplateSpecification'].update(LaunchTemplateName=s['name']),r['SpotFleetRequestConfig']['LaunchTemplateConfigs'][0]['Overrides'][0].update(WeightedCapacity=1.0)))
    def test_setup_cannot_extend_or_outlive_native_deadline(self):
        args=ready()
        with patch.object(p.time,'time',return_value=NOW.timestamp()+200),self.assertRaises(RuntimeError):p.validate_zero(*args)
    def test_simulation_requires_actual_allow_and_explicit_original_deny(self):
        s=state();base='arn:aws:ec2:'+p.b.REGION+':'+p.b.ACCOUNT+':instance/';rows=[{'EvalResourceName':base+i,'EvalDecision':d} for i,d in [('i-0123456789abcdef0','allowed'),('i-0c39eff85c4286b38','explicitDeny')]];p.simulate_termination_authority(Mock(return_value={'EvaluationResults':rows}),s);rows[1]['EvalDecision']='allowed'
        with self.assertRaises(RuntimeError):p.simulate_termination_authority(Mock(return_value={'EvaluationResults':rows}),s)
    def test_activate_cannot_modify_capacity_before_fresh_zero_containment(self):
        api=Mock()
        with patch.object(p,'zero_readback',side_effect=RuntimeError('not verified')),self.assertRaisesRegex(RuntimeError,'not verified'):p.activate(api,state())
        api.assert_not_called()


if __name__=='__main__':unittest.main()
