<!-- markdownlint-disable MD013 MD014 -->

# Linux on AWS: native ASG scheduling without an extra scheduling bill

이 브랜치는 `feature/linux-on-cloud`의 ARM NixOS 설정입니다. **스케줄 실행은 AWS ASG 자체에 등록**하며, 로컬 컴퓨터·Git 저장소·상주 클라이언트 없이 실행됩니다. NixOS는 EC2 내부 안전 가드와 부팅 환경만 제공합니다.

## 현재 배포 상태 (2026-10-27 격리 이미지 검증)

- 운영 ASG: `nixos-ec2-asg`, 서울 `ap-northeast-2d`, min=0 / max=1.
- native 예약 3개 등록: 평일 16:30 / 주말 10:30 시작, 익일 02:00 scale-in 요청.
- 신규/현재 인스턴스의 scale-in protection 활성화.
- 운영 EC2에는 **armed=false 컴파일된 Nix 관찰 가드**를 runtime unit으로 설치.
- 60개 오프라인 테스트와 Nix 평가 통과. 새 암호화 32 GiB 루트를 빈 파일시스템에 설치하고 **v2 AMI `ami-0d44956a8229b0dad`의 UEFI/SSM 실제 격리 부팅**과 탑재된 수정 코드의 SHA256 일치를 확인함. 운영 시스템 switch/boot 기본값/AMI 전환은 하지 않음. 운영 암호화 홈 전환·실제 작업 추적·백업 보존·최종 종료/깨우기 검증은 아직 필요함.
- 새 프로필 복구 모듈로 현재 closure 1,294개를 별도 빈 Nix 스토어에 복원하여 모든 본문 해시·서명을 검증했고 임시 스토어도 정리함.
- 프로필 변경 path 감시와 5분 보완 timer를 runtime 설치하여 실제 자동 캐시 갱신을 확인함.
- 새 AMI의 InService/scale-in protection 게이트를 격리 ASG에서 실제 통과시킴. 홈이 없을 때 SSM만 접근 가능하고 사용자/HM/Docker/EIP가 비활성인 것도 확인함. 테스트 역할의 운영 홈 연결/EIP 연계 거부를 실제 dry-run으로 검증함.
- 실제 Nix로 혼합 캐시 경계를 추가 검증함: 새 이미지에 이미 있는 시스템도 `nix copy --from` 요청에 넣으면, 옛 캐시에 없는 시스템 때문에 실패함. **없는 root만 서명 캐시에서 요청**하도록 소스를 수정했고 실제 모듈/서명 import 회귀 테스트도 통과. 이 수정은 v2 이미지에 반영하여 부팅 검증함. 홈 누락 시 실제 GC 실행도 차단됨을 확인함. 격리 EC2에서 새 패키지 설치 → 자동 캐시 게시 → 실제 루트 삭제 → 새 EC2의 서명 복구 → 실제 GC 이후 실행까지 통과함.
- `main`의 Darwin 설정은 이 변경으로 수정하지 않음.

**예약 Desired=0과 실제 종료는 다릅니다.** 보호가 켜진 서버는 예약 시각에도 남습니다. 현재는 아직 실제 자동 종료가 비활성화된 관찰 단계입니다.

## 요금 계약

EC2 Auto Scaling 예약 기능 자체에는 추가 요금이 없습니다. Free Tier에 기대지 않습니다.

사용하지 않는 것: Lambda, Step Functions, DynamoDB, EventBridge Scheduler, SNS, 유료 CloudWatch 알람/사용자 지정 지표/로그 전송, 로컬 cron.

기존 EC2 안의 systemd 가드가 기본 AWS API로 보호 여부를 제어합니다. 별도 제어 서버는 없습니다. EC2 실행 시간, EBS, IPv4, 스냅샷 및 초기 검증용 임시 리소스는 별도 과금됩니다.

- <https://aws.amazon.com/ec2/autoscaling/pricing/>
- <https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-instance-protection.html>

## 운영 리소스

