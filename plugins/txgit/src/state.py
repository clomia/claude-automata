"""SessionStart guard — surface branch state: protected branch, stale transaction, base ahead."""

import json
import re
import sys
from datetime import UTC, datetime, timedelta

from src.repo import (
    base_ahead_count,
    base_branch,
    current_branch,
    fetch_base,
    git,
    is_tx_branch,
    pause_marker,
)

TX_AGE_LIMIT = timedelta(hours=24)
BASE_AHEAD_THRESHOLD = 1
REFLOG_TIMESTAMP_RE = re.compile(r"@\{([^}]+)\}")


def tx_open_time(branch: str) -> datetime | None:
    """Timestamp of the branch's oldest reflog entry — when the transaction opened."""
    out = git("reflog", "show", "--date=iso-strict", branch)
    if not out:
        return None
    match = REFLOG_TIMESTAMP_RE.search(out.splitlines()[-1])
    if not match:
        return None
    try:
        return datetime.fromisoformat(match.group(1))
    except ValueError:
        return None


def build_messages(branch: str, base: str) -> list[str]:
    if branch == base:
        return [
            f"[branch-state-warn] You are on '{branch}' (protected). Open a transaction first: /txgit:tx-open"
        ]

    messages: list[str] = []

    if is_tx_branch(branch):
        opened_at = tx_open_time(branch)
        if opened_at:
            age = datetime.now(UTC) - opened_at.astimezone(UTC)
            if age > TX_AGE_LIMIT:
                hours = int(age.total_seconds() // 3600)
                messages.append(
                    f"[branch-state-warn] This transaction has been open for {hours}h. "
                    "Reach an integral point and consider splitting it."
                )

    fetch_ok = fetch_base(base)
    ahead = base_ahead_count(base)
    if ahead is not None and ahead >= BASE_AHEAD_THRESHOLD:
        message = (
            f"[branch-state-warn] origin/{base} is {ahead} PR(s) ahead. "
            f"Resolve conflict risk before continuing: git fetch origin {base} && git rebase origin/{base}"
        )
        if not fetch_ok:
            message += " (fetch failed — local view)"
        messages.append(message)

    return messages


def emit(context: str) -> None:
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context,
            }
        },
        sys.stdout,
    )


def main() -> None:
    sys.stdin.read()  # drain — payload unused

    branch = current_branch()
    if not branch:
        return

    marker = pause_marker()
    if marker and marker.exists():
        emit(
            f"[branch-state-warn] txgit sync is paused by the {marker} marker "
            f"(protecting long-running analysis). If the analysis is done, remove it: rm -f {marker}"
        )
        return

    messages = build_messages(branch, base_branch())
    if not messages:
        return

    emit("\n".join(messages))


if __name__ == "__main__":
    main()
