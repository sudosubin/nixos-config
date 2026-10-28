#!/usr/bin/env python3
"""CloudShell-compatible disposable BUILD infrastructure, never production rollout.

Uses AWS CLI's existing credential provider; never reads/copies credentials.
All operational state is in the private S3 control ledger, not a local file.
Native ASG zero-capacity expiry MUST be read back before requesting capacity.
EC2/EBS/IPv4/S3 are billed separately; no Free Tier/credit assumption.
"""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

ACCOUNT='537112465379'
REGION='ap-northeast-2'
AMI='ami-0d44956a8229b0dad'
PRODUCTION='i-0c39eff85c4286b38'
CORE='arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore'
BASELINE={'SpotHomeVolumeAndEip':'a8c4089bff0d27f8b3d0058d20008bd5ac8ca49eea24276b31def4cff42b1be1',
          'SpotScheduleGuard':'adc337574b774e81b0608ea6f46278336f97c848afe2edab0b1b1dcc8c0c1120'}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def plan(scope,source,now=None):
    if not re.fullmatch('[0-9a-f]{12}',scope) or not re.fullmatch('[0-9a-f]{40}',source):
        raise ValueError('exact random scope and pinned public source revision required')
    now=now or datetime.now(timezone.utc)
    if now.utcoffset() is None:raise ValueError('aware UTC clock required')
    # Leave ten minutes of the library's maximum two hours for setup.
    expires=(now+timedelta(minutes=110)).replace(microsecond=0)
    name='nixos-spot-proof-'+scope;bucket='nixos-spot-proof-'+ACCOUNT+'-'+scope
    tags=[{'Key':k,'Value':v} for k,v in {'ManagedBy':'nixos-spot-validation','Purpose':'artifact-test','ScopeId':scope,
                                       'Disposable':'true','DisposableUntil':expires.isoformat()}.items()]
    return {'scope':scope,'name':name,'bucket':bucket,'source_revision':source,'created':now.isoformat(),
            'expires':expires.isoformat(),'permission_expires':(expires+timedelta(minutes=20)).isoformat(),
            'primary_policy_name':'SpotProofArtifacts'+scope,'tags':tags,'stage':'planned',
            'production_instance':PRODUCTION,'instance_type':'r7g.large','spot_hourly_ceiling':'0.020',
            'base_image':AMI,'new_instance':None,'production_rollout':False,'goal_complete':False}


def scoped_policy(state):
    bucket=state['bucket']
    return {'Version':'2012-10-17','Statement':[
        {'Effect':'Allow','Action':['ec2:DescribeInstances','autoscaling:DescribeAutoScalingInstances',
                                   'autoscaling:DescribeScheduledActions'],'Resource':'*'},
        {'Effect':'Allow','Action':'s3:GetObject','Resource':['arn:aws:s3:::'+bucket+'/artifacts/*','arn:aws:s3:::'+bucket+'/results/*']},
        {'Effect':'Allow','Action':'s3:PutObject','Resource':'arn:aws:s3:::'+bucket+'/results/*'},
        {'Effect':'Deny','Action':['ec2:AttachVolume','ec2:DetachVolume','ec2:AssociateAddress','ec2:DisassociateAddress',
                                  'ec2:ReleaseAddress','ec2:TerminateInstances','ec2:DeleteVolume','ec2:CreateSnapshot',
                                  'ec2:DeleteSnapshot','ec2:StopInstances','ec2:StartInstances','autoscaling:SetInstanceProtection',
                                  'autoscaling:UpdateAutoScalingGroup','autoscaling:SetDesiredCapacity','autoscaling:TerminateInstanceInAutoScalingGroup'],
         'Resource':'*'}]}


def primary_policy(state):
    bucket=state['bucket']
    return {'Version':'2012-10-17','Statement':[
        {'Effect':'Allow','Action':'s3:PutObject','Resource':'arn:aws:s3:::'+bucket+'/artifacts/*',
         'Condition':{'DateLessThan':{'aws:CurrentTime':state['permission_expires']}}},
        {'Effect':'Allow','Action':'s3:GetObject','Resource':'arn:aws:s3:::'+bucket+'/results/*',
         'Condition':{'DateLessThan':{'aws:CurrentTime':state['permission_expires']}}}]}


class API:
    def __init__(self,profile=None):self.profile=profile
    def __call__(self,service,operation,*args):
        command=['aws',service,operation,'--region',REGION,'--output','json']
        if self.profile:command+=['--profile',self.profile]
        p=subprocess.run(command+list(args),capture_output=True,text=True,timeout=60)
        if p.returncode:raise RuntimeError(service+':'+operation+': '+p.stderr.strip())
        return json.loads(p.stdout) if p.stdout.strip() else {}
    def account(self):
        if self('sts','get-caller-identity')['Account']!=ACCOUNT:raise RuntimeError('wrong account; no mutations permitted')
    def upload(self,bucket,key,value):
        data=json.dumps(value,indent=2).encode()
        with tempfile.TemporaryDirectory(prefix='spot-control-') as directory:
            p=Path(directory)/'control.json';p.write_bytes(data);p.chmod(0o600)
            self('s3api','put-object','--bucket',bucket,'--key',key,'--body',str(p),
                 '--server-side-encryption','AES256','--checksum-algorithm','SHA256',
                 '--metadata','sha256='+hashlib.sha256(data).hexdigest())


