"""Marketplace-wide update alert — one SessionStart notice for every claude-automata plugin.

Installed as a dependency of every plugin in the marketplace, so a single hook
watches them all.  Installed versions come from the documented CLI
(`claude plugin list --json`), scoped to the plugins this session actually
loaded — user scope plus the current project — and read fresh on every fire so
the notice clears the moment the user updates.  A stale copy pinned in an
unrelated project never leaks into this session's notice.  Published versions
come from the plugin manifests on the repository's main branch, fetched under a
6-hour cooldown.  When any of this session's plugins is behind, one user-visible
systemMessage names them all — updates are applied interactively in /plugin, so
the notice points there and nowhere else.

The notice re-emits on every fire (startup, resume, clear) until the user
updates; only the fetch is cooled.  `compact` is deliberately excluded from
the matcher: long-running loops compact often and would spam it.  Alert-only
by design: a running session is never mutated from under itself — the user
chooses when to update.

Fails silently on every error path — missing env, network, CLI, parse — to
guarantee session startup is never delayed or disrupted.

State: ${CLAUDE_PLUGIN_DATA}/update_cache.json, written atomically.
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

MARKETPLACE = "claude-automata"
RAW_ROOT = "https://raw.githubusercontent.com/clomia/claude-automata/main"
COOLDOWN_SECONDS = 6 * 60 * 60
HTTP_TIMEOUT = 3.0
CLI_TIMEOUT = 10.0
CACHE_FILENAME = "update_cache.json"


def http_json(url: str) -> object | None:
    """GET a JSON document; None on any network or parse failure."""
    request = urllib.request.Request(url, headers={"User-Agent": "version-up-alert"})
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
            return json.loads(response.read())
    except OSError, json.JSONDecodeError:
        return None


def fetch_remote_versions() -> dict[str, str] | None:
    """Published versions from the marketplace listing on the repository's main branch.

    None when the listing itself is unreachable (the caller keeps its previous
    snapshot); a plugin whose manifest fails to load or parse is skipped.
    """
    listing = http_json(f"{RAW_ROOT}/.claude-plugin/marketplace.json")
    if not isinstance(listing, dict):
        return None
    entries = listing.get("plugins")
    versions: dict[str, str] = {}
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        name, source = entry.get("name"), entry.get("source")
        if not isinstance(name, str) or not isinstance(source, str):
            continue
        manifest = http_json(
            f"{RAW_ROOT}/{source.removeprefix('./')}/.claude-plugin/plugin.json"
        )
        if isinstance(manifest, dict) and isinstance(manifest.get("version"), str):
            versions[name] = manifest["version"]
    return versions


def installed_versions(project_dir: str | None) -> dict[str, str]:
    """Versions of this marketplace's plugins active in the current session.

    `claude plugin list --json` reports every install on the machine; only user
    scope and the entries pinned to project_dir belong to this session — an
    unrelated project's stale copy is ignored so updating here can clear the
    notice.  A plugin present at several of this session's scopes keeps its
    oldest version.  {} on any failure.
    """
    try:
        result = subprocess.run(
            ["claude", "plugin", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=CLI_TIMEOUT,
            check=False,
        )
        plugins = json.loads(result.stdout) if result.returncode == 0 else None
    except OSError, subprocess.TimeoutExpired, json.JSONDecodeError:
        return {}
    versions: dict[str, str] = {}
    for plugin in plugins if isinstance(plugins, list) else []:
        if not isinstance(plugin, dict) or not plugin.get("enabled", True):
            continue
        if plugin.get("scope") != "user" and plugin.get("projectPath") != project_dir:
            continue
        plugin_id, version = plugin.get("id"), plugin.get("version")
        if not isinstance(plugin_id, str) or not isinstance(version, str):
            continue
        name, _, marketplace = plugin_id.rpartition("@")
        if marketplace != MARKETPLACE:
            continue
        if name not in versions or is_newer(versions[name], version):
            versions[name] = version
    return versions


def parse_version(v: str) -> tuple[int, ...]:
    """Dotted numeric version; raises ValueError on non-numeric parts."""
    return tuple(int(part) for part in v.split("."))


def is_newer(a: str, b: str) -> bool:
    """Strict a > b; False on any parse failure."""
    try:
        return parse_version(a) > parse_version(b)
    except ValueError:
        return False


def outdated(remote: dict[str, str], local: dict[str, str]) -> list[str]:
    """One `name local > remote` row per installed plugin with a newer release."""
    return [
        f"{name} {local[name]} > {remote[name]}"
        for name in sorted(local)
        if name in remote and is_newer(remote[name], local[name])
    ]


def build_message(rows: list[str]) -> str:
    bracketed = " ".join(f"[{row}]" for row in rows)
    return f"{MARKETPLACE.capitalize()} can now be updated. {bracketed} — /plugin"


def load_cache(cache_file: Path) -> dict:
    """The update cache; {} on any failure."""
    try:
        cache = json.loads(cache_file.read_text())
    except OSError, json.JSONDecodeError:
        return {}
    return cache if isinstance(cache, dict) else {}


def save_cache(cache_file: Path, payload: dict) -> None:
    """Atomic write via tempfile + rename to survive concurrent sessions."""
    tmp = cache_file.parent / (cache_file.name + ".tmp")
    try:
        tmp.write_text(json.dumps(payload))
        tmp.replace(cache_file)
    except OSError:
        tmp.unlink(missing_ok=True)


def cooldown_elapsed(cache: dict, now: float) -> bool:
    """Whether a fresh remote fetch is due (malformed or time-warped ts counts as due)."""
    last_check = cache.get("last_check_ts")
    if not isinstance(last_check, (int, float)) or isinstance(last_check, bool):
        return True
    return not 0 <= now - last_check < COOLDOWN_SECONDS


def read_event() -> dict:
    """SessionStart payload on stdin; {} on any failure."""
    try:
        event = json.loads(sys.stdin.read())
    except OSError, json.JSONDecodeError:
        return {}
    return event if isinstance(event, dict) else {}


def session_project(event: dict) -> str | None:
    """The project this session belongs to — hooks get CLAUDE_PROJECT_DIR; the
    payload's cwd is the fallback.  None when neither is set."""
    for value in (os.environ.get("CLAUDE_PROJECT_DIR"), event.get("cwd")):
        if isinstance(value, str) and value:
            return value
    return None


def check_for_update() -> None:
    """SessionStart hook entry point."""
    event = read_event()

    data_dir = os.environ.get("CLAUDE_PLUGIN_DATA")
    if not data_dir:
        return
    cache_file = Path(data_dir) / CACHE_FILENAME
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return

    cache = load_cache(cache_file)
    remote = cache.get("remote_versions")
    remote = remote if isinstance(remote, dict) else {}

    now = time.time()
    if cooldown_elapsed(cache, now):
        # Claim the window before the slow work: even a killed hook leaves the
        # throttle in place, so a hanging network cannot stall session starts
        # back to back.
        save_cache(cache_file, {"last_check_ts": now, "remote_versions": remote})
        fetched = fetch_remote_versions()
        if fetched is not None:
            remote = fetched
            save_cache(cache_file, {"last_check_ts": now, "remote_versions": remote})

    if not remote:
        return

    rows = outdated(remote, installed_versions(session_project(event)))
    if rows:
        sys.stdout.write(json.dumps({"systemMessage": build_message(rows)}))
