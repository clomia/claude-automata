# ploop-wake-integrity — delta

Supervision replaces classification: instead of judging which commands can exit, the
loop is woken after 3 hours of silence and the agent itself audits what is still
running. Wake-integrity becomes "no sleep outlives the heartbeat interval".

## ADDED Requirements

### Requirement: Silence wakes an armed loop within the heartbeat interval

Every stop of an armed loop SHALL arm a heartbeat: record a fresh nonce and continue as
a detached 3-hour timer (an `asyncRewake` Stop hook process, alive across context
compaction). At fire time the timer SHALL exit silently when the loop is no longer
armed or a later stop has superseded its nonce, and SHALL otherwise end with exit 2 —
waking the idle session with a notice that directs an audit of live background tasks
(kill what can never finish, relaunch bounded if needed, then continue or stop). Stops
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

## REMOVED Requirements

### Requirement: Wait commands classify by wake guarantee

**Reason**: Mortality of a command is undecidable; the classifier was a spelling
treadmill with a blind spot (script-internal waits) shared by both of its consumers.
**Migration**: none — the heartbeat needs no theory of why a session sleeps.

### Requirement: Launch-time wait gate in active-loop sessions

**Reason**: Policing agent-written Bash assumes the agent's responsibility and taxes
every Bash call; with sleep bounded by the heartbeat, prevention-by-deny lost its
justification. The mortal-wait doctrine line in the launch skill carries the teaching.
**Migration**: none — commands run ungated; a bad wait now costs at most one heartbeat
interval.

### Requirement: Stop into a wakeless state is blocked once, informed

**Reason**: Superseded by the heartbeat, which covers strictly more park modes (opaque
scripts, hung subagents) without classifying shells at stop time.
**Migration**: `wakeless_shells` state is replaced by the heartbeat nonce; no user
action.
