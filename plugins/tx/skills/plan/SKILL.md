---
name: plan
description: Plan the change as OpenSpec artifacts — proposal, delta specs, design, tasks
argument-hint: "[change intent]"
effort: max
---

변경의 intent·design을 change artifact로 기록한다. squash merge는 branch history를 지운다 —
이 artifact의 archive만이 그 과정을 보존한다.

# 절차

1. change-id를 정한다 — 보통 tx branch의 slug와 같다.

   ```bash
   uv run --project "${CLAUDE_PLUGIN_ROOT}" openspec new change <change-id>
   ```

2. artifact를 dependency 순서로 작성한다. artifact마다
   instructions·format·template을 engine에서 받는다 — format의 정본은 engine이다:

   ```bash
   uv run --project "${CLAUDE_PLUGIN_ROOT}" openspec instructions <artifact> --change <change-id> --json
   ```

   task에는 close 전에 done이 되는 작업만 적는다 — transaction의 종결(close·archive·merge)과
   merge 이후의 행동(deploy·production 검증)은 task가 될 수 없다. 후자는 후속 change다.

3. validate한다:

   ```bash
   uv run --project "${CLAUDE_PLUGIN_ROOT}" openspec validate <change-id> --strict --no-interactive --json
   ```

   delta 없는 change(tooling·infra·docs 변경)에서는 validate가 class 전체로 `no deltas`
   ERROR를 낸다 — 이 ERROR는 fix 대상이 아니고, 그 class의 gate는 task 완료와
   archive의 `--skip-specs`, 사후 CI다. 그 외의 지적은 전부 green까지 수정한다.

4. 즉시 `tx:apply`로 이어간다 — plan은 구현의 시작이지 정지점이 아니다.

# Unknown 처리

계획 중 만나는 모든 unknown은 셋 중 하나로 처리한다:

- **measurable하면** — 측정하고 결과를 기록한다.
- **reversible하면** — assumption을 채택하고 design에 명시한다.
- **둘 다 아니면** — 변경을 중단·연기하고 사유를 proposal에 기록한다.
