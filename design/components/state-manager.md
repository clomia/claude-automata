# State Manager 컴포넌트 설계서

> **파일**: `system/state_manager.py`
> **책임**: 파일 기반 상태 영속화, 원자적 쓰기, Git 체크포인트, 상태 복구
> **참조 요구사항**: C-2 (파일 기반), C-3 (복구 지점), E-2 (장애 불멸)

---

## 1. 개요

StateManager는 Deterministic Core의 핵심 컴포넌트로, 모든 상태 파일(`state/` 디렉토리)의 읽기/쓰기를 관리한다. 크래시 안전성을 보장하기 위해 모든 쓰기는 원자적(atomic)으로 수행되며, 세션 시작 전 Git 체크포인트를 생성하여 복구 지점을 확보한다.

### 설계 원칙

1. **원자적 쓰기**: 어떤 시점에 크래시가 발생해도 상태 파일이 손상되지 않는다
2. **단일 진실 원천**: 모든 상태는 `state/` 디렉토리의 JSON 파일에 존재한다
3. **Git 추적**: 상태 변경은 Git으로 추적되어 시간 여행 복구가 가능하다
4. **동기적 I/O**: Supervisor는 단일 프로세스이므로 동시성 문제가 없다

---

## 2. Class: StateManager

```python
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


@dataclass
class StateManager:
    """
    파일 기반 상태 영속화 관리자.

    모든 상태 파일의 읽기/쓰기를 원자적으로 수행하고,
    Git 체크포인트를 통해 복구 지점을 생성한다.

    Attributes:
        project_dir: 프로젝트 루트 디렉토리 (Git 저장소 루트)
        state_dir: 상태 파일 디렉토리 (project_dir/state)
        run_dir: 런타임 임시 파일 디렉토리 (project_dir/run)
    """
    project_dir: Path
    state_dir: Path = field(init=False)
    run_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        self.state_dir = self.project_dir / "state"
        self.run_dir = self.project_dir / "run"
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """state/ 및 run/ 디렉토리가 존재하는지 확인하고 없으면 생성."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.run_dir.mkdir(parents=True, exist_ok=True)
```

### 초기화 흐름

```
StateManager(project_dir="/path/to/claude-automata")
    │
    ├── state_dir = project_dir / "state"
    ├── run_dir = project_dir / "run"
    └── _ensure_directories()
         ├── state/ 디렉토리 생성 (없으면)
         └── run/ 디렉토리 생성 (없으면)
```

---

## 3. 원자적 파일 연산 (Atomic File Operations)

### 패턴 설명

모든 파일 쓰기는 다음 패턴을 따른다:

1. **tempfile.mkstemp**: 대상 파일과 같은 디렉토리에 임시 파일 생성
2. **write**: 임시 파일에 데이터 쓰기
3. **os.fsync**: 디스크에 플러시 강제 (커널 버퍼 → 디스크)
4. **os.replace**: 임시 파일을 대상 파일로 원자적 교체

이 패턴은 POSIX 파일시스템에서 크래시 안전성을 보장한다. `os.replace`는 원자적 연산이므로 쓰기 도중 크래시가 발생해도 기존 파일이 손상되지 않는다.

### 구현

```python
def atomic_write(self, filepath: Path, data: dict[str, Any]) -> None:
    """
    원자적 파일 쓰기.

    같은 디렉토리에 임시 파일을 생성하여 데이터를 쓴 후,
    os.replace로 원자적으로 대상 파일을 교체한다.
    이 패턴은 쓰기 도중 크래시가 발생해도 파일 손상을 방지한다.

    Args:
        filepath: 대상 파일 경로
        data: JSON으로 직렬화할 딕셔너리

    Raises:
        OSError: 파일 쓰기 또는 교체 실패 시
        TypeError: data가 JSON 직렬화 불가능할 때
    """
    # 1. 대상과 같은 디렉토리에 임시 파일 생성 (같은 파일시스템이어야 rename 원자적)
    dir_path = filepath.parent
    fd, tmp_path = tempfile.mkstemp(
        dir=str(dir_path),
        prefix=f".{filepath.name}.",
        suffix=".tmp",
    )
    try:
        # 2. 임시 파일에 JSON 쓰기
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            f.write("\n")  # 파일 끝 개행
            f.flush()
            # 3. 디스크에 플러시 강제
            os.fsync(f.fileno())

        # 4. 원자적 교체 (POSIX rename은 원자적)
        os.replace(tmp_path, str(filepath))

    except Exception:
        # 실패 시 임시 파일 정리
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def atomic_read(self, filepath: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    상태 파일 읽기. 파일이 없으면 default 반환.

    Args:
        filepath: 대상 파일 경로
        default: 파일이 없을 때 반환할 기본값. None이면 빈 딕셔너리.

    Returns:
        파싱된 JSON 딕셔너리

    Raises:
        json.JSONDecodeError: JSON 파싱 실패 시 (파일 손상)
    """
    if default is None:
        default = {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        # 파일 손상 — 백업 후 기본값 반환
        backup_path = filepath.with_suffix(f".corrupted.{int(time.time())}")
        try:
            os.replace(str(filepath), str(backup_path))
        except OSError:
            pass
        return default
```

### 원자적 쓰기 시퀀스 다이어그램

```
StateManager              FileSystem              Disk
     │                        │                     │
     │ mkstemp(dir=state/)    │                     │
     │───────────────────────>│                     │
     │  fd, /state/.tmp.xxx   │                     │
     │<───────────────────────│                     │
     │                        │                     │
     │ write(fd, json_data)   │                     │
     │───────────────────────>│                     │
     │                        │  (kernel buffer)    │
     │                        │                     │
     │ fsync(fd)              │                     │
     │───────────────────────>│────────────────────>│
     │                        │  (flushed to disk)  │
     │                        │                     │
     │ replace(tmp, target)   │                     │
     │───────────────────────>│                     │
     │  (atomic rename)       │                     │
     │                        │                     │
     │  ✓ Complete            │                     │
     │<───────────────────────│                     │
```

---

## 4. 상태 파일 메서드

### 4.1 Purpose (`state/purpose.json`)

```python
def load_purpose(self) -> dict[str, Any]:
    """
    Purpose 상태를 로드한다.

    Returns:
        Purpose 딕셔너리. 파일이 없으면 빈 딕셔너리.
        스키마:
        {
            "raw_input": str,       # Owner의 원문 입력
            "purpose": str,         # 추출된 영속적 방향
            "domain": str,          # 도메인 영역
            "constructed_at": str,  # ISO 8601 타임스탬프
            "last_evolved_at": str  # ISO 8601 타임스탬프
        }
    """
    return self.atomic_read(self.state_dir / "purpose.json")


def save_purpose(self, purpose: dict[str, Any]) -> None:
    """
    Purpose 상태를 저장한다.

    Args:
        purpose: Purpose 딕셔너리
    """
    self.atomic_write(self.state_dir / "purpose.json", purpose)
```

