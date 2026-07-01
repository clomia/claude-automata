"""Tests for the state module."""

import json

from src.state import (
    ROUND_LIMIT,
    State,
    HookInput,
    build_state,
    load_ledger,
    save_ledger,
    session_workspace,
)


def make_stdin(*, session_id="s1", transcript_path="/t.jsonl", **extra):
    return json.dumps(
        {"session_id": session_id, "transcript_path": transcript_path, **extra}
    )


def make_state(tmp_path, **overrides):
    defaults = dict(
        session_id="s1",
        transcript_path="/t.jsonl",
        data_dir=tmp_path,
        mission_active=True,
        compacted=False,
        current_round=0,
        region_history=[],
        done=False,
    )
    defaults.update(overrides)
    return State(**defaults)


# ── HookInput ──


class TestHookInput:
    def test_parse(self):
        hook = HookInput.model_validate_json(make_stdin(session_id="abc"))
        assert hook.session_id == "abc"

    def test_ignores_extra_fields(self):
        hook = HookInput.model_validate_json(
            make_stdin(cwd="/x", stop_hook_active=True)
        )
        assert not hasattr(hook, "cwd")
        assert not hasattr(hook, "stop_hook_active")


# ── Ledger persistence ──


class TestLedger:
    def test_roundtrip(self, tmp_path):
        f = tmp_path / "s1_loop.json"
        save_ledger(f, round_number=2, regions=["a", "b"], done=False)
        assert load_ledger(f) == {"round": 2, "regions": ["a", "b"], "done": False}

    def test_load_missing_returns_empty(self, tmp_path):
        assert load_ledger(tmp_path / "none.json") == {}

    def test_load_corrupt_returns_empty(self, tmp_path):
        f = tmp_path / "s1.json"
        f.write_text("{broken")
        assert load_ledger(f) == {}


# ── State path properties ──


class TestStatePaths:
    def test_per_session_paths(self, tmp_path):
        state = make_state(tmp_path)
        assert state.mission_path == tmp_path / "s1_mission.md"
        assert state.active_path == tmp_path / "s1_active"
        assert state.compacted_path == tmp_path / "s1_compacted"
        assert state.state_path == tmp_path / "s1_loop.json"
        assert state.action_path == tmp_path / "s1_action.json"
        assert state.regions_path == tmp_path / "s1_regions.md"
        assert state.log_path == tmp_path / "s1_loop.log"
        assert state.advisor_token_path == tmp_path / "s1_advisor_token"
        assert state.advisor_running_path == tmp_path / "s1_advisor_running"


# ── build_state ──


class TestBuildState:
    def test_inactive_without_active_marker(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        state = build_state(make_stdin())
        assert state.mission_active is False
        assert state.compacted is False
        assert state.current_round == 0
        assert state.region_history == []
        assert state.done is False

    def test_active_with_active_marker(self, tmp_path, monkeypatch):
        (tmp_path / "s1_active").touch()
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        state = build_state(make_stdin())
        assert state.mission_active is True

    def test_compacted_marker_detected(self, tmp_path, monkeypatch):
        (tmp_path / "s1_active").touch()
        (tmp_path / "s1_compacted").touch()
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        state = build_state(make_stdin())
        assert state.compacted is True

    def test_loads_persisted_ledger(self, tmp_path, monkeypatch):
        (tmp_path / "s1_active").touch()
        save_ledger(
            tmp_path / "s1_loop.json",
            round_number=3,
            regions=["r1", "r2", "r3"],
            done=False,
        )
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        state = build_state(make_stdin())
        assert state.current_round == 3
        assert state.region_history == ["r1", "r2", "r3"]


def test_round_limit_constant():
    assert ROUND_LIMIT == 30


def test_session_workspace_pairs_data_dir_with_session(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "s1")
    assert session_workspace(str(tmp_path)) == (tmp_path, "s1")
