# ploop-wake-integrity Specification

## Purpose
TBD - created by archiving change ploop-wakeless-shell-gate. Update Purpose after archive.
## Requirements
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

### Requirement: Silence wakes an armed loop within the heartbeat interval

Every stop of an armed loop SHALL arm a heartbeat: record a fresh nonce and continue as
a detached 3-hour timer (an `asyncRewake` Stop hook process, alive across context
compaction). At fire time the timer SHALL exit silently when the loop is no longer
armed or a later stop has superseded its nonce, and SHALL otherwise end with exit 2 —
waking the idle session with a notice that directs an audit of everything alive in the
background (kill what can never finish, relaunch bounded if needed, then continue or
stop). Stops
outside an armed loop SHALL arm nothing.

#### Scenario: An armed stop arms the timer

- **WHEN** the heartbeat arm phase runs for a session whose active marker exists
- **THEN** a fresh nonce is persisted and the handoff (session, nonce, interval) is
  emitted for the hook process, which sleeps the interval and re-enters the fire
  phase with exactly that session and nonce

#### Scenario: A later stop supersedes the watch

- **WHEN** the fire phase runs with a nonce that no longer matches the persisted one
- **THEN** it exits 0 with no output

#### Scenario: Three hours of silence wake the session

- **WHEN** the fire phase runs with the current nonce and the loop still armed
- **THEN** it exits 2 with the heartbeat notice on stderr

#### Scenario: A finished or paused loop is never woken

- **WHEN** the fire phase runs after the active marker is gone
- **THEN** it exits 0 with no output

#### Scenario: Ordinary sessions are untouched

- **WHEN** the heartbeat entry runs for a session with no active marker
- **THEN** it exits 0 without writing a nonce or starting a timer

