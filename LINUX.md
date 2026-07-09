<!-- markdownlint-disable MD013 MD014 -->

# Linux on Cloud (AWS EC2)

`modules/linux` 를 headless AWS EC2(arm64 / Graviton) 서버로 배포/운영하기 위한 AWS CLI 가이드입니다.
접속은 **SSM Session Manager** 를 기본 채널로 사용하며, 보안 그룹에 인바운드 포트를 열지 않습니다.

## 리소스 정보

| 항목 | 값 |
|------|----|
| Instance ID | `i-0b730f1c65ff3477c` |
| Instance Type | `t4g.medium` (2 vCPU / 4 GiB, Graviton2) |
| Region | `ap-northeast-2` (Seoul) |
| AWS Profile | `sudosubin` |
| Root Disk | gp3 64 GiB |
| Security Group | `sg-065aa5f3bd3cac988` (인바운드 없음) |
| IAM Instance Profile | `nixos-ec2-ssm-profile` (role `nixos-ec2-ssm-role`, `AmazonSSMManagedInstanceCore`) |
| OS user | `sudosubin` (SSH key `~/.ssh/id_ed25519`) |
| Base AMI | `ami-0a06fb6d3d42b9d98` (NixOS 26.05 aarch64) |
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

## 1. SSM 연결 방법

### 1-1. 대화형 셸 (Session Manager)

```sh
$ aws ssm start-session \
    --target i-0b730f1c65ff3477c \
    --profile sudosubin --region ap-northeast-2
```

- `ssm-user` 로 접속됩니다. `sudo -i` 또는 `sudo su - sudosubin` 로 전환하세요.
- 인바운드 포트가 전혀 필요 없고, AWS TLS 터널로 종단간 암호화됩니다.

### 1-2. 인스턴스가 SSM 에 등록되어 있는지 확인

```sh
$ aws ssm describe-instance-information \
    --filters "Key=InstanceIds,Values=i-0b730f1c65ff3477c" \
    --query "InstanceInformationList[0].PingStatus" --output text
# => Online
```

### 1-3. 한 번에 명령 실행 (run-command)

```sh
$ CMD_ID=$(aws ssm send-command \
    --instance-ids i-0b730f1c65ff3477c \
    --document-name "AWS-RunShellScript" \
    --parameters '{"commands":["uptime","free -h","df -h /"]}' \
    --query "Command.CommandId" --output text)

$ aws ssm get-command-invocation \
    --command-id "$CMD_ID" --instance-id i-0b730f1c65ff3477c \
    --query "StandardOutputContent" --output text
```

## 2. SSH over SSM (권장)

SSM 터널 위에서 SSH 를 사용합니다. 포트를 열지 않으면서도 `scp`, `nixos-rebuild --target-host`, 포트 포워딩이 가능합니다.

`~/.ssh/config` 에 추가:

```sshconfig
Host nixos-ec2
  HostName i-0b730f1c65ff3477c
  User sudosubin
  IdentityFile ~/.ssh/id_ed25519
  ProxyCommand aws ssm start-session --target %h --document-name AWS-StartSSHSession --parameters portNumber=%p --profile sudosubin --region ap-northeast-2
```

사용:

```sh
$ ssh nixos-ec2
$ ssh nixos-ec2 "uptime"
$ scp ./file nixos-ec2:/home/sudosubin/
```

### 2-1. 포트 포워딩 (예: 원격 8080 → 로컬 8080)

```sh
$ aws ssm start-session \
    --target i-0b730f1c65ff3477c \
    --document-name AWS-StartPortForwardingSession \
    --parameters '{"portNumber":["8080"],"localPortNumber":["8080"]}' \
    --profile sudosubin --region ap-northeast-2
```

## 3. 인스턴스 시작 / 중지 / 상태 (비용 절감)

컴퓨트와 Public IPv4 요금은 **실행 중에만** 부과됩니다. 안 쓸 때는 중지하세요. (EBS 는 중지해도 부과)

```sh
# 상태 확인
$ aws ec2 describe-instances --instance-ids i-0b730f1c65ff3477c \
    --query "Reservations[0].Instances[0].[State.Name,InstanceType,PublicIpAddress]" --output text

# 중지 (컴퓨트/IPv4 과금 정지)
$ aws ec2 stop-instances --instance-ids i-0b730f1c65ff3477c

# 시작
$ aws ec2 start-instances --instance-ids i-0b730f1c65ff3477c

# 시작 후 SSM 재등록 대기 (Online 될 때까지 잠시 소요)
$ aws ssm describe-instance-information \
    --filters "Key=InstanceIds,Values=i-0b730f1c65ff3477c" \
    --query "InstanceInformationList[0].PingStatus" --output text
```

> 중지 후 재시작하면 Public IP 가 바뀔 수 있으나, SSM/SSH-over-SSM 은 Instance ID 로 접속하므로 영향이 없습니다.

