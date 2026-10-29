#!/usr/bin/env python3
"""One-shot cloud-only EMPTY recovery builder with independent native Fleet expiry.

Never production/accepted-work deadline authority. Build starts with ONE disposable
root and unprotected exact ASG membership for the existing resource attestation.
A later protected disposable OS boot cannot defeat Fleet.ValidUntil. ASG-born
replacements are discarded by the native30s ABANDON hook; fixed ASG off precedes
Fleet expiry by5min. This creator does NOT claim OS/home or replacement replay.
"""
import argparse
from datetime import datetime, timedelta
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time


def sibling(name, filename):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(filename))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


b=sibling('recovery_build','spot-build-canary.py')
f=sibling('recovery_fleet','spot-fleet-expiry.py')
require=f.require


def plan(scope,source,now=None):
    state=b.plan(scope,source,now)
    state.update(fleet_role=state['name']+'-fleet',asg_off_at=(datetime.fromisoformat(state['expires'])-timedelta(minutes=5)).isoformat(),
                 creator_script_sha256=hashlib.sha256(Path(b.__file__).read_bytes()).hexdigest(),
                 recovery_phase='single-root-build-only',independent_Fleet_expiry_required=True)
    return state


def fleet_state(state):
    return {**state,'role':state['fleet_role'],'image':state['base_image']}


def fleet_policy(state):
    value=f.fleet_policy(fleet_state(state))
    for row in value['Statement']:
        if row['Effect']=='Deny' and isinstance(row['Action'],list):row['Action']=[a for a in row['Action'] if a!='iam:PassRole']
    value['Statement'].append({'Effect':'Allow','Action':'iam:PassRole','Resource':state['role_arn'],
                               'Condition':{'StringEquals':{'iam:PassedToService':'ec2.amazonaws.com'}}})
    return value


def guest_policy(state):
    value=b.scoped_policy(state)
    for row in value['Statement']:
        if row['Effect']=='Deny':row['Action']=[a for a in row['Action'] if a!='autoscaling:SetInstanceProtection']
    value['Statement'].append({'Effect':'Allow','Action':'autoscaling:SetInstanceProtection','Resource':state['asg_arn'],
                               'Condition':{'StringEquals':{'aws:RequestedRegion':b.REGION}}})
    # No storage/EIP/snapshot authority yet. Exact disposable home grants require
    # their own separately validated provisioned identity; never a production ID.
    return value


def fleet_config(state):
    value=f.config(fleet_state(state));value['TagSpecifications']=[{'ResourceType':'spot-fleet-request','Tags':state['tags']}];return value


