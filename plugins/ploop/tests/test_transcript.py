"""Tests for the transcript module."""

import json

from src.transcript import (
    is_round_boundary,
    parse_round_actions,
)


def write_jsonl(path, messages):
    path.write_text("\n".join(json.dumps({"message": m}) for m in messages))


def agent_exchange(result, *, tool="Agent", subagent="advisor", call_id="a1"):
    """An Agent(subagent) tool_use followed by its tool_result."""
    return [
        {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": call_id,
                    "name": tool,
                    "input": {"subagent_type": subagent},
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": call_id, "content": result}
            ],
        },
    ]


# ── is_round_boundary ──


class TestRoundBoundary:
    def test_user_string_is_boundary(self):
        assert is_round_boundary({"role": "user", "content": "task"}) is True

    def test_tool_result_is_not_boundary(self):
        msg = {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "t", "content": "ok"}],
        }
        assert is_round_boundary(msg) is False

    def test_assistant_is_not_boundary(self):
        assert is_round_boundary({"role": "assistant", "content": "hi"}) is False


# ── parse_round_actions ──


class TestParseRoundActions:
    def test_returns_actions_after_last_boundary(self, tmp_path):
        t = tmp_path / "t.jsonl"
        write_jsonl(
            t,
            [
                {"role": "user", "content": "mission handoff"},
                {"role": "assistant", "content": "round 0 work"},
                {"role": "user", "content": "advisor trigger injection"},
                {"role": "assistant", "content": "round 1 work"},
            ],
        )
        actions = parse_round_actions(str(t))
        assert len(actions) == 1
        assert actions[0]["content"] == "round 1 work"

    def test_strips_advisor_exchange(self, tmp_path):
        """The Agent(advisor) call is loop machinery, not the main agent's work,
        so it is removed from action-history (the loop keeps action-history and
        advice-history distinct)."""
        t = tmp_path / "t.jsonl"
        write_jsonl(
            t,
            [
                {"role": "user", "content": "trigger"},
                *agent_exchange("provide advice"),
                {"role": "assistant", "content": "the main agent's actual work"},
            ],
        )
        actions = parse_round_actions(str(t))
        assert len(actions) == 1
        assert actions[0]["content"] == "the main agent's actual work"

    def test_keeps_non_advisor_subagent_calls(self, tmp_path):
        """The main agent's own delegation (e.g. Explore) is real work and stays."""
        t = tmp_path / "t.jsonl"
        write_jsonl(
            t,
            [
                {"role": "user", "content": "trigger"},
                *agent_exchange("findings", subagent="Explore", call_id="e1"),
                {"role": "assistant", "content": "acted on findings"},
            ],
        )
        actions = parse_round_actions(str(t))
        assert len(actions) == 3

    def test_missing_file_returns_empty(self):
        assert parse_round_actions("/nonexistent.jsonl") == []

    def test_truncated_last_line_skipped(self, tmp_path):
        t = tmp_path / "t.jsonl"
        full = json.dumps({"message": {"role": "assistant", "content": "final"}})
        t.write_text(
            json.dumps({"message": {"role": "user", "content": "trigger"}})
            + "\n"
            + full[:15]
        )
        assert parse_round_actions(str(t)) == []
