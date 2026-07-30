# ploop-heartbeat

## Why

0.50's wake-integrity answer polices agent-written Bash with a string classifier. Review
found the flaw structural, not incidental: mortality of a command is undecidable, both
protective layers share one classifier (a wait inside a called script defeats both), the
bound-marker allowlist is a spelling treadmill, and the deny gate assumes responsibility
that belongs to the agent. The owner's decision: reproduce the human supervision pattern
instead — a human who sees hours of silence asks "what are you doing?". Supervision
generalizes (it needs no theory of why the session sleeps — dead file waits, opaque
script waits, hung subagents alike); policing enumerates.

## What Changes

- **Heartbeat (new)**: a second Stop hook with `asyncRewake: true`. On every stop of an
  armed loop the arm phase records a nonce and hands off to the wrapper sh, which
  itself sleeps the 3h; at fire time it exits 0 silently if a later stop superseded it
  or the loop is gone, else exits 2 — waking the idle session with a payload directing
  a background-task audit (kill what can never finish, relaunch bounded, then continue
  or stop). Silence is the trigger, exactly the human pattern; an actively cycling loop
  never hears it. Sleep's cost cap drops from unbounded to 3h with zero agent
  compliance surface.
- **Classifier stack removal (0.50 rollback)**: `classify_wait` + regexes, the
  PreToolUse Bash `wait_gate`, the stop-side wakeless block, `wakeless_shells` state,
  and the wrapper fast path are deleted. `session_crons` is no longer read.
- **Kept from 0.50**: the running-status shell filter (decidable fact, orthogonal bug)
  and the launch-skill mortal-wait doctrine line (information, zero machinery).
- **No version guard** (owner premise, recorded in the root canon's 결정 기록):
  claude-automata targets the newest Claude Code at ship time and assumes auto-update —
  plugins never detect or branch on harness versions.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `ploop-wake-integrity`: the classification, launch-gate, and wakeless-block
  requirements are REMOVED; a heartbeat requirement is ADDED. The running-status
  gating requirement is unchanged.

## Impact

- `plugins/ploop/src/main.py`: − classifier/gate/wakeless (~130 lines); +
  `heartbeat_arm`, `heartbeat_fire` entries and notice.
- `plugins/ploop/src/state.py`: `wakeless_shells_path` → `heartbeat_nonce_path`.
- `plugins/ploop/src/__main__.py`, `hooks/hooks.json`, `bin/ploop-hook`: entry swap,
  Stop hook entry with `asyncRewake`/`timeout: 11100`, fast path removed.
- `plugins/ploop/ARCHITECTURE.md` decision 19 rewritten; tables and file map follow.
- `docs/research/`: dated measurement note (bundle statics + live wake canary).
- Tests reshaped; version 0.50.0 → 0.51.0 (`pyproject.toml`, `plugin.json`).
