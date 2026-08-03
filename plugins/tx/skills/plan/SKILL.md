---
name: plan
description: "Plan the change as OpenSpec artifacts: proposal, delta specs, design, tasks"
argument-hint: "[change intent]"
effort: max
---

squash merge erases branch history. Only the archive of these artifacts preserves the
change's intent and design.

# 절차

1. Pick a change-id. Usually the tx branch's slug:

   ```bash
   "${CLAUDE_PLUGIN_ROOT}/bin/tx-hook" openspec new change <change-id>
   ```

2. Write the artifacts in dependency order. Each artifact's instructions come from the
   engine; the engine owns the format:

   ```bash
   "${CLAUDE_PLUGIN_ROOT}/bin/tx-hook" openspec instructions <artifact> --change <change-id> --json
   ```

   Tasks hold only work that is done before close. Post-merge actions are follow-up
   changes, not tasks.

3. Validate:

   ```bash
   "${CLAUDE_PLUGIN_ROOT}/bin/tx-hook" openspec validate <change-id> --strict --no-interactive --json
   ```

   A delta-less change declares `skip_specs: true` in its `.openspec.yaml`; validate
   then accepts zero deltas. Fix everything until green.

4. Continue straight into `tx:apply`. plan is not a stopping point.

# Unknown 처리

Every unknown met while planning resolves one of three ways:

- **measurable**: measure it and record the result.
- **reversible**: adopt an assumption and state it in design.
- **neither**: halt the change and record why in the proposal.
