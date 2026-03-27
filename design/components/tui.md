# TUI (Textual 기반 실시간 모니터링 대시보드)

> 요구사항 O-7, O-8 구현 — 시스템 상태를 실시간으로 파악하고, Mission 주입 및 요청 응답 등의 상호작용을 지원하는 로컬 인터페이스

---

## 1. 아키텍처

### 1.1 독립 프로세스 모델

TUI는 Supervisor와 **완전히 독립된 프로세스**이다. Supervisor 내부에 임베딩되지 않으며, 별도의 터미널에서 실행된다.

```
┌─────────────────┐         ┌─────────────────┐
│    Supervisor    │         │       TUI       │
│   (데몬 프로세스) │         │  (사용자 터미널)  │
│                 │         │                 │
│  writes → state/│ ◄─ fs ─►│ reads ← state/  │
│  writes → run/  │         │ reads ← run/    │
│  writes → logs/ │         │ reads ← logs/   │
│                 │         │ writes → state/  │
└─────────────────┘         └─────────────────┘
```

**설계 근거:**
- Supervisor 장애가 TUI에 전파되지 않는다 (반대도 마찬가지)
- TUI를 열고 닫아도 시스템 운영에 영향 없다
- 여러 터미널에서 동시에 TUI를 실행할 수 있다
- IPC, 소켓, 공유 메모리 없이 파일 시스템만으로 통신한다

### 1.2 통신 방식: 파일 기반 (File-based Communication)

TUI와 Supervisor 사이에 **IPC 채널이 없다**. 모든 통신은 파일 시스템을 통해 이루어진다.

| 방향 | 파일 | 용도 |
|------|------|------|
| **TUI 읽기** | `state/purpose.json` | Purpose 표시 |
| **TUI 읽기** | `state/strategy.json` | 전략 표시 |
| **TUI 읽기** | `state/missions.json` | 미션 큐 표시 |
| **TUI 읽기** | `state/friction.json` | Friction 로그 표시 |
| **TUI 읽기** | `state/requests.json` | Owner 요청 표시 |
| **TUI 읽기** | `state/sessions.json` | 세션 이력/통계 |
| **TUI 읽기** | `state/config.toml` | 설정 값 표시 |
| **TUI 읽기** | `run/supervisor.heartbeat` | 시스템 생존 상태 |
| **TUI 읽기** | `run/current_session.json` | 현재 세션 정보 |
| **TUI 읽기** | `logs/*.log` | 로그 스트림 |
| **TUI 쓰기** | `state/missions.json` | 미션 주입 (O-8) |
| **TUI 쓰기** | `state/requests.json` | 요청 응답 (O-8) |

TUI가 `state/` 파일에 쓸 때는 반드시 `StateManager`의 원자적 쓰기 패턴을 따른다 (write to temp → rename). 이로써 Supervisor의 동시 읽기와 충돌하지 않는다.

### 1.3 엔트리포인트

```bash
# CLI에서 실행
acc tui

# 내부 실행
uv run python -m tui.app
```

`cli/main.py`의 `acc tui` 명령이 `tui.app.DashboardApp`을 인스턴스화하고 `app.run()`을 호출한다.

### 1.4 의존성

```toml
# pyproject.toml
[project]
dependencies = [
    "textual>=1.0.0",
]
```

Textual v1.0+ (Textual v0.x가 아닌 정식 릴리즈)를 사용한다. Textual은 CSS 기반 레이아웃, 리액티브 속성, Worker 스레드를 기본 지원한다.

---

## 2. 클래스 설계: DashboardApp(App)

### 2.1 클래스 정의

```python
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import (
    Header, Footer, TabbedContent, TabPane,
    Static, DataTable, RichLog, Input, Button, Select
)


class DashboardApp(App):
    """claude-automata 실시간 모니터링 대시보드"""

    TITLE = "claude-automata"
    CSS_PATH = "dashboard.tcss"

    BINDINGS = [
        Binding("1", "switch_tab('dashboard')", "대시보드", show=True),
        Binding("2", "switch_tab('missions')", "미션 큐", show=True),
        Binding("3", "switch_tab('logs')", "로그", show=True),
        Binding("4", "switch_tab('slack')", "슬랙", show=True),
        Binding("5", "switch_tab('friction')", "마찰", show=True),
        Binding("q", "quit", "종료", show=True),
    ]

    # Reactive attributes
    system_status: reactive[str] = reactive("unknown")
    uptime: reactive[str] = reactive("--")
    current_mission_id: reactive[str] = reactive("--")
    current_mission_title: reactive[str] = reactive("--")

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(
            "대시보드", "미션 큐", "로그", "슬랙", "마찰",
            id="tabs"
        ):
            yield TabPane("대시보드", id="dashboard"):
                yield DashboardTab()
            yield TabPane("미션 큐", id="missions"):
                yield MissionQueueTab()
            yield TabPane("로그", id="logs"):
                yield LogViewerTab()
            yield TabPane("슬랙", id="slack"):
                yield SlackTab()
            yield TabPane("마찰", id="friction"):
                yield FrictionTab()
        yield Footer()

    def on_mount(self) -> None:
        """앱 마운트 시 폴링 타이머 시작"""
        self.set_interval(5.0, self.refresh_state)
        self.tail_log_worker = self.run_worker(
            self._tail_session_log, thread=True
        )

    def action_switch_tab(self, tab_id: str) -> None:
        """탭 전환 액션"""
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = tab_id

    async def refresh_state(self) -> None:
        """주기적 상태 파일 폴링 (5초 간격)"""
        # StateFileReader가 모든 state/ 파일을 한 번에 읽어 캐시
        state = StateFileReader.read_all()
        self._update_dashboard(state)
        self._update_mission_table(state)
        self._update_slack_table(state)
        self._update_friction_table(state)

    async def _tail_session_log(self) -> None:
        """로그 파일 테일링 (백그라운드 스레드)"""
        # 별도 스레드에서 실행, call_from_thread()로 UI 갱신
        ...
```

