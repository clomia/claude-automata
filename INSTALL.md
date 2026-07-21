# Installing claude-automata

You are the agent of the repository adopting claude-automata, an autonomous
agent environment where transactions are the only write gate into git-tracked
memory. This document defines the **installed state**, not the procedure. The
path there is yours to derive: it depends on this repository, and you are the
one who can see it.

## Installed state

When every line below holds, claude-automata is installed.

- `uvx claude-automata@latest init` has converged, with `uv` on PATH for it
  to run at all: every line it prints reports a satisfied state, and `gh` is
  authenticated. `@latest` is part of the command — a bare `claude-automata`
  reuses whatever version uvx cached on this machine, and stale caches are
  real (an unrelated prototype once occupied this PyPI name). Init's first
  line is its own version: output that doesn't start with a version line is
  the stale cache talking, not init. Its output is the oracle for
  prerequisites, so act on its notes instead of re-deriving them. Init also
  installs the marketplace and every plugin into the local plugin cache
  through the claude CLI, so the restart below loads them whole; when that
  CLI is not on PATH the plugins line reads `deferred` and the next session
  start installs them instead.
- The repository's `.claude/settings.json` carries the environment this
  autonomy needs: `permissions.defaultMode` is `"bypassPermissions"` (the
  agent stops asking before it acts), `model` is `"opus[1m]"`,
  `alwaysThinkingEnabled` `true`, `autoCompactEnabled` `true`,
  `autoMemoryEnabled` `false`, and the `clomia/claude-automata` marketplace
  is registered with its plugins enabled. That is what adopting this
  environment means. Init writes these values, and a cautious human reads
  them here before delegating the install.
- The session has restarted since init ran. Claude Code loads the installed
  plugins and the new `model`/`bypassPermissions` only at startup, so in the
  session that ran init the tx skills (`/tx:open` and the rest) do not exist
  yet. You can neither restart yourself nor carry this context across the
  restart, so tell the user to restart Claude Code and then re-send the same
  install request. The returning session re-reads this document, finds init
  already converged, and runs the transaction below. If the tx skills are
  still missing after the restart — the deferred path installs lazily at
  startup, and that startup can miss registering skills — run
  `/reload-plugins` once and re-check; that is the whole repair.
- The GitHub default branch is the branch this repository actually
  integrates into, the one transactions open from and merge back into.
- In that restarted session, one transaction (opened with `/tx:open`, closed
  with `/tx:close`) has carried the adoption to the base branch: the seed's
  artifacts (openspec scaffold, memory-check CI) merged through the
  transaction's own gate with green checks. Branch protection is the seed's
  server-side, best-effort companion: where GitHub offers rulesets to this
  repository it lands and later converges upward; where GitHub withholds
  them (a private repository on a free plan) the seed reports `unsupported`,
  and that line is satisfied as-is — never a reason to change the
  repository's visibility or plan. In the merged state:
  - No tracked living document resolves a gitignored, untracked, or
    system-temp path. The facts those references carried survive, now
    pointed at the tracked source that defines each path (a config key, an
    env var name) instead of the path literal.
  - `openspec validate --strict` under the plugin's pinned version passes
    for whatever specs this repository keeps.
  - Exactly one CI job reports the `openspec-validate` context. If this
    repository already validated openspec on its own, that job is gone and
    the seeded memory-check workflow carries the context name onward, so
    configurations that required it keep their continuity.
- Pre-existing frozen history under `openspec/changes/archive/` is
  byte-identical to before the adoption, in place. It is judged only as
  pull requests bring files into it, and editing or moving it revokes that
  exemption.
- The host harness (CLAUDE.md, rules, hooks, CI, documentation conventions)
  is intact except where the lines above required otherwise. claude-automata
  binds writes going forward; nothing is restructured retroactively.
- Every decision that belongs to this repository was made by its user, not
  silently by you: the integration branch; the fate of pre-existing specs
  (keep and repair, or delete, but history is never transcribed into new
  specs); whether human review requirements coexist with agent self-merge
  (all rulesets apply together, and the most restrictive wins).
- After the adoption merged: open PRs from before it are rebased so the new
  checks can report, and — where the protection landed — a later `/tx:open`
  has reported it upgraded with required checks. Steady state: every seed
  line reads `present`, or `unsupported` where that is the protection
  line's settled report.

Oracles outrank assumptions, including any this document leaves you with.
Init's output, the seed's one-line reports, `openspec validate`, and CI are
the state of record.
