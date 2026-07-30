# Design — ploop-silent-shell-gate

## Context

Owner-directed audit of all 15 agent-facing injection surfaces after the heartbeat
landed. Two surfaces still assert the extinct threat ("asleep for good" / "깨어날
근거를 잃는다"); both are removed rather than rewritten, because their truthful
residue is already carried elsewhere.

## Decisions

- **Remove, don't rewrite.** A truthful rewrite of either surface would restate what
  the constitution ("완료가 session을 깨운다", advisor convening rule) and the
  heartbeat audit (remedies, at the moment of actual stall) already carry — a rewrite
  is machinery for a redundancy (llm-prompt: omission first).
- **Silent gate = the subagent/workflow pattern.** Shells were the one gated type with
  a speaking lane; post-heartbeat there is nothing true left to say at gate time, so
  shells join the silent-wait pattern. The `gated_shells` state existed only to dedup
  the notice — it goes with it. Legacy files on disk are inert (0.51 precedent:
  `wakeless_shells`).
- **What the removal does NOT change**: the advisor-convening contract (decision 16 —
  running shells still defer), the status filter, the Monitor/ambient rule in the
  constitution (advisor-deferral by a live ambient process is real and heartbeat does
  not cure it — that rule stays).
- **Accepted cost** (owner-ratified in the audit): an ambient process mistakenly left
  on the shell lane is now corrected at the first heartbeat audit (≤3h) instead of at
  the first stop. Bounded, rare, and the constitution already forbids the form.

## Risks / Trade-offs

- [Agent wonders why no advisor arrives while shells run] → the constitution line
  "background가 빌 때까지 advisor는 소집되지 않으며" carries this; a sleeping agent
  does no wondering.

## Migration Plan

Pure removal; no state migration. Rollback = revert.

## Open Questions

None.
