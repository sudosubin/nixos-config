#!/usr/bin/env python3
"""Native Spot Fleet expiry for EMPTY-WORKLOAD protected ASG trials only.

ASG Launch is suspended BEFORE any paid request so it cannot create a non-fleet
replacement escaping Fleet expiry. Fleet target starts0; fixed ValidUntil and
TerminateInstancesWithExpiration are read back before target1. No guest role,
keys, userdata, public IPv4, model/config data or larger validation authority.
Never use this forced disposable deadline on production or accepted user work.
"""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import time

spec = importlib.util.spec_from_file_location('native_expiry', Path(__file__).with_name('spot-protected-expiry.py'))
b = importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
require = b.require


def plan(scope, image, revision, now=None):
    value = b.plan(scope, 'empty', image, revision, now)
    now = datetime.fromisoformat(value['created'])
    value.update(name='nixos-fleet-expiry-'+scope, role='nixos-fleet-expiry-'+scope+'-fleet',
                 expires=(now+timedelta(minutes=12)).replace(microsecond=0).isoformat(),
                 purpose='empty-workload native protected expiry', capacity_after_containment=1)
    return value


def fleet_policy(state):
    base = 'arn:aws:ec2:'+b.REGION+':'+b.ACCOUNT+':'
    lt = base+'launch-template/'+state['LT']
    return {'Version':'2012-10-17','Statement':[
        {'Effect':'Allow','Action':['ec2:DescribeImages','ec2:DescribeSubnets','ec2:DescribeInstances',
         'ec2:DescribeInstanceStatus','ec2:DescribeSpotInstanceRequests'],'Resource':'*',
         'Condition':{'StringEquals':{'aws:RequestedRegion':b.REGION}}},
        {'Effect':'Allow','Action':['ec2:RunInstances','ec2:RequestSpotInstances'],
         'Resource':[lt,'arn:aws:ec2:'+b.REGION+'::image/'+state['image'],base+'subnet/'+b.SUBNET,
                     base+'security-group/'+b.SG,base+'network-interface/*',base+'spot-instances-request/*'],
         'Condition':{'StringEquals':{'aws:RequestedRegion':b.REGION},'ArnEqualsIfExists':{'ec2:LaunchTemplate':lt}}},
        # A guest without the expiry role's mandatory termination tags must not
        # be launched first and tagged later: that would leave an expiry gap.
        {'Effect':'Allow','Action':'ec2:RunInstances','Resource':[base+'instance/*',base+'volume/*'],
         'Condition':{'StringEquals':{'aws:RequestedRegion':b.REGION,'aws:RequestTag/ScopeId':state['scope'],
                                     'aws:RequestTag/ManagedBy':'nixos-spot-validation'},'ArnEquals':{'ec2:LaunchTemplate':lt}}},
        {'Effect':'Allow','Action':'ec2:TerminateInstances','Resource':base+'instance/*',
         'Condition':{'StringEquals':{'ec2:ResourceTag/ScopeId':state['scope'],'ec2:ResourceTag/ManagedBy':'nixos-spot-validation'}}},
        {'Effect':'Allow','Action':'ec2:CreateTags','Resource':[base+'instance/*',base+'volume/*',base+'spot-instances-request/*'],
         'Condition':{'StringEquals':{'aws:RequestTag/ScopeId':state['scope'],
                                     'ec2:CreateAction':['RunInstances','RequestSpotInstances']}}},
        {'Effect':'Allow','Action':'ec2:CreateTags','Resource':[base+'instance/*',base+'volume/*',base+'spot-instances-request/*'],
         'Condition':{'StringEquals':{'aws:RequestTag/ScopeId':state['scope'],'ec2:ResourceTag/ScopeId':state['scope']}}},
        {'Effect':'Deny','Action':'ec2:TerminateInstances','Resource':base+'instance/i-0c39eff85c4286b38'},
        {'Effect':'Deny','Action':['iam:PassRole','ec2:AttachVolume','ec2:DetachVolume','ec2:AssociateAddress',
         'ec2:DisassociateAddress','ec2:CreateSnapshot','ec2:DeleteSnapshot','ec2:DeleteVolume'],'Resource':'*'}]}


def config(state):
    return {'IamFleetRole':'arn:aws:iam::'+b.ACCOUNT+':role/'+state['role'], 'ClientToken':state['name'],
            'Type':'maintain','TargetCapacity':0,'OnDemandTargetCapacity':0,
            'AllocationStrategy':'lowestPrice','InstancePoolsToUseCount':1,
            'SpotPrice':state['spot_hourly_ceiling'],'SpotMaxTotalPrice':state['spot_hourly_ceiling'],
            'ValidUntil':state['expires'],'TerminateInstancesWithExpiration':True,
            'InstanceInterruptionBehavior':'terminate','ReplaceUnhealthyInstances':False,
            'ExcessCapacityTerminationPolicy':'noTermination',
            'LaunchTemplateConfigs':[{'LaunchTemplateSpecification':{'LaunchTemplateId':state['LT'],'Version':'1'},
                                      'Overrides':[{'InstanceType':state['instance_type'],'SubnetId':b.SUBNET}]}],
            'TagSpecifications':[{'ResourceType':'spot-fleet-request','Tags':b.tags(state)}]}


