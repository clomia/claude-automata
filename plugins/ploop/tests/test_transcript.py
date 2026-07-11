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

    def test_compact_summary_does_not_split_round(self, tmp_path):
        """Auto-compaction appends its session summary as a string-content
        user line — the round boundary's exact shape — while every earlier
        line stays in the append-only file.  The parser must drop it, or a
        mid-round compaction truncates the round's pre-compaction actions."""
        t = tmp_path / "t.jsonl"
        t.write_text(
            "\n".join(
                json.dumps(line)
                for line in [
                    {"message": {"role": "user", "content": "trigger"}},
                    {"message": {"role": "assistant", "content": "work before"}},
                    {
                        "type": "system",
                        "subtype": "compact_boundary",
                        "compactMetadata": {"trigger": "auto"},
                    },
                    {
                        "isCompactSummary": True,
                        "message": {
                            "role": "user",
                            "content": "This session is being continued...",
                        },
                    },
                    {"message": {"role": "assistant", "content": "work after"}},
                ]
            )
        )
        actions = parse_round_actions(str(t))
        assert [a["content"] for a in actions] == ["work before", "work after"]

    def test_queued_commands_enter_actions_without_splitting_round(self, tmp_path):
        """Mid-turn injections (user steering above all) exist only as
        queued_command attachments — never as message lines.  They must enter
        the actions at their delivery position as list-content user messages:
        visible to the narrator, never a round boundary.  Both prompt forms
        (plain string, block list) occur in real transcripts; image blocks are
        base64 noise and stay out."""
        t = tmp_path / "t.jsonl"
        t.write_text(
            "\n".join(
                json.dumps(line)
                for line in [
                    {"message": {"role": "user", "content": "trigger"}},
                    {"message": {"role": "assistant", "content": "work before"}},
                    {
                        "type": "attachment",
                        "attachment": {"type": "queued_command", "prompt": "긴급 지시"},
                    },
                    {
                        "type": "attachment",
                        "attachment": {
                            "type": "queued_command",
                            "prompt": [
                                {"type": "text", "text": "블록 지시"},
                                {"type": "image", "source": {"data": "…base64…"}},
                            ],
                        },
                    },
                    {
                        "type": "attachment",
                        "attachment": {"type": "task_reminder", "content": []},
                    },
                    {"message": {"role": "assistant", "content": "work after"}},
                ]
            )
        )
        actions = parse_round_actions(str(t))
        assert [a["content"] for a in actions] == [
            "work before",
            [{"type": "text", "text": "긴급 지시"}],
            [{"type": "text", "text": "블록 지시"}],
            "work after",
        ]

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
