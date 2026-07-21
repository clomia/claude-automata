## MODIFIED Requirements

### Requirement: Agent install canon — INSTALL.md
repo root의 `INSTALL.md`는 설치를 수행할 agent 대상의 English 단일본이어야 하며(SHALL),
방법 절차가 아니라 **installed state** — 전부 참이면 설치된 것인 검증 가능한 술어 집합 —
를 서술해야 한다(SHALL). 상태 oracle(init 출력·seed 보고·openspec validate·CI)을 지정해야
하고(MUST), host repository의 기존 harness를 존중하는 경계 — 동결 이력 불가침, 소급 재구성
금지, repo 소유 결정의 사용자 귀속 — 를 installed state의 술어로 포함해야 한다(MUST).
init이 기록하는 settings 전제조건(`permissions.defaultMode="bypassPermissions"`·
`model="opus[1m]"`·flag 3종·marketplace 등록)을 installed state의 일부로 공개해야 하며(SHALL —
방문자 표면이 아니라 여기가 공개의 home이다), 그 값은 `claude_automata/settings.py`의 실값과
CI로 결속되어야 한다(MUST). init이 기록하는 settings가 세션 재시작으로만 발효하고 plugin이
세션 시작 시 로드되므로, installed state는 **init 이후의 세션 재시작을 별도 술어로 요구해야
하며(SHALL)** — 재시작 전에는 tx skill이 없어 transaction 술어가 성립 불가다 — 설치 agent가
자기 세션을 재시작할 수 없다는 사실과 그 재시작을 사용자에게 표면화해야 한다는 것을
술어에 담아야 한다(MUST). 명령 시퀀스·단계 절차를 강제해서는 안 되며(MUST NOT — 경로는
대상 repo의 agent가 도출한다), 내부 개발 정본(ARCHITECTURE.md·MEMORY.md)을 참조해서는 안
된다(MUST NOT).

#### Scenario: 성공 상태 서술
- **WHEN** agent가 INSTALL.md만 읽고 임의의 기 구축 repository에서 설치를 수행하면
- **THEN** 도달할 상태와 각 술어의 검증 oracle이 전부 주어지고, 경로·순서는 문서가
  강제하지 않는다

#### Scenario: host harness 존중
- **WHEN** 대상 repository에 자체 CLAUDE.md·rules·CI·문서 체계가 있으면
- **THEN** installed state의 술어가 그 보존을 요구하고, 충돌 시 사용자 결정 귀속을 요구한다

#### Scenario: settings 공개의 home
- **WHEN** 신중한 사용자가 위임 prompt를 건네기 전에 INSTALL.md를 읽으면
- **THEN** init이 기록하는 settings(bypassPermissions·model 고정 포함)가 명시되어 있고,
  그 값은 settings.py와 CI로 결박되어 표류하지 않는다

#### Scenario: 재시작 관문
- **WHEN** 설치 agent가 init을 실행한 세션에서 곧바로 다음 단계로 나아가려 하면
- **THEN** installed state가 init 이후의 세션 재시작을 요구하고(재시작 전에는 plugin·tx
  skill이 없다), agent는 스스로 재시작할 수 없으므로 그 재시작을 사용자에게 표면화한다
