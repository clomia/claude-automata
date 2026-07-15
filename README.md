# claude-automata

English | [한국어](README.ko.md)

Plugins that amplify Claude Code's autonomy.

## Getting Started

**[`uv` is required. If you don't have it, install it first.](https://docs.astral.sh/uv/getting-started/installation/)**

Add this repository to the marketplace:

```
claude plugin marketplace add clomia/claude-automata
```

# Ploop - Advisor Loop

> Install: `claude plugin install ploop@claude-automata`  
> Update: `claude plugin update ploop@claude-automata`  

ploop is an advisor loop built for long-running work that spans days.

- An independent advisor manages progress on the user's behalf.
  - The advisor finds what the main agent missed.
- It never loses context across repeated auto-compactions.
  - When a compaction occurs, the anchor is re-injected.
  - The advisor keeps the full context in files.
- It creates no separate sessions and uses only the official subagent path — safe on subscription plans.

The **anchor** is the file the loop is anchored to. It comes in two kinds.

- **Mission** (a goal) — receive requirements, process them, and finish once the goal is fully met. Write one with `/ploop:define-mission`.
- **Purpose** (a direction) — create requirements as you go and keep advancing, with no fixed end. Write one with `/ploop:define-purpose`.

### Usage

> Auto-Compact must be set to True.

1. Write your anchor — `/ploop:define-mission` for a clear goal, `/ploop:define-purpose` for an ongoing direction.
2. In a fresh session, run `/ploop:launch [anchor]`.
   The loop rides the Stop hook's error behavior — whenever the agent stops, the hook blocks the stop and directs it to invoke the advisor.
3. The loop ends on its own when the advisor judges there is nothing left to advise — at which point the agent reads the log and recaps every round.
   To pause it, run `/ploop:off`; to pick it back up from where it stopped, run `/ploop:on` (interrupt with ESC first if a turn is running).
   `off` halts the loop quietly and preserves its state; `on` resumes the loop from that state.
   `on` is also the one way to revive a long-running loop stalled by a mishap — an accidental ESC, an API error, a subscription session limit: it always resumes cleanly, except when the advisor ended the loop itself.
   Nothing else — mid-run instructions, answered questions, background-task notifications, ESC itself — stops the loop.

# Refine Architecture

> Install: `claude plugin install refine-architecture@claude-automata`  
> Update: `claude plugin update refine-architecture@claude-automata`  

refine-architecture is a large-scale workflow that optimizes code architecture.

Usage:
```
/refine-architecture:refine-architecture [focus area]
```

Leave the focus area empty to target the whole codebase.  
Watch progress with `/workflows`.

# txgit - Git Transaction Workflow

> Install: `claude plugin install txgit@claude-automata`  
> Update: `claude plugin update txgit@claude-automata`  

txgit is a Git workflow that manages change as transactions.

- A transaction is not a unit of work — it is an **integrity boundary**. Everything from tx-open to tx-close is bound into one.
- `/txgit:tx-open` cuts a `tx-*` branch off your base branch and plans the change with [OpenSpec](https://github.com/Fission-AI/OpenSpec).
- `/txgit:tx-close` archives the OpenSpec change and squash-merges to the base branch once CI passes.
- Three guard hooks keep edits off protected branches, flag stale transactions, and stop out-of-sync branches.

Prerequisites: uv, [OpenSpec](https://github.com/Fission-AI/OpenSpec) (installed and `openspec init`-ed), GitHub CLI (`gh`).

### Usage

```
/txgit:tx-open  [change description]   # cut a tx-* branch off base, plan with OpenSpec
...work...                             # implement (e.g. /opsx:apply)
/txgit:tx-close                        # archive the change, squash-merge to base
```

For the full details — the transaction model, guard hooks, base-branch config, pausing sync — see the [plugin README](plugins/txgit/README.md).
