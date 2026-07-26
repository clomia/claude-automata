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

`interrupted`가 반환되면 `args.agoraPath`를 반환된 경로로 바꿔 재실행하라 — 중단 지점부터 이어간다.
