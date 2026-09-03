"""Prompt — assemble the standing round directive and the loop notices.

Every stop of an armed loop injects one standing directive: narrate the finished
round (the narrator call, run by the main agent at depth 1), then judge the state
against the anchor — keep working, or convene the advisor when the mission reads
complete or an independent audit is wanted.  The advisor is the completion gate:
only its verdict certifies completion, and the directive spells both Agent calls
out verbatim so nothing is left for the LLM to construct.

The advisor reads five sections in canonical order:

    role (advisor system prompt)
    -> anchor           (anchor file)
    -> action-history   (loop log, then the freshest narration)
    -> audit-history    (advice-history file — prior audit reports)
    -> instructions     (static prompt file)

action-history is the flight recorder: the hook slices each round's own lines out
of the main transcript into a small file (round_path) and the narrator — invoked
by the main agent every round, not by the advisor — renders it into the loop log.
The slice is a pure line range [round_start .. end-of-transcript-at-this-stop],
so the hook does no message-format parsing and the loop carries no dependency on
the transcript's internal message shapes.  Accumulated narrations keep the audit
input bounded no matter how long the mission runs.
"""

import textwrap
from datetime import datetime
from pathlib import Path

INSTRUCTION_PATH = Path(__file__).resolve().parent.parent / "prompts" / "instruction.md"

# The one string that ties deadline_status (producer) to format_directive
# (consumer): an expired status opens with this prefix, and the directive's
# mandatory-audit branch keys on it.  A reworded status that forgot the
# consumer would silently reopen the keep-working branch past the deadline.
DEADLINE_EXPIRED_PREFIX = "expired"


