# Supervisor 컴포넌트 설계

> **파일**: `system/supervisor.py`, `system/watchdog.py`
> **역할**: 시스템 최상위 오케스트레이터 데몬. 모든 컴포넌트를 관리하고 Claude Code 세션을 영속적으로 운영한다.

---

## 1. 개요

Supervisor는 claude-automata의 Deterministic Core 핵심이다. Python asyncio 기반 단일 프로세스 데몬으로, macOS launchd LaunchAgent가 관리한다. 시스템의 모든 생명주기(시작, 운영, 복구, 종료)를 통제하며, 자체적으로는 어떤 지능적 판단도 하지 않는다 — 모든 판단은 Claude Code 세션(Agentic Shell)에 위임한다.

### 핵심 원칙

- **결정론적 동작**: Supervisor 코드는 조건 분기와 상태 전이만 수행한다. AI 판단이 필요한 결정은 없다.
- **단일 인스턴스**: PID 잠금 파일로 중복 실행을 방지한다.
- **장애 불멸**: launchd KeepAlive + 별도 Watchdog으로 어떤 상황에서도 복구된다.
- **관찰 가능성**: heartbeat 파일, 로그, state 파일을 통해 외부에서 상태를 관찰할 수 있다.

---

## 2. Class: Supervisor

### 2.1 클래스 인터페이스

```python
import asyncio
import fcntl
import os
import signal
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from system.session_manager import SessionManager, SessionInfo, SessionStatus
from system.state_manager import StateManager
from system.slack_client import SlackClient
from system.error_classifier import ErrorClassifier, ErrorType, RecoveryStrategy


class SupervisorState(Enum):
    """Supervisor 자체의 상태 (세션 상태와 별개)"""
    INITIALIZING = "initializing"       # 시작 중, 상태 복구 진행
    RUNNING = "running"                 # 정상 운영 루프 실행 중
    SESSION_ACTIVE = "session_active"   # Claude Code 세션 실행 중
    WAITING = "waiting"                 # rate limit 대기 등
    SHUTTING_DOWN = "shutting_down"     # 종료 진행 중
    STOPPED = "stopped"                 # 완전 종료


@dataclass
class SupervisorConfig:
    """Supervisor 동적 설정. state/config.toml에서 로드."""
    heartbeat_interval_s: float = 10.0
    session_timeout_minutes: int = 120       # 세션 타임아웃 (분)
    git_checkpoint_enabled: bool = True
    max_consecutive_crashes: int = 3
    crash_cooldown_s: float = 60.0
    rate_limit_base_wait_s: float = 30.0
    friction_threshold: int = 3
    proactive_improvement_interval: int = 10  # 미션 수


class Supervisor:
    """
    시스템 최상위 오케스트레이터.

    단일 asyncio 이벤트 루프에서 모든 하위 컴포넌트를 관리한다.
    launchd LaunchAgent가 이 프로세스의 생명주기를 관리하며,
    별도 Watchdog LaunchAgent가 이 프로세스의 활성 상태를 감시한다.
    """

    def __init__(
        self,
        project_root: Path,
        config: Optional[SupervisorConfig] = None,
    ) -> None: ...

    # ── 생명주기 ──────────────────────────────────────────────

    async def run(self) -> None:
        """메인 진입점. 시그널 핸들러 등록 → 초기화 → 메인 루프 실행."""
        ...

    async def shutdown(self, reason: str = "unknown") -> None:
        """모든 컴포넌트를 정리하고 종료한다."""
        ...

    async def reload_config(self) -> None:
        """SIGHUP 수신 시 state/config.toml을 다시 로드한다."""
        ...

    # ── 메인 루프 ─────────────────────────────────────────────

    async def _main_loop(self) -> None:
        """핵심 운영 루프. 세션 시작 → 모니터링 → 결과 처리를 반복한다."""
        ...

    async def _run_single_cycle(self) -> None:
        """메인 루프의 한 사이클: checkpoint → select → launch → monitor → record."""
        ...

    # ── 세션 관리 ─────────────────────────────────────────────

    async def _prepare_session(self) -> Optional[str]:
        """다음 미션을 선택하고 세션 프롬프트를 생성한다. 미션이 없으면 None."""
        ...

    async def _launch_and_monitor_session(self, prompt: str) -> None:
        """세션을 시작하고 stream-json 이벤트를 실시간 처리한다."""
        ...

    async def _handle_session_end(
        self,
        session_info: SessionInfo,
        exit_code: int,
    ) -> None:
        """세션 종료 후 결과를 기록하고 다음 행동을 결정한다."""
        ...

    # ── 부가 기능 ─────────────────────────────────────────────

    async def _heartbeat_writer(self) -> None:
        """백그라운드 태스크: heartbeat 파일을 주기적으로 갱신한다."""
        ...

    async def _check_owner_messages(self) -> None:
        """Slack에서 수신된 Owner 메시지를 확인하고 처리한다."""
        ...

    async def _check_friction_thresholds(self) -> None:
        """friction 축적 임계값을 확인하고 자기개선 미션을 생성한다."""
        ...

    async def _git_checkpoint(self) -> None:
        """state/ 파일을 Git 커밋 + 태그로 체크포인트한다."""
        ...

    # ── 시그널 핸들링 ─────────────────────────────────────────

    def _setup_signal_handlers(self) -> None:
        """SIGTERM, SIGINT, SIGHUP 핸들러를 asyncio 루프에 등록한다."""
        ...

    def _handle_sigterm(self) -> None:
        """SIGTERM/SIGINT: graceful shutdown을 시작한다."""
        ...

    def _handle_sighup(self) -> None:
        """SIGHUP: config를 다시 로드한다."""
        ...

    # ── PID 잠금 ──────────────────────────────────────────────

    def _acquire_pid_lock(self) -> None:
        """run/supervisor.pid에 exclusive lock을 획득한다."""
        ...

    def _release_pid_lock(self) -> None:
        """PID 잠금 파일을 해제하고 삭제한다."""
        ...
```

