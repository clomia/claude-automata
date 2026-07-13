"""Real temporary git repositories for the guard tests — no internal mocking."""

import subprocess
from pathlib import Path

import pytest


def run(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def make_origin_ahead(repo: Path, base: str, commits: int) -> None:
    """Point refs/remotes/origin/<base> `commits` ahead of HEAD (no real remote)."""
    head = run(repo, "rev-parse", "HEAD")
    for i in range(commits):
        run(repo, "commit", "--allow-empty", "-q", "-m", f"ahead-{i}")
    ahead = run(repo, "rev-parse", "HEAD")
    run(repo, "update-ref", f"refs/remotes/origin/{base}", ahead)
    run(repo, "reset", "-q", "--hard", head)


def set_origin_head(repo: Path, base: str) -> None:
    """Set refs/remotes/origin/HEAD -> origin/<base>, creating the tracking ref."""
    run(
        repo,
        "update-ref",
        f"refs/remotes/origin/{base}",
        run(repo, "rev-parse", "HEAD"),
    )
    run(repo, "symbolic-ref", "refs/remotes/origin/HEAD", f"refs/remotes/origin/{base}")


@pytest.fixture
def gitrepo(tmp_path, monkeypatch):
    """A git repo on `main` with one tracked file, checked out as the CWD."""
    root = tmp_path / "repo"
    root.mkdir()
    run(root, "init", "-q", "-b", "main")
    run(root, "config", "user.email", "t@example.com")
    run(root, "config", "user.name", "tester")
    run(root, "commit", "-q", "--allow-empty", "-m", "init")
    (root / "tracked.txt").write_text("x")
    run(root, "add", "tracked.txt")
    run(root, "commit", "-q", "-m", "add tracked")
    monkeypatch.chdir(root)
    monkeypatch.delenv("TXGIT_BASE_BRANCH", raising=False)
    return root
