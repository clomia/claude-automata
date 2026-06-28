"""Tests for the messages module."""

from pathlib import Path

from src.messages import format_advisor_trigger


class TestFormatAdvisorTrigger:
    def test_fills_both_paths(self):
        out = format_advisor_trigger(
            analysis_path=Path("/data/s1_analysis.md"),
            action_path=Path("/data/s1_action.json"),
        )
        assert "/data/s1_analysis.md" in out
        assert "/data/s1_action.json" in out

    def test_instructs_advisor_invocation(self):
        out = format_advisor_trigger(analysis_path=Path("/a"), action_path=Path("/b"))
        assert "advisor" in out

    def test_no_leftover_placeholders(self):
        out = format_advisor_trigger(analysis_path=Path("/a"), action_path=Path("/b"))
        assert "{analysis_path}" not in out
        assert "{action_path}" not in out
