"""Pure pipeline tests. Never run AWS, Nix, systemd, IMDS or a host workload."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

spec=importlib.util.spec_from_file_location('pipeline',Path(__file__).with_name('spot-canary-pipeline.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)


def completed():
    counts=[('validation',42),('work',74),('schedule-guard',98),('profile-cache',29),('cache',52),('acp',43),('gateway',28),('backup',33),('drain',29),('gateway-recovery',19),('cold',17),('frontend',20),('work-linux',14),('acp-linux',9),('gateway-linux',7),('cold-linux',8),('validation-linux',2),('cache-linux',9),('native-kiro-linux',8),('frontend-JS',15),('native-frontend-linux',3)]
    return {'all_passed':True,'executed':559,'unit_cases':499,'root_linux_cases':60,'source_sha256':{'test':'a'*64},
            'compiled_source_sha256':{str(n):'b'*64 for n in range(16)},'production_armed':False,'full_work_tracking_verified':False,'production_rollout':False,
            'suites':[{'suite':name,'expected':count,'executed':count,'passed':True,'returncode':0,'no_skips_or_resource_warnings':True} for name,count in counts]}


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.expected={'test':'a'*64}
    def test_actual_complete_count_source_and_disarmed_scope_required(self):p.validate_full(completed(),self.expected)
    def test_partial_or_receipt_is_not_executed_success(self):
        for changes in [{'all_passed':False},{'executed':507},{'suites':[]},{'compiled_source_sha256':{}},{'source_sha256':{'other':'a'*64}}]:
            with self.subTest(changes=changes),self.assertRaises(RuntimeError):p.validate_full({**completed(),**changes},self.expected)
    def test_failed_or_resource_ambiguous_suite_is_not_success(self):
        for changes in [{'passed':False},{'returncode':1},{'executed':13},{'no_skips_or_resource_warnings':False}]:
            value=completed();value['suites'][12].update(changes)
            with self.subTest(changes=changes),self.assertRaises(RuntimeError):p.validate_full(value,self.expected)
    def test_duplicate_suites_or_substituted_header_counts_cannot_pass(self):
        value=completed();value['suites'][0]['suite']='work'
        with self.assertRaises(RuntimeError):p.validate_full(value,self.expected)
        value=completed();value['suites'][0]['expected']=0;value['suites'][0]['executed']=0
        with self.assertRaises(RuntimeError):p.validate_full(value,self.expected)
    def test_test_pipeline_never_accepts_production_authority(self):
        for key in ['production_armed','full_work_tracking_verified','production_rollout']:
            value=completed();value[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):p.validate_full(value,self.expected)
    def test_only_new_runtime_requisites_are_exported(self):
        old='/nix/store/'+'a'*32+'-base';new='/nix/store/'+'b'*32+'-prepared'
        self.assertEqual(p.missing_paths([old],[new,old,new]),[new])
        for value in ['/home/sudosubin/secret','../escape','/nix/store/not-a-store-path']:
            with self.subTest(value=value),self.assertRaises(RuntimeError):p.missing_paths([], [value])
    def test_baseline_uses_readonly_existing_nix_db_not_unsupported_query_all(self):
        import sqlite3
        database=self.root/'db.sqlite';connection=sqlite3.connect(database);connection.execute('CREATE TABLE ValidPaths(path TEXT NOT NULL)');path='/nix/store/'+'a'*32+'-base';connection.execute('INSERT INTO ValidPaths VALUES (?)',(path,));connection.commit();connection.close();before=p.sha(database)
        self.assertEqual(p.baseline_inventory(database),[path]);self.assertEqual(p.sha(database),before)
        with self.assertRaises(sqlite3.OperationalError):p.baseline_inventory(self.root/'nonexistent.sqlite')
        self.assertFalse((self.root/'nonexistent.sqlite').exists())
    def test_atomic_publish_preserves_parseable_result(self):
        path=self.root/'result.json';p.publish(path,{'all_passed':False});p.publish(path,{'all_passed':True})
        self.assertEqual(json.loads(path.read_text()),{'all_passed':True});self.assertEqual(path.stat().st_mode&0o777,0o600)
    def test_stage_exit_without_complete_result_is_failure_not_idle_success(self):
        v=SimpleNamespace(CGROUP=self.root);proof={'expires':time.time()+1000}
        with patch.object(p.time,'monotonic',side_effect=[0,11]),self.assertRaisesRegex(RuntimeError,'without a durable'):
            p.wait_file(self.root/'missing.json',proof,lambda r:r.get('all_passed'),{'slice':'absent-owned.slice'},v)
    def test_completed_result_may_survive_collected_unit_but_missing_result_cannot(self):
        path=self.root/'complete.json';path.write_text('{"completed":true}')
        self.assertEqual(p.wait_file(path,{'expires':time.time()+1000},lambda r:r.get('completed'),{'slice':'gone'},SimpleNamespace(CGROUP=self.root)),{'completed':True})
    def test_artifact_put_receipt_requires_fresh_body_readback(self):
        source=self.root/'proof.tar.gz';source.write_bytes(b'public test evidence');calls=[]
        def api(*args):
            calls.append(args[:2])
            if args[1]=='head-object':return {'Metadata':{'sha256':p.sha(source)},'ContentLength':source.stat().st_size}
            if args[1]=='get-object':Path(args[-1]).write_bytes(source.read_bytes())
            return {}
        with patch.object(p,'aws',side_effect=api):value=p.upload('own-bucket','results/proof',source,self.root)
        self.assertTrue(value['body_readback_verified']);self.assertEqual(calls,[('s3api','put-object'),('s3api','head-object'),('s3api','get-object')])
        self.assertFalse(list(self.root.glob('readback-*')))
    def test_corrupt_body_cannot_pass_matching_metadata_or_ack(self):
        source=self.root/'proof';source.write_bytes(b'expected')
        def api(*args):
            if args[1]=='head-object':return {'Metadata':{'sha256':p.sha(source)},'ContentLength':source.stat().st_size}
            if args[1]=='get-object':Path(args[-1]).write_bytes(b'corrupt')
            return {}
        with patch.object(p,'aws',side_effect=api),self.assertRaisesRegex(RuntimeError,'body readback'):p.upload('own','results/proof',source,self.root)
    def test_failed_prefetch_is_completed_failure_not_endless_wait(self):
        source=self.root/'source';source.mkdir();(source/'flake.lock').write_text(json.dumps({'nodes':{'public':{'locked':{'type':'github','owner':'public','repo':'test','rev':'a'*40,'narHash':'sha256-test'}}}}))
        folder=self.root/'attempt';folder.mkdir();group=self.root/'owned.slice';group.mkdir();(group/'memory.peak').write_text('1024');(group/'memory.events').write_text('oom 0')
        v=Mock();v.current.return_value={'purpose':'canary-build','slice':'owned.slice'};v.CGROUP=self.root
        error=subprocess.CalledProcessError(1,['never-executed'],stderr='public source unavailable')
        with patch.object(p,'nix',side_effect=error),self.assertRaises(subprocess.CalledProcessError):p.build(source,folder,v,{})
        result=json.loads((folder/'build-result.json').read_text());self.assertTrue(result['completed']);self.assertEqual(result['returncode'],-1);v.cleanup_definition.assert_called_once()
    def test_controller_launcher_bounds_parent_but_allows_exact_owned_oom_initializer(self):
        def path(*args):return self.root if args==('/home/persist/root',) else Path(*args)
        with patch.object(p,'Path',side_effect=path),patch.object(p.subprocess,'run') as run:
            value=p.launch_controller(self.root,self.root/'authority',{'scope':'123456abcdef'})
        argv=run.call_args.args[0]
        for item in ['--property=MemoryMax=256M','--property=MemorySwapMax=0','--property=CPUQuota=25%','--property=OOMScoreAdjust=1000','--property=NoNewPrivileges=yes','--property=ProtectControlGroups=no','--setenv=PATH=/run/current-system/sw/bin','--setenv=HOME=/var/empty']:self.assertIn(item,argv)
        self.assertFalse(value['launch_receipt_is_phase_success']);self.assertFalse(value['goal_complete']);self.assertEqual(Path(value['log']).stat().st_mode&0o777,0o600)

    def run_orchestrator(self,fail_final=False,fail_baseline=False):
        from contextlib import ExitStack
        work=self.root/'work';work.mkdir();source=self.root/'source';source.mkdir();uploads=[]
        proof={'scope':'123456abcdef','instance':'i-0123456789abcdef0','expires':time.time()+1000}
        v=Mock();v.current.return_value=None
        def launch(argv,output,purpose):
            folder=output.parent
            if argv[3]=='build':
                (folder/'prepared').mkdir();p.publish(output,{'completed':True,'returncode':0,'prepared':str(folder/'prepared')})
            elif argv[3]=='package':
                for name in ['proof.tar.gz','missing-from-base.nix-export.gz']:(folder/name).write_bytes(b'fixture-only')
                p.publish(output,{'completed':True,'all_packaged':True})
            else:raise AssertionError(argv)
            return {'slice':'owned-'+argv[3]+'.slice'}
        v.launch.side_effect=launch
        def verify(argv,**kwargs):
            if argv[0]=='systemd-run':
                self.assertIn('--setenv=PATH=/run/current-system/sw/bin',argv);self.assertIn('--setenv=HOME=/var/empty',argv)
                return SimpleNamespace(returncode=0,stdout='',stderr='')
            path=Path(argv[argv.index('--output')+1]);p.publish(path,completed())
            return SimpleNamespace(returncode=0,stdout=json.dumps({'slice':'owned-verify.slice'}),stderr='')
        def upload(bucket,key,path,folder):
            uploads.append(key)
            if fail_final and key=='results/final/123456abcdef/pipeline.json':raise RuntimeError('test final S3 failure')
            return {'key':key,'body_readback_verified':True}
        def path(*args):return work if args==('/home/persist/root',) else Path(*args)
        with ExitStack() as stack:
            stack.enter_context(patch.object(p,'Path',side_effect=path));stack.enter_context(patch.object(p,'baseline_inventory',side_effect=RuntimeError('baseline snapshot failed') if fail_baseline else None,return_value=['/nix/store/'+'a'*32+'-base']))
            stack.enter_context(patch.object(p.subprocess,'run',side_effect=verify));stack.enter_context(patch.object(p,'settled'));stack.enter_context(patch.object(p,'upload',side_effect=upload))
            if fail_final or fail_baseline:
                with self.assertRaisesRegex(RuntimeError,'baseline snapshot' if fail_baseline else 'final S3'):p.orchestrate(source,self.root/'authority',v,proof,self.expected)
            else:p.orchestrate(source,self.root/'authority',v,proof,self.expected)
        state=json.loads(next(work.glob('pipeline-*/pipeline.json')).read_text());return state,uploads

    def test_build_verify_package_and_body_checked_upload_chain_needs_no_operator_poll(self):
        state,uploads=self.run_orchestrator();self.assertTrue(state['all_requested_phase_passed']);self.assertTrue(state['all_artifacts_uploaded_and_read_back'])
        for name in ['proof.tar.gz','missing-from-base.nix-export.gz','full-tests.json','package-result.json','pipeline.json']:
            self.assertIn('results/final/123456abcdef/'+name,uploads)
        self.assertFalse(state['actual_OS_boot_performed']);self.assertFalse(state['goal_complete'])

    def test_failed_final_commit_upload_cannot_leave_pipeline_success(self):
        state,uploads=self.run_orchestrator(True);self.assertFalse(state['all_requested_phase_passed']);self.assertEqual(state['error_type'],'RuntimeError')

    def test_early_baseline_failure_is_durable_and_uploaded_not_outside_try(self):
        state,uploads=self.run_orchestrator(fail_baseline=True);self.assertFalse(state['all_requested_phase_passed']);self.assertFalse(state['full_regression_verified']);self.assertEqual(state['error'],'baseline snapshot failed');self.assertNotIn('build_receipt',state)
        self.assertTrue(any(key.endswith('/pipeline.json') for key in uploads))

    def test_progress_serializer_uploads_frozen_snapshot_not_growing_source(self):
        source=self.root/'progress.json';source.write_text('{"complete":false}');captured=[]
        def upload(bucket,key,path,folder):
            captured.append(Path(path).read_bytes());source.write_text('{"changed":true}');(folder/'.finished').touch();return {'body_readback_verified':True}
        with patch.object(p,'upload',side_effect=upload),patch.object(p.time,'sleep'):
            p.watch(self.root,{'scope':'123456abcdef','expires':time.time()+1000})
        self.assertEqual(captured,[b'{"complete":false}']);self.assertFalse(list(self.root.glob('watch-*')))

    def test_failed_packaging_writes_failure_without_import_or_upload(self):
        folder=self.root/'package';folder.mkdir();(folder/'full-tests.json').write_text(json.dumps({'all_passed':False}))
        v=Mock();v.current.return_value={'purpose':'build'}
        with patch.object(p,'nix') as nix,patch.object(p,'aws') as api,self.assertRaises(RuntimeError):p.package(self.root,folder,v,{})
        value=json.loads((folder/'package-result.json').read_text());self.assertTrue(value['completed']);self.assertFalse(value['all_packaged']);nix.assert_not_called();api.assert_not_called();v.cleanup_definition.assert_called_once()


if __name__=='__main__':unittest.main()