| 항목 | 값 |
|---|---|
| AWS account / region | 537112465379 / ap-northeast-2 |
| ASG / subnet | nixos-ec2-asg / subnet-0500a35263dc62859 |
| Launch template | lt-01468c818ef1bb11a, 기존 숫자 버전 1에 고정 ($Latest 제거) |
| 현재 AMI | ami-0f82d67a7f735cab1 (새 이미지 검증/교체 전의 8월 이미지) |
| 현재 후보/정책 | m6g.large / m7g.large / m8g.large / m6gd.large, price-capacity-optimized |
| 추후 후보 | 위 4종 + m7gd.large, 이미지 검증 후 최저가 우선 정책 적용 예정 |
| 영구 홈 EBS | vol-09fea2ff4615b1088, gp3 80GiB, UUID e47b82eb-22d2-4b12-9e58-92d5aabfbc65 |
| EIP | 52.78.88.164 / eipalloc-04d6e702ea3b20bd7 |
| SG | sg-065aa5f3bd3cac988, inbound 없음 |
| instance profile | nixos-ec2-ssm-profile |
| OS user | sudosubin, UID 1001 |

운영 인스턴스 ID는 교체 시 바뀝니다. 원본 보호를 위해 현재 루트는 DeleteOnTermination=false로 임시 보존했습니다. 기존 launch template의 루트는 여전히 true입니다. 영구 홈은 항상 false여야 합니다.

## AWS 콘솔/CloudShell로 상태 확인

CloudShell에서는 로그인한 AWS 자격 증명을 사용합니다. 로컬 `sudosubin` 프로필 파일이 필요하지 않습니다. 로컬 AWS CLI를 운영 도구로 사용하는 경우에만 `--profile sudosubin`을 추가하면 됩니다.

```sh
export AWS_REGION=ap-northeast-2
aws sts get-caller-identity

aws autoscaling describe-scheduled-actions \
  --auto-scaling-group-name nixos-ec2-asg

aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names nixos-ec2-asg \
  --query 'AutoScalingGroups[0].{Desired:DesiredCapacity,Instances:Instances[].{Id:InstanceId,State:LifecycleState,Protected:ProtectedFromScaleIn}}'

INSTANCE_ID=$(aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names nixos-ec2-asg \
  --query 'AutoScalingGroups[0].Instances[?LifecycleState==`InService`].InstanceId|[0]' --output text)

aws ssm start-session --target "$INSTANCE_ID"
```

SSM은 public SSH 포트 없이 작동합니다. CloudShell 자체는 Session Manager plugin 제공 여부에 따라 EC2 콘솔의 Session Manager를 대신 사용할 수 있습니다.

## Native 예약

ASG cron은 5개 필드이며 `--time-zone Asia/Seoul`이 중요합니다.

| action | cron | desired |
|---|---|---:|
| nixos-start-weekdays | 30 16 * * 1-5 | 1 |
| nixos-start-weekends | 30 10 * * 0,6 | 1 |
| nixos-guarded-scale-in | 0 2 * * * | 0 |

02:00 요청이 와도 scale-in protection을 가드가 해제하기 전에는 서버가 종료되지 않습니다. 장애/판정 실패면 보호를 유지합니다. **프로세스가 없다는 이유만으로 EC2 Stop을 호출하거나 보호를 수동 해제하지 마세요.** ASG는 Stop을 비정상 상태로 보고 대체 인스턴스를 만들 수 있습니다.

## 수동 깨우기

AWS 콘솔 또는 CloudShell에서:

```sh
aws autoscaling set-desired-capacity \
  --auto-scaling-group-name nixos-ec2-asg --desired-capacity 1
```

이후 새 ID와 SSM Online을 확인합니다. 시간 밖에서 켰다면 필요 시 AWS의 무료 일회 ASG 예약으로 종료를 요청할 수 있습니다. 그 요청도 보호 검사를 우회하면 안 됩니다. 다음 정규 운영 시간과 충돌하는 일회 종료 예약은 만들지 마세요.

## 인스턴스 내부 가드

소스:

- `modules/linux/spot-schedule-guard.py`
- `modules/linux/spot-schedule-guard.nix`
- `modules/linux/test-spot-schedule-guard.py`

```sh
sudo systemctl status spot-schedule-guard.timer
sudo journalctl -u spot-schedule-guard.service -n 10 --no-pager
sudo python3 -m json.tool /run/spot-schedule-guard/status.json
```

시스템 PATH에 python3가 없는 관찰용 runtime 설치에서는 journal로 확인하거나 설치된 Python 경로를 사용합니다. NixOS 모듈 설치 후에는 `spot-schedule-guard` 패키지가 자체 Python 경로를 포함합니다.

다음 중 하나라도 해당하면 종료를 보류합니다.

