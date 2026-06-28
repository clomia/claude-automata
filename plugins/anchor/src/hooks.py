"""Hooks — the anchor SubagentStop entry point.

On each anchor stop the hook owns both ends of the parallax round:

1) It reads what the advisor returned last round (extract_advisor_output) and
   records it — appending the region to history, or setting done on the
   termination token.  This is the advisor's old "record & return" step,
   lifted into code so the advisor prompt stays a pure analysis prompt.
2) If not done and under the round limit, it records this round's actions for
   the narrator, advances the round, and injects (exit 2 + stderr) the
   instruction for the anchor to invoke the advisor again.

The hook never runs the advisor itself — it drives the anchor (the LLM) to
call it via the Agent tool, which keeps anchor on the subscription-native path.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.messages import format_advisor_trigger
from src.prompt import build_analysis_input
from src.state import ROUND_LIMIT, build_state, save_ledger
from src.transcript import extract_advisor_output, parse_round_actions

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
    """SubagentStop hook entry point (matcher: anchor)."""
    state = build_state(sys.stdin.read())

    # Not an anchor mission: no mission file was handed off — allow the stop.
    if not state.mission_active:
        sys.exit(0)

    # Already terminated in a prior round — allow the stop.
    if state.done:
        sys.exit(0)

    regions = state.region_history

    # Record last round's advisor verdict (none in round 0, before any call).
    if state.current_round >= 1:
        verdict = extract_advisor_output(state.transcript_path)
        if verdict and TERMINATION_TOKEN in verdict:
            save_ledger(
                state.state_path,
                round_number=state.current_round,
                regions=regions,
                done=True,
            )
            sys.exit(0)
        if verdict:
            regions = [*regions, verdict.strip()]

    if state.current_round >= ROUND_LIMIT:
        save_ledger(
            state.state_path,
            round_number=state.current_round,
            regions=regions,
            done=False,
        )
        sys.exit(0)

    # Record this round's actions for the narrator (read later via advisor).
    actions = parse_round_actions(state.transcript_path)
    state.action_path.write_text(json.dumps(actions, ensure_ascii=False, indent=2))

    # Assemble the deterministic part of the advisor's input in code —
    # original-mission + region-history, XML-wrapped (parallax did this in
    # prompt.py).  Only the action narrative stays a runtime narrator call.
    mission = state.mission_path.read_text() if state.mission_path.exists() else ""
    state.analysis_path.write_text(build_analysis_input(mission, regions))

    new_turn = state.current_round == 0
    save_ledger(
        state.state_path,
        round_number=state.current_round + 1,
        regions=regions,
        done=False,
    )

    trigger = format_advisor_trigger(
        analysis_path=state.analysis_path,
        action_path=state.action_path,
    )
    write_log(
        state.log_path,
        state.current_round + 1,
        new_turn=new_turn,
        advisor_trigger=trigger,
    )
    sys.stderr.write(trigger)
    sys.exit(2)


if __name__ == "__main__":
    subagent_stop()
