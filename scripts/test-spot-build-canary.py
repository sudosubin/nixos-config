"""Pure infrastructure transition tests: NO AWS calls or created resources."""
import copy
from datetime import datetime,timezone,timedelta
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('canary',Path(__file__).with_name('spot-build-canary.py'))
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)


class Fake:
    def __init__(self,state):
        self.state=state;self.events=[];self.group=None;self.actions=[];self.bad=None
    def account(self):self.events.append(('account',))
    def upload(self,bucket,key,value):self.events.append(('upload',key,copy.deepcopy(value)))
    def __call__(self,service,action,*args):
        self.events.append((service,action,args));values=list(args)
        def arg(name):return values[values.index(name)+1]
        name=self.state['name']
        if action=='describe-auto-scaling-groups':
            if self.bad=='existing':return {'AutoScalingGroups':[{'AutoScalingGroupName':name}]}
            g=copy.deepcopy(self.group)
            if g and self.bad=='protected':g['NewInstancesProtectedFromScaleIn']=True
            if g and self.bad=='ondemand':g['MixedInstancesPolicy']['InstancesDistribution']['OnDemandPercentageAboveBaseCapacity']=100
            return {'AutoScalingGroups':[] if g is None else [g]}
        if action=='list-role-policies':return {'PolicyNames':list(c.BASELINE)+(['unknown'] if self.bad=='baseline' else [])}
        if action=='get-role-policy':return {'PolicyDocument':{'name':arg('--policy-name')}}
        if action=='describe-images':return {'Images':[{'State':'unavailable' if self.bad=='image' else 'available','Architecture':'arm64'}]}
        if action=='create-role':return {'Role':{'Arn':'arn:aws:iam::'+c.ACCOUNT+':role/'+name}}
        if action=='create-instance-profile':return {'InstanceProfile':{'Arn':'arn:aws:iam::'+c.ACCOUNT+':instance-profile/'+name}}
        if action=='create-launch-template':return {'LaunchTemplate':{'LaunchTemplateId':'lt-0123456789abcdef0'}}
        if action=='create-auto-scaling-group':
            self.group={'DesiredCapacity':0,'Instances':[],'NewInstancesProtectedFromScaleIn':False,'MixedInstancesPolicy':json.loads(arg('--mixed-instances-policy'))}
            self.group['MixedInstancesPolicy']['LaunchTemplate']['LaunchTemplateSpecification']['LaunchTemplateName']=name
        if action=='put-scheduled-update-group-action':
            self.actions=[{'AutoScalingGroupName':name,'ScheduledActionName':name+'-off','StartTime':arg('--start-time'),'MinSize':0,'MaxSize':0,'DesiredCapacity':0}]
        if action=='describe-scheduled-actions':
            rows=copy.deepcopy(self.actions)
            if self.bad=='expiry-missing':rows=[]
            if self.bad=='expiry-later':rows[0]['StartTime']=(datetime.fromisoformat(self.state['expires'])+timedelta(hours=1)).isoformat()
            if self.bad=='expiry-recurring':rows[0]['Recurrence']='* * * * *'
            if self.bad=='expiry-bool':rows[0]['DesiredCapacity']=False
            return {'ScheduledUpdateGroupActions':rows}
        return {}


