#!/usr/bin/env python3
"""Disposable infrastructure expiry investigation, NEVER a production deadline.

CloudFormation's intentionally unsignalled CreationPolicy rolls back an empty
ASG first. Only independently verified native force-delete evidence permits a
later EMPTY-WORKLOAD protected Spot trial. No guest code/profile/keys/channels,
no public IPv4, no paid scheduler/controller. CFN/ASG are native provisioning;
EC2/EBS still cost money. Rollback failures are failures, not expiry success.
CloudShell-compatible; deterministic names/tags + CFN template metadata retain
recovery state without a local checkout/process after the one-off creation.
"""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time

ACCOUNT = '537112465379'
REGION = 'ap-northeast-2'
SUBNET = 'subnet-0500a35263dc62859'
SG = 'sg-065aa5f3bd3cac988'
PRODUCTION = 'nixos-ec2-asg'
AMI_OWNER = '137112412989'


def require(value, message):
    if not value:
        raise RuntimeError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class APIError(RuntimeError):
    def __init__(self, service, action, code, detail=''):
        self.service, self.action, self.code, self.detail = service, action, code, detail
        super().__init__(service+':'+action+':'+code+(':'+detail if detail else ''))


class API:
    def __init__(self, profile=None):
        self.profile = profile

    def __call__(self, service, action, *args):
        command = ['aws', service, action, '--region', REGION, '--output', 'json']
        if self.profile:
            command += ['--profile', self.profile]
        # Do not retry a possibly accepted provisioning/capacity mutation.
        import os
        env = {**os.environ, 'AWS_MAX_ATTEMPTS': '1'}
        result = subprocess.run(command+list(args), capture_output=True, text=True, timeout=60, env=env)
        if result.returncode:
            code = re.search(r'An error occurred \(([A-Za-z0-9_.-]+)\)', result.stderr)
            detail = result.stderr.split(' operation: ', 1)[-1].strip()[:1000] if code else ''
            raise APIError(service, action, code[1] if code else 'UnknownTransportOrCLIError', detail)
        return json.loads(result.stdout) if result.stdout.strip() else {}


def plan(scope, mode, image, revision, now=None):
    require(isinstance(scope, str) and re.fullmatch('[0-9a-f]{12}', scope), 'exact fresh scope required')
    require(mode in {'empty', 'protected'} and re.fullmatch('ami-[0-9a-f]{17}', image or ''), 'invalid mode/image')
    require(re.fullmatch('[0-9a-f]{40}', revision or ''), 'pinned source revision required')
    now = now or datetime.now(timezone.utc)
    require(now.utcoffset() is not None, 'aware clock required')
    name = 'nixos-protected-expiry-'+scope
    return {'schema': 1, 'scope': scope, 'name': name, 'role': name+'-cfn', 'mode': mode,
            'account': ACCOUNT, 'region': REGION, 'image': image, 'source_revision': revision,
            'created': now.isoformat(), 'off_at': (now+timedelta(minutes=4)).replace(microsecond=0).isoformat(),
            'wait_seconds': 90 if mode == 'empty' else 600, 'stack_timeout_minutes': 5 if mode == 'empty' else 15,
            'capacity_initial': 0, 'capacity_after_containment': 0 if mode == 'empty' else 1,
            'instance_type': 't4g.small', 'spot_hourly_ceiling': '0.010',
            'production_rollout': False, 'goal_complete': False}


def tags(state):
    return [{'Key': k, 'Value': v} for k, v in {
        'ManagedBy': 'nixos-spot-validation', 'Purpose': 'native-protected-expiry',
        'ScopeId': state['scope'], 'Disposable': 'true'}.items()]


