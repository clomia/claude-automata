"""The unattended contract's wiring — ploop and refine each answer the same
dialogs of their own unattended sessions (root ARCHITECTURE, 무인 계약).

Each plugin owns its guard, so nothing but this check keeps the two from
drifting apart when a dialog kind is added to one of them.
"""

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

# (event, matcher) pairs every autonomous plugin routes to its guard entry.
ANSWERED = {
    ("PermissionRequest", None),
    ("PreToolUse", "EnterPlanMode"),
    ("Elicitation", None),
}


def guarded(plugin: str) -> set[tuple[str, str | None]]:
    hooks = json.loads((REPO / "plugins" / plugin / "hooks" / "hooks.json").read_text())
    return {
        (event, group.get("matcher"))
        for event, groups in hooks["hooks"].items()
        for group in groups
        for handler in group["hooks"]
        if handler.get("args") == ["guard"]
    }


@pytest.mark.parametrize("plugin", ["ploop", "refine"])
def test_guard_answers_every_dialog_kind(plugin):
    assert ANSWERED <= guarded(plugin)
