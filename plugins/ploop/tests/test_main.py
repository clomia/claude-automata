"""Tests for the main module — Stop, PreToolUse, UserPromptSubmit, PostCompact entry points.

The hook owns the whole ledger: it records the advisor's prior-round verdict
(the region it wrote to advice.md, or done on an absent file / the termination
token — parallax's rule), then drives the next round.  These tests drive `stop`
with a main transcript plus the advisor's advice.md, the sole region channel.
"""

import io
import json

import pytest

from src.main import (
    TERMINATION_TOKEN,
    launch,
    mark_compaction,
    pre_tool_use,
    stop,
    subagent_stop,
    user_prompt_submit,
    write_log,
)
from src.state import ROUND_LIMIT, load_ledger, save_ledger

# A minimal round transcript: a trigger boundary + the main agent's own work.
# The region no longer comes from here — advice.md is the sole channel — so this
# only feeds parse_round_actions (which writes the narrator's action file).
ROUND_WORK = [
    {"role": "user", "content": "advisor trigger"},
    {"role": "assistant", "content": "working on the region"},
]


def make_stdin(*, session_id="s1", transcript_path="/t.jsonl"):
    return json.dumps({"session_id": session_id, "transcript_path": transcript_path})


def make_pretooluse_stdin(*, session_id="s1", subagent_type="ploop:advisor"):
    return json.dumps(
        {
            "session_id": session_id,
            "tool_name": "Agent",
            "tool_input": {"subagent_type": subagent_type},
        }
    )


def write_jsonl(path, messages):
    path.write_text("\n".join(json.dumps({"message": m}) for m in messages))


def arrange(tmp_path, monkeypatch, stdin):
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin))


def arrange_mission(
    tmp_path,
    monkeypatch,
    main_messages,
    *,
    session_id="s1",
    ledger=None,
    advice=None,
    narration=None,
):
    """Activate a mission and write the main transcript holding `main_messages`.

    The main agent runs the mission directly, so its work lives in the main session
    transcript the Stop hook receives.  The active marker gates the loop; the mission
    file is the anchor.  `advice` / `narration` (when given) are the advisor's and
    narrator's temp-channel files, routed under tmp_path via gettempdir.
    """
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    (tmp_path / f"{session_id}_active").touch()
    (tmp_path / f"{session_id}_mission.md").write_text("build the thing")
    if ledger:
        save_ledger(tmp_path / f"{session_id}_loop.json", **ledger)
    if advice is not None:
        (tmp_path / f"ploop_{session_id}_advice.md").write_text(advice)
    if narration is not None:
        (tmp_path / f"ploop_{session_id}_narration.md").write_text(narration)
    main = tmp_path / f"{session_id}.jsonl"
    write_jsonl(main, main_messages)
    arrange(
        tmp_path,
        monkeypatch,
        make_stdin(session_id=session_id, transcript_path=str(main)),
    )


# ── stop branches ──