### 4.2 Strategy (`state/strategy.json`)

```python
def load_strategy(self) -> dict[str, Any]:
    """
    현재 전략을 로드한다.

    Returns:
        Strategy 딕셔너리. 파일이 없으면 빈 딕셔너리.
    """
    return self.atomic_read(self.state_dir / "strategy.json")


def save_strategy(self, strategy: dict[str, Any]) -> None:
    """전략을 저장한다."""
    self.atomic_write(self.state_dir / "strategy.json", strategy)
```

### 4.3 Mission Queue (`state/missions.json`)

미션 관리는 가장 복잡한 상태 연산으로, 큐 조회/변경/의존성 해석을 포함한다.

```python
def load_missions(self) -> dict[str, Any]:
    """
    미션 큐를 로드한다.

    Returns:
        MissionQueue 딕셔너리.
        스키마:
        {
            "missions": [Mission, ...],
            "next_id": int
        }
        파일이 없으면 {"missions": [], "next_id": 1} 반환.
    """
    return self.atomic_read(
        self.state_dir / "missions.json",
        default={"missions": [], "next_id": 1},
    )


def save_missions(self, missions: dict[str, Any]) -> None:
    """미션 큐를 저장한다."""
    self.atomic_write(self.state_dir / "missions.json", missions)


def get_next_mission(self) -> dict[str, Any] | None:
    """
    다음으로 실행할 미션을 반환한다.

    선택 기준 (우선순위 순):
    1. status가 "pending"인 미션만 대상
    2. 미충족 의존성(dependencies)이 없어야 함
       - 의존 미션이 "completed" 상태여야 충족
    3. 활성 blocker가 없어야 함
       - blockers 배열이 비어있거나 모든 blocker가 resolved
    4. 위 조건을 만족하는 미션 중 priority가 가장 낮은 값 (0이 최고)
    5. 동일 priority이면 created_at이 가장 이른 것

    Returns:
        실행 가능한 Mission 딕셔너리, 없으면 None
    """
    queue = self.load_missions()
    missions = queue["missions"]

    # 완료된 미션 ID 세트 구축
    completed_ids = {
        m["id"] for m in missions if m["status"] == "completed"
    }

    candidates = []
    for mission in missions:
        # 1. pending 미션만
        if mission["status"] != "pending":
            continue

        # 2. 의존성 확인: 모든 dependency가 completed여야 함
        deps = mission.get("dependencies", [])
        if deps and not all(d in completed_ids for d in deps):
            continue

        # 3. blocker 확인: 모든 blocker가 resolved여야 함
        blockers = mission.get("blockers", [])
        active_blockers = [
            b for b in blockers
            if not b.get("resolved", False)
        ]
        if active_blockers:
            continue

        candidates.append(mission)

    if not candidates:
        return None

    # 4+5. priority 오름차순, 같으면 created_at 오름차순
    candidates.sort(key=lambda m: (m.get("priority", 999), m.get("created_at", "")))
    return candidates[0]


def add_mission(self, mission: dict[str, Any]) -> str:
    """
    미션 큐에 새 미션을 추가한다.

    Args:
        mission: Mission 딕셔너리 (id 필드 없어도 됨, 자동 할당)

    Returns:
        할당된 미션 ID (예: "M-007")
    """
    queue = self.load_missions()
    next_id = queue["next_id"]
    mission_id = f"M-{next_id:03d}"

    mission["id"] = mission_id
    mission.setdefault("status", "pending")
    mission.setdefault("blockers", [])
    mission.setdefault("dependencies", [])
    mission.setdefault("created_at", datetime.now(timezone.utc).isoformat())

    queue["missions"].append(mission)
    queue["next_id"] = next_id + 1
    self.save_missions(queue)

    return mission_id


def complete_mission(self, mission_id: str, result: str) -> None:
    """
    미션을 완료 처리한다.

    Args:
        mission_id: 미션 ID (예: "M-001")
        result: 완료 결과 요약 텍스트

    Raises:
        ValueError: 해당 ID의 미션이 없을 때
    """
    queue = self.load_missions()
    mission = self._find_mission(queue, mission_id)

    mission["status"] = "completed"
    mission["result"] = result
    mission["completed_at"] = datetime.now(timezone.utc).isoformat()

    self.save_missions(queue)


def fail_mission(self, mission_id: str, reason: str) -> None:
    """
    미션을 실패 처리한다.

    Args:
        mission_id: 미션 ID
        reason: 실패 사유

    Raises:
        ValueError: 해당 ID의 미션이 없을 때
    """
    queue = self.load_missions()
    mission = self._find_mission(queue, mission_id)

    mission["status"] = "failed"
    mission["failure_reason"] = reason
    mission["failed_at"] = datetime.now(timezone.utc).isoformat()

    self.save_missions(queue)


def block_mission(self, mission_id: str, blocker: dict[str, Any]) -> None:
    """
    미션에 blocker를 추가한다.

    Blocker가 추가되면 미션은 get_next_mission()에서 선택되지 않는다.
    Owner의 응답 또는 외부 조건 충족 후 unblock_mission()으로 해제한다.

    Args:
        mission_id: 미션 ID
        blocker: Blocker 딕셔너리
            {
                "id": str,          # blocker 고유 ID
                "type": str,        # "owner_input" | "external" | "dependency"
                "description": str, # 차단 사유
                "created_at": str,  # ISO 8601
                "resolved": bool    # 해결 여부 (기본 False)
            }

    Raises:
        ValueError: 해당 ID의 미션이 없을 때
    """
    queue = self.load_missions()
    mission = self._find_mission(queue, mission_id)

    blocker.setdefault("resolved", False)
    blocker.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    mission["blockers"].append(blocker)

    self.save_missions(queue)


def unblock_mission(self, mission_id: str, blocker_id: str) -> None:
    """
    미션의 특정 blocker를 해제한다.

    Args:
        mission_id: 미션 ID
        blocker_id: 해제할 blocker의 ID

    Raises:
        ValueError: 해당 ID의 미션 또는 blocker가 없을 때
    """
    queue = self.load_missions()
    mission = self._find_mission(queue, mission_id)

    found = False
    for blocker in mission["blockers"]:
        if blocker["id"] == blocker_id:
            blocker["resolved"] = True
            blocker["resolved_at"] = datetime.now(timezone.utc).isoformat()
            found = True
            break

    if not found:
        raise ValueError(f"Blocker not found: {blocker_id} in mission {mission_id}")

    # 모든 blocker가 해제되었으면 미션을 pending으로 복귀
    if all(b["resolved"] for b in mission["blockers"]):
        if mission.get("status") == "blocked":
            mission["status"] = "pending"

    self.save_missions(queue)


def _find_mission(self, queue: dict[str, Any], mission_id: str) -> dict[str, Any]:
    """미션 큐에서 ID로 미션을 찾는다. 내부 헬퍼."""
    for mission in queue["missions"]:
        if mission["id"] == mission_id:
            return mission
    raise ValueError(f"Mission not found: {mission_id}")
```

