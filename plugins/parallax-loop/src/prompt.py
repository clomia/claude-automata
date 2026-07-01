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
    mission_text: str | None = None,
) -> str:
    """Build the stderr feedback that drives the main agent to invoke the advisor.

    The trigger spells out the advisor's Agent-tool call verbatim, with the
    narrator's Agent-tool call inlined inside it — the hook authors the exact
    invocations (as parallax's hook did via subprocess.run), and the main agent
    and advisor relay them as written.  Handing over the literal call is the
    simplest, most deterministic path: nothing is left for the LLM to construct.
    The five sections appear in parallax's order; the advisor reads/runs them
    top-to-bottom (advisor.md), reconstructing the same ordered context.

    The call is synchronous (run_in_background=false): parallax ran the advisor
    in-hook so its stdout WAS the region.  Here the hook cannot call the tool, so
    the main agent relays it — and the region returns as this call's tool_result
    only when the call blocks.  The inlined narrator call blocks for the same
    reason: the advisor must receive the narrative to analyze on it.

    On a compacted round, mission_text is the original-mission's full text,
    re-injected at this recency position (parallax mechanism 2) — the discrete
    compaction event puts the mission text itself into context.
    """
    prefix = ""
    if mission_text:
        prefix = (
            "Your original mission, re-injected after a compaction — hold to it:\n\n"
            f"{mission_text}\n\n"
        )
    return prefix + (
        "Consult the advisor — invoke it EXACTLY as written below, a synchronous "
        "call (run_in_background=false), copied verbatim — then act on the single "
        "region it returns:\n"
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