### 2.2 의존성

| 컴포넌트 | 역할 | 인스턴스 소유 |
|----------|------|:------------:|
| `SessionManager` | Claude Code 프로세스 생명주기 | Supervisor가 생성 |
| `StateManager` | state/ 파일 읽기/쓰기, Git 체크포인트 | Supervisor가 생성 |
| `SlackClient` | Owner 비동기 통신 | Supervisor가 생성 |
| `ErrorClassifier` | 에러 분류 및 복구 전략 결정 | Supervisor가 생성 |

```python
# __init__ 내부 의존성 초기화
def __init__(self, project_root: Path, config: Optional[SupervisorConfig] = None) -> None:
    self.project_root = project_root
    self.config = config or SupervisorConfig()
    self.state = SupervisorState.INITIALIZING

    # 경로
    self.run_dir = project_root / "run"
    self.pid_file = self.run_dir / "supervisor.pid"
    self.heartbeat_file = self.run_dir / "supervisor.heartbeat"

    # 컴포넌트
    self.state_manager = StateManager(project_root)
    self.session_manager = SessionManager(project_root)
    self.slack_client = SlackClient(
        bot_token=os.environ["SLACK_BOT_TOKEN"],
        app_token=os.environ["SLACK_APP_TOKEN"],
        channel_id=os.environ["SLACK_CHANNEL_ID"],
        state_manager=self.state_manager,
    )
    self.error_classifier = ErrorClassifier(self.state_manager.load_config())

    # 내부 상태
    self._shutdown_event = asyncio.Event()
    self._current_session: Optional[SessionInfo] = None
    self._consecutive_crashes: int = 0
    self._missions_since_improvement: int = 0
    self._pid_lock_fd: Optional[int] = None

    # 백그라운드 태스크
    self._background_tasks: list[asyncio.Task] = []
```

### 2.3 생명주기: `__init__` → `run()` → `shutdown()`

```
┌──────────┐     ┌──────────────┐     ┌─────────────┐
│ __init__ │────▶│    run()     │────▶│  shutdown()  │
│          │     │              │     │              │
│ 경로 설정 │     │ 1. PID 잠금  │     │ 1. 세션 종료 │
│ 컴포넌트  │     │ 2. 시그널    │     │ 2. Slack 종료│
│  생성     │     │ 3. 상태 복구 │     │ 3. 태스크    │
│          │     │ 4. Slack 시작│     │    취소      │
│          │     │ 5. Heartbeat │     │ 4. Heartbeat │
│          │     │ 6. 메인 루프 │     │    삭제      │
│          │     │              │     │ 5. PID 해제  │
└──────────┘     └──────────────┘     └─────────────┘
```

### 2.4 시그널 핸들링

| 시그널 | 동작 | 설명 |
|--------|------|------|
| `SIGTERM` | graceful shutdown | launchd가 종료 시 전송. 실행 중인 세션을 안전하게 종료한 뒤 프로세스 종료 |
| `SIGINT` | graceful shutdown | 수동 Ctrl+C. SIGTERM과 동일하게 처리 |
| `SIGHUP` | reload config | state/config.toml을 다시 읽어서 런타임 설정 갱신 |

```python
def _setup_signal_handlers(self) -> None:
    loop = asyncio.get_running_loop()

    # SIGTERM, SIGINT → graceful shutdown
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, self._handle_sigterm)

    # SIGHUP → config reload
    loop.add_signal_handler(signal.SIGHUP, self._handle_sighup)

def _handle_sigterm(self) -> None:
    """shutdown_event를 세팅하여 메인 루프가 자연스럽게 종료되게 한다."""
    if self.state != SupervisorState.SHUTTING_DOWN:
        self.state = SupervisorState.SHUTTING_DOWN
        self._shutdown_event.set()

def _handle_sighup(self) -> None:
    """config reload을 스케줄링한다. 메인 루프 안에서 안전하게 실행."""
    asyncio.get_running_loop().create_task(self.reload_config())
```

### 2.5 PID 잠금 파일

Supervisor 중복 실행을 방지한다. `fcntl.lockf` exclusive lock을 사용하며, 프로세스가 종료되면 OS가 자동으로 잠금을 해제한다.

```python
def _acquire_pid_lock(self) -> None:
    """
    run/supervisor.pid에 exclusive lock을 획득한다.
    이미 다른 Supervisor가 실행 중이면 SystemExit을 발생시킨다.
    """
    self.run_dir.mkdir(parents=True, exist_ok=True)
    self._pid_lock_fd = os.open(
        str(self.pid_file),
        os.O_CREAT | os.O_RDWR,
    )
    try:
        fcntl.lockf(self._pid_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(self._pid_lock_fd)
        raise SystemExit(
            "Another Supervisor is already running "
            f"(pid file: {self.pid_file})"
        )
    # PID 기록
    os.ftruncate(self._pid_lock_fd, 0)
    os.lseek(self._pid_lock_fd, 0, os.SEEK_SET)
    os.write(self._pid_lock_fd, str(os.getpid()).encode())

def _release_pid_lock(self) -> None:
    """PID 잠금을 해제하고 파일을 삭제한다."""
    if self._pid_lock_fd is not None:
        try:
            fcntl.lockf(self._pid_lock_fd, fcntl.LOCK_UN)
            os.close(self._pid_lock_fd)
        except OSError:
            pass
        self._pid_lock_fd = None
    self.pid_file.unlink(missing_ok=True)
```

