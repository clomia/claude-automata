"""Tests for the state module."""

from pathlib import Path

from src.state import Workspace, load_ledger, save_ledger


# ── Ledger persistence ──


class TestLedger:
    def test_roundtrip_defaults_clean_counters(self, tmp_path):
        f = tmp_path / "s1_loop.json"
        save_ledger(f, round_number=2, advice_history=["a", "b"], done=False)
        assert load_ledger(f) == {
            "round": 2,
            "advice_history": ["a", "b"],
            "done": False,
            "advisor_failures": 0,
            "declines": 0,
        }

    def test_roundtrip_persists_anomaly_counters(self, tmp_path):
        f = tmp_path / "s1_loop.json"
        save_ledger(
            f,
            round_number=3,
            advice_history=["a"],
            done=False,
            advisor_failures=1,
            declines=1,
        )
        ledger = load_ledger(f)
        assert ledger["advisor_failures"] == 1
        assert ledger["declines"] == 1

    def test_load_missing_returns_empty(self, tmp_path):
        assert load_ledger(tmp_path / "none.json") == {}

    def test_load_corrupt_returns_empty(self, tmp_path):
        f = tmp_path / "s1.json"
        f.write_text("{broken")
        assert load_ledger(f) == {}


# ── Workspace ──


class TestWorkspace:
    def test_per_session_paths(self, tmp_path, monkeypatch):
        monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
        ws = Workspace(data_dir=tmp_path, session_id="s1")
        assert ws.mission_path == tmp_path / "s1_mission.md"
        assert ws.active_path == tmp_path / "s1_active"
        assert ws.launching_path == tmp_path / "s1_launching"
        assert ws.ledger_path == tmp_path / "s1_loop.json"
        assert ws.action_path == tmp_path / "s1_action.json"
        assert ws.advice_history_path == tmp_path / "s1_advice_history.md"
        assert ws.log_path == tmp_path / "s1_loop.log"
        assert ws.advisor_token_path == tmp_path / "s1_advisor_token"
        assert ws.advisor_running_path == tmp_path / "s1_advisor_running"
        assert ws.compacted_path == tmp_path / "s1_compacted"
        assert ws.advice_path == tmp_path / "ploop_s1_advice.md"
        assert ws.narration_path == tmp_path / "ploop_s1_narration.md"

    def test_from_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        assert Workspace.from_env("s1") == Workspace(data_dir=tmp_path, session_id="s1")

    def test_temp_channels_live_outside_the_protected_claude_dir(self):
        """The advisor's and narrator's Write targets must be unprotected (not
        under ~/.claude), else an auto-mode Write is classifier-gated and can be
        silently blocked."""
        ws = Workspace(data_dir=Path("/home/u/.claude/plugins/data"), session_id="s1")
        for path in (str(ws.advice_path), str(ws.narration_path)):
            assert ".claude" not in path
            assert "s1" in path

    def test_clear_round_state_keeps_anchor_and_log(self, tmp_path, monkeypatch):
        monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
        ws = Workspace(data_dir=tmp_path, session_id="s1")
        round_state = (
            ws.ledger_path,
            ws.advisor_token_path,
            ws.advisor_running_path,
            ws.compacted_path,
            ws.advice_path,
            ws.narration_path,
        )
        for path in (*round_state, ws.mission_path, ws.active_path, ws.log_path):
            path.touch()
        ws.clear_round_state()
        assert not any(path.exists() for path in round_state)
        assert ws.mission_path.exists()
        assert ws.active_path.exists()
        assert ws.log_path.exists()
