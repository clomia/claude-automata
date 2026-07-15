import io
import json

import pytest

from src import pause, repo


def feed(monkeypatch, **payload):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))


def test_off_pauses_idempotently(gitrepo, monkeypatch):
    for _ in range(2):
        feed(monkeypatch, command_name="txgit:git-sync-off")
        pause.off()
        assert repo.sync_paused()


def test_on_resumes_idempotently(gitrepo, monkeypatch):
    feed(monkeypatch, command_name="txgit:git-sync-off")
    pause.off()
    for _ in range(2):
        feed(monkeypatch, command_name="txgit:git-sync-on")
        pause.on()
        assert not repo.sync_paused()


def test_outside_repo_blocks_expansion(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    feed(monkeypatch, command_name="txgit:git-sync-off")
    with pytest.raises(SystemExit) as exc:
        pause.off()
    assert exc.value.code == 0
    assert json.loads(capsys.readouterr().out)["decision"] == "block"


def test_foreign_command_is_ignored(gitrepo, monkeypatch):
    """The guard matches the full scoped name, so another plugin's
    :git-sync-off cannot toggle txgit's pause."""
    feed(monkeypatch, command_name="other:git-sync-off")
    with pytest.raises(SystemExit):
        pause.off()
    assert not repo.sync_paused()
