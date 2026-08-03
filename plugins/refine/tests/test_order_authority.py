"""Refine의 executionOrder가 실행 집합의 정본이다 — Plan 산출물로 되돌려 거르면
Refine이 분할·신설한 계획이 Apply에서 소리 없이 사라진다 (#121)."""

from pathlib import Path

WORKFLOWS = sorted((Path(__file__).parents[1] / "skills").glob("*/workflow.js"))

ORDERED = "const ordered = [...new Set((refined?.executionOrder ?? []).map((n) => String(n).trim()))]"
FALLBACK = "const order = ordered.length ? ordered : plans.map((p) => p.name)"
APPLY_FROM_NAME = "계획(${plansDir}/${name}/proposal.md)"


def test_execution_order_is_authoritative():
    assert WORKFLOWS
    for script in WORKFLOWS:
        source = script.read_text(encoding="utf-8")
        assert ORDERED in source, script
        assert FALLBACK in source, script
        assert APPLY_FROM_NAME in source, script
