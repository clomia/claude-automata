"""
Slack Client.

Owner와의 모든 비동기 통신을 관리하는 Slack 클라이언트.
Supervisor의 asyncio 루프 내에서 백그라운드 태스크로 실행된다.

참조 요구사항: O-1~O-4, O-6
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from slack_bolt.async_app import AsyncApp
from slack_sdk.errors import SlackApiError
from slack_sdk.socket_mode.async_client import AsyncBaseSocketModeClient
from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.web.async_client import AsyncWebClient

from system.state_manager import StateManager


class SlackClient:
    """Owner와의 모든 Slack 통신을 관리하는 클라이언트."""

    def __init__(
        self,
        bot_token: str,
        app_token: str,
        channel_id: str,
        state_manager: StateManager,
    ) -> None:
        self._bot_token = bot_token
        self._app_token = app_token
        self._channel_id = channel_id
        self._state_manager = state_manager

        self._app: AsyncApp | None = None
        self._socket_client: SocketModeClient | None = None
        self._web_client: AsyncWebClient | None = None
        self._running: bool = False
        self._task: asyncio.Task[None] | None = None

        self._message_queue: asyncio.Queue[dict[str, Any]] = (
            asyncio.Queue()
        )
        self._rate_limited: bool = False
        self._rate_limit_until: float = 0.0

        self._logger = logging.getLogger("automata.slack")

    # ── Lifecycle ──

    async def start(self) -> None:
        """Socket Mode 연결을 시작하고 이벤트 리스너를 등록한다."""
        self._app = AsyncApp(token=self._bot_token)
        self._web_client = AsyncWebClient(token=self._bot_token)

        @self._app.event("message")
        async def handle_message(event: dict[str, Any], client: AsyncWebClient) -> None:
            await self._on_message(event, client)

        @self._app.event("reaction_added")
        async def handle_reaction(event: dict[str, Any], client: AsyncWebClient) -> None:
            await self._on_reaction(event, client)

        self._socket_client = SocketModeClient(
            app=self._app,
            app_token=self._app_token,
        )

        self._running = True
        self._task = asyncio.create_task(
            self._socket_client.connect(), name="slack-socket-mode"
        )

        asyncio.create_task(
            self._process_message_queue(),
            name="slack-message-queue",
        )

        self._logger.info("Slack Client 시작됨")

    async def stop(self) -> None:
        """Socket Mode 연결을 정상 종료한다."""
        self._running = False
        if self._socket_client:
            try:
                await self._socket_client.disconnect()
            except Exception:
                pass
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
        self._logger.info("Slack Client 종료됨")

    # ── Outbound ──

    async def send_status(
        self, text: str, thread_ts: str | None = None
    ) -> str:
        """상태 업데이트 메시지를 전송한다."""
        blocks = self._build_status_blocks(text)
        return await self._post_message(
            text=text, blocks=blocks, thread_ts=thread_ts
        )

    async def send_alert(self, level: str, text: str) -> str:
        """경고/알림 메시지를 전송한다."""
        blocks = self._build_alert_blocks(level, text)
        return await self._post_message(text=text, blocks=blocks)

    async def ask_owner(
        self,
        question: str,
        request_id: str,
        timeout_minutes: int = 1440,
    ) -> str:
        """Owner에게 질문을 보내고 thread_ts를 반환한다."""
        blocks = self._build_question_blocks(
            question, request_id, timeout_minutes
        )
        thread_ts = await self._post_message(
            text=question, blocks=blocks
        )

        if self._web_client and thread_ts:
            try:
                await self._web_client.reactions_add(
                    channel=self._channel_id,
                    timestamp=thread_ts,
                    name="hourglass_flowing_sand",
                )
            except SlackApiError:
                pass

        return thread_ts

    async def send_report(
        self, title: str, sections: list[dict[str, Any]]
    ) -> str:
        """구조화된 보고서 메시지를 전송한다."""
        blocks = self._build_report_blocks(title, sections)
        return await self._post_message(
            text=title, blocks=blocks
        )

    async def notify(self, text: str) -> str:
        """간단한 알림 메시지를 전송한다."""
        return await self._post_message(text=text)

    # ── Event Handlers ──

    async def _on_message(
        self, event: dict[str, Any], client: AsyncWebClient
    ) -> None:
        """Slack 메시지 이벤트 핸들러. Owner 응답을 감지한다."""
        if not await self._is_human_reply(event):
            return

        thread_ts = event.get("thread_ts", "")
        answer_text = event.get("text", "")

        data = self._state_manager.load_requests()
        for request in data.get("requests", []):
            if (
                request.get("slack_thread_ts") == thread_ts
                and request.get("status") == "pending"
            ):
                request["answer"] = answer_text
                request["status"] = "answered"
                request["answered_at"] = (
                    datetime.now(timezone.utc).isoformat()
                )
                self._state_manager.save_requests(data)

                try:
                    await client.reactions_remove(
                        channel=self._channel_id,
                        timestamp=thread_ts,
                        name="hourglass_flowing_sand",
                    )
                except SlackApiError:
                    pass

                try:
                    await client.reactions_add(
                        channel=self._channel_id,
                        timestamp=thread_ts,
                        name="white_check_mark",
                    )
                except SlackApiError:
                    pass

                await self._post_message(
                    text="답변이 반영되었습니다.",
                    thread_ts=thread_ts,
                )

                blocker_for = request.get("blocker_for")
                if blocker_for:
                    try:
                        self._state_manager.unblock_mission(
                            blocker_for
                        )
                    except ValueError:
                        pass

                self._logger.info(
                    "Owner 응답 수신: %s → %s",
                    request["id"],
                    answer_text[:50],
                )
                break

    async def _on_reaction(
        self, event: dict[str, Any], client: AsyncWebClient
    ) -> None:
        """Slack 리액션 이벤트 핸들러."""
        reaction = event.get("reaction", "")
        item = event.get("item", {})
        item_ts = item.get("ts", "")
        item_channel = item.get("channel", "")

        if item_channel != self._channel_id:
            return

        reaction_map = {
            "thumbsup": "approved",
            "+1": "approved",
            "thumbsdown": "rejected",
            "-1": "rejected",
            "x": "cancelled",
        }

        answer = reaction_map.get(reaction)
        if not answer:
            return

        data = self._state_manager.load_requests()
        for request in data.get("requests", []):
            if (
                request.get("slack_thread_ts") == item_ts
                and request.get("status") == "pending"
            ):
                request["answer"] = answer
                request["status"] = "answered"
                request["answered_at"] = (
                    datetime.now(timezone.utc).isoformat()
                )
                self._state_manager.save_requests(data)

                blocker_for = request.get("blocker_for")
                if blocker_for:
                    try:
                        self._state_manager.unblock_mission(
                            blocker_for
                        )
                    except ValueError:
                        pass

                self._logger.info(
                    "Owner 리액션 응답: %s → %s",
                    request["id"],
                    answer,
                )
                break

    async def _is_human_reply(self, event: dict[str, Any]) -> bool:
        return (
            "thread_ts" in event
            and "bot_id" not in event
            and event.get("subtype") is None
            and event.get("channel") == self._channel_id
        )

    # ── Message Queue ──

    async def _process_message_queue(self) -> None:
        """메시지 큐를 순차적으로 처리한다."""
        while self._running:
            try:
                msg = await asyncio.wait_for(
                    self._message_queue.get(), timeout=5.0
                )
            except asyncio.TimeoutError:
                continue

            for attempt in range(3):
                try:
                    if self._web_client:
                        result = (
                            await self._web_client.chat_postMessage(
                                **msg
                            )
                        )
                        msg_callback = msg.get("_callback")
                        if msg_callback:
                            msg_callback(result.get("ts", ""))
                    await asyncio.sleep(1.0)
                    break
                except SlackApiError as e:
                    if e.response.status_code == 429:
                        retry_after = int(
                            e.response.headers.get(
                                "Retry-After", "5"
                            )
                        )
                        self._logger.warning(
                            "Rate limited. %ds 대기", retry_after
                        )
                        await asyncio.sleep(retry_after)
                    else:
                        self._logger.error(
                            "Slack API 에러: %s", e
                        )
                        break
                except Exception as e:
                    self._logger.error(
                        "메시지 전송 실패: %s", e
                    )
                    break

    async def _post_message(
        self,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
        thread_ts: str | None = None,
    ) -> str:
        """메시지를 큐에 추가하고 thread_ts를 반환한다."""
        result_ts: list[str] = [""]

        def callback(ts: str) -> None:
            result_ts[0] = ts

        msg: dict[str, Any] = {
            "channel": self._channel_id,
            "text": text,
            "_callback": callback,
        }
        if blocks:
            msg["blocks"] = blocks
        if thread_ts:
            msg["thread_ts"] = thread_ts

        await self._message_queue.put(msg)

        # 동기적 결과가 아니므로 빈 문자열을 반환할 수 있음
        # 큐 기반이므로 실제 전송은 비동기적으로 이루어짐
        await asyncio.sleep(0.1)
        return result_ts[0]

    # ── Block Kit ──

    def _build_status_blocks(
        self, text: str
    ) -> list[dict[str, Any]]:
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "시스템 상태 업데이트",
                },
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
                    }
                ],
            },
        ]

    def _build_alert_blocks(
        self, level: str, text: str
    ) -> list[dict[str, Any]]:
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
                    }
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
                    }
                ],
            },
        ]

    def _build_question_blocks(
        self,
        question: str,
        request_id: str,
        timeout_minutes: int,
    ) -> list[dict[str, Any]]:
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
                    }
                ],
            },
        ]

    def _build_report_blocks(
        self, title: str, sections: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📋 {title}",
                },
            },
            {"type": "divider"},
        ]

        for section in sections:
            section_block: dict[str, Any] = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{section['heading']}*\n{section.get('content', '')}",
                },
            }
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
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"📅 생성: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                    }
                ],
            }
        )
        return blocks

    # ── Pending Answers ──

    async def check_pending_answers(self) -> list[dict[str, Any]]:
        """미응답 요청을 확인하고 타임아웃 처리한다."""
        data = self._state_manager.load_requests()
        now = datetime.now(timezone.utc)
        newly_answered: list[dict[str, Any]] = []

        for request in data.get("requests", []):
            if request.get("status") != "pending":
                continue

            if request.get("status") == "answered":
                newly_answered.append(request)
                continue

            timeout = request.get("timeout_minutes", 1440)
            if timeout > 0:
                created = datetime.fromisoformat(
                    request["created_at"]
                )
                elapsed = (now - created).total_seconds() / 60
                if elapsed > timeout:
                    request["status"] = "expired"
                    self._logger.warning(
                        "요청 만료: %s", request["id"]
                    )

        self._state_manager.save_requests(data)
        return newly_answered
