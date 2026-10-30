<!-- markdownlint-disable MD013 MD014 -->

# Linux on AWS: native ASG scheduling without an extra scheduling bill

이 브랜치는 `feature/linux-on-cloud`의 ARM NixOS 설정입니다. **스케줄 실행은 AWS ASG 자체에 등록**하며, 로컬 컴퓨터·Git 저장소·상주 클라이언트 없이 실행됩니다. NixOS는 EC2 내부 안전 가드와 부팅 환경만 제공합니다.

## 현재 배포 상태 (2026-10-27 격리 이미지 검증)

- 운영 ASG: `nixos-ec2-asg`, 서울 `ap-northeast-2d`, min=0 / max=1.
- native 예약 3개 등록: 평일 16:30 / 주말 10:30 시작, 익일 02:00 scale-in 요청.
- 신규/현재 인스턴스의 scale-in protection 활성화.
- 운영 EC2에는 **armed=false 컴파일된 Nix 관찰 가드**를 runtime unit으로 설치.
- 102개 오프라인 테스트, root Linux에서 실제 UID 전환/프로세스 경합 테스트 4개 및 Nix 평가 통과. 새 암호화 32 GiB 루트를 빈 파일시스템에 설치하고 **v2 AMI `ami-0d44956a8229b0dad`의 UEFI/SSM 실제 격리 부팅**과 탑재된 수정 코드의 SHA256 일치를 확인함. 운영 시스템 switch/boot 기본값/AMI 전환은 하지 않음. 운영 암호화 홈 전환·실제 작업 추적·백업 보존·최종 종료/깨우기 검증은 아직 필요함.
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

## 작업 등록·수동 연장과 종료 admission (2026-10-27 후속)

소스: `spot_work.py`, `spot-work.nix`, `test-spot-work.py`, `test-spot-work-linux.py`.

현재 운영 OS에는 **새 관찰 가드와 admission 초기화만 runtime 배포**했으며 앱·SSM·Docker 재시작/OS switch는 하지 않음. `/run/spot-work`는 검증된 Nix 패키지로 가는 임시 실행 경로이고, 새 이미지 배포 후에는 `spot-work`가 PATH에 제공됨. 현재 v2 AMI에는 이 후속 변경이 아직 포함되지 않음.

```sh
/run/spot-work run -- your-command arg1
/run/spot-work extend --seconds 7200
/run/spot-work cancel manual-<returned-id>
sudo /run/spot-work status
```

- 작업 lease를 만든 후에만 명령을 시작하며 명령 인수/프롬프트는 기록하지 않음. 메인 명령이 종료되어도 background/double-fork/setsid 자손이 남으면 Linux subreaper가 작업 lease를 유지함.
- 후속 generic-job 개선은 **소스/검증 준비 단계이며 운영 미적용**임. Popen 호출 전에 spawn attempt를 표시해 constructor가 예외를 던져도 `child is None`을 미시작 증거로 사용하지 않음. executable 부재를 포함한 불확실한 spawn은 자동으로 lease를 지우지 않으며, trusted reconciliation은 여전히 필요함. 명백히 호출 전 취소된 경우만 미시작으로 정산함.
- subreaper 설정을 GET으로 확인하고 Linux `__WALL` wait로 비-SIGCHLD clone child까지 기다림. 정상 종료 뒤에도 이 wrapper의 boot/PID/start/UID 및 원본 lease와 정확히 일치할 때만 정산하며, heartbeat도 바뀐 unknown record를 덮어쓰지 않음. 이 process-tree 정산은 IPC로 다른 서비스에 위임한 작업/출력의 완료나 전체 서버 유휴 증거가 아님.
- 선언한 generic `spot-work`는 shell wrapper 없이 immutable Python `-I`로 직접 시작하도록 구성함. admission 전 BASH_ENV/PYTHONPATH/user-site hook을 실행하지 않되, 실제 target의 요청 환경은 lease 뒤에 유지함. 다른 모든 launcher·서비스나 dynamic-loader 환경까지 이 보장을 확대하지 않음. 이 변경의 새 Linux/compiled-CLI 검증은 SSM 복구 후 실행해야 하며, 기존 468개 cloud 증거를 새 변경의 검증으로 재사용하지 않음.
- wrapper가 죽거나 heartbeat가 낡아도 lease는 유휴 판정으로 만료되지 않음. 불명확한 작업은 계속 보류하며 일반 연장 취소 명령으로 작업 lease를 제거하지 못함.
- 종료 준비와 작업 시작은 root 소유 admission lock으로 경합을 제어. 준비 후 새 작업은 실행하지 않으며, 마지막 release 이전에 승인된 수동 연장은 종료를 취소함. release 중/이후의 늦은 요청은 성공했다고 응답하지 않음.
- 서비스 중지 전/후에 안전 조건을 재검사함. rollback은 종료 보호 재확인 → 홈/앱 복구 성공 후에만 admission을 다시 열며, 이미 release한 뒤에는 로깅 실패로 앱을 다시 열지 않음.
- GC/optimise/Docker prune는 admission 조건을 통과해야 시작. 이미 실행 중인 maintenance도 queue 유무와 별개로 가드를 차단함.
- 실제 Linux UID 1001 작업·double-fork 자손·강제 종료된 테스트 wrapper의 stale lease·수동 연장 경합을 **별도 `/run` sandbox에서 검증**했으며 해당 sandbox는 삭제함. 운영자의 짧은 테스트 연장도 관찰 가드가 인식하고 테스트 lease만 제거했음.
- **아직 모든 기존 작업이 이 wrapper를 쓰는 것은 아님.** OpenClaw/Herdr/Kiro의 실제 admission/활동 상태, 전체 프로세스 소유권 및 일반 작업 생산자 연결은 남아 있고 `work_tracking_verified`는 승인하지 않음. lease가 없다는 이유만으로 전체 서버를 유휴라 판단하지 않음.

## Kiro ACP 요청 경계 (후속 준비, 운영 비활성)

소스: `spot_acp.py`, `spot-acp.nix`, `test-spot-acp.py`, `test-spot-acp-linux.py`, `verify-spot-kiro-native.py`.

- 실제 실행 중인 Kiro 2.10.0의 hook 스키마와 ACP/Bun 코드를 확인함. `UserPromptSubmit` 실패는 프롬프트 제출을 차단하지 못하므로 종료 admission으로 사용하지 않음.
- ACP 요청을 backend에 전달하기 **전에** 기존 admission lock 아래 작업 lease를 게시함. fence 뒤 요청은 명시적인 JSON-RPC 오류로 거절하며 backend에 전달하지 않음. 취소 알림 자체는 작업 완료로 간주하지 않음.
- `session/prompt`는 알려진 최종 `stopReason` 응답과 출력 전달까지 확인해야 lease를 해제함. 도구 승인 응답의 전달도 대기함. ACK만 반환하는 비동기 확장, 오류, 불명확한 메시지, 낡은 상태는 유휴가 아님.
- frontend EOF/출력 단절/잘못된 늦은 입력 때문에 진행 중인 backend 작업을 중단하지 않음. 실제 UID 1001 stdio sandbox에서 작업 보존과 fence, 분할 UTF-8, 상태 파일의 프롬프트 비기록을 검증함.
- ACP 단계 당시 ARM 회귀 **136개 단위 테스트 + 11개 실제 Linux 테스트 = 147개** 통과. 실제 native Kiro의 ACP protocol 1 초기화 및 fence 뒤 요청 거절도 network namespace에서 확인했으며 실제 세션/모델 요청은 만들지 않음.
- 후속 검증에서 **실제 native outer CLI → native chat launcher → vendor Bun/TUI → immutable Nix admission proxy → 실제 native ACP backend** 경로를 확인함. backend의 모델 스트림만 vendor `KIRO_MOCK_CHAT_RESPONSE`로 대체하고 비기능 fixture API key만 사용함. 개인 홈/복구 파일/host 사용자 socket을 숨긴 private PID/mount/network namespace, 빈 홈, 도구/Hook/MCP 없는 agent, UID1001/NoNewPrivileges에서 실행하며 외부 모델·실제 인증·운영 앱은 쓰지 않음. **실제 provider/model/tool/subagent 완료나 전체 작업 추적의 증거는 아님.**
- native test-entry 경로는 일반 bundled 경로와 달리 PATH의 `bun`을 사용한다는 실제 ENOENT를 찾아 수정함. 준비된 명시적 `spot-kiro [chat options]`만 vendor runtime PATH와 entry 환경을 설정하고 native CLI를 그대로 실행함. 전역 `KIRO_TEST_TUI_JS_PATH`를 주입하지 않으며 legacy/v3/noninteractive 우회, runtime 부재, 이미 닫힌 admission은 fallback 없이 거절함. 기존 plain native launcher는 검증된 경로로 자동 승격하지 않음.
- 실제 TUI boot의 readonly settings/session-list RPC와 제한된 metadata schema를 확인함. 비어 있지 않은 subagent/pending-stage/tool/MCP inventory와 새 schema는 여전히 unknown. metadata/metric은 idle 권한이 아니며 기존 작업 lease를 해제하지 않음. 거절 횟수만 기록하고 프롬프트·세션/RPC ID는 기록하지 않음.
- 실제 PTY에서 먼저 승인된 요청을 유지한 채 fence 이후 busy steering을 거절하고, 원래 native mock turn의 최종 응답/화면 출력까지 보존함. 이어 idle 상태의 새 prompt도 거절함. busy UI가 wire 오류를 `Failed to queue message`로 감추므로 **실제 UI 오류 + 전달 전 admission 거절 counter + 기존 요청 custody + 후속 모델 출력 부재**를 함께 검사함. busy는 자기 canary backend를 일시 정지한 wire-inflight 조건이며 실제 모델 지연으로 표현하지 않음.
- native 단계 ARM 회귀 **221개 단위 + 17개 root Linux = 238개**, 전부 실행/skip 없음. 새 Linux 3개는 실제 native ACP, 실제 native/vendor TUI, 컴파일된 launcher의 거절 경로임. 실제 vendor TUI의 detached ACP process group도 namespace 안에서 식별/정리하며 생산 프로세스를 신호하거나 재시작하지 않음.
- `services.spotAcp.enable`은 기본 false이며 운영 앱/환경에는 반영하지 않음. `/run/spot-schedule-guard/participants`의 레코드는 coordinator가 프로세스·프로토콜·fence 범위를 검증하기 전까지 **모두 unverified blocker**임. 기존 worker 검사를 완화하지 않음.
- 최신 준비 소스 `/home/persist/nixos-kiro-build`, 빌드 결과 `/home/persist/build-results/nixos-kiro-prepared`는 **빌드 전용**. 이전 ACP 준비본은 역사적 증거이며 현재 v2 AMI에는 최신 통합이 없음. `work_tracking_verified`/`armed`는 승인하지 않음. open 상태의 async steering/queue, 실제 도구/MCP/subagent와 frontend crash/output custody, Herdr/일반 생산자/전체 프로세스 범위 및 중단된 coordinator 복구를 계속 검증해야 함.

## Gateway 비강제 admission·종료/복구 어댑터 (후속 준비)

소스: `spot_gateway.py`, `spot-gateway-rpc.mjs`, `spot-gateway.nix`, 관련 테스트.

- 실제 운영 Gateway는 조회만 수행. UID/서비스 MainPID/프로세스 시작 식별자와 RPC processInstanceId/연결 boot ID를 묶고 loopback만 허용함. 공개 lifecycle 모듈의 hash도 고정하며 인증값·설정·예외 원문을 인수/로그에 노출하지 않음.
- readonly status는 **부분 활동 투영이지 전체 idle 증거가 아님**. root admission 차단 뒤 `terminalPolicy=preserve, drain=false`의 full prepare가 ready인 경우만 진행. busy는 기존 작업을 중단하지 않고 취소/재검사하며 오류·불명확한 응답을 busy/idle로 바꾸지 않음.
- 동일 request ID로 lease를 갱신하고 owner/만료/write custody를 검사함. 서비스 정지는 만료 전 조회만으로 허용하지 않고 resident의 PID+processInstanceId에 묶인 atomic handoff commit이 확인된 뒤에만 수행. 실패 시 일반 systemctl stop으로 우회하지 않음.
- 실제 로드된 non-ignoring ExecCondition, 무한 stop timeout, SendSIGKILL=no를 확인해야 제어 가능. NixOS `asDropin`으로 HM의 원래 ExecStart/인증/재시작 설정을 교체하지 않음. rollback 중에는 종료 보호 재확인 후 root/boot/살아 있는 controller PID에 묶인 특정 서비스 시작만 허용하고, 일반 작업 admission은 열지 않음. Gateway RPC 복구 성공 후에만 outer admission을 다시 엶.
- **175개 단위 + 14개 실제 root/UID1001 Linux = 189개를 ARM에서 모두 실행했고 skip이 없음을 검사함.** 실제 별도 Gateway의 세션 변경 허용→거절→재허용, lease 갱신, atomic 종료, 새 PID로 rollback 재시작을 검증. 기존 작업/개인 홈/인증을 복제하지 않고 private network/mount/tmp, ProtectHome, 읽기 전용 앱/Node bind, 빈 설정으로 수행했으며 모델·채널·외부 네트워크는 쓰지 않음.
- busy/만료/스케줄러 실패/회복은 **별도 Node 프로세스의 실제 vendor coordinator + 주입한 활동 counter**로 검증함. 실제 production 모델 busy나 전체 프로세스 추적의 증거로 확대하지 않음.
- 초기 테스트의 Node 경로 skip, base Node 24.12의 SQLite TEXT/NUL 호환성 오류, Nix `/etc/systemd/user` 중첩 symlink 충돌을 실제로 찾아 수정함. 지금은 skip을 성공으로 세지 않으며, 이미 홈에 영구 보존된 지원 Node 26.4.0을 사용함. `nativeStopBudget=false`는 무한 supervisor timeout에서도 정상이며 idle/기능 지원 여부와 혼동하지 않음.
- 준비 소스 `/home/persist/nixos-gateway-build`, 빌드 결과 `/home/persist/build-results/nixos-gateway-prepared`는 **빌드 전용**. `services.spotGateway.enable` 기본 false, 운영 drop-in/앱/OS/홈/EIP/LT에는 적용하지 않음. v2 AMI에도 포함되지 않음.
- 최신 가드와 admission 초기화만 runtime unit으로 갱신해 실제 운영 Gateway를 읽기 전용으로 관찰함. `/run/spot-schedule-guard/observation-gateway.json`은 armed=false이며 실제 현재 캐시 manifest도 검사함. 운영 prepare/stop/resume는 호출하지 않았고, 앱/OS 재시작이나 재부팅 영속성 검증과는 구별함.
- 기존 WORKERS/participant blocker를 완화하지 않음. Herdr/PTY/모든 프로세스·생산자, 실제 Kiro frontend, 중단된 drain의 자동 reconcile, 성공 백업 3개 보존, 최신 이미지·홈 전환·운영 종료/깨우기 검증과 남은 임시 도구 정리는 아직 필요함. `work_tracking_verified`와 `armed`는 승인하지 않음.

