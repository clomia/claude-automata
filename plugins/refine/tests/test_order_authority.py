"""Refine의 executionOrder가 실행 집합의 정본이다 — Plan 산출물로 되돌려 거르면
Refine이 분할·신설한 계획이 Apply에서 소리 없이 사라지고 (#121), 빈 배열을 전량
실행으로 뒤집으면 정당한 전량 폐기가 표현 불가능해진다."""

from pathlib import Path

WORKFLOWS = sorted((Path(__file__).parents[1] / "skills").glob("*/workflow.js"))

ORDERED = "const ordered = [...new Set((refined?.executionOrder ?? []).map((n) => String(n).trim()))]"
ALL_DROPPED = "if (refined && !ordered.length)"
ORDER_IS_ORDERED = "const order = ordered"
APPLY_FROM_NAME = "계획(${plansDir}/${name}/proposal.md)"


def test_execution_order_is_authoritative():
    assert WORKFLOWS
    for script in WORKFLOWS:
        source = script.read_text(encoding="utf-8")
        assert ORDERED in source, script
        assert ALL_DROPPED in source, script
        assert ORDER_IS_ORDERED in source, script
        assert APPLY_FROM_NAME in source, script
        assert "minItems" not in source, script