def validate_zero(state,request,group,actions,hooks,lt):
    c=request['SpotFleetRequestConfig'];wanted=fleet_config(state)
    require(request['SpotFleetRequestId']==state['FleetId'] and request['SpotFleetRequestState'] in {'submitted','active'}
            and type(c['TargetCapacity']) is int and c['TargetCapacity']==0 and c.get('FulfilledCapacity',0)==0 and type(c.get('OnDemandTargetCapacity',0)) is int and c.get('OnDemandTargetCapacity',0)==0
            and c.get('OnDemandFulfilledCapacity',0)==0 and c['Type']=='maintain' and c['TerminateInstancesWithExpiration'] is True
            and c['IamFleetRole']==wanted['IamFleetRole'] and c['AllocationStrategy']=='lowestPrice'
            and c['InstanceInterruptionBehavior']=='terminate' and c.get('ReplaceUnhealthyInstances') is False
            and datetime.fromisoformat(c['ValidUntil']).timestamp()==datetime.fromisoformat(state['expires']).timestamp()
            and float(c['SpotPrice'])==.020 and float(c['SpotMaxTotalPrice'])==.020,'native recovery Fleet differs')
    f.fixed_launch_config(fleet_state(state),c['LaunchTemplateConfigs'])
    require(group['AutoScalingGroupName']==state['name'] and group['AutoScalingGroupARN']==state['asg_arn']
            and all(type(group[k]) is int for k in ['DesiredCapacity','MinSize','MaxSize']) and group['DesiredCapacity']==0 and not group['Instances'] and group['MinSize']==0 and group['MaxSize']==1
            and group['NewInstancesProtectedFromScaleIn'] is False and group['CapacityRebalance'] is False
            and not group['SuspendedProcesses'],'single-root build membership authority differs')
    mixed=group['MixedInstancesPolicy'];require(mixed['LaunchTemplate']['LaunchTemplateSpecification']['LaunchTemplateId']==state['LT']
            and mixed['LaunchTemplate']['LaunchTemplateSpecification']['Version']=='1'
            and mixed['LaunchTemplate']['Overrides']==[{'InstanceType':'r7g.large'}]
            and mixed['InstancesDistribution']['OnDemandBaseCapacity']==mixed['InstancesDistribution']['OnDemandPercentageAboveBaseCapacity']==0
            and mixed['InstancesDistribution']['SpotAllocationStrategy']=='lowest-price' and mixed['InstancesDistribution']['SpotInstancePools']==1
            and float(mixed['InstancesDistribution']['SpotMaxPrice'])==.020,'ASG numeric LT/Spot differs')
    require(len(actions)==1 and actions[0]['AutoScalingGroupName']==state['name'] and actions[0]['ScheduledActionName']==state['name']+'-off'
            and not actions[0].get('Recurrence') and all(type(actions[0].get(k)) is int and actions[0][k]==0 for k in ['MinSize','MaxSize','DesiredCapacity'])
            and datetime.fromisoformat(actions[0]['StartTime']).timestamp()==datetime.fromisoformat(state['asg_off_at']).timestamp(),'native ASG off differs')
    f.validate_launch_guard(fleet_state(state),hooks)
    require(300<datetime.fromisoformat(state['asg_off_at']).timestamp()-time.time()<6600
            and 600<datetime.fromisoformat(state['expires']).timestamp()-time.time()<=6600,'fixed recovery budget exhausted')
    require(lt['ImageId']==b.AMI and lt['InstanceType']=='r7g.large' and lt['IamInstanceProfile']=={'Name':state['name']}
            and lt['SecurityGroupIds']==[f.b.SG] and not lt.get('UserData') and not lt.get('KeyName')
            and lt['MetadataOptions']['HttpTokens']=='required'
            and lt['BlockDeviceMappings']==[{'DeviceName':'/dev/xvda','Ebs':{'VolumeSize':32,'VolumeType':'gp3','Encrypted':True,'DeleteOnTermination':True}}],
            'fixed disposable root/profile/image differs')
    require(lt.get('TagSpecifications')==[{'ResourceType':kind,'Tags':state['tags']} for kind in ['instance','volume']],'disposable launch tags differ')


class API(b.API):
    def __call__(self,service,operation,*args):
        # Unknown/lost provision/PUT replies are never automatically replayed.
        old=os.environ.get('AWS_MAX_ATTEMPTS');os.environ['AWS_MAX_ATTEMPTS']='1'
        try:return super().__call__(service,operation,*args)
        finally:
            if old is None:os.environ.pop('AWS_MAX_ATTEMPTS',None)
            else:os.environ['AWS_MAX_ATTEMPTS']=old

    def new(self,state,key,value):
        data=json.dumps(value,sort_keys=True,separators=(',',':')).encode()
        with tempfile.TemporaryDirectory(prefix='recovery-public-control-') as directory:
            path=Path(directory)/'body';path.write_bytes(data);path.chmod(0o600)
            self('s3api','put-object','--bucket',state['bucket'],'--key',key,'--body',str(path),'--if-none-match','*','--expected-bucket-owner',b.ACCOUNT,
                 '--server-side-encryption','AES256','--checksum-algorithm','SHA256','--metadata','sha256='+hashlib.sha256(data).hexdigest())
            read=Path(directory)/'readback';self('s3api','get-object','--bucket',state['bucket'],'--key',key,'--expected-bucket-owner',b.ACCOUNT,str(read))
            require(read.read_bytes()==data,'immutable cloud control body differs')

    def read(self,state,key):
        with tempfile.TemporaryDirectory(prefix='recovery-control-read-') as directory:
            path=Path(directory)/'body';self('s3api','get-object','--bucket',state['bucket'],'--key',key,'--expected-bucket-owner',b.ACCOUNT,str(path))
            require(path.stat().st_size<=65536,'control state too large');return json.loads(path.read_text())


