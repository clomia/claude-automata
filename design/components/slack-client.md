# Slack Client 컴포넌트 설계

> Owner와의 모든 비동기 통신을 담당하는 Slack 클라이언트

---

## 1. 아키텍처 개요

Slack Client는 Supervisor의 asyncio 이벤트 루프 내에서 백그라운드 태스크로 실행된다. slack-bolt의 `AsyncApp`과 Socket Mode를 사용하여 Slack API와 양방향 통신한다.

### 핵심 설계 결정

| 결정 | 선택 | 근거 |
|------|------|------|
| 라이브러리 | slack-bolt (AsyncApp) | 공식 SDK, Socket Mode 지원, 이벤트 핸들러 패턴 |
| 연결 방식 | Socket Mode (WebSocket) | 방화벽 내부 동작, Public URL 불필요, 요구사항 O-2 |
| 실행 모델 | asyncio background task | Supervisor의 이벤트 루프와 통합, 논블로킹 |
| 메시지 언어 | 한국어 전용 | 요구사항 O-6 |
| 메시지 포맷 | Block Kit | 구조화된 리치 메시지, 버튼/액션 지원 |

### 컴포넌트 위치

```
system/
├── slack_client.py          # SlackClient 클래스
└── ...

logs/
└── slack.log                # Slack 전용 로그

state/
└── requests.json            # Owner 요청/응답 추적 (slack_thread_ts 포함)
```

### 의존성

```
slack-bolt[async] >= 1.20.0
slack-sdk >= 3.30.0
aiohttp >= 3.9.0
```

---

## 2. 클래스 인터페이스

### SlackClient

