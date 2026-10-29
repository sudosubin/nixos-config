#!/usr/bin/env python3
"""Native-expiring EMPTY image volume and NON-ACTIVATED production LT candidate.

No production ASG update, original reboot/protection release, force detach,
snapshot success inference, or guest permission to provision/terminate anything.
"""
import argparse
from datetime import datetime,timedelta,timezone
import hashlib
import importlib.util
import json
import math
import os
import re
from pathlib import Path
import tempfile
import time

s=importlib.util.spec_from_file_location('controller',Path(__file__).with_name('spot-canary-controller.py'));c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
b=c.b
require=c.require
PROTECTED={'vol-065729ef75553a7ec','vol-09fea2ff4615b1088','vol-0b529abe51df1eca1'}


def root_plan(state,now=None):
    now=now or datetime.now(timezone.utc);deadline=datetime.fromisoformat(state['expires'])+timedelta(minutes=10);seconds=math.ceil((deadline-now).total_seconds());require(900<seconds<=7800,'image-root native window exhausted/unbounded')
    name='nixos-image-root-'+state['scope'];tags=[{'Key':k,'Value':v} for k,v in {'ManagedBy':'nixos-spot-validation','Purpose':'image-root','ScopeId':state['scope'],'Disposable':'true','DisposableUntil':deadline.isoformat()}.items()]
    base='arn:aws:ec2:'+b.REGION+':'+b.ACCOUNT+':volume/*';policy={'Version':'2012-10-17','Statement':[
        {'Effect':'Allow','Action':'ec2:DescribeVolumes','Resource':'*','Condition':{'StringEquals':{'aws:RequestedRegion':b.REGION}}},
        {'Effect':'Allow','Action':'ec2:CreateVolume','Resource':base,'Condition':{'StringEquals':{'aws:RequestedRegion':b.REGION,'aws:RequestTag/ScopeId':state['scope'],'aws:RequestTag/Purpose':'image-root','ec2:VolumeType':'gp3','ec2:AvailabilityZone':'ap-northeast-2d'},'Bool':{'ec2:Encrypted':'true'},'NumericEquals':{'ec2:VolumeSize':32}}},
        {'Effect':'Allow','Action':'ec2:CreateTags','Resource':base,'Condition':{'StringEquals':{'aws:RequestTag/ScopeId':state['scope'],'ec2:CreateAction':'CreateVolume'}}},
        {'Effect':'Allow','Action':'ec2:DeleteVolume','Resource':base,'Condition':{'StringEquals':{'ec2:ResourceTag/ScopeId':state['scope'],'ec2:ResourceTag/Purpose':'image-root'}}},
        {'Effect':'Deny','Action':['ec2:DeleteVolume','ec2:AttachVolume','ec2:DetachVolume'],'Resource':['arn:aws:ec2:'+b.REGION+':'+b.ACCOUNT+':volume/'+v for v in sorted(PROTECTED)]},
        {'Effect':'Deny','Action':['ec2:AttachVolume','ec2:DetachVolume','ec2:CreateSnapshot','ec2:DeleteSnapshot','ec2:AssociateAddress','ec2:DisassociateAddress','ec2:TerminateInstances','cloudformation:SignalResource','iam:PassRole'],'Resource':'*'}]}
    template={'AWSTemplateFormatVersion':'2010-09-09','Description':'Fresh empty encrypted32GiB image root; independent unsignalled native rollback, never forced detach',
              'Metadata':{'scope':state['scope'],'expected_native_timeout':deadline.isoformat(),'compute_expires':state['expires'],'not_strict_wall_clock_or_production_authority':True,'policy':policy},
              'Resources':{'ImageRoot':{'Type':'AWS::EC2::Volume','DeletionPolicy':'Delete','UpdateReplacePolicy':'Delete','Properties':{'AvailabilityZone':'ap-northeast-2d','Size':32,'VolumeType':'gp3','Encrypted':True,'Tags':tags}},
                           'Deadline':{'Type':'AWS::CloudFormation::WaitCondition','DependsOn':'ImageRoot','CreationPolicy':{'ResourceSignal':{'Count':1,'Timeout':'PT'+str(seconds)+'S'}}}}}
    return {'scope':state['scope'],'name':name,'role':name+'-cfn','deadline':deadline.isoformat(),'timeout_minutes':math.ceil(seconds/60)+5,'policy':policy,'template':template,'tags':tags}