def role_policy(state):
    arn = 'arn:aws:autoscaling:'+REGION+':'+ACCOUNT+':autoScalingGroup:*:autoScalingGroupName/'+state['name']
    return {'Version': '2012-10-17', 'Statement': [
        {'Effect': 'Allow', 'Action': ['autoscaling:CreateAutoScalingGroup', 'autoscaling:UpdateAutoScalingGroup',
         'autoscaling:DeleteAutoScalingGroup', 'autoscaling:SetInstanceProtection', 'autoscaling:CreateOrUpdateTags',
         'autoscaling:DeleteTags', 'autoscaling:PutScheduledUpdateGroupAction', 'autoscaling:DeleteScheduledAction'],
         'Resource': arn},
        {'Effect': 'Allow', 'Action': ['autoscaling:DescribeAutoScalingGroups', 'autoscaling:DescribeScalingActivities',
         'autoscaling:DescribeScheduledActions', 'ec2:DescribeLaunchTemplates', 'ec2:DescribeLaunchTemplateVersions',
         'ec2:DescribeSubnets', 'ec2:DescribeSecurityGroups', 'ec2:DescribeImages'], 'Resource': '*',
         'Condition': {'StringEquals': {'aws:RequestedRegion': REGION}}},
        {'Effect': 'Deny', 'Action': ['ec2:AttachVolume', 'ec2:DetachVolume', 'ec2:AssociateAddress',
         'ec2:DisassociateAddress', 'ec2:TerminateInstances', 'ec2:CreateSnapshot', 'ec2:DeleteSnapshot',
         'ec2:DeleteVolume', 'cloudformation:SignalResource'], 'Resource': '*'}]}


def launch_data(state):
    return {'ImageId': state['image'], 'InstanceType': state['instance_type'],
            'CreditSpecification': {'CpuCredits': 'standard'},
            'MetadataOptions': {'HttpTokens': 'required', 'HttpEndpoint': 'enabled'},
            'InstanceInitiatedShutdownBehavior': 'terminate',
            'NetworkInterfaces': [{'DeviceIndex': 0, 'AssociatePublicIpAddress': False, 'Groups': [SG]}],
            'BlockDeviceMappings': [{'DeviceName': '/dev/xvda', 'Ebs': {'VolumeSize': 8, 'VolumeType': 'gp3',
                                      'Encrypted': True, 'DeleteOnTermination': True}}],
            'TagSpecifications': [{'ResourceType': kind, 'Tags': tags(state)} for kind in ['instance', 'volume']]}


def template(state, lt, program):
    require(re.fullmatch('lt-[0-9a-f]{17}', lt), 'exact launch template required')
    return {'AWSTemplateFormatVersion': '2010-09-09',
            'Description': 'Disposable native rollback investigation; never production safety authority',
            'Metadata': {'Investigation': state, 'CreatorProgram': program,
                         'CreatorSHA256': hashlib.sha256(program.encode()).hexdigest(),
                         'RolePolicySHA256': digest(role_policy(state))},
            'Resources': {
                'Group': {'Type': 'AWS::AutoScaling::AutoScalingGroup', 'DeletionPolicy': 'Delete',
                    'Properties': {'AutoScalingGroupName': state['name'], 'MinSize': '0', 'MaxSize': '1',
                     'DesiredCapacity': '0', 'VPCZoneIdentifier': [SUBNET], 'CapacityRebalance': False,
                     'DeletionProtection': 'none', 'NewInstancesProtectedFromScaleIn': True,
                     'HealthCheckType': 'EC2', 'HealthCheckGracePeriod': 300,
                     'MixedInstancesPolicy': {'LaunchTemplate': {'LaunchTemplateSpecification': {
                         'LaunchTemplateId': lt, 'Version': '1'}, 'Overrides': [{'InstanceType': state['instance_type']}]},
                         'InstancesDistribution': {'OnDemandBaseCapacity': 0, 'OnDemandPercentageAboveBaseCapacity': 0,
                          'SpotAllocationStrategy': 'lowest-price', 'SpotInstancePools': 1,
                          'SpotMaxPrice': state['spot_hourly_ceiling']}},
                     'Tags': [{**t, 'PropagateAtLaunch': True} for t in tags(state)]}},
                'Off': {'Type': 'AWS::AutoScaling::ScheduledAction', 'DeletionPolicy': 'Delete',
                    'Properties': {'AutoScalingGroupName': {'Ref': 'Group'}, 'StartTime': state['off_at'],
                                   'MinSize': 0, 'MaxSize': 0, 'DesiredCapacity': 0}},
                # No handle/presigned URL or guest signal exists. This resource
                # MUST fail and roll back; CREATE_COMPLETE would be suspicious.
                'Deadline': {'Type': 'AWS::CloudFormation::WaitCondition', 'DependsOn': ['Group', 'Off'],
                    'CreationPolicy': {'ResourceSignal': {'Count': 1, 'Timeout': 'PT'+str(state['wait_seconds'])+'S'}}}},
            'Outputs': {'GroupName': {'Value': {'Ref': 'Group'}}}}


