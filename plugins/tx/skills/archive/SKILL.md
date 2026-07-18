---
name: archive
description: Archive the completed change — task gate, delta sync into main specs, revalidate
argument-hint: "[change-id]"
effort: high
---

완료된 change를 아카이브한다 — delta가 main spec에 sync되고 change 디렉토리가
`openspec/changes/archive/`로 동결된다.

# 절차

1. 활성 change와 태스크 계수를 확인한다:

   ```bash
   uv run --project "${CLAUDE_PLUGIN_ROOT}" openspec list --json
   ```

   활성 change가 없으면 그렇다고 반환한다. **미완료 태스크가 있으면 실패를 반환한다** —
   CLI는 경고만 하고 진행하므로 이 게이트는 여기서 강제된다. 수리는 `tx:apply` 소관이다.

2. 아카이브한다. delta spec이 없는 change(도구·인프라·문서 변경)는 `--skip-specs`를 덧붙인다:

   ```bash
   uv run --project "${CLAUDE_PLUGIN_ROOT}" openspec archive <change-id> --yes
   ```

3. sync 결과를 재검증한다 — 실패는 아카이브가 만든 spec 상태의 결함이다. 고치고 재검증한다:

   ```bash
   uv run --project "${CLAUDE_PLUGIN_ROOT}" openspec validate --all --strict --no-interactive --json
   ```
