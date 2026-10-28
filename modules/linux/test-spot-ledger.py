"""Off-root authority tests: real local locks, injected S3/EC2, no real AWS.

Root loss and EC2 termination here are simulations, NOT actual AWS/OS proof.
The separate API verifier checks real S3 conditional semantics and terminated EC2.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import spot_ledger as l
import spot_drain as d
import spot_backup as b


class Backend:
    def __init__(self):
        self.value = None; self.tag = None; self.puts = 0; self.fail = None
    def get(self):
        if self.value is None:raise FileNotFoundError('explicit virgin seed absent')
        return copy.deepcopy(self.value), self.tag
    def put(self, value, tag):
        self.puts += 1
        if tag != self.tag or (tag is None and self.value is not None):raise RuntimeError('PreconditionFailed')
        if self.fail == 'before':raise RuntimeError('lost before commit')
        self.value = copy.deepcopy(value);self.tag = '"'+hashlib.md5(l.encode(value)).hexdigest()+'"'
        if self.fail == 'after':raise RuntimeError('lost reply after commit')


class Cases(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        # Pure model tests inject kernel observations on EVERY OS, not skips or
        # a production fallback. Actual ARM/API verifier uses real /proc facts.
        start=patch.object(l.work,'process_start',return_value=123);start.start();self.addCleanup(start.stop)
        readlink=os.readlink
        ns=patch.object(l.os,'readlink',side_effect=lambda p: 'pid:[unit-test]' if p=='/proc/self/ns/pid' else readlink(p));ns.start();self.addCleanup(ns.stop)
        self.cfg={'account':'537112465379','region':'ap-northeast-2','asg':'private-test','instance_id':'i-'+'1'*17,
                  'home_volume':'vol-'+'a'*17,'home_uuid':'11111111-1111-1111-1111-111111111111','uid':1001,
                  'backup':{'set':'private-test','keep':3,'journal':str(self.root/'unused.json')}}
        self.protocol=d.work.Protocol(self.root/'runtime',uid=os.geteuid(),gid=os.getegid(),root_uid=os.geteuid(),boot_id='boot')
        self.protocol.initialize();self.backend=Backend();self.states={};self.calls=[]
        self.ledger=l.Ledger(self.cfg,self.protocol,self.backend,self.api)
        self.ledger.seed();self.before={'user@1001.service':'active','docker.service':'inactive'}
    def api(self,service,operation,*args):
        self.calls.append((service,operation,args))
        if (service,operation)==('ec2','describe-instances'):
            ident=args[args.index('--instance-ids')+1]
            return {'Reservations':[{'OwnerId':self.cfg['account'],'Instances':[{'InstanceId':ident,'State':{'Name':self.states.get(ident,'running')}}]}]}
        raise AssertionError('unapproved test API')
    def transaction(self,protocol=None,cfg=None,ledger=None,name='private'):
        t=d.Transaction(cfg or self.cfg,protocol or self.protocol,self.root/name/'drain.json',owner_uid=os.geteuid(),ledger=ledger or self.ledger)
        self.addCleanup(t.close);return t
    def other_writer(self,**values):
        self.backend.value['writer']={**self.ledger.me,'pid':987654,'pid_start':123,**values}
        self.backend.value['revision']=1
    def test_missing_remote_state_is_not_empty_or_implicitly_seeded(self):
        self.backend.value=None
        with self.assertRaises(FileNotFoundError):self.ledger.claim()
        self.assertEqual(self.backend.puts,1)
    def test_second_seed_cannot_overwrite_existing_state(self):
        before=copy.deepcopy(self.backend.value)
        with self.assertRaises(RuntimeError):self.ledger.seed()
        self.assertEqual(self.backend.value,before)
    def test_malformed_or_foreign_deployment_is_never_absence(self):
        for change in [{'schema':True},{'revision':True},{'revision':-1},{'deployment':{}},{'writer':{}},{'extra':True}]:
            with self.subTest(change=change),self.assertRaises(l.Unsafe):self.ledger.validate({**self.backend.value,**change})
    def test_duplicate_nonfinite_and_oversize_json_refused(self):
        for data in [b'{"x":1,"x":2}',b'{"x":NaN}',b' '* (l.LIMIT+1)]:
            with self.subTest(data=data[:20]),self.assertRaises((l.Unsafe,ValueError)):l.decode(data)
    def test_claim_is_conditional_and_confirmed_by_body(self):
        self.ledger.claim();self.assertEqual(self.ledger.read()['writer'],self.ledger.me);self.assertEqual(self.backend.puts,2)
    def test_live_same_boot_owner_cannot_be_stolen(self):
        self.other_writer()
        original=l.work.process_start
        with patch.object(l.work,'process_start',side_effect=lambda p:123 if p==987654 else original(p)),self.assertRaisesRegex(l.Unsafe,'still alive'):self.ledger.claim()
        self.assertEqual(self.backend.puts,1)
    def test_different_pid_namespace_is_not_exit_proof(self):
        self.other_writer(pid_namespace='unknown-namespace')
        with self.assertRaisesRegex(l.Unsafe,'namespaces'):self.ledger.claim()
    def test_dead_same_boot_owner_can_be_claimed(self):
        self.other_writer();original=l.work.process_start
        def exited(pid):
            if pid==987654:raise ProcessLookupError()
            return original(pid)
        with patch.object(l.work,'process_start',side_effect=exited):self.ledger.claim()
        self.assertEqual(self.ledger.read()['writer'],self.ledger.me)
    def test_new_boot_same_instance_can_reconcile_old_process(self):
        self.other_writer(boot_id='old-boot');self.ledger.claim();self.assertFalse(self.calls)
    def test_running_stopped_shutting_down_unknown_foreign_instance_cannot_be_claimed(self):
        old='i-'+'2'*17
        for state in ['running','stopped','shutting-down','pending','unknown']:
            self.other_writer(instance_id=old);self.states[old]=state
            with self.subTest(state=state),self.assertRaises(l.Unsafe):self.ledger.claim()
    def test_exact_terminated_foreign_instance_can_be_claimed(self):
        old='i-'+'2'*17;self.other_writer(instance_id=old);self.states[old]='terminated';self.ledger.claim()
        self.assertEqual(self.ledger.read()['writer'],self.ledger.me)
    def test_absent_or_paginated_ec2_response_is_not_termination(self):
        for reply in [{},{'Reservations':[]},{'NextToken':'more','Reservations':[]}, {'Reservations':[{'OwnerId':'000000000000','Instances':[{'InstanceId':'i-'+'2'*17,'State':{'Name':'terminated'}}]}]}]:
            with self.subTest(reply=reply),patch.object(self.ledger,'call',return_value=reply),self.assertRaises(l.Unsafe):self.ledger.terminal('i-'+'2'*17)
    def test_ec2_api_error_retains_original_writer(self):
        self.other_writer(instance_id='i-'+'2'*17);old=copy.deepcopy(self.backend.value)
        with patch.object(self.ledger,'call',side_effect=RuntimeError('injected API failure')),self.assertRaises(RuntimeError):self.ledger.claim()
        self.assertEqual(self.backend.value,old)
    def test_lost_put_reply_is_resolved_by_exact_body_without_second_put(self):
        self.backend.fail='after';self.ledger.claim();self.assertEqual(self.backend.puts,2);self.assertEqual(self.ledger.read()['writer'],self.ledger.me)
    def test_put_not_accepted_does_not_become_success(self):
        self.backend.fail='before'
        with self.assertRaisesRegex(l.Unsafe,'not confirmed'):self.ledger.claim()
        self.assertIsNone(self.backend.value['writer']);self.assertEqual(self.backend.puts,2)
    def test_stale_compare_and_swap_does_not_overwrite_another_value(self):
        self.ledger.read();self.backend.tag='"'+'f'*32+'"'
        with self.assertRaisesRegex(l.Unsafe,'not confirmed'):self.ledger.commit({**self.ledger.value,'writer':self.ledger.me,'revision':1})
        self.assertIsNone(self.backend.value['writer'])
    def test_old_stream_and_writer_are_checked_before_any_update(self):
        self.ledger.claim()
        with self.assertRaisesRegex(l.Unsafe,'stale'):self.ledger.write('drain',{}, {'id':'drain-x'})
        self.backend.value['writer']={**self.ledger.me,'pid':987654}
        with self.assertRaisesRegex(l.Unsafe,'ownership'):self.ledger.write('drain',None,{'id':'drain-x'})
    def test_fork_cannot_reuse_parent_writer(self):
        self.ledger.claim()
        with patch.object(l.os,'getpid',return_value=987654):
            with self.assertRaisesRegex(l.Unsafe,'forked'):self.ledger.write('drain',None,{'id':'drain-x'})
            with self.assertRaisesRegex(l.Unsafe,'forked'):self.ledger.claim()
    def test_backup_cannot_exist_without_same_drain(self):
        value={**self.backend.value,'writer':self.ledger.me,'revision':1,'backup':{'drain_id':'other'}}
        with self.assertRaises(l.Unsafe):self.ledger.validate(value)
        value['drain']={'id':'drain-ours'}
        with self.assertRaises(l.Unsafe):self.ledger.validate(value)
    def test_backup_mutation_cannot_change_expected_remote_record(self):
        t=self.transaction();t.begin(self.before);j=self.ledger.backup_journal();j.read();j.write({'phase':'creating','attempt':'backup-test'})
        previous=j.read();previous['phase']='rejected';j.write(previous)
        self.assertEqual(self.ledger.stream('backup')['phase'],'rejected')
    def test_unknown_backup_cannot_be_discarded_by_next_drain(self):
        t=self.transaction();t.begin(self.before);j=self.ledger.backup_journal();j.read();j.write({'phase':'uncertain'});t.update('recovered')
        old=copy.deepcopy(self.backend.value);candidate={**t.record,'id':'drain-'+'a'*32,'phase':'created'}
        with self.assertRaisesRegex(l.Unsafe,'unfinished backup'):self.ledger.write('drain',t.record,candidate)
        self.assertEqual(self.backend.value,old)
    def test_known_terminal_backup_can_yield_to_fresh_intent(self):
        t=self.transaction();t.begin(self.before);j=self.ledger.backup_journal();j.read();j.write({'phase':'rejected'});t.update('recovered');t.close()
        self.protocol.unseal(t.record['id']);other=self.transaction(name='next');other.begin(self.before)
        self.assertIsNone(self.ledger.stream('backup'));self.assertNotEqual(other.record['id'],t.record['id'])
    def test_local_cache_loss_recovers_exact_remote_intent_not_an_empty_registry(self):
        t=self.transaction();t.begin(self.before);t.update('home_unmounted',services_may_be_stopped=True);ident=t.record['id'];t.close();t.path.unlink()
        fresh=self.transaction(name='empty-new-root');self.assertFalse(fresh.path.exists());self.assertEqual(fresh.read()['id'],ident)
    def test_missing_remote_cannot_fall_back_to_local_recovered_cache(self):
        t=self.transaction();t.begin(self.before);t.update('recovered');self.backend.value=None
        with self.assertRaises(FileNotFoundError):t.read()
    def test_local_publish_failure_does_not_erase_accepted_remote_intent(self):
        t=self.transaction()
        with patch.object(self.protocol,'publish',side_effect=OSError('injected root disk loss')),self.assertRaises(OSError):t.begin(self.before)
        self.assertEqual(self.backend.value['drain']['phase'],'created');self.assertEqual(self.protocol.state(),'open')
    def test_replacement_adoption_preserves_attempt_and_origin_after_termination_only(self):
        t=self.transaction();t.begin(self.before);t.update('home_unmounted',services_may_be_stopped=True);old=t.record['id'];t.close()
        cfg={**self.cfg,'instance_id':'i-'+'2'*17};protocol=d.work.Protocol(self.root/'replacement-run',uid=os.geteuid(),gid=os.getegid(),root_uid=os.geteuid(),boot_id='new-boot');protocol.initialize(boot_closed=True)
        ledger=l.Ledger(cfg,protocol,self.backend,self.api);new=self.transaction(protocol,cfg,ledger,'new-root')
        with self.assertRaises(l.Unsafe):new.claim()
        self.states[self.cfg['instance_id']]='terminated';new.claim();self.assertEqual(new.record['id'],old);self.assertEqual(new.record['origin_instance_id'],self.cfg['instance_id']);self.assertEqual(new.record['identity']['instance_id'],cfg['instance_id']);self.assertEqual(protocol.state(),'starting')
    def test_replacement_unknown_create_cannot_mount_or_reopen(self):
        t=self.transaction();t.begin(self.before);t.update('backing_up',services_may_be_stopped=True);j=self.ledger.backup_journal();j.read();j.write({'schema':1,'volume':self.cfg['home_volume'],'set':'private-test','attempt':'backup-'+'a'*32,'phase':'creating','snapshot_id':None});t.close()
        cfg={**self.cfg,'instance_id':'i-'+'2'*17};self.states[self.cfg['instance_id']]='terminated'
        protocol=d.work.Protocol(self.root/'replacement-run',uid=os.geteuid(),gid=os.getegid(),root_uid=os.geteuid(),boot_id='new-boot');protocol.initialize(boot_closed=True);ledger=l.Ledger(cfg,protocol,self.backend,self.api);new=self.transaction(protocol,cfg,ledger,'new-root');events=[]
        def backup(journal):
            events.append('backup');b.configured(cfg,lambda *args:{'Snapshots':[]},None,None,journal=journal).prepare()
        ops=SimpleNamespace(group=lambda:{'Instances':[{'InstanceId':cfg['instance_id'],'LifecycleState':'InService','ProtectedFromScaleIn':True}]},protect=lambda:events.append('protect'),backup=backup,home=lambda:events.append('home'))
        with self.assertRaisesRegex(b.Unsafe,'unknown create'):new.recover(ops)
        self.assertEqual(events,['protect','backup']);self.assertNotEqual(protocol.state(),'open');self.assertEqual(self.ledger.stream('backup')['phase'],'creating')
    def test_remote_transaction_never_ignores_foreign_volume_or_gateway_identity(self):
        t=self.transaction();t.begin(self.before);t.close();self.backend.value['drain']['identity']['home_volume']='vol-'+'f'*17
        with self.assertRaises(d.Unsafe):self.transaction(name='fresh').read()
    def guard(self):
        spec=importlib.util.spec_from_file_location('ledger_guard_fixture',Path(__file__).with_name('spot-schedule-guard.py'))
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
    def test_prehome_unknown_create_is_reconciled_before_any_mount_permission(self):
        guard=self.guard();t=self.transaction();t.begin(self.before);t.update('backing_up',services_may_be_stopped=True);j=self.ledger.backup_journal();j.read();j.write({'schema':1,'volume':self.cfg['home_volume'],'set':'private-test','attempt':'backup-'+'a'*32,'phase':'creating','snapshot_id':None});t.close();self.cfg['durable_journal']={'bucket':'private-test','key':'journal/private-test/state.json'}
        with patch.object(guard,'drain_transaction',return_value=t),patch.object(guard,'aws',return_value={'Snapshots':[]}),patch.object(guard,'command') as command,self.assertRaises(b.Unsafe):guard.pre_home_journal(self.cfg,self.protocol)
        command.assert_not_called();self.assertIsNone(t.fd);self.assertEqual(self.ledger.stream('backup')['phase'],'creating')
    def test_prehome_missing_remote_cannot_fall_back_to_existing_local_cache(self):
        guard=self.guard();t=self.transaction();t.begin(self.before);t.close();self.cfg['durable_journal']={'bucket':'private-test','key':'journal/private-test/state.json'};self.backend.value=None
        with patch.object(guard,'drain_transaction',return_value=t),patch.object(guard,'reconcile_backup') as backup,self.assertRaises(FileNotFoundError):guard.pre_home_journal(self.cfg,self.protocol)
        backup.assert_not_called();self.assertIsNone(t.fd)
    def test_boot_startup_keeps_closed_for_remote_pending_drain_without_local_file(self):
        guard=self.guard();t=self.transaction();t.begin(self.before);t.close();t.path.unlink()
        protocol=d.work.Protocol(self.root/'starting',uid=os.geteuid(),gid=os.getegid(),root_uid=os.geteuid(),boot_id='boot');protocol.initialize(boot_closed=True)
        with patch.object(guard,'drain_transaction',return_value=t),patch.object(guard,'startup_protection'),patch.object(guard,'verify_recovery_home'):
            self.assertFalse(guard.startup_workloads(self.cfg,protocol))
        self.assertEqual(protocol.state(),'starting');self.assertFalse(t.path.exists())
    def test_boot_startup_keeps_closed_for_unsettled_remote_backup(self):
        guard=self.guard();t=self.transaction();t.begin(self.before);j=self.ledger.backup_journal();j.read();j.write({'phase':'uncertain'});t.update('recovered');t.close()
        protocol=d.work.Protocol(self.root/'starting',uid=os.geteuid(),gid=os.getegid(),root_uid=os.geteuid(),boot_id='boot');protocol.initialize(boot_closed=True)
        with patch.object(guard,'drain_transaction',return_value=t),patch.object(guard,'startup_protection'),patch.object(guard,'verify_recovery_home'),patch.object(guard,'reconcile_backup') as backup:
            self.assertFalse(guard.startup_workloads(self.cfg,protocol));backup.assert_not_called()
        self.assertEqual(protocol.state(),'starting')
    def test_guard_reads_remote_pending_intent_even_when_disposable_root_has_no_file(self):
        guard=self.guard();t=self.transaction();t.begin(self.before);t.update('home_unmounted',services_may_be_stopped=True);t.close();t.path.unlink();cfg={**self.cfg,'durable_journal':{'bucket':'private-test','key':'journal/private-test/state.json'},'drain_journal':str(t.path)}
        with patch('sys.argv',['guard']),patch.object(guard,'RUNTIME',self.protocol.runtime),patch.object(guard,'root_json',return_value=cfg),patch.object(guard,'identity',return_value={'accountId':cfg['account'],'region':cfg['region'],'instanceId':cfg['instance_id']}),patch.object(guard,'work_protocol',return_value=self.protocol),patch.object(guard,'drain_transaction',return_value=t),patch.object(guard,'reconcile_drain',return_value='recovered') as recover,patch.object(guard,'probe') as probe,patch.object(guard,'drain') as drain,patch.object(guard,'status'):
            guard.main();recover.assert_called_once();probe.assert_not_called();drain.assert_not_called()
    def test_guard_put_is_single_attempt_and_cannot_take_credentials_or_endpoint_from_environment(self):
        guard=self.guard()
        with patch.dict(os.environ,{'AWS_ENDPOINT_URL':'https://not-real.invalid','AWS_WEB_IDENTITY_TOKEN_FILE':'/not-real','AWS_ACCESS_KEY_ID':'not-real'}),patch.object(guard.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='{}')) as run:
            guard.aws(self.cfg,'s3api','put-object');env=run.call_args.kwargs['env'];self.assertEqual(env['AWS_MAX_ATTEMPTS'],'1');self.assertFalse(any(k in env for k in ['AWS_ENDPOINT_URL','AWS_WEB_IDENTITY_TOKEN_FILE','AWS_ACCESS_KEY_ID']))
    def test_guard_get_remains_bounded_but_not_a_nonidempotent_put_retry(self):
        guard=self.guard()
        with patch.object(guard.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='{}')) as run:
            guard.aws(self.cfg,'s3api','get-object');self.assertEqual(run.call_args.kwargs['env']['AWS_MAX_ATTEMPTS'],'3');self.assertEqual(run.call_args.kwargs['timeout'],30)
    def test_s3_client_checks_account_checksum_size_and_etag(self):
        data=l.encode(self.backend.value);digest=hashlib.sha256(data).hexdigest();calls=[]
        def api(*args):
            calls.append(args);Path(args[-1]).write_bytes(data)
            return {'ContentLength':len(data),'Metadata':{'sha256':digest},'ChecksumSHA256':l.base64.b64encode(bytes.fromhex(digest)).decode(),'ETag':'"'+'a'*32+'"'}
        s=l.S3({'bucket':'private-unit-test-bucket','key':'journal/private-test/state.json'},api,self.root/'scratch',self.cfg['account'],uid=os.geteuid());value,tag=s.get();self.assertEqual(value,self.backend.value);self.assertIn('--expected-bucket-owner',calls[0]);self.assertFalse(list((self.root/'scratch').iterdir()))
        with patch.object(s,'call',side_effect=lambda *args:(Path(args[-1]).write_bytes(data),{})[1]),self.assertRaises(l.Unsafe):s.get()
    def test_s3_put_uses_conditions_not_ack_as_authority(self):
        calls=[];s=l.S3({'bucket':'private-unit-test-bucket','key':'journal/private-test/state.json'},lambda *args:calls.append(args),self.root/'scratch',self.cfg['account'],uid=os.geteuid());s.put(self.backend.value,None);self.assertEqual(calls[0][-2:],('--if-none-match','*'));s.put(self.backend.value,'"'+'a'*32+'"');self.assertEqual(calls[1][-2:],('--if-match','"'+'a'*32+'"'));self.assertIn('--expected-bucket-owner',calls[1])
    def test_untrusted_scratch_or_broad_key_is_not_used(self):
        with self.assertRaises(l.Unsafe):l.S3({'bucket':'private-test','key':'../any'},None,self.root/'scratch',self.cfg['account'])
        scratch=self.root/'scratch';scratch.mkdir(mode=0o755);s=l.S3({'bucket':'private-test','key':'journal/test/state.json'},None,scratch,self.cfg['account'],uid=os.geteuid())
        with self.assertRaises(l.Unsafe):s.directory()


if __name__=='__main__':unittest.main()
