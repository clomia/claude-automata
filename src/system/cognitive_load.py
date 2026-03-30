"""
인지 부하 트리거 모듈.

두 가지 클래스를 제공한다:
1. CognitiveLoadTrigger — 미션 프롬프트의 인지 부하 내용 생성 (자기 주도 계층)
2. StreamAnalyzer — stream-json 이벤트에서 작업 패턴 추출 (Supervisor 모니터링용)

참조 요구사항: Q-3, Q-4
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class CognitiveLoadTrigger:
    """미션 프롬프트의 인지 부하 내용을 생성한다."""

    def generate_mission_protocol(
        self,
        mission: dict[str, Any],
        health_metrics: dict[str, Any],
        friction_history: list[dict[str, Any]],
    ) -> dict[str, list[str]]:
        """미션 특화 검증/확장 지시를 생성한다."""
        phase2: list[str] = []
        phase3: list[str] = []

        # 유사 미션의 friction 이력 기반
        related = [
            f
            for f in friction_history
            if self._is_related(f, mission)
        ]
        if related:
            types = sorted({f.get("type", "unknown") for f in related})
            phase2.append(
                f"유사 미션에서 {', '.join(types)} friction이 "
                f"발생한 이력이 있다. 이 영역을 특히 주의하여 검증하라."
            )

        # 건강 메트릭 기반
        if health_metrics.get("friction_trend") == "increasing":
            phase3.append(
                "시스템 friction이 증가 추세이다. "
                "이 미션의 결과가 friction을 줄이는 방향인지 확인하라."
            )

        stalled = health_metrics.get("stalled_mission_id")
        if stalled and stalled == mission.get("id"):
            phase2.append(
                "이 미션이 이전 세션에서 정체되었다. "
                "이전과 다른 접근법을 시도하라."
            )

        short_sessions = health_metrics.get("short_sessions_recent", 0)
        if short_sessions >= 3:
            phase3.append(
                "최근 세션이 반복적으로 짧게 종료되고 있다. "
                "근본 원인이 이 미션과 관련이 있는지 탐색하라."
            )

        return {"phase2": phase2, "phase3": phase3}

    def build_mission_prompt(
        self,
        mission: dict[str, Any],
        context: str,
        health_metrics: dict[str, Any],
        friction_history: list[dict[str, Any]],
    ) -> str:
        """미션 실행 프롬프트를 4단계 프로토콜로 구성한다."""
        protocol = self.generate_mission_protocol(
            mission, health_metrics, friction_history
        )

        phase2_extra = ""
        if protocol["phase2"]:
            phase2_extra = (
                "\n  " + "\n  ".join(protocol["phase2"])
            )

        phase3_extra = ""
        if protocol["phase3"]:
            phase3_extra = (
                "\n  " + "\n  ".join(protocol["phase3"])
            )

        success_criteria = mission.get("success_criteria", [])
        criteria_text = "\n".join(
            f"  - {c}" for c in success_criteria
        )

        return f"""당신은 claude-automata 시스템의 AI 에이전트입니다.

## 현재 상태
{context}

## 미션: {mission.get('id', '?')} {mission.get('title', '?')}

### 목표
{mission.get('description', '(설명 없음)')}

### 성공 기준
{criteria_text}

### 실행 프로토콜

이 미션을 다음 단계로 실행하라. 각 단계를 건너뛰지 마라.

**1단계 — 실행**: 성공 기준을 달성하라.

**2단계 — 검증**: 성공 기준 각 항목을 개별적으로 대조 확인하라.
  달성 여부가 불확실한 항목이 있으면 추가 작업하라.{phase2_extra}

**3단계 — 미탐색 영역**: 이 접근법의 약점 3가지를 식별하고 대응하라.{phase3_extra}

**4단계 — 요약**: state/session-summary.md에 다음을 기록하라:
  - 이 미션에서 취한 접근법과 그 이유
  - 가장 불확실했던 결정 3가지와 근거
  - 검토했지만 채택하지 않은 대안과 기각 이유
  - 타협한 부분과 이유