### 2.2 CSS 레이아웃 (`tui/dashboard.tcss`)

```css
/* 전체 레이아웃 */
Screen {
    layout: vertical;
}

TabbedContent {
    height: 1fr;
}

/* 대시보드 탭 */
#dashboard-status {
    height: 3;
    border: solid $primary;
    padding: 0 1;
}

#dashboard-content {
    layout: horizontal;
    height: auto;
}

#dashboard-mission {
    width: 1fr;
    border: solid $secondary;
    padding: 1;
    min-height: 6;
}

#dashboard-stats {
    width: 1fr;
    border: solid $secondary;
    padding: 1;
    min-height: 6;
}

#dashboard-purpose {
    height: auto;
    border: solid $accent;
    padding: 1;
}

#dashboard-activity {
    height: 1fr;
    border: solid $primary;
    min-height: 10;
}

/* 미션 큐 탭 */
#mission-table {
    height: 1fr;
}

#mission-inject {
    height: 3;
    layout: horizontal;
}

#mission-inject Input {
    width: 1fr;
}

#mission-inject Button {
    width: auto;
}

/* 로그 탭 */
#log-selector {
    height: 3;
}

#log-viewer {
    height: 1fr;
}

/* 슬랙 탭 */
#slack-table {
    height: 1fr;
}

#slack-detail {
    height: auto;
    min-height: 5;
    border: solid $secondary;
    padding: 1;
}

#slack-respond {
    height: 3;
    layout: horizontal;
}

/* 마찰 탭 */
#friction-table {
    height: 1fr;
}

#friction-history {
    height: 1fr;
    border: solid $secondary;
}
```

### 2.3 상태 파일 읽기 유틸리티

```python
import json
import tomllib
from pathlib import Path
from dataclasses import dataclass
from typing import Any


@dataclass
class SystemState:
    """state/ 및 run/ 파일에서 읽은 통합 시스템 상태"""
    purpose: dict | None = None
    strategy: dict | None = None
    missions: dict | None = None
    friction: dict | None = None
    requests: dict | None = None
    sessions: dict | None = None
    config: dict | None = None
    heartbeat_age_seconds: float = float("inf")
    current_session: dict | None = None


class StateFileReader:
    """state/ 및 run/ 파일을 안전하게 읽는 유틸리티

    Supervisor가 원자적 쓰기(write to temp → rename)를 사용하므로,
    읽기 시점에 파일이 완전한 상태임이 보장된다.
    읽기 실패(파일 없음, JSON 파싱 에러) 시 None을 반환한다.
    """

    BASE_DIR = Path(".")  # 프로젝트 루트, 실제로는 설정에서 주입

    @classmethod
    def read_all(cls) -> SystemState:
        """모든 상태 파일을 한 번에 읽어 SystemState 반환"""
        return SystemState(
            purpose=cls._read_json("state/purpose.json"),
            strategy=cls._read_json("state/strategy.json"),
            missions=cls._read_json("state/missions.json"),
            friction=cls._read_json("state/friction.json"),
            requests=cls._read_json("state/requests.json"),
            sessions=cls._read_json("state/sessions.json"),
            config=cls._read_toml("state/config.toml"),
            heartbeat_age_seconds=cls._heartbeat_age(),
            current_session=cls._read_json("run/current_session.json"),
        )

    @classmethod
    def _read_json(cls, rel_path: str) -> dict | None:
        """JSON 파일 안전 읽기. 실패 시 None 반환."""
        try:
            path = cls.BASE_DIR / rel_path
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None

    @classmethod
    def _read_toml(cls, rel_path: str) -> dict | None:
        """TOML 파일 안전 읽기. 실패 시 None 반환."""
        try:
            path = cls.BASE_DIR / rel_path
            return tomllib.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, tomllib.TOMLDecodeError, OSError):
            return None

    @classmethod
    def _heartbeat_age(cls) -> float:
        """heartbeat 파일의 경과 시간(초) 반환"""
        try:
            path = cls.BASE_DIR / "run/supervisor.heartbeat"
            mtime = path.stat().st_mtime
            return time.time() - mtime
        except (FileNotFoundError, OSError):
            return float("inf")
```

### 2.4 상태 파일 쓰기 유틸리티

```python
import json
import tempfile
from pathlib import Path


class StateFileWriter:
    """state/ 파일에 원자적으로 쓰는 유틸리티

    StateManager와 동일한 원자적 쓰기 패턴을 사용한다:
    1. 같은 디렉토리에 임시 파일 생성
    2. JSON 직렬화 후 임시 파일에 쓰기
    3. os.rename()으로 원자적 교체 (POSIX rename은 atomic)

    이로써 Supervisor가 동시에 같은 파일을 읽어도 항상 완전한 JSON을 본다.
    """

    BASE_DIR = Path(".")

    @classmethod
    def write_json(cls, rel_path: str, data: dict) -> None:
        """JSON 파일에 원자적으로 쓰기"""
        path = cls.BASE_DIR / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)

        # 같은 디렉토리에 임시 파일 생성 (같은 파일시스템이어야 rename이 atomic)
        fd, tmp_path = tempfile.mkstemp(
            dir=str(path.parent),
            suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.rename(tmp_path, str(path))
        except Exception:
            # 실패 시 임시 파일 정리
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    @classmethod
    def inject_mission(cls, title: str, description: str = "") -> str:
        """미션을 큐에 주입한다. 새 미션 ID를 반환한다."""
        missions = StateFileReader._read_json("state/missions.json")
        if missions is None:
            missions = {"missions": [], "next_id": 1}

        mission_id = f"M-{missions['next_id']:03d}"
        missions["missions"].append({
            "id": mission_id,
            "title": title,
            "description": description,
            "success_criteria": [],
            "priority": 5,  # 기본 우선순위 (중간)
            "status": "pending",
            "blockers": [],
            "dependencies": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": "owner",  # TUI에서 주입 = Owner 소스
        })
        missions["next_id"] += 1

        cls.write_json("state/missions.json", missions)
        return mission_id

    @classmethod
    def respond_to_request(cls, request_id: str, answer: str) -> None:
        """Owner 요청에 응답한다."""
        requests = StateFileReader._read_json("state/requests.json")
        if requests is None:
            return

        for req in requests.get("requests", []):
            if req["id"] == request_id:
                req["answer"] = answer
                req["status"] = "answered"
                req["answered_at"] = datetime.now(timezone.utc).isoformat()
                req["answered_via"] = "tui"
                break

        cls.write_json("state/requests.json", requests)
```