#### 미션 선택 결정 트리

```
get_next_mission()
    │
    ▼
[모든 미션 순회]
    │
    ├── status != "pending" → 건너뜀
    │
    ├── status == "pending"
    │       │
    │       ├── 미충족 dependency 있음 → 건너뜀
    │       │   (의존 미션이 "completed"가 아닌 것이 하나라도 있으면)
    │       │
    │       ├── 활성 blocker 있음 → 건너뜀
    │       │   (resolved=false인 blocker가 하나라도 있으면)
    │       │
    │       └── 실행 가능 → 후보 목록에 추가
    │
    ▼
[후보 정렬]
    priority ASC → created_at ASC
    │
    ▼
[첫 번째 후보 반환] 또는 None
```

### 4.4 Friction Log (`state/friction.json`)

```python
def load_friction(self) -> dict[str, Any]:
    """
    Friction 로그를 로드한다.

    Returns:
        FrictionLog 딕셔너리.
        스키마:
        {
            "frictions": [Friction, ...],
            "next_id": int
        }
    """
    return self.atomic_read(
        self.state_dir / "friction.json",
        default={"frictions": [], "next_id": 1},
    )


def add_friction(self, friction: dict[str, Any]) -> str:
    """
    Friction 기록을 추가한다.

    Friction은 시스템 운영 중 발생한 마찰(문제, 비효율, 반복 에러 등)을
    기록한 것으로, 자기개선 시스템의 입력이 된다.

    Args:
        friction: Friction 딕셔너리
            {
                "type": str,            # "error" | "repeated_failure" | "stuck" | "quality" | "owner_intervention" | "slow" | "context_loss"
                "pattern_key": str,      # 패턴 식별 키 (같은 유형 그룹핑)
                "description": str,      # 상세 설명
                "context": dict,         # 발생 맥락 (미션 ID, 에러 메시지 등)
                "source": str,           # "session" | "supervisor" | "owner"
            }

    Returns:
        할당된 Friction ID (예: "F-012")
    """
    log = self.load_friction()
    next_id = log["next_id"]
    friction_id = f"F-{next_id:03d}"

    friction["id"] = friction_id
    friction.setdefault("resolved", False)
    friction.setdefault("created_at", datetime.now(timezone.utc).isoformat())

    log["frictions"].append(friction)
    log["next_id"] = next_id + 1
    self.save_friction(log)

    return friction_id


def save_friction(self, friction_log: dict[str, Any]) -> None:
    """Friction 로그를 저장한다."""
    self.atomic_write(self.state_dir / "friction.json", friction_log)


def resolve_friction(self, friction_id: str, resolution: str) -> None:
    """
    Friction을 해결 처리한다.

    자기개선 미션이 해당 friction의 원인을 수정한 후 호출된다.

    Args:
        friction_id: Friction ID
        resolution: 해결 방법 설명

    Raises:
        ValueError: 해당 ID의 friction이 없을 때
    """
    log = self.load_friction()
    for friction in log["frictions"]:
        if friction["id"] == friction_id:
            friction["resolved"] = True
            friction["resolution"] = resolution
            friction["resolved_at"] = datetime.now(timezone.utc).isoformat()
            self.save_friction(log)
            return
    raise ValueError(f"Friction not found: {friction_id}")


def get_unresolved_friction_count(self, pattern_key: str) -> int:
    """
    특정 패턴의 미해결 friction 수를 반환한다.

    자기개선 트리거 판단에 사용된다.
    config.toml.friction_threshold(기본 3)와 비교하여
    임계값 도달 시 자기개선 미션을 생성한다.

    Args:
        pattern_key: 패턴 식별 키

    Returns:
        미해결 friction 수
    """
    log = self.load_friction()
    return sum(
        1
        for f in log["frictions"]
        if f.get("pattern_key") == pattern_key and not f.get("resolved", False)
    )
```

### 4.5 Requests (`state/requests.json`)

```python
def load_requests(self) -> list[dict[str, Any]]:
    """
    Owner 요청 목록을 로드한다.

    Returns:
        Request 딕셔너리 리스트.
        스키마:
        {
            "requests": [
                {
                    "id": str,              # "R-001"
                    "type": str,            # "approval" | "input" | "decision" | "notification"
                    "question": str,        # Owner에게 보낸 질문
                    "context": str,         # 맥락 설명
                    "mission_id": str | None, # 관련 미션 ID
                    "slack_thread_ts": str | None, # Slack 스레드 타임스탬프
                    "status": str,          # "pending" | "answered"
                    "answer": str | None,   # Owner의 답변
                    "created_at": str,
                    "answered_at": str | None
                }
            ],
            "next_id": int
        }
    """
    data = self.atomic_read(
        self.state_dir / "requests.json",
        default={"requests": [], "next_id": 1},
    )
    return data.get("requests", [])


def add_request(self, request: dict[str, Any]) -> str:
    """
    Owner 요청을 추가한다.

    요청은 Slack 스레드로 Owner에게 전달되며,
    응답이 올 때까지 관련 미션은 block 상태가 된다.

    Args:
        request: Request 딕셔너리

    Returns:
        할당된 Request ID (예: "R-003")
    """
    data = self.atomic_read(
        self.state_dir / "requests.json",
        default={"requests": [], "next_id": 1},
    )
    next_id = data["next_id"]
    request_id = f"R-{next_id:03d}"

    request["id"] = request_id
    request.setdefault("status", "pending")
    request.setdefault("answer", None)
    request.setdefault("created_at", datetime.now(timezone.utc).isoformat())

    data["requests"].append(request)
    data["next_id"] = next_id + 1
    self.atomic_write(self.state_dir / "requests.json", data)

    return request_id


def answer_request(self, request_id: str, answer: str) -> None:
    """
    Owner 요청에 답변을 기록한다.

    Slack에서 Owner의 응답이 수신되면 호출된다.
    관련 미션의 blocker도 함께 해제되어야 한다 (호출자 책임).

    Args:
        request_id: Request ID
        answer: Owner의 답변 텍스트

    Raises:
        ValueError: 해당 ID의 request가 없을 때
    """
    data = self.atomic_read(
        self.state_dir / "requests.json",
        default={"requests": [], "next_id": 1},
    )
    for request in data["requests"]:
        if request["id"] == request_id:
            request["status"] = "answered"
            request["answer"] = answer
            request["answered_at"] = datetime.now(timezone.utc).isoformat()
            self.atomic_write(self.state_dir / "requests.json", data)
            return
    raise ValueError(f"Request not found: {request_id}")
```

