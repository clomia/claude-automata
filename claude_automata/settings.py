"""Settings — merge the claude-automata prerequisites into a Claude Code settings payload."""

import copy
import json
from importlib.resources import files
from pathlib import Path

MARKETPLACE = "claude-automata"
MARKETPLACE_REPO = "clomia/claude-automata"

PREREQUISITES = {
    "alwaysThinkingEnabled": True,
    "autoMemoryEnabled": False,
    "autoCompactEnabled": True,
    "model": "opus[1m]",
}

# Claude Code grants these modes only from user, managed, or command-line
# settings; from a repository's settings they are ignored and shadow the
# user's own mode, dropping the session to Manual.  Autonomous runs check the
# mode themselves when they start.
IGNORED_MODES = ("bypassPermissions", "auto")


def manifest() -> dict:
    # The wheel carries the manifest via force-include; a source-tree run reads the repo copy.
    resource = files("claude_automata").joinpath("marketplace.json")
    if resource.is_file():
        return json.loads(resource.read_text())
    repo_copy = Path(__file__).parents[1] / ".claude-plugin" / "marketplace.json"
    return json.loads(repo_copy.read_text())


def plugin_names() -> list[str]:
    return [plugin["name"] for plugin in manifest()["plugins"]]


def merged(current: dict) -> dict:
    """Return `current` with every prerequisite applied and an ignored permission
    mode removed; unrelated keys survive."""
    out = copy.deepcopy(current)
    out.update(PREREQUISITES)
    permissions = out.get("permissions")
    if (
        isinstance(permissions, dict)
        and permissions.get("defaultMode") in IGNORED_MODES
    ):
        del permissions["defaultMode"]
        if not permissions:
            del out["permissions"]
    out.setdefault("env", {})["CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"] = "5"
    out.setdefault("extraKnownMarketplaces", {})[MARKETPLACE] = {
        "source": {"source": "github", "repo": MARKETPLACE_REPO}
    }
    enabled = out.setdefault("enabledPlugins", {})
    for name in plugin_names():
        enabled[f"{name}@{MARKETPLACE}"] = True
    return out


def overridden(local: dict) -> list[str]:
    """Prerequisite keys a higher-precedence settings.local.json forces away from init's values."""
    return [
        key
        for key, value in PREREQUISITES.items()
        if key in local and local[key] != value
    ]
