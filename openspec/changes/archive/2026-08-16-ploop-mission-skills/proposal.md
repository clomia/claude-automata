# ploop-mission-skills

## Why

Field use of define-mission surfaced two calibration gaps. First, over 90% of
launched missions run unattended — the operator starts the loop and leaves — yet most
in-loop AskUserQuestion calls are rhetorical (the agent already holds the answer),
and when the agent owns the initiative it is also the participant best placed to
resolve a choice. The mission interview never asks about attendance, so anchors ship
without the one line that pre-empts decision offloading. Blocking the ask channel
alone would be unsafe: choices that would have gone out as questions become
unilateral decisions, so unmanned operation must also tighten the Constraint
interview (what may NOT be decided without the user). Second, agents present the
deadline declaration as if it were required; it is optional, and a fabricated
deadline distorts the advisor's judgment.

## What Changes

- **Unmanned operation becomes a standard interview axis.** define-mission always
  asks whether the run is unattended. When it is, the interview extracts the no-go
  zone into Constraint and adds one dense declaration line — user absent, decisions
  owned, no waiting for confirmation. The target is the behavior (deferring
  decisions), not the tool: `askUserQuestionTimeout` already prevents hangs, so the
  line owns decision-making rather than banning AskUserQuestion.
- **The deadline is explicitly optional.** The rule now opens with (선택), states
  that no declaration is the default, and forbids inventing a deadline for a mission
  that has none.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none — define-mission has no spec'd capability; the ploop-deadline spec governs the
loop's handling of a declared deadline, which is unchanged here)

## Impact

- `plugins/ploop/skills/define-mission/SKILL.md`: interview step 2 (unmanned) added,
  deadline rule reworded to explicit optionality.
