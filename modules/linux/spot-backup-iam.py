#!/usr/bin/env python3
"""Render least-privilege snapshot policy. Does not install IAM or call AWS."""
import argparse
import json
import re


KEYS = ['ManagedBy', 'Purpose', 'BackupSchema', 'BackupSet', 'SourceVolume',
        'AttemptId', 'Protected', 'ColdCapture', 'BackupStatus']


def policy(account, region, volume, backup_set):
    if (not re.fullmatch(r'[0-9]{12}', account) or not re.fullmatch(r'[a-z0-9-]+', region)
            or not re.fullmatch(r'vol-[0-9a-f]{8,17}', volume)
            or not re.fullmatch(r'[a-zA-Z0-9_.-]{1,100}', backup_set)):
        raise ValueError('invalid backup policy identity')
    prefix = f'arn:aws:ec2:{region}:{account}:'
    # Snapshot ARNs have an empty account segment; EC2 plus immutable ownership
    # tags enforce the boundary, rather than an invalid account-qualified ARN.
    snapshots = f'arn:aws:ec2:{region}::snapshot/*'
    identity = {'ManagedBy': 'nixos-spot-schedule', 'Purpose': 'daily-home', 'BackupSchema': '1',
                'BackupSet': backup_set, 'SourceVolume': volume, 'Protected': 'false'}
    request = {'aws:RequestTag/' + key: value for key, value in identity.items()}
    request.update({'aws:RequestTag/ColdCapture': 'unverified', 'aws:RequestTag/BackupStatus': 'pending'})
    resource = {'ec2:ResourceTag/' + key: value for key, value in identity.items()}
    return {'Version': '2012-10-17', 'Statement': [
        {'Sid': 'MetadataOnlyInRegion', 'Effect': 'Allow',
         'Action': ['ec2:DescribeVolumes', 'ec2:DescribeSnapshots', 'ec2:DescribeImages'],
         'Resource': '*', 'Condition': {'StringEquals': {'aws:RequestedRegion': region}}},
        {'Sid': 'OnlyExactSourceVolume', 'Effect': 'Allow', 'Action': 'ec2:CreateSnapshot',
         'Resource': prefix + 'volume/' + volume},
        {'Sid': 'SnapshotCreateWithRequiredIdentity', 'Effect': 'Allow', 'Action': 'ec2:CreateSnapshot',
         'Resource': snapshots, 'Condition': {'StringEquals': request,
             'StringLike': {'aws:RequestTag/AttemptId': 'backup-' + '?'*32},
             'ForAllValues:StringEquals': {'aws:TagKeys': KEYS}}},
        {'Sid': 'TagsOnlyWithAtomicSnapshotCreate', 'Effect': 'Allow', 'Action': 'ec2:CreateTags',
         'Resource': snapshots, 'Condition': {'StringEquals': {**request, 'ec2:CreateAction': 'CreateSnapshot'},
             'StringLike': {'aws:RequestTag/AttemptId': 'backup-' + '?'*32},
             'ForAllValues:StringEquals': {'aws:TagKeys': KEYS}}},
        {'Sid': 'OnlyAdvanceOwnedCaptureStatus', 'Effect': 'Allow', 'Action': 'ec2:CreateTags',
         'Resource': snapshots, 'Condition': {'StringEquals': resource,
             'StringLike': {'ec2:ResourceTag/AttemptId': 'backup-' + '?'*32},
             'StringEqualsIfExists': {'aws:RequestTag/ColdCapture': 'verified', 'aws:RequestTag/BackupStatus': 'successful'},
             'ForAllValues:StringEquals': {'aws:TagKeys': ['ColdCapture', 'BackupStatus']}}},
        {'Sid': 'DeleteOnlyOwnedUnprotectedSet', 'Effect': 'Allow', 'Action': 'ec2:DeleteSnapshot',
         'Resource': snapshots, 'Condition': {'StringEquals': {**resource,
             'ec2:ResourceTag/ColdCapture': ['unverified', 'verified'],
             'ec2:ResourceTag/BackupStatus': ['pending', 'successful']},
             'StringLike': {'ec2:ResourceTag/AttemptId': 'backup-' + '?'*32}}},
    ]}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--account', required=True);p.add_argument('--region', required=True)
    p.add_argument('--volume', required=True);p.add_argument('--set', required=True)
    args = p.parse_args()
    print(json.dumps(policy(args.account, args.region, args.volume, args.set), indent=2))