class ProvisionTests(unittest.TestCase):
    def setUp(self):
        self.state=c.plan('123456abcdef','f'*40);self.state['creator_script_sha256']='a'*64;self.api=Fake(self.state)
        original=c.digest
        p=patch.object(c,'digest',side_effect=lambda v:c.BASELINE[v['name']] if set(v)=={'name'} else original(v));p.start();self.addCleanup(p.stop)
    def requested(self):return any(e[:2]==('autoscaling','set-desired-capacity') for e in self.api.events)
    def rejected(self,condition):
        self.api.bad=condition
        with self.assertRaises(RuntimeError):c.create(self.api,self.state)
        self.assertFalse(self.requested())

    def test_invalid_scope_source_or_naive_clock_cannot_create_plan(self):
        for scope,source in [('nixos-ec2-asg','f'*40),('../bad','f'*40),('123456abcdef','main')]:
            with self.subTest(scope=scope,source=source),self.assertRaises(ValueError):c.plan(scope,source)
        with self.assertRaises(ValueError):c.plan('123456abcdef','f'*40,datetime(2026,1,1))

    def test_plan_fixed_namespace_and_bounded_native_deadline(self):
        now=datetime(2026,1,1,tzinfo=timezone.utc);s=c.plan('123456abcdef','f'*40,now)
        self.assertEqual(s['name'],'nixos-spot-proof-123456abcdef');self.assertNotEqual(s['name'],'nixos-ec2-asg')
        self.assertEqual((datetime.fromisoformat(s['expires'])-now).total_seconds(),6600)
        self.assertEqual(s['production_instance'],c.PRODUCTION);self.assertFalse(s['production_rollout'])

    def test_no_paid_capacity_before_expiry_and_exact_source_program_are_archived(self):
        result=c.create(self.api,self.state);self.assertTrue(self.requested());self.assertEqual(result['stage'],'capacity-requested-not-build-success')
        events=self.api.events;request=next(i for i,e in enumerate(events) if e[:2]==('autoscaling','set-desired-capacity'))
        self.assertTrue(any(e[:2]==('upload','control/creator-program.json') for e in events[:request]))
        self.assertTrue(any(e[:2]==('autoscaling','describe-scheduled-actions') for e in events[:request]))
        self.assertTrue(any(e[:2]==('upload','control/infra-ledger-current.json') and e[2]['stage']=='native-expiry-readback-and-scoped-artifact-access-installed' for e in events[:request]))

    def test_existing_scope_is_not_recreated(self):self.rejected('existing')
    def test_unknown_production_IAM_change_is_not_overwritten(self):self.rejected('baseline')
    def test_unavailable_image_is_not_replaced_with_another_image(self):self.rejected('image')
    def test_missing_native_expiry_cannot_request_capacity(self):self.rejected('expiry-missing')
    def test_later_native_expiry_cannot_extend_the_budget(self):self.rejected('expiry-later')
    def test_recurring_action_is_not_one_shot_expiry(self):self.rejected('expiry-recurring')
    def test_truthy_boolean_capacity_is_not_zero(self):self.rejected('expiry-bool')
    def test_protected_member_default_cannot_disable_expiry(self):self.rejected('protected')
    def test_ondemand_fallback_cannot_be_introduced(self):self.rejected('ondemand')

    def test_single_encrypted_disposable_root_and_no_user_data_or_EIP(self):
        c.create(self.api,self.state);call=next(e for e in self.api.events if e[:2]==('ec2','create-launch-template'));args=list(call[2]);data=json.loads(args[args.index('--launch-template-data')+1])
        self.assertEqual(data['ImageId'],c.AMI);self.assertEqual(data['MetadataOptions']['HttpTokens'],'required');self.assertNotIn('UserData',data)
        self.assertNotIn('KeyName',data);self.assertEqual(len(data['BlockDeviceMappings']),1)
        self.assertEqual(data['BlockDeviceMappings'][0]['Ebs'],{'VolumeSize':32,'VolumeType':'gp3','Encrypted':True,'DeleteOnTermination':True})
        self.assertFalse(any(e[:2] in [('ec2','attach-volume'),('ec2','associate-address')] for e in self.api.events))

    def test_canary_can_read_back_only_its_own_artifacts_and_results(self):
        rows=[s for s in c.scoped_policy(self.state)['Statement'] if s['Effect']=='Allow' and s['Action']=='s3:GetObject']
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['Resource'],['arn:aws:s3:::'+self.state['bucket']+'/artifacts/*','arn:aws:s3:::'+self.state['bucket']+'/results/*'])

    def test_instance_role_explicitly_denies_storage_and_ASG_mutations(self):
        rows=[s for s in c.scoped_policy(self.state)['Statement'] if s['Effect']=='Deny'];self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['Resource'],'*')
        self.assertTrue({'ec2:AttachVolume','ec2:AssociateAddress','ec2:TerminateInstances','autoscaling:SetInstanceProtection','autoscaling:SetDesiredCapacity'}<=set(rows[0]['Action']))

    def test_primary_permission_has_only_scope_artifacts_and_expiration(self):
        policy=c.primary_policy(self.state)
        self.assertEqual({s['Action'] for s in policy['Statement']},{'s3:GetObject','s3:PutObject'})
        for statement in policy['Statement']:
            self.assertTrue(statement['Resource'].startswith('arn:aws:s3:::'+self.state['bucket']+'/'))
            self.assertEqual(statement['Condition']['DateLessThan']['aws:CurrentTime'],self.state['permission_expires'])


if __name__=='__main__':unittest.main()
