---
name: integrity
description: "Long-running (6-30h) multi-agent integrity-boundary optimization — hunts every reachable state the boundary (types, invariants, error definitions, tests) fails to contain, then absorbs only the highest-ROI set into it — code and docs both, pinned by tests. Not for fixing a known bug."
argument-hint: "[focus area]"
effort: max
---

아래를 실행해, 출력된 `Workflow(...)` 호출을 그대로 실행하라.

```bash
"${CLAUDE_PLUGIN_ROOT}/bin/refine-hook" bootstrap integrity "$ARGUMENTS"
```

`interrupted`면 **같은 args 그대로** `resumeFromRunId`(launch 결과에 있다)를 더해 재실행하라 — 끝난 agent는 캐시에서 돌아오고 Agora가 나머지를 잇는다. bootstrap을 다시 돌리면 Agora가 새로 파여 둘 다 잃는다.
