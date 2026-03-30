# Hook System 컴포넌트 설계

> Claude Code 세션의 생명주기에 개입하여 자율 동작을 구현하는 훅 시스템

---

## 1. Hook 아키텍처 개요

Hook System은 Claude Code의 공식 Hook 메커니즘을 활용하여 세션의 시작, 종료, 알림 시점에 커스텀 로직을 주입한다. 각 훅은 독립적인 Python 스크립트로 구현되며, `.claude/settings.json`에 등록된다.

### 핵심 설계 결정

| 결정 | 선택 | 근거 |
|------|------|------|
| 훅 구현 언어 | Python (시스템과 동일) | StateManager 재사용, 일관성 |
| 통신 방식 | stdin(JSON) → stdout(JSON) | Claude Code Hook 공식 프로토콜 |
| 실행 모델 | 독립 프로세스 (subprocess) | Claude Code가 직접 실행 |
| 안전 장치 | 타임아웃 + 호출 카운터 + 재귀 방지 플래그 | 무한 루프/행 방지 |

### 훅 목록

| 훅 | 파일 | 이벤트 | 역할 |
|----|------|--------|------|
| Stop Hook | `system/hooks/on_stop.py` | Claude가 응답 완료 시 | 다음 미션 주입으로 연속 실행 유지 (Ralph Loop) |
| SessionStart Hook | `system/hooks/on_session_start.py` | 세션 시작/재개 시 | 컨텍스트 주입 (상태, 미션, Purpose) |
| Notification Hook | `system/hooks/on_notification.py` | 시스템 알림 발생 시 | Slack/TUI 알림 전달 |

### 컴포넌트 위치

```
system/
└── hooks/
    ├── on_stop.py               # Stop Hook 스크립트
    ├── on_session_start.py      # SessionStart Hook 스크립트
    └── on_notification.py       # Notification Hook 스크립트

.claude/
└── settings.json                # 훅 등록 설정

state/
├── missions.json                # 미션 큐 (Stop Hook이 읽기/쓰기)
├── purpose.json                 # Purpose (SessionStart Hook이 읽기)
├── sessions.json                # 세션 이력 (SessionStart Hook이 읽기)
└── config.toml                  # 동적 설정 (임계값 등)

run/
└── hook_state.json              # 훅 실행 상태 (호출 카운터 등, Git 무시)
```

---

