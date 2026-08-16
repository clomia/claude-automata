"""Main — ploop hook entry points (one per hooks.json event).

A hook is code and cannot call tools, so the loop is driven by feedback: stop()
blocks the main agent's stop (exit 2) and injects the standing round directive —
narrate the finished round, keep working, or convene the advisor.  The advisor
is the completion gate: only its verdict certifies completion.  The active
marker written at /ploop:launch gates everything.

The loop ENDS through auto-termination — the advisor writes the completion
token or the deadline-closure token (phase -> converged), or two consecutive
anomalies trip the cap (a bare stop that left the directive unanswered, or an
advisor run that wrote no report) — and every such end has the main agent recap the loop log
(format_end_notice); that exposed end behavior is left untouched.  A working
stop is never an anomaly: the directive stands, the round advances, and the
main agent convenes the advisor on its own judgment.
The user PAUSES and RESUMES the loop with /ploop:off and /ploop:on: off drops
the active gate quietly so the next stop passes (exit 0, the round state
preserved for resume), on re-arms it so the next stop presents the directive
(exit 2).  off is the quiet counterpart to auto-termination — no end recap.

Prompt submission is otherwise a non-event for ploop — no hook fires on a typed
user turn, task notification, or scheduled wakeup, so they all pass through an
armed loop untouched.  An ESC only cuts the turn (no hook fires on an interrupt
either): the loop stays armed and resumes at the next stop, so the way to pause
a running loop is ESC, then /ploop:off.  Both loop participants are unreliable
LLMs, so the first anomaly gets a corrective repeat (an empty advisor run is
retried; a bare stop is redirected to the advisor's authority, and that notice
is the one place the silent exit is disclosed) and a second consecutive anomaly
ends the loop.  See ARCHITECTURE.md for the loop design.

Hooks must never break the session: malformed events and missing files degrade
to exit 0 (allow the action).
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.prompt import (
    deadline_status,
    format_advice_history,
    format_candidates_notice,
    format_directive,
    format_end_notice,
)
from src.state import (
    ADVISING,
    CONVERGED,
    FRESH,
    Workspace,
    load_ledger,
    save_ledger,
)

# Sentinels the advisor writes to end the loop, each carrying its honest cause:
# certified completion, or a deadline-expiry closure (which must never be dressed
# as completion — decision 20).  Checked with `in` so the signal survives any
# surrounding prose the model emits alongside it.
COMPLETION_TOKEN = "MISSION_COMPLETE_ENDING_THE_TURN"
EXPIRY_TOKEN = "DEADLINE_EXPIRED_ENDING_THE_TURN"

# Anomaly cap: the first anomaly gets one corrective repeat (an empty advisor run
# is retried, a bare stop is redirected to the advisor's authority); a second
# CONSECUTIVE anomaly of any kind ends the loop with an honest cause, beating a
# stalemate against the harness stop-block cap.  One counter resets to 0 on an
# audit round or a working stop, so it can't be dodged by alternating anomaly
# types — and since the loop ends resumable (/ploop:on), ending one anomaly
# sooner costs nothing.  The silent exit this cap implements is the main agent's
# emergency stop; it ends the loop WITHOUT a completion verdict and is disclosed
# only in the decline notice — never in the standing directive.
MAX_ANOMALIES = 2

# A stop whose round added at most this many transcript lines did no tool work —
# a bare stop (the silence the failsafe exists for).  Measured on this machine
# (2.1.233, thinking on, 2026-08): text-only turns append 1-9 lines, the
# smallest tool-using turn appended 23 — the threshold sits between the bands
# with margin both ways.  Misjudging is mild in both directions: work read as
# bare costs one decline notice (the streak resets on the next working stop),
# bare read as work delays the failsafe by one round.  An observed dependency
# (audit-harness-deps): re-measure if transcript line granularity shifts.
BARE_STOP_LINE_THRESHOLD = 15

# Prefixes for anomalous re-arms.  The retry notice tells the main agent the
# advisor's empty run was a malfunction, not a verdict.  The decline notice
# upholds the authority split — only the advisor certifies completion — and is
# the single place the silent exit is disclosed: after a first unanswered
# directive the second silence must be an informed signal, not an ambush, while
# the steady-state directive keeps the audit as the only visible exit.  An
# unconsumed token also arises when the user cuts a turn short (ESC), so the
# notice — like the failsafe's end cause — names no actor.
RETRY_NOTICE = (
    "The previous advisor run malfunctioned: it ended without writing its "
    "report file, so it rendered no verdict. That run is void. Invoke the "
    "advisor again.\n\n"
)
DECLINE_NOTICE = (
    "The authority to certify completion belongs to the advisor. Invoke the "
    "advisor: it will read what was said this round and judge whether the "
    "mission is complete. If this directive goes unanswered again, the loop "
    "will end without a completion verdict, resumable with /ploop:on.\n\n"
)

# Heartbeat — the human supervision pattern, mechanized (decision 19).  Every
# stop of an armed loop leaves a 3h timer behind (an asyncRewake Stop hook:
# the process outlives context compaction, and its exit 2 wakes even an idle
# session — official as of 2026-08; first measured in
# docs/research/asyncrewake-stop-hook-2026.md).  A fresh nonce per stop
# supersedes every older timer, so the heartbeat fires only after 3h WITHOUT a
# stop: an actively cycling loop never hears it, and a loop parked by
# background work that can never finish is woken for the audit below instead
# of sleeping forever.  Should the harness ever stop delivering the wake,
# behavior degrades to the pre-heartbeat status quo — no new harm.
HEARTBEAT_SECONDS = 10800

HEARTBEAT_NOTICE = (
    "Heartbeat: 3 hours without a stop — this session has likely been asleep. "
    "Audit everything alive in the background: kill what can never finish (a "
    "wait on a dead producer, an orphaned process); relaunch bounded (`timeout "
    "N`) if still needed. Then continue the anchor, or stop again to keep "
    "waiting.\n"
)


# ploop depends on non-obvious Claude Code settings, and a Claude Code release
# can flip a default out from under them — the nested-subagent default moved
# 5 (2.1.172) -> 1 (2.1.217) -> 3 (2.1.219) across three releases.  launch
# asserts each required setting and, if any is unmet, refuses to arm and names
# the settings.json fix, so a user who just updated Claude Code gets a fix list,
# not a silently degraded loop.  The depth pin is an environment contract for
# orchestration (mission workers delegate in trees), not a loop-machinery
# requirement — the loop itself closes at depth 1.  Harness capabilities
# themselves (e.g. asyncRewake) are not asserted: claude-automata assumes an
# auto-updated Claude Code (root canon, 결정 기록).  Extend the tuple in
# unmet_prerequisites as Claude Code changes require.
SPAWN_DEPTH_ENV = "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"
SPAWN_DEPTH_MIN = 5
PREREQUISITE_HEADER = (
    "ploop requires these .claude/settings.json settings — set them, then "
    "restart Claude Code:"
)
NESTED_FIX = '"env": {"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "5"}'
COMPACT_FIX = '"autoCompactEnabled": true'
THINKING_FIX = '"alwaysThinkingEnabled": true'


def read_event() -> dict:
    """Parse the hook event from stdin; malformed input or a read error allows
    the action (exit 0), so a hook never breaks the session."""
    try:
        return json.loads(sys.stdin.read())
    except json.JSONDecodeError, OSError:
        sys.exit(0)


def project_dir(event: dict) -> str:
    """The directory this loop belongs to — hooks get CLAUDE_PROJECT_DIR in
    their environment; the event's cwd and the process cwd are the fallbacks."""
    for value in (os.environ.get("CLAUDE_PROJECT_DIR"), event.get("cwd")):
        if isinstance(value, str) and value.strip():
            return value.strip().rstrip("/") or "/"
    return str(Path.cwd())