```python
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from slack_bolt.async_app import AsyncApp
from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

from system.state_manager import StateManager


class SlackClient:
    """
    Owner와의 모든 Slack 통신을 관리하는 클라이언트.
    Supervisor의 asyncio 루프 내에서 백그라운드 태스크로 실행된다.

    모든 Owner 대면 메시지는 한국어로 작성된다 (요구사항 O-6).
    """

    def __init__(
        self,
        bot_token: str,
        app_token: str,
        channel_id: str,
        state_manager: StateManager,
    ) -> None:
        """
        Args:
            bot_token: Slack Bot User OAuth Token (xoxb-...)
            app_token: Slack App-Level Token (xapp-...) for Socket Mode
            channel_id: 통신에 사용할 Slack 채널 ID
            state_manager: 상태 파일 관리자 (requests.json 읽기/쓰기)
        """
        self._bot_token = bot_token
        self._app_token = app_token
        self._channel_id = channel_id
        self._state_manager = state_manager

        self._app: AsyncApp | None = None
        self._socket_client: SocketModeClient | None = None
        self._web_client: AsyncWebClient | None = None
        self._running: bool = False
        self._task: asyncio.Task | None = None

        # Rate limit 관리
        self._message_queue: asyncio.Queue[dict] = asyncio.Queue()
        self._rate_limited: bool = False
        self._rate_limit_until: float = 0.0

        # 로거
        self._logger = logging.getLogger("automata.slack")

    # ─── Lifecycle ───────────────────────────────────────

    async def start(self) -> None:
        """
        Socket Mode 연결을 시작하고 이벤트 리스너를 등록한다.
        Supervisor.start()에서 호출된다.

        실행 흐름:
        1. AsyncApp 초기화 + 이벤트 핸들러 등록
        2. SocketModeClient 생성
        3. 백그라운드 태스크로 Socket Mode 연결 시작
        4. 메시지 큐 프로세서 태스크 시작

        Raises:
            SlackApiError: 토큰이 유효하지 않거나 연결 실패 시
        """
        ...

    async def stop(self) -> None:
        """
        Socket Mode 연결을 정상 종료한다.

        실행 흐름:
        1. _running = False 설정
        2. 메시지 큐의 남은 메시지 전송 시도 (최대 5초)
        3. SocketModeClient disconnect
        4. 백그라운드 태스크 cancel + await
        """
        ...

    # ─── Outbound: 메시지 전송 ────────────────────────────

    async def send_status(
        self, text: str, thread_ts: str | None = None
    ) -> str:
        """
        상태 업데이트 메시지를 전송한다.

        Args:
            text: 상태 메시지 텍스트 (한국어)
            thread_ts: 기존 스레드에 답글로 보낼 때의 thread timestamp.
                       None이면 새 메시지로 전송.

        Returns:
            전송된 메시지의 thread_ts (새 스레드 시작 시 해당 메시지의 ts)

        Block Kit 포맷:
            header: 시스템 상태
            fields:
              - 미션: {현재 미션 제목}
              - 상태: {running|blocked|idle}
              - 진행도: {progress_description}
            context: 타임스탬프
        """
        ...

    async def send_alert(self, level: str, text: str) -> str:
        """
        경고/알림 메시지를 전송한다.

        Args:
            level: "info" | "warning" | "error" | "critical"
            text: 알림 내용 (한국어)

        Returns:
            전송된 메시지의 thread_ts

        Level별 이모지:
            info: ℹ️
            warning: ⚠️
            error: ❌
            critical: 🚨

        Block Kit 포맷:
            context: [{emoji} {level_korean}]
            section: 알림 내용
            context: 타임스탬프
        """
        ...

    async def ask_owner(
        self,
        question: str,
        request_id: str,
        timeout_minutes: int = 1440,
    ) -> str:
        """
        Owner에게 질문을 보내고 응답을 기다린다 (비동기).

        이 메서드는 질문을 전송하고 즉시 반환한다. 응답은 _on_message
        이벤트 핸들러에서 비동기적으로 처리된다.

        Args:
            question: Owner에게 보낼 질문 (한국어)
            request_id: requests.json의 요청 ID (예: "REQ-001")
            timeout_minutes: 응답 대기 타임아웃 (기본 24시간)

        Returns:
            전송된 메시지의 thread_ts (requests.json에 기록됨)

        Side effects:
            - requests.json에 요청 기록 (status: "pending", slack_thread_ts 포함)
            - 메시지에 ⏳ 리액션 추가 (대기 중 표시)

        Block Kit 포맷:
            header: 🙋 Owner 확인 필요
            section: 질문 내용
            context: 요청 ID + 타임아웃 정보
            [선택적] actions: 버튼 (예: "승인", "거부")
        """
        ...

    async def send_report(
        self, title: str, sections: list[dict]
    ) -> str:
        """
        구조화된 보고서 메시지를 전송한다.

        Args:
            title: 보고서 제목 (한국어)
            sections: 보고서 섹션 리스트. 각 섹션:
                {
                    "heading": "섹션 제목",
                    "content": "섹션 내용",
                    "fields": [{"label": "...", "value": "..."}]  # 선택
                }

        Returns:
            전송된 메시지의 thread_ts

        Block Kit 포맷:
            header: {title}
            divider
            [반복] section: heading + content + fields
            divider
            context: 생성 시각
        """
        ...

    async def send_file(
        self,
        filepath: str,
        title: str,
        thread_ts: str | None = None,
    ) -> None:
        """
        파일을 Slack에 업로드한다.

        Args:
            filepath: 업로드할 파일의 로컬 경로
            title: 파일 제목
            thread_ts: 스레드에 첨부할 때의 thread timestamp

        Raises:
            FileNotFoundError: filepath가 존재하지 않을 때
            SlackApiError: 업로드 실패 시
        """
        ...

    # ─── State Sync ──────────────────────────────────────

    async def check_pending_answers(self) -> list[dict]:
        """
        미응답 요청을 확인하고 타임아웃 처리한다.
        Supervisor의 주기적 체크 루프에서 호출된다.

        Returns:
            새로 응답이 도착한 요청 리스트:
            [{"request_id": "REQ-001", "answer": "...", "answered_at": "..."}]

        동작:
        1. requests.json에서 status="pending" 요청 조회
        2. 타임아웃 초과 요청 → status="timeout" 업데이트
        3. 타임아웃 초과 메시지에 ⏰ 리액션 추가
        4. Slack 채널에 타임아웃 알림 전송
        """
        ...

    # ─── Event Handlers (내부) ────────────────────────────

    async def _on_message(self, event: dict, client: AsyncWebClient) -> None:
        """
        Slack 메시지 이벤트 핸들러. Owner 응답을 감지한다.

        필터링 조건 (모두 충족해야 처리):
        1. event["channel"] == self._channel_id (지정 채널)
        2. "thread_ts" in event (스레드 답글)
        3. "bot_id" not in event (봇이 아닌 사람의 메시지)
        4. event.get("subtype") is None (일반 메시지)

        처리 흐름:
        1. event["thread_ts"]를 requests.json의 slack_thread_ts와 매칭
        2. 매칭되는 요청이 있고 status="pending"이면:
           a. request.answer = event["text"]
           b. request.status = "answered"
           c. request.answered_at = now()
           d. requests.json 원자적 업데이트
           e. ⏳ 리액션 제거, ✅ 리액션 추가
           f. Blocker가 연결된 미션이 있으면 StateManager.unblock_mission() 호출
           g. 스레드에 확인 메시지 전송: "답변이 반영되었습니다 ✅"
        3. 매칭되는 요청이 없으면: 무시 (일반 대화)
        """
        ...

    async def _on_reaction(self, event: dict, client: AsyncWebClient) -> None:
        """
        Slack 리액션 이벤트 핸들러.

        처리하는 리액션:
        - 👍 (thumbsup): 승인으로 처리 → answer = "approved"
        - 👎 (thumbsdown): 거부로 처리 → answer = "rejected"
        - ❌ (x): 취소로 처리 → answer = "cancelled"

        필터링 조건:
        1. event["user"] != bot_user_id (봇 자신의 리액션 무시)
        2. event["item"]["channel"] == self._channel_id
        3. event["item"]["ts"]를 requests.json의 slack_thread_ts와 매칭
        """
        ...

    # ─── Rate Limit Handling ─────────────────────────────

    async def _process_message_queue(self) -> None:
        """
        메시지 큐를 처리하는 백그라운드 태스크.
        Rate limit을 준수하며 순차적으로 메시지를 전송한다.

        Rate limit 규칙:
        - chat.postMessage: 1 msg/sec/channel
        - 429 응답 시: Retry-After 헤더 값만큼 대기 후 재시도
        - 연속 429 시: 지수 백오프 (최대 60초)

        루프:
        1. 큐에서 메시지 가져오기 (blocking)
        2. Rate limit 상태 확인 → 필요시 대기
        3. 메시지 전송 시도
        4. 429 응답 → _rate_limited = True, Retry-After만큼 대기
        5. 성공 → 1초 대기 (rate limit 준수)
        """
        ...

    async def _send_with_retry(
        self,
        method: str,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> dict:
        """
        Rate limit 재시도를 포함한 Slack API 호출.

        Args:
            method: Slack API 메서드명 (예: "chat.postMessage")
            max_retries: 최대 재시도 횟수
            **kwargs: API 메서드에 전달할 인자

        Returns:
            Slack API 응답 dict

        재시도 전략:
        - 429 (Rate Limited): Retry-After 헤더 값만큼 대기 후 재시도
        - 5xx (Server Error): 지수 백오프로 재시도 (1s, 2s, 4s)
        - 4xx (Client Error): 재시도 없이 즉시 예외 발생

        Raises:
            SlackApiError: 최대 재시도 초과 시
        """
        ...
```

