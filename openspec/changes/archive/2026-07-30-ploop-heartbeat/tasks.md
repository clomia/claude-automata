# Tasks — ploop-heartbeat

## 1. Measurement (gate)

- [x] 1.1 Bundle statics: `asyncRewake` present in installed builds, timeout path
      unclamped for command hooks
- [x] 1.2 Live canary: asyncRewake Stop hook wakes an idle interactive session through
      the exec-chain shape, payload reaches the model
- [x] 1.3 Record both in `docs/research/asyncrewake-stop-hook-2026.md`

## 2. Core swap

- [x] 2.1 `main.py`: remove classifier stack (constants, regexes, `classify_wait`,
      `wait_gate`, wakeless block, notices); revert stop() shell branch keeping the
      running-status filter
- [x] 2.2 `main.py`: add `heartbeat_arm` (nonce + wrapper handoff; the wrapper sh owns
      the sleep) and `heartbeat_fire` (supersession/armed checks, exit 2 + notice) with
      `HEARTBEAT_SECONDS`, `HEARTBEAT_NOTICE`
- [x] 2.3 root canon: record the auto-update premise (no harness version guards) in
      결정 기록; prerequisites stay settings-only
- [x] 2.4 `state.py`: `wakeless_shells_path` → `heartbeat_nonce_path`, clear_round_state

## 3. Wiring

- [x] 3.1 `hooks.json`: drop PreToolUse Bash matcher; add Stop heartbeat entry
      (`asyncRewake: true`, `timeout: 11100`)
- [x] 3.2 `__main__.py`: entries swap (`wait-gate` out; `heartbeat`, `heartbeat-fire` in)
- [x] 3.3 `bin/ploop-hook`: remove the wait-gate fast path

## 4. Docs

- [x] 4.1 `ARCHITECTURE.md`: decision 19 rewritten (heartbeat), decision 16 pointer,
      hook table, file table, file map annotations
- [x] 4.2 Launch skill: keep the mortal-wait line; no heartbeat announcement

## 5. Verification & release

- [x] 5.1 Tests: heartbeat arm/fire branches; classifier and wakeless tests removed;
      status-filter test kept; prerequisite tests stay settings-only
- [x] 5.2 Full `pytest` + `ruff` green
- [x] 5.3 Version 0.50.0 → 0.51.0 (`pyproject.toml`, `plugin.json`)
