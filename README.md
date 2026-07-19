# claude-automata

English | [한국어](https://github.com/clomia/claude-automata/blob/main/README.ko.md)

**An autonomous agent environment for Claude Code, modeled on human memory.** The loop holds the initiative around the clock, the user is one event type among many, and nothing is remembered except verified, git-tracked text. The structure exists so that days-long unattended work neither loses its intent nor lets unverified change contaminate the repository.

**[Landing page](https://clomia.github.io/claude-automata/)** — the memory-system visualization and the whole picture, in minutes. The design canons are [ARCHITECTURE.md](https://github.com/clomia/claude-automata/blob/main/ARCHITECTURE.md) (the ecosystem) and [MEMORY.md](https://github.com/clomia/claude-automata/blob/main/MEMORY.md) (the memory system).

| Plugin | Role |
|---|---|
| **ploop** | advisor loop — an autonomous loop for long work spanning days (working memory) |
| **tx** | Git transaction workflow — the only consolidation gate into long-term memory |
| **refine** | hours-long heavyweight workflows that eliminate repository debt (the re-grounding cycle) |
| **version-up-alert** | new-release notice — a shared dependency of every plugin |

## Getting Started

**[Claude Code](https://claude.com/claude-code) and [`uv`](https://docs.astral.sh/uv/getting-started/installation/) are required.**
**Runs on POSIX (macOS / Linux / WSL).**

From your project root:

```
uvx claude-automata init
```

One command converges everything — the settings prerequisites, marketplace registration with all four plugins, and the external CLI dependencies (gh · Node.js ≥ 20 · repomix) installed into your user area (no sudo, present tools skipped). Re-running is safe (idempotent). To force the latest version, use `uvx claude-automata@latest init`.

**What init actually writes** — this environment assumes unattended operation, and init merge-writes the following into `.claude/settings.json` (unrelated keys are preserved). Review the diff before you commit it:

- `permissions.defaultMode: "bypassPermissions"` — no approval prompts. The agent edits files and runs commands without asking first — adopt this in a repository where you accept that mode.
- `model: "opus[1m]"` — pinned model, 1M context
- `alwaysThinkingEnabled: true` · `autoCompactEnabled: true` · `autoMemoryEnabled: false`
- registers the claude-automata marketplace and enables all four plugins

`gh` authentication is never automated — if you are not logged in, init prints a `gh auth login` reminder.

## ploop — Advisor Loop

ploop is an advisor loop built for long-running work that spans days.

- An independent advisor finds, on the user's behalf, what the main agent missed in every round.
- The main agent is an orchestrator — it delegates work to agents and stays in command.
- It never loses context across repeated auto-compactions — the anchor is re-injected, and the advisor keeps the full context in files.
- It creates no separate sessions and uses only the official subagent path — safe on subscription plans.

The **anchor** is the file the loop is anchored to. It comes in two kinds.

- **Mission** (a goal) — receive requirements, process them, and finish once the goal is fully met. Write one with `/ploop:define-mission`.
- **Purpose** (a direction) — create requirements as you go and keep advancing, with no fixed end. Write one with `/ploop:define-purpose`.

### Usage

> Auto-Compact must be set to True.
> For unattended runs, set `askUserQuestionTimeout` — an unanswered question then never parks the loop forever.

1. Write your anchor — `/ploop:define-mission` or `/ploop:define-purpose`.
2. In a fresh session, run `/ploop:launch [anchor]`. The loop rides the Stop hook — whenever the agent stops, the hook blocks the stop and has the advisor summoned.
3. The loop ends on its own when the advisor judges there is nothing left to advise, and the agent recaps every round.
   To pause, run `/ploop:off`; to pick it back up, `/ploop:on` (interrupt with ESC first if a turn is running). `on` is a universal wake button — it revives a loop stalled by an accidental ESC, an API error, or a subscription session limit, and always resumes except when the advisor ended the loop itself. Nothing else — mid-run instructions, answered questions, background-task notifications — stops the loop.
4. To check on progress, run `/ploop:docent` in a **separate session in the same directory** — a read-only guide that answers from the loop's records and never touches the loop. Questions go to the docent; interventions (instructions, stopping) go straight to the loop session.

Design details: [plugins/ploop/ARCHITECTURE.md](https://github.com/clomia/claude-automata/blob/main/plugins/ploop/ARCHITECTURE.md)

## refine

refine is a family of large-scale workflows that eliminate the debt a repository accumulates.

All three skills work the same way — split into regions for parallel analysis, settle findings through a cross-examination assembly, and execute only the highest-ROI plans. Each run is a heavyweight workflow taking hours (3–12h).

- `/refine:code [focus]` — code architecture optimization. Filters antipatterns through consensus and applies only the highest-ROI refactors.
- `/refine:docs [focus]` — documentation architecture optimization. Every claim in every non-executable text is checked against the code and set right. Code is never modified — code defects are reported.
- `/refine:integrity [focus]` — integrity-boundary optimization. Hunts the reachable states the boundary fails to contain, digs in from **"should this be defined as an error?"**, absorbs them, and pins the result with tests and docs.

Leave the focus empty to target the whole codebase. Watch progress with `/workflows`.

## tx — Git Transaction Workflow

tx is a Git workflow that manages change as transactions.

A transaction is an **integrity boundary** — everything from open to close is bound into one, and it can only close once verified integral. Guard hooks keep the base branch protected in between.

```
/tx:open  [change description]   # cut a tx-* branch off base, seed, route the change
...work...                       # tx:plan → tx:apply → tx:verify
/tx:close                        # verify, archive, docs gate, then squash-merge to base
```

For the full details — the transaction model, guard hooks, base-branch resolution — see the [plugin README](https://github.com/clomia/claude-automata/blob/main/plugins/tx/README.md).

## version-up-alert

When a newer release of any installed claude-automata plugin ships, a one-line notice appears at session start. Alert-only — it never swaps plugins out from under a running session; you choose when to update. Every claude-automata plugin installs it as a dependency, so there is nothing to install.

---

MIT License · An independent open-source project, unaffiliated with Anthropic.
