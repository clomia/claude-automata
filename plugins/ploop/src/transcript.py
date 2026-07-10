"""Transcript — read the main session's transcript for the Stop hook.

parse_round_actions returns the main agent's own domain work since the last
advisor injection, written to a file the advisor's narrator reads.  The
Agent(advisor) exchange is stripped so action-history stays the main agent's
own work — kept distinct from advice-history, which accumulates the advisor's
advice files (never scraped from the transcript).
"""

import json
from pathlib import Path

# The Agent tool was renamed from Task in Claude Code 2.1.63; both resolve.
AGENT_TOOL_NAMES = ("Agent", "Task")


def load_messages(transcript_path: str) -> list[dict]:
    """Parse the transcript JSONL into a flat list of messages.

    Compact-summary lines are dropped: a compaction appends its session
    summary as a string-content user line (`isCompactSummary`) — the round
    boundary's exact shape — while every pre-compaction line stays in the
    append-only file.  Filtering it keeps a mid-round auto-compaction from
    faking a boundary and truncating the round's actions.
    """
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
        if obj.get("isCompactSummary"):
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

    The advisor call is loop machinery, not the main agent's domain work.
    The parallax loop keeps action-history (the main agent's own work) distinct
    from advice-history, but here the main agent calls the advisor in-context —
    so we strip the call and its result to keep action-history free of the
    advisor's own advice echoing back.
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
    main agent's own work, keeping action-history and advice-history distinct.
    """
    messages = load_messages(transcript_path)
    last_boundary = -1
    for i, msg in enumerate(messages):
        if is_round_boundary(msg):
            last_boundary = i
    return strip_advisor_exchanges(messages[last_boundary + 1 :])
