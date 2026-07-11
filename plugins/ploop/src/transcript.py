"""Transcript — read the main session's transcript for the hooks.

parse_round_actions (Stop) returns the main agent's own domain work since the
last advisor injection, written to a file the advisor's narrator reads.  The
Agent(advisor) exchange is stripped so action-history stays the main agent's
own work — kept distinct from advice-history, which accumulates the advisor's
advice files (never scraped from the transcript).

was_interrupted (UserPromptSubmit) reads the transcript for the one signal
that has no hook event of its own: the user's interrupt (ESC), whose only
trace is the sentinel record it leaves.
"""

import json
from pathlib import Path

# The Agent tool was renamed from Task in Claude Code 2.1.63; both resolve.
AGENT_TOOL_NAMES = ("Agent", "Task")

# The user record an ESC leaves in the transcript (observed: a single text
# block; the string form is the defensive spelling of the same record).
INTERRUPT_SENTINELS = frozenset(
    {
        "[Request interrupted by user]",
        "[Request interrupted by user for tool use]",
    }
)


def queued_user_message(obj: dict) -> dict | None:
    """A delivered mid-turn injection as a list-content user message.

    Mid-turn injections — the user's steering prompts above all, but also
    notifications riding the same queue — reach the main agent only through
    queued_command attachments, never as message lines.  A steering prompt
    outranks the mission itself, so lifting these into the actions keeps the
    narrator's account aligned with everything the main agent was told.  List
    content keeps them off the round-boundary path (a steering does not reset
    the round), and only text blocks are kept (an inlined image is base64
    noise to the narrator).
    """
    attachment = obj.get("attachment") or {}
    if attachment.get("type") != "queued_command":
        return None
    prompt = attachment.get("prompt")
    if isinstance(prompt, str):
        blocks = [{"type": "text", "text": prompt}]
    elif isinstance(prompt, list):
        blocks = [b for b in prompt if isinstance(b, dict) and b.get("type") == "text"]
    else:
        blocks = []
    blocks = [b for b in blocks if str(b.get("text", "")).strip()]
    if not blocks:
        return None
    return {"role": "user", "content": blocks}


def load_messages(transcript_path: str) -> list[dict]:
    """Parse the transcript JSONL into a flat list of messages.

    Compact-summary lines are dropped: a compaction appends its session
    summary as a string-content user line (`isCompactSummary`) — the round
    boundary's exact shape — while every pre-compaction line stays in the
    append-only file.  Filtering it keeps a mid-round auto-compaction from
    faking a boundary and truncating the round's actions.

    Queued-command attachments are lifted in as messages (queued_user_message)
    at their delivery position, so mid-turn injections stay in chronological
    order with the work they influenced.
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
        elif queued := queued_user_message(obj):
            messages.append(queued)
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


def is_interrupt(msg: dict) -> bool:
    """True for the user record an ESC interrupt leaves in the transcript."""
    if msg.get("role") != "user":
        return False
    content = msg.get("content")
    if isinstance(content, str):
        return content.strip() in INTERRUPT_SENTINELS
    return any(
        isinstance(block, dict)
        and block.get("type") == "text"
        and str(block.get("text", "")).strip() in INTERRUPT_SENTINELS
        for block in content_blocks(msg)
    )


def was_interrupted(transcript_path: str) -> bool:
    """True when the session's latest completed act is a user interrupt (ESC).

    An interrupt fires no hook of its own; it is read here, at the next
    prompt, from the record it left.  Walking backwards, an assistant message
    means the last turn ended normally; everything else — the prompt being
    submitted, tool results, queued injections — is passed over, so the
    verdict is about how the last turn ended, not about the prompt riding
    this one.  An unreadable transcript reads as not interrupted: when in
    doubt the loop survives (/ploop:stop always works).
    """
    for msg in reversed(load_messages(transcript_path)):
        if msg.get("role") == "assistant":
            return False
        if is_interrupt(msg):
            return True
    return False


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