def absent(api, service, action, args, code):
    try:
        api(service, action, *args)
    except APIError as error:
        require(error.code == code, 'absence not confirmed: '+str(error))
        return
    raise RuntimeError('scope already exists; reconcile cloud state, never overwrite/recreate')


def inspect(api, state):
    stack = api('cloudformation', 'describe-stacks', '--stack-name', state['name'])['Stacks']
    require(len(stack) == 1, 'stack observation unknown')
    resources = api('cloudformation', 'list-stack-resources', '--stack-name', state['name'])['StackResourceSummaries']
    groups = api('autoscaling', 'describe-auto-scaling-groups', '--auto-scaling-group-names', state['name'])['AutoScalingGroups']
    return {'stack': stack[0], 'resources': resources, 'groups': groups,
            'all_observed_complete_is_goal_success': False}


def containment(api, state, stack_id, lt, policy, doc):
    observed = inspect(api, state);stack = observed['stack']
    require(stack['StackId'] == stack_id and stack['StackStatus'] == 'CREATE_IN_PROGRESS'
            and stack.get('DisableRollback') is False and stack['TimeoutInMinutes'] == state['stack_timeout_minutes']
            and stack['RoleARN'] == 'arn:aws:iam::'+ACCOUNT+':role/'+state['role'], 'native stack rollback not armed')
    actual = api('cloudformation', 'get-template', '--stack-name', stack_id)['TemplateBody']
    if isinstance(actual, str):actual = json.loads(actual)
    require(actual == doc, 'cloud template differs')
    statuses = {r['LogicalResourceId']: r['ResourceStatus'] for r in observed['resources']}
    require(statuses == {'Group': 'CREATE_COMPLETE', 'Off': 'CREATE_COMPLETE', 'Deadline': 'CREATE_IN_PROGRESS'},
            'native deadline has not started; no capacity')
    group = observed['groups'];require(len(group) == 1, 'group unknown')
    group = group[0]
    require(group['DesiredCapacity'] == 0 and not group['Instances'] and group['MinSize'] == 0 and group['MaxSize'] == 1
            and group['NewInstancesProtectedFromScaleIn'] is True and group['CapacityRebalance'] is False
            and group.get('DeletionProtection', 'none') == 'none', 'empty protected group differs')
    mixed = group['MixedInstancesPolicy'];require(mixed['LaunchTemplate']['LaunchTemplateSpecification']['LaunchTemplateId'] == lt
            and mixed['LaunchTemplate']['LaunchTemplateSpecification']['Version'] == '1'
            and mixed['InstancesDistribution']['OnDemandBaseCapacity'] == 0
            and mixed['InstancesDistribution']['OnDemandPercentageAboveBaseCapacity'] == 0, 'numeric LT/Spot policy differs')
    actions = api('autoscaling', 'describe-scheduled-actions', '--auto-scaling-group-name', state['name'])['ScheduledUpdateGroupActions']
    require(len(actions) == 1 and all(actions[0][k] == 0 for k in ['MinSize', 'MaxSize', 'DesiredCapacity'])
            and datetime.fromisoformat(actions[0]['StartTime']).timestamp() == datetime.fromisoformat(state['off_at']).timestamp(), 'native zero request differs')
    versions = api('ec2', 'describe-launch-template-versions', '--launch-template-id', lt, '--versions', '1')['LaunchTemplateVersions']
    require(len(versions) == 1 and versions[0]['VersionNumber'] == 1 and versions[0]['LaunchTemplateId'] == lt, 'launch template identity unknown')
    data = versions[0]['LaunchTemplateData'];expected = launch_data(state)
    require(not {'IamInstanceProfile', 'UserData', 'KeyName'} & data.keys()
            and all(data.get(k) == v for k, v in expected.items()), 'guest authority/network/root/LT changed; no capacity')
    remote = api('iam', 'get-role-policy', '--role-name', state['role'], '--policy-name', 'OnlyThisDisposableGroup')['PolicyDocument']
    require(remote == policy, 'native cleanup execution policy differs')
    stack_created = datetime.fromisoformat(stack['CreationTime']).timestamp()
    require(0 <= time.time()-stack_created < state['stack_timeout_minutes']*60-60, 'absolute native stack timeout exhausted')
    remaining = datetime.fromisoformat(state['off_at']).timestamp()-time.time()
    require(60 < remaining <= 240, 'setup deadline exhausted; no capacity')
    return observed


