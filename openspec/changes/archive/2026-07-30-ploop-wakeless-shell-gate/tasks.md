# Tasks — ploop-wakeless-shell-gate

## 1. Core

- [x] 1.1 Wait classifier in `src/main.py` (mortal / file-condition / unbounded) + notices
- [x] 1.2 `wait_gate` PreToolUse entry (deny / warn / silent; inert outside active loop)
- [x] 1.3 `stop()` shell branch: running-status filter, wakeless prod (one-shot per set,
      `session_crons` voids), `wakeless_shells` written alongside `gated_shells`
- [x] 1.4 `state.py`: `wakeless_shells_path` + lifecycle (round arm, `/ploop:on`, launch clear)

## 2. Wiring

- [x] 2.1 `__main__.py` entry + `hooks.json` PreToolUse Bash matcher
- [x] 2.2 `bin/ploop-hook` fast path (no `*_active` marker → exit before Python)

## 3. Doctrine & docs

- [x] 3.1 `skills/launch/SKILL.md` wait-form rule (mortal conditions)
- [x] 3.2 `ARCHITECTURE.md`: decision 16 amendment, file table, hook table

## 4. Verification & release

- [x] 4.1 Tests: classifier parametrize, wait_gate I/O, wakeless prod (incident replay,
      informed sleep, cron void), status filter
- [x] 4.2 Full `pytest` + `ruff` green
- [x] 4.3 Version bump 0.49.2 → 0.50.0 (`pyproject.toml`, `plugin.json`)
