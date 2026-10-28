#!/usr/bin/env python3
"""One-shot CANARY-ONLY build -> full regression -> archive -> S3 readback.

No local poller is needed after launch. The already installed native ASG expiry
is never extended. No system/profile/AMI/boot/storage/EIP changes are performed.
Only the exact API-attested disposable instance may run any stage. Production
readiness/arming and actual OS boot are explicitly outside this phase.
"""
import argparse
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import time
import types
import urllib.parse
import uuid

EXPECTED=(559,499,60)


def require(condition,message):
    if not condition:raise RuntimeError(message)


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()


def publish(path,value):
    path=Path(path);temporary=path.with_name('.'+path.name+'-'+uuid.uuid4().hex)
    fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as stream:json.dump(value,stream,indent=2);stream.flush();os.fsync(stream.fileno())
    os.replace(temporary,path);fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


def validate_full(value,expected):
    require(value.get('all_passed') is True,'regression has no executed success')
    require((value.get('executed'),value.get('unit_cases'),value.get('root_linux_cases'))==EXPECTED,'incomplete measured regression count')
    rows=value.get('suites',[])
    require(len(rows)==21 and all(r.get('passed') is True and r.get('returncode')==0
            and r.get('no_skips_or_resource_warnings') is True and r.get('executed')==r.get('expected') for r in rows),'failed/ambiguous regression suite')
    require(len({r.get('suite') for r in rows})==21 and all(type(r.get('executed')) is int for r in rows)
            and sum(r['executed'] for r in rows)==EXPECTED[0]
            and sum(r['executed'] for r in rows if r['suite'].endswith('-linux'))==EXPECTED[2],
            'measured suite sums or identities do not match the header')
    require(value.get('source_sha256')==expected and len(value.get('compiled_source_sha256',{}))==16,'source or immutable identity mismatch')
    require(value.get('production_armed') is False and value.get('full_work_tracking_verified') is False
            and value.get('production_rollout') is False,'test result cannot grant production authority')


def baseline_inventory(database=Path('/nix/var/nix/db/db.sqlite')):
    # Legacy nix-store --query has no --all on Nix2.34. Read the existing DB
    # through a read-only connection; never instantiate/build via a daemon.
    connection=sqlite3.connect('file:'+str(database)+'?mode=ro',uri=True)
    try:
        rows=[row[0] for row in connection.execute('SELECT path FROM ValidPaths ORDER BY path')]
        missing_paths(rows,[])
        return rows
    finally:connection.close()


def missing_paths(baseline,requisites):
    pattern=r'/nix/store/[0-9a-df-np-sv-z]{32}-[^/\s]+'
    require(isinstance(baseline,list) and isinstance(requisites,list),'unknown store roster')
    require(all(isinstance(p,str) and re.fullmatch(pattern,p) for p in baseline+requisites),'invalid store path in export roster')
    return sorted(set(requisites)-set(baseline))


def load_source(source,authority,stage='run',folder=None):
    source=Path(source).resolve(strict=True);authority=Path(authority)
    fd=os.open(authority,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd) as stream:
        import stat
        st=os.fstat(stream.fileno());require(stat.S_ISREG(st.st_mode) and st.st_uid==0 and not st.st_mode&0o022 and st.st_size<=1048576,'untrusted source authority');expected=json.load(stream)
    require(isinstance(expected,dict) and expected,'empty source map')
    for name,value in expected.items():
        p=Path(name);require(not p.is_absolute() and '..' not in p.parts and re.fullmatch('[0-9a-f]{64}',value),'invalid source identity')
        require(sha(source/name)==value,'pinned source differs: '+name)
    git=next(p for p in Path('/nix/store').glob('*-git-*/bin/git') if p.is_file())
    tracked=subprocess.check_output([str(git),'-C',str(source),'ls-files','-z']).decode().split('\0')
    require(set(filter(None,tracked))==set(expected),'source authority is not the complete tracked tree')
    subprocess.run([str(git),'-C',str(source),'diff','--quiet'],check=True)
    subprocess.run([str(git),'-C',str(source),'diff','--cached','--quiet'],check=True)
    require('scripts/spot-canary-pipeline.py' in expected and Path(__file__).read_bytes()==(source/'scripts/spot-canary-pipeline.py').read_bytes(),'executed pipeline is not the pinned source')
    name='modules/linux/spot_validation.py';v=types.ModuleType('spot_validation');p=source/name
    exec(compile(p.read_bytes(),str(p),'exec'),v.__dict__)
    # Before creating any workspace or using a larger cage: actual IMDS/STS/
    # Spot/root/ASG/tags/deadline checks, not an environment assertion.
    budget=v.current()
    if budget is None:
        proof=v.attest_disposable()
    elif stage=='build' and budget['purpose']=='canary-build':
        proof=v.trusted_json(v.RUNTIME/budget['id']/'owner.json')['disposable']
    elif stage=='package' and budget['purpose']=='build' and folder is not None:
        proof=v.trusted_json(folder/'identity.json')
        require(proof.get('production') is False and proof.get('instance')!=v.PRODUCTION_INSTANCE
                and proof.get('image')=='ami-0d44956a8229b0dad' and proof.get('account')=='537112465379'
                and proof.get('region')=='ap-northeast-2' and re.fullmatch('[0-9a-f]{12}',proof.get('scope',''))
                and proof.get('root_volume') not in v.PROTECTED_VOLUMES and 0<proof.get('expires',0)-time.time()<=7200,
                'packaging lost its parent disposable identity')
    else:raise RuntimeError('stage cannot use another purpose or escape a cage')
    return source,expected,v,proof


