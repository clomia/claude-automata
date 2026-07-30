# Tasks — ploop-silent-shell-gate

## 1. Core removal

- [x] 1.1 `main.py`: `SHELL_WAIT_NOTICE` + comment out; stop() shell branch → bare
      silent exit 0 (status filter kept); `gated_shells` unlinks out of arm_advisor
      and on_command (+docstring)
- [x] 1.2 `state.py`: `gated_shells_path` property + clear_round_state entry out
- [x] 1.3 `skills/launch/SKILL.md`: mortal-wait line out

## 2. Docs

- [x] 2.1 `ARCHITECTURE.md`: decision 16 rewrite (silent gate, notice rationale out),
      file table row out, hook table Stop row, `/ploop:on` transient list

## 3. Verification & release

- [x] 3.1 Tests: silent-gate test replaces nags-once; monitor-only test drops
      `gated_shells` seeding (on/launch tests never referenced it — no-op verified)
- [x] 3.2 Full `pytest` + `ruff` green; no live machinery references remain —
      `gated_shells`/`SHELL_WAIT` survive only in frozen archives and decision 16's
      historical removal note
- [x] 3.3 Version 0.51.0 → 0.52.0 (`pyproject.toml`, `plugin.json`)