---

## 3. Tab 1: 대시보드 (Dashboard)

### 3.1 레이아웃

```
┌──────────────────────────────────────────────────────┐
│ 시스템 상태: 실행 중                                   │
│ 가동 시간: 2일 5시간 30분                              │
├──────────────────────┬───────────────────────────────┤
│ 현재 미션             │ 통계                           │
│ M-042                │ 완료: 41/50                    │
│ API 성능 최적화       │ 실패: 3                        │
│ 진행 중...            │ Friction: 5 (미해결: 2)        │
├──────────────────────┴───────────────────────────────┤
│ Purpose                                               │
│ "지속적으로 자동화된 수익 시스템을 개발..."              │
├──────────────────────────────────────────────────────┤
│ 최근 활동 (RichLog, auto-scroll)                      │
│ [10:30] M-041 완료: 데이터베이스 마이그레이션           │
│ [10:32] M-042 시작: API 성능 최적화                    │
│ [10:35] 에이전트 팀 전개: 3개 서브에이전트              │
└──────────────────────────────────────────────────────┘
```

### 3.2 위젯 구성

```python
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Static, RichLog
from textual.containers import Horizontal, Vertical


class DashboardTab(Vertical):
    """대시보드 탭 컨테이너"""

    def compose(self) -> ComposeResult:
        yield SystemStatusBar(id="dashboard-status")
        with Horizontal(id="dashboard-content"):
            yield CurrentMissionPanel(id="dashboard-mission")
            yield StatisticsPanel(id="dashboard-stats")
        yield PurposePanel(id="dashboard-purpose")
        yield ActivityLog(id="dashboard-activity")
```

### 3.3 SystemStatusBar

```python
class SystemStatusBar(Static):
    """시스템 상태 표시 바

    run/supervisor.heartbeat 파일의 mtime을 확인하여 시스템 상태를 판단한다.
    - heartbeat 경과 < 30초: 실행 중 (running)
    - heartbeat 경과 30~120초: 응답 없음 (unresponsive)
    - heartbeat 경과 > 120초 또는 파일 없음: 중지됨 (stopped)
    """

    status = reactive("unknown")
    uptime = reactive("--")

    STATUS_DISPLAY = {
        "running": ("실행 중", "green"),
        "unresponsive": ("응답 없음", "yellow"),
        "stopped": ("중지됨", "red"),
        "unknown": ("확인 중...", "dim"),
    }

    def render(self) -> str:
        label, color = self.STATUS_DISPLAY.get(
            self.status, ("알 수 없음", "dim")
        )
        return (
            f"[{color}]●[/] 시스템 상태: [{color}]{label}[/]\n"
            f"  가동 시간: {self.uptime}"
        )

    def update_from_state(self, state: SystemState) -> None:
        """SystemState로부터 상태 갱신"""
        age = state.heartbeat_age_seconds
        if age < 30:
            self.status = "running"
        elif age < 120:
            self.status = "unresponsive"
        else:
            self.status = "stopped"

        # 가동 시간: current_session.json의 started_at으로부터 계산
        if state.current_session and "started_at" in state.current_session:
            started = datetime.fromisoformat(
                state.current_session["started_at"]
            )
            delta = datetime.now(timezone.utc) - started
            days = delta.days
            hours, remainder = divmod(delta.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            if days > 0:
                self.uptime = f"{days}일 {hours}시간 {minutes}분"
            elif hours > 0:
                self.uptime = f"{hours}시간 {minutes}분"
            else:
                self.uptime = f"{minutes}분"
        else:
            self.uptime = "--"
```

### 3.4 CurrentMissionPanel

```python
class CurrentMissionPanel(Static):
    """현재 실행 중인 미션 패널

    state/missions.json에서 status가 "in_progress"인 미션을 표시한다.
    여러 개인 경우 가장 높은 우선순위 (낮은 priority 숫자)를 표시한다.
    """

    mission_id = reactive("--")
    mission_title = reactive("대기 중")
    mission_status = reactive("--")

    def render(self) -> str:
        return (
            f"[bold]현재 미션[/]\n"
            f"  {self.mission_id}\n"
            f"  {self.mission_title}\n"
            f"  {self.mission_status}"
        )

    def update_from_state(self, state: SystemState) -> None:
        if state.missions is None:
            return
        in_progress = [
            m for m in state.missions.get("missions", [])
            if m.get("status") == "in_progress"
        ]
        if in_progress:
            # 가장 높은 우선순위 (낮은 priority 값)
            current = min(in_progress, key=lambda m: m.get("priority", 99))
            self.mission_id = current["id"]
            self.mission_title = current["title"]
            self.mission_status = "진행 중..."
        else:
            self.mission_id = "--"
            self.mission_title = "대기 중"
            self.mission_status = "--"
```

### 3.5 StatisticsPanel