## 중단된 drain의 소유권·보호 복구 (준비, 운영 미활성)

소스: `spot_drain.py`, guard/Gateway/work 모듈, `test-spot-drain.py`, `test-spot-gateway-recovery.py`, 실제 Linux Gateway 테스트.

- `/var/lib/spot-schedule-guard/drain.json`에 root 전용 intent/attempt/배포 identity/boot/PID-start/PID namespace/서비스 baseline/단계를 기록함. journal은 홈 밖에 있고 file+directory fsync/atomic rename하며 별도 flock으로 controller를 직렬화함. 살아 있는 controller나 다른 PID namespace의 소유권을 가로채지 않음.
- fence/서비스 stop/home unmount/backup/release보다 먼저 해당 intent를 기록함. 새 guard는 mounted-home probe보다 **먼저** 미완료 journal을 조정하므로 홈이 내려간 상태를 영구적인 probe 실패로 남기지 않음. 이전 backup을 새 shutdown 성공으로 재사용하거나 불명확한 CreateSnapshot을 재발행하지 않음.
- 복구는 보호된 InService 상태 readback → 정확한 EBS serial/UUID/source/FS root/writable mount → 원래 active였던 서비스의 idempotent start → Gateway/서비스 확인 → 같은 attempt의 admission 재개 순서임. 다른 mount/alias/복제 UUID device, 다른 attachment, 보호 미확인은 막음. 새 PID/일반 작업 lease를 삭제하거나 유휴로 바꾸지 않으며, 원래 inactive 서비스나 정상 replacement Gateway를 강제로 재시작하지 않음.
- startup 권한은 durable authority ID/boot/살아 있는 root PID-start/명시된 unit에만 묶임. 죽은 controller의 **정확히 일치하는** permit만 제거하고 ID/소유권/범위가 바뀌면 닫힌 상태를 유지함. 이 권한은 일반 job admission을 열지 않음.
- prepare reply 유실은 동일 request ID로 소유 lease를 복구해 resume함. commit 유실은 같은 PID/start/connection boot와 retired lifecycle을 확인한 경우에만 vendor의 idempotent handoff ACK로 해소함. 일반 `systemctl stop` fallback은 없음. held 상태의 `system.info`가 실제 vendor fence에 막힌다는 실패를 발견해, 저장된 hello boot ID를 dispatch 전에 확인하고 suspend-control RPC만 사용하도록 수정함.
- 이미 발행한 release와 일치하는 닫힌 fence는 로깅 실패만으로 되돌리지 않음. wake/SSM/window가 supersede하면 보호를 다시 확인한 뒤 복구함. `spot-schedule-guard --recover-only`는 새 shutdown을 시작하지 않음. 이것은 off-instance wake 자체를 대체하는 명령이 아니며 cloud-only wake UX는 계속 필요함.
- 실제 별도 Gateway에서 **controller SIGKILL 4개**(held, prepare reply 유실, commit reply 유실, committed/dead permit)를 실행해 새 controller가 durable journal만으로 복구하고 실제 새/기존 Gateway RPC와 mutation을 확인함. 기존 3개와 합쳐 Gateway Linux **7개**가 실제 실행됨. private network/mount/tmp/빈 홈/읽기 전용 vendor runtime/NoNewPrivileges를 유지하며 **AWS/EBS 관측만 주입**함. 운영 API·실제 EBS remount·OS reboot 복구나 모델 작업 보존의 증거로 확대하지 않음.
- recovery 단계 ARM 회귀 **272개 단위 + 21개 실제 root Linux = 293개**, 전부 실행/skip 없음. parent fsync를 위해 UID1001 runtime 디렉터리(1733)의 읽기 권한을 넓히지 않음. directory fsync는 root-private persistent journal에서만 요청하며 기존 cross-UID work/ACP/실제 TUI 사례도 다시 통과함.
- 준비 소스 `/home/persist/nixos-recovery-build`, 결과 `/home/persist/build-results/nixos-recovery-prepared`는 빌드 전용임. 기존 runtime observer/운영 앱/서비스/홈/AMI/LT를 전환하지 않았고 `armed`/`work_tracking_verified`는 계속 false. 실제 boot/API/storage 중단 복구, 전체 producer/custody, final image/home 전환 및 실제 종료/깨우기 검증은 남아 있음.

## 완료된 cold 백업과 최근 성공본 3개 보존 (준비, 운영 미활성)

소스: `spot_backup.py`, `spot-backup-iam.py`, `verify-spot-backup-aws.py`, `verify-spot-backup-restore.py`.

- 현재 namespace의 빈 `findmnt`만으로 cold를 승인하지 않음. 홈을 내린 뒤 아래 kernel filesystem claim을 보유하고 정확한 encrypted EBS의 단일 attachment/DeleteOnTermination=false와 source identity를 재검사함. filesystem mount custody와 전체 producer/raw-I/O write custody는 별개이며 후자는 아직 전체 작업 추적과 함께 검증해야 함. create 응답의 pending/암호화 표시는 성공 증거가 아님. 완료 상태·소유 계정·source volume·고정 schema/set/attempt·cold 확인 tag를 다시 읽고, 마지막 release lock 안에서도 성공본을 재검사함.
- `CreateSnapshot`에는 ClientToken이 없으므로 SDK 자동 재시도를 끔. API 전 root 전용 journal에 attempt를 기록하고 응답 유실 시 동일 tag로 찾음. 불명확한 결과에서 추가 create를 반복하지 않음. 확인된 권한/요청 rate 거절과 실제 수락 여부 미상은 구별함.
- snapshot 완료 대기에는 강제 종료 마감이 없음. 새 native 시작, 활성 SSM, 승인된 연장/작업, admission·중지 상태 변화가 있으면 protection을 유지하고 홈/서비스 복구 경로로 돌아감. journal은 `/var/lib/spot-schedule-guard/backup.json`이므로 홈이 내려가도 기록 가능함.
- 성공한 cold/encrypted/completed 일반 백업만 최신 3개 보존. Protected=true와 AMI 참조본은 제외하고 deprecated/disabled AMI도 조회함. 삭제 직전 owner/tag/상태/AMI와 새 성공 anchor를 재확인하며 최종 보존 수까지 관찰해야 완료함. 미확인/실패 orphan은 새 성공본이 있고 24시간 지난 경우에만 정리하며 pending은 지우지 않음.
- `spot-backup-policy`는 정확한 source volume/set과 필수 tag, 생성 시 tag, 제한된 상태 tag 전이, Protected=false 삭제 조건을 가진 IAM JSON을 **출력만** 함. snapshot ARN의 account 부분은 EC2 규격대로 비어 있음. 운영 IAM에는 아직 설치하지 않았으며 최종 encrypted home ID와 맞춰야 함.
- 실제 cloud-only worker가 별도 제한 role로 **사용 중이지 않은 encrypted 후보 홈**에서 4개를 생성·완료하고 3개만 남김을 검증함. 같은 set의 protected fixture/실제 AMI 참조 fixture는 보존했고, 기존 production volume create/보호본 delete/보호 tag 변경은 DryRun으로 거절됨을 확인함. production instance/ASG/EIP 제어 권한도 허용되지 않음.
- 최신 canary 성공본에서 새 encrypted EBS를 복원해 exact NVMe serial/UUID 확인, pinned e2fsprogs 1.47.4의 read-only fsck, private ro,noload mount와 UID1001/캐시 metadata를 검증함. 개인 파일 내용·인증을 출력하거나 앱/모델을 시작하지 않음. 테스트용 복원 EBS·6개 snapshot(보존 동작 중 삭제한 1개 포함)·AMI·role·임시 AssumeRole 허가는 정리했으며 원래 보호 백업은 건드리지 않음.
- 최종 **217개 단위 + 14개 실제 Linux = 231개 ARM 사례를 skip 없이 실행**함. 실제 API normal path 이후 추가한 엄격한 read-only 보존/AMI 모순 검사는 단위 회귀에 포함하며, 최종 운영 ID로의 백업/복원 재검증은 여전히 필요함.
- 준비 소스 `/home/persist/nixos-backup-build`, 빌드 결과 `/home/persist/build-results/nixos-backup-prepared`. source 기본 armed=false이며 운영 앱/홈/AMI/LT나 mutating backup IAM을 전환하지 않음. 기존 runtime observer만 계속 동작함. **실제 운영 daily 백업/보존 활성화, 최종 image/home rollout과 전체 작업 추적이 완료된 상태는 아님.**

## 모든 filesystem namespace를 배제하는 kernel cold custody (준비)

소스: `spot_cold.py`, `test-spot-cold.py`, `test-spot-cold-linux.py`, guard 연결.

- 실행 중인 Linux 6.18.38의 block-device claim 코드를 확인하고 실제 커널에서 검증함. 정확한 EBS serial/UUID alias로 찾은 block device를 **O_RDONLY|O_EXCL|O_NOFOLLOW|O_CLOEXEC**로 열어 실제 kernel claim을 유지함. 다른 namespace, lazy-unmount의 open file/cwd, overlay upper/work가 filesystem을 참조하면 EBUSY이며 재시도·freeze·강제 unmount로 성공을 만들지 않음.
- descriptor의 block identity/diskseq/readonly/CLOEXEC/소유 PID와 ext4 superblock UUID/clean+journal 상태를 확인함. user 파일·인증은 읽지 않으며 device readonly flag, 포맷, fsck repair, 기존 mount를 변경하지 않음. 추가 raw writable descriptor 관측도 수행하고 권한 오류/불완전한 process view는 통과시키지 않음.
- **O_EXCL은 모든 privileged raw write를 막는 잠금이 아님.** 실제 canary에서도 O_WRONLY open 자체가 가능함을 확인하고 observer가 이를 거절하는지 검사함. io_uring/privileged raw-I/O와 모든 producer의 새 작업 admission은 별도 미완료 조건이며, 이 claim을 whole-server idle 또는 raw-write atomic fencing으로 표현하지 않음.
- 단발 check 후 descriptor를 닫지 않음. snapshot 생성/응답 확인/cold tag/완료 polling/최종 release lock+API 재검사까지 **같은 claim을 보유**함. 실패 시 context가 먼저 descriptor를 닫은 뒤 보호/홈 복구를 수행하므로 자기 claim 때문에 rollback mount를 막지 않음. coordinator 종료 시 커널이 FD를 회수하며 exec child로 누출하지 않음.
- 실제 private mount/network namespace에서 자기 32MiB loop disk만 포맷/사용한 **8개 Linux 사례**를 모두 실행함: remount race, 다른 namespace mount, detached open file/cwd, detached overlay, raw writer 관측, 잘못된 UUID 후 mount 복구, coordinator SIGKILL 후 claim 회수, exec child 비상속. 빈 namespace-local findmnt와 전/후 동일 mount 성공을 대조하고 skip/resource warning이 없음. 원본 EBS는 테스트 장치로 사용하지 않음.
- 별도로 **기존 encrypted 후보 `vol-0b529abe51df1eca1`만** 임시 attach하여 실제 NVMe serial/UUID/diskseq/ext4 상태와 read-only claim을 검증하고 실제 API attachment/암호화/보호를 claim 보유 중 다시 읽음. filesystem mount/포맷/repair/user 파일 읽기/앱·모델·snapshot 생성은 없었으며 정상 detach해 다시 available임. production home switch나 운영 backup rollout 증거는 아님.
- 최신 ARM 회귀 **293개 단위 + 29개 실제 root Linux = 322개**, 모두 실행/skip 없음. scope와 완전한 suite 결과는 `/home/persist/manifests/cold-ARM-tests-20261027.json`, kernel 8개는 `cold-kernel-tests-20261027.json`, 실제 후보 EBS는 `cold-encrypted-candidate-readonly-verification-20261027.json`에 기록함.
- 준비 소스 `/home/persist/nixos-cold-build`, 결과 `/home/persist/build-results/nixos-cold-prepared`는 **빌드 전용**. 운영 runtime/앱/홈/AMI/LT/백업 IAM은 전환하지 않았고 `work_tracking_verified`/`armed`는 계속 false. 전체 producer/raw-I/O, 실제 boot/production backup·복구·종료/예약 wake, 최종 image/encrypted-home 전환과 로컬 도구 정리는 계속 필요함.

## ACP startup custody와 실제 async producer의 남은 경계 (준비)

- ACP backend의 `Popen` **이전**에 admission lock을 거쳐 startup job lease를 게시함. 닫힌 admission에서는 native 프로세스 자체를 시작하지 않으며 spawn/publication 결과가 불확실하면 lease를 남김. 초기 participant가 실제 게시된 뒤에만 bootstrap lease를 제거함. 그 participant는 아직 uninitialized/unverified blocker이므로 vendor startup helper나 전체 앱이 idle이라는 뜻이 아님.
- 실제 UID1001 교차 UID 검사에서 fence 뒤 두 번째 backend의 startup side effect 자체가 없음을 확인함. immutable proxy + 실제 native backend 경로도 exit75, participant/홈 변경 없음으로 검사함. publication 실패 시 backend를 죽이거나 예외를 완료로 취급하지 않음.
- 실제 native 2.10.0의 메서드는 `_message/send`, `_session/steer`임. model-free private namespace에서 전자는 `{ok:true}` 응답 뒤 실제 mock stream이 계속되고, 후자는 idle에서도 `{queued:true}` 및 `AgentExecutionUserMessageQueued`를 보낼 수 있음을 확인함. ACK를 terminal response로 승격하지 않으며 async lease/unknown blocker를 유지하면서 기존 출력을 계속 전달함.
- parent prompt와 steering을 모두 admission한 실제 native 사례에서 queued/injected event, parent `end_turn`, steering ACK가 모두 관측되어도 별도의 steering 완료/output 계약은 미검증으로 유지함. 자기 fixture backend를 잠시 SIGSTOP한 wire-inflight 시험이며 provider/model 지연 증거가 아님. 벤더 notification은 ACK보다 늦게 올 수 있어 실제 event를 확인하고, 죽은 TEST process의 sticky participant cleanup도 PID/start-bound로 처리함.
- 실제 vendor TUI의 `queuedMessages`/`pendingSteerContent`는 ACP 전송 **이전**에 메모리 안에 존재할 수 있음. 따라서 ACP만으로 frontend queue 전체를 추적했다고 주장하지 않음. frontend producer admission/custody와 seal 직전의 원자적인 blocker 검사, tools/MCP/subagent/Herdr/PTY/SSM-command 소유권은 계속 필요함. `_session/steer/clear` 등 미검증 extension도 request-scoped allowlist에 추가하지 않음.
- native 검증기 **7개**, ACP 단위 **43개**, 교차 UID stdio **8개**를 각각 실제 실행했으며 skip/resource warning이 없음. 최신 전체 ARM 회귀의 실행 수/완전한 stderr는 `/home/persist/manifests/producer-ARM-tests-20261027.json`에서 확인함. 별도 protocol 진단 3개를 이 회귀 수에 중복 합산하지 않음.
- 준비 소스 `/home/persist/nixos-producer-build`, 결과 `/home/persist/build-results/nixos-producer-prepared`는 **빌드 전용**. vendor Bun/TUI 원본과 운영 system/profile/앱/홈/AMI/LT/runtime observer를 바꾸지 않음. native 검증은 빈 홈, 비기능 fixture key, private PID/mount/network, NoNewPrivileges, 도구/hooks/MCP 없음으로 수행하며 실제 provider 완료나 운영 적용 증거가 아님. `participant_unverified`, `work_tracking_verified=false`, `armed=false`를 유지함.

