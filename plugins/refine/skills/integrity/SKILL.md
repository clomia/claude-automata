---
name: integrity
description: "Long-running (6-30h) multi-agent integrity-boundary optimization — hunts every reachable state the boundary (types, invariants, error definitions, tests) fails to contain, then absorbs only the highest-ROI set into it — code and docs both, pinned by tests. Not for fixing a known bug."
argument-hint: "[focus area]"
effort: max
---

> tx 플러그인이 활성이면 Workflow 실행 전 사용자에게 `/tx:git-sync-off`를, 끝난 뒤 `/tx:git-sync-on` 복원을 요청하라 — 둘 다 user-only command라 너는 실행할 수 없다. tx가 유도하는 mid-flight rebase는 장시간 workflow를 무효화한다.

아래를 실행해, 출력된 `Workflow(...)` 호출을 그대로 실행하라.

```bash
"${CLAUDE_PLUGIN_ROOT}/bin/refine-hook" bootstrap integrity "$ARGUMENTS"
```

중단 시: 산출물은 `agoraPath`에 남고 agent는 자기 기록에서 이어간다. `resumeFromRunId`는 끝난 agent의 결과를 cache에서 그대로 돌려준다. args가 바뀌면 둘 다 잃는다.
