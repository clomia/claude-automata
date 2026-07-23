---
name: integrity
description: "Hours-long (3-12h) multi-agent integrity-boundary optimization — hunts every reachable state the boundary (types, invariants, error definitions, tests) fails to contain, then absorbs only the highest-ROI set into it — code and docs both, pinned by tests. Not for fixing a known bug."
argument-hint: "[focus area]"
effort: max
---

아래를 실행해, 출력된 `Workflow(...)` 호출을 그대로 실행하라.

```bash
"${CLAUDE_PLUGIN_ROOT}/bin/refine-hook" bootstrap integrity "$ARGUMENTS"
```
