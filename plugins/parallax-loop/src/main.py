"""Main — the parallax-loop SubagentStop and PreToolUse entry points.

On each operator stop the hook owns both ends of the parallax round:

1) It reads what the advisor returned last round (extract_advisor_output) and
   records it — appending the region to history, or setting done on the
   termination token.  This is the advisor's old "record & return" step,
   lifted into code so the advisor prompt stays a pure analysis prompt.
2) If not done and under the round limit, it records this round's actions for
   the narrator, advances the round, and injects (exit 2 + stderr) the trigger
   that drives the operator to invoke the advisor again.

The hook never runs the advisor itself — it drives the operator (the LLM) to
call it via the Agent tool, which keeps the loop on the subscription path.
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
    find_operator_transcript,
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


def subagent_stop() -> None:
    """SubagentStop hook entry point (matcher: parallax-loop:operator)."""
    state = build_state(sys.stdin.read())

    # Not a parallax-loop run: no mission file was handed off — allow the stop.
    if not state.mission_active:
        sys.exit(0)

    # Already terminated in a prior round — allow the stop.
    if state.done:
        sys.exit(0)

    # SubagentStop hands us the MAIN transcript; the operator's own work lives
    # in a separate subagent transcript.  Resolve the latest operator spawn's,
    # or allow the stop if we can't (the loop can't run without its actions).
    operator_transcript = find_operator_transcript(state.transcript_path)
    if operator_transcript is None:
        sys.exit(0)

    regions = state.region_history
    region = None  # the advisor's region this round, for the user + the log

    # Record last round's advisor verdict (none in round 0, before any call).
    if state.current_round >= 1:
        verdict = extract_advisor_output(operator_transcript)
        if verdict and TERMINATION_TOKEN in verdict:
            save_ledger(
                state.state_path,
                round_number=state.current_round,
                regions=regions,
                done=True,
            )
            sys.exit(0)
        if verdict:
            region = verdict
            regions = [*regions, region]

    if state.current_round >= ROUND_LIMIT:
        save_ledger(
            state.state_path,
            round_number=state.current_round,
            regions=regions,
            done=False,
        )
        sys.exit(0)

    # Record this round's actions for the narrator (read later via advisor).
    actions = parse_round_actions(operator_transcript)
    state.action_path.write_text(json.dumps(actions, ensure_ascii=False, indent=2))

    # Write the deterministic section — parallax-region-history — to a file the
    # advisor reads.  original-mission and instructions are already files; the
    # trigger lists all five sections in parallax's order (prompt.py).
    state.regions_path.write_text(format_region_history(regions))

    new_turn = state.current_round == 0
    save_ledger(
        state.state_path,
        round_number=state.current_round + 1,
        regions=regions,
        done=False,
    )

    trigger = format_advisor_trigger(
        mission_path=state.mission_path,
        action_path=state.action_path,
        regions_path=state.regions_path,
    )

    # Post-hoc log (browsable via /parallax-loop:log): the advisor's region, if
    # any, then the next-round trigger.
    sections = {"region": region} if region else {}
    sections["advisor_trigger"] = trigger
    write_log(state.log_path, state.current_round + 1, new_turn=new_turn, **sections)

    state.advisor_token_path.write_text("")
    sys.stderr.write(trigger)
    sys.exit(2)


def pre_tool_use() -> None:
    """PreToolUse hook (matcher: Agent): gate the operator's advisor invocation.

    Allow an Agent(parallax-loop:advisor) call only when a SubagentStop set the
    single-use token; a self-initiated call (no token) is denied so the
    operator keeps working until it stops and the hook drives the call properly.
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

    # Not an advisor invocation (operator / narrator / other) — allow.
    if "advisor" not in subagent_type:
        sys.exit(0)

    # Outside a parallax-loop run — do not interfere.
    if not (data_dir / f"{session_id}_mission.md").exists():
        sys.exit(0)

    # Authorized by a SubagentStop directive: consume the token and allow.
    token = advisor_token_file(data_dir, session_id)
    if token.exists():
        token.unlink()
        sys.exit(0)

    # Self-initiated advisor call: deny so the operator keeps working.
    sys.stderr.write("The advisor cannot be called right now.")
    sys.exit(2)


if __name__ == "__main__":
    subagent_stop()
