# ploop-wake-integrity — delta

## MODIFIED Requirements

### Requirement: Only running shells gate the round

Shell entries SHALL gate the round only while their `status` is `running` (an absent
status counts as running). A terminal-status shell SHALL NOT defer the advisor. Gating
SHALL be silent: a stop with running shells exits 0 without blocking the stop or
injecting any text — the sleep it allows is bounded by the heartbeat.

#### Scenario: A completed shell left in the list does not park the loop

- **WHEN** the only background task is a shell with `status: "completed"`
- **THEN** the stop proceeds to ordinary round handling (the advisor can arm)

#### Scenario: Running shells defer the advisor silently

- **WHEN** an armed loop stops while a running shell is in `background_tasks`
- **THEN** the stop exits 0 with no stderr and no gating state written — the shell's
  exit or the heartbeat wakes the session