## 새 종료 fence의 원자적 blocker 검사와 pre-action 복구 (준비)

- `spot_work.Protocol.seal()`은 `create()`와 **같은 admission lock 안에서** 현재의 모든 프로토콜 blocker를 다시 읽고 fence를 게시함. 먼저 승인된 job/extension, stale·malformed 기록, unverified participant 또는 registry/복구 authority 불확실성은 admission을 닫지 않고 fresh seal을 거절함. 빈 CPU/이전 probe/partial status를 권한으로 사용하지 않으며 worker/participant exemption을 추가하지 않음.
- durable `created` intent 뒤 seal이 거절되거나 reply/post-seal 기록이 유실되어도, **같은 boot·아직 begin()이 반환하지 않아 action이 시작될 수 없었던 intent**는 보호된 InService readback 후 자기 draining fence만 되돌림. open admission에 복구 fence를 새로 만들지 않으며 홈/Gateway/user/Docker/backup을 건드리지 않음. 다른 attempt/release/미확인 startup authority는 거절하고 기존 job·extension은 삭제하지 않음.
- `created`와 side-effect 기록이 모순되면 fail closed. 다른 boot나 action이 시작될 수 있었던 단계는 이 지름길을 사용하지 않고 기존 storage/service/Gateway 확인을 모두 수행함. cancellation journal 쓰기가 실패해도 다음 controller가 안전하게 다시 확인하며, 불확실한 결과를 완료로 승격하지 않음.
- private root Linux에서 실제 교차 UID의 두 lock 순서와, durable intent를 쓴 controller의 실제 SIGKILL 뒤 새 controller 복구를 검사함. AWS protection 관측은 주입하며 실제 production AWS/EBS/OS reboot 복구 증거가 아님. native verifier에도 fresh seal 거절 후 기존 mock turn·후속 입력 보존 사례가 있음. 전체 실행 수/완전한 stderr/immutable package bytes는 `/home/persist/manifests/seal-ARM-tests-20261027.json`에서 확인함.
- 기존 '이미 닫힌 fence에서 출력/취소/새 입력 거절' 회귀는 **private fixture에만 명시적으로 fault fence를 주입**함. 정상 fresh seal이 busy job 또는 unverified participant를 무시할 수 있다는 증거로 취급하지 않으며 production force/bypass 옵션은 추가하지 않음.
- 준비 소스 `/home/persist/nixos-seal-build`, 결과 `/home/persist/build-results/nixos-seal-prepared`는 빌드 전용. 이것은 프로토콜 사용자의 admission race 보강이지 TUI 내부 queue/전체 producer·raw-I/O fencing 완료가 아님. `work_tracking_verified=false`, `armed=false` 및 전체 전환·실제 종료/wake·로컬 정리 gate는 그대로 유지함.

## ACP 이전 실제 TUI local queue/draft custody (준비)

- `spot_frontend.py`와 `spot-kiro-frontend.mjs`가 명시적 `spot-kiro`의 native 시작 전 bootstrap lease, 실제 Bun PID/start-bound frontend epoch와 unverified participant를 연결함. 단일 admission lock 안에서 bootstrap·epoch·participant를 겹쳐 handoff하며 native spawn/게시/IPC/종료가 불확실하면 sticky custody를 남김. 기존 운영 세션에는 주입하지 않음.
- native launcher는 추가 FD를 실제로 닫으므로 inherited-socket 가정을 버림. Bun은 짧은 동기 CLI로 **승인 ACK 이전**에 작업 epoch를 게시함. bootstrap ancestry/UID/boot/PID-start/sequence/epoch owner를 검사하고 메타데이터는 primitive counter와 opaque ID만 전달함. prompt/command/session ID/파일·이미지 내용은 전달·기록하지 않음. backend에 bootstrap 환경을 넘기지 않음.
- 실제 public vendor bundle SHA256를 확인한 같은 bytes에만 Bun loader의 **인메모리 instrumentation**을 적용함. vendor 파일 원본/전역 auth·test-mode/GET_STORE IPC는 바꾸지 않음. store factory/setState 및 이미 승인된 processQueue handoff의 정확한 형태가 바뀌면 fallback 없이 거절함. React effect/polling으로 idle을 추정하지 않고 상태 변경 경계에서 승인하며, functional updater는 한 번만 실행하고 동일 primitive 상태의 model chunk마다 CLI를 만들지 않음.
- local queuedMessages/pendingSteerContent, draft/attachment, processing/cancel/approval 및 진행 중 producer promise가 epoch를 유지함. queue pop→send 사이와 async yield에서 잠깐 idle을 게시하지 않음. 새 submit은 기존 epoch가 있어도 fence를 재확인하고 거절 UI/counter를 남기며 ACP로 전달하지 않음. 예외/알 수 없는 state는 기존 출력 전달을 계속하지만 healthy/idle로 승격하지 않음.
- 실제 UID1001/private PID1/mount/network/NoNewPrivileges/빈 HOME·비기능 key·tools/hooks/MCP 없는 native TUI에서 (1) backend가 멈춘 동안 두 번째 입력이 **frontend queue에만** 있고 자기 Bun epoch가 유지됨, (2) fresh seal 거절 후 두 mock turn의 실제 출력 보존, (3) 이미 닫힌 private fault fence에서 새 submit을 store/ACP 이전에 거절하고 기존 turn 보존, (4) bundle 변경 시 untracked fallback 거절을 검사함. 3개 canary case와 기존 8개 native 회귀를 모두 실행함. SIGSTOP은 wire-inflight fixture이며 실제 provider 지연/완료 증거가 아님.
- Python epoch 20개 + JavaScript 15개 단위도 ARM에서 실제 실행함. Node test reporter를 명시하고 실제 count/no skips를 확인함. 전체 회귀/소스·immutable bytes/완전한 stderr는 `/home/persist/manifests/frontend-ARM-tests-20261027.json`을 기준으로 함. 진단의 failed FD/partial-frame 시도나 별도 store-schema probe는 이 회귀 수에 합산하지 않음.
- source `/home/persist/nixos-frontend-build`, result `/home/persist/build-results/nixos-frontend-prepared`는 **빌드 전용**. 모든 frontend/ACP participant는 여전히 `participant_unverified`임. 이 증거는 pinned TUI의 검증한 local queue/draft 경계에 한정되며 모든 frontend action/client callback/async tool/MCP/subagent/SSM/Herdr/PTY 소유권, 실제 provider·frontend crash output custody, 모든 raw-I/O·복구·실제 종료/wake·최종 마이그레이션을 증명하지 않음. `work_tracking_verified`, `armed`, `goal_complete`는 계속 false임.

## 프로필 복구와 부팅 의존성

소스: `modules/linux/spot-profile-cache.py`, `spot_cache.py`, `spot-profile-cache.nix`.

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

## 서명 캐시의 무결성·용량·복구·정리

- schema 2 완료 manifest는 root 전용 immutable inventory의 SHA256과 연결됨. 서명 이름의 prefix만 보지 않고 OpenSSL Ed25519로 지정 public key의 실제 서명을 검증하며, 압축 파일의 FileHash/크기와 Nix가 압축 해제한 NAR hash를 모두 검사함. 캐시 activation script는 실행하지 않음.
- 종료 직전 본문 검증은 공통 cache/drain lock을 보유한 채 **원자적인 fresh seal 뒤, Gateway/사용자/Docker/홈을 정지하기 전** 실행함. seal 전에 끝난 job이 active profile을 바꾸지 않고 보존 세대를 추가한 경우도 전체 roster 비교로 거절함. 검증 중 승인한 연장도 서비스 정지 전에 취소시킴.
- 두 설정 디렉터리(`~/.local/state/nix/profiles`, `/nix/var/nix/profiles/per-user/sudosubin`)의 기본·named profile/channel alias와 모든 보존 세대를 포함함. 임의의 다른 디렉터리까지 모두 발견했다고 주장하지 않으며 향후 모든 Nix 생산자의 등록/소유권 검증은 별도 과제임. 사용자 세대 링크 자체는 삭제하지 않음.
- 최신 완료 checkpoint 2개와 마지막 참조 후 기본 24시간 이내 객체를 보호함. legacy adoption은 정리 소유권 증거이지 영원히 남기는 profile checkpoint가 아님. 모든 남은 narinfo(다른 signer 포함)의 URL을 보호하고, 동일 store path의 이전 압축본도 객체 단위로 판단함. 모르는 파일은 보존하고 불명확한 inventory/객체는 삭제하지 않음.
- 손상된 현재 캐시의 readiness를 먼저 unverified로 무효화한 뒤 durable intent로 원본 바이트를 격리함. 새 완료본의 전체 본문 검증 후 정확히 자기 격리 파일만 정리하며, 완료 manifest 게시 직후 controller가 죽은 경우의 후속 noop에서도 잔여 정리를 시도함. 실패한 복사를 완료본으로 게시하지 않음. 기본 8 GiB 여유와 필요한 NAR 상한/압축 overhead를 확보하지 못하면 보류함.
- signer/public key 쌍을 확인하고 기존 캐시의 key가 없을 때 암묵적으로 새 key를 만들지 않음. public key만 없으면 root 소유의 기존 manifest 또는 보호된 signer로부터 복구할 수 있음. signer를 잃어도 public metadata가 남으면 서명된 패키지의 읽기 전용 import는 가능하지만, 다음 종료 승인은 signer 손실/불일치로 거절함. private key 바이트는 argv/환경/로그/임시 파일로 복사하지 않음.
- 검증기는 `test-spot-cache.py`, `test-spot-profile-cache.py`, `test-spot-cache-linux.py`임. Linux 검증은 빈 홈/개인 PID·mount·network namespace/NoNewPrivileges와 별도 Nix store·fixture key를 사용하며 실제 import·GC·서명 위조 거절·손상 복구·retention을 검사함. 실제 OS boot/최종 encrypted home/AMI 전환/운영 backup·종료/wake의 증거가 아님.
- 준비 소스 `/home/persist/nixos-cache-build`, 결과 `/home/persist/build-results/nixos-cache-prepared`와 전체 실행 결과 `/home/persist/manifests/cache-ARM-tests-20261027.json`은 운영 runtime 적용과 구별함. 기존 운영 캐시는 schema 1이며 이번 변경을 설치하지 않음. 모든 `participant_unverified`, `work_tracking_verified=false`, `armed=false`, `goal_complete=false` 제약을 유지함.

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

새 canonical `modules/linux/verify-spot-linux.py`는 고유한 **root-level validation slice**와 one-shot service로 재실행한다. 기존 SSM/앱 cgroup을 수정하지 않으며 기본 parent와 별도 Gateway fixture가 같은 1GiB MemoryMax/SwapMax0/OOM group, 최대1 CPU 예산을 공유한다. 자기 검증 프로세스만 OOMScoreAdjust1000/Nice19로 설정하며 서비스는 private network/NoNewPrivileges/readonly cgroup view를 사용한다. 시작·각 suite 전에 실제 cgroup membership/커널 한도와 MemAvailable≥2GiB를 검사한다. systemd260에 없는 `MemoryOOMGroup=` slice 지시어를 신뢰하지 않는다. 고유 scope의 대기 중인 initializer PID만 실제로 존재함을 확인하고 그 scope의 kernel `memory.oom.group=1`을 설정·재조회한 뒤 root-private ready gate를 연다. 초기화·ACK만으로 검증 작업을 허용하지 않는다. 이는 자원 수용 조건이지 서버 유휴 판정이 아니다. 부족·불명확한 예산은 실패/보류이며 skip이나 통과로 바꾸지 않는다. launch/cleanup 모두 global daemon-reload를 호출하지 않는다(다른 active scope의 수동 OOM fence를 reset할 수 있음). d163의 fresh UUID unit on-demand load/커널 admission/cleanup 전후 fence 유지와 actual ARM scoped106=operator64+validation42/4suites/source216/peak30834688/noOOM을 확인했다. 이106은 canonical618·OS/EBS 복구·전체 vendor1GiB capacity 또는 새 AMI 증거가 아니다.

