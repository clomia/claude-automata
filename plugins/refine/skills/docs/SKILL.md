---
name: docs
description: "Heavyweight, hours-long (3-12h) documentation-to-code alignment — a large multi-agent workflow that verifies every claim in every non-executable text (markdown, spec systems, comments) against the code, cross-examines discrepancies into consensus, then applies only the highest-ROI fixes. Invoke only when a deep, deliberate docs pass is genuinely needed, not for touching up a single file."
argument-hint: "[focus area]"
effort: max
---

아래를 실행해, 출력된 `Workflow(...)` 호출을 그대로 실행하라.

```bash
uv run --project "${CLAUDE_PLUGIN_ROOT}" bootstrap docs "$ARGUMENTS"
```
