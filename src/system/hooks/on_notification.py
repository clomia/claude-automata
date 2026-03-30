#!/usr/bin/env python3
"""
Notification Hook: Claude Code 알림을 Slack/TUI로 전달한다.

Claude Code Hook 프로토콜:
- stdin: JSON (hook_type, type, session_id, message)
- stdout: JSON ({})
- exit 0: 정상 처리
"""

import json
import logging
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
RUN_DIR = PROJECT_ROOT / "run"


def _timeout_handler(signum: int, frame: object) -> None:
    print(json.dumps({}))
    sys.exit(0)


signal.signal(signal.SIGALRM, _timeout_handler)
signal.alarm(8)

LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOGS_DIR / "hooks.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("automata.hook.notification")


def write_notification_file(notification: dict) -> None:
    """알림을 run/notifications.json에 추가한다."""
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    notifications_path = RUN_DIR / "notifications.json"

    try:
        data = json.loads(
            notifications_path.read_text(encoding="utf-8")
        )
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"notifications": []}

    data["notifications"].append(notification)

    if len(data["notifications"]) > 100:
        data["notifications"] = data["notifications"][-100:]

    tmp = notifications_path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.rename(notifications_path)


def main() -> None:
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        input_data = {}

    notification_type = input_data.get("type", "unknown")
    session_id = input_data.get("session_id", "unknown")
    message = input_data.get("message", "")

    now = datetime.now(timezone.utc).isoformat()

    if notification_type == "idle_prompt":
        logger.warning(
            "Idle prompt received (session: %s)", session_id
        )
        write_notification_file(
            {
                "type": "idle_prompt",
                "level": "warning",
                "text": "시스템이 유휴 상태입니다",
                "detail": message,
                "session_id": session_id,
                "created_at": now,
                "sent": False,
            }
        )

    elif notification_type == "permission_prompt":
        logger.warning(
            "Permission prompt received (session: %s): %s",
            session_id,
            message,
        )
        write_notification_file(
            {
                "type": "permission_prompt",
                "level": "warning",
                "text": "권한 프롬프트가 발생했습니다 (비정상)",
                "detail": message,
                "session_id": session_id,
                "created_at": now,
                "sent": False,
            }
        )

    elif notification_type == "auth_success":
        logger.info(
            "Authentication successful (session: %s)", session_id
        )

    else:
        logger.info(
            "Unknown notification type '%s' (session: %s): %s",
            notification_type,
            session_id,
            message,
        )

    print(json.dumps({}))


if __name__ == "__main__":
    main()