### 4.6 Config (`state/config.toml`)

```python
# 기본 설정값 상수
DEFAULT_CONFIG: dict[str, Any] = {
    "session_timeout_minutes": 120,
    "max_consecutive_failures": 3,
    "friction_threshold": 3,
    "proactive_improvement_interval": 10,
    "compaction_refresh_count": 5,
    "checkpoint_before_session": True,
    "slack_notification_level": "warning",  # "info" | "warning" | "error" | "critical"
    "max_retry_attempts": 5,
    "backoff_base_seconds": 1.0,
    "backoff_max_seconds": 60.0,
}


def load_config(self) -> dict[str, Any]:
    """
    동적 설정을 로드한다.

    TOML 형식의 설정 파일을 읽어 딕셔너리로 반환한다.
    파일이 없으면 DEFAULT_CONFIG를 반환한다.
    Claude Code 세션이 자기개선의 일환으로 이 파일을 수정할 수 있다 (S-5).

    Returns:
        Config 딕셔너리
    """
    config_path = self.state_dir / "config.toml"
    try:
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
    except FileNotFoundError:
        config = DEFAULT_CONFIG.copy()
    except tomllib.TOMLDecodeError:
        # 파일 손상 — 백업 후 기본값 반환
        backup_path = config_path.with_suffix(f".corrupted.{int(time.time())}")
        try:
            os.replace(str(config_path), str(backup_path))
        except OSError:
            pass
        config = DEFAULT_CONFIG.copy()
    # 누락된 키는 기본값으로 보완
    for key, default_value in DEFAULT_CONFIG.items():
        config.setdefault(key, default_value)
    return config


# Note: save_config()는 제공하지 않는다.
# config.toml은 TOML 형식이므로 Python의 json.dump()로 쓰면 파일이 손상된다.
# 설정 쓰기는 Claude Code의 Edit/Write 도구가 직접 수행한다.
# (file-format-decisions.md 참조: "쓰기는 Python이 아닌 Claude Code가 수행하므로 tomli-w 의존성이 불필요하다.")
```

### 4.7 Sessions (`state/sessions.json`)

```python
def load_sessions(self) -> list[dict[str, Any]]:
    """
    세션 이력을 로드한다.

    Returns:
        SessionRecord 딕셔너리 리스트.
        스키마:
        {
            "sessions": [
                {
                    "id": str,              # "S-001"
                    "type": str,            # "initialization" | "working" | "recovery"
                    "mission_id": str | None, # 실행한 미션 ID
                    "started_at": str,
                    "ended_at": str | None,
                    "exit_code": int | None,
                    "outcome": str,         # "completed" | "failed" | "crashed" | "timeout"
                    "result_summary": str | None,
                    "error_type": str | None,
                    "token_usage": dict | None,
                    "checkpoint_tag": str | None
                }
            ],
            "next_id": int
        }
    """
    data = self.atomic_read(
        self.state_dir / "sessions.json",
        default={"sessions": [], "next_id": 1},
    )
    return data.get("sessions", [])


def add_session(self, session: dict[str, Any]) -> str:
    """
    세션 기록을 추가한다.

    Supervisor가 세션 시작/종료 시 호출한다.
    세션 시작 시 최소 정보로 기록하고, 종료 시 update_session()으로 갱신한다.

    Args:
        session: SessionRecord 딕셔너리

    Returns:
        할당된 세션 ID (예: "S-042")
    """
    data = self.atomic_read(
        self.state_dir / "sessions.json",
        default={"sessions": [], "next_id": 1},
    )
    next_id = data["next_id"]
    session_id = f"S-{next_id:03d}"

    session["id"] = session_id
    session.setdefault("started_at", datetime.now(timezone.utc).isoformat())

    data["sessions"].append(session)
    data["next_id"] = next_id + 1
    self.atomic_write(self.state_dir / "sessions.json", data)

    return session_id


def update_session(self, session_id: str, updates: dict[str, Any]) -> None:
    """
    기존 세션 기록을 갱신한다.

    세션 종료 시 exit_code, outcome, result_summary 등을 업데이트한다.

    Args:
        session_id: 세션 ID
        updates: 갱신할 필드 딕셔너리

    Raises:
        ValueError: 해당 ID의 세션이 없을 때
    """
    data = self.atomic_read(
        self.state_dir / "sessions.json",
        default={"sessions": [], "next_id": 1},
    )
    for session in data["sessions"]:
        if session["id"] == session_id:
            session.update(updates)
            self.atomic_write(self.state_dir / "sessions.json", data)
            return
    raise ValueError(f"Session not found: {session_id}")
```

---

## 5. Git Checkpoint

Git 체크포인트는 상태 파일의 시점 스냅샷을 생성하여, 크래시나 상태 오염 발생 시 알려진 좋은 상태로 복구할 수 있게 한다. 요구사항 C-3에 의해 **매 세션 시작 전** 반드시 체크포인트를 생성한다.