def nix(*arguments,**kwargs):
    return subprocess.run(['nix','--store','local','--extra-experimental-features','nix-command flakes',*arguments],check=True,**kwargs)


def build(source,folder,v,expected):
    budget=v.current();require(budget and budget['purpose']=='canary-build','build requires its actual attested6GiB cage');v.memory_gate('canary-build')
    result={'stage':'build','returncode':None,'prepared':None,'source_sha256':expected,'resource_budget':budget,'production_rollout':False}
    try:
        home=folder/'nix-home';home.mkdir(mode=0o700);os.environ.update(HOME=str(home),XDG_CACHE_HOME=str(home/'cache'),GC_INITIAL_HEAP_SIZE='67108864',GC_FREE_SPACE_DIVISOR='8',GC_MAXIMUM_HEAP_SIZE='4294967296')
        lock=json.loads((source/'flake.lock').read_text());rows=[]
        for name,node in sorted(lock['nodes'].items()):
            entry=node.get('locked')
            if not entry:continue
            if entry.get('repo')=='nixos-config-private':
                rows.append({'name':name,'not_fetched':'unused private Linux inputs; no credentials supplied'});continue
            kind=entry.get('type');require(kind in {'github','gitlab'},'unknown public source transport')
            query={'narHash':entry['narHash']}
            if entry.get('dir'):query['dir']=entry['dir']
            uri=kind+':'+entry['owner']+'/'+entry['repo']+'/'+entry['rev']+'?'+urllib.parse.urlencode(query)
            r=nix('flake','prefetch','--json',uri,capture_output=True,text=True);rows.append({'name':name,'stdout':r.stdout,'stderr':r.stderr});publish(folder/'prefetch.json',rows)
        git=next(p for p in Path('/nix/store').glob('*-git-*/bin/git') if p.is_file());os.environ['PATH']=str(git.parent)+':/run/current-system/sw/bin'
        head=subprocess.check_output([str(git),'-C',str(source),'rev-parse','HEAD'],text=True).strip()
        expression='let f = builtins.getFlake "git+file://'+str(source)+'?rev='+head+'&shallow=1"; in (f.nixosConfigurations.linux.extendModules { modules = [{ services.spotAcp.enable = true; services.spotGateway.enable = true; }]; }).config.system.build.toplevel'
        output=folder/'prepared';require(not output.exists(),'prepared link already exists')
        with (folder/'build.log').open('x') as log:
            p=subprocess.run(['nix','--store','local','--extra-experimental-features','nix-command flakes','build','--impure','--no-write-lock-file','--max-jobs','1','--cores','1','--option','builders','','--option','substituters','https://cache.nixos.org','--option','require-sigs','true','--out-link',str(output),'--expr',expression],stdout=log,stderr=subprocess.STDOUT)
        result.update(returncode=p.returncode,prepared=str(output.resolve()) if p.returncode==0 else None)
        require(p.returncode==0 and output.exists(),'full system build failed; complete log retained')
        require(json.loads((output/'etc/spot-schedule-guard.json').read_text())['armed'] is False,'prepared guard is not disarmed')
    except BaseException as error:
        result.update(returncode=-1,error_type=type(error).__name__,stderr=getattr(error,'stderr',None))
        raise
    finally:
        result['completed']=True
        result['memory_peak']=(v.CGROUP/budget['slice']/'memory.peak').read_text();result['memory_events']=(v.CGROUP/budget['slice']/'memory.events').read_text();publish(folder/'build-result.json',result);v.cleanup_definition()