def immutable(api,state,key,value):
    with tempfile.TemporaryDirectory(prefix='image-control-') as d:
        path=Path(d)/'control';data=json.dumps(value,sort_keys=True,separators=(',',':')).encode();path.write_bytes(data);digest=hashlib.sha256(data).hexdigest()
        api('s3api','put-object','--bucket',state['bucket'],'--key',key,'--body',str(path),'--if-none-match','*','--checksum-algorithm','SHA256','--metadata','sha256='+digest,'--server-side-encryption','AES256')
        back=Path(d)/'readback';reply=api('s3api','get-object','--bucket',state['bucket'],'--key',key,str(back));require(back.read_bytes()==data and reply['Metadata']['sha256']==digest,'image control body differs')


def create_root(api,state,run):
    api.account();require(re.fullmatch('[0-9a-f]{32}',run),'exact retained artifact run required');receipt=c.read(api,state,'artifacts/retained-'+run+'.json');require(receipt.get('scope')==state['scope'] and receipt.get('artifact_run')==run and receipt.get('full_regression_executed')==618 and receipt.get('source_count',0)>=227 and receipt.get('opaque_delta_not_imported') is True,'complete independently retained build proof required')
    require(all(receipt.get(k) is False for k in ['production_rollout','OS_boot_verified','work_tracking_verified','armed','goal_complete']),'build receipt cannot arm/promote production')
    iid=receipt['instance'];require(iid!=b.PRODUCTION,'original forbidden');rows=api('ec2','describe-instances','--instance-ids',iid)['Reservations'];require(len(rows)==1 and rows[0]['OwnerId']==b.ACCOUNT and len(rows[0]['Instances'])==1,'unknown image builder');instance=rows[0]['Instances'][0]
    require(instance['InstanceLifecycle']=='spot' and instance['ImageId']==b.AMI and instance['State']['Name']=='running' and len(instance['BlockDeviceMappings'])==1 and instance['BlockDeviceMappings'][0]['Ebs']['DeleteOnTermination'] is True and instance['BlockDeviceMappings'][0]['Ebs']['VolumeId'] not in PROTECTED and {t['Key']:t['Value'] for t in instance['Tags']}.get('ScopeId')==state['scope'],'not empty single-root builder')
    prepared=c.read(api,state,'artifacts/autobootstrap-prepared-control');require(prepared['state']['source_revision']==state['source_revision'],'image builder source changed')
    group=api('autoscaling','describe-auto-scaling-groups','--auto-scaling-group-names',state['name'])['AutoScalingGroups'];require(len(group)==1 and group[0]['AutoScalingGroupARN']==prepared['state']['asg_arn'] and group[0]['NewInstancesProtectedFromScaleIn'] is False and group[0]['CapacityRebalance'] is False and len(group[0]['Instances'])==1 and group[0]['Instances'][0]['InstanceId']==iid and group[0]['Instances'][0]['ProtectedFromScaleIn'] is False and not group[0]['SuspendedProcesses'] and group[0]['MixedInstancesPolicy']['LaunchTemplate']['LaunchTemplateSpecification']['LaunchTemplateId']==state['LT'],'image builder lost unprotected native containment')
    actions=api('autoscaling','describe-scheduled-actions','--auto-scaling-group-name',state['name'])['ScheduledUpdateGroupActions'];require(len(actions)==1 and actions[0]['AutoScalingGroupName']==state['name'] and actions[0]['ScheduledActionName']==state['name']+'-off' and not actions[0].get('Recurrence') and datetime.fromisoformat(actions[0]['StartTime']).timestamp()==datetime.fromisoformat(state['expires']).timestamp() and all(type(actions[0].get(k)) is int and actions[0][k]==0 for k in ['MinSize','MaxSize','DesiredCapacity']),'image builder native off changed')
    require(datetime.fromisoformat(state['expires']).timestamp()-time.time()>900,'too little fixed lifetime for image installation')
    plan=root_plan(state);immutable(api,state,'control/image-root-intent.json',{'plan':plan,'build_receipt':receipt,'instance':iid,'volume_creation_not_success':True})
    trust={'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':'cloudformation.amazonaws.com'},'Action':'sts:AssumeRole'}]}
    role=api('iam','create-role','--role-name',plan['role'],'--assume-role-policy-document',json.dumps(trust),'--tags',json.dumps(plan['tags']))['Role'];api('iam','put-role-policy','--role-name',plan['role'],'--policy-name','OnlyThisBlankImageRoot','--policy-document',json.dumps(plan['policy']))
    require(api('iam','get-role-policy','--role-name',plan['role'],'--policy-name','OnlyThisBlankImageRoot')['PolicyDocument']==plan['policy'],'image role policy differs');time.sleep(10)
    # No blind retry of CreateStack/volume creation. A definite preacceptance
    # role-propagation rejection may be reconciled with the frozen intent/token.
    stack=api('cloudformation','create-stack','--stack-name',plan['name'],'--template-body',json.dumps(plan['template']),'--role-arn',role['Arn'],'--timeout-in-minutes',str(plan['timeout_minutes']),'--on-failure','ROLLBACK','--client-request-token',plan['name'],'--tags',json.dumps(plan['tags']))['StackId']
    end=time.monotonic()+120
    while time.monotonic()<end:
        resources=api('cloudformation','describe-stack-resources','--stack-name',stack)['StackResources'];volumes=[r for r in resources if r['LogicalResourceId']=='ImageRoot' and r['ResourceStatus']=='CREATE_COMPLETE'];waiting=[r for r in resources if r['LogicalResourceId']=='Deadline' and r['ResourceStatus']=='CREATE_IN_PROGRESS']
        if len(volumes)==len(waiting)==1:break
        time.sleep(2)
    else:raise RuntimeError('native image volume containment not observed; no attachment')
    vid=volumes[0]['PhysicalResourceId'];require(vid not in PROTECTED,'retained volume forbidden');actual=api('ec2','describe-volumes','--volume-ids',vid)['Volumes'];require(len(actual)==1 and actual[0]['Encrypted'] is True and actual[0]['Size']==32 and actual[0]['State']=='available' and not actual[0].get('SnapshotId') and not actual[0]['Attachments'] and {t['Key']:t['Value'] for t in actual[0]['Tags']}.get('ScopeId')==state['scope'],'not the fresh blank image volume')
    immutable(api,state,'control/image-root-attach-intent.json',{'volume':vid,'instance':iid,'stack':stack,'plan':plan});api('ec2','attach-volume','--volume-id',vid,'--instance-id',iid,'--device','/dev/sdf')
    value={'volume':vid,'instance':iid,'stack':stack,'role':plan['role'],'plan':plan,'build_receipt':receipt,'installed_snapshot_or_AMI_verified':False,'goal_complete':False};immutable(api,state,'control/image-root-created.json',value);return value