```python
def create_checkpoint(self, label: str) -> str:
    """
    Git 체크포인트를 생성한다.

    state/ 디렉토리의 현재 상태를 Git 커밋하고 태그를 생성한다.
    세션 시작 전 반드시 호출되어야 한다 (요구사항 C-3).

    순서:
    1. git add state/
    2. git commit -m "checkpoint: {label}"
    3. git tag checkpoint-{timestamp}-{label}

    Args:
        label: 체크포인트 라벨 (예: "pre-session-42", "pre-recovery")

    Returns:
        생성된 태그 이름

    Raises:
        subprocess.CalledProcessError: Git 명령 실패 시
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tag_name = f"checkpoint-{timestamp}-{label}"

    cwd = str(self.project_dir)

    # 1. state/ 디렉토리 스테이징
    subprocess.run(
        ["git", "add", "state/"],
        cwd=cwd,
        check=True,
        capture_output=True,
    )

    # 2. 커밋 (변경이 없으면 무시)
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=cwd,
        capture_output=True,
    )
    if result.returncode != 0:
        # 스테이징된 변경이 있을 때만 커밋
        subprocess.run(
            ["git", "commit", "-m", f"checkpoint: {label}"],
            cwd=cwd,
            check=True,
            capture_output=True,
        )

    # 3. 태그 생성
    subprocess.run(
        ["git", "tag", tag_name],
        cwd=cwd,
        check=True,
        capture_output=True,
    )

    return tag_name


def list_checkpoints(self) -> list[str]:
    """
    모든 체크포인트 태그를 시간 역순으로 반환한다.

    Returns:
        체크포인트 태그 이름 리스트 (최신 순)
    """
    result = subprocess.run(
        ["git", "tag", "-l", "checkpoint-*", "--sort=-creatordate"],
        cwd=str(self.project_dir),
        check=True,
        capture_output=True,
        text=True,
    )
    tags = result.stdout.strip().split("\n")
    return [t for t in tags if t]  # 빈 문자열 제거


def restore_checkpoint(self, tag: str) -> None:
    """
    특정 체크포인트로 state/ 디렉토리를 복원한다.

    현재 state/ 파일을 지정된 태그 시점의 상태로 되돌린다.
    복원 전 현재 상태를 'pre-restore' 체크포인트로 백업한다.

    Args:
        tag: 복원할 체크포인트 태그 이름

    Raises:
        subprocess.CalledProcessError: Git 명령 실패 시
        ValueError: 해당 태그가 존재하지 않을 때
    """
    cwd = str(self.project_dir)

    # 태그 존재 확인
    result = subprocess.run(
        ["git", "tag", "-l", tag],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    if tag not in result.stdout.strip().split("\n"):
        raise ValueError(f"Checkpoint tag not found: {tag}")

    # 현재 상태를 백업 체크포인트로 생성
    self.create_checkpoint(f"pre-restore-{tag}")

    # state/ 디렉토리를 해당 태그 시점으로 복원
    subprocess.run(
        ["git", "checkout", tag, "--", "state/"],
        cwd=cwd,
        check=True,
        capture_output=True,
    )
```

### 체크포인트 운영 흐름

```
[Supervisor Loop 반복]
    │
    ▼
create_checkpoint("pre-session-{N}")     ← 요구사항 C-3
    │  git add state/
    │  git commit -m "checkpoint: pre-session-{N}"
    │  git tag checkpoint-20260325T100000Z-pre-session-42
    │
    ▼
[Claude Code 세션 실행]
    │
    ├── 정상 완료 → 다음 루프
    │
    └── 크래시/오염 발생
            │
            ▼
        list_checkpoints()
            │  → ["checkpoint-20260325T100000Z-pre-session-42", ...]
            │
            ▼
        restore_checkpoint("checkpoint-20260325T100000Z-pre-session-42")
            │  git checkout {tag} -- state/
            │
            ▼
        [복구된 상태로 세션 재시작]
```

---

## 6. 상태 복구 (State Recovery)

### recover_from_crash()

Supervisor 재시작 시(launchd KeepAlive에 의한 재시작 포함) 호출되어 중단된 세션을 정리한다.

```python
def recover_from_crash(self) -> dict[str, Any] | None:
    """
    크래시 후 상태를 복구한다.

    Supervisor 시작 시 호출된다. 이전 세션이 비정상 종료되었는지
    확인하고, 필요하면 중단된 미션을 재큐잉한다.

    복구 절차:
    1. run/current_session.json 확인 → 중단된 세션이 있는지 판별
    2. 중단된 세션이 있으면:
       a. 해당 미션이 in_progress 상태인지 확인
       b. git diff로 세션이 작업을 저장했는지 확인
       c. 작업이 저장되지 않았으면 미션을 pending으로 재설정
       d. 세션 기록에 crashed 결과 추가
    3. 연속 크래시 카운터 증가
    4. current_session.json 정리

    Returns:
        복구된 세션 정보 딕셔너리, 복구할 것이 없으면 None
    """
    session_file = self.run_dir / "current_session.json"

    # 1. 중단된 세션 확인
    if not session_file.exists():
        return None

    try:
        with open(session_file, "r", encoding="utf-8") as f:
            current = json.load(f)
    except (json.JSONDecodeError, OSError):
        # current_session.json 자체가 손상 — 정리만 수행
        self._cleanup_current_session()
        return None

    session_id = current.get("session_id")
    mission_id = current.get("mission_id")

    recovery_info = {
        "recovered_session_id": session_id,
        "recovered_mission_id": mission_id,
        "action_taken": "none",
    }

    # 2. in_progress 상태인 모든 미션을 pending으로 리셋
    queue = self.load_missions()
    for m in queue["missions"]:
        if m.get("status") == "in_progress":
            m["status"] = "pending"
            recovery_info.setdefault("reset_missions", []).append(m["id"])

    # 2a. 크래시된 세션의 미션에 대해 추가 처리
    if mission_id:
        mission = None
        for m in queue["missions"]:
            if m["id"] == mission_id:
                mission = m
                break

        if mission and mission.get("status") == "pending":
            # 2b. Git diff로 작업 저장 여부 확인
            has_saved_work = self._check_saved_work()

            if has_saved_work:
                # 작업이 일부 저장됨 — 미션을 pending으로 되돌려 이어서 진행
                mission["status"] = "pending"
                recovery_info["action_taken"] = "re_enqueued_with_partial_work"
            else:
                # 작업이 저장되지 않음 — 미션을 pending으로 재설정
                mission["status"] = "pending"
                recovery_info["action_taken"] = "re_enqueued_clean"

            self.save_missions(queue)

    # 2d. 세션 기록 업데이트
    if session_id:
        try:
            self.update_session(session_id, {
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "outcome": "crashed",
                "error_type": "PROCESS_CRASH",
            })
        except ValueError:
            pass  # 세션 기록이 없는 경우 (초기화 중 크래시)

    # 3. 연속 크래시 카운터 증가
    self._increment_restart_count()

    # 4. current_session.json 정리
    self._cleanup_current_session()

    return recovery_info


def _check_saved_work(self) -> bool:
    """Git diff로 세션이 작업을 저장했는지 확인한다."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "state/"],
        cwd=str(self.project_dir),
        capture_output=True,
        text=True,
    )
    # state/ 외의 파일에도 변경이 있으면 작업이 저장된 것으로 판단
    all_diff = subprocess.run(
        ["git", "diff", "--name-only"],
        cwd=str(self.project_dir),
        capture_output=True,
        text=True,
    )
    return bool(all_diff.stdout.strip())


def _increment_restart_count(self) -> None:
    """연속 재시작 카운터를 증가시킨다."""
    counter_file = self.run_dir / "restart_count.json"
    try:
        with open(counter_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"count": 0, "first_restart_at": None}

    data["count"] = data.get("count", 0) + 1
    if data.get("first_restart_at") is None:
        data["first_restart_at"] = datetime.now(timezone.utc).isoformat()
    data["last_restart_at"] = datetime.now(timezone.utc).isoformat()

    self.atomic_write(counter_file, data)


def reset_restart_count(self) -> None:
    """세션이 정상 완료되면 연속 재시작 카운터를 리셋한다."""
    counter_file = self.run_dir / "restart_count.json"
    self.atomic_write(counter_file, {"count": 0, "first_restart_at": None})


def _cleanup_current_session(self) -> None:
    """current_session.json을 제거한다."""
    session_file = self.run_dir / "current_session.json"
    try:
        os.unlink(str(session_file))
    except OSError:
        pass
```

