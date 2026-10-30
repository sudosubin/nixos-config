#!/usr/bin/env python3
"""Read-only protection/deployment audit from standard-role CloudShell/AWS CLI.

One bounded SSM metadata reader, no guard invocation, initialization, release,
IAM change, service reload/restart, snapshot or approval publication.
"""
import argparse
from datetime import datetime,timezone
import importlib.util
import json
import os
from pathlib import Path
import time

spec=importlib.util.spec_from_file_location('audit_controller',Path(__file__).with_name('spot-canary-controller.py'));c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
spec=importlib.util.spec_from_file_location('protection_core',Path(__file__).parent.parent/'modules/linux/spot_protection.py');core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
COLLECTOR=core.COLLECTOR
decode=core.decode
diagnose=core.diagnose
fields=core.fields
signature=core.signature


def audit(api,asg,instance):
    api.account();groups=api('autoscaling','describe-auto-scaling-groups','--auto-scaling-group-names',asg)['AutoScalingGroups'];c.require(len(groups)==1 and groups[0]['AutoScalingGroupName']==asg,'ASG identity unknown');before=groups[0]
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
