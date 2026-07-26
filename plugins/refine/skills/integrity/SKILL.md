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

중단 시: 산출물은 `agoraPath`에 남고 agent는 자기 기록을 읽어 이어간다. `resumeFromRunId`(launch 결과)는 끝난 agent를 캐시에서 되살린다. 둘 다 args에 매여 있다.