## 2. `.claude/settings.json` 전체 설정

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run python system/hooks/on_stop.py"
          }
        ]
      },
      {
        "hooks": [
          {
            "type": "agent",
            "model": "opus",
            "timeout": 300,
            "tools": ["Read"],
            "prompt": "인지 부하 트리거 생성자. 상세: cognitive-load-trigger.md §3.4"
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "startup|resume|compact",
        "hooks": [
          {
            "type": "command",
            "command": "uv run python system/hooks/on_session_start.py"
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": "idle_prompt|permission_prompt",
        "hooks": [
          {
            "type": "command",
            "command": "uv run python system/hooks/on_notification.py"
          }
        ]
      }
    ]
  },
  "permissions": {
    "allow": [
      "Bash(*)",
      "Read",
      "Edit",
      "Write",
      "Glob",
      "Grep",
      "Agent",
      "WebFetch",
      "WebSearch"
    ]
  }
}
```

**설정 설명:**

- `Stop`: matcher 생략 = 모든 stop 이벤트에 매칭
- `SessionStart`: matcher `"startup|resume|compact"` = 시작, 재개, compaction 이벤트에 매칭
- `Notification`: matcher `"idle_prompt|permission_prompt"` = 유휴 프롬프트, 권한 프롬프트에 매칭
- `type: "command"`: 외부 명령 실행 방식
- `command`: `uv run`으로 실행하여 프로젝트 가상환경 내 Python 사용
- `permissions.allow`: `--dangerously-skip-permissions` 대신 프로젝트 레벨에서 전체 허용 (두 가지 모두 지원)

---

## 3. Hook 1: Stop Hook (`system/hooks/on_stop.py`)

### 목적

Claude가 응답을 완료하고 멈추려 할 때 개입하여, 아직 할 일이 남아있으면 다음 미션을 주입해 연속 실행을 유지한다. 이것이 Ralph Loop 패턴의 핵심이다.

### 입력 (stdin JSON)

```json
{
  "hook_type": "Stop",
  "session_id": "session-abc-123",
  "stop_hook_active": false,
  "transcript_summary": "...",
  "last_assistant_message": "미션 M-001을 완료했습니다. tests/를 통과했고..."
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `hook_type` | string | 항상 "Stop" |
| `session_id` | string | 현재 Claude Code 세션 ID |
| `stop_hook_active` | boolean | true이면 Claude가 이미 Stop Hook에 의해 실행 중 (재귀 방지) |
| `transcript_summary` | string | 현재 대화 요약 |
| `last_assistant_message` | string | Claude의 마지막 응답 메시지 |

### 출력 (stdout JSON)

```json
{
  "decision": "block",
  "reason": "다음 미션이 있습니다",
  "additionalContext": "## 다음 미션\n\n### M-002: API 엔드포인트 구현\n\n..."
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `decision` | `"block"` \| `"allow"` | block = 종료 방지, allow = 종료 허용 |
| `reason` | string | 결정 사유 (한국어) |
| `additionalContext` | string | block 시 Claude에 주입할 추가 컨텍스트 |

### 결정 트리

```
on_stop.py 실행
    │
    ▼
[1] stop_hook_active == true?
    │
    ├── Yes → decision: "allow"
    │         reason: "Stop Hook 재귀 방지"
    │         (무한 루프 방지: 이미 Stop Hook이 주입한 작업 중이었음)
    │
    └── No → 계속
              │
              ▼
[2] 호출 카운터 확인: session_stop_count >= 50?
    │
    ├── Yes → decision: "allow"
    │         reason: "세션당 최대 Stop Hook 호출 횟수 초과 (안전 장치)"
    │         (런어웨이 방지: 한 세션에서 50번 이상 멈추면 강제 종료)
    │
    └── No → session_stop_count += 1, 계속
              │
              ▼
[3] state/missions.json 읽기
    │
    ▼
[4] 현재 미션이 완료되었는가? (last_assistant_message 분석)
    │
    ├── 완료 징후 있음 → missions.json에서 현재 미션 status = "completed" 업데이트
    │
    └── 완료 아님 → (미션 중단 상황, 그래도 다음 단계 진행)
              │
              ▼
[5] pending 미션이 더 있는가?
    │
    ├── Yes → 우선순위 가장 높은 pending 미션 선택
    │         │
    │         ▼
    │         decision: "block"
    │         reason: "다음 미션이 있습니다"
    │         additionalContext: """
    │           ## 다음 미션
    │
    │           ### {mission.id}: {mission.title}
    │
    │           **설명:** {mission.description}
    │
    │           **성공 기준:**
    │           {success_criteria 리스트}
    │
    │           **의존성:** {dependencies}
    │
    │           ---
    │           state/missions.json에서 이 미션의 status를 "in_progress"로 변경한 후 작업을 시작하세요.
    │         """
    │
    └── No → 미션 큐가 비었음
              │
              ▼
[6] 사전 개선(Proactive Improvement) 시점인가?
    (completed_mission_count % proactive_improvement_interval == 0)
    │
    ├── Yes → decision: "block"
    │         reason: "사전 개선 시점입니다"
    │         additionalContext: """
    │           ## 사전 개선 (Proactive Improvement)
    │
    │           미션 큐가 비었고, 주기적 시스템 개선 시점입니다.
    │
    │           다음을 검토하고 개선하세요:
    │           1. CLAUDE.md의 지시문이 효과적인가?
    │           2. .claude/rules/의 규칙이 최신 상태인가?
    │           3. 반복되는 마찰 패턴이 state/friction.json에 있는가?
    │           4. system/ 코드에 개선할 점이 있는가?
    │           5. 현재 전략(state/strategy.json)이 Purpose에 부합하는가?
    │
    │           개선 사항을 찾으면 즉시 수정하고, friction.json에 해소 기록을 남기세요.
    │           개선이 완료되면 다음 단계로 넘어가세요.
    │         """
    │
    └── No → 계속
              │
              ▼
[7] 미션 생성 필요
    │
    ▼
    decision: "block"
    reason: "미션 생성 필요"
    additionalContext: """
      ## 미션 생성 필요

      미션 큐가 비었습니다. Purpose에 기반하여 새 미션을 생성하세요.

      ### 현재 Purpose
      {state/purpose.json의 purpose 필드}

      ### 현재 전략
      {state/strategy.json 요약}

      ### 완료된 미션 이력
      {최근 완료 미션 10개 요약}

      ### 지시사항
      1. Purpose와 전략을 분석하여 다음에 해야 할 작업을 파악하세요.
      2. 3~5개의 구체적인 미션을 생성하세요.
      3. 각 미션에 명확한 success_criteria를 포함하세요.
      4. state/missions.json에 추가하세요.
      5. 전략 업데이트가 필요하면 state/strategy.json도 수정하세요.
      6. 첫 번째 미션을 즉시 시작하세요.
    """
```

### 컨텍스트 리프레시 판단

```
[추가 판단] 컨텍스트 리프레시 필요?
    │
    조건: compaction_count >= context_refresh_after_compactions (config.toml, 기본: 5)
    │
    ├── Yes → decision: "allow"
    │         reason: "컨텍스트 리프레시 필요 (compaction 횟수 초과)"
    │         (Supervisor가 새 세션을 시작하여 깨끗한 컨텍스트로 계속)
    │
    └── No → 위 결정 트리대로 진행
```

### 전체 구현

```python
#!/usr/bin/env python3
"""
Stop Hook: Claude가 멈추려 할 때 다음 미션을 주입하여 연속 실행을 유지한다.

Claude Code Hook 프로토콜:
- stdin: JSON (hook_type, session_id, stop_hook_active, last_assistant_message)
- stdout: JSON (decision, reason, additionalContext)
- exit 0: 결정 적용 (block or allow)
- exit 2: 강제 block (비정상 상황)
"""

import json
import sys
import time
import tomllib
from datetime import datetime, timezone
from pathlib import Path

# 프로젝트 루트 기준 경로
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STATE_DIR = PROJECT_ROOT / "state"
RUN_DIR = PROJECT_ROOT / "run"

# 안전 장치 상수
MAX_STOP_HOOK_INVOCATIONS = 50
CONTEXT_REFRESH_DEFAULT = 5
PROACTIVE_IMPROVEMENT_INTERVAL_DEFAULT = 10


def load_json(path: Path) -> dict:
    """JSON 파일을 안전하게 로드."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_toml(path: Path) -> dict:
    """TOML 파일을 안전하게 로드."""
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return {}


def save_json(path: Path, data: dict) -> None:
    """JSON 파일을 원자적으로 저장."""
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.rename(path)


def get_hook_state() -> dict:
    """훅 실행 상태 로드 (run/hook_state.json)."""
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
    """훅 실행 상태 저장."""
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    save_json(RUN_DIR / "hook_state.json", state)


def output_decision(decision: str, reason: str, additional_context: str = "") -> None:
    """결정을 stdout JSON으로 출력."""
    result = {
        "decision": decision,
        "reason": reason,
    }
    if additional_context:
        result["additionalContext"] = additional_context
    print(json.dumps(result, ensure_ascii=False))


def select_next_mission(missions_data: dict) -> dict | None:
    """
    다음 실행할 미션을 선택한다.

    선택 기준 (우선순위 순):
    1. priority 값이 가장 낮은 (높은 우선순위) pending 미션
    2. 동일 priority 내에서 dependencies가 모두 충족된 미션
    3. 동일 조건 내에서 created_at이 가장 오래된 미션
    """
    missions = missions_data.get("missions", [])
    completed_ids = {
        m["id"] for m in missions if m["status"] == "completed"
    }

    pending = [m for m in missions if m["status"] == "pending"]

    # 의존성 충족 필터
    eligible = []
    for m in pending:
        deps = set(m.get("dependencies", []))
        if deps.issubset(completed_ids):
            eligible.append(m)

    if not eligible:
        # 의존성 미충족이지만 pending인 미션이 있으면 경고와 함께 반환
        if pending:
            return pending[0]  # 의존성 무시하고 첫 번째 반환
        return None

    # priority 오름차순 → created_at 오름차순 정렬
    eligible.sort(key=lambda m: (m.get("priority", 999), m.get("created_at", "")))
    return eligible[0]


def format_mission_context(mission: dict) -> str:
    """미션을 Claude에 주입할 컨텍스트 문자열로 포맷."""
    lines = [
        "## 다음 미션\n",
        f"### {mission['id']}: {mission['title']}\n",
        f"**설명:** {mission.get('description', '(없음)')}\n",
        "**성공 기준:**",
    ]
    for criterion in mission.get("success_criteria", []):
        lines.append(f"- {criterion}")

    deps = mission.get("dependencies", [])
    if deps:
        lines.append(f"\n**의존성:** {', '.join(deps)}")

    blockers = mission.get("blockers", [])
    if blockers:
        lines.append(f"\n**Blockers:** {', '.join(str(b) for b in blockers)}")

    lines.append("\n---")
    lines.append(
        f"state/missions.json에서 {mission['id']}의 status를 "
        '"in_progress"로 변경한 후 작업을 시작하세요.'
    )

    return "\n".join(lines)


def main() -> None:
    """Stop Hook 메인 로직."""
    # stdin에서 입력 읽기
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        input_data = {}

    session_id = input_data.get("session_id", "unknown")
    stop_hook_active = input_data.get("stop_hook_active", False)

    # ─── [1] 재귀 방지 ───
    if stop_hook_active:
        output_decision("allow", "Stop Hook 재귀 방지")
        return

    # ─── 훅 상태 로드 ───
    hook_state = get_hook_state()

    # 세션이 바뀌었으면 카운터 리셋
    if hook_state.get("current_session_id") != session_id:
        hook_state["current_session_id"] = session_id
        hook_state["session_stop_count"] = 0

    # ─── [2] 호출 카운터 안전 장치 ───
    hook_state["session_stop_count"] += 1
    hook_state["last_invoked_at"] = datetime.now(timezone.utc).isoformat()
    save_hook_state(hook_state)

    if hook_state["session_stop_count"] >= MAX_STOP_HOOK_INVOCATIONS:
        output_decision(
            "allow",
            f"세션당 최대 Stop Hook 호출 횟수 초과 ({MAX_STOP_HOOK_INVOCATIONS}회, 안전 장치)",
        )
        return

    # ─── [3] 미션 데이터 로드 ───
    missions_data = load_json(STATE_DIR / "missions.json")

    # ─── 컨텍스트 리프레시 확인 ───
    config = load_toml(STATE_DIR / "config.toml")
    refresh_threshold = config.get(
        "context_refresh_after_compactions", CONTEXT_REFRESH_DEFAULT
    )
    if hook_state.get("compaction_count", 0) >= refresh_threshold:
        hook_state["compaction_count"] = 0
        save_hook_state(hook_state)
        output_decision("allow", "컨텍스트 리프레시 필요 (compaction 횟수 초과)")
        return

    # ─── [4] 미션 상태 확인 ───
    # 미션 완료 마킹은 AI의 책임이다 (CLAUDE.md 프로토콜).
    # Hook은 AI가 프로토콜을 따랐는지 키워드로 추측하지 않는다.
    # missions.json의 현재 상태를 사실로 받아들이고 "다음에 할 일"만 판단한다.
    completed_count = sum(
        1 for m in missions_data.get("missions", [])
        if m["status"] == "completed"
    )
    hook_state["completed_mission_count"] = completed_count
    save_hook_state(hook_state)

    # ─── [5] 다음 미션 확인 ───
    next_mission = select_next_mission(missions_data)

    if next_mission:
        context = format_mission_context(next_mission)
        output_decision("block", "다음 미션이 있습니다", context)
        return

    # ─── [6] 사전 개선 시점 확인 ───
    improvement_interval = config.get(
        "proactive_improvement_interval",
        PROACTIVE_IMPROVEMENT_INTERVAL_DEFAULT,
    )
    completed_count = hook_state.get("completed_mission_count", 0)

    if completed_count > 0 and completed_count % improvement_interval == 0:
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

        output_decision("block", "사전 개선 시점입니다", improvement_context)
        return

    # ─── [7] 미션 생성 필요 ───
    purpose_data = load_json(STATE_DIR / "purpose.json")
    strategy_data = load_json(STATE_DIR / "strategy.json")

    # 최근 완료 미션 요약
    completed_missions = [
        m for m in missions_data.get("missions", [])
        if m["status"] == "completed"
    ]
    recent_completed = sorted(
        completed_missions,
        key=lambda m: m.get("completed_at", ""),
        reverse=True,
    )[:10]

    recent_summary = "\n".join(
        f"- {m['id']}: {m['title']}"
        for m in recent_completed
    ) or "(없음)"

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

    output_decision("block", "미션 생성 필요", generation_context)


if __name__ == "__main__":
    main()
```

---

## 4. Hook 2: SessionStart Hook (`system/hooks/on_session_start.py`)

### 목적

새 세션이 시작되거나 기존 세션이 재개될 때, 현재 시스템 상태와 컨텍스트를 Claude에 주입한다. 특히 compaction 후에는 Purpose와 현재 미션을 재주입하여 목표 드리프트를 방지한다.

### 입력 (stdin JSON)

```json
{
  "hook_type": "SessionStart",
  "session_id": "session-abc-123",
  "type": "startup"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `hook_type` | string | 항상 "SessionStart" |
| `session_id` | string | 세션 ID |
| `type` | `"startup"` \| `"resume"` \| `"compact"` \| `"clear"` | 세션 시작 유형 |

**세션 시작 유형:**

| 유형 | 상황 | 주입할 컨텍스트 |
|------|------|-----------------|
| `startup` | 새 세션 시작 | 전체 상태 요약 |
| `resume` | 세션 재개 (--resume) | 변경된 상태 + 이전 작업 요약 |
| `compact` | Autocompaction 발생 | 전체 상태 + Purpose 재주입 (드리프트 방지) |
| `clear` | 컨텍스트 클리어 | 전체 상태 + Purpose + 현재 미션 상세 |

### 출력 (stdout JSON)

```json
{
  "additionalContext": "## 시스템 상태\n\n### Purpose\n..."
}
```

SessionStart Hook의 출력은 `additionalContext` 필드 하나만 포함한다. 이 내용이 세션 시작 시 Claude에 주입된다.

### 결정 트리

```
on_session_start.py 실행
    │
    ▼
[1] 입력 파싱: session_id, type 추출
    │
    ▼
[2] 상태 파일 로드
    ├── state/purpose.json
    ├── state/strategy.json
    ├── state/missions.json
    ├── state/friction.json
    ├── state/requests.json
    └── state/config.toml
    │
    ▼
[3] type별 컨텍스트 생성
    │
    ├── "startup" 또는 "clear":
    │   │
    │   ▼
    │   전체 상태 요약 생성:
    │   - Purpose 전문
    │   - 현재 전략 요약
    │   - 미션 큐 현황 (pending, in_progress, completed 개수)
    │   - 현재 미션 상세 (있으면)
    │   - 미해결 Blocker 목록
    │   - 미해결 Owner 요청 목록
    │   - 최근 Friction 기록 (최근 5개)
    │   - 시스템 설정 요약 (임계값 등)
    │
    ├── "resume":
    │   │
    │   ▼
    │   변경 상태 + 이전 작업 요약:
    │   - 현재 미션 상세 (이전에 작업 중이었던 미션)
    │   - 새로 도착한 Owner 응답 (있으면)
    │   - 새로 해제된 Blocker (있으면)
    │   - 최근 Friction 기록 (세션 중단 후 추가된 것)
    │
    └── "compact":
        │
        ▼
        전체 상태 + Purpose 재주입 (드리프트 방지):
        - ⚠️ "Autocompaction이 발생했습니다. 아래 컨텍스트를 다시 확인하세요." 경고
        - Purpose 전문 (반드시 포함)
        - 현재 전략 전문
        - 현재 미션 상세 (success_criteria 포함)
        - 진행 중인 작업의 요약
        - 미해결 Blocker 목록
        - 시스템 규칙 재확인 사항
    │
    ▼
[4] compaction_count 업데이트
    (type == "compact" 이면 hook_state.compaction_count += 1)
    │
    ▼
[5] stdout으로 출력
```

### 전체 구현

```python
#!/usr/bin/env python3
"""
SessionStart Hook: 세션 시작 시 컨텍스트를 주입한다.

Claude Code Hook 프로토콜:
- stdin: JSON (hook_type, session_id, type)
- stdout: JSON (additionalContext)
- exit 0: 컨텍스트 주입 성공
"""

import json
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STATE_DIR = PROJECT_ROOT / "state"
RUN_DIR = PROJECT_ROOT / "run"


def load_json(path: Path) -> dict:
    """JSON 파일을 안전하게 로드."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_toml(path: Path) -> dict:
    """TOML 파일을 안전하게 로드."""
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return {}


def save_json(path: Path, data: dict) -> None:
    """JSON 파일을 원자적으로 저장."""
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.rename(path)


def get_mission_summary(missions_data: dict) -> str:
    """미션 큐 현황 요약."""
    missions = missions_data.get("missions", [])
    by_status = {}
    for m in missions:
        status = m.get("status", "unknown")
        by_status.setdefault(status, []).append(m)

    lines = [
        f"- 전체: {len(missions)}개",
        f"- 대기(pending): {len(by_status.get('pending', []))}개",
        f"- 진행중(in_progress): {len(by_status.get('in_progress', []))}개",
        f"- 완료(completed): {len(by_status.get('completed', []))}개",
        f"- 차단(blocked): {len(by_status.get('blocked', []))}개",
    ]
    return "\n".join(lines)


def get_current_mission(missions_data: dict) -> dict | None:
    """현재 진행 중인 미션 반환."""
    for m in missions_data.get("missions", []):
        if m.get("status") == "in_progress":
            return m
    return None


def format_mission_detail(mission: dict) -> str:
    """미션 상세 정보를 문자열로 포맷."""
    lines = [
        f"**{mission['id']}: {mission['title']}**",
        f"- 설명: {mission.get('description', '(없음)')}",
        f"- 상태: {mission.get('status', 'unknown')}",
        "- 성공 기준:",
    ]
    for c in mission.get("success_criteria", []):
        lines.append(f"  - {c}")

    blockers = mission.get("blockers", [])
    if blockers:
        lines.append(f"- Blockers: {', '.join(str(b) for b in blockers)}")

    return "\n".join(lines)


def get_pending_requests(requests_data: dict) -> list[dict]:
    """미답변 Owner 요청 목록."""
    return [
        r for r in requests_data.get("requests", [])
        if r.get("status") == "pending"
    ]


def get_recent_frictions(friction_data: dict, count: int = 5) -> list[dict]:
    """최근 Friction 기록."""
    frictions = friction_data.get("frictions", [])
    return sorted(
        frictions,
        key=lambda f: f.get("created_at", ""),
        reverse=True,
    )[:count]


def build_full_context(
    purpose_data: dict,
    strategy_data: dict,
    missions_data: dict,
    friction_data: dict,
    requests_data: dict,
    config_data: dict,
    preamble: str = "",
) -> str:
    """전체 시스템 상태 컨텍스트를 생성."""
    sections = []

    if preamble:
        sections.append(preamble)

    # 건강 메트릭 (Supervisor가 계산, 컨텍스트 최상단에 배치)
    # 이 메트릭은 코드가 state 파일에서 계산한 객관적 수치이다.
    # 모델의 자기 평가가 아닌 외부 앵커로 기능한다.
    health_metrics = load_json(RUN_DIR / "health_metrics.json")
    if health_metrics:
        trend = health_metrics.get("friction_trend", "unknown")
        unresolved = health_metrics.get("friction_unresolved", 0)
        effectiveness = health_metrics.get("improvement_effectiveness", 1.0)

        warnings = []
        if trend == "increasing" or unresolved > 5:
            warnings.append(f"friction {unresolved}건 미해소 (추세: {trend})")
        if effectiveness < 0.3:
            warnings.append(f"개선 효과율 {effectiveness:.0%}")
        stalled = health_metrics.get("stalled_mission_id")
        if stalled:
            stall_count = health_metrics.get("stalled_mission_sessions", 0)
            warnings.append(f"미션 {stalled}이 {stall_count}회 연속 세션에서 정체")
        short = health_metrics.get("short_sessions_recent", 0)
        if short >= 3:
            warnings.append(f"최근 {short}개 세션이 60초 이내 종료 (thrashing 의심)")

        if warnings:
            sections.append("⚠️ **시스템 건강 경고**: " + ". ".join(warnings) + ".\n")
        else:
            sections.append(
                f"시스템 건강: friction {unresolved}건 미해소 "
                f"(추세: {trend}), 개선 효과율 {effectiveness:.0%}\n"
            )

    # Purpose
    sections.append("## Purpose")
    sections.append(purpose_data.get("purpose", "(미설정)"))

    # 전략
    if strategy_data:
        sections.append("\n## 현재 전략")
        sections.append(
            strategy_data.get("summary", json.dumps(strategy_data, ensure_ascii=False, indent=2))
        )

    # 미션 현황
    sections.append("\n## 미션 큐 현황")
    sections.append(get_mission_summary(missions_data))

    # 현재 미션
    current = get_current_mission(missions_data)
    if current:
        sections.append("\n## 현재 미션")
        sections.append(format_mission_detail(current))

    # 미해결 요청
    pending_requests = get_pending_requests(requests_data)
    if pending_requests:
        sections.append("\n## 미해결 Owner 요청")
        for r in pending_requests:
            sections.append(f"- {r['id']}: {r.get('question', '(질문 없음)')}")

    # 최근 Friction
    recent_frictions = get_recent_frictions(friction_data)
    if recent_frictions:
        sections.append("\n## 최근 마찰 기록")
        for f in recent_frictions:
            sections.append(
                f"- [{f.get('type', 'unknown')}] {f.get('description', '(설명 없음)')}"
            )

    # 설정 요약
    if config_data:
        sections.append("\n## 시스템 설정")
        sections.append(f"- Friction 임계값: {config_data.get('friction_threshold', 3)}")
        sections.append(
            f"- 사전 개선 간격: 매 {config_data.get('proactive_improvement_interval', 10)}미션"
        )
        sections.append(
            f"- 컨텍스트 리프레시 임계값: {config_data.get('context_refresh_after_compactions', 5)} compactions"
        )

    return "\n".join(sections)


def build_resume_context(
    missions_data: dict,
    requests_data: dict,
    friction_data: dict,
) -> str:
    """세션 재개용 컨텍스트를 생성."""
    sections = ["## 세션 재개 컨텍스트"]

    # 현재 미션
    current = get_current_mission(missions_data)
    if current:
        sections.append("\n### 진행 중이었던 미션")
        sections.append(format_mission_detail(current))

    # 새 Owner 응답
    recent_answers = [
        r for r in requests_data.get("requests", [])
        if r.get("status") == "answered"
    ]
    if recent_answers:
        sections.append("\n### Owner 응답 도착")
        for r in recent_answers[-3:]:
            sections.append(f"- {r['id']}: {r.get('answer', '(응답 없음)')}")

    # 최근 Friction
    recent = get_recent_frictions(friction_data, count=3)
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
    """Compaction 후 컨텍스트를 생성 (드리프트 방지 강화)."""
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
    """SessionStart Hook 메인 로직."""
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        input_data = {}

    session_type = input_data.get("type", "startup")

    # 상태 파일 로드
    purpose_data = load_json(STATE_DIR / "purpose.json")
    strategy_data = load_json(STATE_DIR / "strategy.json")
    missions_data = load_json(STATE_DIR / "missions.json")
    friction_data = load_json(STATE_DIR / "friction.json")
    requests_data = load_json(STATE_DIR / "requests.json")
    config_data = load_toml(STATE_DIR / "config.toml")

    # 유형별 컨텍스트 생성
    if session_type == "resume":
        context = build_resume_context(missions_data, requests_data, friction_data)
    elif session_type == "compact":
        context = build_compact_context(
            purpose_data, strategy_data, missions_data,
            friction_data, requests_data, config_data,
        )
        # compaction 카운터 증가
        hook_state_path = RUN_DIR / "hook_state.json"
        hook_state = load_json(hook_state_path)
        hook_state["compaction_count"] = hook_state.get("compaction_count", 0) + 1
        RUN_DIR.mkdir(parents=True, exist_ok=True)
        save_json(hook_state_path, hook_state)
    else:
        # startup, clear
        context = build_full_context(
            purpose_data, strategy_data, missions_data,
            friction_data, requests_data, config_data,
        )

    # 출력
    print(json.dumps({"additionalContext": context}, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

---

## 5. Hook 3: Notification Hook (`system/hooks/on_notification.py`)

### 목적

Claude Code의 시스템 알림 (권한 프롬프트, 유휴 상태, 인증 성공)을 Slack과 TUI로 전달한다.

### 입력 (stdin JSON)

```json
{
  "hook_type": "Notification",
  "type": "idle_prompt",
  "session_id": "session-abc-123",
  "message": "..."
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `hook_type` | string | 항상 "Notification" |
| `type` | `"permission_prompt"` \| `"idle_prompt"` \| `"auth_success"` | 알림 유형 |
| `session_id` | string | 세션 ID |
| `message` | string | 알림 메시지 (선택적) |

### 처리 로직

```
on_notification.py 실행
    │
    ▼
[1] 입력 파싱: type 추출
    │
    ▼
[2] type별 처리
    │
    ├── "idle_prompt":
    │   │
    │   ▼
    │   시스템이 유휴 상태.
    │   ├── Slack 알림 전송: "⏸️ 시스템이 유휴 상태입니다"
    │   └── 로그 기록: WARNING "Idle prompt received"
    │
    ├── "permission_prompt":
    │   │
    │   ▼
    │   권한 프롬프트 발생 (비정상: --dangerously-skip-permissions 사용 중이면 발생하면 안 됨)
    │   ├── 로그 기록: WARNING "Permission prompt received (should not happen)"
    │   └── Slack 알림: "⚠️ 권한 프롬프트가 발생했습니다 (비정상)"
    │
    └── "auth_success":
        │
        ▼
        인증 성공.
        └── 로그 기록: INFO "Authentication successful"
    │
    ▼
[3] stdout: 빈 JSON (Notification Hook은 컨텍스트 주입 없음)
```

### 전체 구현

```python
#!/usr/bin/env python3
"""
Notification Hook: Claude Code 알림을 Slack/TUI로 전달한다.

Claude Code Hook 프로토콜:
- stdin: JSON (hook_type, type, session_id, message)
- stdout: JSON ({}) — Notification Hook은 컨텍스트를 주입하지 않음
- exit 0: 정상 처리
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
RUN_DIR = PROJECT_ROOT / "run"

# 로그 설정
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOGS_DIR / "hooks.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("automata.hook.notification")


def write_notification_file(notification: dict) -> None:
    """
    알림을 run/notifications.json에 추가한다.
    Supervisor가 이 파일을 주기적으로 읽어 Slack으로 전송한다.

    Notification Hook은 독립 프로세스이므로 직접 Slack API를 호출하지 않는다.
    대신 파일 기반으로 Supervisor에 알림을 전달한다.
    """
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    notifications_path = RUN_DIR / "notifications.json"

    try:
        data = json.loads(notifications_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"notifications": []}

    data["notifications"].append(notification)

    # 최대 100개 유지 (오래된 것 제거)
    if len(data["notifications"]) > 100:
        data["notifications"] = data["notifications"][-100:]

    tmp = notifications_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.rename(notifications_path)


def main() -> None:
    """Notification Hook 메인 로직."""
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        input_data = {}

    notification_type = input_data.get("type", "unknown")
    session_id = input_data.get("session_id", "unknown")
    message = input_data.get("message", "")

    now = datetime.now(timezone.utc).isoformat()

    if notification_type == "idle_prompt":
        logger.warning("Idle prompt received (session: %s)", session_id)
        write_notification_file({
            "type": "idle_prompt",
            "level": "warning",
            "text": "⏸️ 시스템이 유휴 상태입니다",
            "detail": message,
            "session_id": session_id,
            "created_at": now,
            "sent": False,
        })

    elif notification_type == "permission_prompt":
        logger.warning(
            "Permission prompt received - should not happen (session: %s): %s",
            session_id,
            message,
        )
        write_notification_file({
            "type": "permission_prompt",
            "level": "warning",
            "text": "⚠️ 권한 프롬프트가 발생했습니다 (비정상)",
            "detail": message,
            "session_id": session_id,
            "created_at": now,
            "sent": False,
        })

    elif notification_type == "auth_success":
        logger.info("Authentication successful (session: %s)", session_id)
        # 인증 성공은 Slack 알림 불필요, 로그만 기록

    else:
        logger.info(
            "Unknown notification type '%s' (session: %s): %s",
            notification_type,
            session_id,
            message,
        )

    # Notification Hook은 컨텍스트를 주입하지 않으므로 빈 JSON 출력
    print(json.dumps({}))


if __name__ == "__main__":
    main()
```

---

## 6. Hook 안전 메커니즘

### 6.1 타임아웃

Claude Code는 각 훅에 타임아웃을 적용한다. 기본 타임아웃은 10초이다.

```
Claude Code Hook 실행
    │
    ▼
[subprocess 실행] timeout = 10s
    │
    ├── 10초 내 완료 → stdout 파싱 → 결정 적용
    │
    └── 10초 초과 → 프로세스 강제 종료
                   → Hook 실패로 처리
                   → Stop Hook의 경우: allow (종료 허용, 안전 fallback)
```

각 훅 스크립트 내에서도 자체 타임아웃을 적용한다:

```python
import signal

def timeout_handler(signum, frame):
    """타임아웃 시 안전한 기본 동작."""
    output_decision("allow", "Hook 타임아웃 (안전 장치)")
    sys.exit(0)

# 8초 타임아웃 (Claude Code의 10초보다 짧게 설정)
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(8)
```

### 6.2 Stop Hook 호출 카운터

세션당 Stop Hook 호출 횟수를 추적하여 무한 루프를 방지한다.

```
세션 시작 → session_stop_count = 0

Stop Hook 호출마다:
    session_stop_count += 1

    if session_stop_count >= 50:
        decision = "allow"  # 강제 세션 종료
        → Supervisor가 새 세션 시작
```

**카운터 상태 저장:**

```json
// run/hook_state.json (Git 무시)
{
  "current_session_id": "session-abc-123",
  "session_stop_count": 15,
  "completed_mission_count": 42,
  "compaction_count": 1,
  "last_invoked_at": "2026-03-25T10:30:00Z"
}
```

- `current_session_id`: 세션이 바뀌면 `session_stop_count`를 리셋
- `session_stop_count`: 현재 세션의 Stop Hook 호출 횟수
- `completed_mission_count`: 전체 완료 미션 수 (사전 개선 주기 판단)
- `compaction_count`: autocompaction 횟수 (컨텍스트 리프레시 판단)

### 6.3 `stop_hook_active` 재귀 방지

Claude Code가 Stop Hook에 의해 block되어 추가 작업을 수행한 후 다시 멈추려 할 때, `stop_hook_active: true`가 전달된다. 이때 무조건 `allow`를 반환하여 무한 재귀를 방지한다.

```
[Claude 작업 완료] → Stop Hook 호출 (stop_hook_active: false)
    │
    ├── decision: "block" + 다음 미션 주입
    │
    ▼
[Claude가 다음 미션 실행] → Stop Hook 호출 (stop_hook_active: false)
    │
    ├── decision: "block" + 다음 미션 주입  (여전히 할 일 있음)
    │
    ▼
[Claude가 다음 미션 실행] → Stop Hook 호출 (stop_hook_active: false)
    │
    ├── decision: "allow"  (미션 큐 비었고 사전 개선도 아님)
    │
    ▼
[세션 종료]
```

주의: `stop_hook_active`는 Claude Code가 "Stop Hook이 block한 뒤 추가 실행된 부분" 자체의 종료 시에만 true가 된다. 정상적인 다중 미션 실행에서는 매번 false로 전달되므로 연속 미션 처리가 가능하다.

### 6.4 로깅

모든 훅은 결정 과정을 로그에 기록한다:

```python
# 각 훅 스크립트 상단에 로거 설정
import logging

logging.basicConfig(
    filename=str(LOGS_DIR / "hooks.log"),
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("automata.hook.stop")  # or .session_start, .notification

# 결정 기록
logger.info(
    "Stop Hook 결정: %s (reason: %s, session: %s, count: %d)",
    decision,
    reason,
    session_id,
    session_stop_count,
)
```

로그 위치: `logs/hooks.log`

로그 포맷 예:
```
2026-03-25 10:30:00 [INFO] automata.hook.stop: Stop Hook 결정: block (reason: 다음 미션이 있습니다, session: session-abc-123, count: 3)
2026-03-25 10:30:00 [DEBUG] automata.hook.stop: 다음 미션 선택: M-004 (priority: 1, title: API 구현)
2026-03-25 10:35:00 [INFO] automata.hook.session_start: SessionStart Hook: type=compact, context_length=2048
2026-03-25 10:35:00 [WARNING] automata.hook.notification: Idle prompt received (session: session-abc-123)
```

---

## 7. 훅 간 상호작용

### 7.1 Stop Hook → SessionStart Hook 연계

```
[Stop Hook] decision: "allow" (컨텍스트 리프레시)
    │
    ▼
[세션 종료] → Supervisor가 감지
    │
    ▼
[Supervisor] 새 세션 시작
    │
    ▼
[SessionStart Hook] type: "startup" → 전체 상태 주입
    │
    ▼
[새 세션에서 미션 실행 계속]
```

### 7.2 Notification Hook → Supervisor → Slack 연계

```
[Claude Code] 유휴 상태 감지
    │
    ▼
[Notification Hook] run/notifications.json에 알림 기록
    │
    ▼
[Supervisor] 주기적으로 notifications.json 확인 (5초 간격)
    │
    ├── 새 알림 있음 → SlackClient.send_alert() 호출
    │                 → notification.sent = true 업데이트
    │
    └── 없음 → 다음 주기
```

### 7.3 Compaction 감지 흐름

```
[Claude Code] 컨텍스트 95% 도달 → Autocompaction 실행
    │
    ▼
[SessionStart Hook] type: "compact"
    │
    ├── 전체 상태 + Purpose 재주입 (드리프트 방지)
    ├── hook_state.compaction_count += 1
    │
    ▼
[다음 Stop Hook 호출 시]
    │
    ├── compaction_count >= threshold?
    │   │
    │   ├── Yes → decision: "allow" (새 세션으로 전환)
    │   │         compaction_count = 0 리셋
    │   │
    │   └── No → 정상 미션 주입 계속
```

---

## 8. 설정 가능 파라미터

`state/config.toml`에서 훅 동작을 제어하는 파라미터:

```toml
context_refresh_after_compactions = 5
proactive_improvement_interval = 10
friction_threshold = 3

[stop_hook]
max_invocations_per_session = 50
completion_indicators = ["완료", "completed", "성공", "달성", "마무리"]
enabled = true

[session_start_hook]
max_friction_count = 5
max_recent_completed = 10
enabled = true

[notification_hook]
max_stored_notifications = 100
enabled = true
```

이 값들은 Claude Code의 자기개선 과정에서 수정될 수 있다 (요구사항 S-5).

---

## 9. 에러 처리

### 9.1 훅 실행 실패 시 기본 동작

| 훅 | 실패 시 기본 동작 | 근거 |
|----|-------------------|------|
| Stop Hook | allow (세션 종료 허용) | 안전한 방향으로. Supervisor가 새 세션 시작 |
| SessionStart Hook | 빈 컨텍스트 | 세션은 CLAUDE.md만으로도 동작 가능 |
| Notification Hook | 무시 | 알림 누락은 치명적이지 않음 |

### 9.2 파일 I/O 에러

```python
def load_json(path: Path) -> dict:
    """
    JSON 파일을 안전하게 로드.

    에러 처리:
    - FileNotFoundError: 빈 dict 반환 (초기 상태)
    - JSONDecodeError: 빈 dict 반환 + 로그 경고
    - PermissionError: 빈 dict 반환 + 로그 에러
    """
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        logger.warning("JSON 파싱 실패 (%s): %s", path, e)
        return {}
    except PermissionError as e:
        logger.error("파일 접근 불가 (%s): %s", path, e)
        return {}
```

### 9.3 원자적 파일 쓰기

훅이 상태 파일을 업데이트할 때는 반드시 원자적 쓰기를 사용한다:

```python
def save_json(path: Path, data: dict) -> None:
    """
    원자적 JSON 파일 쓰기.

    1. 임시 파일(.tmp)에 쓰기
    2. rename으로 원본 교체 (atomic on POSIX)
    → 중간에 크래시해도 파일이 깨지지 않음
    """
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.rename(path)
```

---

## 10. 테스트 전략

### 10.1 단위 테스트

```python
# tests/test_hooks.py

class TestStopHook:
    """Stop Hook 단위 테스트."""

    def test_allows_when_stop_hook_active(self): ...
    def test_allows_after_max_invocations(self): ...
    def test_blocks_with_next_mission(self): ...
    def test_blocks_for_mission_generation(self): ...
    def test_blocks_for_proactive_improvement(self): ...
    def test_allows_for_context_refresh(self): ...
    def test_selects_highest_priority_mission(self): ...
    def test_respects_mission_dependencies(self): ...
    def test_detects_mission_completion(self): ...
    def test_resets_counter_on_new_session(self): ...


class TestSessionStartHook:
    """SessionStart Hook 단위 테스트."""

    def test_startup_injects_full_context(self): ...
    def test_resume_injects_changed_context(self): ...
    def test_compact_includes_purpose_warning(self): ...
    def test_compact_increments_compaction_count(self): ...
    def test_handles_missing_state_files(self): ...


class TestNotificationHook:
    """Notification Hook 단위 테스트."""

    def test_idle_prompt_writes_notification(self): ...
    def test_permission_prompt_logs_warning(self): ...
    def test_auth_success_logs_info(self): ...
    def test_notification_file_max_entries(self): ...
```

### 10.2 통합 테스트

```python
# tests/test_hooks_integration.py

class TestHookIntegration:
    """훅 시스템 통합 테스트 (subprocess로 실제 훅 실행)."""

    def test_stop_hook_stdin_stdout_protocol(self): ...
    def test_stop_hook_continuous_mission_loop(self): ...
    def test_session_start_hook_all_types(self): ...
    def test_hooks_with_missing_state_files(self): ...
    def test_hooks_with_corrupt_json(self): ...
    def test_hook_timeout_behavior(self): ...
```
