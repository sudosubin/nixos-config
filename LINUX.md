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
- There is deliberately NO paid activate action yet. Autonomous original-host run discovery/body receipt and preactivation admission/replacement test containment must be implemented/proven first. Pure bootstrap25+builder17+pipeline26 are scoped operator tests, NOT actual new-root boot/full618/replacement/production0-wake proof. Full goal and all remaining production gates above stay active.

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

## 비용·백업 주의

- EIP는 연결 중에도, 미연결 보유 중에도 public IPv4 요금이 발생함.
- 스냅샷은 EBS 볼륨과 별도 과금되며 볼륨 삭제 시 자동 삭제되지 않음.
- 정상 운영용 홈 백업은 최종 운영 encrypted home ID에 맞는 cold snapshot·성공본 3개 보존·복원 및 최소 권한을 검증한 뒤 활성화. 보호 스냅샷/AMI 참조 스냅샷은 일반 정리 대상에서 제외.
- 안전장치가 종료를 보류하면 EC2 실행료는 계속됨. 별도 스케줄링 요금 0원과 전체 청구액 0원은 다른 개념.
