"""Transcript — read the main session's transcript for the Stop hook.

Two reads:
- parse_round_actions: the main agent's own domain work since the last advisor
  injection, written to a file the advisor's narrator reads.
- extract_advisor_output: the text the advisor subagent last returned.  The
  main agent calls the advisor via the Agent tool, so the advisor's verdict
  arrives as that call's tool_result.  The hook reads it here to record the
  region and detect termination — work the advisor used to do in its own
  prompt, now lifted into code so the advisor prompt stays pure analysis.
"""

import json
import re
from pathlib import Path

# The Agent tool was renamed from Task in Claude Code 2.1.63; both resolve.
AGENT_TOOL_NAMES = ("Agent", "Task")


def load_messages(transcript_path: str) -> list[dict]:
    """Parse the transcript JSONL into a flat list of messages."""
    try:
        lines = Path(transcript_path).read_text().splitlines()
    except OSError:
        return []
    messages: list[dict] = []
    for line in lines:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg := obj.get("message"):
            messages.append(msg)
    return messages


def content_blocks(msg: dict) -> list:
    """A message's content as a list of blocks (empty for string content)."""
    content = msg.get("content")
    return content if isinstance(content, list) else []


def is_advisor_call(block: dict) -> bool:
    """True for an Agent tool_use whose subagent is the advisor."""
    return (
        block.get("type") == "tool_use"
        and block.get("name") in AGENT_TOOL_NAMES
        and "advisor" in str(block.get("input", {}).get("subagent_type", ""))
    )


def is_round_boundary(msg: dict) -> bool:
    """A user message with string content marks a round boundary.

    The mission handoff and every Stop injection appear as string-content user
    messages; tool results are list-content and never split a round.
    """
    if msg.get("role") != "user":
        return False
    return isinstance(msg.get("content", ""), str)


def strip_advisor_exchanges(messages: list[dict]) -> list[dict]:
    """Drop the main agent's Agent(advisor) call and its result from the messages.

    The advisor call is ploop machinery, not the main agent's domain
    work.  In parallax the advisor ran as an external process and never touched
    the main transcript, so action-history was pure work.  Here the main agent
    calls it in-context, so we strip the call and its result to keep
    action-history free of the advisor's own region echoing back — preserving
    the action-history vs region-history distinction the instruction relies on.
    Other subagent calls (the main agent's own delegation) are kept.
    """
    advisor_ids = {
        block.get("id")
        for msg in messages
        for block in content_blocks(msg)
        if is_advisor_call(block)
    }
    if not advisor_ids:
        return messages

    def is_advisor_block(block: dict) -> bool:
        return (block.get("type") == "tool_use" and block.get("id") in advisor_ids) or (
            block.get("type") == "tool_result"
            and block.get("tool_use_id") in advisor_ids
        )

    cleaned: list[dict] = []
    for msg in messages:
        blocks = content_blocks(msg)
        if not blocks:
            cleaned.append(msg)
            continue
        kept = [block for block in blocks if not is_advisor_block(block)]
        if kept:
            cleaned.append({**msg, "content": kept})
    return cleaned


def parse_round_actions(transcript_path: str) -> list[dict]:
    """Return the main agent's domain work since the last round boundary.

    Strips the Agent(advisor) exchange so the narrator narrates only the
    main agent's own work, keeping action-history and region-history distinct.
    """
    messages = load_messages(transcript_path)
    last_boundary = -1
    for i, msg in enumerate(messages):
        if is_round_boundary(msg):
            last_boundary = i
    return strip_advisor_exchanges(messages[last_boundary + 1 :])


def result_text(content) -> str | None:
    """Flatten a tool_result content (string or text blocks) to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            block["text"]
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        return "\n".join(parts) if parts else None
    return None


# An Agent tool_result carries trailing subagent metadata the advisor never
# authored: "agentId: <id> (...)\n<usage>...</usage>".  parallax's advisor ran
# as a plain claude -p process whose stdout was pure region text; the Agent
# tool reintroduces this envelope.  Strip it so it never reaches region-history.
# Anchor to the full envelope shape (an agentId line immediately followed by the
# <usage>...</usage> block at end-of-text): a bare "agentId:.*?</usage>" would
# bridge from the FIRST "agentId:" in the region's own prose to the final
# </usage>, swallowing the region — and any termination token inside it.
SUBAGENT_META = re.compile(r"\n*agentId:[^\n]*\n\s*<usage>.*?</usage>\s*$", re.DOTALL)


def strip_subagent_meta(text: str) -> str:
    """Remove the trailing Agent-tool subagent metadata block."""
    return SUBAGENT_META.sub("", text).strip()


def extract_advisor_output(transcript_path: str) -> str | None:
    """Return the region the most recent successful advisor call returned, or None.

    None in round 0 (no advisor call yet).  The hook records this as the round's
    surfaced region (or detects the termination token within it).  Denied calls
    (is_error — a PreToolUse-gated self-initiated call) are skipped so only a
    successful call is read; the trailing Agent-tool metadata is stripped.
    """
    messages = load_messages(transcript_path)

    call_ids = {
        block.get("id")
        for msg in messages
        if msg.get("role") == "assistant"
        for block in content_blocks(msg)
        if is_advisor_call(block)
    }
    if not call_ids:
        return None

    output = None
    for msg in messages:
        if msg.get("role") != "user":
            continue
        for block in content_blocks(msg):
            if (
                block.get("type") == "tool_result"
                and block.get("tool_use_id") in call_ids
                and not block.get("is_error")
            ):
                output = result_text(block.get("content"))
    if output is None:
        return None
    return strip_subagent_meta(output)


def advisor_output_settled(transcript_path: str) -> bool:
    """True if the most recent advisor call has returned a completed result.

    A finished subagent's tool_result ends with the "agentId: ...</usage>"
    envelope.  Its absence means the call is still in flight — no tool_result yet,
    or the user pushed the call to the background (whose launch ack lacks the
    envelope).  The Stop hook uses this to avoid re-triggering an advisor that is
    still running.  Returns False when no advisor call exists at all.
    """
    messages = load_messages(transcript_path)

    last_id = None
    for msg in messages:
        if msg.get("role") != "assistant":
            continue
        for block in content_blocks(msg):
            if is_advisor_call(block):
                last_id = block.get("id")
    if last_id is None:
        return False

    text = None
    for msg in messages:
        if msg.get("role") != "user":
            continue
        for block in content_blocks(msg):
            if (
                block.get("type") == "tool_result"
                and block.get("tool_use_id") == last_id
            ):
                text = result_text(block.get("content"))
    return text is not None and "</usage>" in text


def advisor_in_flight(running_marker: Path, transcript_path: str) -> bool:
    """True while a background advisor is genuinely running: its marker is present
    and its result has not settled.  Shared by the Stop hook (wait, don't cascade a
    second advisor) and UserPromptSubmit (don't let an incidental turn abort a
    mid-round mission).  A present-but-settled marker is stale, not in flight."""
    return running_marker.exists() and not advisor_output_settled(transcript_path)