### 2.6 Heartbeat

10초마다 `run/supervisor.heartbeat` 파일에 현재 UNIX timestamp를 기록한다. Watchdog이 이 파일을 읽어서 Supervisor의 활성 상태를 판단한다.

```python
async def _heartbeat_writer(self) -> None:
    """
    백그라운드 태스크: heartbeat_interval_s마다 heartbeat 파일을 갱신한다.
    shutdown_event가 세팅되면 종료한다.
    """
    while not self._shutdown_event.is_set():
        try:
            # 원자적 쓰기: 임시 파일에 쓴 뒤 rename
            tmp = self.heartbeat_file.with_suffix(".tmp")
            tmp.write_text(str(time.time()))
            tmp.rename(self.heartbeat_file)
        except OSError as e:
            logging.warning("Heartbeat write failed: %s", e)

        try:
            await asyncio.wait_for(
                self._shutdown_event.wait(),
                timeout=self.config.heartbeat_interval_s,
            )
            break  # shutdown 신호 수신
        except asyncio.TimeoutError:
            pass  # 정상 — 다음 heartbeat 기록
```

### 2.7 메인 루프 의사코드

```python
async def run(self) -> None:
    """Supervisor 메인 진입점."""
    try:
        # 1. PID 잠금 획득
        self._acquire_pid_lock()

        # 2. 시그널 핸들러 등록
        self._setup_signal_handlers()

        # 3. 상태 복구 — 이전 실행에서 중단된 상태가 있으면 로드
        await self.state_manager.load_or_recover()
        self.config = self._load_config_from_state()

        # 4. Slack 클라이언트 시작 (백그라운드 WebSocket)
        # Note: Slack은 필수가 아니다. 연결 실패 시에도 세션은 정상 실행된다.
        # Slack이 다운되면 미션은 계속 실행되지만 Owner 알림이 실패한다.
        # 백그라운드에서 주기적으로 재연결을 시도한다.
        try:
            slack_task = asyncio.create_task(
                self.slack_client.start(),
                name="slack-client",
            )
            self._background_tasks.append(slack_task)
        except Exception:
            logging.warning(
                "Slack 연결 실패. 세션은 Slack 없이 계속 실행됩니다. "
                "백그라운드에서 재연결을 시도합니다.",
                exc_info=True,
            )

        # 5. Heartbeat writer 시작 (백그라운드)
        heartbeat_task = asyncio.create_task(
            self._heartbeat_writer(),
            name="heartbeat-writer",
        )
        self._background_tasks.append(heartbeat_task)

        # 6. Slack으로 시작 알림 (Slack이 없으면 조용히 실패)
        try:
            await self.slack_client.notify("시스템이 시작되었습니다.")
        except Exception:
            logging.warning("Slack 시작 알림 전송 실패.", exc_info=True)

        # 7. 메인 루프
        self.state = SupervisorState.RUNNING
        await self._main_loop()

    except Exception as e:
        logging.critical("Supervisor 치명적 오류: %s", e, exc_info=True)
        await self.slack_client.notify(
            f"Supervisor 치명적 오류가 발생했습니다: {e}"
        )
    finally:
        await self.shutdown(reason="run() 종료")


async def _main_loop(self) -> None:
    """
    핵심 운영 루프.
    shutdown_event가 세팅될 때까지 세션 사이클을 반복한다.
    """
    while not self._shutdown_event.is_set():
        try:
            await self._run_single_cycle()
        except Exception as e:
            logging.error("사이클 오류: %s", e, exc_info=True)
            self._consecutive_crashes += 1
            if self._consecutive_crashes >= self.config.max_consecutive_crashes:
                await self.slack_client.notify(
                    f"연속 크래시 {self._consecutive_crashes}회 발생. "
                    f"{self.config.crash_cooldown_s}초 대기합니다."
                )
                await asyncio.sleep(self.config.crash_cooldown_s)
                self._consecutive_crashes = 0


async def _run_single_cycle(self) -> None:
    """
    메인 루프의 한 사이클:
    1. Git 체크포인트
    2. 건강 메트릭 계산 + Owner 피드백 확인
    3. Owner 메시지 확인
    4. friction 임계값 확인
    5. 다음 미션 선택 및 프롬프트 생성
    6. 세션 시작 및 모니터링
    7. 세션 종료 처리
    """
    # ── Step 1: Git 체크포인트 ──
    if self.config.git_checkpoint_enabled:
        await self._git_checkpoint()

    # ── Step 2: 건강 메트릭 계산 ──
    # state 파일에서 결정론적으로 계산. 모델 개입 없음.
    # SessionStart Hook이 이 메트릭을 세션 컨텍스트에 주입한다.
    metrics = self._compute_health_metrics()
    self.state_manager.write_health_metrics(metrics)

    # Owner 피드백 주기 확인
    if metrics["missions_since_owner_interaction"] >= self.config.owner_feedback_interval:
        await self._request_owner_feedback(metrics)

    # ── Step 3: Owner 메시지 확인 ──
    await self._check_owner_messages()

    # ── Step 4: Friction 임계값 확인 ──
    await self._check_friction_thresholds()

    # ── Step 5: 세션 프롬프트 생성 ──
    prompt = await self._prepare_session()
    if prompt is None:
        # 실행 가능한 미션이 없는 이유를 구분한다:
        # - 큐가 비었음 → 새 미션 생성 세션 시작 (P-3)
        # - 전부 blocked → 독립적 작업 생성 세션 시작 (P-3 정신)
        # - 둘 다 아님 → 30초 대기 후 재시도
        missions = self.state_manager.load_missions()
        all_missions = missions.get("missions", [])
        blocked = [m for m in all_missions if m["status"] == "blocked"]
        pending = [m for m in all_missions if m["status"] == "pending"]

        if not all_missions or (not pending and not blocked):
            # 큐가 비었거나 모든 미션이 완료/실패 → 미션 생성 세션
            prompt = self._build_mission_generation_prompt()
        elif blocked and not pending:
            # 실행 가능한 미션 없음, 전부 blocked → 독립적 작업 생성 세션
            prompt = self._build_independent_work_prompt(blocked)
        else:
            # pending이 있지만 의존성 미충족 등 → 잠시 대기
            logging.info("의존성 미충족 미션 대기. 30초 후 재시도.")
            await asyncio.sleep(30)
            return

    # ── Step 6: 세션 시작 및 모니터링 ──
    self.state = SupervisorState.SESSION_ACTIVE
    await self._launch_and_monitor_session(prompt)

    # ── Step 7: 결과 처리 ──
    self.state = SupervisorState.RUNNING
    self._consecutive_crashes = 0
    self._missions_since_improvement += 1

    if (self._missions_since_improvement
            >= self.config.proactive_improvement_interval):
        await self._trigger_proactive_improvement()
        self._missions_since_improvement = 0


def _compute_health_metrics(self) -> dict:
    """
    state 파일에서 결정론적으로 건강 메트릭을 계산한다.
    모든 값은 Python이 계산하며 모델의 자기 평가에 의존하지 않는다.
    결과는 run/health_metrics.json에 기록되어 SessionStart Hook이 주입한다.
    """
    friction = self.state_manager.load_friction()
    sessions = self.state_manager.load_sessions()
    requests = self.state_manager.load_requests()
    missions = self.state_manager.load_missions()

    unresolved = [f for f in friction.get("records", []) if not f.get("resolved_at")]
    recent_sessions = sessions[-10:] if sessions else []

    # friction 추세: 최근 10세션의 friction 발생 수 vs 이전 10세션
    recent_friction = [f for f in friction.get("records", [])
                       if f.get("timestamp", "") > (recent_sessions[0].get("started_at", "") if recent_sessions else "")]
    older_friction = [f for f in friction.get("records", [])
                      if f not in recent_friction and f.get("resolved_at")]

    if len(recent_friction) > len(older_friction) * 1.5:
        trend = "increasing"
    elif len(recent_friction) < len(older_friction) * 0.5:
        trend = "decreasing"
    else:
        trend = "stable"

    # 개선 효과: 개선 미션이 해소한 friction 비율
    improvement_missions = [m for m in missions.get("missions", [])
                            if m.get("source") == "friction" and m.get("status") == "completed"]
    resolved_by_improvement = [f for f in friction.get("records", [])
                                if f.get("resolved_by") and f.get("resolved_at")]
    effectiveness = (len(resolved_by_improvement) / len(improvement_missions)
                     if improvement_missions else 1.0)

    # Owner 상호작용 경과
    answered = [r for r in requests.get("records", []) if r.get("answered_at")]
    last_interaction = max((r["answered_at"] for r in answered), default=None) if answered else None
    completed_since = sum(1 for m in missions.get("missions", [])
                          if m.get("status") == "completed"
                          and m.get("completed_at", "") > (last_interaction or ""))

    # 특정 패턴 감지: 미션 정체 (같은 미션이 연속 N세션에서 실행)
    mission_stall_count = 0
    stalled_mission_id = None
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

    # 특정 패턴 감지: 짧은 세션 (60초 이내 종료 = 비정상)
    short_session_count = sum(
        1 for s in recent_sessions
        if s.get("duration_s", 999) < 60
    )

    return {
        "friction_unresolved": len(unresolved),
        "friction_trend": trend,
        "improvement_effectiveness": round(effectiveness, 2),
        "missions_since_owner_interaction": completed_since,
        "total_sessions": len(sessions),
        "total_missions_completed": sum(1 for m in missions.get("missions", [])
                                         if m.get("status") == "completed"),
        "stalled_mission_id": stalled_mission_id,
        "stalled_mission_sessions": mission_stall_count,
        "short_sessions_recent": short_session_count,
    }


async def _request_owner_feedback(self, metrics: dict) -> None:
    """Owner에게 주기적 피드백을 요청한다. 비차단."""
    summary = (
        f"시스템이 {metrics['total_missions_completed']}개 미션을 완료했습니다.\n"
        f"미해소 friction: {metrics['friction_unresolved']}건 ({metrics['friction_trend']})\n"
        f"개선 효과율: {metrics['improvement_effectiveness']:.0%}\n\n"
        f"현재 방향에 대한 피드백을 부탁드립니다."
    )
    self.state_manager.add_request(
        type="feedback",
        question=summary,
    )


def _build_mission_generation_prompt(self) -> str:
    """
    미션 큐가 비었을 때 Purpose 기반 미션 생성 세션 프롬프트.
    P-3: Mission 큐가 비면 시스템은 Purpose에 따라 스스로 할 일을 결정한다.
    """
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


def _build_independent_work_prompt(self, blocked: list[dict]) -> str:
    """
    모든 미션이 blocked 상태일 때 독립적 작업 생성 세션 프롬프트.
    P-3 정신: 실행 가능한 작업이 없을 때도 시스템은 유용한 작업을 수행한다.
    """
    purpose = self.state_manager.load_purpose()
    context = self.state_manager.create_session_context()
    blocker_summary = "\n".join(
        f"- {m['id']}: {m['title']} — 차단 사유: "
        f"{', '.join(b.get('description', '') for b in m.get('blockers', []))}"
        for m in blocked
    )
    return (
        f"현재 모든 미션이 차단 상태입니다 (Owner 응답 대기 등).\n\n"
        f"## 차단된 미션\n{blocker_summary}\n\n"
        f"## Purpose\n{purpose.get('purpose', '')}\n\n"
        f"## 시스템 상태\n{context}\n\n"
        f"차단된 미션과 독립적인 새 작업을 생성하고 실행하세요.\n"
        f"차단된 미션의 의존성과 무관한 방향을 선택하세요.\n"
        f"3~5개의 미션을 state/missions.json에 생성한 후 "
        f"첫 번째 미션을 즉시 시작하세요."
    )


async def _launch_and_monitor_session(self, prompt: str) -> None:
    """
    SessionManager를 통해 세션을 시작하고 stream-json 이벤트를 실시간 처리한다.
    """
    # 세션 시작
    session_info = await self.session_manager.launch_session(prompt)
    self._current_session = session_info

    # run/current_session.json에 현재 세션 정보 기록
    await self.state_manager.write_current_session(session_info)

    # stream-json 이벤트 모니터링
    async for event in self.session_manager.monitor_session(session_info.process):
        if self._shutdown_event.is_set():
            await self.session_manager.terminate_session(
                session_info.session_id, graceful=True,
            )
            return

        match event.type:
            case "system" if event.subtype == "init":
                # 세션 ID 확인 및 기록
                session_info.session_id = event.data.get("session_id", "")
                logging.info("세션 시작: %s", session_info.session_id)

            case "system" if event.subtype == "api_retry":
                # Rate limit / API 에러 감지
                error_cat = event.data.get("error", "")
                if error_cat == "rate_limit":
                    retry_delay = event.data.get("retry_delay_ms", 30000)
                    logging.warning(
                        "Rate limit 감지. %dms 후 자동 재시도.",
                        retry_delay,
                    )
                    self.state = SupervisorState.WAITING

            case "assistant":
                # 텍스트/도구 사용 이벤트 — TUI 갱신용 전달
                pass

            case "result":
                # 세션 종료
                await self._handle_session_end(
                    session_info,
                    exit_code=session_info.process.returncode or 0,
                )

    self._current_session = None


async def _handle_session_end(
    self,
    session_info: SessionInfo,
    exit_code: int,
) -> None:
    """
    세션 종료 후처리:
    1. 결과 분류 (정상/에러/rate limit/크래시)
    2. 세션 이력 기록
    3. 복구 전략 결정 및 실행
    """
    # 에러 분류
    category = self.error_classifier.classify(
        exit_code=exit_code,
        stderr=session_info.stderr_buffer,
        last_event=session_info.last_event,
    )

    # 세션 이력 기록
    await self.state_manager.record_session_result(
        session_id=session_info.session_id,
        exit_code=exit_code,
        error_category=category,
    )

    match category:
        case None:
            # 정상 종료 (ErrorClassifier가 에러 없음으로 판단)
            logging.info("세션 정상 종료: %s", session_info.session_id)

        case ErrorType.RATE_LIMITED:
            wait_s = self.config.rate_limit_base_wait_s
            logging.warning("Rate limit. %s초 대기 후 재개.", wait_s)
            await self.slack_client.notify(
                f"Rate limit 발생. {wait_s}초 대기 후 재개합니다."
            )
            await asyncio.sleep(wait_s)
            # resume로 재개 시도
            await self.session_manager.resume_session(
                session_info.session_id, prompt="계속 진행하세요.",
            )

        case ErrorType.PROCESS_CRASH | ErrorType.UNKNOWN:
            self._consecutive_crashes += 1
            logging.error(
                "세션 크래시 (연속 %d회): exit=%d",
                self._consecutive_crashes, exit_code,
            )
            # friction 기록
            await self.state_manager.record_friction(
                source="crash",
                description=f"세션 크래시 exit_code={exit_code}",
            )

        case ErrorType.AUTH_FAILURE:
            logging.critical("인증 실패. 수동 개입 필요.")
            await self.slack_client.notify(
                "인증 오류가 발생했습니다. `claude login`을 실행해주세요."
            )
            # 장시간 대기 — Owner가 해결할 때까지
            await asyncio.sleep(300)
```

