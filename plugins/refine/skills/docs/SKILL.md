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

`interrupted`가 반환되면 `args.agoraPath`를 반환된 경로로 바꿔 재실행하라 — 중단 지점부터 이어간다.
