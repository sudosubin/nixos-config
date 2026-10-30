#!/usr/bin/env python3
"""Read-only ASG protection/deployment diagnosis, never idle/arming authority.

Run from standard-role CloudShell or any AWS CLI host; no resident Mac process.
Does NOT run the guard, initialize leases, release protection, change IAM,
reload/restart services, snapshot disks, or publish readiness/approval flags.
Only SendCommand (once) starts a bounded private-network metadata reader.
"""
import argparse
import base64
from datetime import datetime,timezone
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import time

spec=importlib.util.spec_from_file_location('audit_controller',Path(__file__).with_name('spot-canary-controller.py'));c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

COLLECTOR=r'''from pathlib import Path
import json,subprocess,hashlib,os,time,base64,gzip
units={}
for name in ['spot-schedule-guard.service','spot-schedule-guard.timer','spot-scale-in-protection-ready.service','spot-work-admission-ready.service','spot-workload-startup-ready.service']:
 p=subprocess.run(['systemctl','show',name,'-p','LoadState','-p','ActiveState','-p','UnitFileState','-p','FragmentPath','-p','MainPID'],capture_output=True,text=True,timeout=10)
 units[name]={'probe_ok':p.returncode==0,'properties':dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)}
files={};allowed={'armed','asg','asg_arn','home_volume','home_uuid','manifest','durable_journal','profile_cache_manifest','schema','state','phase','reasons','system','user_profile','boot_id','instance_id','updated_at','replacement_verified','closure_restore_verified','work_tracking_verified','backup_restore_verified','production_armed','termination_armed','runtime_units_reboot_persistent','runtime_atomic_seal_installed','runtime_cold_guard_installed','full_work_tracking_verified','all_producer_fencing_verified','cold_raw_privileged_write_fencing_verified','production_backup_IAM_installed','production_cold_backup_rollout_verified','production_daily_retention_enabled','home_live_sync_complete','home_migration_complete','production_cutover_complete'}
for name in ['/etc/spot-schedule-guard.json','/run/spot-schedule-guard/status.json','/run/spot-schedule-guard/startup','/run/spot-work/state.json','/home/persist/manifests/active.json','/home/persist/manifests/profile-cache.json','/home/persist/manifests/deployment-status.json']:
 p=Path(name);row={'exists':p.exists()}
 if p.is_file() and p.stat().st_size<=1048576:
  data=p.read_bytes();row['sha256']=hashlib.sha256(data).hexdigest()
  try:
   obj=json.loads(data);row['fields']={k:v for k,v in obj.items() if k in allowed};row['mtime']=p.stat().st_mtime
  except (ValueError,AttributeError):row['malformed']=True
 files[name]=row
processes=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  comm=(p/'comm').read_text().strip()
  if comm in {'herdr','kiro-cli','kiro-cli-chat','bun','node','nix','nix-build','cargo','rustc','java'}:processes.append({'pid':int(p.name),'comm':comm,'uid':p.stat().st_uid})
 except OSError:pass
value={'schema':1,'observed_at':time.time(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'current_system':str(Path('/run/current-system').resolve()),'profile':str(Path('/nix/var/nix/profiles/system').resolve()),'units':units,'files':files,'guard_binary_exists':Path('/run/current-system/sw/bin/spot-schedule-guard').exists(),'work_binary_exists':Path('/run/current-system/sw/bin/spot-work').exists(),'named_process_observations_NOT_busy_or_idle_proof':processes,'not_idle_or_arming_authority':True};data=json.dumps(value).encode();print(json.dumps({'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'gzip':base64.b64encode(gzip.compress(data)).decode()}))
'''


def fields(runtime,path):
    row=runtime.get('files',{}).get(path,{})
    return row.get('fields',{}) if row.get('exists') is True and row.get('malformed') is not True else {}


def unit(runtime,name):return runtime.get('units',{}).get(name,{})


def signature(group):
    return (group.get('AutoScalingGroupARN'),group.get('DesiredCapacity'),group.get('NewInstancesProtectedFromScaleIn'),sorted((i.get('InstanceId'),i.get('ProtectedFromScaleIn'),i.get('LifecycleState')) for i in group.get('Instances',[])))


