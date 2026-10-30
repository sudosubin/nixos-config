"""Pure resident observer tests, never AWS or production units."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

s=importlib.util.spec_from_file_location('observer_tested',Path(__file__).parent.parent/'modules/linux/spot_observer.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
IID='i-'+'a'*17
ARN='arn:aws:autoscaling:ap-northeast-2:537112465379:autoScalingGroup:12345678-1234-1234-1234-123456789abc:autoScalingGroupName/nixos-ec2-asg'


def config():return {'schema':1,'account':'537112465379','region':'ap-northeast-2','asg':'nixos-ec2-asg','asg_arn':ARN,'deployment_id':'a'*12,'state_directory':'/var/lib/spot-protection-observer/'+'a'*12}

def runtime():return {'schema':1,'observed_at':1000,'boot_id':'current','guard_binary_exists':False,'units':{n:{'probe_ok':True,'properties':{'LoadState':'not-found','ActiveState':'inactive'}} for n in ['spot-schedule-guard.service','spot-schedule-guard.timer']},'files':{}}

def group():return {'AutoScalingGroupARN':ARN,'AutoScalingGroupName':'nixos-ec2-asg','DesiredCapacity':0,'NewInstancesProtectedFromScaleIn':True,'Instances':[{'InstanceId':IID,'ProtectedFromScaleIn':True,'LifecycleState':'InService'}]}


class API:
    def __init__(self):self.calls=[];self.doc={'accountId':'537112465379','region':'ap-northeast-2','instanceId':IID};self.groups=[group(),group()]
    def identity(self):return self.doc
    def __call__(self,service,operation,*args):
        self.calls.append((service,operation,args))
        if service=='sts':return {'Account':'537112465379','Arn':'arn:aws:sts::537112465379:assumed-role/instance-role/'+IID}
        if service=='autoscaling':return {'AutoScalingGroups':[self.groups.pop(0)]}
        if service=='ssm':return {'Sessions':[]}
        if service=='ec2':return {'Volumes':[{'Encrypted':False}]}
        raise AssertionError('unexpected API')


class ObserverTests(unittest.TestCase):
    def test_exact_settings(self):self.assertEqual(p.settings(config()),config())
    def test_no_arming_setting_accepted(self):
        c=config();c['armed']=True
        with self.assertRaises(RuntimeError):p.settings(c)
    def test_foreign_output_path_rejected(self):
        c=config();c['state_directory']='/run/spot-schedule-guard'
        with self.assertRaises(RuntimeError):p.settings(c)
    def test_name_only_ASG_rejected(self):
        c=config();c['asg_arn']='nixos-ec2-asg'
        with self.assertRaises(RuntimeError):p.settings(c)
    def test_API_deny_before_any_subprocess(self):
        api=p.Reads(config())
        for pair in [('autoscaling','set-instance-protection'),('ec2','terminate-instances'),('ssm','send-command'),('s3api','put-object')]:
            with patch.object(p.subprocess,'run') as run,self.assertRaises(RuntimeError):api(*pair)
            run.assert_not_called()
    def test_network_job_has_own128MiB_CPU10_exec_gate(self):
        with patch.object(p.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='{}')) as run:p.Reads(config())('sts','get-caller-identity')
        args=run.call_args.args[0]
        for value in ['MemoryMax=128M','MemorySwapMax=0','CPUQuota=10%','OOMPolicy=kill','ProtectControlGroups=yes']:self.assertIn(value,args)
        self.assertIn('os.execvp',p.GATE);self.assertIn("key.startswith(('AWS_','AMAZON_'))",p.GATE)
    def test_read_failure_never_becomes_success(self):
        with patch.object(p.subprocess,'run',return_value=SimpleNamespace(returncode=1,stdout='{}')),self.assertRaises(RuntimeError):p.Reads(config())('sts','get-caller-identity')
    def test_actual_observation_keeps_all_arming_flags_false(self):
        api=API()
        with patch.object(p.time,'time',return_value=1000):r=p.observe(config(),api,runtime())
        self.assertEqual(r['classification'],'protected_without_deployed_guard');self.assertFalse(r['termination_capable']);self.assertFalse(r['armed']);self.assertFalse(r['work_tracking_verified']);self.assertFalse(r['goal_complete']);self.assertIsNone(r['diagnosis']['runtime_busy_reason'])
    def test_no_home_does_not_guess_encryption_or_restoration(self):
        api=API()
        with patch.object(p.time,'time',return_value=1000):r=p.observe(config(),api,runtime())
        self.assertIsNone(r['home_volume_observation'])
    def test_optional_home_metadata_is_read_only(self):
        api=API();r=runtime();r['files']['/etc/spot-schedule-guard.json']={'exists':True,'fields':{'home_volume':'vol-'+'b'*17}}
        with patch.object(p.time,'time',return_value=1000):value=p.observe(config(),api,r)
        self.assertFalse(value['home_volume_observation'][0]['Encrypted']);self.assertTrue(all((s,o) in p.ALLOWED for s,o,a in api.calls))
    def test_foreign_IMDS_account_refuses_before_AWS(self):
        api=API();api.doc['accountId']='0'*12
        with self.assertRaises(RuntimeError):p.observe(config(),api,runtime())
        self.assertEqual(api.calls,[])
    def test_foreign_role_session_refuses(self):
        class Wrong(API):
            def __call__(self,*args):return {'Account':'537112465379','Arn':'arn:wrong'}
        with self.assertRaises(RuntimeError):p.observe(config(),Wrong(),runtime())
    def test_group_name_reuse_refused(self):
        api=API();api.groups[0]['AutoScalingGroupARN']='arn:recreated'
        with self.assertRaises(RuntimeError):p.observe(config(),api,runtime())
    def test_missing_membership_refused(self):
        api=API();api.groups[0]['Instances']=[]
        with self.assertRaises(RuntimeError):p.observe(config(),api,runtime())
    def test_changed_group_during_read_is_unknown(self):
        api=API();api.groups[1]['DesiredCapacity']=1
        with patch.object(p.time,'time',return_value=1000):r=p.observe(config(),api,runtime())
        self.assertEqual(r['classification'],'observation_unknown');self.assertFalse(r['termination_capable'])
    def test_observer_is_not_full_guard_or_idle_authority(self):
        r=runtime();r['observer']={'trusted':True,'status':{'observed_at':999,'boot_id':'current','instance':IID,'termination_capable':False},'service':{'properties':{'LoadState':'loaded'}},'timer':{'properties':{'LoadState':'loaded','ActiveState':'active'}}}
        result=p.core.diagnose(group(),r,IID,now=1000);self.assertEqual(result['classification'],'protected_observer_only_guard_not_armed');self.assertFalse(result['guard_service_and_timer_and_binary_loaded']);self.assertFalse(result['auto_unprotect_recommended'])
    def test_stale_observer_not_reported_as_current(self):
        r=runtime();r['observer']={'trusted':True,'status':{'observed_at':0,'boot_id':'current','instance':IID,'termination_capable':False}}
        self.assertEqual(p.core.diagnose(group(),r,IID,now=1000)['classification'],'protected_without_deployed_guard')
    def test_observer_cannot_claim_to_terminate(self):
        r=runtime();r['observer']={'trusted':True,'status':{'observed_at':1000,'boot_id':'current','instance':IID,'termination_capable':True}}
        self.assertFalse(p.core.observer_current(r,IID,1000))
    def test_version_covers_both_shared_and_observer_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'spot_protection.py').write_text('a');(root/'spot_observer.py').write_text('b');old=p.version(root);(root/'spot_protection.py').write_text('c');self.assertNotEqual(old,p.version(root))
    def test_no_guard_or_work_protocol_execution(self):
        text=Path(p.__file__).read_text()
        for value in ['Protocol(','initialize(','--protect-only','--startup-only','set-instance-protection']:self.assertNotIn(value,text)
    def test_Nix_timer_and_resource_declarations(self):
        text=(Path(p.__file__).parent/'spot-protection-observer.nix').read_text()
        for value in ['MemoryMax = "256M"','MemorySwapMax = 0','CPUQuota = "25%"','OOMPolicy = "kill"','PrivateNetwork = true','Persistent = false','OnUnitInactiveSec = "5min"']:self.assertIn(value,text)


if __name__=='__main__':unittest.main()