### 크래시 복구 결정 트리

```
recover_from_crash()
    │
    ▼
[run/current_session.json 존재?]
    │
    ├── 없음 → return None (정상 시작)
    │
    └── 있음 → 비정상 종료 감지
            │
            ▼
        [JSON 파싱 가능?]
            │
            ├── 아니오 → 정리만 수행, return
            │
            └── 예 → mission_id 추출
                    │
                    ▼
                [미션이 in_progress?]
                    │
                    ├── 아니오 → 세션 기록만 업데이트
                    │
                    └── 예 → git diff 확인
                            │
                            ├── 작업 저장됨 → pending으로 변경 (이어서 진행)
                            │
                            └── 작업 없음 → pending으로 변경 (처음부터)
                    │
                    ▼
                [연속 크래시 카운터 증가]
                    │
                    ▼
                [current_session.json 정리]
                    │
                    ▼
                return recovery_info
```

---

## 7. create_session_context()

이 메서드는 새 Claude Code 세션에 주입되는 시스템 상태 요약 텍스트를 생성한다. 세션 프롬프트의 `{state_manager.create_session_context() 출력}` 부분에 삽입되어, AI 에이전트가 현재 시스템 상태를 파악하고 연속성을 유지할 수 있게 한다.

```python
def create_session_context(self) -> str:
    """
    새 세션에 주입할 시스템 상태 요약 텍스트를 생성한다.

    이 텍스트는 세션 프롬프트에 포함되어 AI 에이전트가:
    - 시스템의 Purpose와 현재 전략을 인지
    - 최근 완료된 미션 결과를 참조 (컨텍스트 연속성)
    - 현재 미션 큐 상태를 파악
    - 미해결 마찰을 인지하고 개선 기회 포착
    - Owner 대기 중인 요청을 인지
    - 전체 운영 통계를 참조

    Returns:
        마크다운 형식의 시스템 상태 요약 문자열
    """
    purpose = self.load_purpose()
    strategy = self.load_strategy()
    queue = self.load_missions()
    friction_log = self.load_friction()
    requests = self.load_requests()
    sessions = self.load_sessions()

    sections: list[str] = []
    sections.append("## 시스템 상태 요약")

    # ── Purpose ──
    sections.append("\n### Purpose")
    if purpose:
        sections.append(f"- 방향: {purpose.get('purpose', '(미설정)')}")
        sections.append(f"- 도메인: {purpose.get('domain', '(미설정)')}")
        sections.append(f"- 설정일: {purpose.get('constructed_at', 'N/A')}")
    else:
        sections.append("(Purpose 미설정)")

    # ── 현재 전략 ──
    sections.append("\n### 현재 전략")
    if strategy:
        sections.append(f"- 전략: {strategy.get('description', '(없음)')}")
        goals = strategy.get("goals", [])
        if goals:
            for goal in goals[:5]:
                sections.append(f"  - {goal}")
    else:
        sections.append("(전략 미설정)")

    # ── 최근 완료 미션 (최근 5개) ──
    sections.append("\n### 최근 완료 미션 (최근 5개)")
    completed = [
        m for m in queue.get("missions", [])
        if m.get("status") == "completed"
    ]
    # completed_at 기준 최신 순 정렬
    completed.sort(
        key=lambda m: m.get("completed_at", ""),
        reverse=True,
    )
    if completed[:5]:
        for m in completed[:5]:
            result = m.get("result", "(결과 없음)")
            # 결과가 너무 길면 잘라냄
            if len(result) > 200:
                result = result[:200] + "..."
            sections.append(
                f"- [{m['id']}] {m.get('title', '?')} — {result}"
            )
    else:
        sections.append("(완료된 미션 없음)")

    # ── 현재 미션 큐 (상위 5개) ──
    sections.append("\n### 현재 미션 큐 (상위 5개)")
    pending = [
        m for m in queue.get("missions", [])
        if m.get("status") == "pending"
    ]
    pending.sort(key=lambda m: (m.get("priority", 999), m.get("created_at", "")))
    if pending[:5]:
        for m in pending[:5]:
            blockers = m.get("blockers", [])
            active_blockers = [b for b in blockers if not b.get("resolved", False)]
            blocker_text = f" [BLOCKED: {len(active_blockers)}]" if active_blockers else ""
            deps = m.get("dependencies", [])
            dep_text = f" [deps: {', '.join(deps)}]" if deps else ""
            sections.append(
                f"- [{m['id']}] P{m.get('priority', '?')}: {m.get('title', '?')}{blocker_text}{dep_text}"
            )
    else:
        sections.append("(대기 미션 없음)")

    # ── 미해결 Friction (최근 5개) ──
    sections.append("\n### 미해결 Friction (최근 5개)")
    unresolved = [
        f for f in friction_log.get("frictions", [])
        if not f.get("resolved", False)
    ]
    unresolved.sort(key=lambda f: f.get("created_at", ""), reverse=True)
    if unresolved[:5]:
        for f in unresolved[:5]:
            sections.append(
                f"- [{f['id']}] [{f.get('category', '?')}] {f.get('description', '?')}"
                f" (패턴: {f.get('pattern_key', 'N/A')})"
            )
    else:
        sections.append("(미해결 friction 없음)")

    # ── Owner 대기 중인 요청 ──
    sections.append("\n### Owner 대기 중인 요청")
    pending_requests = [
        r for r in requests
        if r.get("status") == "pending"
    ]
    if pending_requests:
        for r in pending_requests:
            sections.append(
                f"- [{r['id']}] {r.get('question', '?')}"
                f" (미션: {r.get('mission_id', 'N/A')})"
            )
    else:
        sections.append("(대기 중인 요청 없음)")

    # ── 주요 통계 ──
    sections.append("\n### 주요 통계")
    total_sessions = len(sessions)
    total_completed = len(completed)
    total_failed = len([
        m for m in queue.get("missions", [])
        if m.get("status") == "failed"
    ])

    # 연속 실패 계산: 최근 세션부터 역순으로 연속 실패 수
    consecutive_failures = 0
    sorted_sessions = sorted(
        sessions,
        key=lambda s: s.get("ended_at", s.get("started_at", "")),
        reverse=True,
    )
    for s in sorted_sessions:
        if s.get("outcome") in ("failed", "crashed"):
            consecutive_failures += 1
        else:
            break

    # 마지막 성공 세션 타임스탬프
    last_success = None
    for s in sorted_sessions:
        if s.get("outcome") == "completed":
            last_success = s.get("ended_at", s.get("started_at"))
            break

    sections.append(f"- 총 세션: {total_sessions}")
    sections.append(f"- 총 완료 미션: {total_completed}")
    sections.append(f"- 총 실패 미션: {total_failed}")
    sections.append(f"- 연속 실패: {consecutive_failures}")
    sections.append(f"- 마지막 성공 세션: {last_success or 'N/A'}")

    return "\n".join(sections)
```

