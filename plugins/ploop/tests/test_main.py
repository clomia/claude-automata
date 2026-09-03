"""Tests for the main module — Stop, PreToolUse, SubagentStop, SessionStart entry points.

The hook owns the whole ledger.  Per advising stop it appends the previous
round's narration to the loop log (the flight recorder), reads advice.md — the
advisor's sole output channel — and judges the round: a report becomes an
audit-history entry, the completion token converges the loop, an empty advisor
run is a malfunction, and an un-convened stop splits on transcript growth into
a WORKING stop (the normal case — no anomaly) or a BARE stop (an unanswered
directive).  The first anomaly gets a corrective repeat; a second consecutive
anomaly of any kind ends the loop with an honest cause.  These tests drive
`stop` with a main transcript plus the advisor's advice.md and the narrator's
narration.md, the two file channels.
"""

import io
import json

import pytest

from src.main import (
    BARE_STOP_LINE_THRESHOLD,
    COMPLETION_TOKEN,
    EXPIRY_TOKEN,
    HEARTBEAT_NOTICE,
    HEARTBEAT_SECONDS,
    heartbeat_arm,
    heartbeat_fire,
    launch,
    off_command,
    on_command,
    pre_tool_use,
    reanchor,
    stop,
    subagent_stop,
    write_audit_entry,
    write_round_entry,
    write_round_slice,
)
from src.prompt import format_candidates_notice
from src.state import (
    ADVISING,
    CONVERGED,
    FRESH,
    Workspace,
    load_ledger,
    save_ledger,
)

# A bare round transcript: the injected directive boundary plus one short
# text-only reply — under the bare-stop line threshold, no tool work.
BARE_WORK = [
    {"role": "user", "content": "round directive"},
    {"role": "assistant", "content": "done, I believe"},
]

# A working round transcript: enough lines past round_start to clear the
# bare-stop threshold — the shape a round of real tool activity leaves.
WORK = [{"role": "user", "content": "round directive"}] + [
    {"role": "assistant", "content": f"tool call {i}"}
    for i in range(BARE_STOP_LINE_THRESHOLD + 5)
]


def make_stdin(*, session_id="s1", transcript_path="/t.jsonl", background_tasks=None):
    event = {"session_id": session_id, "transcript_path": transcript_path}
    if background_tasks is not None:
        event["background_tasks"] = background_tasks
    return json.dumps(event)


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


