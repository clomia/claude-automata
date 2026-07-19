<p align="center">
  <a href="https://clomia.github.io/claude-automata/"><img src="https://raw.githubusercontent.com/clomia/claude-automata/main/site/assets/banner.png" alt="claude-automata — runs for days, remembers only what's verified" width="840"></a>
</p>

<p align="center"><strong>Your agent stops when it <em>thinks</em> it's done. This one stops when it's actually done.</strong></p>

<p align="center">
  An autonomous agent environment for Claude Code, modeled on human memory.<br>
  An advisor audits every stop; one verified gate decides what gets remembered.
</p>

<p align="center"><a href="https://clomia.github.io/claude-automata/"><strong>▶ Watch the memory circuit run</strong></a></p>

<p align="center">
  <a href="https://pypi.org/project/claude-automata/"><img src="https://img.shields.io/pypi/v/claude-automata?style=flat&color=b25c28" alt="PyPI"></a>
  <a href="https://github.com/clomia/claude-automata/blob/main/LICENSE"><img src="https://img.shields.io/github/license/clomia/claude-automata?style=flat&color=3e6f5e" alt="MIT"></a>
</p>

English | [한국어](https://github.com/clomia/claude-automata/blob/main/README.ko.md)

---

Claude Code ends its turn the moment it believes it's finished, and forgets everything at the next compaction. claude-automata rebuilds it around the way memory actually works:

| Plugin | Memory role |
|---|---|
| **ploop** | working memory — a loop for work spanning days; every stop is audited by an independent advisor until nothing is left to surface |
| **tx** | consolidation — the only gate into memory: plan, independent verify, CI, squash merge |
| **refine** | re-grounding — hours-long workflows that re-verify old memory against the code |
| **version-up-alert** | update notice — one line at session start when a plugin is behind; alert-only, never swaps a running plugin; ships with the others |

Long-term memory isn't a database. It's the repository's own git-tracked text — recall is grep. Whatever never passes the gate dies with the loop, on purpose.

## Install

Needs [Claude Code](https://claude.com/claude-code) and [uv](https://docs.astral.sh/uv/getting-started/installation/), on POSIX (macOS / Linux / WSL). One command, from your project root:

```
uvx claude-automata init
```

Re-running is safe (idempotent). `uvx claude-automata@latest init` forces the newest release.

**What init actually writes** — this environment assumes unattended operation. Review the diff before you commit it:

- `permissions.defaultMode: "bypassPermissions"` — no approval prompts. The agent runs shell commands on your machine without asking first; the trust is host-level, not repo-level.
- `model: "opus[1m]"` — pinned model, 1M context
- `alwaysThinkingEnabled: true` · `autoCompactEnabled: true` · `autoMemoryEnabled: false`
- registers the `clomia/claude-automata` marketplace and enables all four plugins
- installs missing `gh`, Node.js ≥ 20, `repomix` into your user area — no sudo, present tools skipped, `gh auth login` stays yours

## Run a loop

```
/ploop:define-mission          # write the anchor — your intent, interviewed out of you
/ploop:launch [anchor text]    # hand it to the loop in a fresh session
```

The loop rides the Stop hook: whenever the agent stops, an independent advisor with a clean context inspects the round and surfaces what was missed. It ends only when the advisor has nothing left to say — not when the agent feels finished.

```
agent   › Mission accomplished. Stopping.
hook    › Stop blocked — summoning the advisor.
advisor › Not yet. The mobile layout was never measured. Two claims cite no source.
agent   › …resuming.
        ⟲ six rounds later
advisor › I have no further advice. Ending the turn.
```

*An illustrative exchange — the mechanics are real.* The anchor survives every auto-compaction. Safe on subscription plans — safe in mechanism, not in price: the loop shares your plan's quota, and multi-day runs spend it accordingly.

<details>
<summary><strong>Pause, resume, observe</strong></summary>

<br>

- Auto-Compact must be set to True. For unattended runs, set `askUserQuestionTimeout` — an unanswered question then never parks the loop forever.
- `/ploop:off` pauses; `/ploop:on` resumes — a universal wake button that also revives a loop stalled by an accidental ESC, an API error, or a session limit (interrupt with ESC first if a turn is running). Nothing else stops the loop.
- `/ploop:docent` in a **separate session, same directory** answers your questions from the loop's records without touching the loop. Questions go to the docent; interventions go straight to the loop session.

</details>

## Change as transactions

```
/tx:open  [description]   # cut a tx-* branch off base
...work...                # tx:plan → tx:apply → tx:verify
/tx:close                 # verify, docs gate, CI, then squash-merge
```

A transaction is an integrity boundary — it can only close once the implementation and its recorded intent are both verified. Guard hooks keep the base branch protected in between. This is the gate everything above flows through.

## Keep memory true

```
/refine:code [focus] · /refine:docs [focus] · /refine:integrity [focus]
```

Heavyweight multi-agent workflows (hours per run, 3–12h) that eliminate accumulated debt: code architecture, documentation truth, integrity boundaries. Findings settle through cross-examination into consensus; only the highest-ROI plans execute. The docs pass never modifies code — defects are reported. Empty focus targets the whole codebase; watch with `/workflows`.

---

<p align="center"><a href="https://clomia.github.io/claude-automata/"><strong>▶ Watch the memory circuit run</strong></a></p>

MIT License · An independent open-source project, unaffiliated with Anthropic. By design, every contribution to this repository is authored by Claude Code agents.
