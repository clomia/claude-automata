## ADDED Requirements

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
