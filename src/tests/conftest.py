"""공용 test fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """임시 프로젝트 디렉토리를 생성한다."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    (state_dir / "archive").mkdir()
    (tmp_path / "run").mkdir()
    (tmp_path / "logs").mkdir()

    # 빈 상태 파일 초기화
    (state_dir / "purpose.json").write_text(
        json.dumps(
            {
                "raw_input": "테스트 목적",
                "purpose": "테스트 시스템을 지속적으로 개선한다",
                "domain": "testing",
                "key_directions": ["테스트 자동화"],
                "constructed_at": "2026-03-25T10:00:00Z",
                "last_evolved_at": "2026-03-25T10:00:00Z",
                "evolution_history": [],
            },
            ensure_ascii=False,
        )
    )
    (state_dir / "missions.json").write_text(
        json.dumps(
            {
                "missions": [],
                "next_id": 1,
                "metadata": {
                    "total_created": 0,
                    "total_completed": 0,
                    "total_failed": 0,
                    "total_blocked": 0,
                },
            }
        )
    )
    (state_dir / "friction.json").write_text(
        json.dumps({"frictions": [], "next_id": 1})
    )
    (state_dir / "requests.json").write_text(
        json.dumps({"requests": [], "next_id": 1})
    )
    (state_dir / "sessions.json").write_text(
        json.dumps({"sessions": []})
    )
    (state_dir / "strategy.json").write_text(json.dumps({}))
    (state_dir / "config.toml").write_text(
        "friction_threshold = 3\n"
        "proactive_improvement_interval = 10\n"
        "context_refresh_after_compactions = 5\n"
        "goal_drift_check_interval = 20\n"
        "session_timeout_minutes = 120\n"
        "max_consecutive_failures = 3\n"
        'slack_notification_level = "warning"\n'
        "mission_idle_generation_count = 3\n"
        "owner_feedback_interval = 20\n"
        "all_thresholds_modifiable = true\n"
    )

    return tmp_path