- armed=false, 미검증 manifest, 프로필 불일치
- 정규 운영 시간, ASG가 Desired=0을 요청하지 않은 상태
- 활성 SSM, 작업/유지보수 lease, 미추적 작업 프로세스
- 홈 마운트/UUID/연결 대상 불일치, 암호화 준비 미완료
- AWS API/상태 판정 실패

01:45 알림은 NixOS 모듈의 TTY/journal notice이며 외부 유료 알림 채널을 사용하지 않습니다. 가드가 사용자 작업을 강제로 끝내게 하지 않습니다. Spot 회수나 건강 검사 교체는 이 보호로 막을 수 없으므로 작업 상태는 영구 홈에 저장해야 합니다.

## 프로필 복구와 부팅 의존성

소스: `modules/linux/spot-profile-cache.py`, `spot-profile-cache.nix`.

준비된 새 시스템의 순서:

```text
network → InService/종료 보호 확인 → 지정 EBS 연결 + serial/UUID 확인
        → /home 마운트 → 서명된 프로필 캐시 복구 → 사용자/HM/Docker/EIP
```

- 태그 검색 결과의 첫 볼륨을 임의로 쓰지 않음. 홈 EBS ID는 `services.spotScheduleGuard.homeVolume`, UUID는 `homeUUID`로 명시.
- UUID가 잘못되거나 홈/패키지가 복구되지 않으면 앱을 시작하지 않되 SSM은 독립적으로 접근 가능하게 유지.
- 캐시 복원/갱신은 종료 가드와 공통 lock을 사용하므로 홈을 내리는 중에 캐시를 기록하지 않음.
- `spot-profile-cache-refresh.path`와 5분 timer가 프로필 변경을 서명 캐시에 게시. 복사 실패·용량 부족·프로필 변경 경합에서는 새 완료 manifest를 게시하지 않음.
- `/home/persist/manifests/profile-cache.json`이 현재 시스템/프로필과 맞지 않으면 가드는 종료 보류.
- 새 루트의 GC가 복원된 프로필을 지우지 않도록 `/nix/var/nix/gcroots/spot-profile-cache`에 Nix 자체 API로 명시적인 root를 등록·갱신. 단순히 홈 심볼릭 링크 체인이 보호될 것이라고 가정하지 않음.
- 현재 운영 OS에 설치한 timer/path는 runtime unit이다. 새 AMI로 영구 제공하기 전에는 재부팅 시 유지된다고 취급하지 않음.
- OpenClaw의 비강제 idle admission lease 및 Herdr agent 상태 API는 실제 확인했으나, 가드의 최종 작업 판정에는 아직 연결 전. 프로세스가 있다는 이유만으로 active 작업이라고 단정하거나 그 반대로 유휴라 단정하지 않음.

## 데이터와 이미지의 계약

