# ploop-reanchor-on-compact

## Why

anchor 정박의 mechanism 2(compaction 후 anchor 원문 재주입)가 round에 묶여 있었다 — `PostCompact`가
marker를 찍고 **다음 armed Stop**의 directive가 그것을 소비해 inline했다. round는 background가 빈
정지에만 arm되는데(결정 16), launch rule을 따르는 orchestrator는 정지마다 background를 걸어 두므로
armed Stop이 무기한 오지 않을 수 있다. 실측(2026-09, 11h·42 stop의 loop session)에서 background가 빈
정지는 0회였다 — 그 형상에서 compaction 뒤 anchor는 skill re-inject(5,000token cap) 한 겹에만
남는다. 재주입을 round에서 떼어내야 한다. round는 비용이므로 round를 더 만드는 방향은 기각한다.

## What Changes

- mechanism 2의 운반체가 `PostCompact` marker + directive inline에서 **`SessionStart` hook(matcher
  `compact`)의 `additionalContext`**로 바뀐다. compaction 직후, 요약 바로 뒤에 anchor 원문이
  놓인다 — round와 무관하다. candidates 주소(launch의 또 하나의 배달)가 동승한다.
- `_compacted` marker, `mark_compaction` entry, `arm_round`의 marker 소비, `format_directive`의
  `anchor_text` 분기가 삭제된다.
- heartbeat·background gate·directive는 변경 없음.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none — anchor 정박에는 spec'd capability가 없다; `skip_specs`)

## Impact

- `plugins/ploop/hooks/hooks.json`: `PostCompact` → `SessionStart` (`compact`).
- `plugins/ploop/src/main.py`: `mark_compaction` → `reanchor`; `deliver_expansion_context` →
  `deliver_context(hook_event, text)`; `arm_round`의 marker 소비 삭제.
- `plugins/ploop/src/prompt.py`: `format_anchor_notice` 추가, `format_directive(anchor_text)` 삭제.
- `plugins/ploop/src/state.py`: `compacted_path` 삭제.
- `plugins/ploop/ARCHITECTURE.md`: anchor 정박 3겹·결정 1·6·21·hook/file table·file map.
- Version 0.55.1 → 0.56.0.
