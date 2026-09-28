"""The unattended guard: a refine workflow launch marks its session unattended
(only in bypassPermissions), and a marked session never leaves a dialog to a
human — while every other session keeps the usual flow."""

import io
import json

import pytest

from src import guard

OWN = str(guard.WORKFLOWS / "code" / "workflow.js")
PRINCIPLES = str(guard.WORKFLOWS / "code" / "principles.md")


def hook(monkeypatch, capsys, entry, **event):
    monkeypatch.setattr(
        "sys.stdin", io.StringIO(json.dumps({"session_id": "s1", **event}))
    )
    try:
        entry()
    except SystemExit as exc:
        assert exc.code == 0
    out = capsys.readouterr().out
    return json.loads(out)["hookSpecificOutput"] if out else None


@pytest.fixture
def data(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
    return tmp_path


def launch(monkeypatch, capsys, mode="bypassPermissions", **tool_input):
    return hook(
        monkeypatch,
        capsys,
        guard.arm,
        hook_event_name="PreToolUse",
        tool_name="Workflow",
        permission_mode=mode,
        tool_input=tool_input or {"scriptPath": OWN, "args": {}},
    )


@pytest.mark.parametrize(
    "call",
    [
        {"scriptPath": OWN, "args": {"principlesPath": PRINCIPLES}},
        {"script": "export const meta = {}", "args": {"principlesPath": PRINCIPLES}},
        {
            "script": "export const meta = {}",
            "args": json.dumps({"principlesPath": PRINCIPLES}),
        },
    ],
)
def test_own_run_in_bypass_marks_the_session(data, monkeypatch, capsys, call):
    """The run is recognized by what it names — bootstrap's script path, or the
    principles path its args carry when the same run arrives as an inline
    script or a resume with string args."""
    assert launch(monkeypatch, capsys, **call) is None
    assert (data / "s1_unattended").exists()


@pytest.mark.parametrize("mode", ["auto", "default", None])
def test_own_workflow_outside_bypass_is_refused_unmarked(
    data, monkeypatch, capsys, mode
):
    """The effective mode rides the event; anything but bypass would hand the
    whole run to the guard's denials, so the launch itself is refused."""
    out = launch(monkeypatch, capsys, mode=mode)
    assert out["permissionDecision"] == "deny"
    assert (
        "claude --permission-mode bypassPermissions" in out["permissionDecisionReason"]
    )
    assert not (data / "s1_unattended").exists()


def test_another_workflow_is_none_of_refines_business(data, monkeypatch, capsys):
    """A workflow outside this plugin neither arms nor needs the mode."""
    for call in (
        {"scriptPath": str(data / "workflow.js"), "args": {}},
        {"script": "export const meta = {}", "args": "not json"},
    ):
        assert launch(monkeypatch, capsys, mode="auto", **call) is None
    assert not (data / "s1_unattended").exists()


def test_unmarked_session_keeps_its_dialogs(data, monkeypatch, capsys):
    out = hook(
        monkeypatch,
        capsys,
        guard.guard,
        hook_event_name="PermissionRequest",
        tool_name="Bash",
    )
    assert out is None


def test_marked_session_answers_every_dialog(data, monkeypatch, capsys):
    """Once marked — by the run, for the rest of the session — permission
    requests are denied with a reason fitted to the tool, plan mode is refused
    before entry, and elicitations are declined.  Nothing is ever allowed."""
    launch(monkeypatch, capsys)

    def ask(**event):
        return hook(monkeypatch, capsys, guard.guard, agent_id="a1", **event)

    bash = ask(hook_event_name="PermissionRequest", tool_name="Bash")["decision"]
    assert bash["behavior"] == "deny"
    assert "exact absolute path" in bash["message"]
    question = ask(hook_event_name="PermissionRequest", tool_name="AskUserQuestion")
    assert question["decision"] == {
        "behavior": "deny",
        "message": guard.QUESTION_DENIAL,
    }
    plan = ask(hook_event_name="PreToolUse", tool_name="EnterPlanMode")
    assert plan["permissionDecision"] == "deny"
    assert ask(hook_event_name="PreToolUse", tool_name="Read") is None
    assert ask(hook_event_name="Elicitation") == {
        "hookEventName": "Elicitation",
        "action": "decline",
    }