이 session-summary.md는 다음 세션의 컨텍스트 보존과 인지 부하 트리거의 핵심 입력이다."""

    def _is_related(
        self,
        friction: dict[str, Any],
        mission: dict[str, Any],
    ) -> bool:
        """friction이 미션과 관련 있는지 판단한다."""
        friction_mission = friction.get("source_mission_id", "")
        if friction_mission == mission.get("id"):
            return True

        friction_key = friction.get("pattern_key", "")
        mission_title = mission.get("title", "").lower()
        mission_desc = mission.get("description", "").lower()

        if friction_key:
            parts = friction_key.replace("_", " ").split()
            return any(
                p in mission_title or p in mission_desc for p in parts
            )
        return False


class StreamAnalyzer:
    """
    stream-json 이벤트에서 작업 패턴을 실시간 추출한다.

    Supervisor의 세션 모니터링, ErrorClassifier 입력,
    friction 감지, trigger-context.json 생성의 원천 데이터.
    """

    def __init__(self) -> None:
        self.tool_call_count: int = 0
        self.tool_distribution: dict[str, int] = {}
        self.files_read: list[str] = []
        self.files_written: list[str] = []
        self.errors: list[dict[str, Any]] = []
        self.error_count: int = 0
        self.tests_executed: bool = False
        self.bash_commands: list[str] = []
        self.start_time: float = time.time()
        self._events: list[dict[str, Any]] = []

    def process_event(self, event: dict[str, Any]) -> None:
        """stream-json 이벤트를 처리하고 통계를 갱신한다."""
        self._events.append(event)
        event_type = event.get("type", "")

        if event_type == "assistant":
            self._process_assistant_event(event)

    def _process_assistant_event(
        self, event: dict[str, Any]
    ) -> None:
        content_list = event.get("content", [])
        if not isinstance(content_list, list):
            return

        for content in content_list:
            content_type = content.get("type", "")

            if content_type == "tool_use":
                self._process_tool_use(content)
            elif content_type == "tool_result":
                self._process_tool_result(content)

    def _process_tool_use(self, content: dict[str, Any]) -> None:
        tool_name = content.get("name", "unknown")
        self.tool_call_count += 1
        self.tool_distribution[tool_name] = (
            self.tool_distribution.get(tool_name, 0) + 1
        )

        tool_input = content.get("input", {})

        if tool_name in ("Read", "Glob"):
            path = tool_input.get("file_path") or tool_input.get(
                "path", ""
            )
            if path and path not in self.files_read:
                self.files_read.append(path)

        elif tool_name in ("Edit", "Write"):
            path = tool_input.get("file_path", "")
            if path and path not in self.files_written:
                self.files_written.append(path)

        elif tool_name == "Bash":
            cmd = tool_input.get("command", "")
            if cmd:
                self.bash_commands.append(cmd[:100])
                if "pytest" in cmd or "test" in cmd:
                    self.tests_executed = True

    def _process_tool_result(
        self, content: dict[str, Any]
    ) -> None:
        if content.get("is_error"):
            self.error_count += 1
            self.errors.append(
                {
                    "tool": content.get("name", "unknown"),
                    "error": str(content.get("content", ""))[:200],
                    "timestamp": time.time() - self.start_time,
                }
            )

    def to_dict(self) -> dict[str, Any]:
        """분석 결과를 딕셔너리로 반환한다."""
        files_read_not_written = [
            f for f in self.files_read if f not in self.files_written
        ]

        topic_areas: dict[str, int] = {}
        for path in self.files_read + self.files_written:
            parts = path.split("/")
            if len(parts) >= 2:
                area = parts[0] + "/"
                topic_areas[area] = topic_areas.get(area, 0) + 1

        return {
            "tool_call_count": self.tool_call_count,
            "tool_distribution": self.tool_distribution,
            "files_read": self.files_read,
            "files_written": self.files_written,
            "files_read_not_written": files_read_not_written,
            "errors": self.errors,
            "error_count": self.error_count,
            "tests_executed": self.tests_executed,
            "bash_commands": self.bash_commands,
            "duration_minutes": (time.time() - self.start_time) / 60,
            "topic_areas": topic_areas,
        }

    def save(self, filepath: Path) -> None:
        """분석 결과를 JSON 파일로 저장한다."""
        import json
        import tempfile
        import os

        data = self.to_dict()
        dir_path = filepath.parent
        dir_path.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=str(dir_path), suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, str(filepath))
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise


def prepare_trigger_context(
    mission: dict[str, Any],
    session_analysis: dict[str, Any],
    output_path: Path,
) -> None:
    """Stop Hook Agent를 위한 최소 컨텍스트를 생성한다."""
    import json
    import tempfile
    import os

    context = {
        "mission_id": mission.get("id", ""),
        "mission_description": mission.get("description", ""),
        "files_changed": sorted(
            set(session_analysis.get("files_read", []))
            | set(session_analysis.get("files_written", []))
        ),
    }

    dir_path = output_path.parent
    dir_path.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(dir_path), suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(context, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(output_path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
