"""Tests for the prompt module — advice-history formatting and the triggers."""

from pathlib import Path

from src.prompt import (
    format_advice_history,
    format_advisor_trigger,
    format_end_notice,
)


class TestFormatAdviceHistory:
    def test_empty(self):
        assert format_advice_history([]) == "No prior advice."

    def test_single(self):
        assert format_advice_history(["A"]) == "<advice-1>\n\nA\n\n</advice-1>"

    def test_multiple_are_numbered(self):
        out = format_advice_history(["A", "B"])
        assert "<advice-1>\n\nA\n\n</advice-1>" in out
        assert "<advice-2>\n\nB\n\n</advice-2>" in out


class TestFormatAdvisorTrigger:
    def trigger(self, mission_text=None, round_start=100):
        return format_advisor_trigger(
            mission_path=Path("/d/s1_mission.md"),
            transcript_path="/proj/s1.jsonl",
            round_start=round_start,
            advice_history_path=Path("/d/s1_advice_history.md"),
            advice_path=Path("/d/s1_advice.md"),
            narration_path=Path("/t/s1_narration.md"),
            instruction_path=Path("/p/prompts/instruction.md"),
            mission_text=mission_text,
        )

    def test_lists_sections_in_canonical_order(self):
        """role lives in the advisor system prompt; the trigger carries the other
        four in the loop's canonical order, with the narrator call inlined under actions-history."""
        out = self.trigger()
        assert (
            out.index("original-mission:")
            < out.index("actions-history:")
            < out.index("advice-history:")
            < out.index("instructions:")
            < out.index("advice-path:")
        )

    def test_carries_all_paths(self):
        out = self.trigger()
        assert "/d/s1_mission.md" in out
        assert "/proj/s1.jsonl" in out
        assert "/d/s1_advice_history.md" in out
        assert "/d/s1_advice.md" in out
        assert "/t/s1_narration.md" in out
        assert "/p/prompts/instruction.md" in out

    def test_narrator_reads_from_the_rounds_start_line(self):
        """narrator.md contracts on the `transcript` / `round-start-line` /
        `narration-path` labels — it reads from the start and self-bounds the
        round's end, no hook-side parsing and no end offset."""
        out = self.trigger(round_start=100)
        assert "transcript: /proj/s1.jsonl" in out
        assert "round-start-line: 100" in out
        assert "narration-path: /t/s1_narration.md" in out

    def test_directs_main_to_read_advice(self):
        """The trigger tells the main agent to read the advice file after the call
        returns — deterministic delivery, not reliant on the advisor's message."""
        out = self.trigger()
        assert "read its advice at" in out
        assert "/d/s1_advice.md" in out

    def test_inlines_narrator_call_under_advisor(self):
        """The hook authors both invocations verbatim — the advisor call with the
        narrator call inlined inside it (the literal call, nothing for the LLM to
        construct)."""
        out = self.trigger()
        assert 'subagent_type="ploop:advisor"' in out
        assert 'subagent_type="ploop:narrator"' in out

    def test_both_calls_synchronous(self):
        """advisor + inlined narrator both set run_in_background=false."""
        assert self.trigger().count("run_in_background=false") == 2

    def test_directs_exact_fenced_invocation(self):
        """The trigger names the advisor and demands a verbatim invocation,
        fenced as a literal code block."""
        out = self.trigger()
        assert "advisor" in out
        assert "exactly" in out.lower()
        assert out.count("```") == 2

    def test_mission_text_inlined_when_compacted(self):
        """Mechanism 2: the mission text is inlined ahead of the section list on a
        compacted round (recency position)."""
        out = self.trigger(mission_text="THE MISSION BODY")
        assert "THE MISSION BODY" in out
        assert out.index("THE MISSION BODY") < out.index("original-mission:")

    def test_no_mission_text_by_default(self):
        assert "THE MISSION BODY" not in self.trigger()

    def test_no_leftover_placeholders(self):
        out = self.trigger()
        assert "{" not in out and "}" not in out


class TestFormatEndNotice:
    def test_directs_main_to_report_end_and_cause(self):
        out = format_end_notice("the user ran /ploop:stop")
        assert "has ended" in out
        assert "the user ran /ploop:stop" in out
        assert "report" in out.lower()
        assert "{" not in out and "}" not in out

    def test_log_recap_appended_only_when_given(self):
        assert "/d/s1_loop.log" not in format_end_notice("c")
        with_log = format_end_notice("c", log_path=Path("/d/s1_loop.log"))
        assert "Read /d/s1_loop.log" in with_log
        assert "recap" in with_log