---

## 3. 스레드 관리

### 3.1 스레드 전략

각 Owner 요청은 독립적인 Slack 스레드를 가진다 (요구사항 O-2, O-3).

```
#automata-channel
├── [메시지] 🙋 Owner 확인 필요: 데이터베이스 스키마 검토 (REQ-001)
│   └── [답글] Owner: "PostgreSQL로 진행해주세요"        ← 이것이 answer
│   └── [답글] Bot: "답변이 반영되었습니다 ✅"
│
├── [메시지] 🙋 Owner 확인 필요: API 엔드포인트 결정 (REQ-002)
│   └── (아직 미답변 - ⏳ 리액션 표시)
│
├── [메시지] 📊 시스템 상태 업데이트
│   └── [자동 갱신 스레드]
│
└── [메시지] ⚠️ 경고: Rate limit 감지
```

### 3.2 스레드 추적 (requests.json)

```json
{
  "requests": [
    {
      "id": "REQ-001",
      "type": "question",
      "question": "데이터베이스 스키마를 검토해주세요",
      "answer": "PostgreSQL로 진행해주세요",
      "status": "answered",
      "slack_thread_ts": "1711324800.000100",
      "related_mission_id": "M-003",
      "blocker_id": "BLK-001",
      "created_at": "2026-03-25T10:00:00Z",
      "answered_at": "2026-03-25T10:30:00Z",
      "timeout_minutes": 1440
    },
    {
      "id": "REQ-002",
      "type": "question",
      "question": "API 엔드포인트 구조를 결정해주세요",
      "answer": null,
      "status": "pending",
      "slack_thread_ts": "1711324900.000200",
      "related_mission_id": "M-005",
      "blocker_id": "BLK-002",
      "created_at": "2026-03-25T11:00:00Z",
      "answered_at": null,
      "timeout_minutes": 1440
    }
  ],
  "next_id": 3
}
```

