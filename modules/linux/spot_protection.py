"""Read-only protection diagnosis shared by operator audit and resident observer.

No leases, guard invocation, AWS mutations, initialization or idle authority.
"""
import base64
from contextlib import redirect_stdout
import gzip
import hashlib
import io
import json
import time


def require(ok,message):
    if not ok:raise RuntimeError(message)


COLLECTOR=r'''from pathlib import Path
import json,subprocess,hashlib,os,time,base64,gzip,stat,re
units={}
def show(name):
 p=subprocess.run(['systemctl','show',name,'-p','LoadState','-p','ActiveState','-p','UnitFileState','-p','FragmentPath','-p','MainPID'],capture_output=True,text=True,timeout=10)
 return {'probe_ok':p.returncode==0,'properties':dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)}
for name in ['spot-schedule-guard.service','spot-schedule-guard.timer','spot-scale-in-protection-ready.service','spot-work-admission-ready.service','spot-workload-startup-ready.service']:units[name]=show(name)
files={};allowed={'armed','asg','asg_arn','home_volume','home_uuid','manifest','durable_journal','profile_cache_manifest','schema','state','phase','reasons','system','user_profile','boot_id','instance_id','updated_at','replacement_verified','closure_restore_verified','work_tracking_verified','backup_restore_verified','production_armed','termination_armed','runtime_units_reboot_persistent','runtime_atomic_seal_installed','runtime_cold_guard_installed','full_work_tracking_verified','all_producer_fencing_verified','cold_raw_privileged_write_fencing_verified','production_backup_IAM_installed','production_cold_backup_rollout_verified','production_daily_retention_enabled','home_live_sync_complete','home_migration_complete','production_cutover_complete'}
for name in ['/etc/spot-schedule-guard.json','/run/spot-schedule-guard/status.json','/run/spot-schedule-guard/startup','/run/spot-schedule-guard/draining','/home/persist/manifests/active.json','/home/persist/manifests/profile-cache.json','/home/persist/manifests/deployment-status.json']:
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
metadata={}
for name,kind,mode in [('admission.lock','file',0o660),('leases','directory',0o1733),('participants','directory',0o1733)]:
 p=Path('/run/spot-schedule-guard')/name;row={'exists':p.exists(),'trusted':False}
 try:
  st=p.lstat();row['trusted']=not p.is_symlink() and st.st_uid==0 and stat.S_IMODE(st.st_mode)==mode and (stat.S_ISREG(st.st_mode) if kind=='file' else stat.S_ISDIR(st.st_mode))
 except OSError:pass
 metadata[name]=row
root=Path('/run/spot-schedule-guard');metadata['runtime']={'trusted':False}
try:
 st=root.lstat();metadata['runtime']['trusted']=stat.S_ISDIR(st.st_mode) and st.st_uid==0 and not st.st_mode&0o022
except OSError:pass
observer={'present':False,'trusted':False};marker=Path('/etc/spot-protection-observer-current.json')
try:
 st=marker.stat();assert st.st_uid==0 and not st.st_mode&0o022 and st.st_size<=16384
 spec=json.loads(marker.read_text());identifier=spec['deployment_id'];assert re.fullmatch('[0-9a-f]{12}',identifier)
 service='spot-protection-observer-'+identifier+'.service';timer='spot-protection-observer-'+identifier+'.timer';path=Path('/var/lib/spot-protection-observer')/identifier/'status.json';assert spec['observer_unit']==service and spec['observer_timer']==timer and spec['status_path']==str(path) and spec['observation_only'] is True and spec['termination_capable'] is False
 observer={'present':True,'trusted':True,'deployment_id':identifier,'service':show(service),'timer':show(timer),'status':None}
 if path.is_file():
  st=path.lstat();assert not path.is_symlink() and st.st_uid==0 and not st.st_mode&0o077 and st.st_size<=1048576
  data=json.loads(path.read_text());observer['status']={k:data[k] for k in ['observed_at','boot_id','instance','classification','termination_capable'] if k in data}
except (OSError,ValueError,KeyError,AssertionError):pass
value={'schema':1,'observed_at':time.time(),'protocol_metadata':metadata,'observer':observer,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'current_system':str(Path('/run/current-system').resolve()),'profile':str(Path('/nix/var/nix/profiles/system').resolve()),'units':units,'files':files,'guard_binary_exists':Path('/run/current-system/sw/bin/spot-schedule-guard').exists(),'work_binary_exists':Path('/run/current-system/sw/bin/spot-work').exists(),'named_process_observations_NOT_busy_or_idle_proof':processes,'not_idle_or_arming_authority':True};data=json.dumps(value).encode();print(json.dumps({'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'gzip':base64.b64encode(gzip.compress(data)).decode()}))
'''


def decode(reply):
    if '--output truncated--' in reply:raise RuntimeError('SSM output truncated; no diagnosis may be accepted')
    envelope=json.loads(reply)
    with gzip.GzipFile(fileobj=io.BytesIO(base64.b64decode(envelope['gzip'],validate=True))) as stream:data=stream.read(1048577)
    require(len(data)==envelope['bytes'] and len(data)<=1048576 and hashlib.sha256(data).hexdigest()==envelope['sha256'],'runtime audit body mismatch');value=json.loads(data);require(isinstance(value,dict) and type(value.get('schema')) is int and value['schema']==1,'unsupported audit runtime schema');return value


