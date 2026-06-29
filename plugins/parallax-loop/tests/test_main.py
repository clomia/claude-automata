"""Tests for the main module — the SubagentStop entry point and its branches.

The hook owns the whole ledger: it records the advisor's prior-round verdict
(region or termination), then drives the next round — writing the deterministic
parallax-region-history file and injecting the five-section advisor trigger.
These tests verify both ends with transcripts that mock the operator's
Agent(advisor) exchange.
"""

import io
import json

import pytest

from src.main import TERMINATION_TOKEN, pre_tool_use, subagent_stop, write_log
from src.state import ROUND_LIMIT, load_ledger, save_ledger


def make_stdin(*, session_id="s1", transcript_path="/t.jsonl"):
    return json.dumps(
        {
            "session_id": session_id,
            "transcript_path": transcript_path,
            "stop_hook_active": False,
        }
    )


def make_pretooluse_stdin(*, session_id="s1", subagent_type="parallax-loop:advisor"):
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
    """An operator turn whose Agent(advisor) call returned `region`."""
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
    tmp_path, monkeypatch, operator_messages, *, session_id="s1", ledger=None
):
    """Set up a mission, a main transcript that spawns operator, and the operator's
    own subagent transcript holding `operator_messages`.

    SubagentStop receives the MAIN transcript; the hook resolves the operator's
    own transcript via the parallax-loop:operator spawn -> meta.json(toolUseId) chain.
    """
    (tmp_path / f"{session_id}_mission.md").write_text("build the thing")
    if ledger:
        save_ledger(tmp_path / f"{session_id}_loop.json", **ledger)
    main = tmp_path / "main.jsonl"
    write_jsonl(
        main,
        [
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tu_a",
                        "name": "Agent",
                        "input": {"subagent_type": "parallax-loop:operator"},
                    }
                ],
            }
        ],
    )
    subdir = tmp_path / "main" / "subagents"
    subdir.mkdir(parents=True)
    (subdir / "agent-A.meta.json").write_text(
        json.dumps({"agentType": "parallax-loop:operator", "toolUseId": "tu_a"})
    )
    write_jsonl(subdir / "agent-A.jsonl", operator_messages)
    arrange(
        tmp_path,
        monkeypatch,
        make_stdin(session_id=session_id, transcript_path=str(main)),
    )


# ── subagent_stop branches ──