### 3.3 Human Reply 감지 알고리즘

```python
async def _is_human_reply(self, event: dict) -> bool:
    """
    이벤트가 사람의 스레드 답글인지 판별한다.

    조건 (모두 AND):
    1. thread_ts 존재 (스레드 답글)
    2. bot_id 없음 (사람의 메시지)
    3. subtype 없음 (일반 메시지, 채널 참여 등이 아님)
    4. channel이 지정 채널과 일치
    """
    return (
        "thread_ts" in event
        and "bot_id" not in event
        and event.get("subtype") is None
        and event.get("channel") == self._channel_id
    )
```

### 3.4 동시 요청 처리

Owner는 여러 요청 스레드에 임의 순서로 답변할 수 있다. 시스템은 이를 다음과 같이 처리한다:

```
[REQ-001 전송] ──────────────────────────────── [REQ-001 답변 수신]
      │                                                │
[REQ-002 전송] ─────── [REQ-002 답변 수신]             │
      │                       │                        │
[REQ-003 전송] ───────────────┼────────────────────────┼──── [아직 미답변]
                              │                        │
                              ▼                        ▼
                    M-005 blocker 해제          M-003 blocker 해제
                    M-005 실행 재개             M-003 실행 재개
```

각 요청은 `slack_thread_ts`로 독립 추적되므로, 순서에 무관하게 처리된다.

---

## 4. 메시지 포맷팅

### 4.1 Block Kit 템플릿

모든 메시지는 한국어로 작성되며, Block Kit을 사용하여 구조화된 형태로 전송한다.

#### 상태 업데이트 메시지

```python
def _build_status_blocks(
    self,
    mission_title: str,
    status: str,
    progress: str,
) -> list[dict]:
    """상태 업데이트 Block Kit 블록 생성."""
    status_emoji = {
        "running": "🔄",
        "blocked": "⏳",
        "idle": "💤",
        "completed": "✅",
        "error": "❌",
    }
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📊 시스템 상태 업데이트",
            },
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*미션:*\n{mission_title}",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*상태:*\n{status_emoji.get(status, '❓')} {status}",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*진행 상황:*\n{progress}",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*시각:*\n{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                },
            ],
        },
    ]
```

#### 경고 메시지

