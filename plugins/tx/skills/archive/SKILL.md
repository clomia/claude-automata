---
name: archive
description: "Archive the completed change: task gate, delta sync into main specs, revalidate"
argument-hint: "[change-id]"
effort: high
---

Archiving syncs the deltas into the main specs and freezes the change directory under
`openspec/changes/archive/`.

# 절차

1. Check the active changes and their task counts:

   ```bash
   "${CLAUDE_PLUGIN_ROOT}/bin/tx-hook" openspec list --json
   ```

   If no change is active, say so and stop. **A change with no tasks (no-tasks) or
   unfinished tasks fails the archive.** The CLI does not block this; the gate is
   enforced here. Fill missing tasks through `tx:plan`, unfinished ones through
   `tx:apply`.

2. Archive:

   ```bash
   "${CLAUDE_PLUGIN_ROOT}/bin/tx-hook" openspec archive <change-id> --yes
   ```

3. Revalidate the synced state. A failure is a defect in the spec state archive
   produced: fix it and revalidate. A finding against a still-active change belongs
   to that change, not to this archive:

   ```bash
   "${CLAUDE_PLUGIN_ROOT}/bin/tx-hook" openspec validate --all --strict --no-interactive --json
   ```