### 생성 출력 예시

```markdown
## 시스템 상태 요약

### Purpose
- 방향: 고품질 한국어 기술 블로그 자동 생성 및 퍼블리싱
- 도메인: technical-writing
- 설정일: 2026-03-25T10:00:00Z

### 현재 전략
- 전략: SEO 최적화된 기술 포스트를 주 3회 자동 생성하고, 독자 반응을 분석하여 주제 선정을 개선한다
  - 키워드 리서치 자동화
  - 포스트 품질 자동 검증
  - 퍼블리싱 파이프라인 구축

### 최근 완료 미션 (최근 5개)
- [M-005] SEO 키워드 분석 모듈 구현 — keyword_analyzer.py 완성, 10개 키워드 추출 테스트 통과
- [M-004] 마크다운 → HTML 변환기 구현 — converter.py 완성, 코드 블록/이미지 지원
- [M-003] 블로그 템플릿 시스템 설계 — Jinja2 기반 템플릿 3종 생성
- [M-002] 프로젝트 초기 구조 생성 — pyproject.toml, 디렉토리 구조, CI 설정 완료
- [M-001] 도메인 분석 및 전략 수립 — 기술 블로그 도메인 분석 완료, 초기 전략 수립

### 현재 미션 큐 (상위 5개)
- [M-006] P1: GitHub Actions 퍼블리싱 파이프라인
- [M-007] P2: 독자 반응 분석 모듈
- [M-008] P2: 자동 교정 시스템 [deps: M-005]
- [M-009] P3: RSS 피드 생성
- [M-010] P3: 소셜 미디어 자동 공유

### 미해결 Friction (최근 5개)
- [F-003] [performance] 키워드 분석이 30초 이상 소요 (패턴: slow_keyword_analysis)
- [F-002] [error] HTML 변환 시 코드 블록 내 특수문자 이스케이프 누락 (패턴: html_escape_error)

### Owner 대기 중인 요청
- [R-002] 블로그 퍼블리싱 대상 플랫폼을 확인해주세요 (GitHub Pages / Vercel / 직접 호스팅) (미션: M-006)

### 주요 통계
- 총 세션: 12
- 총 완료 미션: 5
- 총 실패 미션: 0
- 연속 실패: 0
- 마지막 성공 세션: 2026-03-25T14:30:00Z
```

---

## 8. Current Session 관리

Supervisor가 세션을 시작/종료할 때 `run/current_session.json`을 관리한다. 이 파일은 크래시 복구의 핵심 입력이다.

```python
def set_current_session(self, session_id: str, mission_id: str | None) -> None:
    """
    현재 실행 중인 세션 정보를 기록한다.

    세션 시작 시 호출. 크래시 발생 시 recover_from_crash()가 이 파일을 참조한다.

    Args:
        session_id: 현재 세션 ID
        mission_id: 실행 중인 미션 ID (없으면 None)
    """
    self.atomic_write(
        self.run_dir / "current_session.json",
        {
            "session_id": session_id,
            "mission_id": mission_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "pid": os.getpid(),
        },
    )


def clear_current_session(self) -> None:
    """현재 세션 정보를 제거한다. 세션 정상 종료 시 호출."""
    self._cleanup_current_session()
```

---

## 9. 외부 인터페이스 요약

### Supervisor가 호출하는 메서드 (세션 생명주기 순)

```
[시스템 시작]
    recover_from_crash()           ← 이전 세션 중단 복구

[세션 루프]
    load_config()                  ← 설정 확인
    create_checkpoint(label)       ← 복구 지점 생성 (C-3)
    get_next_mission()             ← 다음 미션 선택
    set_current_session(sid, mid)  ← 현재 세션 기록
    create_session_context()       ← 세션 프롬프트용 컨텍스트 생성

    [세션 실행 중...]

    complete_mission(mid, result)  ← 미션 완료 시
    fail_mission(mid, reason)      ← 미션 실패 시
    clear_current_session()        ← 세션 정상 종료
    reset_restart_count()          ← 정상 완료 시 카운터 리셋
    add_session(record)            ← 세션 이력 기록

[아카이브 rotation]
    rotate_missions()              ← 완료/실패 미션 아카이브 (최근 10개 유지)
    rotate_friction()              ← 해결 friction 아카이브 (최근 20개 유지)
    rotate_sessions()              ← 오래된 세션 아카이브 (최근 20개 유지)
    load_archive(entity, period)   ← JSONL 아카이브 읽기
```

### Claude Code 세션이 직접 수정하는 파일

Claude Code는 `state/` 파일을 직접 읽고 쓸 수 있다. StateManager를 거치지 않는 직접 파일 수정이 발생할 수 있으며, 이는 의도된 동작이다:

- `state/missions.json` — 미션 상태 변경, 새 미션 추가
- `state/friction.json` — friction 기록 추가
- `state/requests.json` — Owner 요청 추가
- `state/strategy.json` — 전략 갱신 (자기개선)
- `state/config.toml` — 설정 값 조정 (자기개선, S-5)

Supervisor는 세션 종료 후 이 파일들의 변경을 Git 체크포인트에 포함시킨다.

---

## 10. Archive Rotation

상태 파일의 무한 성장을 방지하기 위해, 완료/해결된 레코드를 주기적으로 JSONL 아카이브 파일로 이동한다. 아카이브 파일은 `state/archive/` 디렉토리에 `{entity}-{period}.jsonl` 형식으로 저장된다. 각 rotation 메서드는 Supervisor가 세션 루프 사이에 호출한다.

### 아카이브 디렉토리 구조

```
state/archive/
    missions-2026-03.jsonl
    missions-2026-02.jsonl
    friction-2026-03.jsonl
    sessions-2026-03.jsonl
```

