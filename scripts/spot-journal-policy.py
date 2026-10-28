#!/usr/bin/env python3
"""Render minimal journal policies; never apply, seed, reset or delete state.

Bucket owner separately provisions private AES256 storage without expiration of
current journal objects. Runtime gets exact-object Get/Put and regional EC2 DescribeInstances only; service-side
policy rejects unconditional creation/overwrite independently of client code.
"""
import argparse
import json
import re


def policies(account,bucket,namespaces,region='ap-northeast-2'):
    if (not re.fullmatch('[a-z]{2}(-[a-z]+)+-[0-9]',region) or not re.fullmatch('[0-9]{12}',account) or not re.fullmatch('[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]',bucket)
            or not namespaces or len(namespaces)>100 or len(set(namespaces))!=len(namespaces)
            or any(not re.fullmatch('[a-zA-Z0-9_.-]{1,100}',n) or n in {'.','..'} for n in namespaces)):
        raise ValueError('exact account/bucket/unique namespaces required; no wildcards or force/reset')
    objects=['arn:aws:s3:::'+bucket+'/journal/'+n+'/state.json' for n in namespaces]
    return {'runtime_role':{'Version':'2012-10-17','Statement':[{'Effect':'Allow','Action':['s3:GetObject','s3:PutObject'],'Resource':objects,'Condition':{'StringEquals':{'s3:ResourceAccount':account}}},
            {'Effect':'Allow','Action':['ec2:DescribeInstances'],'Resource':'*','Condition':{'StringEquals':{'aws:RequestedRegion':region}}}]},

            'bucket':{'Version':'2012-10-17','Statement':[
                {'Sid':'DenyInsecureJournal','Effect':'Deny','Principal':'*','Action':'s3:*','Resource':['arn:aws:s3:::'+bucket,*objects],'Condition':{'Bool':{'aws:SecureTransport':'false'}}},
                {'Sid':'DenyUnconditionalJournalWrite','Effect':'Deny','Principal':'*','Action':'s3:PutObject','Resource':objects,'Condition':{'Null':{'s3:if-match':'true','s3:if-none-match':'true'},'Bool':{'s3:ObjectCreationOperation':'true'}}}]}}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--account',required=True);p.add_argument('--bucket',required=True);p.add_argument('--namespace',action='append',required=True);p.add_argument('--region',default='ap-northeast-2');a=p.parse_args();print(json.dumps(policies(a.account,a.bucket,a.namespace,a.region),indent=2))


if __name__=='__main__':main()
