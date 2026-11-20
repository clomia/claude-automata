## Purpose

An anchor may declare that its end is its own — reached by the anchor's own act or the operator's pause,
never certified by a loop agent. This capability governs that declaration and the loop it launches: one that
keeps every holding device of the advisor loop and runs neither loop agent.

## ADDED Requirements

### Requirement: The anchor's frontmatter declares its own end

The anchor's leading frontmatter block — where `deadline:` is read — SHALL accept the key `end:`, whose one
value is `own`, read from the anchor the launch recorded. An anchor without the key SHALL launch the advisor
loop, unchanged. Any other value SHALL block the launch with a reason naming the fix, changing no loop state
and delivering nothing: a declared kind the hook cannot read never arms the other kind.

#### Scenario: Own end declared

- **WHEN** `/ploop:launch` receives an anchor whose frontmatter holds `end: own`
- **THEN** the loop arms as an own-end loop

#### Scenario: Unreadable end

- **WHEN** the frontmatter holds `end:` with any value other than `own`
- **THEN** the launch is blocked with a reason naming `own` or the key's absence, no anchor, log or active
  marker is written, and the previous anchor's ledger and queue survive

#### Scenario: Key outside the frontmatter

- **WHEN** `end: own` appears only in the anchor's body
- **THEN** it is anchor prose, and the advisor loop launches

### Requirement: The launch says which loop it armed

A launch that arms the loop SHALL deliver in its turn the kind's notice, then the queue address. An advisor
loop's notice: the advisor judges completion and only its verdict ends the loop; every stop's directive
carries the narrator and advisor calls, convened at the main agent's judgment. An own-end loop's: no stop ends
it; the anchor says what does. Every re-anchoring after a compaction SHALL carry both ahead of the anchor,
and the launch skill body SHALL carry no notice of the kind.

#### Scenario: Advisor loop launched

- **WHEN** `/ploop:launch` arms an anchor without the key
- **THEN** the launch turn carries the advisor-loop notice, then the queue address

#### Scenario: Own-end loop launched

- **WHEN** `/ploop:launch` arms an anchor whose frontmatter holds `end: own`
- **THEN** the launch turn carries the own-end notice, which names neither loop agent, then the queue
  address

#### Scenario: Compaction re-anchors the kind

- **WHEN** an armed loop's context is compacted
- **THEN** the re-anchoring carries the notice of its kind and the queue address, then the anchor

#### Scenario: A long anchor keeps the notice in view

- **WHEN** the re-anchoring runs past the harness's 10,000-character cap on a hook's context, which then
  delivers only its first 2,000 characters as a preview
- **THEN** the notice and the queue address fall within those 2,000 characters

### Requirement: An own-end loop holds every stop

Past the background gate, an armed own-end loop SHALL block (exit 2) every stop with the hold — the
directive less its narrator and advisor parts: re-read the anchor, hold the state against it; work remains,
keep working now; nothing remains, do what the anchor says comes next; the queue address. A deadline's
status SHALL head it, inert at expiry. Stops SHALL neither write loop state nor end the loop;
`/ploop:off` or the session's end does. Gate, heartbeat and guard SHALL be the advisor loop's.

#### Scenario: Bare stops are held, never ended

- **WHEN** an armed own-end loop stops again and again with nothing in the background and no tool work
- **THEN** every stop is answered with the hold, the loop stays armed, and no ledger, round slice or audit
  token exists

#### Scenario: A stray in-flight marker does not silence the hold

- **WHEN** an armed own-end loop stops with an advisor in-flight marker left over (an advisor run before the
  key was read, a missed SubagentStop)
- **THEN** the stop is answered with the hold, and the marker is left as it was

#### Scenario: Background work waits

- **WHEN** an armed own-end loop stops with a subagent, a workflow or a running shell in the background
- **THEN** the stop exits 0 with no output

#### Scenario: A deadline is information

- **WHEN** the own-end anchor's deadline has expired
- **THEN** the hold opens with the expired status and still directs keeping on while work remains

### Requirement: No loop agent runs in an own-end loop

While an own-end loop is armed, a call of the narrator or of the advisor SHALL be refused with the reason that
the loop's anchor declares its own end, and the refusal SHALL write no audit token or in-flight marker. In an
advisor loop, and outside an armed loop, the gate SHALL be as it was: the narrator ungated, the advisor
admitted on the round's audit token.

#### Scenario: Both agents refused

- **WHEN** the main agent of an armed own-end loop calls `ploop:narrator` or `ploop:advisor`
- **THEN** the call is refused with the own-end reason, and no audit token or in-flight marker is written

#### Scenario: The advisor loop's gate is unchanged

- **WHEN** the main agent of an armed advisor loop calls `ploop:narrator`
- **THEN** the call passes
