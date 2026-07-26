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

중단 시: 산출물은 `agoraPath`에 남고 agent는 자기 기록을 읽어 이어간다. `resumeFromRunId`(launch 결과)는 끝난 agent를 캐시에서 되살린다. 둘 다 args에 매여 있다.
