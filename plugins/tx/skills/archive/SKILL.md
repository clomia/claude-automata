---
name: archive
description: Archive the completed change — task gate, delta sync into main specs, revalidate
argument-hint: "[change-id]"
effort: high
---

delta가 main spec에 sync되고 change directory가 `openspec/changes/archive/`로 동결된다.

# 절차

1. 활성 change와 task 개수를 확인한다:

   ```bash
   "${CLAUDE_PLUGIN_ROOT}/bin/tx-hook" openspec list --json
   ```

   활성 change가 없으면 그렇다고 반환한다. **task가 없거나(no-tasks) 미완료면
   실패를 반환한다** — CLI는 막지 않으므로 이 gate는 여기서 강제된다. fix는 task
   부재면 `tx:plan`, 미완료면 `tx:apply` 소관이다.

2. archive한다. delta spec이 없는 change(tooling·infra·docs 변경)는 `--skip-specs`를 덧붙인다:

   ```bash
   "${CLAUDE_PLUGIN_ROOT}/bin/tx-hook" openspec archive <change-id> --yes
   ```

3. sync 결과를 재검증한다 — 실패는 archive가 만든 spec 상태의 결함이다. 고치고 재검증한다:

   ```bash
   "${CLAUDE_PLUGIN_ROOT}/bin/tx-hook" openspec validate --all --strict --no-interactive --json
   ```
