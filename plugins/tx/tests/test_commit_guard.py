import io
import json
import sys

import pytest
from conftest import run

from src import commit_guard


def feed(monkeypatch, repo, command: str) -> None:
    payload = {"tool_input": {"command": command}, "cwd": str(repo)}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))


def test_commit_targets_detection():
    assert commit_guard.commit_targets("git commit -m x") == [(None, False)]
    assert commit_guard.commit_targets("git add -A && git commit -m x") == [
        (None, False)
    ]
    assert commit_guard.commit_targets("GIT_TRACE=1 git -c user.name=t commit") == [
        (None, False)
    ]
    assert commit_guard.commit_targets("git -C /elsewhere commit -m x") == [
        ("/elsewhere", False)
    ]
    assert commit_guard.commit_targets("git -C '/elsewhere' commit") == [
        ("/elsewhere", False)
    ]
    assert commit_guard.commit_targets('echo "git commit"') == []
    assert commit_guard.commit_targets("git log && ls") == []
    assert commit_guard.commit_targets("echo hi & git commit") == [(None, False)]


def test_commit_targets_cd_flag():
    assert commit_guard.commit_targets("cd /x && git commit -m y") == [(None, True)]
    assert commit_guard.commit_targets("pushd /x; git commit") == [(None, True)]
    assert commit_guard.commit_targets("cd /x && git -C /y commit") == [("/y", True)]
    assert commit_guard.commit_targets("git commit -m y && cd /x") == [(None, False)]


def test_commit_targets_masks_quotes_and_heredocs():
    assert commit_guard.commit_targets('git commit -m "a && b"') == [(None, False)]
    assert commit_guard.commit_targets('echo "x && git commit"') == []
    assert commit_guard.commit_targets("cat > f <<'EOF'\ngit commit -m x\nEOF") == []
    assert commit_guard.commit_targets(
        "cat <<EOF\ngit commit\nEOF\ngit commit -m real"
    ) == [(None, False)]


def test_commit_targets_linear_on_hostile_options():
    """Hundreds of dash tokens parse instantly (the old regex backtracked
    exponentially); an unknown option's value ends the scan — that command
    is one git itself would refuse, so the miss is the accepted direction."""
    assert commit_guard.commit_targets("git " + "-c k=v " * 200 + "commit") == [
        (None, False)
    ]
    assert commit_guard.commit_targets("git " + "--verbose " * 200 + "status") == []
    assert commit_guard.commit_targets("git --opt val commit") == []


def test_block_commit_on_base(gitrepo, monkeypatch):
    feed(monkeypatch, gitrepo, "git commit -m msg")
    with pytest.raises(SystemExit) as exc:
        commit_guard.main()
    assert exc.value.code == 2


def test_allow_commit_on_tx_branch(gitrepo, monkeypatch):
    run(gitrepo, "checkout", "-q", "-b", "tx-work")
    feed(monkeypatch, gitrepo, "git commit -m msg")
    assert commit_guard.main() is None


def test_allow_non_commit_command(gitrepo, monkeypatch):
    feed(monkeypatch, gitrepo, "ls -la && git status")
    assert commit_guard.main() is None


def test_allow_commit_quoted_as_string(gitrepo, monkeypatch):
    feed(monkeypatch, gitrepo, 'echo "git commit"')
    assert commit_guard.main() is None


def test_allow_heredoc_body_on_base(gitrepo, monkeypatch):
    feed(monkeypatch, gitrepo, "cat > note.md <<'EOF'\nrun git commit here\nEOF")
    assert commit_guard.main() is None


def test_block_cd_then_commit(gitrepo, tmp_path, monkeypatch):
    """A cd makes the payload cwd meaningless for the commit's real target —
    fail-closed unless the commit names its own -C."""
    feed(monkeypatch, gitrepo, f"cd {tmp_path} && git commit -m msg")
    with pytest.raises(SystemExit) as exc:
        commit_guard.main()
    assert exc.value.code == 2


def test_allow_commit_in_other_repo(gitrepo, tmp_path, monkeypatch):
    """`-C <other repo>` passes even on the base branch name — scratch
    repositories are working memory, told apart by git-common-dir."""
    other = tmp_path / "scratch"
    other.mkdir()
    run(other, "init", "-q", "-b", "main")
    run(other, "config", "user.email", "t@example.com")
    run(other, "config", "user.name", "tester")
    run(other, "commit", "-q", "--allow-empty", "-m", "init")
    feed(monkeypatch, gitrepo, f"git -C {other} commit -m msg")
    assert commit_guard.main() is None


def test_block_commit_in_linked_worktree(gitrepo, tmp_path, monkeypatch):
    """A linked worktree shares the git common dir — the base branch checked
    out there is still this repository's base."""
    worktree = tmp_path / "wt"
    run(gitrepo, "worktree", "add", "--force", str(worktree), "main")
    feed(monkeypatch, gitrepo, f"git -C {worktree} commit -m msg")
    with pytest.raises(SystemExit) as exc:
        commit_guard.main()
    assert exc.value.code == 2


def test_block_unresolvable_target(gitrepo, monkeypatch):
    """A detected commit whose target cannot be resolved blocks (fail-closed)."""
    feed(monkeypatch, gitrepo, "git -C /no/such/dir commit -m msg")
    with pytest.raises(SystemExit) as exc:
        commit_guard.main()
    assert exc.value.code == 2


def test_no_guard_without_origin_head(gitrepo, monkeypatch):
    """An unresolvable base (no GitHub default branch mirror) disables the guard."""
    run(gitrepo, "symbolic-ref", "--delete", "refs/remotes/origin/HEAD")
    feed(monkeypatch, gitrepo, "git commit -m msg")
    assert commit_guard.main() is None
