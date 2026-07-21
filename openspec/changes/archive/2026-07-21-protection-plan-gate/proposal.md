# Proposal — protection-plan-gate

## Why

설치 시나리오 실측(free-plan 개인 private repo)에서 seed의 rulesets API 호출이
`gh: Upgrade to GitHub Pro or make this repository public (HTTP 403)`로 거부됐다.
GitHub는 private repo의 rulesets를 유료 plan에서만 제공하므로 이 조건은 plan·visibility가
바뀌지 않는 한 영구적인데, seed는 이를 `branch protection: unavailable (…)` — 후속 실행이
수렴시킬 일시 장애 — 로 보고한다. INSTALL.md의 installed state는 "a later `/tx:open` has
reported the branch protection upgraded"와 "Steady state: every seed line reads `present`"를
무조건 요구하므로, 설치 agent가 도달 불가능한 상태를 좇는다 — 설치를 실패로 판정하거나
repo를 public으로 만들라는 압박으로 발화하는 치명 결함이다. server-side protection은
설계상 이미 best-effort다(MEMORY.md: 실패는 1행 고지 후 진행, close gate는 server 설정
없이 성립) — 보고 어휘와 INSTALL.md만 그 canon과 어긋난다.

## What Changes

- **seed 보고 어휘에 terminal state 추가** — rulesets API 거부 사유가 plan-gate
  (GitHub 응답 "Upgrade to GitHub Pro")이면 `branch protection: unsupported
  (private repo on a free plan)`로 보고한다. `unavailable`(일시 장애, 후속 수렴 대상)과
  구분되는 satisfied state다. 판별 불가한 나머지 실패는 기존대로 `unavailable`.
  후속 seed는 계속 재시도하므로 repo가 public이 되거나 plan이 오르면 기존 수렴
  의미론 그대로 자동 상향된다.
- **INSTALL.md installed state 조건부화** — protection의 upgraded/`present` 요구를
  "GitHub가 이 repo에 rulesets를 제공하는 경우"로 한정하고, plan-gate에서는
  `unsupported`가 그 라인의 converged state임을 명시한다.
- **tx README seed 절 동기화** — best-effort 서술에 terminal skip 어휘 1문장 추가.
- **version bump** — tx 0.13.0 → 0.13.1 (보고 behavior 수정).

## Capabilities

### New Capabilities

없음.

### Modified Capabilities

- `tx-seed`: Ruleset shape convergence — plan-gate 거부를 terminal satisfied state로
  보고하는 requirement 추가 (실패 아님, 차단 없음, 조건 해소 시 상향 수렴 유지).

## Impact

- `plugins/tx/src/seed.py` · `plugins/tx/tests/test_seed.py`
- `INSTALL.md` · `plugins/tx/README.md`
- version pair: `plugins/tx/{.claude-plugin/plugin.json,pyproject.toml}`
- 외부 기 시드 repo: plugin 갱신 후 첫 seed부터 free-plan private repo가
  `unsupported`로 안착한다 — 설치 흐름이 protection 부재를 결함으로 오판하지 않는다.
