"""PreToolUse(Edit|Write) guard — block edits to tracked files on the base branch.

Invariant: the base branch (the GitHub default branch) holds only what merged
through a transaction, so its tracked files may not be edited in place — open a
transaction first.  Untracked targets stay allowed: paths outside the worktree,
gitignored paths, and not-yet-tracked new files.  A single
`git ls-files --error-unmatch` decides all three.  When the path or payload is
unclear the block stands (fail-closed) so the protection invariant holds.
This is a hot path: it reads only the local origin/HEAD mirror, never the
network; an unresolvable base disables the guard (SessionStart warns about it).
"""

import json
import sys

from src.repo import base_branch, current_branch, git


def target_path() -> str | None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError, OSError:
        return None
    tool_input = payload.get("tool_input", {})
    return tool_input.get("file_path") or tool_input.get("notebook_path") or None


def untracked(target: str) -> bool:
    """True only when the target is confirmed outside git tracking."""
    return git("ls-files", "--error-unmatch", "--", target) is None


def main() -> None:
    target = target_path()  # also drains stdin
    branch = current_branch()
    if branch is None or branch != base_branch():
        return

    if target is not None and untracked(target):
        return

    print(
        f"[branch-protect-block] '{branch}' is protected — open a transaction first (/tx:open).",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
