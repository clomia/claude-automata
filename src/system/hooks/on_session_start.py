#!/usr/bin/env python3
"""
SessionStart Hook: 세션 시작 시 컨텍스트를 주입한다.

Claude Code Hook 프로토콜:
- stdin: JSON (hook_type, session_id, type)
- stdout: JSON (additionalContext)
- exit 0: 컨텍스트 주입 성공
"""

import json
import signal
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STATE_DIR = PROJECT_ROOT / "state"
RUN_DIR = PROJECT_ROOT / "run"


def _timeout_handler(signum: int, frame: object) -> None:
    print(json.dumps({"additionalContext": ""}, ensure_ascii=False))
    sys.exit(0)


signal.signal(signal.SIGALRM, _timeout_handler)
signal.alarm(8)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_toml(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return {}


def save_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    tmp.rename(path)


def get_mission_summary(missions_data: dict) -> str:
    missions = missions_data.get("missions", [])
    by_status: dict[str, list] = {}
    for m in missions:
        status = m.get("status", "unknown")
        by_status.setdefault(status, []).append(m)

    return "\n".join([
        f"- 전체: {len(missions)}개",
        f"- 대기(pending): {len(by_status.get('pending', []))}개",
        f"- 진행중(in_progress): {len(by_status.get('in_progress', []))}개",
        f"- 완료(completed): {len(by_status.get('completed', []))}개",
        f"- 차단(blocked): {len(by_status.get('blocked', []))}개",
    ])


def get_current_mission(missions_data: dict) -> dict | None:
    for m in missions_data.get("missions", []):
        if m.get("status") == "in_progress":
            return m
    return None


def format_mission_detail(mission: dict) -> str:
    lines = [
        f"**{mission['id']}: {mission.get('title', '?')}**",
        f"- 설명: {mission.get('description', '(없음)')}",
        f"- 상태: {mission.get('status', 'unknown')}",
        "- 성공 기준:",
    ]
    for c in mission.get("success_criteria", []):
        lines.append(f"  - {c}")
    return "\n".join(lines)


def build_full_context(
    purpose_data: dict,
    strategy_data: dict,
    missions_data: dict,
    friction_data: dict,
    requests_data: dict,
    config_data: dict,
    preamble: str = "",
) -> str:
    sections = []

    if preamble:
        sections.append(preamble)

    # 건강 메트릭
    health_metrics = load_json(RUN_DIR / "health_metrics.json")
    if health_metrics:
        trend = health_metrics.get("friction_trend", "unknown")
        unresolved = health_metrics.get("friction_unresolved", 0)
        effectiveness = health_metrics.get(
            "improvement_effectiveness", 1.0
        )

        warnings = []
        if trend == "increasing" or unresolved > 5:
            warnings.append(
                f"friction {unresolved}건 미해소 (추세: {trend})"
            )
        if effectiveness < 0.3:
            warnings.append(f"개선 효과율 {effectiveness:.0%}")
        stalled = health_metrics.get("stalled_mission_id")
        if stalled:
            stall_count = health_metrics.get(
                "stalled_mission_sessions", 0
            )
            warnings.append(
                f"미션 {stalled}이 {stall_count}회 연속 세션에서 정체"
            )
        short = health_metrics.get("short_sessions_recent", 0)
        if short >= 3:
            warnings.append(
                f"최근 {short}개 세션이 60초 이내 종료 (thrashing 의심)"
            )

        if warnings:
            sections.append(
                "⚠️ **시스템 건강 경고**: "
                + ". ".join(warnings)
                + ".\n"
            )

    # Purpose
    sections.append("## Purpose")
    sections.append(purpose_data.get("purpose", "(미설정)"))

    # 전략
    if strategy_data:
        sections.append("\n## 현재 전략")
        sections.append(
            strategy_data.get("summary", "(요약 없음)")
        )

    # 미션 현황
    sections.append("\n## 미션 큐 현황")
    sections.append(get_mission_summary(missions_data))

    current = get_current_mission(missions_data)
    if current:
        sections.append("\n## 현재 미션")
        sections.append(format_mission_detail(current))

    # 미해결 요청
    pending_requests = [
        r
        for r in requests_data.get("requests", [])
        if r.get("status") == "pending"
    ]
    if pending_requests:
        sections.append("\n## 미해결 Owner 요청")
        for r in pending_requests:
            sections.append(
                f"- {r['id']}: {r.get('question', '(질문 없음)')}"
            )

    # 최근 Friction
    frictions = friction_data.get("frictions", [])
    unresolved_frictions = [
        f for f in frictions if not f.get("resolved_at")
    ]
    recent = sorted(
        unresolved_frictions,
        key=lambda f: f.get("timestamp", ""),
        reverse=True,
    )[:5]
    if recent:
        sections.append("\n## 최근 마찰 기록")
        for f in recent:
            sections.append(
                f"- [{f.get('type', 'unknown')}] "
                f"{f.get('description', '(설명 없음)')}"
            )

    return "\n".join(sections)


def build_resume_context(
    missions_data: dict,
    requests_data: dict,
    friction_data: dict,
) -> str:
    sections = ["## 세션 재개 컨텍스트"]

    current = get_current_mission(missions_data)
    if current:
        sections.append("\n### 진행 중이었던 미션")
        sections.append(format_mission_detail(current))

    recent_answers = [
        r
        for r in requests_data.get("requests", [])
        if r.get("status") == "answered"
    ]
    if recent_answers:
        sections.append("\n### Owner 응답 도착")
        for r in recent_answers[-3:]:
            sections.append(
                f"- {r['id']}: {r.get('answer', '(응답 없음)')}"
            )

    frictions = friction_data.get("frictions", [])
    recent = sorted(
        [f for f in frictions if not f.get("resolved_at")],
        key=lambda f: f.get("timestamp", ""),
        reverse=True,
    )[:3]
    if recent:
        sections.append("\n### 최근 마찰")
        for f in recent:
            sections.append(f"- {f.get('description', '')}")

    return "\n".join(sections)


def build_compact_context(
    purpose_data: dict,
    strategy_data: dict,
    missions_data: dict,
    friction_data: dict,
    requests_data: dict,
    config_data: dict,
) -> str:
    preamble = (
        "⚠️ **Autocompaction이 발생했습니다.**\n"
        "이전 대화의 세부 사항이 압축되었습니다. "
        "아래 컨텍스트를 반드시 확인하고, Purpose와 현재 미션에 집중하세요.\n"
        "목표에서 벗어나지 않도록 주의하세요."
    )
    return build_full_context(
        purpose_data,
        strategy_data,
        missions_data,
        friction_data,
        requests_data,
        config_data,
        preamble=preamble,
    )


def main() -> None:
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        input_data = {}

    session_type = input_data.get("type", "startup")

    purpose_data = load_json(STATE_DIR / "purpose.json")
    strategy_data = load_json(STATE_DIR / "strategy.json")
    missions_data = load_json(STATE_DIR / "missions.json")
    friction_data = load_json(STATE_DIR / "friction.json")
    requests_data = load_json(STATE_DIR / "requests.json")
    config_data = load_toml(STATE_DIR / "config.toml")

    if session_type == "resume":
        context = build_resume_context(
            missions_data, requests_data, friction_data
        )
    elif session_type == "compact":
        context = build_compact_context(
            purpose_data,
            strategy_data,
            missions_data,
            friction_data,
            requests_data,
            config_data,
        )
        # compaction 카운터 증가
        hook_state_path = RUN_DIR / "hook_state.json"
        hook_state = load_json(hook_state_path)
        hook_state["compaction_count"] = (
            hook_state.get("compaction_count", 0) + 1
        )
        RUN_DIR.mkdir(parents=True, exist_ok=True)
        save_json(hook_state_path, hook_state)
    else:
        context = build_full_context(
            purpose_data,
            strategy_data,
            missions_data,
            friction_data,
            requests_data,
            config_data,
        )

    print(json.dumps({"additionalContext": context}, ensure_ascii=False))


if __name__ == "__main__":
    main()
