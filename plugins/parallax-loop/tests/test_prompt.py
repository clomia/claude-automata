"""Tests for the prompt module — region-history formatting and the trigger."""

from pathlib import Path

from src.prompt import format_advisor_trigger, format_region_history


class TestFormatRegionHistory:
    def test_empty(self):
        assert format_region_history([]) == "No prior regions."

    def test_single(self):
        assert format_region_history(["A"]) == "<region-1>\n\nA\n\n</region-1>"

    def test_multiple_are_numbered(self):
        out = format_region_history(["A", "B"])
        assert "<region-1>\n\nA\n\n</region-1>" in out
        assert "<region-2>\n\nB\n\n</region-2>" in out


class TestFormatAdvisorTrigger:
    def trigger(self, mission_text=None):
        return format_advisor_trigger(
            mission_path=Path("/d/s1_mission.md"),
            action_path=Path("/d/s1_action.json"),
            regions_path=Path("/d/s1_regions.md"),
            instruction_path=Path("/p/prompts/instruction.md"),
            mission_text=mission_text,
        )

    def test_lists_sections_in_parallax_order(self):
        """role lives in the advisor system prompt; the trigger carries the other
        four in parallax's order, with the narrator call inlined under actions-history."""
        out = self.trigger()
        assert (
            out.index("original-mission:")
            < out.index("actions-history:")
            < out.index("parallax-region-history:")
            < out.index("instructions:")
        )

    def test_carries_all_paths(self):
        out = self.trigger()
        assert "/d/s1_mission.md" in out
        assert "/d/s1_action.json" in out
        assert "/d/s1_regions.md" in out
        assert "/p/prompts/instruction.md" in out

    def test_inlines_narrator_call_under_advisor(self):
        """The hook authors both invocations verbatim — the advisor call with the
        narrator call inlined inside it (the literal call, nothing for the LLM to
        construct)."""
        out = self.trigger()
        assert 'subagent_type="parallax-loop:advisor"' in out
        assert 'subagent_type="parallax-loop:narrator"' in out

    def test_both_calls_synchronous(self):
        """advisor + inlined narrator, both run_in_background=false (the param
        precedes each call's prompt)."""
        assert self.trigger().count("run_in_background=false, prompt=") == 2

    def test_directs_verbatim_synchronous(self):
        out = self.trigger().lower()
        assert "verbatim" in out
        assert "synchronous" in out

    def test_mission_text_inlined_when_compacted(self):
        """Mechanism 2: the mission text is inlined at recency on a compacted round."""
        out = self.trigger(mission_text="THE MISSION BODY")
        assert "THE MISSION BODY" in out
        assert "compaction" in out.lower()

    def test_no_mission_text_by_default(self):
        assert "THE MISSION BODY" not in self.trigger()

    def test_no_leftover_placeholders(self):
        out = self.trigger()
        assert "{" not in out and "}" not in out