def fixed_launch_config(state, configs):
    require(isinstance(configs,list) and len(configs)==1,'unknown Fleet launch roster')
    spec=configs[0]['LaunchTemplateSpecification'];overrides=configs[0]['Overrides']
    require(spec['LaunchTemplateId']==state['LT'] and spec['Version']=='1' and spec.get('LaunchTemplateName',state['name'])==state['name']
            and len(overrides)==1 and overrides[0].get('InstanceType')==state['instance_type'] and overrides[0].get('SubnetId')==b.SUBNET
            and overrides[0].get('AvailabilityZone','ap-northeast-2d')=='ap-northeast-2d'
            and overrides[0].get('WeightedCapacity',1)==1 and not overrides[0].get('InstanceRequirements'),'Fleet numeric LT/single fixed Spot pool differs')


def validate_zero(state, request, group, actions):
    c=request['SpotFleetRequestConfig']
    require(request['SpotFleetRequestState'] in {'submitted','active'} and c['Type']=='maintain'
            and c['TargetCapacity']==0 and c.get('OnDemandTargetCapacity',0)==0
            and c['TerminateInstancesWithExpiration'] is True and c['IamFleetRole']==config(state)['IamFleetRole']
            and c['AllocationStrategy']=='lowestPrice' and c['InstanceInterruptionBehavior']=='terminate'
            and c.get('FulfilledCapacity',0)==0 and c.get('OnDemandFulfilledCapacity',0)==0
            and float(c['SpotPrice'])==float(state['spot_hourly_ceiling']) and float(c['SpotMaxTotalPrice'])==float(state['spot_hourly_ceiling'])
            and datetime.fromisoformat(c['ValidUntil']).timestamp()==datetime.fromisoformat(state['expires']).timestamp()
            , 'native Fleet expiry/zero target differs')
    fixed_launch_config(state,c['LaunchTemplateConfigs'])
    require(group['AutoScalingGroupName']==state['name'] and group['DesiredCapacity']==0 and not group['Instances']
            and group['MinSize']==0 and group['MaxSize']==1 and group['NewInstancesProtectedFromScaleIn'] is True
            and group['CapacityRebalance'] is False and group.get('DeletionProtection','none')=='none'
            and {x['ProcessName'] for x in group['SuspendedProcesses']}=={'Launch'}, 'ASG can create an unbounded non-fleet replacement')
    mixed=group['MixedInstancesPolicy'];require(mixed['LaunchTemplate']['LaunchTemplateSpecification']['LaunchTemplateId']==state['LT']
            and mixed['LaunchTemplate']['LaunchTemplateSpecification']['Version']=='1'
            and mixed['InstancesDistribution']['OnDemandBaseCapacity']==0
            and mixed['InstancesDistribution']['OnDemandPercentageAboveBaseCapacity']==0,'ASG numeric LT/Spot policy changed')
    require(len(actions)==1 and all(actions[0][k]==0 for k in ['MinSize','MaxSize','DesiredCapacity'])
            and datetime.fromisoformat(actions[0]['StartTime']).timestamp()==datetime.fromisoformat(state['off_at']).timestamp(), 'native ASG zero request missing')
    require(60<datetime.fromisoformat(state['off_at']).timestamp()-time.time()<240
            and 300<datetime.fromisoformat(state['expires']).timestamp()-time.time()<=720, 'native containment setup exhausted')


