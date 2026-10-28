"""Pure retained-home receiver tests. No AWS, IMDS, Nix, units or real home."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

spec=importlib.util.spec_from_file_location('receiver',Path(__file__).with_name('spot-canary-receive.py'))
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)


def commit(scope='123456abcdef'):
    prefix='results/final/'+scope+'/'
    return {'scope':scope,'all_requested_phase_passed':True,'full_regression_verified':True,'all_artifacts_uploaded_and_read_back':True,
            'production_rollout':False,'work_tracking_verified':False,'armed':False,'goal_complete':False,
            'artifacts':[{'key':prefix+n,'sha256':'a'*64,'bytes':1,'body_readback_verified':True} for n in ['proof.tar.gz','missing-from-base.nix-export.gz','package-result.json','full-tests.json']]}


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
    def test_scope_is_fixed_private_bucket_and_final_prefix(self):
        self.assertEqual(r.key_for('123456abcdef'),('nixos-spot-proof-537112465379-123456abcdef','results/final/123456abcdef/'))
        for scope in ['../escape','nixos-ec2-asg','BAD']:
            with self.subTest(scope=scope),self.assertRaises(RuntimeError):r.key_for(scope)
    def test_all_four_artifacts_require_independent_body_readback_identity(self):
        self.assertEqual(len(r.validate_commit(commit(),'123456abcdef','results/final/123456abcdef/')),4)
        for key in ['all_requested_phase_passed','full_regression_verified','all_artifacts_uploaded_and_read_back']:
            value=commit();value[key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):r.validate_commit(value,'123456abcdef','results/final/123456abcdef/')
    def test_unknown_duplicate_or_cross_scope_roster_never_downloads(self):
        for key in ['results/final/other/proof.tar.gz','../../escape','results/final/123456abcdef/full-tests.json']:
            value=commit();value['artifacts'][0]['key']=key
            with self.subTest(key=key),self.assertRaises(RuntimeError):r.validate_commit(value,'123456abcdef','results/final/123456abcdef/')
    def test_production_authority_flags_are_not_receiver_success(self):
        for key in ['production_rollout','work_tracking_verified','armed','goal_complete']:
            value=commit();value[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):r.validate_commit(value,'123456abcdef','results/final/123456abcdef/')
    def test_existing_evidence_is_never_overwritten(self):
        target=self.root/'existing';target.write_bytes(b'old')
        with patch.object(r,'aws') as api,self.assertRaises(RuntimeError):r.get('bucket','key',target)
        api.assert_not_called();self.assertEqual(target.read_bytes(),b'old')
    def test_wrong_body_hash_never_passes_server_metadata(self):
        target=self.root/'download'
        def get(*args):target.write_bytes(b'wrong');return {'Metadata':{'sha256':'a'*64}}
        with patch.object(r,'aws',side_effect=get),self.assertRaisesRegex(RuntimeError,'disagree'):r.get('bucket','key',target)
        self.assertTrue(target.exists())  # retain failed bytes, never overwrite
    def test_complete_pipeline_is_retained_without_executing_delta_or_profile(self):
        scope='123456abcdef';directory=self.root/'received';value=commit();full={'prepared_system':'/nix/store/'+'a'*32+'-system','executed':618,'source_sha256':{'p':'b'*64}};validator=Mock()
        def get(bucket,key,target,expected=None):
            target.write_text(json.dumps(value if key.endswith('/pipeline.json') else full if key.endswith('/full-tests.json') else {'opaque':True}));return 'a'*64
        with patch.object(r,'get',side_effect=get),patch('shutil.disk_usage',return_value=SimpleNamespace(free=100*1024**3)),patch.object(r.subprocess,'run') as run:
            result=r.receive(scope,time.time()+60,directory,validator,{'expected':'b'*64})
        validator.validate_full.assert_called_once_with(full,{'expected':'b'*64});run.assert_not_called()
        self.assertEqual(result['full_regression_executed'],618);self.assertTrue(result['opaque_delta_not_imported']);self.assertFalse(result['goal_complete']);self.assertTrue((directory/'received.json').exists())
    def test_insufficient_home_reserve_never_downloads_large_artifacts(self):
        scope='123456abcdef';calls=[]
        def get(bucket,key,target,expected=None):calls.append(key);target.write_text(json.dumps(commit()));return 'a'*64
        with patch.object(r,'get',side_effect=get),patch('shutil.disk_usage',return_value=SimpleNamespace(free=1024)), \
                patch.object(r.time,'time',side_effect=[0,100]),patch.object(r.time,'sleep'),self.assertRaisesRegex(RuntimeError,'deadline expired'):
            r.receive(scope,50,self.root/'low-space',Mock(),{})
        self.assertEqual(calls,['results/final/'+scope+'/pipeline.json']);self.assertFalse((self.root/'low-space/received.json').exists())


if __name__=='__main__':unittest.main()
