# ploop-silent-shell-gate

## Why

A full audit of every surface ploop injects into agents (15 surfaces) found two that
still speak the pre-heartbeat threat model — "the loop can sleep forever" — which the
heartbeat (decision 19) made structurally false. Injected falsehoods manufacture false
assumptions (llm-prompt rule); both surfaces are also redundant: their teaching is
carried by the launch constitution and, better-timed, by the heartbeat audit itself.

## What Changes

- **Shell gating goes silent.** The once-per-set exit-2 `SHELL_WAIT_NOTICE` ("leaves
  the loop asleep for good — clear it first") is removed together with its machinery:
  the subset check and the `gated_shells` state file + its three lifecycle clears.
  Running shells now defer the advisor exactly like subagents and workflows — a silent
  exit 0 — and the sleep this allows is bounded by the heartbeat. Legacy `gated_shells`
  files on disk become inert (same precedent as `wakeless_shells` in 0.51).
- **The constitution's mortal-wait line is removed.** "producer가 죽으면 영원해져
  session이 깨어날 근거를 잃는다" is false post-heartbeat (the wake basis is never
  lost; the cost is ≤3h), and its remedy teaching (`pgrep`/`timeout`) duplicates
  `HEARTBEAT_NOTICE`, which teaches it at the moment it actually matters.
- Everything else survived the audit verbatim: RETRY/DECLINE notices, advisor trigger,
  end notice, heartbeat notice, on/off/define-*/docent skills, advisor/narrator
  definitions, instruction.md — 13 surfaces verified accurate.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `ploop-wake-integrity`: the shell-gating requirement gains the silent semantics
  (gating never blocks a stop or injects text; the allowed sleep is heartbeat-bounded).

## Impact

- `plugins/ploop/src/main.py`: notice + subset logic removed; stop() shell branch is a
  bare silent gate; `gated_shells` unlinks dropped from arm/on.
- `plugins/ploop/src/state.py`: `gated_shells_path` property + round-clear entry out.
- `plugins/ploop/skills/launch/SKILL.md`: mortal-wait line out.
- `plugins/ploop/ARCHITECTURE.md`: decision 16 rewrite (silent gate), file/hook tables,
  `/ploop:on` transient list.
- Tests reshaped; version 0.51.0 → 0.52.0.
