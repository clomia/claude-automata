"""State — external inputs for a main-session Stop, assembled into one object.

Parses the hook event, locates the per-session workspace files under
CLAUDE_PLUGIN_DATA, and loads the persisted round/regions/done ledger.

The hook owns the entire ledger: it reads the advisor's returned region from
the transcript and records round, regions, and done.  The advisor only
analyzes and returns text — it does not write state.  The original-mission
lives in an external file (not the transcript), so there is no
transcript-vs-capture reconciliation.
"""

import json
import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict

ROUND_LIMIT = 30


def mission_file(data_dir: Path, session_id: str) -> Path:
    return data_dir / f"{session_id}_mission.md"


def active_file(data_dir: Path, session_id: str) -> Path:
    return data_dir / f"{session_id}_active"


class HookInput(BaseModel):
    """Stop hook event data from stdin."""

    model_config = ConfigDict(extra="ignore")

    session_id: str
    transcript_path: str


class State(BaseModel):
    """All external inputs for one Stop, assembled into one object."""

    session_id: str
    transcript_path: str
    data_dir: Path
    mission_active: bool
    compacted: bool
    current_round: int
    region_history: list[str]
    done: bool

    @property
    def mission_path(self) -> Path:
        return mission_file(self.data_dir, self.session_id)

    @property
    def active_path(self) -> Path:
        return active_file(self.data_dir, self.session_id)

    @property
    def compacted_path(self) -> Path:
        return self.data_dir / f"{self.session_id}_compacted"

    @property
    def state_path(self) -> Path:
        return self.data_dir / f"{self.session_id}_loop.json"

    @property
    def action_path(self) -> Path:
        return self.data_dir / f"{self.session_id}_action.json"

    @property
    def regions_path(self) -> Path:
        return self.data_dir / f"{self.session_id}_regions.md"

    @property
    def log_path(self) -> Path:
        return self.data_dir / f"{self.session_id}_loop.log"

    @property
    def advisor_token_path(self) -> Path:
        return advisor_token_file(self.data_dir, self.session_id)


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


def advisor_token_file(data_dir: Path, session_id: str) -> Path:
    """The single-use token a Stop writes to authorize one advisor call.

    PreToolUse consumes (deletes) it on the advisor call, so its presence at the
    next Stop signals the advisor was NOT called this round — the hook uses this
    to skip stale-region extraction (no fresh verdict to record).  A call with no
    fresh token is self-initiated and gets denied.  UserPromptSubmit clears it at
    the turn boundary so it never leaks into the next mission.
    """
    return data_dir / f"{session_id}_advisor_token"


def session_workspace() -> tuple[Path, str]:
    """(data_dir, session_id) for the running session, read from the environment.

    /ploop:launch's CLI entry points call this — they run outside the hook
    stdin protocol, so session identity comes straight from the environment
    Claude Code sets for every session rather than from a hook payload.
    """
    return Path(os.environ["CLAUDE_PLUGIN_DATA"]), os.environ["CLAUDE_CODE_SESSION_ID"]


def build_state(stdin_raw: str) -> State:
    """Collect all external inputs and assemble a State. No side effects.

    mission_active gates the whole hook: it is True only when a
    {session}_active marker exists.  /ploop:launch creates it at handoff,
    UserPromptSubmit clears it on every new user turn, and stop() clears it when
    the loop terminates.  Absent the marker the stopping session is not an
    active ploop run.

    compacted reflects a {session}_compacted marker the PostCompact hook touches;
    on a compacted round stop() re-injects the original-mission text into the
    trigger (parallax mechanism 2) and clears the marker.
    """
    hook = HookInput.model_validate_json(stdin_raw)
    data_dir = Path(os.environ["CLAUDE_PLUGIN_DATA"])

    mission_active = (data_dir / f"{hook.session_id}_active").exists()
    compacted = (data_dir / f"{hook.session_id}_compacted").exists()
    ledger = load_ledger(data_dir / f"{hook.session_id}_loop.json")

    return State(
        session_id=hook.session_id,
        transcript_path=hook.transcript_path,
        data_dir=data_dir,
        mission_active=mission_active,
        compacted=compacted,
        current_round=ledger.get("round", 0),
        region_history=ledger.get("regions", []),
        done=ledger.get("done", False),
    )
