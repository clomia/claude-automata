"""Tests for the prompt module — audit-history formatting and the round directive."""

from datetime import datetime
from pathlib import Path

from src.prompt import (
    INSTRUCTION_PATH,
    deadline_status,
    format_advice_history,
    format_directive,
    format_end_notice,
)


class TestDeadlineStatus:
    """anchor frontmatter의 deadline — 상태 4종(무선언/remaining/expired/unreadable)과
    경계. 코드는 시각 사실만 만들고 판단은 advisor 몫이다(결정 20)."""

    NOW = datetime.fromisoformat("2026-08-04T19:47+09:00")

    def anchor(self, value):
        return f"---\ndeadline: {value}\n---\n\n# Mission\nbuild"

    def test_remaining_renders_hours_and_minutes(self):
        assert (
            deadline_status(self.anchor("2026-08-04T22:00+09:00"), self.NOW)
            == "2h 13m remaining"
        )

    def test_remaining_under_an_hour_drops_the_hour(self):
        assert (
            deadline_status(self.anchor("2026-08-04T20:17+09:00"), self.NOW)
            == "30m remaining"
        )

    def test_expired_renders_elapsed(self):
        assert (
            deadline_status(self.anchor("2026-08-04T19:24+09:00"), self.NOW)
            == "expired 23m ago"
        )

    def test_cross_timezone_arithmetic(self):
        """deadline과 now의 timezone이 달라도 aware 연산으로 정확하다."""
        now_utc = datetime.fromisoformat("2026-08-04T12:00+00:00")
        assert (
            deadline_status(self.anchor("2026-08-04T22:00+09:00"), now_utc)
            == "1h 0m remaining"
        )

    def test_timezone_missing_is_unreadable_not_dropped(self):
        out = deadline_status(self.anchor("2026-08-04T22:00"), self.NOW)
        assert out.startswith("unreadable:") and "2026-08-04T22:00" in out

    def test_garbage_value_is_unreadable(self):
        assert deadline_status(self.anchor("tomorrow-ish"), self.NOW).startswith(
            "unreadable:"
        )

    def test_undeclared_forms_are_silent(self):
        """frontmatter 부재·key 부재·본문 산문 key·닫히지 않은 block — 전부 무선언."""
        for anchor in (
            "# Mission\nbuild",
            "---\ntitle: x\n---\nbody",
            "# Mission\ndeadline: 2026-08-04T22:00+09:00 까지다",
            "---\ndeadline: 2026-08-04T22:00+09:00\nbody without close",
        ):
            assert deadline_status(anchor, self.NOW) == ""


class TestFormatAdviceHistory:
    def test_empty(self):
        assert format_advice_history([]) == "No prior audits."

    def test_single(self):
        assert format_advice_history(["A"]) == "<audit-1>\n\nA\n\n</audit-1>"

    def test_multiple_are_numbered(self):
        out = format_advice_history(["A", "B"])
        assert "<audit-1>\n\nA\n\n</audit-1>" in out
        assert "<audit-2>\n\nB\n\n</audit-2>" in out


