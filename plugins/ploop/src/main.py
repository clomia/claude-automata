"""Main — ploop Stop, PreToolUse, SubagentStop, UserPromptSubmit, PostCompact, UserPromptExpansion entry points.

On each main-agent stop the hook owns both ends of the parallax round:

1) It reads the region the advisor wrote to advice.md last round and records it
   — appending the region to history and logging it beside the narrated work it
   came from (parallax's log shape), or ending the turn on an absent file (the
   advisor wrote nothing) or the termination token (parallax's own rule).  This
   is the advisor's old "record & return" step, lifted into code so the advisor
   prompt stays a pure analysis prompt.
2) If not done and under the round limit, it records this round's actions for
   the narrator, advances the round, and injects (exit 2 + stderr) the trigger
   that drives the main agent to invoke the advisor again.  On a compacted round
   the trigger carries the original-mission text (parallax mechanism 2).  When
   the loop ends after surfacing regions, one final injection has the main agent
   summarize the round log for the user — the log outlives compaction.

The hook never runs the advisor itself — it drives the main agent (the LLM) to
call it via the Agent tool, which keeps the loop on the subscription path.

The Stop hook fires on every main-session stop, so an active marker gates it: the
launch() UserPromptExpansion hook writes the marker (and mission) when /ploop:launch
expands; UserPromptSubmit clears it on a new user turn — but spares it on the launch
turn (a launching sentinel, since expansion runs before submit) and while a
background advisor is in flight (so an incidental question can't abort a mid-round
mission) — and stop() clears it when the loop terminates, so an ESC-interrupted
mission never silently resumes.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.prompt import (
    format_advisor_trigger,
    format_region_history,
    format_summary_trigger,
)
from src.state import (
    ROUND_LIMIT,
    State,
    active_file,
    advisor_running_file,
    advisor_token_file,
    build_state,
    clear_round_state,
    log_file,
    mission_file,
    save_ledger,
)
from src.transcript import parse_round_actions

# Sentinel the advisor emits to end the turn.  Checked with `in` so the signal
# survives any surrounding prose the model emits alongside it.
TERMINATION_TOKEN = "I_FIND_NO_FURTHER_REGION_WORTH_SURFACING_ENDING_THE_PARALLAX_TURN"


def write_log(log_path: Path, round_number: int, **sections: str) -> None:
    """Append a round's sections to the mission log (parallax's log shape).

    Numbered by region ordinal, so the entries stay aligned with regions.md even
    when a round is skipped.  launch() resets the file; the finished log outlives
    the mission so the whole turn stays reconstructable after any compaction.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    header = f"[[ Round {round_number} - {timestamp} ]]\n\n"
    body = "".join(
        f"[[ Round {round_number} / {title.replace('_', ' ').title()} ]]"
        f"\n\n{content}\n\n"
        for title, content in sections.items()
    )
    with open(log_path, "a") as f:
        f.write(header + body)


def end_loop(state: State, regions: list[str], *, done: bool) -> None:
    """Terminate the loop: persist the final ledger and drop the active gate.

    When the turn surfaced any region, block this one stop (exit 2) to have the
    main agent summarize the round log for the user — over a long mission its
    context may have compacted the early rounds away, so the log is the one
    complete record.  The active marker is already gone, so the next stop passes.
    """
    save_ledger(
        state.state_path,
        round_number=state.current_round,
        regions=regions,
        done=done,
    )
    state.active_path.unlink(missing_ok=True)
    if regions:
        sys.stderr.write(format_summary_trigger(state.log_path))
        sys.exit(2)
    sys.exit(0)


