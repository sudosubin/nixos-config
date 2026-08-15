<!-- markdownlint-disable MD013 MD014 -->

# Linux on Cloud (AWS EC2)

`modules/linux` 를 headless AWS EC2(arm64 / Graviton) 서버로 배포/운영하기 위한 AWS CLI 가이드입니다.
접속은 **SSM Session Manager** 를 기본 채널로 사용하며, 보안 그룹에 인바운드 포트를 열지 않습니다.

> **2026-08-15 부로 Spot + Auto Scaling Group 구성으로 전환했습니다.** 인스턴스는 더 이상
> 고정 ID로 상시 실행되지 않고, Spot 회수 시 ASG 가 자동으로 새 인스턴스를 띄웁니다.
> `/home` 과 Elastic IP 는 인스턴스 교체와 무관하게 유지되지만, **인스턴스 ID 는 매번 바뀝니다.**
> 아래 명령들은 그 점을 반영해 갱신되었습니다.

## 리소스 정보

| 항목 | 값 |
|------|----|
| Auto Scaling Group | `nixos-ec2-asg` (min=max=desired=1, 단일 인스턴스 유지) |
| Launch Template | `nixos-ec2-spot-lt` (`lt-01468c818ef1bb11a`) |
| Instance Types | `m6g.large` / `m7g.large` / `m8g.large` / `m6gd.large` (Spot, `price-capacity-optimized`, 2 vCPU / 8 GiB) |
| Region / AZ | `ap-northeast-2` (Seoul) / `ap-northeast-2d` (subnet-0500a35263dc62859) |
| AWS Profile | `sudosubin` |
| Root Disk | gp3 64 GiB, `DeleteOnTermination=true` (인스턴스 교체 시 AMI 기준으로 새로 생성됨 — **영구 아님**) |
| `/home` 데이터 | 별도 EBS gp3 80 GiB (`vol-09fea2ff4615b1088`, `Name=nixos-ec2-home`, ap-northeast-2d 고정) — 인스턴스 교체와 무관하게 유지 |
| Elastic IP | `52.78.88.164` (`eipalloc-04d6e702ea3b20bd7`) — 인스턴스 교체와 무관하게 유지 |
| Security Group | `sg-065aa5f3bd3cac988` (인바운드 없음) |
| IAM Instance Profile | `nixos-ec2-ssm-profile` (role `nixos-ec2-ssm-role`: `AmazonSSMManagedInstanceCore` + 인라인 `SpotHomeVolumeAndEip`) |
| OS user | `sudosubin` (SSH key `~/.ssh/id_ed25519`) |
| 배포용 AMI | `ami-0f82d67a7f735cab1` (`nixos-ec2-spot-*`, `modules/linux/spot-home-volume.nix` 반영됨) |
| Flake target | `github:sudosubin/nixos-config#linux` |

> 모든 명령은 `--profile sudosubin --region ap-northeast-2` 를 사용합니다.
> 편의상 `export AWS_PROFILE=sudosubin AWS_REGION=ap-northeast-2` 를 설정하면 아래에서 두 플래그를 생략할 수 있습니다.

## 0. 사전 준비 (로컬)

```sh
# AWS CLI v2 + Session Manager plugin 필요
$ aws --version
$ session-manager-plugin --version

# NixOS 환경에서는 다음 패키지 제공: awscli2, ssm-session-manager-plugin
```

## 1. 현재 인스턴스 ID 조회

인스턴스는 ASG 가 관리하므로 ID 가 고정되어 있지 않습니다. 아래 명령으로 항상 먼저 현재 ID 를 조회하세요.

```sh
$ INSTANCE_ID=$(aws autoscaling describe-auto-scaling-groups \
    --auto-scaling-group-names nixos-ec2-asg \
    --profile sudosubin --region ap-northeast-2 \
    --query "AutoScalingGroups[0].Instances[0].InstanceId" --output text)
$ echo "$INSTANCE_ID"
```

이후 모든 `--instance-ids`/`--target` 자리에 이 값을 사용합니다.

## 2. SSM 연결 방법

### 2-1. 대화형 셸 (Session Manager)

```sh
$ aws ssm start-session \
    --target "$INSTANCE_ID" \
    --profile sudosubin --region ap-northeast-2
```

- `ssm-user` 로 접속됩니다. `sudo -i` 또는 `sudo su - sudosubin` 로 전환하세요.
- 인바운드 포트가 전혀 필요 없고, AWS TLS 터널로 종단간 암호화됩니다.

