"""Tests for the main module — Stop, PreToolUse, SubagentStop, PostCompact entry points.

The hook owns the whole ledger: it records the advisor's prior-round verdict (the
advice it wrote to advice.md; the termination token moves the phase to converged),
then drives the next round.  The first anomaly gets a benefit-of-the-doubt repeat
(an empty advisor run is retried, a stop that ignored the trigger is re-triggered);
a second consecutive anomaly of any kind ends the loop with an honest cause.  These
tests drive `stop` with a main transcript plus the advisor's advice.md, the sole
advice channel.
"""

import io
import json

import pytest

from src.main import (
    TERMINATION_TOKEN,
    launch,
    mark_compaction,
    off_command,
    on_command,
    pre_tool_use,
    stop,
    subagent_stop,
    write_log,
    write_round_slice,
)
from src.state import ADVISING, CONVERGED, FRESH, load_ledger, save_ledger

# A minimal round transcript: a trigger boundary + the main agent's own work.
# The advice comes from advice.md (the sole channel); this transcript only sets
# the line count (the round's end offset the hook records for the narrator).
ROUND_WORK = [
    {"role": "user", "content": "advisor trigger"},
    {"role": "assistant", "content": "working on the advice"},
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
    holds the anchor text.  `ledger` (a partial dict) seeds the round state — load fills
    the rest with defaults.  `advice` / `narration` (when given) are the advisor's and
    narrator's temp-channel files, routed under tmp_path via gettempdir.
    """
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    (tmp_path / f"{session_id}_active").touch()
    (tmp_path / f"{session_id}_anchor.md").write_text("build the thing")
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

    def test_fresh_phase_writes_advice_history_and_injects(
        self, tmp_path, monkeypatch, capsys
    ):
        """A fresh (just-launched) loop has no verdict to record: the first stop
        arms the first advisor round and advances the phase to advising."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            [
                {"role": "user", "content": "anchor"},
                {"role": "assistant", "content": "initial work"},
            ],
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        assert load_ledger(tmp_path / "s1_loop.json")["phase"] == ADVISING
        assert "No prior advice." in (tmp_path / "s1_advice_history.md").read_text()
        err = capsys.readouterr().err
        assert "anchor:" in err
        assert str(tmp_path / "s1_anchor.md") in err
        assert "advice-history:" in err
        assert "instructions:" in err
        assert "ploop:advisor" in err
        assert "round:" in err  # narrator gets the round slice file
        assert str(tmp_path / "s1_round.jsonl") in err
        assert (tmp_path / "s1_advisor_token").exists()
        # the queue path rides every trigger; an empty queue shows no advisor line
        assert "Your candidates queue" in err
        assert "uncovered region" not in err
        # the fresh round's slice is the whole transcript (from line 1)
        assert "initial work" in (tmp_path / "s1_round.jsonl").read_text()
        assert load_ledger(tmp_path / "s1_loop.json")["round_start_line"] == 3

    def test_records_advice_and_logs_completed_first_round(self, tmp_path, monkeypatch):
        arrange_anchor(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"phase": ADVISING, "advice_history": []},
            advice="consider error handling",
            narration="initial work narrative",
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["phase"] == ADVISING  # arms the next round
        assert ledger["advice_history"] == ["consider error handling"]
        advice_history = (tmp_path / "s1_advice_history.md").read_text()
        assert "<advice-1>" in advice_history
        assert "consider error handling" in advice_history
        # The narration narrates round 0 (anchor work, no advice answered), so
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
        arrange_anchor(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"phase": ADVISING, "advice_history": []},
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
        arrange_anchor(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"phase": ADVISING, "advice_history": ["r1", "r2"]},
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

    def test_absent_advice_retries_round_with_inputs_frozen(
        self, tmp_path, monkeypatch, capsys
    ):
        """The advisor finished (no running marker) and wrote nothing — a
        malfunction, not a verdict (the protocol demands a Write even to
        terminate).  The round is retried: phase stays advising, a fresh token,
        and the round's inputs (round_start_line, advice_history.md) preserved by
        the merge so the retried advisor sees what the failed one saw; nothing is
        logged — the round completes at its eventual successful stop."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={
                "phase": ADVISING,
                "advice_history": [],
                "round_start_line": 5,
            },
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["phase"] == ADVISING  # retried, still advising
        assert ledger["anomalies"] == 1
        assert ledger["round_start_line"] == 5  # frozen — same slice re-narrated
        assert (tmp_path / "s1_active").exists()
        assert (tmp_path / "s1_advisor_token").exists()
        assert not (tmp_path / "s1_advice_history.md").exists()
        assert not (tmp_path / "s1_loop.log").exists()  # nothing logged
        err = capsys.readouterr().err
        assert "malfunctioned" in err
        assert "EXACTLY as written" in err  # the trigger follows the notice

    def test_second_consecutive_anomaly_ends_loop(self, tmp_path, monkeypatch, capsys):
        """One retry is the benefit of the doubt; a second empty run in a row is
        accepted as a real malfunction — the loop halts with that cause, never
        disguised as convergence: the phase stays advising (an unfinished anchor
        /ploop:on can resume), only the active marker is dropped."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"phase": ADVISING, "advice_history": [], "anomalies": 1},
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        assert not (tmp_path / "s1_active").exists()  # halted
        # an anomaly halt is not a finished anchor — /ploop:on can wake it
        assert load_ledger(tmp_path / "s1_loop.json")["phase"] == ADVISING
        err = capsys.readouterr().err
        assert "advisor loop has ended" in err
        assert "finished without writing advice" in err

    def test_anomaly_end_preserves_round_start_line(self, tmp_path, monkeypatch):
        """P1, at the stop level: an anomaly end keeps the real slice offset (the
        merge preserves it), else the first /ploop:on round would re-slice the
        whole transcript.  A second malfunction ends the loop with offset 500 —
        it must survive."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={
                "phase": ADVISING,
                "advice_history": ["r"],
                "anomalies": 1,
                "round_start_line": 500,
            },
        )
        with pytest.raises(SystemExit):
            stop()  # empty advice -> malfunction -> anomalies 2 -> end
        assert not (tmp_path / "s1_active").exists()
        assert load_ledger(tmp_path / "s1_loop.json")["round_start_line"] == 500

    def test_advice_after_anomaly_resets_the_counter(self, tmp_path, monkeypatch):
        """A clean round clears the anomaly streak — the cap counts consecutive
        anomalies, not lifetime ones."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"phase": ADVISING, "advice_history": [], "anomalies": 1},
            advice="fresh advice",
            narration="round work",
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["advice_history"] == ["fresh advice"]
        assert ledger["anomalies"] == 0
        assert ledger["phase"] == ADVISING

    def test_second_anomaly_of_any_kind_ends(self, tmp_path, monkeypatch, capsys):
        """One counter, not two per type: a decline at anomalies=1 (from a prior
        malfunction) reaches the cap and ends — no per-type cross-reset, so
        alternating anomaly kinds can't dodge the cap forever."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"phase": ADVISING, "advice_history": ["r"], "anomalies": 1},
        )
        (tmp_path / "s1_advisor_token").write_text("")  # not consumed -> decline
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        assert not (tmp_path / "s1_active").exists()  # ended at the 2nd anomaly
        assert "advisor loop has ended" in capsys.readouterr().err

    def test_read_failure_freezes_round_start_line(self, tmp_path, monkeypatch):
        """An unreadable transcript at a stop must not reset round_start_line to
        1 — that would make the next round slice the whole session.  Freeze it
        instead (the round's own slice degrades to empty; wider never happens)."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={
                "phase": ADVISING,
                "advice_history": ["r"],
                "round_start_line": 200,
            },
            advice="more",  # advice present -> reaches the bottom save
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

    def test_compacted_round_inlines_anchor_text(self, tmp_path, monkeypatch, capsys):
        """Mechanism 2: a compacted round re-injects the anchor text into
        the trigger and consumes the marker."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"phase": ADVISING, "advice_history": []},
            advice="some advice",
        )
        (tmp_path / "s1_compacted").touch()
        with pytest.raises(SystemExit):
            stop()
        err = capsys.readouterr().err
        assert "build the thing" in err  # anchor text inlined
        assert not (tmp_path / "s1_compacted").exists()  # consumed

    def test_termination_token_converges_and_triggers_recap(
        self, tmp_path, monkeypatch, capsys
    ):
        """Termination on a turn that surfaced advice: phase -> converged and
        deactivated, the final round completed in the log (its narration + the
        advice it answered; the token is machinery and never logged), and one last
        injection has the main agent report the end and recap the round log."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"phase": ADVISING, "advice_history": ["r"]},
            advice=f"All paths covered. {TERMINATION_TOKEN}",
            narration="final round work",
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["phase"] == CONVERGED  # finished — /ploop:on won't resume
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
        assert "candidates" not in err  # empty queue: no drain directive

    def test_no_round_cap_arms_indefinitely(self, tmp_path, monkeypatch):
        """There is no round limit: a long history still arms the next round rather
        than terminating — only the advisor (or an anomaly failsafe) ends the loop;
        /ploop:off merely pauses it."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"phase": ADVISING, "advice_history": ["r"] * 999},
            advice="still more",
            narration="work",
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2  # armed, not terminated
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["phase"] == ADVISING
        assert len(ledger["advice_history"]) == 1000  # recorded the 1000th advice
        assert (tmp_path / "s1_active").exists()

    def test_running_marker_pauses_without_retrigger(self, tmp_path, monkeypatch):
        """Running marker present (advisor in flight — e.g. the user pushed it to the
        background): allow the stop, don't re-trigger — no cascade.  SubagentStop is
        the marker's sole clearer, so the loop just waits for it."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"phase": ADVISING, "advice_history": []},
        )
        (tmp_path / "s1_advisor_running").touch()
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 0
        # ledger untouched, marker left in place — the loop just waits
        assert load_ledger(tmp_path / "s1_loop.json")["phase"] == ADVISING
        assert (tmp_path / "s1_advisor_running").exists()

    def test_inflight_background_subagent_waits(self, tmp_path, monkeypatch):
        """The harness stops the session with delegated background work still in
        flight, reporting it in background_tasks: a subagent or workflow entry
        means the round is not done — allow the stop, don't trigger the advisor."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
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
        # ledger untouched, no advisor armed — the loop just waits for the wake-up
        assert load_ledger(tmp_path / "s1_loop.json")["phase"] == ADVISING
        assert not (tmp_path / "s1_advisor_token").exists()

    def test_background_shell_nags_once_then_waits(self, tmp_path, monkeypatch, capsys):
        """A shell-only background holds the round open: the first stop gets one
        redirect notice (wait, or move an ambient process off the shell lane) and
        no advisor; a repeat stop with the same shell set waits silently; a new
        shell id nags again."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"phase": ADVISING, "advice_history": []},
        )
        shell_stdin = lambda ids: make_stdin(  # noqa: E731
            transcript_path=str(tmp_path / "s1.jsonl"),
            background_tasks=[
                {"id": i, "type": "shell", "status": "running"} for i in ids
            ],
        )
        arrange(tmp_path, monkeypatch, shell_stdin(["t1"]))
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        assert "Background shell" in capsys.readouterr().err
        assert not (tmp_path / "s1_advisor_token").exists()
        assert load_ledger(tmp_path / "s1_loop.json")["phase"] == ADVISING

        arrange(tmp_path, monkeypatch, shell_stdin(["t1"]))
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 0  # same set: the loop waits for the exit wake

        arrange(tmp_path, monkeypatch, shell_stdin(["t1", "t9"]))
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2  # a new shell id gets its own redirect
        assert "Background shell" in capsys.readouterr().err

    def test_monitor_only_background_arms_advisor(self, tmp_path, monkeypatch, capsys):
        """Monitor is the ambient, session-lifetime lane and never gates: a stop
        with only monitors left is a legitimate round end — the advisor arms and
        a stale shell-redirect marker is cleared."""
        arrange_anchor(tmp_path, monkeypatch, ROUND_WORK, ledger={"phase": FRESH})
        (tmp_path / "s1_gated_shells").write_text("t1")
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
        assert not (tmp_path / "s1_gated_shells").exists()

    def test_first_decline_redirects_to_advisor_authority(
        self, tmp_path, monkeypatch, capsys
    ):
        """Advisor NOT invoked this round (token still present): don't re-append a
        prior round's advice as a duplicate, even if a stale advice file lingers.
        The trigger is re-injected behind the authority notice — only the advisor
        may end the loop, and the refusal turn is in the round's transcript slice,
        so the narrator routes its stated reasons to the advisor's verdict; no
        main-side exit is advertised."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"phase": ADVISING, "advice_history": ["prior advice"]},
            advice="prior advice",
        )
        (tmp_path / "s1_advisor_token").write_text("")
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["advice_history"] == ["prior advice"]  # not duplicated
        assert ledger["phase"] == ADVISING
        assert ledger["anomalies"] == 1
        err = capsys.readouterr().err
        # the re-injected trigger points the narrator at the refusal round slice
        assert "round:" in err
        assert "working on the advice" in (tmp_path / "s1_round.jsonl").read_text()
        assert "authority to end the loop belongs to the advisor" in err
        assert "EXACTLY as written" in err  # the trigger follows the notice
        assert "loop will end" not in err  # no main-side exit advertised

    def test_second_consecutive_decline_trips_failsafe_and_ends_loop(
        self, tmp_path, monkeypatch, capsys
    ):
        """A second stop in a row without invoking the advisor means the
        consensus channel itself is broken — the failsafe ends the loop with
        that honest cause instead of stalemating against the harness
        stop-block cap.  The cause names no actor: an unconsumed token may
        equally come from a refusal or from turns the user cut short."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"phase": ADVISING, "advice_history": ["r"], "anomalies": 1},
        )
        (tmp_path / "s1_advisor_token").write_text("")
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        ledger = load_ledger(tmp_path / "s1_loop.json")
        # an anomaly halt is not a finished anchor — /ploop:on can wake it
        assert ledger["phase"] == ADVISING
        assert ledger["advice_history"] == ["r"]
        assert not (tmp_path / "s1_active").exists()
        err = capsys.readouterr().err
        assert "advisor loop has ended" in err
        assert "uninvoked" in err

    def test_pending_candidates_surface_to_advisor(self, tmp_path, monkeypatch, capsys):
        """A non-empty candidates queue reaches the advisor as a conditional
        prompt line — the hook decides emptiness in code — and the main-owned
        file survives the arm (rounds accumulate into it, only launch clears)."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"phase": ADVISING, "advice_history": []},
            advice="keep going",
            narration="worked",
        )
        (tmp_path / "ploop_s1_candidates.md").write_text("fact: X — measured via Y")
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "uncovered region" in err  # the advisor-facing conditional line
        assert str(tmp_path / "ploop_s1_candidates.md") in err
        assert (tmp_path / "ploop_s1_candidates.md").exists()

    def test_end_notice_directs_candidates_drain(self, tmp_path, monkeypatch, capsys):
        """An automatic end with entries still queued appends the drain
        directive — end_loop is the single point, so every auto-termination
        path carries it — and the queue file survives the end."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"phase": ADVISING, "advice_history": ["r"]},
            advice=f"All covered. {TERMINATION_TOKEN}",
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

    def test_compliance_resets_the_anomaly_counter(self, tmp_path, monkeypatch):
        """Invoking the advisor after a decline clears the streak — the cap
        counts consecutive anomalies, not lifetime ones."""
        arrange_anchor(
            tmp_path,
            monkeypatch,
            ROUND_WORK,
            ledger={"phase": ADVISING, "advice_history": ["r"], "anomalies": 1},
            advice="new advice",
            narration="complied and worked",
        )
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["anomalies"] == 0
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
        """Outside an active anchor the advisor gate does not interfere."""
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
        re-trigger a second advisor."""
        (tmp_path / "s1_advisor_running").touch()
        arrange(
            tmp_path,
            monkeypatch,
            json.dumps({"session_id": "s1", "agent_type": "my-advisor-x"}),
        )
        with pytest.raises(SystemExit):
            subagent_stop()
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

    def test_writes_stripped_anchor_and_arms_loop(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
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
        assert not (tmp_path / "s1_loop.json").exists()  # prior ledger cleared
        # an anchor owns one log, opened with its own text
        log = (tmp_path / "s1_loop.log").read_text()
        assert log.startswith("[[ ANCHOR ]]\n\n")
        assert saved in log
        assert "prior anchor log" not in log

    def test_array_command_args_join_verbatim(self, tmp_path, monkeypatch):
        """The reference schema types command_args as an array while observed
        events carry a string — both shapes must yield the anchor verbatim,
        or a harness update corrupts the anchor."""
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
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
        (ledger, advice-history) is PRESERVED so /ploop:on can resume from here.
        No end notice is emitted; the static skill body carries the quiet notice."""
        for name in ("s1_active", "s1_advisor_running", "s1_advisor_token"):
            (tmp_path / name).touch()
        save_ledger(
            tmp_path / "s1_loop.json",
            {"phase": ADVISING, "advice_history": ["r"]},
        )
        (tmp_path / "s1_advice_history.md").write_text("<advice-1>\n\nr\n\n</advice-1>")
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
        arming point: phase reset to fresh (so the next stop skips recording a
        round no advisor ran) while advice-history and round_start_line are
        PRESERVED by the merge, and the stale handoff/gate transients are cleared
        so the first resumed stop arms cleanly."""
        self.arrange_paused(
            tmp_path,
            ledger={
                "phase": ADVISING,
                "advice_history": ["a", "b"],
                "round_start_line": 842,
            },
        )
        for name in (
            "s1_advisor_token",
            "s1_advisor_running",
            "ploop_s1_advice.md",
            "ploop_s1_narration.md",
        ):
            (tmp_path / name).touch()
        monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
        self.arrange(tmp_path, monkeypatch)
        on_command()
        assert (tmp_path / "s1_active").exists()  # re-armed
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["phase"] == FRESH  # the next stop skips recording
        assert ledger["advice_history"] == ["a", "b"]  # preserved
        assert ledger["round_start_line"] == 842  # preserved
        # stale transients cleared so the first resumed stop arms cleanly
        assert not (tmp_path / "s1_advisor_token").exists()
        assert not (tmp_path / "s1_advisor_running").exists()
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
        deliberately finished, a genuine completion, not a stall. on refuses it;
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

    def test_resume_then_stop_arms_advisor(self, tmp_path, monkeypatch, capsys):
        """The resume guarantee, end to end: after /ploop:on, the very next stop
        arms an advisor round (exit 2) without malfunctioning or double-recording —
        the fresh phase makes it skip recording a round no advisor ran, and the
        preserved advice-history is re-emitted intact."""
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
        # now drive the next main-session stop
        main = tmp_path / "s1.jsonl"
        write_jsonl(main, ROUND_WORK)
        arrange(tmp_path, monkeypatch, make_stdin(transcript_path=str(main)))
        with pytest.raises(SystemExit) as exc:
            stop()
        assert exc.value.code == 2  # armed, not passed or terminated
        ledger = load_ledger(tmp_path / "s1_loop.json")
        assert ledger["phase"] == ADVISING  # advanced from the reset fresh
        assert ledger["advice_history"] == ["a", "b"]  # preserved, not duplicated
        assert (tmp_path / "s1_advisor_token").exists()  # a fresh round armed
        err = capsys.readouterr().err
        assert "ploop:advisor" in err  # the advisor trigger was injected
        assert "malfunctioned" not in err  # not mistaken for an empty advisor run


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


# ── write_log ──


class TestWriteLog:
    def test_round_zero_has_no_advice_section(self, tmp_path):
        log = tmp_path / "l.log"
        write_log(log, 0, "anchor work", None)
        content = log.read_text()
        assert "[[ Round 0 - " in content
        assert "anchor work" in content
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
