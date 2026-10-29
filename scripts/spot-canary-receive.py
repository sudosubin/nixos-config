#!/usr/bin/env python3
"""Temporary ORIGINAL-EC2 artifact receiver, never scheduling/work authority.

Start once before a canary pipeline. It independently copies the final proof
and opaque NAR delta to retained home and checks hashes. Bounded lifetime and
resources are supplied by its one-shot systemd unit; no paid controller stack,
store import, profile activation, userdata/config reads or AWS mutations.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.request
import uuid

ORIGINAL='i-0c39eff85c4286b38'
ACCOUNT='537112465379'
REGION='ap-northeast-2'


def require(value,message):
    if not value:raise RuntimeError(message)


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()


def key_for(scope,artifact_run=None):
    require(re.fullmatch('[0-9a-f]{12}',scope) is not None,'invalid scope')
    require(artifact_run is None or re.fullmatch('[0-9a-f]{32}',artifact_run) is not None,'invalid artifact run')
    return 'nixos-spot-proof-'+ACCOUNT+'-'+scope,'results/final/'+scope+'/'+(artifact_run+'/' if artifact_run is not None else '')


def identity():
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request=urllib.request.Request('http://169.254.169.254/latest/api/token',method='PUT',headers={'X-aws-ec2-metadata-token-ttl-seconds':'60'})
    with opener.open(request,timeout=3) as stream:token=stream.read(4096).decode()
    with opener.open(urllib.request.Request('http://169.254.169.254/latest/dynamic/instance-identity/document',headers={'X-aws-ec2-metadata-token':token}),timeout=3) as stream:value=json.load(stream)
    require(value.get('instanceId')==ORIGINAL and value.get('accountId')==ACCOUNT and value.get('region')==REGION,'receiver is not on the retained original host')


def aws(*args):
    env={k:v for k,v in os.environ.items() if not k.startswith(('AWS_','AMAZON_'))}
    env.update(AWS_DEFAULT_REGION=REGION,AWS_CONFIG_FILE='/dev/null',AWS_SHARED_CREDENTIALS_FILE='/dev/null',AWS_EC2_METADATA_DISABLED='false',AWS_MAX_ATTEMPTS='1',HOME='/var/empty')
    p=subprocess.run(['aws',*args,'--region',REGION,'--output','json'],env=env,capture_output=True,text=True,timeout=120)
    if p.returncode:
        code=re.search(r'An error occurred \(([A-Za-z0-9_.-]+)\)',p.stderr)
        raise RuntimeError('artifact API: '+(code[1] if code else 'transport_or_cli_error'))
    return json.loads(p.stdout) if p.stdout.strip() else {}


def get(bucket,key,target,expected=None):
    require(not target.exists(),'evidence destination already exists')
    reply=aws('s3api','get-object','--bucket',bucket,'--key',key,'--checksum-mode','ENABLED',str(target));target.chmod(0o600)
    digest=sha(target);require(reply.get('Metadata',{}).get('sha256')==digest,'artifact SHA metadata/body disagree')
    if expected is not None:require(expected.get('sha256')==digest and expected.get('bytes')==target.stat().st_size,'artifact differs from final manifest')
    return digest


def validate_commit(value,scope,prefix):
    require(value.get('scope')==scope and value.get('all_requested_phase_passed') is True
            and value.get('full_regression_verified') is True and value.get('startup_contract_verified') is True and value.get('all_artifacts_uploaded_and_read_back') is True,'pipeline is not complete')
    require(value.get('production_rollout') is False and value.get('work_tracking_verified') is False
            and value.get('armed') is False and value.get('goal_complete') is False,'proof cannot authorize production')
    names={'proof.tar.gz','missing-from-base.nix-export.gz','package-result.json','full-tests.json'}
    rows=value.get('artifacts',[]);require(len(rows)==4 and {r.get('key') for r in rows}=={prefix+n for n in names},'unknown/duplicate artifact roster')
    for row in rows:require(row.get('body_readback_verified') is True and re.fullmatch('[0-9a-f]{64}',row.get('sha256','')) and type(row.get('bytes')) is int and row['bytes']>0,'unverified artifact identity')
    return rows


def receive(scope,deadline,directory,pipeline_module,expected_source,artifact_run=None):
    bucket,prefix=key_for(scope,artifact_run);directory.mkdir(mode=0o700,parents=False)
    last='no_final_commit'
    while time.time()<deadline:
        attempt=directory/('attempt-'+uuid.uuid4().hex);attempt.mkdir(mode=0o700)
        try:
            commit=attempt/'pipeline.json';get(bucket,prefix+'pipeline.json',commit);value=json.loads(commit.read_text());require(value.get('artifact_run')==artifact_run,'artifact run identity differs');rows=validate_commit(value,scope,prefix)
            required=sum(r['bytes'] for r in rows)+8*1024**3
            import shutil
            require(shutil.disk_usage(directory).free>=required,'insufficient retained-home reserve; no GC or overwrite')
            for row in rows:get(bucket,row['key'],attempt/row['key'].rsplit('/',1)[1],row)
            full=json.loads((attempt/'full-tests.json').read_text());pipeline_module.validate_full(full,expected_source)
            require(full['prepared_system'].startswith('/nix/store/'),'unknown prepared system identity')
            result={'scope':scope,'artifact_run':artifact_run,'received':str(attempt),'full_regression_executed':full['executed'],'source_count':len(full['source_sha256']),
                    'files_sha256':{p.name:sha(p) for p in attempt.iterdir() if p.is_file()},'opaque_delta_not_imported':True,
                    'production_rollout':False,'OS_boot_verified':False,'work_tracking_verified':False,'armed':False,'goal_complete':False}
            target=directory/'received.json';fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'w') as stream:json.dump(result,stream,indent=2);stream.flush();os.fsync(stream.fileno())
            fd=os.open(directory,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd);print(json.dumps(result),flush=True);return result
        except Exception as error:
            # Preserve failed/partial attempts, never overwrite or infer success
            # from absence/ACKs. A future attempt uses a fresh private path.
            last=type(error).__name__+':'+str(error);(attempt/'failure.txt').write_text(last)
            time.sleep(10)
    raise RuntimeError('receiver deadline expired without verified retained artifacts: '+last)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--scope',required=True);parser.add_argument('--expires',required=True);parser.add_argument('--expected-source',type=Path,required=True);parser.add_argument('--artifact-run');parser.add_argument('--home-uuid',default='e47b82eb-22d2-4b12-9e58-92d5aabfbc65');args=parser.parse_args()
    require(os.geteuid()==0,'root receiver required');identity();key_for(args.scope,args.artifact_run)
    deadline=datetime.fromisoformat(args.expires).timestamp();require(0<deadline-time.time()<=8400,'receiver lifetime expired or unbounded')
    p=subprocess.run(['findmnt','-n','-o','TARGET,UUID','--mountpoint','/home'],capture_output=True,text=True,check=True)
    require(p.stdout.split()==['/home',args.home_uuid],'retained home is not the expected mount')
    import stat
    fd=os.open(args.expected_source,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd) as stream:
        st=os.fstat(stream.fileno());require(stat.S_ISREG(st.st_mode) and st.st_uid==0 and not st.st_mode&0o022 and st.st_size<=1048576,'untrusted expected source map');expected=json.load(stream)
    require(sha(__file__)==expected.get('scripts/spot-canary-receive.py'),'executed receiver differs from expected source')
    require(sha(Path(__file__).with_name('spot-canary-pipeline.py'))==expected.get('scripts/spot-canary-pipeline.py'),'executed validator differs from expected source')
    module=Path(__file__).with_name('spot-canary-pipeline.py');spec=importlib.util.spec_from_file_location('pipeline',module);pipeline=importlib.util.module_from_spec(spec);exec(compile(module.read_bytes(),str(module),'exec'),pipeline.__dict__)
    receive(args.scope,deadline,Path('/home/persist/root')/('canary-received-'+args.scope+'-'+uuid.uuid4().hex),pipeline,expected,args.artifact_run)


if __name__=='__main__':main()
