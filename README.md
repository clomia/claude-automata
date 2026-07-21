<p align="center">
  <a href="https://claude-automata.clomia.com/"><img src="https://raw.githubusercontent.com/clomia/claude-automata/main/site/assets/banner.png" alt="claude-automata: 24/7 full self-driving for Claude Code" width="840"></a>
</p>

<p align="center"><strong>Your agent stops when it thinks it's done. This one stops when it's actually done.</strong></p>

<p align="center">
  An agent environment for Claude Code, modeled on human memory.<br>
  Hand it months of work and rest: it finishes in days.
</p>

<p align="center"><a href="https://claude-automata.clomia.com/"><strong>▶ Watch the memory circuit run</strong></a></p>

<p align="center">
  <a href="https://pypi.org/project/claude-automata/"><img src="https://img.shields.io/pypi/v/claude-automata?style=flat&color=f54e00" alt="PyPI"></a>
  <a href="https://github.com/clomia/claude-automata/blob/main/LICENSE"><img src="https://img.shields.io/pypi/l/claude-automata?style=flat&color=447e48" alt="License"></a>
</p>

English | [한국어](https://github.com/clomia/claude-automata/blob/main/README.ko.md)

---

Claude Code ends its turn the moment it believes it's finished, and loses the detail at the next compaction. claude-automata rebuilds it around the way human memory works:

| Plugin | Memory role |
|---|---|
| **ploop** | working memory: a single session sails autonomously for days; an independent advisor audits every stop |
| **tx** | consolidation: the screening gate into long-term memory (independent verify, CI, squash merge) |
| **refine** | re-grounding: large-scale workflows that eliminate technical debt |

Long-term memory is the repository's own git-tracked text, not a database. Recall is grep. Whatever never passes the gate dies with the loop, on purpose.

## Getting started

Installation is agent work — like everything else here. Paste this into Claude Code, inside the repository to adopt:

```
Read https://github.com/clomia/claude-automata/blob/main/INSTALL.md and install claude-automata in this repository.
```

Your agent reads [INSTALL.md](https://github.com/clomia/claude-automata/blob/main/INSTALL.md) — the installed state, and exactly what it writes to your settings — and converges the repository to it. Needs [Claude Code](https://claude.com/claude-code) and [uv](https://docs.astral.sh/uv/getting-started/installation/) on POSIX (macOS / Linux / WSL).

## Operating the loop

```
/ploop:define-mission          # an agent interviews you, interprets your intent, and writes the anchor
/ploop:launch [anchor text]    # hand it to the loop in a fresh session
```

Declare it done and a hook blocks the stop, summoning the advisor: an independent metacognition with access to the whole story. The loop ends when the advisor has nothing left to say.

```
agent   › Mission accomplished. Stopping.
hook    › Stop blocked. Summoning the advisor.
advisor › Not yet. The mobile layout was never measured. Two claims cite no source.
agent   › …resuming.
        ⟲ six rounds later
advisor › I have no further advice. Ending the turn.
```

*An illustrative exchange: this is what ploop provides. The authority to end the loop rests with the advisor.* The anchor survives every auto-compaction. Safe on subscription plans (safe in mechanism, not in price): the loop shares your plan's quota, and a multi-day run spends days of it.

<details>
<summary><strong>Pause, resume, observe</strong></summary>

<br>

- init sets Auto-Compact; keep it on. For unattended runs, set `askUserQuestionTimeout` so an unanswered question can't park the loop.
- `/ploop:off` pauses the loop. `/ploop:on` resumes or restores it, even after an accidental ESC, an API error, or a session limit (interrupt with ESC first if a turn is running). Nothing else stops the loop.
- `/ploop:docent` reports the loop's progress. Run it in a **separate session, same directory**: questions go to the docent, interventions go straight to the loop session.

</details>

## Change as transactions

Agents drive tx on their own. Every change lands as one verified, CI-green squash merge behind an integrity boundary, and tx blocks writes to the base branch in between. You review merged results, not work in progress.

## Keep the repository lean

```
/refine:code [focus] · /refine:docs [focus] · /refine:integrity [focus]
```

Large-scale workflows that eliminate technical debt: `/refine:code` optimizes the code architecture, `/refine:docs` aligns documentation with the code, `/refine:integrity` verifies logical integrity. They sweep the whole repository, so a run can take ten hours or more. Empty focus targets the whole codebase; watch with `/workflows`.

---

<p align="center"><a href="https://claude-automata.clomia.com/"><strong>▶ Watch the memory circuit run</strong></a></p>

Apache-2.0 · Recursive self-improvement: claude-automata is developed inside claude-automata. A Claude Code agent running this environment authored every contribution in this repository.
