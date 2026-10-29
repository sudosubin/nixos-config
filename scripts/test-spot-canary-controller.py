"""Pure original discovery/live admission gates; NEVER AWS/SSM/systemd/IMDS."""
from datetime import datetime,timezone
import importlib.util
import hashlib
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch


def module(name,filename):
    s=importlib.util.spec_from_file_location(name,Path(__file__).with_name(filename));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


c=module('controller','spot-canary-controller.py');a=module('autoreceiver','spot-canary-auto-receive.py')


def value():
    s=c.b.plan('123456abcdef','a'*40,datetime(2026,1,1,tzinfo=timezone.utc))
    return {'state':s,'publication':{'source_path':'/home/persist/nixos-rollout-source-'+s['source_revision'],'authority_path':'/home/persist/root/autopublished-'+s['scope']+'/authority.json'},'config':{'artifacts':{'authority':{'sha256':'b'*64}}}}


class ControllerTests(unittest.TestCase):
    def test_discovery_only_accepts_exact_final_commits(self):
        prefix='results/final/123456abcdef/';run='c'*32
        self.assertEqual(a.runs('123456abcdef',{'Contents':[{'Key':prefix+run+'/pipeline.json'},{'Key':prefix+run+'/proof.tar.gz'}]}),[run])
        self.assertEqual(a.runs('123456abcdef',{'Contents':[{'Key':prefix+run+'/proof.tar.gz'}]}),[])

    def test_discovery_refuses_partial_malformed_foreign_or_unbounded_rosters(self):
        for listing in [{'IsTruncated':True},{'Contents':[{'Key':'foreign'}]},{'Contents':[{'Key':'results/final/123456abcdef/$Latest/pipeline.json'}]},
                        {'Contents':[{'Key':'results/final/123456abcdef/'+str(i)*32+'/pipeline.json'} for i in range(4)]}]:
            with self.assertRaises(RuntimeError):a.runs('123456abcdef',listing)

    def test_native_CLI_console_is_already_decoded_not_base64(self):
        self.assertEqual(a.console_bytes({'Output':'UEFI boot\r\n\x1b[31mfailed'}),b'UEFI boot\r\n\x1b[31mfailed');self.assertEqual(a.console_bytes({}),b'')
        with self.assertRaises(RuntimeError):a.console_bytes({'Output':b'not CLI string'})
        with self.assertRaises(RuntimeError):a.console_bytes({'Output':'x'*2097153})

    def test_exact_instance_boot_source_binding_is_required(self):
        identity={'instanceId':'i-'+'c'*17,'boot':'12345678-1234-1234-1234-123456789abc','root_volume':'vol-'+'d'*17,'scope':'123456abcdef'};run=hashlib.sha256((identity['instanceId']+':'+identity['boot']).encode()).hexdigest()[:32];binding={'identity':identity,'authority_sha256':'f'*64};commit={'instance':identity['instanceId']}
        self.assertEqual(a.validate_binding('123456abcdef',run,commit,binding,'f'*64),identity)
        for changes in [{'instanceId':a.r.ORIGINAL},{'boot':'foreign'},{'scope':'foreign'},{'root_volume':'vol-09fea2ff4615b1088'}]:
            bad=copy.deepcopy(binding);bad['identity'].update(changes)
            with self.assertRaises(RuntimeError):a.validate_binding('123456abcdef',run,commit,bad,'f'*64)
        with self.assertRaises(RuntimeError):a.validate_binding('123456abcdef',run,{'instance':'foreign'},binding,'f'*64)
        with self.assertRaises(RuntimeError):a.validate_binding('123456abcdef',run,commit,binding,'a'*64)

    def test_s3_put_unknown_is_never_replayed(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'receipt';path.write_text('public')
            with patch.object(a.r,'aws',side_effect=RuntimeError('lost reply')) as api,self.assertRaises(RuntimeError):a.put('owned','key',path)
            self.assertEqual(api.call_count,1);self.assertIn('--if-none-match',api.call_args.args)

    def test_matching_put_ack_is_not_body_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'receipt';path.write_text('public')
            with patch.object(a.r,'aws',return_value={}),patch.object(a.r,'get',side_effect=RuntimeError('corrupt body')),self.assertRaises(RuntimeError):a.put('owned','key',path)

    def test_original_policy_has_scoped_s3_and_readonly_console_not_work_mutation(self):
        policy=c.original_policy(value()['state']);self.assertEqual({action for row in policy['Statement'] for action in row['Action'] if isinstance(row['Action'],list)},{'s3:GetObject','s3:PutObject'})
        for row in policy['Statement']:
            self.assertIn(c.b.PRODUCTION,row['Condition']['ArnEquals']['ec2:SourceInstanceARN']);self.assertIn('DateLessThan',row['Condition'])
        self.assertEqual(policy['Statement'][1]['Action'],'s3:ListBucket');self.assertNotIn('ec2:',json.dumps(policy['Statement'][0]['Action']))

    def test_admission_checks_live_PID_start_epoch_exact_kernel_and_source_not_green_file(self):
        code=c.admission_code(value());compile(code,'admission','exec')
        for text in ['pid_start','MainPID','memory.max','memory.swap.max','memory.oom.group','cpu.max','NoNewPrivs:','oom_score_adj','authority_sha256','findmnt','spot-canary-auto-receive.py']:
            self.assertIn(text,code)
        self.assertNotIn('set-desired-capacity',code);self.assertNotIn('daemon-reload',code)

    def test_foreign_admission_paths_refuse(self):
        for name in ['source_path','authority_path']:
            v=value();v['publication'][name]='/tmp/untrusted'
            with self.assertRaises(RuntimeError):c.admission_code(v)

    def test_original_diagnostic_is_bounded_private_not_global_reload(self):
        script=c.shell("print('{}')")
        for text in ['MemoryMax=128M','MemorySwapMax=0','CPUQuota=10%','NoNewPrivileges=yes','OOMScoreAdjust=1000','PrivateNetwork=yes','memory.oom.group']:self.assertIn(text,script)
        self.assertNotIn('daemon-reload',script)

    def test_zero_custody_failure_never_requests_capacity(self):
        api=Mock()
        with patch.object(c.p,'validate_prepared',side_effect=RuntimeError('unknown zero')),self.assertRaises(RuntimeError):c.activate(api,value())
        api.assert_not_called()

    def test_missing_live_receiver_never_requests_capacity(self):
        api=Mock();now=datetime(2026,1,1,tzinfo=timezone.utc).timestamp()
        with patch.object(c.p,'validate_prepared'),patch.object(c,'verify_original'),patch.object(c.time,'time',return_value=now),patch.object(c,'command',return_value={'live_original_receiver_admitted':False}),self.assertRaises(RuntimeError):c.activate(api,value())
        api.assert_not_called()

    def test_lost_paid_capacity_reply_is_once_and_not_success(self):
        api=Mock(side_effect=RuntimeError('lost capacity reply'));now=datetime(2026,1,1,tzinfo=timezone.utc).timestamp()
        with patch.object(c.p,'validate_prepared'),patch.object(c,'verify_original'),patch.object(c.time,'time',return_value=now),patch.object(c,'command',return_value={'live_original_receiver_admitted':True,'scope':'123456abcdef'}),self.assertRaises(RuntimeError):c.activate(api,value())
        self.assertEqual(api.call_count,1);self.assertEqual(api.call_args.args[:2],('autoscaling','set-desired-capacity'));self.assertEqual(api.call_args.args[-1],'1')

    def test_short_remaining_native_lifetime_never_requests_capacity(self):
        api=Mock();now=datetime(2026,1,1,1,40,tzinfo=timezone.utc).timestamp()
        with patch.object(c.p,'validate_prepared'),patch.object(c,'verify_original'),patch.object(c.time,'time',return_value=now),self.assertRaises(RuntimeError):c.activate(api,value())
        api.assert_not_called()

    def test_changed_original_policy_blocks_before_any_live_command_or_capacity(self):
        api=Mock()
        with patch.object(c.p,'validate_prepared'),patch.object(c,'verify_original',side_effect=RuntimeError('foreign IAM')),patch.object(c,'command') as command,self.assertRaises(RuntimeError):c.activate(api,value())
        api.assert_not_called();command.assert_not_called()

    def test_ssm_acceptance_without_executed_success_is_not_admission(self):
        api=Mock(side_effect=[{'Command':{'CommandId':'exact'}},{'Status':'Failed','StandardErrorContent':'unknown fence'}])
        with self.assertRaises(RuntimeError):c.command(api,'public-readonly','admit')
        self.assertEqual(api.call_count,2)

    def test_lost_SSM_send_reply_is_not_replayed(self):
        api=Mock(side_effect=RuntimeError('lost SendCommand'))
        with self.assertRaises(RuntimeError):c.command(api,'public-readonly','admit')
        self.assertEqual(api.call_count,1)

    def test_ssm_payload_limits_fail_before_request(self):
        api=Mock()
        for script,comment in [('x'*63000,'short'),('short','x'*101)]:
            with self.assertRaises(RuntimeError):c.command(api,script,comment)
        api.assert_not_called()


if __name__=='__main__':unittest.main()