class TestFormatDirective:
    def directive(self, anchor_text=None, candidates_pending=False, deadline=""):
        return format_directive(
            anchor_path=Path("/d/s1_anchor.md"),
            round_path=Path("/d/s1_round.jsonl"),
            log_path=Path("/d/s1_loop.log"),
            advice_history_path=Path("/d/s1_advice_history.md"),
            advice_path=Path("/d/s1_advice.md"),
            narration_path=Path("/t/s1_narration.md"),
            candidates_path=Path("/t/s1_candidates.md"),
            candidates_pending=candidates_pending,
            instruction_path=Path("/p/prompts/instruction.md"),
            anchor_text=anchor_text,
            deadline=deadline,
        )

    def test_narrator_then_judgment_then_audit_call(self):
        """The standing directive: narrate the finished round first (the flight
        recorder is unconditional), then judge — keep working, or convene."""
        out = self.directive()
        assert (
            out.index("Narrate the finished round")
            < out.index("keep working now")
            < out.index("ONLY when you judge the mission complete")
        )

    def test_both_calls_verbatim_and_synchronous(self):
        """The hook authors both invocations verbatim, fenced, each behind an
        EXACTLY-as-written demand; both are synchronous — the next action
        depends on each result."""
        out = self.directive()
        assert 'subagent_type="ploop:narrator"' in out
        assert 'subagent_type="ploop:advisor"' in out
        assert out.count("run_in_background=false") == 2
        assert out.count("```") == 4
        assert out.count("EXACTLY as written") == 2

    def test_lists_advisor_sections_in_canonical_order(self):
        """role lives in the advisor system prompt; the call carries the other
        sections in the loop's canonical order."""
        out = self.directive()
        assert (
            out.index("anchor:")
            < out.index("action-history:")
            < out.index("audit-history:")
            < out.index("instructions:")
            < out.index("report-path:")
        )

    def test_action_history_is_log_then_fresh_narration(self):
        """The audit's action-history input is the accumulated loop log plus the
        freshest round's narration — bounded no matter how long the mission ran,
        and the consensus lane (steering, rebuttals) rides the narration."""
        assert (
            "action-history: /d/s1_loop.log then /t/s1_narration.md" in self.directive()
        )

    def test_carries_all_paths(self):
        out = self.directive()
        for path in (
            "/d/s1_anchor.md",
            "/d/s1_round.jsonl",
            "/d/s1_loop.log",
            "/d/s1_advice_history.md",
            "/d/s1_advice.md",
            "/t/s1_narration.md",
            "/t/s1_candidates.md",
            "/p/prompts/instruction.md",
        ):
            assert path in out

    def test_narrator_gets_the_round_slice_file(self):
        """narrator.md contracts on the `round` / `narration-path` labels — it
        analyzes the whole pre-cut slice file, no offsets, no boundary-finding."""
        out = self.directive()
        assert "round: /d/s1_round.jsonl" in out
        assert "narration-path: /t/s1_narration.md" in out

    def test_directs_main_to_read_the_report_as_observation(self):
        """The report is read from the file channel and consumed critically:
        findings are observations to judge against the anchor, not orders."""
        out = self.directive()
        assert "read its report at /d/s1_advice.md" in out
        assert "observations, not orders" in out
        assert "Only the advisor can certify completion." in out

    def test_silent_exit_is_not_disclosed(self):
        """The bare-stop failsafe is disclosed only in the decline notice —
        the steady-state directive keeps the audit as the only visible exit."""
        out = self.directive()
        assert "loop will end" not in out
        assert "/ploop:on" not in out

    def test_deadline_surfaces_to_both_participants(self):
        """One status string, two readers: a header line for the main agent
        (convening is its decision) and the same line inside the advisor
        prompt, after anchor.  Undeclared leaves no trace."""
        out = self.directive(deadline="2h 13m remaining")
        assert out.count("deadline: 2h 13m remaining") == 2
        assert out.index("deadline:") < out.index("Narrate the finished round")
        assert (
            out.index("anchor:")
            < out.index("deadline:", out.index("anchor:"))
            < out.index("action-history:")
        )
        assert "deadline" not in self.directive()

    def test_expired_deadline_mandates_the_audit(self):
        """expired closes the keep-working branch: the directive itself becomes
        the convening order — judgment stays with the advisor."""
        out = self.directive(deadline="expired 23m ago")
        assert "NOW" in out
        assert "keep working" not in out
        assert 'subagent_type="ploop:narrator"' in out  # the recorder still runs

    def test_unreadable_deadline_keeps_the_normal_branches(self):
        out = self.directive(deadline="unreadable: tomorrow-ish")
        assert "keep working now" in out
        assert "unreadable: tomorrow-ish" in out

    def test_anchor_text_inlined_when_compacted(self):
        """Mechanism 2: the anchor text is inlined ahead of the directive on a
        compacted round (recency position)."""
        out = self.directive(anchor_text="THE ANCHOR BODY")
        assert "THE ANCHOR BODY" in out
        assert out.index("THE ANCHOR BODY") < out.index("Narrate the finished round")

    def test_no_anchor_text_by_default(self):
        assert "THE ANCHOR BODY" not in self.directive()

    def test_no_leftover_placeholders(self):
        out = self.directive()
        assert "{" not in out and "}" not in out

    def test_candidates_queue_path_always_rides_the_main_direction(self):
        """The directive is the loop's one deterministic per-round channel into
        main context, so the queue path rides every injection — pending or not."""
        expected = "Your candidates queue: /t/s1_candidates.md"
        for out in (self.directive(), self.directive(candidates_pending=True)):
            assert expected in out
            assert out.index("certify completion") < out.index("Your candidates queue")

    def test_advisor_sees_candidates_only_when_pending(self):
        """Emptiness is decided in code: the advisor block names the queue only
        on candidates_pending, between audit-history and instructions — a loop
        that never queues candidates keeps its advisor prompt free of the
        promotion domain."""
        out = self.directive(candidates_pending=True)
        assert "candidates: /t/s1_candidates.md — facts and terms" in out
        assert "un-promoted remainder is unfinished work" in out
        assert (
            out.index("audit-history:")
            < out.index("candidates: /t/s1_candidates.md")
            < out.index("instructions:")
        )
        bare = self.directive()
        assert "queued for promotion" not in bare
        assert "candidates: /t/s1_candidates.md —" not in bare


class TestFormatEndNotice:
    def test_directs_main_to_report_end_and_cause(self):
        """Every auto-termination lands here — the advisor's verdict or an anomaly
        failsafe — and the notice reports that cause to the user."""
        out = format_end_notice("the advisor confirmed the mission complete")
        assert "has ended" in out
        assert "the advisor confirmed the mission complete" in out
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


def test_decline_notice_discloses_the_silent_exit():
    """The one place the silent exit is disclosed: after a first unanswered
    directive, the second silence must be an informed signal — and the notice
    names no actor (an unconsumed token may equally come from an ESC)."""
    from src.main import DECLINE_NOTICE

    assert "certify completion belongs to the advisor" in DECLINE_NOTICE
    assert "loop will end" in DECLINE_NOTICE
    assert "/ploop:on" in DECLINE_NOTICE
    assert "you" not in DECLINE_NOTICE.split("Invoke")[0].lower()


def test_static_agent_files_carry_directive_labels():
    """테스트는 directive 측 라벨만 단정해 왔다 — 정적 파일 측 개정이 조용히 계약을 깨지 못하게 고정."""
    agents = INSTRUCTION_PATH.parent.parent / "agents"
    advisor = (agents / "advisor.md").read_text()
    for label in (
        "anchor",
        "action-history",
        "narration",
        "audit-history",
        "instructions",
    ):
        assert label in advisor
    narrator = (agents / "narrator.md").read_text()
    assert "round" in narrator and "narration-path" in narrator
