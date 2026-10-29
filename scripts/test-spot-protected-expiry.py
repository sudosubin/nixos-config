"""Pure native-expiry investigation tests. No AWS/EC2/CFN/systemd calls."""
from datetime import datetime, timezone
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('expiry', Path(__file__).with_name('spot-protected-expiry.py'))
p = importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
NOW = datetime(2026, 10, 29, tzinfo=timezone.utc)


def state(mode='empty'):
    return p.plan('fa0123456789', mode, 'ami-'+'a'*17, 'b'*40, NOW)


def evidence():
    s = state()
    return {'state': s, 'StackId': 'arn:aws:cloudformation:'+p.REGION+':'+p.ACCOUNT+':stack/'+s['name']+'/uuid',
            'stack_status': 'ROLLBACK_COMPLETE', 'group_absent': True,
            'event': p.event_projection({'eventID': '11111111-2222-3333-4444-555555555555',
             'eventTime': '2026-10-29T00:02:00Z', 'eventSource': 'autoscaling.amazonaws.com',
             'eventName': 'DeleteAutoScalingGroup', 'awsRegion': p.REGION, 'recipientAccountId': p.ACCOUNT,
             'requestParameters': {'autoScalingGroupName': s['name'], 'forceDelete': True},
             'userAgent': 'cloudformation.amazonaws.com', 'userIdentity': {'invokedBy': 'cloudformation.amazonaws.com',
              'sessionContext': {'sessionIssuer': {'arn': 'arn:aws:iam::'+p.ACCOUNT+':role/'+s['role']}}}})}


