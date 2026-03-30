"""
claude-automata TUI 대시보드.

Textual 기반 실시간 모니터링 + 상호작용 인터페이스.
Supervisor와 독립 프로세스로 실행. 파일 기반 통신.

참조 요구사항: O-7 (실시간 TUI), O-8 (상호작용)
"""

from __future__ import annotations

import asyncio
import json
import time
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    RichLog,
    Static,
    TabbedContent,
    TabPane,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ── State Reading ──


def read_json(rel_path: str) -> dict | None:
    try:
        path = PROJECT_ROOT / rel_path
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def read_toml(rel_path: str) -> dict | None:
    try:
        path = PROJECT_ROOT / rel_path
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, tomllib.TOMLDecodeError, OSError):
        return None


def heartbeat_age() -> float:
    try:
        path = PROJECT_ROOT / "run" / "supervisor.heartbeat"
        content = path.read_text().strip()
        return time.time() - float(content)
    except (FileNotFoundError, ValueError, OSError):
        return float("inf")


def atomic_write_json(rel_path: str, data: dict) -> None:
    import os
    import tempfile

    path = PROJECT_ROOT / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, str(path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ── Dashboard Tab Widgets ──


class SystemStatusBar(Static):
    status = reactive("unknown")
    uptime = reactive("--")

    def render(self) -> str:
        indicators = {
            "running": ("[green]●[/]", "실행 중"),
            "unresponsive": ("[yellow]●[/]", "응답 없음"),
            "stopped": ("[red]●[/]", "중지됨"),
            "unknown": ("[dim]●[/]", "확인 중..."),
        }
        dot, label = indicators.get(
            self.status, ("[dim]●[/]", "알 수 없음")
        )
        return f" {dot} 시스템: {label}  |  가동: {self.uptime}"


class CurrentMissionPanel(Static):
    def render(self) -> str:
        return self._text

    _text: str = "[dim]미션 대기 중...[/]"

    def update_data(
        self, missions: dict | None
    ) -> None:
        if not missions:
            return
        in_progress = [
            m
            for m in missions.get("missions", [])
            if m.get("status") == "in_progress"
        ]
        if in_progress:
            m = in_progress[0]
            self._text = (
                f"[bold]{m['id']}[/]: {m.get('title', '?')}\n"
                f"  상태: 진행 중"
            )
        else:
            self._text = "[dim]미션 대기 중...[/]"
        self.refresh()


class StatsPanel(Static):
    def render(self) -> str:
        return self._text

    _text: str = "[dim]통계 로딩 중...[/]"

    def update_data(
        self,
        missions: dict | None,
        friction: dict | None,
    ) -> None:
        m_list = (
            missions.get("missions", []) if missions else []
        )
        total = len(m_list)
        completed = sum(
            1
            for m in m_list
            if m.get("status") == "completed"
        )
        failed = sum(
            1
            for m in m_list
            if m.get("status") == "failed"
        )

        f_list = (
            friction.get("frictions", []) if friction else []
        )
        f_unresolved = sum(
            1 for f in f_list if not f.get("resolved_at")
        )

        self._text = (
            f"완료: {completed}/{total}  |  "
            f"실패: {failed}  |  "
            f"Friction: {f_unresolved}건"
        )
        self.refresh()


class PurposePanel(Static):
    def render(self) -> str:
        return self._text

    _text: str = "[dim]Purpose 로딩 중...[/]"

    def update_data(self, purpose: dict | None) -> None:
        if purpose and purpose.get("purpose"):
            self._text = (
                f'[bold]Purpose:[/] "{purpose["purpose"]}"'
            )
        else:
            self._text = "[dim]Purpose 미설정[/]"
        self.refresh()


# ── Mission Queue Tab ──


class MissionTable(DataTable):
    STATUS_MAP = {
        "pending": "대기",
        "in_progress": "진행",
        "completed": "완료",
        "failed": "실패",
        "blocked": "차단",
    }

    def on_mount(self) -> None:
        self.add_columns("ID", "제목", "상태", "우선", "소스")
        self.cursor_type = "row"

    def update_data(self, missions: dict | None) -> None:
        self.clear()
        if not missions:
            return

        m_list = missions.get("missions", [])
        order = {
            "in_progress": 0,
            "blocked": 1,
            "pending": 2,
            "failed": 3,
            "completed": 4,
        }
        m_list_sorted = sorted(
            m_list,
            key=lambda m: (
                order.get(m.get("status", "pending"), 99),
                m.get("priority", 99),
            ),
        )

        for m in m_list_sorted:
            self.add_row(
                m.get("id", "?"),
                (m.get("title", "?"))[:40],
                self.STATUS_MAP.get(
                    m.get("status", "?"), "?"
                ),
                str(m.get("priority", "?")),
                m.get("source", "?")[:5],
                key=m.get("id"),
            )


# ── Slack Tab ──


class RequestTable(DataTable):
    def on_mount(self) -> None:
        self.add_columns("ID", "질문", "상태", "경과")
        self.cursor_type = "row"

    def update_data(
        self, requests: dict | None
    ) -> None:
        self.clear()
        if not requests:
            return

        now = datetime.now(timezone.utc)
        for req in sorted(
            requests.get("requests", []),
            key=lambda r: (
                0 if r.get("status") == "pending" else 1,
                r.get("created_at", ""),
            ),
        ):
            try:
                created = datetime.fromisoformat(
                    req.get("created_at", "")
                )
                delta = now - created
                elapsed = (
                    f"{delta.days}d"
                    if delta.days > 0
                    else (
                        f"{delta.seconds // 3600}h"
                        if delta.seconds >= 3600
                        else f"{delta.seconds // 60}m"
                    )
                )
            except (ValueError, TypeError):
                elapsed = "?"

            q = req.get("question", "")
            if len(q) > 40:
                q = q[:37] + "..."

            status_map = {
                "pending": "대기 중",
                "answered": "답변됨",
                "expired": "만료",
            }

            self.add_row(
                req.get("id", "?"),
                q,
                status_map.get(
                    req.get("status", "?"), "?"
                ),
                elapsed,
                key=req.get("id"),
            )


# ── Friction Tab ──


class FrictionTable(DataTable):
    def on_mount(self) -> None:
        self.add_columns("ID", "유형", "설명", "해소")
        self.cursor_type = "row"

    def update_data(
        self, friction: dict | None
    ) -> None:
        self.clear()
        if not friction:
            return

        f_list = sorted(
            friction.get("frictions", []),
            key=lambda f: (
                0 if not f.get("resolved_at") else 1,
                f.get("timestamp", ""),
            ),
        )

        for f in f_list:
            desc = f.get("description", "")
            if len(desc) > 35:
                desc = desc[:32] + "..."

            self.add_row(
                f.get("id", "?"),
                f.get("type", "?")[:8],
                desc,
                "해소" if f.get("resolved_at") else "미해소",
                key=f.get("id"),
            )


# ── Main App ──


class DashboardApp(App):
    TITLE = "claude-automata"
    CSS = """
    Screen { layout: vertical; }
    TabbedContent { height: 1fr; }
    #status-bar { height: 1; background: $surface; }
    #dashboard-content { layout: horizontal; height: auto; min-height: 4; }
    #mission-panel { width: 1fr; padding: 0 1; }
    #stats-panel { width: 1fr; padding: 0 1; }
    #purpose-panel { height: auto; padding: 0 1; }
    #activity-log { height: 1fr; min-height: 8; }
    #mission-inject { height: 3; layout: horizontal; }
    #mission-inject Input { width: 1fr; }
    #mission-inject Button { width: auto; }
    #slack-respond { height: 3; layout: horizontal; }
    #slack-respond Input { width: 1fr; }
    #slack-respond Button { width: auto; }
    """

    BINDINGS = [
        Binding("1", "switch_tab('tab-1')", "대시보드", show=True),
        Binding("2", "switch_tab('tab-2')", "미션", show=True),
        Binding("3", "switch_tab('tab-3')", "로그", show=True),
        Binding("4", "switch_tab('tab-4')", "슬랙", show=True),
        Binding("5", "switch_tab('tab-5')", "마찰", show=True),
        Binding("q", "quit", "종료", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent("대시보드", "미션 큐", "로그", "슬랙", "마찰"):
            with TabPane("대시보드", id="tab-1"):
                yield SystemStatusBar(id="status-bar")
                with Horizontal(id="dashboard-content"):
                    yield CurrentMissionPanel(
                        id="mission-panel"
                    )
                    yield StatsPanel(id="stats-panel")
                yield PurposePanel(id="purpose-panel")
                yield RichLog(
                    id="activity-log", max_lines=500
                )

            with TabPane("미션 큐", id="tab-2"):
                yield MissionTable(id="mission-table")
                with Horizontal(id="mission-inject"):
                    yield Input(
                        placeholder="새 미션을 입력하세요...",
                        id="mission-input",
                    )
                    yield Button(
                        "주입",
                        variant="primary",
                        id="mission-submit",
                    )

            with TabPane("로그", id="tab-3"):
                yield RichLog(
                    id="log-viewer", max_lines=2000
                )

            with TabPane("슬랙", id="tab-4"):
                yield RequestTable(id="request-table")
                yield Static(
                    "[dim]요청을 선택하세요[/]",
                    id="request-detail",
                )
                with Horizontal(id="slack-respond"):
                    yield Input(
                        placeholder="응답 입력...",
                        id="slack-input",
                    )
                    yield Button(
                        "전송",
                        variant="primary",
                        id="slack-send",
                    )

            with TabPane("마찰", id="tab-5"):
                yield FrictionTable(id="friction-table")

        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(5.0, self.refresh_state)
        self.run_worker(self._tail_log, thread=True)

    def action_switch_tab(self, tab_id: str) -> None:
        tabs = self.query_one(TabbedContent)
        tabs.active = tab_id

    async def refresh_state(self) -> None:
        purpose = read_json("state/purpose.json")
        missions = read_json("state/missions.json")
        friction = read_json("state/friction.json")
        requests = read_json("state/requests.json")

        # Dashboard
        status_bar = self.query_one(
            "#status-bar", SystemStatusBar
        )
        age = heartbeat_age()
        if age < 30:
            status_bar.status = "running"
        elif age < 120:
            status_bar.status = "unresponsive"
        else:
            status_bar.status = "stopped"

        current = read_json("run/current_session.json")
        if current and "started_at" in current:
            try:
                started = datetime.fromisoformat(
                    current["started_at"]
                )
                delta = datetime.now(timezone.utc) - started
                d, h = delta.days, delta.seconds // 3600
                m = (delta.seconds % 3600) // 60
                if d > 0:
                    status_bar.uptime = f"{d}d {h}h {m}m"
                elif h > 0:
                    status_bar.uptime = f"{h}h {m}m"
                else:
                    status_bar.uptime = f"{m}m"
            except (ValueError, TypeError):
                status_bar.uptime = "--"
        else:
            status_bar.uptime = "--"

        self.query_one(
            "#mission-panel", CurrentMissionPanel
        ).update_data(missions)
        self.query_one("#stats-panel", StatsPanel).update_data(
            missions, friction
        )
        self.query_one(
            "#purpose-panel", PurposePanel
        ).update_data(purpose)

        # Missions
        self.query_one(
            "#mission-table", MissionTable
        ).update_data(missions)

        # Slack
        self.query_one(
            "#request-table", RequestTable
        ).update_data(requests)

        # Friction
        self.query_one(
            "#friction-table", FrictionTable
        ).update_data(friction)

    async def _tail_log(self) -> None:
        log_path = PROJECT_ROOT / "logs" / "supervisor.log"
        position = 0
        log_widget = self.query_one("#log-viewer", RichLog)
        activity_widget = self.query_one(
            "#activity-log", RichLog
        )

        while True:
            try:
                if log_path.exists():
                    file_size = log_path.stat().st_size
                    if file_size < position:
                        position = 0
                    if file_size > position:
                        with open(
                            log_path, "r", encoding="utf-8"
                        ) as f:
                            f.seek(position)
                            new_lines = f.read()
                            position = f.tell()

                        for line in new_lines.splitlines():
                            colored = self._colorize(line)
                            self.call_from_thread(
                                log_widget.write, colored
                            )
                            self.call_from_thread(
                                activity_widget.write,
                                colored,
                            )
            except (FileNotFoundError, OSError):
                pass

            await asyncio.sleep(1.0)

    @staticmethod
    def _colorize(line: str) -> str:
        if "[ERROR" in line or "ERROR" in line:
            return f"[red]{line}[/]"
        if "[WARN" in line or "WARNING" in line:
            return f"[yellow]{line}[/]"
        if "[INFO" in line:
            return f"[blue]{line}[/]"
        if "[DEBUG" in line:
            return f"[dim]{line}[/]"
        return line

    # ── Mission Inject ──

    def on_button_pressed(
        self, event: Button.Pressed
    ) -> None:
        if event.button.id == "mission-submit":
            self._inject_mission()
        elif event.button.id == "slack-send":
            self._respond_to_request()

    def on_input_submitted(
        self, event: Input.Submitted
    ) -> None:
        if event.input.id == "mission-input":
            self._inject_mission()
        elif event.input.id == "slack-input":
            self._respond_to_request()

    def _inject_mission(self) -> None:
        inp = self.query_one("#mission-input", Input)
        title = inp.value.strip()
        if not title:
            self.notify("미션 제목을 입력하세요.", severity="warning")
            return

        try:
            missions = read_json("state/missions.json")
            if missions is None:
                missions = {
                    "missions": [],
                    "next_id": 1,
                    "metadata": {
                        "total_created": 0,
                        "total_completed": 0,
                        "total_failed": 0,
                        "total_blocked": 0,
                    },
                }

            mid = f"M-{missions['next_id']:03d}"
            missions["missions"].append(
                {
                    "id": mid,
                    "title": title,
                    "description": title,
                    "success_criteria": [title],
                    "priority": 5,
                    "status": "pending",
                    "blockers": [],
                    "dependencies": [],
                    "friction_ids": [],
                    "created_at": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "started_at": None,
                    "completed_at": None,
                    "session_id": None,
                    "source": "owner",
                    "result_summary": None,
                }
            )
            missions["next_id"] += 1
            missions["metadata"]["total_created"] += 1

            atomic_write_json("state/missions.json", missions)
            inp.value = ""
            self.notify(f"미션 {mid} 주입 완료")
        except Exception as e:
            self.notify(f"주입 실패: {e}", severity="error")

    def _respond_to_request(self) -> None:
        inp = self.query_one("#slack-input", Input)
        answer = inp.value.strip()
        if not answer:
            self.notify("응답을 입력하세요.", severity="warning")
            return

        # 선택된 요청 찾기 (첫 번째 pending)
        requests = read_json("state/requests.json")
        if not requests:
            self.notify("요청이 없습니다.", severity="warning")
            return

        pending = [
            r
            for r in requests.get("requests", [])
            if r.get("status") == "pending"
        ]
        if not pending:
            self.notify(
                "대기 중인 요청이 없습니다.", severity="warning"
            )
            return

        req = pending[0]
        req["answer"] = answer
        req["status"] = "answered"
        req["answered_at"] = datetime.now(
            timezone.utc
        ).isoformat()
        req["answered_via"] = "tui"

        try:
            atomic_write_json(
                "state/requests.json", requests
            )
            inp.value = ""
            self.notify(f"요청 {req['id']}에 응답 완료")
        except Exception as e:
            self.notify(f"응답 실패: {e}", severity="error")


if __name__ == "__main__":
    DashboardApp().run()
