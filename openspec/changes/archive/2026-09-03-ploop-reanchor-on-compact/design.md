# ploop-reanchor-on-compact — design

## Context

See proposal.md — Why. 제약: round를 늘리지 않는다 — round(narrator·advisor)는 에이전트가 역할을
다하지 못하고 멈추는 것을 막는 대가이지 목표가 아니다. irreducible — 새 기계를 덧대지 않고
운반체를 교체한다.

## Goals / Non-Goals

- Goal: compaction 뒤 anchor 원문이 round와 무관하게 다음 turn 전에 recency에 있다.
- Non-goal: background 상시 점유 형상에서 round·advisor·flight recorder를 기계로 보장하는 것 —
  수용한 한계 그대로. deadline의 기계 강제 — 규율로 남는다(재정박된 anchor의 frontmatter가
  시계를 보여 준다).

## Decisions

1. **운반체는 `SessionStart` `compact` + `additionalContext`** — 공식 hook 계약이고, 이 repo의
   tx가 같은 경로로 branch-state-warn을 auto-compaction마다 싣는다(root ARCHITECTURE). 실측
   (2026-09, transcript): `compact_boundary` → 요약 → `SessionStart:compact` → `hook_additional_context`.
   `PostCompact`는 입력에 `compact_summary`를 주지만 additionalContext 출력 lane이 없다.
2. **교체이지 추가가 아니다** — marker·directive inline·`anchor_text`는 운반체가 바뀌면 존재 이유가
   없어 삭제한다. 기각: 두 경로 병존(fallback) — 같은 text가 두 시점에 들어가는 중복이고,
   SessionStart가 침묵하면 skill re-inject가 이미 남는다.
3. **candidates 주소 동승** — 결정 21의 "compaction 이후 재공급" 역할이 directive에서 재정박으로
   옮겨 온다. 재정박이 없던 형상에서 주소는 요약의 보존 여부에 걸려 있었다. 기존
   `format_candidates_notice` 한 줄을 재사용한다.
4. **기각: round cadence floor** — "round가 3h 열려 있으면 background가 점유돼도 arm"은 재주입을
   회복하지만 round를 강제로 만든다. round는 최소가 이상이다.
5. **기각: heartbeat 변경** — heartbeat는 침묵(3h 무정지)의 상한이고, 이 형상은 정지가 잦아
   침묵이 아니다. gated stop에서 재무장을 건너뛰면 fire 뒤 heartbeat가 죽는다.
6. **`deliver_context(hook_event, text)`** — launch의 `UserPromptExpansion` 배달과 같은 JSON 형태라
   helper를 일반화한다.

## Risks / Trade-offs

- [`SessionStart` `compact`가 조용히 fire하지 않는 harness 변화] → skill re-inject 한 겹으로 퇴행,
  종전 형태의 gate-잠든 loop와 같은 수준 — 새 피해 없음. tx의 같은 의존이 함께 표류하므로
  감지된다.
- [compaction마다 anchor 전문 + 주소 1행 주입] → 종전과 같은 양이 더 이른 시점에 들어갈 뿐이다.