def register_image(api,state,snapshot,system):
    api.account();created=c.read(api,state,'control/image-root-created.json');capture=c.read(api,state,'control/image-snapshot-created.json');proof=capture['cold_verification'];require(capture['snapshot']==snapshot and capture['volume']==created['volume']==proof['target_volume'] and created['volume'] not in PROTECTED and proof['system']==system and proof['all_NAR_hashes_match'] is True and proof['verified_and_cold_FD_held'] is True and proof['source_closure_paths']>1000,'complete independent cold image authority required')
    snapshots=api('ec2','describe-snapshots','--snapshot-ids',snapshot)['Snapshots'];require(len(snapshots)==1,'snapshot ambiguous');snap=snapshots[0];tags={r['Key']:r['Value'] for r in snap.get('Tags',[])}
    require(snap['State']=='completed' and snap['VolumeId']==created['volume'] and snap['OwnerId']==b.ACCOUNT and snap['Encrypted'] is True and snap['VolumeSize']==32 and tags.get('ScopeId')==state['scope'] and tags.get('Purpose')=='image-candidate' and tags.get('Protected')=='true','not the completed own cold encrypted image snapshot')
    name='nixos-ec2-cloud-20261029-'+state['scope']+'-'+state['source_revision'][:12];mapping=[{'DeviceName':'/dev/xvda','Ebs':{'SnapshotId':snapshot,'VolumeSize':32,'VolumeType':'gp3','DeleteOnTermination':True}}];image_tags=[{'Key':k,'Value':v} for k,v in {'Name':name,'ManagedBy':'nixos-spot-validation','ScopeId':state['scope'],'DeploymentStage':'candidate','SourceRevision':state['source_revision'],'PreparedSystem':system,'ProductionApproved':'false'}.items()]
    immutable(api,state,'control/image-registration-intent.json',{'name':name,'snapshot':snapshot,'system':system,'mapping':mapping,'image_tags':image_tags,'no_register_replay_on_unknown_response':True})
    reply=api('ec2','register-image','--name',name,'--architecture','arm64','--virtualization-type','hvm','--ena-support','--boot-mode','uefi','--root-device-name','/dev/xvda','--block-device-mappings',json.dumps(mapping),'--tag-specifications',json.dumps([{'ResourceType':'image','Tags':image_tags}]))
    value={'image':reply['ImageId'],'snapshot':snapshot,'system':system,'candidate_only_not_boot_or_production_approval':True,'goal_complete':False};immutable(api,state,'control/image-registered-candidate.json',value);return value


