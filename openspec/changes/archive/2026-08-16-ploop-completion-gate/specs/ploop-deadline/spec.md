# ploop-deadline — delta

The clock now informs both participants: convening is the main agent's decision, so
the status line rides the directive header as well as the advisor prompt, and an
expired deadline turns the directive into the convening order. Enforcement stays with
the advisor.

## MODIFIED Requirements

### Requirement: Every advisor round carries the deadline status

When a deadline is declared, the round directive SHALL carry one status line —
remaining time, elapsed time past expiry, or the unreadable raw value — rendered at
directive-assembly time in two positions: a header line for the main agent and the
same line inside the advisor call's prompt. When the status is expired, the
directive SHALL close the keep-working branch and direct the advisor call itself.
Judgment stays with the advisor — the loop machinery SHALL NOT pause, stop, or gate
the loop on the deadline.

#### Scenario: Deadline ahead

- **WHEN** the directive is assembled 2 hours 13 minutes before the deadline
- **THEN** `deadline: 2h 13m remaining` appears as a directive header line and
  inside the advisor prompt

#### Scenario: Deadline passed

- **WHEN** the directive is assembled after the deadline
- **THEN** the keep-working branch is absent and the directive orders the advisor
  call now

#### Scenario: Unreadable declaration

- **WHEN** the frontmatter's `deadline:` value cannot be parsed as an aware datetime
- **THEN** the directive surfaces `deadline: unreadable:` with the raw value and
  keeps the normal branches

#### Scenario: No deadline declared

- **WHEN** the anchor declares no deadline
- **THEN** the directive carries no deadline line and loop behavior is unchanged
