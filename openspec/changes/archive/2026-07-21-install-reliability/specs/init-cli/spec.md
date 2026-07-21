## MODIFIED Requirements

### Requirement: Zero-install entrypoint
repo root는 Python package `claude-automata`여야 하며, `claude-automata` 실행 파일과 `init` command를 노출해야 한다(SHALL). package는 PyPI에 `claude-automata`로 발행되어야 하며(SHALL), uv만 설치된 machine에서 `uvx claude-automata@latest init`으로 사전 설치 없이 실행되어야 한다(SHALL). 안내되는 실행형은 `@latest`를 포함해야 한다(MUST) — 무지정 `uvx claude-automata`는 캐시된 tool 환경을 재해석 없이 재사용하므로 stale version이 실행될 수 있다. `init`은 첫 줄에 자기 package version을 보고해야 한다(SHALL) — stale 환경의 실행을 산출물에서 판별 가능하게 한다. git source 실행(`uvx --from git+https://github.com/clomia/claude-automata claude-automata init`)도 유효해야 한다(MUST).

#### Scenario: uvx 단축형 실행
- **WHEN** uv만 설치된 machine에서 `uvx claude-automata@latest init`을 실행하면
- **THEN** 캐시 환경 존재 여부와 무관하게 PyPI의 최신 발행 version이 resolve되고 `init` command가 실행된다

#### Scenario: version 자기 보고
- **WHEN** init이 실행되면
- **THEN** 출력 첫 줄에 실행 중인 package version이 나타난다

#### Scenario: uvx로 실행
- **WHEN** `uvx --from git+<repo-url> claude-automata init`을 실행하면
- **THEN** package가 격리 환경에 resolve되고 `init` command가 실행된다

## ADDED Requirements

### Requirement: Deterministic plugin installation
`init`은 settings 선언에 더해 `claude` CLI로 plugin cache를 직접 수렴해야 한다(SHALL): `claude plugin marketplace add clomia/claude-automata`(idempotent) 후 `claude plugin marketplace update claude-automata`로 listing을 최신화하고, marketplace manifest의 각 plugin 중 target repo에 project scope로 미설치인 것을 `claude plugin install <name>@claude-automata --scope project`로 설치한다. 설치 여부 판별은 `claude plugin list --json`을 oracle로 해야 한다(MUST) — CLI 출력 산문을 파싱하지 않는다. `claude plugin update`는 사용해서는 안 된다(MUST NOT) — scope 자동 감지가 없고 실패에도 exit 0이다(실측). `claude` CLI가 PATH에 없으면 실패가 아니라 유예로 보고해야 하며(SHALL), settings 선언에 의한 다음 session 시작의 lazy 설치와 skills 부재 시 `/reload-plugins` 1회 복구를 note로 안내해야 한다(SHALL). 재실행은 idempotent해야 한다(MUST).

#### Scenario: 미설치 repo에서 결정론적 설치
- **WHEN** plugin이 없는 repo에서 claude CLI가 있는 상태로 init이 실행되면
- **THEN** marketplace가 등록·최신화되고 manifest의 전 plugin이 project scope로 cache에 설치되며, 설치된 목록이 보고된다

#### Scenario: 기설치 repo의 재실행
- **WHEN** 전 plugin이 이미 project scope로 설치된 repo에서 init이 재실행되면
- **THEN** 설치 시도 없이 satisfied로 보고된다

#### Scenario: claude CLI 부재 시 유예
- **WHEN** `claude`가 PATH에 없는 환경에서 init이 실행되면
- **THEN** plugin 단계는 유예로 보고되고, restart에 의한 lazy 설치와 skills 부재 시 `/reload-plugins` 복구 안내 note가 출력된다

#### Scenario: 부분 실패는 계속 진행한다
- **WHEN** 일부 plugin의 install이 실패하면
- **THEN** 나머지 plugin 설치는 계속되고 실패 항목과 사유가 보고되며 init은 비정상 종료 code를 반환한다
