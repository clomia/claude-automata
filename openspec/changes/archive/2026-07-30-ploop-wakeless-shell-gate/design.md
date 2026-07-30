# Design — ploop-wakeless-shell-gate

## Context

Decision 16 (ARCHITECTURE.md) rests on "a stop the gate swallows always comes back":
the harness re-wakes the session when a background task completes. That premise is
conditional — it needs at least one gated shell that actually exits. A file-condition
wait whose producer died never exits; the gate then `exit 0`s forever with zero wake
sources, and no hook runs after the stall (hooks fire only at stop). The verdict must
therefore be rendered *at the stop that creates the sleep*, and prevention must happen
*at launch*. Mortality of an arbitrary command is undecidable, so both surfaces are
heuristics over the command string with an explicit fail direction.

## Goals / Non-Goals

- Goal: an armed loop never *silently* enters a sleep no event can end.
- Goal: preserve decision 16 exactly — no advisor round arms while background pends,
  and deferral length itself is not a defect.
- Non-Goal: detecting waits hidden inside called scripts (`await.sh log 6000`) — the
  string is opaque; classification presumes mortal. The stop-time prod shares this
  blind spot by construction.
- Non-Goal: periodic re-prodding (report §5-D) — it consumes the harness's consecutive
  stop-block cap, which MAX_ANOMALIES exists to respect; one informed prod per set.

## Decisions

- **Deny only file-condition waits; warn the rest.** The one observed fatality and
  26/31 of loop-session unbounded waits are file-condition, and a strictly better form
  always exists (process-existence wait, `timeout`), so a deny costs nothing when
  right and one word (`timeout N`) when wrong. Hard-blocking the whole
  `until/while + sleep` class teaches hook evasion — worse than a warning being ignored.
- **The classifier errs mortal.** Bound markers (timeout/seq/SECONDS/read -t/--timeout/
  counter arithmetic) and process-existence conditions rescue to mortal; a missing
  `command` field is mortal. False-mortal → today's behavior (sleep); false-wakeless →
  one extra prod. Both are recoverable; a false advisor arm would not be (decision 16).
- **Stop prod is one-shot per set and arms nothing.** It rides the same exit-2 lane as
  SHELL_WAIT_NOTICE, before ledger/anomaly machinery, and writes both `wakeless_shells`
  and `gated_shells` so the very next identical stop sleeps (informed). Repeat prods
  would stalemate against the harness stop-block cap for no information gain.
- **`session_crons` voids the hazard.** A scheduled wakeup is a wake source; the sleep
  cannot be permanent, so the prod stays silent (ordinary shell gating still applies).
- **Status gates on `running` (absent counts as running).** Unknown non-running
  statuses fall to the early-advisor side — decision 16's stated failure direction —
  while absent-status keeps today's gating (schema-drift safety).
- **Wrapper fast path for the per-Bash hook.** `bin/ploop-hook` exits before spawning
  Python when `$CLAUDE_PLUGIN_DATA` holds no `*_active` marker, so machines with no
  armed loop pay a stat, not an interpreter, per Bash call.
- **Loop-scoped, tool-shape-scoped.** The gate runs only under an active loop (ploop
  owns loop sessions, not the user's ordinary sessions) and keys on command shape, not
  `run_in_background` — a foreground unbounded wait auto-backgrounds at its timeout
  and lands in the same immortal lane.

## Risks / Trade-offs

- [False deny on an exotically-bounded file wait] → the reason names the one-word fix
  (`timeout N`); bound-marker allowlist covers the common spellings.
- [Wakeless miss via opaque scripts] → documented non-goal; the launch-skill rule and
  deny reason teach the mortal forms, shrinking the population at the source.
- [Unknown `status` vocabulary] → fails toward early advisor per decision 16, never
  toward a parked loop.
- [Per-Bash-call hook latency in loop sessions] → single `uv run` spawn, 30s timeout,
  and only while a loop is armed; non-loop sessions take the wrapper fast path.
  Measured (this machine, warm): fast path ~4ms/call, Python path ~57ms/call.

## Migration Plan

Pure addition behind existing gates; no state migration. `wakeless_shells` follows the
`gated_shells` lifecycle (round arm, `/ploop:on`, launch clear). Rollback = revert.

## Open Questions

None — the `background_tasks` schema question from the incident report (§6) is settled
by the official Stop-input reference: shell entries carry `command` (≤1000 chars) and
`status`.
