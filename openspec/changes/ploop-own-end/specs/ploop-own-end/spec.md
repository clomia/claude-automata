## Purpose

An anchor may declare that its end is its own — reached by the anchor's own act or the operator's pause,
never certified by a loop agent. This capability governs that declaration and the loop it launches: one that
keeps every holding device of the advisor loop and runs neither loop agent.

## ADDED Requirements

### Requirement: The anchor's frontmatter declares its own end

The anchor's leading frontmatter block — the block `deadline:` is read from — SHALL accept the key `end:`,
whose one value is `own`. The kind SHALL be read from the anchor the launch recorded, so it holds for the
loop's whole life. An anchor without the key SHALL launch the advisor loop, unchanged. Any other value SHALL
block the launch with a reason that names the fix, and the blocked launch SHALL change no loop state and
deliver nothing: a declared kind the hook cannot read never arms the other kind.

#### Scenario: Own end declared

- **WHEN** `/ploop:launch` receives an anchor whose frontmatter holds `end: own`
- **THEN** the loop arms as an own-end loop

#### Scenario: Unreadable end

- **WHEN** the frontmatter holds `end:` with any value other than `own`
- **THEN** the launch is blocked with a reason naming `own` or the key's absence, and no anchor, log or
  active marker is written

#### Scenario: Key outside the frontmatter

- **WHEN** `end: own` appears only in the anchor's body
- **THEN** it is anchor prose, and the advisor loop launches

### Requirement: The launch says which loop it armed

A launch that arms the loop SHALL deliver in the same turn, ahead of the candidates queue address, the notice
of the loop's kind: for an advisor loop, that the advisor judges mission completion and the loop ends only by
its verdict, and that every stop's directive carries the narrator and advisor calls, convened on the main
agent's judgment; for an own-end loop, that no stop ends it and the anchor says what does. Every
re-anchoring after a compaction SHALL carry the same notice and address after the anchor. The launch skill
body SHALL carry no notice of the loop's kind — static text cannot be true of both.

#### Scenario: Advisor loop launched

- **WHEN** `/ploop:launch` arms an anchor without the key
- **THEN** the launch turn carries the advisor-loop notice, then the queue address

#### Scenario: Own-end loop launched

- **WHEN** `/ploop:launch` arms an anchor whose frontmatter holds `end: own`
- **THEN** the launch turn carries the own-end notice, which names neither loop agent, then the queue
  address

#### Scenario: Compaction re-anchors the kind

- **WHEN** an armed loop's context is compacted
- **THEN** the re-anchoring carries the anchor, then the notice of its kind and the queue address

### Requirement: An own-end loop holds every stop

Every stop of an armed own-end loop that passes the background gate SHALL be blocked (exit 2) with the hold —
the standing directive with everything of the narrator and the advisor taken out: re-read the anchor and hold
the state against it; work remains, keep working now; nothing remains, do what the anchor says comes next;
the candidates queue address. A declared deadline's status line SHALL open the hold, and nothing SHALL act on
its expiry. The stop SHALL write no loop state — no round slice, no ledger, no audit token — and no count of
stops SHALL end the loop: it ends only by `/ploop:off` or the session's end. The background gate, the
heartbeat and the unattended guard SHALL be those of the advisor loop.

#### Scenario: Bare stops are held, never ended

- **WHEN** an armed own-end loop stops again and again with nothing in the background and no tool work
- **THEN** every stop is answered with the hold, the loop stays armed, and no ledger, round slice or audit
  token exists

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
