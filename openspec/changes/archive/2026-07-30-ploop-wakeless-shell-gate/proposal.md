# ploop-wakeless-shell-gate

## Why

ploop's Stop gate defers the advisor while background shells run, on the premise that
"a shell's exit wakes the session" (ARCHITECTURE decision 16). The premise is conditional:
it holds only if at least one gated shell actually exits. A background shell that can
never exit — observed form: `until [ -s <file> ]; do sleep 60; done` whose producer died —
leaves the loop asleep with zero wake sources, and since hooks only run at stop, no code
can ever recover it. Field incident: 32.8 hours of a 39-hour mission lost, recovered only
by a human keystroke. Loop sessions produce this form 2.9x more often than other sessions
(21.5% vs 7.5% of background shells) because the launch skill itself directs completion
waits into background shells.

## What Changes

- **Launch-time wait gate (new PreToolUse Bash hook, active-loop sessions only)**:
  deny unbounded file-condition waits (the observed fatal form — a strictly better
  alternative always exists), inject a warning for other unbounded sleep-loops, pass
  everything else untouched. Fails at the moment of the mistake, not 33 hours later.
- **Stop-time wakeless prod**: when every still-running background shell classifies as an
  unbounded wait and no session cron exists, the stop is blocked once (exit 2) with a
  notice naming the shells — a guaranteed-delivered warning at the exact transition into
  the wakeless state. Stopping again with the same set is honored (informed sleep); no
  advisor round is armed with background pending (decision 16 is preserved).
- **Status filter**: only `status == "running"` shells gate the round; a terminal-status
  shell lingering in `background_tasks` can no longer defer the advisor forever.
- **Launch-skill wait-form rule**: one line teaching mortal wait conditions
  (process existence / `timeout` bound over file content).
- **hooks wrapper fast path**: the new per-Bash-call hook exits in the shell wrapper when
  no loop is active on the machine, so non-loop sessions pay no interpreter spawn.

## Capabilities

### New Capabilities
- `ploop-wake-integrity`: an armed loop never sleeps without a wake source — background
  waits are kept mortal at launch, and a stop into a wakeless state is blocked once with
  an informed notice.

### Modified Capabilities

(none — the advisor-convening contract of decision 16 is unchanged: the advisor still
convenes only when foreground and background are both empty)

## Impact

- `plugins/ploop/src/main.py`: wait classifier, `wait_gate` entry, stop() shell-branch
  (status filter + wakeless prod), notices.
- `plugins/ploop/src/state.py`: `wakeless_shells` workspace path (+ round-clear).
- `plugins/ploop/src/__main__.py`, `plugins/ploop/hooks/hooks.json`,
  `plugins/ploop/bin/ploop-hook`: new `wait-gate` entry + fast path.
- `plugins/ploop/skills/launch/SKILL.md`: wait-form rule.
- `plugins/ploop/ARCHITECTURE.md`: decision 16 amendment, file/hook tables.
- `plugins/ploop/tests/test_main.py`: classifier, gate, prod, status-filter coverage.
- Version bump: `pyproject.toml` + `plugin.json` 0.49.2 → 0.50.0.
