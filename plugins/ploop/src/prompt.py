"""Prompt — assemble the advisor's input artifacts and the trigger.

The parallax loop feeds the advisor five sections in a canonical order.  ploop
can't run the advisor from the hook, so it writes the deterministic section
(advice-history) to a file and emits a trigger that points the advisor at the
five sections in that order:

    role (advisor system prompt)
    -> original-mission (mission file)
    -> action-history   (narrator call, run by the advisor)
    -> advice-history   (advice-history file)
    -> instructions     (static prompt file)

The advisor reads/runs them top-to-bottom, building the ordered context.

action-history is the one runtime-collected section: the hook slices the round's
own lines out of the main transcript into a small file (round_path), and the
narrator analyzes that whole file — no offsets, no boundary-finding.  The slice
is a pure line range [round_start .. end-of-transcript-at-this-stop], which is
exactly the round (the next handoff has not been appended yet), so the hook does
no message-format parsing and the loop carries no dependency on the transcript's
internal message shapes.
"""

import textwrap
from pathlib import Path

INSTRUCTION_PATH = Path(__file__).resolve().parent.parent / "prompts" / "instruction.md"


def format_advice_history(advice_history: list[str]) -> str:
    """Format prior advices as <advice-N> blocks (advice-history).

    Each block is one round's advice verbatim — its action-history recap plus
    the uncovered regions it lists — so the history also carries regions the
    main agent reached on its own, and covered ground is never re-surfaced.
    """
    if not advice_history:
        return "No prior advice."
    return "\n\n".join(
        f"<advice-{i + 1}>\n\n{advice}\n\n</advice-{i + 1}>"
        for i, advice in enumerate(advice_history)
    )


def format_advisor_trigger(
    *,
    mission_path: Path,
    round_path: Path,
    advice_history_path: Path,
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
    reasoning prose neither the main agent nor the hook should read.  Both the
    advice and the termination token go to advice_path (the sole channel); the trigger
    directs the main agent to read that file, and the hook reads it too for the
    ledger.  The narrator analyzes round_path — the round's own transcript slice the
    hook cut (a contiguous line range ending before the next handoff, so no
    interjection can truncate it) — and hands off through the same kind of channel:
    it Writes the narrative to narration_path, which the advisor reads as analysis
    input after the inlined call blocks — and the hook reads into the round log.

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
                        round: {round_path}
                        narration-path: {narration_path}
                    '
                )
                advice-history: {advice_history_path}
                instructions: {instruction_path}
                advice-path: {advice_path}
            """
        )
        ```

        When the advisor returns, read its advice at {advice_path}.
    ''')
    return prefix + body


def format_end_notice(cause: str, log_path: Path | None = None) -> str:
    """Build the notice every termination path sends to the main agent.

    The main agent must clearly report the end and its cause to the user —
    whatever ended the loop.  When the turn surfaced any advice the notice
    also has it recap the round log: over a long mission the main agent's
    context may have auto-compacted early rounds away, so the log on disk is
    the one complete record.
    """
    notice = (
        f"The parallax loop has ended — {cause}. "
        f"Clearly report the end and its cause to the user."
    )
    if log_path is not None:
        notice += f" Read {log_path} and add a brief recap of the rounds."
    return notice + "\n"
