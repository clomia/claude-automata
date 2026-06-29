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
    """
    return (
        "Consult advisor:\n"
        '`Agent(subagent_type="parallax-loop:advisor", description="region review", prompt="""\n'
        f"original-mission: {mission_path}\n"
        'actions-history: Agent(subagent_type="parallax-loop:narrator", '
        f'description="narrate actions", prompt="{action_path}")\n'
        f"parallax-region-history: {regions_path}\n"
        f"instructions: {instruction_path}\n"
        '""")`'
    )
