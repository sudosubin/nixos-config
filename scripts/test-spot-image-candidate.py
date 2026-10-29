"""Pure candidate metadata/containment gates; NEVER AWS or storage actions."""
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import Mock,patch

s=importlib.util.spec_from_file_location('image_candidate',Path(__file__).with_name('spot-image-candidate.py'));p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
NOW=datetime(2026,1,1,tzinfo=timezone.utc)


def state():return p.b.plan('123456abcdef','a'*40,NOW)


class CandidateTests(unittest.TestCase):
    def test_volume_timeout_is_native_compute_plus_ten_minutes(self):
        plan=p.root_plan(state(),NOW);self.assertEqual(plan['deadline'],'2026-01-01T02:00:00+00:00');self.assertEqual(plan['template']['Resources']['Deadline']['CreationPolicy']['ResourceSignal']['Timeout'],'PT7200S')
    def test_root_is_only_fresh32GiB_encrypted_no_snapshot_or_retained_volume(self):
        props=p.root_plan(state(),NOW)['template']['Resources']['ImageRoot']['Properties'];self.assertEqual(props['Size'],32);self.assertIs(props['Encrypted'],True);self.assertNotIn('SnapshotId',props);self.assertEqual(props['AvailabilityZone'],'ap-northeast-2d')
    def test_role_cannot_detach_snapshot_signal_or_modify_production(self):
        rows=p.root_plan(state(),NOW)['policy']['Statement'];denied={a for row in rows if row['Effect']=='Deny' for a in row['Action']};self.assertTrue({'ec2:DetachVolume','ec2:CreateSnapshot','cloudformation:SignalResource','ec2:TerminateInstances'}<=denied)
        self.assertEqual(rows[1]['Condition']['NumericEquals']['ec2:VolumeSize'],32);self.assertEqual(rows[3]['Condition']['StringEquals']['ec2:ResourceTag/Purpose'],'image-root')
        for volume in p.PROTECTED:self.assertIn(volume,json.dumps(rows[4]))
    def test_expired_or_unbounded_root_plan_never_authorizes_creation(self):
        for now in [datetime(2026,1,1,1,55,tzinfo=timezone.utc),datetime(2025,12,31,23,tzinfo=timezone.utc)]:
            with self.assertRaises(RuntimeError):p.root_plan(state(),now)
    def test_missing_complete_retained_receipt_never_creates_paid_volume(self):
        api=Mock()
        with patch.object(p.c,'read',return_value={'scope':'123456abcdef','full_regression_executed':0}),self.assertRaises(RuntimeError):p.create_root(api,state(),'b'*32)
        api.assert_not_called()
    def test_untrusted_run_refuses_before_receipt_or_cloud_mutation(self):
        api=Mock()
        with patch.object(p.c,'read') as read,self.assertRaises(RuntimeError):p.create_root(api,state(),'../escape')
        api.assert_not_called();read.assert_not_called()
    def test_lost_control_PUT_is_not_replayed(self):
        api=Mock(side_effect=RuntimeError('lost PUT'))
        with self.assertRaises(RuntimeError):p.immutable(api,state(),'control/exact',{'goal_complete':False})
        self.assertEqual(api.call_count,1);self.assertIn('--if-none-match',api.call_args.args)
    def test_unknown_cold_capture_never_registers_AMI(self):
        api=Mock()
        with patch.object(p.c,'read',side_effect=RuntimeError('missing capture')),self.assertRaises(RuntimeError):p.register_image(api,state(),'snap-'+'b'*17,'/nix/store/system')
        api.assert_not_called()
    def test_register_requires_matching_actual_cold_target_and_all_hashes(self):
        api=Mock();created={'volume':'vol-'+'c'*17};capture={'snapshot':'snap-'+'b'*17,'volume':created['volume'],'cold_verification':{'target_volume':created['volume'],'system':'wrong-system','all_NAR_hashes_match':False}}
        with patch.object(p.c,'read',side_effect=[created,capture]),self.assertRaises(RuntimeError):p.register_image(api,state(),capture['snapshot'],'expected-system')
        api.assert_not_called()
    def test_candidate_writer_never_changes_default_ASG_or_releases_protection(self):
        text=Path(p.__file__).read_text()
        for action in ['update-auto-scaling-group','set-desired-capacity','modify-launch-template','set-instance-protection','--force-detach','--force-delete']:self.assertNotIn(action,text)
        self.assertIn("'--source-version','1'",text);self.assertIn("'numeric_candidate_version':2",text);self.assertIn('UNAPPROVED-source-',text)


if __name__=='__main__':unittest.main()
