"""Main — ploop hook entry points (one per hooks.json event).

A hook is code and cannot call tools, so the loop is driven by feedback: stop()
blocks the main agent's stop (exit 2) and injects the next instruction — invoke
the advisor, or summarize the finished round log.  The active marker written at
/ploop:launch gates everything; the loop ends when the advisor has no further
advice, or when the user runs /ploop:stop — there is no round cap.  See
ARCHITECTURE.md for the loop design.

Hooks must never break the session: malformed events and missing files degrade
to exit 0 (allow the action).
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.prompt import (
    format_advice_history,
    format_advisor_trigger,
    format_end_notice,
)
from src.state import Workspace, load_ledger, save_ledger
from src.transcript import parse_round_actions

# Sentinel the advisor emits to end the turn.  Checked with `in` so the signal
# survives any surrounding prose the model emits alongside it.
TERMINATION_TOKEN = "I_HAVE_NO_FURTHER_ADVICE_ENDING_THE_PARALLAX_TURN"


def read_event() -> dict:
    """Parse the hook event from stdin; malformed input allows the action."""
    try:
        return json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        sys.exit(0)


def block_expansion(reason: str) -> None:
    """Deny a slash-command expansion (decision: block).

    The turn is erased before submission: the skill body never enters context,
    the reason is shown to the user only, and no state is touched — a live loop
    survives its own guard.
    """
    sys.stdout.write(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


def write_log(
    log_path: Path, round_number: int, narration: str, advice: str | None
) -> None:
    """Append one completed round to the mission log.

    An entry is the round's narrated work — which itself opens with the round's
    advice arriving and being read — followed by that advice verbatim under
    /Advice (round 0 is the mission's initial work, so it has none).  Numbered
    by advice ordinal, so entries stay aligned with advice_history.md even when
    a round is skipped.  launch() starts the file with the mission text; the finished log
    outlives the mission so the whole turn stays reconstructable after any
    compaction.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = f"[[ Round {round_number} - {timestamp} ]]\n\n{narration}\n\n"
    if advice is not None:
        entry += f"[[ Round {round_number} / Advice ]]\n\n{advice}\n\n"
    with open(log_path, "a") as f:
        f.write(entry)


def end_loop(ws: Workspace, current_round: int, advice_history: list[str]) -> None:
    """Terminate the loop: mark it done, drop the active gate, and inject the
    end notice — the main agent reports the end and its cause to the user, with
    a round-log recap when the turn surfaced any advice.

    The advisor ending the turn (termination token / empty advice) is the loop's
    only automatic exit; there is no round cap.  The active marker is dropped,
    so the next stop passes.
    """
    save_ledger(
        ws.ledger_path,
        round_number=current_round,
        advice_history=advice_history,
        done=True,
    )
    ws.active_path.unlink(missing_ok=True)
    sys.stderr.write(
        format_end_notice(
            "the advisor had no further advice to provide",
            log_path=ws.log_path if advice_history else None,
        )
    )
    sys.exit(2)


def stop() -> None:
    """Stop hook: record the advisor's verdict, then end the loop or arm the next round.

    Fires on every main-session stop; the active marker gates it.  advice.md is
    the advisor's sole output channel: its text becomes the round's
    advice-history entry, the termination token (or an absent file — the advisor
    wrote nothing) ends the turn, parallax's rule.  Arming injects the next
    advisor trigger via exit 2.
    """
    event = read_event()
    ws = Workspace.from_env(event.get("session_id", ""))

    if not ws.active_path.exists():
        sys.exit(0)

    ledger = load_ledger(ws.ledger_path)
    if ledger.get("done", False):
        sys.exit(0)
    current_round = ledger.get("round", 0)
    advice_history = ledger.get("advice_history", [])

    # Consume any launching sentinel that outlived the turn boundary (possible only
    # if UserPromptSubmit didn't run before this Stop) so it can't later spare the
    # active marker on an intervention turn.
    ws.launching_path.unlink(missing_ok=True)

    # An advisor is still in flight (PreToolUse set the marker; SubagentStop, its
    # sole clearer, hasn't fired): re-triggering would cascade a second advisor,
    # so wait — the loop resumes when the advisor stops.
    if ws.advisor_running_path.exists():
        sys.exit(0)

    # The advisor ran this round iff PreToolUse consumed the token a prior Stop
    # wrote.  A leftover token means the main agent ignored the trigger and no
    # advisor ran — skip recording so a prior round's advice is not re-appended
    # as a duplicate; the trigger is re-injected below.  A main that keeps
    # re-stopping without working trips the harness Stop-block cap.
    advisor_invoked = not ws.advisor_token_path.exists()

    # Record last round's verdict (none in round 0, before any call).  Past the
    # in-flight guard the advisor has finished, so an absent advice file means it
    # wrote nothing.  The narration narrates the round just completed: it opens
    # with the prior advice arriving and shows how the main agent responded, so
    # the log entry pairs it with that advice — true cause -> effect order.  The
    # termination token is machinery and never enters the log.
    if current_round >= 1 and advisor_invoked:
        advice = ws.advice_path.read_text().strip() if ws.advice_path.exists() else ""
        narration = (
            ws.narration_path.read_text().strip() if ws.narration_path.exists() else ""
        ) or "(no narration)"
        write_log(
            ws.log_path,
            len(advice_history),
            narration,
            advice_history[-1] if advice_history else None,
        )
        if not advice or TERMINATION_TOKEN in advice:
            end_loop(ws, current_round, advice_history)
        advice_history = [*advice_history, advice]

    # This round's inputs for the next advisor call: the main agent's actions
    # (narrated by the narrator) and the accumulated advice-history.
    actions = parse_round_actions(event.get("transcript_path", ""))
    ws.action_path.write_text(json.dumps(actions, ensure_ascii=False, indent=2))
    ws.advice_history_path.write_text(format_advice_history(advice_history))

    save_ledger(
        ws.ledger_path,
        round_number=current_round + 1,
        advice_history=advice_history,
        done=False,
    )

    # Mechanism 2: on a compacted round, re-inject the original-mission text into
    # the trigger (recency position).  Consume the marker so it fires once.
    mission_text = None
    if ws.compacted_path.exists():
        try:
            mission_text = ws.mission_path.read_text()
        except OSError:
            mission_text = None
        ws.compacted_path.unlink(missing_ok=True)

    trigger = format_advisor_trigger(
        mission_path=ws.mission_path,
        action_path=ws.action_path,
        advice_history_path=ws.advice_history_path,
        advice_path=ws.advice_path,
        narration_path=ws.narration_path,
        mission_text=mission_text,
    )

    # Clear both handoff channels as we arm the next round: an absent file next
    # round then unambiguously means its agent wrote nothing.
    ws.advice_path.unlink(missing_ok=True)
    ws.narration_path.unlink(missing_ok=True)
    ws.advisor_token_path.write_text("")
    sys.stderr.write(trigger)
    sys.exit(2)


def pre_tool_use() -> None:
    """PreToolUse hook (matcher: Agent): gate the main agent's advisor invocation.

    Allow an Agent(ploop:advisor) call only when a Stop hook set the single-use
    token — consuming it and marking the advisor in flight, so a stop while it
    runs (e.g. pushed to the background) won't re-trigger.  A self-initiated
    call (no token) is denied so the main agent keeps working until the hook
    drives the call properly.  Outside an active mission the gate stays out of
    the way.
    """
    event = read_event()
    tool_input = event.get("tool_input") or {}
    subagent_type = (
        tool_input.get("subagent_type", "") if isinstance(tool_input, dict) else ""
    )
    if "advisor" not in subagent_type:
        sys.exit(0)
    ws = Workspace.from_env(event.get("session_id", ""))
    if not ws.active_path.exists():
        sys.exit(0)
    if ws.advisor_token_path.exists():
        ws.advisor_token_path.unlink()
        ws.advisor_running_path.touch()
        sys.exit(0)
    sys.stderr.write("The Advisor cannot be invoked arbitrarily.")
    sys.exit(2)


def user_prompt_submit() -> None:
    """UserPromptSubmit hook: turn-boundary cleanup.

    A direct user turn is an intervention that turns the loop off — round state
    and the active marker are cleared, so an ESC-interrupted mission never
    silently resumes (the mission file stays as the durable anchor).  Two
    exceptions keep a live loop intact: a /ploop:launch turn (the launching
    sentinel, set because UserPromptExpansion runs before this hook, spares the
    fresh active marker) and a background advisor in flight (the running marker
    — the loop is mid-round and main has merely yielded to the user).

    When this turn actually deactivates a live loop, the end notice goes to the
    main agent as additionalContext — every termination path sends it, and the
    notice has the main agent report the end and its cause to the user.
    """
    event = read_event()
    ws = Workspace.from_env(event.get("session_id", ""))
    if ws.advisor_running_path.exists():
        return
    keep_active = ws.launching_path.exists()
    ws.launching_path.unlink(missing_ok=True)
    ws.clear_round_state()
    if not keep_active:
        ended = ws.active_path.exists()
        ws.active_path.unlink(missing_ok=True)
        if ended:
            sys.stdout.write(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "UserPromptSubmit",
                            "additionalContext": format_end_notice(
                                "a direct user turn intervened"
                            ),
                        }
                    }
                )
            )


