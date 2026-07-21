"""The docs-form-check embedded in the seeded workflow, run against real repos.

The script is extracted from references/memory-check.yml so the seed-owned
artifact itself is the unit under test — no copy to drift.  Each repo ends on
a merge commit shaped like the CI checkout: HEAD^1 is the base head.
"""

import os
import subprocess
import sys
import textwrap
from pathlib import Path

from conftest import run

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SEED_WORKFLOW = PLUGIN_ROOT / "references" / "memory-check.yml"


def form_check_script() -> str:
    lines = SEED_WORKFLOW.read_text(encoding="utf-8").splitlines()
    start = next(
        i for i, line in enumerate(lines) if line.strip() == "python3 - <<'PY'"
    )
    end = next(i for i, line in enumerate(lines) if i > start and line.strip() == "PY")
    return textwrap.dedent("\n".join(lines[start + 1 : end]))


def form_check(repo: Path) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
    }
    return subprocess.run(
        [sys.executable, "-"],
        input=form_check_script(),
        capture_output=True,
        text=True,
        cwd=repo,
        env=env,
    )


def write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def seeded_repo(tmp_path: Path) -> Path:
    """One base commit: a gitignore, a frozen archive violation, a clean living doc."""
    repo = tmp_path / "repo"
    repo.mkdir()
    run(repo, "init", "-q", "-b", "main")
    run(repo, "config", "user.email", "t@t")
    run(repo, "config", "user.name", "t")
    write(repo, ".gitignore", "secret/\n")
    write(
        repo,
        "openspec/changes/archive/2020-01-01-old/design.md",
        "frozen `secret/key.txt`\n",
    )
    write(repo, "docs/live.md", "clean\n")
    run(repo, "add", "-A")
    run(repo, "commit", "-q", "-m", "base")
    return repo


def merge_pr(repo: Path, files: dict[str, str]) -> None:
    run(repo, "checkout", "-q", "-b", "pr")
    for rel, text in files.items():
        write(repo, rel, text)
    run(repo, "add", "-A")
    run(repo, "commit", "-q", "-m", "pr")
    run(repo, "checkout", "-q", "main")
    run(repo, "checkout", "-q", "-b", "merge-head")
    run(repo, "merge", "-q", "--no-ff", "pr", "-m", "merge")


def test_frozen_violation_does_not_block_unrelated_pr(tmp_path):
    repo = seeded_repo(tmp_path)
    merge_pr(repo, {"docs/note.md": "clean addition\n"})
    result = form_check(repo)
    assert result.returncode == 0, result.stdout + result.stderr


def test_entering_archive_content_is_checked(tmp_path):
    repo = seeded_repo(tmp_path)
    merge_pr(
        repo,
        {"openspec/changes/archive/2020-01-02-new/tasks.md": "backup `/tmp/x.json`\n"},
    )
    result = form_check(repo)
    assert result.returncode == 1
    assert "/tmp/x.json" in result.stdout


def test_living_surface_is_scanned_regardless_of_diff(tmp_path):
    repo = seeded_repo(tmp_path)
    write(repo, "docs/rot.md", "see `secret/key.txt`\n")
    run(repo, "add", "-A")
    run(repo, "commit", "-q", "-m", "rot")
    merge_pr(repo, {"docs/note.md": "clean\n"})
    result = form_check(repo)
    assert result.returncode == 1
    assert "docs/rot.md" in result.stdout


def test_unresolvable_diff_fails_loud(tmp_path):
    repo = seeded_repo(tmp_path)
    result = form_check(repo)
    assert result.returncode == 1
    assert "cannot resolve" in result.stderr
