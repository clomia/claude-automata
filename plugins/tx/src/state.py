"""SessionStart guard — surface branch state: protected branch, stale transaction, base ahead.

This is the one guard that pays for network: it heals a missing origin/HEAD
mirror (set_origin_head) and fetches the base to measure drift.  The hot-path
guards read the mirror this guard and the skills maintain.  The sync pause
silences only the rebase pressure (the ahead warning) — protected-branch and
stale-transaction warnings still surface while it lingers.
"""

import json
import re
import sys
from datetime import UTC, datetime, timedelta

from src.repo import (
    ahead_notice,
    base_ahead_count,
    base_branch,
    current_branch,
    fetch_base,
    git,
    has_origin,
    is_tx_branch,
    rebase_cmd,
    set_origin_head,
    sync_paused,
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


def build_messages(branch: str, base: str, paused: bool) -> list[str]:
    if branch == base:
        return [
            f"[branch-state-warn] You are on '{branch}' (protected). Open a transaction first: /tx:open"
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

    if paused:
        messages.append(
            "[branch-state-warn] tx git-sync is off (protecting long-running "
            "analysis). If that work is done, turn it back on: /tx:git-sync-on"
        )
        return messages

    fetch_ok = fetch_base(base)
    ahead = base_ahead_count(base)
    if ahead is not None and ahead >= BASE_AHEAD_THRESHOLD:
        message = (
            f"[branch-state-warn] {ahead_notice(ahead, base)}. "
            f"Resolve conflict risk before continuing: {rebase_cmd(base)}"
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
    if not branch or not has_origin():
        return  # not a repository, or no origin remote — tx does not apply

    base = base_branch()
    if base is None:
        set_origin_head()
        base = base_branch()
    if base is None:
        emit(
            "[branch-state-warn] Cannot resolve the GitHub default branch "
            "(origin/HEAD is unset). Run: git remote set-head origin --auto "
            "— tx guards stay off until it resolves."
        )
        return

    messages = build_messages(branch, base, sync_paused())
    if not messages:
        return

    emit("\n".join(messages))


if __name__ == "__main__":
    main()