def package(source,folder,v,expected):
    budget=v.current();require(budget and budget['purpose']=='build','packaging is bounded artifact work, not verification');v.memory_gate('build')
    outcome={'completed':False,'all_packaged':False}
    try:
        result=json.loads((folder/'full-tests.json').read_text());validate_full(result,expected);prepared=folder/'prepared'
        refs=subprocess.check_output(['nix-store','--query','--requisites',str(prepared)],text=True).splitlines()
        baseline=json.loads((folder/'baseline.json').read_text());delta=missing_paths(baseline,refs)
        # Export only outputs missing from this exact retained base AMI inventory.
        # This archive is opaque evidence/rebuild material, NEVER a signature
        # bypass or a store import on the production host.
        sizes=nix('path-info','--json','--json-format','1',*delta,capture_output=True,text=True) if delta else None
        info=json.loads(sizes.stdout) if sizes else {};entries=info.values() if isinstance(info,dict) else info
        reserve=sum(entry['narSize'] for entry in entries)+512*1024**2
        require(shutil.disk_usage(folder).free>=reserve,'insufficient archive reserve; no GC or storage workaround')
        archive=folder/'missing-from-base.nix-export.gz';require(not archive.exists(),'delta archive already exists')
        with (folder/'export.stderr').open('x') as error,archive.open('xb') as raw:
            p=subprocess.Popen(['nix-store','--export',*delta],stdout=subprocess.PIPE,stderr=error)
            try:
                with gzip.GzipFile(fileobj=raw,mode='wb',compresslevel=3) as compressed:shutil.copyfileobj(p.stdout,compressed)
            finally:
                p.stdout.close();status=p.wait()  # even compression/disk errors must reap our exact exporter
            require(status==0,'NAR export failed; not complete');raw.flush();os.fsync(raw.fileno())
        archive.chmod(0o600);publish(folder/'delta.json',{'paths':delta,'path_count':len(delta),'sha256':sha(archive),'bytes':archive.stat().st_size,'baseline_image':'ami-0d44956a8229b0dad','opaque_no_import':True})
        nixinfo=nix('path-info','--recursive','--json','--json-format','1',str(prepared),capture_output=True,text=True);(folder/'closure.json').write_text(nixinfo.stdout)
        proof=folder/'proof.tar.gz';require(not proof.exists(),'proof archive exists')
        members=[p for p in folder.iterdir() if p.is_file() and p!=archive and not p.name.startswith(('watch-','readback-'))]
        with tarfile.open(proof,'w:gz',compresslevel=3) as t:
            for name in sorted(expected):t.add(source/name,arcname='source/'+name,recursive=False)
            for p in members:t.add(p,arcname='evidence/'+p.name,recursive=False)
        proof.chmod(0o600)
        with tarfile.open(proof) as t:
            require({m.name[7:]:hashlib.sha256(t.extractfile(m).read()).hexdigest() for m in t.getmembers() if m.name.startswith('source/')}==expected,'archived source differs')
        outcome.update(all_packaged=True,proof=str(proof),proof_sha256=sha(proof),delta=str(archive),delta_sha256=sha(archive),production_rollout=False,OS_boot_verified=False)
    except BaseException as error:
        outcome.update(error_type=type(error).__name__,stderr=getattr(error,'stderr',None))
        raise
    finally:
        outcome['completed']=True;publish(folder/'package-result.json',outcome);v.cleanup_definition()


def aws(*args):
    env={k:value for k,value in os.environ.items() if not k.startswith(('AWS_','AMAZON_'))}
    env.update(AWS_DEFAULT_REGION='ap-northeast-2',AWS_CONFIG_FILE='/dev/null',AWS_SHARED_CREDENTIALS_FILE='/dev/null',AWS_EC2_METADATA_DISABLED='false')
    p=subprocess.run(['aws',*args,'--region','ap-northeast-2','--output','json'],env=env,capture_output=True,text=True,timeout=120)
    require(p.returncode==0,'scoped artifact API failed: '+args[0]+':'+args[1])
    return json.loads(p.stdout) if p.stdout.strip() else {}


