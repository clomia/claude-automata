"""CognitiveLoadTrigger + StreamAnalyzer 테스트."""

from __future__ import annotations

import json
from pathlib import Path

from system.cognitive_load import (
    CognitiveLoadTrigger,
    StreamAnalyzer,
    prepare_trigger_context,
)


class TestCognitiveLoadTrigger:
    def test_empty_protocol(self) -> None:
        clt = CognitiveLoadTrigger()
        result = clt.generate_mission_protocol(
            mission={"id": "M-001", "title": "테스트"},
            health_metrics={},
            friction_history=[],
        )
        assert isinstance(result["phase2"], list)
        assert isinstance(result["phase3"], list)

    def test_friction_triggers_phase2(self) -> None:
        clt = CognitiveLoadTrigger()
        result = clt.generate_mission_protocol(
            mission={
                "id": "M-001",
                "title": "auth 모듈 구현",
                "description": "인증 모듈",
            },
            health_metrics={},
            friction_history=[
                {
                    "type": "error",
                    "pattern_key": "auth_failure",
                    "source_mission_id": "M-001",
                }
            ],
        )
        assert len(result["phase2"]) > 0
        assert "friction" in result["phase2"][0]

    def test_stalled_mission_triggers_phase2(self) -> None:
        clt = CognitiveLoadTrigger()
        result = clt.generate_mission_protocol(
            mission={"id": "M-005", "title": "정체 미션"},
            health_metrics={"stalled_mission_id": "M-005"},
            friction_history=[],
        )
        assert len(result["phase2"]) > 0
        assert "정체" in result["phase2"][0]

    def test_increasing_friction_triggers_phase3(self) -> None:
        clt = CognitiveLoadTrigger()
        result = clt.generate_mission_protocol(
            mission={"id": "M-001", "title": "테스트"},
            health_metrics={"friction_trend": "increasing"},
            friction_history=[],
        )
        assert len(result["phase3"]) > 0
        assert "증가" in result["phase3"][0]

    def test_build_mission_prompt_structure(self) -> None:
        clt = CognitiveLoadTrigger()
        prompt = clt.build_mission_prompt(
            mission={
                "id": "M-001",
                "title": "테스트 미션",
                "description": "설명",
                "success_criteria": ["기준1", "기준2"],
            },
            context="## 시스템 상태",
            health_metrics={},
            friction_history=[],
        )
        assert "M-001" in prompt
        assert "테스트 미션" in prompt
        assert "1단계" in prompt
        assert "2단계" in prompt
        assert "3단계" in prompt
        assert "4단계" in prompt
        assert "session-summary.md" in prompt


class TestStreamAnalyzer:
    def test_process_tool_use(self) -> None:
        sa = StreamAnalyzer()
        sa.process_event(
            {
                "type": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Read",
                        "input": {"file_path": "/src/main.py"},
                    }
                ],
            }
        )

        assert sa.tool_call_count == 1
        assert sa.tool_distribution["Read"] == 1
        assert "/src/main.py" in sa.files_read

    def test_process_edit(self) -> None:
        sa = StreamAnalyzer()
        sa.process_event(
            {
                "type": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Edit",
                        "input": {"file_path": "/src/app.py"},
                    }
                ],
            }
        )

        assert "/src/app.py" in sa.files_written

    def test_process_bash_test(self) -> None:
        sa = StreamAnalyzer()
        sa.process_event(
            {
                "type": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": "uv run pytest"},
                    }
                ],
            }
        )

        assert sa.tests_executed is True
        assert "uv run pytest" in sa.bash_commands

    def test_to_dict(self) -> None:
        sa = StreamAnalyzer()
        sa.process_event(
            {
                "type": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Read",
                        "input": {"file_path": "system/main.py"},
                    }
                ],
            }
        )

        d = sa.to_dict()
        assert d["tool_call_count"] == 1
        assert "system/main.py" in d["files_read"]
        assert d["duration_minutes"] >= 0

    def test_save(self, tmp_path: Path) -> None:
        sa = StreamAnalyzer()
        filepath = tmp_path / "analysis.json"
        sa.save(filepath)

        data = json.loads(filepath.read_text())
        assert "tool_call_count" in data


class TestPrepareTriggerContext:
    def test_creates_file(self, tmp_path: Path) -> None:
        output_path = tmp_path / "trigger-context.json"
        prepare_trigger_context(
            mission={
                "id": "M-042",
                "description": "API 인증 모듈 구현",
            },
            session_analysis={
                "files_read": ["system/auth.py"],
                "files_written": ["system/auth.py", "tests/test_auth.py"],
            },
            output_path=output_path,
        )

        assert output_path.exists()
        data = json.loads(output_path.read_text())
        assert data["mission_id"] == "M-042"
        assert "system/auth.py" in data["files_changed"]
        assert "tests/test_auth.py" in data["files_changed"]
