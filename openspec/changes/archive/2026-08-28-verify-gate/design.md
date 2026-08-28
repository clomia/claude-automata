# verify-gate — design

## Context

See proposal.md — Why. 제약: 에이전트 주입 텍스트는 irreducible(`.claude/rules/llm-prompt.md`) —
요구사항 추가가 텍스트 증가로 이어져서는 안 된다. verify spawn의 clean-context 계약
(`2026-08-16-tx-verify-convergence`)은 유지된다.

## Goals / Non-Goals

- Goal: 세 과호출 모드를 각각의 원인 문장에서 막되, 에이전트 주입 표면은 순감소.
- Non-goal: 소환 조건의 기계 강제. 재시도 상한(convergence에서 기각된 그대로).

## Decisions

1. **조건은 접속이 아니라 단일 절** — "delta ∧ behavior 변경" 대신 "a delta that moved
   observable behavior". delta 부재는 자동으로 전건 밖이라 조건 하나가 모드 1·3을 함께
   막는다. "observable"은 close의 prefix 표(refactor = behavior 불변)와 어휘를 맞춘다.
2. **apply는 자기 판정이 기본, verify가 예외** — "judge the implementation. The verify stage
   judges every delta that moved observable behavior". 명시적 dichotomy("yourself, unless…")
   는 더 길고 verify를 선행 priming한다. 둘 다 하는 독해(자기 판정 후 verify)는 무해하다.
3. **재소환 조건은 close 게이트의 명령형** — "until a pass is newer than the last behavior
   change". FAIL → 수정(behavior 불변이어도 pass가 없으므로 재소환), PASS → refactor(유지),
   PASS → behavior 변경(재소환) 세 경우 모두 정확하다. 기각: "if the repair moved behavior"
   — FAIL 뒤 consistency defect를 refactor로 고친 경우 pass 없이 apply를 끝낸다.
4. **파생 가능한 문장은 삭제** — close의 "Delta-less changes are gated by task completion
   and CI"는 archive 불릿(task)과 PR 불릿(CI)이 이미 모든 change의 게이트라 재언이었다.
   "by your reading"은 close 헤더의 무결 선언에서 파생된다. apply의 "here while the
   implementation context is live"는 rationale — 요구사항은 `here` 한 단어다.
5. **description 중복 채택** — 한 사실 한 집의 예외. `Agent(subagent_type="tx:verify")`를
   apply·close 밖에서 고르는 경로에는 agent description이 유일한 게이트다.
6. **spawner-side 계약은 lead-in에 흡수** — "Pass nothing but the change-id"(6단어)는 템플릿
   예시에서 파생되지 않는 금지라 삭제 불가; "on the change-id alone"(4단어)로 유지.

## Risks / Trade-offs

- [에이전트가 "behavior 움직임"을 넓게 읽어 여전히 과호출] → 어휘가 feat/fix vs refactor
  경계와 일치한다. 실측으로 재평가.
- [delta-less 예외의 부재를 verify 요구로 오독] → 전건이 정확해 무delta는 자명하게 제외.
  README가 사람 몫으로 dichotomy를 명시한다.
