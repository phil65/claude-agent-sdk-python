"""Tests for message parser — content block dispatch, error extraction, error wrapping."""

from __future__ import annotations

import pytest

from clawd_code_sdk._errors import MessageParseError
from clawd_code_sdk._internal.message_parser import parse_message
from clawd_code_sdk.models import (
    AssistantMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from .conftest import make_beta_message


class TestContentBlockDispatch:
    """parse_message routes content blocks to the correct typed dataclasses."""

    def test_user_message_mixed_content(self):
        """All four content block types parse into their typed classes."""
        data = {
            "type": "user",
            "uuid": "u1",
            "session_id": "s1",
            "message": {
                "role": "user",
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
        assert isinstance(text, TextBlock)
        assert text.text == "intro"
        assert isinstance(tool_use, ToolUseBlock)
        assert tool_use.id == "t1"
        assert tool_use.name == "Read"
        assert tool_use.input == {"path": "/x"}
        assert isinstance(tool_result, ToolResultBlock)
        assert tool_result.tool_use_id == "t1"
        assert tool_result.content == "file contents"
        assert isinstance(tool_err, ToolResultBlock)
        assert tool_err.is_error is True

    def test_assistant_message_with_thinking(self):
        """Thinking blocks parse with signature preserved."""
        data = {
            "type": "assistant",
            "message": make_beta_message(
                content=[
                    {"type": "thinking", "thinking": "hmm...", "signature": "sig-abc"},
                    {"type": "text", "text": "answer"},
                ],
            ),
        }
        msg = parse_message(data)
        assert isinstance(msg, AssistantMessage)
        thinking, text = msg.content
        assert isinstance(thinking, ThinkingBlock)
        assert thinking.thinking == "hmm..."
        assert thinking.signature == "sig-abc"
        assert isinstance(text, TextBlock)
        assert text.text == "answer"

    def test_user_message_string_content(self):
        """String content is passed through without block parsing."""
        data = {
            "type": "user",
            "uuid": "u1",
            "session_id": "s1",
            "message": {"role": "user", "content": "plain text"},
        }
        msg = parse_message(data)
        assert isinstance(msg, UserMessage)
        assert msg.content == "plain text"


class TestAssistantErrorExtraction:
    """Error field is extracted from both top-level and nested message."""

    def test_error_from_message_level(self):
        data = {
            "type": "assistant",
            "message": make_beta_message(
                content=[{"type": "text", "text": "API Error: bad key"}],
                error="authentication_failed",
            ),
        }
        msg = parse_message(data)
        assert isinstance(msg, AssistantMessage)
        assert msg.error == "authentication_failed"

    def test_error_from_top_level(self):
        data = {
            "type": "assistant",
            "error": "rate_limit",
            "message": make_beta_message(
                content=[{"type": "text", "text": "Rate limited"}],
            ),
        }
        msg = parse_message(data)
        assert isinstance(msg, AssistantMessage)
        assert msg.error == "rate_limit"

    def test_no_error(self):
        data = {
            "type": "assistant",
            "message": make_beta_message(
                content=[{"type": "text", "text": "ok"}],
            ),
        }
        msg = parse_message(data)
        assert isinstance(msg, AssistantMessage)
        assert msg.error is None


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
