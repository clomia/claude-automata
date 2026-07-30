# Design — ploop-heartbeat

## Context

The owner's verdict on 0.50: the wait classifier pulls agent responsibility into the
plugin, and heuristic string policing always leaks. The replacement reproduces the
human supervision pattern — hours of silence trigger a "what are you doing?" — with the
plugin owning supervision (its own domain: ploop already reproduces the human reviewer
as the advisor) and the agent owning judgment at wake time.

## Goals / Non-Goals

- Goal: no sleep of an armed loop outlives 3 hours, regardless of why it sleeps.
- Goal: zero agent compliance surface for the wake mechanism itself.
- Non-Goal: resume/exit robustness — exit ends ploop's guarantee (owner scoping).
  Compaction robustness IS required and holds: the timer is an OS process, the payload
  regenerated at fire time.
- Non-Goal: preventing bad waits from being written. Doctrine teaches; the heartbeat
  bounds the cost.

## Decisions

- **Carrier: `asyncRewake` Stop hook** over session crons and plugin monitors. Crons:
  agent-registered (compliance), frozen prompt text, and a discovered 7-day recurring
  expiry that would silently drop the wake source mid-mission. Plugin monitors: no
  timeout concern, but experimental surface and silently skipped on Monitor-unavailable
  hosts (providers, telemetry-off) — a silent protection hole is the pathology being
  eliminated. asyncRewake is stable hooks surface and runs wherever ploop runs.
- **Silence semantics via nonce supersession.** Each armed stop writes a fresh nonce;
  each timer captures its own. Fire = nonce still current = no stop for 3h. An actively
  cycling loop never hears a heartbeat. Wakes during a 3h single working turn are
  accepted (rare; harmless interjection).
- **The sleep lives in the wrapper sh, above uv.** Measured (uv 0.11.21): `exec uv run`
  does not exec into python — uv stays resident (~26MB RSS) as the watched process for
  as long as anything below it runs, so sleeping in python (or in a child it execs)
  would keep one uv per timer alive for 3h. Instead the wrapper's heartbeat branch runs
  python twice, briefly: `heartbeat-arm` reads the event, writes the nonce, and prints
  the handoff line ("session nonce seconds", empty = not armed); the wrapper sh itself
  (~1MB) sleeps the interval and then runs `heartbeat-fire`, whose exit 2 and stderr
  propagate up as the wrapper's own result. Superseded timers (one per stop) each cost
  a sleeping sh, not an interpreter.
- **`timeout: 11100`** (> 10800 + fire-phase slack). Verified against the 2.1.220
  bundle: command-hook timeout is `e.timeout*1000` passed through unclamped (the only
  Math.min clamp is SessionEnd's budget); the async registry consumes the same value.
  Live canary (75s scale) verifies the end-to-end wake; see
  `docs/research/asyncrewake-stop-hook-2026.md`.
- **Failure direction.** If asyncRewake ever silently stops firing (harness drift), the
  loop reverts exactly to pre-0.50 behavior — no new harm. An old harness would run the
  hook synchronously (3h block per stop), but that concern is void by owner premise —
  claude-automata assumes an auto-updated Claude Code and ships against the newest
  harness only (root canon, 결정 기록); no version guard exists. Known residual:
  `claude -p --resume` of an armed session may run the hook synchronously
  (interactive-gated wake path) — headless resume of a loop is outside ploop's
  guarantee (same owner scoping as resume).
- **What stays.** Running-status shell filter (decidable, fixes advisor-deferral — a
  defect the heartbeat cannot reach: a phantom shell blocks convening while awake) and
  the mortal-wait doctrine line (information at zero machinery; a bad wait still costs
  a 3h window). `session_crons` reading goes: nothing consumes it.
- **No skill announcement of the heartbeat.** The payload is self-describing at fire
  time; pre-announcing would spend launch-context on an event that may never fire
  (llm-prompt: omission first).

## Risks / Trade-offs

- [Hidden async-hook reaper beyond `timeout`] → none found in bundle statics; if one
  exists, failure = today's behavior (no wake), not a regression. 3h-scale live run
  deliberately not a merge gate for this reason.
- [Timer fleet growth] → one sleeping `sh` (~1MB) per stop, all but the newest exit 0
  at their fire time; worst case tens of MB-hours per mission.
- [Wake during a long working turn] → accepted; the notice reads as an audit prompt,
  harmless mid-work.

## Migration Plan

Pure swap within the plugin; `wakeless_shells` state file is dropped (stale copies are
inert — nothing reads them), `heartbeat_nonce` follows `clear_round_state`. Rollback =
revert.

## Open Questions

None — both unknowns were measured (bundle statics; live wake canary).
