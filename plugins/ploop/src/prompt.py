"""Prompt — assemble the advisor's input artifacts and the trigger.

The parallax loop feeds the advisor five sections in a canonical order.  ploop
can't run the advisor from the hook, so it writes the deterministic section
(parallax-region-history) to a file and emits a trigger that points the advisor
at the five sections in that order:

    role (advisor system prompt)
    -> original-mission        (mission file)
    -> action-history          (narrator call, run by the advisor)
    -> parallax-region-history (regions file)
    -> instructions            (static prompt file)

The advisor reads/runs them top-to-bottom, building the ordered context.
"""

import textwrap
from pathlib import Path

INSTRUCTION_PATH = Path(__file__).resolve().parent.parent / "prompts" / "instruction.md"


def format_region_history(region_history: list[str]) -> str:
    """Format prior regions as <region-N> blocks (parallax-region-history)."""
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
    narration_path: Path,
    instruction_path: Path = INSTRUCTION_PATH,
    mission_text: str | None = None,
) -> str:
    """Build the stderr feedback that drives the main agent to invoke the advisor.

    The trigger spells out the advisor's Agent-tool call verbatim, with the
    narrator's Agent-tool call inlined inside it — the hook authors the exact
    invocations, and the main agent and advisor relay them as written.  Handing over the literal call is the
    simplest, most deterministic path: nothing is left for the LLM to construct.
    The five sections appear in the loop's canonical order; the advisor
    reads/runs them top-to-bottom (advisor.md).

    The call is synchronous (run_in_background=false): the advisor Writes its
    advice to advice_path — a clean file channel, since its chat message may carry
    reasoning prose neither the main agent nor the hook should read.  Both a region
    and the termination token go to advice_path (the sole channel); the trigger
    directs the main agent to read that file, and the hook reads it too for the
    ledger.  The narrator hands off through the same kind of channel: it Writes the
    narrative to narration_path, which the advisor reads as analysis input after the
    inlined call blocks — and the hook reads into the round log.

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
                    prompt='
                        actions: {action_path}
                        narration-path: {narration_path}
                    '
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


def format_end_notice(cause: str) -> str:
    """Build the notice that tells the main agent the loop has ended.

    Every termination path must reach the main agent — told explicitly, it
    relays the end to the user in its reply.  Ends that carry a log worth
    recapping use format_summary_trigger instead.
    """
    return (
        f"The parallax loop has ended ({cause}); no further advisor rounds "
        f"will run. Mention this briefly to the user.\n"
    )


def format_summary_trigger(log_path: Path) -> str:
    """Build the stderr feedback for the loop's final stop.

    Over a long mission the main agent's context may have auto-compacted several
    times, so the round log on disk is the one complete record of the turn.  The
    trigger has the main agent read it and hand the user a compact recap.
    """
    return (
        f"The parallax loop has ended. "
        f"Read {log_path} and give the user a brief summary.\n"
    )
