## Why

seed 소유 표면에 결함 3건이 실측됐다 — 셋 다 이 repo 자체에서 재현되며, brownfield 도입 리포트
(dronesquare-backend, 위반 90건 중 frozen archive 71건)는 발화 사례일 뿐이다.

1. **동결 표면의 소급 재심판.** seed되는 `docs-form-check`는 전 추적 `.md`를 매 PR 전량
   스캔한다. `git check-ignore`는 *현재* `.gitignore`의 함수이므로, `.gitignore`에 항목이
   추가되는 순간 동결된 `openspec/changes/archive/**`가 소급 위반이 되어 모든 후속 PR을 영구
   차단한다 — 해소책이 동결 위반(이력 편집)뿐인 교착이다. 실측: 이 repo의
   `archive/2026-07-19-init-cli/design.md`가 `.claude/settings.local.json`을 참조하며, 그 표준
   위생 항목 한 줄 거리에 있다. brownfield 도입에서는 기 archive가 gate를 통과한 적이 없어
   즉시 발화한다.
2. **ruleset 부트스트랩 비대칭.** seed는 `tx-base-protection`을 즉시 active로 생성하며
   required check 2종을 요구하지만, 그 check를 만드는 workflow는 첫 tx가 merge되어야 base에
   닿는다. Actions-disabled는 처리하면서 workflow-not-on-base는 미처리라, 도입 시점에 열려
   있던 기존 PR 전부가 실행 불가능한 required check로 영구 `Expected`가 된다. present
   short-circuit은 ruleset을 영영 승격하지 않는다.
3. **workflow 갱신 트리거가 pin drift뿐.** `pin_drifted`는 openspec pin만 비교하므로 내용
   변경이 기 시드 repo에 전파되지 않는다. 실측: `71614d6`(english-form-tokens)이 workflow
   8줄을 바꾸면서 pin 1.6.0을 유지 — 구 plugin으로 시드된 repo는 구판에 머문다.

## What Changes

- **docs-form-check scan domain** — living 표면(archive 밖 전 추적 `.md`)은 현행 전량 스캔
  유지, `openspec/changes/archive/**`는 해당 PR diff로 유입(추가·수정)되는 파일만 검사.
  gate-at-entry 의미론: 장기기억으로 들어가는 모든 바이트는 동일 검사를 통과하고, 동결 후엔
  현재 규칙으로 재심판하지 않는다. diff 해석 실패는 loud fail이다.
- **seed workflow byte 수렴** — `pin_drifted`를 폐기하고 plugin reference와의 byte 비교로
  교체. seed-owned 계약("overwrites whole")의 구현 정확화.
- **ruleset shape 수렴** — required checks rule은 "Actions enabled ∧ workflow가
  `origin/<base>`에 존재"일 때만 포함. 아니면 나머지 rule(PR 강제·non-fast-forward·deletion)
  만으로 **active** 생성. 이후 seed 실행이 조건 충족을 보면 reduced → full로 상향 수렴.
  downgrade는 없다. 문서화된 기존 trade-off(Actions 재활성화 후 reduced 영구 잔존)도 이
  수렴으로 해소된다.
- **canon 이행** — MEMORY.md의 scan-domain 문장·경합 창 절, seed.py docstring,
  workflow header 주석, tx README seed 절.
- **이 repo 인스턴스 동기화** — `.github/workflows/memory-check.yml`을 새 reference와
  byte-identical로.
- **version bump** — tx 0.12.11 → 0.13.0 (seed behavior·배포물 변경).
- dronesquare 특수화는 없다 — 세 수정 모두 이 repo 단독으로 정당하다.

## Capabilities

### New Capabilities

- `tx-seed`: seed 소유 산출물(memory-check workflow · base ruleset)의 수렴 behavior.
  이번 delta가 도입하는 세 behavior만 담는다 — 기존 seed behavior의 소급 전사가 아니다
  (ARCHITECTURE 배제 기록).

### Modified Capabilities

없음.

## Impact

- `plugins/tx/references/memory-check.yml` · `.github/workflows/memory-check.yml` (byte pair)
- `plugins/tx/src/seed.py` · `plugins/tx/tests/test_seed.py` · 신규 form-check 테스트
- `MEMORY.md` · `plugins/tx/README.md`
- version pair: `plugins/tx/{.claude-plugin/plugin.json,pyproject.toml,uv.lock}`
- 외부 기 시드 repo: plugin 갱신 후 첫 seed가 byte 수렴으로 신판 workflow를 배포하고,
  reduced ruleset이 있으면 상향 수렴한다. 도입 중이던 repo(dronesquare)는 첫 tx부터
  frozen archive에 막히지 않는다 — living 위반은 여전히 그 repo 몫이다.
