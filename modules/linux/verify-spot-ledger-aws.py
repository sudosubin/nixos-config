#!/usr/bin/env python3
"""One-shot REAL S3 CAS/EC2 observation verifier in an explicit private namespace.

No EC2/ASG/EBS/service mutations, production journal, model credentials or store
import. Run with a short-lived Get/Put policy on nine EXACT object keys and a
bounded network-enabled transport unit (not a larger test/build authority).
Synthetic old-drain records and local-cache loss are labelled, not OS/root-loss
or full production recovery proof. Operator deletes this test bucket afterward.
"""
import argparse
import base64
import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import types
import unittest
import urllib.request

NAMES = ['missing', 'seed', 'stale', 'race', 'lost-reply', 'cache-loss', 'old-EC2', 'live-PID', 'unconditional']


def require(value, message):
    if not value:raise RuntimeError(message)


def document():
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request=urllib.request.Request('http://169.254.169.254/latest/api/token',method='PUT',headers={'X-aws-ec2-metadata-token-ttl-seconds':'60'})
    with opener.open(request,timeout=3) as reply:token=reply.read().decode()
    request=urllib.request.Request('http://169.254.169.254/latest/dynamic/instance-identity/document',headers={'X-aws-ec2-metadata-token':token})
    with opener.open(request,timeout=3) as reply:return json.load(reply)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--scope',required=True);p.add_argument('--bucket',required=True);p.add_argument('--terminated-instance',required=True);p.add_argument('--retired-asg',required=True);p.add_argument('--retired-asg-arn',required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    require(sys.platform=='linux' and os.geteuid()==0,'root Linux required; never skip or fake /proc')
    require(re.fullmatch('[0-9a-f]{12}',args.scope),'invalid namespace')
    cgroup=Path('/proc/self/cgroup').read_text().strip().removeprefix('0::')
    require(cgroup=='/system.slice/spot-ledger-api-proof-'+args.scope+'.service','unknown one-shot API cgroup')
    leaf=Path('/sys/fs/cgroup')/cgroup.lstrip('/')
    require((leaf/'memory.max').read_text().strip()==str(256*1024**2) and (leaf/'memory.swap.max').read_text().strip()=='0'
            and (leaf/'memory.oom.group').read_text().strip()=='1' and Path('/proc/self/oom_score_adj').read_text().strip()=='1000','API resource containment is not kernel-confirmed')
    quota,period=(leaf/'cpu.max').read_text().split();require(quota!='max' and int(quota)*2<=int(period),'API CPU quota exceeds one half CPU')
    require(re.search(r'^NoNewPrivs:\s+1$',Path('/proc/self/status').read_text(),re.M),'API helper privilege growth not disabled')
    def headroom():
        available=int(re.search(r'^MemAvailable:\s+(\d+) kB$',Path('/proc/meminfo').read_text(),re.M)[1])*1024
        require(available>=2*1024**3,'API helper host headroom insufficient; not an idle/work approval')
    headroom()
    doc=document();require(doc['accountId']=='537112465379' and doc['region']=='ap-northeast-2','unexpected account/region')
    require(args.bucket=='nixos-ledger-proof-'+doc['accountId']+'-'+args.scope,'not a dedicated test bucket')
    require(re.fullmatch('i-[0-9a-f]{8,17}',args.terminated_instance) and args.terminated_instance!=doc['instanceId'],'old instance must be distinct')
    require(re.fullmatch('nixos-spot-proof-[0-9a-f]{12}',args.retired_asg),'only a retired disposable ASG may be the observation subject')
    fd=os.open(args.authority,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd) as stream:
        info=os.fstat(stream.fileno());require(stat.S_ISREG(info.st_mode) and info.st_uid==0 and not info.st_mode&0o022 and info.st_size<1048576,'untrusted authority');expected=json.load(stream)
    source=Path(__file__).resolve().parents[2]
    def hashes():
        require(all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in expected),'unsafe source roster')
        return {n:hashlib.sha256((source/n).read_bytes()).hexdigest() for n in expected}
    require(hashes()==expected,'source does not match complete pinned authority')
    require(not args.output.exists(),'fresh output required');folder=args.output.parent/('ledger-aws-'+args.scope);folder.mkdir(mode=0o700)
    sys.pycache_prefix=str(folder/'fresh-pycache')
    for name in ['spot_work','spot_ledger','spot_drain','spot_backup']:
        path=source/'modules/linux'/(name+'.py');module=types.ModuleType(name);module.__file__=str(path);sys.modules[name]=module;exec(compile(path.read_bytes(),str(path),'exec'),module.__dict__)
    work=sys.modules['spot_work'];ledger=sys.modules['spot_ledger'];drain=sys.modules['spot_drain'];backup=sys.modules['spot_backup'];calls=[]
    def call(service,operation,*values):
        require((service,operation) in {('s3api','get-object'),('s3api','put-object'),('ec2','describe-instances'),('autoscaling','describe-scaling-activities')},'verifier cannot mutate compute/storage/services')
        env={k:v for k,v in os.environ.items() if not k.startswith(('AWS_','AMAZON_'))};env.update(AWS_CONFIG_FILE='/dev/null',AWS_SHARED_CREDENTIALS_FILE='/dev/null',AWS_EC2_METADATA_DISABLED='false',AWS_MAX_ATTEMPTS='1',HOME='/var/empty')
        result=subprocess.run(['aws',service,operation,'--region',doc['region'],'--output','json',*values],env=env,capture_output=True,text=True,timeout=30)
        calls.append({'service':service,'operation':operation,'returncode':result.returncode})
        if result.returncode:
            code=re.search(r'An error occurred \(([A-Za-z0-9_.-]+)\)',result.stderr);raise backup.AWSFailure(service,operation,code[1] if code else 'UnknownTransportOrCliError')
        return json.loads(result.stdout) if result.stdout.strip() else {}
    cfg={'account':doc['accountId'],'region':doc['region'],'asg':args.retired_asg,'asg_arn':args.retired_asg_arn,'home_volume':'vol-'+'0'*17,
         'home_uuid':'00000000-0000-0000-0000-000000000000','instance_id':doc['instanceId'],'uid':1001}
    observations={}
    class Cases(unittest.TestCase):
        def setUp(self):
            headroom()
            name=NAMES[int(self._testMethodName.split('_')[1])-1];self.private=folder/name;self.private.mkdir(mode=0o700)
            self.protocol=work.Protocol(self.private/'runtime',uid=0,gid=0,root_uid=0);self.protocol.initialize()
            self.backend=ledger.S3({'bucket':args.bucket,'key':'journal/'+args.scope+'-'+name+'/state.json'},call,self.private/'scratch',cfg['account'])
            self.ledger=ledger.Ledger(cfg,self.protocol,self.backend,call)
        def seed(self):self.ledger.seed();self.ledger.claim()
        def test_1_missing_is_not_empty(self):
            with self.assertRaises(backup.AWSFailure):self.ledger.read()
            self.assertIsNone(self.ledger.value)
        def test_2_seed_never_resets_existing_object(self):
            self.seed();before=self.ledger.read()
            with self.assertRaises(backup.AWSFailure) as error:self.ledger.seed()
            self.assertEqual(error.exception.code,'PreconditionFailed');self.assertEqual(self.ledger.read(),before)
        def test_3_stale_ETag_cannot_overwrite(self):
            self.seed();old=copy.deepcopy(self.ledger.read());tag=self.ledger.tag
            self.ledger.commit({**old,'revision':old['revision']+1});winner=self.ledger.read()
            with self.assertRaises(backup.AWSFailure) as error:self.backend.put({**old,'revision':old['revision']+2},tag)
            self.assertEqual(error.exception.code,'PreconditionFailed');self.assertEqual(self.ledger.read(),winner)
        def test_4_actual_concurrent_CAS_has_one_winner(self):
            self.seed();old=copy.deepcopy(self.ledger.read());tag=self.ledger.tag
            def put(revision):
                try:self.backend.put({**old,'revision':revision},tag);return 'accepted'
                except backup.AWSFailure as error:return error.code
            with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(put,[old['revision']+1,old['revision']+2]))
            self.assertEqual(results.count('accepted'),1);self.assertEqual(len(results),2);self.assertTrue(all(r in {'accepted','PreconditionFailed','ConditionalRequestConflict'} for r in results));self.assertIn(self.ledger.read()['revision'],[old['revision']+1,old['revision']+2])
        def test_5_injected_lost_receipt_after_actual_PUT_no_retry(self):
            self.seed();old=self.ledger.read();original=self.backend.put;puts=[]
            def lost(value,tag):
                puts.append(True);original(value,tag);raise backup.AWSFailure('s3api','put-object','InjectedLostReceiptAfterRealPUT')
            self.backend.put=lost;self.ledger.commit({**old,'revision':old['revision']+1});self.assertEqual(len(puts),1)
        def test_6_local_cache_loss_keeps_actual_remote_intent(self):
            self.seed();tx=drain.Transaction(cfg,self.protocol,self.private/'old-root/drain.json',ledger=self.ledger)
            try:tx.begin({'user@1001.service':'inactive','docker.service':'inactive'});tx.update('home_unmounted',services_may_be_stopped=True);expected_record=copy.deepcopy(tx.record)
            finally:tx.close()
            tx.path.unlink();fresh=drain.Transaction(cfg,self.protocol,self.private/'new-root/drain.json',ledger=self.ledger)
            self.assertFalse(fresh.path.exists());self.assertEqual(fresh.read(),expected_record)
        def test_7_actual_late_native_witness_allows_synthetic_origin_adoption(self):
            self.seed();proof=self.ledger.terminal(args.terminated_instance);self.assertEqual(proof['kind'],'asg-activity')
            old=self.ledger.read();origin={**drain.owner(self.protocol.boot_id),'boot_id':'synthetic-prior-boot'}
            record={'schema':1,'id':'drain-'+'a'*32,'identity':{**{k:cfg[k] for k in drain.IDENTITY},'instance_id':args.terminated_instance,'gateway_config_sha256':hashlib.sha256(ledger.encode(None)).hexdigest()},'owner':origin,'origin_boot':origin['boot_id'],'phase':'home_unmounted','services_before':{'user@1001.service':'inactive','docker.service':'inactive'},'services_may_be_stopped':True,'gateway':None,'service_authority':None,'snapshot_id':None}
            historical={**old,'revision':old['revision']+1,'writer':{**origin,'instance_id':args.terminated_instance},'drain':record};self.backend.put(historical,self.ledger.tag)
            fresh=ledger.Ledger(cfg,self.protocol,self.backend,call);tx=drain.Transaction(cfg,self.protocol,self.private/'replacement-root/drain.json',ledger=fresh)
            try:tx.claim();self.assertEqual(tx.record['origin_instance_id'],args.terminated_instance);self.assertEqual(tx.record['id'],record['id']);self.assertEqual(tx.record['identity']['instance_id'],doc['instanceId'])
            finally:tx.close()
            cached=ledger.Ledger(cfg,self.protocol,self.backend,lambda *args:(_ for _ in ()).throw(RuntimeError('injected later observation unavailable')));cached.claim();persisted=cached.confirm_terminal(args.terminated_instance);self.assertEqual(persisted['kind'],'asg-activity');observations['late_terminal']={'witness':persisted,'persisted_with_writer_CAS':True,'cached_without_further_terminal_API':True,'historical_drain_is_synthetic':True}
        def test_8_actual_live_PID_cannot_be_stolen(self):
            self.seed();child=subprocess.Popen([sys.executable,'-I','-c','import time;time.sleep(120)'],env={'HOME':'/var/empty'})
            try:
                old=self.ledger.read();owner={**self.ledger.me,'pid':child.pid,'pid_start':work.process_start(child.pid)};self.backend.put({**old,'writer':owner,'revision':old['revision']+1},self.ledger.tag)
                with self.assertRaisesRegex(ledger.Unsafe,'still alive'):ledger.Ledger(cfg,self.protocol,self.backend,call).claim()
                self.assertEqual(self.ledger.read()['writer'],owner)
            finally:child.terminate();child.wait()
        def test_9_service_policy_rejects_unconditional_overwrite(self):
            self.seed();before=self.ledger.read();path=self.private/'invalid-unconditional.json';path.write_bytes(ledger.encode(before))
            with self.assertRaises(backup.AWSFailure) as error:
                call('s3api','put-object','--bucket',args.bucket,'--key',self.backend.settings['key'],'--body',str(path),'--server-side-encryption','AES256')
            self.assertEqual(error.exception.code,'AccessDenied');self.assertEqual(self.ledger.read(),before)
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Cases);start=time.time();result=unittest.TextTestRunner(verbosity=2).run(suite)
    require(hashes()==expected,'source changed during real API verification')
    value={'scope':args.scope,'executed':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'all_passed':result.wasSuccessful() and result.testsRun==9 and not result.skipped,
           'resource_scope':{'cgroup':cgroup,'memory_peak':(leaf/'memory.peak').read_text(),'memory_events':(leaf/'memory.events').read_text(),'memory_max':256*1024**2,'not_general_networked_verification_authority':True},'source_sha256':expected,'instance':doc['instanceId'],'requested_old_instance':args.terminated_instance,'observations':observations,'calls':calls,'started':start,'finished':time.time(),
           'proof_scope':'actual S3 conditional writes/checksum body readback/concurrency + real late ASG-ARN terminal witness, durable receipt and PID observations; synthetic old-drain and local-cache deletion, NOT actual root loss/OS/EBS recovery',
           'snapshot_or_compute_mutations':False,'production_rollout':False,'work_tracking_verified':False,'armed':False,'goal_complete':False}
    fd=os.open(args.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as out:json.dump(value,out,indent=2);out.flush();os.fsync(out.fileno())
    print(json.dumps({k:v for k,v in value.items() if k not in ['calls','source_sha256']}),flush=True)
    if not value['all_passed']:raise SystemExit(1)


if __name__=='__main__':main()
