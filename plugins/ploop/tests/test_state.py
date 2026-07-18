"""Tests for the state module."""

from pathlib import Path

from src.state import CONVERGED, Workspace, load_ledger, save_ledger

DEFAULTS = {
    "advice_history": [],
    "round_start_line": 1,
    "anomalies": 0,
    "phase": "fresh",
}


# ── Ledger persistence ──


class TestLedger:
    def test_roundtrip(self, tmp_path):
        f = tmp_path / "s1_loop.json"
        ledger = {
            "advice_history": ["a", "b"],
            "round_start_line": 842,
            "anomalies": 1,
            "phase": "advising",
        }
        save_ledger(f, ledger)
        assert load_ledger(f) == ledger

    def test_load_fills_defaults(self, tmp_path):
        """load returns every key, so a partial save reads back whole — callers
        index directly and update by merge, never re-defaulting an omitted key."""
        f = tmp_path / "s1_loop.json"
        save_ledger(f, {"advice_history": ["a"]})
        assert load_ledger(f) == {**DEFAULTS, "advice_history": ["a"]}

    def test_load_missing_returns_defaults(self, tmp_path):
        assert load_ledger(tmp_path / "none.json") == DEFAULTS

    def test_load_corrupt_returns_defaults(self, tmp_path):
        f = tmp_path / "s1.json"
        f.write_text("{broken")
        assert load_ledger(f) == DEFAULTS

    def test_merge_preserves_untouched_fields(self, tmp_path):
        """The update idiom save({**ledger, change}) preserves everything else, so
        a terminating write can't clobber round_start_line (the P1 fix, structural)."""
        f = tmp_path / "s1_loop.json"
        save_ledger(
            f,
            {
                "advice_history": ["a"],
                "round_start_line": 500,
                "anomalies": 2,
                "phase": "advising",
            },
        )
        save_ledger(f, {**load_ledger(f), "phase": CONVERGED})  # end: only phase moves
        after = load_ledger(f)
        assert after["phase"] == CONVERGED
        assert after["round_start_line"] == 500  # preserved
        assert after["advice_history"] == ["a"]


# ── Workspace ──


class TestWorkspace:
    def test_per_session_paths(self, tmp_path, monkeypatch):
        monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
        ws = Workspace(data_dir=tmp_path, session_id="s1")
        assert ws.anchor_path == tmp_path / "s1_anchor.md"
        assert ws.active_path == tmp_path / "s1_active"
        assert ws.ledger_path == tmp_path / "s1_loop.json"
        assert ws.round_path == tmp_path / "s1_round.jsonl"
        assert ws.advice_history_path == tmp_path / "s1_advice_history.md"
        assert ws.log_path == tmp_path / "s1_loop.log"
        assert ws.advisor_token_path == tmp_path / "s1_advisor_token"
        assert ws.advisor_running_path == tmp_path / "s1_advisor_running"
        assert ws.compacted_path == tmp_path / "s1_compacted"
        assert ws.advice_path == tmp_path / "ploop_s1_advice.md"
        assert ws.narration_path == tmp_path / "ploop_s1_narration.md"
        assert ws.candidates_path == tmp_path / "ploop_s1_candidates.md"

    def test_from_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        assert Workspace.from_env("s1") == Workspace(data_dir=tmp_path, session_id="s1")

    def test_temp_channels_live_outside_the_protected_claude_dir(self):
        """The advisor's, narrator's, and main agent's Write targets must be
        unprotected (not under ~/.claude), else an auto-mode Write is
        classifier-gated and can be silently blocked."""
        ws = Workspace(data_dir=Path("/home/u/.claude/plugins/data"), session_id="s1")
        for path in (
            str(ws.advice_path),
            str(ws.narration_path),
            str(ws.candidates_path),
        ):
            assert ".claude" not in path
            assert "s1" in path

    def test_clear_round_state_keeps_anchor_and_log(self, tmp_path, monkeypatch):
        monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
        ws = Workspace(data_dir=tmp_path, session_id="s1")
        round_state = (
            ws.ledger_path,
            ws.round_path,
            ws.advice_history_path,
            ws.advisor_token_path,
            ws.advisor_running_path,
            ws.compacted_path,
            ws.advice_path,
            ws.narration_path,
            ws.candidates_path,
        )
        for path in (*round_state, ws.anchor_path, ws.active_path, ws.log_path):
            path.touch()
        ws.clear_round_state()
        assert not any(path.exists() for path in round_state)
        assert ws.anchor_path.exists()
        assert ws.active_path.exists()
        assert ws.log_path.exists()
