# tx — Git Transaction Workflow

Manage change as transactions. Open a branch as an integrity boundary, drive
[OpenSpec](https://github.com/Fission-AI/OpenSpec) through the change, and
squash-merge it back into your base branch only when everything is clean — with
guard hooks that keep protected branches, stale transactions, and out-of-sync
branches from slipping through.

## The transaction model

**A transaction is the process of turning the prior state into an integral one.**

Whether the prior state was integral or not, by `/tx:close` the implementation
and its documented intent must both be integral. Between `/tx:open` and
`/tx:close`, they are allowed to be non-integral.

Two declarations bound it:

- **`/tx:open`** declares: "I will make the implementation or its intent non-integral."
- **`/tx:close`** declares: "The implementation and its intent are now both integral."

A transaction is **not a unit of work — it is an integrity boundary.** It does
not depend on a Claude Code session or the nature of the task; it depends only on
integrity, and can be closed only once integrity is verified. One transaction may
span several tasks and sessions at once.

## The base branch

The base branch — the integration branch transactions open from and merge back
into — is **the repository's GitHub default branch**. There is nothing to
configure: tx reads it from `origin/HEAD`, the local mirror of the remote's
default branch. The SessionStart guard heals a missing mirror, and `/tx:open`
and `/tx:close` re-sync it (`git remote set-head origin --auto`) at every
transaction boundary, so changing the default branch on GitHub is picked up
automatically. Without an `origin` remote, tx does not apply and the guards
stay silent.

## Prerequisites

- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** — runs the guard hooks.
- **[OpenSpec](https://github.com/Fission-AI/OpenSpec)**, installed **skills-only** and initialized in the repo:
  ```bash
  npm install -g @fission-ai/openspec@latest   # requires Node.js >= 20.19.0
  openspec config profile                      # → Change delivery only → Skills only
  cd your-project && openspec init             # select Claude Code (already initialized? run: openspec update)
  ```
  **Skills only matters**: the default delivery also installs `/opsx:*` commands
  that duplicate the skills — tx drives OpenSpec through the skills alone
  (`openspec-explore`, `openspec-propose`, `openspec-apply-change`,
  `openspec-archive-change`), so the commands are dead weight. If OpenSpec is
  absent, `/tx:open` proceeds on the "skip openspec" path.
- **GitHub CLI (`gh`)** — `/tx:close` opens the PR and watches CI.

## Install

```
claude plugin install tx@claude-automata
claude plugin update tx@claude-automata
```

## Usage

```
/tx:open  [change description]   # cut a tx-* branch off base, plan the change
...work...                       # implement (e.g. the openspec-apply-change skill)
/tx:close                        # archive the change, then squash-merge to base
```

- **`/tx:open`** — from the base branch with a clean tree, cuts `tx-<slug>`
  off the latest `origin/<base>` and triggers the right OpenSpec entry: `explore`
  when the problem is fuzzy, `propose` when it is clear but structural, or skips
  OpenSpec for trivial changes.
- **`/tx:close`** — archives the OpenSpec change (syncing its delta specs),
  renames the branch to `<type>/<scope>/<slug>`, rebases onto `origin/<base>`,
  opens a PR, waits for CI, squash-merges, and cleans up. Idempotent throughout.

## Guard hooks

Three hooks keep the invariants the skills rely on. Each degrades to a silent
no-op outside a git repository, without an `origin` remote, or when uv is missing.

| Hook | Event | What it does |
| ---- | ----- | ------------ |
| `branch-protect-block` | `PreToolUse(Edit\|Write\|NotebookEdit)` | Blocks edits to **tracked** files on the base branch — open a transaction first. Untracked, new, and gitignored targets are allowed. |
| `branch-state-warn` | `SessionStart` (incl. after compaction) | Heals a missing `origin/HEAD` mirror, then surfaces branch state: on the protected branch, a transaction open > 24h, or `origin/<base>` ahead by unmerged PRs. |
| `git-sync` | `Stop` | On a `tx-*` branch, if `origin/<base>` has pulled ahead, blocks the stop and nudges a rebase — until the branch is synced. Defers while worktree-holding background work (a shell, subagent, or workflow) is in flight, so the rebase never rewrites files under it. Multi-session safe (flock, fetch throttle, announce dedupe). |

## Pause the sync nagging

A mid-flight rebase invalidates long-running analysis (large refactors, spec
sync). `/tx:git-sync-off` pauses the `git-sync` guard and the ahead warnings,
`/tx:git-sync-on` resumes them; both are idempotent. The pause is scoped
per-worktree and survives sessions — while it lingers, every session start
re-surfaces it.