```python
def _build_alert_blocks(self, level: str, text: str) -> list[dict]:
    """경고/알림 Block Kit 블록 생성."""
    level_config = {
        "info": {"emoji": "ℹ️", "label": "정보"},
        "warning": {"emoji": "⚠️", "label": "경고"},
        "error": {"emoji": "❌", "label": "오류"},
        "critical": {"emoji": "🚨", "label": "긴급"},
    }
    config = level_config.get(level, level_config["info"])
    return [
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"{config['emoji']} *{config['label']}*",
                },
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": text},
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"🕐 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                },
            ],
        },
    ]
```

#### Owner 질문 메시지

```python
def _build_question_blocks(
    self,
    question: str,
    request_id: str,
    timeout_minutes: int,
) -> list[dict]:
    """Owner 질문 Block Kit 블록 생성."""
    timeout_hours = timeout_minutes / 60
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🙋 Owner 확인 필요",
            },
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": question},
        },
        {"type": "divider"},
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        f"📋 요청 ID: `{request_id}` | "
                        f"⏰ 타임아웃: {timeout_hours:.0f}시간 | "
                        f"💬 이 스레드에 답글로 응답해주세요"
                    ),
                },
            ],
        },
    ]
```

#### 보고서 메시지

```python
def _build_report_blocks(
    self, title: str, sections: list[dict]
) -> list[dict]:
    """구조화된 보고서 Block Kit 블록 생성."""
    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📋 {title}"},
        },
        {"type": "divider"},
    ]

    for section in sections:
        # 섹션 헤딩 + 내용
        section_block: dict = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{section['heading']}*\n{section.get('content', '')}",
            },
        }

        # 필드가 있으면 추가
        if "fields" in section:
            section_block["fields"] = [
                {
                    "type": "mrkdwn",
                    "text": f"*{f['label']}:*\n{f['value']}",
                }
                for f in section["fields"]
            ]

        blocks.append(section_block)

    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"📅 생성: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            },
        ],
    })

    return blocks
```

### 4.2 코드 블록 포맷

기술적 상세 정보는 Slack mrkdwn의 코드 블록으로 감싼다:

```python
def _format_technical_detail(self, label: str, content: str) -> str:
    """기술적 세부 정보를 코드 블록으로 포맷."""
    return f"*{label}:*\n```\n{content}\n```"
```

### 4.3 시각적 인디케이터 이모지 규칙

| 이모지 | 의미 | 사용처 |
|--------|------|--------|
| ✅ | 완료/성공 | 미션 완료, 응답 확인 |
| ❌ | 실패/오류 | 에러 알림, 미션 실패 |
| ⏳ | 대기 중 | 미답변 요청 리액션 |
| 🔄 | 진행 중 | 실행 중 상태 |
| ⚠️ | 경고 | 경고 알림 |
| 🚨 | 긴급 | 크리티컬 알림 |
| 📊 | 보고/상태 | 상태 업데이트 헤더 |
| 📋 | 보고서/요청 | 보고서 헤더, 요청 ID |
| 🙋 | 질문 | Owner 확인 요청 헤더 |
| 💤 | 유휴 | 시스템 유휴 상태 |
| ⏰ | 타임아웃 | 타임아웃 표시 리액션 |

---

## 5. Rate Limit 처리

### 5.1 Slack API Rate Limits

| API 메서드 | 제한 | 적용 범위 |
|-----------|------|-----------|
| chat.postMessage | Tier 2 (~1/sec/channel) | 채널별 |
| reactions.add | Tier 2 | 전체 |
| files.upload | Tier 2 | 전체 |
| conversations.history | Tier 3 (~50/min) | 전체 |

### 5.2 Rate Limit 처리 전략

