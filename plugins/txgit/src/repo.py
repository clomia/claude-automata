"""Shared git-repository queries for the txgit transaction guards.

A transaction lives on a `tx-*` branch cut from the repository's base branch —
the integration branch that transactions merge back into.  The guards resolve
that branch once, here, so the whole plugin agrees on it:

    TXGIT_BASE_BRANCH env override
      -> origin's default branch (refs/remotes/origin/HEAD)
      -> first of main / master / dev that exists locally
      -> "main"

Every helper degrades to a no-op value when git is unavailable or a query
fails, so a non-repository session or a missing prerequisite never breaks the
loop.
"""

import os
import re
import subprocess
from pathlib import Path

TX_BRANCH_RE = re.compile(r"^tx-")
BASE_BRANCH_ENV = "TXGIT_BASE_BRANCH"
BASE_FALLBACKS = ("main", "master", "dev")


def git(*args: str) -> str | None:
    """Run a git command; stripped stdout on success, None on any failure."""
    try:
        result = subprocess.run(
            ["git", *args], capture_output=True, text=True, check=False
        )
    except FileNotFoundError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def current_branch() -> str | None:
    """The checked-out branch name, or None outside a repository."""
    return git("rev-parse", "--abbrev-ref", "HEAD") or None


def is_tx_branch(branch: str) -> bool:
    return bool(TX_BRANCH_RE.match(branch))


def base_branch() -> str:
    """The integration branch transactions open from and merge back into."""
    override = os.environ.get(BASE_BRANCH_ENV)
    if override and override.strip():
        return override.strip()
    head = git("symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if head and head.startswith("origin/"):
        return head[len("origin/") :]
    for name in BASE_FALLBACKS:
        if git("rev-parse", "--verify", "--quiet", f"refs/heads/{name}") is not None:
            return name
    return BASE_FALLBACKS[0]


def git_dir() -> Path | None:
    out = git("rev-parse", "--absolute-git-dir")
    return Path(out) if out else None


def pause_marker() -> Path | None:
    """`<git-dir>/txgit-pause` — its presence silences the sync guards.

    A mid-flight rebase invalidates long-running analysis (large refactors, spec
    sync), so such work touches this marker to pause the nagging and removes it
    when done.  It lives in the git dir: never committed, scoped per-worktree.
    """
    gd = git_dir()
    return gd / "txgit-pause" if gd else None


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
