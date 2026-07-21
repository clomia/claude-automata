import json

from claude_automata import plugins
from claude_automata.settings import MARKETPLACE, plugin_names


def fake_run_claude(calls, root, listed=None, fail_install=()):
    """run_claude stand-in — `listed` names appear installed at project scope
    (None = the list probe itself fails); installs in `fail_install` error."""

    def run(args, cwd):
        calls.append(args)
        if args[:2] == ["plugin", "list"]:
            if listed is None:
                return None, "probe down"
            entries = [
                {
                    "id": f"{name}@{MARKETPLACE}",
                    "scope": "project",
                    "projectPath": str(root),
                }
                for name in listed
            ]
            return json.dumps(entries), ""
        if args[:2] == ["plugin", "install"]:
            name = args[2].split("@")[0]
            return (None, "HTTP 500") if name in fail_install else ("ok", "")
        return "ok", ""

    return run


def converge(monkeypatch, tmp_path, **fake_kwargs):
    calls = []
    monkeypatch.setattr(plugins.shutil, "which", lambda name: "/usr/bin/claude")
    monkeypatch.setattr(
        plugins, "run_claude", fake_run_claude(calls, tmp_path, **fake_kwargs)
    )
    return plugins.ensure_plugins(tmp_path), calls


def installs(calls):
    return [
        args[2].split("@")[0] for args in calls if args[:2] == ["plugin", "install"]
    ]


def test_fresh_repo_installs_everything(monkeypatch, tmp_path):
    outcome, calls = converge(monkeypatch, tmp_path, listed=[])
    assert outcome.status == "installed"
    assert installs(calls) == plugin_names()
    assert all(name in outcome.note for name in plugin_names())
    marketplace = [args for args in calls if args[:2] == ["plugin", "marketplace"]]
    assert [args[2] for args in marketplace] == ["add", "update"]


def test_rerun_with_all_installed_is_satisfied(monkeypatch, tmp_path):
    outcome, calls = converge(monkeypatch, tmp_path, listed=plugin_names())
    assert outcome.status == "ok"
    assert installs(calls) == []


def test_list_probe_failure_falls_through_to_full_install(monkeypatch, tmp_path):
    outcome, calls = converge(monkeypatch, tmp_path, listed=None)
    assert outcome.status == "installed"
    assert installs(calls) == plugin_names()


def test_list_shape_drift_falls_through_to_full_install(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(plugins.shutil, "which", lambda name: "/usr/bin/claude")
    drifted = fake_run_claude(calls, tmp_path, listed=[])

    def run(args, cwd):
        if args[:2] == ["plugin", "list"]:
            calls.append(args)
            return '{"plugins": [null]}', ""
        return drifted(args, cwd)

    monkeypatch.setattr(plugins, "run_claude", run)
    outcome = plugins.ensure_plugins(tmp_path)
    assert outcome.status == "installed"
    assert installs(calls) == plugin_names()


def test_partial_failure_continues_and_reports(monkeypatch, tmp_path):
    failing = plugin_names()[0]
    outcome, calls = converge(monkeypatch, tmp_path, listed=[], fail_install={failing})
    assert outcome.status == "failed"
    assert failing in outcome.note and "HTTP 500" in outcome.note
    assert installs(calls) == plugin_names()


def test_missing_claude_cli_defers(monkeypatch, tmp_path):
    monkeypatch.setattr(plugins.shutil, "which", lambda name: None)
    outcome = plugins.ensure_plugins(tmp_path)
    assert outcome.status == "deferred"
    assert "/reload-plugins" in outcome.note


def test_marketplace_failure_reports_reason(monkeypatch, tmp_path):
    monkeypatch.setattr(plugins.shutil, "which", lambda name: "/usr/bin/claude")
    monkeypatch.setattr(plugins, "run_claude", lambda args, cwd: (None, "no network"))
    outcome = plugins.ensure_plugins(tmp_path)
    assert outcome.status == "failed"
    assert "no network" in outcome.note
