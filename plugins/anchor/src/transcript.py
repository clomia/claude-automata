"""Transcript — read the anchor's transcript for the SubagentStop hook.

Two reads:
- parse_round_actions: the anchor's own domain work since the last advisor
  injection, handed to the narrator for narration.
- extract_advisor_output: the text the advisor subagent last returned.  The
  anchor calls the advisor via the Agent tool, so the advisor's verdict
  arrives as that call's tool_result.  The hook reads it here to record the
  region and detect termination — work the advisor used to do in its own
  prompt, now lifted into code so the advisor prompt stays pure analysis.
"""

import json
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

    The anchor's mission handoff and every SubagentStop injection appear as
    string-content user messages; tool results are list-content and never
    split a round.
    """
    if msg.get("role") != "user":
        return False
    return isinstance(msg.get("content", ""), str)


def strip_advisor_exchanges(messages: list[dict]) -> list[dict]:
    """Drop the anchor's Agent(advisor) call and its result from the messages.

    The advisor call is parallax machinery, not the anchor's domain work.  In
    parallax the advisor ran as an external process and never touched the main
    transcript, so action-history was pure work.  Here the anchor calls it
    in-context, so we strip the call and its result to keep action-history
    free of the advisor's own region echoing back — preserving the
    action-history vs region-history distinction the instruction relies on.
    Other subagent calls (the anchor's own delegation) are kept.
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
    """Return the anchor's domain work since the last round boundary.

    Strips the Agent(advisor) exchange so the narrator narrates only the
    anchor's own work, keeping action-history and region-history distinct.
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


def extract_advisor_output(transcript_path: str) -> str | None:
    """Return the text the most recent successful advisor call returned, or None.

    None when no advisor call is present (e.g. round 0).  A call denied by
    PreToolUse gating leaves an error tool_result; those are skipped so a
    blocked self-initiated call never reaches region-history.
    """
    messages = load_messages(transcript_path)

    advisor_ids = {
        block.get("id")
        for msg in messages
        if msg.get("role") == "assistant"
        for block in content_blocks(msg)
        if is_advisor_call(block)
    }
    if not advisor_ids:
        return None

    output = None
    for msg in messages:
        if msg.get("role") != "user":
            continue
        for block in content_blocks(msg):
            if (
                block.get("type") == "tool_result"
                and block.get("tool_use_id") in advisor_ids
                and not block.get("is_error")
            ):
                output = result_text(block.get("content"))
    return output


def is_anchor_spawn(block: dict) -> bool:
    """True for an Agent tool_use that spawns the anchor (subagent_type *:anchor)."""
    return (
        block.get("type") == "tool_use"
        and block.get("name") in AGENT_TOOL_NAMES
        and str(block.get("input", {}).get("subagent_type", "")).endswith(":anchor")
    )


def find_anchor_transcript(main_transcript_path: str) -> str | None:
    """Resolve the anchor subagent's own transcript from the main transcript.

    SubagentStop hands the hook the MAIN session transcript, not the stopped
    subagent's — the anchor's work lives in a separate file under
    {session}/subagents/agent-{agentId}.jsonl.  Find the latest anchor:anchor
    spawn in the main transcript, match its tool_use id to a subagent's
    meta.json (toolUseId), and return that agent's transcript path.
    """
    messages = load_messages(main_transcript_path)
    spawn_id = None
    for msg in messages:
        if msg.get("role") != "assistant":
            continue
        for block in content_blocks(msg):
            if is_anchor_spawn(block):
                spawn_id = block.get("id")
    if spawn_id is None:
        return None

    subagents_dir = Path(main_transcript_path).with_suffix("") / "subagents"
    if not subagents_dir.is_dir():
        return None
    for meta_path in subagents_dir.glob("agent-*.meta.json"):
        try:
            meta = json.loads(meta_path.read_text())
        except json.JSONDecodeError, OSError:
            continue
        if meta.get("toolUseId") == spawn_id:
            transcript = meta_path.with_name(
                meta_path.name[: -len(".meta.json")] + ".jsonl"
            )
            return str(transcript) if transcript.exists() else None
    return None
