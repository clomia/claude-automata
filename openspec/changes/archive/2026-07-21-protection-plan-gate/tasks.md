## 1. Seed 분류기

- [x] 1.1 `seed.py` — plan-gate marker 판별을 담은 실패 보고 함수를 추가하고 `protection_report`의 전 실패 지점이 이를 경유하게 한다; docstring의 protection 절에 terminal state를 반영한다
- [x] 1.2 `test_seed.py` — plan-gate 403은 `unsupported`, 그 외 실패는 `unavailable`로 보고되는 테스트를 추가한다

## 2. 문서 정합화

- [x] 2.1 `INSTALL.md` — installed state의 protection 요구를 rulesets 제공 조건부로 한정하고, plan-gate에서는 `unsupported`가 converged state임을 명시한다
- [x] 2.2 `plugins/tx/README.md` — seed 절의 best-effort 서술에 plan-gate terminal skip 1문장을 추가한다

## 3. Release

- [x] 3.1 tx version 0.13.0 → 0.13.1 — `plugin.json`·`pyproject.toml`·lock 일관 갱신