CLI가 반환하는 `verification_started`/unit/log receipt는 **실행 완료가 아니다**. 완전한 result JSON의 실제 count/소스·immutable bytes/모든 suite와 cleanup 결과를 확인해야 한다. 기존 증거를 덮어쓰지 않도록 새 `--output` 경로가 필수이다. `spot_validation.py`, `test-spot-validation.py`, `test-spot-validation-linux.py`가 정책·실제 한도/상속을 검사한다. 고의 OOM/전체 production 메모리 안전/외부 Nix daemon·distributed build까지 검증했다고 확대하지 않는다. 실제 ARM에서 검증 프로세스·별도 fixture의 상속/공유 한도와 자동 cgroup 정리를 확인했다(고의 OOM 시험은 아님). Nix 전체 평가가 1GiB에 도달해 자기 그룹만 OOM 종료되고 SSM PID/boot가 유지된 실패도 보존했다. 별도 `build` 목적은 2GiB/시작시 MemAvailable≥4GiB로 제한하며 검증 fixture/canonical driver는 이를 거절한다. 운영-host 기본 검증1GiB 및 build2GiB는 유지한다. 합산 vendor server/client가1GiB에서 OOM한 증거를 보존하며, `--disposable-verify`는 같은 강제 IMDS/STS/Spot/단일root/ASG/만료 증명을 통과한 별도 canary에만 고정2GiB/시작시10GiB 여유·private network 검증을 허용한다. 이는 운영1GiB capacity 통과 증거가 아니며 검사·count·output/arming 조건은 완화하지 않는다. 외부 daemon/distributed build는 범위 밖이며, 큰 image build는 별도 한정된 canary/workspace가 필요하다. `canary-build`의6GiB/시작시10GiB 여유는 IMDSv2·실제 STS role·EC2 Spot/clean AMI/단일 disposable root·정확한 ASG membership/비보호·2시간 이내 native one-shot Desired/Min/Max0 예약을 모두 대조한 별도 호스트에만 허용한다. 원본 instance/retained volumes/운영 ASG/다른 role은 거절하며 build 예산은 검증 fixture의 권한이 될 수 없다. attested canary artifact build에 한해 pinned 공개 소스와 서명된 cache.nixos.org 대체물을 받는 네트워크를 허용할 수 있다. private Git/model 자격 증명을 공급하거나 signature/sandbox를 우회하지 않으며 검증 및 운영-host build의 private network는 유지한다. 이 경로는 추가 EC2/EBS/IPv4 및 artifact 저장 비용이 들 수 있는 한정된 시험용이며 운영2-vCPU/8-GiB 선택 정책을 바꾸지 않는다. 전체 새 ARM 회귀와 production rollout은 여전히 미검증이다.

### Boot admission / interrupted startup (prepared, not rolled out)

- Production `spot-work initialize` now publishes a boot-bound `starting` gate, never a ready/idle claim from an empty `/run` registry. Missing/malformed/foreign-boot startup custody refuses work. Re-initialization preserves existing custody and cannot close already accepted work or promote a starting boot. There is no CLI ready/force flag; private empty fixtures initialize independently.
- `spot-workload-startup-ready.service` is declarative and precedes user@1001, Docker and HM activation. It verifies protected InService membership, exact EBS ID/serial/UUID/mount/retained attachment, completed cache-restore service and the root-private durable drain journal before opening the independent boot gate. User/Docker/HM and maintenance have non-ignoring admission conditions. SSM does not depend on home or this gate.
- Pending/foreign/malformed intent never means no intent. A live recovery owns only named PID/start/UID/boot-bound service permits while ordinary jobs remain closed. Unsealing a recovered drain does not itself open boot admission. Extensions remain accepted before release and survive opening. Startup preflight uses a distinct controller mutex and never waits for a busy drain journal: the recovery owner may be synchronously starting a unit requiring preflight; waiting would deadlock. Re-running an already-ready preflight cannot re-protect/unseal an active drain.
- Readiness manifests also require this `boot_id` and `instance_id`. Persistent `work_tracking_verified:true` from a previous boot/replacement cannot authorize termination. Boot-gate readiness does **not** set any work-tracking/arming flags.
- `startup-contract.nix` evaluates the actual Linux startup modules with only harmless **fake HM activation**, and exposes their source hashes/dependencies/conditions plus the actual declared Python-I CLI. `verify-spot-startup-contract.py` checks this output inside the normal verification cage without loading/restarting units. Schema2 also observes the home-dependent cache watcher and implicit service/basic/path edges, and requires the original real-boot cycle to fail its negative control. This is still a selected declaration graph, **not** a full systemd/HM/application graph or real OS/EBS/API recovery proof.
- `scripts/spot-build-canary.py` is a one-off AWS CLI/standard-Python creator runnable from CloudShell as well as an operator terminal (`plan|create --scope <12hex> --source-revision <40hex> [--profile ...]`). It archives its exact program and every stage ledger in private S3, checks unchanged production IAM, and reads back fixed native expiry/unprotected zero-capacity/100%Spot/numeric LT before any paid capacity request. It creates no recurring controller, never attaches production storage/EIP or activates a system; scope cleanup still requires explicit owned-resource verification after preserving evidence. Its 16 pure transition tests create no AWS resources and are separate from the canonical runtime count.
- `scripts/spot-canary-pipeline.py launch --source <pinned tree> --authority <root source map>` is a **canary-only one-shot**, not a production controller. Actual IMDS/STS/Spot/expiry/storage attestation precedes work. It chains6GiB full system + scoped declaration build → dedicated2GiB canonical regression → separate dedicated2GiB declaration inspection (12checks, including the failing old-cycle control) → private2GiB missing-from-base-AMI opaque NAR/source archive → checksum + metadata + body readback in scoped S3. A tiny expiring evidence serializer retains partial failures; no operator poll is required between stages. Failed/missing stage results are not success. The launcher fixes256MiB/CPU25%/NNP/priority for the tiny coordinator; its own exact UUID OOM initializer needs writable cgroupfs, whereas validation children retain `ProtectControlGroups=yes`. The separate128MiB evidence serializer gets an explicit immutable-system tool PATH. No boot/profile/store-import/arming action is performed. A matching optional `--artifact-run <32lowerhex>` on launcher and receiver isolates final evidence under a fresh per-run prefix. Final bodies/commit use If-None-Match and one PUT attempt; previous successful evidence is never overwritten. Run once on a FRESH disposable root: a reused root's expanded inventory is NOT proof of the base AMI's inventory. Pure pipeline tests are not cloud execution proof.
- Before launching that workflow, a temporary128MiB/CPU10%/OOM1000/NNP `spot-canary-receive.py --scope <scope> --expires <bounded UTC> --expected-source <trusted map>` on the original EC2 can copy the verified final artifacts to existing retained home, leaving8GiB reserve. It checks actual original IMDS identity and home UUID, checks final roster/body hashes and expected full source, preserves failed attempts, imports/activates nothing and exits. It also requires the separately verified startup declaration flag; canonical618 alone does not imply the12 declaration checks ran. Its role needs only time-bound scoped S3 GetObject. It is neither a recurring scheduler nor work/idle authority; source/receiver tests are separate from the canonical count.
- The earlier7e2d96c9ab31 run really built the latest full system and passed559, but the operator paused before its final guest archive/delta was uploaded or any OS boot was requested. Native expiry terminated that disposable root; the independent exporter preserved full regression/build logs, which were hash-read back on retained home. Do not claim the unexported binary archive or OS boot proof. The chained uploader/retained-home receiver address that observed local-harvest dependency and still require a fresh actual end-to-end run before claiming success.
- Source1b3c16c actually passed **559=499unit+60Linux**,21suites on prepared i6g35; its full proof and45-path opaque base-AMI delta were automatically received/hash-checked on retained home. A real disposable-only reboot then changed kernel boot epoch/current system to i6g35 while SSM stayed available and boot admission stayed `starting`; direct work exited75 before payload. The first protection API was denied, so this is NOT positive/isolated wrong/missing/delayed-home recovery proof. New off-root code expands the required canonical scope to **618=558unit+60Linux**,22suites/17 immutable copies; sourcee4aeb29 actually built prepared82sa4 and passed this full618/22/17 scope, with all artifacts automatically received on retained home. Its real new-OS boot kept SSM/admission safe but exposed an actual ordering-cycle FAILURE: home-dependent cache refresh.path implicitly preceded paths.target/basic.target, needed by protected attachment. The618 pass is therefore NOT a cycle-free startup/positive recovery proof. The watcher is now explicit late maintenance with DefaultDependencies=false, startup/home ordering and explicit shutdown cleanup; updated declaration/actual cycle-free boot proof is required for these new bytes. Historical results remain valid only for their exact source/artifact. The observed production boot gap/Gateway inactive state has not been repaired by restarting apps or creating an empty registry; activation remains disarmed.

### Independent expiry for protected disposable trials (investigation only)

- `scripts/spot-protected-expiry.py plan|create|status` first creates a **zero-capacity** protected ASG plus an intentionally unsignalled native CloudFormation CreationPolicy. The exact program/policy/state live in the cloud template. There is no signal handle/URL, guest profile, userdata, key, public IPv4, Lambda or recurring external controller. Native rollback stays enabled with a separate absolute stack timeout and a persistent narrowly scoped CFN execution role. Rollback/service failures remain failures, not a strict wall-clock guarantee.
- Before any protected **empty-workload** Spot capacity trial, the creator requires an earlier actual empty-stack rollback and exact CloudTrail CFN-role `DeleteAutoScalingGroup(forceDelete=true)` evidence, then independently rereads its stack/template/group absence/event. A manifest or API ACK alone cannot authorize capacity. Numeric LT1, zero capacity, native deadline, protection, 100%Spot, no guest authority and encrypted disposable root are read back first. The later protected trial still needs actual protected/running + scheduled-zero observations, real native deletion/EC2 terminated/root absence and preserved evidence. This feature is not yet proved by pure tests, not production safety authority, and never grants larger validation budgets. EC2/EBS costs are separate; no credit/Free Tier assumptions.

- Actual empty probe `cd18a0e94fb2` reached its missing-signal timeout and ROLLBACK_COMPLETE/group absence, but CloudTrail event09c0e46c recorded native CFN DeleteAutoScalingGroup **without forceDelete**. This is a negative result for the stronger protected-expiry gate, NOT permission to start protected capacity. Earlier IAM propagation and narrow RunInstances authorization failures occurred at0 capacity and are preserved separately. `audit-empty` rereads native sources and keeps this outcome unverified.
- `scripts/spot-fleet-expiry.py` is the alternative disposable-only experiment: `create-zero` reads fixed native Spot Fleet ValidUntil/TerminateInstancesWithExpiration at0 capacity; `activate` separately rereads cloud state before Spot target1 and attaches the empty guest to a protected ASG. The first real triale7 showed AttachInstances refuses a Launch-suspended group; that failed attachment is NOT protected-expiry proof. The corrected empty-only experiment requires a native launch hook (30second heartbeat/defaultABANDON/no notification target or external heartbeat), plus the fixed ASG off request, before allowing ASG launches. This bounds any ASG-born replacement outside the Fleet roster without an external controller. It is disposable containment, NOT production policy; no actual user work is accepted. Mandatory launch tags precede tag-scoped CUSTOMER-role termination permission, and that customer role explicitly denies the original instance. Actual native expiry uses the separate AWSServiceRoleForEC2SpotFleet (observed in CloudTrail); customer-role simulation alone is NOT proof of the real termination actor. Native Fleet ID/history, exact expiry time, that service actor, actual EC2 terminated/root absence and protected-live/zero-request custody must all agree. Actual scopea6401bc9d875 proved this ONE empty protected-member expiry: native off02:29:57Z left it protected/InService/running; fixed Fleet expiry02:37:57Z was followed by Fleet's native termination02:38:02Z, later ASG reconciliation02:38:22Z, actual terminated state and exact root absence. The earlier single-actor audit failed on that second native event; it is preserved, not hidden. The auditor requires a unique earliest exact Fleet actor and permits only strictly later exact ASG reconciliation. This is NOT production configuration, a larger test budget, OS/EBS recovery, or production zero-capacity wake proof. ASG-born replacement ABANDON execution was not exercised. `verify-spot-fleet-expiry-aws.py` is a separate original-host-only readonly API observer: exact256MiB/Swap0/halfCPU/sharedOOM/NNP/score1000 and2GiB resource headroom, original IMDS/home UUID, pinned bytes and fixed API roster. It persists actual protected-running/zero-request/terminal/root-absence and raw native history on retained home without an operator polling loop. Capture completion alone still does NOT verify native causality, OS/home recovery, whole tracking or production readiness. Trial creator8fc returned a transient Pending-state protection error after attaching; the member inherited true default protection without operator correction, and cloud observation/expiry completed. The newer settled-member creator fix has pure tests but still needs fresh actual end-to-end execution; do not rewrite that failed CLI result as successful.
- `scripts/spot-recovery-canary.py plan|create-zero|activate` prepares a separate EMPTY recovery builder: exact preexisting protected-expiry capture is pinned and its native history/actors reread, native Fleet110min plus ASG off5min earlier, single r7g.large Spot32GiB encrypted root, exact SSM-only guest role/profile and owned-ASG protection permission, native30s ABANDON for ASG-born replacements. Zero provisioning never requests capacity; activation rereads native config/LT/profile/all inline+managed policy rosters. Guest storage/EIP/snapshot/termination permissions remain denied. Fixed native expiry may later contain a protected DISPOSABLE boot, never accepted work. Public IPv4/EC2/EBS/S3 are separately billed; no paid scheduling stack. Immutable recovery control bodies are conditionally created and body-read back in S3. This is not yet actual recovery/automatic Spot replay proof.
- `modules/linux/recovery-system.nix` evaluates a REAL isolated NixOS using the maintained storage/cache/admission/user-manager/Docker startup modules. HM alone is inert/public and explicitly not real HM proof; production EIP and SSH are disabled, protected volume IDs/UUIDs rejected, guard disarmed. Actual scope8f0a79c26d13 now has fresh REAL boot evidence for this fixture only: positive boot93c49245 restored the exact encrypted16GiB home/cache before user-manager/Docker/inert-HM; wrong UUID boot70bc1d3c left startup starting and workloads0; delayed boot3179a849 remained closed during a native90s IAM AttachVolume denial then automatically attached/mounted/restored/opened. No readiness override or forced detach was used. All complete journals/actual units/observer bytes/body hashes were autonomously copied to original retained home under `recovery-OS-v2-received-8f0a79c26d13`. This does NOT prove real HM/EIP, missing-store/root replacement, delayed OLD-owner release, durable pending-snapshot recovery, whole producer/output/raw-I/O safety, or production shutdown/wake. The fixed Fleet expiry actually terminated that protected member/root; CloudTrail identifies Fleet05:49:21 followed by native ASG05:50:11. The independent empty-home CFN deadline then actually deleted its detached16GiB home at05:59:44; exact own role/stack events and real volume absence agree. All86 bucket bodies (including failures/control/progress) were preserved/rehashed on original before bucket/customer-role/profile/LT/empty-ASG/stack/temporary-original-policy cleanup. Cancelled history/shared nonbillable service role remain intentionally. Original boot/system/profile/SSM/Docker/user/home/EIP/protection/baseline2IAM and operational status stayed unchanged. No production cutover or full goal completion follows. The current observer uses the real spot_work.RUNTIME startup path; earlier immutable-/etc nofollow and nonexistent-/run/spot-work observation failures are preserved and never relabeled as success. Whole618/22suites/17compiled/source220+separate12 belongs to71d; actual OS fixture proof/source222 belongs toa4e43f1, not a promotion of that older whole regression. A fresh-root coordinator missing-log-parent bootstrap failure is fixed in the maintained launcher (create/check private owned parent). Actual ARM private1GiB/source8a3f4ae222 ran all pipeline26, peak30576640/noOOM/no skips or ResourceWarning; own definition removal preserved live OOMgroup1/MemoryMax and exact cgroup/definition were later absent. These mock-based operator cases still are NOT fresh replacement-bootstrap execution or another whole618. After full cloud archive/body+source/legacy SHA readback, all15 named old local deployment scripts (including aws_cli.py/paid prototype and /tmp helpers) were actually removed; audited legacy roots have zero scripts, credentials/logs/JSON/user data/public maintained Git source untouched. Full cloud workflow and production0-wake remain incomplete. The original-host readonly observer has a fixed `--purpose recovery` identity (exact base image/own profile/32GiB root and at most one own-tagged encrypted16GiB fixture home); it does not grant general networked validation or larger build authority.

