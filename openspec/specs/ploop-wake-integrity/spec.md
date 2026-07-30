# ploop-wake-integrity Specification

## Purpose
TBD - created by archiving change ploop-wakeless-shell-gate. Update Purpose after archive.
## Requirements
### Requirement: Wait commands classify by wake guarantee

The hook SHALL classify a shell command as one of: `mortal` (no unbounded sleep-loop —
includes commands with a bound marker such as `timeout N`, `seq`, `SECONDS`, `read -t`,
`--timeout`, a numeric counter comparison, or wait loops conditioned on process
existence such as `pgrep`/`kill -0`/`ps`), `file-condition` (an unbounded sleep-loop
whose condition is a file-state test: `[`/`[[`/`test` with `-s/-f/-e/-d/-r`), or
`unbounded` (any other unbounded sleep-loop). A command whose wait lives inside a
called script is opaque and SHALL classify as `mortal` (presume-mortal fail direction).

#### Scenario: The incident form is file-condition

- **WHEN** `until [ -s /t/x.output ]; do sleep 60; done; head -20 /t/x.output` is classified
- **THEN** the verdict is `file-condition`

#### Scenario: Bounded and process-conditioned waits are mortal

- **WHEN** `timeout 6000 bash -c 'until [ -s /x ]; do sleep 60; done'` or
  `until ! pgrep -f train.py; do sleep 30; done` is classified
- **THEN** the verdict is `mortal`

#### Scenario: A non-file unbounded poll is unbounded

- **WHEN** `until curl -sf localhost:8080/ready; do sleep 5; done` is classified
- **THEN** the verdict is `unbounded`

### Requirement: Launch-time wait gate in active-loop sessions

On PreToolUse for Bash in a session with an active loop, the hook SHALL deny a
`file-condition` command with a reason teaching the mortal forms (process-existence
wait, `timeout` bound), SHALL inject a warning as additional context for an `unbounded`
command without deciding permission, and SHALL stay silent for a `mortal` command.
Outside an active loop the gate SHALL stay silent regardless of command.

#### Scenario: File-condition wait is denied inside a loop

- **WHEN** the main agent launches `until [ -s /x ]; do sleep 60; done` while the loop is armed
- **THEN** the hook returns `permissionDecision: "deny"` with a reason naming the
  process-existence and `timeout` alternatives

#### Scenario: Unbounded wait is warned, not decided

- **WHEN** the main agent launches `until curl -sf $URL; do sleep 5; done` while the loop is armed
- **THEN** the hook returns only `additionalContext` (no `permissionDecision`)

#### Scenario: Outside a loop the gate is inert

- **WHEN** the same file-condition command is launched with no active marker
- **THEN** the hook exits 0 with no output

### Requirement: Stop into a wakeless state is blocked once, informed

At stop, when at least one shell gates the round, every gating shell classifies as
non-`mortal`, and the event carries no `session_crons`, the hook SHALL block the stop
(exit 2) with a notice naming each shell id and command — once per shell set. A repeat
stop with the same set SHALL fall through to ordinary shell gating (informed sleep is
honored). A set containing any `mortal` shell SHALL NOT trigger the prod (its exit
wakes the session). The prod SHALL never arm an advisor round.

#### Scenario: The incident path is caught at the transition

- **WHEN** a mortal shell and a file-condition shell gate the round, the mortal shell
  later exits, and the next stop leaves only the file-condition shell
- **THEN** that stop is blocked with the wakeless notice naming the surviving shell

#### Scenario: Stopping again with the same wakeless set is honored

- **WHEN** the agent stops again with the identical wakeless shell set already prodded
  and already gated
- **THEN** the hook exits 0

#### Scenario: A scheduled wakeup voids the hazard

- **WHEN** every gating shell is wakeless but `session_crons` is non-empty
- **THEN** no wakeless prod fires and ordinary shell gating applies

### Requirement: Only running shells gate the round

Shell entries SHALL gate the round only while their `status` is `running` (an absent
status counts as running). A terminal-status shell SHALL NOT defer the advisor.

#### Scenario: A completed shell left in the list does not park the loop

- **WHEN** the only background task is a shell with `status: "completed"`
- **THEN** the stop proceeds to ordinary round handling (the advisor can arm)

