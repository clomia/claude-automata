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

The listing shows only loops launched in the invoking project directory —
resolved --project-dir first (the skill passes "${CLAUDE_PROJECT_DIR}"
through; the Bash lane gets no CLAUDE_* env, measured 2026-07), then the env
var, then the process cwd.  The verdict is the launch-recorded directory
({session}_project, written at launch and backfilled at stop); a session from
before that recording falls back to its transcript's parent name, matched
char-tolerantly (the observed encoding dashes path separators; unsampled
characters may dash or survive), so an encoding variant errs toward inclusion.
No record and no transcript is no verdict, and only positive verdicts are
shown — everything else is one hidden-count line, never content.
--exclude-converged additionally drops finished anchors (phase converged),
for questions about the work still in flight.

Everything here reads; nothing writes — the loop surface owns all mutation.
Output is English (code-emitted lane).
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.state import CONVERGED, Workspace, load_ledger


def resolve_data_dir(flag: str | None) -> Path | None:
    """The chain: non-empty --data-dir, non-empty env, observed layout glob."""
    for value in (flag, os.environ.get("CLAUDE_PLUGIN_DATA")):
        if value and value.strip():
            return Path(value.strip())
    found = sorted(Path.home().glob(".claude/plugins/data/ploop-*"))
    return found[0] if found else None


def resolve_project_dir(flag: str | None) -> str:
    """The chain: non-empty --project-dir, non-empty env, process cwd."""
    for value in (flag, os.environ.get("CLAUDE_PROJECT_DIR")):
        if value and value.strip():
            return value.strip().rstrip("/") or "/"
    return str(Path.cwd())


def encodes(path: str, name: str) -> bool:
    """Whether `name` is a plausible harness encoding of `path` — char-wise:
    ASCII alphanumerics must match case-insensitively, anything else may
    appear as itself or `-`.  The observed samples fix only `/`→`-` and
    literal `-` survival; the tolerance covers the unsampled variants (case
    folding included), so a rule variant errs toward inclusion and can never
    hide the project's own loops."""
    return len(name) == len(path) and all(
        n.lower() == c.lower() if (c.isascii() and c.isalnum()) else n in ("-", c)
        for c, n in zip(path, name)
    )


def find_transcripts(session_id: str) -> list[Path]:
    return sorted(Path.home().glob(f".claude/projects/*/{session_id}.jsonl"))


def launched_here(ws: Workspace, project_dir: str) -> bool | None:
    """The provenance verdict — the launch-recorded directory when present,
    else the transcript's parent name (loops from before the recording), else
    None: no record is no verdict, and only positive verdicts are listed."""
    try:
        recorded = ws.project_path.read_text().strip()
    except OSError, UnicodeDecodeError:
        recorded = ""  # unreadable record degrades to the fallback, never a crash
    if recorded:
        return recorded.rstrip("/") == project_dir.rstrip("/")
    if found := find_transcripts(ws.session_id):
        return any(encodes(project_dir, t.parent.name) for t in found)
    return None


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


def render(data_dir: Path, project_dir: str, exclude_converged: bool = False) -> str:
    sessions = [
        Workspace(data_dir, anchor.name.removesuffix("_anchor.md"))
        for anchor in data_dir.glob("*_anchor.md")
    ]
    if not sessions:
        return f"No loops found in {data_dir}."
    launched = [ws for ws in sessions if launched_here(ws, project_dir)]
    shown = launched
    notes = []
    if len(launched) < len(sessions):
        notes.append(
            f"{len(sessions) - len(launched)} loop(s) hidden "
            "(not attributed to this project directory)."
        )
    if exclude_converged:
        shown = [
            ws for ws in launched if load_ledger(ws.ledger_path)["phase"] != CONVERGED
        ]
        if len(shown) < len(launched):
            notes.append(f"{len(launched) - len(shown)} converged loop(s) excluded.")
    if not shown:
        return "\n".join([f"No loops for this project ({project_dir}).", *notes])
    ordered = sorted(
        shown, key=lambda ws: (not ws.active_path.exists(), -last_activity(ws))
    )
    listing = "\n\n".join(render_session(ws) for ws in ordered)
    return "\n\n".join([listing, "\n".join(notes)]) if notes else listing


def resolve() -> None:
    """Console entry: resolve the data dir and project scope, then print the
    records of this directory's loops."""
    parser = argparse.ArgumentParser(prog="docent")
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--project-dir", default=None)
    parser.add_argument("--exclude-converged", action="store_true")
    args = parser.parse_args()
    data_dir = resolve_data_dir(args.data_dir)
    if data_dir is None or not data_dir.is_dir():
        sys.stdout.write(
            "No ploop data dir found (CLAUDE_PLUGIN_DATA unset and no "
            "~/.claude/plugins/data/ploop-*).\n"
        )
        return
    sys.stdout.write(
        render(data_dir, resolve_project_dir(args.project_dir), args.exclude_converged)
        + "\n"
    )