def boot_empty_trial(api,state,image):
    """Replace ONLY the output-delivered empty fixture, never original/work."""
    api.account();require(datetime.fromisoformat(state['expires']).timestamp()-time.time()>900,'too little unchanged native lifetime for candidate boot');registered=c.read(api,state,'control/image-registered-candidate.json');retained=c.read(api,state,'artifacts/image-evidence-retained.json');created=c.read(api,state,'control/image-root-created.json');prepared=c.read(api,state,'artifacts/autobootstrap-prepared-control')
    require(registered['image']==image and retained['all_complete_log_and_NAR_bytes_received'] is True and retained['normal_snapshot_claim_released_owned_scopes_collected'] is True and retained['scope']==state['scope'] and created['instance']!=b.PRODUCTION,'candidate/source evidence not safely delivered')
    images=api('ec2','describe-images','--image-ids',image)['Images'];require(len(images)==1 and images[0]['State']=='available' and images[0]['OwnerId']==b.ACCOUNT and {t['Key']:t['Value'] for t in images[0]['Tags']}.get('ScopeId')==state['scope'],'candidate image not available')
    groups=api('autoscaling','describe-auto-scaling-groups','--auto-scaling-group-names',state['name'])['AutoScalingGroups'];require(len(groups)==1,'empty trial group ambiguous');g=groups[0];require(g['AutoScalingGroupARN']==prepared['state']['asg_arn'] and g['NewInstancesProtectedFromScaleIn'] is False and g['CapacityRebalance'] is False and not g['SuspendedProcesses'] and len(g['Instances'])==1 and g['Instances'][0]['InstanceId']==created['instance'] and g['Instances'][0]['ProtectedFromScaleIn'] is False,'not the unchanged unprotected empty trial')
    actions=api('autoscaling','describe-scheduled-actions','--auto-scaling-group-name',state['name'])['ScheduledUpdateGroupActions'];require(len(actions)==1 and actions[0]['ScheduledActionName']==state['name']+'-off' and not actions[0].get('Recurrence') and datetime.fromisoformat(actions[0]['StartTime']).timestamp()==datetime.fromisoformat(state['expires']).timestamp() and all(type(actions[0].get(k)) is int and actions[0][k]==0 for k in ['MinSize','MaxSize','DesiredCapacity']),'trial native expiry changed')
    policy=g['MixedInstancesPolicy'];spec=policy['LaunchTemplate']['LaunchTemplateSpecification'];require(spec['LaunchTemplateId']==state['LT'] and spec['Version']=='2','unknown trial LT version');versions=api('ec2','describe-launch-templates','--launch-template-ids',state['LT'])['LaunchTemplates'];require(len(versions)==1 and versions[0]['LatestVersionNumber']==2,'unknown trial LT history')
    import base64
    data={'ImageId':image,'UserData':base64.b64encode(b'#!/bin/sh\nexit 0\n').decode()};immutable(api,state,'control/empty-image-boot-intent.json',{'original_image_source_instance':created['instance'],'image':image,'old_policy':policy,'numeric_new_version':3,'data':data,'expires_not_extended':state['expires'],'NOT_production_or_user_work_termination':True})
    version=api('ec2','create-launch-template-version','--launch-template-id',state['LT'],'--source-version','2','--client-token','imageboot-'+state['scope'],'--launch-template-data',json.dumps(data))['LaunchTemplateVersion'];require(version['VersionNumber']==3 and version['LaunchTemplateData']['ImageId']==image,'trial candidate LT differs');policy=json.loads(json.dumps(policy));policy['LaunchTemplate']['LaunchTemplateSpecification']['Version']='3';policy['LaunchTemplate']['LaunchTemplateSpecification'].pop('LaunchTemplateName',None)
    api('autoscaling','update-auto-scaling-group','--auto-scaling-group-name',state['name'],'--mixed-instances-policy',json.dumps(policy));now=api('autoscaling','describe-auto-scaling-groups','--auto-scaling-group-names',state['name'])['AutoScalingGroups'];require(len(now)==1 and now[0]['AutoScalingGroupARN']==g['AutoScalingGroupARN'] and now[0]['MixedInstancesPolicy']['LaunchTemplate']['LaunchTemplateSpecification']['Version']=='3' and len(now[0]['Instances'])==1 and now[0]['Instances'][0]['InstanceId']==created['instance'] and now[0]['Instances'][0]['ProtectedFromScaleIn'] is False,'trial switch/member unknown; no termination')
    reply=api('autoscaling','terminate-instance-in-auto-scaling-group','--instance-id',created['instance'],'--no-should-decrement-desired-capacity');value={'image':image,'source_instance':created['instance'],'native_replacement_requested_not_boot_success':reply,'expires_unchanged':state['expires'],'original_and_production_LT_untouched':True,'goal_complete':False};immutable(api,state,'control/empty-image-boot-requested.json',value);return value