def mark_compaction() -> None:
    """PostCompact hook: mark the compaction.

    The next stop() re-injects the original-mission text into its trigger
    (parallax mechanism 2) and consumes the marker; a marker left by a
    non-mission compaction is cleared at the next turn boundary.
    """
    event = read_event()
    Workspace.from_env(event.get("session_id", "")).compacted_path.touch()


def subagent_stop() -> None:
    """SubagentStop hook: the sole clearer of the advisor-running marker.

    Paired with PreToolUse setting it, the marker tells stop() and
    user_prompt_submit() an advisor is still in flight; narrator and other
    subagent stops are ignored.
    """
    event = read_event()
    agent_type = str(event.get("agent_type") or event.get("subagent_type") or "")
    if "advisor" not in agent_type:
        sys.exit(0)
    Workspace.from_env(event.get("session_id", "")).advisor_running_path.unlink(
        missing_ok=True
    )


def launch() -> None:
    """UserPromptExpansion hook (matcher: ploop:launch): the whole launch prep.

    Fires when /ploop:launch <mission> expands — before UserPromptSubmit, hence
    the launching sentinel that tells that later cleanup to spare the fresh
    active marker.  The mission rides in command_args as structured JSON, so
    multi-line text with quotes or `$` is captured verbatim.

    Two guards block the expansion (block_expansion — pure, turn erased): an
    armed loop (active marker), because relaunching over it would overwrite the
    mission and log mid-flight and orphan an in-flight advisor — /ploop:stop
    ends it first; and a blank mission, because the skill body would otherwise
    announce an activation this hook never armed (a ghost loop).

    A real launch clears the prior mission's round state, starts the round log
    with the mission text (a mission owns one log, and its final summary reads
    the goal first; the finished log survives ordinary turns), writes the
    mission anchor, and arms the loop.
    """
    event = read_event()
    if event.get("command_name", "") != "ploop:launch":
        sys.exit(0)
    ws = Workspace.from_env(event.get("session_id", ""))
    if ws.active_path.exists():
        block_expansion(
            "A parallax loop is already active. Stop it with /ploop:stop, then launch again."
        )
    mission = str(event.get("command_args", "")).strip()
    if not mission:
        block_expansion("The mission is empty. Run it as /ploop:launch <mission>.")
    ws.clear_round_state()
    ws.log_path.write_text(f"[[ MISSION ]]\n\n{mission}\n\n")
    ws.mission_path.write_text(mission)
    ws.active_path.touch()
    ws.launching_path.touch()


