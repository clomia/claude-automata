"""Tests for the prompt module — advice-history formatting and the triggers."""

from pathlib import Path

from src.prompt import (
    INSTRUCTION_PATH,
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
    def trigger(self, anchor_text=None, candidates_pending=False):
        return format_advisor_trigger(
            anchor_path=Path("/d/s1_anchor.md"),
            round_path=Path("/d/s1_round.jsonl"),
            advice_history_path=Path("/d/s1_advice_history.md"),
            advice_path=Path("/d/s1_advice.md"),
            narration_path=Path("/t/s1_narration.md"),
            candidates_path=Path("/t/s1_candidates.md"),
            candidates_pending=candidates_pending,
            instruction_path=Path("/p/prompts/instruction.md"),
            anchor_text=anchor_text,
        )

    def test_lists_sections_in_canonical_order(self):
        """role lives in the advisor system prompt; the trigger carries the other
        four in the loop's canonical order, with the narrator call inlined under action-history."""
        out = self.trigger()
        assert (
            out.index("anchor:")
            < out.index("action-history:")
            < out.index("advice-history:")
            < out.index("instructions:")
            < out.index("advice-path:")
        )

    def test_carries_all_paths(self):
        out = self.trigger()
        assert "/d/s1_anchor.md" in out
        assert "/d/s1_round.jsonl" in out
        assert "/d/s1_advice_history.md" in out
        assert "/d/s1_advice.md" in out
        assert "/t/s1_narration.md" in out
        assert "/t/s1_candidates.md" in out
        assert "/p/prompts/instruction.md" in out

    def test_narrator_gets_the_round_slice_file(self):
        """narrator.md contracts on the `round` / `narration-path` labels — it
        analyzes the whole pre-cut slice file, no offsets, no boundary-finding."""
        out = self.trigger()
        assert "round: /d/s1_round.jsonl" in out
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

    def test_anchor_text_inlined_when_compacted(self):
        """Mechanism 2: the anchor text is inlined ahead of the section list on a
        compacted round (recency position)."""
        out = self.trigger(anchor_text="THE ANCHOR BODY")
        assert "THE ANCHOR BODY" in out
        assert out.index("THE ANCHOR BODY") < out.index("anchor:")

    def test_no_anchor_text_by_default(self):
        assert "THE ANCHOR BODY" not in self.trigger()

    def test_no_leftover_placeholders(self):
        out = self.trigger()
        assert "{" not in out and "}" not in out

    def test_candidates_queue_path_always_rides_the_main_direction(self):
        """The trigger is the loop's one deterministic per-round channel into
        main context, so the queue path rides every trigger — pending or not —
        on the line after the advice-read direction."""
        expected = "Your candidates queue: /t/s1_candidates.md"
        for out in (self.trigger(), self.trigger(candidates_pending=True)):
            assert expected in out
            assert out.index("read its advice at") < out.index("Your candidates queue")

    def test_advisor_sees_candidates_only_when_pending(self):
        """Emptiness is decided in code: the advisor block names the queue only
        on candidates_pending, between advice-history and instructions — a loop
        that never queues candidates keeps its advisor prompt free of the
        promotion domain."""
        out = self.trigger(candidates_pending=True)
        assert "candidates: /t/s1_candidates.md — facts and terms" in out
        assert (
            out.index("advice-history:")
            < out.index("candidates: /t/s1_candidates.md")
            < out.index("instructions:")
        )
        bare = self.trigger()
        assert "uncovered region" not in bare
        assert "candidates: /t/s1_candidates.md —" not in bare


class TestFormatEndNotice:
    def test_directs_main_to_report_end_and_cause(self):
        """Every auto-termination lands here — the advisor's verdict or an anomaly
        failsafe — and the notice reports that cause to the user."""
        out = format_end_notice("the advisor had no further advice to provide")
        assert "has ended" in out
        assert "the advisor had no further advice to provide" in out
        assert "report" in out.lower()
        assert "{" not in out and "}" not in out

    def test_log_recap_appended_only_when_given(self):
        assert "/d/s1_loop.log" not in format_end_notice("c")
        with_log = format_end_notice("c", log_path=Path("/d/s1_loop.log"))
        assert "Read /d/s1_loop.log" in with_log
        assert "recap" in with_log

    def test_candidates_drain_appended_only_when_given(self):
        """A still-loaded queue at termination gets the drain directive; an
        empty one (candidates_path None) leaves the notice silent about it."""
        assert "candidates" not in format_end_notice("c")
        out = format_end_notice("c", candidates_path=Path("/t/s1_candidates.md"))
        assert "The candidates queue at /t/s1_candidates.md still holds entries" in out
        assert "promote or discard each one" in out


def test_instruction_file_carries_termination_token():
    """instruction.md의 토큰 wording과 main.py 상수는 같은 계약의 양면 — 표류는 침묵 고장이 된다."""
    from src.main import TERMINATION_TOKEN

    assert TERMINATION_TOKEN in INSTRUCTION_PATH.read_text()


def test_static_agent_files_carry_trigger_labels():
    """테스트는 trigger 측 라벨만 단정해 왔다 — 정적 파일 측 개정이 조용히 계약을 깨지 못하게 고정."""
    agents = INSTRUCTION_PATH.parent.parent / "agents"
    advisor = (agents / "advisor.md").read_text()
    for label in (
        "anchor",
        "action-history",
        "narration-path",
        "advice-history",
        "instructions",
    ):
        assert label in advisor
    narrator = (agents / "narrator.md").read_text()
    assert "round" in narrator and "narration-path" in narrator