class ExpiryTests(unittest.TestCase):
    def test_exact_scope_and_pinned_revision(self):
        for bad in ['nixos-ec2-asg', '../escape', 'A'*12, '']:
            with self.subTest(bad=bad),self.assertRaises(RuntimeError):p.plan(bad,'empty','ami-'+'a'*17,'b'*40,NOW)
        with self.assertRaises(RuntimeError):p.plan('fa0123456789','empty','ami-'+'a'*17,'latest',NOW)
    def test_empty_is_always_zero_paid_capacity(self):
        s=state();self.assertEqual(s['capacity_initial'],0);self.assertEqual(s['capacity_after_containment'],0);self.assertEqual(s['wait_seconds'],90)
    def test_protected_is_bounded_one_only_after_containment(self):
        s=state('protected');self.assertEqual(s['capacity_initial'],0);self.assertEqual(s['capacity_after_containment'],1);self.assertEqual(s['stack_timeout_minutes'],15)
        self.assertEqual((datetime.fromisoformat(s['off_at'])-NOW).total_seconds(),240)
    def test_naive_clock_and_unknown_mode_refused(self):
        with self.assertRaises(RuntimeError):p.plan('fa0123456789','empty','ami-'+'a'*17,'b'*40,NOW.replace(tzinfo=None))
        with self.assertRaises(RuntimeError):p.plan('fa0123456789','production','ami-'+'a'*17,'b'*40,NOW)
    def test_launch_has_no_guest_authority_public_ip_userdata_or_keys(self):
        d=p.launch_data(state());self.assertFalse({'IamInstanceProfile','UserData','KeyName'}&d.keys());self.assertFalse(d['NetworkInterfaces'][0]['AssociatePublicIpAddress']);self.assertEqual(d['CreditSpecification'],{'CpuCredits':'standard'});self.assertEqual(d['MetadataOptions']['HttpTokens'],'required')
    def test_single_encrypted_disposable_root(self):
        d=p.launch_data(state());self.assertEqual(len(d['BlockDeviceMappings']),1);e=d['BlockDeviceMappings'][0]['Ebs'];self.assertEqual(e['VolumeSize'],8);self.assertTrue(e['Encrypted']);self.assertTrue(e['DeleteOnTermination'])
    def test_role_mutations_are_exact_group_and_never_production(self):
        s=state();policy=p.role_policy(s);self.assertTrue(policy['Statement'][0]['Resource'].endswith('/'+s['name']));self.assertNotIn(p.PRODUCTION,policy['Statement'][0]['Resource'])
        self.assertEqual(policy['Statement'][0]['Effect'],'Allow');self.assertIn('autoscaling:DeleteAutoScalingGroup',policy['Statement'][0]['Action']);self.assertEqual(policy['Statement'][1]['Condition']['StringEquals']['aws:RequestedRegion'],p.REGION)
    def test_explicit_storage_eip_and_signal_denials(self):
        deny=p.role_policy(state())['Statement'][2];self.assertEqual(deny['Effect'],'Deny');self.assertIn('ec2:AttachVolume',deny['Action']);self.assertIn('ec2:TerminateInstances',deny['Action']);self.assertIn('cloudformation:SignalResource',deny['Action'])
    def test_template_has_only_native_resources_and_fixed_numeric_LT(self):
        d=p.template(state(),'lt-'+'a'*17,'public-code');self.assertEqual({r['Type'] for r in d['Resources'].values()},{'AWS::AutoScaling::AutoScalingGroup','AWS::AutoScaling::ScheduledAction','AWS::CloudFormation::WaitCondition'})
        g=d['Resources']['Group']['Properties'];self.assertTrue(g['NewInstancesProtectedFromScaleIn']);self.assertFalse(g['CapacityRebalance']);self.assertEqual(g['DesiredCapacity'],'0');self.assertEqual(g['DeletionProtection'],'none');self.assertEqual(g['MixedInstancesPolicy']['LaunchTemplate']['LaunchTemplateSpecification']['Version'],'1');self.assertEqual(g['MixedInstancesPolicy']['InstancesDistribution']['OnDemandPercentageAboveBaseCapacity'],0)
    def test_wait_has_no_handle_properties_or_signal_path(self):
        d=p.template(state(),'lt-'+'a'*17,'public-code');w=d['Resources']['Deadline'];self.assertNotIn('Properties',w);self.assertEqual(w['CreationPolicy']['ResourceSignal'],{'Count':1,'Timeout':'PT90S'});self.assertEqual(w['DependsOn'],['Group','Off']);self.assertNotIn('WaitConditionHandle',json.dumps(d))
    def test_creator_program_and_policy_are_in_cloud_template(self):
        d=p.template(state(),'lt-'+'a'*17,'public-code');self.assertEqual(d['Metadata']['CreatorProgram'],'public-code');self.assertEqual(d['Metadata']['RolePolicySHA256'],p.digest(p.role_policy(state())))
    def test_transport_denied_is_not_resource_absence(self):
        for code in ['AccessDenied','UnknownTransportOrCLIError']:
            with self.subTest(code=code),self.assertRaises(RuntimeError):p.absent(Mock(side_effect=p.APIError('iam','get-role',code)),'iam','get-role',[],'NoSuchEntity')
        p.absent(Mock(side_effect=p.APIError('iam','get-role','NoSuchEntity')),'iam','get-role',[],'NoSuchEntity')
    def test_protected_cannot_create_role_or_LT_without_first_native_evidence(self):
        api=Mock();api.side_effect=[{'Account':p.ACCOUNT},{'AutoScalingGroups':[]},p.APIError('iam','get-role','NoSuchEntity'),p.APIError('ec2','describe-launch-templates','InvalidLaunchTemplateName.NotFoundException'),{'StackSummaries':[]}]
        with self.assertRaisesRegex(RuntimeError,'first prove'):p.create(api,state('protected'))
        self.assertFalse(any(c.args[1] in ['create-role','create-launch-template','create-stack','set-desired-capacity'] for c in api.call_args_list))
    def contained(self, change=None):
        s=state('protected');lt='lt-'+'a'*17;doc=p.template(s,lt,'public-code');policy=p.role_policy(s);stack_id='exact-stack-id'
        group={'DesiredCapacity':0,'Instances':[],'MinSize':0,'MaxSize':1,'NewInstancesProtectedFromScaleIn':True,'CapacityRebalance':False,'DeletionProtection':'none','MixedInstancesPolicy':doc['Resources']['Group']['Properties']['MixedInstancesPolicy']}
        replies={('cloudformation','describe-stacks'):{'Stacks':[{'StackId':stack_id,'StackStatus':'CREATE_IN_PROGRESS','DisableRollback':False,'TimeoutInMinutes':15,'RoleARN':'arn:aws:iam::'+p.ACCOUNT+':role/'+s['role'],'CreationTime':NOW.isoformat()}]},('cloudformation','list-stack-resources'):{'StackResourceSummaries':[{'LogicalResourceId':n,'ResourceStatus':'CREATE_IN_PROGRESS' if n=='Deadline' else 'CREATE_COMPLETE'} for n in ['Group','Off','Deadline']]},('autoscaling','describe-auto-scaling-groups'):{'AutoScalingGroups':[group]},('cloudformation','get-template'):{'TemplateBody':doc},('autoscaling','describe-scheduled-actions'):{'ScheduledUpdateGroupActions':[{'StartTime':s['off_at'],'MinSize':0,'MaxSize':0,'DesiredCapacity':0}]},('ec2','describe-launch-template-versions'):{'LaunchTemplateVersions':[{'VersionNumber':1,'LaunchTemplateId':lt,'LaunchTemplateData':p.launch_data(s)}]},('iam','get-role-policy'):{'PolicyDocument':policy}}
        if change:change(replies)
        api=Mock(side_effect=lambda service,action,*args:replies[service,action])
        with patch.object(p.time,'time',return_value=NOW.timestamp()+30):return p.containment(api,s,stack_id,lt,policy,doc)
    def test_exact_native_deadline_and_empty_protected_spot_LT_required(self):self.contained()
    def test_no_capacity_after_rollback_disabled_or_deadline_not_running(self):
        for change in [lambda r:r['cloudformation','describe-stacks']['Stacks'][0].update(DisableRollback=True),lambda r:r['cloudformation','list-stack-resources']['StackResourceSummaries'][2].update(ResourceStatus='CREATE_COMPLETE')]:
            with self.assertRaises(RuntimeError):self.contained(change)
    def test_unexpected_guest_authority_public_IP_or_root_never_passes(self):
        for change in [lambda d:d.update(UserData='payload'),lambda d:d['NetworkInterfaces'][0].update(AssociatePublicIpAddress=True),lambda d:d['BlockDeviceMappings'][0]['Ebs'].update(DeleteOnTermination=False)]:
            with self.assertRaises(RuntimeError):self.contained(lambda r:change(r['ec2','describe-launch-template-versions']['LaunchTemplateVersions'][0]['LaunchTemplateData']))
    def test_deleted_group_or_on_demand_cannot_pass_native_readback(self):
        for change in [lambda r:r['autoscaling','describe-auto-scaling-groups'].update(AutoScalingGroups=[]),lambda r:r['autoscaling','describe-auto-scaling-groups']['AutoScalingGroups'][0]['MixedInstancesPolicy']['InstancesDistribution'].update(OnDemandPercentageAboveBaseCapacity=1)]:
            with self.assertRaises(RuntimeError):self.contained(change)
    def test_role_policy_change_never_passes_capacity_gate(self):
        with self.assertRaises(RuntimeError):self.contained(lambda r:r['iam','get-role-policy'].update(PolicyDocument={}))
    def test_only_exact_definite_role_rejection_retries_same_frozen_stack_request(self):
        s=state();error=p.APIError('cloudformation','create-stack','ValidationError','Role arn:aws:iam::'+p.ACCOUNT+':role/'+s['role']+' is invalid or cannot be assumed');api=Mock(side_effect=[error,{'StackId':'native'}])
        with patch.object(p.time,'sleep'):self.assertEqual(p.create_native_stack(api,['same-template','same-token'],s['role']),{'StackId':'native'})
        self.assertEqual(api.call_args_list[0],api.call_args_list[1])
    def test_unknown_create_reply_or_other_role_error_never_replays(self):
        for code,detail in [('UnknownTransportOrCLIError',''),('ValidationError','foreign role invalid'),('AccessDenied','')]:
            api=Mock(side_effect=p.APIError('cloudformation','create-stack',code,detail))
            with self.subTest(code=code),self.assertRaises(RuntimeError):p.create_native_stack(api,[],state()['role'])
            self.assertEqual(api.call_count,1)
    def test_exact_completed_native_force_event_required(self):p.validate_force_evidence(evidence())
    def test_ack_nonforce_wrong_actor_error_or_foreign_account_cannot_authorize_capacity(self):
        for key,bad in [('forceDelete',False),('forceDelete',1),('autoScalingGroupName',p.PRODUCTION)]:
            v=evidence();v['event']['requestParameters'][key]=bad
            with self.subTest(key=key,bad=bad),self.assertRaises(RuntimeError):p.validate_force_evidence(v)
        for key,bad in [('errorCode','AccessDenied'),('recipientAccountId','0'*12),('eventName','UpdateAutoScalingGroup'),('eventID','unknown')]:
            v=evidence();v['event'][key]=bad
            with self.subTest(key=key),self.assertRaises(RuntimeError):p.validate_force_evidence(v)
        for key,bad in [('stack_status','ROLLBACK_IN_PROGRESS'),('group_absent',False)]:
            v=evidence();v[key]=bad
            with self.subTest(key=key),self.assertRaises(RuntimeError):p.validate_force_evidence(v)
    def test_access_identifiers_IP_and_other_event_data_not_persisted(self):
        event={**evidence()['event'],'sourceIPAddress':'sensitive','userIdentity':{'accessKeyId':'sensitive','sessionContext':{'sessionIssuer':{'arn':'expected'}}},'responseElements':{'private':'value'}}
        result=p.event_projection(event);self.assertNotIn('sensitive',json.dumps(result));self.assertNotIn('responseElements',result)
    def test_file_receipt_must_be_independently_reread_from_CFN_and_CloudTrail(self):
        v=evidence();api=Mock(side_effect=[{'Stacks':[{'StackStatus':'ROLLBACK_COMPLETE','StackName':v['state']['name'],'StackId':v['StackId']}]},{'TemplateBody':{'Metadata':{'Investigation':v['state']}}},{'AutoScalingGroups':[]},{'Events':[{'CloudTrailEvent':json.dumps(v['event'])}]}]);p.verify_force_evidence(api,v)
        self.assertEqual(api.call_count,4);self.assertEqual(api.call_args.args[0:2],('cloudtrail','lookup-events'))
    def test_missing_or_partial_fresh_event_never_passes_manifest(self):
        for reply in [{'Events':[]},{'Events':[{'CloudTrailEvent':json.dumps(evidence()['event'])}],'NextToken':'incomplete'}]:
            v=evidence();api=Mock(side_effect=[{'Stacks':[{'StackStatus':'ROLLBACK_COMPLETE','StackName':v['state']['name'],'StackId':v['StackId']}]},{'TemplateBody':{'Metadata':{'Investigation':v['state']}}},{'AutoScalingGroups':[]},reply])
            with self.subTest(reply=reply),self.assertRaises(RuntimeError):p.verify_force_evidence(api,v)


if __name__ == '__main__':unittest.main()
