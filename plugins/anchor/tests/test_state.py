"""Tests for the state module."""

import json

from src.state import (
    ROUND_LIMIT,
    AnchorState,
    HookInput,
    build_state,
    load_ledger,
    save_ledger,
)


def make_stdin(*, session_id="s1", transcript_path="/t.jsonl", **extra):
    return json.dumps(
        {"session_id": session_id, "transcript_path": transcript_path, **extra}
    )


def make_state(tmp_path, **overrides):
    defaults = dict(
        session_id="s1",
        transcript_path="/t.jsonl",
        stop_hook_active=False,
        data_dir=tmp_path,
        mission_active=True,
        current_round=0,
        region_history=[],
        done=False,
    )
    defaults.update(overrides)
    return AnchorState(**defaults)


# ── HookInput ──


class TestHookInput:
    def test_parse(self):
        hook = HookInput.model_validate_json(make_stdin(session_id="abc"))
        assert hook.session_id == "abc"

    def test_ignores_extra_fields(self):
        hook = HookInput.model_validate_json(make_stdin(cwd="/x", agent_type="anchor"))
        assert not hasattr(hook, "cwd")

    def test_stop_hook_active_defaults_false(self):
        hook = HookInput.model_validate_json(
            json.dumps({"session_id": "s", "transcript_path": "/t"})
        )
        assert hook.stop_hook_active is False


# ── Ledger persistence ──


class TestLedger:
    def test_roundtrip(self, tmp_path):
        f = tmp_path / "s1_anchor.json"
        save_ledger(f, round_number=2, regions=["a", "b"], done=False)
        assert load_ledger(f) == {"round": 2, "regions": ["a", "b"], "done": False}

    def test_load_missing_returns_empty(self, tmp_path):
        assert load_ledger(tmp_path / "none.json") == {}

    def test_load_corrupt_returns_empty(self, tmp_path):
        f = tmp_path / "s1.json"
        f.write_text("{broken")
        assert load_ledger(f) == {}


# ── AnchorState path properties ──


class TestAnchorStatePaths:
    def test_per_session_paths(self, tmp_path):
        state = make_state(tmp_path)
        assert state.mission_path == tmp_path / "s1_mission.md"
        assert state.state_path == tmp_path / "s1_anchor.json"
        assert state.action_path == tmp_path / "s1_action.json"
        assert state.analysis_path == tmp_path / "s1_analysis.md"
        assert state.log_path == tmp_path / "s1_anchor.log"


# ── build_state ──


class TestBuildState:
    def test_inactive_without_mission_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        state = build_state(make_stdin())
        assert state.mission_active is False
        assert state.current_round == 0
        assert state.region_history == []
        assert state.done is False

    def test_active_with_mission_file(self, tmp_path, monkeypatch):
        (tmp_path / "s1_mission.md").write_text("# Mission")
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        state = build_state(make_stdin())
        assert state.mission_active is True

    def test_loads_persisted_ledger(self, tmp_path, monkeypatch):
        (tmp_path / "s1_mission.md").write_text("m")
        save_ledger(
            tmp_path / "s1_anchor.json",
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
