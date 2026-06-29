"""Tests for the transcript module."""

import json

from src.transcript import (
    extract_advisor_output,
    find_operator_transcript,
    is_round_boundary,
    parse_round_actions,
    strip_subagent_meta,
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
        """The Agent(advisor) call is parallax machinery, not the operator's work,
        so it is removed from action-history (parallax kept these distinct)."""
        t = tmp_path / "t.jsonl"
        write_jsonl(
            t,
            [
                {"role": "user", "content": "trigger"},
                *agent_exchange("surface this region"),
                {"role": "assistant", "content": "the operator's actual work"},
            ],
        )
        actions = parse_round_actions(str(t))
        assert len(actions) == 1
        assert actions[0]["content"] == "the operator's actual work"

    def test_keeps_non_advisor_subagent_calls(self, tmp_path):
        """The operator's own delegation (e.g. Explore) is real work and stays."""
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


# ── extract_advisor_output ──


class TestExtractAdvisorOutput:
    def test_extracts_advisor_tool_result(self, tmp_path):
        t = tmp_path / "t.jsonl"
        write_jsonl(
            t,
            [
                {"role": "user", "content": "trigger"},
                *agent_exchange("surface this region"),
                {"role": "assistant", "content": "acting on it"},
            ],
        )
        assert extract_advisor_output(str(t)) == "surface this region"

    def test_none_when_no_advisor_call(self, tmp_path):
        t = tmp_path / "t.jsonl"
        write_jsonl(
            t,
            [
                {"role": "user", "content": "trigger"},
                {"role": "assistant", "content": "just working, no advisor"},
            ],
        )
        assert extract_advisor_output(str(t)) is None

    def test_recognizes_task_alias_and_namespaced_type(self, tmp_path):
        """The Task alias and a plugin-namespaced subagent_type both resolve."""
        t = tmp_path / "t.jsonl"
        write_jsonl(
            t, agent_exchange("region", tool="Task", subagent="parallax-loop:advisor")
        )
        assert extract_advisor_output(str(t)) == "region"

    def test_takes_most_recent_advisor_call(self, tmp_path):
        t = tmp_path / "t.jsonl"
        write_jsonl(
            t,
            [
                *agent_exchange("old region", call_id="a1"),
                *agent_exchange("new region", call_id="a2"),
            ],
        )
        assert extract_advisor_output(str(t)) == "new region"

    def test_flattens_text_block_result(self, tmp_path):
        t = tmp_path / "t.jsonl"
        write_jsonl(
            t,
            [
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "a1",
                            "name": "Agent",
                            "input": {"subagent_type": "advisor"},
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "a1",
                            "content": [{"type": "text", "text": "region from block"}],
                        }
                    ],
                },
            ],
        )
        assert extract_advisor_output(str(t)) == "region from block"

    def test_ignores_non_advisor_subagent(self, tmp_path):
        t = tmp_path / "t.jsonl"
        write_jsonl(t, agent_exchange("narration", subagent="narrator"))
        assert extract_advisor_output(str(t)) is None

    def test_skips_denied_error_result(self, tmp_path):
        """A PreToolUse-denied advisor call leaves an is_error result; the most
        recent successful call is returned instead, keeping region-history clean."""
        t = tmp_path / "t.jsonl"
        write_jsonl(
            t,
            [
                *agent_exchange("real region", call_id="a1"),
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "a2",
                            "name": "Agent",
                            "input": {"subagent_type": "parallax-loop:advisor"},
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "a2",
                            "content": "denied",
                            "is_error": True,
                        }
                    ],
                },
            ],
        )
        assert extract_advisor_output(str(t)) == "real region"


# ── find_operator_transcript ──


class TestFindOperatorTranscript:
    @staticmethod
    def operator_spawn(call_id):
        return {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": call_id,
                    "name": "Agent",
                    "input": {"subagent_type": "parallax-loop:operator"},
                }
            ],
        }

    @staticmethod
    def write_meta(subdir, agent_id, tool_use_id):
        (subdir / f"agent-{agent_id}.meta.json").write_text(
            json.dumps(
                {"agentType": "parallax-loop:operator", "toolUseId": tool_use_id}
            )
        )
        (subdir / f"agent-{agent_id}.jsonl").write_text("")

    def test_resolves_latest_operator_spawn(self, tmp_path):
        """Main may spawn operator more than once — resolve the LAST one via its
        tool_use id, matched to the subagent meta.json (toolUseId)."""
        main = tmp_path / "sess.jsonl"
        write_jsonl(
            main, [self.operator_spawn("tu_old"), self.operator_spawn("tu_new")]
        )
        subdir = tmp_path / "sess" / "subagents"
        subdir.mkdir(parents=True)
        self.write_meta(subdir, "OLD", "tu_old")
        self.write_meta(subdir, "NEW", "tu_new")
        assert find_operator_transcript(str(main)) == str(subdir / "agent-NEW.jsonl")

    def test_none_without_operator_spawn(self, tmp_path):
        main = tmp_path / "sess.jsonl"
        write_jsonl(main, [{"role": "assistant", "content": "no spawn here"}])
        assert find_operator_transcript(str(main)) is None


# ── strip_subagent_meta ──


class TestStripSubagentMeta:
    META = (
        "agentId: aaa (use SendMessage with to: 'aaa', summary: 's')\n"
        "<usage>subagent_tokens: 1\ntool_uses: 1\nduration_ms: 1</usage>"
    )

    def test_strips_trailing_meta(self):
        assert strip_subagent_meta(f"the region\n{self.META}") == "the region"

    def test_preserves_clean_text(self):
        assert strip_subagent_meta("just a region") == "just a region"

    def test_extract_advisor_output_strips_meta(self, tmp_path):
        """The Agent tool_result envelope must never reach region-history."""
        t = tmp_path / "t.jsonl"
        write_jsonl(t, agent_exchange(f"the region\n{self.META}"))
        assert extract_advisor_output(str(t)) == "the region"
