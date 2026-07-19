# claude-automata

English | [한국어](https://github.com/clomia/claude-automata/blob/main/README.ko.md)

Plugins that amplify Claude Code's autonomy.

## Getting Started

**[`uv` is required. If you don't have it, install it first.](https://docs.astral.sh/uv/getting-started/installation/)**
**Runs on POSIX (macOS / Linux / WSL).**

Set everything up in one command from your project root — settings prerequisites, marketplace and plugin registration, and the external CLI dependencies (gh · Node.js · repomix):

```
uvx claude-automata init
```

Re-running is safe (idempotent). To force the latest version, use `uvx claude-automata@latest init`.

To only add the marketplace without registering plugins:

```
claude plugin marketplace add clomia/claude-automata
```

# Ploop - Advisor Loop

> Install: `claude plugin install ploop@claude-automata`  
> Update: `claude plugin update ploop@claude-automata`  

ploop is an advisor loop built for long-running work that spans days.

- An independent advisor manages progress on the user's behalf.
  - The advisor finds what the main agent missed.
- The main agent is an orchestrator — it delegates work to agents and stays in command.
- It never loses context across repeated auto-compactions.
  - When a compaction occurs, the anchor is re-injected.
  - The advisor keeps the full context in files.
- It creates no separate sessions and uses only the official subagent path — safe on subscription plans.

The **anchor** is the file the loop is anchored to. It comes in two kinds.

- **Mission** (a goal) — receive requirements, process them, and finish once the goal is fully met. Write one with `/ploop:define-mission`.
- **Purpose** (a direction) — create requirements as you go and keep advancing, with no fixed end. Write one with `/ploop:define-purpose`.

### Usage

> Auto-Compact must be set to True.  
> For unattended runs, set `askUserQuestionTimeout` — an unanswered question then never parks the loop forever.

1. Write your anchor — `/ploop:define-mission` for a goal with clear completion criteria, `/ploop:define-purpose` for an ongoing direction.
2. In a fresh session, run `/ploop:launch [anchor]`.
   The loop rides the Stop hook's error behavior — whenever the agent stops, the hook blocks the stop and directs it to invoke the advisor.
3. The loop ends on its own when the advisor judges there is nothing left to advise — at which point the agent reads the log and recaps every round.
   To pause it, run `/ploop:off`; to pick it back up from where it stopped, run `/ploop:on` (interrupt with ESC first if a turn is running).
   `off` halts the loop quietly and preserves its state; `on` resumes the loop from that state.
   `on` is also a universal wake button for a long-running loop stalled by a mishap — an accidental ESC, an API error, a subscription session limit: it always resumes cleanly, except when the advisor ended the loop itself.
   Nothing else — mid-run instructions, answered questions, background-task notifications, ESC itself — stops the loop.

# Refine

> Install: `claude plugin install refine@claude-automata`  
> Update: `claude plugin update refine@claude-automata`  

refine is a family of large-scale workflows that eliminate the debt a repository accumulates.

All three skills work the same way — split into regions for parallel analysis, settle findings through a cross-examination assembly, and execute only the highest-ROI plans. Each run is a heavyweight workflow taking hours (3–12h).

- `/refine:code [focus]` — code architecture optimization. Filters antipatterns through consensus and applies only the highest-ROI refactors.
- `/refine:docs [focus]` — documentation architecture optimization. Every claim in every non-executable text (markdown, doc systems like openspec, comments and docstrings) is checked against the code and set right. Alignment is the precondition — converging duplicates, deleting dead docs, and keeping docs minimal is the optimum. Code is never modified — code defects are reported.
- `/refine:integrity [focus]` — integrity-boundary optimization. Hunts the reachable states the existing boundary (types, invariants, error definitions, tests) fails to contain, digs in from **"should this be defined as an error?"**, absorbs them into the boundary, and pins every defined behavior with tests and its rationale in docs and comments.

Leave the focus empty to target the whole codebase. Watch progress with `/workflows`.

# tx - Git Transaction Workflow

> Install: `claude plugin install tx@claude-automata`  
> Update: `claude plugin update tx@claude-automata`  

tx is a Git workflow that manages change as transactions.

- A transaction is an **integrity boundary** — everything from open to close is bound into one, and it can only close once verified integral.
- The whole path runs on tx's own skills: `/tx:open` cuts a `tx-*` branch off the base branch and seeds the repo, `tx:plan`·`tx:apply`·`tx:verify` drive the change, and `/tx:close` squash-merges to base behind the docs gate and CI. Guard hooks keep the base branch protected in between.

Prerequisites: uv, Node.js >= 20 (drives the pinned [OpenSpec](https://github.com/Fission-AI/OpenSpec) CLI through npx — nothing to install), GitHub CLI (`gh`).

### Usage

```
/tx:open  [change description]   # cut a tx-* branch off base, seed, route the change
...work...                       # tx:plan → tx:apply → tx:verify
/tx:close                        # verify, archive, docs gate, then squash-merge to base
```

For the full details — the transaction model, guard hooks, base-branch resolution, pausing sync — see the [plugin README](https://github.com/clomia/claude-automata/blob/main/plugins/tx/README.md).

# version-up-alert

> Nothing to install — every claude-automata plugin installs it as a dependency.

When a newer release of any installed claude-automata plugin ships, a one-line notice appears at session start.

- Compares the installed versions against what this repository publishes, and raises one notice naming every plugin that is behind. Update interactively in `/plugin`.
- Alert-only — it never swaps plugins out from under a running session. You choose when to update.
