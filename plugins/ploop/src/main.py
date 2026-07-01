"""Main — ploop Stop, PreToolUse, SubagentStop, UserPromptSubmit, PostCompact, UserPromptExpansion entry points.

On each main-agent stop the hook owns both ends of the parallax round:

1) It reads what the advisor returned last round (extract_advisor_output) and
   records it — appending the region to history, or ending the turn on an
   empty output or the termination token (parallax's own rule).  This is the
   advisor's old "record & return" step, lifted into code so the advisor prompt
   stays a pure analysis prompt.
2) If not done and under the round limit, it records this round's actions for
   the narrator, advances the round, and injects (exit 2 + stderr) the trigger
   that drives the main agent to invoke the advisor again.  On a compacted round
   the trigger carries the original-mission text (parallax mechanism 2).

The hook never runs the advisor itself — it drives the main agent (the LLM) to
call it via the Agent tool, which keeps the loop on the subscription path.

The Stop hook fires on every main-session stop, so an active marker gates it:
the launch() UserPromptExpansion hook writes the marker (and the mission) when
/ploop:launch expands, UserPromptSubmit clears it (with the ledger and the token)
on every new user turn, and stop() clears it when the loop terminates — so an
ESC-interrupted mission never silently resumes.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.prompt import format_advisor_trigger, format_region_history
from src.state import (
    ROUND_LIMIT,
    active_file,
    advisor_running_file,
    advisor_token_file,
    build_state,
    mission_file,
    save_ledger,
)
from src.transcript import (
    advisor_output_settled,
    extract_advisor_output,
    parse_round_actions,
)

# Sentinel the advisor emits to end the turn.  Checked with `in` so the signal
# survives any surrounding prose the model emits alongside it.
TERMINATION_TOKEN = "I_FIND_NO_FURTHER_REGION_WORTH_SURFACING_ENDING_THE_PARALLAX_TURN"


def write_log(
    log_file: Path, round_number: int, *, new_turn: bool, **sections: str
) -> None:
    """Append a round's log. Overwrites when a new mission begins (round 1)."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    header = f"[[ Round {round_number} - {timestamp} ]]\n\n"
    body = ""
    for title, content in sections.items():
        label = title.replace("_", " ").title()
        body += f"[[ Round {round_number} / {label} ]]\n\n{content}\n\n"
    mode = "w" if new_turn else "a"
    with open(log_file, mode) as f:
        f.write(header + body)