### 2.8 shutdown 의사코드

```python
async def shutdown(self, reason: str = "unknown") -> None:
    """
    모든 컴포넌트를 정리하고 프로세스를 종료한다.

    순서:
    1. 실행 중인 Claude Code 세션 종료
    2. Slack 종료 알림 전송
    3. Slack 클라이언트 종료
    4. 백그라운드 태스크 취소
    5. Heartbeat 파일 삭제
    6. PID 잠금 해제
    """
    if self.state == SupervisorState.STOPPED:
        return
    self.state = SupervisorState.SHUTTING_DOWN
    logging.info("Supervisor 종료 시작: %s", reason)

    # 1. 실행 중인 세션 종료
    if self._current_session is not None:
        try:
            await self.session_manager.terminate_session(
                self._current_session.session_id,
                graceful=True,
            )
        except Exception as e:
            logging.warning("세션 종료 실패: %s", e)

    # 2. Slack 알림
    try:
        await asyncio.wait_for(
            self.slack_client.notify(f"시스템이 종료됩니다: {reason}"),
            timeout=5.0,
        )
    except (asyncio.TimeoutError, Exception):
        pass

    # 3. Slack 클라이언트 종료
    await self.slack_client.stop()

    # 4. 백그라운드 태스크 취소
    for task in self._background_tasks:
        task.cancel()
    await asyncio.gather(*self._background_tasks, return_exceptions=True)
    self._background_tasks.clear()

    # 5. Heartbeat 파일 삭제
    self.heartbeat_file.unlink(missing_ok=True)

    # 6. PID 잠금 해제
    self._release_pid_lock()

    self.state = SupervisorState.STOPPED
    logging.info("Supervisor 종료 완료.")
```

