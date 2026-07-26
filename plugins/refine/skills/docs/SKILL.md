---
name: docs
description: "Long-running (6-30h) multi-agent documentation-architecture optimization — verifies every claim in every non-executable text (markdown, spec systems, comments) against the code, cross-examines discrepancies into consensus, then applies only the highest-ROI fixes. Code is never modified — defects are reported, not fixed. Not for touching up a single file."
argument-hint: "[focus area]"
effort: max
---

아래를 실행해, 출력된 `Workflow(...)` 호출을 그대로 실행하라.

```bash
"${CLAUDE_PLUGIN_ROOT}/bin/refine-hook" bootstrap docs "$ARGUMENTS"
```

`interrupted`면 **같은 args 그대로** `resumeFromRunId`(launch 결과에 있다)를 더해 재실행하라 — 끝난 agent는 캐시에서 돌아오고 Agora가 나머지를 잇는다. bootstrap을 다시 돌리면 Agora가 새로 파여 둘 다 잃는다.
