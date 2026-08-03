---
name: apply
description: Implement the planned change task by task, then spawn the independent verify stage until it passes
argument-hint: "[change-id]"
effort: max
---

# 절차

1. gate를 판정한다: `applyRequires`에 열거된 artifact가 전부 `done`이어야 한다.
   (`isComplete`는 gate가 아니다. design은 포함 조건에 해당할 때만 존재한다.)
   아니면 부족한 것은 구현이 아니라 계획이다: `tx:plan`으로 돌아간다.

   ```bash
   "${CLAUDE_PLUGIN_ROOT}/bin/tx-hook" openspec status --change <change-id> --json
   ```

2. context 파일 경로와 task checklist를 받는다:

   ```bash
   "${CLAUDE_PLUGIN_ROOT}/bin/tx-hook" openspec instructions apply --change <change-id> --json
   ```

3. task를 dependency 순서대로 구현한다.
   spec wording이 구현을 구속한다. 구현 중 spec이 틀렸음이 드러나면 `tx:plan`으로 delta를
   고친 뒤 계속한다.

4. 모든 task가 완료되고 change에 spec delta가 있으면 **verify stage를 spawn한다** (필수):

   ```
   Agent(subagent_type="tx:verify", prompt="change-id: <change-id>")
   ```

   change-id 외에는 아무것도 전달하지 않는다. verifier는 artifact와 코드를 직접 읽는다.
   결함이 보고되면 구현 context가 살아있는 지금 이 자리에서 고치고, pass까지 재spawn한다.

# Unknown 처리

구현 중 만나는 모든 unknown은 셋 중 하나로 처리한다:

- **measurable하면**: 측정하고 결과를 기록한다.
- **reversible하면**: assumption을 채택하고 design에 명시한다.
- **둘 다 아니면**: 해당 task를 중단하고 사유를 tasks.md에 기록한다.
