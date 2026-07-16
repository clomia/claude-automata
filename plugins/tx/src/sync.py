"""Stop guard — nudge sync when origin/<base> has pulled ahead of a transaction.

Invariant: on a `tx-*` branch, origin/<base>'s first-parent history must stay an
ancestor of HEAD.  When it pulls ahead (ahead > 0) the main agent's Stop is
blocked to compel a sync — no permanent snooze; it re-announces until the
invariant is restored.  The base branch is the GitHub default branch read from
the local origin/HEAD mirror; when the mirror is unset the guard stays off.

Exception: the `<git-dir>/tx-pause` marker disables this entirely —
/tx:git-sync-off sets it, /tx:git-sync-on clears it.  A mid-flight rebase
invalidates long-running analysis (large refactors, spec sync), so such work
turns the sync off and back on around itself.  (If the pause lingers,
SessionStart re-warns.)

Multi-session safety:
- flock(LOCK_EX): atomic read-modify-write of the state file
- FETCH_TTL_SECONDS: throttle concurrent origin fetches
- DEDUPE_TTL_SECONDS: within the window only one session announces a given
  origin sha (window expiry re-announces — if ignored it keeps nudging; a new
  sha announces immediately)
"""

import fcntl
import json
import math
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TypedDict, cast

from src.repo import (
    base_ahead_count,
    base_branch,
    current_branch,
    fetch_base,
    git,
    git_dir,
    is_tx_branch,
    rebase_cmd,
    sync_paused,
)

FETCH_TTL_SECONDS = 30
DEDUPE_TTL_SECONDS = 600
STATE_FILENAME = "tx-sync-state.json"


class SyncState(TypedDict, total=False):
    last_fetch_ts: float
    last_announced_origin_sha: str
    last_announced_ts: float


def load_json_dict(raw: str) -> dict[str, object] | None:
    if not raw:
        return None
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(loaded, dict):
        return None
    return cast(dict[str, object], loaded)


def finite_ts(value: object) -> float | None:
    """A finite numeric timestamp, or None (bool is not a timestamp)."""
    if (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    ):
        return float(value)
    return None


def parse_state(raw: str) -> SyncState:
    data = load_json_dict(raw) or {}
    state = SyncState()
    if (fetch_ts := finite_ts(data.get("last_fetch_ts"))) is not None:
        state["last_fetch_ts"] = fetch_ts
    sha = data.get("last_announced_origin_sha")
    if isinstance(sha, str):
        state["last_announced_origin_sha"] = sha
    if (announced_ts := finite_ts(data.get("last_announced_ts"))) is not None:
        state["last_announced_ts"] = announced_ts
    return state


@contextmanager
def locked_state(path: Path) -> Iterator[SyncState]:
    path.touch(exist_ok=True)
    with path.open("r+", encoding="utf-8", errors="replace") as fp:
        fcntl.flock(fp.fileno(), fcntl.LOCK_EX)
        try:
            state = parse_state(fp.read())
            yield state
            fp.seek(0)
            fp.truncate()
            fp.write(json.dumps(state))
            fp.flush()
        finally:
            fcntl.flock(fp.fileno(), fcntl.LOCK_UN)


def state_path() -> Path | None:
    gd = git_dir()
    return gd / STATE_FILENAME if gd else None


def maybe_fetch(state: SyncState, base: str) -> None:
    now = time.time()
    elapsed = now - state.get("last_fetch_ts", 0.0)
    if 0 <= elapsed < FETCH_TTL_SECONDS:
        return
    if fetch_base(base):
        state["last_fetch_ts"] = now


def build_reason(ahead: int, base: str) -> str:
    return (
        f"Local is {ahead} commit(s) behind origin/{base}. "
        f"Fetch and sync locally: {rebase_cmd(base)}. "
        "It must complete cleanly — be ready for conflicts."
    )


def should_announce(
    state: SyncState, ahead: int, origin_sha: str, base: str, now: float
) -> str | None:
    """Dedupe policy (pure): the reason to announce, or None. Mutates state on announce.

    The same origin sha is announced at most once per DEDUPE_TTL_SECONDS window;
    a new sha announces immediately, and window expiry re-announces so an ignored
    nudge keeps returning until the invariant is restored.
    """
    if ahead <= 0:
        return None
    same_sha = bool(origin_sha) and origin_sha == state.get("last_announced_origin_sha")
    elapsed = now - state.get("last_announced_ts", 0.0)
    if same_sha and 0 <= elapsed < DEDUPE_TTL_SECONDS:
        return None

    state["last_announced_origin_sha"] = origin_sha
    state["last_announced_ts"] = now
    return build_reason(ahead, base)


def decide_announcement(state: SyncState, base: str) -> str | None:
    maybe_fetch(state, base)
    ahead = base_ahead_count(base) or 0
    if ahead <= 0:
        return None
    origin_sha = git("rev-parse", f"origin/{base}") or ""
    return should_announce(state, ahead, origin_sha, base, time.time())


def is_stop_hook_active(data: dict[str, object] | None) -> bool:
    return bool(data and data.get("stop_hook_active"))


# Background task types that hold or mutate the working tree.  While one is in
# flight the harness stops the session but wakes it again on completion (their
# specs promise a notification/re-invoke), so the rebase nudge is deferred until
# the tree is genuinely idle — a mid-flight rebase would rewrite tracked files
# under that work, the exact hazard /tx:git-sync-off guards against.  monitor,
# teammate, and cron never complete, so they never gate.
WORKTREE_BACKGROUND_TYPES = ("shell", "subagent", "workflow")


def worktree_work_in_flight(data: dict[str, object] | None) -> bool:
    tasks = (data or {}).get("background_tasks")
    if not isinstance(tasks, list):
        return False
    return any(
        isinstance(t, dict) and t.get("type") in WORKTREE_BACKGROUND_TYPES
        for t in tasks
    )


def main() -> None:
    event = load_json_dict(sys.stdin.read())
    if is_stop_hook_active(event):
        return

    # Defer the nudge while worktree-holding background work is still running —
    # the completion event re-wakes the session, and the sha-dedupe re-announces
    # at the next genuinely idle stop, so nothing is lost.
    if worktree_work_in_flight(event):
        return

    if sync_paused():
        return

    branch = current_branch()
    if not branch or not is_tx_branch(branch):
        return

    base = base_branch()
    if base is None:
        return

    path = state_path()
    if path is None:
        return

    with locked_state(path) as state:
        announcement = decide_announcement(state, base)

    if announcement is None:
        return

    json.dump(
        {"decision": "block", "reason": announcement}, sys.stdout, ensure_ascii=False
    )


if __name__ == "__main__":
    main()
