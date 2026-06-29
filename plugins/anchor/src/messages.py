"""Messages — the stderr feedback the SubagentStop hook injects.

The hook can't call the Agent tool itself (hooks are code, not the LLM), so it
injects an executable tool-call line telling the anchor to consult the advisor
with the round's file paths.  The protocol lives in the advisor's agent.md;
this carries only the call.
"""

from pathlib import Path


def format_advisor_trigger(*, analysis_path: Path, action_path: Path) -> str:
    """Build the stderr feedback that drives the anchor to invoke the advisor."""
    return (
        'Consult advisor: `Agent(subagent_type="anchor:advisor", '
        'description="region review", '
        f'prompt="history={analysis_path}, latest_action={action_path}")`'
    )


def format_region_notice(round_number: int, region: str) -> str:
    """User-facing systemMessage: the region the advisor surfaced for this round."""
    return f"anchor · round {round_number} — advisor가 짚은 영역:\n\n{region}"


def format_termination_notice() -> str:
    """User-facing systemMessage: the parallax turn ended (no region left)."""
    return "anchor · parallax 종료 — advisor가 더 surface할 영역을 찾지 못했습니다."
