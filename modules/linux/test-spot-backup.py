"""Offline backup lifecycle/retention tests; no AWS, services or user data."""
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import Mock

spec=importlib.util.spec_from_file_location('backup',Path(__file__).with_name('spot_backup.py'))
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
p=importlib.util.spec_from_file_location('iam',Path(__file__).with_name('spot-backup-iam.py'))
iam=importlib.util.module_from_spec(p);p.loader.exec_module(iam)


class Memory:
    def __init__(self):self.value=None;self.history=[]
    def read(self):return copy.deepcopy(self.value)
    def write(self,value):self.value=copy.deepcopy(value);self.history.append(copy.deepcopy(value))


class Cloud:
    def __init__(self,owner):self.owner=owner;self.rows={};self.counter=0;self.deleted=[];self.calls=[];self.refs=set();self.pending=0;self.timeout=False;self.reject=False
    def add(self,minutes=0,**changes):
        self.counter+=1;ident='snap-'+f'{self.counter:017x}'
        row={'SnapshotId':ident,'OwnerId':self.owner.account,'VolumeId':self.owner.volume,'Encrypted':True,
             'State':'completed','StartTime':(self.owner.now()-timedelta(minutes=minutes)).isoformat(),
             'Tags':[{'Key':k,'Value':v} for k,v in self.owner.base_tags('backup-'+f'{self.counter:032x}').items()]}
        row['Tags']=[{'Key':x['Key'],'Value':{'ColdCapture':'verified','BackupStatus':'successful'}.get(x['Key'],x['Value'])} for x in row['Tags']]
        row.update(changes);self.rows[ident]=row;return ident
    def set(self,ident,**changes):
        d=b.tags(self.rows[ident]);d.update(changes);self.rows[ident]['Tags']=[{'Key':k,'Value':v} for k,v in d.items()]
    def __call__(self,service,action,*args):
        self.calls.append((action,args));args=list(args)
        def value(name):return args[args.index(name)+1]
        if action=='describe-volumes':return {'Volumes':[{'VolumeId':self.owner.volume,'Encrypted':True}]}
        if action=='create-snapshot':
            if self.reject:raise b.AWSFailure(service,action,self.reject if isinstance(self.reject,str) else 'UnauthorizedOperation')
            ident=self.add();self.rows[ident]['Tags']=json.loads(value('--tag-specifications'))[0]['Tags']
            if self.pending:self.rows[ident]['State']='pending'
            if self.timeout:raise TimeoutError('lost create response')
            return {'SnapshotId':ident,'Encrypted':True,'State':'pending'}
        if action=='describe-snapshots':
            if '--snapshot-ids' in args:
                ident=value('--snapshot-ids');row=self.rows[ident]
                if row['State']=='pending' and self.pending:
                    self.pending-=1
                    if not self.pending:row['State']='completed'
                return {'Snapshots':[copy.deepcopy(row)]}
            expected={x['Name'][4:]:x['Values'][0] for x in json.loads(value('--filters'))}
            return {'Snapshots':[copy.deepcopy(row) for row in self.rows.values() if all(b.tags(row).get(k)==v for k,v in expected.items())]}
        if action=='create-tags':self.set(value('--resources'),**{x['Key']:x['Value'] for x in json.loads(value('--tags'))});return {}
        if action=='describe-images':
            requested=set(json.loads(value('--filters'))[0]['Values'])
            return {'Images':[{'BlockDeviceMappings':[{'Ebs':{'SnapshotId':ident}}]} for ident in self.refs&requested]}
        if action=='delete-snapshot':
            ident=value('--snapshot-id');self.deleted.append(ident);del self.rows[ident];return {}
        raise AssertionError(action)


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.cfg={'account':'123456789012','home_volume':'vol-0123456789abcdef0','backup':{'set':'test-home','keep':3}}
        self.date=datetime(2026,10,27,4,tzinfo=timezone.utc);self.j=Memory();self.check=Mock();self.cold=Mock();self.sleeps=[]
        self.backup=b.Backup(self.cfg,None,self.cold,self.check,self.j,sleep=lambda seconds:self.sleeps.append(seconds),now=lambda:self.date)
        self.cloud=Cloud(self.backup);self.backup.call=self.cloud

    def test_create_response_pending_never_counts_as_success(self):
        self.cloud.pending=4;row=self.backup.capture()
        self.assertEqual(row['State'],'completed');self.assertTrue(self.sleeps)
        self.assertEqual(self.j.value['phase'],'successful')
        self.assertEqual(b.tags(row)['ColdCapture'],'verified')

    def test_create_attempt_journal_precedes_aws_mutation(self):
        self.backup.capture();self.assertEqual(self.j.history[0]['phase'],'creating');self.assertIsNone(self.j.history[0]['snapshot_id'])

    def test_four_successes_retain_exactly_latest_three(self):
        ids=[]
        for i in range(4):
            ids.append(self.backup.capture()['SnapshotId']);self.date+=timedelta(seconds=1)
        self.assertEqual(set(self.cloud.rows),set(ids[1:]));self.assertEqual(self.cloud.deleted,[ids[0]])

    def test_protected_and_foreign_set_never_pruned(self):
        protected=self.cloud.add(minutes=100);self.cloud.set(protected,Protected='true')
        foreign=self.cloud.add(minutes=99);self.cloud.set(foreign,BackupSet='another-set')
        for i in range(5):self.cloud.add(minutes=10+i)
        self.backup.capture();self.assertIn(protected,self.cloud.rows);self.assertIn(foreign,self.cloud.rows)

    def test_AMI_references_exempt_even_deprecated_or_disabled(self):
        ami=self.cloud.add(minutes=100);self.cloud.refs.add(ami)
        for i in range(4):self.cloud.add(minutes=10+i)
        self.backup.capture();self.assertIn(ami,self.cloud.rows)
        for action,args in self.cloud.calls:
            if action=='describe-images':self.assertIn('--include-deprecated',args);self.assertIn('--include-disabled',args)

    def test_cold_failure_before_create_does_not_request_snapshot(self):
        self.cold.side_effect=RuntimeError('mounted')
        with self.assertRaises(RuntimeError):self.backup.capture()
        self.assertFalse(any(a=='create-snapshot' for a,args in self.cloud.calls))

    def test_cold_failure_after_create_does_not_certify_or_prune(self):
        self.cold.side_effect=[None,RuntimeError('remounted')]
        with self.assertRaises(RuntimeError):self.backup.capture()
        self.assertEqual(self.cloud.deleted,[])
        self.assertEqual(b.tags(next(iter(self.cloud.rows.values())))['ColdCapture'],'unverified')

    def test_extension_or_new_start_cancels_while_pending(self):
        self.cloud.pending=20;self.check.side_effect=[None,RuntimeError('extension')]
        with self.assertRaises(RuntimeError):self.backup.capture()
        self.assertEqual(self.cloud.deleted,[]);self.assertEqual(self.j.value['phase'],'aborted')
        self.assertTrue(all(b.tags(row)['BackupStatus']=='pending' for row in self.cloud.rows.values()))

    def test_failed_or_unknown_snapshot_state_never_success(self):
        original=self.cloud.__call__
        def call(service,action,*args):
            value=original(service,action,*args)
            if action=='describe-snapshots' and '--snapshot-ids' in args:value['Snapshots'][0]['State']='error'
            return value
        self.backup.call=call
        with self.assertRaises(b.Unsafe):self.backup.capture()
        self.assertEqual(self.cloud.deleted,[]);self.assertNotEqual(self.j.value['phase'],'successful')

    def test_non_boolean_encryption_rejected(self):
        for encrypted in [False,'true',1,None]:
            with self.subTest(encrypted=encrypted):
                row={'SnapshotId':'snap-00000000000000000','Encrypted':encrypted,'VolumeId':self.backup.volume,'OwnerId':self.backup.account}
                with self.assertRaises(b.Unsafe):self.backup.identify(row)

    def test_lost_create_reply_adopts_exact_tagged_attempt_not_duplicate(self):
        self.cloud.timeout=True;row=self.backup.capture()
        self.assertEqual(len(self.cloud.rows),1);self.assertEqual(row['State'],'completed')
        self.assertEqual(sum(a=='create-snapshot' for a,args in self.cloud.calls),1)

    def test_unknown_create_blocks_next_non_idempotent_create(self):
        original=self.cloud.__call__
        def call(service,action,*args):
            if action=='create-snapshot':raise TimeoutError('unknown')
            return original(service,action,*args)
        self.backup.call=call
        with self.assertRaises(b.Unsafe):self.backup.capture()
        self.assertEqual(self.j.value['phase'],'uncertain')
        with self.assertRaises(b.Unsafe):self.backup.capture()

    def test_definite_permission_rejection_not_unknown_accepted_create(self):
        self.cloud.reject=True
        with self.assertRaises(b.AWSFailure):self.backup.capture()
        self.assertEqual(self.j.value['phase'],'rejected');self.assertEqual(len(self.cloud.rows),0)
        self.cloud.reject=False;self.backup.capture()

    def test_confirmed_throttle_rejected_not_indeterminate_or_retried(self):
        self.cloud.reject='SnapshotCreationPerVolumeRateExceeded'
        with self.assertRaises(b.AWSFailure):self.backup.capture()
        self.assertEqual(self.j.value['phase'],'rejected');self.assertEqual(len(self.cloud.rows),0)
        self.cloud.reject=False;self.backup.capture()

    def test_reconciled_old_capture_is_not_reused_for_new_shutdown(self):
        self.backup.capture();old=next(iter(self.cloud.rows));self.j.value['phase']='uncertain'
        self.j.value['attempt']=b.tags(self.cloud.rows[old])['AttemptId']
        new=self.backup.capture()['SnapshotId'];self.assertNotEqual(old,new)

    def test_old_verified_cancelled_capture_can_be_success_after_completion(self):
        old=self.cloud.add(minutes=60);self.cloud.set(old,BackupStatus='pending')
        self.backup.capture();self.assertEqual(b.tags(self.cloud.rows[old])['BackupStatus'],'successful')

    def test_old_unverified_or_failed_orphans_only_after_fresh_success(self):
        old=self.cloud.add(minutes=25*60);self.cloud.set(old,ColdCapture='unverified',BackupStatus='pending')
        recent=self.cloud.add(minutes=20);self.cloud.set(recent,ColdCapture='unverified',BackupStatus='pending')
        self.backup.capture();self.assertIn(old,self.cloud.deleted);self.assertIn(recent,self.cloud.rows)

    def test_pending_orphan_is_not_deleted_even_when_old(self):
        pending=self.cloud.add(minutes=25*60,State='pending');self.cloud.set(pending,ColdCapture='unverified',BackupStatus='pending')
        self.backup.capture();self.assertIn(pending,self.cloud.rows)

    def test_AMI_unknown_or_API_failure_prevents_any_deletion(self):
        for i in range(5):self.cloud.add(minutes=10+i)
        original=self.cloud.__call__
        def call(service,action,*args):
            if action=='describe-images':raise RuntimeError('unknown AMI state')
            return original(service,action,*args)
        self.backup.call=call
        with self.assertRaises(RuntimeError):self.backup.capture()
        self.assertEqual(self.cloud.deleted,[])

    def test_filtered_AMI_with_missing_snapshot_mapping_is_unknown(self):
        for i in range(5):self.cloud.add(minutes=10+i)
        original=self.cloud.__call__
        def call(service,action,*args):
            if action=='describe-images':return {'Images':[{'BlockDeviceMappings':[]}]}
            return original(service,action,*args)
        self.backup.call=call
        with self.assertRaises(b.Unsafe):self.backup.capture()
        self.assertEqual(self.cloud.deleted,[])

    def test_newly_protected_old_snapshot_not_deleted(self):
        old=self.cloud.add(minutes=100)
        for i in range(4):self.cloud.add(minutes=10+i)
        original=self.cloud.__call__
        def call(service,action,*args):
            if action=='describe-snapshots' and '--snapshot-ids' in args and args[1]==old:self.cloud.set(old,Protected='true')
            return original(service,action,*args)
        self.backup.call=call
        with self.assertRaises(b.Unsafe):self.backup.capture()
        self.assertNotIn(old,self.cloud.deleted)

    def test_duplicate_listing_not_a_three_backup_quorum(self):
        self.backup.capture();original=self.cloud.__call__
        def call(service,action,*args):
            value=original(service,action,*args)
            if action=='describe-snapshots' and '--filters' in args:value['Snapshots']*=2
            return value
        self.backup.call=call
        with self.assertRaises(b.Unsafe):self.backup.retention(next(iter(self.cloud.rows)))

    def test_delete_ack_without_observed_retention_is_not_completion(self):
        for i in range(5):self.cloud.add(minutes=10+i)
        original=self.cloud.__call__
        def call(service,action,*args):
            if action=='delete-snapshot':return {}  # unknown or stale outcome
            return original(service,action,*args)
        self.backup.call=call
        with self.assertRaises(b.Unsafe):self.backup.capture()
        self.assertNotEqual(self.j.value['phase'],'successful')

    def test_unknown_protection_state_is_not_silently_ignored(self):
        ident=self.cloud.add();self.cloud.set(ident,Protected='unknown')
        with self.assertRaises(b.Unsafe):self.backup.capture()
        self.assertEqual(self.cloud.deleted,[])

    def test_no_success_anchor_no_retention(self):
        ident=self.cloud.add();self.cloud.set(ident,BackupStatus='pending')
        with self.assertRaises(b.Unsafe):self.backup.retention(ident)
        self.assertEqual(self.cloud.deleted,[])

    def test_wrong_keep_policy_rejected(self):
        self.cfg['backup']['keep']=2
        with self.assertRaises(b.Unsafe):b.Backup(self.cfg,None,None,None,None)

    def test_malformed_ownership_tags_not_ignored(self):
        ident=self.cloud.add();self.cloud.rows[ident]['Tags'].append({'Key':'Protected','Value':'true'})
        with self.assertRaises(b.Unsafe):self.backup.snapshot(ident)

    def test_wrong_owner_or_source_never_validated(self):
        for field,value in [('OwnerId','999999999999'),('VolumeId','vol-00000000000000000')]:
            ident=self.cloud.add(**{field:value})
            with self.subTest(field=field),self.assertRaises(b.Unsafe):self.backup.snapshot(ident)

    def test_future_or_naive_time_not_success(self):
        for when in [self.date+timedelta(hours=1),datetime(2026,10,27)]:
            ident=self.cloud.add(StartTime=when.isoformat())
            with self.subTest(when=when),self.assertRaises(b.Unsafe):self.backup.snapshot(ident)


