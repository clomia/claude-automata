"""State — external inputs for an anchor SubagentStop, assembled into one object.

Parses the hook event, locates the per-session workspace files under
CLAUDE_PLUGIN_DATA, and loads the persisted round/regions/done ledger.

The hook owns the entire ledger: it reads the advisor's returned region from
the transcript and records round, regions, and done.  The advisor only
analyzes and returns text — it no longer writes state.  The mission lives in
an external file (not the transcript), so there is no transcript-vs-capture
reconciliation.
"""

import json
import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict

ROUND_LIMIT = 30


class HookInput(BaseModel):
    """SubagentStop hook event data from stdin."""

    model_config = ConfigDict(extra="ignore")

    session_id: str
    transcript_path: str
    stop_hook_active: bool = False


class AnchorState(BaseModel):
    """All external inputs for one SubagentStop, assembled into one object."""

    session_id: str
    transcript_path: str
    stop_hook_active: bool
    data_dir: Path
    mission_active: bool
    current_round: int
    region_history: list[str]
    done: bool

    @property
    def mission_path(self) -> Path:
        return self.data_dir / f"{self.session_id}_mission.md"

    @property
    def state_path(self) -> Path:
        return self.data_dir / f"{self.session_id}_anchor.json"

    @property
    def action_path(self) -> Path:
        return self.data_dir / f"{self.session_id}_action.json"

    @property
    def analysis_path(self) -> Path:
        return self.data_dir / f"{self.session_id}_analysis.md"

    @property
    def log_path(self) -> Path:
        return self.data_dir / f"{self.session_id}_anchor.log"


def load_ledger(state_file: Path) -> dict:
    """Load the {round, regions, done} ledger. Empty dict on any failure."""
    if not state_file.exists():
        return {}
    try:
        return json.loads(state_file.read_text())
    except json.JSONDecodeError, OSError:
        return {}


def save_ledger(
    state_file: Path, *, round_number: int, regions: list[str], done: bool
) -> None:
    """Persist the round/regions/done ledger."""
    state_file.write_text(
        json.dumps({"round": round_number, "regions": regions, "done": done})
    )


def build_state(stdin_raw: str) -> AnchorState:
    """Collect all external inputs and assemble an AnchorState. No side effects.

    mission_active gates the whole hook: it is True only when a
    {session}_mission.md file exists, which main writes at handoff.  Absent
    that file the stopping subagent is not an anchor mission.
    """
    hook = HookInput.model_validate_json(stdin_raw)
    data_dir = Path(os.environ["CLAUDE_PLUGIN_DATA"])

    mission_active = (data_dir / f"{hook.session_id}_mission.md").exists()
    ledger = load_ledger(data_dir / f"{hook.session_id}_anchor.json")

    return AnchorState(
        session_id=hook.session_id,
        transcript_path=hook.transcript_path,
        stop_hook_active=hook.stop_hook_active,
        data_dir=data_dir,
        mission_active=mission_active,
        current_round=ledger.get("round", 0),
        region_history=ledger.get("regions", []),
        done=ledger.get("done", False),
    )
