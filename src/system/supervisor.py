"""
Supervisor.

시스템 최상위 오케스트레이터 데몬.
모든 컴포넌트를 관리하고 Claude Code 세션을 영속적으로 운영한다.

참조 요구사항: E-2 (장애 불멸), E-4 (독립 감시)
"""

from __future__ import annotations

import asyncio
import fcntl
import logging
import os
import signal
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from system.cognitive_load import (
    CognitiveLoadTrigger,
    StreamAnalyzer,
    prepare_trigger_context,
)
from system.error_classifier import ErrorClassifier, ErrorType
from system.session_manager import (
    SessionInfo,
    SessionManager,
    SessionState,
    StreamEvent,
)
from system.state_manager import StateManager


class SupervisorState(Enum):
    INITIALIZING = "initializing"
    RUNNING = "running"
    SESSION_ACTIVE = "session_active"
    WAITING = "waiting"
    SHUTTING_DOWN = "shutting_down"
    STOPPED = "stopped"


@dataclass
class SupervisorConfig:
    heartbeat_interval_s: float = 10.0
    session_timeout_minutes: int = 120
    git_checkpoint_enabled: bool = True
    max_consecutive_crashes: int = 3
    crash_cooldown_s: float = 60.0
    rate_limit_base_wait_s: float = 30.0
    friction_threshold: int = 3
    proactive_improvement_interval: int = 10
    owner_feedback_interval: int = 20


