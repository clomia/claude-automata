---
name: integrity
description: "Heavyweight, hours-long (3-12h) logical-integrity hardening — a large multi-agent workflow that hunts every state where code can fail, interrogates each from 'should this be defined as an error?', cross-examines hazards into consensus, then applies only the highest-ROI hardening pinned by tests. Invoke only when a deep, deliberate integrity pass is genuinely needed, not for fixing a known bug."
argument-hint: "[focus area]"
effort: max
---

아래를 실행해, 출력된 `Workflow(...)` 호출을 그대로 실행하라.

```bash
uv run --project "${CLAUDE_PLUGIN_ROOT}" bootstrap integrity "$ARGUMENTS"
```
