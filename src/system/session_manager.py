"""
Session Manager.

Claude Code CLI 프로세스의 생명주기를 관리한다.
시작, 모니터링, 종료, 재개를 담당한다.

참조 요구사항: E-1 (격리), E-2 (장애 불멸), Q-1 (opus max)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator


class SessionState(Enum):
    LAUNCHING = "launching"
    RUNNING = "running"
    RATE_LIMITED = "rate_limited"
    STOPPING = "stopping"
    COMPLETED = "completed"
    CRASHED = "crashed"
    TIMED_OUT = "timed_out"


@dataclass
class StreamEvent:
    """stream-json에서 파싱한 단일 이벤트."""

    type: str = ""
    subtype: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def session_id(self) -> str:
        return self.data.get("session_id", "")

    @property
    def is_rate_limit(self) -> bool:
        return (
            self.type == "system"
            and self.subtype == "api_retry"
            and self.data.get("error") == "rate_limit"
        )

    @property
    def retry_delay_ms(self) -> int:
        return self.data.get("retry_delay_ms", 0)

    @property
    def is_result(self) -> bool:
        return self.type == "result"

    @property
    def result_text(self) -> str:
        return self.data.get("result", "")

    @property
    def is_error(self) -> bool:
        return self.data.get("is_error", False)

    @property
    def is_tool_use(self) -> bool:
        return self.subtype == "tool_use"

    @property
    def is_tool_result(self) -> bool:
        return self.subtype == "tool_result"


@dataclass
class SessionInfo:
    session_id: str = ""
    process: asyncio.subprocess.Process | None = None
    state: SessionState = SessionState.LAUNCHING
    prompt: str = ""
    mission_id: str = ""

    started_at: float = field(default_factory=time.time)
    ended_at: float | None = None

    exit_code: int | None = None
    result_text: str = ""
    is_error: bool = False
    cost_usd: float = 0.0
    num_turns: int = 0
    duration_ms: int = 0

    stderr_buffer: str = ""
    last_event: StreamEvent | None = None

    event_count: int = 0
    tool_use_count: int = 0
    api_retry_count: int = 0
    compaction_count: int = 0


@dataclass
class SessionStatus:
    is_active: bool = False
    session_id: str = ""
    state: SessionState = SessionState.COMPLETED
    mission_id: str = ""
    running_seconds: float = 0.0
    event_count: int = 0
    tool_use_count: int = 0
    api_retry_count: int = 0
    last_event_type: str = ""
    last_event_time: float = 0.0


class SessionManager:
    """Claude Code 프로세스의 생명주기를 관리한다."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.log = logging.getLogger("automata.session_manager")
        self._current: SessionInfo | None = None
        self._claude_bin: str = "claude"
        self._session_env: dict[str, str] = self._build_session_env()
        self.session_timeout_s: float = 0
        self.graceful_shutdown_timeout_s: float = 10.0

    def _build_session_env(self) -> dict[str, str]:
        """Claude Code 프로세스에 전달할 격리된 환경 변수를 구성한다."""
        env = os.environ.copy()

        # Tier 1: 핵심 동작 고정
        env["CLAUDE_CODE_EFFORT_LEVEL"] = "max"
        env["CLAUDE_CODE_SUBAGENT_MODEL"] = "opus"
        env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] = "1"
        env["DISABLE_AUTOUPDATER"] = "1"

        # 오염 변수 제거
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("ANTHROPIC_MODEL", None)
        env.pop("CLAUDE_AUTOCOMPACT_PCT_OVERRIDE", None)

        # Python
        env["PYTHONUNBUFFERED"] = "1"

        return env

    def _build_launch_command(
        self,
        prompt: str,
        *,
        resume_session_id: str | None = None,
    ) -> list[str]:
        """Claude Code CLI 실행 명령을 구성한다."""
        cmd = [
            self._claude_bin,
            "-p",
            prompt,
            "--dangerously-skip-permissions",
            "--model",
            "opus",
            "--effort",
            "max",
            "--output-format",
            "stream-json",
            "--setting-sources",
            "project,local",
            "--strict-mcp-config",
            "--mcp-config",
            "{}",
        ]

        if resume_session_id is not None:
            cmd.extend(["--resume", resume_session_id])

        return cmd

    async def launch_session(
        self,
        prompt: str,
        *,
        mission_id: str = "",
    ) -> SessionInfo:
        """새 Claude Code 세션을 시작한다."""
        if (
            self._current is not None
            and self._current.state == SessionState.RUNNING
        ):
            raise RuntimeError(
                f"이미 활성 세션 존재: {self._current.session_id}"
            )

        cmd = self._build_launch_command(prompt)
        self.log.info("세션 시작: %s", " ".join(cmd[:6]) + " ...")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.project_root),
            env=self._session_env,
            start_new_session=True,
        )

        info = SessionInfo(
            process=proc,
            state=SessionState.LAUNCHING,
            prompt=prompt,
            mission_id=mission_id,
        )
        self._current = info
        self.log.info("프로세스 시작됨: pid=%d", proc.pid)
        return info

    async def resume_session(
        self,
        session_id: str,
        prompt: str,
        *,
        mission_id: str = "",
    ) -> SessionInfo:
        """기존 세션을 --resume으로 재개한다."""
        cmd = self._build_launch_command(
            prompt, resume_session_id=session_id
        )
        self.log.info("세션 재개: session_id=%s", session_id)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.project_root),
            env=self._session_env,
            start_new_session=True,
        )

        info = SessionInfo(
            session_id=session_id,
            process=proc,
            state=SessionState.LAUNCHING,
            prompt=prompt,
            mission_id=mission_id,
        )
        self._current = info
        self.log.info(
            "세션 재개 프로세스 시작됨: pid=%d", proc.pid
        )
        return info

    async def monitor_session(
        self,
        proc: asyncio.subprocess.Process,
    ) -> AsyncIterator[StreamEvent]:
        """실행 중인 세션의 stream-json 출력을 파싱하여 이벤트 스트림으로 제공한다."""
        assert (
            proc.stdout is not None
        ), "stdout이 PIPE로 설정되어야 합니다"

        info = self._current
        if info is not None:
            info.state = SessionState.RUNNING

        stderr_task = asyncio.create_task(
            self._collect_stderr(proc), name="stderr-collector"
        )

        try:
            while True:
                try:
                    if self.session_timeout_s > 0:
                        line_bytes = await asyncio.wait_for(
                            proc.stdout.readline(),
                            timeout=self.session_timeout_s,
                        )
                    else:
                        line_bytes = await proc.stdout.readline()
                except asyncio.TimeoutError:
                    self.log.warning(
                        "세션 타임아웃: %s초",
                        self.session_timeout_s,
                    )
                    if info is not None:
                        info.state = SessionState.TIMED_OUT
                    await self._force_terminate(proc)
                    return

                if not line_bytes:
                    break

                line = line_bytes.decode(
                    "utf-8", errors="replace"
                ).strip()
                if not line:
                    continue

                event = self._parse_stream_line(line)
                if event is None:
                    continue

                self._update_session_info(info, event)
                yield event

        finally:
            await proc.wait()
            stderr_task.cancel()
            try:
                await stderr_task
            except asyncio.CancelledError:
                pass

            if info is not None:
                info.exit_code = proc.returncode
                info.ended_at = time.time()
                if info.state == SessionState.RUNNING:
                    if proc.returncode == 0:
                        info.state = SessionState.COMPLETED
                    else:
                        info.state = SessionState.CRASHED

            self.log.info(
                "세션 종료: pid=%d exit_code=%s state=%s",
                proc.pid,
                proc.returncode,
                info.state.value if info else "unknown",
            )

    def _parse_stream_line(
        self, line: str
    ) -> StreamEvent | None:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            self.log.debug(
                "JSON 파싱 실패 (무시): %s", line[:200]
            )
            return None

        event_type = data.get("type", "")
        subtype = data.get("subtype", "")

        if event_type == "assistant" and not subtype:
            content = data.get("content", [])
            if content and isinstance(content, list):
                first_type = content[0].get("type", "")
                if first_type in ("tool_use", "tool_result"):
                    subtype = first_type
                else:
                    subtype = "text"

        return StreamEvent(type=event_type, subtype=subtype, data=data)

    def _update_session_info(
        self,
        info: SessionInfo | None,
        event: StreamEvent,
    ) -> None:
        if info is None:
            return

        info.last_event = event
        info.event_count += 1

        match event.type:
            case "system" if event.subtype == "init":
                info.session_id = event.session_id
                info.state = SessionState.RUNNING

            case "system" if event.subtype == "api_retry":
                info.api_retry_count += 1
                if event.is_rate_limit:
                    info.state = SessionState.RATE_LIMITED

            case "assistant" if event.is_tool_use:
                info.tool_use_count += 1

            case "result":
                info.result_text = event.result_text
                info.is_error = event.is_error
                info.cost_usd = event.data.get(
                    "total_cost_usd", 0.0
                )
                info.num_turns = event.data.get("num_turns", 0)
                info.duration_ms = event.data.get(
                    "duration_ms", 0
                )
                if event.is_error:
                    info.state = SessionState.CRASHED
                else:
                    info.state = SessionState.COMPLETED

    async def _collect_stderr(
        self, proc: asyncio.subprocess.Process
    ) -> None:
        assert proc.stderr is not None
        try:
            buffer_parts: list[str] = []
            while True:
                line = await proc.stderr.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace")
                buffer_parts.append(text)
                self.log.debug("STDERR> %s", text.strip())

            if self._current is not None:
                self._current.stderr_buffer = "".join(buffer_parts)
        except asyncio.CancelledError:
            pass

    async def terminate_session(
        self,
        session_id: str,
        *,
        graceful: bool = True,
    ) -> None:
        """실행 중인 세션을 종료한다."""
        info = self._current
        if info is None or info.session_id != session_id:
            self.log.warning(
                "종료할 세션을 찾을 수 없음: %s", session_id
            )
            return

        proc = info.process
        if proc is None or proc.returncode is not None:
            self.log.info("프로세스가 이미 종료됨.")
            return

        info.state = SessionState.STOPPING

        try:
            pgid = os.getpgid(proc.pid)
        except ProcessLookupError:
            self.log.info("프로세스가 이미 종료됨.")
            return

        if graceful:
            self.log.info(
                "SIGTERM 전송: pid=%d pgid=%d", proc.pid, pgid
            )
            try:
                os.killpg(pgid, signal.SIGTERM)
            except ProcessLookupError:
                self.log.info("프로세스 그룹이 이미 종료됨.")
                return

            try:
                await asyncio.wait_for(
                    proc.wait(),
                    timeout=self.graceful_shutdown_timeout_s,
                )
                self.log.info(
                    "graceful 종료 성공: exit_code=%s",
                    proc.returncode,
                )
                info.exit_code = proc.returncode
                info.state = SessionState.COMPLETED
                return
            except asyncio.TimeoutError:
                self.log.warning(
                    "SIGTERM 타임아웃 (%s초) — SIGKILL 전송",
                    self.graceful_shutdown_timeout_s,
                )

        await self._force_terminate(proc)

    async def _force_terminate(
        self, proc: asyncio.subprocess.Process
    ) -> None:
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGKILL)
            self.log.info("SIGKILL 전송: pgid=%d", pgid)
        except ProcessLookupError:
            self.log.info("프로세스 그룹이 이미 종료됨.")
            return

        await proc.wait()
        if self._current is not None:
            self._current.exit_code = proc.returncode
            if self._current.state != SessionState.TIMED_OUT:
                self._current.state = SessionState.COMPLETED
        self.log.info(
            "강제 종료 완료: exit_code=%s", proc.returncode
        )

    def get_session_status(self) -> SessionStatus:
        if self._current is None:
            return SessionStatus(is_active=False)

        info = self._current
        running_seconds = 0.0
        if info.ended_at is not None:
            running_seconds = info.ended_at - info.started_at
        elif info.state in (
            SessionState.RUNNING,
            SessionState.RATE_LIMITED,
        ):
            running_seconds = time.time() - info.started_at

        return SessionStatus(
            is_active=info.state
            in (
                SessionState.LAUNCHING,
                SessionState.RUNNING,
                SessionState.RATE_LIMITED,
                SessionState.STOPPING,
            ),
            session_id=info.session_id,
            state=info.state,
            mission_id=info.mission_id,
            running_seconds=running_seconds,
            event_count=info.event_count,
            tool_use_count=info.tool_use_count,
            api_retry_count=info.api_retry_count,
            last_event_type=(
                f"{info.last_event.type}/{info.last_event.subtype}"
                if info.last_event
                else ""
            ),
            last_event_time=(
                info.last_event.timestamp
                if info.last_event
                else 0.0
            ),
        )