```python
class RateLimiter:
    """Slack API rate limit 관리."""

    def __init__(self) -> None:
        self._min_interval: float = 1.0  # 초 단위 최소 간격
        self._last_sent: float = 0.0
        self._backoff_count: int = 0
        self._max_backoff: float = 60.0

    async def wait_if_needed(self) -> None:
        """다음 메시지 전송 전 필요한 대기를 수행."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_sent
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)
        self._last_sent = asyncio.get_event_loop().time()

    def on_rate_limited(self, retry_after: float) -> float:
        """
        429 응답 처리. 대기해야 할 시간을 반환.

        Args:
            retry_after: Retry-After 헤더 값 (초)

        Returns:
            실제 대기 시간 (초). retry_after와 지수 백오프 중 큰 값.
        """
        self._backoff_count += 1
        backoff = min(2 ** self._backoff_count, self._max_backoff)
        wait_time = max(retry_after, backoff)
        return wait_time

    def on_success(self) -> None:
        """성공적 전송 후 백오프 카운터 리셋."""
        self._backoff_count = 0
```

### 5.3 메시지 큐 처리 흐름

```
메시지 생성 (send_status, send_alert, ...)
    │
    ▼
[메시지 큐에 추가]
    │
    ▼
[큐 프로세서 태스크] (백그라운드 루프)
    │
    ├── 큐에서 메시지 꺼냄
    │
    ├── RateLimiter.wait_if_needed()
    │
    ├── Slack API 호출 시도
    │   │
    │   ├── 성공 → RateLimiter.on_success() → 다음 메시지
    │   │
    │   ├── 429 → RateLimiter.on_rate_limited(retry_after)
    │   │         → asyncio.sleep(wait_time)
    │   │         → 재시도 (메시지를 큐 앞에 다시 넣음)
    │   │
    │   └── 5xx → 지수 백오프 재시도 (최대 3회)
    │
    └── 루프 계속
```

---

## 6. 이벤트 흐름

### 6.1 Owner 응답 수신 흐름 (메인 시나리오)

```
Owner가 Slack 스레드에 답글 작성
    │
    ▼
[Slack WebSocket] Socket Mode가 message 이벤트 수신
    │
    ▼
[_on_message 핸들러]
    │
    ├── 필터: has thread_ts? ─── No ──→ 무시 (일반 메시지)
    │         │
    │         Yes
    │         │
    ├── 필터: bot_id 없음? ──── No ──→ 무시 (봇 메시지)
    │         │
    │         Yes
    │         │
    ├── 필터: subtype 없음? ─── No ──→ 무시 (시스템 메시지)
    │         │
    │         Yes
    │         │
    ├── 필터: 지정 채널? ────── No ──→ 무시 (다른 채널)
    │         │
    │         Yes
    │         │
    ▼
[requests.json에서 thread_ts 매칭]
    │
    ├── 매칭 없음 ──→ 무시 (일반 스레드 대화)
    │
    ├── 매칭됨 + status != "pending" ──→ 무시 (이미 처리됨)
    │
    └── 매칭됨 + status == "pending"
        │
        ▼
    [요청 업데이트]
    ├── request.answer = event["text"]
    ├── request.status = "answered"
    ├── request.answered_at = now()
    │
    ▼
    [StateManager.update_request()] ── 원자적 파일 쓰기
    │
    ▼
    [리액션 업데이트]
    ├── reactions.remove("hourglass_flowing_sand")  # ⏳ 제거
    └── reactions.add("white_check_mark")           # ✅ 추가
    │
    ▼
    [스레드에 확인 메시지]
    └── "답변이 반영되었습니다 ✅"
    │
    ▼
    [Blocker 해제 확인]
    ├── request.blocker_id 존재?
    │   │
    │   ├── Yes → StateManager.unblock_mission(request.related_mission_id)
    │   │         → Supervisor에 미션 재개 알림
    │   │
    │   └── No → 완료
    │
    ▼
[완료]
```

### 6.2 리액션 응답 흐름