class TestSubagentStop:
    def test_no_mission_allows_stop(self, tmp_path, monkeypatch):
        arrange(tmp_path, monkeypatch, make_stdin())
        with pytest.raises(SystemExit) as exc:
            subagent_stop()
        assert exc.value.code == 0

    def test_done_flag_allows_stop(self, tmp_path, monkeypatch):
        (tmp_path / "s1_mission.md").write_text("m")
        save_ledger(tmp_path / "s1_loop.json", round_number=2, regions=["r"], done=True)
        arrange(tmp_path, monkeypatch, make_stdin())
        with pytest.raises(SystemExit) as exc:
            subagent_stop()
        assert exc.value.code == 0

    def test_round_zero_writes_regions_and_injects(self, tmp_path, monkeypatch, capsys):
        """Round 0 has no advisor verdict — write region-history (empty),
        advance, inject the five-section trigger."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            [
                {"role": "user", "content": "mission"},
                {"role": "assistant", "content": "initial work"},
            ],
        )
        with pytest.raises(SystemExit) as exc:
            subagent_stop()
        assert exc.value.code == 2
        assert load_ledger(tmp_path / "s1_loop.json")["round"] == 1

        # deterministic region-history file (round 0 → no regions yet)
        assert "No prior regions." in (tmp_path / "s1_regions.md").read_text()

        # the trigger lists the sections in parallax order and carries the paths
        err = capsys.readouterr().err
        assert "original-mission:" in err
        assert str(tmp_path / "s1_mission.md") in err
        assert "parallax-region-history:" in err
        assert "instructions:" in err
        assert "parallax-loop:advisor" in err
        assert (tmp_path / "s1_advisor_token").exists()

    def test_records_region_into_next_regions_file(self, tmp_path, monkeypatch):
        """Round 1: advisor returned a region — record it, write it into the
        next region-history file, and log it for /parallax-loop:log."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            advisor_returns("consider error handling"),
            ledger={"round_number": 1, "regions": [], "done": False},
        )
        with pytest.raises(SystemExit) as exc:
            subagent_stop()
        assert exc.value.code == 2
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["round"] == 2
        assert ledger["regions"] == ["consider error handling"]

        regions = (tmp_path / "s1_regions.md").read_text()
        assert "<region-1>" in regions
        assert "consider error handling" in regions

        # region is recorded to the log for /parallax-loop:log
        assert "consider error handling" in (tmp_path / "s1_loop.log").read_text()

    def test_termination_token_sets_done_and_stops(self, tmp_path, monkeypatch):
        """The advisor's termination token ends the turn — set done, allow stop,
        do not append a region."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            advisor_returns(f"All paths covered. {TERMINATION_TOKEN}"),
            ledger={"round_number": 2, "regions": ["r"], "done": False},
        )
        with pytest.raises(SystemExit) as exc:
            subagent_stop()
        assert exc.value.code == 0
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["done"] is True
        assert ledger["regions"] == ["r"]

    def test_round_limit_allows_stop(self, tmp_path, monkeypatch):
        arrange_mission(
            tmp_path,
            monkeypatch,
            advisor_returns("a late region"),
            ledger={"round_number": ROUND_LIMIT, "regions": [], "done": False},
        )
        with pytest.raises(SystemExit) as exc:
            subagent_stop()
        assert exc.value.code == 0


# ── pre_tool_use gating ──


class TestPreToolUse:
    def test_token_present_allows_and_consumes(self, tmp_path, monkeypatch):
        """A SubagentStop-set token authorizes exactly one advisor call."""
        (tmp_path / "s1_mission.md").write_text("m")
        token = tmp_path / "s1_advisor_token"
        token.write_text("")
        arrange(tmp_path, monkeypatch, make_pretooluse_stdin())
        with pytest.raises(SystemExit) as exc:
            pre_tool_use()
        assert exc.value.code == 0
        assert not token.exists()

    def test_no_token_denies_self_initiated_call(self, tmp_path, monkeypatch):
        """No token = operator called advisor on its own — deny so it keeps working."""
        (tmp_path / "s1_mission.md").write_text("m")
        arrange(tmp_path, monkeypatch, make_pretooluse_stdin())
        with pytest.raises(SystemExit) as exc:
            pre_tool_use()
        assert exc.value.code == 2

    def test_non_advisor_call_passes_through(self, tmp_path, monkeypatch):
        """narrator/operator invocations are never gated."""
        (tmp_path / "s1_mission.md").write_text("m")
        arrange(
            tmp_path,
            monkeypatch,
            make_pretooluse_stdin(subagent_type="parallax-loop:narrator"),
        )
        with pytest.raises(SystemExit) as exc:
            pre_tool_use()
        assert exc.value.code == 0


# ── write_log ──


class TestWriteLog:
    def test_new_turn_overwrites(self, tmp_path):
        log = tmp_path / "l.log"
        log.write_text("stale content")
        write_log(log, 1, new_turn=True, advisor_trigger="fresh")
        content = log.read_text()
        assert "stale content" not in content
        assert "[[ Round 1" in content

    def test_appends_across_rounds(self, tmp_path):
        log = tmp_path / "l.log"
        write_log(log, 1, new_turn=True, advisor_trigger="r1")
        write_log(log, 2, new_turn=False, advisor_trigger="r2")
        content = log.read_text()
        assert "[[ Round 1" in content
        assert "[[ Round 2" in content
