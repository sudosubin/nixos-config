"""Pure image-root custody tests; no AWS/devices/mounts/Nix/systemd executed."""
import copy
from datetime import datetime,timezone
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('image',Path(__file__).with_name('spot_image.py'));p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
NOW=datetime(2026,1,1,tzinfo=timezone.utc).timestamp();SCOPE='123456abcdef';EXPIRES='2026-01-01T01:50:00+00:00';IID='i-'+'c'*17;ROOT='vol-'+'a'*17;TARGET='vol-'+'b'*17


def evidence():
    doc={'instanceId':IID,'accountId':p.ACCOUNT,'region':p.REGION,'imageId':'ami-0d44956a8229b0dad'}
    tags={'ScopeId':SCOPE,'Disposable':'true','DisposableUntil':EXPIRES,'ManagedBy':'nixos-spot-validation','Purpose':'artifact-test','aws:autoscaling:groupName':'nixos-spot-proof-'+SCOPE}
    instance={'InstanceId':IID,'InstanceLifecycle':'spot','ImageId':doc['imageId'],'InstanceType':'r7g.large','IamInstanceProfile':{'Arn':'arn:aws:iam::'+p.ACCOUNT+':instance-profile/nixos-spot-proof-'+SCOPE},'State':{'Name':'running'},'Tags':[{'Key':k,'Value':v} for k,v in tags.items()],
              'BlockDeviceMappings':[{'DeviceName':'/dev/xvda','Ebs':{'VolumeId':ROOT,'DeleteOnTermination':True}},{'DeviceName':'/dev/sdf','Ebs':{'VolumeId':TARGET,'DeleteOnTermination':False}}]}
    caller={'Account':p.ACCOUNT,'Arn':'arn:aws:sts::'+p.ACCOUNT+':assumed-role/nixos-spot-proof-'+SCOPE+'/'+IID};member={'InstanceId':IID,'AutoScalingGroupName':'nixos-spot-proof-'+SCOPE,'ProtectedFromScaleIn':False,'LifecycleState':'InService'}
    actions=[{'AutoScalingGroupName':member['AutoScalingGroupName'],'ScheduledActionName':member['AutoScalingGroupName']+'-off','StartTime':EXPIRES,'MinSize':0,'MaxSize':0,'DesiredCapacity':0}]
    volumes=[{'VolumeId':v,'Encrypted':True,'Size':32,'SnapshotId':'snap-base' if v==ROOT else '', 'Tags':[{'Key':'ScopeId','Value':SCOPE},{'Key':'ManagedBy','Value':'nixos-spot-validation'},{'Key':'Purpose','Value':'image-root'}], 'Attachments':[{'InstanceId':IID,'State':'attached','DeleteOnTermination':v==ROOT}]} for v in [ROOT,TARGET]]
    return [doc,instance,caller,member,actions,volumes,TARGET,SCOPE,EXPIRES]


class ImageTests(unittest.TestCase):
    def validate(self,change=None):
        args=evidence()
        if change:change(args)
        with tempfile.TemporaryDirectory() as d:
            boot=Path(d)/'boot';boot.write_text('private-fixture-boot')
            def path(name):return boot if name=='/proc/sys/kernel/random/boot_id' else Path(name)
            with patch.object(p,'Path',side_effect=path):return p.validate(*args,now=NOW)

    def test_fresh_exact_two_disk_unprotected_spot_data_contract(self):
        r=self.validate();self.assertEqual(r['target_volume'],TARGET);self.assertTrue(r['not_production_or_idle_authority'])
    def test_original_or_foreign_account_never_authorizes_image_disk(self):
        for values in [{'instanceId':p.ORIGINAL},{'accountId':'000000000000'},{'imageId':'ami-other'}]:
            with self.assertRaises(RuntimeError):self.validate(lambda a:a[0].update(values))
    def test_retained_target_never_passes_even_with_green_tags(self):
        for volume in p.PROTECTED:
            with self.assertRaises(RuntimeError):self.validate(lambda a:a.__setitem__(6,volume))
    def test_wrong_role_or_protected_member_refuses(self):
        with self.assertRaises(RuntimeError):self.validate(lambda a:a[2].update(Arn='operator'))
        with self.assertRaises(RuntimeError):self.validate(lambda a:a[3].update(ProtectedFromScaleIn=True))
    def test_extra_or_duplicate_attached_storage_refuses(self):
        with self.assertRaises(RuntimeError):self.validate(lambda a:a[1]['BlockDeviceMappings'].append({'Ebs':{'VolumeId':'foreign'}}))
        with self.assertRaises(RuntimeError):self.validate(lambda a:a[5].__setitem__(1,copy.deepcopy(a[5][0])))
    def test_source_root_delete_on_termination_is_required(self):
        with self.assertRaises(RuntimeError):self.validate(lambda a:a[1]['BlockDeviceMappings'][0]['Ebs'].update(DeleteOnTermination=False))
    def test_target_snapshot_or_wrong_tag_is_not_virgin(self):
        with self.assertRaises(RuntimeError):self.validate(lambda a:a[5][1].update(SnapshotId='snap-production'))
        with self.assertRaises(RuntimeError):self.validate(lambda a:a[5][1]['Tags'][2].update(Value='production-home'))
    def test_target_encryption_size_and_attachment_are_exact(self):
        for values in [{'Encrypted':False},{'Size':80},{'Attachments':[{'InstanceId':p.ORIGINAL,'State':'attached','DeleteOnTermination':False}]}]:
            with self.assertRaises(RuntimeError):self.validate(lambda a:a[5][1].update(values))
    def test_target_not_delete_on_termination_is_required(self):
        with self.assertRaises(RuntimeError):self.validate(lambda a:a[5][1]['Attachments'][0].update(DeleteOnTermination=True))
    def test_native_off_cannot_be_recurring_shifted_or_boolean(self):
        for changes in [{'Recurrence':'* * * * *'},{'StartTime':'2026-01-02T00:00:00+00:00'},{'DesiredCapacity':False}]:
            with self.assertRaises(RuntimeError):self.validate(lambda a:a[4][0].update(changes))
    def test_late_expired_image_build_window_refuses(self):
        args=evidence()
        with self.assertRaises(RuntimeError):p.validate(*args,now=NOW+6500)
    def test_installer_declares_private2GiB_local_store_not_canary_or_live_host(self):
        source=Path(p.__file__).read_text();self.assertIn("budget['purpose']=='build'",source);self.assertIn('private image mount namespace required',source);self.assertIn('private image network/NNP required',source);self.assertIn('local?trusted=1',source)
        for bad in ['--force-detach','umount -l','umount -f','systemctl daemon-reload','create-snapshot','register-image']:self.assertNotIn(bad,source)


if __name__=='__main__':unittest.main()