### 2-2. 인스턴스가 SSM 에 등록되어 있는지 확인

```sh
$ aws ssm describe-instance-information \
    --filters "Key=InstanceIds,Values=$INSTANCE_ID" \
    --query "InstanceInformationList[0].PingStatus" --output text
# => Online
```

### 2-3. 한 번에 명령 실행 (run-command)

```sh
$ CMD_ID=$(aws ssm send-command \
    --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters '{"commands":["uptime","free -h","df -h /"]}' \
    --query "Command.CommandId" --output text)

$ aws ssm get-command-invocation \
    --command-id "$CMD_ID" --instance-id "$INSTANCE_ID" \
    --query "StandardOutputContent" --output text
```

## 3. SSH over SSM (권장)

SSM 터널 위에서 SSH 를 사용합니다. 포트를 열지 않으면서도 `scp`, `nixos-rebuild --target-host`, 포트 포워딩이 가능합니다.
인스턴스 ID 가 매번 바뀌므로, `HostName` 을 고정하지 말고 **ProxyCommand 안에서 매번 ASG 를 조회**하도록 구성합니다.

`~/.ssh/config` 에 추가:

```sshconfig
Host nixos-ec2
  User sudosubin
  IdentityFile ~/.ssh/id_ed25519
  ProxyCommand bash -c 'aws ssm start-session --target $(aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names nixos-ec2-asg --profile sudosubin --region ap-northeast-2 --query "AutoScalingGroups[0].Instances[0].InstanceId" --output text) --document-name AWS-StartSSHSession --parameters portNumber=%p --profile sudosubin --region ap-northeast-2'
```

사용:

```sh
$ ssh nixos-ec2
$ ssh nixos-ec2 "uptime"
$ scp ./file nixos-ec2:/home/sudosubin/
```

> Elastic IP(`52.78.88.164`)는 고정이지만 SSM/SSH-over-SSM 은 IP 가 아니라 인스턴스 ID 로 접속하므로,
> 위 ProxyCommand 방식이 IP 를 직접 다루는 것보다 항상 안전합니다.

### 3-1. 포트 포워딩 (예: 원격 8080 → 로컬 8080)

```sh
$ aws ssm start-session \
    --target "$INSTANCE_ID" \
    --document-name AWS-StartPortForwardingSession \
    --parameters '{"portNumber":["8080"],"localPortNumber":["8080"]}' \
    --profile sudosubin --region ap-northeast-2
```

## 4. 인스턴스 시작 / 중지 / 상태 (비용 절감)

Spot + ASG 구조에서는 개별 인스턴스를 stop/start 하지 않습니다. **ASG 의 desired capacity 를 0 으로 낮춰 "일시정지"**하고,
다시 1 로 올려 재개합니다.

```sh
# 상태 확인
$ aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names nixos-ec2-asg \
    --query "AutoScalingGroups[0].Instances[].[InstanceId,InstanceType,LifecycleState]" --output text

# 일시정지 (컴퓨트/IPv4 과금 정지 — /home 볼륨과 EIP 는 그대로 남아 계속 과금)
$ aws autoscaling update-auto-scaling-group --auto-scaling-group-name nixos-ec2-asg \
    --min-size 0 --max-size 0 --desired-capacity 0

# 재개
$ aws autoscaling update-auto-scaling-group --auto-scaling-group-name nixos-ec2-asg \
    --min-size 1 --max-size 1 --desired-capacity 1

# 재개 후 새 인스턴스 ID 다시 조회 (섹션 1) 후 SSM 등록 대기
$ aws ssm describe-instance-information \
    --filters "Key=InstanceIds,Values=$INSTANCE_ID" \
    --query "InstanceInformationList[0].PingStatus" --output text
```

> desired capacity 를 0 으로 내리면 EIP 는 자동으로 연결 해제되고, 1 로 올리면 `associate-eip.service` 가
> 부팅 시 다시 붙입니다. `/home` 볼륨도 `attach-home-volume.service` 가 동일하게 재부착합니다.

## 5. 배포 (nixos-rebuild)

빌드는 인스턴스에서 네이티브(arm64)로 수행합니다.

