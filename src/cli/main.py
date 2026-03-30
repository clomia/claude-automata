"""
claude-automata CLI.

엔트리포인트: automata
모든 시스템 관리 명령을 제공한다.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_state_manager():
    from system.state_manager import StateManager
    return StateManager(PROJECT_ROOT)


# ── configure ──

def cmd_configure(args: argparse.Namespace) -> None:
    """초기 설정: Slack 토큰, 목적 입력, .env 생성."""
    env_path = PROJECT_ROOT / ".env"

    print("claude-automata 초기 설정")
    print("=" * 50)

    # Slack 토큰
    bot_token = input("\nSlack Bot Token (xoxb-...): ").strip()
    app_token = input("Slack App Token (xapp-...): ").strip()
    channel_id = input("Slack Channel ID (C...): ").strip()

    # 목적 입력
    print("\n시스템의 목적을 입력하세요.")
    print("(예: '자동화된 블로그 콘텐츠 생성 시스템을 만들고 싶어')")
    raw_purpose = input("\n목적: ").strip()

    if not raw_purpose:
        print("오류: 목적을 입력해야 합니다.")
        sys.exit(1)

    # Slack 연결 검증
    if bot_token:
        print("\nSlack 연결 검증 중...")
        try:
            from slack_sdk.web import WebClient
            client = WebClient(token=bot_token)
            result = client.auth_test()
            print(f"  Slack 연결 성공: {result['team']}")
        except Exception as e:
            print(f"  경고: Slack 연결 실패 ({e}). 나중에 재설정 가능합니다.")

    # .env 생성
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(f"SLACK_BOT_TOKEN={bot_token}\n")
        f.write(f"SLACK_APP_TOKEN={app_token}\n")
        f.write(f"SLACK_CHANNEL_ID={channel_id}\n")
        f.write(f"AUTOMATA_RAW_PURPOSE={raw_purpose}\n")

    # state/ 초기 파일 생성
    sm = get_state_manager()

    # purpose.json 초기화 (raw_input만, purpose는 Initialization Session이 채움)
    sm.save_purpose({
        "raw_input": raw_purpose,
        "purpose": "",
        "domain": "",
        "key_directions": [],
        "constructed_at": "",
        "last_evolved_at": "",
        "evolution_history": [],
    })

    # 빈 상태 파일들 초기화
    sm.save_missions({
        "missions": [],
        "next_id": 1,
        "metadata": {
            "total_created": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_blocked": 0,
        },
    })
    sm.save_friction({"frictions": [], "next_id": 1})
    sm.save_requests({"requests": [], "next_id": 1})
    sm.save_sessions({"sessions": []})
    sm.save_strategy({})

    # config.toml 초기화
    config_path = sm.state_dir / "config.toml"
    if not config_path.exists():
        config_path.write_text(
            '# claude-automata 동적 설정\n'
            '# 시스템(Claude Code)이 자기개선의 일환으로 이 값들을 직접 수정할 수 있다 (S-5)\n\n'
            'friction_threshold = 3\n'
            'proactive_improvement_interval = 10\n'
            'context_refresh_after_compactions = 5\n'
            'goal_drift_check_interval = 20\n'
            'session_timeout_minutes = 120\n'
            'max_consecutive_failures = 3\n'
            'slack_notification_level = "warning"\n'
            'mission_idle_generation_count = 3\n'
            'owner_feedback_interval = 20\n'
            'all_thresholds_modifiable = true\n',
            encoding="utf-8",
        )

    print(f"\n설정 완료. 파일: {env_path}")
    print("다음 명령으로 시스템을 시작하세요: automata start")


# ── start ──

def cmd_start(args: argparse.Namespace) -> None:
    """LaunchAgent 설치 + Supervisor 시작."""
    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    launch_agents_dir.mkdir(parents=True, exist_ok=True)

    setup_dir = PROJECT_ROOT / "setup" / "launchd"
    uid = os.getuid()
    home = str(Path.home())

    # logs, run 디렉토리 생성
    (PROJECT_ROOT / "logs").mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "run").mkdir(parents=True, exist_ok=True)

    for plist_name in [
        "com.clomia.automata.supervisor.plist",
        "com.clomia.automata.watchdog.plist",
    ]:
        src = setup_dir / plist_name
        if not src.exists():
            print(f"경고: {src} 파일이 없습니다.")
            continue

        content = src.read_text(encoding="utf-8")
        content = content.replace("/Users/USERNAME", home)
        content = content.replace(
            "/Users/USERNAME/dev/claude-automata",
            str(PROJECT_ROOT),
        )

        dst = launch_agents_dir / plist_name
        dst.write_text(content, encoding="utf-8")
        print(f"설치: {dst}")

        # bootstrap
        target = f"gui/{uid}"
        result = subprocess.run(
            ["launchctl", "bootstrap", target, str(dst)],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"  시작됨: {plist_name}")
        else:
            # 이미 로드된 경우
            if "already loaded" in result.stderr.lower() or result.returncode == 37:
                print(f"  이미 실행 중: {plist_name}")
            else:
                print(f"  경고: {result.stderr.strip()}")

    print("\nclaude-automata 시스템이 시작되었습니다.")
    print(f"  로그: tail -f {PROJECT_ROOT}/logs/supervisor.log")
    print(f"  상태: automata status")


# ── stop ──

def cmd_stop(args: argparse.Namespace) -> None:
    """시스템 중지 + LaunchAgent 제거."""
    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    uid = os.getuid()

    for label in [
        "com.clomia.automata.watchdog",
        "com.clomia.automata.supervisor",
    ]:
        target = f"gui/{uid}/{label}"
        subprocess.run(
            ["launchctl", "bootout", target],
            capture_output=True,
        )
        plist = launch_agents_dir / f"{label}.plist"
        if plist.exists():
            plist.unlink()
            print(f"제거: {label}")

    # 런타임 파일 정리
    for f in ["supervisor.pid", "supervisor.heartbeat", "current_session.json"]:
        p = PROJECT_ROOT / "run" / f
        p.unlink(missing_ok=True)

    print("claude-automata 시스템이 중지되었습니다.")


# ── restart ──

def cmd_restart(args: argparse.Namespace) -> None:
    """stop → start."""
    cmd_stop(args)
    time.sleep(2)
    cmd_start(args)


# ── status ──

def cmd_status(args: argparse.Namespace) -> None:
    """현재 상태 출력."""
    sm = get_state_manager()

    # Supervisor 상태
    heartbeat_file = PROJECT_ROOT / "run" / "supervisor.heartbeat"
    pid_file = PROJECT_ROOT / "run" / "supervisor.pid"

    if heartbeat_file.exists():
        try:
            ts = float(heartbeat_file.read_text().strip())
            age = time.time() - ts
            if age < 30:
                sup_status = "실행 중"
            elif age < 120:
                sup_status = "응답 없음"
            else:
                sup_status = "중지됨 (stale)"
        except ValueError:
            sup_status = "알 수 없음"
    else:
        sup_status = "중지됨"

    pid = "N/A"
    if pid_file.exists():
        pid = pid_file.read_text().strip()

    print(f"=== claude-automata 상태 ===")
    print(f"Supervisor: {sup_status} (PID: {pid})")

    # Purpose
    purpose = sm.load_purpose()
    if purpose.get("purpose"):
        print(f"Purpose: {purpose['purpose'][:80]}...")
    else:
        print("Purpose: (미설정)")

    # 미션 큐
    missions = sm.load_missions()
    all_m = missions.get("missions", [])
    pending = sum(1 for m in all_m if m["status"] == "pending")
    in_progress = sum(1 for m in all_m if m["status"] == "in_progress")
    completed = sum(1 for m in all_m if m["status"] == "completed")
    blocked = sum(1 for m in all_m if m["status"] == "blocked")
    print(f"미션: 대기 {pending} | 진행 {in_progress} | 완료 {completed} | 차단 {blocked}")

    # 현재 세션
    current = sm.load_current_session()
    if current:
        print(f"현재 세션: {current.get('session_id', 'N/A')}")
        print(f"  미션: {current.get('mission_id', 'N/A')}")
    else:
        print("현재 세션: 없음")

    # Friction
    friction = sm.load_friction()
    unresolved = sum(
        1 for f in friction.get("frictions", []) if not f.get("resolved_at")
    )
    print(f"Friction: {unresolved}건 미해결")

    # 격리 상태
    print(f"\n=== 격리 상태 ===")
    print(f"[Tier 1] Model: opus (--model opus)")
    print(f"[Tier 1] Effort: max (CLAUDE_CODE_EFFORT_LEVEL=max)")
    print(f"[Tier 1] MCP 격리: --strict-mcp-config")
    print(f"[Tier 2] Settings: --setting-sources project,local")


# ── tui ──

def cmd_tui(args: argparse.Namespace) -> None:
    """Textual TUI 실행."""
    from tui.app import DashboardApp
    app = DashboardApp()
    app.run()


# ── logs ──

def cmd_logs(args: argparse.Namespace) -> None:
    """로그 출력."""
    log_file = PROJECT_ROOT / "logs" / (args.file or "supervisor.log")
    if not log_file.exists():
        print(f"로그 파일 없음: {log_file}")
        sys.exit(1)

    if args.follow:
        os.execvp("tail", ["tail", "-f", str(log_file)])
    else:
        n = args.lines or 50
        os.execvp("tail", ["tail", f"-{n}", str(log_file)])


# ── inject ──

def cmd_inject(args: argparse.Namespace) -> None:
    """미션 큐에 수동 주입."""
    sm = get_state_manager()
    mission_id = sm.add_mission({
        "title": args.title,
        "description": args.description or args.title,
        "success_criteria": [args.title],
        "priority": args.priority,
        "source": "owner",
    })
    print(f"미션 주입 완료: {mission_id} — {args.title}")


# ── reset ──

def cmd_reset(args: argparse.Namespace) -> None:
    """체크포인트로 롤백."""
    sm = get_state_manager()
    checkpoints = sm.list_checkpoints()

    if not checkpoints:
        print("체크포인트가 없습니다.")
        sys.exit(1)

    if args.checkpoint:
        tag = args.checkpoint
    else:
        tag = checkpoints[0]
        print(f"최근 체크포인트로 롤백: {tag}")

    confirm = input(f"'{tag}'로 롤백하시겠습니까? (y/N): ")
    if confirm.lower() != "y":
        print("취소됨.")
        return

    sm.restore_checkpoint(tag)
    print(f"롤백 완료: {tag}")


# ── purpose ──

def cmd_purpose(args: argparse.Namespace) -> None:
    """현재 Purpose 출력."""
    sm = get_state_manager()
    purpose = sm.load_purpose()

    if purpose.get("purpose"):
        print(f"Purpose: {purpose['purpose']}")
        print(f"도메인: {purpose.get('domain', 'N/A')}")
        print(f"구성일: {purpose.get('constructed_at', 'N/A')}")
        if purpose.get("key_directions"):
            print("\n핵심 방향:")
            for d in purpose["key_directions"]:
                print(f"  - {d}")
    else:
        print("Purpose가 아직 구성되지 않았습니다.")
        print("'automata configure'로 목적을 설정한 후 'automata start'를 실행하세요.")


# ── Main ──

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="automata",
        description="claude-automata — 목적을 가지고 AI를 영속적으로 실행시키는 재귀적 자기개선 시스템",
    )
    subparsers = parser.add_subparsers(dest="command", help="서브커맨드")

    subparsers.add_parser("configure", help="초기 설정")
    subparsers.add_parser("start", help="시스템 시작")
    subparsers.add_parser("stop", help="시스템 중지")
    subparsers.add_parser("restart", help="시스템 재시작")
    subparsers.add_parser("status", help="현재 상태 출력")
    subparsers.add_parser("tui", help="TUI 대시보드 실행")

    logs_parser = subparsers.add_parser("logs", help="로그 출력")
    logs_parser.add_argument("--follow", "-f", action="store_true", help="실시간 추적")
    logs_parser.add_argument("--file", default="supervisor.log", help="로그 파일명")
    logs_parser.add_argument("--lines", "-n", type=int, default=50, help="출력 줄 수")

    inject_parser = subparsers.add_parser("inject", help="미션 수동 주입")
    inject_parser.add_argument("title", help="미션 제목")
    inject_parser.add_argument("--description", "-d", default="", help="미션 설명")
    inject_parser.add_argument("--priority", "-p", type=int, default=5, help="우선순위 (0=최고)")

    reset_parser = subparsers.add_parser("reset", help="체크포인트로 롤백")
    reset_parser.add_argument("checkpoint", nargs="?", help="체크포인트 태그명")

    subparsers.add_parser("purpose", help="현재 Purpose 출력")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    commands = {
        "configure": cmd_configure,
        "start": cmd_start,
        "stop": cmd_stop,
        "restart": cmd_restart,
        "status": cmd_status,
        "tui": cmd_tui,
        "logs": cmd_logs,
        "inject": cmd_inject,
        "reset": cmd_reset,
        "purpose": cmd_purpose,
    }

    handler = commands.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