### Native UserData bootstrap/replacement preparation (ZERO capacity only)

- `scripts/spot-canary-bootstrap.py plan|create-zero|configure-zero` prepares a separate unprotected/empty native-ASG Spot builder, NOT a protected OS-recovery deadline. The actual pinned Nixpkgs `amazon-init.nix` was read on the cloud host: a `#!` UserData is executed by its runtime shell, not implicitly a NixOS reconfiguration. Actual native UserData execution/replacement replay is still NOT proven by this source inspection.
- Numeric trial LT2 freezes a <=16KiB decoded shell/compressed Python bootstrap. It starts only its own128MiB/CPU10%/Swap0/NNP/score1000/Nice19/actualOOMgroup transport, checks actual IMDSv2/STS/Spot/ASG unprotected membership/native expiry/encrypted32GiB single-root/no retained home, then verifies all three pinned S3 bodies and a complete clean shallow Git commit. The source package points at public GitHub, never a laptop path. No real config/keys/user home are copied; exact public runtime b66b… contains only kiro-cli/openclaw-npm (actual44811 archive members inspected). Existing boot/runtime custody is never reset/overwritten.
- Only then does the existing launcher perform its own fresh disposable/memory attestation and start its separate256MiB coordinator→6GiB build→private2GiB regression/declaration/package chain. The transport is NOT build/verification authority. Instance+boot-derived32hex artifact runs cannot overwrite previous/replacement results. Guest storage/EIP/snapshot/termination/protection/capacity mutations stay denied; only regional DescribeVolumes is added.
- `create-zero` provisions no capacity; `configure-zero` verifies frozen UserData/numericLT2/profile/all inline+managed rosters/native off/100%Spot and uploads immutable body-readback source/authority/public software. Standard-role CloudShell can configure after the original cloud host publishes its retained public archive; no Mac or Mac AWS profile is a runtime dependency. EC2/EBS/IPv4/S3 cost separately if a future paid trial is admitted.
- There is deliberately NO paid activate action yet. Autonomous original-host run discovery/body receipt, bootstrap failure delivery before root expiry, preactivation admission and replacement test containment must be implemented/proven first. Actual ARM private1GiB **68=bootstrap25+builder17+pipeline26/source4f9dd12/224files** passed, peak36446208/noOOM/no skips/ResourceWarning. Exact unit/cgroup/definition collection and live parent OOMgroup1/MemoryMax preservation were read back without daemon-reload. Complete shallow Git archive819730bytes/SHA891c1eb0…/HEAD+224SHA+tracked roster were independently verified on cloud; first metadata readback's missing Git PATH and a before-execution null serialization failure remain separate failures (fresh explicit Nix-store Git readback passed). These mock/fixture-based operator cases are NOT actual native UserData execution/new-root boot/full618/replacement/production0-wake proof. No new EC2/EBS/IAM/bucket/association/scheduling resources or paid activation were created for this phase. Full goal and all remaining production gates above stay active.

### Off-root drain/backup authority (prepared, not activated)

- `spot_ledger.py` makes one explicitly seeded S3 object authoritative for both drain and backup intent, independent of the disposable root and removable home. Schema2 binds account/region/the exact ASG UUID ARN/home EBS/UUID/UID/Gateway configuration. Schema1 is refused, not silently upgraded or reset. The local journal is only a diagnostic cache. Missing/denied/malformed/foreign remote state never falls back to empty/local readiness, and arming requires `services.spotScheduleGuard.durableJournal = { bucket = ...; key = "journal/<namespace>/state.json"; };` plus the exact `services.spotScheduleGuard.asgARN`. Current membership/protection checks also reject a recreated group with the same name.
- Every update uses an exact ETag conditional PUT and checksum/metadata/body GET. There is no unconditional overwrite, PUT retry, TTL lease takeover, delete or runtime seed/reset path. A lost PUT reply can be resolved only by the exact fresh proposed revision/body; competing/stale state remains closed. Current journal objects must have **no expiration lifecycle**. `scripts/spot-journal-policy.py` prints exact-object Get/Put and service-side TLS/conditional-write policies; it grants no runtime List/Delete/bucket control; replacement fencing additionally needs regional read-only `ec2:DescribeInstances` and `autoscaling:DescribeScalingActivities`, which the renderer includes. Provisioning and an explicit first seed require independent operator review of existing data/intent; runtime does not infer seeding permission from absence.
- A replacement needs either the exact EC2 account/instance `terminated` state or, ONLY after definitive EC2 absence, an independently successful native ASG termination event. Live/stopped/shutting-down/denied/malformed/transport outcomes never select the history path. The entire bounded history (explicit no-auto-pagination, up to8x100 rows) must have exactly one completed `Terminating EC2 instance: <exact ID>` event for the exact ARN/name, UUID activity ID, Successful/typed100 progress and ordered/zoned/nonfuture completion times. Launch/detach/substring/ACK/name reuse/partial/cyclic/contradictory pages remain closed. The verified irreversible witness and new writer are committed in the SAME CAS; referenced origins plus bounded recent receipts survive root-cache and AWS history loss without an implicit reset. Missing both independent sources still blocks. Same-boot owners still need actual PID/start/namespace exit proof. Snapshot uncertainty remains uncertainty even through repeated root replacement; no CreateSnapshot retry, service startup or unseal is authorized by a terminal witness alone. Old-boot work approvals never authorize new-instance termination.
- Protected startup now inspects/reconciles remote backup intent **before attach-home can proceed**. Ordinary recovery reconciles it before mounting home/restoring services/unsealing. New boot readiness also refuses pending remote intent even if the new root has no local journal. This is not all-producer tracking, privileged raw-I/O fencing or approval to activate production.
- `test-spot-ledger.py` has58 pure/injected authority/adapter cases. `verify-spot-ledger-aws.py` separately requires real IMDS, source authority, a kernel-readback256MiB/Swap0/halfCPU/OOM-group/NNP one-shot and nine exact test objects. It checks real S3 CAS/concurrency/checksum readback, actual late ASG-ARN terminal evidence and same-CAS persistence/cached receipt, actual live PID refusal and injected lost reply/local-cache deletion. Synthetic old-drain fixtures are NOT actual OS/root-loss/EBS recovery evidence; it cannot mutate EC2/ASG/EBS/services or publish arming flags.

```sh
python3 modules/linux/test-spot-schedule-guard.py -v
python3 modules/linux/test-spot-profile-cache.py -v
python3 modules/linux/test-spot-cache.py -v
python3 modules/linux/test-spot-validation.py -v
python3 modules/linux/test-spot-work.py -v
python3 modules/linux/test-spot-acp.py -v
python3 modules/linux/test-spot-gateway.py -v
python3 modules/linux/test-spot-backup.py -v
# 실제 Linux 회귀는 canonical bounded driver로 실행한다.
# 아래 개별 Linux 검증 예시는 해당 resource cage 안에서만 실행:
# root Linux sandbox (Mac의 skip은 실행 증거가 아님):
python3 modules/linux/test-spot-work-linux.py -v --tool /absolute/prepared-system/sw/bin/spot-work
python3 modules/linux/test-spot-acp-linux.py -v
python3 modules/linux/test-spot-gateway-linux.py -v
# root Linux 필수; skip으로 성공을 대신하지 않는 private Nix store 검증:
python3 modules/linux/test-spot-cache-linux.py
nix-instantiate --parse modules/linux/spot-schedule-guard.nix
nix-instantiate --parse modules/linux/spot-profile-cache.nix
nix-instantiate --parse modules/linux/spot-home-volume.nix
nix eval --no-write-lock-file --raw \
  'path:/absolute/path/to/this/worktree#nixosConfigurations.linux.config.system.build.toplevel.drvPath'
```

이 브랜치의 패키지는 aarch64-linux이므로 전체 빌드는 AWS의 ARM 빌더에서 해야 합니다. 운영 루트가 부족할 때 큰 이미지 빌드를 밀어 넣지 않습니다. 진행 중인 작업이 있는 운영 서버에 전체 switch/reboot/terminate를 실행하지 마세요.

새 이미지 검증이 끝나기 전 `services.spotScheduleGuard.armed`를 true로 바꾸거나 검증 플래그를 임의로 채우지 않습니다. 관찰 단계는 실수로 종료를 활성화하지 않도록 설계되었습니다.

## 실제 네이티브 부트스트랩·이미지 후보 (2026-10-29, 범위 제한)

- `d521546`/231파일, 빈 Spot 범위 `76e73035372b`: 숫자 LT2의 **네이티브 UserData → 공개 소스/런타임 수령 → private2GiB 런타임 추출 → 별도256MiB 코디네이터 → 실제 ARM 전체618(558+60)/22 suites/17 compiled → 별도 선언12 → 조건부 S3 전체 body readback → 원본 서버 자동 발견·전체 수령**을 실제 확인했다. 런치 ACK나 수동 SSM 부트스트랩을 성공으로 대신하지 않았다. 원본 수령본은 `/home/persist/root/autoreceived-76e73035372b-90acfb76c4a249bd9810b6c45d52b8dd/run-805be21d8e9d07933dadc68a9d8e45ec-f2128d25efec4e85b51a054d2c310ca3/attempt-5ee9ee45e0734357b30441ccbef6e6a1`에 있다. 빌드 peak3345702912bytes/OOM0. 이는 운영 idle/종료/복원 승인이 아니다.
- 첫 빈 시도 `bbe979458515`의128MiB 추출 OOM은 실패 그대로 원본에 보존하고 인스턴스/root 및 임시 자원을 정리했다. 두 번째 범위의 게시자도128MiB에서 OOM으로 실패했으며 당시 capacity0이었다. `51e3a36`은256MiB 메타데이터 코디네이터와 **각각 별도128MiB/CPU10 AWS CLI**로 분리했다. 이미 커밋된 세 파일은 HEAD+전체 GET으로만 조정했고 **잃은 데이터 PUT을 재실행하지 않았다**. 새 완료 키만 조건부 게시했다. private 예산의 성공은 운영1GiB 빌드 용량 증거가 아니다.
- `spot-image-candidate.py`는 독립 수령618과 현재 정확한 ASG ARN/비보호/nativeoff를 확인한 후에만 새 암호화32GiB 빈 이미지 볼륨을 만든다. 신호 없는 CFN 정상 rollback은 compute 만료10분 뒤의 별도 정리 요청이며 강제 분리나 엄격한 wall-clock 보장이 아니다. 기존 root/home/candidate는 명시적으로 제외한다.
- 그 새 볼륨에서 `spot_image.py`의 **private2GiB/local-store-only 오프라인 설치**, ARM64 GRUB, 정상 unmount가 실제 통과했다(peak2147483648/max45011/OOM0). 실행 중인 OS/profile은 바꾸지 않았다. `bab03d8`의 별도 private1GiB 검증은 타깃 내부의 절대 symlink, 비어 있는 machine/agent/secret custody, ARM64 UEFI와 **실제1169개 NAR 전체 hash**를 확인했다(peak1073741824/max48467/OOM0). 완전 로그378307bytes/SHA `94c75a8dde8092d074f628989484d604a9d78ea5ec17793b378cfa83dd8e693d`. 정상 unmount 뒤 정확한 device epoch FD를 유지하되 **모든 privileged raw-I/O 차단 증거는 아니다**.
- 이미지 검증의 첫 호출은 결과 parent 부재로 **단위 실행 전에 실패**했다. 그 실패/원본 레시피를 보존하고 새 경로에서만 수정했다. 설치 로그188406bytes/SHA `957f94fc70f1dc89f22dec93d9846965bbc776951f8a8a3a6f3bf313b81335c0`. SSM stdout truncation은 전체 로그 수령으로 세지 않는다.
- 새 암호화 snapshot **snap-0af40fce97dc2db31**의 실제 completed를 읽고 FD를 정상 해제·정확한 cgroup/definition 소멸을 확인했다. ARM64/UEFI AMI 후보 **ami-04c8ba21b0f989bbe**를 등록했다. 전체 설치/NAR/privacy/추출44811(peak1230057472/OOM0) 증거182911bytes/SHA `3c2c0a665600e29ffb02307534cc6ce91d5b804e4396df08df6d10f47ee83672`를 원본 `/home/persist/root/image-received-76e73035372b-cef559b006b14fd0b3b0a2bf7954c2fc`에서 재검증했다.
- 빈 fixture만 정상 ASG 종료 후 시험 LT3으로 위 AMI를 부팅했다. 첫 후보 인스턴스는 **실제 capacity-loss Spot reclaim**(Server.SpotInstanceTermination, sir-djxfqrcj/instance-terminated-no-capacity)됐고 ASG가 **i-0c8048f3c09fa9098/boot07ff4831-0fe3-4914-8780-9c90f98b0b89**로 자동 대체했다. 실제 profile/current=iv2/kernel6.18.38/SSM active/home 없음/startup starting/Docker·user PID0/armedfalse를 읽었다. 전체1062 journal 및 PID1 JSON343records(메시지 없는8개도 보존)에서 실제 ordering cycle0을 원본이 독립 확인했다. 전체 archive76971bytes/SHA `896b3864037aa43d701ed18392d4687baa09f4935e9f302a004c4abc3c798c23`, 원본 `/home/persist/root/AMI-boot-received-76e73035372b-b639c3fa4887431096a58abf2047d94f`. 이는 **닫힌 부팅/AMI 대체** 증거이며 real home/EIP/HM 또는 UserData full-pipeline 재실행 증거가 아니다.
- 첫 후보 부팅의 SSM gzip stdout는 truncation으로 전체 전달에 실패했다. 그 root가 실제 Spot 회수되며 전체 journal은 회수하지 못했다. 관찰 코드의 자기 명령 문자열에 들어 있는 cycle 문구 오탐과 MESSAGE 없는 JSON record 실패도 보존했다. 새 부팅의 fresh archive에서 정확한 PID1 메시지만 분류하고 원본이 전체 record를 다시 읽었다. 실패를 덮거나 같은 데이터 PUT을 재시도하지 않았다.
- 운영 LT **lt-01468c818ef1bb11a의 숫자2 후보**를 실제 생성했지만 **UNAPPROVED**이며 default와 운영 ASG 참조는 계속 **1**이다. 기존 protected 원본을 전환/종료하지 않았다. 운영 guard 활성화·real recovery·실제 운영 zero→재생성은 별도 후속 게이트다. `armed`, `work_tracking_verified`, `goal_complete`는 계속 false다.
- 고정16:46:28Z nativeoff 뒤 실제 시험 ASG Min/Max/Desired0/member0 및 세 인스턴스 terminated를 읽었다. 최종 native ASG service-linked TerminateInstances **16:46:43Z/event19dbd3a0**는 forcefalse/skipOsShutdownfalse였다. 수동 deadline 연장/강제 종료/분리를 하지 않았다. 전체 bucket 당시 **67objects**를 원본 `/home/persist/root/phase36-complete-S3-mirror-8266a11df45b4c4a9ad63ff1fad6cf02`에서 전체 SHA/길이/ETag로 검증했다(receipt SHA `c775ac403c774fb14889c2fdfd72ceb13b579b46aa2c379df8cb4eb8534cbde3`). 뒤에 추가한 source/control85+plan archive574660bytes/SHA `3c89166a6262e0c698950fcb271e798704691cdc9db05c1d204cdc4552615f83`도 원본 `phase36-current-controls-15d44d7269c545edab5fca1e90037695`에서 전87record를 별도 검증했다. 이미지 볼륨은 **16:56:57Z CFN 전용 role의 DeleteVolume/eventc3c48e43**로 실제 삭제됐고 genuine timeout→ROLLBACK_COMPLETE/두 resource DELETE_COMPLETE/실제 volume 부재를 확인했다. 그 빈 stack·시험 ASG(no force)·시험 LT·profile·고객 role2개·bucket68objects·자기 원본 임시 policy2개도 삭제/부재를 재조회했다. 의도적 후보 AMI/snapshot/운영 후보 LT2만 보존하며 원본 IAM baseline2 SHA는 그대로다.
- **8d346341/source235의 실제 ARM140/9suites**도 별도 private1GiB/최소2GiB/Swap0/CPU≤1/OOM1/NNP/score1000에서 모두 통과했다. peak37199872/모든 OOM events0/no skips/ResourceWarning, live fence 보존/정확한 단위·정의·cgroup 소멸을 재확인했다. 원본 `/home/persist/root/rollout-phase36-ARM140-20261029/ARM140-full-and-cleanup.json`, result SHA `1a4099fe3cc0046abbd9e9f1f056a6bd31166ca723347d6499d1494e223e64b4`. 이는 새 helper 회귀이며 d521/source231의 whole618 증거와 구별한다. 보존 후보 AMI/snapshot/운영 LT2는 의도적 예외이고 운영 원본의 EC2/EBS/EIP 비용도 계속된다.