def stop() -> None:
    """Stop hook entry point (fires on every main-session stop)."""
    state = build_state(sys.stdin.read())

    # Not an active ploop run: no active marker — allow the stop.
    if not state.mission_active:
        sys.exit(0)

    # Already terminated in a prior round — allow the stop.
    if state.done:
        sys.exit(0)

    # Consume any launching sentinel that outlived the turn boundary (possible only
    # if UserPromptSubmit didn't run before this Stop) so it can't later spare the
    # active marker on an intervention turn.
    state.launching_path.unlink(missing_ok=True)

    # The main session transcript IS the work transcript: the main agent runs
    # the mission directly, so its actions and the Agent(advisor) exchange live
    # here.  There is no operator subagent transcript to resolve.
    transcript = state.transcript_path

    # A background advisor still running: PreToolUse set the marker and SubagentStop
    # (its sole clearer) has not removed it.  Re-triggering here would cascade a
    # second advisor, so wait — the loop resumes when SubagentStop clears the marker.
    if state.advisor_running_path.exists():
        sys.exit(0)

    regions = state.region_history

    # The advisor ran this round iff PreToolUse consumed the token a prior Stop
    # wrote.  If the token is still here the main agent ignored the trigger and no
    # advisor ran — skip recording so a prior round's region is not re-appended as
    # a duplicate; the trigger is re-injected below (bounded by ROUND_LIMIT).
    advisor_invoked = not state.advisor_token_path.exists()

    # Record last round's advisor verdict (none in round 0, before any call).
    # advice.md is the SOLE region/termination channel: the advisor Writes its one
    # paragraph there, or the termination token.  We are past the in-flight guard, so
    # the advisor has finished (SubagentStop cleared its marker); an absent file
    # therefore means it wrote nothing, which ends the turn — parallax's rule that an
    # empty output (or the termination token) deactivates the loop.
    if state.current_round >= 1 and advisor_invoked:
        advice = (
            state.advice_path.read_text().strip() if state.advice_path.exists() else ""
        )
        # The log entry pairs the narrated work the advisor analyzed with the
        # verdict it produced — parallax's log shape, so the whole turn's flow
        # (work -> region -> work -> ...) reads back from the file alone.
        narration = (
            state.narration_path.read_text().strip()
            if state.narration_path.exists()
            else ""
        ) or "(no narration)"
        if not advice or TERMINATION_TOKEN in advice:
            write_log(
                state.log_path,
                len(regions) + 1,
                action_history=narration,
                region=advice or "(no output)",
            )
            end_loop(state, regions, done=True)
        regions = [*regions, advice]
        write_log(state.log_path, len(regions), action_history=narration, region=advice)

    if state.current_round >= ROUND_LIMIT:
        end_loop(state, regions, done=False)

    # Record this round's actions for the narrator (read later via advisor).
    actions = parse_round_actions(transcript)
    state.action_path.write_text(json.dumps(actions, ensure_ascii=False, indent=2))

    # Write the deterministic section — parallax-region-history — to a file the
    # advisor reads.  original-mission and instructions are already files; the
    # trigger lists the sections in parallax's order (prompt.py).
    state.regions_path.write_text(format_region_history(regions))

    save_ledger(
        state.state_path,
        round_number=state.current_round + 1,
        regions=regions,
        done=False,
    )

    # Mechanism 2: on a compacted round, re-inject the original-mission text into
    # the trigger (recency position).  Consume the marker so it fires once.
    mission_text = None
    if state.compacted:
        try:
            mission_text = state.mission_path.read_text()
        except OSError:
            mission_text = None
        state.compacted_path.unlink(missing_ok=True)

    trigger = format_advisor_trigger(
        mission_path=state.mission_path,
        action_path=state.action_path,
        regions_path=state.regions_path,
        advice_path=state.advice_path,
        narration_path=state.narration_path,
        mission_text=mission_text,
    )

    # Clear this round's advice and narration files as we arm the next: an absent
    # file next round then unambiguously means its agent wrote nothing (termination
    # / no compliance) rather than a stale carry-over.
    state.advice_path.unlink(missing_ok=True)
    state.narration_path.unlink(missing_ok=True)
    state.advisor_token_path.write_text("")
    sys.stderr.write(trigger)
    sys.exit(2)


def pre_tool_use() -> None:
    """PreToolUse hook (matcher: Agent): gate the main agent's advisor invocation.

    Allow an Agent(ploop:advisor) call only when a Stop hook set the
    single-use token; a self-initiated call (no token) is denied so the main
    agent keeps working until it stops and the hook drives the call properly.
    """
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(0)
    data_dir = Path(os.environ["CLAUDE_PLUGIN_DATA"])
    session_id = data.get("session_id", "")

    tool_input = data.get("tool_input") or {}
    subagent_type = (
        tool_input.get("subagent_type", "") if isinstance(tool_input, dict) else ""
    )

    # Not an advisor invocation (narrator / other) — allow.
    if "advisor" not in subagent_type:
        sys.exit(0)

    # Outside an active ploop run — do not interfere.
    if not (data_dir / f"{session_id}_active").exists():
        sys.exit(0)

    # Authorized by a Stop directive: consume the token, mark the advisor in
    # flight (so a stop while it runs — e.g. after the user backgrounds it —
    # won't re-trigger), and allow.
    token = advisor_token_file(data_dir, session_id)
    if token.exists():
        token.unlink()
        advisor_running_file(data_dir, session_id).touch()
        sys.exit(0)

    # Self-initiated advisor call: deny so the main agent keeps working.
    sys.stderr.write("The Advisor cannot be invoked arbitrarily.")
    sys.exit(2)


