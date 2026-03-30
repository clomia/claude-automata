#!/usr/bin/env python3
"""
Stop Hook: Claude가 멈추려 할 때 다음 미션을 주입하여 연속 실행을 유지한다.

Claude Code Hook 프로토콜:
- stdin: JSON (hook_type, session_id, stop_hook_active, last_assistant_message)
- stdout: JSON (decision, reason, additionalContext)
- exit 0: 결정 적용
- exit 2: 강제 block
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

MAX_STOP_HOOK_INVOCATIONS = 50
CONTEXT_REFRESH_DEFAULT = 5
PROACTIVE_IMPROVEMENT_INTERVAL_DEFAULT = 10


def _timeout_handler(signum: int, frame: object) -> None:
    output_decision("allow", "Hook 타임아웃 (안전 장치)")
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
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.rename(path)


def get_hook_state() -> dict:
    path = RUN_DIR / "hook_state.json"
    state = load_json(path)
    if not state:
        state = {
            "session_stop_count": 0,
            "current_session_id": None,
            "completed_mission_count": 0,
            "compaction_count": 0,
            "last_invoked_at": None,
        }
    return state


def save_hook_state(state: dict) -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    save_json(RUN_DIR / "hook_state.json", state)


def output_decision(
    decision: str, reason: str, additional_context: str = ""
) -> None:
    result: dict = {"decision": decision, "reason": reason}
    if additional_context:
        result["additionalContext"] = additional_context
    print(json.dumps(result, ensure_ascii=False))


def select_next_mission(missions_data: dict) -> dict | None:
    missions = missions_data.get("missions", [])
    completed_ids = {
        m["id"] for m in missions if m["status"] == "completed"
    }

    pending = [m for m in missions if m["status"] == "pending"]
    eligible = []
    for m in pending:
        deps = set(m.get("dependencies", []))
        if deps.issubset(completed_ids):
            blockers = m.get("blockers", [])
            active = [
                b for b in blockers if not b.get("resolved", False)
            ]
            if not active:
                eligible.append(m)

    if not eligible:
        if pending:
            return pending[0]
        return None

    eligible.sort(
        key=lambda m: (
            m.get("priority", 999),
            m.get("created_at", ""),
        )
    )
    return eligible[0]


def format_mission_context(mission: dict) -> str:
    lines = [
        "## 다음 미션\n",
        f"### {mission['id']}: {mission.get('title', '?')}\n",
        f"**설명:** {mission.get('description', '(없음)')}\n",
        "**성공 기준:**",
    ]
    for criterion in mission.get("success_criteria", []):
        lines.append(f"- {criterion}")

    deps = mission.get("dependencies", [])
    if deps:
        lines.append(f"\n**의존성:** {', '.join(deps)}")

    lines.append("\n---")
    lines.append(
        f"state/missions.json에서 {mission['id']}의 status를 "
        '"in_progress"로 변경한 후 작업을 시작하세요.'
    )
    return "\n".join(lines)


def main() -> None:
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        input_data = {}

    session_id = input_data.get("session_id", "unknown")
    stop_hook_active = input_data.get("stop_hook_active", False)

    # [1] 재귀 방지
    if stop_hook_active:
        output_decision("allow", "Stop Hook 재귀 방지")
        return

    # 훅 상태 로드
    hook_state = get_hook_state()

    if hook_state.get("current_session_id") != session_id:
        hook_state["current_session_id"] = session_id
        hook_state["session_stop_count"] = 0

    # [2] 호출 카운터 안전 장치
    hook_state["session_stop_count"] += 1
    hook_state["last_invoked_at"] = datetime.now(
        timezone.utc
    ).isoformat()
    save_hook_state(hook_state)

    if hook_state["session_stop_count"] >= MAX_STOP_HOOK_INVOCATIONS:
        output_decision(
            "allow",
            f"세션당 최대 Stop Hook 호출 횟수 초과 ({MAX_STOP_HOOK_INVOCATIONS}회, 안전 장치)",
        )
        return

    # [3] 미션 데이터 로드
    missions_data = load_json(STATE_DIR / "missions.json")
    config = load_toml(STATE_DIR / "config.toml")

    # 컨텍스트 리프레시 확인
    refresh_threshold = config.get(
        "context_refresh_after_compactions", CONTEXT_REFRESH_DEFAULT
    )
    if hook_state.get("compaction_count", 0) >= refresh_threshold:
        hook_state["compaction_count"] = 0
        save_hook_state(hook_state)
        output_decision(
            "allow", "컨텍스트 리프레시 필요 (compaction 횟수 초과)"
        )
        return

    # [4] 완료 미션 카운트
    completed_count = sum(
        1
        for m in missions_data.get("missions", [])
        if m["status"] == "completed"
    )
    hook_state["completed_mission_count"] = completed_count
    save_hook_state(hook_state)

    # [5] 다음 미션 확인
    next_mission = select_next_mission(missions_data)

    if next_mission:
        context = format_mission_context(next_mission)
        output_decision("block", "다음 미션이 있습니다", context)
        return

    # [6] 사전 개선 시점 확인
    improvement_interval = config.get(
        "proactive_improvement_interval",
        PROACTIVE_IMPROVEMENT_INTERVAL_DEFAULT,
    )

    if (
        completed_count > 0
        and completed_count % improvement_interval == 0
    ):
        improvement_context = """## 사전 개선 (Proactive Improvement)

미션 큐가 비었고, 주기적 시스템 개선 시점입니다.

다음을 검토하고 개선하세요:
1. CLAUDE.md의 지시문이 효과적인가?
2. .claude/rules/의 규칙이 최신 상태인가?
3. 반복되는 마찰 패턴이 state/friction.json에 있는가?
4. system/ 코드에 개선할 점이 있는가?
5. 현재 전략(state/strategy.json)이 Purpose에 부합하는가?

개선 사항을 찾으면 즉시 수정하고, friction.json에 해소 기록을 남기세요.
개선이 완료되면 다음 단계로 넘어가세요."""

        output_decision(
            "block", "사전 개선 시점입니다", improvement_context
        )
        return

    # [7] 미션 생성 필요
    purpose_data = load_json(STATE_DIR / "purpose.json")
    strategy_data = load_json(STATE_DIR / "strategy.json")

    completed_missions = [
        m
        for m in missions_data.get("missions", [])
        if m["status"] == "completed"
    ]
    recent_completed = sorted(
        completed_missions,
        key=lambda m: m.get("completed_at", ""),
        reverse=True,
    )[:10]

    recent_summary = (
        "\n".join(
            f"- {m['id']}: {m.get('title', '?')}"
            for m in recent_completed
        )
        or "(없음)"
    )

    generation_context = f"""## 미션 생성 필요

미션 큐가 비었습니다. Purpose에 기반하여 새 미션을 생성하세요.

### 현재 Purpose
{purpose_data.get('purpose', '(미설정)')}

### 현재 전략
{json.dumps(strategy_data, ensure_ascii=False, indent=2) if strategy_data else '(미설정)'}

### 완료된 미션 이력 (최근 10개)
{recent_summary}

### 지시사항
1. Purpose와 전략을 분석하여 다음에 해야 할 작업을 파악하세요.
2. 3~5개의 구체적인 미션을 생성하세요.
3. 각 미션에 명확한 success_criteria를 포함하세요.
4. state/missions.json에 추가하세요.
5. 전략 업데이트가 필요하면 state/strategy.json도 수정하세요.
6. 첫 번째 미션을 즉시 시작하세요."""

    output_decision(
        "block", "미션 생성 필요", generation_context
    )


if __name__ == "__main__":
    main()
