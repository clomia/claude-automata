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

중단 시: 산출물은 `agoraPath`에 남고 agent는 자기 기록에서 이어간다. `resumeFromRunId`는 끝난 agent의 결과를 cache에서 그대로 돌려준다. args가 바뀌면 둘 다 잃는다.