def arrange_anchor(
    tmp_path,
    monkeypatch,
    main_messages,
    *,
    session_id="s1",
    ledger=None,
    advice=None,
    narration=None,
):
    """Activate an anchor and write the main transcript holding `main_messages`.

    The main agent does the anchor's work directly, so it lives in the main session
    transcript the Stop hook receives.  The active marker gates the loop; anchor.md
    holds the anchor text; the loop log exists from launch on.  `ledger` (a partial
    dict) seeds the round state — load fills the rest with defaults.  `advice` /
    `narration` (when given) are the advisor's and narrator's temp-channel files,
    routed under tmp_path via gettempdir.
    """
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    (tmp_path / f"{session_id}_active").touch()
    (tmp_path / f"{session_id}_anchor.md").write_text("build the thing")
    (tmp_path / f"{session_id}_loop.log").write_text(
        "[[ ANCHOR ]]\n\nbuild the thing\n\n"
    )
    if ledger:
        save_ledger(tmp_path / f"{session_id}_loop.json", ledger)
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

    def test_fresh_phase_arms_without_judging(self, tmp_path, monkeypatch, capsys):
        """A fresh (just-launched) loop has no token armed yet: the first stop
        must not read its absent token as consumed (a false malfunction) or its
        short transcript as bare — it just arms the first round."""
        arrange_anchor(tmp_path, monkeypatch, BARE_WORK)
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["phase"] == ADVISING
        assert ledger["anomalies"] == 0
        assert ledger["round"] == 1
        assert ledger["round_start_line"] == 3
        assert "No prior audits." in (tmp_path / "s1_advice_history.md").read_text()
        err = capsys.readouterr().err
        assert "ploop:narrator" in err
        assert "ploop:advisor" in err
        assert str(tmp_path / "s1_anchor.md") in err
        assert str(tmp_path / "s1_round.jsonl") in err
        assert "audit-history:" in err
        assert "instructions:" in err
        assert (tmp_path / "s1_advisor_token").exists()
        # the queue path rides every directive; an empty queue shows no advisor line
        assert "Your candidates queue" in err
        assert "queued for promotion" not in err
        # no anomaly notice on a fresh arm
        assert "malfunctioned" not in err
        assert "certify completion belongs" not in err
        # the fresh round's slice is the whole transcript (from line 1)
        assert "done, I believe" in (tmp_path / "s1_round.jsonl").read_text()

    def test_working_stop_is_not_an_anomaly(self, tmp_path, monkeypatch, capsys):
        """The normal case under the completion gate: the directive stood, the
        main agent worked and stopped without convening.  Real transcript growth
        means no anomaly — the directive is simply re-injected and the round
        advances."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            WORK,
            ledger={"phase": ADVISING, "advice_history": [], "round": 3},
        )
        (tmp_path / "s1_advisor_token").write_text("")  # unconsumed: no audit
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["anomalies"] == 0
        assert ledger["round"] == 4
        assert ledger["advice_history"] == []
        err = capsys.readouterr().err
        assert "certify completion belongs" not in err  # no decline notice
        assert "ploop:advisor" in err  # the directive stands again

    def test_working_stop_resets_the_anomaly_streak(self, tmp_path, monkeypatch):
        """Consecutive means consecutive: a working stop clears the streak, so
        two unrelated ESC-cut turns days apart can never sum to a failsafe."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            WORK,
            ledger={"phase": ADVISING, "advice_history": [], "anomalies": 1},
        )
        (tmp_path / "s1_advisor_token").write_text("")
        with pytest.raises(SystemExit):
            stop()
        assert load_ledger(tmp_path / "s1_loop.json")["anomalies"] == 0

    def test_bare_stop_discloses_the_silent_exit(self, tmp_path, monkeypatch, capsys):
        """A stop with no tool work and no audit is the unanswered directive.
        The re-arm rides the decline notice — the one place the silent exit is
        disclosed, so the second silence is an informed signal."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            BARE_WORK,
            ledger={"phase": ADVISING, "advice_history": ["a1"]},
        )
        (tmp_path / "s1_advisor_token").write_text("")
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["anomalies"] == 1
        assert ledger["advice_history"] == ["a1"]  # nothing recorded
        err = capsys.readouterr().err
        assert "certify completion belongs to the advisor" in err
        assert "loop will end" in err and "/ploop:on" in err  # disclosed here
        assert "EXACTLY as written" in err  # the directive follows the notice

    def test_second_bare_stop_ends_without_a_verdict(
        self, tmp_path, monkeypatch, capsys
    ):
        """The emergency stop: a second unanswered directive ends the loop —
        honestly, without a completion verdict, resumable — never dressed as a
        finished anchor."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            BARE_WORK,
            ledger={"phase": ADVISING, "advice_history": ["a1"], "anomalies": 1},
        )
        (tmp_path / "s1_advisor_token").write_text("")
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["phase"] == ADVISING  # not converged — /ploop:on can resume
        assert not (tmp_path / "s1_active").exists()
        err = capsys.readouterr().err
        assert "advisor loop has ended" in err
        assert "no completion verdict was issued" in err
        assert str(tmp_path / "s1_loop.log") in err  # recap of the flight record

    def test_audit_report_is_recorded_and_logged(self, tmp_path, monkeypatch):
        """An audit round: the previous round's narration lands as its Round
        entry, the report as an Audit entry and an audit-history item, and the
        streak resets."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            WORK,
            ledger={
                "phase": ADVISING,
                "advice_history": [],
                "anomalies": 1,
                "round": 2,
            },
            advice="- Mission: the mobile layout was never measured",
            narration="round one: measured the desktop layout",
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["advice_history"] == [
            "- Mission: the mobile layout was never measured"
        ]
        assert ledger["anomalies"] == 0
        assert ledger["round"] == 3
        log = (tmp_path / "s1_loop.log").read_text()
        assert "[[ Round 1 - " in log
        assert "round one: measured the desktop layout" in log
        assert "[[ Audit 1 - " in log
        assert "mobile layout" in log
        assert log.index("[[ Round 1 - ") < log.index("[[ Audit 1 - ")
        history = (tmp_path / "s1_advice_history.md").read_text()
        assert "<audit-1>" in history

    def test_advice_and_narration_cleared_on_arm(self, tmp_path, monkeypatch):
        """Both temp channels are read (advice stripped), then cleared as the next
        round arms — an absent file next round unambiguously means no write."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            WORK,
            ledger={"phase": ADVISING, "advice_history": []},
            advice="  - finding  ",
            narration="did things",
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        assert load_ledger(tmp_path / "s1_loop.json")["advice_history"] == ["- finding"]
        assert not (tmp_path / "ploop_s1_advice.md").exists()
        assert not (tmp_path / "ploop_s1_narration.md").exists()

    def test_skipped_narrator_degrades_to_no_entry(self, tmp_path, monkeypatch):
        """A skipped narrator relay is a degrade, not an anomaly: the round goes
        unnarrated and the loop moves on."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            WORK,
            ledger={"phase": ADVISING, "advice_history": [], "round": 2},
            advice="- finding",
        )
        with pytest.raises(SystemExit):
            stop()
        log = (tmp_path / "s1_loop.log").read_text()
        assert "[[ Round" not in log  # no narration, no Round entry
        assert "[[ Audit 1 - " in log
        assert load_ledger(tmp_path / "s1_loop.json")["anomalies"] == 0

    def test_malfunction_gets_a_retry_notice(self, tmp_path, monkeypatch, capsys):
        """Token consumed but no report: the advisor ran and wrote nothing — a
        malfunction, not a verdict (the protocol demands a Write even to
        certify).  One retry notice; rounds are time slices now, so the round
        advances instead of freezing."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            WORK,
            ledger={
                "phase": ADVISING,
                "advice_history": [],
                "round": 2,
                "round_start_line": 5,
            },
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["anomalies"] == 1
        assert ledger["round"] == 3
        assert ledger["round_start_line"] == len(WORK) + 1  # advanced, not frozen
        assert (tmp_path / "s1_advisor_token").exists()
        err = capsys.readouterr().err
        assert "malfunctioned" in err
        assert "EXACTLY as written" in err

    def test_second_malfunction_ends_loop(self, tmp_path, monkeypatch, capsys):
        """One retry is the benefit of the doubt; a second empty run in a row is
        accepted as a real malfunction — the loop halts with that cause, never
        disguised as convergence."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            WORK,
            ledger={"phase": ADVISING, "advice_history": [], "anomalies": 1},
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        assert not (tmp_path / "s1_active").exists()
        assert load_ledger(tmp_path / "s1_loop.json")["phase"] == ADVISING
        err = capsys.readouterr().err
        assert "advisor loop has ended" in err
        assert "without writing its report" in err

    def test_anomalies_of_mixed_kind_share_one_counter(
        self, tmp_path, monkeypatch, capsys
    ):
        """One counter, not two per type: a bare stop at anomalies=1 (from a
        prior malfunction) reaches the cap and ends — alternating anomaly kinds
        can't dodge the cap forever."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            BARE_WORK,
            ledger={"phase": ADVISING, "advice_history": ["r"], "anomalies": 1},
        )
        (tmp_path / "s1_advisor_token").write_text("")
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        assert not (tmp_path / "s1_active").exists()
        assert "advisor loop has ended" in capsys.readouterr().err

    def test_anomaly_end_preserves_round_start_line(self, tmp_path, monkeypatch):
        """An anomaly end keeps the real slice offset (the merge preserves it),
        else the first /ploop:on round would re-slice the whole transcript."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            WORK,
            ledger={
                "phase": ADVISING,
                "advice_history": ["r"],
                "anomalies": 1,
                "round_start_line": 500,
            },
        )
        with pytest.raises(SystemExit):
            stop()  # empty advisor run -> malfunction -> anomalies 2 -> end
        assert not (tmp_path / "s1_active").exists()
        assert load_ledger(tmp_path / "s1_loop.json")["round_start_line"] == 500

    def test_termination_token_converges_and_triggers_recap(
        self, tmp_path, monkeypatch, capsys
    ):
        """The advisor certifies completion: phase -> converged and deactivated,
        the final round's narration logged (the token is machinery and never
        logged), and one last injection has the main agent report the end and
        recap the loop log."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            WORK,
            ledger={"phase": ADVISING, "advice_history": ["r"], "round": 4},
            advice=f"All requirements verified.\n\n{COMPLETION_TOKEN}",
            narration="final round work",
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["phase"] == CONVERGED  # finished — /ploop:on won't resume
        assert ledger["advice_history"] == ["r"]  # the token is never recorded
        assert not (tmp_path / "s1_active").exists()
        log = (tmp_path / "s1_loop.log").read_text()
        assert "[[ Round 3 - " in log
        assert "final round work" in log
        assert COMPLETION_TOKEN not in log
        err = capsys.readouterr().err
        assert "has ended" in err
        assert "confirmed the mission complete" in err
        assert str(tmp_path / "s1_loop.log") in err
        assert "recap" in err
        assert "candidates" not in err  # empty queue: no drain directive

    def test_expiry_token_closes_with_honest_cause(self, tmp_path, monkeypatch, capsys):
        """A deadline-expiry closure is never dressed as completion: the
        dedicated token converges the loop with the expired-deadline cause."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            WORK,
            ledger={"phase": ADVISING, "advice_history": ["r"], "round": 4},
            advice=f"Unmet: X, Y. Wrapping up.\n\n{EXPIRY_TOKEN}",
            narration="wrap-up work",
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["phase"] == CONVERGED
        assert ledger["advice_history"] == ["r"]  # the token is never recorded
        assert not (tmp_path / "s1_active").exists()
        err = capsys.readouterr().err
        assert "deadline expired" in err
        assert "mission complete" not in err
        # the closure's rationale survives in the log, without the token
        log = (tmp_path / "s1_loop.log").read_text()
        assert "Unmet: X, Y. Wrapping up." in log
        assert "[[ Audit" in log
        assert EXPIRY_TOKEN not in log

    def test_unconsumed_token_report_is_no_verdict(self, tmp_path, monkeypatch, capsys):
        """The directive exposes the report path, so a report sitting there with
        the audit token unconsumed was not written by the gated advisor — a
        self-certification attempt must not pass the gate: no convergence, no
        history entry, the file cleared at the arm."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            WORK,
            ledger={"phase": ADVISING, "advice_history": ["r"]},
            advice=f"I judge my own mission complete.\n{COMPLETION_TOKEN}",
        )
        (tmp_path / "s1_advisor_token").write_text("")  # never consumed
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2  # loop continues — no convergence
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["phase"] == ADVISING
        assert ledger["advice_history"] == ["r"]  # forged report not recorded
        assert ledger["anomalies"] == 0  # WORK transcript: a working stop
        assert (tmp_path / "s1_active").exists()
        assert not (tmp_path / "ploop_s1_advice.md").exists()  # cleared at arm
        assert "[[ Audit" not in (tmp_path / "s1_loop.log").read_text()

    def test_prose_mention_of_a_token_is_not_a_verdict(self, tmp_path, monkeypatch):
        """Machinery must be deliberate: the instruction teaches the token
        strings, so a findings report may legitimately mention one in prose —
        only a line written alone converges the loop."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            WORK,
            ledger={"phase": ADVISING, "advice_history": []},
            advice=f"- Mission: {COMPLETION_TOKEN}은 아직 쓸 수 없다 — 요구사항 3 미달",
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2  # loop continues
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["phase"] == ADVISING
        assert len(ledger["advice_history"]) == 1  # an ordinary finding set
        assert (tmp_path / "s1_active").exists()

    def test_advisor_stop_observation_is_second_provenance(self, tmp_path, monkeypatch):
        """PreToolUse drift must not strand the loop unclosable: with the token
        unconsumed but an advisor stop observed this round, the report is
        honored as a verdict."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            WORK,
            ledger={"phase": ADVISING, "advice_history": []},
            advice=f"All requirements verified.\n\n{COMPLETION_TOKEN}",
        )
        (tmp_path / "s1_advisor_token").write_text("")  # PreToolUse never fired
        (tmp_path / "s1_advisor_stopped").touch()  # but SubagentStop observed it
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        assert load_ledger(tmp_path / "s1_loop.json")["phase"] == CONVERGED
        assert not (tmp_path / "s1_active").exists()

    def test_no_round_cap_arms_indefinitely(self, tmp_path, monkeypatch):
        """There is no round limit: a long audit history still arms the next
        round rather than terminating — only the advisor (or an anomaly
        failsafe) ends the loop; /ploop:off merely pauses it."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            WORK,
            ledger={"phase": ADVISING, "advice_history": ["r"] * 999},
            advice="- still unmet",
            narration="work",
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2  # armed, not terminated
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["phase"] == ADVISING
        assert len(ledger["advice_history"]) == 1000
        assert (tmp_path / "s1_active").exists()

    def test_read_failure_freezes_round_start_line(self, tmp_path, monkeypatch):
        """An unreadable transcript at a stop must not reset round_start_line to
        1 — that would make the next round slice the whole session.  Freeze it
        instead, and never judge bareness on an unreadable transcript."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            WORK,
            ledger={
                "phase": ADVISING,
                "advice_history": ["r"],
                "round_start_line": 200,
            },
            advice="- more",
            narration="w",
        )
        arrange(  # override the transcript path with a nonexistent file
            tmp_path,
            monkeypatch,
            make_stdin(transcript_path=str(tmp_path / "gone.jsonl")),
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        assert load_ledger(tmp_path / "s1_loop.json")["round_start_line"] == 200

    def test_unreadable_transcript_is_never_bare(self, tmp_path, monkeypatch, capsys):
        """No lines means no growth evidence either way — fail toward patience:
        a working stop, not an anomaly."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            WORK,
            ledger={"phase": ADVISING, "advice_history": []},
        )
        (tmp_path / "s1_advisor_token").write_text("")
        arrange(
            tmp_path,
            monkeypatch,
            make_stdin(transcript_path=str(tmp_path / "gone.jsonl")),
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        assert load_ledger(tmp_path / "s1_loop.json")["anomalies"] == 0
        assert "certify completion belongs" not in capsys.readouterr().err

    def test_deadline_frontmatter_rides_the_directive(
        self, tmp_path, monkeypatch, capsys
    ):
        """anchor frontmatter의 deadline이 arm 시점에 status로 렌더링되어 directive에
        실린다 — parse·시계·주입이 stop() 경유로 이어지는 end-to-end."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            WORK,
            ledger={"phase": ADVISING, "advice_history": []},
            advice="- finding",
        )
        (tmp_path / "s1_anchor.md").write_text(
            "---\ndeadline: 2099-01-01T00:00+00:00\n---\n\nbuild the thing"
        )
        with pytest.raises(SystemExit):
            stop()
        err = capsys.readouterr().err
        assert "deadline:" in err and "remaining" in err

    def test_expired_deadline_mandates_convening(self, tmp_path, monkeypatch, capsys):
        """Past the deadline the directive closes the keep-working branch and
        orders the audit — enforcement stays with the advisor."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            WORK,
            ledger={"phase": ADVISING, "advice_history": []},
            advice="- finding",
        )
        (tmp_path / "s1_anchor.md").write_text(
            "---\ndeadline: 2020-01-01T00:00+00:00\n---\n\nbuild the thing"
        )
        with pytest.raises(SystemExit):
            stop()
        err = capsys.readouterr().err
        assert "expired" in err
        assert "NOW" in err
        assert "keep working" not in err

    def test_running_marker_pauses_without_rearm(self, tmp_path, monkeypatch):
        """Running marker present (advisor in flight — e.g. pushed to the
        background): allow the stop, don't re-arm — no cascade.  SubagentStop is
        the marker's sole clearer, so the loop just waits for it."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            WORK,
            ledger={"phase": ADVISING, "advice_history": []},
        )
        (tmp_path / "s1_advisor_running").touch()
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 0
        assert load_ledger(tmp_path / "s1_loop.json")["phase"] == ADVISING
        assert (tmp_path / "s1_advisor_running").exists()

    def test_inflight_background_subagent_waits(self, tmp_path, monkeypatch):
        """The harness stops the session with delegated background work still in
        flight, reporting it in background_tasks: a subagent or workflow entry
        means the round is not done — allow the stop, don't inject."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            WORK,
            ledger={"phase": ADVISING, "advice_history": []},
        )
        arrange(
            tmp_path,
            monkeypatch,
            make_stdin(
                transcript_path=str(tmp_path / "s1.jsonl"),
                background_tasks=[
                    {"id": "t1", "type": "subagent", "status": "running"}
                ],
            ),
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 0
        assert load_ledger(tmp_path / "s1_loop.json")["phase"] == ADVISING
        assert not (tmp_path / "s1_advisor_token").exists()

    def test_backfills_project_provenance(self, tmp_path, monkeypatch):
        """A loop launched before provenance recording gains its launch-directory
        record at the next stop — even one that exits early on a gate."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            WORK,
            ledger={"phase": ADVISING, "advice_history": []},
        )
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/w/repo")
        arrange(
            tmp_path,
            monkeypatch,
            make_stdin(
                transcript_path=str(tmp_path / "s1.jsonl"),
                background_tasks=[
                    {"id": "t1", "type": "subagent", "status": "running"}
                ],
            ),
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 0
        assert (tmp_path / "s1_project").read_text() == "/w/repo"

    def test_running_shells_gate_silently(self, tmp_path, monkeypatch, capsys):
        """A shell-only background defers the directive exactly like a subagent:
        silent exit 0, nothing injected, no state written — the shell's exit
        or the heartbeat wakes the session."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            WORK,
            ledger={"phase": ADVISING, "advice_history": []},
        )
        arrange(
            tmp_path,
            monkeypatch,
            make_stdin(
                transcript_path=str(tmp_path / "s1.jsonl"),
                background_tasks=[{"id": "t1", "type": "shell", "status": "running"}],
            ),
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 0
        assert capsys.readouterr().err == ""
        assert not (tmp_path / "s1_advisor_token").exists()
        assert load_ledger(tmp_path / "s1_loop.json")["phase"] == ADVISING

    def test_monitor_only_background_arms(self, tmp_path, monkeypatch, capsys):
        """Monitor is the ambient, session-lifetime lane and never gates: a stop
        with only monitors left is a legitimate round end — the directive arms."""
        arrange_anchor(tmp_path, monkeypatch, WORK, ledger={"phase": FRESH})
        arrange(
            tmp_path,
            monkeypatch,
            make_stdin(
                transcript_path=str(tmp_path / "s1.jsonl"),
                background_tasks=[{"id": "t2", "type": "monitor", "status": "running"}],
            ),
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        assert (tmp_path / "s1_advisor_token").exists()
        assert "ploop:advisor" in capsys.readouterr().err

    def test_terminal_status_shell_does_not_gate(self, tmp_path, monkeypatch):
        """A completed shell lingering in the list must not defer the round —
        its completion already woke the session."""
        arrange_anchor(tmp_path, monkeypatch, WORK, ledger={"phase": FRESH})
        arrange(
            tmp_path,
            monkeypatch,
            make_stdin(
                transcript_path=str(tmp_path / "s1.jsonl"),
                background_tasks=[{"id": "t1", "type": "shell", "status": "completed"}],
            ),
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        assert (tmp_path / "s1_advisor_token").exists()

    def test_pending_candidates_surface_to_advisor(self, tmp_path, monkeypatch, capsys):
        """A non-empty candidates queue reaches the advisor as a conditional
        prompt line — the hook decides emptiness in code — and the main-owned
        file survives the arm (rounds accumulate into it, only launch clears)."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            WORK,
            ledger={"phase": ADVISING, "advice_history": []},
            advice="- keep going",
            narration="worked",
        )
        (tmp_path / "ploop_s1_candidates.md").write_text("fact: X — measured via Y")
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "queued for promotion" in err  # the advisor-facing conditional line
        assert str(tmp_path / "ploop_s1_candidates.md") in err
        assert (tmp_path / "ploop_s1_candidates.md").exists()

    def test_end_notice_directs_candidates_drain(self, tmp_path, monkeypatch, capsys):
        """An automatic end with entries still queued appends the drain
        directive — end_loop is the single point, so every auto-termination
        path carries it — and the queue file survives the end."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            WORK,
            ledger={"phase": ADVISING, "advice_history": ["r"]},
            advice=f"All covered.\n\n{COMPLETION_TOKEN}",
            narration="final",
        )
        (tmp_path / "ploop_s1_candidates.md").write_text("term: foo")
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "still holds entries" in err
        assert "promote or discard" in err
        assert str(tmp_path / "ploop_s1_candidates.md") in err
        assert (tmp_path / "ploop_s1_candidates.md").exists()


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
        """Outside an active anchor the advisor gate does not interfere."""
        arrange(tmp_path, monkeypatch, make_pretooluse_stdin())
        with pytest.raises(SystemExit) as exc:
            pre_tool_use()
        assert exc.value.code == 0

    def test_no_token_denies_second_audit_this_round(self, tmp_path, monkeypatch):
        """The token authorizes one audit per round: consumed (or never armed)
        means the call is denied until the next stop re-arms."""
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

    def test_worker_types_containing_advisor_pass_ungated(self, tmp_path, monkeypatch):
        """The gate matches the registered scoped name exactly: a delegated
        worker whose type merely contains "advisor" is neither denied without a
        token nor allowed to consume one."""
        (tmp_path / "s1_active").touch()
        (tmp_path / "s1_advisor_token").write_text("")
        for name in ("security-advisor", "advisor"):
            arrange(tmp_path, monkeypatch, make_pretooluse_stdin(subagent_type=name))
            with pytest.raises(SystemExit) as exc:
                pre_tool_use()
            assert exc.value.code == 0
            assert (tmp_path / "s1_advisor_token").exists()  # not consumed
            assert not (tmp_path / "s1_advisor_running").exists()


# ── heartbeat: the silence timer and its fire phase ──


class TestHeartbeatArm:
    def arm(self, tmp_path, monkeypatch):
        arrange(
            tmp_path,
            monkeypatch,
            make_stdin(transcript_path=str(tmp_path / "s1.jsonl")),
        )

    def test_unarmed_session_prints_nothing(self, tmp_path, monkeypatch, capsys):
        """No handoff line -> the wrapper stands down without sleeping."""
        self.arm(tmp_path, monkeypatch)
        with pytest.raises(SystemExit) as exc:
            heartbeat_arm()
        assert exc.value.code == 0
        assert capsys.readouterr().out == ""
        assert not (tmp_path / "s1_heartbeat_nonce").exists()

    def test_armed_stop_writes_nonce_and_hands_off(self, tmp_path, monkeypatch, capsys):
        """An armed stop persists a fresh nonce and prints the wrapper handoff
        (session, nonce, interval); a second stop supersedes the first nonce."""
        (tmp_path / "s1_active").touch()
        self.arm(tmp_path, monkeypatch)
        heartbeat_arm()
        first = (tmp_path / "s1_heartbeat_nonce").read_text()
        assert capsys.readouterr().out == f"s1 {first} {HEARTBEAT_SECONDS}"

        self.arm(tmp_path, monkeypatch)
        heartbeat_arm()
        second = (tmp_path / "s1_heartbeat_nonce").read_text()
        assert second != first
        assert capsys.readouterr().out == f"s1 {second} {HEARTBEAT_SECONDS}"


class TestHeartbeatFire:
    def fire(self, tmp_path, monkeypatch, argv):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        monkeypatch.setattr("sys.argv", ["heartbeat-fire", *argv])
        with pytest.raises(SystemExit) as exc:
            heartbeat_fire()
        return exc.value.code

    def test_silent_interval_wakes_the_session(self, tmp_path, monkeypatch, capsys):
        (tmp_path / "s1_active").touch()
        (tmp_path / "s1_heartbeat_nonce").write_text("n1")
        assert self.fire(tmp_path, monkeypatch, ["s1", "n1"]) == 2
        assert capsys.readouterr().err == HEARTBEAT_NOTICE

    @pytest.mark.parametrize(
        "arrange_case, argv",
        [
            ("superseded", ["s1", "n1"]),  # a later stop owns the watch
            ("inactive", ["s1", "n2"]),  # the loop ended or paused
            ("no-nonce", ["s1", "n1"]),  # round state cleared under the timer
            ("short-argv", ["s1"]),  # malformed relaunch of the fire phase
        ],
    )
    def test_stand_down_paths_are_silent(
        self, tmp_path, monkeypatch, capsys, arrange_case, argv
    ):
        if arrange_case == "superseded":
            (tmp_path / "s1_active").touch()
            (tmp_path / "s1_heartbeat_nonce").write_text("n2")
        elif arrange_case == "inactive":
            (tmp_path / "s1_heartbeat_nonce").write_text("n2")
        elif arrange_case == "no-nonce":
            (tmp_path / "s1_active").touch()
        assert self.fire(tmp_path, monkeypatch, argv) == 0
        assert capsys.readouterr().err == ""


# ── subagent_stop advisor-running marker ──


class TestSubagentStop:
    def test_advisor_stop_clears_running_and_records_provenance(
        self, tmp_path, monkeypatch
    ):
        (tmp_path / "s1_advisor_running").touch()
        arrange(
            tmp_path,
            monkeypatch,
            json.dumps({"session_id": "s1", "agent_type": "advisor"}),
        )
        subagent_stop()
        assert not (tmp_path / "s1_advisor_running").exists()
        assert (tmp_path / "s1_advisor_stopped").exists()  # 2nd verdict provenance

    def test_scoped_advisor_stop_clears_running_marker(self, tmp_path, monkeypatch):
        """The stop payload has carried the bare name as well as the scoped
        registration name — both forms must clear the marker, else it strands
        and stalls the loop."""
        (tmp_path / "s1_advisor_running").touch()
        arrange(
            tmp_path,
            monkeypatch,
            json.dumps({"session_id": "s1", "agent_type": "ploop:advisor"}),
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

    def test_worker_name_containing_advisor_leaves_marker(self, tmp_path, monkeypatch):
        """A delegated worker whose name merely contains "advisor" must not
        clear the in-flight marker — an early clear would let the next stop
        re-arm a second advisor."""
        (tmp_path / "s1_advisor_running").touch()
        arrange(
            tmp_path,
            monkeypatch,
            json.dumps({"session_id": "s1", "agent_type": "my-advisor-x"}),
        )
        with pytest.raises(SystemExit):
            subagent_stop()
        assert (tmp_path / "s1_advisor_running").exists()


# ── SessionStart compact: re-anchoring (mechanism 2) ──


class TestReanchor:
    def test_armed_loop_reenters_anchor_and_queue_address(
        self, tmp_path, monkeypatch, capsys
    ):
        """Right after a compaction the anchor's full text and the candidates
        address ride additionalContext into the rebuilt context — no round has
        to arm first, so a loop asleep on the background gate is re-anchored too."""
        arrange_anchor(tmp_path, monkeypatch, [])
        reanchor()
        delivered = json.loads(capsys.readouterr().out)["hookSpecificOutput"]
        assert delivered["hookEventName"] == "SessionStart"
        context = delivered["additionalContext"]
        queue_line = format_candidates_notice(Workspace.from_env("s1").candidates_path)
        assert "build the thing" in context
        assert context.index("build the thing") < context.index(queue_line)

    def test_unarmed_session_is_silent(self, tmp_path, monkeypatch, capsys):
        arrange(tmp_path, monkeypatch, make_stdin())
        with pytest.raises(SystemExit) as exc:
            reanchor()
        assert exc.value.code == 0
        assert capsys.readouterr().out == ""


# ── /ploop:launch UserPromptExpansion hook ──


class TestLaunch:
    def make_stdin(self, **payload):
        return io.StringIO(json.dumps(payload))

    def prereqs(
        self, tmp_path, monkeypatch, *, depth="5", auto_compact=True, thinking=True
    ):
        """Satisfy ploop's launch prerequisites; return the project dir.

        Sets the nested-subagent env cap (depth=None leaves it unset) and writes a
        project .claude/settings.json with the compaction and thinking toggles.
        """
        if depth is None:
            monkeypatch.delenv("CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH", raising=False)
        else:
            monkeypatch.setenv("CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH", depth)
        proj = tmp_path / "repo"
        (proj / ".claude").mkdir(parents=True, exist_ok=True)
        (proj / ".claude" / "settings.json").write_text(
            json.dumps(
                {"autoCompactEnabled": auto_compact, "alwaysThinkingEnabled": thinking}
            )
        )
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(proj))
        return proj

    def test_writes_stripped_anchor_and_arms_loop(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        proj = self.prereqs(tmp_path, monkeypatch)
        anchor = '  do the thing\nwith "quotes" and $vars  '
        monkeypatch.setattr(
            "sys.stdin",
            self.make_stdin(
                command_name="ploop:launch", command_args=anchor, session_id="s1"
            ),
        )
        save_ledger(
            tmp_path / "s1_loop.json",
            {"phase": CONVERGED, "advice_history": ["stale"]},
        )
        (tmp_path / "s1_loop.log").write_text("prior anchor log")
        launch()
        saved = (tmp_path / "s1_anchor.md").read_text()
        assert saved == 'do the thing\nwith "quotes" and $vars'
        assert (tmp_path / "s1_active").exists()
        assert (tmp_path / "s1_project").read_text() == str(proj)
        assert not (tmp_path / "s1_loop.json").exists()  # prior ledger cleared
        # an anchor owns one log, opened with its own text
        log = (tmp_path / "s1_loop.log").read_text()
        assert log.startswith("[[ ANCHOR ]]\n\n")
        assert saved in log
        assert "prior anchor log" not in log

    def test_arming_launch_delivers_the_candidates_address(
        self, tmp_path, monkeypatch, capsys
    ):
        """The skill body directs candidates at the queue, so the address ships in
        the same turn — and it is the very line every directive re-delivers, so the
        main agent is never left reconciling two addresses."""
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        self.prereqs(tmp_path, monkeypatch)
        monkeypatch.setattr(
            "sys.stdin",
            self.make_stdin(
                command_name="ploop:launch", command_args="do it", session_id="s1"
            ),
        )
        launch()
        delivered = json.loads(capsys.readouterr().out)["hookSpecificOutput"]
        assert delivered["hookEventName"] == "UserPromptExpansion"
        assert delivered["additionalContext"] == format_candidates_notice(
            Workspace.from_env("s1").candidates_path
        )

    def test_array_command_args_join_verbatim(self, tmp_path, monkeypatch):
        """The reference schema types command_args as an array while observed
        events carry a string — both shapes must yield the anchor verbatim,
        or a harness update corrupts the anchor."""
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        self.prereqs(tmp_path, monkeypatch)
        monkeypatch.setattr(
            "sys.stdin",
            self.make_stdin(
                command_name="ploop:launch",
                command_args=["multi\nline anchor", "with args"],
                session_id="s1",
            ),
        )
        launch()
        saved = (tmp_path / "s1_anchor.md").read_text()
        assert saved == "multi\nline anchor with args"
        assert (tmp_path / "s1_active").exists()

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
        assert not (tmp_path / "s1_anchor.md").exists()
        assert not (tmp_path / "s1_active").exists()

    def test_blank_anchor_blocks_expansion(self, tmp_path, monkeypatch, capsys):
        """A blank anchor is blocked at expansion — otherwise the skill body
        would announce an activation the hook never armed (a ghost loop).  A
        blocked turn is erased, so it carries the reason and nothing else: the
        queue address rides only a launch that armed."""
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
        out = capsys.readouterr().out
        assert json.loads(out)["decision"] == "block"
        assert "candidates" not in out
        assert not (tmp_path / "s1_active").exists()

    def test_armed_loop_blocks_relaunch_untouched(self, tmp_path, monkeypatch, capsys):
        """Relaunching over an armed loop is blocked purely: anchor, log, and
        the in-flight marker survive — the running loop is not disturbed, and
        the reason routes the user to /ploop:off."""
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        (tmp_path / "s1_active").touch()
        (tmp_path / "s1_anchor.md").write_text("old anchor")
        (tmp_path / "s1_loop.log").write_text("old log")
        (tmp_path / "s1_advisor_running").touch()
        monkeypatch.setattr(
            "sys.stdin",
            self.make_stdin(
                command_name="ploop:launch", command_args="new anchor", session_id="s1"
            ),
        )
        with pytest.raises(SystemExit) as exc:
            launch()
        assert exc.value.code == 0
        out = json.loads(capsys.readouterr().out)
        assert out["decision"] == "block"
        assert "/ploop:off" in out["reason"]
        assert (tmp_path / "s1_anchor.md").read_text() == "old anchor"
        assert (tmp_path / "s1_loop.log").read_text() == "old log"
        assert (tmp_path / "s1_advisor_running").exists()

    def test_all_prerequisites_met_arms(self, tmp_path, monkeypatch):
        """With nesting (env >= 5), auto compaction, and thinking all satisfied,
        the launch clears the assertion and arms the loop."""
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        self.prereqs(tmp_path, monkeypatch)
        monkeypatch.setattr(
            "sys.stdin",
            self.make_stdin(
                command_name="ploop:launch", command_args="do it", session_id="s1"
            ),
        )
        launch()
        assert (tmp_path / "s1_active").exists()
        assert (tmp_path / "s1_anchor.md").read_text() == "do it"

    @pytest.mark.parametrize(
        "unmet, needle",
        [
            ({"depth": None}, "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"),
            ({"depth": "2"}, "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"),
            ({"auto_compact": False}, "autoCompactEnabled"),
            ({"thinking": False}, "alwaysThinkingEnabled"),
        ],
    )
    def test_unmet_prerequisite_blocks(
        self, tmp_path, monkeypatch, capsys, unmet, needle
    ):
        """Each unmet prerequisite blocks the launch and names its settings.json
        fix — nesting from the env (unset or below 5, the provisioned pin),
        compaction and thinking from the project settings.json."""
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        self.prereqs(tmp_path, monkeypatch, **unmet)
        monkeypatch.setattr(
            "sys.stdin",
            self.make_stdin(
                command_name="ploop:launch", command_args="do it", session_id="s1"
            ),
        )
        with pytest.raises(SystemExit) as exc:
            launch()
        assert exc.value.code == 0
        out = json.loads(capsys.readouterr().out)
        assert out["decision"] == "block"
        assert needle in out["reason"]
        assert not (tmp_path / "s1_active").exists()
        assert not (tmp_path / "s1_anchor.md").exists()

    def test_multiple_unmet_all_listed_with_restart(
        self, tmp_path, monkeypatch, capsys
    ):
        """Several unmet prerequisites collect into one notice that lists every
        fix and calls for a settings.json edit + restart."""
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        self.prereqs(
            tmp_path, monkeypatch, depth=None, auto_compact=False, thinking=False
        )
        monkeypatch.setattr(
            "sys.stdin",
            self.make_stdin(
                command_name="ploop:launch", command_args="do it", session_id="s1"
            ),
        )
        with pytest.raises(SystemExit):
            launch()
        reason = json.loads(capsys.readouterr().out)["reason"]
        assert "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH" in reason
        assert "autoCompactEnabled" in reason
        assert "alwaysThinkingEnabled" in reason
        assert "restart" in reason.lower()
        assert not (tmp_path / "s1_active").exists()


# ── /ploop:off UserPromptExpansion hook ──


class TestOffCommand:
    def make_stdin(self, **payload):
        return io.StringIO(json.dumps(payload))

    def arrange(self, tmp_path, monkeypatch, *, command_name="ploop:off"):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        monkeypatch.setattr(
            "sys.stdin",
            self.make_stdin(command_name=command_name, session_id="s1"),
        )

    def test_pauses_preserving_round_state_for_resume(
        self, tmp_path, monkeypatch, capsys
    ):
        """off pauses unconditionally — the active gate and the running marker are
        dropped even with a background advisor in flight — but the round state
        (ledger, audit-history) is PRESERVED so /ploop:on can resume from here.
        No end notice is emitted; the static skill body carries the quiet notice."""
        for name in ("s1_active", "s1_advisor_running", "s1_advisor_token"):
            (tmp_path / name).touch()
        save_ledger(
            tmp_path / "s1_loop.json",
            {"phase": ADVISING, "advice_history": ["r"]},
        )
        (tmp_path / "s1_advice_history.md").write_text("<audit-1>\n\nr\n\n</audit-1>")
        (tmp_path / "s1_anchor.md").write_text("m")
        (tmp_path / "s1_loop.log").write_text("log")
        self.arrange(tmp_path, monkeypatch)
        off_command()
        assert not (tmp_path / "s1_active").exists()  # loop paused
        assert not (tmp_path / "s1_advisor_running").exists()  # unconditional pause
        # round state preserved for resume (unlike the old destructive stop)
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["phase"] == ADVISING
        assert ledger["advice_history"] == ["r"]
        assert (tmp_path / "s1_advice_history.md").exists()
        assert (tmp_path / "s1_anchor.md").exists()
        assert (tmp_path / "s1_loop.log").exists()
        assert capsys.readouterr().out == ""  # quiet — no report injected

    def test_inactive_off_blocks_expansion(self, tmp_path, monkeypatch, capsys):
        """Already off (or never launched): the expansion is blocked purely — the
        skill body never announces a pause that didn't happen, and prior state is
        untouched."""
        (tmp_path / "s1_anchor.md").write_text("m")
        self.arrange(tmp_path, monkeypatch)
        with pytest.raises(SystemExit) as exc:
            off_command()
        assert exc.value.code == 0
        assert json.loads(capsys.readouterr().out)["decision"] == "block"
        assert (tmp_path / "s1_anchor.md").exists()

    def test_ignores_other_plugin_off(self, tmp_path, monkeypatch):
        """The guard matches the full scoped name, so another plugin's :off cannot
        pause ploop."""
        (tmp_path / "s1_active").touch()
        self.arrange(tmp_path, monkeypatch, command_name="other:off")
        with pytest.raises(SystemExit):
            off_command()
        assert (tmp_path / "s1_active").exists()  # untouched


# ── /ploop:on UserPromptExpansion hook ──


class TestOnCommand:
    def make_stdin(self, **payload):
        return io.StringIO(json.dumps(payload))

    def arrange(self, tmp_path, monkeypatch, *, command_name="ploop:on"):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        monkeypatch.setattr(
            "sys.stdin",
            self.make_stdin(command_name=command_name, session_id="s1"),
        )

    def arrange_paused(self, tmp_path, *, ledger=None):
        """A paused loop: anchors on disk, no active marker."""
        (tmp_path / "s1_anchor.md").write_text("build the thing")
        (tmp_path / "s1_loop.log").write_text("[[ ANCHOR ]]\n\nbuild the thing\n\n")
        if ledger:
            save_ledger(tmp_path / "s1_loop.json", ledger)

    def test_resumes_paused_loop_normalizing_state(self, tmp_path, monkeypatch):
        """A resume re-arms the loop and normalizes the round state to a clean
        arming point: phase reset to fresh (so the next stop skips judging a
        round whose token was never armed) while audit-history and
        round_start_line are PRESERVED by the merge, and the stale handoff/gate
        transients are cleared so the first resumed stop arms cleanly."""
        self.arrange_paused(
            tmp_path,
            ledger={
                "phase": ADVISING,
                "advice_history": ["a", "b"],
                "round_start_line": 842,
                "round": 7,
            },
        )
        for name in (
            "s1_advisor_token",
            "s1_advisor_running",
            "s1_advisor_stopped",
            "ploop_s1_advice.md",
            "ploop_s1_narration.md",
        ):
            (tmp_path / name).touch()
        monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
        self.arrange(tmp_path, monkeypatch)
        on_command()
        assert (tmp_path / "s1_active").exists()  # re-armed
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["phase"] == FRESH  # the next stop skips judging
        assert ledger["advice_history"] == ["a", "b"]  # preserved
        assert ledger["round_start_line"] == 842  # preserved
        assert ledger["round"] == 7  # preserved
        # stale transients cleared so the first resumed stop arms cleanly
        assert not (tmp_path / "s1_advisor_token").exists()
        assert not (tmp_path / "s1_advisor_running").exists()
        assert not (tmp_path / "s1_advisor_stopped").exists()
        assert not (tmp_path / "ploop_s1_advice.md").exists()
        assert not (tmp_path / "ploop_s1_narration.md").exists()

    def test_active_loop_is_rearmed_not_blocked(self, tmp_path, monkeypatch):
        """on is the universal wake button: a loop still marked active but stuck
        mid-round (e.g. an in-flight advisor stranded by an ESC or API error) is
        re-armed, not refused — the round state is normalized and the stuck
        running marker cleared so the next stop arms cleanly."""
        self.arrange_paused(
            tmp_path,
            ledger={
                "phase": ADVISING,
                "advice_history": ["a"],
                "round_start_line": 200,
            },
        )
        (tmp_path / "s1_active").touch()  # still active, but stalled
        (tmp_path / "s1_advisor_running").touch()  # a stranded in-flight marker
        monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
        self.arrange(tmp_path, monkeypatch)
        on_command()
        assert (tmp_path / "s1_active").exists()  # armed, not blocked
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["phase"] == FRESH  # normalized
        assert ledger["advice_history"] == ["a"]  # preserved
        assert ledger["round_start_line"] == 200  # preserved
        assert not (tmp_path / "s1_advisor_running").exists()  # stranded marker cleared

    def test_missing_anchor_blocks_on(self, tmp_path, monkeypatch, capsys):
        """No anchor (never launched, or a different session): nothing to
        resume — blocked, no loop armed."""
        (tmp_path / "s1_loop.log").write_text("log")  # log without anchor
        self.arrange(tmp_path, monkeypatch)
        with pytest.raises(SystemExit):
            on_command()
        assert json.loads(capsys.readouterr().out)["decision"] == "block"
        assert not (tmp_path / "s1_active").exists()

    def test_missing_log_blocks_on(self, tmp_path, monkeypatch, capsys):
        """No round log: nothing to resume — blocked, no loop armed."""
        (tmp_path / "s1_anchor.md").write_text("m")  # anchor without log
        self.arrange(tmp_path, monkeypatch)
        with pytest.raises(SystemExit):
            on_command()
        assert json.loads(capsys.readouterr().out)["decision"] == "block"
        assert not (tmp_path / "s1_active").exists()

    def test_converged_anchor_blocks_on(self, tmp_path, monkeypatch, capsys):
        """The one non-resumable state: a converged anchor — the advisor
        certified completion, a genuine end, not a stall. on refuses it;
        the user launches a fresh anchor.  (An anomaly halt or /ploop:off leaves
        the phase advising, so it resumes like any paused loop — same state,
        covered by test_resumes_paused_loop_normalizing_state.)"""
        self.arrange_paused(
            tmp_path,
            ledger={"phase": CONVERGED, "advice_history": ["a"]},
        )
        self.arrange(tmp_path, monkeypatch)
        with pytest.raises(SystemExit):
            on_command()
        assert json.loads(capsys.readouterr().out)["decision"] == "block"
        assert not (tmp_path / "s1_active").exists()

    def test_ignores_other_plugin_on(self, tmp_path, monkeypatch):
        """The guard matches the full scoped name, so another plugin's :on cannot
        resume ploop."""
        self.arrange_paused(tmp_path)
        self.arrange(tmp_path, monkeypatch, command_name="other:on")
        with pytest.raises(SystemExit):
            on_command()
        assert not (tmp_path / "s1_active").exists()

    def test_resume_then_stop_arms_cleanly(self, tmp_path, monkeypatch, capsys):
        """The resume guarantee, end to end: after /ploop:on, the very next stop
        arms the directive (exit 2) without a false malfunction or a false bare
        judgment — the fresh phase skips judging a round whose token was never
        armed, and the preserved audit-history is re-emitted intact."""
        self.arrange_paused(
            tmp_path,
            ledger={
                "phase": ADVISING,
                "advice_history": ["a", "b"],
                "round_start_line": 1,
            },
        )
        monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
        self.arrange(tmp_path, monkeypatch)
        on_command()  # resume
        # now drive the next main-session stop, with a short (bare-like) transcript
        main = tmp_path / "s1.jsonl"
        write_jsonl(main, BARE_WORK)
        arrange(tmp_path, monkeypatch, make_stdin(transcript_path=str(main)))
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2  # armed, not passed or terminated
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["phase"] == ADVISING  # advanced from the reset fresh
        assert ledger["advice_history"] == ["a", "b"]  # preserved, not duplicated
        assert ledger["anomalies"] == 0  # a short resume turn is not bare
        assert (tmp_path / "s1_advisor_token").exists()  # a fresh round armed
        err = capsys.readouterr().err
        assert "ploop:advisor" in err  # the directive was injected
        assert "malfunctioned" not in err
        assert "certify completion belongs" not in err


# ── write_round_slice ──


class TestWriteRoundSlice:
    def test_slice_starts_at_round_start_excluding_prior_rounds(self, tmp_path):
        """The slice is a pure line range [round_start .. end]: prior rounds'
        lines (before round_start) are excluded, and the whole rest is kept —
        no message parsing, so a mid-round interjection can't truncate it."""
        lines = [f"line {i}\n" for i in range(1, 6)]  # 5 transcript lines
        out = tmp_path / "round.jsonl"
        write_round_slice(lines, round_start=3, out_path=out)
        assert out.read_text() == "line 3\nline 4\nline 5\n"

    def test_round_zero_slice_is_the_whole_transcript(self, tmp_path):
        lines = ["a\n", "b\n"]
        out = tmp_path / "round.jsonl"
        write_round_slice(lines, round_start=1, out_path=out)
        assert out.read_text() == "a\nb\n"

    def test_empty_transcript_yields_empty_slice(self, tmp_path):
        out = tmp_path / "round.jsonl"
        write_round_slice([], round_start=1, out_path=out)
        assert out.read_text() == ""


# ── log entries ──


class TestLogEntries:
    def test_round_entry_carries_the_narration(self, tmp_path):
        log = tmp_path / "l.log"
        write_round_entry(log, 0, "anchor work")
        content = log.read_text()
        assert "[[ Round 0 - " in content
        assert "anchor work" in content

    def test_audit_entry_carries_the_report_verbatim(self, tmp_path):
        log = tmp_path / "l.log"
        write_round_entry(log, 0, "w0")
        write_audit_entry(log, 1, "- Mission: X unmet")
        content = log.read_text()
        assert "[[ Audit 1 - " in content
        assert content.index("w0") < content.index("- Mission: X unmet")
