"""ErrorClassifier 단위 테스트."""

from __future__ import annotations

from system.error_classifier import ErrorClassifier, ErrorType, RecoveryStrategy


def make_classifier() -> ErrorClassifier:
    return ErrorClassifier(
        {
            "max_consecutive_failures": 3,
            "backoff_base_seconds": 1.0,
            "backoff_max_seconds": 60.0,
        }
    )


class TestClassify:
    def test_rate_limited_from_stream_events(self) -> None:
        ec = make_classifier()
        events = [
            {
                "type": "system",
                "subtype": "api_retry",
                "error": "rate_limit",
                "retry_delay_ms": 30000,
            }
        ]
        result = ec.classify(1, "", events)
        assert result == ErrorType.RATE_LIMITED

    def test_rate_limited_from_stderr(self) -> None:
        ec = make_classifier()
        result = ec.classify(1, "Error: 429 rate limit exceeded", [])
        assert result == ErrorType.RATE_LIMITED

    def test_auth_failure(self) -> None:
        ec = make_classifier()
        result = ec.classify(1, "Error: 401 Unauthorized", [])
        assert result == ErrorType.AUTH_FAILURE

    def test_auth_failure_forbidden(self) -> None:
        ec = make_classifier()
        result = ec.classify(1, "403 Forbidden", [])
        assert result == ErrorType.AUTH_FAILURE

    def test_transient_api(self) -> None:
        ec = make_classifier()
        result = ec.classify(1, "502 Bad Gateway", [])
        assert result == ErrorType.TRANSIENT_API

    def test_transient_api_not_on_exit_0(self) -> None:
        ec = make_classifier()
        result = ec.classify(0, "502 Bad Gateway", [])
        # exit 0이면 transient가 아님
        assert result != ErrorType.TRANSIENT_API

    def test_network_error(self) -> None:
        ec = make_classifier()
        result = ec.classify(1, "ECONNREFUSED", [])
        assert result == ErrorType.NETWORK_ERROR

    def test_context_corruption(self) -> None:
        ec = make_classifier()
        result = ec.classify(1, "json parse error: unexpected token", [])
        assert result == ErrorType.CONTEXT_CORRUPTION

    def test_stuck(self) -> None:
        ec = make_classifier()
        events = [{"type": "_supervisor_timeout"}]
        result = ec.classify(1, "", events)
        assert result == ErrorType.STUCK

    def test_process_crash(self) -> None:
        ec = make_classifier()
        result = ec.classify(139, "", [])  # SIGSEGV
        assert result == ErrorType.PROCESS_CRASH

    def test_unknown(self) -> None:
        ec = make_classifier()
        # exit 0이고 result 이벤트 없으면 — 어떤 조건에도 안 맞음
        events = [{"type": "result"}]
        result = ec.classify(0, "", events)
        assert result == ErrorType.UNKNOWN

    def test_priority_rate_limit_over_transient(self) -> None:
        """rate limit이 transient보다 우선."""
        ec = make_classifier()
        events = [
            {
                "type": "system",
                "subtype": "api_retry",
                "error": "rate_limit",
            }
        ]
        result = ec.classify(1, "502 Bad Gateway", events)
        assert result == ErrorType.RATE_LIMITED


class TestBackoff:
    def test_exponential_backoff(self) -> None:
        ec = make_classifier()
        d0 = ec.calculate_backoff(attempt=0, base=1.0)
        d1 = ec.calculate_backoff(attempt=1, base=1.0)
        d2 = ec.calculate_backoff(attempt=2, base=1.0)

        assert 1.0 <= d0 <= 1.25
        assert 2.0 <= d1 <= 2.5
        assert 4.0 <= d2 <= 5.0

    def test_max_delay_cap(self) -> None:
        ec = make_classifier()
        d = ec.calculate_backoff(attempt=20, base=1.0, max_delay=60.0)
        assert d <= 75.0  # 60 + 25% jitter


class TestRecoveryStrategy:
    def test_transient_retry_resume(self) -> None:
        ec = make_classifier()
        strategy = ec.get_recovery_strategy(ErrorType.TRANSIENT_API)
        assert strategy.action == "retry_resume"

    def test_auth_notify_owner(self) -> None:
        ec = make_classifier()
        strategy = ec.get_recovery_strategy(ErrorType.AUTH_FAILURE)
        assert strategy.action == "notify_owner"

    def test_escalation(self) -> None:
        ec = make_classifier()
        for _ in range(5):
            ec.record_failure(ErrorType.TRANSIENT_API)
        strategy = ec.get_recovery_strategy(ErrorType.TRANSIENT_API)
        assert strategy.action == "notify_owner"


class TestFailureTracking:
    def test_record_and_count(self) -> None:
        ec = make_classifier()
        ec.record_failure(ErrorType.NETWORK_ERROR)
        ec.record_failure(ErrorType.NETWORK_ERROR)
        assert ec.get_failure_count(ErrorType.NETWORK_ERROR) == 2

    def test_record_success_resets(self) -> None:
        ec = make_classifier()
        ec.record_failure(ErrorType.NETWORK_ERROR)
        ec.record_success(ErrorType.NETWORK_ERROR)
        assert ec.get_failure_count(ErrorType.NETWORK_ERROR) == 0

    def test_record_success_all(self) -> None:
        ec = make_classifier()
        ec.record_failure(ErrorType.NETWORK_ERROR)
        ec.record_failure(ErrorType.TRANSIENT_API)
        ec.record_success()
        assert ec.get_failure_count(ErrorType.NETWORK_ERROR) == 0
        assert ec.get_failure_count(ErrorType.TRANSIENT_API) == 0


class TestClassifyAndRecover:
    def test_rate_limit_uses_retry_after(self) -> None:
        ec = make_classifier()
        events = [
            {
                "type": "system",
                "subtype": "api_retry",
                "error": "rate_limit",
                "retry_delay_ms": 45000,
            }
        ]
        error_type, strategy = ec.classify_and_recover(
            exit_code=1, stderr="", stream_events=events
        )
        assert error_type == ErrorType.RATE_LIMITED
        assert strategy.delay_seconds == 45.0

    def test_extract_retry_after(self) -> None:
        events = [
            {
                "type": "system",
                "subtype": "api_retry",
                "error": "rate_limit",
                "retry_delay_ms": 30000,
            }
        ]
        result = ErrorClassifier.extract_retry_after(events)
        assert result == 30.0
