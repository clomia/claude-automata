"""Tests for the marketplace-wide updater — version math, both version readers,
and the end-to-end emit/cooldown/clear behavior of the hook entry point."""

import io
import json
import time
from types import SimpleNamespace

from src import updater


def test_is_newer_strict_and_robust():
    assert updater.is_newer("0.6.0", "0.5.0") is True
    assert updater.is_newer("0.5.0", "0.5.0") is False
    assert updater.is_newer("0.5.0", "0.6.0") is False
    assert updater.is_newer("0.6.0", "unknown") is False


def test_outdated_reports_only_installed_and_behind():
    remote = {"a": "2.0.0", "b": "1.0.0", "c": "9.9.9"}
    local = {"b": "1.0.0", "a": "1.0.0", "d": "1.0.0"}
    assert updater.outdated(remote, local) == ["a 1.0.0 > 2.0.0"]


def test_build_message_names_marketplace_and_points_at_plugin():
    message = updater.build_message(["a 1.0.0 > 2.0.0", "b 1.0.0 > 3.0.0"])
    assert "Claude-automata can now be updated." in message
    assert "[a 1.0.0 > 2.0.0] [b 1.0.0 > 3.0.0]" in message
    assert "/plugin" in message


def test_fetch_remote_versions_joins_sources_and_skips_bad_manifests(monkeypatch):
    documents = {
        f"{updater.RAW_ROOT}/.claude-plugin/marketplace.json": {
            "plugins": [
                {"name": "ploop", "source": "./plugins/ploop"},
                {"name": "broken", "source": "./plugins/broken"},
                "not-an-entry",
            ]
        },
        f"{updater.RAW_ROOT}/plugins/ploop/.claude-plugin/plugin.json": {
            "version": "1.0.0"
        },
        f"{updater.RAW_ROOT}/plugins/broken/.claude-plugin/plugin.json": None,
    }
    monkeypatch.setattr(updater, "http_json", documents.get)
    assert updater.fetch_remote_versions() == {"ploop": "1.0.0"}


def test_fetch_remote_versions_none_when_listing_unreachable(monkeypatch):
    monkeypatch.setattr(updater, "http_json", lambda url: None)
    assert updater.fetch_remote_versions() is None


def cli_result(payload: object, returncode: int = 0) -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=json.dumps(payload))


def test_installed_versions_scopes_to_session_and_keeps_oldest(monkeypatch):
    here = "/work/here"
    listing = [
        {
            "id": "ploop@claude-automata",
            "version": "0.5.0",
            "enabled": True,
            "scope": "local",
            "projectPath": here,
        },
        {
            "id": "ploop@claude-automata",
            "version": "0.4.0",
            "enabled": True,
            "scope": "project",
            "projectPath": "/work/./here",
        },
        {
            "id": "ploop@claude-automata",
            "version": "0.1.0",
            "enabled": True,
            "scope": "project",
            "projectPath": "/work/elsewhere",
        },
        {
            "id": "user@claude-automata",
            "version": "2.0.0",
            "enabled": True,
            "scope": "user",
            "projectPath": None,
        },
        {
            "id": "off@claude-automata",
            "version": "1.0.0",
            "enabled": False,
            "scope": "local",
            "projectPath": here,
        },
        {
            "id": "other@another-market",
            "version": "1.0.0",
            "enabled": True,
            "scope": "local",
            "projectPath": here,
        },
        {
            "id": "raw@claude-automata",
            "version": "unknown",
            "enabled": True,
            "scope": "local",
            "projectPath": here,
        },
    ]
    monkeypatch.setattr(updater.subprocess, "run", lambda *a, **k: cli_result(listing))
    assert updater.installed_versions(here) == {
        "ploop": "0.4.0",
        "user": "2.0.0",
        "raw": "unknown",
    }


def test_session_project_prefers_env_over_payload_cwd(monkeypatch):
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    assert updater.session_project({"cwd": "/p"}) == "/p"
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/env")
    assert updater.session_project({"cwd": "/p"}) == "/env"
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    assert updater.session_project({}) is None


def test_installed_versions_empty_on_cli_failure(monkeypatch):
    monkeypatch.setattr(
        updater.subprocess, "run", lambda *a, **k: cli_result([], returncode=1)
    )
    assert updater.installed_versions("/work/here") == {}
    monkeypatch.setattr(
        updater.subprocess,
        "run",
        lambda *a, **k: (_ for _ in ()).throw(OSError("no claude")),
    )
    assert updater.installed_versions("/work/here") == {}


class TestCheckForUpdate:
    def arrange(self, tmp_path, monkeypatch, installed: dict[str, str]):
        data = tmp_path / "data"
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(data))
        monkeypatch.setattr("sys.stdin", io.StringIO(""))
        monkeypatch.setattr(
            updater, "installed_versions", lambda project_dir=None: installed
        )
        return data / updater.CACHE_FILENAME

    def test_emits_fresh_then_reuses_cache_within_cooldown(
        self, tmp_path, monkeypatch, capsys
    ):
        self.arrange(tmp_path, monkeypatch, {"ploop": "0.1.0"})
        monkeypatch.setattr(
            updater, "fetch_remote_versions", lambda: {"ploop": "9.9.9"}
        )
        updater.check_for_update()
        assert "[ploop 0.1.0 > 9.9.9]" in capsys.readouterr().out

        def unexpected_fetch():
            raise AssertionError("fetch must be cooled")

        monkeypatch.setattr(updater, "fetch_remote_versions", unexpected_fetch)
        updater.check_for_update()
        assert "[ploop 0.1.0 > 9.9.9]" in capsys.readouterr().out

    def test_clears_the_moment_local_is_current(self, tmp_path, monkeypatch, capsys):
        cache_file = self.arrange(tmp_path, monkeypatch, {"ploop": "9.9.9"})
        cache_file.parent.mkdir(parents=True)
        updater.save_cache(
            cache_file,
            {"last_check_ts": time.time(), "remote_versions": {"ploop": "9.9.9"}},
        )
        updater.check_for_update()
        assert capsys.readouterr().out == ""

    def test_offline_claims_window_and_stays_silent(
        self, tmp_path, monkeypatch, capsys
    ):
        cache_file = self.arrange(tmp_path, monkeypatch, {"ploop": "0.1.0"})
        monkeypatch.setattr(updater, "fetch_remote_versions", lambda: None)
        updater.check_for_update()
        assert capsys.readouterr().out == ""
        assert json.loads(cache_file.read_text())["last_check_ts"] > 0
