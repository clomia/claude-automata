---
name: apply
description: Implement the planned change task by task, then spawn the independent verify stage until it passes
argument-hint: "[change-id]"
effort: max
---

# 절차

1. 게이트를 판정한다: `applyRequires`에 열거된 아티팩트가 전부 `done`이어야 한다.
   (`isComplete`는 게이트가 아니다 — design은 포함 조건에 해당할 때만 존재한다.)
   아니면 구현이 아니라 계획이 부족한 것 — `tx:plan`으로 돌아간다.
   **게이트 통과 전에는 apply 지시를 소비하지 않는다.**

   ```bash
   uv run --project "${CLAUDE_PLUGIN_ROOT}" openspec status --change <change-id> --json
   ```

2. 컨텍스트 파일 경로와 태스크 체크리스트를 받는다:

   ```bash
   uv run --project "${CLAUDE_PLUGIN_ROOT}" openspec instructions apply --change <change-id> --json
   ```

3. 태스크를 의존 순서대로 구현하고, 완료할 때마다 tasks.md의 체크박스를 `- [x]`로 갱신한다.
   spec 문면이 구현을 구속한다 — 구현 중 spec이 틀렸음이 드러나면 `tx:plan`으로 delta를
   고친 뒤 계속한다.

4. 모든 태스크가 완료되면 **verify 스테이지를 spawn한다** (필수):

   ```
   Agent(subagent_type="tx:verify", run_in_background=false, prompt="change-id: <change-id>")
   ```

   change-id 외에는 아무것도 전달하지 않는다 — 검증자는 아티팩트와 코드를 직접 읽는다.
   결함이 보고되면 구현 컨텍스트가 살아있는 지금 이 자리에서 수리하고 재spawn한다 —
   pass까지.

# 미지의 번역

구현 중 만나는 모든 미지는 셋 중 하나로 번역한다:

- **측정 가능하면** — 측정하고 결과를 기록한다.
- **가역적이면** — 가정을 채택하고 design에 명기한다.
- **둘 다 아니면** — 해당 태스크를 중단하고 사유를 tasks.md에 기록한다.