class Supervisor:
    """시스템 최상위 오케스트레이터."""

    def __init__(
        self,
        project_root: Path,
        config: SupervisorConfig | None = None,
    ) -> None:
        self.project_root = project_root
        self.config = config or SupervisorConfig()
        self.state = SupervisorState.INITIALIZING

        self.run_dir = project_root / "run"
        self.pid_file = self.run_dir / "supervisor.pid"
        self.heartbeat_file = self.run_dir / "supervisor.heartbeat"

        self.state_manager = StateManager(project_root)
        self.session_manager = SessionManager(project_root)
        self.error_classifier = ErrorClassifier(
            self.state_manager.load_config()
        )
        self.cognitive_load = CognitiveLoadTrigger()

        self._slack_client: Any = None  # Lazy init
        self._shutdown_event = asyncio.Event()
        self._current_session: SessionInfo | None = None
        self._consecutive_crashes: int = 0
        self._missions_since_improvement: int = 0
        self._pid_lock_fd: int | None = None
        self._background_tasks: list[asyncio.Task[Any]] = []

        self.log = logging.getLogger("automata.supervisor")

    # ── Lifecycle ──

    async def run(self) -> None:
        """메인 진입점."""
        try:
            self._acquire_pid_lock()
            self._setup_signal_handlers()

            recovery = self.state_manager.recover_from_crash()
            if recovery:
                self.log.info(
                    "크래시 복구 완료: %s", recovery
                )

            self._load_config_from_state()

            await self._init_slack_client()

            heartbeat_task = asyncio.create_task(
                self._heartbeat_writer(),
                name="heartbeat-writer",
            )
            self._background_tasks.append(heartbeat_task)

            await self._notify_slack(
                "시스템이 시작되었습니다."
            )

            self.state = SupervisorState.RUNNING
            await self._main_loop()

        except Exception as e:
            self.log.critical(
                "Supervisor 치명적 오류: %s", e, exc_info=True
            )
            await self._notify_slack(
                f"Supervisor 치명적 오류: {e}"
            )
        finally:
            await self.shutdown(reason="run() 종료")

    async def shutdown(self, reason: str = "unknown") -> None:
        if self.state == SupervisorState.STOPPED:
            return
        self.state = SupervisorState.SHUTTING_DOWN
        self.log.info("Supervisor 종료 시작: %s", reason)

        if self._current_session is not None:
            sid = self._current_session.session_id
            if sid:
                try:
                    await self.session_manager.terminate_session(
                        sid, graceful=True
                    )
                except Exception as e:
                    self.log.warning("세션 종료 실패: %s", e)

        await self._notify_slack(
            f"시스템이 종료됩니다: {reason}"
        )

        if self._slack_client:
            try:
                await self._slack_client.stop()
            except Exception:
                pass

        for task in self._background_tasks:
            task.cancel()
        await asyncio.gather(
            *self._background_tasks, return_exceptions=True
        )
        self._background_tasks.clear()

        self.heartbeat_file.unlink(missing_ok=True)
        self._release_pid_lock()

        self.state = SupervisorState.STOPPED
        self.log.info("Supervisor 종료 완료.")

    async def reload_config(self) -> None:
        self._load_config_from_state()
        self.log.info("설정 재로드 완료")

    def _load_config_from_state(self) -> None:
        cfg = self.state_manager.load_config()
        self.config.session_timeout_minutes = cfg.get(
            "session_timeout_minutes", 120
        )
        self.config.max_consecutive_crashes = cfg.get(
            "max_consecutive_failures", 3
        )
        self.config.friction_threshold = cfg.get(
            "friction_threshold", 3
        )
        self.config.proactive_improvement_interval = cfg.get(
            "proactive_improvement_interval", 10
        )
        self.config.owner_feedback_interval = cfg.get(
            "owner_feedback_interval", 20
        )

        self.session_manager.session_timeout_s = (
            self.config.session_timeout_minutes * 60
        )
        self.error_classifier = ErrorClassifier(cfg)

    # ── Main Loop ──

    async def _main_loop(self) -> None:
        while not self._shutdown_event.is_set():
            try:
                await self._run_single_cycle()
            except Exception as e:
                self.log.error(
                    "사이클 오류: %s", e, exc_info=True
                )
                self._consecutive_crashes += 1
                if (
                    self._consecutive_crashes
                    >= self.config.max_consecutive_crashes
                ):
                    await self._notify_slack(
                        f"연속 크래시 {self._consecutive_crashes}회. "
                        f"{self.config.crash_cooldown_s}초 대기."
                    )
                    await asyncio.sleep(
                        self.config.crash_cooldown_s
                    )
                    self._consecutive_crashes = 0

    async def _run_single_cycle(self) -> None:
        # Step 1: Git checkpoint
        if self.config.git_checkpoint_enabled:
            await self._git_checkpoint()

        # Step 2: 건강 메트릭 계산
        metrics = self._compute_health_metrics()
        self.state_manager.write_health_metrics(metrics)

        # Owner 피드백 확인
        missions_since = metrics.get(
            "missions_since_owner_interaction", 0
        )
        if missions_since >= self.config.owner_feedback_interval:
            await self._request_owner_feedback(metrics)

        # Step 3: Owner 메시지 확인
        await self._check_owner_messages()

        # Step 4: Friction 임계값 확인
        await self._check_friction_thresholds()

        # Step 5: 세션 프롬프트 생성
        prompt = await self._prepare_session()
        if prompt is None:
            missions = self.state_manager.load_missions()
            all_missions = missions.get("missions", [])
            blocked = [
                m
                for m in all_missions
                if m["status"] == "blocked"
            ]
            pending = [
                m
                for m in all_missions
                if m["status"] == "pending"
            ]

            if not all_missions or (not pending and not blocked):
                prompt = self._build_mission_generation_prompt()
            elif blocked and not pending:
                prompt = self._build_independent_work_prompt(
                    blocked
                )
            else:
                self.log.info(
                    "의존성 미충족 미션 대기. 30초 후 재시도."
                )
                await asyncio.sleep(30)
                return

        # Step 6: 세션 시작 및 모니터링
        self.state = SupervisorState.SESSION_ACTIVE
        await self._launch_and_monitor_session(prompt)

        # Step 7: 후처리
        self.state = SupervisorState.RUNNING
        self._consecutive_crashes = 0
        self._missions_since_improvement += 1

        # 아카이브 로테이션
        self.state_manager.rotate_missions()
        self.state_manager.rotate_friction()
        self.state_manager.rotate_sessions()

    # ── Session Management ──

    async def _prepare_session(self) -> str | None:
        mission = self.state_manager.get_next_mission()
        if mission is None:
            return None

        context = self.state_manager.create_session_context()
        health_metrics = self.state_manager.load_health_metrics()
        friction_log = self.state_manager.load_friction()
        friction_history = friction_log.get("frictions", [])

        prompt = self.cognitive_load.build_mission_prompt(
            mission=mission,
            context=context,
            health_metrics=health_metrics,
            friction_history=friction_history,
        )
        return prompt

    async def _launch_and_monitor_session(
        self, prompt: str
    ) -> None:
        mission = self.state_manager.get_next_mission()
        mission_id = mission["id"] if mission else ""

        session_info = await self.session_manager.launch_session(
            prompt, mission_id=mission_id
        )
        self._current_session = session_info

        self.state_manager.set_current_session(
            session_info.session_id or "launching", mission_id
        )

        analyzer = StreamAnalyzer()
        stream_events: list[dict[str, Any]] = []

        async for event in self.session_manager.monitor_session(
            session_info.process
        ):
            if self._shutdown_event.is_set():
                if session_info.session_id:
                    await self.session_manager.terminate_session(
                        session_info.session_id, graceful=True
                    )
                return

            analyzer.process_event(event.data)
            stream_events.append(event.data)

            match event.type:
                case "system" if event.subtype == "init":
                    session_info.session_id = event.session_id
                    self.state_manager.set_current_session(
                        event.session_id, mission_id
                    )
                    self.log.info(
                        "세션 시작: %s", event.session_id
                    )

                case "system" if event.subtype == "api_retry":
                    if event.is_rate_limit:
                        self.state = SupervisorState.WAITING
                        self.log.warning(
                            "Rate limit 감지. %dms 후 자동 재시도.",
                            event.retry_delay_ms,
                        )

                case "result":
                    pass  # 종료 후 처리

        # 세션 종료 후 처리
        exit_code = (
            session_info.process.returncode
            if session_info.process
            else -1
        )

        # StreamAnalyzer 결과 저장
        analyzer.save(self.run_dir / "session-analysis.json")

        # trigger-context.json 생성
        if mission:
            prepare_trigger_context(
                mission=mission,
                session_analysis=analyzer.to_dict(),
                output_path=self.run_dir / "trigger-context.json",
            )

        await self._handle_session_end(
            session_info, exit_code or 0, stream_events
        )

        self._current_session = None
        self.state_manager.clear_current_session()

    async def _handle_session_end(
        self,
        session_info: SessionInfo,
        exit_code: int,
        stream_events: list[dict[str, Any]],
    ) -> None:
        # 세션 이력 기록
        self.state_manager.add_session(
            {
                "id": session_info.session_id,
                "mission_id": session_info.mission_id,
                "started_at": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ",
                    time.gmtime(session_info.started_at),
                ),
                "ended_at": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                ),
                "exit_code": exit_code,
                "exit_reason": session_info.state.value,
                "tokens_used": {
                    "input": 0,
                    "output": 0,
                    "total": 0,
                },
                "compaction_count": session_info.compaction_count,
                "tool_calls_count": session_info.tool_use_count,
                "errors": [],
                "result_summary": session_info.result_text[:500]
                if session_info.result_text
                else None,
            }
        )

        if session_info.state == SessionState.COMPLETED:
            self.error_classifier.record_success()
            self.state_manager.reset_restart_count()
            self.log.info(
                "세션 정상 종료: %s", session_info.session_id
            )
            return

        # 에러 처리
        error_type, strategy = (
            self.error_classifier.classify_and_recover(
                exit_code=exit_code,
                stderr=session_info.stderr_buffer,
                stream_events=stream_events,
            )
        )

        self.log.warning(
            "세션 비정상 종료: type=%s action=%s delay=%.1fs",
            error_type.value,
            strategy.action,
            strategy.delay_seconds,
        )

        # Friction 기록
        self.state_manager.add_friction(
            {
                "type": "error",
                "pattern_key": f"session_{error_type.value}",
                "description": (
                    f"세션 비정상 종료: {error_type.value} "
                    f"(exit_code={exit_code})"
                ),
                "source_session_id": session_info.session_id,
                "source_mission_id": session_info.mission_id
                or None,
                "severity": "high"
                if error_type
                in (ErrorType.AUTH_FAILURE, ErrorType.STUCK)
                else "medium",
            }
        )

        match strategy.action:
            case "retry_resume":
                await asyncio.sleep(strategy.delay_seconds)
                if session_info.session_id:
                    await self.session_manager.resume_session(
                        session_info.session_id,
                        "이전 세션이 중단되었습니다. 계속 진행하세요.",
                        mission_id=session_info.mission_id,
                    )
            case "retry_fresh":
                await asyncio.sleep(strategy.delay_seconds)
                # 다음 루프에서 자동 재시도
            case "wait_and_resume":
                await asyncio.sleep(strategy.delay_seconds)
                if session_info.session_id:
                    await self.session_manager.resume_session(
                        session_info.session_id,
                        "Rate limit이 해소되었습니다. 계속 진행하세요.",
                        mission_id=session_info.mission_id,
                    )
            case "checkpoint_restore":
                checkpoints = (
                    self.state_manager.list_checkpoints()
                )
                if checkpoints:
                    self.state_manager.restore_checkpoint(
                        checkpoints[0]
                    )
            case "notify_owner":
                await self._notify_slack(
                    f"세션 에러: {error_type.value}. "
                    f"exit_code={exit_code}. 확인이 필요합니다."
                )

    # ── Health Metrics ──

    def _compute_health_metrics(self) -> dict[str, Any]:
        friction = self.state_manager.load_friction()
        sessions_data = self.state_manager.load_sessions()
        requests_data = self.state_manager.load_requests()
        missions = self.state_manager.load_missions()

        unresolved = [
            f
            for f in friction.get("frictions", [])
            if not f.get("resolved_at")
        ]
        sessions = sessions_data.get("sessions", [])
        recent_sessions = sessions[-10:] if sessions else []

        # friction 추세
        recent_count = len(
            [
                f
                for f in friction.get("frictions", [])
                if not f.get("resolved_at")
            ]
        )
        if recent_count > 5:
            trend = "increasing"
        elif recent_count == 0:
            trend = "decreasing"
        else:
            trend = "stable"

        # 개선 효과
        improvement_missions = [
            m
            for m in missions.get("missions", [])
            if m.get("source") == "friction"
            and m.get("status") == "completed"
        ]
        effectiveness = (
            1.0 if not improvement_missions else min(1.0, len(improvement_missions) / max(1, recent_count))
        )

        # Owner 상호작용
        answered = [
            r
            for r in requests_data.get("requests", [])
            if r.get("answered_at")
        ]
        last_interaction = (
            max(
                (r["answered_at"] for r in answered),
                default=None,
            )
            if answered
            else None
        )
        completed_since = sum(
            1
            for m in missions.get("missions", [])
            if m.get("status") == "completed"
            and m.get("completed_at", "")
            > (last_interaction or "")
        )

        # 미션 정체 감지
        stalled_mission_id = None
        mission_stall_count = 0
        if recent_sessions:
            last_mission = recent_sessions[-1].get("mission_id")
            if last_mission:
                for s in reversed(recent_sessions):
                    if s.get("mission_id") == last_mission:
                        mission_stall_count += 1
                    else:
                        break
                if mission_stall_count >= 3:
                    stalled_mission_id = last_mission

        # 짧은 세션 감지
        short_session_count = sum(
            1
            for s in recent_sessions
            if s.get("duration_s", 999) < 60
        )

        return {
            "friction_unresolved": len(unresolved),
            "friction_trend": trend,
            "improvement_effectiveness": round(
                effectiveness, 2
            ),
            "missions_since_owner_interaction": completed_since,
            "total_sessions": len(sessions),
            "total_missions_completed": sum(
                1
                for m in missions.get("missions", [])
                if m.get("status") == "completed"
            ),
            "stalled_mission_id": stalled_mission_id,
            "stalled_mission_sessions": mission_stall_count,
            "short_sessions_recent": short_session_count,
        }

    # ── Friction Check ──

    async def _check_friction_thresholds(self) -> None:
        friction_log = self.state_manager.load_friction()
        unresolved = [
            f
            for f in friction_log.get("frictions", [])
            if not f.get("resolved_at")
        ]

        pattern_counts: dict[str, int] = {}
        for f in unresolved:
            key = f.get("pattern_key", "")
            if key:
                pattern_counts[key] = (
                    pattern_counts.get(key, 0) + 1
                )

        threshold = self.config.friction_threshold
        for pattern_key, count in pattern_counts.items():
            if count >= threshold:
                # 이미 이 패턴의 개선 미션이 있는지 확인
                missions = self.state_manager.load_missions()
                existing = any(
                    m.get("source") == "friction"
                    and pattern_key in m.get("title", "")
                    and m.get("status")
                    in ("pending", "in_progress")
                    for m in missions.get("missions", [])
                )
                if not existing:
                    related = [
                        f
                        for f in unresolved
                        if f.get("pattern_key") == pattern_key
                    ]
                    friction_desc = "\n".join(
                        f"- {f['id']}: {f.get('description', '')}"
                        for f in related[:5]
                    )
                    self.state_manager.add_mission(
                        {
                            "title": f"자기개선: {pattern_key} 패턴 해결",
                            "description": (
                                f"## Friction 분석\n\n"
                                f"### 패턴: {pattern_key}\n"
                                f"- 미해결 friction {count}건 축적\n\n"
                                f"### 관련 Friction 기록\n{friction_desc}\n\n"
                                f"### 개선 방향\n"
                                f"1. 근본 원인 분석\n"
                                f"2. 코드 수정 또는 설정 조정\n"
                                f"3. 재발 방지 메커니즘 구현"
                            ),
                            "success_criteria": [
                                f"{pattern_key} 패턴의 근본 원인이 식별되었다",
                                "수정 후 관련 테스트가 통과한다",
                                "재발 방지 대책이 구현되었다",
                            ],
                            "priority": 0,
                            "source": "friction",
                        }
                    )
                    self.log.info(
                        "자기개선 미션 생성: %s (%d건 축적)",
                        pattern_key,
                        count,
                    )

    # ── Owner Feedback ──

    async def _request_owner_feedback(
        self, metrics: dict[str, Any]
    ) -> None:
        summary = (
            f"시스템이 {metrics.get('total_missions_completed', 0)}개 미션을 완료했습니다.\n"
            f"미해소 friction: {metrics.get('friction_unresolved', 0)}건 "
            f"({metrics.get('friction_trend', '?')})\n"
            f"개선 효과율: {metrics.get('improvement_effectiveness', 0):.0%}\n\n"
            f"현재 방향에 대한 피드백을 부탁드립니다."
        )
        self.state_manager.add_request(
            {
                "type": "question",
                "question": summary,
            }
        )

    # ── Prompts ──

    def _build_mission_generation_prompt(self) -> str:
        purpose = self.state_manager.load_purpose()
        strategy = self.state_manager.load_strategy()
        context = self.state_manager.create_session_context()
        return (
            f"미션 큐가 비었습니다. Purpose에 기반하여 새 미션을 생성하고 실행하세요.\n\n"
            f"## Purpose\n{purpose.get('purpose', '')}\n\n"
            f"## 전략\n{strategy.get('summary', '')}\n\n"
            f"## 시스템 상태\n{context}\n\n"
            f"3~5개의 구체적인 미션을 state/missions.json에 생성한 후 "
            f"첫 번째 미션을 즉시 시작하세요."
        )

    def _build_independent_work_prompt(
        self, blocked: list[dict[str, Any]]
    ) -> str:
        purpose = self.state_manager.load_purpose()
        context = self.state_manager.create_session_context()
        blocker_summary = "\n".join(
            f"- {m['id']}: {m.get('title', '?')} — 차단 사유: "
            + ", ".join(
                b.get("description", "")
                for b in m.get("blockers", [])
            )
            for m in blocked
        )
        return (
            f"현재 모든 미션이 차단 상태입니다.\n\n"
            f"## 차단된 미션\n{blocker_summary}\n\n"
            f"## Purpose\n{purpose.get('purpose', '')}\n\n"
            f"## 시스템 상태\n{context}\n\n"
            f"차단된 미션과 독립적인 새 작업을 생성하고 실행하세요.\n"
            f"3~5개의 미션을 state/missions.json에 생성한 후 "
            f"첫 번째 미션을 즉시 시작하세요."
        )

    # ── Background Tasks ──

    async def _heartbeat_writer(self) -> None:
        while not self._shutdown_event.is_set():
            try:
                tmp = self.heartbeat_file.with_suffix(".tmp")
                tmp.write_text(str(time.time()))
                tmp.rename(self.heartbeat_file)
            except OSError as e:
                self.log.warning(
                    "Heartbeat write failed: %s", e
                )

            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self.config.heartbeat_interval_s,
                )
                break
            except asyncio.TimeoutError:
                pass

    async def _check_owner_messages(self) -> None:
        if self._slack_client:
            try:
                await self._slack_client.check_pending_answers()
            except Exception as e:
                self.log.debug(
                    "Owner 메시지 확인 실패: %s", e
                )

    async def _git_checkpoint(self) -> None:
        try:
            tag = self.state_manager.create_checkpoint(
                f"pre-session-{int(time.time())}"
            )
            self.log.debug("Git checkpoint: %s", tag)
        except Exception as e:
            self.log.warning(
                "Git checkpoint 실패: %s", e
            )

    # ── Slack ──

    async def _init_slack_client(self) -> None:
        try:
            from dotenv import dotenv_values

            env = dotenv_values(self.project_root / ".env")
        except ImportError:
            env = {}

        bot_token = env.get(
            "SLACK_BOT_TOKEN",
            os.environ.get("SLACK_BOT_TOKEN", ""),
        )
        app_token = env.get(
            "SLACK_APP_TOKEN",
            os.environ.get("SLACK_APP_TOKEN", ""),
        )
        channel_id = env.get(
            "SLACK_CHANNEL_ID",
            os.environ.get("SLACK_CHANNEL_ID", ""),
        )

        if bot_token and app_token and channel_id:
            try:
                from system.slack_client import SlackClient

                self._slack_client = SlackClient(
                    bot_token=bot_token,
                    app_token=app_token,
                    channel_id=channel_id,
                    state_manager=self.state_manager,
                )
                await self._slack_client.start()
                self.log.info("Slack Client 초기화 완료")
            except Exception as e:
                self.log.warning(
                    "Slack 연결 실패 (계속 진행): %s", e
                )
                self._slack_client = None
        else:
            self.log.info(
                "Slack 토큰 미설정. Slack 없이 진행."
            )

    async def _notify_slack(self, text: str) -> None:
        if self._slack_client:
            try:
                await self._slack_client.notify(text)
            except Exception:
                pass

    # ── Signal Handling ──

    def _setup_signal_handlers(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig, self._handle_sigterm
            )
        loop.add_signal_handler(
            signal.SIGHUP, self._handle_sighup
        )

    def _handle_sigterm(self) -> None:
        if self.state != SupervisorState.SHUTTING_DOWN:
            self.state = SupervisorState.SHUTTING_DOWN
            self._shutdown_event.set()

    def _handle_sighup(self) -> None:
        asyncio.get_running_loop().create_task(
            self.reload_config()
        )

    # ── PID Lock ──

    def _acquire_pid_lock(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._pid_lock_fd = os.open(
            str(self.pid_file), os.O_CREAT | os.O_RDWR
        )
        try:
            fcntl.lockf(
                self._pid_lock_fd,
                fcntl.LOCK_EX | fcntl.LOCK_NB,
            )
        except OSError:
            os.close(self._pid_lock_fd)
            raise SystemExit(
                "Another Supervisor is already running "
                f"(pid file: {self.pid_file})"
            )
        os.ftruncate(self._pid_lock_fd, 0)
        os.lseek(self._pid_lock_fd, 0, os.SEEK_SET)
        os.write(
            self._pid_lock_fd, str(os.getpid()).encode()
        )

    def _release_pid_lock(self) -> None:
        if self._pid_lock_fd is not None:
            try:
                fcntl.lockf(
                    self._pid_lock_fd, fcntl.LOCK_UN
                )
                os.close(self._pid_lock_fd)
            except OSError:
                pass
            self._pid_lock_fd = None
        self.pid_file.unlink(missing_ok=True)


# ── Entrypoint ──

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(
                "logs/supervisor.log", encoding="utf-8"
            ),
            logging.StreamHandler(),
        ],
    )

    Path("logs").mkdir(parents=True, exist_ok=True)

    project_root = Path(__file__).resolve().parent.parent
    supervisor = Supervisor(project_root)

    try:
        asyncio.run(supervisor.run())
    except KeyboardInterrupt:
        pass
    except SystemExit as e:
        logging.error("Supervisor 시작 실패: %s", e)
        raise


if __name__ == "__main__":
    main()
