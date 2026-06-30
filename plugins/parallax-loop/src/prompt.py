"""Prompt — assemble the advisor's input artifacts and the trigger.

parallax's prompt.py built all five sections into one string and handed the
advisor a finished prompt.  parallax-loop can't run the advisor from the hook,
so it writes the deterministic section (parallax-region-history) to a file and
emits a trigger that points the advisor at the five sections in parallax's
order:

    role (advisor system prompt)
    -> original-mission        (mission file)
    -> action-history          (narrator call, run by the advisor)
    -> parallax-region-history (regions file)
    -> instructions            (static prompt file)

The advisor reads/runs them top-to-bottom, reconstructing the same ordered
context parallax assembled in code.
"""

from pathlib import Path

INSTRUCTION_PATH = Path(__file__).resolve().parent.parent / "prompts" / "instruction.md"


def format_region_history(region_history: list[str]) -> str:
    """Format prior regions as <region-N> blocks (parallax prompt.py)."""
    if not region_history:
        return "No prior regions."
    return "\n\n".join(
        f"<region-{i + 1}>\n\n{region}\n\n</region-{i + 1}>"
        for i, region in enumerate(region_history)
    )


def format_advisor_trigger(
    *,
    mission_path: Path,
    action_path: Path,
    regions_path: Path,
    instruction_path: Path = INSTRUCTION_PATH,
) -> str:
    """Build the stderr feedback that drives the operator to invoke the advisor.

    Lists the five sections in parallax's order.  The advisor reads each path
    and runs the inlined narrator call to assemble action-history — so the only
    context added to the operator is this short trigger, not the analysis.

    The call MUST be synchronous (run_in_background=false) and verbatim: parallax
    ran the advisor in-hook via subprocess.run, so its stdout WAS the region.
    Here the hook cannot call the tool, so the operator relays it — but the region
    only returns as this call's tool_result when the call blocks.  A backgrounded
    call instead yields the harness's launch acknowledgement, which the hook would
    record as a bogus region.  Verbatim copying keeps the operator from injecting
    its own spin into the advisor's input (the five sections are the only context).

    The inlined narrator call is likewise run_in_background=false: the advisor runs
    it to assemble action-history, so it must block for the advisor to actually
    receive the narrative (else the advisor analyzes blind to the operator's work).
    Blocking also lands the narrative as the advisor's narrator tool_result, which
    the hook recovers from the advisor's transcript to log it (parity with
    parallax, whose in-hook narration was logged directly).

    It opens with a one-line mission re-anchor: parallax re-injected the mission
    on compaction (mechanism 2), but a subagent's compaction is undetectable from
    the hook, so instead this recency-positioned reminder fires every round to make
    self-anchoring deterministic without needing detection.
    """
    return (
        f"Re-anchor: your original mission lives at {mission_path}; re-read it if "
        "your context has drifted or been compacted.\n"
        "Then consult the advisor — invoke it EXACTLY as written below, a "
        "synchronous call (run_in_background=false), copied verbatim with nothing "
        "added to the prompt — then act on the single region it returns:\n"
        '`Agent(subagent_type="parallax-loop:advisor", description="region review", '
        'run_in_background=false, prompt="""\n'
        f"original-mission: {mission_path}\n"
        'actions-history: Agent(subagent_type="parallax-loop:narrator", '
        'description="narrate actions", run_in_background=false, '
        f'prompt="{action_path}")\n'
        f"parallax-region-history: {regions_path}\n"
        f"instructions: {instruction_path}\n"
        '""")`'
    )
