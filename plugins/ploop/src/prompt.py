"""Prompt — assemble the advisor's input artifacts and the trigger.

parallax's prompt.py built all five sections into one string and handed the
advisor a finished prompt.  ploop can't run the advisor from the hook,
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

import textwrap
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
    advice_path: Path,
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

    The call is synchronous (run_in_background=false): the advisor Writes its
    advice to advice_path — a clean file channel, since its chat message may carry
    reasoning prose neither the main agent nor the hook should read.  The trigger
    then directs the main agent to read that file, and the hook reads it too for the
    ledger; the blocking tool_result carries only the termination token (or a
    non-compliant fallback).  The inlined narrator call blocks so the advisor
    receives the narrative to analyze on.

    On a compacted round, mission_text is the original-mission's full text,
    re-injected at this recency position (parallax mechanism 2) — the discrete
    compaction event puts the mission text itself into context.
    """
    prefix = ""
    if mission_text:
        prefix = f"Your mission — stay anchored to it:\n\n{mission_text}\n\n---\n\n"
    body = textwrap.dedent(f'''\
        Invoke the advisor. Run the call below EXACTLY as written:

        ```
        Agent(
          subagent_type="ploop:advisor",
          description="review and advise",
          run_in_background=false,
          prompt="""
            original-mission: {mission_path}
            actions-history: Agent(
              subagent_type="ploop:narrator",
              description="narrate action history",
              run_in_background=false,
              prompt="{action_path}"
            )
            parallax-region-history: {regions_path}
            instructions: {instruction_path}
            advice-path: {advice_path}
          """
        )
        ```

        When the advisor returns, read its advice at {advice_path}.
    ''')
    return prefix + body
