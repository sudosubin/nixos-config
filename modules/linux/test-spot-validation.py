"""Offline validation-budget policy tests. No systemd/AWS/process control."""
import hashlib
import io
import json
from datetime import datetime,timezone
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from contextlib import ExitStack
import spot_validation as validation

IDENT='a'*32
SLICE='spotvalidation'+IDENT+'.slice'
UNIT='spot-validation-'+IDENT+'.service'
LEAF='/'+SLICE
GROUP=LEAF+'/'+UNIT


class ValidationBudgetTests(unittest.TestCase):
    def owner(self):
        return {'schema':2,'purpose':'verify','id':IDENT,'slice':SLICE,'driver':UNIT,'boot_id':'fixture-boot'}

    def files(self):
        return {'/proc/self/cgroup':'0::'+GROUP+'\n','/proc/sys/kernel/random/boot_id':'fixture-boot\n',
                str(validation.CGROUP/LEAF.lstrip('/')/'memory.max'):str(validation.MEMORY_MAX),
                str(validation.CGROUP/LEAF.lstrip('/')/'memory.swap.max'):'0',
                str(validation.CGROUP/LEAF.lstrip('/')/'memory.oom.group'):'1',
                str(validation.CGROUP/LEAF.lstrip('/')/'cpu.max'):'100000 100000',
                '/proc/self/oom_score_adj':'1000',
                str(validation.CGROUP/GROUP.lstrip('/')/'cgroup.procs'):str(os.getpid())+'\n'}

    def test_available_memory_is_resource_capacity_not_idle(self):
        self.assertEqual(validation.available_memory('MemAvailable:   2097152 kB\n'),2*1024**3)

    def test_missing_duplicate_or_unknown_memory_unit_rejected(self):
        for text in ['', 'MemAvailable: 1 MB\n','MemAvailable: 1 kB\nMemAvailable: 2 kB\n']:
            with self.subTest(text=text),self.assertRaises(validation.Unsafe):validation.available_memory(text)

    def test_root_or_production_cgroup_has_no_validation_authority(self):
        for text in ['0::/\n','0::/system.slice/amazon-ssm-agent.service\n','0::/user.slice/user-1001.slice\n']:
            self.assertIsNone(validation.own_group(text))

    def test_exact_driver_group_is_recognized(self):
        self.assertEqual(validation.own_group('0::'+GROUP+'\n'),(IDENT,GROUP,LEAF,UNIT))

    def test_only_named_fixture_service_types_may_join(self):
        for name in ['gateway','resource']:
            path=LEAF+'/spot-'+name+'-validation-'+('b'*12)+'.service'
            self.assertEqual(validation.own_group('0::'+path)[0],IDENT)
        with self.assertRaises(validation.Unsafe):validation.own_group('0::'+LEAF+'/amazon-ssm-agent.service')

    def test_unknown_nested_or_traversal_cgroups_refused(self):
        for path in ['0::'+GROUP+'/child','0::/../'+SLICE+'/'+UNIT,'1::/x','0::'+GROUP+'\n1::/x',
                     '0::/system.slice/'+SLICE+'/'+UNIT]:
            with self.subTest(path=path),self.assertRaises(validation.Unsafe):validation.own_group(path)

    def test_exact_enforced_limits_accepted(self):
        validation.limits(str(validation.MEMORY_MAX),'0','1','100000 100000','1000')

    def test_unbounded_memory_swap_or_oom_preferences_refused(self):
        args=[str(validation.MEMORY_MAX),'0','1','100000 100000','1000']
        for index,value in [(0,'max'),(0,str(2*validation.MEMORY_MAX)),(1,'max'),(1,'1'),(2,'0'),(4,'0')]:
            changed=args.copy();changed[index]=value
            with self.subTest(index=index,value=value),self.assertRaises(validation.Unsafe):validation.limits(*changed)

    def test_cpu_budget_cannot_be_absent_or_greater_than_one_cpu(self):
        for value in ['max 100000','0 100000','200000 100000','100000 0','missing']:
            with self.subTest(value=value),self.assertRaises(validation.Unsafe):
                validation.limits(str(validation.MEMORY_MAX),'0','1',value,'1000')

    def test_low_available_memory_defers_not_skips_or_starts_work(self):
        with patch.object(Path,'read_text',return_value='MemAvailable: 1 kB\n'),patch.object(validation.subprocess,'run') as run:
            with self.assertRaisesRegex(validation.Unsafe,'deferred'):validation.memory_gate()
        run.assert_not_called()

    def test_outside_validation_scope_returns_none_without_owner_lookup(self):
        with patch.object(Path,'read_text',return_value='0::/system.slice/amazon-ssm-agent.service'), \
                patch.object(validation,'trusted_json') as owner:
            self.assertIsNone(validation.current())
        owner.assert_not_called()

    def test_kernel_budget_and_current_membership_are_read_back(self):
        files=self.files()
        with patch.object(Path,'read_text',autospec=True,side_effect=lambda p:files[str(p)]), \
                patch.object(validation,'trusted_json',return_value=self.owner()):
            value=validation.current()
        self.assertEqual(value['slice'],SLICE);self.assertEqual(value['memory_max'],1024**3)
        self.assertFalse(value['production_memory_or_idle_verified']);self.assertFalse(value['external_Nix_daemon_builds_covered'])

    def test_foreign_boot_or_owner_is_not_a_resource_witness(self):
        files=self.files()
        for change in [{'schema':True},{'boot_id':'other'},{'driver':'production.service'},{'id':'b'*32}]:
            with self.subTest(change=change),patch.object(Path,'read_text',autospec=True,side_effect=lambda p:files[str(p)]), \
                    patch.object(validation,'trusted_json',return_value={**self.owner(),**change}):
                with self.assertRaises(validation.Unsafe):validation.current()

    def test_missing_kernel_process_membership_is_unknown(self):
        files=self.files();files[str(validation.CGROUP/GROUP.lstrip('/')/'cgroup.procs')]='999999999'
        with patch.object(Path,'read_text',autospec=True,side_effect=lambda p:files[str(p)]), \
                patch.object(validation,'trusted_json',return_value=self.owner()):
            with self.assertRaisesRegex(validation.Unsafe,'membership'):validation.current()

    def test_fixture_cannot_select_production_slice_by_environment(self):
        with patch.dict(os.environ,{'SPOT_VALIDATION_SLICE':'system.slice'}),patch.object(validation,'current',return_value=None):
            with self.assertRaises(validation.Unsafe):validation.fixture_directives()
        with patch.object(validation,'current',return_value={'slice':SLICE,'purpose':'verify','memory_max':validation.MEMORY_MAX}):
            data=validation.fixture_directives()
        self.assertIn('Slice='+SLICE,data);self.assertIn('OOMScoreAdjust=1000',data)
        self.assertIn('MemorySwapMax=0',data);self.assertNotIn('RuntimeMaxSec',data)

    def test_new_files_never_overwrite_an_existing_path_or_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'owned';validation.write_new(p,b'keep')
            with self.assertRaises(FileExistsError):validation.write_new(p,b'overwrite')
            alias=Path(tmp)/'alias';alias.symlink_to(p)
            with self.assertRaises(FileExistsError):validation.write_new(alias,b'overwrite')
            self.assertEqual(p.read_bytes(),b'keep')

    def test_non_linux_launch_cannot_change_service_or_files(self):
        with patch.object(validation.sys,'platform','darwin'),patch.object(validation.subprocess,'run') as run:
            with self.assertRaises(validation.Unsafe):validation.launch(['not-started'],Path('/no-write'))
        run.assert_not_called()

    def test_existing_evidence_is_never_replaced_on_relaunch(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'result';p.write_text('prior-proof')
            with patch.object(validation.sys,'platform','linux'),patch.object(validation.os,'geteuid',return_value=0), \
                    patch.object(validation,'current',return_value=None),patch.object(validation,'memory_gate',return_value=2**32), \
                    patch.object(validation.subprocess,'run') as run:
                with self.assertRaisesRegex(validation.Unsafe,'fresh validation output'):validation.launch(['not-started'],p)
            run.assert_not_called();self.assertEqual(p.read_text(),'prior-proof')

    def test_launch_never_reloads_and_acknowledgement_is_not_execution_or_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);runtime=root/'runtime';units=root/'units';units.mkdir()
            real_lstat=Path.lstat
            def root_owned(path):
                old=real_lstat(path);return SimpleNamespace(st_mode=old.st_mode,st_uid=0)
            with patch.object(validation,'RUNTIME',runtime),patch.object(validation,'UNITS',units), \
                    patch.object(validation.sys,'platform','linux'),patch.object(validation.os,'geteuid',return_value=0), \
                    patch.object(validation,'current',return_value=None),patch.object(validation,'memory_gate',return_value=2**32), \
                    patch.object(Path,'lstat',autospec=True,side_effect=root_owned), \
                    patch.object(Path,'read_text',return_value='fixture-boot'), \
                    patch.object(validation.subprocess,'run') as run,patch.object(validation,'configure_slice') as configure:
                receipt=validation.launch(['/nix/store/fixture-python','fixture.py'],root/'result.json')
                configure.side_effect=validation.Unsafe('injected kernel initialization failure')
                with self.assertRaises(validation.Unsafe):validation.launch(['/nix/store/fixture-python','never.py'],root/'failed.json')
                failed=[p for p in runtime.iterdir() if p.name!=receipt['run_id']]
                self.assertEqual(len(failed),1);self.assertFalse((failed[0]/'ready').exists())
            self.assertEqual(configure.call_args_list[0].args,(receipt['run_id'],))
            self.assertEqual((runtime/receipt['run_id']/'ready').read_text(),receipt['run_id'])
            self.assertTrue(receipt['verification_started']);self.assertFalse(receipt['all_passed'])
            self.assertFalse(receipt['launch_receipt_is_test_success']);self.assertFalse(receipt['production_rollout'])
            self.assertTrue(all(call.args[0][0]=='systemd-run' for call in run.call_args_list))
            self.assertFalse(any('daemon-reload' in call.args[0] for call in run.call_args_list))
            argv=run.call_args.args[0];self.assertIn('--property=PrivateNetwork=yes',argv)
            self.assertIn('--property=OOMScoreAdjust=1000',argv);self.assertIn('--collect',argv)
            self.assertFalse((root/'result.json').exists())

    def initializer(self,stack,foreign=False,extra=False):
        files=self.files();leaf=validation.CGROUP/LEAF.lstrip('/');pid=str(os.getpid())
        files[str(leaf/'cgroup.procs')]='';files['/proc/'+pid+'/cgroup']='0::'+GROUP
        files['/proc/'+pid+'/oom_score_adj']='1000';files[str(leaf/'memory.oom.group')]='0'
        if extra:files[str(leaf/UNIT/'cgroup.procs')]+='\n999999999'
        stack.enter_context(patch.object(validation,'trusted_json',return_value=self.owner()))
        stack.enter_context(patch.object(Path,'read_text',autospec=True,side_effect=lambda p:files[str(p)]))
        stack.enter_context(patch.object(Path,'iterdir',return_value=iter([leaf/UNIT])))
        stack.enter_context(patch.object(Path,'is_dir',return_value=True))
        stack.enter_context(patch.object(validation.subprocess,'run',side_effect=[SimpleNamespace(stdout='/system.slice' if foreign else LEAF),SimpleNamespace(stdout=pid)]))
        write=stack.enter_context(patch.object(Path,'write_text',autospec=True,side_effect=lambda p,text:files.__setitem__(str(p),text)))
        return files,write,leaf

    def test_initializer_writes_only_its_fresh_gated_slice_and_reads_back(self):
        with ExitStack() as stack:
            files,write,leaf=self.initializer(stack)
            validation.configure_slice(IDENT)
            write.assert_called_once_with(leaf/'memory.oom.group','1')
            self.assertEqual(files[str(leaf/'memory.oom.group')],'1')

    def test_initializer_cannot_write_a_foreign_or_production_cgroup(self):
        with ExitStack() as stack:
            files,write,leaf=self.initializer(stack,foreign=True)
            with self.assertRaisesRegex(validation.Unsafe,'foreign'):validation.configure_slice(IDENT)
            write.assert_not_called()

    def test_initializer_will_not_publish_over_unknown_scope_participants(self):
        with ExitStack() as stack:
            files,write,leaf=self.initializer(stack,extra=True)
            with self.assertRaisesRegex(validation.Unsafe,'unknown participants'):validation.configure_slice(IDENT)
            write.assert_not_called()

    def test_build_profile_is_bounded_and_cannot_authorize_test_fixtures(self):
        self.assertEqual(validation.policy('build'),(2*1024**3,4*1024**3))
        with patch.object(validation,'current',return_value={'slice':SLICE,'purpose':'build'}):
            with self.assertRaises(validation.Unsafe):validation.fixture_properties()
        with self.assertRaises(validation.Unsafe):validation.limits(str(2*1024**3),'0','1','100000 100000','1000')

    def test_build_headroom_is_stricter_without_relaxing_verification(self):
        with patch.object(Path,'read_text',return_value='MemAvailable: 3145728 kB\n'):
            self.assertEqual(validation.memory_gate('verify'),3*1024**3)
            with self.assertRaises(validation.Unsafe):validation.memory_gate('build')
        with self.assertRaises(validation.Unsafe):validation.policy('unbounded')

    def test_kernel_limits_must_match_the_recorded_purpose(self):
        files=self.files();files[str(validation.CGROUP/LEAF.lstrip('/')/'memory.max')]=str(2*1024**3)
        with patch.object(Path,'read_text',autospec=True,side_effect=lambda p:files[str(p)]), \
                patch.object(validation,'trusted_json',return_value=self.owner()):
            with self.assertRaises(validation.Unsafe):validation.current()
        with patch.object(Path,'read_text',autospec=True,side_effect=lambda p:files[str(p)]), \
                patch.object(validation,'trusted_json',return_value={**self.owner(),'purpose':'build'}):
            budget=validation.current();self.assertEqual(budget['memory_max'],2*1024**3)
            self.assertEqual(budget['purpose'],'build');self.assertEqual(budget['minimum_available'],4*1024**3)

    def disposable(self):
        scope='b'*12;ident='i-'+'b'*17;group='nixos-spot-proof-'+scope
        document={'instanceId':ident,'accountId':'537112465379','region':'ap-northeast-2','imageId':'ami-0d44956a8229b0dad'}
        instance={'InstanceId':ident,'ImageId':document['imageId'],'State':{'Name':'running'},'InstanceLifecycle':'spot',
                  'BlockDeviceMappings':[{'DeviceName':'/dev/xvda','Ebs':{'VolumeId':'vol-'+'b'*17,'DeleteOnTermination':True}}],
                  'Tags':[{'Key':k,'Value':v} for k,v in {'ScopeId':scope,'ManagedBy':'nixos-spot-validation','Purpose':'artifact-test',
                          'Disposable':'true','DisposableUntil':datetime.fromtimestamp(4600,timezone.utc).isoformat(),
                          'aws:autoscaling:groupName':group}.items()]}
        caller={'Account':'537112465379','Arn':'arn:aws:sts::537112465379:assumed-role/'+group+'/private-session'}
        scheduled=[{'AutoScalingGroupName':group,'ScheduledActionName':group+'-off','StartTime':datetime.fromtimestamp(4500,timezone.utc).isoformat(),'MinSize':0,'MaxSize':0,'DesiredCapacity':0}]
        member={'InstanceId':ident,'AutoScalingGroupName':group,'ProtectedFromScaleIn':False,'LifecycleState':'InService'}
        return document,instance,caller,scheduled,member

    def test_canary_build_profile_cannot_authorize_fixtures(self):
        self.assertEqual(validation.policy('canary-build'),(6*1024**3,10*1024**3))
        with patch.object(validation,'current',return_value={'slice':SLICE,'purpose':'canary-build'}):
            with self.assertRaises(validation.Unsafe):validation.fixture_properties()

    def test_network_access_is_only_for_attested_canary_artifact_fetches(self):
        self.assertEqual(validation.private_network('verify'),'yes')
        self.assertEqual(validation.private_network('build'),'yes')
        self.assertEqual(validation.private_network('canary-build'),'no')
        with self.assertRaises(validation.Unsafe):validation.private_network('unverified')

    def test_disposable_verification_is_fixed_bounded_and_always_private(self):
        self.assertEqual(validation.policy('verify'),(1024**3,2*1024**3))
        self.assertEqual(validation.policy('canary-verify'),(2*1024**3,10*1024**3))
        self.assertEqual(validation.private_network('canary-verify'),'yes')
        with patch.object(validation,'current',return_value={'slice':SLICE,'purpose':'canary-verify','memory_max':2*1024**3}):
            self.assertEqual(validation.fixture_properties()['MemoryMax'],str(2*1024**3))

    def test_disposable_verification_refuses_without_actual_attestation(self):
        with patch.object(validation.sys,'platform','linux'),patch.object(validation.os,'geteuid',return_value=0), \
                patch.object(validation,'current',return_value=None),patch.object(validation,'memory_gate'), \
                patch.object(validation,'attest_disposable',side_effect=validation.Unsafe('no authority')) as attest,patch.object(validation.subprocess,'run') as run:
            with self.assertRaises(validation.Unsafe):validation.launch(['never-started'],Path('/no-write'),'canary-verify')
        attest.assert_called_once();run.assert_not_called()

    def test_canary_verify_owner_proof_and_kernel_limit_are_both_required(self):
        files=self.files();files[str(validation.CGROUP/LEAF.lstrip('/')/'memory.max')]=str(2*1024**3)
        proof=validation.disposable_identity(*self.disposable(),now=1000);owner={**self.owner(),'purpose':'canary-verify','disposable':proof}
        with patch.object(Path,'read_text',autospec=True,side_effect=lambda p:files[str(p)]),patch.object(validation,'trusted_json',return_value=owner),patch.object(validation.time,'time',return_value=1000):
            self.assertEqual(validation.current()['purpose'],'canary-verify')
        with patch.object(Path,'read_text',autospec=True,side_effect=lambda p:files[str(p)]),patch.object(validation,'trusted_json',return_value={**owner,'disposable':{}}):
            with self.assertRaises(validation.Unsafe):validation.current()

    def test_exact_disposable_identity_requires_native_expiry(self):
        proof=validation.disposable_identity(*self.disposable(),now=1000)
        self.assertFalse(proof['production']);self.assertEqual(proof['expires'],4600)
        self.assertNotIn('credentials',proof)

    def test_production_instance_never_obtains_larger_canary_budget(self):
        args=list(self.disposable());args[0]['instanceId']=validation.PRODUCTION_INSTANCE
        with self.assertRaises(validation.Unsafe):validation.disposable_identity(*args,now=1000)

    def test_foreign_account_region_AMI_or_nonspot_identity_refused(self):
        for where,key,value in [(0,'accountId','other'),(0,'region','other'),(0,'imageId','other'),(1,'InstanceLifecycle','on-demand'),(1,'State',{'Name':'stopped'})]:
            args=list(self.disposable());args[where][key]=value
            with self.subTest(key=key),self.assertRaises(validation.Unsafe):validation.disposable_identity(*args,now=1000)

    def test_canary_scope_role_and_unique_tags_are_bound(self):
        for change in ['role','scope','duplicate']:
            args=list(self.disposable())
            if change=='role':args[2]['Arn']='arn:aws:sts::537112465379:assumed-role/nixos-ec2-ssm-role/session'
            elif change=='scope':args[1]['Tags'][0]['Value']='untrusted'
            else:args[1]['Tags'].append(args[1]['Tags'][0])
            with self.subTest(change=change),self.assertRaises(validation.Unsafe):validation.disposable_identity(*args,now=1000)

    def test_disposable_expiry_cannot_be_missing_naive_expired_or_unbounded(self):
        for stamp in ['missing','1970-01-01T01:00:00',datetime.fromtimestamp(900,timezone.utc).isoformat(),datetime.fromtimestamp(9000,timezone.utc).isoformat()]:
            args=list(self.disposable());next(row for row in args[1]['Tags'] if row['Key']=='DisposableUntil')['Value']=stamp
            with self.subTest(stamp=stamp),self.assertRaises(validation.Unsafe):validation.disposable_identity(*args,now=1000)

    def test_retained_or_extra_storage_is_not_a_disposable_root(self):
        for volume in validation.PROTECTED_VOLUMES:
            args=list(self.disposable());args[1]['BlockDeviceMappings'][0]['Ebs']['VolumeId']=volume
            with self.subTest(volume=volume),self.assertRaises(validation.Unsafe):validation.disposable_identity(*args,now=1000)
        args=list(self.disposable());args[1]['BlockDeviceMappings']*=2
        with self.assertRaises(validation.Unsafe):validation.disposable_identity(*args,now=1000)

    def test_protected_or_unknown_ASG_membership_cannot_bypass_expiry(self):
        for key,value in [('ProtectedFromScaleIn',True),('AutoScalingGroupName','nixos-ec2-asg'),('LifecycleState','Pending')]:
            args=list(self.disposable());args[4][key]=value
            with self.subTest(key=key),self.assertRaises(validation.Unsafe):validation.disposable_identity(*args,now=1000)

    def test_recurring_missing_or_nonzero_expiry_action_refused(self):
        args=list(self.disposable());args[3]=[]
        with self.assertRaises(validation.Unsafe):validation.disposable_identity(*args,now=1000)
        for key,value in [('DesiredCapacity',1),('MaxSize',1),('MinSize',False),('Recurrence','0 * * * *'),('StartTime',datetime.fromtimestamp(4700,timezone.utc).isoformat())]:
            args=list(self.disposable());args[3][0][key]=value
            with self.subTest(key=key),self.assertRaises(validation.Unsafe):validation.disposable_identity(*args,now=1000)

    def test_IMDS_production_refusal_happens_before_AWS_queries(self):
        document=self.disposable()[0];document['instanceId']=validation.PRODUCTION_INSTANCE
        opener=SimpleNamespace(open=unittest.mock.Mock(side_effect=[io.BytesIO(b'private-fixture-token'),io.BytesIO(json.dumps(document).encode())]))
        with patch.object(validation.urllib.request,'build_opener',return_value=opener),patch.object(validation.subprocess,'run') as run:
            with self.assertRaisesRegex(validation.Unsafe,'production'):validation.attest_disposable()
        run.assert_not_called()

    def test_canary_launch_attests_before_creating_any_cgroup_or_ready_file(self):
        with patch.object(validation.sys,'platform','linux'),patch.object(validation.os,'geteuid',return_value=0), \
                patch.object(validation,'current',return_value=None),patch.object(validation,'memory_gate') as gate, \
                patch.object(validation,'attest_disposable',side_effect=validation.Unsafe('no authority')),patch.object(validation.subprocess,'run') as run:
            with self.assertRaises(validation.Unsafe):validation.launch(['never-started'],Path('/no-write'),'canary-build')
        gate.assert_called_once_with('canary-build');run.assert_not_called()

    def test_canary_current_scope_rejects_expired_attestation(self):
        files=self.files();files[str(validation.CGROUP/LEAF.lstrip('/')/'memory.max')]=str(6*1024**3)
        proof=validation.disposable_identity(*self.disposable(),now=1000);owner={**self.owner(),'purpose':'canary-build','disposable':proof}
        with patch.object(Path,'read_text',autospec=True,side_effect=lambda p:files[str(p)]),patch.object(validation,'trusted_json',return_value=owner),patch.object(validation.time,'time',return_value=1000):
            self.assertEqual(validation.current()['memory_max'],6*1024**3)
        with patch.object(Path,'read_text',autospec=True,side_effect=lambda p:files[str(p)]),patch.object(validation,'trusted_json',return_value=owner),patch.object(validation.time,'time',return_value=5000):
            with self.assertRaises(validation.Unsafe):validation.current()

    def test_definition_cleanup_does_not_stop_or_kill_running_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            units=Path(tmp);p=units/SLICE;p.write_bytes(b'own definition')
            owner={'definition_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
            with patch.object(validation,'UNITS',units),patch.object(validation,'current',return_value={'id':IDENT,'slice':SLICE}), \
                    patch.object(validation,'trusted_json',return_value=owner),patch.object(validation.subprocess,'run') as run:
                validation.cleanup_definition()
            self.assertFalse(p.exists());run.assert_not_called()  # preserve the active slice policy until last service exits


if __name__=='__main__':unittest.main()
