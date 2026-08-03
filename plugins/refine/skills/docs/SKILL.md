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

무인 장기 실행이다: agent들이 쓰는 shell 명령(repomix 포함)이 allowlist 밖이면 mid-run permission prompt에서 멎는다. 실행 전에 사용자에게 등록을 권하라.

재개 시: bootstrap을 다시 돌리지 마라. 호출마다 새 agora가 생겨 기록과 cache를 둘 다 잃는다. 이전 `Workflow(...)` 호출을 같은 args로 재발행하라(같은 세션이면 `resumeFromRunId`를 더해 cache를 재생한다). 산출물은 `agoraPath`에 남아 agent가 자기 기록에서 이어간다.
