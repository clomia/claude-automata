# ploop-completion-gate

## Why

The per-round advisor was an ideation engine — derive every region the anchor implies,
avoid local optima — which fits a purpose anchor (open-ended direction), while 100% of
field use is missions (bounded goals). On missions it produced complexity recursion
(the commonest advice was defects in the previous round's advice-driven work) and, on
multi-day runs, retrospective doubts whose cost to act on exceeded their value. The
observed value concentrated in the anchor system and the never-silently-stops safety
rails; the every-stop advisor subscription paid opus-max per stop for diminishing
returns.

The redesign keeps the product promise — the loop ends when the mission is really
done, not when the agent believes it is — by moving the advisor from a forced
per-round summons to a **completion gate**: the main agent works freely, convenes the
advisor on its own judgment (a completion claim, or a voluntary audit), and only the
advisor's verdict certifies completion. A silent main-side emergency exit (two
consecutive unanswered directives) is preserved against infinite loops, disclosed only
at the moment of decision. Design records in design.md cover the rejected
alternatives (silence-as-completion, per-round retention, narration at audit time)
and the official-docs audit that grounded the mechanics.

## What Changes

- **Standing directive replaces the advisor trigger.** Every armed stop injects:
  narrate the finished round (narrator call, verbatim, unconditional), re-read the
  anchor and keep working if work remains, convene the advisor (verbatim call) only
  on a completion judgment or a wanted audit. Only the advisor can certify
  completion.
- **The advisor becomes a mission auditor.** Its instruction is rewritten from
  region-derivation to verdict: every finding must cite an anchor coordinate
  (requirement/Constraint); state beats narrative (measure directly); evidence that
  passed an independent gate outranks re-measurement; rebutted items are not
  re-flagged; the loop is ended with `MISSION_COMPLETE_ENDING_THE_TURN` (certified
  completion) or `DEADLINE_EXPIRED_ENDING_THE_TURN` (expiry closure — never dressed
  as completion; the old "no further advice" wording is false under the new
  semantics). A report is honored as a verdict only when the audit token was
  consumed this round — a file the gated advisor did not write cannot certify.
  The main agent consumes reports as observations, not orders.
- **Rounds become stop-to-stop time slices.** The ledger gains a `round` counter;
  the narrator runs every round at depth 1, invoked by the main agent directly (the
  advisor no longer spawns anyone — `Agent` joins its disallowedTools), and the loop
  log becomes a two-entry flight recorder (`[[ Round N ]]` narrations, `[[ Audit K ]]`
  reports) that bounds the audit's action-history input.
- **Anomaly judgment narrows.** A working stop (real transcript growth, judged by a
  measured line-delta threshold T=15) is never an anomaly and resets the streak; a
  bare stop (no tool activity) gets the decline notice — now the single place the
  silent exit is disclosed — and a second consecutive anomaly ends the loop without
  a completion verdict, resumable. Malfunction (advisor ran, wrote nothing) keeps
  its retry path; round freezing is retired (rounds are temporal).
- **Deadline reaches both participants**: the status line rides the directive header
  (the clock is now the main agent's convening input) and the advisor prompt; an
  expired deadline closes the keep-working branch and mandates the audit.
- **Depth pin re-grounded**: the nested-subagent prerequisite stays (init provision +
  launch assertion) but as an orchestration-environment pin against a default that
  drifted 5→1→3 across three releases — the loop machinery itself closes at depth 1.
- Exposure surfaces re-aligned: launch/docent/define-purpose skill bodies, docent
  resolver output (round vs audits), README pair, site pages, ploop canon.

## Capabilities

### New Capabilities

- `ploop-completion-gate`: the standing round directive, the advisor's sole
  certification authority, working/bare stop judgment, the disclosure policy, and
  the per-stop narration flight recorder.

### Modified Capabilities

- `ploop-deadline`: the status line now surfaces to the main agent (directive
  header) as well as the advisor prompt, and an expired deadline mandates convening;
  the machinery still never pauses or gates on the clock.
- `ploop-candidates`: the re-delivery vehicle is the round directive (wording — the
  behavior is unchanged).
- `ploop-docent`: the resolver reports the round ordinal from the ledger's `round`
  field and the audit count separately.
- `init-cli`: the settings-prerequisites rationale for the spawn-depth env is
  re-grounded (environment pin against the drifted default, not an advisor-path
  repair) — the provisioned value and behavior are unchanged.

## Impact

- `plugins/ploop/src/prompt.py`: `format_advisor_trigger` → `format_directive`;
  audit-history formatting; deadline dual delivery + expired variant.
- `plugins/ploop/src/main.py`: `stop()` re-judged (flight-record, verdict,
  working/bare, no freeze); token renamed; `BARE_STOP_LINE_THRESHOLD`; two log entry
  writers; deny message; docstrings.
- `plugins/ploop/src/state.py`: 5-field ledger (`round` added).
- `plugins/ploop/src/docent.py`: round/audits output.
- `plugins/ploop/agents/advisor.md`, `prompts/instruction.md`: rewritten;
  `agents/narrator.md` unchanged.
- `plugins/ploop/skills/launch|define-purpose|docent/SKILL.md`: re-aligned.
- `plugins/ploop/ARCHITECTURE.md`: glossary, core loop, decisions 2–20 revised,
  decisions 22–24 added, risks/limits updated.
- `docs/research/stop-turn-line-footprint-2026.md`: T measurement record.
- Root `ARCHITECTURE.md` 결정 기록 wording; README ko/en; site en/ko.
- Tests reshaped; version 0.54.0 → 0.55.0.