### 구현

```python
def _append_to_archive(self, filepath: Path, records: list[dict[str, Any]]) -> None:
    """
    JSON 객체들을 JSONL 파일에 한 줄씩 추가한다.

    아카이브 디렉토리가 없으면 생성한다.
    각 레코드는 한 줄의 JSON으로 직렬화되어 파일에 추가된다.

    Args:
        filepath: JSONL 아카이브 파일 경로
        records: 아카이브할 레코드 딕셔너리 리스트
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "a", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_archive(self, entity: str, period: str) -> list[dict[str, Any]]:
    """
    JSONL 아카이브 파일을 읽어 레코드 리스트로 반환한다.

    Args:
        entity: 엔티티 이름 ("missions", "friction", "sessions")
        period: 기간 문자열 (예: "2026-03")

    Returns:
        아카이브된 레코드 딕셔너리 리스트.
        파일이 없으면 빈 리스트를 반환한다.
    """
    filepath = self.state_dir / "archive" / f"{entity}-{period}.jsonl"
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
    """
    완료/실패 미션을 아카이브로 이동한다.

    최근 10개의 완료/실패 미션은 활성 파일에 유지하고,
    나머지를 state/archive/missions-{period}.jsonl로 이동한다.
    period는 미션의 completed_at 또는 updated_at 월 기준이다.

    Returns:
        아카이브로 이동된 미션 수
    """
    queue = self.load_missions()
    missions = queue.get("missions", [])

    # 활성 미션 (pending, in_progress)은 그대로 유지
    active = [m for m in missions if m.get("status") in ("pending", "in_progress")]
    done = [m for m in missions if m.get("status") in ("completed", "failed")]

    # 최신순 정렬 후 최근 10개 유지
    done.sort(
        key=lambda m: m.get("completed_at", m.get("updated_at", "")),
        reverse=True,
    )
    keep = done[:10]
    archive = done[10:]

    if not archive:
        return 0

    # period별로 그룹화하여 아카이브
    from collections import defaultdict
    by_period: dict[str, list] = defaultdict(list)
    for m in archive:
        ts = m.get("completed_at", m.get("updated_at", ""))
        period = ts[:7] if len(ts) >= 7 else "unknown"
        by_period[period].append(m)

    for period, records in by_period.items():
        archive_path = self.state_dir / "archive" / f"missions-{period}.jsonl"
        self._append_to_archive(archive_path, records)

    # 활성 파일 갱신
    queue["missions"] = active + keep
    self.atomic_write(self.state_dir / "missions.json", queue)

    return len(archive)


def rotate_friction(self) -> int:
    """
    해결된 friction을 아카이브로 이동한다.

    최근 20개의 해결된 friction은 활성 파일에 유지하고,
    나머지를 state/archive/friction-{period}.jsonl로 이동한다.
    period는 friction의 resolved_at 월 기준이다.

    Returns:
        아카이브로 이동된 friction 수
    """
    friction_log = self.load_friction()
    frictions = friction_log.get("frictions", [])

    # 미해결 friction은 그대로 유지
    unresolved = [f for f in frictions if not f.get("resolved", False)]
    resolved = [f for f in frictions if f.get("resolved", False)]

    # 최신순 정렬 후 최근 20개 유지
    resolved.sort(
        key=lambda f: f.get("resolved_at", f.get("created_at", "")),
        reverse=True,
    )
    keep = resolved[:20]
    archive = resolved[20:]

    if not archive:
        return 0

    # period별로 그룹화하여 아카이브
    from collections import defaultdict
    by_period: dict[str, list] = defaultdict(list)
    for f in archive:
        ts = f.get("resolved_at", f.get("created_at", ""))
        period = ts[:7] if len(ts) >= 7 else "unknown"
        by_period[period].append(f)

    for period, records in by_period.items():
        archive_path = self.state_dir / "archive" / f"friction-{period}.jsonl"
        self._append_to_archive(archive_path, records)

    # 활성 파일 갱신
    friction_log["frictions"] = unresolved + keep
    self.atomic_write(self.state_dir / "friction.json", friction_log)

    return len(archive)


def rotate_sessions(self) -> int:
    """
    오래된 세션 기록을 아카이브로 이동한다.

    최근 20개의 세션은 활성 파일에 유지하고,
    나머지를 state/archive/sessions-{period}.jsonl로 이동한다.
    period는 세션의 started_at 월 기준이다.

    Returns:
        아카이브로 이동된 세션 수
    """
    sessions = self.load_sessions()

    # 최신순 정렬 후 최근 20개 유지
    sessions.sort(
        key=lambda s: s.get("started_at", ""),
        reverse=True,
    )
    keep = sessions[:20]
    archive = sessions[20:]

    if not archive:
        return 0

    # period별로 그룹화하여 아카이브
    from collections import defaultdict
    by_period: dict[str, list] = defaultdict(list)
    for s in archive:
        ts = s.get("started_at", "")
        period = ts[:7] if len(ts) >= 7 else "unknown"
        by_period[period].append(s)

    for period, records in by_period.items():
        archive_path = self.state_dir / "archive" / f"sessions-{period}.jsonl"
        self._append_to_archive(archive_path, records)

    # 활성 파일 갱신
    self.save_sessions(keep)

    return len(archive)
```

### Rotation 호출 타이밍

Supervisor는 각 세션 루프 사이클 완료 후 rotation을 수행한다:

```
[세션 완료/실패]
    │
    ├── add_session(record)
    ├── complete_mission(mid, result) 또는 fail_mission(mid, reason)
    │
    ├── rotate_missions()    ← 완료/실패 미션 10개 초과 시 아카이브
    ├── rotate_friction()    ← 해결 friction 20개 초과 시 아카이브
    └── rotate_sessions()    ← 세션 기록 20개 초과 시 아카이브
```

---

## 11. 에러 처리 정책

| 상황 | 처리 |
|------|------|
| 상태 파일 없음 | 기본값 반환 (시스템 초기 상태) |
| JSON 파싱 실패 (파일 손상) | `.corrupted.{timestamp}` 백업 후 기본값 반환 |
| TOML 파싱 실패 (config 손상) | `.corrupted.{timestamp}` 백업 후 기본값 반환 |
| 원자적 쓰기 실패 | 임시 파일 정리 후 예외 전파 |
| Git 명령 실패 | `subprocess.CalledProcessError` 전파 (Supervisor가 처리) |
| 존재하지 않는 ID 참조 | `ValueError` 발생 |
| 디스크 공간 부족 | `OSError` 전파 (Supervisor가 Owner에 알림) |
| 아카이브 파일 없음 | `load_archive()`가 빈 리스트 반환 |
