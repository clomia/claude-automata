"""Shared git-repository queries for the tx transaction guards.

A transaction lives on a `tx-*` branch cut from the repository's base branch —
the integration branch that transactions merge back into.  The base branch is
the repository's GitHub default branch, read from its local mirror
`refs/remotes/origin/HEAD`.  The mirror is healed by `set_origin_head` (one
network round-trip) at SessionStart when it is missing, and re-synced by the
open/close skills through `print_base`; the hot-path guards only read locally.

Every helper degrades to a no-op value when git is unavailable or a query
fails, so a non-repository session or a missing prerequisite never breaks the
loop.
"""

import re
import subprocess
import sys
from pathlib import Path

TX_BRANCH_RE = re.compile(r"^tx-")
ORIGIN_HEAD_REMEDY = "git remote set-head origin --auto"


def git(*args: str) -> str | None:
    """Run a git command; stripped stdout on success, None on any failure."""
    try:
        result = subprocess.run(
            ["git", *args], capture_output=True, text=True, check=False
        )
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def current_branch() -> str | None:
    """The checked-out branch name — `"HEAD"` when detached, None outside a repository."""
    return git("rev-parse", "--abbrev-ref", "HEAD") or None


def is_tx_branch(branch: str) -> bool:
    return bool(TX_BRANCH_RE.match(branch))


def has_origin() -> bool:
    """Whether an `origin` remote is configured — without one, tx does not apply."""
    return git("remote", "get-url", "origin") is not None


def base_branch() -> str | None:
    """The GitHub default branch, as mirrored by origin/HEAD; None when unset."""
    head = git("symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if head and head.startswith("origin/"):
        return head[len("origin/") :]
    return None


def set_origin_head() -> bool:
    """Sync origin/HEAD to the remote's default branch (network, one round-trip)."""
    return git("remote", "set-head", "origin", "--auto") is not None


def origin_head_remedy() -> str:
    """The remedy that heals origin/HEAD in this clone — narrow-refspec clones widen first."""
    lines = (git("config", "--get-all", "remote.origin.fetch") or "").splitlines()
    if not lines or "+refs/heads/*:refs/remotes/origin/*" in lines:
        return ORIGIN_HEAD_REMEDY
    return f"git remote set-branches origin '*' && git fetch origin && {ORIGIN_HEAD_REMEDY}"


def resolve_base_or_exit() -> str:
    """Resolve the base branch or exit 1 with the standard guidance."""
    set_origin_head()
    base = base_branch()
    if base is None:
        print(
            "Cannot resolve the GitHub default branch (origin/HEAD). "
            f"Ensure an `origin` remote exists, then run: {origin_head_remedy()}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return base


def print_base() -> None:
    """CLI for the close skill — resolve and print the base branch.

    Re-syncs the mirror first, so a default-branch change on GitHub is picked
    up at every transaction boundary.  Exit 1 with guidance when unresolvable
    or when a rebase is in progress.
    """
    if rebase_in_progress_branch():
        print(
            "A rebase is in progress — `git rebase --continue` (or --abort) first.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    print(resolve_base_or_exit())


def rebase_cmd(base: str) -> str:
    """The one sync remedy every guard recommends."""
    return f"git fetch origin {base} && git rebase origin/{base}"


def ahead_notice(ahead: int, base: str) -> str:
    """The one drift fact every guard reports (first-parent commits = merged PRs)."""
    return f"origin/{base} is {ahead} PR(s) ahead"


def git_dir() -> Path | None:
    out = git("rev-parse", "--absolute-git-dir")
    return Path(out) if out else None


def rebase_in_progress_branch() -> str | None:
    """The branch a paused rebase started from — None when no rebase is in progress."""
    gd = git_dir()
    if gd is None:
        return None
    for kind in ("rebase-merge", "rebase-apply"):
        marker = gd / kind
        if marker.is_dir():
            try:
                ref = (marker / "head-name").read_text(encoding="utf-8").strip()
            except OSError:
                ref = ""
            return ref.removeprefix("refs/heads/") or "(unknown)"
    return None


def pause_marker() -> Path | None:
    """`<git-dir>/tx-pause` — its presence silences the sync nudges.

    /tx:git-sync-off touches it, /tx:git-sync-on removes it (pause.py),
    shielding long-running analysis that a mid-flight rebase would invalidate.
    It lives in the git dir: never committed, scoped per-worktree.
    """
    gd = git_dir()
    return gd / "tx-pause" if gd else None


def sync_paused() -> bool:
    marker = pause_marker()
    return bool(marker and marker.exists())


def fetch_base(base: str) -> bool:
    return git("fetch", "--quiet", "origin", base) is not None


def base_ahead_count(base: str) -> int | None:
    """First-parent commits on origin/<base> not yet in HEAD (= unmerged PRs).

    None when it cannot be determined (no remote-tracking ref, git failure).
    """
    out = git("rev-list", "--count", "--first-parent", f"origin/{base}", "^HEAD")
    if out is None:
        return None
    try:
        return int(out)
    except ValueError:
        return None