def collect():
    output=io.StringIO()
    with redirect_stdout(output):exec(COLLECTOR,{})
    return decode(output.getvalue())


def fields(runtime,path):
    row=runtime.get('files',{}).get(path,{})
    return row.get('fields',{}) if row.get('exists') is True and row.get('malformed') is not True else {}


def unit(runtime,name):return runtime.get('units',{}).get(name,{})


def signature(group):
    return (group.get('AutoScalingGroupARN'),group.get('DesiredCapacity'),group.get('NewInstancesProtectedFromScaleIn'),sorted((i.get('InstanceId'),i.get('ProtectedFromScaleIn'),i.get('LifecycleState')) for i in group.get('Instances',[])))


def observer_current(runtime,instance,now):
    o=runtime.get('observer',{});s=o.get('status') or {};stamp=s.get('observed_at')
    return (o.get('trusted') is True and type(stamp) in {int,float} and 0<=now-stamp<=900 and s.get('boot_id')==runtime.get('boot_id') and s.get('instance')==instance and s.get('termination_capable') is False and all(o.get(n,{}).get('properties',{}).get('LoadState')=='loaded' for n in ['service','timer']) and o['timer']['properties'].get('ActiveState')=='active')


def diagnose(group,runtime,instance,*,now=None,after=None):
    now=time.time() if now is None else now;members=[i for i in group.get('Instances',[]) if i.get('InstanceId')==instance];service=unit(runtime,'spot-schedule-guard.service');timer=unit(runtime,'spot-schedule-guard.timer');config=fields(runtime,'/etc/spot-schedule-guard.json');status=fields(runtime,'/run/spot-schedule-guard/status.json');manifest=fields(runtime,'/home/persist/manifests/active.json');cache=fields(runtime,'/home/persist/manifests/profile-cache.json');issues=[]
    fresh=type(runtime.get('observed_at')) in {int,float} and 0<=now-runtime['observed_at']<=180
    known=all(u.get('probe_ok') is True and u.get('properties',{}).get('LoadState') in {'loaded','not-found','masked','error','bad-setting'} for u in [service,timer]) and type(runtime.get('guard_binary_exists')) is bool
    controller_loaded=known and all(u['properties']['LoadState']=='loaded' for u in [service,timer]) and runtime['guard_binary_exists'] is True
    if not fresh:issues.append('runtime_observation_stale_or_unknown')
    if after is not None and signature(group)!=signature(after):issues.append('ASG_changed_during_collection')
    observing=observer_current(runtime,instance,now)
    if len(members)!=1 or type(members[0].get('ProtectedFromScaleIn')) is not bool:classification='membership_or_protection_unknown'
    elif not fresh or not known or issues:classification='observation_unknown'
    elif members[0]['ProtectedFromScaleIn'] is False:classification='not_scale_in_protected'
    elif not controller_loaded:classification='protected_observer_only_guard_not_armed' if observing else 'protected_without_deployed_guard'
    elif timer['properties'].get('ActiveState')!='active':classification='protected_guard_timer_inactive'
    elif config.get('armed') is not True:classification='protected_observation_mode'
    else:classification='protected_guard_reasons_require_current_custody'
    if config.get('armed') is not True:issues.append('termination_not_explicitly_armed')
    if not config.get('durable_journal') or not config.get('asg_arn'):issues.append('durable_journal_or_exact_ASG_ARN_unconfigured')
    startup=fields(runtime,'/run/spot-schedule-guard/startup');metadata=runtime.get('protocol_metadata',{})
    if (startup.get('boot_id')!=runtime.get('boot_id') or not runtime.get('boot_id') or startup.get('state') not in {'starting','ready'} or not all(metadata.get(name,{}).get('trusted') is True for name in ['runtime','admission.lock','leases','participants'])):issues.append('current_work_custody_unknown')
    if not manifest:issues.append('current_arming_manifest_missing_or_unknown')
    for key in ['replacement_verified','closure_restore_verified','work_tracking_verified','backup_restore_verified']:
        if manifest.get(key) is not True:issues.append('arming_prerequisite_unverified:'+key)
    if not runtime.get('boot_id') or manifest.get('boot_id')!=runtime['boot_id'] or manifest.get('instance_id')!=instance:issues.append('arming_epoch_not_current')
    if config.get('asg')!=group.get('AutoScalingGroupName'):issues.append('configuration_ASG_unknown_or_mismatched')
    if cache.get('schema')!=2:issues.append('production_profile_cache_not_schema2')
    return {'classification':classification,'ASG_desired_capacity':group.get('DesiredCapacity'),'ASG_new_members_default_protected':group.get('NewInstancesProtectedFromScaleIn'),'instance':instance,'scale_in_protected':members[0].get('ProtectedFromScaleIn') if len(members)==1 else None,'read_only_observer_current':observing,'guard_deployment_observation_known':known,'guard_service_and_timer_and_binary_loaded':controller_loaded if known else None,'configured_armed':config.get('armed'),'actual_guard_status_observation':status or None,'runtime_busy_reason':None,'runtime_busy_reason_explanation':'Named process presence/absence is NOT accepted-work or idle proof; missing controller/status is not a busy-work decision.','deployment_and_safety_gaps':issues,'auto_unprotect_recommended':False,'authority':'diagnosis-only; never a termination/idle/arming approval'}