```python
class StatisticsPanel(Static):
    """통계 패널

    state/missions.json과 state/friction.json에서 통계를 계산한다.
    """

    def render(self) -> str:
        return self._stats_text

    _stats_text: str = "통계 로딩 중..."

    def update_from_state(self, state: SystemState) -> None:
        missions = state.missions.get("missions", []) if state.missions else []
        total = len(missions)
        completed = sum(1 for m in missions if m.get("status") == "completed")
        failed = sum(1 for m in missions if m.get("status") == "failed")

        frictions = (
            state.friction.get("frictions", []) if state.friction else []
        )
        friction_total = len(frictions)
        friction_unresolved = sum(
            1 for f in frictions if not f.get("resolved", False)
        )

        self._stats_text = (
            f"[bold]통계[/]\n"
            f"  완료: {completed}/{total}\n"
            f"  실패: {failed}\n"
            f"  Friction: {friction_total} (미해결: {friction_unresolved})"
        )
        self.refresh()
```

### 3.6 PurposePanel

```python
class PurposePanel(Static):
    """Purpose 표시 패널

    state/purpose.json에서 purpose 필드를 읽어 표시한다.
    Purpose는 거의 변하지 않으므로 초기 로딩 후 변경 시에만 갱신한다.
    """

    purpose_text = reactive("Purpose를 불러오는 중...")

    def render(self) -> str:
        return f"[bold]Purpose[/]\n  \"{self.purpose_text}\""

    def update_from_state(self, state: SystemState) -> None:
        if state.purpose and "purpose" in state.purpose:
            self.purpose_text = state.purpose["purpose"]
```

### 3.7 ActivityLog

```python
class ActivityLog(RichLog):
    """최근 활동 로그

    logs/session.log를 실시간으로 테일링한다.
    max_lines=200으로 메모리 사용을 제한한다.

    테일링은 @work(thread=True) 워커에서 실행되며,
    새 라인이 추가될 때 call_from_thread()로 UI를 갱신한다.
    """

    max_lines = 200

    def on_mount(self) -> None:
        self.write("[dim]최근 활동 로그를 불러오는 중...[/]")
```

---

## 4. Tab 2: 미션 큐 (Mission Queue)

### 4.1 레이아웃

```
┌──────────────────────────────────────────────────────┐
│ DataTable: 미션 목록                                  │
│ ┌─────┬──────────────────┬──────────┬──────┬───────┐ │
│ │ ID  │ 제목             │ 상태     │ 우선 │ 소스  │ │
│ ├─────┼──────────────────┼──────────┼──────┼───────┤ │
│ │M-042│ API 최적화       │ 진행 중  │ 1    │ self  │ │
│ │M-043│ 로그 개선        │ 대기     │ 2    │ frict │ │
│ │M-044│ UI 리팩토링      │ 차단     │ 3    │ owner │ │
│ └─────┴──────────────────┴──────────┴──────┴───────┘ │
├──────────────────────────────────────────────────────┤
│ 미션 주입                                             │
│ [Input: 새 미션을 입력하세요...             ] [Submit]│
└──────────────────────────────────────────────────────┘
```

### 4.2 위젯 구성

```python
class MissionQueueTab(Vertical):
    """미션 큐 탭"""

    def compose(self) -> ComposeResult:
        yield MissionTable(id="mission-table")
        with Horizontal(id="mission-inject"):
            yield Input(
                placeholder="새 미션을 입력하세요...",
                id="mission-input"
            )
            yield Button("Submit", variant="primary", id="mission-submit")
```

### 4.3 MissionTable

```python
class MissionTable(DataTable):
    """미션 큐 DataTable

    state/missions.json을 5초 간격으로 폴링하여 갱신한다.
    상태별 이모지 인디케이터로 직관적 상태 파악이 가능하다.
    """

    STATUS_EMOJI = {
        "pending": "대기",
        "in_progress": "진행 중",
        "completed": "완료",
        "failed": "실패",
        "blocked": "차단",
        "cancelled": "취소",
    }

    SOURCE_ABBREV = {
        "purpose": "purp",
        "friction": "frict",
        "owner": "owner",
        "self": "self",
        "improvement": "impr",
    }

    def on_mount(self) -> None:
        """테이블 컬럼 초기화"""
        self.add_columns("ID", "제목", "상태", "우선", "소스")
        self.cursor_type = "row"

    def update_from_state(self, state: SystemState) -> None:
        """missions.json으로부터 테이블 갱신

        전체 clear + 재구성 방식. 미션 수가 수백 개를 넘지 않으므로
        diff-update보다 단순하고 안정적이다.
        """
        self.clear()
        if state.missions is None:
            return

        missions = state.missions.get("missions", [])

        # 정렬: in_progress 먼저, 그 다음 priority 순
        status_order = {
            "in_progress": 0,
            "blocked": 1,
            "pending": 2,
            "failed": 3,
            "completed": 4,
            "cancelled": 5,
        }
        missions_sorted = sorted(
            missions,
            key=lambda m: (
                status_order.get(m.get("status", "pending"), 99),
                m.get("priority", 99),
            )
        )

        for m in missions_sorted:
            status_display = self.STATUS_EMOJI.get(
                m.get("status", "pending"), m.get("status", "?")
            )
            source_display = self.SOURCE_ABBREV.get(
                m.get("source", "?"), m.get("source", "?")
            )
            self.add_row(
                m.get("id", "?"),
                m.get("title", "?"),
                status_display,
                str(m.get("priority", "?")),
                source_display,
                key=m.get("id"),
            )
```

### 4.4 미션 주입 핸들러

```python
class MissionQueueTab(Vertical):
    # ... (compose 생략)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """미션 주입 버튼 클릭 핸들러"""
        if event.button.id != "mission-submit":
            return

        input_widget = self.query_one("#mission-input", Input)
        title = input_widget.value.strip()
        if not title:
            self.notify("미션 제목을 입력하세요.", severity="warning")
            return

        try:
            mission_id = StateFileWriter.inject_mission(title=title)
            input_widget.value = ""
            self.notify(
                f"미션 {mission_id} 주입 완료: {title}",
                severity="information"
            )
        except Exception as e:
            self.notify(
                f"미션 주입 실패: {e}",
                severity="error"
            )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Input에서 Enter 키 핸들러 (Button 클릭과 동일 동작)"""
        if event.input.id == "mission-input":
            self.query_one("#mission-submit", Button).press()
```