def save(api,state,stage):
    state['stage']=stage
    api.upload(state['bucket'],'control/infra-ledger-current.json',state)
    print(json.dumps({'scope':state['scope'],'stage':stage,'capacity_request_is_build_or_test_success':False}),flush=True)


def create(api,state):
    api.account();name=state['name'];bucket=state['bucket']
    # An existing group or role is not ours to overwrite/retry blindly.
    if api('autoscaling','describe-auto-scaling-groups','--auto-scaling-group-names',name)['AutoScalingGroups']:
        raise RuntimeError('scope already exists; reconcile its cloud ledger, do not recreate')
    policies=api('iam','list-role-policies','--role-name','nixos-ec2-ssm-role')['PolicyNames']
    if set(policies)!=set(BASELINE):raise RuntimeError('unknown production IAM changes; no temporary permission installed')
    for key,value in BASELINE.items():
        if digest(api('iam','get-role-policy','--role-name','nixos-ec2-ssm-role','--policy-name',key)['PolicyDocument'])!=value:
            raise RuntimeError('production baseline policy changed')
    image=api('ec2','describe-images','--image-ids',AMI)['Images']
    if len(image)!=1 or image[0]['State']!='available' or image[0]['Architecture']!='arm64':raise RuntimeError('base image unavailable')
    api('s3api','create-bucket','--bucket',bucket,'--create-bucket-configuration',json.dumps({'LocationConstraint':REGION}))
    save(api,state,'bucket-created-capacity-zero')
    api('s3api','put-public-access-block','--bucket',bucket,'--public-access-block-configuration',json.dumps({k:True for k in ['BlockPublicAcls','IgnorePublicAcls','BlockPublicPolicy','RestrictPublicBuckets']}))
    api('s3api','put-bucket-ownership-controls','--bucket',bucket,'--ownership-controls',json.dumps({'Rules':[{'ObjectOwnership':'BucketOwnerEnforced'}]}))
    api('s3api','put-bucket-encryption','--bucket',bucket,'--server-side-encryption-configuration',json.dumps({'Rules':[{'ApplyServerSideEncryptionByDefault':{'SSEAlgorithm':'AES256'}}]}))
    api('s3api','put-bucket-tagging','--bucket',bucket,'--tagging',json.dumps({'TagSet':state['tags']}))
    api('s3api','put-bucket-lifecycle-configuration','--bucket',bucket,'--lifecycle-configuration',json.dumps({'Rules':[{'ID':'short-lived-proof','Status':'Enabled','Filter':{'Prefix':''},'Expiration':{'Days':1},'AbortIncompleteMultipartUpload':{'DaysAfterInitiation':1}}]}))
    api.upload(bucket,'control/creator-program.json',{'source':Path(__file__).read_text(),'sha256':state['creator_script_sha256']})
    trust={'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':'ec2.amazonaws.com'},'Action':'sts:AssumeRole'}]}
    role=api('iam','create-role','--role-name',name,'--assume-role-policy-document',json.dumps(trust),'--tags',json.dumps(state['tags']))['Role'];state['role_arn']=role['Arn'];save(api,state,'role-created-capacity-zero')
    api('iam','attach-role-policy','--role-name',name,'--policy-arn',CORE)
    api('iam','put-role-policy','--role-name',name,'--policy-name','DisposableAttestationAndArtifacts','--policy-document',json.dumps(scoped_policy(state)))
    profile=api('iam','create-instance-profile','--instance-profile-name',name,'--tags',json.dumps(state['tags']))['InstanceProfile'];state['profile_arn']=profile['Arn']
    api('iam','add-role-to-instance-profile','--instance-profile-name',name,'--role-name',name)
    template={'ImageId':AMI,'InstanceType':state['instance_type'],'IamInstanceProfile':{'Name':name},
              'SecurityGroupIds':['sg-065aa5f3bd3cac988'],'MetadataOptions':{'HttpTokens':'required','HttpEndpoint':'enabled'},
              'InstanceInitiatedShutdownBehavior':'terminate',
              'BlockDeviceMappings':[{'DeviceName':'/dev/xvda','Ebs':{'VolumeSize':32,'VolumeType':'gp3','Encrypted':True,'DeleteOnTermination':True}}],
              'TagSpecifications':[{'ResourceType':kind,'Tags':state['tags']} for kind in ['instance','volume']]}
    lt=api('ec2','create-launch-template','--launch-template-name',name,'--client-token',name,'--launch-template-data',json.dumps(template),
           '--tag-specifications',json.dumps([{'ResourceType':'launch-template','Tags':state['tags']}]))['LaunchTemplate'];state['LT']=lt['LaunchTemplateId'];save(api,state,'profile-LT-created-capacity-zero')
    mixed={'LaunchTemplate':{'LaunchTemplateSpecification':{'LaunchTemplateId':state['LT'],'Version':'1'},'Overrides':[{'InstanceType':state['instance_type']}]},
           'InstancesDistribution':{'OnDemandBaseCapacity':0,'OnDemandPercentageAboveBaseCapacity':0,'SpotAllocationStrategy':'lowest-price','SpotInstancePools':1,'SpotMaxPrice':state['spot_hourly_ceiling']}}
    for attempt in range(12):
        try:
            api('autoscaling','create-auto-scaling-group','--auto-scaling-group-name',name,'--min-size','0','--max-size','1','--desired-capacity','0',
                '--vpc-zone-identifier','subnet-0500a35263dc62859','--no-new-instances-protected-from-scale-in','--no-capacity-rebalance',
                '--mixed-instances-policy',json.dumps(mixed),'--tags',json.dumps([{**t,'PropagateAtLaunch':True} for t in state['tags']]))
            break
        except RuntimeError as error:
            # Only definite pre-launch IAM propagation rejection is retryable.
            if 'Invalid IAM Instance Profile' not in str(error) and 'InvalidIamInstanceProfile' not in str(error):raise
            save(api,state,'IAM-profile-propagation-rejected-capacity-zero');time.sleep(5)
    else:raise RuntimeError('profile propagation not confirmed; no capacity requested')
    api('autoscaling','put-scheduled-update-group-action','--auto-scaling-group-name',name,'--scheduled-action-name',name+'-off',
        '--start-time',state['expires'],'--min-size','0','--max-size','0','--desired-capacity','0')
    actions=api('autoscaling','describe-scheduled-actions','--auto-scaling-group-name',name)['ScheduledUpdateGroupActions']
    if not any(x['ScheduledActionName']==name+'-off' and not x.get('Recurrence')
               and datetime.fromisoformat(x['StartTime']).timestamp()==datetime.fromisoformat(state['expires']).timestamp()
               and all(type(x.get(k)) is int and x[k]==0 for k in ['MinSize','MaxSize','DesiredCapacity']) for x in actions):
        raise RuntimeError('native expiry not confirmed; no capacity requested')
    groups=api('autoscaling','describe-auto-scaling-groups','--auto-scaling-group-names',name)['AutoScalingGroups']
    if len(groups)!=1:raise RuntimeError('scope group unknown; no capacity requested')
    group=groups[0];distribution=group['MixedInstancesPolicy']['InstancesDistribution']
    if (group['DesiredCapacity']!=0 or group['Instances'] or group['NewInstancesProtectedFromScaleIn'] is not False
            or distribution['OnDemandBaseCapacity']!=0 or distribution['OnDemandPercentageAboveBaseCapacity']!=0
            or group['MixedInstancesPolicy']['LaunchTemplate']['LaunchTemplateSpecification']!={'LaunchTemplateId':state['LT'],'LaunchTemplateName':name,'Version':'1'}):
        raise RuntimeError('scope capacity/protection/Spot/LT is not the declared policy; no capacity requested')
    api('iam','put-role-policy','--role-name','nixos-ec2-ssm-role','--policy-name',state['primary_policy_name'],'--policy-document',json.dumps(primary_policy(state)))
    state['primary_policy_sha256']=digest(primary_policy(state));save(api,state,'native-expiry-readback-and-scoped-artifact-access-installed')
    # A slow setup cannot turn a bounded launch into an expired/unbounded one.
    if not 300<(datetime.fromisoformat(state['expires'])-datetime.now(timezone.utc)).total_seconds()<=7200:
        raise RuntimeError('insufficient remaining native expiry; no capacity requested')
    api('autoscaling','set-desired-capacity','--auto-scaling-group-name',name,'--desired-capacity','1')
    save(api,state,'capacity-requested-not-build-success')
    return state


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['plan','create']);parser.add_argument('--scope',required=True)
    parser.add_argument('--source-revision',required=True);parser.add_argument('--profile');args=parser.parse_args()
    state=plan(args.scope,args.source_revision);state['creator_script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if args.action=='plan':print(json.dumps(state,indent=2));return
    api=API(args.profile)
    # Preserve this exact operator program in cloud before any paid capacity.
    # Ledger saves are cloud-side; an interrupted operator never needs a laptop
    # file to identify the still-native-expiring disposable infrastructure.
    result=create(api,state);api.upload(state['bucket'],'control/creation-final.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
