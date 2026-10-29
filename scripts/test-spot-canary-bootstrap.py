"""Pure bootstrap safety tests: NEVER AWS/systemd/IMDS/Nix or a host workload.

The compressed UserData and source packaging are tested, NOT actual native boot,
actual API custody, automatic replacement, or production bootstrap authority.
"""
import ast
import base64
import copy
from datetime import datetime,timezone
import importlib.util
import io
import json
from pathlib import Path
import re
import shlex
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import Mock,patch
import zlib

spec=importlib.util.spec_from_file_location('bootstrap',Path(__file__).with_name('spot-canary-bootstrap.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)


def config():
    return {'scope':'123456abcdef','bucket':'nixos-spot-proof-537112465379-123456abcdef','revision':'a'*40,
            'expires':'2026-01-01T01:50:00+00:00','artifacts':{
                name:{'key':'artifacts/autobootstrap-'+name,'bytes':p.PUBLIC_BYTES if name=='runtime' else 4096,
                      'sha256':p.PUBLIC_SHA if name=='runtime' else 'b'*64} for name in ['source','authority','runtime']}}


def ready():
    c=config();s=p.b.plan(c['scope'],c['revision'],datetime(2026,1,1,tzinfo=timezone.utc));s.update(LT='lt-0123456789abcdef0',asg_arn='arn:exact:owned-group',role_arn='arn:aws:iam::537112465379:role/'+s['name'],profile_arn='arn:aws:iam::537112465379:instance-profile/'+s['name'])
    value={'state':s,'config':c};data={'UserData':p.user_data(c),'ImageId':p.b.AMI,'InstanceType':'r7g.large','IamInstanceProfile':{'Name':s['name']},'SecurityGroupIds':['sg-065aa5f3bd3cac988'],'MetadataOptions':{'HttpTokens':'required'},'InstanceInitiatedShutdownBehavior':'terminate',
          'BlockDeviceMappings':[{'DeviceName':'/dev/xvda','Ebs':{'VolumeSize':32,'VolumeType':'gp3','Encrypted':True,'DeleteOnTermination':True}}]}
    group={'AutoScalingGroupName':s['name'],'AutoScalingGroupARN':s['asg_arn'],'DesiredCapacity':0,'MinSize':0,'MaxSize':1,'Instances':[],'NewInstancesProtectedFromScaleIn':False,'CapacityRebalance':False,'SuspendedProcesses':[],
           'MixedInstancesPolicy':{'LaunchTemplate':{'LaunchTemplateSpecification':{'LaunchTemplateId':s['LT'],'Version':'2'},'Overrides':[{'InstanceType':'r7g.large'}]},
                                  'InstancesDistribution':{'OnDemandBaseCapacity':0,'OnDemandPercentageAboveBaseCapacity':0,'SpotAllocationStrategy':'lowest-price','SpotInstancePools':1,'SpotMaxPrice':'.020'}}}
    action={'AutoScalingGroupName':s['name'],'ScheduledActionName':s['name']+'-off','StartTime':s['expires'],'MinSize':0,'MaxSize':0,'DesiredCapacity':0}
    return value,data,group,action


class BootstrapTests(unittest.TestCase):
    def test_decoded_userdata_is_bounded_shell_not_a_nixos_reconfiguration(self):
        body=base64.b64decode(p.user_data(config())).decode();self.assertLessEqual(len(body.encode()),16384);self.assertTrue(body.startswith('#!/bin/sh\nset -eu\n'))
        self.assertNotIn('nixos-rebuild',body);self.assertNotIn('daemon-reload',body)
        for option in ['--wait','--collect','MemoryMax=128M','MemorySwapMax=0','CPUQuota=10%','OOMScoreAdjust=1000','Nice=19','NoNewPrivileges=yes','ProtectControlGroups=no']:
            self.assertIn(option,body)

    def test_compressed_userdata_contains_exact_runtime_and_fixed_config(self):
        body=base64.b64decode(p.user_data(config())).decode();command=shlex.split(body.split(' -c ',1)[1]);tree=ast.parse(command[0]);call=tree.body[1].value.args[0].args[0].args[0]
        encoded=ast.literal_eval(call.args[0]);decoded=zlib.decompress(base64.b64decode(encoded)).decode()
        self.assertEqual(decoded,p.RUNTIME+'\nrun('+repr(config())+')\n');compile(decoded,'pinned-userdata','exec')

    def test_userdata_is_deterministic_not_a_new_deadline_or_artifact_run(self):
        self.assertEqual(p.user_data(config()),p.user_data(copy.deepcopy(config())));self.assertNotIn('datetime.now',p.RUNTIME)
        self.assertIn("(iid+':'+boot)",p.RUNTIME);self.assertIn("hexdigest()[:32]",p.RUNTIME)

    def test_foreign_bucket_or_unpinned_revision_refuses(self):
        for field,value in [('scope','../escape'),('revision','$Latest'),('bucket','production-journal')]:
            c=config();c[field]=value
            with self.subTest(field=field),self.assertRaises(RuntimeError):p.user_data(c)

    def test_missing_or_unknown_artifact_refuses(self):
        for change in [lambda c:c['artifacts'].pop('authority'),lambda c:c['artifacts'].update(private_home={})]:
            c=config();change(c)
            with self.assertRaises(RuntimeError):p.user_data(c)

    def test_public_runtime_identity_size_and_hash_cannot_change(self):
        for change in [{'sha256':'d'*64},{'bytes':1},{'key':'artifacts/user-home'}]:
            c=config();c['artifacts']['runtime'].update(change)
            with self.assertRaises(RuntimeError):p.user_data(c)

    def test_source_path_size_digest_and_boolean_lengths_refuse(self):
        for change in [{'key':'../escape'},{'bytes':False},{'bytes':16777217},{'sha256':'bad'}]:
            c=config();c['artifacts']['source'].update(change)
            with self.assertRaises(RuntimeError):p.user_data(c)

    def test_naive_deadline_or_unknown_config_never_serializes(self):
        for change in [{'expires':'2026-01-01T01:50:00'},{'environment_attestation':True}]:
            c=config();c.update(change)
            with self.assertRaises(RuntimeError):p.user_data(c)

    def test_runtime_contains_real_identity_storage_resource_and_source_gates(self):
        for token in ["build_opener(urllib.request.ProxyHandler({}))","get-caller-identity","describe-instances","describe-volumes","describe-auto-scaling-instances","describe-scheduled-actions","memory.oom.group","NoNewPrivs:","ProtectedFromScaleIn","DeleteOnTermination","DisposableUntil","--expected-bucket-owner","--checksum-mode","'diff','--exit-code','--quiet','HEAD'"]:
            self.assertIn(token,p.RUNTIME)
        for volume in ['vol-065729ef75553a7ec','vol-09fea2ff4615b1088','vol-0b529abe51df1eca1']:self.assertIn(volume,p.RUNTIME)

    def test_runtime_has_no_work_acceptance_storage_changes_or_capacity_authority(self):
        for forbidden in ['attach-volume','detach-volume','set-instance-protection','set-desired-capacity','terminate-instances','nixos-rebuild','systemctl reboot','daemon-reload','startup_ready(']:self.assertNotIn(forbidden,p.RUNTIME)
        self.assertIn("folder.mkdir(mode=0o700)",p.RUNTIME);self.assertIn("existing runtime custody is never overwritten",p.RUNTIME)

    def test_guest_preserves_all_mutation_denies_and_adds_only_regional_root_read(self):
        s=ready()[0]['state'];rows=p.guest_policy(s)['Statement'];extra=rows[-1]
        self.assertEqual(extra,{'Effect':'Allow','Action':'ec2:DescribeVolumes','Resource':'*','Condition':{'StringEquals':{'aws:RequestedRegion':p.b.REGION}}})
        denied={a for row in rows if row['Effect']=='Deny' for a in row['Action']}
        self.assertTrue({'ec2:AttachVolume','ec2:DetachVolume','ec2:TerminateInstances','ec2:CreateSnapshot','ec2:AssociateAddress','autoscaling:SetInstanceProtection','autoscaling:SetDesiredCapacity'}<=denied)

    def test_create_zero_never_uses_base_creator_paid_default(self):
        api=Mock();s=ready()[0]['state']
        with patch.object(p.b,'create') as create:r=p.create_zero(api,s)
        create.assert_called_once_with(api,s,activate=False);self.assertFalse(r['capacity_requested']);self.assertFalse(r['paid_activation_authorized'])

    def test_cloud_control_must_be_exact_pinned_zero_stage_and_body(self):
        s=ready()[0]['state'];good={**s,'stage':'native-zero-ready-no-capacity-requested'}
        for changes in [{},{'stage':'capacity-requested'},{'source_revision':'c'*40}]:
            body=json.dumps({**good,**changes}).encode()
            def api(*args):Path(args[-1]).write_bytes(body);return {'Metadata':{'sha256':__import__('hashlib').sha256(body).hexdigest()}}
            if changes:
                with self.assertRaises(RuntimeError):p.read_state(api,s)
            else:self.assertEqual(p.read_state(api,s),good)

    def test_lost_artifact_put_is_never_replayed_or_green(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'public';f.write_bytes(b'public');api=Mock(side_effect=RuntimeError('lost PUT'))
            with self.assertRaises(RuntimeError):p.upload_new(api,ready()[0]['state'],'source',f)
            self.assertEqual(api.call_count,1);self.assertIn('--if-none-match',api.call_args.args)

    def test_matching_metadata_without_matching_full_body_is_not_success(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'public';f.write_bytes(b'public')
            def api(*args):
                if args[:2]==('s3api','get-object'):Path(args[-1]).write_bytes(b'wrong!');return {'Metadata':{'sha256':p.sha(f)}}
                return {}
            with self.assertRaises(RuntimeError):p.upload_new(api,ready()[0]['state'],'source',f)

    def validate(self,change=None):
        value,data,group,action=ready()
        if change:change(value,data,group,action)
        s=value['state'];replies=[{'LaunchTemplateVersions':[{'LaunchTemplateData':data}]},{'AutoScalingGroups':[group]},{'ScheduledUpdateGroupActions':[action]},{'PolicyDocument':p.guest_policy(s)},{'PolicyNames':['DisposableAttestationAndArtifacts']},{'AttachedPolicies':[{'PolicyName':'AmazonSSMManagedInstanceCore','PolicyArn':p.b.CORE}]},{'InstanceProfile':{'Arn':s['profile_arn'],'Roles':[{'Arn':s['role_arn']}]}}]
        api=Mock(side_effect=replies);p.validate_prepared(api,value,now=datetime(2026,1,1,tzinfo=timezone.utc).timestamp()+30);return api

    def test_actual_zero_readback_contract_includes_numeric_LT_and_pinned_userdata(self):self.assertEqual(self.validate().call_count,7)

    def test_nonzero_protected_foreign_or_suspended_group_refuses(self):
        for changes in [{'DesiredCapacity':1},{'DesiredCapacity':False},{'NewInstancesProtectedFromScaleIn':True},{'AutoScalingGroupARN':'reused-name'},{'Instances':[{'InstanceId':'foreign'}]},{'SuspendedProcesses':[{'ProcessName':'Terminate'}]}]:
            with self.subTest(changes=changes),self.assertRaises(RuntimeError):self.validate(lambda v,d,g,a:g.update(changes))

    def test_unpinned_userdata_retained_root_or_profile_refuses(self):
        for changes in [{'UserData':'other'},{'ImageId':'ami-other'},{'IamInstanceProfile':{'Name':'nixos-ec2-ssm-profile'}},{'BlockDeviceMappings':[]},{'KeyName':'operator'},{'SecurityGroupIds':['sg-foreign']},{'MetadataOptions':{'HttpTokens':'optional'}}]:
            with self.assertRaises(RuntimeError):self.validate(lambda v,d,g,a:d.update(changes))

    def test_ondemand_fallback_or_dynamic_LT_refuses(self):
        for field,val in [('OnDemandPercentageAboveBaseCapacity',1),('SpotAllocationStrategy','price-capacity-optimized')]:
            with self.assertRaises(RuntimeError):self.validate(lambda v,d,g,a:g['MixedInstancesPolicy']['InstancesDistribution'].update({field:val}))
        with self.assertRaises(RuntimeError):self.validate(lambda v,d,g,a:g['MixedInstancesPolicy']['LaunchTemplate']['LaunchTemplateSpecification'].update(Version='$Latest'))

    def test_recurring_shifted_or_untyped_native_deadline_refuses(self):
        for changes in [{'Recurrence':'* * * * *'},{'StartTime':'2026-01-02T01:50:00+00:00'},{'DesiredCapacity':False}]:
            with self.assertRaises(RuntimeError):self.validate(lambda v,d,g,a:a.update(changes))

    def test_expired_or_unbounded_prepared_window_is_refused_before_APIs(self):
        value=ready()[0]
        for now in [datetime(2026,1,1,tzinfo=timezone.utc).timestamp()-1,datetime(2026,1,1,1,49,tzinfo=timezone.utc).timestamp()]:
            api=Mock()
            with self.assertRaises(RuntimeError):p.validate_prepared(api,value,now=now)
            api.assert_not_called()

    def test_foreign_inline_managed_or_profile_authority_refuses(self):
        for changes in [{'PolicyNames':['DisposableAttestationAndArtifacts','Foreign']},{'AttachedPolicies':[{'PolicyName':'AdministratorAccess','PolicyArn':'foreign'}]},{'InstanceProfile':{'Arn':'foreign','Roles':[]}}]:
            value,data,group,action=ready();s=value['state'];replies=[{'LaunchTemplateVersions':[{'LaunchTemplateData':data}]},{'AutoScalingGroups':[group]},{'ScheduledUpdateGroupActions':[action]},{'PolicyDocument':p.guest_policy(s)},{'PolicyNames':['DisposableAttestationAndArtifacts']},{'AttachedPolicies':[{'PolicyName':'AmazonSSMManagedInstanceCore','PolicyArn':p.b.CORE}]},{'InstanceProfile':{'Arn':s['profile_arn'],'Roles':[{'Arn':s['role_arn']}]}}]
            index=4 if 'PolicyNames' in changes else 5 if 'AttachedPolicies' in changes else 6;replies[index]=changes
            with self.assertRaises(RuntimeError):p.validate_prepared(Mock(side_effect=replies),value,now=datetime(2026,1,1,tzinfo=timezone.utc).timestamp()+30)

    def test_current_entrypoint_has_no_paid_activation_action(self):
        source=Path(p.__file__).read_text();self.assertIn("choices=['plan','create-zero','configure-zero']",source);self.assertNotIn("'set-desired-capacity'",source)
        self.assertIn("'paid_activation_authorized':False",source)

    def test_public_source_snapshot_retains_commit_and_complete_worktree_not_laptop_origin(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);repo=root/'repo';repo.mkdir();subprocess.run(['git','init','--quiet',str(repo)],check=True)
            (repo/'public.txt').write_text('public source only');subprocess.run(['git','-C',str(repo),'add','.'],check=True)
            subprocess.run(['git','-C',str(repo),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','commit','--quiet','-m','fixture'],check=True)
            rev=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip();out=root/'out';out.mkdir();files=p.source_snapshot(repo,rev,out)
            self.assertEqual(json.loads(files['authority'].read_text()),{'public.txt':p.sha(repo/'public.txt')})
            with tarfile.open(files['source']) as t:
                self.assertEqual(t.extractfile('public.txt').read(),b'public source only');gitconfig=t.extractfile('.git/config').read().decode();self.assertIn('https://github.com/sudosubin/nixos-config',gitconfig);self.assertNotIn(str(repo),gitconfig);self.assertFalse(any(n.startswith(('.git/logs','.git/hooks')) for n in t.getnames()))

    def test_dirty_or_wrong_revision_source_cannot_be_packaged(self):
        with patch.object(p.subprocess,'check_output',return_value='b'*40+'\n'),self.assertRaises(RuntimeError):p.source_snapshot('.', 'a'*40,'.')
        with patch.object(p.subprocess,'check_output',side_effect=['a'*40+'\n',' M public.txt\n']),self.assertRaises(RuntimeError):p.source_snapshot('.', 'a'*40,'.')


if __name__=='__main__':unittest.main()
