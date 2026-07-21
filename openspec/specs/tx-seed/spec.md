# tx-seed Specification

## Purpose
TBD - created by archiving change seed-convergence. Update Purpose after archive.
## Requirements
### Requirement: Frozen-surface scan domain
seed되는 `docs-form-check`는 `openspec/changes/archive/` 밖의 전 추적 `.md`를 전량
검사해야 하며(SHALL), `openspec/changes/archive/` 아래의 추적 `.md`는 해당 pull request
diff가 추가·수정하는 파일만 검사해야 한다(SHALL). PR diff를 해석할 수 없으면 동결 표면을
건너뛰는 대신 check가 실패해야 한다(MUST).

#### Scenario: 동결된 기존 위반은 무관한 PR을 막지 않는다
- **WHEN** archive의 추적 `.md`가 현재 gitignored인 경로를 참조하고 PR이 그 파일을 건드리지 않으면
- **THEN** docs-form-check는 통과한다

#### Scenario: archive로 유입되는 내용은 검사된다
- **WHEN** PR이 gitignored 또는 system temp 경로를 참조하는 `.md`를 archive 아래로 추가(이동 포함)하면
- **THEN** docs-form-check는 실패한다

#### Scenario: living 표면은 diff와 무관하게 전량 검사된다
- **WHEN** archive 밖의 추적 `.md`가 gitignored 경로를 참조하면
- **THEN** PR이 그 파일을 건드리지 않아도 docs-form-check는 실패한다

#### Scenario: diff 해석 실패는 loud fail
- **WHEN** PR diff의 기준 commit을 해석할 수 없으면
- **THEN** check는 사유를 출력하고 실패한다 (동결 표면 무검사 통과 금지)

### Requirement: Seed-owned workflow convergence
seed는 배포된 memory-check workflow가 plugin의 reference 사본과 byte 단위로 다르면 전체를
덮어써야 하며(SHALL), 동일하면 건드리지 않아야 한다(MUST).

#### Scenario: pin이 같아도 내용 drift는 재배포된다
- **WHEN** 배포본이 reference와 다르고 openspec pin은 동일한 상태에서 seed가 실행되면
- **THEN** 배포본은 reference 전체로 덮어써지고 refresh가 보고된다

#### Scenario: 동일 byte는 무변경
- **WHEN** 배포본이 reference와 byte-identical하면
- **THEN** seed는 파일을 건드리지 않고 present를 보고한다

### Requirement: Ruleset shape convergence
seed는 `tx-base-protection` ruleset의 required-status-checks rule을 "GitHub Actions가
enabled이고 memory-check workflow가 `origin/<base>`에 존재"할 때만 포함해야 하며(SHALL),
조건 미충족 시 나머지 rule만으로 ruleset을 active로 생성해야 한다(SHALL). checks rule이
없는 ruleset이 존재하고 두 조건이 충족되면 seed는 canonical full 형상으로 상향 수렴해야
한다(SHALL). 존재하는 checks rule을 제거해서는 안 되며(MUST NOT), probe 실패는 full 형상으로
fall through해야 한다(MUST).

#### Scenario: 최초 도입 — workflow가 base에 없다
- **WHEN** `origin/<base>`에 memory-check workflow가 없는 repo에서 seed가 ruleset을 생성하면
- **THEN** required-status-checks rule이 빠진 ruleset이 active로 생성되고 유예가 보고된다

#### Scenario: 후속 seed가 상향 수렴한다
- **WHEN** checks rule 없는 ruleset이 존재하고 Actions enabled·workflow-on-base가 충족된
  상태에서 seed가 실행되면
- **THEN** ruleset은 canonical full 형상으로 갱신되고 upgrade가 보고된다

#### Scenario: downgrade는 없다
- **WHEN** full ruleset이 존재하고 조건이 퇴행(Actions disabled 등)한 상태에서 seed가 실행되면
- **THEN** ruleset은 변경되지 않는다

#### Scenario: probe 실패는 full로
- **WHEN** ruleset 생성 시 Actions probe 또는 base 해석이 실패하면
- **THEN** full 형상이 시도된다 (새 failure mode 추가 금지)

### Requirement: Plan-gate terminal state
seed는 rulesets API 거부 사유가 plan-gate(GitHub 응답에 "Upgrade to GitHub Pro" 포함)이면
`branch protection: unsupported (private repo on a free plan)`를 보고해야 하며(SHALL),
이를 실패로 취급하거나 진행을 차단해서는 안 된다(MUST NOT). unsupported는 terminal
satisfied state다 — 후속 seed는 동일하게 재시도하므로 visibility·plan 변경 시 별도 상태
없이 기존 수렴 의미론으로 상향된다(SHALL). plan-gate로 판별되지 않는 실패는 기존대로
`branch protection: unavailable (<사유>)`로 보고해야 한다(SHALL).

#### Scenario: free-plan private repo는 unsupported로 안착한다
- **WHEN** rulesets API 호출이 "Upgrade to GitHub Pro or make this repository public (HTTP 403)"로 거부되면
- **THEN** seed는 `branch protection: unsupported (private repo on a free plan)`를 보고하고 정상 종료한다

#### Scenario: 판별 불가 실패는 unavailable로 남는다
- **WHEN** rulesets API 호출이 plan-gate 외 사유(token 권한 등)로 실패하면
- **THEN** seed는 `branch protection: unavailable (<사유>)`를 보고하고 정상 종료한다

#### Scenario: 조건 해소 시 상향 수렴한다
- **WHEN** unsupported로 안착한 repo가 public이 되거나 유료 plan으로 전환된 뒤 seed가 실행되면
- **THEN** ruleset 생성·상향이 기존 수렴 의미론대로 진행된다

