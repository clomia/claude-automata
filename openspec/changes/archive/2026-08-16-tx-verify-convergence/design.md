# tx-verify-convergence — design

## Rejected: hard retry cap

A cap on verify respawns closes non-integral transactions. "A transaction simply
cannot close before it is integral" is the tx invariant; the cap is a direct
violation, and heavy changes legitimately take five verify rounds. Rejected.

## Rejected: fail-count-lowered pass threshold

The proposal `threshold = 1/(fail_count·a) · (importance·b)` fails three ways:

1. **Evidence inversion.** An implementation that failed four verifies is *more*
   likely to be defective, not less. Lowering the bar as failures accumulate moves
   the gate against the direction the evidence points.
2. **Clean-context contamination.** The verify spawn receives the change-id and
   nothing else — that isolation is the stage's soul. Passing the attempt count in
   smuggles a narrative ("the implementer is struggling; grade easier") into the one
   context designed to be free of narrative.
3. **Pseudo-math.** The coefficients do not exist; an LLM handed a formula grades by
   vibe anyway. Deterministic parts belong in code; judgment parts belong in words.

What the proposal actually wanted — judgment cost proportional to stakes — is
achieved without the count by two separate dials:

- **The blocking bar is definitional**: pass = the spec is satisfied. A defect must
  cite the artifact coordinate it violates; a finding without one is an observation
  and cannot block. This is the load-bearing dial: fresh-spawn sampling noise drains
  into the observation lane and the goalposts stop moving.
- **Judgment depth ∝ change weight**: the verifier reads the delta's breadth and
  blast radius from proposal/design itself — no injection, no contamination.

## Coordinate set

Defect coordinates span all four artifact anchors — Requirement, Scenario, task,
design decision — so the three judgment axes (completeness, correctness,
consistency) keep their full reach: an unimplemented requirement blocks (its own
coordinate), a design contradiction blocks (the design decision is the coordinate),
while advice with no anchor cannot.
