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
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.messages import (
    format_advisor_trigger,
    format_region_notice,
    format_termination_notice,
)
from src.prompt import build_analysis_input
from src.state import (
    ROUND_LIMIT,
    AnchorState,
    advisor_token_file,
    build_state,
    save_ledger,
)
from src.transcript import (
    extract_advisor_output,
    find_anchor_transcript,
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


def write_trace(state: AnchorState, raw_stdin: str) -> None:
    """Unconditional hook-firing trace for diagnosis.

    The hook exits silently when mission_active is False, so without this there
    is no way to distinguish a hook that never fired from one that fired and
    bailed.  The file name carries the session_id the hook actually received,
    revealing whether it matches the session init wrote the mission under.  The
    raw stdin is recorded too, exposing the event's real fields (e.g.
    agent_type) so anchor stops can be identified in code if matcher is unfit.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = (
        f"{timestamp} session={state.session_id} "
        f"transcript_exists={Path(state.transcript_path).exists()} "
        f"mission_active={state.mission_active} "
        f"round={state.current_round} done={state.done}\n"
        f"  stdin={raw_stdin.strip()}\n"
    )
    with open(state.data_dir / f"{state.session_id}_hook_trace.log", "a") as f:
        f.write(line)


def write_pretooluse_trace(data_dir: Path, session_id: str, raw: str) -> None:
    """Unconditional PreToolUse trace: confirms the hook fires on anchor's tool
    calls and exposes the stdin shape (session_id, tool_input.subagent_type)."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(data_dir / f"{session_id}_pretooluse_trace.log", "a") as f:
        f.write(f"{timestamp} stdin={raw.strip()}\n")


def emit_system_message(text: str) -> None:
    """Print a hook systemMessage to stdout — shown in the user's UI, the same
    channel the SessionStart updater uses.  Paired with exit 2: the block lives
    in stderr, so if the runtime ignores stdout on exit 2 the loop is unaffected
    and {session}_anchor.log still holds the region for /anchor:log."""
    print(json.dumps({"systemMessage": text}, ensure_ascii=False))


def subagent_stop() -> None:
    """SubagentStop hook entry point (matcher: anchor)."""
    raw = sys.stdin.read()
    state = build_state(raw)
    write_trace(state, raw)

    # Not an anchor mission: no mission file was handed off — allow the stop.
    if not state.mission_active:
        sys.exit(0)

    # Already terminated in a prior round — allow the stop.
    if state.done:
        sys.exit(0)

    # SubagentStop hands us the MAIN transcript; the anchor's own work lives in
    # a separate subagent transcript.  Resolve the latest anchor spawn's, or
    # allow the stop if we can't (the loop can't run without anchor's actions).
    anchor_transcript = find_anchor_transcript(state.transcript_path)
    with open(state.data_dir / f"{state.session_id}_hook_trace.log", "a") as f:
        f.write(f"  anchor_transcript={anchor_transcript}\n")
    if anchor_transcript is None:
        sys.exit(0)

    regions = state.region_history
    region = None  # the advisor's region this round, for the user + the log

    # Record last round's advisor verdict (none in round 0, before any call).
    if state.current_round >= 1:
        verdict = extract_advisor_output(anchor_transcript)
        if verdict and TERMINATION_TOKEN in verdict:
            save_ledger(
                state.state_path,
                round_number=state.current_round,
                regions=regions,
                done=True,
            )
            emit_system_message(format_termination_notice())
            sys.exit(0)
        if verdict:
            region = verdict.strip()
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
    actions = parse_round_actions(anchor_transcript)
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

    # Post-hoc log (browsable via /anchor:log): the advisor's region, if any,
    # then the next-round trigger.
    sections = {"region": region} if region else {}
    sections["advisor_trigger"] = trigger
    write_log(state.log_path, state.current_round + 1, new_turn=new_turn, **sections)

    state.advisor_token_path.write_text("")

    # Real-time: surface the region to the user's UI via systemMessage, while
    # the block (stderr + exit 2) drives the anchor to consult the advisor again.
    if region:
        emit_system_message(format_region_notice(state.current_round + 1, region))
    sys.stderr.write(trigger)
    sys.exit(2)


def pre_tool_use() -> None:
    """PreToolUse hook (matcher: Agent): gate anchor's advisor invocation.

    Allow an Agent(anchor:advisor) call only when a SubagentStop set the
    single-use token; a self-initiated call (no token) is denied so anchor
    keeps working until it stops and the hook drives the call properly.
    """
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(0)
    data_dir = Path(os.environ["CLAUDE_PLUGIN_DATA"])
    session_id = data.get("session_id", "")
    write_pretooluse_trace(data_dir, session_id, raw)

    tool_input = data.get("tool_input") or {}
    subagent_type = (
        tool_input.get("subagent_type", "") if isinstance(tool_input, dict) else ""
    )

    # Not an advisor invocation (anchor:anchor / anchor:narrator / other) — allow.
    if "advisor" not in subagent_type:
        sys.exit(0)

    # Outside an anchor mission — do not interfere.
    if not (data_dir / f"{session_id}_mission.md").exists():
        sys.exit(0)

    # Authorized by a SubagentStop directive: consume the token and allow.
    token = advisor_token_file(data_dir, session_id)
    if token.exists():
        token.unlink()
        sys.exit(0)

    # Self-initiated advisor call: deny and send anchor back to the mission.
    sys.stderr.write(
        "지금은 advisor를 호출할 때가 아닙니다. 미션 작업을 계속하고, "
        "더 할 일이 없으면 멈추세요."
    )
    sys.exit(2)


if __name__ == "__main__":
    subagent_stop()
