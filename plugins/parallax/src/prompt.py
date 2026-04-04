"""Prompt — assembles the 5-section XML+Markdown analysis prompt.

Pure string formatting. Reads prompt templates from prompts/ but performs
no subprocess calls or other I/O.
"""

import json
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

ROLE_PROMPT = (PROMPTS_DIR / "role.md").read_text().strip()
INSTRUCTION_PROMPT = (PROMPTS_DIR / "instruction.md").read_text().strip()

CONVERSION_PROMPT_TEMPLATE = """\
다음은 AI 에이전트가 사용자의 요청에 대해 수행한 작업 기록입니다.
이 작업 기록을 설명하는 마크다운 문서를 작성하세요.
에이전트가 어떤 도구를 사용했고, 어떤 결과를 얻었으며, 어떤 판단을 내렸는지 서술하세요.

<action-record>
{actions_json}
</action-record>"""


def wrap_section(tag: str, content: str) -> str:
    """Wrap content in an XML tag."""
    return f"<{tag}>\n\n{content}\n\n</{tag}>"


def format_direction_history(direction_history: list[str]) -> str:
    """Format previous parallax directions for the <parallax-direction-history> section."""
    if not direction_history:
        return "이번 턴에서 이전에 제시한 방향 없음."
    return "\n".join(
        f"- 라운드 {i + 1}: {direction}"
        for i, direction in enumerate(direction_history)
    )


def format_conversion_prompt(actions: list[dict]) -> str:
    """Build the prompt string for the action-to-markdown conversion call."""
    actions_json = json.dumps(actions, ensure_ascii=False, indent=2)
    return CONVERSION_PROMPT_TEMPLATE.format(actions_json=actions_json)


def build_analysis_prompt(
    user_input: str,
    action_history: str,
    direction_history: list[str],
) -> str:
    """Assemble the 5-section analysis prompt. Pure string assembly."""
    sections = [
        wrap_section("role", ROLE_PROMPT),
        wrap_section("original-mission", user_input),
        wrap_section("action-history", action_history),
        wrap_section(
            "parallax-direction-history",
            format_direction_history(direction_history),
        ),
        wrap_section("instructions", INSTRUCTION_PROMPT),
    ]
    return "\n\n".join(sections)