---

## 5. Tab 3: 로그 (Logs)

### 5.1 레이아웃

```
┌──────────────────────────────────────────────────────┐
│ Select: [supervisor.log ▾]                           │
├──────────────────────────────────────────────────────┤
│ RichLog: 전체 로그 (max_lines=5000)                   │
│ 2026-03-25 10:30:00 [INFO] Session started            │
│ 2026-03-25 10:30:01 [INFO] Mission M-042 assigned...  │
│ ...                                                    │
└──────────────────────────────────────────────────────┘
```

### 5.2 위젯 구성

```python
class LogViewerTab(Vertical):
    """로그 뷰어 탭"""

    LOG_FILES = [
        ("supervisor.log", "supervisor.log"),
        ("session.log", "session.log"),
        ("slack.log", "slack.log"),
    ]

    current_log_file: reactive[str] = reactive("supervisor.log")

    def compose(self) -> ComposeResult:
        yield Select(
            options=[(name, value) for name, value in self.LOG_FILES],
            value="supervisor.log",
            id="log-selector",
        )
        yield LogViewer(id="log-viewer")

    def on_select_changed(self, event: Select.Changed) -> None:
        """로그 파일 변경 핸들러"""
        self.current_log_file = event.value
        viewer = self.query_one("#log-viewer", LogViewer)
        viewer.switch_file(self.current_log_file)
```

### 5.3 LogViewer

```python
class LogViewer(RichLog):
    """로그 파일 뷰어

    선택된 로그 파일을 실시간으로 테일링한다.
    - max_lines=5000으로 메모리 사용 제한
    - 백그라운드 스레드에서 파일 변경 감지
    - 새 라인 추가 시 자동 스크롤
    """

    max_lines = 5000

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._current_file: str = "supervisor.log"
        self._tail_position: int = 0
        self._tail_worker = None

    def on_mount(self) -> None:
        self._start_tailing()

    def switch_file(self, filename: str) -> None:
        """로그 파일 전환

        1. 현재 테일링 워커 취소
        2. RichLog 클리어
        3. 새 파일로 테일링 시작
        """
        self._current_file = filename
        self._tail_position = 0
        self.clear()

        if self._tail_worker is not None:
            self._tail_worker.cancel()

        self._start_tailing()

    def _start_tailing(self) -> None:
        """테일링 워커 시작"""
        self._tail_worker = self.app.run_worker(
            self._tail_loop, thread=True
        )

    async def _tail_loop(self) -> None:
        """로그 파일 테일링 루프 (백그라운드 스레드)

        1초 간격으로 파일 변경을 체크한다.
        파일 크기가 줄어들면 (rotation) 처음부터 다시 읽는다.
        새 라인이 있으면 call_from_thread()로 UI에 추가한다.
        """
        log_path = Path("logs") / self._current_file
        while True:
            try:
                if not log_path.exists():
                    await asyncio.sleep(1.0)
                    continue

                file_size = log_path.stat().st_size
                if file_size < self._tail_position:
                    # 파일이 rotation됨 — 처음부터 다시 읽기
                    self._tail_position = 0
                    self.app.call_from_thread(self.clear)

                if file_size > self._tail_position:
                    with open(log_path, "r", encoding="utf-8") as f:
                        f.seek(self._tail_position)
                        new_lines = f.read()
                        self._tail_position = f.tell()

                    for line in new_lines.splitlines():
                        # 스레드에서 UI 갱신 — call_from_thread 사용
                        self.app.call_from_thread(
                            self.write, self._colorize_log_line(line)
                        )

            except (FileNotFoundError, OSError):
                pass

            await asyncio.sleep(1.0)

    @staticmethod
    def _colorize_log_line(line: str) -> str:
        """로그 라인에 Rich 마크업 컬러 적용

        [ERROR] → 빨강, [WARN] → 노랑, [INFO] → 파랑, [DEBUG] → dim
        """
        if "[ERROR]" in line:
            return f"[red]{line}[/]"
        elif "[WARN" in line:
            return f"[yellow]{line}[/]"
        elif "[INFO]" in line:
            return f"[blue]{line}[/]"
        elif "[DEBUG]" in line:
            return f"[dim]{line}[/]"
        return line
```

---

## 6. Tab 4: 슬랙 (Slack)

### 6.1 레이아웃

```
┌──────────────────────────────────────────────────────┐
│ DataTable: 활성 요청                                  │
│ ┌─────┬────────────────────────┬──────────┬────────┐ │
│ │ ID  │ 질문                   │ 상태     │ 경과   │ │
│ ├─────┼────────────────────────┼──────────┼────────┤ │
│ │R-005│ API 토큰 발급 필요     │ 대기 중  │ 2h     │ │
│ │R-004│ 배포 전략 확인         │ 답변됨   │ 5h     │ │
│ └─────┴────────────────────────┴──────────┴────────┘ │
├──────────────────────────────────────────────────────┤
│ 선택된 요청 상세                                      │
│ Q: API 토큰을 발급해주세요.                            │
│ A: (대기 중)                                          │
├──────────────────────────────────────────────────────┤
│ [Input: 응답 입력...                       ] [Send]  │
└──────────────────────────────────────────────────────┘
```

### 6.2 위젯 구성

