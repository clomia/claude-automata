"""Tests for the main module — Stop, PreToolUse, UserPromptSubmit, PostCompact entry points.

The hook owns the whole ledger: it records the advisor's prior-round verdict
(the advice it wrote to advice.md; only the explicit termination token ends
the turn), then drives the next round.  Anomalies get one benefit-of-the-doubt
repeat before their signal is accepted as real: an advisor run that wrote
nothing is retried with the round's inputs frozen, a stop that ignored the
trigger is re-triggered — the second in a row ends the loop with an honest
cause.  These tests drive `stop` with a main transcript plus the advisor's
advice.md, the sole advice channel.
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
    stop_command,
    subagent_stop,
    user_prompt_submit,
    write_log,
)
from src.state import load_ledger, save_ledger

# A minimal round transcript: a trigger boundary + the main agent's own work.
# The advice no longer comes from here — advice.md is the sole channel — so this
# only feeds parse_round_actions (which writes the narrator's action file).
ROUND_WORK = [
    {"role": "user", "content": "advisor trigger"},
    {"role": "assistant", "content": "working on the advice"},
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
        save_ledger(
            tmp_path / "s1_loop.json", round_number=2, advice_history=["r"], done=True
        )
        arrange(tmp_path, monkeypatch, make_stdin())
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 0

    def test_round_zero_writes_advice_history_and_injects(
        self, tmp_path, monkeypatch, capsys
    ):
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
        assert "No prior advice." in (tmp_path / "s1_advice_history.md").read_text()
        err = capsys.readouterr().err
        assert "original-mission:" in err
        assert str(tmp_path / "s1_mission.md") in err
        assert "advice-history:" in err
        assert "instructions:" in err
        assert "ploop:advisor" in err
        assert (tmp_path / "s1_advisor_token").exists()

    def test_records_advice_and_logs_completed_round_zero(self, tmp_path, monkeypatch):
        arrange_mission(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"round_number": 1, "advice_history": [], "done": False},
            advice="consider error handling",
            narration="initial work narrative",
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["round"] == 2
        assert ledger["advice_history"] == ["consider error handling"]
        advice_history = (tmp_path / "s1_advice_history.md").read_text()
        assert "<advice-1>" in advice_history
        assert "consider error handling" in advice_history
        # The narration narrates round 0 (mission work, no advice answered), so
        # the completed entry is "Round 0" with no Advice section; the fresh
        # advice is not logged yet — its round completes at the next stop.
        log = (tmp_path / "s1_loop.log").read_text()
        assert "[[ Round 0 - " in log
        assert "initial work narrative" in log
        assert "/ Advice" not in log
        assert "consider error handling" not in log

    def test_advice_and_narration_cleared_on_arm(self, tmp_path, monkeypatch):
        """Both temp channels are read (advice stripped), then cleared as the next
        round arms — an absent file next round unambiguously means no write."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"round_number": 1, "advice_history": [], "done": False},
            advice="  consider concurrency  ",
            narration="did things",
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        assert load_ledger(tmp_path / "s1_loop.json")["advice_history"] == [
            "consider concurrency"
        ]
        assert not (tmp_path / "ploop_s1_advice.md").exists()
        assert not (tmp_path / "ploop_s1_narration.md").exists()

    def test_log_pairs_narration_with_the_advice_it_answered(
        self, tmp_path, monkeypatch
    ):
        """The entry pairs the narrated round with the advice it responded to
        (advice_history[-1]), numbered by that advice's ordinal — aligned with
        advice_history.md even after a skipped round, and the fresh advice waits
        for its own round to complete."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"round_number": 4, "advice_history": ["r1", "r2"], "done": False},
            advice="r3",
            narration="worked on r2",
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        log = (tmp_path / "s1_loop.log").read_text()
        assert "[[ Round 2 - " in log
        assert "[[ Round 2 / Advice ]]" in log
        assert log.index("worked on r2") < log.index("r2\n")
        assert "r3" not in log
        assert "Round 4" not in log

    def test_absent_advice_retries_round_with_inputs_frozen(
        self, tmp_path, monkeypatch, capsys
    ):
        """The advisor finished (no running marker) and wrote nothing — a
        malfunction, not a verdict (the protocol demands a Write even to
        terminate).  The round is retried: same round number, a fresh token,
        and the round's inputs (action.json, advice_history.md) untouched so
        the retried advisor sees what the failed one saw; nothing is logged —
        the round completes at its eventual successful stop."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"round_number": 1, "advice_history": [], "done": False},
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["round"] == 1  # same round, not advanced
        assert ledger["done"] is False
        assert ledger["advisor_failures"] == 1
        assert (tmp_path / "s1_active").exists()
        assert (tmp_path / "s1_advisor_token").exists()
        assert not (tmp_path / "s1_action.json").exists()  # inputs frozen
        assert not (tmp_path / "s1_advice_history.md").exists()
        assert not (tmp_path / "s1_loop.log").exists()  # nothing logged
        err = capsys.readouterr().err
        assert "malfunctioned" in err
        assert "Invoke the advisor" in err  # the trigger follows the notice

    def test_second_consecutive_advisor_failure_ends_loop(
        self, tmp_path, monkeypatch, capsys
    ):
        """One retry is the benefit of the doubt; a second empty run in a row is
        accepted as a real malfunction — the loop ends with that cause, never
        disguised as convergence."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"round_number": 1, "advice_history": [], "done": False},
        )
        save_ledger(
            tmp_path / "s1_loop.json",
            round_number=1,
            advice_history=[],
            done=False,
            advisor_failures=1,
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        assert load_ledger(tmp_path / "s1_loop.json")["done"] is True
        assert not (tmp_path / "s1_active").exists()
        err = capsys.readouterr().err
        assert "parallax loop has ended" in err
        assert "malfunctioned" in err

    def test_advice_after_failure_resets_the_counter(self, tmp_path, monkeypatch):
        """A successful retry clears the failure streak — the caps count
        consecutive anomalies, not lifetime ones."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"round_number": 1, "advice_history": [], "done": False},
            advice="fresh advice",
            narration="round work",
        )
        save_ledger(
            tmp_path / "s1_loop.json",
            round_number=1,
            advice_history=[],
            done=False,
            advisor_failures=1,
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["advice_history"] == ["fresh advice"]
        assert ledger["advisor_failures"] == 0
        assert ledger["round"] == 2

    def test_compacted_round_inlines_mission_text(self, tmp_path, monkeypatch, capsys):
        """Mechanism 2: a compacted round re-injects the original-mission text into
        the trigger and consumes the marker."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"round_number": 1, "advice_history": [], "done": False},
            advice="some advice",
        )
        (tmp_path / "s1_compacted").touch()
        with pytest.raises(SystemExit):
            stop()
        err = capsys.readouterr().err
        assert "build the thing" in err  # original-mission text inlined
        assert not (tmp_path / "s1_compacted").exists()  # consumed

    def test_termination_token_ends_loop_and_triggers_recap(
        self, tmp_path, monkeypatch, capsys
    ):
        """Termination on a turn that surfaced advice: done + deactivated, the
        final round completed in the log (its narration + the advice it
        answered; the token is machinery and never logged), and one last
        injection has the main agent report the end and recap the round log."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"round_number": 2, "advice_history": ["r"], "done": False},
            advice=f"All paths covered. {TERMINATION_TOKEN}",
            narration="final round work",
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["done"] is True
        assert ledger["advice_history"] == ["r"]
        assert not (tmp_path / "s1_active").exists()
        log = (tmp_path / "s1_loop.log").read_text()
        assert "[[ Round 1 - " in log
        assert "final round work" in log
        assert "[[ Round 1 / Advice ]]" in log
        assert TERMINATION_TOKEN not in log
        # the end notice reports the cause and points the main agent at the log
        err = capsys.readouterr().err
        assert "has ended" in err
        assert str(tmp_path / "s1_loop.log") in err
        assert "recap" in err

    def test_no_round_cap_arms_indefinitely(self, tmp_path, monkeypatch):
        """There is no round limit: a high round still arms the next round rather
        than terminating — only the advisor (or /ploop:stop) ends the loop."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"round_number": 999, "advice_history": ["r"] * 999, "done": False},
            advice="still more",
            narration="work",
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2  # armed, not terminated
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["round"] == 1000
        assert ledger["done"] is False
        assert (tmp_path / "s1_active").exists()

    def test_running_marker_pauses_without_retrigger(self, tmp_path, monkeypatch):
        """Running marker present (advisor in flight — e.g. the user pushed it to the
        background): allow the stop, don't re-trigger — no cascade.  SubagentStop is
        the marker's sole clearer, so the loop just waits for it."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"round_number": 1, "advice_history": [], "done": False},
        )
        (tmp_path / "s1_advisor_running").touch()
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 0
        # ledger untouched, marker left in place — the loop just waits
        assert load_ledger(tmp_path / "s1_loop.json")["round"] == 1
        assert (tmp_path / "s1_advisor_running").exists()

    def test_first_decline_redirects_to_advisor_authority(
        self, tmp_path, monkeypatch, capsys
    ):
        """Advisor NOT invoked this round (token still present): don't re-append a
        prior round's advice as a duplicate, even if a stale advice file lingers.
        The trigger is re-injected behind the authority notice — only the advisor
        may end the loop, and the refusal's stated reasons ride action.json to
        its verdict; no main-side exit is advertised."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={
                "round_number": 2,
                "advice_history": ["prior advice"],
                "done": False,
            },
            advice="prior advice",
        )
        (tmp_path / "s1_advisor_token").write_text("")
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["advice_history"] == ["prior advice"]  # not duplicated
        assert ledger["round"] == 3
        assert ledger["declines"] == 1
        # the refusal turn is re-parsed into action.json for the advisor to read
        assert "working on the advice" in (tmp_path / "s1_action.json").read_text()
        err = capsys.readouterr().err
        assert "authority to end the loop belongs to the advisor" in err
        assert "Invoke the advisor" in err  # the trigger follows the notice
        assert "loop will end" not in err  # no main-side exit advertised

    def test_second_consecutive_decline_trips_failsafe_and_ends_loop(
        self, tmp_path, monkeypatch, capsys
    ):
        """A second stop in a row without invoking the advisor means the
        consensus channel itself is broken — the failsafe ends the loop with
        that honest cause instead of stalemating against the harness
        stop-block cap."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
        )
        save_ledger(
            tmp_path / "s1_loop.json",
            round_number=3,
            advice_history=["r"],
            done=False,
            declines=1,
        )
        (tmp_path / "s1_advisor_token").write_text("")
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["done"] is True
        assert ledger["advice_history"] == ["r"]
        assert not (tmp_path / "s1_active").exists()
        err = capsys.readouterr().err
        assert "parallax loop has ended" in err
        assert "declined" in err

    def test_compliance_resets_the_decline_counter(self, tmp_path, monkeypatch):
        """Invoking the advisor after a decline clears the streak — the caps
        count consecutive anomalies, not lifetime ones."""
        arrange_mission(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            advice="new advice",
            narration="complied and worked",
        )
        save_ledger(
            tmp_path / "s1_loop.json",
            round_number=3,
            advice_history=["r"],
            done=False,
            declines=1,
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["declines"] == 0
        assert ledger["advice_history"] == ["r", "new advice"]


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
            tmp_path / "s1_loop.json", round_number=3, advice_history=["r"], done=False
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

    def test_launch_turn_keeps_active_via_sentinel(self, tmp_path, monkeypatch, capsys):
        """On a /ploop:launch turn the launching sentinel is present: the fresh
        active marker (and mission) survive cleanup; the sentinel is consumed."""
        (tmp_path / "s1_active").touch()
        (tmp_path / "s1_mission.md").write_text("fresh mission")
        (tmp_path / "s1_launching").touch()
        save_ledger(
            tmp_path / "s1_loop.json",
            round_number=9,
            advice_history=["stale"],
            done=True,
        )
        (tmp_path / "s1_advisor_token").touch()
        arrange(tmp_path, monkeypatch, json.dumps({"session_id": "s1"}))
        user_prompt_submit()
        assert (tmp_path / "s1_active").exists()  # spared
        assert not (tmp_path / "s1_launching").exists()  # consumed
        assert not (tmp_path / "s1_loop.json").exists()  # stale ledger cleared
        assert not (tmp_path / "s1_advisor_token").exists()
        assert (tmp_path / "s1_mission.md").exists()
        assert capsys.readouterr().out == ""  # loop not ended → no notice

    def test_running_marker_preserves_loop(self, tmp_path, monkeypatch, capsys):
        """A running marker (advisor in flight) makes an incidental user turn leave
        the whole loop intact — SubagentStop, not this hook, clears the marker."""
        for name in ("s1_active", "s1_advisor_running"):
            (tmp_path / name).touch()
        save_ledger(
            tmp_path / "s1_loop.json", round_number=2, advice_history=["r"], done=False
        )
        arrange(tmp_path, monkeypatch, json.dumps({"session_id": "s1"}))
        user_prompt_submit()
        assert (tmp_path / "s1_active").exists()  # loop survives the interjection
        assert (tmp_path / "s1_loop.json").exists()
        assert (tmp_path / "s1_advisor_running").exists()  # SubagentStop clears it
        assert capsys.readouterr().out == ""  # loop not ended → no notice

    def test_intervention_termination_notifies_agent(
        self, tmp_path, monkeypatch, capsys
    ):
        """Deactivating a live loop tells the main agent via additionalContext —
        the notice instructs it to relay the end to the user, so no separate
        user channel is needed."""
        (tmp_path / "s1_active").touch()
        save_ledger(
            tmp_path / "s1_loop.json", round_number=2, advice_history=["r"], done=False
        )
        arrange(tmp_path, monkeypatch, json.dumps({"session_id": "s1"}))
        user_prompt_submit()
        out = json.loads(capsys.readouterr().out)
        assert out["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
        assert (
            "parallax loop has ended" in out["hookSpecificOutput"]["additionalContext"]
        )
        assert not (tmp_path / "s1_active").exists()

    def test_ordinary_turn_stays_silent(self, tmp_path, monkeypatch, capsys):
        """A turn with no live loop deactivates nothing, so it emits no notice."""
        arrange(tmp_path, monkeypatch, json.dumps({"session_id": "s1"}))
        user_prompt_submit()
        assert capsys.readouterr().out == ""


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
            tmp_path / "s1_loop.json",
            round_number=9,
            advice_history=["stale"],
            done=True,
        )
        (tmp_path / "s1_loop.log").write_text("prior mission log")
        launch()
        saved = (tmp_path / "s1_mission.md").read_text()
        assert saved == 'do the thing\nwith "quotes" and $vars'
        assert (tmp_path / "s1_active").exists()
        assert (tmp_path / "s1_launching").exists()  # sentinel for user_prompt_submit
        assert not (tmp_path / "s1_loop.json").exists()  # prior ledger cleared
        # a mission owns one log, opened with its own text
        log = (tmp_path / "s1_loop.log").read_text()
        assert log.startswith("[[ MISSION ]]\n\n")
        assert saved in log
        assert "prior mission log" not in log

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

    def test_blank_mission_blocks_expansion(self, tmp_path, monkeypatch, capsys):
        """A blank mission is blocked at expansion — otherwise the skill body
        would announce an activation the hook never armed (a ghost loop)."""
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        monkeypatch.setattr(
            "sys.stdin",
            self.make_stdin(
                command_name="ploop:launch", command_args="   ", session_id="s1"
            ),
        )
        with pytest.raises(SystemExit) as exc:
            launch()
        assert exc.value.code == 0
        assert json.loads(capsys.readouterr().out)["decision"] == "block"
        assert not (tmp_path / "s1_active").exists()

    def test_armed_loop_blocks_relaunch_untouched(self, tmp_path, monkeypatch, capsys):
        """Relaunching over an armed loop is blocked purely: mission, log, and
        the in-flight marker survive — the running loop is not disturbed, and
        the reason routes the user to /ploop:stop."""
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        (tmp_path / "s1_active").touch()
        (tmp_path / "s1_mission.md").write_text("old mission")
        (tmp_path / "s1_loop.log").write_text("old log")
        (tmp_path / "s1_advisor_running").touch()
        monkeypatch.setattr(
            "sys.stdin",
            self.make_stdin(
                command_name="ploop:launch", command_args="new mission", session_id="s1"
            ),
        )
        with pytest.raises(SystemExit) as exc:
            launch()
        assert exc.value.code == 0
        out = json.loads(capsys.readouterr().out)
        assert out["decision"] == "block"
        assert "/ploop:stop" in out["reason"]
        assert (tmp_path / "s1_mission.md").read_text() == "old mission"
        assert (tmp_path / "s1_loop.log").read_text() == "old log"
        assert (tmp_path / "s1_advisor_running").exists()
        assert not (tmp_path / "s1_launching").exists()


# ── /ploop:stop UserPromptExpansion hook ──


class TestStopCommand:
    def make_stdin(self, **payload):
        return io.StringIO(json.dumps(payload))

    def arrange(self, tmp_path, monkeypatch, *, command_name="ploop:stop"):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        monkeypatch.setattr(
            "sys.stdin",
            self.make_stdin(command_name=command_name, session_id="s1"),
        )

    def test_deactivates_and_clears_round_state(self, tmp_path, monkeypatch):
        for name in ("s1_active", "s1_advisor_token", "s1_compacted"):
            (tmp_path / name).touch()
        save_ledger(
            tmp_path / "s1_loop.json", round_number=5, advice_history=["r"], done=False
        )
        (tmp_path / "s1_mission.md").write_text("m")
        (tmp_path / "s1_loop.log").write_text("log")
        self.arrange(tmp_path, monkeypatch)
        stop_command()
        assert not (tmp_path / "s1_active").exists()  # loop deactivated
        assert not (tmp_path / "s1_loop.json").exists()
        assert not (tmp_path / "s1_advisor_token").exists()
        assert (tmp_path / "s1_mission.md").exists()  # anchor kept
        assert (tmp_path / "s1_loop.log").exists()  # record kept

    def test_delivers_log_path_to_main_agent(self, tmp_path, monkeypatch, capsys):
        """A running loop (active marker) is stopped: it hands the main agent the
        real session log path — the only channel that can, since the skill body is
        static — as UserPromptExpansion additionalContext."""
        (tmp_path / "s1_active").touch()
        (tmp_path / "s1_loop.log").write_text("[[ MISSION ]]\n\nm\n\n")
        self.arrange(tmp_path, monkeypatch)
        stop_command()
        out = json.loads(capsys.readouterr().out)
        assert out["hookSpecificOutput"]["hookEventName"] == "UserPromptExpansion"
        context = out["hookSpecificOutput"]["additionalContext"]
        assert str(tmp_path / "s1_loop.log") in context
        assert "/ploop:stop" in context  # the cause reaches the user's report

    def test_inactive_stop_blocks_expansion(self, tmp_path, monkeypatch, capsys):
        """No armed loop (already ended / double-stop): the expansion is blocked
        purely — the skill body never runs, so no false termination notice, and
        the prior mission's record survives untouched."""
        (tmp_path / "s1_loop.log").write_text("[[ MISSION ]]\n\nm\n\n")  # stale log
        (tmp_path / "s1_mission.md").write_text("m")
        self.arrange(tmp_path, monkeypatch)
        with pytest.raises(SystemExit) as exc:
            stop_command()
        assert exc.value.code == 0
        assert json.loads(capsys.readouterr().out)["decision"] == "block"
        assert (tmp_path / "s1_loop.log").read_text() == "[[ MISSION ]]\n\nm\n\n"
        assert (tmp_path / "s1_mission.md").exists()

    def test_stops_even_while_advisor_in_flight(self, tmp_path, monkeypatch):
        """Unlike an incidental user turn (which user_prompt_submit spares while a
        background advisor runs), /ploop:stop is unconditional: it clears the
        running marker and the active gate."""
        for name in ("s1_active", "s1_advisor_running"):
            (tmp_path / name).touch()
        self.arrange(tmp_path, monkeypatch)
        stop_command()
        assert not (tmp_path / "s1_active").exists()
        assert not (tmp_path / "s1_advisor_running").exists()

    def test_ignores_other_plugin_stop(self, tmp_path, monkeypatch):
        """The guard matches the full scoped name, so another plugin's :stop
        cannot deactivate ploop."""
        (tmp_path / "s1_active").touch()
        self.arrange(tmp_path, monkeypatch, command_name="other:stop")
        with pytest.raises(SystemExit):
            stop_command()
        assert (tmp_path / "s1_active").exists()  # untouched


# ── write_log ──


class TestWriteLog:
    def test_round_zero_has_no_advice_section(self, tmp_path):
        log = tmp_path / "l.log"
        write_log(log, 0, "mission work", None)
        content = log.read_text()
        assert "[[ Round 0 - " in content
        assert "mission work" in content
        assert "/ Advice" not in content

    def test_appends_completed_rounds_with_advice(self, tmp_path):
        log = tmp_path / "l.log"
        write_log(log, 0, "w0", None)
        write_log(log, 1, "answered a1 with w1", "a1")
        content = log.read_text()
        assert "[[ Round 1 / Advice ]]" in content
        # narration first, then the advice it answered; rounds in append order
        assert (
            content.index("w0")
            < content.index("answered a1 with w1")
            < content.index("a1", content.index("[[ Round 1 / Advice ]]"))
        )