def lt_candidate(api,state,image,system):
    api.account();rows=api('ec2','describe-images','--image-ids',image)['Images'];require(len(rows)==1,'candidate image ambiguous');im=rows[0];tags={r['Key']:r['Value'] for r in im.get('Tags',[])}
    require(im['OwnerId']==b.ACCOUNT and im['State']=='available' and im['Architecture']=='arm64' and im.get('BootMode')=='uefi' and im['RootDeviceName']=='/dev/xvda' and tags.get('ScopeId')==state['scope'] and tags.get('DeploymentStage')=='candidate' and tags.get('PreparedSystem')==system,'unverified/foreign candidate image')
    mappings=im['BlockDeviceMappings'];require(len(mappings)==1 and mappings[0]['Ebs']['Encrypted'] is True and mappings[0]['Ebs']['VolumeSize']==32,'candidate root mapping differs')
    snapshots=api('ec2','describe-snapshots','--snapshot-ids',mappings[0]['Ebs']['SnapshotId'])['Snapshots'];require(len(snapshots)==1 and snapshots[0]['State']=='completed' and snapshots[0]['OwnerId']==b.ACCOUNT and snapshots[0]['Encrypted'] is True,'candidate snapshot not complete')
    group=api('autoscaling','describe-auto-scaling-groups','--auto-scaling-group-names','nixos-ec2-asg')['AutoScalingGroups'];require(len(group)==1 and len(group[0]['Instances'])==1 and group[0]['Instances'][0]['InstanceId']==b.PRODUCTION and group[0]['Instances'][0]['ProtectedFromScaleIn'] is True,'original protected membership changed')
    spec=group[0]['MixedInstancesPolicy']['LaunchTemplate']['LaunchTemplateSpecification'];require(spec['LaunchTemplateId']=='lt-01468c818ef1bb11a' and spec['Version']=='1','original LT policy changed')
    latest=api('ec2','describe-launch-templates','--launch-template-ids',spec['LaunchTemplateId'])['LaunchTemplates'];require(len(latest)==1 and latest[0]['LatestVersionNumber']==1 and latest[0]['DefaultVersionNumber']==1,'unknown existing production LT versions')
    import base64
    data={'ImageId':image,'UserData':base64.b64encode(b'#!/bin/sh\nexit 0\n').decode(),'MetadataOptions':{'HttpTokens':'required','HttpEndpoint':'enabled'},'BlockDeviceMappings':[{'DeviceName':'/dev/xvda','Ebs':{'VolumeSize':32,'VolumeType':'gp3','Encrypted':True,'DeleteOnTermination':True}}]}
    intent={'image':image,'system':system,'source_LT':spec,'new_version_data':data,'not_default_or_ASG_cutover':True,'work_tracking_verified':False,'armed':False,'goal_complete':False};immutable(api,state,'control/production-LT-candidate-intent.json',intent)
    result=api('ec2','create-launch-template-version','--launch-template-id',spec['LaunchTemplateId'],'--source-version','1','--client-token','candidate-'+state['scope'],'--version-description','UNAPPROVED-source-'+state['source_revision'][:12]+'-'+state['scope'],'--launch-template-data',json.dumps(data))['LaunchTemplateVersion'];require(result['VersionNumber']==2 and result['LaunchTemplateData']['ImageId']==image,'candidate LT readback differs');value={**intent,'numeric_candidate_version':2,'actual_version':result};immutable(api,state,'control/production-LT-candidate-created.json',value);return value


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['plan','create-root','register-image','boot-empty-trial','lt-candidate']);parser.add_argument('--scope',required=True);parser.add_argument('--source-revision',required=True);parser.add_argument('--run');parser.add_argument('--image');parser.add_argument('--snapshot');parser.add_argument('--system');parser.add_argument('--profile');args=parser.parse_args();os.environ['AWS_MAX_ATTEMPTS']='1';api=b.API(args.profile);state=c.p.read_state(api,b.plan(args.scope,args.source_revision))
    if args.action=='plan':result=root_plan(state)
    elif args.action=='create-root':require(args.run is not None,'retained run required');result=create_root(api,state,args.run)
    elif args.action=='register-image':require(args.snapshot and args.system,'completed cold snapshot/system required');result=register_image(api,state,args.snapshot,args.system)
    elif args.action=='boot-empty-trial':require(args.image,'candidate image required');result=boot_empty_trial(api,state,args.image)
    else:require(args.image and args.system,'verified candidate image/system required');result=lt_candidate(api,state,args.image,args.system)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
