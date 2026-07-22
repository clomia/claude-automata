"""Tests for the docent resolver."""

import os
from pathlib import Path

from src.docent import (
    encodes,
    find_transcripts,
    render,
    resolve_data_dir,
    resolve_project_dir,
)
from src.state import Workspace, save_ledger


def seed_session(
    data_dir: Path,
    session: str,
    *,
    active: bool,
    phase: str,
    rounds: int,
    mtime: float,
    project: str | None = None,
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
    if project:
        ws.project_path.write_text(project)
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
            project="/w/repo",
        )
        seed_session(
            tmp_path,
            "live",
            active=True,
            phase="advising",
            rounds=2,
            mtime=1000.0,
            project="/w/repo",
        )
        out = render(tmp_path, "/w/repo")
        assert out.index("session live") < out.index("session old-conv")
        assert "[ACTIVE]  phase=advising  round=2  round_start_line=1" in out
        assert "[inactive]  phase=converged  round=5" in out
        assert "# Mission of live" in out
        assert f"{Workspace(tmp_path, 'live').log_path} (" in out

    def test_no_loops(self, tmp_path):
        assert render(tmp_path, "/w/repo") == f"No loops found in {tmp_path}."

    def test_read_only(self, tmp_path):
        seed_session(
            tmp_path,
            "live",
            active=True,
            phase="advising",
            rounds=1,
            mtime=1000.0,
            project="/w/repo",
        )
        before = snapshot(tmp_path)
        render(tmp_path, "/w/repo")
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
        out = render(data, "/home/user/repo")
        assert f"transcript:      {transcript} (last write " in out
        assert f"worker records:  {subagents} (absent)" in out

        subagents.mkdir(parents=True)
        (subagents / "agent-a1.jsonl").write_text("{}\n")
        assert f"worker records:  {subagents}/agent-*.jsonl" in render(
            data, "/home/user/repo"
        )

    def test_missing_is_stated(self, tmp_path, monkeypatch):
        """A recorded loop whose transcript is gone (a pause can outlive
        transcript retention) stays listed in its own directory, with the
        absence stated."""
        monkeypatch.setenv("HOME", str(tmp_path))
        data = tmp_path / "data"
        data.mkdir()
        seed_session(
            data,
            "ghost",
            active=False,
            phase="fresh",
            rounds=0,
            mtime=1.0,
            project="/w/repo",
        )
        assert "transcript:      not found under ~/.claude/projects" in render(
            data, "/w/repo"
        )


# ── Project scope ──


def seed_transcript(home: Path, dir_name: str, session: str) -> None:
    project = home / ".claude" / "projects" / dir_name
    project.mkdir(parents=True, exist_ok=True)
    (project / f"{session}.jsonl").write_text("{}\n")


class TestProjectScope:
    def test_only_loops_launched_here_are_shown(self, tmp_path, monkeypatch):
        """Recorded-here and legacy-transcript-here sessions are listed; a
        session recorded elsewhere and one with no verdict at all are both
        hidden behind the count line, content never shown."""
        monkeypatch.setenv("HOME", str(tmp_path))
        seed_transcript(tmp_path, "-w-mine", "legacy")
        data = tmp_path / "data"
        data.mkdir()
        seed_session(
            data,
            "own",
            active=True,
            phase="advising",
            rounds=1,
            mtime=4.0,
            project="/w/mine",
        )
        seed_session(
            data, "legacy", active=False, phase="advising", rounds=1, mtime=3.0
        )
        seed_session(
            data,
            "alien",
            active=True,
            phase="advising",
            rounds=1,
            mtime=2.0,
            project="/w/other",
        )
        seed_session(data, "unknown", active=False, phase="fresh", rounds=0, mtime=1.0)
        out = render(data, "/w/mine")
        assert "session own" in out and "session legacy" in out
        assert "alien" not in out and "session unknown" not in out
        assert "2 loop(s) hidden (not attributed to this project directory)." in out

    def test_record_outranks_transcript(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        seed_transcript(tmp_path, "-w-mine", "moved")
        data = tmp_path / "data"
        data.mkdir()
        seed_session(
            data,
            "moved",
            active=True,
            phase="advising",
            rounds=1,
            mtime=1.0,
            project="/w/other",
        )
        assert "session moved" not in render(data, "/w/mine")
        assert "session moved" in render(data, "/w/other")

    def test_all_foreign_states_reason(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        data = tmp_path / "data"
        data.mkdir()
        seed_session(
            data,
            "alien",
            active=True,
            phase="advising",
            rounds=1,
            mtime=1.0,
            project="/w/other",
        )
        out = render(data, "/w/mine")
        assert "No loops for this project (/w/mine)" in out
        assert "1 loop(s) hidden" in out
        assert "Mission of alien" not in out

    def test_exclude_converged_flag(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        data = tmp_path / "data"
        data.mkdir()
        seed_session(
            data,
            "running",
            active=True,
            phase="advising",
            rounds=1,
            mtime=2.0,
            project="/w/mine",
        )
        seed_session(
            data,
            "done",
            active=False,
            phase="converged",
            rounds=3,
            mtime=1.0,
            project="/w/mine",
        )
        both = render(data, "/w/mine")
        assert "session running" in both and "session done" in both
        live = render(data, "/w/mine", exclude_converged=True)
        assert "session running" in live
        assert "session done" not in live
        assert "1 converged loop(s) excluded." in live

    def test_encoding_tolerance(self):
        path = "/w/my_repo.app"
        assert encodes(path, "-w-my_repo-app")  # separator/dot-only rule
        assert encodes(path, "-w-my-repo-app")  # every-non-alnum rule
        assert encodes("/w/MyRepo", "-w-myrepo")  # case-folding variant
        assert not encodes(path, "-w-my_repo-app2")  # length guard
        assert not encodes("/w/mine", "-w-other")

    def test_corrupt_record_degrades_never_crashes(self, tmp_path, monkeypatch):
        """One undecodable provenance record must not take the listing down —
        it degrades to no-record (hidden and counted), the healthy loop stays."""
        monkeypatch.setenv("HOME", str(tmp_path))
        data = tmp_path / "data"
        data.mkdir()
        seed_session(
            data,
            "own",
            active=True,
            phase="advising",
            rounds=1,
            mtime=2.0,
            project="/w/mine",
        )
        broken = seed_session(
            data, "broken", active=False, phase="advising", rounds=1, mtime=1.0
        )
        broken.project_path.write_bytes(b"\xff\xfe/w/mine")
        out = render(data, "/w/mine")
        assert "session own" in out
        assert "session broken" not in out
        assert "1 loop(s) hidden" in out


class TestResolveProjectDir:
    def test_chain(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/from/env")
        assert resolve_project_dir("/from/flag/") == "/from/flag"
        assert resolve_project_dir("") == "/from/env"
        monkeypatch.delenv("CLAUDE_PROJECT_DIR")
        monkeypatch.chdir(tmp_path)
        assert resolve_project_dir(None) == str(tmp_path)
