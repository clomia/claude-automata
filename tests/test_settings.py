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
    assert out["permissions"]["defaultMode"] == "bypassPermissions"
    assert out["extraKnownMarketplaces"]["claude-automata"] == {
        "source": {"source": "github", "repo": "clomia/claude-automata"}
    }
    for plugin in REPO_MANIFEST["plugins"]:
        assert out["enabledPlugins"][f"{plugin['name']}@claude-automata"] is True


def test_existing_settings_survive():
    current = {
        "statusLine": {"type": "command", "command": "x"},
        "permissions": {"allow": ["Bash(ls)"]},
        "enabledPlugins": {"foreign@other": True},
        "extraKnownMarketplaces": {
            "other": {"source": {"source": "github", "repo": "a/b"}}
        },
    }
    snapshot = copy.deepcopy(current)
    out = settings.merged(current)
    assert current == snapshot  # input is not mutated
    assert out["statusLine"] == {"type": "command", "command": "x"}
    assert out["permissions"]["allow"] == ["Bash(ls)"]
    assert out["permissions"]["defaultMode"] == "bypassPermissions"
    assert out["enabledPlugins"]["foreign@other"] is True
    assert out["extraKnownMarketplaces"]["other"] == {
        "source": {"source": "github", "repo": "a/b"}
    }


def test_rerun_converges():
    once = settings.merged({})
    assert settings.merged(once) == once


def test_overridden_flags_conflicting_local_settings():
    assert settings.overridden({}) == []
    assert (
        settings.overridden(
            {"model": "opus[1m]", "permissions": {"defaultMode": "bypassPermissions"}}
        )
        == []
    )
    assert settings.overridden({"model": "sonnet", "autoMemoryEnabled": False}) == [
        "model"
    ]
    assert settings.overridden({"permissions": {"defaultMode": "ask"}}) == [
        "permissions.defaultMode"
    ]
