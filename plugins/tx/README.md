# tx — Git Transaction Workflow

Manage change as transactions. Open a branch as an integrity boundary, drive the
change through tx's own [OpenSpec](https://github.com/Fission-AI/OpenSpec)-backed
skills — plan, apply, an independent verify stage, archive — and squash-merge it
back into your base branch only when everything is clean, with guard hooks that
keep protected branches, stale transactions, and out-of-sync branches from
slipping through.

## The transaction model

**A transaction is the process of turning the prior state into an integral one.**

Whether the prior state was integral or not, by `/tx:close` the whole state
must be integral. Between `/tx:open` and `/tx:close`, it is allowed to be
non-integral.

Two declarations bound it:

- **`/tx:open`** declares: "I will make the whole state non-integral."
- **`/tx:close`** declares: "The whole state is now integral."

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

- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** — runs the guard hooks and tx commands.
- **Node.js >= 22** — tx drives the OpenSpec CLI through `npx` at a version
  pinned inside tx. Nothing to install or configure: no global package, no
  `openspec init` by hand, no upstream prompts. `/tx:open` seeds a repository
  that lacks the scaffold.
- **GitHub CLI (`gh`)** — `/tx:close` opens the PR and watches CI. The token
  needs the `workflow` scope: the seed commits a CI workflow file (and
  re-commits it when it drifts from the plugin's copy), and pushing it is
  rejected without that scope.

## Install

```
claude plugin install tx@claude-automata
claude plugin update tx@claude-automata
```

## Usage

```
/tx:open  [change description]   # cut a tx-* branch off base, seed, route the change
...plan & implement...           # tx:plan → tx:apply → verify stage (all tx-owned)
/tx:close                        # verify, archive, docs gate, squash-merge, settle every trace
```

- **`/tx:open`** — from the base branch with a clean tree, cuts `tx-<slug>` off
  the latest `origin/<base>`, seeds the repo when needed (OpenSpec scaffold +
  CI workflow + a best-effort server-side branch-protection attempt), then
  routes the change: `tx:plan` for anything structural, or skipping OpenSpec
  for trivial or docs-only changes.
- **`tx:plan`** — records the change as OpenSpec artifacts (proposal, delta
  specs, design, tasks) until `validate --strict` is green — except the
  class-wide `no deltas` error on delta-less changes, whose gate is task
  completion and CI. Unknowns are translated three
  ways: measure and record / adopt a reversible assumption and note it in
  design / halt the change and record why.
- **`tx:apply`** — implements task by task; when the change carries spec
  deltas it must then spawn **`tx:verify`** — an independent agent with a clean
  context that receives only the change-id and checks the implementation
  against the artifacts (completeness, correctness, consistency). Delta-less
  changes are gated by task completion and CI instead. The verdict gates every next step, and the repair happens while
  the implementation context is still live.
  Defects are repaired on the spot and verify is re-spawned until it passes;
  there is no retry cap — a transaction simply cannot close before it is
  integral.
- **`/tx:close`** — re-verifies when needed, archives the change through
  `tx:archive` (incomplete tasks block the close), rebases onto the latest
  `origin/<base>`, runs the docs-surface
  gate with a post-rebase conflict scan, opens the PR, waits for CI,
  squash-merges, and settles every trace: what the transaction brought into
  existence has landed in base or ceased to exist — anything of uncertain
  origin or holding unmerged changes is surfaced, never deleted. Idempotent
  throughout.

## The seed

On a repository without them, `/tx:open` plants — inside the transaction, so
they merge through the same gate:

- `openspec/` scaffold (`init --tools none`; no upstream prompts, ever).
- `.github/workflows/memory-check.yml` — CI that runs `openspec validate` and
  a docs-form-check (research filename years, provenance self-containment,
  research headers). The checks are form-only: CI proves document form, never prose meaning or
  code semantics — the verify stage and the repository's own tests carry the
  meaning. Frozen `openspec/changes/archive/` is judged only as files enter
  it through a PR — never re-judged against present-day rules, so adopting tx
  on a repository with prior history cannot wedge on that history. The file
  is seed-owned whole: any byte drift from the plugin's copy is overwritten
  on the next seed run.
- A **best-effort** server-side branch-protection attempt (PRs required, the
  seeded checks required, no force-push or deletion). The required-checks
  rule joins only once the seeded workflow is on the base branch and Actions
  is enabled — until then the rest of the ruleset holds active, and a later
  seed run converges it upward. Failure is reported in one line and never
  blocks. Where GitHub itself withholds rulesets (a private repository on a
  free plan) the seed reports `unsupported` — a settled state, not a
  failure — and converges upward if visibility or plan ever changes.
  Server-side rules make bypasses auditable rather than impossible —
  an admin token can still remove the gate.

## Guard hooks

Four hooks keep the invariants the skills rely on. Each degrades to a silent
no-op outside a git repository, without an `origin` remote, or when uv is missing.

| Hook | Event | What it does |
| ---- | ----- | ------------ |
| `branch-protect-block` | `PreToolUse(Edit\|Write\|NotebookEdit)` | Blocks edits to **tracked** files on the base branch — open a transaction first. Untracked, new, and gitignored targets are allowed. |
| `base-commit-block` | `PreToolUse(Bash)` | Blocks `git commit` into this repository while on the base branch — the other half of the same invariant (new files, shell-side edits). Commits into other repositories (`git -C <path>`) pass. |
| `branch-state-warn` | `SessionStart` (incl. after compaction) | Heals a missing `origin/HEAD` mirror, then surfaces branch state: on the protected branch, a transaction open > 24h, or `origin/<base>` ahead by unmerged PRs. |
| `git-sync` | `Stop` | On a `tx-*` branch, if `origin/<base>` has pulled ahead, blocks the stop and nudges a rebase — until the branch is synced. Defers while worktree-holding background work (a shell, subagent, or workflow) is in flight, so the rebase never rewrites files under it. Multi-session safe (flock, fetch throttle, announce dedupe). |

## Pause the sync nagging

A mid-flight rebase invalidates long-running analysis (large refactors, spec
sync). `/tx:git-sync-off` pauses the `git-sync` guard and the ahead warnings,
`/tx:git-sync-on` resumes them; both are idempotent. The pause is scoped
per-worktree and survives sessions — while it lingers, every session start
re-surfaces it. It never exempts `/tx:close` from rebasing.
