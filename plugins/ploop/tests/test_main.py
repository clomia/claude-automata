"""Tests for the main module — Stop, PreToolUse, UserPromptSubmit, PostCompact entry points.

The hook owns the whole ledger: it records the advisor's prior-round verdict
(region, or done on empty output / the termination token — parallax's rule),
then drives the next round.  These tests drive `stop` with a main transcript
that mocks the main agent's Agent(advisor) exchange directly.
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


def advisor_returns(region):
    """A main agent turn whose Agent(advisor) call returned `region`."""
    return [
        {"role": "user", "content": "advisor trigger"},
        {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "a1",
                    "name": "Agent",
                    "input": {"subagent_type": "advisor"},
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "a1", "content": region}
            ],
        },
        {"role": "assistant", "content": "working on the region"},
    ]


def arrange(tmp_path, monkeypatch, stdin):
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin))


def arrange_mission(
    tmp_path, monkeypatch, main_messages, *, session_id="s1", ledger=None
):
    """Activate a mission and write the main transcript holding `main_messages`.

    The main agent runs the mission directly, so its work — including the
    Agent(advisor) exchange — lives in the main session transcript the Stop hook
    receives.  The active marker gates the loop; the mission file is the anchor.
    """
    (tmp_path / f"{session_id}_active").touch()
    (tmp_path / f"{session_id}_mission.md").write_text("build the thing")
    if ledger:
        save_ledger(tmp_path / f"{session_id}_loop.json", **ledger)
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
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        assert load_ledger(tmp_path / "s1_loop.json")["round"] == 1
        assert "No prior regions." in (tmp_path / "s1_regions.md").read_text()
        err = capsys.readouterr().err
        assert "original-mission:" in err
        assert str(tmp_path / "s1_mission.md") in err
        assert "parallax-region-history:" in err
        assert "instructions:" in err
        assert "ploop:advisor" in err
        assert (tmp_path / "s1_advisor_token").exists()

    def test_records_region_into_next_regions_file(self, tmp_path, monkeypatch):
        arrange_mission(
            tmp_path,
            monkeypatch,
            advisor_returns("consider error handling"),
            ledger={"round_number": 1, "regions": [], "done": False},
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
        # logged under "Round 1" (parallax parity: the first region is round 1)
        log = (tmp_path / "s1_loop.log").read_text()
        assert "consider error handling" in log
        assert "[[ Round 1" in log

    def test_advice_file_overrides_transcript_and_clears_on_arm(
        self, tmp_path, monkeypatch
    ):
        """The region is read from the advisor's advice file (not scraped from its
        prose-polluted transcript), stripped, then cleared as the next round arms."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            advisor_returns("analysis prose... --- consider concurrency"),
            ledger={"round_number": 1, "regions": [], "done": False},
        )
        (tmp_path / "s1_advice.md").write_text("  consider concurrency  ")
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        assert load_ledger(tmp_path / "s1_loop.json")["regions"] == [
            "consider concurrency"
        ]
        assert not (tmp_path / "s1_advice.md").exists()

    def test_empty_verdict_terminates(self, tmp_path, monkeypatch):
        """parallax's rule: an empty advisor output ends the turn (done, deactivate)."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            advisor_returns(""),
            ledger={"round_number": 1, "regions": [], "done": False},
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 0
        assert load_ledger(tmp_path / "s1_loop.json")["done"] is True
        assert not (tmp_path / "s1_active").exists()

    def test_compacted_round_inlines_mission_text(self, tmp_path, monkeypatch, capsys):
        """Mechanism 2: a compacted round re-injects the original-mission text into
        the trigger and consumes the marker."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            advisor_returns("region"),
            ledger={"round_number": 1, "regions": [], "done": False},
        )
        (tmp_path / "s1_compacted").touch()
        with pytest.raises(SystemExit):
            stop()
        err = capsys.readouterr().err
        assert "build the thing" in err  # original-mission text inlined
        assert not (tmp_path / "s1_compacted").exists()  # consumed

    def test_termination_token_sets_done_and_deactivates(self, tmp_path, monkeypatch):
        arrange_mission(
            tmp_path,
            monkeypatch,
            advisor_returns(f"All paths covered. {TERMINATION_TOKEN}"),
            ledger={"round_number": 2, "regions": ["r"], "done": False},
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 0
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["done"] is True
        assert ledger["regions"] == ["r"]
        assert not (tmp_path / "s1_active").exists()

    def test_round_limit_deactivates_and_allows_stop(self, tmp_path, monkeypatch):
        arrange_mission(
            tmp_path,
            monkeypatch,
            advisor_returns("a late region"),
            ledger={"round_number": ROUND_LIMIT, "regions": [], "done": False},
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 0
        assert not (tmp_path / "s1_active").exists()
        # the round-limit round's region is logged, not dropped before write_log
        assert "a late region" in (tmp_path / "s1_loop.log").read_text()

    def test_backgrounded_advisor_pauses_without_retrigger(self, tmp_path, monkeypatch):
        """Running marker present and the advisor's result not settled (user pushed
        it to the background): allow the stop, don't re-trigger — no cascade."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            advisor_returns("Async agent launched. Working in the background."),
            ledger={"round_number": 1, "regions": [], "done": False},
        )
        (tmp_path / "s1_advisor_running").touch()
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 0
        # ledger untouched, marker left in place — the loop just waits
        assert load_ledger(tmp_path / "s1_loop.json")["round"] == 1
        assert (tmp_path / "s1_advisor_running").exists()

    def test_stale_running_marker_cleared_when_result_settled(
        self, tmp_path, monkeypatch
    ):
        """Marker present but the advisor actually completed (result carries the
        </usage> envelope): clear the stale marker and process, don't stall."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            advisor_returns("real region\nagentId: x\n<usage>u</usage>"),
            ledger={"round_number": 1, "regions": [], "done": False},
        )
        (tmp_path / "s1_advisor_running").touch()
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        assert not (tmp_path / "s1_advisor_running").exists()
        assert load_ledger(tmp_path / "s1_loop.json")["regions"] == ["real region"]

    def test_token_present_skips_stale_extraction(self, tmp_path, monkeypatch):
        """Advisor NOT invoked this round (token still present): don't re-append a
        prior round's region as a duplicate."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            advisor_returns("prior region\nagentId: x\n<usage>u</usage>"),
            ledger={"round_number": 2, "regions": ["prior region"], "done": False},
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
        for name in (
            "s1_active",
            "s1_advisor_token",
            "s1_advisor_running",
            "s1_compacted",
        ):
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
        assert not (tmp_path / "s1_advisor_running").exists()
        assert not (tmp_path / "s1_compacted").exists()
        assert (tmp_path / "s1_mission.md").exists()


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
        launch()
        saved = (tmp_path / "s1_mission.md").read_text()
        assert saved == 'do the thing\nwith "quotes" and $vars'
        assert (tmp_path / "s1_active").exists()

    def test_ignores_non_launch_command(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        monkeypatch.setattr(
            "sys.stdin",
            self.make_stdin(
                command_name="other:cmd", command_args="x", session_id="s1"
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
    def test_new_turn_overwrites(self, tmp_path):
        log = tmp_path / "l.log"
        log.write_text("stale content")
        write_log(log, 1, new_turn=True, region="fresh")
        content = log.read_text()
        assert "stale content" not in content
        assert "[[ Round 1" in content

    def test_appends_across_rounds(self, tmp_path):
        log = tmp_path / "l.log"
        write_log(log, 1, new_turn=True, region="r1")
        write_log(log, 2, new_turn=False, region="r2")
        content = log.read_text()
        assert "[[ Round 1" in content
        assert "[[ Round 2" in content
