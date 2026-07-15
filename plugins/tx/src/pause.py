"""UserPromptExpansion commands — /tx:git-sync-off|on toggle the sync pause.

The pause marker silences the sync guards (see repo.pause_marker); these two
commands are its whole interface.  off touches the marker, on removes it —
each converges on its state no matter how often it runs, so the skill bodies
always report the reached state truthfully.  Outside a git repository there is
no marker to manage: the expansion is blocked — pure, the turn erased — so the
body never announces a toggle that didn't happen.
"""

import json
import sys
from pathlib import Path

from src.repo import pause_marker


def block_expansion(reason: str) -> None:
    """Deny the expansion (decision: block) — pure, the turn erased."""
    sys.stdout.write(
        json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False)
    )
    sys.exit(0)


def resolve_marker(command: str) -> Path:
    """The pause marker, once the stdin event is verified as `command`'s expansion.

    A malformed event or another command's expansion exits 0 untouched (never
    break the session, never interfere with a foreign command); outside a git
    repository the expansion is blocked with the reason shown to the user.
    """
    try:
        event = json.loads(sys.stdin.read())
    except json.JSONDecodeError, OSError:
        sys.exit(0)
    if not isinstance(event, dict) or event.get("command_name", "") != command:
        sys.exit(0)
    marker = pause_marker()
    if marker is None:
        block_expansion("Not a git repository — tx sync cannot be toggled here.")
    return marker


def off() -> None:
    resolve_marker("tx:git-sync-off").touch()


def on() -> None:
    resolve_marker("tx:git-sync-on").unlink(missing_ok=True)