def reference(api,data):
    """Re-read the exact previous empty protected expiry, not a green boolean."""
    require(b.digest(data)=='ab2f7a80e6283de654d3b0ec3ef65015694814cfbd379e6019d8be254fcd57e2','pinned original-host capture/reference bytes differ')
    state=data['state'];require(state['scope']=='a6401bc9d875' and state['FleetId']=='sfr-c137961d-0d7f-442a-a0ea-925c7b0f4f7d','unknown protected expiry reference')
    request=api('ec2','describe-spot-fleet-requests','--spot-fleet-request-ids',state['FleetId'])['SpotFleetRequestConfigs']
    require(len(request)==1 and request[0]['SpotFleetRequestState'].startswith('cancelled'),'reference Fleet not terminal')
    start=datetime.fromisoformat(state['created']).replace(microsecond=0).isoformat()
    history=api('ec2','describe-spot-fleet-request-history','--spot-fleet-request-id',state['FleetId'],'--start-time',start)
    events=[]
    for old in data['termination_events']:
        rows=api('cloudtrail','lookup-events','--lookup-attributes','AttributeKey=EventId,AttributeValue='+old['eventID'])
        require(not rows.get('NextToken') and len(rows['Events'])==1,'native reference event unknown')
        events.append(json.loads(rows['Events'][0]['CloudTrailEvent']))
    return f.verify_expiry_evidence(state,request[0],history,data['capture'],events)


def create_zero(api,state,evidence):
    api.account();proof=reference(api,evidence)
    b.create(api,state,activate=False)  # native ASG only; explicitly no paid mutation
    api.new(state,'control/recovery-creator.json',{'program':Path(__file__).read_text(),'sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'reference':proof})
    group=api('autoscaling','describe-auto-scaling-groups','--auto-scaling-group-names',state['name'])['AutoScalingGroups'];require(len(group)==1,'new group unknown');state['asg_arn']=group[0]['AutoScalingGroupARN']
    api('iam','put-role-policy','--role-name',state['name'],'--policy-name','DisposableAttestationAndArtifacts','--policy-document',json.dumps(guest_policy(state)))
    api('autoscaling','put-lifecycle-hook','--auto-scaling-group-name',state['name'],'--lifecycle-hook-name',state['name']+'-discard-new',
        '--lifecycle-transition','autoscaling:EC2_INSTANCE_LAUNCHING','--heartbeat-timeout','30','--default-result','ABANDON')
    api('autoscaling','put-scheduled-update-group-action','--auto-scaling-group-name',state['name'],'--scheduled-action-name',state['name']+'-off',
        '--start-time',state['asg_off_at'],'--min-size','0','--max-size','0','--desired-capacity','0')
    trust={'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':'spotfleet.amazonaws.com'},'Action':'sts:AssumeRole'}]}
    api('iam','create-role','--role-name',state['fleet_role'],'--assume-role-policy-document',json.dumps(trust),'--tags',json.dumps(state['tags']))
    api('iam','put-role-policy','--role-name',state['fleet_role'],'--policy-name','OnlyThisRecoveryFleet','--policy-document',json.dumps(fleet_policy(state)))
    time.sleep(10);state['FleetId']=api('ec2','request-spot-fleet','--spot-fleet-request-config',json.dumps(fleet_config(state)))['SpotFleetRequestId']
    zero_readback(api,state);api.new(state,'control/recovery-zero.json',state)
    return {'state':state,'native_zero_readback':True,'capacity_requested':False,'OS_recovery_verified':False,'goal_complete':False}


def zero_readback(api,state):
    request=api('ec2','describe-spot-fleet-requests','--spot-fleet-request-ids',state['FleetId'])['SpotFleetRequestConfigs'];groups=api('autoscaling','describe-auto-scaling-groups','--auto-scaling-group-names',state['name'])['AutoScalingGroups']
    require(len(request)==len(groups)==1,'ambiguous recovery scope')
    actions=api('autoscaling','describe-scheduled-actions','--auto-scaling-group-name',state['name'])['ScheduledUpdateGroupActions'];hooks=api('autoscaling','describe-lifecycle-hooks','--auto-scaling-group-name',state['name'])['LifecycleHooks']
    lt=api('ec2','describe-launch-template-versions','--launch-template-id',state['LT'],'--versions','1')['LaunchTemplateVersions'];require(len(lt)==1,'LT unknown')
    validate_zero(state,request[0],groups[0],actions,hooks,lt[0]['LaunchTemplateData'])
    subnet=api('ec2','describe-subnets','--subnet-ids',f.b.SUBNET)['Subnets'];require(len(subnet)==1 and subnet[0]['MapPublicIpOnLaunch'] is True and subnet[0]['AvailabilityZone']=='ap-northeast-2d','SSM/public-source network unavailable')
    for role,name,expected in [(state['name'],'DisposableAttestationAndArtifacts',guest_policy(state)),(state['fleet_role'],'OnlyThisRecoveryFleet',fleet_policy(state))]:
        require(api('iam','get-role-policy','--role-name',role,'--policy-name',name)['PolicyDocument']==expected,'recovery IAM changed')
        require(api('iam','list-role-policies','--role-name',role)['PolicyNames']==[name],'foreign inline recovery policy')
        managed=api('iam','list-attached-role-policies','--role-name',role)['AttachedPolicies']
        require([p['PolicyArn'] for p in managed]==([b.CORE] if role==state['name'] else []),'foreign managed recovery authority')
    profile=api('iam','get-instance-profile','--instance-profile-name',state['name'])['InstanceProfile']
    require(profile['Arn']==state['profile_arn'] and len(profile['Roles'])==1 and profile['Roles'][0]['Arn']==state['role_arn'],'guest profile role changed')