def upload(bucket,key,path,folder):
    digest=sha(path)
    aws('s3api','put-object','--bucket',bucket,'--key',key,'--body',str(path),'--server-side-encryption','AES256','--checksum-algorithm','SHA256','--checksum-sha256',base64.b64encode(bytes.fromhex(digest)).decode(),'--metadata','sha256='+digest)
    head=aws('s3api','head-object','--bucket',bucket,'--key',key,'--checksum-mode','ENABLED')
    require(head['Metadata']['sha256']==digest and head['ContentLength']==Path(path).stat().st_size,'artifact metadata readback differs')
    readback=folder/('readback-'+uuid.uuid4().hex)
    try:
        aws('s3api','get-object','--bucket',bucket,'--key',key,'--checksum-mode','ENABLED',str(readback));require(sha(readback)==digest,'artifact body readback differs')
    finally:readback.unlink(missing_ok=True)
    return {'key':key,'sha256':digest,'bytes':Path(path).stat().st_size,'body_readback_verified':True}


def watch(folder,proof):
    """Bounded evidence serializer, not a workload/idle controller."""
    bucket='nixos-spot-proof-537112465379-'+proof['scope'];seen={}
    while time.time()<proof['expires'] and not (folder/'.finished').exists():
        for path in list(folder.iterdir()):
            if not path.is_file() or path.suffix not in {'.json','.log','.stderr'} or path.stat().st_size>20*1024*1024:continue
            data=path.read_bytes()
            if not data or len(data)>20*1024*1024:continue
            if path.suffix=='.json':
                try:json.loads(data)
                except ValueError:continue
            digest=hashlib.sha256(data).hexdigest()
            if seen.get(path.name)==digest:continue
            snapshot=folder/('watch-'+uuid.uuid4().hex)
            try:
                fd=os.open(snapshot,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
                with os.fdopen(fd,'wb') as stream:stream.write(data)
                upload(bucket,'results/progress/'+folder.name+'/'+path.name,snapshot,folder);seen[path.name]=digest
            except Exception:pass  # failure remains failure; main final artifacts require readback
            finally:snapshot.unlink(missing_ok=True)
        time.sleep(10)


def wait_file(path,proof,completed,receipt=None,v=None):
    started=time.monotonic()
    while time.time()<proof['expires']-120:
        if path.exists():
            try:value=json.loads(path.read_text())
            except json.JSONDecodeError:time.sleep(2);continue
            if completed(value):return value
        if receipt and v and time.monotonic()-started>10:
            group=v.CGROUP/receipt['slice']
            require(group.exists() and 'populated 0' not in (group/'cgroup.events').read_text(),
                    'owned stage exited without a durable complete result; never success from absence')
        time.sleep(5)
    raise RuntimeError('native expiry approaching; no further stages or completion claim')


def settled(v,receipt):
    group=v.CGROUP/receipt['slice'];limit=time.monotonic()+30
    while group.exists() and 'populated 0' not in (group/'cgroup.events').read_text():
        require(time.monotonic()<limit,'previous owned stage has not exited; no next launch/reload');time.sleep(.1)


def orchestrate(source,authority,v,proof,expected):
    require(v.current() is None,'orchestrator must not escape/relabel another cage')
    scope=proof['scope'];bucket='nixos-spot-proof-537112465379-'+scope;folder=Path('/home/persist/root')/('pipeline-'+uuid.uuid4().hex);folder.mkdir(mode=0o700)
    state={'scope':scope,'instance':proof['instance'],'expires':proof['expires'],'folder':str(folder),'all_requested_phase_passed':False,'full_regression_verified':False,'all_artifacts_uploaded_and_read_back':False,'actual_OS_boot_performed':False,'production_rollout':False,'work_tracking_verified':False,'armed':False,'goal_complete':False}
    publish(folder/'source-map.json',expected);publish(folder/'identity.json',proof);publish(folder/'pipeline.json',state)
    # Snapshot before fetching/building. The retained clean base AMI can recreate
    # these paths; every additional runtime output is exported automatically.
    script=source/'scripts/spot-canary-pipeline.py';common=['--source',str(source),'--authority',str(authority),'--folder',str(folder)]
    try:
        require(proof['expires']-time.time()>900,'too little native lifetime for a new full run')
        # A separate tiny serializer continues uploading partial evidence even
        # if this coordinator fails. It has no workload control or paid service.
        subprocess.run(['systemd-run','--unit=spot-proof-watch-'+scope+'-'+folder.name[-12:],'--description=Scoped-expiring-evidence-only','--collect',
                        '--property=Type=exec','--property=MemoryMax=128M','--property=MemorySwapMax=0','--property=CPUQuota=10%',
                        '--property=OOMScoreAdjust=1000','--property=Nice=19','--property=NoNewPrivileges=yes','--property=ProtectControlGroups=yes',
                        sys.executable,'-I',str(script),'watch',*common],check=True,capture_output=True,text=True)
        publish(folder/'baseline.json',baseline_inventory())
        receipt=v.launch([sys.executable,'-I',str(script),'build',*common],folder/'build-result.json',purpose='canary-build');state['build_receipt']=receipt;publish(folder/'pipeline.json',state)
        value=wait_file(folder/'build-result.json',proof,lambda r:r.get('completed') is True,receipt,v)
        require(value['returncode']==0 and value['prepared'],'build failed, not verification success');settled(v,receipt)
        command=[sys.executable,'-I',str(source/'modules/linux/verify-spot-linux.py'),'--source',str(source),'--prepared',str(folder/'prepared'),'--expected-source',str(authority),'--output',str(folder/'full-tests.json'),'--disposable-verify']
        p=subprocess.run(command,capture_output=True,text=True);publish(folder/'verify-launch.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr});require(p.returncode==0,'verification launcher failed')
        receipt=json.loads(p.stdout.strip().splitlines()[-1]);state['verify_receipt']=receipt
        value=wait_file(folder/'full-tests.json',proof,lambda r:r.get('all_passed') is True or 'resource_failure' in r or any(row.get('passed') is False for row in r.get('suites',[])),receipt,v)
        validate_full(value,expected);settled(v,receipt);state['full_regression_verified']=True;publish(folder/'pipeline.json',state)
        receipt=v.launch([sys.executable,'-I',str(script),'package',*common],folder/'package-result.json',purpose='build');state['package_receipt']=receipt
        value=wait_file(folder/'package-result.json',proof,lambda r:r.get('completed') is True,receipt,v);require(value.get('all_packaged') is True,'packaging failed; no artifact success');settled(v,receipt)
        state['artifacts']=[upload(bucket,'results/final/'+scope+'/'+name,folder/name,folder) for name in ['proof.tar.gz','missing-from-base.nix-export.gz','package-result.json','full-tests.json']]
        state['all_artifacts_uploaded_and_read_back']=True;state['all_requested_phase_passed']=True
        publish(folder/'pipeline.json',state)
        upload(bucket,'results/final/'+scope+'/pipeline.json',folder/'pipeline.json',folder)
    except Exception as error:
        state['all_requested_phase_passed']=False
        state['error_type']=type(error).__name__;state['error']=str(error)
        raise
    finally:
        publish(folder/'pipeline.json',state)
        # Even failed runs retain their exact outputs independently of an
        # operator. Do not infer success from this last upload or unit exit.
        for p in folder.iterdir():
            if p.is_file() and p.suffix in {'.json','.log','.stderr'}:
                try:upload(bucket,'results/pipeline/'+folder.name+'/'+p.name,p,folder)
                except Exception:pass  # native expiry still bounds the canary; never mark upload success
        (folder/'.finished').touch(mode=0o600,exist_ok=False)
        print(json.dumps(state),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=['run','build','package','watch']);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--authority',type=Path,required=True);parser.add_argument('--folder',type=Path);args=parser.parse_args()
    require(sys.platform=='linux' and os.geteuid()==0,'root Linux required; no skip or production fallback')
    os.environ['NIX_REMOTE']='local'  # legacy nix-store export/query must not escape the resource cage via a daemon
    if args.stage!='run':
        require(args.folder is not None and args.folder.parent==Path('/home/persist/root') and re.fullmatch('pipeline-[0-9a-f]{32}',args.folder.name)
                and args.folder.is_dir() and not args.folder.is_symlink() and args.folder.stat().st_uid==0 and not args.folder.stat().st_mode&0o077,'unknown stage workspace')
    source,expected,v,proof=load_source(args.source,args.authority,args.stage,args.folder)
    if args.stage=='run':orchestrate(source,args.authority,v,proof,expected)
    elif args.stage=='watch':
        require(v.current() is None,'observer cannot escape another cage');watch(args.folder,proof)
    else:
        {'build':build,'package':package}[args.stage](source,args.folder,v,expected)


if __name__=='__main__':main()
