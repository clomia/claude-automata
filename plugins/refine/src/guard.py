"""Unattended guard — a refine run has nobody at the terminal.

A run lasts hours and every agent in it works alone, so a dialog is a stall:
background agents surface their permission prompts in the main session, and no
one answers them.  Two hook entries keep the run from ever waiting on a human.

- arm (PreToolUse, matcher Workflow): the launch of this plugin's own workflow
  is the moment the session becomes unattended — both entry paths (a typed
  /refine:<skill> and the model invoking the skill) end in a Workflow call, and
  so does a resume.  The call is this plugin's when it names this plugin's
  workflow material: the script path bootstrap prints, or the principles path
  its args carry — the same run handed over as an inline script, or resumed
  with the same args, still names it.  The run starts only in bypassPermissions, read from the event (the
  effective mode — a repository's settings cannot grant it); otherwise the
  launch is refused with the way to start such a session.
- guard (PreToolUse EnterPlanMode, PermissionRequest, Elicitation): in a marked
  session — the main agent and every agent of the run, whose events carry the
  session's id — permission requests are denied with a reason the agent can act
  on, plan mode is refused before entry (only a human approves its exit), and
  MCP elicitations are declined.  Nothing is ever allowed: the guard removes the
  wait, never the approval.  An unmarked session is left to the usual flow.

The mark lasts the session's life: the turns after a run are no more attended
than the run itself (human work belongs in a fresh session).
"""

import json
import os
import sys
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parent.parent / "skills"

MODE_REFUSAL = (
    "refine runs unattended and starts only in bypassPermissions mode: start "
    "Claude Code with `claude --permission-mode bypassPermissions` (a "
    "repository's settings cannot grant this mode), then launch the workflow "
    "again."
)
QUESTION_DENIAL = (
    "Unattended refine run: nobody is here to answer. Decide yourself, state "
    "the assumption you made, and continue."
)
PLAN_MODE_DENIAL = (
    "Unattended refine run: leaving plan mode needs a human's approval, which "
    "never comes. Plan in your own reasoning and act."
)


def permission_denial(tool: str) -> str:
    return (
        f"Unattended refine run: no human can approve this {tool} call, so it "
        "is denied. Do not retry it as written — rework the step so it needs no "
        "approval, or leave it undone, record why, and continue. A removal names "
        "its exact absolute path: never /, a top-level directory, ~, the working "
        "directory or its parents, or a variable followed by / or /*."
    )


def read_event() -> dict:
    """The hook event from stdin; unreadable input leaves the action alone."""
    try:
        return json.loads(sys.stdin.read())
    except json.JSONDecodeError, OSError:
        sys.exit(0)


def marker(event: dict) -> Path:
    session = str(event.get("session_id", ""))
    return Path(os.environ["CLAUDE_PLUGIN_DATA"]) / f"{session}_unattended"


def answer(hook_event: str, **fields: object) -> None:
    sys.stdout.write(
        json.dumps({"hookSpecificOutput": {"hookEventName": hook_event, **fields}})
    )


def inside(path: object) -> bool:
    return (
        isinstance(path, str)
        and bool(path)
        and WORKFLOWS in Path(path).resolve().parents
    )


def own_run(tool_input: dict) -> bool:
    """True iff the Workflow call runs one of this plugin's workflows."""
    args = tool_input.get("args")
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            args = None
    principles = args.get("principlesPath") if isinstance(args, dict) else None
    return inside(tool_input.get("scriptPath")) or inside(principles)


def arm() -> None:
    event = read_event()
    tool_input = event.get("tool_input") or {}
    if not isinstance(tool_input, dict) or not own_run(tool_input):
        sys.exit(0)
    if event.get("permission_mode") != "bypassPermissions":
        answer(
            "PreToolUse",
            permissionDecision="deny",
            permissionDecisionReason=MODE_REFUSAL,
        )
        sys.exit(0)
    path = marker(event)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def guard() -> None:
    event = read_event()
    if not marker(event).exists():
        sys.exit(0)
    tool = str(event.get("tool_name") or "tool")
    match event.get("hook_event_name"):
        case "PreToolUse" if tool == "EnterPlanMode":
            answer(
                "PreToolUse",
                permissionDecision="deny",
                permissionDecisionReason=PLAN_MODE_DENIAL,
            )
        case "PermissionRequest":
            message = (
                QUESTION_DENIAL
                if tool == "AskUserQuestion"
                else permission_denial(tool)
            )
            answer(
                "PermissionRequest", decision={"behavior": "deny", "message": message}
            )
        case "Elicitation":
            answer("Elicitation", action="decline")
