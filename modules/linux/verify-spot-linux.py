#!/usr/bin/env python3
"""Cloud-only ARM regression driver, not an installer or idle/arming authority.

Requires a hash-pinned source tree and an already BUILT system. Runs unit tests
and isolated real Linux/vendor/private-Nix canaries; persists complete output.
Never switches a system/profile/image, controls the production app, or changes
AWS resources. Mock/model-free tests are not provider/OS-boot/rollout evidence.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
import time


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--prepared',type=Path,required=True)
    parser.add_argument('--expected-source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if sys.platform!='linux' or platform.machine() not in ('aarch64','arm64') or os.geteuid()!=0:
        raise RuntimeError('root ARM Linux required; no skip-as-proof')
    root=args.source.resolve(strict=True);prepared=args.prepared.resolve(strict=True)
    if not re.fullmatch(r'/nix/store/[0-9a-df-np-sv-z]{32}-nixos-system-[^/]+',str(prepared)):
        raise RuntimeError('prepared target is not an immutable NixOS build')
    fd=os.open(args.expected_source,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd) as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=0 or info.st_mode&0o022 or info.st_size>1048576:
            raise RuntimeError('source-hash authority is not root-owned and trusted')
        expected=json.load(stream)
    if not isinstance(expected,dict) or not expected:raise RuntimeError('empty expected source')
    for name,value in expected.items():
        p=Path(name)
        if (not isinstance(value,str) or not re.fullmatch(r'[0-9a-f]{64}',value) or p.is_absolute()
                or '..' in p.parts or not (root/p).is_file()):raise RuntimeError('invalid source identity')
    if 'modules/linux/verify-spot-linux.py' not in expected:raise RuntimeError('driver absent from source authority')
    actual={name:sha(root/name) for name in expected}
    if actual!=expected:raise RuntimeError('canonical source bytes changed')
    if Path(__file__).read_bytes()!=(root/'modules/linux/verify-spot-linux.py').read_bytes():
        raise RuntimeError('executed verification driver is not the pinned source')
    os.environ['PATH']='/run/current-system/sw/bin'
    requirements=subprocess.run(['nix-store','--query','--requisites',str(prepared)],check=True,capture_output=True,text=True).stdout.splitlines()
    guard_config=json.loads((prepared/'etc/spot-schedule-guard.json').read_text())
    cache_config=json.loads((prepared/'etc/spot-profile-cache.json').read_text())
    if (guard_config.get('armed') is not False or guard_config.get('profile_cache_config')!='/etc/spot-profile-cache.json'
            or cache_config.get('home_uuid')!=guard_config.get('home_uuid')
            or cache_config.get('keep_checkpoints')!=2 or cache_config.get('prune_grace_seconds')!=86400):
        raise RuntimeError('prepared guard/cache configuration is not the disarmed, identity-bound policy')
    compiled={}
    sources=[('-spot-schedule-sources',['spot-schedule-guard.py','spot_work.py','spot_gateway.py','spot-gateway-rpc.mjs',
                                      'spot_backup.py','spot_drain.py','spot_cold.py','spot-profile-cache.py','spot_cache.py']),
             ('-spot-acp-sources',['spot_acp.py','spot_work.py','spot_frontend.py']),
             ('-spot-profile-cache-sources',['spot-profile-cache.py','spot_cache.py'])]
    for suffix,names in sources:
        directories=[Path(x) for x in requirements if x.endswith(suffix)]
        if len(directories)!=1:raise RuntimeError('ambiguous immutable source directory: '+suffix)
        for name in names:
            path=directories[0]/name
            if path.read_bytes()!=(root/'modules/linux'/name).read_bytes():raise RuntimeError('compiled source differs: '+name)
            compiled[str(path)]=sha(path)
    for suffix,name in [('-spot_work.py','spot_work.py'),('-spot-kiro-frontend.mjs','spot-kiro-frontend.mjs')]:
        paths=[Path(x) for x in requirements if x.endswith(suffix)]
        if len(paths)!=1 or paths[0].read_bytes()!=(root/'modules/linux'/name).read_bytes():
            raise RuntimeError('immutable direct module differs: '+name)
        compiled[str(paths[0])]=sha(paths[0])
    if len(compiled)!=16:raise RuntimeError('not all sixteen immutable module copies were verified')
    openssl=[Path(x)/'bin/openssl' for x in requirements if (Path(x)/'bin/openssl').is_file()]
    if not openssl:raise RuntimeError('compiled OpenSSL runtime missing; signature tests cannot skip')
    os.environ['PATH']=':'.join(sorted({str(p.parent) for p in openssl}))+':/run/current-system/sw/bin'
    launcher=(prepared/'sw/bin/spot-work').resolve(strict=True)
    if not launcher.read_text().splitlines()[0].endswith('/bin/python3 -I'):
        raise RuntimeError('generic CLI must start directly in isolated Python, without shell/env startup hooks')
    launchers={str(launcher):sha(launcher)}
    state={'schema':1,'timestamp':time.time(),'prepared_system':str(prepared),'source_root':str(root),
           'source_sha256':actual,'compiled_source_sha256':compiled,'compiled_launcher_sha256':launchers,'suites':[],'executed':0,'unit_cases':0,
           'root_linux_cases':0,'all_passed':False,'production_armed':False,'full_work_tracking_verified':False,
           'production_rollout':False,'OS_boot_verified':False,'prepared_guard_armed_false_verified':True,
           'scope':'generic job uncertain-spawn/bound-retirement/all-child waits and configured-profile cache plus previous isolated regressions; '
                   'NOT all producers, real provider/crash output, raw-I/O fencing, boot, migration or actual shutdown/wake'}
    def save():
        tmp=args.output.with_suffix('.tmp')
        fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'w') as stream:
            json.dump(state,stream,indent=2);stream.flush();os.fsync(stream.fileno())
        os.replace(tmp,args.output)
        fd=os.open(args.output.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    base=[('work',59),('schedule-guard',82),('profile-cache',29),('cache',52),('acp',43),('gateway',28),('backup',33),
          ('drain',29),('gateway-recovery',19),('cold',17),('frontend',20),('work-linux',12),('acp-linux',9),
          ('gateway-linux',7),('cold-linux',8)]
    commands=[(name,count,[sys.executable,'-W','error::ResourceWarning',str(root/'modules/linux'/('test-spot-'+name+'.py')),'-v']) for name,count in base]
    for name,count,command in commands:
        if name=='work-linux':command.extend(['--tool',str(prepared/'sw/bin/spot-work')])
    commands.append(('cache-linux',9,[sys.executable,'-W','error::ResourceWarning',str(root/'modules/linux/test-spot-cache-linux.py')]))
    native=['--frontend','/nix/store/bn6yjl0rgrd0yqxk3cbkkamjcxg9h47x-kiro-cli-2.10.0/bin/kiro-cli',
            '--backend','/nix/store/bn6yjl0rgrd0yqxk3cbkkamjcxg9h47x-kiro-cli-2.10.0/bin/kiro-cli-chat',
            '--bun','/home/sudosubin/.local/share/kiro-cli/bun','--tui','/home/sudosubin/.local/share/kiro-cli/tui.js',
            '--proxy',str(prepared/'sw/bin/spot-acp-proxy'),'--launcher',str(prepared/'sw/bin/spot-kiro')]
    commands.append(('native-kiro-linux',8,[sys.executable,'-W','error::ResourceWarning',str(root/'modules/linux/verify-spot-kiro-native.py'),*native]))
    commands.append(('frontend-JS',15,['/home/sudosubin/.local/share/openclaw-npm/node-v26.4.0-linux-arm64/bin/node',
                                     '--test','--test-reporter=tap',str(root/'modules/linux/test-spot-kiro-frontend.mjs')]))
    entries=[x for x in requirements if x.endswith('-spot-kiro-entry.mjs')]
    if len(entries)!=1:raise RuntimeError('native entry identity ambiguous')
    commands.append(('native-frontend-linux',3,[sys.executable,'-W','error::ResourceWarning',str(root/'modules/linux/verify-spot-kiro-frontend.py'),
                    *native,'--fronttool',str(prepared/'sw/bin/spot-kiro-front'),'--entry',entries[0]]))
    save()
    for name,count,command in commands:
        for argument in command:
            path=Path(argument)
            if path.is_absolute() and path.is_relative_to(root) and path.suffix in ('.py','.mjs'):
                relative=str(path.relative_to(root))
                if relative not in expected or sha(path)!=expected[relative]:raise RuntimeError('executed test source is not pinned')
        result=subprocess.run(command,capture_output=True,text=True,
                              env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONWARNINGS':'error::ResourceWarning'})
        counts=re.findall(r'^# tests (\d+)$',result.stdout,re.M) if name=='frontend-JS' else re.findall(r'^Ran (\d+) tests? in ',result.stderr,re.M)
        executed=int(counts[0]) if len(counts)==1 else -1
        clean='skipped' not in result.stderr and 'ResourceWarning' not in result.stderr
        success=all(token in result.stdout for token in ['# fail 0','# skipped 0','# cancelled 0','# todo 0']) if name=='frontend-JS' else '\nOK\n' in result.stderr
        passed=result.returncode==0 and executed==count and clean and success
        row={'suite':name,'command':command,'expected':count,'executed':executed,'returncode':result.returncode,
             'stdout':result.stdout,'stderr':result.stderr,'no_skips_or_resource_warnings':clean,'passed':passed}
        if name in ('native-kiro-linux','cache-linux','work-linux'):
            scope=json.loads(result.stdout.strip().splitlines()[-1]);row['scope']=scope
            passed=passed and scope['skipped']==0 and scope['failures']==0 and scope['errors']==0
            passed=passed and scope['native_integration_cases' if name=='native-kiro-linux' else 'tests']==count
            row['passed']=passed
        state['suites'].append(row);state['executed']+=max(0,executed)
        state['root_linux_cases' if name.endswith('-linux') else 'unit_cases']+=max(0,executed)
        save();print(json.dumps({'suite':name,'executed':executed,'passed':passed}),flush=True)
        if not passed:raise RuntimeError('suite failed; COMPLETE stdout/stderr preserved: '+name)
    if (state['executed'],state['unit_cases'],state['root_linux_cases'])!=(482,426,56):
        raise RuntimeError('executed counts do not match the complete scope')
    if {name:sha(root/name) for name in expected}!=actual:raise RuntimeError('source changed during verification')
    for name,value in compiled.items():
        if sha(Path(name))!=value:raise RuntimeError('immutable source changed during verification')
    for name,value in launchers.items():
        if sha(Path(name))!=value:raise RuntimeError('immutable launcher changed during verification')
    state['all_passed']=True;state['finished_at']=time.time();save()
    print(json.dumps({k:v for k,v in state.items() if k not in ['suites','source_sha256','compiled_source_sha256']}),flush=True)


if __name__=='__main__':main()
