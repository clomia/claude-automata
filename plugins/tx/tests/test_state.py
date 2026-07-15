import io
from datetime import datetime

from conftest import make_origin_ahead, run

from src import state


def feed(monkeypatch, raw: str = "") -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(raw))


def test_protected_branch_message_is_standalone():
    messages = state.build_messages("main", "main", paused=False)
    assert len(messages) == 1
    assert "protected" in messages[0] and "/tx:open" in messages[0]


def test_clean_tx_branch_has_no_messages(gitrepo):
    run(gitrepo, "checkout", "-q", "-b", "tx-solo")
    assert state.build_messages("tx-solo", "main", paused=False) == []


def test_base_ahead_message_on_tx_branch(gitrepo):
    run(gitrepo, "checkout", "-q", "-b", "tx-work")
    make_origin_ahead(gitrepo, "main", 2)
    joined = "\n".join(state.build_messages("tx-work", "main", paused=False))
    assert "2 PR(s) ahead" in joined


def test_pause_silences_only_the_ahead_warning(gitrepo):
    """Paused: the ahead nudge is replaced by the pause reminder; the
    protected-branch warning is untouched."""
    run(gitrepo, "checkout", "-q", "-b", "tx-work")
    make_origin_ahead(gitrepo, "main", 2)
    joined = "\n".join(state.build_messages("tx-work", "main", paused=True))
    assert "ahead" not in joined
    assert "/tx:git-sync-on" in joined
    assert state.build_messages("main", "main", paused=True) == [
        state.build_messages("main", "main", paused=False)[0]
    ]


def test_tx_open_time_parses_reflog(gitrepo):
    assert isinstance(state.tx_open_time("main"), datetime)


def test_warns_when_base_unresolvable_with_origin(gitrepo, monkeypatch, capsys):
    """origin exists but its default branch cannot be resolved -> actionable warn."""
    run(gitrepo, "symbolic-ref", "--delete", "refs/remotes/origin/HEAD")
    run(gitrepo, "remote", "add", "origin", str(gitrepo / "nonexistent.git"))
    feed(monkeypatch)
    state.main()
    assert "git remote set-head origin --auto" in capsys.readouterr().out


def test_silent_without_origin_remote(gitrepo, monkeypatch, capsys):
    """No origin remote -> tx does not apply -> no output at all, even paused."""
    run(gitrepo, "symbolic-ref", "--delete", "refs/remotes/origin/HEAD")
    (gitrepo / ".git" / "tx-pause").touch()
    feed(monkeypatch)
    state.main()
    assert capsys.readouterr().out == ""