class PolicyTests(unittest.TestCase):
    def setUp(self):self.policy=iam.policy('123456789012','ap-northeast-2','vol-0123456789abcdef0','test-home')
    def test_exact_volume_no_production_control_actions(self):
        statements=self.policy['Statement'];actions=json.dumps([x['Action'] for x in statements])
        for forbidden in ['AttachVolume','DetachVolume','TerminateInstances','SetInstanceProtection','CopySnapshot','DeleteVolume']:self.assertNotIn(forbidden,actions)
        self.assertEqual(next(x for x in statements if x['Sid']=='OnlyExactSourceVolume')['Resource'],'arn:aws:ec2:ap-northeast-2:123456789012:volume/vol-0123456789abcdef0')
    def test_delete_requires_unprotected_owned_specific_set(self):
        condition=next(x for x in self.policy['Statement'] if x['Action']=='ec2:DeleteSnapshot')['Condition']['StringEquals']
        self.assertEqual(next(x for x in self.policy['Statement'] if x['Action']=='ec2:DeleteSnapshot')['Resource'],'arn:aws:ec2:ap-northeast-2::snapshot/*')
        self.assertEqual(condition['ec2:ResourceTag/Protected'],'false');self.assertEqual(condition['ec2:ResourceTag/BackupSet'],'test-home');self.assertEqual(condition['ec2:ResourceTag/SourceVolume'],'vol-0123456789abcdef0')
    def test_existing_tags_cannot_change_owner_or_protection(self):
        row=next(x for x in self.policy['Statement'] if x['Sid']=='OnlyAdvanceOwnedCaptureStatus')
        self.assertEqual(row['Condition']['ForAllValues:StringEquals']['aws:TagKeys'],['ColdCapture','BackupStatus'])
    def test_invalid_policy_identifiers_rejected(self):
        with self.assertRaises(ValueError):iam.policy('bad','ap-northeast-2','vol-0123456789abcdef0','test')


if __name__=='__main__':unittest.main()