def deadline_status(anchor: str, now: datetime) -> str:
    """anchor frontmatter의 deadline을 now 기준 status로 렌더링 — 미선언이면 "".

    frontmatter는 anchor 첫 줄의 `---`로 열려 다음 `---` 줄로 닫히는 block이고, 그
    안의 `deadline:` 값은 timezone 있는 ISO 8601이어야 읽힌다 — parse 불가나
    timezone 부재는 원문을 unreadable로 표면화한다(조용한 무장 해제는 거짓 안심이다).
    본문의 `deadline:`은 산문이다.  여기서는 시각 사실만 만든다 — 판단은 advisor
    몫이고, expired가 directive의 소집 의무화로 이어지는 것도 그 판단의 배달일 뿐이다
    (결정 20).
    """
    lines = anchor.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    body = lines[1:]
    closes = [i for i, line in enumerate(body) if line.strip() == "---"]
    if not closes:
        return ""  # 닫히지 않은 block은 frontmatter가 아니다
    value = None
    for line in body[: closes[0]]:
        key, sep, rest = line.partition(":")
        if sep and key.strip() == "deadline":
            value = rest.strip()
            break
    if value is None:
        return ""
    try:
        deadline = datetime.fromisoformat(value)
    except ValueError:
        deadline = None
    if deadline is None or deadline.tzinfo is None:
        return f"unreadable: {value[:40]}"
    seconds = (deadline - now).total_seconds()
    hours, minutes = divmod(int(abs(seconds) // 60), 60)
    span = f"{hours}h {minutes}m" if hours else f"{minutes}m"
    if seconds >= 0:
        return f"{span} remaining"
    return f"{DEADLINE_EXPIRED_PREFIX} {span} ago"


def format_candidates_notice(candidates_path: Path) -> str:
    """The queue's address, worded once.

    Both deliveries share this line: launch hands it over in the turn that arms the
    loop, every directive re-delivers it afterwards.  One wording, so the main agent
    never has two addresses to reconcile.
    """
    return f"Your candidates queue: {candidates_path}"


def format_anchor_notice(anchor: str, candidates_path: Path) -> str:
    """What re-enters the main context right after a compaction (mechanism 2):
    the anchor's full text and the queue address — the two launch deliveries a
    compaction can drop."""
    return (
        f"Your anchor — stay anchored to it:\n\n{anchor}\n\n"
        f"{format_candidates_notice(candidates_path)}"
    )


def format_advice_history(advice_history: list[str]) -> str:
    """Format prior audit reports as <audit-N> blocks (audit-history).

    Each block is one audit verbatim, so the advisor sees its own prior findings
    and never re-flags an item the main agent already answered or rebutted.
    """
    if not advice_history:
        return "No prior audits."
    return "\n\n".join(
        f"<audit-{i + 1}>\n\n{advice}\n\n</audit-{i + 1}>"
        for i, advice in enumerate(advice_history)
    )


def format_directive(
    *,
    anchor_path: Path,
    round_path: Path,
    log_path: Path,
    advice_history_path: Path,
    advice_path: Path,
    narration_path: Path,
    candidates_path: Path,
    candidates_pending: bool,
    instruction_path: Path = INSTRUCTION_PATH,
    deadline: str = "",
) -> str:
    """Build the standing directive every armed stop injects.

    The directive spells both Agent calls out verbatim — the hook authors the
    exact invocations and the main agent relays them as written, the simplest and
    most deterministic path.  The narrator call is unconditional (the flight
    recorder), the advisor call is the main agent's judgment: convene it on a
    completion claim or whenever an independent audit is wanted.  Only the
    advisor certifies completion — the silent-exit failsafe is disclosed only
    after a first unanswered directive (the decline notice), never here.

    Both calls are synchronous (run_in_background=false: the next action depends
    on each result).  The advisor Writes its report to advice_path — a clean file
    channel, since its chat message may carry reasoning prose — and reads the
    loop log plus the freshest narration as action-history, its own prior reports
    as audit-history.  A deadline surfaces to both participants from one status
    string: a header line for the main agent (convening is its decision, so the
    clock is its input too) and the same line inside the advisor prompt; an
    expired deadline closes the keep-working branch and makes convening the
    directive itself — judgment stays with the advisor.

    The candidates queue rides both directions: a standing line re-delivers the
    address to the main agent (launch delivers it first, the compaction
    re-anchoring restores it), and the advisor block names the queue only when
    candidates_pending — emptiness is decided here in code, so a loop that never
    queues candidates keeps its advisor prompt free of the promotion domain.
    """
    prefix = ""
    if deadline:
        prefix = f"deadline: {deadline}\n\n"
    deadline_line = ""
    if deadline:
        deadline_line = f"\n                deadline: {deadline}"
    candidates_line = ""
    if candidates_pending:
        candidates_line = (
            f"\n                candidates: {candidates_path} — facts and terms"
            " the main agent queued for promotion; an un-promoted remainder is"
            " unfinished work"
        )
    narrator_call = textwrap.dedent(f"""\
        ```
        Agent(
            subagent_type="ploop:narrator",
            description="narrate action history",
            run_in_background=false,
            prompt='
                round: {round_path}
                narration-path: {narration_path}
            '
        )
        ```
    """)
    advisor_call = textwrap.dedent(f'''\
        ```
        Agent(
            subagent_type="ploop:advisor",
            description="audit the mission",
            run_in_background=false,
            prompt="""
                anchor: {anchor_path}{deadline_line}
                action-history: {log_path} then {narration_path}
                audit-history: {advice_history_path}{candidates_line}
                instructions: {instruction_path}
                report-path: {advice_path}
            """
        )
        ```
    ''')
    if deadline.startswith(DEADLINE_EXPIRED_PREFIX):
        judge = (
            "2. The deadline has expired. Run the advisor call below NOW,"
            " EXACTLY as written — it judges the wrap-up:\n\n"
        )
    else:
        judge = (
            "2. Re-read your anchor and hold your state against it.\n"
            "   Work remains -> keep working now.\n\n"
            "3. ONLY when you judge the mission complete — or when you want an\n"
            "   independent audit — run the call below EXACTLY as written:\n\n"
        )
    body = (
        "1. Narrate the finished round — run the call below EXACTLY as written:\n\n"
        + narrator_call
        + "\n"
        + judge
        + advisor_call
        + "\n"
        + f"When the advisor returns, read its report at {advice_path}.\n"
        "Findings are observations, not orders: judge each against the anchor —\n"
        "act on what holds, rebut what does not (your rebuttal reaches the next\n"
        "audit). Only the advisor can certify completion.\n"
        f"{format_candidates_notice(candidates_path)}\n"
    )
    return prefix + body


def format_end_notice(
    cause: str,
    log_path: Path | None = None,
    candidates_path: Path | None = None,
) -> str:
    """Build the notice every termination path sends to the main agent.

    The main agent must clearly report the end and its cause to the user —
    whatever ended the loop.  The loop log is the one complete record (round
    narrations plus every audit), so the notice has the main agent recap it: over
    a long run the main agent's context may have auto-compacted early rounds
    away.  A candidates_path (passed when the queue still holds entries) appends
    the drain directive — promote or discard — so an automatic end never strands
    the queue.
    """
    notice = (
        f"The advisor loop has ended — {cause}. "
        f"Clearly report the end and its cause to the user."
    )
    if log_path is not None:
        notice += f" Read {log_path} and add a brief recap of the rounds."
    if candidates_path is not None:
        notice += (
            f" The candidates queue at {candidates_path} still holds entries — "
            "drain it before finishing: promote or discard each one."
        )
    return notice + "\n"
