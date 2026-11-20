## MODIFIED Requirements

### Requirement: Every armed stop injects the standing round directive

Every stop of an armed advisor loop — a loop whose anchor does not declare its own end (`ploop-own-end`) —
that passes the background and in-flight gates SHALL be blocked (exit 2) with the standing directive: a
verbatim narrator call for the round just sliced, the direction to re-read the anchor and keep working while
work remains, and a verbatim advisor call to run only on a completion judgment or a wanted audit. The
directive SHALL state that only the advisor can certify completion and SHALL NOT disclose the silent-exit
failsafe.

#### Scenario: Fresh launch arms without judging

- **WHEN** the first stop after /ploop:launch fires
- **THEN** the directive is injected with both verbatim calls, the audit token is
  armed, and no anomaly is recorded regardless of transcript size or token absence

#### Scenario: The steady-state directive keeps the audit as the only visible exit

- **WHEN** any directive is injected outside an anomalous re-arm
- **THEN** it contains no mention of the loop ending on unanswered directives

### Requirement: Per-stop narration is the flight recorder

The hook SHALL cut each round's transcript slice at every armed stop of an advisor loop, and the directive
SHALL have the main agent run the narrator on it each round. The narration read at the next stop SHALL be
appended to the loop log as that round's entry; audit reports SHALL be appended verbatim as Audit entries; a
skipped narrator relay SHALL degrade to an unnarrated round, never an anomaly. The advisor's action-history
input SHALL be the loop log followed by the freshest narration.

#### Scenario: Narration lands one stop behind

- **WHEN** a stop reads a narration file produced during the finished round
- **THEN** the log gains a Round entry numbered one behind the round in progress

#### Scenario: Skipped relay degrades

- **WHEN** a stop finds no narration file
- **THEN** no Round entry is written and no anomaly is recorded
