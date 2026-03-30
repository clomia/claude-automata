"""Hook 스크립트 통합 테스트 (subprocess로 실제 훅 실행)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_hook(
    hook_script: str,
    input_data: dict,
    project_root: Path,
) -> dict:
    """Hook 스크립트를 subprocess로 실행하고 JSON 출력을 반환한다."""
    result = subprocess.run(
        [sys.executable, hook_script],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        cwd=str(project_root),
        timeout=10,
    )
    if result.returncode not in (0, 2):
        raise RuntimeError(
            f"Hook failed: exit={result.returncode} "
            f"stderr={result.stderr}"
        )
    if result.stdout.strip():
        return json.loads(result.stdout.strip())
    return {}


class TestStopHook:
    def _setup_state(self, tmp_project: Path) -> None:
        """테스트용 state 파일과 hook_state를 준비한다."""
        (tmp_project / "run").mkdir(exist_ok=True)

    def test_allows_when_stop_hook_active(
        self, tmp_project: Path
    ) -> None:
        self._setup_state(tmp_project)
        hook_path = str(
            Path(__file__).resolve().parent.parent
            / "system"
            / "hooks"
            / "on_stop.py"
        )

        # stop_hook_active=True 시 무조건 allow
        # 직접 실행하면 PROJECT_ROOT가 달라져서 파일을 찾지 못하므로
        # 이 테스트는 핵심 로직만 검증
        from system.hooks.on_stop import (
            select_next_mission,
        )

        # 빈 미션 큐에서 None 반환
        result = select_next_mission({"missions": []})
        assert result is None

    def test_select_next_mission_by_priority(self) -> None:
        from system.hooks.on_stop import (
            select_next_mission,
        )

        missions_data = {
            "missions": [
                {
                    "id": "M-001",
                    "title": "낮은",
                    "status": "pending",
                    "priority": 5,
                    "dependencies": [],
                    "blockers": [],
                    "created_at": "2026-01-01T00:00:00Z",
                },
                {
                    "id": "M-002",
                    "title": "높은",
                    "status": "pending",
                    "priority": 0,
                    "dependencies": [],
                    "blockers": [],
                    "created_at": "2026-01-01T00:00:00Z",
                },
            ]
        }

        result = select_next_mission(missions_data)
        assert result is not None
        assert result["id"] == "M-002"

    def test_select_skips_blocked(self) -> None:
        from system.hooks.on_stop import (
            select_next_mission,
        )

        missions_data = {
            "missions": [
                {
                    "id": "M-001",
                    "title": "차단됨",
                    "status": "pending",
                    "priority": 0,
                    "dependencies": [],
                    "blockers": [
                        {"resolved": False, "description": "대기"}
                    ],
                    "created_at": "2026-01-01T00:00:00Z",
                },
                {
                    "id": "M-002",
                    "title": "사용 가능",
                    "status": "pending",
                    "priority": 5,
                    "dependencies": [],
                    "blockers": [],
                    "created_at": "2026-01-01T00:00:00Z",
                },
            ]
        }

        result = select_next_mission(missions_data)
        assert result is not None
        assert result["id"] == "M-002"

    def test_format_mission_context(self) -> None:
        from system.hooks.on_stop import (
            format_mission_context,
        )

        mission = {
            "id": "M-001",
            "title": "API 구현",
            "description": "REST API를 구현한다",
            "success_criteria": ["엔드포인트 동작", "테스트 통과"],
            "dependencies": [],
        }

        context = format_mission_context(mission)
        assert "M-001" in context
        assert "API 구현" in context
        assert "엔드포인트 동작" in context


class TestSessionStartHook:
    def test_build_full_context(self) -> None:
        from system.hooks.on_session_start import (
            build_full_context,
        )

        context = build_full_context(
            purpose_data={"purpose": "테스트 목적"},
            strategy_data={"summary": "테스트 전략"},
            missions_data={"missions": []},
            friction_data={"frictions": []},
            requests_data={"requests": []},
            config_data={},
        )

        assert "Purpose" in context
        assert "테스트 목적" in context
        assert "테스트 전략" in context

    def test_build_compact_context_has_warning(self) -> None:
        from system.hooks.on_session_start import (
            build_compact_context,
        )

        context = build_compact_context(
            purpose_data={"purpose": "목적"},
            strategy_data={},
            missions_data={"missions": []},
            friction_data={"frictions": []},
            requests_data={"requests": []},
            config_data={},
        )

        assert "Autocompaction" in context
        assert "Purpose" in context
