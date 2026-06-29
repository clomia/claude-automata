"""Tests for the hooks module — the SubagentStop entry point and its branches.

The hook owns the whole ledger: it records the advisor's prior-round verdict
(region or termination), then drives the next round — assembling the
deterministic analysis input (mission + region-history) and injecting the
advisor-call trigger.  These tests verify both ends with transcripts that mock
the anchor's Agent(advisor) exchange.
"""

import io
import json

import pytest

from src.hooks import TERMINATION_TOKEN, pre_tool_use, subagent_stop, write_log
from src.state import ROUND_LIMIT, load_ledger, save_ledger


def make_stdin(*, session_id="s1", transcript_path="/t.jsonl"):
    return json.dumps(
        {
            "session_id": session_id,
            "transcript_path": transcript_path,
            "stop_hook_active": False,
        }
    )


def make_pretooluse_stdin(*, session_id="s1", subagent_type="anchor:advisor"):
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
    """An anchor turn whose Agent(advisor) call returned `region`."""
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
    tmp_path, monkeypatch, anchor_messages, *, session_id="s1", ledger=None
):
    """Set up a mission, a main transcript that spawns anchor, and the anchor's
    own subagent transcript holding `anchor_messages`.

    SubagentStop receives the MAIN transcript; the hook resolves the anchor's
    own transcript via the anchor:anchor spawn -> meta.json(toolUseId) chain.
    """
    (tmp_path / f"{session_id}_mission.md").write_text("build the thing")
    if ledger:
        save_ledger(tmp_path / f"{session_id}_anchor.json", **ledger)
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
                        "input": {"subagent_type": "anchor:anchor"},
                    }
                ],
            }
        ],
    )
    subdir = tmp_path / "main" / "subagents"
    subdir.mkdir(parents=True)
    (subdir / "agent-A.meta.json").write_text(
        json.dumps({"agentType": "anchor:anchor", "toolUseId": "tu_a"})
    )
    write_jsonl(subdir / "agent-A.jsonl", anchor_messages)
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
        save_ledger(
            tmp_path / "s1_anchor.json", round_number=2, regions=["r"], done=True
        )
        arrange(tmp_path, monkeypatch, make_stdin())
        with pytest.raises(SystemExit) as exc:
            subagent_stop()
        assert exc.value.code == 0

    def test_round_zero_assembles_analysis_and_injects(
        self, tmp_path, monkeypatch, capsys
    ):
        """Round 0 has no advisor verdict — assemble analysis input (mission +
        empty region-history), advance, inject."""
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
        assert exc.value.code == 0
        assert load_ledger(tmp_path / "s1_anchor.json")["round"] == 1

        # deterministic analysis input assembled by the hook (XML-wrapped)
        analysis = (tmp_path / "s1_analysis.md").read_text()
        assert "<original-mission>" in analysis
        assert "build the thing" in analysis
        assert "<parallax-region-history>" in analysis
        assert "No prior regions." in analysis
        # block + trigger come back as JSON on stdout (exit 0 so stdout is read)
        out = capsys.readouterr().out
        assert '"decision": "block"' in out
        assert "advisor" in out
        assert (tmp_path / "s1_advisor_token").exists()

    def test_records_region_and_wraps_into_next_analysis(
        self, tmp_path, monkeypatch, capsys
    ):
        """Round 1: advisor returned a region — record it, XML-wrap it into the
        next analysis input, log it, and surface it to the user (systemMessage)."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            advisor_returns("consider error handling"),
            ledger={"round_number": 1, "regions": [], "done": False},
        )
        with pytest.raises(SystemExit) as exc:
            subagent_stop()
        assert exc.value.code == 0
        ledger = load_ledger(tmp_path / "s1_anchor.json")
        assert ledger["round"] == 2
        assert ledger["regions"] == ["consider error handling"]

        analysis = (tmp_path / "s1_analysis.md").read_text()
        assert "<region-1>" in analysis
        assert "consider error handling" in analysis

        # JSON on stdout: block + systemMessage(region); log carries region too
        out = capsys.readouterr().out
        assert '"decision": "block"' in out
        assert "consider error handling" in out
        assert "consider error handling" in (tmp_path / "s1_anchor.log").read_text()

    def test_termination_token_sets_done_and_stops(self, tmp_path, monkeypatch, capsys):
        """The advisor's termination token ends the turn — set done, allow stop,
        do not append a region, and notify the user (systemMessage)."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            advisor_returns(f"All paths covered. {TERMINATION_TOKEN}"),
            ledger={"round_number": 2, "regions": ["r"], "done": False},
        )
        with pytest.raises(SystemExit) as exc:
            subagent_stop()
        assert exc.value.code == 0
        ledger = load_ledger(tmp_path / "s1_anchor.json")
        assert ledger["done"] is True
        assert ledger["regions"] == ["r"]
        assert "종료" in capsys.readouterr().out

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
        """No token = anchor called advisor on its own — deny so it keeps working."""
        (tmp_path / "s1_mission.md").write_text("m")
        arrange(tmp_path, monkeypatch, make_pretooluse_stdin())
        with pytest.raises(SystemExit) as exc:
            pre_tool_use()
        assert exc.value.code == 2

    def test_non_advisor_call_passes_through(self, tmp_path, monkeypatch):
        """narrator/anchor invocations are never gated."""
        (tmp_path / "s1_mission.md").write_text("m")
        arrange(
            tmp_path,
            monkeypatch,
            make_pretooluse_stdin(subagent_type="anchor:narrator"),
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
