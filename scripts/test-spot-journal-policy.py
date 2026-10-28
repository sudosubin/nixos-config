"""Pure policy rendering only, NOT actual IAM/S3 denial proof."""
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('policy',Path(__file__).with_name('spot-journal-policy.py'));p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)


class Cases(unittest.TestCase):
    def make(self):return p.policies('537112465379','private-journal-test',['first','second'])
    def test_only_exact_objects_not_bucket_or_wildcard_S3_permission(self):
        statements=self.make()['runtime_role']['Statement'];self.assertEqual(len(statements),2);self.assertEqual(statements[1],{'Effect':'Allow','Action':['ec2:DescribeInstances'],'Resource':'*','Condition':{'StringEquals':{'aws:RequestedRegion':'ap-northeast-2'}}});self.assertEqual(statements[0]['Action'],['s3:GetObject','s3:PutObject']);self.assertEqual(statements[0]['Resource'],['arn:aws:s3:::private-journal-test/journal/first/state.json','arn:aws:s3:::private-journal-test/journal/second/state.json'])
    def test_runtime_no_list_delete_create_policy_or_multipart_grants(self):
        self.assertFalse(any(action in str(self.make()['runtime_role']) for action in ['s3:Delete','s3:List','s3:CreateBucket','s3:PutBucketPolicy','s3:*']))
    def test_expected_bucket_account_is_independent_of_client(self):
        self.assertEqual(self.make()['runtime_role']['Statement'][0]['Condition'],{'StringEquals':{'s3:ResourceAccount':'537112465379'}})
    def test_unconditional_put_is_explicitly_denied_on_service_side(self):
        statement=self.make()['bucket']['Statement'][1];self.assertEqual(statement['Effect'],'Deny');self.assertEqual(statement['Condition']['Null'],{'s3:if-match':'true','s3:if-none-match':'true'});self.assertEqual(statement['Condition']['Bool'],{'s3:ObjectCreationOperation':'true'})
    def test_tls_required(self):self.assertEqual(self.make()['bucket']['Statement'][0]['Condition'],{'Bool':{'aws:SecureTransport':'false'}})
    def test_broad_ambiguous_or_duplicate_namespace_is_refused(self):
        for names in [[],['*'],['..'],['/escape'],['a','a']]:
            with self.subTest(names=names),self.assertRaises(ValueError):p.policies('537112465379','private-journal-test',names)


if __name__=='__main__':unittest.main()