```python
class SlackTab(Vertical):
    """슬랙 탭 — Owner 요청 관리"""

    selected_request_id: reactive[str | None] = reactive(None)

    def compose(self) -> ComposeResult:
        yield RequestTable(id="slack-table")
        yield RequestDetail(id="slack-detail")
        with Horizontal(id="slack-respond"):
            yield Input(
                placeholder="응답 입력...",
                id="slack-input"
            )
            yield Button("Send", variant="primary", id="slack-send")
```

### 6.3 RequestTable

```python
class RequestTable(DataTable):
    """활성 요청 DataTable

    state/requests.json을 5초 간격으로 폴링한다.
    미응답 요청이 위, 응답됨이 아래. 각 행 내에서는 최신 순.
    """

    STATUS_DISPLAY = {
        "pending": "대기 중",
        "answered": "답변됨",
        "resolved": "해결됨",
    }

    def on_mount(self) -> None:
        self.add_columns("ID", "질문", "상태", "경과")
        self.cursor_type = "row"

    def update_from_state(self, state: SystemState) -> None:
        self.clear()
        if state.requests is None:
            return

        requests = state.requests.get("requests", [])

        # 정렬: pending 먼저, 그 다음 created_at 역순 (최신 먼저)
        status_order = {"pending": 0, "answered": 1, "resolved": 2}
        requests_sorted = sorted(
            requests,
            key=lambda r: (
                status_order.get(r.get("status", "pending"), 99),
                r.get("created_at", ""),  # 역순은 display에서 처리
            ),
        )

        now = datetime.now(timezone.utc)
        for req in requests_sorted:
            # 경과 시간 계산
            created = datetime.fromisoformat(req.get("created_at", ""))
            delta = now - created
            if delta.days > 0:
                elapsed = f"{delta.days}d"
            elif delta.seconds >= 3600:
                elapsed = f"{delta.seconds // 3600}h"
            else:
                elapsed = f"{delta.seconds // 60}m"

            status_display = self.STATUS_DISPLAY.get(
                req.get("status", "pending"), "?"
            )

            # 질문 텍스트 잘라내기 (테이블에 맞게)
            question = req.get("question", "")
            if len(question) > 40:
                question = question[:37] + "..."

            self.add_row(
                req.get("id", "?"),
                question,
                status_display,
                elapsed,
                key=req.get("id"),
            )

    def on_data_table_row_selected(
        self, event: DataTable.RowSelected
    ) -> None:
        """행 선택 시 상세 패널에 요청 정보 전달"""
        # 부모 SlackTab에 선택된 요청 ID 전달
        slack_tab = self.ancestors_with_type(SlackTab).__next__()
        slack_tab.selected_request_id = event.row_key.value
```

### 6.4 RequestDetail

```python
class RequestDetail(Static):
    """선택된 요청 상세 표시

    RequestTable에서 행이 선택되면 해당 요청의 전체 질문과
    현재 응답 상태를 표시한다.
    """

    def render(self) -> str:
        return self._detail_text

    _detail_text: str = "[dim]요청을 선택하세요[/]"

    def show_request(self, request: dict) -> None:
        question = request.get("question", "(질문 없음)")
        answer = request.get("answer", "(대기 중)")
        context = request.get("context", "")

        self._detail_text = (
            f"[bold]Q:[/] {question}\n"
        )
        if context:
            self._detail_text += f"[dim]Context: {context}[/]\n"
        self._detail_text += f"[bold]A:[/] {answer}"
        self.refresh()
```

### 6.5 요청 응답 핸들러

```python
class SlackTab(Vertical):
    # ... (compose 생략)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """응답 전송 버튼 핸들러"""
        if event.button.id != "slack-send":
            return

        if self.selected_request_id is None:
            self.notify("응답할 요청을 선택하세요.", severity="warning")
            return

        input_widget = self.query_one("#slack-input", Input)
        answer = input_widget.value.strip()
        if not answer:
            self.notify("응답을 입력하세요.", severity="warning")
            return

        try:
            StateFileWriter.respond_to_request(
                request_id=self.selected_request_id,
                answer=answer,
            )
            input_widget.value = ""
            self.notify(
                f"요청 {self.selected_request_id}에 응답 완료",
                severity="information",
            )
        except Exception as e:
            self.notify(f"응답 실패: {e}", severity="error")

    def watch_selected_request_id(self, request_id: str | None) -> None:
        """selected_request_id가 변경될 때 상세 패널 갱신"""
        detail = self.query_one("#slack-detail", RequestDetail)
        if request_id is None:
            return

        # 현재 requests 상태에서 해당 요청 찾기
        state = StateFileReader.read_all()
        if state.requests is None:
            return
        for req in state.requests.get("requests", []):
            if req.get("id") == request_id:
                detail.show_request(req)
                break
```

---

## 7. Tab 5: 마찰 (Friction)

### 7.1 레이아웃

```
┌──────────────────────────────────────────────────────┐
│ DataTable: Friction 로그                              │
│ ┌─────┬────────┬────────────────────┬──────────────┐ │
│ │ ID  │ 유형   │ 설명               │ 해소 여부    │ │
│ ├─────┼────────┼────────────────────┼──────────────┤ │
│ │F-012│ error  │ API timeout        │ 미해소       │ │
│ │F-011│ slow   │ 미션 120분 초과    │ 해소됨       │ │
│ └─────┴────────┴────────────────────┴──────────────┘ │
├──────────────────────────────────────────────────────┤
│ 개선 이력                                             │
│ [RichLog: 자기개선 활동 로그]                          │
└──────────────────────────────────────────────────────┘
```

### 7.2 위젯 구성

```python
class FrictionTab(Vertical):
    """마찰 탭 — Friction 로그 및 자기개선 이력"""

    def compose(self) -> ComposeResult:
        yield FrictionTable(id="friction-table")
        yield ImprovementHistory(id="friction-history")
```

### 7.3 FrictionTable