def stop() -> None:
    """Stop hook entry point (fires on every main-session stop)."""
    state = build_state(sys.stdin.read())

    # Not an active ploop run: no active marker — allow the stop.
    if not state.mission_active:
        sys.exit(0)

    # Already terminated in a prior round — allow the stop.
    if state.done:
        sys.exit(0)

    # The main session transcript IS the work transcript: the main agent runs
    # the mission directly, so its actions and the Agent(advisor) exchange live
    # here.  There is no operator subagent transcript to resolve.
    transcript = state.transcript_path

    # An advisor call is still in flight: PreToolUse set the running marker and
    # neither SubagentStop nor a completed result has cleared it.  This is the
    # user pushing the advisor to the background — the main session stops, but
    # re-triggering here would spawn a second advisor, and again on the next stop:
    # a cascade.  Allow this stop and wait; the loop resumes when the advisor
    # finishes (SubagentStop clears the marker).  If the marker is stale
    # (SubagentStop missed) yet the advisor actually completed, its settled result
    # is in the transcript, so clear the marker and fall through rather than stall.
    if state.advisor_running_path.exists():
        if advisor_output_settled(transcript):
            state.advisor_running_path.unlink(missing_ok=True)
        else:
            sys.exit(0)

    regions = state.region_history
    region = None  # the advisor's region this round, recorded to the log

    # The advisor ran this round iff PreToolUse consumed the token a prior Stop
    # wrote.  If the token is still here the main agent ignored the trigger and no
    # advisor ran — skip extraction so a prior round's region is not re-appended as
    # a duplicate; the trigger is re-injected below (bounded by ROUND_LIMIT).
    advisor_invoked = not state.advisor_token_path.exists()

    # Record last round's advisor verdict (none in round 0, before any call).
    # parallax's rule: an empty output or the termination token ends the turn.
    if state.current_round >= 1 and advisor_invoked:
        # The advisor Writes its region to present_path — a clean channel immune to
        # the reasoning prose its chat message may carry.  Fall back to scraping the
        # transcript when the file is absent: on termination the advisor emits the
        # token there instead of writing, and a non-compliant advisor that narrates
        # without writing still degrades to the pre-file behavior.
        presented = (
            state.present_path.read_text().strip()
            if state.present_path.exists()
            else ""
        )
        verdict = presented or extract_advisor_output(transcript)
        if not verdict or TERMINATION_TOKEN in verdict:
            save_ledger(
                state.state_path,
                round_number=state.current_round,
                regions=regions,
                done=True,
            )
            state.active_path.unlink(missing_ok=True)
            sys.exit(0)
        region = verdict
        regions = [*regions, region]
        # Log the surfaced region now, before any round-limit exit below.
        # Numbered by current_round so the first region is "Round 1".
        write_log(
            state.log_path,
            state.current_round,
            new_turn=(state.current_round == 1),
            region=region,
        )

    if state.current_round >= ROUND_LIMIT:
        save_ledger(
            state.state_path,
            round_number=state.current_round,
            regions=regions,
            done=False,
        )
        state.active_path.unlink(missing_ok=True)
        sys.exit(0)

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
        present_path=state.present_path,
        mission_text=mission_text,
    )

    # Clear this round's region file as we arm the next: an absent file next round
    # then unambiguously means the advisor wrote nothing (termination / no compliance).
    state.present_path.unlink(missing_ok=True)
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

    Every new user-initiated turn clears the prior mission's loop ledger, active
    marker, advisor token, advisor-running marker, compaction marker, and region file.  /ploop:launch re-activates
    by re-creating the active marker after this fires; any other direct user input
    is an intervention that leaves the loop off — so an ESC-interrupted mission
    never silently resumes on the next stop, and a stale token can't authorize a
    self-initiated advisor call in the next mission.  The mission file is left
    intact as the durable anchor; the next run overwrites it.
    """
    try:
        data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        sys.exit(0)
    data_dir = Path(os.environ["CLAUDE_PLUGIN_DATA"])
    session_id = data.get("session_id", "")
    (data_dir / f"{session_id}_loop.json").unlink(missing_ok=True)
    (data_dir / f"{session_id}_active").unlink(missing_ok=True)
    (data_dir / f"{session_id}_advisor_token").unlink(missing_ok=True)
    (data_dir / f"{session_id}_advisor_running").unlink(missing_ok=True)
    (data_dir / f"{session_id}_compacted").unlink(missing_ok=True)
    (data_dir / f"{session_id}_present.md").unlink(missing_ok=True)


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
    """UserPromptExpansion hook (matcher: launch): the whole /ploop:launch prep.

    Fires when the user types /ploop:launch <mission>, before the expanded skill
    reaches the model.  The mission rides in command_args as structured JSON, so
    multi-line text with quotes, newlines, or `$` is captured verbatim — no shell
    quoting to corrupt it.  Writes the stripped mission and arms the loop; it must
    never block (a blocked expansion erases the turn), so it always exits 0.

    UserPromptSubmit clears the prior turn's state just before this fires, so the
    handler only writes.  CLAUDE_PLUGIN_DATA comes from the environment (exported
    to hook processes); session_id comes from the payload.
    """
    try:
        data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        sys.exit(0)
    command = str(data.get("command_name", ""))
    if command.rsplit(":", 1)[-1] != "launch":
        sys.exit(0)
    mission = str(data.get("command_args", "")).strip()
    if not mission:
        sys.exit(0)
    data_dir = Path(os.environ["CLAUDE_PLUGIN_DATA"])
    session_id = str(data.get("session_id", ""))
    mission_file(data_dir, session_id).write_text(mission)
    active_file(data_dir, session_id).touch()


if __name__ == "__main__":
    stop()
