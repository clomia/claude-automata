---
name: code
description: "Long-running (6-30h) multi-agent code-architecture optimization — cross-examines antipatterns into consensus, then applies only the highest-ROI refactors. Not for routine refactors."
argument-hint: "[focus area]"
effort: max
---

아래를 실행해, 출력된 `Workflow(...)` 호출을 그대로 실행하라.

```bash
"${CLAUDE_PLUGIN_ROOT}/bin/refine-hook" bootstrap code "$ARGUMENTS"
```

`interrupted`면 **같은 args 그대로** `resumeFromRunId`(launch 결과에 있다)를 더해 재실행하라 — 끝난 agent는 캐시에서 돌아오고 Agora가 나머지를 잇는다. bootstrap을 다시 돌리면 Agora가 새로 파여 둘 다 잃는다.