class TestStop:
    def test_no_active_marker_allows_stop(self, tmp_path, monkeypatch):
        arrange(tmp_path, monkeypatch, make_stdin())
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 0

    def test_malformed_event_allows_stop(self, tmp_path, monkeypatch):
        """A hook must never break the session: unparseable stdin degrades to
        exit 0 instead of crashing."""
        arrange(tmp_path, monkeypatch, "not json")
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 0

    def test_done_flag_allows_stop(self, tmp_path, monkeypatch):
        (tmp_path / "s1_active").touch()
        save_ledger(tmp_path / "s1_loop.json", round_number=2, regions=["r"], done=True)
        arrange(tmp_path, monkeypatch, make_stdin())
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 0

    def test_round_zero_writes_regions_and_injects(self, tmp_path, monkeypatch, capsys):
        arrange_mission(
            tmp_path,
            monkeypatch,
            [
                {"role": "user", "content": "mission"},
                {"role": "assistant", "content": "initial work"},
            ],
        )
        (tmp_path / "s1_launching").touch()  # a leaked sentinel must be consumed
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        assert not (tmp_path / "s1_launching").exists()  # consumed by stop()
        assert load_ledger(tmp_path / "s1_loop.json")["round"] == 1
        assert "No prior regions." in (tmp_path / "s1_regions.md").read_text()
        err = capsys.readouterr().err
        assert "original-mission:" in err
        assert str(tmp_path / "s1_mission.md") in err
        assert "parallax-region-history:" in err
        assert "instructions:" in err
        assert "ploop:advisor" in err
        assert (tmp_path / "s1_advisor_token").exists()

    def test_records_region_and_narration_into_log(self, tmp_path, monkeypatch):
        arrange_mission(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"round_number": 1, "regions": [], "done": False},
            advice="consider error handling",
            narration="initial work narrative",
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["round"] == 2
        assert ledger["regions"] == ["consider error handling"]
        regions = (tmp_path / "s1_regions.md").read_text()
        assert "<region-1>" in regions
        assert "consider error handling" in regions
        # The log pairs the narrated work with the region it produced (parallax's
        # shape), under "Round 1" — the first region is round 1.
        log = (tmp_path / "s1_loop.log").read_text()
        assert "[[ Round 1 / Action History ]]" in log
        assert "initial work narrative" in log
        assert "[[ Round 1 / Region ]]" in log
        assert "consider error handling" in log

    def test_advice_and_narration_cleared_on_arm(self, tmp_path, monkeypatch):
        """Both temp channels are read (advice stripped), then cleared as the next
        round arms — an absent file next round unambiguously means no write."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"round_number": 1, "regions": [], "done": False},
            advice="  consider concurrency  ",
            narration="did things",
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        assert load_ledger(tmp_path / "s1_loop.json")["regions"] == [
            "consider concurrency"
        ]
        assert not (tmp_path / "ploop_s1_advice.md").exists()
        assert not (tmp_path / "ploop_s1_narration.md").exists()

    def test_log_numbering_is_ordinal_after_skipped_round(self, tmp_path, monkeypatch):
        """A skipped round advances current_round without a region; numbering by
        region ordinal keeps the log aligned with regions.md — no drift, no gap."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"round_number": 4, "regions": ["r1", "r2"], "done": False},
            advice="r3",
            narration="work",
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        log = (tmp_path / "s1_loop.log").read_text()
        assert "[[ Round 3" in log
        assert "Round 4" not in log

    def test_absent_advice_terminates(self, tmp_path, monkeypatch):
        """advice.md is the sole channel: the advisor finished (no running marker)
        and wrote nothing, so the turn ends — parallax's empty-output=terminate.
        No region was ever surfaced, so no summary turn is spent (exit 0), but the
        final work still lands in the log."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"round_number": 1, "regions": [], "done": False},
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 0
        assert load_ledger(tmp_path / "s1_loop.json")["done"] is True
        assert not (tmp_path / "s1_active").exists()
        log = (tmp_path / "s1_loop.log").read_text()
        assert "(no output)" in log
        assert "(no narration)" in log

    def test_compacted_round_inlines_mission_text(self, tmp_path, monkeypatch, capsys):
        """Mechanism 2: a compacted round re-injects the original-mission text into
        the trigger and consumes the marker."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"round_number": 1, "regions": [], "done": False},
            advice="region",
        )
        (tmp_path / "s1_compacted").touch()
        with pytest.raises(SystemExit):
            stop()
        err = capsys.readouterr().err
        assert "build the thing" in err  # original-mission text inlined
        assert not (tmp_path / "s1_compacted").exists()  # consumed

    def test_termination_token_ends_loop_and_triggers_summary(
        self, tmp_path, monkeypatch, capsys
    ):
        """Termination on a turn that surfaced regions: done + deactivated, the
        final round's work logged beside the token, and one last injection has
        the main agent summarize the round log."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"round_number": 2, "regions": ["r"], "done": False},
            advice=f"All paths covered. {TERMINATION_TOKEN}",
            narration="final round work",
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["done"] is True
        assert ledger["regions"] == ["r"]
        assert not (tmp_path / "s1_active").exists()
        # terminating entry: the final work, numbered after the last region
        log = (tmp_path / "s1_loop.log").read_text()
        assert "[[ Round 2 / Action History ]]" in log
        assert "final round work" in log
        # the summary trigger points the main agent at the log
        err = capsys.readouterr().err
        assert str(tmp_path / "s1_loop.log") in err
        assert "summary" in err

    def test_round_limit_ends_loop_and_triggers_summary(
        self, tmp_path, monkeypatch, capsys
    ):
        arrange_mission(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"round_number": ROUND_LIMIT, "regions": [], "done": False},
            advice="a late region",
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        assert not (tmp_path / "s1_active").exists()
        # the round-limit round's region is logged, not dropped before write_log
        assert "a late region" in (tmp_path / "s1_loop.log").read_text()
        assert str(tmp_path / "s1_loop.log") in capsys.readouterr().err

    def test_running_marker_pauses_without_retrigger(self, tmp_path, monkeypatch):
        """Running marker present (advisor in flight — e.g. the user pushed it to the
        background): allow the stop, don't re-trigger — no cascade.  SubagentStop is
        the marker's sole clearer, so the loop just waits for it."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"round_number": 1, "regions": [], "done": False},
        )
        (tmp_path / "s1_advisor_running").touch()
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 0
        # ledger untouched, marker left in place — the loop just waits
        assert load_ledger(tmp_path / "s1_loop.json")["round"] == 1
        assert (tmp_path / "s1_advisor_running").exists()

    def test_token_present_skips_recording(self, tmp_path, monkeypatch):
        """Advisor NOT invoked this round (token still present): don't re-append a
        prior round's region as a duplicate, even if a stale advice file lingers."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"round_number": 2, "regions": ["prior region"], "done": False},
            advice="prior region",
        )
        (tmp_path / "s1_advisor_token").write_text("")
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["regions"] == ["prior region"]  # not duplicated
        assert ledger["round"] == 3


# ── pre_tool_use gating ──


class TestPreToolUse:
    def test_token_present_allows_consumes_and_marks_running(
        self, tmp_path, monkeypatch
    ):
        (tmp_path / "s1_active").touch()
        token = tmp_path / "s1_advisor_token"
        token.write_text("")
        arrange(tmp_path, monkeypatch, make_pretooluse_stdin())
        with pytest.raises(SystemExit) as exc:
            pre_tool_use()
        assert exc.value.code == 0
        assert not token.exists()
        assert (tmp_path / "s1_advisor_running").exists()

    def test_no_active_marker_allows_manual_advisor(self, tmp_path, monkeypatch):
        """Outside an active mission the advisor gate does not interfere."""
        arrange(tmp_path, monkeypatch, make_pretooluse_stdin())
        with pytest.raises(SystemExit) as exc:
            pre_tool_use()
        assert exc.value.code == 0

    def test_no_token_denies_self_initiated_call(self, tmp_path, monkeypatch):
        (tmp_path / "s1_active").touch()
        arrange(tmp_path, monkeypatch, make_pretooluse_stdin())
        with pytest.raises(SystemExit) as exc:
            pre_tool_use()
        assert exc.value.code == 2

    def test_non_advisor_call_passes_through(self, tmp_path, monkeypatch):
        (tmp_path / "s1_active").touch()
        arrange(
            tmp_path,
            monkeypatch,
            make_pretooluse_stdin(subagent_type="ploop:narrator"),
        )
        with pytest.raises(SystemExit) as exc:
            pre_tool_use()
        assert exc.value.code == 0


# ── subagent_stop advisor-running marker ──


class TestSubagentStop:
    def test_advisor_stop_clears_running_marker(self, tmp_path, monkeypatch):
        (tmp_path / "s1_advisor_running").touch()
        arrange(
            tmp_path,
            monkeypatch,
            json.dumps({"session_id": "s1", "agent_type": "advisor"}),
        )
        subagent_stop()
        assert not (tmp_path / "s1_advisor_running").exists()

    def test_narrator_stop_leaves_marker(self, tmp_path, monkeypatch):
        (tmp_path / "s1_advisor_running").touch()
        arrange(
            tmp_path,
            monkeypatch,
            json.dumps({"session_id": "s1", "agent_type": "narrator"}),
        )
        with pytest.raises(SystemExit):
            subagent_stop()
        assert (tmp_path / "s1_advisor_running").exists()


# ── user_prompt_submit turn-boundary cleanup ──


class TestUserPromptSubmit:
    def test_clears_loop_state_keeps_anchor(self, tmp_path, monkeypatch):
        """A new user turn clears active marker, ledger, token, and compaction
        marker — so an ESC-interrupted mission never resumes and no stale token
        leaks; the mission anchor stays."""
        for name in ("s1_active", "s1_advisor_token", "s1_compacted"):
            (tmp_path / name).touch()
        (tmp_path / "s1_mission.md").write_text("m")
        save_ledger(
            tmp_path / "s1_loop.json", round_number=3, regions=["r"], done=False
        )
        arrange(
            tmp_path,
            monkeypatch,
            json.dumps({"session_id": "s1", "prompt": "do something else"}),
        )
        user_prompt_submit()
        assert not (tmp_path / "s1_active").exists()
        assert not (tmp_path / "s1_loop.json").exists()
        assert not (tmp_path / "s1_advisor_token").exists()
        assert not (tmp_path / "s1_compacted").exists()
        assert (tmp_path / "s1_mission.md").exists()

    def test_launch_turn_keeps_active_via_sentinel(self, tmp_path, monkeypatch):
        """On a /ploop:launch turn the launching sentinel is present: the fresh
        active marker (and mission) survive cleanup; the sentinel is consumed."""
        (tmp_path / "s1_active").touch()
        (tmp_path / "s1_mission.md").write_text("fresh mission")
        (tmp_path / "s1_launching").touch()
        save_ledger(
            tmp_path / "s1_loop.json", round_number=9, regions=["stale"], done=True
        )
        (tmp_path / "s1_advisor_token").touch()
        arrange(tmp_path, monkeypatch, json.dumps({"session_id": "s1"}))
        user_prompt_submit()
        assert (tmp_path / "s1_active").exists()  # spared
        assert not (tmp_path / "s1_launching").exists()  # consumed
        assert not (tmp_path / "s1_loop.json").exists()  # stale ledger cleared
        assert not (tmp_path / "s1_advisor_token").exists()
        assert (tmp_path / "s1_mission.md").exists()

    def test_running_marker_preserves_loop(self, tmp_path, monkeypatch):
        """A running marker (advisor in flight) makes an incidental user turn leave
        the whole loop intact — SubagentStop, not this hook, clears the marker."""
        for name in ("s1_active", "s1_advisor_running"):
            (tmp_path / name).touch()
        save_ledger(
            tmp_path / "s1_loop.json", round_number=2, regions=["r"], done=False
        )
        arrange(tmp_path, monkeypatch, json.dumps({"session_id": "s1"}))
        user_prompt_submit()
        assert (tmp_path / "s1_active").exists()  # loop survives the interjection
        assert (tmp_path / "s1_loop.json").exists()
        assert (tmp_path / "s1_advisor_running").exists()


# ── mark_compaction ──


class TestMarkCompaction:
    def test_touches_compacted_marker(self, tmp_path, monkeypatch):
        arrange(tmp_path, monkeypatch, json.dumps({"session_id": "s1"}))
        mark_compaction()
        assert (tmp_path / "s1_compacted").exists()


# ── /ploop:launch UserPromptExpansion hook ──


class TestLaunch:
    def make_stdin(self, **payload):
        return io.StringIO(json.dumps(payload))

    def test_writes_stripped_mission_and_arms_loop(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        mission = '  do the thing\nwith "quotes" and $vars  '
        monkeypatch.setattr(
            "sys.stdin",
            self.make_stdin(
                command_name="ploop:launch", command_args=mission, session_id="s1"
            ),
        )
        save_ledger(
            tmp_path / "s1_loop.json", round_number=9, regions=["stale"], done=True
        )
        (tmp_path / "s1_loop.log").write_text("prior mission log")
        launch()
        saved = (tmp_path / "s1_mission.md").read_text()
        assert saved == 'do the thing\nwith "quotes" and $vars'
        assert (tmp_path / "s1_active").exists()
        assert (tmp_path / "s1_launching").exists()  # sentinel for user_prompt_submit
        assert not (tmp_path / "s1_loop.json").exists()  # prior ledger cleared
        assert not (tmp_path / "s1_loop.log").exists()  # a mission owns one log

    def test_ignores_non_ploop_launch_command(self, tmp_path, monkeypatch):
        """The guard matches the full scoped name, so another plugin's :launch
        cannot hijack ploop's launch."""
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        monkeypatch.setattr(
            "sys.stdin",
            self.make_stdin(
                command_name="other:launch", command_args="x", session_id="s1"
            ),
        )
        with pytest.raises(SystemExit):
            launch()
        assert not (tmp_path / "s1_mission.md").exists()
        assert not (tmp_path / "s1_active").exists()

    def test_blank_mission_does_not_arm(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        monkeypatch.setattr(
            "sys.stdin",
            self.make_stdin(
                command_name="ploop:launch", command_args="   ", session_id="s1"
            ),
        )
        with pytest.raises(SystemExit):
            launch()
        assert not (tmp_path / "s1_active").exists()


# ── write_log ──


class TestWriteLog:
    def test_appends_titled_sections_across_rounds(self, tmp_path):
        log = tmp_path / "l.log"
        write_log(log, 1, action_history="work-1", region="r1")
        write_log(log, 2, action_history="work-2", region="r2")
        content = log.read_text()
        assert "[[ Round 1 / Action History ]]" in content
        assert "[[ Round 1 / Region ]]" in content
        assert "[[ Round 2 / Region ]]" in content
        # sections appear in call order, rounds in append order
        assert (
            content.index("work-1")
            < content.index("r1")
            < content.index("work-2")
            < content.index("r2")
        )