- `/home/sudosubin`, `/home/docker-data`: 영구 홈 EBS에 있음.
- `/root`의 필요한 상태: `/home/persist/root`의 root 전용 보존본으로 추가 백업. 원본은 별도 승인 전 삭제하지 않음.
- Nix 프로필 메타데이터: `/home/sudosubin/.local/state/nix/profiles`에 이미 보존됨.
- Nix 패키지: `/home/persist/nix-closure-cache`에 서명된 closure checkpoint 보존. **실제 인스턴스 재생성으로 사라진 새 프로필/패키지를 복구**하고 서명·본문 검사 및 실제 GC 후 실행까지 확인함. 증거는 `/home/persist/manifests/nix-profile-recreation-verified-20261027.json`에 보존.
- AWS 안의 준비된 소스/시스템: `/home/persist/nixos-cloud-build`, `/home/persist/build-results/nixos-gc-safe`. 운영 원본 소스를 보존하고 Linux 변경만 별도 overlay함.
- 정확한 v2 이미지 빌드 소스와 후보 볼륨 옵션: `/home/persist/root/cloud-image-release-source-20261027-v2.tar.gz` (root:root 0600, SHA256 `7b7ca6cc2b2145abd283a750e24203e512a2f63d5cf2fcbb92b0c7bdb334033f`). 후보 옵션은 운영에 아직 적용하지 않음.
- 새 루트 실측: 32 GiB 중 약 14 GiB 사용/18 GiB 여유, v2 cold 암호화 스냅샷 전체 크기 14,921,236,480 bytes. 기존 운영 루트/백업은 보존하며 이 수치를 운영 절감 실적으로 간주하지 않음.
- 새 암호화 홈은 사전 복사·전체 파일 checksum/메타데이터 비교·cold 읽기 전용 fsck를 통과함. 첫 cold 스냅샷의 FullSnapshotSize는 41,889,038,336 bytes로 실측됨. 실시간 최종 동기화/전환은 미완료이며 아직 운영 홈은 기존 비암호화 볼륨임.
- 최신 루트/홈 암호화 백업의 파일시스템 복원과 루트 Nix DB 검사를 통과함. 가려진 옛 홈도 읽기 전용 namespace에서 실제 내용/심볼릭 링크 비교 완료. 차이가 있거나 현재 홈에 없는 데이터는 원본 루트와 보호된 암호화 루트 스냅샷 `snap-09235382ac255d357`에 보존하며 현재 홈에 덮어쓰지 않음.
- Home Manager/사용자 관리자/OpenClaw 코어도 **loopback 전용 network namespace + NoNewPrivileges**에서 부팅·상태 RPC 확인. 운영 Discord/모델 서비스에는 연결하지 않았으며 운영 앱 전환 검증과 구별함.
- 빌더·canary·테스트 EBS/ASG/LT/IAM 역할은 AWS 증거 보존 후 정리 완료. 후보 홈/이미지/스냅샷만 보존하며 이미지 부팅/향후 스케줄은 빌더나 로컬 파일에 의존하지 않음.
- 이번 이미지 단계의 일회 로컬 스크립트 6개도 삭제함. 감사용 레시피는 `/home/persist/root/image-phase-operator-recipe-20261027.tar.gz` (0600)에 보존하며 운영 런타임에는 쓰지 않음. 이전 단계의 다른 배포 도구까지 모두 정리된 것은 아님.
- AWS 안의 배포 상태: `/home/persist/manifests/deployment-status.json`. 스케줄 운영에 로컬 메모/checkout이 필요하지 않음.
- 새 루트는 임시이므로 `nixos-rebuild switch`만으로는 다음 ASG 인스턴스에 변경이 남지 않음. 검증된 새 root-only AMI와 숫자 LT 버전이 필요함.
- `create-image`는 추가 EBS를 자동 제외하지 않으며 기본 재부팅이 발생할 수 있음. 무조건 `--no-reboot`로 만들고 무결성이 보장된다고 간주하지 않음.
- 복원 테스트는 운영 홈/EIP 제어가 거부된 별도 역할과 복제 볼륨으로 수행. 외부 통신이 차단되고 권한 상승이 금지된 환경에서만 앱을 시험하며 실제 Discord/모델 작업을 중복 실행하지 않음.

## Linux 변경 검증

```sh
python3 modules/linux/test-spot-schedule-guard.py -v
python3 modules/linux/test-spot-profile-cache.py -v
nix-instantiate --parse modules/linux/spot-schedule-guard.nix
nix-instantiate --parse modules/linux/spot-profile-cache.nix
nix-instantiate --parse modules/linux/spot-home-volume.nix
nix eval --no-write-lock-file --raw \
  'path:/absolute/path/to/this/worktree#nixosConfigurations.linux.config.system.build.toplevel.drvPath'
```

이 브랜치의 패키지는 aarch64-linux이므로 전체 빌드는 AWS의 ARM 빌더에서 해야 합니다. 운영 루트가 부족할 때 큰 이미지 빌드를 밀어 넣지 않습니다. 진행 중인 작업이 있는 운영 서버에 전체 switch/reboot/terminate를 실행하지 마세요.

새 이미지 검증이 끝나기 전 `services.spotScheduleGuard.armed`를 true로 바꾸거나 검증 플래그를 임의로 채우지 않습니다. 관찰 단계는 실수로 종료를 활성화하지 않도록 설계되었습니다.

## 비용·백업 주의

- EIP는 연결 중에도, 미연결 보유 중에도 public IPv4 요금이 발생함.
- 스냅샷은 EBS 볼륨과 별도 과금되며 볼륨 삭제 시 자동 삭제되지 않음.
- 정상 운영용 홈 백업은 cold snapshot과 최근 성공본 3개 보존을 검증한 뒤 활성화. 보호 스냅샷/AMI 참조 스냅샷은 일반 정리 대상에서 제외.
- 안전장치가 종료를 보류하면 EC2 실행료는 계속됨. 별도 스케줄링 요금 0원과 전체 청구액 0원은 다른 개념.
