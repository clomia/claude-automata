# Installing claude-automata

You are the agent of the repository adopting claude-automata — an autonomous
agent environment where transactions are the only write gate into git-tracked
memory. This document defines the **installed state**, not the procedure. The
path there is yours to derive: it depends on this repository, and you are the
one who can see it.

## Installed state — when all of this is true, claude-automata is installed

- `uvx claude-automata init` converges: every line it prints reports a
  satisfied state, and nothing in its notes remains unresolved — settings
  picked up by a restarted session, `gh` authenticated. Its output is the
  oracle for prerequisites; do not re-derive what it already reports.
- The GitHub default branch is the branch this repository actually
  integrates into — transactions open from it and merge back into it.
- One transaction — opened with `/tx:open`, closed with `/tx:close` — has
  carried the adoption to the base branch: the seed's artifacts (openspec
  scaffold, memory-check CI, branch protection) merged through the
  transaction's own gate with green checks. In the merged state:
  - No tracked living document resolves a gitignored, untracked, or
    system-temp path. The facts those references carried survive — pointed
    at the tracked source that defines each path (a config key, an env var
    name) instead of the path literal.
  - `openspec validate --strict` under the plugin's pinned version passes
    for whatever specs this repository keeps.
  - Exactly one CI job reports the `openspec-validate` context. If this
    repository already validated openspec on its own, that job is gone and
    the seeded workflow carries the context name onward — configurations
    that required it keep their continuity.
- Pre-existing frozen history under `openspec/changes/archive/` is
  byte-identical to before the adoption, in place. It is judged only as
  pull requests bring files into it — editing or moving it revokes that
  exemption.
- The host harness — CLAUDE.md, rules, hooks, CI, documentation
  conventions — is intact except where the lines above required otherwise.
  claude-automata binds writes going forward; nothing is restructured
  retroactively.
- Every decision that belongs to this repository was made by its user, not
  silently by you: the integration branch; the fate of pre-existing specs
  (keep and repair, or delete — history is never transcribed into new
  specs); whether human review requirements coexist with agent self-merge
  (all rulesets apply together; the most restrictive wins).
- After the adoption merged: open PRs from before it are rebased so the new
  required checks can report, and a later `/tx:open` has reported the
  branch protection upgraded with required checks. Steady state: every seed
  line reads `present`.

Oracles outrank assumptions — including any assumption this document leaves
you with: init's output, the seed's one-line reports, `openspec validate`,
and CI are the state of record.
