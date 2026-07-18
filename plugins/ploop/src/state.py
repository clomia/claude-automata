"""State — the per-session workspace layout and the round ledger.

Workspace is the single authority for where a session's files live: the loop
state under CLAUDE_PLUGIN_DATA, plus three files under the system temp dir —
the two agent handoff channels (advice, narration) and the main agent's
candidates queue (facts and terms staged for promotion).  A Write TOOL call
into the protected ~/.claude routes to the auto-permission-mode classifier and
can be silently blocked, so their writers use unprotected temp, where it is
auto-approved.

The ledger ({advice_history, round_start_line, anomalies, phase}) is the loop's
persisted state; the hook owns it as single writer — advisor and narrator only
hand off text files.  Four fields, each one fact:

- advice_history: the round record; its length is the round ordinal (the log
  numbers by it).
- round_start_line: the transcript line where the current round's work begins —
  a file offset, not a message-format field — so the narrator reads that round's
  slice directly instead of the hook reconstructing it.
- anomalies: consecutive anomaly count (an advisor run that wrote nothing, or a
  stop that ignored the trigger), reset to 0 on any clean round; the cap ends the
  loop before it can stalemate.
- phase: the round-cycle position — "fresh" (just launched/resumed, no verdict to
  record yet), "advising" (rounds running), "converged" (the advisor deliberately
  finished the anchor).  It subsumes the old skip-gate and the finished flag:
  record iff phase == "advising"; /ploop:on resumes any phase except "converged".

load_ledger always returns every key, so callers index directly and update by
merge ({**ledger, "phase": ...}): an omitted key is preserved, never
re-defaulted — a resumable anomaly end can't clobber round_start_line.

Most exceptional stalls (an ESC, an API error, a session limit) fire no hook at
all, so they touch no state — the loop just stays active, and /ploop:on re-arms
it.
"""

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

# The round-cycle position (ledger `phase`).
FRESH = "fresh"  # just launched/resumed — the next stop arms without recording
ADVISING = "advising"  # rounds running — the next stop records then arms
CONVERGED = "converged"  # the advisor finished the anchor — /ploop:on refuses


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
    def anchor_path(self) -> Path:
        return self.path("anchor.md")

    @property
    def active_path(self) -> Path:
        return self.path("active")

    @property
    def ledger_path(self) -> Path:
        return self.path("loop.json")

    @property
    def round_path(self) -> Path:
        return self.path("round.jsonl")

    @property
    def advice_history_path(self) -> Path:
        return self.path("advice_history.md")

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
    def gated_shells_path(self) -> Path:
        return self.path("gated_shells")

    @property
    def advice_path(self) -> Path:
        return Path(tempfile.gettempdir()) / f"ploop_{self.session_id}_advice.md"

    @property
    def narration_path(self) -> Path:
        return Path(tempfile.gettempdir()) / f"ploop_{self.session_id}_narration.md"

    @property
    def candidates_path(self) -> Path:
        return Path(tempfile.gettempdir()) / f"ploop_{self.session_id}_candidates.md"

    def clear_round_state(self) -> None:
        """Remove the per-round loop state (anchor.md and active marker kept).

        Only launch calls this, so the candidates queue empties exactly when a
        fresh anchor starts — a pause, resume, or anomaly end leaves it for the
        drain.
        """
        for path in (
            self.ledger_path,
            self.round_path,
            self.advice_history_path,
            self.advisor_token_path,
            self.advisor_running_path,
            self.compacted_path,
            self.gated_shells_path,
            self.advice_path,
            self.narration_path,
            self.candidates_path,
        ):
            path.unlink(missing_ok=True)


def load_ledger(ledger_file: Path) -> dict:
    """Load the ledger filled with defaults; defaults on any failure.

    Always returns every key, so callers index directly and update by merge
    ({**ledger, "phase": ...}) — an omitted key is preserved, not re-defaulted.
    """
    defaults = {
        "advice_history": [],
        "round_start_line": 1,
        "anomalies": 0,
        "phase": FRESH,
    }
    if not ledger_file.exists():
        return defaults
    try:
        loaded = json.loads(ledger_file.read_text())
    except json.JSONDecodeError, OSError:
        return defaults
    return {**defaults, **loaded} if isinstance(loaded, dict) else defaults


def save_ledger(ledger_file: Path, ledger: dict) -> None:
    """Persist the ledger dict as-is.

    Callers build the next ledger by merge ({**ledger, ...}), so preservation is
    the default and only the changed fields are named at each transition.
    """
    ledger_file.write_text(json.dumps(ledger))
