"""Transcript — read the operator's transcript for the SubagentStop hook.

Two reads:
- parse_round_actions: the operator's own domain work since the last advisor
  injection, handed to the narrator for narration.
- extract_advisor_output: the text the advisor subagent last returned.  The
  operator calls the advisor via the Agent tool, so the advisor's verdict
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


def is_subagent_call(block: dict, keyword: str) -> bool:
    """True for an Agent tool_use whose subagent_type contains keyword."""
    return (
        block.get("type") == "tool_use"
        and block.get("name") in AGENT_TOOL_NAMES
        and keyword in str(block.get("input", {}).get("subagent_type", ""))
    )


def is_advisor_call(block: dict) -> bool:
    """True for an Agent tool_use whose subagent is the advisor."""
    return is_subagent_call(block, "advisor")


def is_round_boundary(msg: dict) -> bool:
    """A user message with string content marks a round boundary.

    The operator's mission handoff and every SubagentStop injection appear as
    string-content user messages; tool results are list-content and never
    split a round.
    """
    if msg.get("role") != "user":
        return False
    return isinstance(msg.get("content", ""), str)


def strip_advisor_exchanges(messages: list[dict]) -> list[dict]:
    """Drop the operator's Agent(advisor) call and its result from the messages.

    The advisor call is parallax-loop machinery, not the operator's domain
    work.  In parallax the advisor ran as an external process and never touched
    the main transcript, so action-history was pure work.  Here the operator
    calls it in-context, so we strip the call and its result to keep
    action-history free of the advisor's own region echoing back — preserving
    the action-history vs region-history distinction the instruction relies on.
    Other subagent calls (the operator's own delegation) are kept.
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
    """Return the operator's domain work since the last round boundary.

    Strips the Agent(advisor) exchange so the narrator narrates only the
    operator's own work, keeping action-history and region-history distinct.
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
SUBAGENT_META = re.compile(r"\n*agentId:.*?</usage>\s*$", re.DOTALL)


def strip_subagent_meta(text: str) -> str:
    """Remove the trailing Agent-tool subagent metadata block."""
    return SUBAGENT_META.sub("", text).strip()


# A backgrounded Agent call returns the harness's async-launch acknowledgement
# ("Async agent launched successfully ... working in the background") in place of
# the advisor's region.  The trigger forces run_in_background=false so calls block
# and the region returns as the tool_result; should one still run async, this
# envelope must never be recorded as a region — recognize and reject it so
# region-history degrades to a graceful stall instead of poisoning.
LAUNCH_BOILERPLATE_PREFIX = "Async agent launched successfully"


def is_launch_boilerplate(text: str) -> bool:
    """True for the async-launch acknowledgement (a non-region the hook must drop)."""
    return text.lstrip().startswith(LAUNCH_BOILERPLATE_PREFIX)


def extract_subagent_output(transcript_path: str, keyword: str) -> str | None:
    """Return the text the most recent successful `keyword` subagent call returned.

    None when no such call is present, when the only result was denied
    (is_error — e.g. a PreToolUse-gated self-initiated call), or when the call
    ran async (the launch acknowledgement, never a real output).  The trigger
    forces run_in_background=false so the output arrives as the call's
    tool_result; the boilerplate guard rejects it if a call still ran async.
    """
    messages = load_messages(transcript_path)

    call_ids = {
        block.get("id")
        for msg in messages
        if msg.get("role") == "assistant"
        for block in content_blocks(msg)
        if is_subagent_call(block, keyword)
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
    cleaned = strip_subagent_meta(output)
    return None if is_launch_boilerplate(cleaned) else cleaned


def extract_advisor_output(transcript_path: str) -> str | None:
    """Return the region the most recent successful advisor call returned, or None.

    None in round 0 (no advisor call yet).  The hook records this as the round's
    surfaced region (or detects the termination token within it).
    """
    return extract_subagent_output(transcript_path, "advisor")


def is_operator_spawn(block: dict) -> bool:
    """True for an Agent tool_use that spawns the operator (subagent_type *:operator)."""
    return (
        block.get("type") == "tool_use"
        and block.get("name") in AGENT_TOOL_NAMES
        and str(block.get("input", {}).get("subagent_type", "")).endswith(":operator")
    )


def find_operator_transcript(main_transcript_path: str) -> str | None:
    """Resolve the operator subagent's own transcript from the main transcript.

    SubagentStop hands the hook the MAIN session transcript, not the stopped
    subagent's — the operator's work lives in a separate file under
    {session}/subagents/agent-{agentId}.jsonl.  Find the latest
    parallax-loop:operator spawn in the main transcript, match its tool_use id
    to a subagent's meta.json (toolUseId), and return that agent's transcript.
    """
    messages = load_messages(main_transcript_path)
    spawn_id = None
    for msg in messages:
        if msg.get("role") != "assistant":
            continue
        for block in content_blocks(msg):
            if is_operator_spawn(block):
                spawn_id = block.get("id")
    if spawn_id is None:
        return None
    subagents_dir = Path(main_transcript_path).with_suffix("") / "subagents"
    return resolve_subagent_transcript(subagents_dir, spawn_id)


def resolve_subagent_transcript(subagents_dir: Path, tool_use_id: str) -> str | None:
    """Resolve the subagent transcript spawned by a given Agent tool_use id.

    Each subagent writes agent-<id>.meta.json carrying its spawning call's
    toolUseId; match it and return the sibling .jsonl transcript (or None).
    """
    if not subagents_dir.is_dir():
        return None
    for meta_path in subagents_dir.glob("agent-*.meta.json"):
        try:
            meta = json.loads(meta_path.read_text())
        except json.JSONDecodeError, OSError:
            continue
        if meta.get("toolUseId") == tool_use_id:
            transcript = meta_path.with_name(
                meta_path.name[: -len(".meta.json")] + ".jsonl"
            )
            return str(transcript) if transcript.exists() else None
    return None


def last_subagent_call_id(messages: list[dict], keyword: str) -> str | None:
    """The id of the last assistant Agent tool_use whose subagent matches keyword."""
    found = None
    for msg in messages:
        if msg.get("role") != "assistant":
            continue
        for block in content_blocks(msg):
            if is_subagent_call(block, keyword):
                found = block.get("id")
    return found


def extract_action_narrative(operator_transcript_path: str) -> str | None:
    """Return the narrator's action-history narrative for the latest advisor round.

    The narrator runs inside the advisor (depth 3); its narrative is the advisor's
    narrator-call tool_result.  Descend one level — resolve the advisor subagent
    the operator's last advisor call spawned, then read that advisor's narrator
    output — so the log can show how the round progressed (parallax logged the
    in-hook narration directly; here it lives one tier down).  None when it can't
    be resolved (no consultation yet, or the narrator did not run synchronously).
    """
    messages = load_messages(operator_transcript_path)
    advisor_call_id = last_subagent_call_id(messages, "advisor")
    if advisor_call_id is None:
        return None
    subagents_dir = Path(operator_transcript_path).parent
    advisor_transcript = resolve_subagent_transcript(subagents_dir, advisor_call_id)
    if advisor_transcript is None:
        return None
    return extract_subagent_output(advisor_transcript, "narrator")
