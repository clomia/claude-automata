#!/usr/bin/env python3
"""
Watchdog — Supervisor heartbeat 감시 및 강제 재시작.

launchd StartInterval로 60초마다 실행된다.
실행 → 확인 → 조치(필요시) → 종료.

참조 요구사항: E-4 (독립적 감시)
"""

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

HEARTBEAT_FILE = (
    Path(__file__).resolve().parent.parent
    / "run"
    / "supervisor.heartbeat"
)
PID_FILE = (
    Path(__file__).resolve().parent.parent
    / "run"
    / "supervisor.pid"
)
STALENESS_THRESHOLD_S = 120.0
SUPERVISOR_SERVICE_LABEL = "com.clomia.automata.supervisor"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [watchdog] %(message)s",
)
log = logging.getLogger("watchdog")


def get_uid() -> int:
    return os.getuid()


def read_heartbeat() -> float | None:
    try:
        content = HEARTBEAT_FILE.read_text().strip()
        return float(content)
    except (FileNotFoundError, ValueError) as e:
        log.warning("Heartbeat 읽기 실패: %s", e)
        return None


def read_pid() -> int | None:
    try:
        content = PID_FILE.read_text().strip()
        return int(content)
    except (FileNotFoundError, ValueError):
        return None


def is_process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def is_stale(heartbeat_ts: float | None) -> bool:
    if heartbeat_ts is None:
        return True
    age = time.time() - heartbeat_ts
    log.info(
        "Heartbeat age: %.1f초 (임계값: %.1f초)",
        age,
        STALENESS_THRESHOLD_S,
    )
    return age > STALENESS_THRESHOLD_S


def kill_process(pid: int) -> None:
    """SIGTERM → 10초 대기 → SIGKILL."""
    import signal

    log.warning("SIGTERM 전송: pid=%d", pid)
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return

    for _ in range(10):
        time.sleep(1)
        if not is_process_alive(pid):
            log.info("프로세스 종료됨: pid=%d", pid)
            return

    log.warning("SIGKILL 전송: pid=%d", pid)
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def kickstart_supervisor() -> None:
    uid = get_uid()
    target = f"gui/{uid}/{SUPERVISOR_SERVICE_LABEL}"
    cmd = ["launchctl", "kickstart", "-k", target]
    log.warning(
        "Supervisor 강제 재시작: %s", " ".join(cmd)
    )

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            log.info("kickstart 성공.")
        else:
            log.error(
                "kickstart 실패: exit=%d stderr=%s",
                result.returncode,
                result.stderr,
            )
    except subprocess.TimeoutExpired:
        log.error("kickstart 명령 타임아웃.")
    except Exception as e:
        log.error("kickstart 예외: %s", e)


def cleanup_pid_file() -> None:
    try:
        PID_FILE.unlink()
        log.info("Stale PID 파일 삭제됨.")
    except FileNotFoundError:
        pass


def main() -> None:
    log.info("Watchdog 실행.")

    heartbeat_ts = read_heartbeat()

    if not is_stale(heartbeat_ts):
        log.info("Supervisor 정상 동작 중.")
        return

    log.warning("Supervisor stale 감지!")

    pid = read_pid()

    if pid is not None:
        if is_process_alive(pid):
            log.warning(
                "프로세스 존재하지만 응답 없음: pid=%d", pid
            )
            kill_process(pid)
        else:
            log.warning(
                "Stale PID 파일 (프로세스 없음): pid=%d",
                pid,
            )
        cleanup_pid_file()

    kickstart_supervisor()


if __name__ == "__main__":
    main()
