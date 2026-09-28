"""The unattended contract — ploop and refine answer the same dialogs of their
own unattended sessions, with the same words (root ARCHITECTURE, 무인 계약).

Each plugin owns its guard (plugin runtimes share no code), so nothing but this
check keeps the two copies from drifting apart: the wiring, and the answers the
real runners give to the same events.
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

# (event, matcher) pairs every autonomous plugin routes to its guard entry.
ANSWERED = {
    ("PermissionRequest", None),
    ("PreToolUse", "EnterPlanMode"),
    ("Elicitation", None),
}

# How each plugin marks a session unattended, under its own data dir.
MARKED = {"ploop": "s1_anchor.md", "refine": "s1_unattended"}

EVENTS = [
    {"hook_event_name": "PermissionRequest", "tool_name": "Bash"},
    {"hook_event_name": "PermissionRequest", "tool_name": "AskUserQuestion"},
    {"hook_event_name": "PreToolUse", "tool_name": "EnterPlanMode"},
    {"hook_event_name": "Elicitation", "mcp_server_name": "m"},
]


def guarded(plugin: str) -> set[tuple[str, str | None]]:
    hooks = json.loads((REPO / "plugins" / plugin / "hooks" / "hooks.json").read_text())
    return {
        (event, group.get("matcher"))
        for event, groups in hooks["hooks"].items()
        for group in groups
        for handler in group["hooks"]
        if handler.get("args") == ["guard"]
    }


def answer(plugin: str, data: Path, event: dict) -> dict:
    data.mkdir(parents=True, exist_ok=True)
    (data / MARKED[plugin]).write_text("")
    done = subprocess.run(
        [str(REPO / "plugins" / plugin / "bin" / f"{plugin}-hook"), "guard"],
        input=json.dumps({"session_id": "s1", **event}),
        env={
            **{k: v for k, v in os.environ.items() if not k.startswith("CLAUDE")},
            "CLAUDE_PLUGIN_DATA": str(data),
        },
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


@pytest.mark.parametrize("plugin", ["ploop", "refine"])
def test_guard_answers_every_dialog_kind(plugin):
    assert ANSWERED <= guarded(plugin)


@pytest.mark.parametrize(
    "event", EVENTS, ids=lambda e: e.get("tool_name", e["hook_event_name"])
)
def test_both_guards_give_the_same_answer(tmp_path, event):
    ploop = answer("ploop", tmp_path / "ploop", event)
    assert ploop == answer("refine", tmp_path / "refine", event)