def create(api, state):
    require(re.fullmatch('[0-9a-f]{12}',state['scope']) and state['name']=='nixos-fleet-expiry-'+state['scope']
            and state['role']==state['name']+'-fleet','not an owned disposable scope')
    require(api('sts','get-caller-identity')['Account']==b.ACCOUNT,'wrong account')
    require(not api('autoscaling','describe-auto-scaling-groups','--auto-scaling-group-names',state['name'])['AutoScalingGroups'],'existing scope')
    b.absent(api,'iam','get-role',['--role-name',state['role']],'NoSuchEntity')
    b.absent(api,'ec2','describe-launch-templates',['--launch-template-names',state['name']],'InvalidLaunchTemplateName.NotFoundException')
    image=api('ec2','describe-images','--image-ids',state['image'])['Images']
    require(len(image)==1 and image[0]['OwnerId']==b.AMI_OWNER and image[0]['Architecture']=='arm64'
            and image[0]['State']=='available' and len(image[0]['BlockDeviceMappings'])==1
            and image[0]['BlockDeviceMappings'][0]['Ebs']['VolumeSize']==8,'not the public empty-workload image')
    trust={'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':'spotfleet.amazonaws.com'},'Action':'sts:AssumeRole'}]}
    api('iam','create-role','--role-name',state['role'],'--assume-role-policy-document',json.dumps(trust),'--tags',json.dumps(b.tags(state)))
    lt=api('ec2','create-launch-template','--launch-template-name',state['name'],'--client-token',state['name'],
           '--launch-template-data',json.dumps(b.launch_data(state)),
           '--tag-specifications',json.dumps([{'ResourceType':'launch-template','Tags':b.tags(state)}]))['LaunchTemplate']['LaunchTemplateId']
    state['LT']=lt;policy=fleet_policy(state)
    api('iam','put-role-policy','--role-name',state['role'],'--policy-name','OnlyThisFleetTaggedInstances','--policy-document',json.dumps(policy))
    mixed={'LaunchTemplate':{'LaunchTemplateSpecification':{'LaunchTemplateId':lt,'Version':'1'},'Overrides':[{'InstanceType':state['instance_type']}]},
           'InstancesDistribution':{'OnDemandBaseCapacity':0,'OnDemandPercentageAboveBaseCapacity':0,'SpotAllocationStrategy':'lowest-price','SpotInstancePools':1,'SpotMaxPrice':state['spot_hourly_ceiling']}}
    api('autoscaling','create-auto-scaling-group','--auto-scaling-group-name',state['name'],'--min-size','0','--max-size','1','--desired-capacity','0',
        '--vpc-zone-identifier',b.SUBNET,'--new-instances-protected-from-scale-in','--no-capacity-rebalance',
        '--mixed-instances-policy',json.dumps(mixed),'--tags',json.dumps([{**x,'PropagateAtLaunch':True} for x in b.tags(state)]))
    api('autoscaling','suspend-processes','--auto-scaling-group-name',state['name'],'--scaling-processes','Launch')
    api('autoscaling','put-scheduled-update-group-action','--auto-scaling-group-name',state['name'],'--scheduled-action-name',state['name']+'-off',
        '--start-time',state['off_at'],'--min-size','0','--max-size','0','--desired-capacity','0')
    # No paid capacity yet. A fleet-role propagation error here is safe but not
    # blindly replayed; reconcile its request tags/cloud state before retrying.
    time.sleep(10)
    reply=api('ec2','request-spot-fleet','--spot-fleet-request-config',json.dumps(config(state)))
    state['FleetId']=reply['SpotFleetRequestId']
    zero_readback(api,state)
    description=json.dumps(state,separators=(',',':'));require(len(description)<=1000,'cloud state exceeds role description limit')
    api('iam','update-role-description','--role-name',state['role'],'--description',description)
    api('autoscaling','create-or-update-tags','--tags',json.dumps([{'ResourceId':state['name'],'ResourceType':'auto-scaling-group',
        'Key':k,'Value':v,'PropagateAtLaunch':False} for k,v in {'FleetId':state['FleetId'],'FleetExpires':state['expires'],
        'CreatorRevision':state['source_revision'],'StateSHA256':b.digest(state)}.items()]))
    return {'state':state,'native_zero_containment_confirmed':True,'capacity_requested':False,'expiry_success':False}


def zero_readback(api,state):
    request=api('ec2','describe-spot-fleet-requests','--spot-fleet-request-ids',state['FleetId'])['SpotFleetRequestConfigs']
    group=api('autoscaling','describe-auto-scaling-groups','--auto-scaling-group-names',state['name'])['AutoScalingGroups']
    actions=api('autoscaling','describe-scheduled-actions','--auto-scaling-group-name',state['name'])['ScheduledUpdateGroupActions']
    require(len(request)==len(group)==1,'containment observation unknown');validate_zero(state,request[0],group[0],actions)
    require(api('iam','get-role-policy','--role-name',state['role'],'--policy-name','OnlyThisFleetTaggedInstances')['PolicyDocument']==fleet_policy(state),'Fleet cleanup policy changed')
    template=api('ec2','describe-launch-template-versions','--launch-template-id',lt,'--versions','1')['LaunchTemplateVersions']
    require(len(template)==1 and template[0]['LaunchTemplateData']==b.launch_data(state),'fixed guest/root/network differs')
    simulate_termination_authority(api,state)


