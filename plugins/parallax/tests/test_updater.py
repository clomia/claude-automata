"""Tests for the updater module — version parsing, cache I/O, HTTP fetch, orchestration."""

import io
import json
import time
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.updater import (
    CACHE_FILENAME,
    COOLDOWN_SECONDS,
    check_for_update,
    fetch_remote_version,
    is_newer,
    load_cache,
    parse_version,
    read_local_version,
    save_cache,
)


# ── read_local_version ──


class TestReadLocalVersion:
    def test_reads_version_from_pyproject(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "parallax"\nversion = "0.2.9"\n'
        )
        assert read_local_version(tmp_path) == "0.2.9"

    def test_returns_none_when_file_missing(self, tmp_path):
        assert read_local_version(tmp_path) is None

    def test_returns_none_on_malformed_toml(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("not valid toml ::: {]}")
        assert read_local_version(tmp_path) is None

    def test_returns_none_when_version_key_missing(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "parallax"\n')
        assert read_local_version(tmp_path) is None

    def test_returns_none_when_project_table_missing(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('[tool.poetry]\nname = "parallax"\n')
        assert read_local_version(tmp_path) is None


# ── parse_version ──


class TestParseVersion:
    def test_single_component(self):
        assert parse_version("1") == (1,)

    def test_three_components(self):
        assert parse_version("0.2.6") == (0, 2, 6)

    def test_raises_on_non_numeric(self):
        with pytest.raises(ValueError):
            parse_version("0.2.6-beta")

    def test_raises_on_empty(self):
        with pytest.raises(ValueError):
            parse_version("")


# ── is_newer ──


class TestIsNewer:
    def test_strictly_newer_patch(self):
        assert is_newer("0.2.9", "0.2.6") is True

    def test_strictly_newer_minor(self):
        assert is_newer("0.3.0", "0.2.99") is True

    def test_strictly_newer_major(self):
        assert is_newer("1.0.0", "0.99.99") is True

    def test_same_version(self):
        assert is_newer("0.2.6", "0.2.6") is False

    def test_remote_older(self):
        assert is_newer("0.2.5", "0.2.6") is False

    def test_different_length_newer(self):
        assert is_newer("0.3", "0.2.99") is True

    def test_parse_error_remote(self):
        assert is_newer("0.2.6-beta", "0.2.6") is False

    def test_parse_error_local(self):
        assert is_newer("0.2.7", "weird") is False


# ── load_cache ──


class TestLoadCache:
    def test_returns_empty_when_file_missing(self, tmp_path):
        assert load_cache(tmp_path / "nope.json") == {}

    def test_loads_valid_json(self, tmp_path):
        cache_file = tmp_path / "c.json"
        cache_file.write_text(
            json.dumps({"last_check_ts": 100.0, "remote_version": "0.2.9"})
        )
        assert load_cache(cache_file) == {
            "last_check_ts": 100.0,
            "remote_version": "0.2.9",
        }

    def test_returns_empty_on_corrupt_json(self, tmp_path):
        cache_file = tmp_path / "c.json"
        cache_file.write_text("{corrupt")
        assert load_cache(cache_file) == {}


# ── save_cache ──


class TestSaveCache:
    def test_writes_payload(self, tmp_path):
        cache_file = tmp_path / "c.json"
        save_cache(cache_file, {"last_check_ts": 100.0, "remote_version": "0.2.9"})
        assert json.loads(cache_file.read_text()) == {
            "last_check_ts": 100.0,
            "remote_version": "0.2.9",
        }

    def test_cleans_up_tempfile_after_success(self, tmp_path):
        cache_file = tmp_path / "c.json"
        save_cache(cache_file, {"x": 1})
        assert not (tmp_path / "c.json.tmp").exists()

    def test_round_trip(self, tmp_path):
        cache_file = tmp_path / "c.json"
        payload = {"last_check_ts": 12345.67, "remote_version": "0.3.0"}
        save_cache(cache_file, payload)
        assert load_cache(cache_file) == payload


# ── fetch_remote_version ──


def mock_urlopen_response(body: str) -> MagicMock:
    """Build a mock urlopen context manager that returns the given body."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = body.encode()
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_resp
    mock_cm.__exit__.return_value = None
    return mock_cm


class TestFetchRemoteVersion:
    def test_extracts_parallax_version(self):
        manifest = json.dumps(
            {
                "plugins": [
                    {"name": "other", "version": "9.9.9"},
                    {"name": "parallax", "version": "0.3.0"},
                ]
            }
        )
        with patch(
            "src.updater.urllib.request.urlopen",
            return_value=mock_urlopen_response(manifest),
        ):
            assert fetch_remote_version() == "0.3.0"

    def test_returns_none_when_plugin_missing(self):
        manifest = json.dumps({"plugins": [{"name": "other", "version": "1.0.0"}]})
        with patch(
            "src.updater.urllib.request.urlopen",
            return_value=mock_urlopen_response(manifest),
        ):
            assert fetch_remote_version() is None

    def test_returns_none_on_url_error(self):
        with patch(
            "src.updater.urllib.request.urlopen",
            side_effect=urllib.error.URLError("no network"),
        ):
            assert fetch_remote_version() is None

    def test_returns_none_on_os_error(self):
        with patch(
            "src.updater.urllib.request.urlopen",
            side_effect=OSError("boom"),
        ):
            assert fetch_remote_version() is None

    def test_returns_none_on_json_decode_error(self):
        with patch(
            "src.updater.urllib.request.urlopen",
            return_value=mock_urlopen_response("not json {"),
        ):
            assert fetch_remote_version() is None


# ── check_for_update (integration) ──


class TestCheckForUpdate:
    def setup_plugin(
        self, tmp_path: Path, local_version: str = "0.2.6"
    ) -> tuple[Path, Path]:
        plugin_root = tmp_path / "plugin"
        plugin_root.mkdir()
        (plugin_root / "pyproject.toml").write_text(
            f'[project]\nname = "parallax"\nversion = "{local_version}"\n'
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        return plugin_root, data_dir

    def configure_env(self, monkeypatch, plugin_root: Path, data_dir: Path):
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin_root))
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(data_dir))
        monkeypatch.delenv("PARALLAX_INSIDE_RECURSION", raising=False)
        monkeypatch.setattr("sys.stdin", io.StringIO(""))

    def test_exits_on_recursion_guard(self, tmp_path, monkeypatch, capsys):
        plugin_root, data_dir = self.setup_plugin(tmp_path)
        self.configure_env(monkeypatch, plugin_root, data_dir)
        monkeypatch.setenv("PARALLAX_INSIDE_RECURSION", "1")

        with patch("src.updater.fetch_remote_version") as mock_fetch:
            check_for_update()
            mock_fetch.assert_not_called()

        assert capsys.readouterr().out == ""
        assert not (data_dir / CACHE_FILENAME).exists()

    def test_exits_when_plugin_root_env_missing(self, tmp_path, monkeypatch, capsys):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(data_dir))
        monkeypatch.delenv("PARALLAX_INSIDE_RECURSION", raising=False)
        monkeypatch.setattr("sys.stdin", io.StringIO(""))

        with patch("src.updater.fetch_remote_version") as mock_fetch:
            check_for_update()
            mock_fetch.assert_not_called()

        assert capsys.readouterr().out == ""

    def test_exits_when_data_dir_env_missing(self, tmp_path, monkeypatch, capsys):
        plugin_root = tmp_path / "plugin"
        plugin_root.mkdir()
        (plugin_root / "pyproject.toml").write_text(
            '[project]\nname = "parallax"\nversion = "0.2.6"\n'
        )
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin_root))
        monkeypatch.delenv("CLAUDE_PLUGIN_DATA", raising=False)
        monkeypatch.delenv("PARALLAX_INSIDE_RECURSION", raising=False)
        monkeypatch.setattr("sys.stdin", io.StringIO(""))

        with patch("src.updater.fetch_remote_version") as mock_fetch:
            check_for_update()
            mock_fetch.assert_not_called()

        assert capsys.readouterr().out == ""

    def test_exits_when_local_version_unreadable(self, tmp_path, monkeypatch, capsys):
        plugin_root = tmp_path / "plugin"
        plugin_root.mkdir()
        # No pyproject.toml — read_local_version returns None
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        self.configure_env(monkeypatch, plugin_root, data_dir)

        with patch("src.updater.fetch_remote_version") as mock_fetch:
            check_for_update()
            mock_fetch.assert_not_called()

        assert capsys.readouterr().out == ""

    def test_first_run_fetches_and_notifies(self, tmp_path, monkeypatch, capsys):
        plugin_root, data_dir = self.setup_plugin(tmp_path, local_version="0.2.6")
        self.configure_env(monkeypatch, plugin_root, data_dir)

        with patch(
            "src.updater.fetch_remote_version", return_value="0.3.0"
        ) as mock_fetch:
            check_for_update()
            mock_fetch.assert_called_once()

        out = capsys.readouterr().out
        assert "0.2.6 -> 0.3.0" in out
        assert "claude plugin marketplace update claude-automata" in out
        assert "claude plugin update parallax@claude-automata" in out

        cache = json.loads((data_dir / CACHE_FILENAME).read_text())
        assert cache["remote_version"] == "0.3.0"
        assert cache["last_check_ts"] > 0

    def test_no_notification_when_remote_same_as_local(
        self, tmp_path, monkeypatch, capsys
    ):
        plugin_root, data_dir = self.setup_plugin(tmp_path, local_version="0.2.6")
        self.configure_env(monkeypatch, plugin_root, data_dir)

        with patch("src.updater.fetch_remote_version", return_value="0.2.6"):
            check_for_update()

        assert capsys.readouterr().out == ""

    def test_no_notification_when_remote_older_than_local(
        self, tmp_path, monkeypatch, capsys
    ):
        plugin_root, data_dir = self.setup_plugin(tmp_path, local_version="0.3.0")
        self.configure_env(monkeypatch, plugin_root, data_dir)

        with patch("src.updater.fetch_remote_version", return_value="0.2.6"):
            check_for_update()

        assert capsys.readouterr().out == ""

    def test_skips_fetch_within_cooldown(self, tmp_path, monkeypatch, capsys):
        plugin_root, data_dir = self.setup_plugin(tmp_path, local_version="0.2.6")
        self.configure_env(monkeypatch, plugin_root, data_dir)
        # Fresh cache: 10 seconds ago, well within 6h cooldown
        (data_dir / CACHE_FILENAME).write_text(
            json.dumps(
                {
                    "last_check_ts": time.time() - 10,
                    "remote_version": "0.3.0",
                }
            )
        )

        with patch("src.updater.fetch_remote_version") as mock_fetch:
            check_for_update()
            mock_fetch.assert_not_called()

        # Notification still emitted from the cached remote version
        assert "0.2.6 -> 0.3.0" in capsys.readouterr().out

    def test_fetches_when_cooldown_elapsed(self, tmp_path, monkeypatch, capsys):
        plugin_root, data_dir = self.setup_plugin(tmp_path, local_version="0.2.6")
        self.configure_env(monkeypatch, plugin_root, data_dir)
        # Stale cache: 1 second past the cooldown window
        stale_ts = time.time() - (COOLDOWN_SECONDS + 1)
        (data_dir / CACHE_FILENAME).write_text(
            json.dumps(
                {
                    "last_check_ts": stale_ts,
                    "remote_version": "0.2.7",
                }
            )
        )

        with patch(
            "src.updater.fetch_remote_version", return_value="0.3.0"
        ) as mock_fetch:
            check_for_update()
            mock_fetch.assert_called_once()

        assert "0.2.6 -> 0.3.0" in capsys.readouterr().out
        cache = json.loads((data_dir / CACHE_FILENAME).read_text())
        assert cache["remote_version"] == "0.3.0"
        assert cache["last_check_ts"] > stale_ts

    def test_network_failure_refreshes_timestamp_preserves_cached_remote(
        self, tmp_path, monkeypatch, capsys
    ):
        """On fetch failure, timestamp refreshes (prevent hammering) and the
        previously cached remote version is preserved for future comparisons."""
        plugin_root, data_dir = self.setup_plugin(tmp_path, local_version="0.2.6")
        self.configure_env(monkeypatch, plugin_root, data_dir)
        old_ts = time.time() - (COOLDOWN_SECONDS + 100)
        (data_dir / CACHE_FILENAME).write_text(
            json.dumps(
                {
                    "last_check_ts": old_ts,
                    "remote_version": "0.3.0",
                }
            )
        )

        with patch("src.updater.fetch_remote_version", return_value=None):
            check_for_update()

        # Notification still emitted from the cached remote version
        assert "0.2.6 -> 0.3.0" in capsys.readouterr().out

        cache = json.loads((data_dir / CACHE_FILENAME).read_text())
        assert cache["last_check_ts"] > old_ts
        assert cache["remote_version"] == "0.3.0"

    def test_first_run_with_network_failure_no_notification(
        self, tmp_path, monkeypatch, capsys
    ):
        """First run with no cache and network failure: no notification, no crash.
        Timestamp still recorded to prevent hammering on next session."""
        plugin_root, data_dir = self.setup_plugin(tmp_path, local_version="0.2.6")
        self.configure_env(monkeypatch, plugin_root, data_dir)

        with patch("src.updater.fetch_remote_version", return_value=None):
            check_for_update()

        assert capsys.readouterr().out == ""

        cache = json.loads((data_dir / CACHE_FILENAME).read_text())
        assert cache["remote_version"] is None
        assert cache["last_check_ts"] > 0
