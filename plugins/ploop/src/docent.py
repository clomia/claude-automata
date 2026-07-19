"""Docent — the resolver behind ploop's read-only query surface.

The docent session answers the owner's questions from the loop's externalized
records.  Sessions change on relaunch and several loops can coexist, so
identity is never injected: this script re-resolves the live layout on every
query — which loops exist, where their records live, and where the harness
keeps the main transcript (whose directory also holds the delegated workers'
agent-*.jsonl files).

The data dir resolves --data-dir first (the skill passes
"${CLAUDE_PLUGIN_DATA}" through — placeholder substitution in skill content is
documented), then the CLAUDE_PLUGIN_DATA env var, then the documented layout
~/.claude/plugins/data/ploop-* (plugins-reference: ~/.claude/plugins/data/{id}/).
Transcript discovery is the observation-based part: the
~/.claude/projects/*/{session}.jsonl location and its
{session}/subagents/agent-*.jsonl worker records are undocumented layouts
(measured 2026-07); when they drift the output degrades to "not found" /
"(absent)" markers.

Everything here reads; nothing writes — the loop surface owns all mutation.
Output is English (code-emitted lane).
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.state import Workspace, load_ledger


def resolve_data_dir(flag: str | None) -> Path | None:
    """The chain: non-empty --data-dir, non-empty env, observed layout glob."""
    for value in (flag, os.environ.get("CLAUDE_PLUGIN_DATA")):
        if value and value.strip():
            return Path(value.strip())
    found = sorted(Path.home().glob(".claude/plugins/data/ploop-*"))
    return found[0] if found else None


def find_transcripts(session_id: str) -> list[Path]:
    return sorted(Path.home().glob(f".claude/projects/*/{session_id}.jsonl"))


def last_activity(ws: Workspace) -> float:
    """Newest mtime across records AND transcript — "when was this loop last
    alive" (0.0 when nothing stats).  Loop-state files only move at stops, so
    mid-round the transcript is the live signal; without it a two-hour round
    reads as a two-hour stall."""
    stamps = []
    for path in (
        ws.anchor_path,
        ws.log_path,
        ws.ledger_path,
        ws.round_path,
        ws.advice_history_path,
        *find_transcripts(ws.session_id),
    ):
        try:
            stamps.append(path.stat().st_mtime)
        except OSError:
            pass
    return max(stamps, default=0.0)


def iso(mtime: float) -> str:
    return datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def human_size(n: float) -> str:
    for unit in ("B", "KB", "MB"):
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}GB"


def first_line(path: Path) -> str:
    try:
        for line in path.read_text().splitlines():
            if line.strip():
                return line.strip()
    except OSError, UnicodeDecodeError:
        pass
    return "(unreadable)"


def describe(path: Path) -> str:
    """The path plus its liveness and weight, so the docent never chases a
    ghost file and can pick a read strategy (whole, tail, delegate)."""
    try:
        size = path.stat().st_size
    except OSError:
        return f"{path} (absent)"
    return f"{path} (empty)" if size == 0 else f"{path} ({human_size(size)})"


def render_session(ws: Workspace) -> str:
    ledger = load_ledger(ws.ledger_path)
    active = ws.active_path.exists()
    lines = [
        f"session {ws.session_id}  [{'ACTIVE' if active else 'inactive'}]"
        f"  phase={ledger['phase']}  round={len(ledger['advice_history'])}"
        f"  round_start_line={ledger['round_start_line']}"
        f"  last_activity={iso(last_activity(ws))}",
        f"  anchor head:     {first_line(ws.anchor_path)}",
        f"  anchor:          {describe(ws.anchor_path)}",
        f"  loop log:        {describe(ws.log_path)}",
        f"  advice history:  {describe(ws.advice_history_path)}",
        f"  round slice:     {describe(ws.round_path)}",
        f"  ledger:          {describe(ws.ledger_path)}",
        f"  candidates:      {describe(ws.candidates_path)}",
    ]
    transcripts = find_transcripts(ws.session_id)
    for t in transcripts:
        try:
            written = f" (last write {iso(t.stat().st_mtime)})"
        except OSError:
            written = ""
        lines.append(f"  transcript:      {t}{written}")
        subagents = t.parent / ws.session_id / "subagents"
        if subagents.is_dir():
            lines.append(f"  worker records:  {subagents}/agent-*.jsonl")
        else:
            lines.append(f"  worker records:  {subagents} (absent)")
    if not transcripts:
        lines.append("  transcript:      not found under ~/.claude/projects")
    return "\n".join(lines)


def render(data_dir: Path) -> str:
    sessions = [
        Workspace(data_dir, anchor.name.removesuffix("_anchor.md"))
        for anchor in data_dir.glob("*_anchor.md")
    ]
    if not sessions:
        return f"No loops found in {data_dir}."
    ordered = sorted(
        sessions, key=lambda ws: (not ws.active_path.exists(), -last_activity(ws))
    )
    return "\n\n".join(render_session(ws) for ws in ordered)


def resolve() -> None:
    """Console entry: resolve the data dir and print every loop's records."""
    parser = argparse.ArgumentParser(prog="docent")
    parser.add_argument("--data-dir", default=None)
    args = parser.parse_args()
    data_dir = resolve_data_dir(args.data_dir)
    if data_dir is None or not data_dir.is_dir():
        sys.stdout.write(
            "No ploop data dir found (CLAUDE_PLUGIN_DATA unset and no "
            "~/.claude/plugins/data/ploop-*).\n"
        )
        return
    sys.stdout.write(render(data_dir) + "\n")
