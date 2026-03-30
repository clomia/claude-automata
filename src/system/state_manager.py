"""
파일 기반 상태 영속화 관리자.

모든 상태 파일(state/)의 읽기/쓰기를 원자적으로 수행하고,
Git 체크포인트를 통해 복구 지점을 생성한다.

참조 요구사항: C-2 (파일 기반), C-3 (복구 지점), E-2 (장애 불멸)
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import tomllib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "session_timeout_minutes": 120,
    "max_consecutive_failures": 3,
    "friction_threshold": 3,
    "proactive_improvement_interval": 10,
    "context_refresh_after_compactions": 5,
    "goal_drift_check_interval": 20,
    "slack_notification_level": "warning",
    "mission_idle_generation_count": 3,
    "owner_feedback_interval": 20,
    "max_retry_attempts": 5,
    "backoff_base_seconds": 1.0,
    "backoff_max_seconds": 60.0,
    "all_thresholds_modifiable": True,
}


@dataclass
class StateManager:
    """
    파일 기반 상태 영속화 관리자.

    모든 상태 파일의 읽기/쓰기를 원자적으로 수행하고,
    Git 체크포인트를 통해 복구 지점을 생성한다.
    """

    project_dir: Path
    state_dir: Path = field(init=False)
    run_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        self.state_dir = self.project_dir / "state"
        self.run_dir = self.project_dir / "run"
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.state_dir / "archive").mkdir(parents=True, exist_ok=True)

    # ── 원자적 파일 연산 ──────────────────────────────────────

    def atomic_write(self, filepath: Path, data: dict[str, Any]) -> None:
        """
        원자적 파일 쓰기.

        같은 디렉토리에 임시 파일을 생성하여 데이터를 쓴 후,
        os.replace로 원자적으로 대상 파일을 교체한다.
        """
        dir_path = filepath.parent
        dir_path.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=str(dir_path),
            prefix=f".{filepath.name}.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, str(filepath))
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def atomic_read(
        self, filepath: Path, default: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        상태 파일 읽기. 파일이 없으면 default 반환.
        JSON 손상 시 백업 후 default 반환.
        """
        if default is None:
            default = {}
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return default.copy()
        except json.JSONDecodeError:
            backup_path = filepath.with_suffix(f".corrupted.{int(time.time())}")
            try:
                os.replace(str(filepath), str(backup_path))
            except OSError:
                pass
            return default.copy()

    # ── Purpose ───────────────────────────────────────────────

    def load_purpose(self) -> dict[str, Any]:
        return self.atomic_read(self.state_dir / "purpose.json")

    def save_purpose(self, purpose: dict[str, Any]) -> None:
        self.atomic_write(self.state_dir / "purpose.json", purpose)

    # ── Strategy ──────────────────────────────────────────────

    def load_strategy(self) -> dict[str, Any]:
        return self.atomic_read(self.state_dir / "strategy.json")

    def save_strategy(self, strategy: dict[str, Any]) -> None:
        self.atomic_write(self.state_dir / "strategy.json", strategy)

    # ── Mission Queue ─────────────────────────────────────────

    def load_missions(self) -> dict[str, Any]:
        return self.atomic_read(
            self.state_dir / "missions.json",
            default={
                "missions": [],
                "next_id": 1,
                "metadata": {
                    "total_created": 0,
                    "total_completed": 0,
                    "total_failed": 0,
                    "total_blocked": 0,
                },
            },
        )

    def save_missions(self, missions: dict[str, Any]) -> None:
        self.atomic_write(self.state_dir / "missions.json", missions)

    def get_next_mission(self) -> dict[str, Any] | None:
        """
        다음으로 실행할 미션을 반환한다.

        선택 기준:
        1. status=pending, 2. 의존성 충족, 3. blocker 없음,
        4. priority 최소, 5. created_at 최조
        """
        queue = self.load_missions()
        missions = queue["missions"]
        completed_ids = {
            m["id"] for m in missions if m["status"] == "completed"
        }

        candidates = []
        for mission in missions:
            if mission["status"] != "pending":
                continue
            deps = mission.get("dependencies", [])
            if deps and not all(d in completed_ids for d in deps):
                continue
            blockers = mission.get("blockers", [])
            active_blockers = [
                b for b in blockers if not b.get("resolved", False)
            ]
            if active_blockers:
                continue
            candidates.append(mission)

        if not candidates:
            return None

        candidates.sort(
            key=lambda m: (m.get("priority", 999), m.get("created_at", ""))
        )
        return candidates[0]

    def add_mission(self, mission: dict[str, Any]) -> str:
        queue = self.load_missions()
        next_id = queue["next_id"]
        mission_id = f"M-{next_id:03d}"

        mission["id"] = mission_id
        mission.setdefault("status", "pending")
        mission.setdefault("blockers", [])
        mission.setdefault("dependencies", [])
        mission.setdefault("friction_ids", [])
        mission.setdefault("started_at", None)
        mission.setdefault("completed_at", None)
        mission.setdefault("session_id", None)
        mission.setdefault("result_summary", None)
        mission.setdefault(
            "created_at", datetime.now(timezone.utc).isoformat()
        )

        queue["missions"].append(mission)
        queue["next_id"] = next_id + 1
        queue["metadata"]["total_created"] = queue["metadata"].get(
            "total_created", 0
        ) + 1
        self.save_missions(queue)
        return mission_id

    def complete_mission(self, mission_id: str, result: str) -> None:
        queue = self.load_missions()
        mission = self._find_mission(queue, mission_id)
        mission["status"] = "completed"
        mission["result_summary"] = result
        mission["completed_at"] = datetime.now(timezone.utc).isoformat()
        queue["metadata"]["total_completed"] = (
            queue["metadata"].get("total_completed", 0) + 1
        )
        self.save_missions(queue)

    def fail_mission(self, mission_id: str, reason: str) -> None:
        queue = self.load_missions()
        mission = self._find_mission(queue, mission_id)
        mission["status"] = "failed"
        mission["result_summary"] = reason
        mission["completed_at"] = datetime.now(timezone.utc).isoformat()
        queue["metadata"]["total_failed"] = (
            queue["metadata"].get("total_failed", 0) + 1
        )
        self.save_missions(queue)

    def block_mission(
        self, mission_id: str, blocker: dict[str, Any]
    ) -> None:
        queue = self.load_missions()
        mission = self._find_mission(queue, mission_id)
        blocker.setdefault("resolved", False)
        blocker.setdefault(
            "created_at", datetime.now(timezone.utc).isoformat()
        )
        mission["blockers"].append(blocker)
        mission["status"] = "blocked"
        queue["metadata"]["total_blocked"] = (
            queue["metadata"].get("total_blocked", 0) + 1
        )
        self.save_missions(queue)

    def unblock_mission(
        self, mission_id: str, blocker_id: str | None = None
    ) -> None:
        queue = self.load_missions()
        mission = self._find_mission(queue, mission_id)

        if blocker_id:
            for blocker in mission["blockers"]:
                if blocker.get("id") == blocker_id:
                    blocker["resolved"] = True
                    blocker["resolved_at"] = (
                        datetime.now(timezone.utc).isoformat()
                    )
                    break
        else:
            for blocker in mission["blockers"]:
                blocker["resolved"] = True
                blocker["resolved_at"] = (
                    datetime.now(timezone.utc).isoformat()
                )

        if all(b.get("resolved", False) for b in mission["blockers"]):
            if mission.get("status") == "blocked":
                mission["status"] = "pending"
                queue["metadata"]["total_blocked"] = max(
                    0, queue["metadata"].get("total_blocked", 0) - 1
                )

        self.save_missions(queue)

    def _find_mission(
        self, queue: dict[str, Any], mission_id: str
    ) -> dict[str, Any]:
        for mission in queue["missions"]:
            if mission["id"] == mission_id:
                return mission
        raise ValueError(f"Mission not found: {mission_id}")

    # ── Friction ──────────────────────────────────────────────

    def load_friction(self) -> dict[str, Any]:
        return self.atomic_read(
            self.state_dir / "friction.json",
            default={"frictions": [], "next_id": 1},
        )

    def save_friction(self, friction_log: dict[str, Any]) -> None:
        self.atomic_write(self.state_dir / "friction.json", friction_log)

    def add_friction(self, friction: dict[str, Any]) -> str:
        log = self.load_friction()
        next_id = log["next_id"]
        friction_id = f"F-{next_id:03d}"

        friction["id"] = friction_id
        friction.setdefault("resolved_at", None)
        friction.setdefault("resolved_by", None)
        friction.setdefault("improvement_mission_id", None)
        friction.setdefault("occurrence_count", 1)
        friction.setdefault(
            "timestamp", datetime.now(timezone.utc).isoformat()
        )

        log["frictions"].append(friction)
        log["next_id"] = next_id + 1
        self.save_friction(log)
        return friction_id

    def resolve_friction(self, friction_id: str, resolution: str) -> None:
        log = self.load_friction()
        for friction in log["frictions"]:
            if friction["id"] == friction_id:
                friction["resolution"] = resolution
                friction["resolved_at"] = (
                    datetime.now(timezone.utc).isoformat()
                )
                self.save_friction(log)
                return
        raise ValueError(f"Friction not found: {friction_id}")

    def get_unresolved_friction_count(self, pattern_key: str) -> int:
        log = self.load_friction()
        return sum(
            1
            for f in log["frictions"]
            if f.get("pattern_key") == pattern_key
            and not f.get("resolved_at")
        )

    # ── Requests ──────────────────────────────────────────────

    def load_requests(self) -> dict[str, Any]:
        return self.atomic_read(
            self.state_dir / "requests.json",
            default={"requests": [], "next_id": 1},
        )

    def save_requests(self, data: dict[str, Any]) -> None:
        self.atomic_write(self.state_dir / "requests.json", data)

    def add_request(self, request: dict[str, Any]) -> str:
        data = self.load_requests()
        next_id = data["next_id"]
        request_id = f"R-{next_id:03d}"

        request["id"] = request_id
        request.setdefault("status", "pending")
        request.setdefault("answer", None)
        request.setdefault("slack_thread_ts", None)
        request.setdefault("answered_at", None)
        request.setdefault("timeout_minutes", 1440)
        request.setdefault(
            "created_at", datetime.now(timezone.utc).isoformat()
        )

        data["requests"].append(request)
        data["next_id"] = next_id + 1
        self.save_requests(data)
        return request_id

    def answer_request(self, request_id: str, answer: str) -> None:
        data = self.load_requests()
        for request in data["requests"]:
            if request["id"] == request_id:
                request["status"] = "answered"
                request["answer"] = answer
                request["answered_at"] = (
                    datetime.now(timezone.utc).isoformat()
                )
                self.save_requests(data)
                return
        raise ValueError(f"Request not found: {request_id}")

    def get_pending_requests(self) -> list[dict[str, Any]]:
        data = self.load_requests()
        return [
            r
            for r in data.get("requests", [])
            if r.get("status") == "pending"
        ]

    # ── Sessions ──────────────────────────────────────────────

    def load_sessions(self) -> dict[str, Any]:
        return self.atomic_read(
            self.state_dir / "sessions.json",
            default={"sessions": []},
        )

    def save_sessions(self, data: dict[str, Any]) -> None:
        self.atomic_write(self.state_dir / "sessions.json", data)

    def add_session(self, session: dict[str, Any]) -> None:
        data = self.load_sessions()
        session.setdefault(
            "started_at", datetime.now(timezone.utc).isoformat()
        )
        data["sessions"].append(session)
        self.save_sessions(data)

    def update_session(
        self, session_id: str, updates: dict[str, Any]
    ) -> None:
        data = self.load_sessions()
        for session in data["sessions"]:
            if session.get("id") == session_id:
                session.update(updates)
                self.save_sessions(data)
                return
        raise ValueError(f"Session not found: {session_id}")

    # ── Config ────────────────────────────────────────────────

    def load_config(self) -> dict[str, Any]:
        config_path = self.state_dir / "config.toml"
        try:
            with open(config_path, "rb") as f:
                config = tomllib.load(f)
        except FileNotFoundError:
            config = DEFAULT_CONFIG.copy()
        except tomllib.TOMLDecodeError:
            backup_path = config_path.with_suffix(
                f".corrupted.{int(time.time())}"
            )
            try:
                os.replace(str(config_path), str(backup_path))
            except OSError:
                pass
            config = DEFAULT_CONFIG.copy()

        for key, default_value in DEFAULT_CONFIG.items():
            config.setdefault(key, default_value)
        return config

    # ── Git Checkpoint ────────────────────────────────────────

    def create_checkpoint(self, label: str) -> str:
        """
        Git 체크포인트를 생성한다 (C-3).
        state/ 디렉토리를 커밋하고 태그를 생성한다.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        tag_name = f"checkpoint-{timestamp}-{label}"
        cwd = str(self.project_dir)

        subprocess.run(
            ["git", "add", "state/"],
            cwd=cwd,
            check=True,
            capture_output=True,
        )

        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=cwd,
            capture_output=True,
        )
        if result.returncode != 0:
            subprocess.run(
                ["git", "commit", "-m", f"checkpoint: {label}"],
                cwd=cwd,
                check=True,
                capture_output=True,
            )

        subprocess.run(
            ["git", "tag", tag_name],
            cwd=cwd,
            check=True,
            capture_output=True,
        )
        return tag_name

    def list_checkpoints(self) -> list[str]:
        result = subprocess.run(
            ["git", "tag", "-l", "checkpoint-*", "--sort=-creatordate"],
            cwd=str(self.project_dir),
            check=True,
            capture_output=True,
            text=True,
        )
        tags = result.stdout.strip().split("\n")
        return [t for t in tags if t]

    def restore_checkpoint(self, tag: str) -> None:
        cwd = str(self.project_dir)

        result = subprocess.run(
            ["git", "tag", "-l", tag],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
        if tag not in result.stdout.strip().split("\n"):
            raise ValueError(f"Checkpoint tag not found: {tag}")

        self.create_checkpoint(f"pre-restore-{tag}")

        subprocess.run(
            ["git", "checkout", tag, "--", "state/"],
            cwd=cwd,
            check=True,
            capture_output=True,
        )

    # ── Current Session (run/) ────────────────────────────────

    def set_current_session(
        self, session_id: str, mission_id: str | None
    ) -> None:
        self.atomic_write(
            self.run_dir / "current_session.json",
            {
                "session_id": session_id,
                "mission_id": mission_id,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "pid": os.getpid(),
                "status": "running",
                "last_event_at": datetime.now(timezone.utc).isoformat(),
                "compaction_count": 0,
                "stream_position": 0,
            },
        )

    def clear_current_session(self) -> None:
        session_file = self.run_dir / "current_session.json"
        try:
            os.unlink(str(session_file))
        except OSError:
            pass

    def load_current_session(self) -> dict[str, Any] | None:
        data = self.atomic_read(self.run_dir / "current_session.json")
        return data if data else None

    # ── Health Metrics ────────────────────────────────────────

    def write_health_metrics(self, metrics: dict[str, Any]) -> None:
        self.atomic_write(self.run_dir / "health_metrics.json", metrics)

    def load_health_metrics(self) -> dict[str, Any]:
        return self.atomic_read(self.run_dir / "health_metrics.json")

    # ── Crash Recovery ────────────────────────────────────────

    def recover_from_crash(self) -> dict[str, Any] | None:
        """
        크래시 후 상태를 복구한다.
        Supervisor 시작 시 호출.
        """
        session_file = self.run_dir / "current_session.json"
        if not session_file.exists():
            return None

        try:
            with open(session_file, "r", encoding="utf-8") as f:
                current = json.load(f)
        except (json.JSONDecodeError, OSError):
            self.clear_current_session()
            return None

        session_id = current.get("session_id")
        mission_id = current.get("mission_id")

        recovery_info: dict[str, Any] = {
            "recovered_session_id": session_id,
            "recovered_mission_id": mission_id,
            "action_taken": "none",
            "reset_missions": [],
        }

        queue = self.load_missions()
        for m in queue["missions"]:
            if m.get("status") == "in_progress":
                m["status"] = "pending"
                recovery_info["reset_missions"].append(m["id"])

        if recovery_info["reset_missions"]:
            self.save_missions(queue)
            recovery_info["action_taken"] = "re_enqueued"

        self._increment_restart_count()
        self.clear_current_session()
        return recovery_info

    def _increment_restart_count(self) -> None:
        counter_file = self.run_dir / "restart_count.json"
        try:
            with open(counter_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {"count": 0, "first_restart_at": None}

        data["count"] = data.get("count", 0) + 1
        if data.get("first_restart_at") is None:
            data["first_restart_at"] = (
                datetime.now(timezone.utc).isoformat()
            )
        data["last_restart_at"] = datetime.now(timezone.utc).isoformat()
        self.atomic_write(counter_file, data)

    def reset_restart_count(self) -> None:
        counter_file = self.run_dir / "restart_count.json"
        self.atomic_write(
            counter_file, {"count": 0, "first_restart_at": None}
        )

    # ── Session Context ───────────────────────────────────────

    def create_session_context(self) -> str:
        """새 세션에 주입할 시스템 상태 요약 텍스트를 생성한다."""
        purpose = self.load_purpose()
        strategy = self.load_strategy()
        queue = self.load_missions()
        friction_log = self.load_friction()
        requests_data = self.load_requests()
        sessions_data = self.load_sessions()

        sections: list[str] = []
        sections.append("## 시스템 상태 요약")

        # Purpose
        sections.append("\n### Purpose")
        if purpose:
            sections.append(
                f"- 방향: {purpose.get('purpose', '(미설정)')}"
            )
            sections.append(
                f"- 도메인: {purpose.get('domain', '(미설정)')}"
            )
        else:
            sections.append("(Purpose 미설정)")

        # Strategy
        sections.append("\n### 현재 전략")
        if strategy:
            sections.append(
                f"- 전략: {strategy.get('summary', '(없음)')}"
            )
        else:
            sections.append("(전략 미설정)")

        # Recent completed missions
        sections.append("\n### 최근 완료 미션 (최근 5개)")
        completed = [
            m
            for m in queue.get("missions", [])
            if m.get("status") == "completed"
        ]
        completed.sort(
            key=lambda m: m.get("completed_at", ""), reverse=True
        )
        if completed[:5]:
            for m in completed[:5]:
                result = m.get("result_summary", "(결과 없음)")
                if result and len(result) > 200:
                    result = result[:200] + "..."
                sections.append(
                    f"- [{m['id']}] {m.get('title', '?')} — {result}"
                )
        else:
            sections.append("(완료된 미션 없음)")

        # Pending missions
        sections.append("\n### 현재 미션 큐 (상위 5개)")
        pending = [
            m
            for m in queue.get("missions", [])
            if m.get("status") == "pending"
        ]
        pending.sort(
            key=lambda m: (
                m.get("priority", 999),
                m.get("created_at", ""),
            )
        )
        if pending[:5]:
            for m in pending[:5]:
                blockers = m.get("blockers", [])
                active = [
                    b for b in blockers if not b.get("resolved", False)
                ]
                b_text = f" [BLOCKED: {len(active)}]" if active else ""
                deps = m.get("dependencies", [])
                d_text = f" [deps: {', '.join(deps)}]" if deps else ""
                sections.append(
                    f"- [{m['id']}] P{m.get('priority', '?')}: "
                    f"{m.get('title', '?')}{b_text}{d_text}"
                )
        else:
            sections.append("(대기 미션 없음)")

        # Unresolved friction
        sections.append("\n### 미해결 Friction (최근 5개)")
        unresolved = [
            f
            for f in friction_log.get("frictions", [])
            if not f.get("resolved_at")
        ]
        unresolved.sort(
            key=lambda f: f.get("timestamp", ""), reverse=True
        )
        if unresolved[:5]:
            for f in unresolved[:5]:
                sections.append(
                    f"- [{f['id']}] [{f.get('type', '?')}] "
                    f"{f.get('description', '?')} "
                    f"(패턴: {f.get('pattern_key', 'N/A')})"
                )
        else:
            sections.append("(미해결 friction 없음)")

        # Pending owner requests
        sections.append("\n### Owner 대기 중인 요청")
        pending_reqs = [
            r
            for r in requests_data.get("requests", [])
            if r.get("status") == "pending"
        ]
        if pending_reqs:
            for r in pending_reqs:
                sections.append(
                    f"- [{r['id']}] {r.get('question', '?')}"
                )
        else:
            sections.append("(대기 중인 요청 없음)")

        # Stats
        sections.append("\n### 주요 통계")
        sessions = sessions_data.get("sessions", [])
        total_completed = len(completed)
        total_failed = len(
            [
                m
                for m in queue.get("missions", [])
                if m.get("status") == "failed"
            ]
        )
        sections.append(f"- 총 세션: {len(sessions)}")
        sections.append(f"- 총 완료 미션: {total_completed}")
        sections.append(f"- 총 실패 미션: {total_failed}")

        return "\n".join(sections)

    # ── Archive Rotation ──────────────────────────────────────

    def _append_to_archive(
        self, filepath: Path, records: list[dict[str, Any]]
    ) -> None:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "a", encoding="utf-8") as f:
            for record in records:
                record["archived_at"] = (
                    datetime.now(timezone.utc).isoformat()
                )
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def load_archive(
        self, entity: str, period: str
    ) -> list[dict[str, Any]]:
        filepath = (
            self.state_dir / "archive" / f"{entity}-{period}.jsonl"
        )
        if not filepath.exists():
            return []
        records = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def rotate_missions(self) -> int:
        queue = self.load_missions()
        missions = queue.get("missions", [])

        active = [
            m
            for m in missions
            if m.get("status") in ("pending", "in_progress", "blocked")
        ]
        done = [
            m
            for m in missions
            if m.get("status") in ("completed", "failed")
        ]

        done.sort(
            key=lambda m: m.get(
                "completed_at", m.get("created_at", "")
            ),
            reverse=True,
        )
        keep = done[:10]
        archive = done[10:]

        if not archive:
            return 0

        from collections import defaultdict

        by_period: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for m in archive:
            ts = m.get("completed_at", m.get("created_at", ""))
            period = ts[:7] if len(ts) >= 7 else "unknown"
            by_period[period].append(m)

        for period, records in by_period.items():
            archive_path = (
                self.state_dir / "archive" / f"missions-{period}.jsonl"
            )
            self._append_to_archive(archive_path, records)

        queue["missions"] = active + keep
        self.save_missions(queue)
        return len(archive)

    def rotate_friction(self) -> int:
        friction_log = self.load_friction()
        frictions = friction_log.get("frictions", [])

        unresolved = [f for f in frictions if not f.get("resolved_at")]
        resolved = [f for f in frictions if f.get("resolved_at")]

        resolved.sort(
            key=lambda f: f.get(
                "resolved_at", f.get("timestamp", "")
            ),
            reverse=True,
        )
        keep = resolved[:20]
        archive = resolved[20:]

        if not archive:
            return 0

        from collections import defaultdict

        by_period: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for f in archive:
            ts = f.get("resolved_at", f.get("timestamp", ""))
            period = ts[:7] if len(ts) >= 7 else "unknown"
            by_period[period].append(f)

        for period, records in by_period.items():
            archive_path = (
                self.state_dir / "archive" / f"friction-{period}.jsonl"
            )
            self._append_to_archive(archive_path, records)

        friction_log["frictions"] = unresolved + keep
        self.save_friction(friction_log)
        return len(archive)

    def rotate_sessions(self) -> int:
        data = self.load_sessions()
        sessions = data.get("sessions", [])

        sessions.sort(
            key=lambda s: s.get("started_at", ""), reverse=True
        )
        keep = sessions[:20]
        archive = sessions[20:]

        if not archive:
            return 0

        from collections import defaultdict

        by_period: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for s in archive:
            ts = s.get("started_at", "")
            period = ts[:7] if len(ts) >= 7 else "unknown"
            by_period[period].append(s)

        for period, records in by_period.items():
            archive_path = (
                self.state_dir / "archive" / f"sessions-{period}.jsonl"
            )
            self._append_to_archive(archive_path, records)

        data["sessions"] = keep
        self.save_sessions(data)
        return len(archive)