def create(api, state, force_evidence=None):
    require(api('sts', 'get-caller-identity')['Account'] == ACCOUNT, 'wrong account')
    require(not api('autoscaling', 'describe-auto-scaling-groups', '--auto-scaling-group-names', state['name'])['AutoScalingGroups'], 'existing group')
    absent(api, 'iam', 'get-role', ['--role-name', state['role']], 'NoSuchEntity')
    absent(api, 'ec2', 'describe-launch-templates', ['--launch-template-names', state['name']], 'InvalidLaunchTemplateName.NotFoundException')
    # Missing stack uses ValidationError; additionally verify there are no live
    # named stacks, rather than treating every ValidationError as absence.
    summaries = api('cloudformation', 'list-stacks')['StackSummaries']
    require(not any(s['StackName'] == state['name'] and s['StackStatus'] != 'DELETE_COMPLETE' for s in summaries), 'existing stack')
    if state['mode'] == 'protected':
        require(force_evidence is not None, 'first prove empty native force-delete without paid capacity')
        validate_force_evidence(force_evidence)
        verify_force_evidence(api, force_evidence)
    image = api('ec2', 'describe-images', '--image-ids', state['image'])['Images']
    require(len(image) == 1 and image[0]['OwnerId'] == AMI_OWNER and image[0]['Architecture'] == 'arm64'
            and image[0]['State'] == 'available' and image[0]['RootDeviceName'] == '/dev/xvda'
            and len(image[0]['BlockDeviceMappings']) == 1 and image[0]['BlockDeviceMappings'][0]['Ebs']['VolumeSize'] <= 8, 'not the public empty-workload AMI')
    policy = role_policy(state)
    trust = {'Version': '2012-10-17', 'Statement': [{'Effect': 'Allow', 'Principal': {'Service': 'cloudformation.amazonaws.com'}, 'Action': 'sts:AssumeRole'}]}
    api('iam', 'create-role', '--role-name', state['role'], '--assume-role-policy-document', json.dumps(trust), '--tags', json.dumps(tags(state)))
    api('iam', 'put-role-policy', '--role-name', state['role'], '--policy-name', 'OnlyThisDisposableGroup', '--policy-document', json.dumps(policy))
    lt = api('ec2', 'create-launch-template', '--launch-template-name', state['name'], '--client-token', state['name'],
             '--launch-template-data', json.dumps(launch_data(state)), '--tag-specifications', json.dumps([{'ResourceType': 'launch-template', 'Tags': tags(state)}]))['LaunchTemplate']['LaunchTemplateId']
    doc = template(state, lt, Path(__file__).read_text())
    with tempfile.TemporaryDirectory(prefix='protected-expiry-') as folder:
        path = Path(folder)/'template.json';path.write_text(json.dumps(doc));path.chmod(0o600)
        api('cloudformation', 'validate-template', '--template-body', 'file://'+str(path))
        # IAM/role validation errors before CreateStack may be retried by the
        # operator only after definite nonacceptance. Never blind replay here.
        reply = api('cloudformation', 'create-stack', '--stack-name', state['name'], '--template-body', 'file://'+str(path),
                    '--role-arn', 'arn:aws:iam::'+ACCOUNT+':role/'+state['role'], '--on-failure', 'ROLLBACK',
                    '--timeout-in-minutes', str(state['stack_timeout_minutes']), '--tags', json.dumps(tags(state)),
                    '--client-request-token', state['name'])
    stack_id = reply['StackId']
    # Waiting observes cloud provisioning; it does NOT implement the expiry.
    limit = time.monotonic()+100
    while True:
        observed = inspect(api, state)
        statuses = {r['LogicalResourceId']: r['ResourceStatus'] for r in observed['resources']}
        if statuses.get('Deadline') == 'CREATE_IN_PROGRESS':break
        require(observed['stack']['StackStatus'] == 'CREATE_IN_PROGRESS' and time.monotonic() < limit, 'native deadline not confirmed; no capacity')
        time.sleep(2)
    observed = containment(api, state, stack_id, lt, policy, doc)
    if state['mode'] == 'protected':
        api('autoscaling', 'set-desired-capacity', '--auto-scaling-group-name', state['name'], '--desired-capacity', '1')
    return {'state': state, 'StackId': stack_id, 'LT': lt, 'containment': observed,
            'capacity_requested': state['mode'] == 'protected', 'expiry_or_termination_verified': False}