```python
class FrictionTable(DataTable):
    """Friction 로그 DataTable

    state/friction.json의 frictions 배열을 표시한다.
    미해소가 위, 해소됨이 아래. 최신 순.
    """

    TYPE_DISPLAY = {
        "error": "error",
        "slow": "slow",
        "failure": "fail",
        "quality": "quality",
        "context_loss": "ctx_loss",
        "owner_intervention": "owner",
        "stuck": "stuck",
    }

    def on_mount(self) -> None:
        self.add_columns("ID", "유형", "설명", "해소 여부")
        self.cursor_type = "row"

    def update_from_state(self, state: SystemState) -> None:
        self.clear()
        if state.friction is None:
            return

        frictions = state.friction.get("frictions", [])

        # 정렬: 미해소 먼저, 그 다음 최신 순
        frictions_sorted = sorted(
            frictions,
            key=lambda f: (
                1 if f.get("resolved", False) else 0,
                f.get("created_at", ""),  # 최신이 위
            ),
            reverse=False,
        )
        # resolved=False 먼저, 그 안에서 최신 먼저
        frictions_sorted = sorted(
            frictions,
            key=lambda f: (
                0 if not f.get("resolved", False) else 1,
                # 최신이 위가 되도록 역순
            ),
        )

        for f in frictions_sorted:
            resolved = f.get("resolved", False)
            resolved_display = "해소됨" if resolved else "미해소"

            type_display = self.TYPE_DISPLAY.get(
                f.get("type", "?"), f.get("type", "?")
            )

            description = f.get("description", "")
            if len(description) > 35:
                description = description[:32] + "..."

            self.add_row(
                f.get("id", "?"),
                type_display,
                description,
                resolved_display,
                key=f.get("id"),
            )
```

### 7.4 ImprovementHistory

```python
class ImprovementHistory(RichLog):
    """자기개선 이력 로그

    state/missions.json에서 source가 "improvement" 또는 "friction"인
    완료된 미션을 시간순으로 표시한다.
    자기개선 미션의 결과를 기록하여 시스템의 진화 과정을 추적한다.
    """

    max_lines = 200

    def update_from_state(self, state: SystemState) -> None:
        """개선 미션 이력 갱신"""
        if state.missions is None:
            return

        improvement_missions = [
            m for m in state.missions.get("missions", [])
            if m.get("source") in ("improvement", "friction")
            and m.get("status") == "completed"
        ]

        if not improvement_missions:
            return

        self.clear()
        for m in sorted(
            improvement_missions,
            key=lambda m: m.get("completed_at", m.get("created_at", "")),
        ):
            completed_at = m.get("completed_at", m.get("created_at", "?"))
            # ISO 형식을 간략화
            if "T" in completed_at:
                completed_at = completed_at.split("T")[0]

            self.write(
                f"[green][{completed_at}][/] "
                f"[bold]{m['id']}[/] {m.get('title', '?')}"
            )
```

---

## 8. 실시간 갱신 메커니즘

### 8.1 폴링 기반 상태 갱신

```python
class DashboardApp(App):

    async def refresh_state(self) -> None:
        """5초 간격으로 모든 상태 파일을 읽어 UI 갱신

        Textual의 set_interval()에 의해 호출된다.
        단일 읽기로 모든 state/ 파일을 한 번에 로드하여
        일관된 스냅샷을 보장한다.
        """
        state = StateFileReader.read_all()

        # 활성 탭에 따라 관련 위젯만 갱신 (불필요한 렌더링 방지)
        active_tab = self.query_one("#tabs", TabbedContent).active

        # 대시보드는 항상 갱신 (시스템 상태 표시)
        self._update_dashboard(state)

        if active_tab == "missions":
            self._update_mission_table(state)
        elif active_tab == "slack":
            self._update_slack_table(state)
        elif active_tab == "friction":
            self._update_friction_table(state)

    def _update_dashboard(self, state: SystemState) -> None:
        """대시보드 탭 위젯 갱신"""
        self.query_one("#dashboard-status", SystemStatusBar).update_from_state(state)
        self.query_one("#dashboard-mission", CurrentMissionPanel).update_from_state(state)
        self.query_one("#dashboard-stats", StatisticsPanel).update_from_state(state)
        self.query_one("#dashboard-purpose", PurposePanel).update_from_state(state)

    def _update_mission_table(self, state: SystemState) -> None:
        """미션 큐 테이블 갱신"""
        self.query_one("#mission-table", MissionTable).update_from_state(state)

    def _update_slack_table(self, state: SystemState) -> None:
        """슬랙 요청 테이블 갱신"""
        self.query_one("#slack-table", RequestTable).update_from_state(state)

    def _update_friction_table(self, state: SystemState) -> None:
        """마찰 테이블 및 개선 이력 갱신"""
        self.query_one("#friction-table", FrictionTable).update_from_state(state)
        self.query_one("#friction-history", ImprovementHistory).update_from_state(state)
```

### 8.2 로그 파일 테일링 (Worker Thread)

```python
class DashboardApp(App):

    def on_mount(self) -> None:
        # 상태 폴링 타이머 (5초)
        self.set_interval(5.0, self.refresh_state)

        # 대시보드 활동 로그 테일링 (별도 스레드)
        self._activity_log_worker = self.run_worker(
            self._tail_activity_log, thread=True
        )

    async def _tail_activity_log(self) -> None:
        """대시보드 탭의 활동 로그 테일링

        logs/session.log를 1초 간격으로 폴링한다.
        call_from_thread()로 UI 스레드에서 RichLog에 라인을 추가한다.

        Thread-safety:
        - 파일 읽기는 워커 스레드에서 수행
        - UI 갱신은 call_from_thread()로 메인 스레드에서 수행
        - Textual이 내부적으로 스레드 동기화를 처리
        """
        log_path = Path("logs/session.log")
        position = 0

        while True:
            try:
                if log_path.exists():
                    file_size = log_path.stat().st_size

                    # 파일이 줄어들었으면 (rotation) 처음부터
                    if file_size < position:
                        position = 0

                    if file_size > position:
                        with open(log_path, "r", encoding="utf-8") as f:
                            f.seek(position)
                            new_content = f.read()
                            position = f.tell()

                        activity_log = self.query_one(
                            "#dashboard-activity", ActivityLog
                        )
                        for line in new_content.splitlines():
                            self.call_from_thread(activity_log.write, line)

            except (FileNotFoundError, OSError):
                pass

            await asyncio.sleep(1.0)
```

