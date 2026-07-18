import pytest
from conftest import make_origin_ahead, mirror_origin_head, run

from src import repo


def test_is_tx_branch():
    assert repo.is_tx_branch("tx-foo")
    assert not repo.is_tx_branch("main")
    assert not repo.is_tx_branch("feature/tx-thing")


def test_base_branch_reads_origin_head(gitrepo):
    assert repo.base_branch() == "main"
    mirror_origin_head(gitrepo, "integration")
    assert repo.base_branch() == "integration"


def test_base_branch_none_without_origin_head(gitrepo):
    run(gitrepo, "symbolic-ref", "--delete", "refs/remotes/origin/HEAD")
    assert repo.base_branch() is None


def test_set_origin_head_syncs_mirror_from_remote(gitrepo, tmp_path, capsys):
    """The full chain against a real (file) remote: no mirror -> set_origin_head
    -> base_branch reads the remote's default branch; print_base prints it."""
    origin = tmp_path / "origin.git"
    run(gitrepo, "clone", "-q", "--bare", ".", str(origin))
    run(gitrepo, "remote", "add", "origin", str(origin))
    run(gitrepo, "symbolic-ref", "--delete", "refs/remotes/origin/HEAD")
    assert repo.base_branch() is None
    assert repo.set_origin_head()
    assert repo.base_branch() == "main"
    repo.print_base()
    assert capsys.readouterr().out.strip() == "main"


def test_origin_head_remedy_widens_narrow_refspec(gitrepo, tmp_path):
    """A --single-branch clone's refspec starves set-head; the remedy widens first."""
    run(gitrepo, "remote", "add", "origin", str(tmp_path / "o.git"))
    run(
        gitrepo,
        "config",
        "remote.origin.fetch",
        "+refs/heads/dev:refs/remotes/origin/dev",
    )
    assert "set-branches" in repo.origin_head_remedy()


def test_origin_head_remedy_plain_by_default(gitrepo, tmp_path):
    assert repo.origin_head_remedy() == repo.ORIGIN_HEAD_REMEDY  # no origin config
    run(gitrepo, "remote", "add", "origin", str(tmp_path / "o.git"))
    assert repo.origin_head_remedy() == repo.ORIGIN_HEAD_REMEDY  # wildcard refspec


def test_print_base_fails_fast_when_unresolvable(gitrepo, capsys):
    """No origin remote: exit 1 with guidance on stderr, nothing on stdout."""
    run(gitrepo, "symbolic-ref", "--delete", "refs/remotes/origin/HEAD")
    with pytest.raises(SystemExit) as exc:
        repo.print_base()
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "git remote set-head origin --auto" in captured.err


def test_print_base_rejects_mid_rebase(gitrepo, capsys):
    (gitrepo / ".git" / "rebase-merge").mkdir()
    with pytest.raises(SystemExit) as exc:
        repo.print_base()
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "rebase is in progress" in captured.err


def test_has_origin(gitrepo, tmp_path):
    assert not repo.has_origin()
    run(gitrepo, "remote", "add", "origin", str(tmp_path / "o.git"))
    assert repo.has_origin()


def test_current_branch_tracks_checkout(gitrepo):
    assert repo.current_branch() == "main"
    run(gitrepo, "checkout", "-q", "-b", "tx-demo")
    assert repo.current_branch() == "tx-demo"


def test_base_ahead_count(gitrepo):
    assert repo.base_ahead_count("main") == 0
    make_origin_ahead(gitrepo, "main", 2)
    assert repo.base_ahead_count("main") == 2
    assert repo.base_ahead_count("nonexistent") is None


def test_pause_marker_gates_sync(gitrepo):
    assert not repo.sync_paused()
    marker = repo.pause_marker()
    assert marker is not None
    marker.touch()
    assert repo.sync_paused()
