import json
import subprocess

from claude_automata import cli, provision


def test_init_outside_git_repo_writes_nothing(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert cli.init() == 1
    assert not (tmp_path / ".claude").exists()
    assert "not inside a git repository" in capsys.readouterr().err


def test_init_writes_settings_and_reports(tmp_path, monkeypatch, capsys):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        cli.provision,
        "ensure_all",
        lambda: [provision.Outcome("gh", "ok", "/usr/bin/gh")],
    )
    monkeypatch.setattr(cli.provision, "gh_auth_note", lambda: None)
    monkeypatch.setattr(cli.provision, "path_note", lambda outcomes: None)

    assert cli.init() == 0
    data = json.loads((tmp_path / ".claude" / "settings.json").read_text())
    assert data["permissions"]["defaultMode"] == "bypassPermissions"
    assert data["enabledPlugins"]["tx@claude-automata"] is True
    out = capsys.readouterr().out
    assert "settings" in out and "gh" in out

    # rerun converges: nothing else to write, same content
    before = (tmp_path / ".claude" / "settings.json").read_text()
    assert cli.init() == 0
    assert (tmp_path / ".claude" / "settings.json").read_text() == before


def test_init_fails_when_provisioning_fails(tmp_path, monkeypatch, capsys):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        cli.provision,
        "ensure_all",
        lambda: [provision.Outcome("node", "failed", "boom")],
    )
    monkeypatch.setattr(cli.provision, "gh_auth_note", lambda: None)
    monkeypatch.setattr(cli.provision, "path_note", lambda outcomes: None)
    assert cli.init() == 1
