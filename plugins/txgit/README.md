# txgit — Git Transaction Workflow

Manage change as transactions. Open a branch as an integrity boundary, drive
[OpenSpec](https://github.com/Fission-AI/OpenSpec) through the change, and
squash-merge it back into your base branch only when everything is clean — with
guard hooks that keep protected branches, stale transactions, and out-of-sync
branches from slipping through.

## The transaction model

**A transaction is the process of turning the prior state into an integral one.**

Whether the prior state was integral or not, by `tx-close` the implementation
and its documented intent must both be integral. Between `tx-open` and
`tx-close`, they are allowed to be non-integral.

Two declarations bound it:

- **`tx-open`** declares: "I will make the implementation or its intent non-integral."
- **`tx-close`** declares: "The implementation and its intent are now both integral."

A transaction is **not a unit of work — it is an integrity boundary.** It does
not depend on a Claude Code session or the nature of the task; it depends only on
integrity, and can be closed only once integrity is verified. One transaction may
span several tasks and sessions at once.

## Prerequisites

- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** — runs the guard hooks.
- **[OpenSpec](https://github.com/Fission-AI/OpenSpec)**, installed and initialized in the repo:
  ```bash
  npm install -g @fission-ai/openspec@latest   # requires Node.js >= 20.19.0
  cd your-project && openspec init             # installs the openspec-* skills
  ```
  `tx-open` triggers OpenSpec's official skills (`openspec-explore`,
  `openspec-propose`) and `tx-close` archives the change
  (`openspec-archive-change`). txgit assumes these skills are present; if OpenSpec
  is absent, `tx-open` proceeds on the "skip openspec" path.
- **GitHub CLI (`gh`)** — `tx-close` opens the PR and watches CI.

## Install

```
claude plugin install txgit@claude-automata
claude plugin update txgit@claude-automata
```

## Usage

```
/txgit:tx-open  [change description]   # cut a tx-* branch off base, plan the change
...work...                             # implement (e.g. /opsx:apply)
/txgit:tx-close                        # archive the change, then squash-merge to base
```

- **`/txgit:tx-open`** — from the base branch with a clean tree, cuts `tx-<slug>`
  off the latest `origin/<base>` and triggers the right OpenSpec entry: `explore`
  when the problem is fuzzy, `propose` when it is clear but structural, or skips
  OpenSpec for trivial changes.
- **`/txgit:tx-close`** — archives the OpenSpec change (syncing its delta specs),
  renames the branch to `<type>/<scope>/<slug>`, rebases onto `origin/<base>`,
  opens a PR, waits for CI, squash-merges, and cleans up. Idempotent throughout.

## Guard hooks

Three hooks keep the invariants the skills rely on. Each degrades to a silent
no-op outside a git repository or when uv is missing.

| Hook | Event | What it does |
| ---- | ----- | ------------ |
| `branch-protect-block` | `PreToolUse(Edit\|Write\|NotebookEdit)` | Blocks edits to **tracked** files on the base branch — open a transaction first. Untracked, new, and gitignored targets are allowed. |
| `branch-state-warn` | `SessionStart` | Surfaces branch state: on the protected branch, a transaction open > 24h, or `origin/<base>` ahead by unmerged PRs. |
| `git-sync` | `Stop` | On a `tx-*` branch, if `origin/<base>` has pulled ahead, blocks the stop and nudges a rebase — until the branch is synced. Multi-session safe (flock, fetch throttle, announce dedupe). |

## Configuration

- **Base branch.** The integration branch is resolved as `TXGIT_BASE_BRANCH` →
  origin's default branch (`refs/remotes/origin/HEAD`) → the first of
  `main`/`master`/`dev` that exists → `main`. Set `TXGIT_BASE_BRANCH` to pin it
  (e.g. a GitFlow `dev`).
- **Pause the sync nagging.** A mid-flight rebase invalidates long-running
  analysis (large refactors, spec sync). `/txgit:git-sync-off` pauses the
  `git-sync` guard and the ahead warnings, `/txgit:git-sync-on` resumes them;
  both are idempotent. The pause is scoped per-worktree and survives sessions —
  while it lingers, every session start re-surfaces it.
