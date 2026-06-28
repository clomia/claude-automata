"""Prompt — assemble the deterministic part of the advisor's input.

parallax's prompt.py assembled all five sections in code and handed the
advisor a finished prompt.  anchor can't run the advisor from the hook, but it
can still assemble the *deterministic* sections — original-mission and
parallax-region-history — in code (this module), wrapped in the same XML the
advisor expects.  The hook writes the result to a file the advisor reads once.

Only action-history stays a runtime collection (the advisor calls narrator),
because narrating raw actions needs an LLM; role/instructions live in the
advisor's system prompt.  Pulling everything deterministic into code keeps the
advisor's context lean — the whole point of the plugin over a bare prompt.
"""


def wrap_section(tag: str, content: str) -> str:
    """Wrap content in an XML tag."""
    return f"<{tag}>\n\n{content}\n\n</{tag}>"


def format_region_history(region_history: list[str]) -> str:
    """Format prior regions as <region-N> blocks (parallax prompt.py)."""
    if not region_history:
        return "No prior regions."
    return "\n\n".join(
        f"<region-{i + 1}>\n\n{region}\n\n</region-{i + 1}>"
        for i, region in enumerate(region_history)
    )


def build_analysis_input(mission: str, region_history: list[str]) -> str:
    """Assemble the deterministic sections of the advisor's input.

    original-mission + parallax-region-history, XML-wrapped, mirroring
    parallax build_analysis_prompt.  action-history is collected by the
    advisor at runtime via a narrator call.
    """
    return "\n\n".join(
        [
            wrap_section("original-mission", mission),
            wrap_section(
                "parallax-region-history", format_region_history(region_history)
            ),
        ]
    )
