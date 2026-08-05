## Purpose

The candidates queue is where the main agent stages facts and terms for promotion into the
repo. This capability governs how that queue's address reaches the loop participants, so the
queue the main agent writes is always the queue the loop machinery reads.

## ADDED Requirements

### Requirement: The launch that arms the loop delivers the queue address

A `/ploop:launch` that arms the loop SHALL deliver this session's candidates queue path to
the main agent in the same turn as the launch instructions, so the instruction to stage
candidates never arrives without its referent. A launch whose expansion is blocked SHALL
deliver no path — the blocked turn carries only its reason.

#### Scenario: Loop armed

- **WHEN** `/ploop:launch <anchor>` arms the loop
- **THEN** the same turn carries the session's candidates queue path

#### Scenario: Launch blocked

- **WHEN** the launch is blocked (a loop is already armed, the anchor is empty, or a
  prerequisite is unmet)
- **THEN** no queue path is delivered

#### Scenario: Candidate found before the first stop

- **WHEN** the main agent stages a candidate during the round that precedes the first
  advisor summons
- **THEN** it lands in the queue the loop machinery owns, so that queue reads as non-empty
  at the first summons and its drain directive is reachable at every termination

### Requirement: One address, delivered by the loop machinery alone

The candidates queue address SHALL be authored by the loop machinery and never inferred by
a loop participant. Every round's advisor trigger SHALL re-deliver the address to the main
agent, so a compaction that erases the launch turn cannot strand the queue.

#### Scenario: Address survives compaction

- **WHEN** the launch turn has been compacted away
- **THEN** the next advisor trigger still carries the queue address

#### Scenario: The address is identical across deliveries

- **WHEN** the launch turn and any round's trigger both name the queue
- **THEN** both name the same path