---

## 3. 상태 다이어그램

```
                         ┌─────────────────┐
                         │  INITIALIZING    │
                         │                  │
                         │ PID 잠금 획득     │
                         │ 상태 복구        │
                         │ Slack/Heartbeat  │
                         └────────┬─────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │        RUNNING          │◀──────────┐
                    │                         │           │
                    │  미션 선택              │           │
                    │  프롬프트 생성          │           │
                    └────────────┬────────────┘           │
                                 │                        │
                                 ▼                        │
                    ┌─────────────────────────┐           │
                    │    SESSION_ACTIVE       │           │
                    │                         │           │
                    │  stream-json 모니터링   │           │
                    │  이벤트 처리            │           │
                    └─────┬─────────┬─────────┘           │
                          │         │                     │
              정상 종료 ──┘         └── rate limit        │
                          │              │                │
                          │              ▼                │
                          │    ┌──────────────────┐       │
                          │    │    WAITING       │       │
                          │    │                  │       │
                          │    │  rate limit 대기 │       │
                          │    │  resume 재개     │       │
                          │    └────────┬─────────┘       │
                          │             │                 │
                          └──────┬──────┘                 │
                                 │                        │
                                 ▼                        │
                    ┌─────────────────────────┐           │
                    │    결과 처리            │───────────┘
                    │                         │
                    │  세션 이력 기록          │
                    │  에러 분류/복구          │
                    │  friction 기록          │
                    └─────────────────────────┘

                          SIGTERM/SIGINT
                               │
                               ▼
                    ┌─────────────────────────┐
                    │    SHUTTING_DOWN        │
                    │                         │
                    │  세션 종료              │
                    │  Slack 알림             │
                    │  태스크 취소            │
                    │  PID 해제              │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │       STOPPED           │
                    └─────────────────────────┘
```

