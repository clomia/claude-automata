---
name: apply
description: Implement the planned change task by task, then spawn the independent verify stage until it passes
argument-hint: "[change-id]"
effort: max
---

# 절차

1. Judge the gate: every artifact listed in `applyRequires` must be `done`.
   (`isComplete` is not the gate; design exists only when its inclusion criteria apply.)
   Otherwise what is missing is planning, not implementation: return to `tx:plan`.

   ```bash
   "${CLAUDE_PLUGIN_ROOT}/bin/tx-hook" openspec status --change <change-id> --json
   ```

2. Take the context file paths and the task checklist:

   ```bash
   "${CLAUDE_PLUGIN_ROOT}/bin/tx-hook" openspec instructions apply --change <change-id> --json
   ```

3. Implement the tasks in dependency order.
   The spec wording binds the implementation. If implementation reveals the spec is
   wrong, fix the delta through `tx:plan`, then continue.

4. When every task is done and the change carries a spec delta, **spawn the verify
   stage** (mandatory):

   ```
   Agent(subagent_type="tx:verify", prompt="change-id: <change-id>")
   ```

   Pass nothing but the change-id.
   Fix reported defects here, while the implementation context is live, and respawn
   until pass. A defect that does not reproduce is a defect in the spec wording: fix
   it through `tx:plan`.

# Unknown 처리

Every unknown met while implementing resolves one of three ways:

- **measurable**: measure it and record the result.
- **reversible**: adopt an assumption and state it in design.
- **neither**: halt the task and record why in tasks.md.