def activate(api,state):
    api.account();zero_readback(api,state)
    api('ec2','modify-spot-fleet-request','--spot-fleet-request-id',state['FleetId'],'--target-capacity','1','--excess-capacity-termination-policy','noTermination')
    api.new(state,'control/recovery-capacity-requested.json',{'native_deadline_unchanged':state['expires'],'capacity_requested':True,'not_build_or_OS_success':True})
    deadline=time.monotonic()+120
    while True:
        rows=api('ec2','describe-spot-fleet-instances','--spot-fleet-request-id',state['FleetId'])['ActiveInstances']
        if rows:break
        require(time.monotonic()<deadline,'Fleet launch unobserved; native expiry remains');time.sleep(3)
    require(len(rows)==1,'unexpected Fleet roster');iid=rows[0]['InstanceId']
    while True:
        rows=api('ec2','describe-instances','--instance-ids',iid)['Reservations'];require(len(rows)==1 and rows[0]['OwnerId']==b.ACCOUNT and len(rows[0]['Instances'])==1,'unknown recovery instance');i=rows[0]['Instances'][0]
        if i['State']['Name']=='running':break
        require(i['State']['Name']=='pending' and time.monotonic()<deadline,'recovery instance not running; native expiry remains');time.sleep(2)
    require(i.get('PublicIpAddress') and not i.get('KeyName') and i['InstanceLifecycle']=='spot' and i['ImageId']==b.AMI and i['IamInstanceProfile']['Arn']==state['profile_arn']
            and len(i['BlockDeviceMappings'])==1 and i['BlockDeviceMappings'][0]['Ebs']['DeleteOnTermination'] is True
            and {t['Key']:t['Value'] for t in i.get('Tags',[])}.get('ScopeId')==state['scope'],'not isolated recovery Spot')
    root=i['BlockDeviceMappings'][0]['Ebs']['VolumeId'];require(root not in {'vol-065729ef75553a7ec','vol-09fea2ff4615b1088','vol-0b529abe51df1eca1'},'retained root forbidden')
    volumes=api('ec2','describe-volumes','--volume-ids',root)['Volumes'];require(len(volumes)==1 and volumes[0]['Encrypted'] is True and volumes[0]['Size']==32,'root differs')
    api('autoscaling','attach-instances','--auto-scaling-group-name',state['name'],'--instance-ids',iid)
    while True:
        groups=api('autoscaling','describe-auto-scaling-groups','--auto-scaling-group-names',state['name'])['AutoScalingGroups'];require(len(groups)==1,'group lost')
        members=[m for m in groups[0]['Instances'] if m['InstanceId']==iid]
        if members and members[0]['LifecycleState']=='InService':
            require(members[0]['ProtectedFromScaleIn'] is False,'not attested unprotected build phase');break
        require(time.monotonic()<deadline,'member not settled; no build admitted');time.sleep(2)
    state.update(new_instance=iid,root_volume=root)
    api.new(state,'control/recovery-single-root-ready.json',state)
    return {'state':state,'unprotected_single_root_member_confirmed':True,'build_success':False,'OS_recovery_verified':False,'goal_complete':False}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['plan','create-zero','activate']);p.add_argument('--scope',required=True);p.add_argument('--source-revision',required=True);p.add_argument('--expiry-evidence',type=Path,default=Path(__file__).parent/'evidence/protected-expiry-a6401bc9d875.json');p.add_argument('--profile');a=p.parse_args();state=plan(a.scope,a.source_revision)
    if a.action=='plan':print(json.dumps(state,indent=2));return
    api=API(a.profile)
    if a.action=='create-zero':
        require(a.expiry_evidence is not None,'actual protected native expiry reference required');result=create_zero(api,state,json.loads(a.expiry_evidence.read_text()))
    else:
        stored=api.read(state,'control/recovery-zero.json');require(stored['scope']==state['scope'] and stored['name']==state['name'] and stored['source_revision']==a.source_revision,'foreign/stale cloud recovery control');result=activate(api,stored)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
