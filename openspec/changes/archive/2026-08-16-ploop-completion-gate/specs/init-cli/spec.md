# init-cli — delta

The provisioned value and behavior are unchanged; the requirement's rationale is
re-grounded. The nested-subagent default has drifted 5 (2.1.172) → 1 (2.1.217) → 3
(2.1.219), and the completion-gate redesign closes the loop machinery at depth 1
(the advisor spawns no one) — the pin is an orchestration-environment contract, not
an advisor-path repair.

## MODIFIED Requirements

### Requirement: Settings prerequisites

`init`은 target repo의 `.claude/settings.json`에 다음 전제조건을 merge-write해야 한다(SHALL): `alwaysThinkingEnabled=true`, `autoMemoryEnabled=false`, `autoCompactEnabled=true`, `model="opus[1m]"`, `permissions.defaultMode="bypassPermissions"`, `env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH="5"`. `env` 전제조건은 mission worker들의 위임 tree 깊이를 harness default 표류(5→1→3, release마다 변동)로부터 pin하는 orchestration 환경 계약이다 — ploop loop 기계 자체는 depth 1에서 닫히며, 값 `5`는 nesting 도입 시(2.1.172) 공식 cap이다. 기존 파일의 다른 key와 `permissions`·`env`의 다른 하위 key는 보존해야 한다(MUST). 재실행은 idempotent해야 한다(MUST).

#### Scenario: settings 파일 부재
- **WHEN** `.claude/settings.json`이 없는 repo에서 init을 실행하면
- **THEN** 전제조건 key 전부(`env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` 포함)를 담은 파일이 생성된다

#### Scenario: 기존 settings 보존
- **WHEN** 무관한 key(`statusLine` 등)·`permissions.allow`·기존 `env` 항목을 가진 settings가 이미 있으면
- **THEN** 무관한 key·`permissions.allow`·기존 `env` 항목은 그대로 남고 전제조건 key(신규 `env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` 포함)만 설정된다

#### Scenario: nested-subagent depth 확보
- **WHEN** init이 완료되면
- **THEN** settings의 `env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`가 `"5"`로 설정되어 mission worker들의 위임 tree 깊이가 harness default 표류와 무관하게 고정된다

#### Scenario: 재실행 수렴
- **WHEN** init을 두 번 실행하면
- **THEN** 두 번째 실행 후 파일 내용이 첫 실행 결과와 동일하다
