"""Tests for the updater module — version comparison, cache, local manifest read."""

import json

from src.updater import (
    is_newer,
    load_cache,
    parse_version,
    read_local_version,
    save_cache,
)


class TestVersionCompare:
    def test_parse(self):
        assert parse_version("1.2.3") == (1, 2, 3)

    def test_newer_strict(self):
        assert is_newer("0.6.0", "0.5.0") is True
        assert is_newer("0.5.0", "0.5.0") is False
        assert is_newer("0.5.0", "0.6.0") is False

    def test_newer_handles_bad_input(self):
        assert is_newer("not-a-version", "0.5.0") is False


class TestCache:
    def test_roundtrip(self, tmp_path):
        f = tmp_path / "update_cache.json"
        save_cache(f, {"remote_version": "0.6.0", "last_check_ts": 1.0})
        assert load_cache(f)["remote_version"] == "0.6.0"

    def test_load_missing_returns_empty(self, tmp_path):
        assert load_cache(tmp_path / "none.json") == {}


class TestReadLocalVersion:
    def test_reads_version(self, tmp_path):
        manifest = tmp_path / ".claude-plugin" / "plugin.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"version": "0.5.0"}))
        assert read_local_version(tmp_path) == "0.5.0"

    def test_missing_returns_none(self, tmp_path):
        assert read_local_version(tmp_path) is None