## 현재 종료 보호의 원인 확인 (2026-10-30 실측)

운영의 **ASG 보호 설정**과 **실행 중인 guard의 작업 보류 판정**을 구분해야 한다.

- 실제 운영은 `ProtectedFromScaleIn=true`, ASG Desired0/new-member protectiontrue다. 최근02:00 KST native 종료 요청은 `Could not scale to desired capacity because all remaining instances are protected from scale-in.`으로 취소됐다.
- 현재 실행 중인 구형 `2gb47…` 시스템에는 **guard 실행 파일/service/timer가 없다**(`LoadState=not-found`). `/etc/spot-schedule-guard.json`의 `armed=false`는 남아 있는 수동 설정일 뿐, 실행 중인 observer가 아니다. `/run/spot-schedule-guard/status.json`과 현재 작업 custody/arming manifest도 없다. 따라서 현재 보호 이유를 “guard가 특정 작업을 busy로 판단했다”라고 설명하면 부정확하다. 실제 원인은 **보호 플래그 유지 + 운영 controller 배포 누락**이다.
- 새 AMI/후보LT2/시험 성공은 기존 운영에 배포됐다는 뜻이 아니다. 현재 cache schema1/unencrypted home/미배포 작업 추적·백업 및 복원 게이트도 남아 있으므로 보호를 먼저 해제하거나 승인을 채우지 않는다. Herdr/Kiro/Bun 프로세스의 존재나 빈 registry도 busy/idle 증거로 사용하지 않는다.
- `scripts/spot-protection-audit.py`는 standard-role CloudShell에서 ASG+bounded SSM metadata를 읽어 `protected_without_deployed_guard`, timer 비활성, observation mode, 관찰 unknown을 구분한다. guard를 실행하거나 lease 초기화/서비스 reload·restart/보호 해제/IAM 변경을 하지 않는다. 단발 reader는 private-network128MiB/Swap0/CPU10/OOM-group/NNP로 제한된다. gzip 전체 SHA/길이/schema/최대1MiB/SSM truncation/ASG 전후 변경을 검사하며 **자동 보호 해제를 권하지 않는다**.

```sh
# 공개 feature/linux-on-cloud checkout + standard AWS CLI role, Mac 상주 작업 불필요
python3 scripts/spot-protection-audit.py --output protection-audit.json
# 로컬 operator profile이 필요한 경우에만 --profile을 명시한다.
python3 scripts/test-spot-protection-audit.py -v
```

진단은 실제 canonical `/run/spot-schedule-guard/startup` 및 root-owned runtime/admission.lock/leases/participants metadata를 읽는다. 존재하지 않는 `/run/spot-work/state.json`를 사용하지 않으며 canonical source와 경로를 대조하는 회귀도 포함한다. **e7f575b/source237의 실제 ARM21**은 private1GiB/최소2GiB/Swap0/CPU≤1/OOM1/NNP/score1000에서 전부 통과했다(peak33083392/모든 OOM events0/no skips/ResourceWarning). live fence 보존과 정확한 자기 cgroup/definition 소멸을 확인했고, 완전 로그·결과는 원본 `/home/persist/root/protection-audit-20261030/ARM21-full-and-cleanup.json`에 보존했다. 최신 read-only 실제 운영 진단도 `protected_without_deployed_guard`를 반환했다.

후속 배포는 원본 작업을 강제로 재시작하지 않는 관찰·수집 단계부터 진행하고, 재부팅 지속성/실제 모든 작업 custody/backup·real recovery를 통과한 뒤에만 arming과 운영 ASG 전환을 허용한다. **진단 보완은 종료 자동화 배포 완료와 다르며 이번 감사에서 운영 guard를 설치하거나 보호를 해제하지 않았다.**

## 운영 실제 적용 1단계: 읽기 전용 observer (2026-10-30)

- 원본에 **`spot-protection-observer-dd163c0b2143.service/.timer`**를 실제 설치·실행했다. 5분마다 인스턴스 역할로 IMDS/STS/정확한 ASG ARN/home metadata/SSM session과 로컬 상태를 읽는다. **종료 guard가 아니며** 보호·capacity·IAM·home/EIP·작업 registry를 바꾸거나 서비스/OS를 재시작하지 않는다. 새 진단은 `protected_observer_only_guard_not_armed`다. `armed/work_tracking_verified/goal_complete=false`는 유지한다.
- 실제 상태는 **`/var/lib/spot-protection-observer/dd163c0b2143/status.json`**, 설치 receipt는 같은 디렉터리 `install-verified.json`이다. 원본 boot/profile/current2gb47 및 SSM901/Docker1318/user743, 원래 guard config SHA와 operational-status SHA가 전후 동일했다. `spot-protection-audit.py`는 이 observer 존재를 full guard 배포/종료 승인과 구분한다.
- 수동 시작 없이 **실제 다음5분 timer 실행**도 확인했다. invocation `7e4d38ca…`→`f04cda8e…`, timer LastTrigger 변경과 새 완전한 status/기존PID 유지가 일치했다. 증거는 원본 `/home/persist/root/observer-deployment-20261030/autonomous-timer-full-proof.json`(SHA `79d7005eaed7680a4f5174148e0abe8c3f34e7331f27ae58b6e6f7fbc9485902`)에 보존했다. 증거 watcher는 만료형 cloud 단발 reader이며 운영 timer가 로컬 Mac을 필요로 하지 않는다.
- metadata parent256MiB/CPU25/PrivateNetwork/Swap0/OOM1/NNP/score1000, AWS·IMDS 각각 별도128MiB/CPU10/exec-only/read allowlist다. 새 scheduler/EC2/EBS/IAM 권한을 만들지 않았으며 로컬 상주 controller가 필요 없다. 운영 journal만 사용한다.
- 원래 `/etc/systemd/system`은 Nix store의 읽기 전용 symlink라 건드리지 않았다. **낮은 우선순위의 `/usr/local/lib/systemd/system`**에 새 versioned units와 persistent `timers.target.wants` vendor link를 배치하고 새 이름을 on-demand로만 로드했다. global daemon-reload/enable/NixOS switch/reboot는 하지 않았다. `systemctl is-enabled`는 vendor link에 대해 **disabled**이며 이를 enabled로 꾸미지 않는다. 실제 지속성 근거는 persistent unit search path/정확한 boot link/원본 interpreter GC root다. **운영 재부팅은 수행하지 않았으며 새 root/Spot 재생성 지속성도 아직 아니다.**
- 다음 clean image에는 `modules/linux/spot-protection-observer.nix`가 선언적으로 포함되도록 추가했다. 현 운영 ASG/defaultLT1 및 후보AMI04c8/LT2는 변경하지 않았다. 현재 warm bridge를 새 AMI에 포함됐다고 주장하지 않는다. 유지관리 도구 `scripts/spot-deploy-observer.py`의 install/owned-only rollback은 기존 작업을 강제로 정리하지 않는다. 미래 Nix-managed marker/unit으로 교체되면 warm rollback이 새 선언적 unit을 중지/삭제하지 않도록 marker symlink/실제 FragmentPath를 확인해 거절한다.
- 사전 actual ARM53/source243/c88dc750(21audit+21observer+11deployment), private1GiB/최소2GiB/Swap0/CPU≤1/OOM1/NNP/score1000/peak32710656/OOM0/no skips/ResourceWarning 및 Nix2파일 parse를 확인했다. 첫 shared-slice child fixture는 systemd가 수동 OOM fence를0으로 재적용해 실행 전에 거절됐고 실패를 보존했다. 후속 process-free target의 실제 timer trigger/단위 lookup/boot link probe는 fence1을 유지하며 통과했다. 이는 actual reboot proof가 아니다. 미래 Nix 소유권 전환을 보호하는 새 rollback 도구13개도 별도 actual ARM13/source2fd4953/private1GiB에서 통과했다(peak27979776/OOM0/정확한 scope·definition 소멸). 이 변경으로 원본 resident byte를 재배포하지 않았으며 실제 운영 rollback은 실행하지 않았다.

## 작업 추적 warm-adoption: 신규 비대화형 shadow 파일럿 (2026-10-30, 부분 적용)

- 사용자 요청 순서는 **격리 시험 → 운영 적용 → 실제 동작 → 재시작 → 갱신 lock 기반 재적용 → 재검증**이다. 그중 **기본 shadow 계층**을 원본에 적용했다. 실제 Kiro/Herdr 세션·기본 launcher를 바꾸거나 완전한 작업 추적을 선언한 것이 아니다. 다음 단계는 신규 provider/PTY/ACP 세션의 안전한 연결·output delivery·MCP/subagent/SSM/Docker 우회 경계다. 이 조건이 남아 있어 **운영 OS 재부팅/전체 NixOS switch/새 AMI·ASG 승격/갱신 lock 재적용은 아직 하지 않았다**.
- `modules/linux/spot_shadow.py`는 시험된 `spot_work.run_job`의 subreaper/`__WALL`/lease-before-spawn/uncertain-spawn 경로를 사용하되 **canonical Protocol.initialize/startup_ready는 호출하지 않는다**. 별도 root-private namespace를 명시적으로 `shadow_only/unknown`으로 seed하며 기존 UID1001 PID/start/pidnamespace metadata만 읽는다. prompt/argv/env를 조사해 기존 작업을 소급 승인하지 않는다. 새 기록에는 argv digest만 저장하고 **하위 프로세스 종료 뒤에도 output/external-work가 unknown이므로 기록을 지우지 않는다**. cancel/ack/force-clear/TTL/replay/takeover API가 없다. 이 로컬 기록은 off-root journal도 아니다.
- 실제 운영 버전 **498e2c5726a5**, `/var/lib/spot-work-shadow/498e2c5726a5/source/spot-work-shadow`, 같은 상위 디렉터리 `seed.json/jobs/status.json/install-verified.json`과 `/etc/spot-work-shadow-current.json`. **spot-work-shadow-498e2c5726a5.service/.timer**가1분마다 metadata만 읽는다. parent256MiB/CPU25/private net/Swap0/OOM1/NNP/score1000/Nice19. 새 EC2/EBS/IAM·paid scheduler는 없다. lower-priority persistent vendor units/boot link/interpreter GCroot이고 기존 immutable `/etc/systemd/system`이나 global daemon-reload를 쓰지 않는다. 실제 OS reboot/새 root 지속성은 아직 아니다. Nix 모듈도 선언했으며 미래 Nix marker는 Nix package를 가리킨다. owned disable은 새 Nix 소유권을 만나면 거절하고 jobs/outputs/source/runtime pin을 보존한다.
- 파일럿은 **명시적으로 실행한 합성 비대화형 작업**만 시험했다. child는 UID1001/groups없음/NNP1/정리된 환경/stdin devnull로 시작하며 stdout/stderr를 root-private 파일에 보존한다. 기존 interactive PTY를 이 도구로 대체하지 않는다. 장시간 실제 사용자 작업의 output quota/backpressure·durable delivery·off-root 보존과 producer 연동은 추가 검증 대상이다. 파일 전체 SHA 확인/exit0도 delivery/idle 증거로 바꾸지 않는다.
- 사전 source3941481/249SHA actual **ARM35=22pure+8deployment+5Linux**, Nix2파일 parse, private1GiB/최소2GiB/Swap0/CPU≤1/OOM1/NNP/score1000/peak39383040/OOM0/no skips/ResourceWarning/exactscope·definition소멸 후 한 번만 설치했다. installer 전후 boot63bfc3f0/current+profile2gb47/SSM901/Docker1318/user743/config·operational-status SHA/canonical registry·approval부재가 같았다.
- 실제 운영 합성 job **job-257a9f251a4046ccbe28dbb722afb10d**는 UID1001/NNP1로 실행해 **99bytes/SHA f5eb1fe13ec282d01947e54c2676cb178d69a2ec14169c936fb950d411bc44f1**를 남겼다. 살아 있는 동안 **새 metadata collector만 restart**해도 같은 lease와 child 실행이 유지됐고, 이후 두 번째 collector restart/seed 재확인 뒤에도 기록 byte가 같았다. 원본 `/home/persist/root/warm-tracking-20261030/operating-proof/complete-proof-and-cleanup.json`, raw proof SHA **f05e2bfa5e692c21dce959efcdad22a5dd65268162ff70ed737555f71400b428**. 운영 기존 앱/OS는 재시작하지 않았다. 별도 private1GiB/peak28684288/OOM0/live fence/exactscope소멸을 읽었다. 이후 수동 start 없이 새1분 timer invocation/status도 확인했다.
- source94ad020 actual ARM37에서 실제 fork 뒤 receipt-loss와 **owned 합성 wrapper만 SIGKILL**한 crash를 추가 검증했다. child는 강제 종료하지 않고 자연 완료하며 late output/unknown custody가 남았다. 미래 선언적 marker까지 보강한 최종 **source642f5d58af434626fee1fc6f70a49c506bfc922f/249SHA actual ARM38=22+9+7**, Nix2파일 parse/private1GiB/peak44351488/OOM0/no skips/ResourceWarning/live fence/exactscope·definition소멸도 통과했다. 결과 `/home/persist/root/warm-tracking-20261030/final-tests/ARM38-full-and-cleanup.json`, raw result SHA **b15c9c30fcb877bf23369d4ab65350d92e0f45822c694adabd42b5d91d00d10d**, full log SHA **1b41d2f0e776f93fbf236f13f9f487416038531810821fb37a0465d54726a84c**. 이는 새로운 whole618 또는 production idle/arming 증명이 아니다. 운영 두 Python byte는 사전394와 같아 재배포하지 않았다.
- main21bd8e8의 갱신 lock은 nixpkgs **95217612160f0b493513cde1d2402af54861d07c**, SHA **a0f4f9896f2726f5498c2fc326aea410c8d6452f05291bd14760d06c7746ca74**다. 기존 feature lock28d4/SHA39fbc997은 유지했다. main의 `nix-skills→agents-nix`/flake-utils 제거와 feature ARM64 설정 호환성 검증 없이 lock만 복사하거나 main x86_64 설정/미커밋 AI 변경을 가져오지 않는다. 현재 **work_tracking_verified/armed/goal_complete=false**, 기존 종료 보호를 유지한다.

