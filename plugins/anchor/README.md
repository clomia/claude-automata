# Anchor

English | [한국어](README.ko.md)

**An autonomous loop that drives long, complex missions to completion — the evolution of parallax.**

Anchor finds the regions Claude overlooked, round after round, and keeps working
until the mission is fully covered. It reimplements [parallax](../parallax/)'s
mechanism on top of Claude Code's nested subagents, so it runs **safely on
subscription plans**.

- Define the mission with Claude, then hand it off with `/anchor:init`.
  - The handoff is a deliberate gate: it writes the mission spec to disk and
    launches the parallax loop. Use it for large missions, not trivial one-off edits.
- Check progress with `/anchor:log`.

### Relationship to parallax — what changed

parallax spawns `claude -p` from a Stop hook. That is an automation pattern that
creates a separate session, which **risked account suspension on Claude Pro/Max
subscriptions** — so it was confined to the Anthropic API plan, and the fear kept
everyone away.

Anchor reimplements the same parallax mechanism — an isolated advisor surfacing
unconsidered regions each round — through the first-class `Agent` tool (nested
subagents). Subagents are a supported feature on every plan and share the main
session's quota, so anchor runs **within subscription terms**. parallax had no
nested agents at the time, leaving `claude -p` the only option; that is no longer
true.

### How it works — [**Architecture (ARCHITECTURE.md)**](ARCHITECTURE.md)

The four-tier agent tree (main→anchor→advisor→narrator), the parallax loop,
compaction resistance, and the decisions behind them.

### Prerequisite

Anchor's durability hook runs via **uv**. Install it from
<https://docs.astral.sh/uv/getting-started/installation/>.

Without uv the tree still runs on prompt-based discipline — only the
hook-enforced advisor invocation is disabled.

### Cost

anchor and advisor run on **1M-context Opus**; narrator runs on Sonnet. The
mission unfolds across a deep tree — a deliberate choice for maximum reasoning,
with heavy token use. For a consistent tree, running `main` on `opus[1m]` is
recommended. This is why anchor is per-mission opt-in — trivial requests are
handled by `main` directly, without a handoff.

### Install

```
claude plugin marketplace add clomia/claude-automata
claude plugin install anchor@claude-automata
```

### Update

```
claude plugin marketplace update claude-automata
claude plugin update anchor@claude-automata
```
