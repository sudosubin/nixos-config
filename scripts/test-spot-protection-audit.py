"""Pure diagnosis cases. No AWS, SSM, systemd, guard invocation or approvals."""
import base64
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import Mock,patch

s=importlib.util.spec_from_file_location('audit',Path(__file__).with_name('spot-protection-audit.py'));p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
IID='i-'+'a'*17


def group():return {'AutoScalingGroupARN':'arn:exact','AutoScalingGroupName':'nixos-ec2-asg','DesiredCapacity':0,'NewInstancesProtectedFromScaleIn':True,'Instances':[{'InstanceId':IID,'ProtectedFromScaleIn':True,'LifecycleState':'InService'}]}

def runtime():
    return {'schema':1,'observed_at':1000,'boot_id':'current','guard_binary_exists':False,'units':{n:{'probe_ok':True,'properties':{'LoadState':'not-found','ActiveState':'inactive','MainPID':'0'}} for n in ['spot-schedule-guard.service','spot-schedule-guard.timer']},'files':{'/etc/spot-schedule-guard.json':{'exists':True,'fields':{'armed':False,'asg':'nixos-ec2-asg'}},'/home/persist/manifests/profile-cache.json':{'exists':True,'fields':{'schema':1}}},'named_process_observations_NOT_busy_or_idle_proof':[{'pid':42,'comm':'kiro-cli-chat'}]}


def loaded(r):
    r['guard_binary_exists']=True
    for value in r['units'].values():value['properties']['LoadState']='loaded'
    r['units']['spot-schedule-guard.timer']['properties']['ActiveState']='active'
    return r


class AuditTests(unittest.TestCase):
    def diagnose(self,r=None,g=None,**kwargs):return p.diagnose(g or group(),r or runtime(),IID,now=1000,**kwargs)
    def test_exact_missing_controller_is_not_busy_work_decision(self):
        result=self.diagnose();self.assertEqual(result['classification'],'protected_without_deployed_guard');self.assertIsNone(result['runtime_busy_reason']);self.assertFalse(result['auto_unprotect_recommended'])
    def test_empty_process_list_never_turns_missing_controller_into_idle(self):
        r=runtime();r['named_process_observations_NOT_busy_or_idle_proof']=[];self.assertEqual(self.diagnose(r)['classification'],'protected_without_deployed_guard');self.assertFalse(self.diagnose(r)['auto_unprotect_recommended'])
    def test_passive_armed_false_config_is_not_a_running_observer(self):
        self.assertEqual(self.diagnose()['configured_armed'],False);self.assertNotEqual(self.diagnose()['classification'],'protected_observation_mode')
    def test_loaded_oneshot_inactive_is_normal_with_active_timer(self):
        r=loaded(runtime());self.assertEqual(self.diagnose(r)['classification'],'protected_observation_mode')
    def test_timer_inactive_distinguished_from_observation_mode(self):
        r=loaded(runtime());r['units']['spot-schedule-guard.timer']['properties']['ActiveState']='inactive';self.assertEqual(self.diagnose(r)['classification'],'protected_guard_timer_inactive')
    def test_binary_missing_still_means_deployment_incomplete(self):
        r=loaded(runtime());r['guard_binary_exists']=False;self.assertEqual(self.diagnose(r)['classification'],'protected_without_deployed_guard')
    def test_unknown_systemctl_probe_never_claims_service_absent(self):
        r=runtime();r['units']['spot-schedule-guard.service']['probe_ok']=False;result=self.diagnose(r);self.assertEqual(result['classification'],'observation_unknown');self.assertIsNone(result['guard_service_and_timer_and_binary_loaded'])
    def test_stale_or_future_metadata_is_unknown(self):
        for observed in [0,1001,None,True]:
            r=runtime();r['observed_at']=observed;self.assertEqual(self.diagnose(r)['classification'],'observation_unknown')
    def test_membership_or_typed_flag_unknown(self):
        for members in [[],[{'InstanceId':IID,'ProtectedFromScaleIn':'true'}]]:
            g=group();g['Instances']=members;self.assertEqual(self.diagnose(g=g)['classification'],'membership_or_protection_unknown')
    def test_false_protection_not_conflated_with_protected_state(self):
        g=group();g['Instances'][0]['ProtectedFromScaleIn']=False;self.assertEqual(self.diagnose(g=g)['classification'],'not_scale_in_protected')
    def test_ASG_change_during_collection_refuses_definitive_diagnosis(self):
        after=group();after['AutoScalingGroupARN']='arn:recreated';self.assertEqual(self.diagnose(after=after)['classification'],'observation_unknown')
    def test_arming_marker_alone_does_not_prove_current_busy_or_idle(self):
        r=loaded(runtime());r['files']['/etc/spot-schedule-guard.json']['fields']['armed']=True;result=self.diagnose(r);self.assertEqual(result['classification'],'protected_guard_reasons_require_current_custody');self.assertIsNone(result['runtime_busy_reason']);self.assertFalse(result['auto_unprotect_recommended'])
    def test_missing_approval_and_schema1_remain_explicit_gaps(self):
        gaps=self.diagnose()['deployment_and_safety_gaps'];self.assertIn('arming_prerequisite_unverified:work_tracking_verified',gaps);self.assertIn('arming_epoch_not_current',gaps);self.assertIn('production_profile_cache_not_schema2',gaps)
    def test_decoder_checks_entire_compressed_body(self):
        raw=json.dumps(runtime()).encode();envelope={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'gzip':base64.b64encode(gzip.compress(raw)).decode()};self.assertEqual(p.decode(json.dumps(envelope)),runtime());envelope['sha256']='0'*64
        with self.assertRaises(RuntimeError):p.decode(json.dumps(envelope))
    def test_compressed_body_is_bounded_before_parsing(self):
        raw=b'x'*2097152;envelope={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'gzip':base64.b64encode(gzip.compress(raw)).decode()}
        with self.assertRaises(RuntimeError):p.decode(json.dumps(envelope))
    def test_unknown_schema_refused(self):
        raw=json.dumps({'schema':2}).encode();envelope={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'gzip':base64.b64encode(gzip.compress(raw)).decode()}
        with self.assertRaisesRegex(RuntimeError,'schema'):p.decode(json.dumps(envelope))
    def test_truncated_SSM_is_explicit_failure_not_partial_success(self):
        with self.assertRaisesRegex(RuntimeError,'truncated'):p.decode('{--output truncated--')
    def test_runtime_reader_has_no_guard_or_service_mutation(self):
        for bad in ['daemon-reload','restart','set-instance-protection','initialize(','--protect-only','--startup-only']:
            self.assertNotIn(bad,p.COLLECTOR)
    def test_unknown_sendcommand_reply_not_retried(self):
        api=Mock();api.side_effect=[{'AutoScalingGroups':[group()]},RuntimeError('lost SendCommand reply')]
        with self.assertRaisesRegex(RuntimeError,'lost SendCommand'):p.audit(api,'nixos-ec2-asg',IID)
        self.assertEqual(api.call_count,2);self.assertEqual(api.call_args.args[:2],('ssm','send-command'))


if __name__=='__main__':unittest.main()