def validate_force_evidence(value):
    """A receipt/manifest assertion alone is insufficient: inspect exact raw API event."""
    state = value['state'];require(state['mode'] == 'empty' and re.fullmatch('[0-9a-f]{12}', state['scope'])
        and state['name'] == 'nixos-protected-expiry-'+state['scope'] and state['role'] == state['name']+'-cfn'
        and state['account'] == ACCOUNT and state['region'] == REGION, 'not an empty native probe')
    require(value['stack_status'] == 'ROLLBACK_COMPLETE' and value['group_absent'] is True, 'empty rollback incomplete')
    event = value['event'];request = event['requestParameters']
    require(event['eventSource'] == 'autoscaling.amazonaws.com' and event['eventName'] == 'DeleteAutoScalingGroup'
            and event['awsRegion'] == REGION and event['recipientAccountId'] == ACCOUNT and not event.get('errorCode')
            and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}', event.get('eventID', ''))
            and request['autoScalingGroupName'] == state['name'] and request.get('forceDelete') is True
            and event['userIdentity']['sessionContext']['sessionIssuer']['arn'] == 'arn:aws:iam::'+ACCOUNT+':role/'+state['role'],
            'no exact native CFN force-delete evidence')
    require(event['userAgent'] == 'cloudformation.amazonaws.com' or event['userIdentity'].get('invokedBy') == 'cloudformation.amazonaws.com', 'not native CloudFormation cleanup')
    return value


def event_projection(event):
    """Retain only the exact deletion fact, never access identifiers/IPs/URLs."""
    identity = event.get('userIdentity', {})
    return {**{k: event.get(k) for k in ['eventID', 'eventTime', 'eventSource', 'eventName', 'awsRegion',
             'recipientAccountId', 'userAgent', 'errorCode', 'requestParameters']},
            'userIdentity': {'invokedBy': identity.get('invokedBy'), 'sessionContext': {
                'sessionIssuer': {'arn': identity.get('sessionContext', {}).get('sessionIssuer', {}).get('arn')}}}}


def verify_force_evidence(api, value):
    validate_force_evidence(value);state = value['state']
    stack = api('cloudformation', 'describe-stacks', '--stack-name', value['StackId'])['Stacks']
    require(len(stack) == 1 and stack[0]['StackStatus'] == 'ROLLBACK_COMPLETE'
            and stack[0]['StackName'] == state['name'] and stack[0]['StackId'] == value['StackId'], 'native rollback not independently confirmed')
    doc = api('cloudformation', 'get-template', '--stack-name', value['StackId'])['TemplateBody']
    if isinstance(doc, str):doc = json.loads(doc)
    require(doc['Metadata']['Investigation'] == state, 'native probe deployment differs')
    require(not api('autoscaling', 'describe-auto-scaling-groups', '--auto-scaling-group-names', state['name'])['AutoScalingGroups'], 'native group still exists')
    events = api('cloudtrail', 'lookup-events', '--lookup-attributes',
                 'AttributeKey=EventId,AttributeValue='+value['event']['eventID'])
    require(not events.get('NextToken') and len(events['Events']) == 1
            and event_projection(json.loads(events['Events'][0]['CloudTrailEvent'])) == value['event'], 'native force-delete event not independently confirmed')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'create', 'status'])
    parser.add_argument('--scope', required=True);parser.add_argument('--mode', choices=['empty', 'protected'], default='empty')
    parser.add_argument('--image', required=True);parser.add_argument('--source-revision', required=True)
    parser.add_argument('--force-evidence', type=Path);parser.add_argument('--profile');args = parser.parse_args()
    state = plan(args.scope, args.mode, args.image, args.source_revision)
    if args.action == 'plan':print(json.dumps({'state': state, 'policy': role_policy(state), 'launch': launch_data(state)}, indent=2));return
    api = API(args.profile)
    if args.action == 'status':
        require(api('sts', 'get-caller-identity')['Account'] == ACCOUNT, 'wrong account');print(json.dumps(inspect(api, state), indent=2));return
    evidence = json.loads(args.force_evidence.read_text()) if args.force_evidence else None
    print(json.dumps(create(api, state, evidence), indent=2))


if __name__ == '__main__':main()
