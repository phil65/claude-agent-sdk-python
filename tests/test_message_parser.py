"""Tests for message parser — content block dispatch, error extraction, error wrapping."""

from __future__ import annotations

import pytest

from clawd_code_sdk._errors import MessageParseError
from clawd_code_sdk._internal.message_parser import parse_message
from clawd_code_sdk.models import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)


class TestContentBlockDispatch:
    """parse_message routes content blocks to the correct typed dataclasses."""

    def test_user_message_mixed_content(self):
        """All four content block types parse into their typed classes."""
        data = {
            "type": "user",
            "uuid": "u1",
            "session_id": "s1",
            "message": {
                "content": [
                    {"type": "text", "text": "intro"},
                    {"type": "tool_use", "id": "t1", "name": "Read", "input": {"path": "/x"}},
                    {"type": "tool_result", "tool_use_id": "t1", "content": "file contents"},
                    {
                        "type": "tool_result",
                        "tool_use_id": "t2",
                        "content": "not found",
                        "is_error": True,
                    },
                ],
            },
        }
        msg = parse_message(data)
        assert isinstance(msg, UserMessage)
        text, tool_use, tool_result, tool_err = msg.content
        assert isinstance(text, TextBlock) and text.text == "intro"
        assert isinstance(tool_use, ToolUseBlock)
        assert tool_use.id == "t1" and tool_use.name == "Read"
        assert tool_use.input == {"path": "/x"}
        assert isinstance(tool_result, ToolResultBlock)
        assert tool_result.tool_use_id == "t1" and tool_result.content == "file contents"
        assert isinstance(tool_err, ToolResultBlock)
        assert tool_err.is_error is True

    def test_assistant_message_with_thinking(self):
        """Thinking blocks parse with signature preserved."""
        data = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "thinking", "thinking": "hmm...", "signature": "sig-abc"},
                    {"type": "text", "text": "answer"},
                ],
                "model": "claude-opus-4-1-20250805",
            },
        }
        msg = parse_message(data)
        assert isinstance(msg, AssistantMessage)
        thinking, text = msg.content
        assert isinstance(thinking, ThinkingBlock)
        assert thinking.thinking == "hmm..." and thinking.signature == "sig-abc"
        assert isinstance(text, TextBlock) and text.text == "answer"

    def test_user_message_string_content(self):
        """String content is passed through without block parsing."""
        data = {
            "type": "user",
            "uuid": "u1",
            "session_id": "s1",
            "message": {"content": "plain text"},
        }
        msg = parse_message(data)
        assert isinstance(msg, UserMessage) and msg.content == "plain text"


class TestParentToolUseId:
    """parent_tool_use_id is forwarded for subagent messages."""

    def test_user_message(self):
        data = {
            "type": "user",
            "uuid": "u1",
            "session_id": "s1",
            "message": {"content": [{"type": "text", "text": "hi"}]},
            "parent_tool_use_id": "toolu_abc",
        }
        msg = parse_message(data)
        assert isinstance(msg, UserMessage) and msg.parent_tool_use_id == "toolu_abc"

    def test_assistant_message(self):
        data = {
            "type": "assistant",
            "message": {
                "content": [{"type": "text", "text": "hi"}],
                "model": "claude-opus-4-1-20250805",
            },
            "parent_tool_use_id": "toolu_xyz",
        }
        msg = parse_message(data)
        assert isinstance(msg, AssistantMessage) and msg.parent_tool_use_id == "toolu_xyz"


class TestAssistantErrorExtraction:
    """Error field is extracted from both top-level and nested message."""

    def test_error_from_message_level(self):
        data = {
            "type": "assistant",
            "message": {
                "content": [{"type": "text", "text": "API Error: bad key"}],
                "model": "claude-opus-4-1-20250805",
                "error": "authentication_failed",
            },
        }
        msg = parse_message(data)
        assert isinstance(msg, AssistantMessage) and msg.error == "authentication_failed"

    def test_error_from_top_level(self):
        data = {
            "type": "assistant",
            "error": "rate_limit",
            "message": {
                "content": [{"type": "text", "text": "Rate limited"}],
                "model": "claude-opus-4-1-20250805",
            },
        }
        msg = parse_message(data)
        assert isinstance(msg, AssistantMessage) and msg.error == "rate_limit"

    def test_no_error(self):
        data = {
            "type": "assistant",
            "message": {
                "content": [{"type": "text", "text": "ok"}],
                "model": "claude-opus-4-1-20250805",
            },
        }
        msg = parse_message(data)
        assert isinstance(msg, AssistantMessage) and msg.error is None


class TestResultMessage:
    """ResultMessage parses with all required fields."""

    def test_round_trip(self):
        data = {
            "type": "result",
            "uuid": "r1",
            "session_id": "s1",
            "subtype": "success",
            "duration_ms": 1000,
            "duration_api_ms": 500,
            "is_error": False,
            "num_turns": 2,
            "total_cost_usd": 0.003,
            "usage": {
                "input_tokens": 200,
                "output_tokens": 80,
                "cache_creation_input_tokens": 1000,
                "cache_read_input_tokens": 500,
            },
        }
        msg = parse_message(data)
        assert isinstance(msg, ResultMessage)
        assert msg.subtype == "success" and msg.num_turns == 2
        assert msg.usage["input_tokens"] == 200
        assert msg.total_cost_usd == 0.003


class TestErrorWrapping:
    """parse_message wraps errors as MessageParseError with original data."""

    def test_non_dict_input(self):
        with pytest.raises(MessageParseError, match="Invalid message data type"):
            parse_message("not a dict")  # type: ignore[arg-type]

    def test_missing_type_field(self):
        with pytest.raises(MessageParseError, match="missing 'type' field"):
            parse_message({"message": {"content": []}})

    def test_unknown_message_type(self):
        with pytest.raises(MessageParseError, match="Unknown message type"):
            parse_message({"type": "banana"})

    def test_error_preserves_original_data(self):
        data = {"type": "banana", "extra": 42}
        with pytest.raises(MessageParseError) as exc_info:
            parse_message(data)
        assert exc_info.value.data == data

    def test_result_missing_required_fields(self):
        with pytest.raises(MessageParseError, match="Missing required field"):
            parse_message({"type": "result", "subtype": "success"})
