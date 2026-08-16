# ploop-completion-gate — delta

The advisor moves from a forced per-round summons to the loop's completion gate: the
main agent sails freely under a standing directive, and only the advisor's verdict
certifies the mission complete.

## ADDED Requirements

### Requirement: Every armed stop injects the standing round directive

Every stop of an armed loop that passes the background and in-flight gates SHALL be
blocked (exit 2) with the standing directive: a verbatim narrator call for the round
just sliced, the direction to re-read the anchor and keep working while work remains,
and a verbatim advisor call to run only on a completion judgment or a wanted audit.
The directive SHALL state that only the advisor can certify completion and SHALL NOT
disclose the silent-exit failsafe.

#### Scenario: Fresh launch arms without judging

- **WHEN** the first stop after /ploop:launch fires
- **THEN** the directive is injected with both verbatim calls, the audit token is
  armed, and no anomaly is recorded regardless of transcript size or token absence

#### Scenario: The steady-state directive keeps the audit as the only visible exit

- **WHEN** any directive is injected outside an anomalous re-arm
- **THEN** it contains no mention of the loop ending on unanswered directives

### Requirement: Only the advisor's verdict certifies completion

The advisor SHALL write its verdict to the report file: a findings report, each
finding citing an anchor coordinate, or an ending token — the completion token,
or the deadline-closure token for an expired-deadline wrap-up, so the end cause
is never disguised. The hook SHALL honor the report file as a verdict only when
the audit token was consumed this round — a report present with the token
unconsumed was not written by the gated advisor and SHALL be ignored (and
cleared at the arm). On an ending token the loop converges (phase converged,
gate dropped, recap notice carrying that token's honest cause); a findings
report SHALL be appended to the audit history and the loop log, and the loop
continues.

#### Scenario: Completion token converges

- **WHEN** the stop reads a report file containing the completion token with the
  audit token consumed
- **THEN** the phase moves to converged, the active gate drops, and the end notice
  reports the advisor's certification with a loop-log recap

#### Scenario: Deadline closure is not dressed as completion

- **WHEN** the stop reads a report file containing the deadline-closure token
- **THEN** the loop converges and the end notice names the expired deadline as the
  cause, not mission completion

#### Scenario: A report the advisor did not write is no verdict

- **WHEN** a report file exists at a stop whose audit token was never consumed
- **THEN** no verdict is recorded — the stop is judged working or bare on its
  transcript growth and the file is cleared as the next round arms

#### Scenario: Findings report continues the loop

- **WHEN** the stop reads a report file with findings and no token
- **THEN** the report joins the audit history and the log as an Audit entry, the
  anomaly streak resets, and the next round is armed

### Requirement: A working stop is never an anomaly

A stop whose round grew the transcript beyond the bare-stop threshold, with the
audit token unconsumed, SHALL be treated as normal sailing: no anomaly, streak reset
to zero, the directive re-armed. An unreadable transcript SHALL be treated as
working.

#### Scenario: Work resets the streak

- **WHEN** a stop follows real tool activity with the token unconsumed and a prior
  anomaly on record
- **THEN** the anomaly count returns to zero and the directive stands again

### Requirement: A bare stop is redirected once, then ends the loop without a verdict

A stop with the token unconsumed and transcript growth at or under the bare-stop
threshold SHALL count one anomaly and re-arm behind the decline notice — the sole
place the silent exit is disclosed (a further unanswered directive ends the loop,
resumable). A second consecutive anomaly SHALL end the loop with an honest cause
that names no completion: the phase stays advising and /ploop:on can resume it.

#### Scenario: First silence discloses the exit

- **WHEN** a bare stop leaves the directive unanswered for the first time
- **THEN** the re-armed directive is prefixed by the decline notice naming the
  advisor's certification authority and the consequence of a second silence

#### Scenario: Second silence is the emergency stop

- **WHEN** a second consecutive anomaly occurs
- **THEN** the loop ends stating no completion verdict was issued, the phase stays
  advising, and the end notice directs a loop-log recap

### Requirement: A malfunctioned audit is retried once

A stop that finds the audit token consumed but no report file SHALL treat the run as
a malfunction, not a verdict: one anomaly, a retry notice directing a fresh summons,
the round advancing without freezing. A second consecutive anomaly ends the loop
with the malfunction cause.

#### Scenario: Empty advisor run retried

- **WHEN** the token was consumed and the report file is absent past the in-flight
  guard
- **THEN** the directive re-arms behind the retry notice and the round counter still
  advances

### Requirement: Per-stop narration is the flight recorder

The hook SHALL cut each round's transcript slice at every armed stop, and the
directive SHALL have the main agent run the narrator on it each round. The narration
read at the next stop SHALL be appended to the loop log as that round's entry; audit
reports SHALL be appended verbatim as Audit entries; a skipped narrator relay SHALL
degrade to an unnarrated round, never an anomaly. The advisor's action-history input
SHALL be the loop log followed by the freshest narration.

#### Scenario: Narration lands one stop behind

- **WHEN** a stop reads a narration file produced during the finished round
- **THEN** the log gains a Round entry numbered one behind the round in progress

#### Scenario: Skipped relay degrades

- **WHEN** a stop finds no narration file
- **THEN** no Round entry is written and no anomaly is recorded