```
Owner가 질문 메시지에 👍 리액션 추가
    │
    ▼
[Slack WebSocket] reaction_added 이벤트 수신
    │
    ▼
[_on_reaction 핸들러]
    │
    ├── 필터: 봇 자신의 리액션? ──→ 무시
    ├── 필터: 지정 채널?         ──→ 아니면 무시
    │
    ▼
[event["item"]["ts"]를 requests.json과 매칭]
    │
    ├── 매칭 없음 ──→ 무시
    │
    └── 매칭됨
        │
        ▼
    [리액션 해석]
    ├── 👍 (thumbsup)   → answer = "approved"
    ├── 👎 (thumbsdown) → answer = "rejected"
    └── ❌ (x)          → answer = "cancelled"
        │
        ▼
    [요청 업데이트 + Blocker 해제] (메시지 응답과 동일 흐름)
```

---

## 7. 초기화 및 연결 관리

### 7.1 AsyncApp 초기화

```python
async def _init_app(self) -> None:
    """AsyncApp 및 이벤트 핸들러를 초기화한다."""
    self._app = AsyncApp(token=self._bot_token)
    self._web_client = AsyncWebClient(token=self._bot_token)

    # 이벤트 핸들러 등록
    @self._app.event("message")
    async def handle_message(event, client):
        await self._on_message(event, client)

    @self._app.event("reaction_added")
    async def handle_reaction(event, client):
        await self._on_reaction(event, client)

    # Socket Mode 클라이언트 생성
    self._socket_client = SocketModeClient(
        app=self._app,
        app_token=self._app_token,
    )
```

### 7.2 연결 복구

```python
async def _connection_monitor(self) -> None:
    """
    Socket Mode 연결 상태를 모니터링하고 재연결한다.

    루프 (10초 간격):
    1. Socket Mode 연결 상태 확인
    2. 연결 끊김 감지 → 재연결 시도
    3. 재연결 실패 → 지수 백오프 (최대 5분)
    4. 5회 연속 실패 → Supervisor에 알림 (fallback: 로그만 기록)
    """
    reconnect_attempts = 0
    max_backoff = 300  # 5분

    while self._running:
        await asyncio.sleep(10)

        if not self._socket_client or not self._socket_client.is_connected():
            reconnect_attempts += 1
            backoff = min(2 ** reconnect_attempts, max_backoff)

            self._logger.warning(
                "Socket Mode 연결 끊김. 재연결 시도 #%d (대기: %ds)",
                reconnect_attempts,
                backoff,
            )

            try:
                await self._socket_client.connect()
                reconnect_attempts = 0
                self._logger.info("Socket Mode 재연결 성공")
            except Exception as e:
                self._logger.error("Socket Mode 재연결 실패: %s", e)
                if reconnect_attempts >= 5:
                    self._logger.critical(
                        "Socket Mode 연결 5회 연속 실패. 수동 확인 필요."
                    )
                await asyncio.sleep(backoff)
```

---

## 8. OAuth Scopes 및 Slack 앱 설정

### 8.1 필요한 Bot Token Scopes

| Scope | 용도 |
|-------|------|
| `chat:write` | 메시지 전송 |
| `channels:history` | 채널 메시지 히스토리 읽기 (public 채널) |
| `groups:history` | private 채널 메시지 히스토리 읽기 (private 채널 사용 시) |
| `reactions:write` | 리액션 추가/제거 |
| `reactions:read` | 리액션 이벤트 수신 |
| `files:write` | 파일 업로드 |
| `files:read` | 파일 정보 읽기 |
| `channels:read` | 채널 정보 읽기 |
| `users:read` | 사용자 정보 읽기 (Owner 식별) |

### 8.2 필요한 Event Subscriptions

| Event | 용도 |
|-------|------|
| `message.channels` | public 채널 메시지 이벤트 |
| `message.groups` | private 채널 메시지 이벤트 |
| `reaction_added` | 리액션 추가 이벤트 |
| `reaction_removed` | 리액션 제거 이벤트 |

### 8.3 Slack App Manifest