### 8.3 Reactive 속성과 Watch 메서드

```python
class SystemStatusBar(Static):
    """Reactive 속성 사용 예시

    reactive 속성이 변경되면 Textual이 자동으로 render()를 호출한다.
    watch_* 메서드로 변경 시 추가 로직을 실행할 수 있다.
    """

    status = reactive("unknown")

    def watch_status(self, old_value: str, new_value: str) -> None:
        """상태 변경 시 추가 동작"""
        if old_value == "running" and new_value != "running":
            # 실행 중이었다가 상태가 변경되면 알림
            self.notify(
                f"시스템 상태 변경: {old_value} → {new_value}",
                severity="warning",
            )
```

---

## 9. 파일 기반 통신 패턴 상세

### 9.1 읽기 경로

```
TUI (읽기 전용)
├── state/purpose.json      ← Purpose 표시
├── state/strategy.json     ← 전략 표시 (향후 탭 추가 시)
├── state/missions.json     ← 미션 큐 표시
├── state/friction.json     ← Friction 로그 표시
├── state/requests.json     ← Owner 요청 표시
├── state/sessions.json     ← 통계 계산
├── state/config.toml       ← 설정 값 표시
├── run/supervisor.heartbeat ← 시스템 생존 상태 (mtime)
├── run/current_session.json ← 현재 세션 상태
├── logs/supervisor.log     ← Supervisor 로그
├── logs/session.log        ← 세션 로그 (활동 로그)
└── logs/slack.log          ← Slack 로그
```

### 9.2 쓰기 경로

```
TUI (쓰기)
├── state/missions.json     ← 미션 주입 (O-8)
│   동작: read → append mission → atomic write
│   Supervisor: 다음 미션 선택 시 새 미션 발견
│
└── state/requests.json     ← 요청 응답 (O-8)
    동작: read → update request status/answer → atomic write
    Supervisor: blocker 해제 시 답변 발견 → 미션 재개
```

### 9.3 동시성 안전

TUI와 Supervisor가 같은 파일을 동시에 접근할 수 있다. 안전성은 다음으로 보장한다:

1. **원자적 쓰기 (Atomic Write)**: 모든 쓰기는 같은 디렉토리의 임시 파일에 쓴 뒤 `os.rename()`으로 교체한다. POSIX에서 `rename()`은 같은 파일시스템 내에서 atomic이다.

2. **읽기 재시도**: JSON 파싱이 실패하면 (파일이 교체 중이었을 가능성) None을 반환하고 다음 폴링 주기에 재시도한다.

3. **Read-Modify-Write 경합**: TUI가 missions.json에 미션을 주입하는 동안 Supervisor가 같은 파일을 수정할 수 있다. 이 경합은 **허용 가능**하다:
   - 빈도가 매우 낮다 (Owner가 수동으로 미션을 주입하는 경우에만)
   - 최악의 경우 미션 하나가 누락되며, 다음 주입에서 복구된다
   - 파일 잠금을 도입하면 복잡도가 크게 증가하므로 의도적으로 하지 않는다

---

## 10. 에러 처리

### 10.1 파일 읽기 실패

```python
# StateFileReader._read_json은 모든 예외를 잡아 None 반환
# UI는 None을 "데이터 없음"으로 우아하게 처리

def update_from_state(self, state: SystemState) -> None:
    if state.missions is None:
        # 파일 없음 또는 파싱 에러 — 이전 데이터 유지
        return
```

### 10.2 파일 쓰기 실패

```python
# StateFileWriter.write_json은 예외를 전파
# UI에서 try/except로 잡아 notify()로 사용자에게 알림

try:
    StateFileWriter.inject_mission(title=title)
    self.notify("미션 주입 완료", severity="information")
except Exception as e:
    self.notify(f"미션 주입 실패: {e}", severity="error")
```

### 10.3 시스템 미실행 상태

TUI는 Supervisor가 실행 중이 아니어도 동작한다. 단지 상태가 "중지됨"으로 표시되고 로그 테일링이 멈출 뿐이다. Supervisor가 다시 시작되면 자동으로 상태가 갱신된다.

---

## 11. 파일 구조

```
tui/
├── __init__.py
├── app.py              # DashboardApp 클래스 (엔트리포인트)
├── dashboard.tcss      # Textual CSS 스타일
├── state_reader.py     # StateFileReader, SystemState
├── state_writer.py     # StateFileWriter
└── widgets/
    ├── __init__.py
    ├── dashboard.py    # DashboardTab, SystemStatusBar, CurrentMissionPanel,
    │                   # StatisticsPanel, PurposePanel, ActivityLog
    ├── missions.py     # MissionQueueTab, MissionTable
    ├── logs.py         # LogViewerTab, LogViewer
    ├── slack.py        # SlackTab, RequestTable, RequestDetail
    └── friction.py     # FrictionTab, FrictionTable, ImprovementHistory
```

---

## 12. 요구사항 추적

| 요구사항 | 구현 |
|----------|------|
| **O-7** 실시간 TUI | DashboardApp: 5초 폴링 + 1초 로그 테일링으로 실시간 상태 표시 |
| **O-8** TUI 상호작용 | MissionQueueTab: 미션 주입, SlackTab: 요청 응답 |
| **O-6** 한국어 | 모든 UI 라벨/메시지가 한국어 |
