---
name: code
description: "Heavyweight, hours-long (3-12h) code-architecture optimization — a large multi-agent workflow that cross-examines antipatterns and defects into consensus, then applies the highest-ROI refactors and repairs every confirmed defect. The target state, the code-architecture optimum, presupposes that all code behaves correctly: defects surfaced en route are fixed, and docs invalidated by the changes are realigned. Invoke only when a deep, deliberate architecture pass is genuinely needed, not for routine refactors."
argument-hint: "[focus area]"
effort: max
---

아래를 실행해, 출력된 `Workflow(...)` 호출을 그대로 실행하라.

```bash
uv run --project "${CLAUDE_PLUGIN_ROOT}" bootstrap code "$ARGUMENTS"
```
