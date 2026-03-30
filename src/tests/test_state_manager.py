"""StateManager 단위 테스트."""

from __future__ import annotations

import json
from pathlib import Path

from system.state_manager import StateManager


class TestAtomicIO:
    def test_atomic_write_and_read(self, tmp_project: Path) -> None:
        sm = StateManager(tmp_project)
        data = {"key": "value", "number": 42}
        filepath = tmp_project / "state" / "test.json"
        sm.atomic_write(filepath, data)

        result = sm.atomic_read(filepath)
        assert result == data

    def test_atomic_read_missing_file(self, tmp_project: Path) -> None:
        sm = StateManager(tmp_project)
        result = sm.atomic_read(
            tmp_project / "state" / "nonexistent.json",
            default={"default": True},
        )
        assert result == {"default": True}

    def test_atomic_read_corrupted_json(self, tmp_project: Path) -> None:
        sm = StateManager(tmp_project)
        filepath = tmp_project / "state" / "corrupt.json"
        filepath.write_text("{invalid json", encoding="utf-8")

        result = sm.atomic_read(filepath, default={"fallback": True})
        assert result == {"fallback": True}
        # 손상 파일이 백업됨
        backups = list(filepath.parent.glob("corrupt.corrupted.*"))
        assert len(backups) == 1


class TestPurpose:
    def test_load_and_save(self, tmp_project: Path) -> None:
        sm = StateManager(tmp_project)
        purpose = sm.load_purpose()
        assert purpose["purpose"] == "테스트 시스템을 지속적으로 개선한다"

        purpose["purpose"] = "새로운 방향"
        sm.save_purpose(purpose)

        reloaded = sm.load_purpose()
        assert reloaded["purpose"] == "새로운 방향"


class TestMissions:
    def test_add_mission(self, tmp_project: Path) -> None:
        sm = StateManager(tmp_project)
        mid = sm.add_mission(
            {
                "title": "테스트 미션",
                "description": "설명",
                "success_criteria": ["기준1"],
                "priority": 1,
                "source": "purpose",
            }
        )

        assert mid == "M-001"
        missions = sm.load_missions()
        assert len(missions["missions"]) == 1
        assert missions["missions"][0]["title"] == "테스트 미션"
        assert missions["next_id"] == 2

    def test_get_next_mission_priority(self, tmp_project: Path) -> None:
        sm = StateManager(tmp_project)
        sm.add_mission(
            {
                "title": "낮은 우선순위",
                "description": "",
                "success_criteria": [],
                "priority": 5,
                "source": "self",
            }
        )
        sm.add_mission(
            {
                "title": "높은 우선순위",
                "description": "",
                "success_criteria": [],
                "priority": 0,
                "source": "friction",
            }
        )

        next_m = sm.get_next_mission()
        assert next_m is not None
        assert next_m["title"] == "높은 우선순위"

    def test_get_next_mission_respects_dependencies(
        self, tmp_project: Path
    ) -> None:
        sm = StateManager(tmp_project)
        sm.add_mission(
            {
                "title": "첫 번째",
                "description": "",
                "success_criteria": [],
                "priority": 2,
                "source": "self",
            }
        )
        sm.add_mission(
            {
                "title": "두 번째 (의존)",
                "description": "",
                "success_criteria": [],
                "priority": 1,
                "source": "self",
                "dependencies": ["M-001"],
            }
        )

        # M-001이 pending이므로 M-002는 선택 불가, M-001 선택
        next_m = sm.get_next_mission()
        assert next_m is not None
        assert next_m["id"] == "M-001"

    def test_complete_mission(self, tmp_project: Path) -> None:
        sm = StateManager(tmp_project)
        mid = sm.add_mission(
            {
                "title": "완료될 미션",
                "description": "",
                "success_criteria": [],
                "priority": 1,
                "source": "self",
            }
        )

        sm.complete_mission(mid, "성공적으로 완료")
        missions = sm.load_missions()
        m = missions["missions"][0]
        assert m["status"] == "completed"
        assert m["result_summary"] == "성공적으로 완료"
        assert m["completed_at"] is not None

    def test_block_and_unblock(self, tmp_project: Path) -> None:
        sm = StateManager(tmp_project)
        mid = sm.add_mission(
            {
                "title": "차단될 미션",
                "description": "",
                "success_criteria": [],
                "priority": 1,
                "source": "self",
            }
        )

        sm.block_mission(
            mid,
            {
                "id": "BLK-001",
                "type": "owner_input",
                "description": "API 토큰 필요",
            },
        )

        missions = sm.load_missions()
        assert missions["missions"][0]["status"] == "blocked"

        # blocked 미션은 선택 불가
        assert sm.get_next_mission() is None

        sm.unblock_mission(mid, "BLK-001")
        missions = sm.load_missions()
        assert missions["missions"][0]["status"] == "pending"

    def test_fail_mission(self, tmp_project: Path) -> None:
        sm = StateManager(tmp_project)
        mid = sm.add_mission(
            {
                "title": "실패할 미션",
                "description": "",
                "success_criteria": [],
                "priority": 1,
                "source": "self",
            }
        )

        sm.fail_mission(mid, "복구 불가능한 에러")
        missions = sm.load_missions()
        assert missions["missions"][0]["status"] == "failed"