## 4. 배포 (nixos-rebuild)

빌드는 인스턴스에서 네이티브(arm64)로 수행합니다. flake 를 push 한 뒤 SSM 으로 rebuild 를 실행합니다.

### 4-1. SSM run-command 로 배포

```sh
$ aws ssm send-command \
    --instance-ids i-0b730f1c65ff3477c \
    --document-name "AWS-RunShellScript" \
    --comment "nixos-rebuild switch" \
    --timeout-seconds 3600 \
    --parameters '{"executionTimeout":["3600"],"commands":["export NIX_CONFIG=\"experimental-features = nix-command flakes\"","nixos-rebuild switch --flake github:sudosubin/nixos-config#linux --refresh"]}' \
    --query "Command.CommandId" --output text
```

- t4g.medium(2코어/4GB)은 소스 빌드가 많으면 오래 걸립니다. 장시간 빌드는 아래처럼 백그라운드로 실행하고 상태 파일을 폴링하세요.

```sh
# 백그라운드(detached) 빌드 — SSM 명령 타임아웃에 영향받지 않음
$ aws ssm send-command --instance-ids i-0b730f1c65ff3477c \
    --document-name "AWS-RunShellScript" --timeout-seconds 120 \
    --parameters '{"commands":["rm -f /tmp/deploy.status","export NIX_CONFIG=\"experimental-features = nix-command flakes\"","setsid bash -c '\''nixos-rebuild switch --flake github:sudosubin/nixos-config#linux --refresh --max-jobs 2 --cores 2 > /tmp/deploy.log 2>&1; echo $? > /tmp/deploy.status'\'' </dev/null >/dev/null 2>&1 &","echo started"]}'

# 진행/완료 확인
$ ssh nixos-ec2 'cat /tmp/deploy.status 2>/dev/null || tail -n3 /tmp/deploy.log'
```

### 4-2. 로컬에서 원격 배포 (SSH-over-SSM, 빌드는 원격)

```sh
$ nixos-rebuild switch \
    --flake .#linux \
    --target-host nixos-ec2 --build-host nixos-ec2 --use-remote-sudo
```

> 로컬(aarch64-darwin)에서 aarch64-linux 를 직접 빌드하려면 remote/linux 빌더가 필요하므로 `--build-host nixos-ec2` 로 원격 빌드를 권장합니다.

## 5. 상태 / 리소스 점검

```sh
$ ssh nixos-ec2 'systemctl is-active sshd amazon-ssm-agent docker'
$ ssh nixos-ec2 'free -h; df -h /; uptime; zramctl'
$ ssh nixos-ec2 'readlink -f /run/current-system'   # 현재 세대

# Helix LSP 정상 여부
$ ssh nixos-ec2 'hx --health python; hx --health nix'

# 시스템 세대 목록 / 롤백
$ ssh nixos-ec2 'sudo nix-env --list-generations -p /nix/var/nix/profiles/system'
$ ssh nixos-ec2 'sudo nixos-rebuild switch --rollback'
```

## 6. 비용 / 스냅샷 관리

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
$ aws ec2 delete-snapshot --snapshot-id snap-03da472953fcff403
```

- 상시(24/7) 예상 비용 ≈ **$40/월** (컴퓨트 ~$30 + gp3 64GB ~$6 + IPv4 ~$4).
- 크레딧은 `standard` 모드라 버스트 초과 과금이 없습니다.
- 정확한 예측: <https://calculator.aws>

## 7. 트러블슈팅

- **SSM 접속 불가**: 인스턴스가 실행 중인지(`describe-instances`), SSM `Online` 인지(`describe-instance-information`) 확인. 시작 직후엔 등록에 1~2분 걸립니다.
- **빌드 중 메모리 부족(OOM)**: zram 이 켜져 있지만, 무거운 소스 빌드는 `--max-jobs 1 --cores 2` 로 병렬도를 낮추거나 임시 swapfile 을 추가하세요.

  ```sh
  $ ssh nixos-ec2 'sudo fallocate -l 8G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile'
  # 빌드 후 정리: sudo swapoff /swapfile && sudo rm /swapfile
  ```

- **빌드가 매우 느림**: 빌드 동안만 큰 인스턴스로 임시 변경 후 되돌리기.

  ```sh
  $ aws ec2 stop-instances --instance-ids i-0b730f1c65ff3477c
  $ aws ec2 wait instance-stopped --instance-ids i-0b730f1c65ff3477c
  $ aws ec2 modify-instance-attribute --instance-id i-0b730f1c65ff3477c --instance-type c7g.2xlarge
  $ aws ec2 start-instances --instance-ids i-0b730f1c65ff3477c
  # 빌드 완료 후 t4g.medium 로 원복 (동일 절차)
  ```
