# ploop

English | [한국어](README.ko.md)

**An autonomous loop that drives long, complex missions to completion.**

ploop implements the **parallax loop** — an autonomous loop in which an isolated
advisor finds the regions Claude overlooked, round after round, and keeps the
work going until the mission is fully covered — on top of Claude Code's nested
subagents. It runs **safely on subscription plans**.

- Define the mission with Claude, then hand it off with `/ploop:launch`.
  - The handoff is a deliberate gate: it writes the mission spec to disk and
    launches the parallax loop. Use it for large missions, not trivial one-off edits.

### Why nested subagents

Spawning `claude -p` from a hook to drive such a loop is an automation pattern
that creates a separate session, which **risks account suspension on Claude
Pro/Max subscriptions**. ploop runs the advisor through the first-class `Agent`
tool (nested subagents) instead — a supported feature on every plan that shares
the main session's quota, so ploop runs **within subscription terms**.

### How it works

- [**Architecture (ARCHITECTURE.md)**](ARCHITECTURE.md) — the three-tier agent
  tree (main→advisor→narrator), the parallax loop, compaction resistance, and
  the decisions behind them.
- [**Theory (theory.md)**](theory.md) — the academic and industry evidence for
  why the parallax loop works.

### Prerequisite

ploop's durability hook runs via **uv**. Install it from
<https://docs.astral.sh/uv/getting-started/installation/>.

Without uv the tree still runs on prompt-based discipline — only the
hook-enforced advisor invocation is disabled.

### Cost

advisor runs on **1M-context Opus**; narrator runs on Sonnet. `main` runs the
mission directly and calls the advisor each round — a deliberate choice for
maximum reasoning, with heavy token use. For consistent results, running `main`
on `opus[1m]` is recommended. This is why ploop is per-mission opt-in —
trivial requests are handled by `main` directly, without a handoff.

### Install

```
claude plugin marketplace add clomia/claude-automata
claude plugin install ploop@claude-automata
```

### Update

```
claude plugin marketplace update claude-automata
claude plugin update ploop@claude-automata
```
