"""State — the per-session workspace layout and the round ledger.

Workspace is the single authority for where a session's files live: the loop
state under CLAUDE_PLUGIN_DATA, plus the two agent handoff channels (advice,
narration) under the system temp dir — a Write TOOL call into the protected
~/.claude routes to the auto-permission-mode classifier and can be silently
blocked, so the agents write to unprotected temp, where it is auto-approved.

The ledger ({round, regions, done}) is the loop's persisted state; the hook
owns it as single writer — advisor and narrator only hand off text files.
"""

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Workspace:
    """Every per-session file path, in one place."""

    data_dir: Path
    session_id: str

    @classmethod
    def from_env(cls, session_id: str) -> "Workspace":
        return cls(Path(os.environ["CLAUDE_PLUGIN_DATA"]), session_id)

    def path(self, name: str) -> Path:
        return self.data_dir / f"{self.session_id}_{name}"

    @property
    def mission_path(self) -> Path:
        return self.path("mission.md")

    @property
    def active_path(self) -> Path:
        return self.path("active")

    @property
    def launching_path(self) -> Path:
        return self.path("launching")

    @property
    def ledger_path(self) -> Path:
        return self.path("loop.json")

    @property
    def action_path(self) -> Path:
        return self.path("action.json")

    @property
    def regions_path(self) -> Path:
        return self.path("regions.md")

    @property
    def log_path(self) -> Path:
        return self.path("loop.log")

    @property
    def advisor_token_path(self) -> Path:
        return self.path("advisor_token")

    @property
    def advisor_running_path(self) -> Path:
        return self.path("advisor_running")

    @property
    def compacted_path(self) -> Path:
        return self.path("compacted")

    @property
    def advice_path(self) -> Path:
        return Path(tempfile.gettempdir()) / f"ploop_{self.session_id}_advice.md"

    @property
    def narration_path(self) -> Path:
        return Path(tempfile.gettempdir()) / f"ploop_{self.session_id}_narration.md"

    def clear_round_state(self) -> None:
        """Remove the per-round loop state (mission.md and active marker kept)."""
        for path in (
            self.ledger_path,
            self.advisor_token_path,
            self.advisor_running_path,
            self.compacted_path,
            self.advice_path,
            self.narration_path,
        ):
            path.unlink(missing_ok=True)


def load_ledger(ledger_file: Path) -> dict:
    """Load the {round, regions, done} ledger. Empty dict on any failure."""
    if not ledger_file.exists():
        return {}
    try:
        ledger = json.loads(ledger_file.read_text())
    except json.JSONDecodeError, OSError:
        return {}
    return ledger if isinstance(ledger, dict) else {}


def save_ledger(
    ledger_file: Path, *, round_number: int, regions: list[str], done: bool
) -> None:
    """Persist the round/regions/done ledger."""
    ledger_file.write_text(
        json.dumps({"round": round_number, "regions": regions, "done": done})
    )