class TestFriction:
    def test_add_friction(self, tmp_project: Path) -> None:
        sm = StateManager(tmp_project)
        fid = sm.add_friction(
            {
                "type": "error",
                "pattern_key": "test_error",
                "description": "테스트 에러",
                "severity": "medium",
            }
        )

        assert fid == "F-001"
        friction = sm.load_friction()
        assert len(friction["frictions"]) == 1

    def test_unresolved_count(self, tmp_project: Path) -> None:
        sm = StateManager(tmp_project)
        for i in range(3):
            sm.add_friction(
                {
                    "type": "error",
                    "pattern_key": "same_pattern",
                    "description": f"에러 {i}",
                    "severity": "medium",
                }
            )

        assert sm.get_unresolved_friction_count("same_pattern") == 3
        assert sm.get_unresolved_friction_count("other") == 0

    def test_resolve_friction(self, tmp_project: Path) -> None:
        sm = StateManager(tmp_project)
        fid = sm.add_friction(
            {
                "type": "error",
                "pattern_key": "resolve_test",
                "description": "해소 테스트",
                "severity": "low",
            }
        )

        sm.resolve_friction(fid, "수정 완료")
        assert sm.get_unresolved_friction_count("resolve_test") == 0


class TestRequests:
    def test_add_and_answer(self, tmp_project: Path) -> None:
        sm = StateManager(tmp_project)
        rid = sm.add_request(
            {
                "type": "question",
                "question": "API 토큰을 발급해주세요",
            }
        )

        assert rid == "R-001"
        pending = sm.get_pending_requests()
        assert len(pending) == 1

        sm.answer_request(rid, "ghp_xxxx1234")
        pending = sm.get_pending_requests()
        assert len(pending) == 0


class TestConfig:
    def test_load_config(self, tmp_project: Path) -> None:
        sm = StateManager(tmp_project)
        config = sm.load_config()
        assert config["friction_threshold"] == 3
        assert config["all_thresholds_modifiable"] is True

    def test_load_config_with_defaults(self, tmp_project: Path) -> None:
        sm = StateManager(tmp_project)
        (tmp_project / "state" / "config.toml").unlink()
        config = sm.load_config()
        assert config["friction_threshold"] == 3
        assert config["session_timeout_minutes"] == 120


class TestSessionContext:
    def test_create_session_context(self, tmp_project: Path) -> None:
        sm = StateManager(tmp_project)
        sm.add_mission(
            {
                "title": "테스트 미션",
                "description": "설명",
                "success_criteria": ["기준"],
                "priority": 1,
                "source": "purpose",
            }
        )

        context = sm.create_session_context()
        assert "시스템 상태 요약" in context
        assert "테스트 시스템을 지속적으로 개선한다" in context
        assert "테스트 미션" in context


class TestCrashRecovery:
    def test_recover_resets_in_progress(self, tmp_project: Path) -> None:
        sm = StateManager(tmp_project)
        mid = sm.add_mission(
            {
                "title": "진행 중 미션",
                "description": "",
                "success_criteria": [],
                "priority": 1,
                "source": "self",
            }
        )

        # in_progress로 수동 변경
        missions = sm.load_missions()
        missions["missions"][0]["status"] = "in_progress"
        sm.save_missions(missions)

        # current_session.json 생성 (크래시 시뮬레이션)
        sm.set_current_session("test-session-id", mid)

        recovery = sm.recover_from_crash()
        assert recovery is not None
        assert mid in recovery["reset_missions"]

        # 미션이 pending으로 리셋됨
        missions = sm.load_missions()
        assert missions["missions"][0]["status"] == "pending"


class TestArchiveRotation:
    def test_rotate_missions(self, tmp_project: Path) -> None:
        sm = StateManager(tmp_project)
        for i in range(15):
            mid = sm.add_mission(
                {
                    "title": f"미션 {i}",
                    "description": "",
                    "success_criteria": [],
                    "priority": 1,
                    "source": "self",
                }
            )
            sm.complete_mission(mid, f"결과 {i}")

        archived = sm.rotate_missions()
        assert archived == 5  # 15 완료 - 10 유지 = 5 아카이브

        missions = sm.load_missions()
        completed = [
            m
            for m in missions["missions"]
            if m["status"] == "completed"
        ]
        assert len(completed) == 10
