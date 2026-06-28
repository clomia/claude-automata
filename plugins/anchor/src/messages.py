"""Messages — assemble the stderr feedback the SubagentStop hook injects.

The hook cannot call the Agent tool itself (hooks are code, not the LLM), so
it injects a short instruction telling the anchor to invoke the advisor
subagent with the round's file paths.  The detailed protocol lives in the
anchor system prompt; this message carries only the trigger and the
per-round paths, keeping the anchor's context lean.
"""

from pathlib import Path

MESSAGES_DIR = Path(__file__).parent.parent / "prompts" / "messages"

ADVISOR_TRIGGER_TEMPLATE = (MESSAGES_DIR / "advisor_trigger.md").read_text().strip()


def format_advisor_trigger(*, analysis_path: Path, action_path: Path) -> str:
    """Build the stderr feedback that drives the anchor to invoke the advisor."""
    return ADVISOR_TRIGGER_TEMPLATE.format(
        analysis_path=analysis_path,
        action_path=action_path,
    )
