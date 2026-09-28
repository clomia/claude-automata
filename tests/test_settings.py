import copy
import json
from pathlib import Path

from claude_automata import settings

REPO_MANIFEST = json.loads(
    (Path(__file__).parents[1] / ".claude-plugin" / "marketplace.json").read_text()
)


def test_fresh_merge_carries_all_prerequisites():
    out = settings.merged({})
    assert out["alwaysThinkingEnabled"] is True
    assert out["autoMemoryEnabled"] is False
    assert out["autoCompactEnabled"] is True
    assert out["model"] == "opus[1m]"
    assert "permissions" not in out  # init writes no permission mode
    assert out["env"]["CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"] == "5"
    assert out["extraKnownMarketplaces"]["claude-automata"] == {
        "source": {"source": "github", "repo": "clomia/claude-automata"}
    }
    for plugin in REPO_MANIFEST["plugins"]:
        assert out["enabledPlugins"][f"{plugin['name']}@claude-automata"] is True


def test_existing_settings_survive():
    current = {
        "statusLine": {"type": "command", "command": "x"},
        "permissions": {"allow": ["Bash(ls)"]},
        "env": {"HTTP_PROXY": "http://proxy"},
        "enabledPlugins": {"foreign@other": True},
        "extraKnownMarketplaces": {
            "other": {"source": {"source": "github", "repo": "a/b"}}
        },
    }
    snapshot = copy.deepcopy(current)
    out = settings.merged(current)
    assert current == snapshot  # input is not mutated
    assert out["statusLine"] == {"type": "command", "command": "x"}
    assert out["permissions"] == {"allow": ["Bash(ls)"]}
    assert out["env"]["HTTP_PROXY"] == "http://proxy"  # existing env key survives
    assert out["env"]["CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"] == "5"
    assert out["enabledPlugins"]["foreign@other"] is True
    assert out["extraKnownMarketplaces"]["other"] == {
        "source": {"source": "github", "repo": "a/b"}
    }


def test_ignored_mode_is_removed_other_modes_kept():
    """A repository's bypassPermissions/auto is ignored by Claude Code and shadows
    the user's mode — the value earlier inits wrote converges away; a mode the
    repository may legitimately pin stays."""
    stale = {"permissions": {"defaultMode": "bypassPermissions", "deny": ["X"]}}
    assert settings.merged(stale)["permissions"] == {"deny": ["X"]}
    assert "permissions" not in settings.merged(
        {"permissions": {"defaultMode": "auto"}}
    )
    assert settings.merged({"permissions": {"defaultMode": "plan"}})["permissions"] == {
        "defaultMode": "plan"
    }


def test_rerun_converges():
    once = settings.merged({})
    assert settings.merged(once) == once


def test_overridden_flags_conflicting_local_settings():
    assert settings.overridden({}) == []
    assert settings.overridden({"model": "opus[1m]"}) == []
    assert settings.overridden({"model": "sonnet", "autoMemoryEnabled": False}) == [
        "model"
    ]
    assert settings.overridden({"permissions": {"defaultMode": "plan"}}) == []
