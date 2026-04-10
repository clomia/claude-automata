"""Update notifier — SessionStart hook that surfaces newer parallax releases.

Runs on SessionStart with source in {startup, clear}.  Reads the installed
version from pyproject.toml, fetches the remote marketplace manifest under
a 6-hour cooldown, and emits a user-visible systemMessage JSON envelope
to stdout when the remote version is strictly newer.

Fails silently on every error path — missing env, network, parse, recursion
guard — to guarantee session startup is never delayed or disrupted.

State is a single file ${CLAUDE_PLUGIN_DATA}/update_cache.json, independent
from the per-session {session_id}_* files used by the other parallax hooks.
"""

import json
import os
import sys
import time
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

REMOTE_URL = "https://raw.githubusercontent.com/clomia/claude-automata/main/.claude-plugin/marketplace.json"
PLUGIN_NAME = "parallax"
COOLDOWN_SECONDS = 6 * 60 * 60
HTTP_TIMEOUT = 3.0
CACHE_FILENAME = "update_cache.json"


def read_local_version(plugin_root: Path) -> str | None:
    """Read the installed plugin version from pyproject.toml."""
    try:
        with (plugin_root / "pyproject.toml").open("rb") as f:
            return tomllib.load(f)["project"]["version"]
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        return None


def fetch_remote_version() -> str | None:
    """HTTP GET the marketplace manifest and extract the parallax version."""
    try:
        request = urllib.request.Request(
            REMOTE_URL,
            headers={"User-Agent": f"{PLUGIN_NAME}-update-check"},
        )
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
            manifest = json.loads(response.read())
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return None

    for entry in manifest.get("plugins", []):
        if entry.get("name") == PLUGIN_NAME:
            return entry.get("version")
    return None


def parse_version(v: str) -> tuple[int, ...]:
    """Parse a dotted numeric version string. Raises ValueError on non-numeric parts."""
    return tuple(int(part) for part in v.split("."))


def is_newer(remote: str, local: str) -> bool:
    """Strict newer comparison. Returns False on any parse error."""
    try:
        return parse_version(remote) > parse_version(local)
    except (ValueError, AttributeError):
        return False


def load_cache(cache_file: Path) -> dict:
    """Load the update cache. Returns empty dict on any failure."""
    if not cache_file.exists():
        return {}
    try:
        return json.loads(cache_file.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def save_cache(cache_file: Path, payload: dict) -> None:
    """Atomic write via tempfile + rename to survive concurrent sessions."""
    tmp = cache_file.parent / (cache_file.name + ".tmp")
    try:
        tmp.write_text(json.dumps(payload))
        tmp.replace(cache_file)
    except OSError:
        tmp.unlink(missing_ok=True)


def check_for_update() -> None:
    """SessionStart hook entry point."""
    # Drain stdin to prevent pipe-close races in hook execution.
    try:
        sys.stdin.read()
    except OSError:
        pass

    # Never run inside claude -p subprocesses spawned by the Stop hook.
    if os.environ.get("PARALLAX_INSIDE_RECURSION") == "1":
        return

    plugin_root_env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    data_dir_env = os.environ.get("CLAUDE_PLUGIN_DATA")
    if not plugin_root_env or not data_dir_env:
        return

    plugin_root = Path(plugin_root_env)
    data_dir = Path(data_dir_env)

    local_version = read_local_version(plugin_root)
    if local_version is None:
        return

    try:
        data_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return

    cache_file = data_dir / CACHE_FILENAME
    cache = load_cache(cache_file)
    now = time.time()
    last_check = cache.get("last_check_ts", 0.0)
    cached_remote = cache.get("remote_version")

    # Cooldown gate: fetch fresh remote version at most once per COOLDOWN window.
    # On network failure, still refresh the timestamp to avoid hammering the
    # remote on every session when the user is offline.
    if now - last_check >= COOLDOWN_SECONDS:
        fetched = fetch_remote_version()
        if fetched is not None:
            cached_remote = fetched
        save_cache(
            cache_file,
            {"last_check_ts": now, "remote_version": cached_remote},
        )

    if cached_remote and is_newer(cached_remote, local_version):
        message = (
            f"parallax update available: {local_version} -> {cached_remote}\n"
            f"Run: claude plugin marketplace update claude-automata "
            f"&& claude plugin update parallax@claude-automata"
        )
        sys.stdout.write(json.dumps({"systemMessage": message}))


if __name__ == "__main__":
    check_for_update()