def stop_command() -> None:
    """UserPromptExpansion hook (matcher: ploop:stop): stop the loop on demand.

    The loop has no round cap — it ends when the advisor has no further advice,
    or here, when the user runs /ploop:stop.  With no armed loop (never launched,
    already ended, or a double-stop) the expansion is blocked (block_expansion —
    pure, turn erased): the skill body never enters context, so the main agent
    can't announce a termination that didn't happen.

    An armed loop is deactivated: the active gate and per-round state are cleared,
    so the next stop is allowed and nothing leaks into a later mission.  Unlike an
    incidental user turn (which user_prompt_submit spares while a background
    advisor is in flight), it stops unconditionally — clearing the running marker
    before UserPromptSubmit reads it.  It injects the same end notice the natural
    end does (cause: the user's stop) with the round log to recap, carried as
    UserPromptExpansion additionalContext — the only channel with the session's
    real log path; the static skill body can't hold it.
    """
    event = read_event()
    if event.get("command_name", "") != "ploop:stop":
        sys.exit(0)
    ws = Workspace.from_env(event.get("session_id", ""))
    if not ws.active_path.exists():
        block_expansion("No active parallax loop.")
    ws.clear_round_state()
    ws.active_path.unlink(missing_ok=True)
    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptExpansion",
                    "additionalContext": format_end_notice(
                        "the user ran /ploop:stop", log_path=ws.log_path
                    ),
                }
            }
        )
    )