```yaml
# setup/slack_manifest.yaml
# Slack App 설정 매니페스트
# Slack API > Your Apps > Create New App > From an app manifest

display_information:
  name: Claude Automata
  description: AI Automata의 Owner 통신 채널
  background_color: "#1a1a2e"
  long_description: |
    claude-automata 시스템의 Slack 클라이언트.
    Owner와의 비동기 통신, 상태 알림, 질문/응답을 담당합니다.

features:
  bot_user:
    display_name: Automata Bot
    always_online: true
  app_home:
    home_tab_enabled: false
    messages_tab_enabled: true
    messages_tab_read_only_enabled: false

oauth_config:
  scopes:
    bot:
      - chat:write
      - channels:history
      - groups:history
      - reactions:write
      - reactions:read
      - files:write
      - files:read
      - channels:read
      - users:read

settings:
  event_subscriptions:
    bot_events:
      - message.channels
      - message.groups
      - reaction_added
      - reaction_removed
  interactivity:
    is_enabled: false  # Block Kit 버튼 사용 시 true로 변경
  org_deploy_enabled: false
  socket_mode_enabled: true
  token_rotation_enabled: false
```

### 8.4 Socket Mode 설정 절차

```
1. Slack API (api.slack.com) → Your Apps → Create New App
   - "From an app manifest" 선택
   - 워크스페이스 선택
   - 위 YAML 매니페스트 붙여넣기

2. Basic Information → App-Level Tokens
   - "Generate Token and Scopes" 클릭
   - Token Name: "automata-socket"
   - Scope: connections:write 추가
   - Generate → xapp-... 토큰 복사

3. OAuth & Permissions → Install to Workspace
   - 권한 승인
   - Bot User OAuth Token (xoxb-...) 복사

4. 시스템 설정
   - `automata configure` 실행 시:
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_APP_TOKEN=xapp-...
     - SLACK_CHANNEL_ID=C0xxxxxxx (사용할 채널 ID)
   - .env 파일에 저장
```

---

## 9. 에러 처리

### 9.1 에러 분류

| 에러 유형 | 처리 전략 |
|-----------|-----------|
| `SlackApiError` (429) | Rate limit 대기 후 재시도 |
| `SlackApiError` (5xx) | 지수 백오프 재시도 |
| `SlackApiError` (4xx) | 로그 기록, 재시도 없음 |
| Socket Mode 연결 끊김 | 자동 재연결 (지수 백오프) |
| `invalid_auth` | 로그 기록, Supervisor에 알림 |
| `channel_not_found` | 로그 기록, Supervisor에 알림 |
| `not_in_channel` | 봇을 채널에 초대 필요 알림 |

### 9.2 Fallback 동작

Slack 연결이 완전히 불가능한 경우:
1. 모든 메시지를 `logs/slack.log`에 기록 (메시지 유실 방지)
2. Supervisor에 Slack 장애 상태 알림
3. 주기적 재연결 시도 (5분 간격)
4. 시스템 운영은 계속 (Slack은 통신 채널일 뿐, 핵심 기능이 아님)

---

## 10. 테스트 전략

### 10.1 단위 테스트

```python
# tests/test_slack_client.py

class TestSlackClient:
    """SlackClient 단위 테스트 (Slack API 모킹)."""

    async def test_send_status_returns_thread_ts(self): ...
    async def test_send_alert_correct_emoji_by_level(self): ...
    async def test_ask_owner_creates_request(self): ...
    async def test_on_message_filters_bot_messages(self): ...
    async def test_on_message_matches_thread_to_request(self): ...
    async def test_on_message_updates_request_status(self): ...
    async def test_on_reaction_thumbsup_approves(self): ...
    async def test_rate_limiter_waits_on_429(self): ...
    async def test_check_pending_answers_timeout(self): ...
    async def test_build_status_blocks_korean(self): ...
```

### 10.2 통합 테스트

```python
# tests/test_slack_integration.py

class TestSlackIntegration:
    """Slack API 실제 연결 통합 테스트 (테스트 채널 사용)."""

    async def test_send_and_receive_message(self): ...
    async def test_thread_reply_detection(self): ...
    async def test_reaction_handling(self): ...
    async def test_file_upload(self): ...
    async def test_socket_mode_reconnection(self): ...
```