def diagnose(group,runtime,instance,*,now=None,after=None):
    now=time.time() if now is None else now;members=[i for i in group.get('Instances',[]) if i.get('InstanceId')==instance];service=unit(runtime,'spot-schedule-guard.service');timer=unit(runtime,'spot-schedule-guard.timer');config=fields(runtime,'/etc/spot-schedule-guard.json');status=fields(runtime,'/run/spot-schedule-guard/status.json');manifest=fields(runtime,'/home/persist/manifests/active.json');cache=fields(runtime,'/home/persist/manifests/profile-cache.json');issues=[]
    fresh=type(runtime.get('observed_at')) in {int,float} and 0<=now-runtime['observed_at']<=180
    known=all(u.get('probe_ok') is True and u.get('properties',{}).get('LoadState') in {'loaded','not-found','masked','error','bad-setting'} for u in [service,timer]) and type(runtime.get('guard_binary_exists')) is bool
    controller_loaded=known and all(u['properties']['LoadState']=='loaded' for u in [service,timer]) and runtime['guard_binary_exists'] is True
    if not fresh:issues.append('runtime_observation_stale_or_unknown')
    if after is not None and signature(group)!=signature(after):issues.append('ASG_changed_during_collection')
    if len(members)!=1 or type(members[0].get('ProtectedFromScaleIn')) is not bool:classification='membership_or_protection_unknown'
    elif not fresh or not known or issues:classification='observation_unknown'
    elif members[0]['ProtectedFromScaleIn'] is False:classification='not_scale_in_protected'
    elif not controller_loaded:classification='protected_without_deployed_guard'
    elif timer['properties'].get('ActiveState')!='active':classification='protected_guard_timer_inactive'
    elif config.get('armed') is not True:classification='protected_observation_mode'
    else:classification='protected_guard_reasons_require_current_custody'
    if config.get('armed') is not True:issues.append('termination_not_explicitly_armed')
    if not config.get('durable_journal') or not config.get('asg_arn'):issues.append('durable_journal_or_exact_ASG_ARN_unconfigured')
    if not runtime.get('files',{}).get('/run/spot-work/state.json',{}).get('exists'):issues.append('current_work_custody_unknown')
    if not manifest:issues.append('current_arming_manifest_missing_or_unknown')
    for key in ['replacement_verified','closure_restore_verified','work_tracking_verified','backup_restore_verified']:
        if manifest.get(key) is not True:issues.append('arming_prerequisite_unverified:'+key)
    if not runtime.get('boot_id') or manifest.get('boot_id')!=runtime['boot_id'] or manifest.get('instance_id')!=instance:issues.append('arming_epoch_not_current')
    if config.get('asg')!=group.get('AutoScalingGroupName'):issues.append('configuration_ASG_unknown_or_mismatched')
    if cache.get('schema')!=2:issues.append('production_profile_cache_not_schema2')
    return {'classification':classification,'ASG_desired_capacity':group.get('DesiredCapacity'),'ASG_new_members_default_protected':group.get('NewInstancesProtectedFromScaleIn'),'instance':instance,'scale_in_protected':members[0].get('ProtectedFromScaleIn') if len(members)==1 else None,'guard_deployment_observation_known':known,'guard_service_and_timer_and_binary_loaded':controller_loaded if known else None,'configured_armed':config.get('armed'),'actual_guard_status_observation':status or None,'runtime_busy_reason':None,'runtime_busy_reason_explanation':'Named process presence/absence is NOT accepted-work or idle proof; missing controller/status is not a busy-work decision.','deployment_and_safety_gaps':issues,'auto_unprotect_recommended':False,'authority':'diagnosis-only; never a termination/idle/arming approval'}


def decode(reply):
    if '--output truncated--' in reply:raise RuntimeError('SSM output truncated; no diagnosis may be accepted')
    envelope=json.loads(reply)
    with gzip.GzipFile(fileobj=io.BytesIO(base64.b64decode(envelope['gzip'],validate=True))) as stream:data=stream.read(1048577)
    c.require(len(data)==envelope['bytes'] and len(data)<=1048576 and hashlib.sha256(data).hexdigest()==envelope['sha256'],'runtime audit body mismatch');value=json.loads(data);c.require(isinstance(value,dict) and type(value.get('schema')) is int and value['schema']==1,'unsupported audit runtime schema');return value


def audit(api,asg,instance):
    api.account();groups=api('autoscaling','describe-auto-scaling-groups','--auto-scaling-group-names',asg)['AutoScalingGroups'];c.require(len(groups)==1 and groups[0]['AutoScalingGroupName']==asg,'ASG identity unknown');before=groups[0]
    # No mutation replay on an unknown SendCommand acceptance.
    reply=api('ssm','send-command','--document-name','AWS-RunShellScript','--instance-ids',instance,'--comment','readonly-scale-in-protection-versus-missing-guard-audit','--timeout-seconds','180','--parameters',json.dumps({'commands':[c.shell(COLLECTOR)],'executionTimeout':['180']}));ident=reply['Command']['CommandId'];end=time.monotonic()+180
    while time.monotonic()<end:
        try:response=api('ssm','get-command-invocation','--command-id',ident,'--instance-id',instance)
        except RuntimeError as e:
            if 'InvocationDoesNotExist' not in str(e):raise
            time.sleep(2);continue
        if response['Status'] not in {'Pending','InProgress','Delayed'}:break
        time.sleep(2)
    else:raise RuntimeError('audit command outcome unknown; no replay: '+ident)
    c.require(response['Status']=='Success','audit reader failed; no diagnosis: '+ident);runtime=decode(response['StandardOutputContent']);after=api('autoscaling','describe-auto-scaling-groups','--auto-scaling-group-names',asg)['AutoScalingGroups'];c.require(len(after)==1,'ASG disappeared during audit')
    return {'observed_at':datetime.now(timezone.utc).isoformat(),'command_id':ident,'AWS_group_before':before,'AWS_group_after':after[0],'runtime':runtime,'diagnosis':diagnose(before,runtime,instance,after=after[0]),'recent_ASG_activities':api('autoscaling','describe-scaling-activities','--auto-scaling-group-name',asg,'--max-records','20','--no-paginate')}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--asg',default='nixos-ec2-asg');parser.add_argument('--instance',default=c.b.PRODUCTION);parser.add_argument('--profile');parser.add_argument('--output',type=Path);args=parser.parse_args();os.environ['AWS_MAX_ATTEMPTS']='1';result=audit(c.b.API(args.profile),args.asg,args.instance)
    if args.output:
        fd=os.open(args.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as out:json.dump(result,out,indent=2);out.flush();os.fsync(out.fileno())
    print(json.dumps(result['diagnosis'],indent=2))


if __name__=='__main__':main()