## 신규 ACP keeper opt-in 적용·native mock 검증 (2026-10-30, 부분 적용)

- `spot_shadow_acp.py`와 명시적 `spot-work-shadow-acp` entry를 추가해 원본에 **e39a4b025d47**를 설치했다. 경로 **`/var/lib/spot-work-shadow-acp/e39a4b025d47/source/spot-work-shadow-acp`**, 설정/설치 receipt는 같은 버전 디렉터리, 발견 marker는 `/etc/spot-work-shadow-acp-current.json`. 기존 **498e2c5726a5 shadow store/collector와 모든 기록을 그대로 재사용**하며 canonical initialize/startup_ready/새 empty ready registry를 만들지 않는다. 설치는 app/model session을 자동 시작하거나 기존 TUI/Herdr launcher·서비스를 바꾸지 않는다. source4개와 Python/native store GC roots를 고정했다. 선언적 `spot-work-shadow-acp.nix`도 추가했지만 전체 NixOS switch/AMI 승격은 아직 아니다.
- root-only UNIX IPC의 keeper가 session/request lease를 native spawn/input 전달 **전에** fsync한다. 한 keeper에서 시도한 RPC ID는 ACK를 잃거나 terminal response가 와도 재실행하지 않는다. 검증되지 않은 async route는 전달 전에 거절한다. 기존 승인된 server-response continuation은 새 admission이 닫혀도 진행한다. 단순 consumer 연결 해제는 native stdin EOF/종료 신호로 바꾸지 않는다. 명시적 finish-input도 알려진 미완료 요청을 기다린다. 불확실 spawn은 부모가 미리 보유한 pipe와 `__WALL` own-child wait로 보수적으로 유지하며 spawn 재시도/TTL/takeover/clear/kill/ack API는 없다.
- 출력은 root-private immutable binary+metadata+**별도 `.exposed` commit**으로 보존한다. `fsync(data)` 후 tracker 상태를 반영하거나 admission을 닫은 뒤에만 읽을 수 있어 initialize 응답/다음 입력의 순서를 보장한다. backend stdout/stderr는 consumer가 없어도 보존한다. metadata에는 prompt/RPC ID/본문을 넣지 않지만 **비공개 output payload에는 응답 본문·ID가 포함될 수 있다**. 실제 사용자 payload를 증거 archive로 복사하지 않는다. 현재 실제 실행은 **비밀/실제 모델/네트워크 없는 mock뿐**이다. 2GiB reserve/세션64MiB·65536segment 제한은 삭제·강제 종료 대신 backpressure를 건다. 불확실 write/exposure는 재시도/다음 frame 소비 없이 unknown으로 대기한다. 실제 ENOSPC·대량 출력 복구, off-root 보존/암호화 및 trusted UI delivery는 추가 gate다. 읽기/해시/pipe flush/terminal/EOF는 consumer delivery나 전체 idle 증명이 아니다.
- native는 실제 **Kiro2.10 `kiro-cli-chat` 548212784bytes/SHA `1c2a36ec26bae2bdd8d5d7cbb77606f4d072b8bc1a5cfcc6b582ae4a047ce479`**로 제한했다. 새 lock이 다른 native bytes를 가져오면 실행 전에 거절하며 SHA를 맹목적으로 갱신하지 않는다. UID1001/groups없음/NNP1/정리된 환경/lease 이후 검증된 HOME으로 chdir하고 exec한다. private native fixture만 dummy mock env를 사용하며 실제 API key/private home/channel은 복사하지 않는다.
- 첫 source8c8e822 actual **ARM40은 Linux4개 실패**였다. durable initialize output이 tracker보다 먼저 공개되는 race였고 성공으로 바꾸지 않았다. 전체 log/journal/source/정확히 비어 있는 자기 definition cleanup을 **`/home/persist/root/warm-ACP-20261030/FAILED-first-ARM40-full-and-owned-cleanup.json`**, SHA **f36ebcfa792973dea7c4d1b09966b8764ec444cdb4564b9b7e1e085f8f6f5024**에 보존했다. 최초 실패 driver의 kernel peak와 정리된 fixture별 body snapshot은 미보존임도 명시했다. 전 attempt를 replay/덮지 않았다.
- corrected **b18e8ce3c1f1cb8f2bc0ee1af88325ee16b87080/source255 actual ARM42=26pure+8deploy+8Linux**, native mock2개/Nix2파일 parse/fixture별 snapshot8개 전체 SHA/완전 log를 확인한 뒤에만 설치했다. private1GiB/최소2GiB/Swap0/CPU≤1/OOM1/NNP/score1000/peak80642048/전memoryevents0/no skips/ResourceWarning/livefence·exactscope/definition소멸. 결과 **`/home/persist/root/warm-ACP-20261030/fixed-b18e8ce/ARM42-full-and-cleanup.json`**, raw result SHA **65b8c10b91b822868b53c8d2c14a4117ad00657670acebb183454aa4bc582f69**, full log **52ce75ab03baedd23c8365f24357a4fdd26039d861ca088c043a190c01c5c592**. 전체618/production idle/다른 lock 검증은 아니다.
- 설치 뒤 실제 설치 byte를 사용한 **source212b65c6b7c1c0d8dbc0973338e54e592e846630/source256 helper9 + operating native mock**도 통과했다. 원본 store의 새 session **job-7082bb8c10354522b018a18ae2d67161**, keeper121319/start23537834, 새 request3개를 보존했다. 별도 consumer process가 input 후 ACK를 읽지 않고 끝나도 keeper는 계속됐고, 다른 consumer 연결의 같은 RPC ID 재전달은 거절됐다. 출력10segments/**6676bytes**를 전부 읽고 SHA를 확인했다. 자기 verification cgroup/UID/PID-start를 검증한 **test backend121320에만 pidfd SIGSTOP/CONT**를 사용해 관찰했으므로 이를 실제 모델 지연이나 기존 앱 제어로 표현하지 않는다. 그동안 기존 shadow metadata collector만 restart해도 keeper/lease가 유지됐고 native는 재개 후 정상 종료했다.
- operating proof **`/home/persist/root/warm-ACP-20261030/operating-212b65c/complete-proof-and-cleanup.json`**, raw native proof SHA **2bb1d78f96b3a9c926958cb216a064763166ad2fe25a8d157504b8a08b5bb297**, raw driver result **71be8b122afcfdb47e8eb39478ef3bf03bcacc529ce7d38a814988ab9e9b0fde**. private1GiB/peak81743872/전memoryevents0/livefence·exactscope/definition소멸. 최초 generic job SHA도 변하지 않았다. **기존 사용자 TUI/Herdr/SSM/Docker/user manager/OS는 재시작하지 않았다**. consumer 재연결·시험 keeper 지속성은 증명했지만 실제 TUI 상태 복구·delivery ACK·keeper crash 이후 takeover/새 boot·off-root journal·모든 tool/MCP/subagent/우회 경계는 아직이다. current lock28d4/원본 보호와 `work_tracking_verified/armed/goal_complete=false`를 유지한다.
- 최종 readback에서는 기존 native weekday action **2026-10-30T07:30:03Z**, activity **0a86862e-dced-40a1-a438-6a1239ffac8b**로 Desired가 **1**이 됐다. 이 작업에서 capacity를 요청한 것이 아니며 같은 보호된 원본1대/boot·profile·SSM901·Docker1318·user743/default·ASG LT1/baselineIAM2는 그대로다. 새 instance를 생성/운영 zero-cycle을 완료한 증거가 아니다. generic1+ACP4개의 retained shadow records가 이후1분 timer에도 보이고 모두 output/consumer delivery 미검증으로 보호한다.

### 2026-10-30: 신규 shadow TUI의 실제 PTY·queue·parse-prefix 시험(운영 미설치)

- `spot_shadow_frontend.py`, `spot-shadow-kiro-frontend.mjs`, `spot_shadow_ui.py`는 **새로 명시적으로 시작한** UID1001 Bun actor만 PID/start/namespace/cgroup/공개 executable SHA/entry/실제 부모 및 SO_PEERCRED로 묶는다. draft/queue/attachment/action의 primitive census를 기존 동기 경계에 연결하며 canonical initialize/ready/clear/ack/takeover/기존 세션 재분류가 없다. opaque native helper도 별도 lease/검증된 HOME에서 실행한다. **아직 운영 entry/Nix module/default route로 설치하지 않았다.**
- keeper 출력의 길이/SHA를 확인한 뒤 stdout frame에 임시 transport tag를 붙이고, pinned parser가 dispatch **전에** 제거한다. content-free 누적 SHA prefix `{sequence,chain,count}`를 묶어 보고한다. 이는 **JSON 파싱 확인이지 dispatch 완료/UI delivery ACK가 아니며**, zero counters/close/terminal/read도 기존 custody를 지우거나 idle로 바꾸지 않는다. 보호 관찰 실패는 새 입력만 거절하고 기존 수락 작업의 state/output 계속 기록은 허용한다.
- source74d8910의 실제 private ARM **Python18+6 및 cloud Node26 JS10(총34)**가 통과했다. 로컬 Node 설치에 의존하지 않았다. Node SHA `b4f62973f7c1b615e5f4a6a264bd740bd3cdad75fe13a5e6601e8ee62e658a9c`는 보존된 공개 runtime archive와 전체 bytes로 대조했다. 최종 source40c805e/source263의 별도 **ARM49=Python24+JS25(기존 LocalCustody15 포함)/compiled5**도 통과했다(private1GiB/peak141811712/전memoryevents0/no skips·ResourceWarning/livefence·owned cleanup). 결과 `/home/persist/root/warm-TUI-20261030/final-40c805e/ARM49-full-and-cleanup.json`, raw result SHA `6151662707d2b5f3d9f082aa6ddd630b91f7dad2109c1ee98277929679489165`. 전체618 또는 새 lock 검증으로 확대하지 않는다.
- 실제 pinned Bun67892b/TUI67cec0/native1c2a36를 새 fake HOME/dummy 비기능 key/모델 mock/사설 network에서 PTY로 실행했다. 최초74d의 붙여 보낸 DEL, c362의 Ctrl+S 뒤 Enter 누락, 8e27379의 고정120ms 입력 병합 실패를 각각 그대로 보존했다. 5b7의 좁은 성공은 parse8 **초기화** prefix만 증명했음을 별도 확인하고, 모델별 prefix/실제 queue까지 더 강하게 검증했다. 재시도 입력/직접 store clear/기존 프로세스 조작으로 통과시키지 않았다.
- **20f26afd318c4cfd5fdbe35e46da2c713479e7c2/source263** 실제 PTY는 primitive 길이 응답으로 각 DEL을 확인하고, 실제 Ctrl+S queue mode+Enter로 수락한 두 번째 작업을 관찰했다. 정확히 자기 mock backend만 stable pidfd STOP/CONT했다. 시험용 admission fault 뒤 세 번째 입력은 vendor mutation 전에 거절됐고 기존 첫/queued 두 작업은 자연 실행되어 두 응답이 PTY에 보였다. 새 모델 stdout까지 parse prefix가 **8→14/offered14**로 따라잡았으며 final actor healthytrue/queue0이지만 **NOT_idle/output_delivery=unverified**다. 결과 `/home/persist/root/warm-TUI-20261030/ack-input-20f26af/full-attempt-and-cleanup.json`, raw result SHA `fcb465b1b1e5764ec4f69902cc99e59acac418968ef2c55cd686ac3462c868fb`; complete snapshot SHA `77997369281c4274fb86e292a40050978938f15b71ee1afa7ceb36035705d019`. private1GiB/최소2GiB/Swap0/CPU≤1/OOM1/NNP/peak451534848/전memoryevents0/live fence·정확한 scope/definition 소멸을 확인했다.
- 전체 source6×263, 실패/좁은 성공/강화한 실제 PTY의 snapshot5개 **195개 body**와 full raw console/log, control26/plan을 원본 `/home/persist/root/warm-TUI-20261030/custody-096aae86c17144a5b912af66e157370d/complete-source-failed-narrow-positive-strong-native-evidence.tar.gz`에 보존했다. **3157975bytes/1663manifest records/SHA `1fb17f1da805b3bfde378b7dcb9880b4531ee21d43f5fe7a31dfa003d1fa81c7`** 전부와 내부 body를 다시 해시했고 여섯 scope/definition 부재를 확인한 뒤 codec parts5개만 삭제했다. 실제 사용자 transcript가 아닌 새 합성 fixture뿐이다.
- 다음 gate는 실제 attachment/consumer crash·복구/Herdr·provider/tool/MCP/subagent/SSM/Docker 경계, opaque helper의 장시간 출력 quota/backpressure, off-root journal 및 신뢰된 delivery다. 그 뒤에만 새 운영 TUI entry 배포·설치 byte 재검증을 진행한다. 기존 observer/shadow/ACP 설치·원본 보호와 `work_tracking_verified/armed/goal_complete=false`를 유지한다. 실제 OS restart/갱신 lock 재적용/암호화 home 승격/전체 복구/운영 zero-cycle도 여전히 미완료다.

### 2026-10-30: 보조 명령 출력 backpressure·실제 파일 첨부·TUI 종료 격리 검증(운영 미설치)

- `spot_shadow_output.py`는 새 TUI의 **opaque native helper** 출력에 parent-owned pipe와 기존 private immutable segments를 연결한다. lease/pipe custody가 spawn보다 앞서며 stdout+stderr의64MiB/65536segment/2GiB reserve를 같은 lock으로 검사한다. 용량 부족은 최대 채널당64KiB를 보유한 채 읽기를 멈추며 삭제·truncate·accepted native kill을 하지 않는다. write/exposure 불확실성은 같은 write/다음 read를 반복하지 않는다. Popen receipt가 유실되면 자기 subreaped child set과 파이프를 유지하여 늦은 출력을 보존한다. bridge의1MiB 한도는 **양 채널 합계**이며 초과 본문은 보존하고 거절한다. 이는 기존 generic pilot의 regular-file 출력까지 바꾼 것이 아니며 off-root spill/무제한 출력 복구도 아니다.
- signed30719955f8511693fc392605b3f298fddab101fa/source266의 실제 **ARM67=Python36+Linux6+JS25**가 통과했다. UID1001/owned HOME/groups없음/NNP1, 양 채널 대량 출력, artificial-small-quota의 실제 pipe backpressure 뒤 자연 완료, fork 뒤 생성 receipt 유실/단 한 번의 late output, metadata consumer 종료, committed-write receipt 유실 hold를 확인했다. quota 복원은 새 synthetic fixture 내부에서 낮춘 값을 원래64MiB 정책으로만 돌린 것이며 운영 quota 변경 API가 아니다. private1GiB/peak161046528/전memoryevents0/full snapshot6/owned cleanup. raw result SHA `6a2686108f799196f995b256cbd769f4d2e3d7fadf182ed7eded8871d034cd5a`.
- root broker는 이미 묶인 frontend PID/start/UID/cgroup/namespace/entry가 사라지거나 불확실하면 같은 actor sequence를 유지한 채 **healthyfalse/unknown**으로 기록한다. keeper input EOF/kill/출력 폐기/기존 기록 reset/자동 proxy 재연결로 바꾸지 않는다. 실제 UI가 죽은 뒤 새 UI로 work/input을 재실행하는 takeover API는 없다.
- **1aaef2ad7726958bc6adfed23c736b78181941c8/source266 actual ARM69=Python38+Linux6+JS25와 별도 native PTY2개** 모두 통과했다. 새 fake HOME의 텍스트 파일을 실제 **@ picker→Enter→파일만 있는 chip**으로 첨부했다. 파일만 있고 processing/actions0이어도 drafttrue였고, synthetic marker가 실제 수락된 native prompt에 포함됐음을 **본문/ID 없는 fixture boolean**으로 확인했다. queue1→admission fault→기존 두turn 자연 실행/세 번째 거절/parse8→14/offered14 회귀도 통과했다. 이미지·음성·모든 첨부 경로를 검증한 것은 아니다.
- 두 번째 실제 PTY는 **새 mock Bun actor153601/start26068757만** PID/start/UID1001/namespace/cgroup/PGID를 확인한 stable pidfd로 종료하고 kernel exit를 관찰했다. root broker는 actor loss를 unknown으로 보존했다. 별도 keeper/accepted request는 유지됐고 자기 mock backend 재개 뒤 기존 immutable24files는 그대로, late stdout까지 **11segments/6705bytes**와 exposed terminal을 독립 root reader가 읽었다. 재실행/새 모델을 만들지 않았다. 이것은 **consumer death 격리/출력 보존**이며 replacement UI 복구·UI delivery·keeper crash takeover·OS 재부팅 증거가 아니다.
- 완전 결과 `/home/persist/root/phase42-output-20261030/native-1aaef2a/ARM69-native2-full-and-cleanup.json`, raw result SHA `4cbd3a7bb1a4f282f7fe37d8f99a97c3e760a01e17861d419d5f3bb489821900`, full log SHA `cbba59269ddf00e3051a4c41b093fdd3c749ba274c04b547b1d88fde86695d36`. private1GiB/min2GiB/Swap0/CPU≤1/OOM1/NNP/peak976146432/전memoryevents0/no skips·ResourceWarning/complete snapshot8개 전 body SHA/livefence·exactscope/definition 소멸을 확인했다. 한도에 가까운 peak이며 실제 사용자 용량/전체 최신-source regression/모든 producer 승인이 아니다.
- source3×266/controls14/전체 raw PTY·log·fixture snapshot14의 **486개 body**를 원본 `/home/persist/root/phase42-output-20261030/custody-98364804e12446e3996eae7afc9b6ccd/complete-helper-native-TUI-source-controls-and-evidence.tar.gz`에서 전부 재해시했다. **1751880bytes/849manifest records/SHA `8b08e0410185828f76ccc152541e11ee4d4f25d8489f627bb92fcb155220880a`**. 자기 두 scope/definition 부재 확인 후 codec parts4개만 삭제했다. 같은 boot63bfc/profile2gb47/SSM901/Docker1318/user743/observer·shadow timer active, 기존5기록 및 설치 ACP4 bytes를 다시 확인했다.
- **운영 TUI entry/default launcher는 여전히 미설치**다. 기존 observer/shadow/ACP/원본 세션·보호는 그대로다. 다음 gate는 명시적 신규 operating entry와 설치 byte 재검증, trusted UI delivery 및 conflict/keeper·off-root 복구, Herdr/tool/MCP/subagent/SSM/Docker/direct 경로다. full guard/암호화 home·백업·EIP 전체 복구/운영 restart/갱신 lock/5종 최저가/실제 zero-cycle도 남아 `work_tracking_verified/armed/goal_complete=false`를 유지한다.

### 2026-10-30: 명시적 신규 운영 TUI entry 설치·설치 경로 재검증(부분 적용)

- **새 선택형 entry `844c978e4dbc`를 실제 설치했다.** `/var/lib/spot-work-shadow-tui/844c978e4dbc/source/spot-work-shadow-tui`, 발견 marker `/etc/spot-work-shadow-tui-current.json`, 같은 버전 디렉터리 `install-intent.json/install-verified.json`이다. 기존498 store/collector와 기존 ACP4 bytes/5기록을 재사용·보존한다. root-owned12 source/고정 Python·native GCroots/공개 Bun·TUI 복사본을 검증한다. 설치 자체는 세션을 시작하지 않았고 기존 TUI/Herdr/default launcher/SSM/Docker/user/OS 재시작·global reload·canonical initialize/readiness가 없다.
- **독립 PID1 keeper**가 frontend/controller와 다른 cgroup에서 같은 소유 budget을 공유한다. 전체 consumer-controller가 죽어도 수락된 backend/pipe/출력을 유지한다. UI exit를 provider EOF/강제 종료/delivery로 해석하지 않으며 명시적 finish-input만 알려진 미완료 요청을 기다린다. 입력 재전달/keeper takeover/기존 세션 소급 승인/출력 retirement는 없다. 새 대화형 실행의 정책은2GiB/최소4GiB MemAvailable/Swap0/CPU≤1/NNP/score1000이며 build/verify 권한이 아니다. 시험은 **기존 private1GiB verify 권한을 그대로 상속**했고 일반 사용자 용량을 승인하지 않았다.
- 첫 actual ARM85의 sibling 시작과 ARM89의 sibling 종료에서 PID1이 수동 parent OOM flag를0으로 재적용하는 **실제 실패**를 보존했다. owner/boot/definition SHA/client PID-start/전체 participant를 검증한 **UID1001 작업이 없는 신규 gate**만 초기화한다. native child set이 자연 reaped돼도 frontend가 살아 있는 동안 root metadata holder를 유지하여 fence를 보존한다. 이후 exact cage에 인증된 metadata holder만 남고 native-reaped/output-pending receipt가 있어야 정상 metadata exit를 요청한다. PID0 unit만 정리하며 작업/출력/unknown은 지우지 않는다. shared/global daemon-reload나 살아 있는 사용자 scope 재초기화가 아니다.
- 중간 ARM88의 AF_UNIX pathname118/112bytes 실패도 보존했다. 그 attempt에는 **ACP lease와 backend_spawn_attempted intent가 존재했으며 native 실행은 확인되지 않았다**. session 생성 전에 두 endpoint의 Linux108byte bound를 검사하도록 수정했다. failed namespace를 reset/replay하지 않았다.
- source2a419d3 actual ARM91/Nix2/native2 후, 초기11-frame 부분 prefix를 성공으로 확대하지 않도록 fa57460의 stronger pre-native2에서 **실제 @ 파일chip/수락 queue/두 모의 응답/전체 stdout prefix8→14/actions0**을 확인했다(peak474873856/OOM0). 동일12 runtime bytes만 한 번 설치했다. 첫 설치 경로 proof는 새 job directory가 durable header보다 먼저 보이는 reader race로 실패했으며 full71-body snapshot/출력/정확한 owned cleanup을 보존했다. b5548f2는 missing header를 **명시적 PublicationPending**으로 read-only 대기하고 malformed는 거절한다. missing을 empty/idle로 간주하지 않는다.
- **b5548f264fe03be200653d35dd86060d36acc7ac/source272 actual ARM93=Python68(19+7+12+6+16+8)+JS25, Nix2 parse + 설치 경로 native2**가 모두 통과했다. 실제 설치된 Bun/TUI/native와 root-private fake HOME/비기능 dummy key/모델 mock/private network만 썼다. 첫 case는 파일chip/queue/응답2개/parse14와 NOT_idle를, 둘째는 **새 합성 root controller만 pidfd SIGKILL**한 뒤 독립 keeper/같은 수락 요청/late output을 확인했다. 기존 사용자/서비스/모델은 신호 대상으로 삼지 않았다. 신뢰된 UI delivery/교체 UI/keeper crash·재부팅 복구 증거는 아니다.
- 완전 결과 `/home/persist/root/phase43-tui-entry-20261030/operating-844c978e4dbc/postinstall-b5548f2/ARM93-installed-native2-full-and-owned-cleanup.json`, raw result SHA **1ebd770a9a934c05ea746b041285576d84bc2fd0caee25706aceeddde88ae352**. private1GiB/min2GiB/Swap0/CPU≤1/OOM1/NNP/peak377032704/전memoryevents0/no skips·ResourceWarning/livefence/정확한 scope·definition 부재, 설치12 bytes/artifacts/vendor SHA/GCroots와 **원래5개를 포함한32기록 불변**을 확인했다. 합성 시험15개와 앞선 failed-installed12개도 unverified로 보존하며 이를 user idle로 정산하지 않는다.
- 위 b554 ARM93은 설치 모듈 경로의 실행이었다. **90ea1213f9266d227dc7c772638f11fa6d426e5b/source272의 후속 ARM93/Nix2/native2는 발견 marker의 배포된 shebang wrapper를 실제 exec하여** 같은 파일chip/queue/parse14와 controller-loss를 재검증했다. private1GiB/peak283963392/전memoryevents0/fence1/정확한 scope·definition 부재 및 **47기록 불변**. 원본 `operating-844c978e4dbc/published-90ea121/ARM93-published-wrapper-native2-full-and-owned-cleanup.json`, raw result SHA **7bbc174673f1caebe996874ca0b8f308eb50951dd2fb165cc5814d9879c6d9e3**. 같은12 runtime bytes이며 실제 사용자 모델/normal2GiB 용량/launch 역할의 대화형 application gate까지 승인한 것은 아니다.
- 아래는 **root interactive cloud TTY에서 새 세션을 명시적으로 요청할 때만** 쓰는 선택형 경로다. 자동/default 사용자 전환을 하지 않았다. 세션 intent/keeper/output은 버전 디렉터리 `sessions/` 및 기존 shadow store에 남으며 UI 종료로 사라지지 않는다.

```sh
sudo /var/lib/spot-work-shadow-tui/844c978e4dbc/source/spot-work-shadow-tui launch --agent kiro_default
```

- `spot-work-shadow-tui.nix`도 추가했지만 **enable=false**다. 선언적 package에는 정확한 공개 vendorBun/vendorTui 입력이 필요하며 실제 reboot/new-root/AMI04c8/LT2 포함을 검증하지 않았다. 설치만으로 현재28d4 lock/unencrypted home/schema1 cache/backup IAM·journal/full guard/운영 LT1을 전환하지 않았다. 다음은 trusted delivery·consumer replacement/conflict·keeper/off-root recovery·Herdr/tool/MCP/subagent/SSM/Docker/direct custody다. **암호화 home/전체 복구/운영 restart→갱신 lock 재적용→재검증/5종 최저가/실제 zero→예약 재생성은 미완료**, `work_tracking_verified/armed/termination_capable/goal_complete=false` 및 원본 보호를 유지한다.

## 비용·백업 주의

- EIP는 연결 중에도, 미연결 보유 중에도 public IPv4 요금이 발생함.
- 스냅샷은 EBS 볼륨과 별도 과금되며 볼륨 삭제 시 자동 삭제되지 않음.
- 정상 운영용 홈 백업은 최종 운영 encrypted home ID에 맞는 cold snapshot·성공본 3개 보존·복원 및 최소 권한을 검증한 뒤 활성화. 보호 스냅샷/AMI 참조 스냅샷은 일반 정리 대상에서 제외.
- 안전장치가 종료를 보류하면 EC2 실행료는 계속됨. 별도 스케줄링 요금 0원과 전체 청구액 0원은 다른 개념.