---

## 4. launchd 구성

### 4.1 com.acc.supervisor.plist

Supervisor 프로세스를 macOS launchd LaunchAgent로 관리한다. 사용자 로그인 시 자동 시작되며, 크래시 시 자동 재시작된다.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>

    <!-- 서비스 식별자 -->
    <key>Label</key>
    <string>com.acc.supervisor</string>

    <!-- 실행 명령 -->
    <key>ProgramArguments</key>
    <array>
        <!--
            uv run을 통해 프로젝트 가상환경에서 실행한다.
            경로는 설치 시 acc configure가 실제 경로로 치환한다.
        -->
        <string>/Users/USERNAME/.local/bin/uv</string>
        <string>run</string>
        <string>--project</string>
        <string>/Users/USERNAME/dev/claude-automata</string>
        <string>python</string>
        <string>-m</string>
        <string>system.supervisor</string>
    </array>

    <!-- 작업 디렉토리 -->
    <key>WorkingDirectory</key>
    <string>/Users/USERNAME/dev/claude-automata</string>

    <!-- 항상 실행 유지: 크래시/종료 시 자동 재시작 -->
    <key>KeepAlive</key>
    <true/>

    <!--
        재시작 쓰로틀링: 10초 미만 간격으로 재시작하지 않는다.
        연속 크래시 시 빠른 재시작 폭주를 방지한다.
    -->
    <key>ThrottleInterval</key>
    <integer>10</integer>

    <!--
        종료 대기 시간: launchd가 SIGTERM 전송 후 30초 대기.
        30초 내에 종료되지 않으면 SIGKILL을 전송한다.
        graceful shutdown에 충분한 시간을 제공한다.
    -->
    <key>ExitTimeOut</key>
    <integer>30</integer>

    <!-- 환경 변수 -->
    <key>EnvironmentVariables</key>
    <dict>
        <!--
            PATH: claude CLI, uv, git 등이 있는 경로를 포함해야 한다.
            launchd 환경은 쉘 환경과 다르므로 명시적으로 설정한다.
        -->
        <key>PATH</key>
        <string>/Users/USERNAME/.local/bin:/Users/USERNAME/.cargo/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>

        <!-- Python 출력 버퍼링 비활성화: 로그가 즉시 파일에 기록되도록 -->
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>

        <!-- HOME 디렉토리: claude login 토큰 등이 여기에 저장됨 -->
        <key>HOME</key>
        <string>/Users/USERNAME</string>

        <!-- Claude Max 사용: API 키 명시적 미설정 -->
        <!-- ANTHROPIC_API_KEY는 의도적으로 설정하지 않음 -->
    </dict>

    <!--
        프로세스 유형: Background로 설정하여 macOS가 리소스 관리 시
        이 프로세스를 백그라운드 우선순위로 처리하도록 한다.
    -->
    <key>ProcessType</key>
    <string>Background</string>

    <!-- 표준 출력/에러를 파일로 리디렉션 -->
    <key>StandardOutPath</key>
    <string>/Users/USERNAME/dev/claude-automata/logs/supervisor-launchd-stdout.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/USERNAME/dev/claude-automata/logs/supervisor-launchd-stderr.log</string>

    <!--
        Nice: 프로세스 우선순위를 약간 낮춤 (기본 0, 범위 -20~20).
        시스템 전체 반응성에 영향을 주지 않도록 한다.
    -->
    <key>Nice</key>
    <integer>5</integer>

    <!--
        SoftResourceLimits: 열린 파일 수 제한 확장.
        Claude Code 세션과 Slack WebSocket이 파일 디스크립터를 사용한다.
    -->
    <key>SoftResourceLimits</key>
    <dict>
        <key>NumberOfFiles</key>
        <integer>4096</integer>
    </dict>

