"""Pure recovery infrastructure safety tests: no AWS/network/resources."""
import copy
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import Mock,patch

spec=importlib.util.spec_from_file_location('recovery',Path(__file__).with_name('spot-recovery-canary.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
NOW=datetime(2026,1,1,tzinfo=timezone.utc)


def state():
    s=p.plan('123456abcdef','f'*40,NOW)
    s.update(LT='lt-0123456789abcdef0',FleetId='sfr-01234567-0123-0123-0123-0123456789ab',
             role_arn='arn:aws:iam::'+p.b.ACCOUNT+':role/'+s['name'],
             profile_arn='arn:aws:iam::'+p.b.ACCOUNT+':instance-profile/'+s['name'],
             asg_arn='arn:aws:autoscaling:'+p.b.REGION+':'+p.b.ACCOUNT+':autoScalingGroup:exact-uuid:autoScalingGroupName/'+s['name'])
    return s


def ready():
    s=state();c=p.fleet_config(s);c['FulfilledCapacity']=0
    request={'SpotFleetRequestId':s['FleetId'],'SpotFleetRequestState':'active','SpotFleetRequestConfig':c}
    group={'AutoScalingGroupName':s['name'],'AutoScalingGroupARN':s['asg_arn'],'DesiredCapacity':0,'MinSize':0,'MaxSize':1,
           'Instances':[],'NewInstancesProtectedFromScaleIn':False,'CapacityRebalance':False,'SuspendedProcesses':[],
           'MixedInstancesPolicy':{'LaunchTemplate':{'LaunchTemplateSpecification':{'LaunchTemplateId':s['LT'],'Version':'1'},'Overrides':[{'InstanceType':'r7g.large'}]},
                                  'InstancesDistribution':{'OnDemandBaseCapacity':0,'OnDemandPercentageAboveBaseCapacity':0,'SpotAllocationStrategy':'lowest-price','SpotInstancePools':1,'SpotMaxPrice':'0.020'}}}
    actions=[{'AutoScalingGroupName':s['name'],'ScheduledActionName':s['name']+'-off','StartTime':s['asg_off_at'],'MinSize':0,'MaxSize':0,'DesiredCapacity':0}]
    hooks=[{'LifecycleHookName':s['name']+'-discard-new','LifecycleTransition':'autoscaling:EC2_INSTANCE_LAUNCHING','HeartbeatTimeout':30,'DefaultResult':'ABANDON'}]
    lt={'ImageId':p.b.AMI,'InstanceType':'r7g.large','IamInstanceProfile':{'Name':s['name']},'SecurityGroupIds':[p.f.b.SG],
        'MetadataOptions':{'HttpTokens':'required'},'BlockDeviceMappings':[{'DeviceName':'/dev/xvda','Ebs':{'VolumeSize':32,'VolumeType':'gp3','Encrypted':True,'DeleteOnTermination':True}}]}
    lt['TagSpecifications']=[{'ResourceType':kind,'Tags':s['tags']} for kind in ['instance','volume']]
    return s,request,group,actions,hooks,lt


class RecoveryTests(unittest.TestCase):
    def valid(self,change=None):
        args=ready()
        if change:change(*args)
        with patch.object(p.time,'time',return_value=NOW.timestamp()+30):p.validate_zero(*args)

    def test_fixed_dual_native_deadlines_never_extend_on_activation(self):
        s=state();self.assertEqual((datetime.fromisoformat(s['expires'])-NOW).total_seconds(),6600)
        self.assertEqual((datetime.fromisoformat(s['expires'])-datetime.fromisoformat(s['asg_off_at'])).total_seconds(),300)
        self.valid()

    def test_no_on_demand_nonzero_capacity_or_nonexpiring_Fleet(self):
        for change in [lambda s,r,g,a,h,l:r['SpotFleetRequestConfig'].update(TargetCapacity=1),lambda s,r,g,a,h,l:r['SpotFleetRequestConfig'].update(TargetCapacity=False),lambda s,r,g,a,h,l:r['SpotFleetRequestConfig'].update(OnDemandTargetCapacity=1),lambda s,r,g,a,h,l:r['SpotFleetRequestConfig'].update(TerminateInstancesWithExpiration=False)]:
            with self.assertRaises(RuntimeError):self.valid(change)

    def test_changed_expiry_pool_or_symbolic_LT_is_not_authority(self):
        for change in [lambda s,r,g,a,h,l:r['SpotFleetRequestConfig'].update(ValidUntil=NOW.isoformat()),lambda s,r,g,a,h,l:r['SpotFleetRequestConfig']['LaunchTemplateConfigs'][0]['LaunchTemplateSpecification'].update(Version='$Latest'),lambda s,r,g,a,h,l:r['SpotFleetRequestConfig']['LaunchTemplateConfigs'][0]['Overrides'].append({'InstanceType':'m8g.large'})]:
            with self.assertRaises(RuntimeError):self.valid(change)

    def test_protection_or_foreign_ASG_cannot_obtain_build_authority(self):
        for update in [{'NewInstancesProtectedFromScaleIn':True},{'AutoScalingGroupARN':'reused-name-foreign-UUID'},{'SuspendedProcesses':[{'ProcessName':'Launch'}]}]:
            with self.assertRaises(RuntimeError):self.valid(lambda s,r,g,a,h,l:g.update(update))

    def test_absent_continue_or_external_lifecycle_guard_refuses_capacity(self):
        for change in [lambda s,r,g,a,h,l:h.clear(),lambda s,r,g,a,h,l:h[0].update(DefaultResult='CONTINUE'),lambda s,r,g,a,h,l:h[0].update(NotificationTargetARN='external')]:
            with self.assertRaises(RuntimeError):self.valid(change)

    def test_root_userdata_profile_or_model_authority_cannot_be_substituted(self):
        for update in [{'ImageId':'ami-00000000000000000'},{'UserData':'anything'},{'KeyName':'operator'},{'IamInstanceProfile':{'Name':'nixos-ec2-ssm-profile'}},{'BlockDeviceMappings':[]}]:
            with self.assertRaises(RuntimeError):self.valid(lambda s,r,g,a,h,l:l.update(update))

    def test_late_native_window_or_recurring_off_refuses(self):
        with self.assertRaises(RuntimeError):
            with patch.object(p.time,'time',return_value=NOW.timestamp()+6500):p.validate_zero(*ready())
        with self.assertRaises(RuntimeError):self.valid(lambda s,r,g,a,h,l:a[0].update(Recurrence='* * * * *'))

    def test_customer_Fleet_passes_only_its_exact_disposable_guest_role(self):
        s=state();rows=p.fleet_policy(s)['Statement'];passed=[r for r in rows if r['Effect']=='Allow' and r['Action']=='iam:PassRole']
        self.assertEqual(len(passed),1);self.assertEqual(passed[0]['Resource'],s['role_arn']);self.assertEqual(passed[0]['Condition']['StringEquals']['iam:PassedToService'],'ec2.amazonaws.com')
        self.assertTrue(any(r['Effect']=='Deny' and r['Action']=='ec2:TerminateInstances' and p.b.PRODUCTION in r['Resource'] for r in rows))

    def test_guest_protection_only_exact_owned_ASG_storage_and_termination_stay_denied(self):
        s=state();rows=p.guest_policy(s)['Statement'];allowed=[r for r in rows if r['Effect']=='Allow' and r['Action']=='autoscaling:SetInstanceProtection']
        self.assertEqual([r['Resource'] for r in allowed],[s['asg_arn']]);denied={a for r in rows if r['Effect']=='Deny' for a in r['Action']}
        self.assertTrue({'ec2:AttachVolume','ec2:DetachVolume','ec2:AssociateAddress','ec2:TerminateInstances','ec2:CreateSnapshot','autoscaling:SetDesiredCapacity'}<=denied)
        self.assertNotIn('autoscaling:SetInstanceProtection',denied)

    def test_invalid_reference_cannot_create_even_zero_resources(self):
        api=Mock()
        with self.assertRaisesRegex(RuntimeError,'reference bytes differ'):p.create_zero(api,state(),{'forged_green':True})
        self.assertEqual(api.call_count,0)

    def test_pinned_reference_requires_fresh_native_history_and_actor_not_just_capture(self):
        data=json.loads((Path(__file__).parent/'evidence/protected-expiry-a6401bc9d875.json').read_text());events=data['termination_events'];api=Mock(side_effect=[{'SpotFleetRequestConfigs':[data['request']]},data['history'],{'Events':[{'CloudTrailEvent':json.dumps(events[0])}]},{'Events':[{'CloudTrailEvent':json.dumps(events[1])}]}])
        result=p.reference(api,data);self.assertTrue(result['independent_disposable_protected_expiry_verified']);self.assertEqual(api.call_count,4)
        changed=copy.deepcopy(data);changed['capture']['goal_complete']=True
        with self.assertRaises(RuntimeError):p.reference(Mock(),changed)

    def test_fresh_zero_failure_prevents_the_only_paid_request(self):
        api=Mock()
        with patch.object(p,'zero_readback',side_effect=RuntimeError('unknown containment')):
            with self.assertRaises(RuntimeError):p.activate(api,state())
        self.assertEqual(api.call_count,0)

    def test_lost_paid_reply_is_not_replayed_or_mistaken_for_launch_success(self):
        api=Mock(side_effect=RuntimeError('lost reply'))
        with patch.object(p,'zero_readback'):
            with self.assertRaisesRegex(RuntimeError,'lost reply'):p.activate(api,state())
        self.assertEqual(api.call_count,1);self.assertEqual(api.call_args.args[:2],('ec2','modify-spot-fleet-request'))


if __name__=='__main__':unittest.main()
