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
    monkeypatch.setattr(
        cli.plugins,
        "ensure_plugins",
        lambda root: provision.Outcome("plugins", "ok", "all installed"),
    )

    assert cli.init() == 0
    data = json.loads((tmp_path / ".claude" / "settings.json").read_text())
    assert data["permissions"]["defaultMode"] == "bypassPermissions"
    assert data["enabledPlugins"]["tx@claude-automata"] is True
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("claude-automata ")
    assert "settings" in out and "gh" in out and "plugins" in out

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
    monkeypatch.setattr(
        cli.plugins,
        "ensure_plugins",
        lambda root: provision.Outcome("plugins", "deferred", plugins_note),
    )
    assert cli.init() == 1


plugins_note = "claude CLI not on PATH"


def test_plugin_convergence_runs_after_settings_write(tmp_path, monkeypatch):
    """The claude CLI re-writes settings during install; init's write must come
    first so the final file is the union of both."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli.provision, "ensure_all", lambda: [])
    monkeypatch.setattr(cli.provision, "gh_auth_note", lambda: None)
    monkeypatch.setattr(cli.provision, "path_note", lambda outcomes: None)
    settings_path = tmp_path / ".claude" / "settings.json"

    def install(root):
        data = json.loads(settings_path.read_text())
        assert data["enabledPlugins"]["tx@claude-automata"] is True
        data["enabledPlugins"]["extra@claude-automata"] = True
        settings_path.write_text(json.dumps(data))
        return provision.Outcome("plugins", "installed", "tx")

    monkeypatch.setattr(cli.plugins, "ensure_plugins", install)
    assert cli.init() == 0
    final = json.loads(settings_path.read_text())
    assert final["enabledPlugins"]["extra@claude-automata"] is True
    assert final["permissions"]["defaultMode"] == "bypassPermissions"


def test_init_succeeds_when_plugins_deferred(tmp_path, monkeypatch, capsys):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli.provision, "ensure_all", lambda: [])
    monkeypatch.setattr(cli.provision, "gh_auth_note", lambda: None)
    monkeypatch.setattr(cli.provision, "path_note", lambda outcomes: None)
    monkeypatch.setattr(
        cli.plugins,
        "ensure_plugins",
        lambda root: provision.Outcome("plugins", "deferred", plugins_note),
    )
    assert cli.init() == 0
    assert "deferred" in capsys.readouterr().out