</dict>
</plist>
```

### 4.2 plist 필드 설명

| 필드 | 값 | 설명 |
|------|-----|------|
| `Label` | `com.acc.supervisor` | launchd 서비스 고유 식별자 |
| `KeepAlive` | `true` | 프로세스가 어떤 이유로든 종료되면 자동 재시작 |
| `ThrottleInterval` | `10` | 재시작 간 최소 간격(초). 빠른 크래시 루프 방지 |
| `ExitTimeOut` | `30` | SIGTERM 후 SIGKILL까지 대기(초). graceful shutdown 시간 |
| `ProcessType` | `Background` | macOS 리소스 관리에서 백그라운드 우선순위 |
| `PYTHONUNBUFFERED` | `1` | stdout/stderr 버퍼링 비활성화. 실시간 로그 보장 |
| `Nice` | `5` | CPU 스케줄링 우선순위를 약간 낮춤 |

---

## 5. Watchdog 구성

### 5.1 목적

Watchdog은 Supervisor와 독립적으로 실행되는 별도 LaunchAgent이다. Supervisor가 응답 불능(hang) 상태에 빠졌을 때 이를 감지하고 강제 재시작한다. launchd의 KeepAlive는 프로세스 종료만 감지하지 hang은 감지하지 못하므로, Watchdog이 이 공백을 메운다.

### 5.2 동작 원리

```
┌──────────────┐                    ┌──────────────────┐
│   Watchdog   │  reads             │  Supervisor      │
│  (launchd    │ ──────────────▶    │                  │
│   60초 간격) │  heartbeat file    │  writes every    │
│              │                    │  10초             │
│  staleness   │                    │                  │
│  > 120초?    │                    │  run/supervisor  │
│  → kickstart │                    │  .heartbeat      │
└──────────────┘                    └──────────────────┘
```

1. Supervisor가 10초마다 `run/supervisor.heartbeat`에 UNIX timestamp를 기록한다.
2. Watchdog이 60초마다 이 파일을 읽는다.
3. 현재 시간과 heartbeat timestamp의 차이가 120초를 초과하면 "stale"로 판정한다.
4. stale 판정 시 `launchctl kickstart -k` 명령으로 Supervisor를 강제 재시작한다.

### 5.3 com.acc.watchdog.plist

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>

    <key>Label</key>
    <string>com.acc.watchdog</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/USERNAME/.local/bin/uv</string>
        <string>run</string>
        <string>--project</string>
        <string>/Users/USERNAME/dev/claude-automata</string>
        <string>python</string>
        <string>-m</string>
        <string>system.watchdog</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/USERNAME/dev/claude-automata</string>

    <!--
        StartInterval: 60초마다 실행.
        KeepAlive와 달리 주기적으로 실행되고 종료되는 패턴이다.
    -->
    <key>StartInterval</key>
    <integer>60</integer>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/Users/USERNAME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
        <key>HOME</key>
        <string>/Users/USERNAME</string>
    </dict>

    <key>ProcessType</key>
    <string>Background</string>

    <key>StandardOutPath</key>
    <string>/Users/USERNAME/dev/claude-automata/logs/watchdog-stdout.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/USERNAME/dev/claude-automata/logs/watchdog-stderr.log</string>

    <key>Nice</key>
    <integer>10</integer>

</dict>
</plist>
```

### 5.4 watchdog.py 구현

```python
#!/usr/bin/env python3
"""
Watchdog — Supervisor heartbeat 감시 및 강제 재시작.

launchd StartInterval로 60초마다 실행된다.
실행 → 확인 → 조치(필요시) → 종료의 단순한 패턴이다.
"""

import logging
import subprocess
import sys
import time
from pathlib import Path

# 설정 상수
HEARTBEAT_FILE = Path(__file__).resolve().parent.parent / "run" / "supervisor.heartbeat"
STALENESS_THRESHOLD_S = 120.0  # heartbeat가 이 시간 이상 오래되면 stale
SUPERVISOR_SERVICE_TARGET = "gui/{uid}/com.acc.supervisor"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [watchdog] %(message)s",
)
log = logging.getLogger("watchdog")


def get_uid() -> int:
    """현재 사용자의 UID를 반환한다."""
    import os
    return os.getuid()


def read_heartbeat() -> float | None:
    """
    heartbeat 파일에서 timestamp를 읽는다.
    파일이 없거나 파싱 실패 시 None을 반환한다.
    """
    try:
        content = HEARTBEAT_FILE.read_text().strip()
        return float(content)
    except (FileNotFoundError, ValueError) as e:
        log.warning("Heartbeat 읽기 실패: %s", e)
        return None


def is_stale(heartbeat_ts: float | None) -> bool:
    """heartbeat timestamp가 staleness 임계값을 초과했는지 확인한다."""
    if heartbeat_ts is None:
        return True  # 파일 없음 = stale
    age = time.time() - heartbeat_ts
    log.info("Heartbeat age: %.1f초 (임계값: %.1f초)", age, STALENESS_THRESHOLD_S)
    return age > STALENESS_THRESHOLD_S


def kickstart_supervisor() -> None:
    """
    launchctl kickstart -k 명령으로 Supervisor를 강제 재시작한다.
    -k 플래그: 이미 실행 중이면 kill 후 재시작한다.
    """
    uid = get_uid()
    target = SUPERVISOR_SERVICE_TARGET.format(uid=uid)
    cmd = ["launchctl", "kickstart", "-k", target]
    log.warning("Supervisor stale — 강제 재시작: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            log.info("kickstart 성공.")
        else:
            log.error(
                "kickstart 실패: exit=%d stderr=%s",
                result.returncode, result.stderr,
            )
    except subprocess.TimeoutExpired:
        log.error("kickstart 명령 타임아웃.")
    except Exception as e:
        log.error("kickstart 예외: %s", e)


def main() -> None:
    """Watchdog 메인: heartbeat 확인 → stale이면 kickstart."""
    log.info("Watchdog 실행.")

    heartbeat_ts = read_heartbeat()

    if is_stale(heartbeat_ts):
        kickstart_supervisor()
    else:
        log.info("Supervisor 정상 동작 중.")


if __name__ == "__main__":
    main()
```