> **중요 — 이전과 달라진 점**: 루트 디스크는 이제 인스턴스 교체마다 AMI 기준으로 새로 생성되는
> **휘발성**입니다. 아래 방식으로 `nixos-rebuild switch` 를 돌리면 **지금 떠 있는 인스턴스에는**
> 바로 반영되지만, 다음 Spot 회수 후 새 인스턴스는 다시 옛 AMI 기준으로 부팅됩니다.
> 변경을 영구 반영하려면 반드시 **6번(AMI 재굽기)** 까지 진행하세요. `/home` 은 별도 볼륨이라
> 이 문제와 무관하게 항상 보존됩니다.

### 5-1. SSM run-command 로 배포 (임시 반영, 현재 인스턴스에만)

```sh
$ aws ssm send-command \
    --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --comment "nixos-rebuild switch" \
    --timeout-seconds 3600 \
    --parameters '{"executionTimeout":["3600"],"commands":["export NIX_CONFIG=\"experimental-features = nix-command flakes\"","nixos-rebuild switch --flake github:sudosubin/nixos-config#linux --refresh"]}' \
    --query "Command.CommandId" --output text
```

- 소스 빌드가 많으면 오래 걸립니다. 장시간 빌드는 아래처럼 백그라운드로 실행하고 상태 파일을 폴링하세요.

```sh
# 백그라운드(detached) 빌드 — SSM 명령 타임아웃에 영향받지 않음
$ aws ssm send-command --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunShellScript" --timeout-seconds 120 \
    --parameters '{"commands":["rm -f /tmp/deploy.status","export NIX_CONFIG=\"experimental-features = nix-command flakes\"","setsid bash -c '\''nixos-rebuild switch --flake github:sudosubin/nixos-config#linux --refresh --max-jobs 2 --cores 2 > /tmp/deploy.log 2>&1; echo $? > /tmp/deploy.status'\'' </dev/null >/dev/null 2>&1 &","echo started"]}'

# 진행/완료 확인
$ ssh nixos-ec2 'cat /tmp/deploy.status 2>/dev/null || tail -n3 /tmp/deploy.log'
```

### 5-2. 로컬에서 원격 배포 (SSH-over-SSM, 빌드는 원격)

```sh
$ nixos-rebuild switch \
    --flake .#linux \
    --target-host nixos-ec2 --build-host nixos-ec2 --use-remote-sudo
```

> 로컬(aarch64-darwin)에서 aarch64-linux 를 직접 빌드하려면 remote/linux 빌더가 필요하므로 `--build-host nixos-ec2` 로 원격 빌드를 권장합니다.

## 6. 변경을 영구 반영하기 (AMI 재굽기)

5번으로 검증까지 마친 변경을, 다음 Spot 회수 이후에도 살아남게 하려면 현재 인스턴스를 새 AMI 로 캡처하고
Launch Template 을 그 AMI 로 갱신해야 합니다.

```sh
# 1) 새 AMI 생성 (데이터 볼륨은 이미 별도 attach/detach 되므로 자동으로 제외됨)
$ AMI_ID=$(aws ec2 create-image \
    --instance-id "$INSTANCE_ID" \
    --name "nixos-ec2-spot-$(date +%Y%m%d-%H%M%S)" \
    --description "nixos-ec2 spot AMI" \
    --no-reboot \
    --tag-specifications 'ResourceType=image,Tags=[{Key=Name,Value=nixos-ec2-spot},{Key=project,Value=nixos-config}]' \
    --query "ImageId" --output text)
$ aws ec2 wait image-available --image-ids "$AMI_ID"

# 2) Launch Template 새 버전 생성 + 기본 버전으로 지정
$ aws ec2 create-launch-template-version \
    --launch-template-name nixos-ec2-spot-lt \
    --source-version '$Latest' \
    --launch-template-data "{\"ImageId\":\"$AMI_ID\"}"
$ aws ec2 modify-launch-template \
    --launch-template-name nixos-ec2-spot-lt --default-version '$Latest'

# 3) (선택) 지금 바로 새 AMI 로 교체하고 싶다면 인스턴스를 재기동
$ aws ec2 terminate-instances --instance-ids "$INSTANCE_ID"
# ASG 가 새 Launch Template 기본 버전(방금 만든 AMI)으로 자동 재기동합니다.
```

> 3번을 생략하면, 다음번 자연 발생하는 Spot 회수 시점에 새 AMI 가 적용됩니다.

## 7. 상태 / 리소스 점검

