# ploop-deadline Specification

## Purpose
TBD - created by archiving change ploop-deadline. Update Purpose after archive.
## Requirements
### Requirement: Anchor frontmatter declares the mission deadline

The anchor text SHALL support a leading `---` frontmatter block whose `deadline:` key
holds an ISO 8601 datetime with a timezone offset. A value that fails to parse or
lacks a timezone SHALL be treated as unreadable rather than silently ignored. An
anchor without frontmatter or without the key declares no deadline.

#### Scenario: Valid declaration

- WHEN the anchor begins with a `---` block containing `deadline: 2026-08-04T22:00+09:00`
- THEN the loop holds an aware deadline for that mission

#### Scenario: Timezone missing

- WHEN the frontmatter holds `deadline: 2026-08-04T22:00`
- THEN the deadline is unreadable and its raw value is surfaced, not dropped

#### Scenario: No declaration

- WHEN the anchor has no frontmatter block or no `deadline:` key inside one
- THEN no deadline exists and no deadline output is produced

#### Scenario: Key outside frontmatter

- WHEN `deadline:` appears only in the anchor body, outside the leading `---` block
- THEN it is anchor prose, not a declaration

### Requirement: Every advisor round carries the deadline status

When a deadline is declared, the advisor-summoning trigger SHALL include one status
line inside the advisor's prompt, rendered at trigger-assembly time: remaining time
before the deadline, elapsed time past it, or the unreadable raw value. Judgment
stays with the advisor — the loop machinery SHALL NOT pause, stop, or gate the loop
on the deadline.

#### Scenario: Deadline ahead

- WHEN the trigger is assembled 2 hours 13 minutes before the deadline
- THEN the advisor prompt contains `deadline: 2h 13m remaining`

#### Scenario: Deadline passed

- WHEN the trigger is assembled 23 minutes after the deadline
- THEN the advisor prompt contains `deadline: expired 23m ago`

#### Scenario: Unreadable declaration

- WHEN the frontmatter's `deadline:` value cannot be parsed as an aware datetime
- THEN the advisor prompt surfaces `deadline: unreadable:` with the raw value

#### Scenario: No deadline declared

- WHEN the anchor declares no deadline
- THEN the trigger carries no deadline line and loop behavior is unchanged

### Requirement: Deadline semantics live in the advisor instruction

The advisor instruction SHALL name the deadline semantics in its judgment section:
pace the mission to finish inside the remaining time, and treat an expired deadline
as sufficient cause to end the turn.

#### Scenario: Expired deadline reaches judgment

- WHEN the advisor reads a trigger whose deadline status says expired
- THEN its instruction licenses returning the termination token for that cause alone