### 5.5 장애 시나리오별 복구 경로

| 시나리오 | 감지 주체 | 복구 방법 |
|----------|-----------|-----------|
| Supervisor 프로세스 크래시 (exit) | launchd KeepAlive | 자동 재시작 (ThrottleInterval 10초) |
| Supervisor hang (무한 루프, 데드락) | Watchdog | heartbeat stale 감지 → kickstart -k |
| Supervisor OOM kill | launchd KeepAlive | 자동 재시작 |
| macOS 재부팅 | launchd LaunchAgent | 로그인 시 자동 시작 |
| Heartbeat 파일 삭제 | Watchdog | stale로 판정 → kickstart |
| 양쪽 모두 크래시 | launchd | 각각 독립적으로 자동 재시작 |

---

## 6. 설치/제거

### 6.1 설치 (acc start)

`acc start` 명령이 실행하는 설치 절차이다.

```bash
#!/bin/bash
# acc start 내부에서 실행되는 설치 로직

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"
UID_CURRENT=$(id -u)

# 1. logs/, run/ 디렉토리 생성
mkdir -p "${PROJECT_ROOT}/logs"
mkdir -p "${PROJECT_ROOT}/run"

# 2. plist 파일 복사 (템플릿의 USERNAME을 실제 값으로 치환)
for plist in com.acc.supervisor.plist com.acc.watchdog.plist; do
    sed \
        -e "s|/Users/USERNAME|${HOME}|g" \
        "${PROJECT_ROOT}/setup/launchd/${plist}" \
        > "${LAUNCH_AGENTS_DIR}/${plist}"
done

# 3. LaunchAgent 등록 (bootstrap)
launchctl bootstrap "gui/${UID_CURRENT}" "${LAUNCH_AGENTS_DIR}/com.acc.supervisor.plist"
launchctl bootstrap "gui/${UID_CURRENT}" "${LAUNCH_AGENTS_DIR}/com.acc.watchdog.plist"

echo "claude-automata 시스템이 시작되었습니다."
echo "  Supervisor: launchctl print gui/${UID_CURRENT}/com.acc.supervisor"
echo "  Watchdog:   launchctl print gui/${UID_CURRENT}/com.acc.watchdog"
```

### 6.2 제거 (acc stop)

```bash
#!/bin/bash
# acc stop 내부에서 실행되는 제거 로직

LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"
UID_CURRENT=$(id -u)

# 1. LaunchAgent 등록 해제 (bootout)
# bootout은 SIGTERM을 전송하고 ExitTimeOut까지 대기한다
launchctl bootout "gui/${UID_CURRENT}/com.acc.watchdog" 2>/dev/null
launchctl bootout "gui/${UID_CURRENT}/com.acc.supervisor" 2>/dev/null

# 2. plist 파일 삭제
rm -f "${LAUNCH_AGENTS_DIR}/com.acc.supervisor.plist"
rm -f "${LAUNCH_AGENTS_DIR}/com.acc.watchdog.plist"

# 3. 런타임 파일 정리
rm -f "${PROJECT_ROOT}/run/supervisor.pid"
rm -f "${PROJECT_ROOT}/run/supervisor.heartbeat"
rm -f "${PROJECT_ROOT}/run/current_session.json"

echo "claude-automata 시스템이 중지되었습니다."
```

### 6.3 상태 확인

```bash
# Supervisor 상태
launchctl print gui/$(id -u)/com.acc.supervisor

# Watchdog 상태
launchctl print gui/$(id -u)/com.acc.watchdog

# Heartbeat 확인
cat run/supervisor.heartbeat

# PID 확인
cat run/supervisor.pid

# 로그 확인
tail -f logs/supervisor.log
```

---

## 7. 엔트리포인트

`system/supervisor.py`의 `__main__` 블록이다. `uv run python -m system.supervisor`로 실행된다.

```python
# system/supervisor.py 하단

def main() -> None:
    """Supervisor 엔트리포인트."""
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler("logs/supervisor.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    project_root = Path(__file__).resolve().parent.parent
    supervisor = Supervisor(project_root)

    try:
        asyncio.run(supervisor.run())
    except KeyboardInterrupt:
        pass  # SIGINT는 run() 내부에서 처리됨
    except SystemExit as e:
        logging.error("Supervisor 시작 실패: %s", e)
        raise


if __name__ == "__main__":
    main()
```