```sh
$ ssh nixos-ec2 'systemctl is-active sshd amazon-ssm-agent docker attach-home-volume associate-eip'
$ ssh nixos-ec2 'free -h; df -h /; df -h /home; uptime; zramctl'
$ ssh nixos-ec2 'readlink -f /run/current-system'   # 현재 세대

# Helix LSP 정상 여부
$ ssh nixos-ec2 'hx --health python; hx --health nix'

# 시스템 세대 목록 / 롤백 (주의: 롤백은 이번 부팅에만 적용, AMI 는 그대로)
$ ssh nixos-ec2 'sudo nix-env --list-generations -p /nix/var/nix/profiles/system'
$ ssh nixos-ec2 'sudo nixos-rebuild switch --rollback'
```

## 8. 비용 / 스냅샷 관리

```sh
# 이 프로젝트 리소스 조회
$ aws ec2 describe-instances --filters "Name=tag:project,Values=nixos-config" \
    --query "Reservations[].Instances[].[InstanceId,InstanceType,State.Name]" --output table
$ aws ec2 describe-volumes --filters "Name=tag:project,Values=nixos-config" \
    --query "Volumes[].[VolumeId,Size,State]" --output table

# 백업 스냅샷 조회 / 삭제
$ aws ec2 describe-snapshots --owner-ids self \
    --filters "Name=tag:project,Values=nixos-config" \
    --query "Snapshots[].[SnapshotId,VolumeSize,StartTime]" --output table
$ aws ec2 delete-snapshot --snapshot-id snap-xxxxxxxx
```

- 컴퓨트: 이전 t4g.large On-Demand 대비 Spot 전환으로 **약 70% 절감** (AZ/타입에 따라 시간당 $0.025~0.04 수준).
- 스토리지: 루트 gp3 64GiB (~$5.8/월) + `/home` gp3 80GiB (~$7.3/월).
- Elastic IP: 인스턴스에 연결되어 있는 동안 무료, ASG desired=0 으로 내려 연결 해제된 상태로 방치하면 시간당 과금됩니다 — 오래 안 쓸 거면 EIP 자체를 release 하세요.
- 정확한 예측: <https://calculator.aws>

## 9. 트러블슈팅

- **SSM 접속 불가**: 섹션 1 로 현재 인스턴스 ID 를 다시 조회했는지 먼저 확인 (교체 직후 ID 가 바뀌어 있을 수 있음). 그다음 인스턴스가 실행 중인지(`describe-instances`), SSM `Online` 인지(`describe-instance-information`) 확인. 기동 직후엔 등록에 1~2분 걸립니다.
- **`/home` 이 비어 보임**: `systemctl status attach-home-volume` 확인. 볼륨이 이전 인스턴스에서 아직 detach 중이면 최대 수 분간 재시도합니다. `nofail` 옵션 때문에 최종 실패해도 부팅 자체는 됩니다.
- **Elastic IP 로 접속이 안 됨**: `systemctl status associate-eip` 확인, 또는 `aws ec2 describe-addresses --allocation-ids eipalloc-04d6e702ea3b20bd7` 로 현재 어느 인스턴스에 붙어있는지 확인.
- **빌드 중 메모리 부족(OOM)**: zram 이 켜져 있지만, 무거운 소스 빌드는 `--max-jobs 1 --cores 2` 로 병렬도를 낮추거나 임시 swapfile 을 추가하세요.

  ```sh
  $ ssh nixos-ec2 'sudo fallocate -l 8G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile'
  # 빌드 후 정리: sudo swapoff /swapfile && sudo rm /swapfile
  ```

- **빌드가 매우 느림**: Launch Template 의 override 인스턴스 타입 목록에 더 큰 타입(예: `c7g.2xlarge`)을 임시로 추가하고 ASG 를 순환시키는 방법이 있으나, 간단히는 `nixos-rebuild switch --max-jobs 2 --cores 2` 로 병렬도를 낮춰 현재 타입에서 버티는 쪽을 권장합니다. (이전 가이드의 "인스턴스 stop 후 modify-instance-attribute 로 타입 변경" 절차는 ASG 관리 하에서는 더 이상 적용되지 않습니다 — ASG 가 다음 회수 시 Launch Template 타입으로 되돌립니다.)
- **Spot 회수(인터럽션)**: AWS 가 2분 전 경고 후 인스턴스를 회수합니다. `capacity-rebalance` 가 켜져 있어 ASG 가 경고를 감지하면 선제적으로 대체 인스턴스를 띄웁니다. `/home` 과 EIP 는 자동으로 새 인스턴스에 재연결되지만, 진행 중이던 셸 세션/빌드는 끊깁니다.