def deliver_expansion_context(text: str) -> None:
    """Ride the expanded skill body with additionalContext (UserPromptExpansion).

    The hook's only channel into the launch turn itself: the text lands alongside
    the submitted prompt, so a reference the skill body makes resolves in the same
    turn instead of waiting for the first stop.  Mutually exclusive with
    block_expansion — a blocked turn is erased and carries only its reason.
    """
    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptExpansion",
                    "additionalContext": text,
                }
            }
        )
    )


def block_expansion(reason: str) -> None:
    """Deny a slash-command expansion (decision: block).

    The turn is erased before submission: the skill body never enters context,
    the reason is shown to the user only, and no state is touched — a live loop
    survives its own guard.
    """
    sys.stdout.write(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


def project_settings(event: dict) -> dict:
    """The project .claude/settings.json as a dict; unreadable/malformed -> {}.

    The launch assertion reads (never writes) it to check the compaction and
    thinking toggles, which have no runtime signal a hook could read instead.
    """
    try:
        return json.loads(
            (Path(project_dir(event)) / ".claude" / "settings.json").read_text()
        )
    except OSError, json.JSONDecodeError:
        return {}


def unmet_prerequisites(event: dict) -> list[str]:
    """ploop's Claude Code prerequisites the environment fails to satisfy.

    Each entry is a settings.json fix line; empty means all are met.  Nested-
    subagent depth is read from os.environ — the effective value, so a settings.json
    edit not yet applied by a restart still reads as unmet (the restart is what makes
    the env var take hold, which a declared settings.json read would miss).  The
    compaction and thinking toggles have no such runtime signal, so they are read
    from the project settings.json.  Extend the tuple to assert a new setting.
    """
    settings = project_settings(event)
    try:
        depth = int(os.environ.get(SPAWN_DEPTH_ENV, ""))
    except ValueError:
        depth = 0
    return [
        fix
        for ok, fix in (
            (depth >= SPAWN_DEPTH_MIN, NESTED_FIX),
            (settings.get("autoCompactEnabled") is True, COMPACT_FIX),
            (settings.get("alwaysThinkingEnabled") is True, THINKING_FIX),
        )
        if not ok
    ]


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_round_entry(log_path: Path, round_number: int, narration: str) -> None:
    """Append one round's narration to the loop log (the flight recorder).

    Rounds are stop-to-stop time slices; a round's narration is produced by the
    narrator the main agent runs at the start of the NEXT round, so each entry
    lands one stop behind the round it narrates.  launch() starts the file with
    the anchor text; the finished log outlives the anchor so the whole turn
    stays reconstructable after any compaction.
    """
    with open(log_path, "a") as f:
        f.write(f"[[ Round {round_number} - {timestamp()} ]]\n\n{narration}\n\n")


def write_audit_entry(log_path: Path, audit_number: int, report: str) -> None:
    """Append one audit report to the loop log, verbatim.

    Appended at the stop that reads it, one position ahead of the narration of
    the round that convened it — the report opens with its own findings and the
    following round's narration describes the response, so the skew reads
    cleanly without buffering.  The completion token is machinery and never
    enters the log.
    """
    with open(log_path, "a") as f:
        f.write(f"[[ Audit {audit_number} - {timestamp()} ]]\n\n{report}\n\n")


def candidates_pending(ws: Workspace) -> bool:
    """True iff the candidates queue holds anything.

    Emptiness is decided here in code — the advisor prompt names the queue only
    on True, so a loop that never queues candidates keeps its advisor prompt
    free of the promotion domain; any read failure counts as empty (a hook
    never breaks the session).
    """
    try:
        return (
            ws.candidates_path.exists() and ws.candidates_path.read_text().strip() != ""
        )
    except OSError, UnicodeDecodeError:
        return False


def end_loop(ws: Workspace, ledger: dict, cause: str, *, converged: bool) -> None:
    """Terminate the loop: drop the active gate and inject the end notice — the
    main agent reports the end and its cause to the user, with a recap of the
    loop log (the one complete record) and a candidates-drain directive when the
    queue still holds entries.

    Every automatic exit lands here with an honest cause — the advisor's
    completion verdict, or a second consecutive anomaly; there is no round cap.
    converged sets the phase: CONVERGED marks the anchor FINISHED (the advisor
    certified completion — /ploop:on refuses it), while an anomaly end stays
    ADVISING (an unfinished anchor /ploop:on can resume) and is never dressed as
    completion — the silent exit ends the loop without a verdict.  Everything
    else in the ledger is preserved by the merge — round_start_line included, so
    a resumed anomaly end keeps the real slice offset.  The active marker is
    dropped, so the next stop passes.
    """
    save_ledger(
        ws.ledger_path, {**ledger, "phase": CONVERGED if converged else ADVISING}
    )
    ws.active_path.unlink(missing_ok=True)
    sys.stderr.write(
        format_end_notice(
            cause,
            log_path=ws.log_path if ws.log_path.exists() else None,
            candidates_path=ws.candidates_path if candidates_pending(ws) else None,
        )
    )
    sys.exit(2)


def read_transcript_lines(transcript_path: str) -> list[str]:
    """The transcript's lines (append-only, so line numbers stay valid).

    Unreadable → empty, so the round slice is empty and the narrator reports no
    actions — graceful, never a crash.
    """
    try:
        with open(transcript_path) as f:
            return f.readlines()
    except OSError:
        return []


def write_round_slice(lines: list[str], round_start: int, out_path: Path) -> None:
    """Cut this round's own lines [round_start .. end] into out_path for the narrator.

    A pure line range, no message parsing: round_start is where the round began
    and the transcript end is this stop (the next directive has not been appended
    yet), so the slice is exactly the round.  The narrator analyzes the whole
    file — no offsets, no boundary-finding.
    """
    out_path.write_text("".join(lines[round_start - 1 :]))


def arm_round(
    ws: Workspace,
    *,
    lines: list[str],
    round_start: int,
    notice: str = "",
) -> None:
    """Arm the next round and end the hook (exit 2).

    Consumes any compaction marker (mechanism 2: the directive inlines the anchor
    text), cuts this round's transcript slice into round_path for the narrator,
    clears both handoff channels so an absent file at the next stop unambiguously
    means its agent wrote nothing, sets the single-use audit token, and injects
    the standing directive — prefixed by `notice` on an anomalous re-arm.
    """
    try:
        full_anchor = ws.anchor_path.read_text()
    except OSError:
        full_anchor = ""
    anchor_text = None
    if ws.compacted_path.exists():
        anchor_text = full_anchor or None
        ws.compacted_path.unlink(missing_ok=True)

    write_round_slice(lines, round_start, ws.round_path)
    directive = format_directive(
        anchor_path=ws.anchor_path,
        round_path=ws.round_path,
        log_path=ws.log_path,
        advice_history_path=ws.advice_history_path,
        advice_path=ws.advice_path,
        narration_path=ws.narration_path,
        candidates_path=ws.candidates_path,
        candidates_pending=candidates_pending(ws),
        anchor_text=anchor_text,
        deadline=deadline_status(full_anchor, datetime.now().astimezone()),
    )
    ws.advice_path.unlink(missing_ok=True)
    ws.narration_path.unlink(missing_ok=True)
    ws.advisor_token_path.write_text("")
    sys.stderr.write(notice + directive)
    sys.exit(2)


def stop() -> None:
    """Stop hook: record the flight, judge the round, then end the loop or arm the next.

    Fires on every main-session stop; the active marker gates it (a converged or
    paused loop has no active marker, so it just passes).  The phase gates the
    judging: only an "advising" round has anything to read — the first stop after
    a launch or resume ("fresh") arms without judging, and its absent token must
    not read as consumed.  Per advising stop, in order: the narration the main
    agent produced for the previous round is appended to the loop log (the
    flight recorder); then advice.md — the advisor's sole output channel — is
    read, and honored only when the audit token was consumed (an unwritten-by-
    the-advisor report is no verdict): a report becomes an audit-history entry
    and a log entry, and only an explicit token — completion, or deadline
    closure — ends the loop (phase -> converged).  The token state splits the
    rest three ways: consumed with no report is a
    malfunctioned advisor run (the protocol demands a Write even to certify),
    retried behind the retry notice; unconsumed with real transcript growth is a
    WORKING stop — the normal case, no anomaly, the directive simply stands
    again; unconsumed with no growth is a bare stop — an unanswered directive —
    re-armed once behind the authority notice (which discloses the silent exit),
    with a second consecutive anomaly of any kind ending the loop as the
    emergency stop.  Arming injects the standing directive via exit 2.
    """
    event = read_event()
    ws = Workspace.from_env(event.get("session_id", ""))

    if not ws.active_path.exists():
        sys.exit(0)

    # Loops launched before provenance recording converge here: every stop of
    # an active loop backfills the launch directory docent scopes by.
    if not ws.project_path.exists():
        ws.project_path.write_text(project_dir(event))

    # The directive is presented only when foreground AND background are both
    # empty.  Foreground-empty is this very Stop; background-empty is read from
    # the official `background_tasks` input (present whenever the task registry
    # is reachable; absent from the docs page but alive in the 2.1.233 bundle —
    # observed 2026-08).  Gate exactly the types whose completion is guaranteed
    # to wake the session: subagent, workflow, and running shell all wait
    # silently.  Every other type (Monitor included, the never-gated
    # session-lifetime lane), a shell past running, and an unreachable registry
    # pass: stalling the loop is worse than an early directive.  Any sleep this
    # gate allows is bounded by the heartbeat (decision 19).
    tasks = [t for t in event.get("background_tasks") or [] if isinstance(t, dict)]
    if any(t.get("type") in ("subagent", "workflow") for t in tasks):
        sys.exit(0)
    if any(
        t.get("type") == "shell" and t.get("status", "running") == "running"
        for t in tasks
    ):
        sys.exit(0)

    ledger = load_ledger(ws.ledger_path)
    phase = ledger["phase"]
    advice_history = ledger["advice_history"]
    anomalies = ledger["anomalies"]
    round_number = ledger["round"]
    # Start line of the round ending at this stop — the narrator's slice begins
    # here.  A "fresh" launch/resume round covers the work so far (defaults to 1).
    round_start = ledger["round_start_line"]
    lines = read_transcript_lines(event.get("transcript_path", ""))

    # An advisor is still in flight (PreToolUse set the marker; SubagentStop, its
    # sole clearer, hasn't fired): re-arming would cascade a second advisor,
    # so wait — the loop resumes when the advisor stops.
    if ws.advisor_running_path.exists():
        sys.exit(0)

    notice = ""
    if phase == ADVISING:
        # Flight recorder first: the narration of the previous round, produced
        # by the narrator the main agent ran this round.  Absent means the relay
        # was skipped — the round goes unnarrated (degrade, not an anomaly).
        narration = (
            ws.narration_path.read_text().strip() if ws.narration_path.exists() else ""
        )
        if narration:
            write_round_entry(ws.log_path, round_number - 1, narration)

        # The advisor ran this round iff PreToolUse consumed the token this
        # stop's predecessor wrote — and ONLY a run the gate admitted can render
        # a verdict: the directive exposes the report path, so a report sitting
        # there with the token unconsumed was not written by the advisor (the
        # main agent, or a worker, wrote it) and self-certification must not
        # pass the gate.  Such a file is ignored and cleared at the arm.  Past
        # the in-flight guard the advisor has finished, so token-consumed with
        # an absent report means it wrote nothing — a malfunction, not a
        # verdict.
        advisor_invoked = not ws.advisor_token_path.exists()
        advice = ws.advice_path.read_text().strip() if ws.advice_path.exists() else ""
        if advisor_invoked and advice:
            if COMPLETION_TOKEN in advice:
                end_loop(
                    ws,
                    ledger,
                    "the advisor confirmed the mission complete",
                    converged=True,
                )
            if EXPIRY_TOKEN in advice:
                end_loop(
                    ws,
                    ledger,
                    "the deadline expired — the advisor closed the mission",
                    converged=True,
                )
            advice_history = [*advice_history, advice]
            write_audit_entry(ws.log_path, len(advice_history), advice)
            anomalies = 0
        elif advisor_invoked:  # a malfunction: ran, wrote nothing
            anomalies += 1
            if anomalies >= MAX_ANOMALIES:
                end_loop(
                    ws,
                    ledger,
                    "two consecutive anomalous rounds (in this one the advisor"
                    " finished without writing its report)",
                    converged=False,
                )
            notice = RETRY_NOTICE
        else:
            # No audit this round.  Real transcript growth = a working stop —
            # the normal case; no growth = a bare stop, the unanswered
            # directive the failsafe exists for.  An unreadable transcript
            # can't be judged and counts as working (fail toward patience).
            delta = len(lines) - round_start + 1
            if lines and delta <= BARE_STOP_LINE_THRESHOLD:
                anomalies += 1
                if anomalies >= MAX_ANOMALIES:
                    end_loop(
                        ws,
                        ledger,
                        "two unanswered audit directives — no completion"
                        " verdict was issued",
                        converged=False,
                    )
                notice = DECLINE_NOTICE
            else:
                anomalies = 0

    # Arm the next round.  arm_round cuts the just-completed round
    # [round_start .. end] into round_path for the narrator — a contiguous slice
    # no interjection can truncate.  The next round starts just past the current
    # transcript end (this stop's directive has not been injected yet), so record
    # that as its start line — but only when the transcript actually read (else
    # freeze it, or an empty read would reset the offset to 1 and slice the whole
    # session).
    ws.advice_history_path.write_text(format_advice_history(advice_history))
    save_ledger(
        ws.ledger_path,
        {
            **ledger,
            "phase": ADVISING,
            "advice_history": advice_history,
            "anomalies": anomalies,
            "round": round_number + 1,
            "round_start_line": len(lines) + 1 if lines else round_start,
        },
    )
    arm_round(ws, lines=lines, round_start=round_start, notice=notice)


def pre_tool_use() -> None:
    """PreToolUse hook (matcher: Agent): gate the main agent's advisor invocation.

    Allow an Agent(ploop:advisor) call only when the single-use audit token a
    Stop hook armed is present — consuming it and marking the advisor in flight,
    so a stop while it runs (e.g. pushed to the background) won't re-arm.  The
    token authorizes one audit per round; a second call in the same round, or a
    call before the first directive armed, is denied so the channel stays clean.
    Outside an active loop the gate stays out of the way.  The match is exact —
    ploop:advisor is the registered scoped name the directive spells out — so a
    delegated worker whose type merely contains "advisor" is neither denied nor
    allowed to consume the token.
    """
    event = read_event()
    tool_input = event.get("tool_input") or {}
    subagent_type = (
        tool_input.get("subagent_type", "") if isinstance(tool_input, dict) else ""
    )
    if subagent_type != "ploop:advisor":
        sys.exit(0)
    ws = Workspace.from_env(event.get("session_id", ""))
    if not ws.active_path.exists():
        sys.exit(0)
    if ws.advisor_token_path.exists():
        ws.advisor_token_path.unlink()
        ws.advisor_running_path.touch()
        sys.exit(0)
    sys.stderr.write(
        "The advisor cannot be convened now: one audit per round, authorized "
        "by the round directive."
    )
    sys.exit(2)


def heartbeat_arm() -> None:
    """First phase of the heartbeat timer: arm the silence watch, or decline.

    Runs briefly under the wrapper's heartbeat branch, which owns the 3h
    residency itself (sleeping python-under-uv would keep uv resident for the
    whole interval).  For an armed loop this records a fresh nonce —
    superseding every older timer — and prints the wrapper's handoff line
    ("session nonce seconds"); outside an armed loop it prints nothing, and
    the wrapper stands down without sleeping.
    """
    event = read_event()
    ws = Workspace.from_env(event.get("session_id", ""))
    if not ws.active_path.exists():
        sys.exit(0)
    nonce = uuid.uuid4().hex
    ws.heartbeat_nonce_path.write_text(nonce)
    sys.stdout.write(f"{ws.session_id} {nonce} {HEARTBEAT_SECONDS}")


def heartbeat_fire() -> None:
    """Second phase of the heartbeat timer: wake the session or stand down.

    Runs HEARTBEAT_SECONDS after the stop that armed it.  Stands down (exit 0)
    when the loop ended or paused (active marker gone) or a later stop wrote a
    newer nonce — that stop's own timer owns the watch.  Otherwise the session
    was silent for the whole interval: exit 2 delivers HEARTBEAT_NOTICE as the
    wake (asyncRewake), and the audit turn's own stop arms the next timer.
    """
    if len(sys.argv) < 3:
        sys.exit(0)
    session_id, nonce = sys.argv[1], sys.argv[2]
    ws = Workspace.from_env(session_id)
    try:
        current = ws.heartbeat_nonce_path.read_text()
    except OSError:
        sys.exit(0)
    if not ws.active_path.exists() or current != nonce:
        sys.exit(0)
    sys.stderr.write(HEARTBEAT_NOTICE)
    sys.exit(2)


def mark_compaction() -> None:
    """PostCompact hook: mark the compaction.

    The next stop() re-injects the anchor text into its directive (mechanism 2)
    and consumes the marker; a marker left by a non-anchor compaction is cleared
    when the next anchor launches.
    """
    event = read_event()
    Workspace.from_env(event.get("session_id", "")).compacted_path.touch()


def subagent_stop() -> None:
    """SubagentStop hook: the sole clearer of the advisor-running marker.

    Paired with PreToolUse setting it, the marker tells stop() an advisor is
    still in flight; narrator and other subagent stops are ignored.  The stop
    payload has been observed carrying the bare agent name as well as the
    scoped one, so both forms clear the marker — a missed clear would strand
    the in-flight marker and stall the loop; a merely-containing name (a
    delegated worker) must not clear it, or the next stop re-arms a second
    advisor.
    """
    event = read_event()
    agent_type = str(event.get("agent_type") or event.get("subagent_type") or "")
    if agent_type not in ("advisor", "ploop:advisor"):
        sys.exit(0)
    Workspace.from_env(event.get("session_id", "")).advisor_running_path.unlink(
        missing_ok=True
    )


def launch() -> None:
    """UserPromptExpansion hook (matcher: ploop:launch): the whole launch prep.

    Fires when /ploop:launch <anchor> expands.  The anchor rides in
    command_args as structured JSON, so multi-line text with quotes or `$` is
    captured verbatim.  Observed as a single string; the reference schema says
    an array of arguments — both shapes are accepted so a harness update
    cannot corrupt the anchor.

    Three guards block the expansion (block_expansion — pure, turn erased): an
    armed loop (active marker), because relaunching over it would overwrite the
    anchor and log mid-flight and orphan an in-flight advisor — /ploop:off
    pauses it first; a blank anchor, because the skill body would otherwise
    announce an activation this hook never armed (a ghost loop); and any unmet
    Claude Code prerequisite (unmet_prerequisites — nested subagents, auto
    compaction, thinking), since a loop launched without them silently degrades —
    the notice lists each settings.json fix and calls for a restart.

    A real launch clears the prior anchor's round state, starts the round log
    with the anchor text (an anchor owns one log, and its final summary reads
    the anchor first; the finished log survives ordinary turns), writes the
    anchor, records the launch directory (the provenance docent scopes its
    listing by), arms the loop, and delivers the candidates queue address into
    the launch turn.  The skill body directs candidates at that queue, so the
    address ships with the directive: an address that arrived only at the first
    stop would leave the opening round to invent its own, and every mechanism
    keyed to the real queue (the advisor's conditional line, the drain
    directive, the next launch's reset) would then be reading an empty file
    while the queue filled elsewhere — a divergence with no signal (decision 21).
    """
    event = read_event()
    if event.get("command_name", "") != "ploop:launch":
        sys.exit(0)
    ws = Workspace.from_env(event.get("session_id", ""))
    if ws.active_path.exists():
        block_expansion(
            "An advisor loop is already active. Pause it with /ploop:off, then launch again."
        )
    args = event.get("command_args", "")
    if isinstance(args, list):
        args = " ".join(str(a) for a in args)
    anchor = str(args).strip()
    if not anchor:
        block_expansion("The anchor is empty. Run it as /ploop:launch <anchor>.")
    if unmet := unmet_prerequisites(event):
        block_expansion(PREREQUISITE_HEADER + "\n\n" + "\n".join(unmet))
    ws.clear_round_state()
    ws.log_path.write_text(f"[[ ANCHOR ]]\n\n{anchor}\n\n")
    ws.anchor_path.write_text(anchor)
    ws.project_path.write_text(project_dir(event))
    ws.active_path.touch()
    deliver_expansion_context(format_candidates_notice(ws.candidates_path))


def off_command() -> None:
    """UserPromptExpansion hook (matcher: ploop:off): pause the loop on demand.

    off is the quiet pause half of the manual pause/resume pair (/ploop:on
    resumes).  Unlike auto-termination — the advisor's verdict or an anomaly
    failsafe, which END the loop and have the main agent recap the log, an
    exposed behavior this leaves untouched — off just drops the active gate so
    the next stop passes (exit 0) and no directive is presented, while the
    round state (ledger, audit-history, round_start_line) is preserved for
    /ploop:on to resume from.

    With no active loop (never launched, already off, or already ended) the
    expansion is blocked (block_expansion — pure, turn erased) so the skill body
    never announces a pause that didn't happen.  An active loop is paused: the
    active gate is dropped (the running marker too — the pause is unconditional,
    even with a background advisor in flight).  No end notice — the skill body
    carries the quiet, non-imperative notice; whether the main agent mentions it
    to the user is left to the main agent.
    """
    event = read_event()
    if event.get("command_name", "") != "ploop:off":
        sys.exit(0)
    ws = Workspace.from_env(event.get("session_id", ""))
    if not ws.active_path.exists():
        block_expansion("No active advisor loop to turn off.")
    ws.active_path.unlink(missing_ok=True)
    ws.advisor_running_path.unlink(missing_ok=True)


def on_command() -> None:
    """UserPromptExpansion hook (matcher: ploop:on): resume the loop.

    on is the universal wake/resume button.  It re-arms the loop so the next stop
    presents the round directive (exit 2), and it resumes the loop from ANY
    stalled state — paused by /ploop:off, ended by an anomaly failsafe, or stuck
    mid-round by an exception (an accidental ESC, an API error, a subscription
    session limit; most of these fire no hook, so they leave the loop active and
    touch no state) — so it is the one way to wake a long-running loop, even one
    still marked active.  The sole exception is a FINISHED anchor (done): the
    advisor certified completion, a genuine end rather than a stall, so on
    refuses it and the user launches a fresh anchor.

    A resume requires the on-disk anchor and log (else there is no loop to
    resume) and refuses a converged anchor (phase == converged); either failure
    blocks the expansion (block_expansion — pure, turn erased) so the
    skill body never announces a resume that didn't happen, and the user gets a
    clear reason.

    The resume normalizes the round state to a clean arming point regardless of
    how the loop stalled: the stale handoff/gate transients (token, running
    marker, report, narration) are cleared so the first resumed stop arms cleanly,
    and the ledger's phase is reset to fresh (so the next stop skips judging a
    round whose token was never armed) with the anomaly streak cleared, while
    audit-history and round_start_line are preserved by the merge (the resumed
    round's slice covers everything since the stall).  The skill body confirms
    the resume.
    """
    event = read_event()
    if event.get("command_name", "") != "ploop:on":
        sys.exit(0)
    ws = Workspace.from_env(event.get("session_id", ""))
    if not ws.anchor_path.exists() or not ws.log_path.exists():
        block_expansion(
            "No advisor loop to resume. Launch one with /ploop:launch <anchor>."
        )
    ledger = load_ledger(ws.ledger_path)
    if ledger["phase"] == CONVERGED:
        block_expansion(
            "The advisor concluded this anchor. Launch a new one with /ploop:launch <anchor>."
        )
    ws.advisor_token_path.unlink(missing_ok=True)
    ws.advisor_running_path.unlink(missing_ok=True)
    ws.advice_path.unlink(missing_ok=True)
    ws.narration_path.unlink(missing_ok=True)
    save_ledger(ws.ledger_path, {**ledger, "phase": FRESH, "anomalies": 0})
    ws.active_path.touch()
