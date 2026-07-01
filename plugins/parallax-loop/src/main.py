"""Main — the parallax-loop Stop, PreToolUse, UserPromptSubmit, and PostCompact entry points.

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
/parallax-loop:run writes the marker (and the mission), UserPromptSubmit clears
it (with the ledger and the token) on every new user turn, and stop() clears it
when the loop terminates — so an ESC-interrupted mission never silently resumes.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.prompt import format_advisor_trigger, format_region_history
from src.state import (
    ROUND_LIMIT,
    advisor_token_file,
    build_state,
    save_ledger,
)
from src.transcript import (
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

    # Not an active parallax-loop run: no active marker — allow the stop.
    if not state.mission_active:
        sys.exit(0)

    # Already terminated in a prior round — allow the stop.
    if state.done:
        sys.exit(0)

    # The main session transcript IS the work transcript: the main agent runs
    # the mission directly, so its actions and the Agent(advisor) exchange live
    # here.  There is no operator subagent transcript to resolve.
    transcript = state.transcript_path

    regions = state.region_history
    region = None  # the advisor's region this round, for the user + the log

    # Record last round's advisor verdict (none in round 0, before any call).
    # parallax's rule: an empty output or the termination token ends the turn.
    if state.current_round >= 1:
        verdict = extract_advisor_output(transcript)
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
        mission_text=mission_text,
    )

    # Post-hoc log (browsable via /parallax-loop:log): the region the advisor
    # surfaced (parallax's new_advice parity).  Numbered by current_round so the
    # first region is "Round 1"; round 0 has no region, so it is not logged.
    if region:
        write_log(
            state.log_path,
            state.current_round,
            new_turn=(state.current_round == 1),
            region=region,
        )

    state.advisor_token_path.write_text("")
    sys.stderr.write(trigger)
    sys.exit(2)


def pre_tool_use() -> None:
    """PreToolUse hook (matcher: Agent): gate the main agent's advisor invocation.

    Allow an Agent(parallax-loop:advisor) call only when a Stop hook set the
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

    # Outside an active parallax-loop run — do not interfere.
    if not (data_dir / f"{session_id}_active").exists():
        sys.exit(0)

    # Authorized by a Stop directive: consume the token and allow.
    token = advisor_token_file(data_dir, session_id)
    if token.exists():
        token.unlink()
        sys.exit(0)

    # Self-initiated advisor call: deny so the main agent keeps working.
    sys.stderr.write("The advisor cannot be called right now.")
    sys.exit(2)


def user_prompt_submit() -> None:
    """UserPromptSubmit hook: turn-boundary cleanup.

    Every new user-initiated turn clears the prior mission's loop ledger, active
    marker, advisor token, and compaction marker.  /parallax-loop:run re-activates
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
    (data_dir / f"{session_id}_compacted").unlink(missing_ok=True)


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


if __name__ == "__main__":
    stop()
