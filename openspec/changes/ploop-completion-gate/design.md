# ploop-completion-gate — design

## Rejected: silence as completion (B)

The owner's draft let two unanswered directives end the loop as a legitimate,
self-certified completion. Rejected for adverse selection: the variable deciding
whether an audit happens would be the main agent's confidence, and LLM confidence at
the end of long work is systematically biased toward overclaiming — the samples most
in need of the audit would be exactly the ones skipping it. The cost difference to
the advisor-signed gate is one advisor call per mission. The silence path is kept as
an **emergency stop** instead: it ends the loop *without* a completion verdict
(phase stays advising, `/ploop:on` resumes), and the end cause says so.

## Disclosure policy: hide until the first ignored directive

The silent exit serves two populations. The pathological one (broken/confused mains,
ESC storms) never reads notices — disclosure is irrelevant to it and the failsafe
works regardless. The deliberate one needs to know the consequence at the moment of
decision. Advertising the exit in the standing directive would erode the audit-only
default every stop for days; hiding it forever would make the second silence
indistinguishable from an accident. So the decline notice — issued once, after the
first unanswered directive — is the single place of disclosure.

## Rejected: per-round advisor retention with a softer prompt

Rewriting the instruction alone (verifier framing) while keeping the every-stop
summons would still pay opus-max per stop and still surface an external report into
every round. The field evidence was that per-round auditing's marginal value turns
negative on multi-day missions; the cadence, not only the prompt shape, was the
recursion fuel.

## Narration cadence: per-stop, narrator invoked by the main agent

Audit-time narration was rejected on three grounds: a multi-day un-narrated span can
exceed the narrator's context (forcing chunking machinery and a narrated-watermark
ledger), the loop log would stay empty between audits (docent blind mid-mission),
and the machinery delta from the existing slice/write_log flow would grow instead of
shrink. Per-stop narration bounds every slice to one round by construction, keeps
the flight recorder live, and preserves the 1-stop consensus latency (steering and
rebuttals ride the narration to the next audit). With the narrator no longer inlined
in the advisor call, the advisor spawns no one: the loop machinery's nesting
dependency vanishes and `Agent` is disallowed on the advisor to seal the Bash-ban
against proxy delegation — an audit demands evidence, it does not produce it.

## Bare-stop judgment: line delta, T = 15

The failsafe's target is silence (a stop with no tool activity), not small work. The
Stop event carries no work signal, so the judgment uses the one structural dependency
the loop already stands on — the transcript is line-append-only — via the delta from
`round_start_line`. Measured on this machine (2.1.233, thinking on): text-only turns
append 1–9 lines, the smallest tool turn 23; T=15 sits between the bands
(`docs/research/stop-turn-line-footprint-2026.md`). A narrator-relay-only turn reads
as working — indistinguishable from a one-tool work round by line count — and the
misjudgment harms were weighed: falsely ending a healthy small round beats delayed
detection of a relay-only zombie (bounded by deadline and `/ploop:off`).
`last_assistant_message` (a new official Stop input field) was considered and
rejected: it carries text, not work evidence, and interpreting meaning is outside
the hook's contract.

## Official-docs audit (2026-08, docs + 2.1.233 bundle grep)

- `asyncRewake` is now officially documented ("wakes Claude on exit code 2") — the
  heartbeat's dependency class upgrades from observed to official.
- `background_tasks` disappeared from the hooks docs page but lives in the 2.1.233
  bundle (32 hits) — the background gate stands; recorded as a docs gap.
- Agent `run_in_background` persists ("background by default … pass false only when
  your very next action depends on the result" — exactly these two calls), with an
  observed context variant that omits the param entirely; the graceful path
  (validation failure → retry without → background run absorbed by the in-flight
  guard and completion notifications) is recorded in decision 10.
- Nested-subagent default drifted 5 (2.1.172) → 1 (2.1.217) → 3 (2.1.219): the
  2.1.217 canon claim was stale; the pin's rationale is re-grounded as environment
  determinism, per the owner's directive that nesting stays provisioned.
- `opus[1m]` agent-frontmatter alias and `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP` are
  absent from docs but alive in the bundle — observed dependencies for
  audit-harness-deps.
