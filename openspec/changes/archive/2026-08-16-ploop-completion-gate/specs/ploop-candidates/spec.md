# ploop-candidates — delta

The per-round delivery vehicle is now the standing round directive (the advisor
trigger's successor). The delivery behavior is unchanged.

## MODIFIED Requirements

### Requirement: One address, delivered by the loop machinery alone

The candidates queue address SHALL be authored by the loop machinery and never
inferred by a loop participant. Every round's directive SHALL re-deliver the address
to the main agent, so a compaction that erases the launch turn cannot strand the
queue.

#### Scenario: Address survives compaction

- **WHEN** the launch turn has been compacted away
- **THEN** the next round directive still carries the queue address

#### Scenario: The address is identical across deliveries

- **WHEN** the launch turn and any round's directive both name the queue
- **THEN** both name the same path
