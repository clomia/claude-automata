<p align="center">
  <a href="https://claude-automata.clomia.com/"><img src="https://raw.githubusercontent.com/clomia/claude-automata/main/site/assets/banner.png" alt="claude-automata: 24/7 full self-driving for Claude Code" width="840"></a>
</p>

<p align="center"><strong>Your agent stops when it thinks it's done. This one stops when it's actually done.</strong></p>

<p align="center">
  An agent environment for Claude Code, modeled on human memory.<br>
  Hand it months of work and rest: it finishes in days.
</p>

<p align="center"><a href="https://claude-automata.clomia.com/"><strong>See more</strong></a></p>

<p align="center"><sub>This README is the summary. The site walks the whole system, animated.</sub></p>

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

Enter the following instruction in Claude Code:

```
Read https://raw.githubusercontent.com/clomia/claude-automata/refs/heads/main/INSTALL.md with curl -sSL and install claude-automata.
```

Your agent reads [INSTALL.md](https://github.com/clomia/claude-automata/blob/main/INSTALL.md) and installs claude-automata. Needs [Claude Code](https://claude.com/claude-code) and [uv](https://docs.astral.sh/uv/getting-started/installation/) on POSIX (macOS / Linux / WSL).

## Operating the loop

```
/ploop:define-mission          # an agent interviews you, interprets your intent, and writes the anchor
/ploop:launch [anchor text]    # hand it to the loop in a fresh session
```

Declare the mission done and a hook blocks the stop, summoning an independent advisor with access to the whole story; the loop ends only when the advisor has nothing left to say.

```
agent   › Mission accomplished. Stopping.
advisor › Not yet. The mobile layout was never measured. …resuming.
```

Six rounds later the advisor ends the turn. [Watch a full round on the site.](https://claude-automata.clomia.com/#advisor) The anchor survives every auto-compaction, and the loop fully complies with your subscription plan's terms of service.

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
/refine:code [focus] · /refine:docs [focus]
```

Repository-wide workflows that clear technical debt: code architecture and doc-to-code alignment. They touch only the representation layer and never change behavior. A run can sweep the whole codebase and take ten hours or more; watch it with `/workflows`.

---

<p align="center"><a href="https://claude-automata.clomia.com/"><strong>See more</strong></a></p>

Apache-2.0 · Recursive self-improvement: claude-automata is developed inside claude-automata. A Claude Code agent running this environment authored every contribution in this repository.
