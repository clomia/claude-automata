"""
에러 분류기.

Claude Code 세션의 종료 상태를 분석하여 에러 유형을 분류하고,
각 유형에 맞는 복구 전략을 반환한다.

참조 요구사항: E-2 (장애 불멸), E-3 (장애 분류)
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ErrorType(Enum):
    """Claude Code 세션 에러 유형. 정의 순서가 분류 우선순위."""

    RATE_LIMITED = "rate_limited"
    AUTH_FAILURE = "auth_failure"
    TRANSIENT_API = "transient_api"
    NETWORK_ERROR = "network_error"
    CONTEXT_CORRUPTION = "context_corruption"
    STUCK = "stuck"
    PROCESS_CRASH = "process_crash"
    UNKNOWN = "unknown"


@dataclass
class RecoveryStrategy:
    """
    에러 복구 전략.

    Attributes:
        action: 복구 동작 유형
            - "retry_resume": 기존 세션을 --resume으로 재개
            - "retry_fresh": 새 세션을 시작
            - "wait_and_resume": 지정 시간 대기 후 세션 재개
            - "notify_owner": Owner에 Slack 알림 후 대기
            - "checkpoint_restore": 체크포인트 복원 후 새 세션
        delay_seconds: 재시도 전 대기 시간 (초)
        max_retries: 이 전략의 최대 재시도 횟수
        escalate_after: N회 실패 후 다음 전략으로 에스컬레이션
        next_strategy: 에스컬레이션 시 전환할 action
    """

    action: str
    delay_seconds: float
    max_retries: int
    escalate_after: int
    next_strategy: str | None


RECOVERY_STRATEGIES: dict[ErrorType, RecoveryStrategy] = {
    ErrorType.TRANSIENT_API: RecoveryStrategy(
        action="retry_resume",
        delay_seconds=1.0,
        max_retries=5,
        escalate_after=5,
        next_strategy="notify_owner",
    ),
    ErrorType.RATE_LIMITED: RecoveryStrategy(
        action="wait_and_resume",
        delay_seconds=0.0,  # retry_after 값을 사용
        max_retries=10,
        escalate_after=5,
        next_strategy="notify_owner",
    ),
    ErrorType.AUTH_FAILURE: RecoveryStrategy(
        action="notify_owner",
        delay_seconds=0.0,
        max_retries=0,
        escalate_after=1,
        next_strategy=None,
    ),
    ErrorType.CONTEXT_CORRUPTION: RecoveryStrategy(
        action="checkpoint_restore",
        delay_seconds=2.0,
        max_retries=3,
        escalate_after=3,
        next_strategy="notify_owner",
    ),
    ErrorType.PROCESS_CRASH: RecoveryStrategy(
        action="retry_fresh",
        delay_seconds=5.0,
        max_retries=3,
        escalate_after=3,
        next_strategy="notify_owner",
    ),
    ErrorType.NETWORK_ERROR: RecoveryStrategy(
        action="retry_resume",
        delay_seconds=2.0,
        max_retries=10,
        escalate_after=10,
        next_strategy="notify_owner",
    ),
    ErrorType.STUCK: RecoveryStrategy(
        action="retry_fresh",
        delay_seconds=10.0,
        max_retries=3,
        escalate_after=3,
        next_strategy="notify_owner",
    ),
    ErrorType.UNKNOWN: RecoveryStrategy(
        action="retry_fresh",
        delay_seconds=5.0,
        max_retries=1,
        escalate_after=2,
        next_strategy="notify_owner",
    ),
}


class ErrorClassifier:
    """
    에러 분류기.

    Claude Code 세션의 종료 상태를 분석하여 에러 유형을 분류하고,
    적절한 복구 전략을 반환한다.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.failure_counts: dict[str, int] = {}
        self._last_classify_result: ErrorType | None = None

    def classify(
        self,
        exit_code: int,
        stderr: str,
        stream_events: list[dict[str, Any]],
    ) -> ErrorType:
        """에러를 분류한다. 우선순위 순서로 첫 번째 매칭 반환."""
        stderr_lower = stderr.lower()

        if self._is_rate_limited(stderr_lower, stream_events):
            return self._record(ErrorType.RATE_LIMITED)

        if self._is_auth_failure(stderr_lower):
            return self._record(ErrorType.AUTH_FAILURE)

        if self._is_transient_api(exit_code, stderr_lower):
            return self._record(ErrorType.TRANSIENT_API)

        if self._is_network_error(stderr_lower):
            return self._record(ErrorType.NETWORK_ERROR)

        if self._is_context_corruption(stderr_lower, stream_events):
            return self._record(ErrorType.CONTEXT_CORRUPTION)

        if self._is_stuck(stream_events):
            return self._record(ErrorType.STUCK)

        if self._is_process_crash(exit_code, stream_events):
            return self._record(ErrorType.PROCESS_CRASH)

        return self._record(ErrorType.UNKNOWN)

    def _record(self, error_type: ErrorType) -> ErrorType:
        self._last_classify_result = error_type
        return error_type

    # ── 개별 탐지 메서드 ──

    def _is_rate_limited(
        self, stderr_lower: str, stream_events: list[dict[str, Any]]
    ) -> bool:
        for event in stream_events:
            if event.get("type") == "system" and event.get("subtype") == "api_retry":
                if event.get("error") == "rate_limit":
                    return True
        return "429" in stderr_lower or "rate limit" in stderr_lower

    def _is_auth_failure(self, stderr_lower: str) -> bool:
        auth_patterns = [
            "401", "403", "unauthorized", "forbidden",
            "authentication", "auth failed", "login required",
            "not authenticated", "invalid token", "expired token",
        ]
        return any(pattern in stderr_lower for pattern in auth_patterns)

    def _is_transient_api(
        self, exit_code: int, stderr_lower: str
    ) -> bool:
        if exit_code == 0:
            return False
        transient_patterns = [
            "500", "502", "503", "504", "internal server error",
            "bad gateway", "service unavailable", "gateway timeout",
        ]
        return any(
            pattern in stderr_lower for pattern in transient_patterns
        )

    def _is_network_error(self, stderr_lower: str) -> bool:
        network_patterns = [
            "econnrefused", "enotfound", "econnreset",
            "econnaborted", "etimedout", "connection refused",
            "connection reset", "connection timed out",
            "network error", "dns resolution", "socket hang up",
            "fetch failed",
        ]
        return any(
            pattern in stderr_lower for pattern in network_patterns
        )

    def _is_context_corruption(
        self,
        stderr_lower: str,
        stream_events: list[dict[str, Any]],
    ) -> bool:
        corruption_patterns = [
            "json parse error", "unexpected token",
            "invalid json", "malformed", "decode error",
            "utf-8", "encoding error",
        ]
        if any(
            pattern in stderr_lower
            for pattern in corruption_patterns
        ):
            return True

        if stream_events:
            last_event = stream_events[-1]
            if "type" not in last_event:
                return True
        return False

    def _is_stuck(
        self, stream_events: list[dict[str, Any]]
    ) -> bool:
        for event in stream_events:
            if event.get("type") == "_supervisor_timeout":
                return True
        return False

    def _is_process_crash(
        self, exit_code: int, stream_events: list[dict[str, Any]]
    ) -> bool:
        if exit_code == 0:
            return False
        has_result = any(
            event.get("type") == "result" for event in stream_events
        )
        return not has_result

    # ── 복구 전략 ──

    def get_recovery_strategy(
        self, error_type: ErrorType, attempt: int = 0
    ) -> RecoveryStrategy:
        base_strategy = RECOVERY_STRATEGIES[error_type]
        failure_count = self.failure_counts.get(error_type.value, 0)

        if failure_count >= base_strategy.escalate_after:
            return self._escalate(base_strategy)

        if base_strategy.action in ("retry_resume", "retry_fresh"):
            delay = self.calculate_backoff(
                attempt=attempt, base=base_strategy.delay_seconds
            )
        else:
            delay = base_strategy.delay_seconds

        return RecoveryStrategy(
            action=base_strategy.action,
            delay_seconds=delay,
            max_retries=base_strategy.max_retries,
            escalate_after=base_strategy.escalate_after,
            next_strategy=base_strategy.next_strategy,
        )

    def _escalate(self, current: RecoveryStrategy) -> RecoveryStrategy:
        next_action = current.next_strategy or "notify_owner"
        return RecoveryStrategy(
            action=next_action,
            delay_seconds=0.0,
            max_retries=0,
            escalate_after=0,
            next_strategy=None,
        )

    # ── 백오프 계산 ──

    def calculate_backoff(
        self,
        attempt: int,
        base: float | None = None,
        max_delay: float | None = None,
    ) -> float:
        """지수 백오프 + 지터 (0~25%)."""
        if base is None:
            base = self.config.get("backoff_base_seconds", 1.0)
        if max_delay is None:
            max_delay = self.config.get("backoff_max_seconds", 60.0)

        delay = base * (2**attempt)
        delay = min(delay, max_delay)
        jitter = delay * random.uniform(0.0, 0.25)
        return delay + jitter

    @staticmethod
    def extract_retry_after(
        stream_events: list[dict[str, Any]],
    ) -> float | None:
        for event in reversed(stream_events):
            if event.get("type") == "system" and event.get("subtype") == "api_retry":
                retry_after = event.get("retry_delay_ms")
                if retry_after is not None:
                    return float(retry_after) / 1000.0
        return None

    # ── 연속 실패 추적 ──

    def record_failure(self, error_type: ErrorType) -> int:
        key = error_type.value
        self.failure_counts[key] = self.failure_counts.get(key, 0) + 1
        return self.failure_counts[key]

    def record_success(
        self, error_type: ErrorType | None = None
    ) -> None:
        if error_type is None:
            self.failure_counts.clear()
        else:
            self.failure_counts.pop(error_type.value, None)

    def get_failure_count(self, error_type: ErrorType) -> int:
        return self.failure_counts.get(error_type.value, 0)

    def should_escalate(self, error_type: ErrorType) -> bool:
        strategy = RECOVERY_STRATEGIES[error_type]
        count = self.get_failure_count(error_type)
        return count >= strategy.escalate_after

    def should_notify_owner(self) -> bool:
        max_failures = self.config.get("max_consecutive_failures", 3)
        total_consecutive = sum(self.failure_counts.values())
        return total_consecutive >= max_failures

    # ── 통합 인터페이스 ──

    def classify_and_recover(
        self,
        exit_code: int,
        stderr: str,
        stream_events: list[dict[str, Any]],
        attempt: int = 0,
    ) -> tuple[ErrorType, RecoveryStrategy]:
        """에러를 분류하고 복구 전략을 반환한다."""
        error_type = self.classify(exit_code, stderr, stream_events)
        self.record_failure(error_type)
        strategy = self.get_recovery_strategy(error_type, attempt)

        if error_type == ErrorType.RATE_LIMITED:
            retry_after = self.extract_retry_after(stream_events)
            if retry_after is not None:
                strategy = RecoveryStrategy(
                    action=strategy.action,
                    delay_seconds=retry_after,
                    max_retries=strategy.max_retries,
                    escalate_after=strategy.escalate_after,
                    next_strategy=strategy.next_strategy,
                )

        return error_type, strategy
