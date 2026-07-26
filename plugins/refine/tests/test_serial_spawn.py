"""workflow는 agent를 직렬로만 spawn한다 — session limit이 fan-out의 상한이다."""

from pathlib import Path

FANOUT = ("parallel(", "pipeline(", "Promise.all")
WORKFLOWS = sorted((Path(__file__).parents[1] / "skills").glob("*/workflow.js"))


def test_workflows_never_fan_out():
    assert WORKFLOWS
    for script in WORKFLOWS:
        source = script.read_text(encoding="utf-8")
        assert [token for token in FANOUT if token in source] == [], script
