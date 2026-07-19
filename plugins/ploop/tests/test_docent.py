"""Tests for the docent resolver."""

import os
from pathlib import Path

from src.docent import find_transcripts, render, resolve_data_dir
from src.state import Workspace, save_ledger


def seed_session(
    data_dir: Path, session: str, *, active: bool, phase: str, rounds: int, mtime: float
) -> Workspace:
    ws = Workspace(data_dir, session)
    ws.anchor_path.write_text(f"# Mission of {session}\n\nbody")
    ws.log_path.write_text(f"[[ ANCHOR ]]\n\n# Mission of {session}\n")
    save_ledger(
        ws.ledger_path,
        {"advice_history": ["advice"] * rounds, "phase": phase},
    )
    if active:
        ws.active_path.touch()
    for path in (ws.anchor_path, ws.log_path, ws.ledger_path):
        os.utime(path, (mtime, mtime))
    return ws


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(p): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


# ── Listing ──


class TestRender:
    def test_orders_active_first_and_annotates(self, tmp_path):
        seed_session(
            tmp_path,
            "old-conv",
            active=False,
            phase="converged",
            rounds=5,
            mtime=2000.0,
        )
        seed_session(
            tmp_path, "live", active=True, phase="advising", rounds=2, mtime=1000.0
        )
        out = render(tmp_path)
        assert out.index("session live") < out.index("session old-conv")
        assert "[ACTIVE]  phase=advising  round=2  round_start_line=1" in out
        assert "[inactive]  phase=converged  round=5" in out
        assert "# Mission of live" in out
        assert f"{Workspace(tmp_path, 'live').log_path} (" in out

    def test_no_loops(self, tmp_path):
        assert render(tmp_path) == f"No loops found in {tmp_path}."

    def test_read_only(self, tmp_path):
        seed_session(
            tmp_path, "live", active=True, phase="advising", rounds=1, mtime=1000.0
        )
        before = snapshot(tmp_path)
        render(tmp_path)
        assert snapshot(tmp_path) == before


# ── Data dir chain ──


class TestResolveDataDir:
    def test_blank_flag_falls_back_to_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        assert resolve_data_dir("") == tmp_path

    def test_flag_wins(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", "/elsewhere")
        assert resolve_data_dir(str(tmp_path)) == tmp_path

    def test_observed_layout_glob(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.delenv("CLAUDE_PLUGIN_DATA", raising=False)
        observed = tmp_path / ".claude" / "plugins" / "data" / "ploop-claude-automata"
        observed.mkdir(parents=True)
        assert resolve_data_dir(None) == observed

    def test_nothing_resolves(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.delenv("CLAUDE_PLUGIN_DATA", raising=False)
        assert resolve_data_dir(None) is None


# ── Transcript resolution ──


class TestTranscripts:
    def test_found_with_worker_dir(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        project = tmp_path / ".claude" / "projects" / "-home-user-repo"
        project.mkdir(parents=True)
        transcript = project / "live.jsonl"
        transcript.write_text("{}\n")
        assert find_transcripts("live") == [transcript]

        data = tmp_path / "data"
        data.mkdir()
        seed_session(data, "live", active=True, phase="advising", rounds=0, mtime=1.0)
        subagents = project / "live" / "subagents"
        out = render(data)
        assert f"transcript:      {transcript} (last write " in out
        assert f"worker records:  {subagents} (absent)" in out

        subagents.mkdir(parents=True)
        (subagents / "agent-a1.jsonl").write_text("{}\n")
        assert f"worker records:  {subagents}/agent-*.jsonl" in render(data)

    def test_missing_is_stated(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        data = tmp_path / "data"
        data.mkdir()
        seed_session(data, "ghost", active=False, phase="fresh", rounds=0, mtime=1.0)
        assert "transcript:      not found under ~/.claude/projects" in render(data)