def user_prompt_submit() -> None:
    """UserPromptSubmit hook: turn-boundary cleanup.

    Clears the prior mission's loop ledger, token, advisor-running marker, compaction
    marker, advice file, and active marker — with two exceptions.  (1) On a
    /ploop:launch turn UserPromptExpansion (launch) ran first and set a fresh active
    marker plus a launching sentinel, which this hook consumes to spare that marker.
    (2) While a background advisor is in flight (advisor-running marker present) the
    loop is mid-round and main has merely yielded, so an incidental user turn leaves
    all state intact.  Otherwise a direct user turn is an intervention that turns the
    loop off — an ESC-interrupted mission never silently resumes.  The mission file is
    the durable anchor.
    """
    try:
        data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        sys.exit(0)
    data_dir = Path(os.environ["CLAUDE_PLUGIN_DATA"])
    session_id = data.get("session_id", "")
    # A background advisor in flight means the loop is mid-round: main invoked it
    # asynchronously and yielded, so an incidental user turn must NOT abort the
    # mission.  SubagentStop is the marker's sole clearer, so its presence alone
    # means in-flight.
    if advisor_running_file(data_dir, session_id).exists():
        return
    # /ploop:launch turn: launch() (UserPromptExpansion) ran first and set a fresh
    # mission + active marker plus a launching sentinel; consume it and spare active.
    launching = data_dir / f"{session_id}_launching"
    keep_active = launching.exists()
    launching.unlink(missing_ok=True)
    clear_round_state(data_dir, session_id)
    if not keep_active:
        (data_dir / f"{session_id}_active").unlink(missing_ok=True)


def mark_compaction() -> None:
    """PostCompact hook: mark that a compaction occurred.

    stop() reads the marker on the next round, re-injects the original-mission
    text into the trigger (parallax mechanism 2), and clears it.  A marker left by
    a non-mission compaction is cleared at the next turn boundary (user_prompt_submit).
    """
    try:
        data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        sys.exit(0)
    data_dir = Path(os.environ["CLAUDE_PLUGIN_DATA"])
    session_id = data.get("session_id", "")
    (data_dir / f"{session_id}_compacted").touch()


def subagent_stop() -> None:
    """SubagentStop hook: clear the advisor-running marker when the advisor finishes.

    Paired with the marker PreToolUse sets, this lets stop() tell an in-flight
    advisor (e.g. one the user pushed to the background) from a completed one, so
    it never re-triggers a second advisor while one still runs.  Only the advisor
    clears the marker; narrator and other subagent stops are ignored.
    """
    try:
        data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        sys.exit(0)
    agent_type = str(data.get("agent_type") or data.get("subagent_type") or "")
    if "advisor" not in agent_type:
        sys.exit(0)
    data_dir = Path(os.environ["CLAUDE_PLUGIN_DATA"])
    session_id = data.get("session_id", "")
    advisor_running_file(data_dir, session_id).unlink(missing_ok=True)


def launch() -> None:
    """UserPromptExpansion hook: the whole /ploop:launch prep (command guard scopes it).

    Fires when the user types /ploop:launch <mission>, before the expanded skill
    reaches the model.  The mission rides in command_args as structured JSON, so
    multi-line text with quotes, newlines, or `$` is captured verbatim — no shell
    quoting to corrupt it.  Writes the stripped mission and arms the loop; it must
    never block (a blocked expansion erases the turn), so it always exits 0.

    On a slash-command turn UserPromptExpansion runs BEFORE UserPromptSubmit, so a
    launching sentinel tells that later cleanup to spare the active marker this sets.
    CLAUDE_PLUGIN_DATA comes from the environment (exported to hook processes);
    session_id comes from the payload.
    """
    try:
        data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        sys.exit(0)
    command = str(data.get("command_name", ""))
    if command != "ploop:launch":
        sys.exit(0)
    mission = str(data.get("command_args", "")).strip()
    if not mission:
        sys.exit(0)
    data_dir = Path(os.environ["CLAUDE_PLUGIN_DATA"])
    session_id = str(data.get("session_id", ""))
    # Fresh start, independent of whether/when UserPromptSubmit fires this turn:
    # clear the prior mission's per-round state before arming.  The round log
    # resets here and only here — a mission owns one log for its whole turn, and
    # the finished log must survive ordinary turns for summary and inspection.
    clear_round_state(data_dir, session_id)
    log_file(data_dir, session_id).unlink(missing_ok=True)
    mission_file(data_dir, session_id).write_text(mission)
    active_file(data_dir, session_id).touch()
    # UserPromptExpansion runs BEFORE UserPromptSubmit on a slash-command turn, so
    # the turn-boundary cleanup would otherwise wipe the active marker just set.  A
    # launching sentinel tells user_prompt_submit() to spare it this turn.
    (data_dir / f"{session_id}_launching").touch()


if __name__ == "__main__":
    stop()
