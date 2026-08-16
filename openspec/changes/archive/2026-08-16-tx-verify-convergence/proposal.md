# tx-verify-convergence

## Why

Field use showed the verify loop stalling for hours even on light changes. Two causes.
First, the implementer turns passive after a report or two — it fixes exactly what
verify flagged and looks no further, while each fresh verify (a clean context by
design) samples new findings from the artifact, so convergence waits on the sampler
instead of on the defect mass. Second, the pass bar was implicitly "the verifier has
nothing left to say": with no definitional bar, taste-level findings block the close
and the goalposts move on every respawn.

Two remedies considered and rejected are recorded in design.md: a hard retry cap
(violates the transaction invariant — a transaction cannot close before it is
integral) and a fail-count-lowered pass threshold (inverts the evidence: more failed
verifies mean a defect is more likely, and passing the count in contaminates the
clean-context spawn).

## What Changes

- **Pass is defined as spec satisfaction.** The verify report splits into two lanes:
  **defect** (blocks the close; must cite an artifact coordinate —
  Requirement/Scenario/task/design decision — plus a code coordinate and evidence)
  and **observation** (advisory; beyond the artifacts; the implementer's call). A
  finding that cannot cite a coordinate cannot block. Judgment depth is scaled to the
  change's weight, which the verifier reads from proposal/design itself.
- **The implementer reads reports as observation, not instruction.** apply and close
  gain the generalize-and-preempt directive: hunt the same cause on other surfaces,
  predict the next report from the flow, then respawn.
- **Stall valve**: a defect re-reported after a grounded rebuttal means the spec
  wording admits two readings — the exit is fixing the wording through tx:plan, not
  another round of the same dispute.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none — the verify stage has no spec'd capability; retroactive transcription is
excluded by the root canon)

## Impact

- `plugins/tx/agents/verify.md`: 보고 section replaced (defect/observation lanes,
  definitional pass, depth ∝ weight).
- `plugins/tx/skills/apply/SKILL.md`: step 4 gains the observation framing,
  generalize-and-preempt, and the widened wording valve.
- `plugins/tx/skills/close/SKILL.md`: verify bullet gains the same directive.
- `plugins/tx/README.md`: verify stage clause — only coordinate-anchored defects
  gate.
- Version 0.16.0 → 0.17.0.
