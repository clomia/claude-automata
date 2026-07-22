## MODIFIED Requirements

### Requirement: Deterministic plugin installation
`init`은 settings 선언에 더해 `claude` CLI로 plugin cache를 직접 수렴해야 한다(SHALL): `claude plugin marketplace add clomia/claude-automata`(idempotent) 후 `claude plugin marketplace update claude-automata`로 listing을 최신화하고, marketplace manifest의 각 plugin 중 target repo에 project scope로 미설치인 것을 `claude plugin install <name>@claude-automata --scope project`로 설치한다. 설치 여부 판별은 `claude plugin list --json`을 oracle로 해야 한다(MUST) — CLI 출력 산문을 파싱하지 않는다. `claude plugin update`는 사용해서는 안 된다(MUST NOT) — scope 자동 감지가 없고 실패에도 exit 0이다(실측). `claude` CLI는 실행 셸의 PATH뿐 아니라 표준 설치 위치(`~/.local/bin/claude`, `~/.claude/local/claude`)에서도 탐지해야 하며(SHALL) — `~/.local/bin`이 PATH에 없는 셸에서 실행돼도 설치된 claude를 놓쳐 false-deferral로 빠지지 않기 위함 —, 찾으면 그 경로로 claude 관리 명령을 실행해야 한다(MUST). 어디에서도 찾지 못할 때만 실패가 아니라 유예로 보고하고(SHALL), 유예 note는 결정론적 remedy(claude를 PATH에 올린 뒤 init 재실행, 또는 `claude plugin install <plugin>@claude-automata --scope project`)를 안내해야 한다(SHALL) — settings 선언은 install 레지스트리(`installed_plugins.json`)를 populate하지 않으므로(실측) 다음 session의 lazy 설치를 약속하지 않는다. 재실행은 idempotent해야 한다(MUST).

#### Scenario: 미설치 repo에서 결정론적 설치
- **WHEN** plugin이 없는 repo에서 claude CLI가 있는 상태로 init이 실행되면
- **THEN** marketplace가 등록·최신화되고 manifest의 전 plugin이 project scope로 cache에 설치되며, 설치된 목록이 보고된다

#### Scenario: 기설치 repo의 재실행
- **WHEN** 전 plugin이 이미 project scope로 설치된 repo에서 init이 재실행되면
- **THEN** 설치 시도 없이 satisfied로 보고된다

#### Scenario: PATH 밖 표준 위치의 claude로 설치
- **WHEN** `claude`가 실행 셸의 PATH에는 없지만 표준 설치 위치에 존재하는 환경에서 init이 실행되면
- **THEN** 유예되지 않고 그 경로의 claude로 marketplace·plugin이 수렴되며, 설치된 목록이 보고된다

#### Scenario: claude CLI 부재 시 유예
- **WHEN** `claude`가 PATH에도 표준 설치 위치에도 없는 환경에서 init이 실행되면
- **THEN** plugin 단계는 유예로 보고되고, claude를 PATH에 올린 뒤 init 재실행(또는 명시적 `claude plugin install --scope project`)을 안내하는 note가 출력된다

#### Scenario: 부분 실패는 계속 진행한다
- **WHEN** 일부 plugin의 install이 실패하면
- **THEN** 나머지 plugin 설치는 계속되고 실패 항목과 사유가 보고되며 init은 비정상 종료 code를 반환한다