def activate(api,state):
    zero_readback(api,state)  # fresh authoritative read before the ONLY paid mutation
    api('ec2','modify-spot-fleet-request','--spot-fleet-request-id',state['FleetId'],'--target-capacity','1','--excess-capacity-termination-policy','noTermination')
    # This observes/attaches the empty guest; Fleet expiry does NOT need it.
    limit=time.monotonic()+90
    while True:
        instances=api('ec2','describe-spot-fleet-instances','--spot-fleet-request-id',state['FleetId'])['ActiveInstances']
        if instances:break
        require(time.monotonic()<limit,'no fleet member observed; native expiry remains armed');time.sleep(3)
    require(len(instances)==1,'unexpected Fleet capacity');iid=instances[0]['InstanceId']
    while True:
        rows=api('ec2','describe-instances','--instance-ids',iid)['Reservations'];require(len(rows)==1 and rows[0]['OwnerId']==b.ACCOUNT and len(rows[0]['Instances'])==1,'unknown instance')
        instance=rows[0]['Instances'][0]
        if instance['State']['Name']=='running':break
        require(instance['State']['Name']=='pending' and time.monotonic()<limit,'instance not running; native expiry remains');time.sleep(2)
    require(instance['InstanceLifecycle']=='spot' and instance['ImageId']==state['image'] and not instance.get('PublicIpAddress')
            and not instance.get('IamInstanceProfile') and not instance.get('KeyName') and len(instance['BlockDeviceMappings'])==1
            and instance['BlockDeviceMappings'][0]['Ebs']['DeleteOnTermination'] is True,'not empty disposable Spot guest')
    require({t['Key']:t['Value'] for t in instance.get('Tags',[])}.get('ScopeId')==state['scope'],'expiry termination tags absent')
    volume=api('ec2','describe-volumes','--volume-ids',instance['BlockDeviceMappings'][0]['Ebs']['VolumeId'])['Volumes']
    require(len(volume)==1 and volume[0]['Encrypted'] is True and volume[0]['Size']==8,'encrypted disposable root unknown')
    require(datetime.fromisoformat(state['off_at']).timestamp()-time.time()>60,'too late to attach; native expiry remains')
    api('autoscaling','attach-instances','--auto-scaling-group-name',state['name'],'--instance-ids',iid)
    api('autoscaling','set-instance-protection','--auto-scaling-group-name',state['name'],'--instance-ids',iid,'--protected-from-scale-in')
    state.update(instance=iid,root_volume=instance['BlockDeviceMappings'][0]['Ebs']['VolumeId'])
    return {'state':state,'capacity_requested':True,'attach_and_protection_requests_are_observations_not_proof':True,'expiry_success':False,'goal_complete':False}


def simulate_termination_authority(api,state):
    base='arn:aws:ec2:'+b.REGION+':'+b.ACCOUNT+':instance/'
    reply=api('iam','simulate-principal-policy','--policy-source-arn','arn:aws:iam::'+b.ACCOUNT+':role/'+state['role'],
        '--action-names','ec2:TerminateInstances','--resource-arns',base+'i-0123456789abcdef0',base+'i-0c39eff85c4286b38',
        '--context-entries',json.dumps([{'ContextKeyName':'ec2:ResourceTag/ScopeId','ContextKeyType':'string','ContextKeyValues':[state['scope']]},
         {'ContextKeyName':'ec2:ResourceTag/ManagedBy','ContextKeyType':'string','ContextKeyValues':['nixos-spot-validation']}]))
    rows={r['EvalResourceName']:r for r in reply['EvaluationResults']}
    require(set(rows)=={base+'i-0123456789abcdef0',base+'i-0c39eff85c4286b38'}
            and rows[base+'i-0123456789abcdef0']['EvalDecision']=='allowed'
            and rows[base+'i-0c39eff85c4286b38']['EvalDecision']=='explicitDeny','native Fleet termination authority not confirmed')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['plan','create-zero','activate']);parser.add_argument('--scope',required=True)
    parser.add_argument('--image',required=True);parser.add_argument('--source-revision',required=True);parser.add_argument('--profile');args=parser.parse_args()
    state=plan(args.scope,args.image,args.source_revision)
    if args.action=='plan':print(json.dumps({'state':state,'launch':b.launch_data(state)},indent=2));return
    api=b.API(args.profile)
    if args.action=='activate':
        require(api('sts','get-caller-identity')['Account']==b.ACCOUNT,'wrong account')
        role=api('iam','get-role','--role-name',state['role'])['Role'];stored=json.loads(role['Description'])
        require(stored['scope']==args.scope and stored['name']==state['name'] and stored['role']==state['role'],'foreign cloud state')
        group=api('autoscaling','describe-auto-scaling-groups','--auto-scaling-group-names',state['name'])['AutoScalingGroups']
        require(len(group)==1 and {t['Key']:t['Value'] for t in group[0]['Tags']}.get('StateSHA256')==b.digest(stored),'cloud state changed')
        print(json.dumps(activate(api,stored),indent=2));return
    print(json.dumps(create(api,state),indent=2))


if __name__=='__main__':main()
