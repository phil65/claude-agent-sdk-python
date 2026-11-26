"""Tests for types and wire mappings added when syncing to @anthropic-ai/claude-agent-sdk 0.3.x."""

from typing import Any

import pytest

from clawd_code_sdk._internal.transport.subprocess_utils import to_cli_args
from clawd_code_sdk.models import (
    AssistantMessage,
    ClaudeAgentOptions,
    CommandsChangedMessage,
    ConversationResetMessage,
    InformationalSystemMessage,
    ModelRefusalFallbackMessage,
    NewSession,
    ResultSuccessMessage,
    ResumeSession,
    SdkPluginConfig,
    StatusSystemMessage,
    StreamEvent,
    ThinkingTokensMessage,
    UserMessage,
    message_adapter,
)
from clawd_code_sdk.models.thinking import ThinkingConfigAdaptive, ThinkingConfigDisabled


BASE = {"uuid": "u1", "session_id": "s1"}


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (
            {"type": "conversation_reset", "new_conversation_id": "c2", "trigger": "clear"},
            ConversationResetMessage,
        ),
        (
            {
                "type": "system",
                "subtype": "thinking_tokens",
                "estimated_tokens": 10,
                "estimated_tokens_delta": 2,
            },
            ThinkingTokensMessage,
        ),
        (
            {
                "type": "system",
                "subtype": "informational",
                "content": "hi",
                "level": "notice",
            },
            InformationalSystemMessage,
        ),
        (
            {
                "type": "system",
                "subtype": "commands_changed",
                "commands": [
                    {"name": "x", "description": "d", "argumentHint": "", "builtin": True}
                ],
            },
            CommandsChangedMessage,
        ),
        (
            {
                "type": "system",
                "subtype": "model_refusal_fallback",
                "trigger": "refusal",
                "direction": "retry",
                "original_model": "a",
                "fallback_model": "b",
                "request_id": None,
                "content": "c",
            },
            ModelRefusalFallbackMessage,
        ),
    ],
)
def test_new_message_types_parse(data: dict[str, Any], expected: type) -> None:
    assert isinstance(message_adapter.validate_python({**BASE, **data}), expected)


def test_assistant_message_new_fields() -> None:
    msg = message_adapter.validate_python({
        **BASE,
        "type": "assistant",
        "parent_tool_use_id": None,
        "request_id": "req_1",
        "user_message_uuid": "um1",
        "timestamp": "2026-01-01T00:00:00Z",
        "error": "overloaded",
        "message": {
            "id": "msg_1",
            "type": "message",
            "role": "assistant",
            "model": "claude-haiku-5-5",
            "content": [{"type": "text", "text": "hi"}],
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        },
    })
    assert isinstance(msg, AssistantMessage)
    assert msg.request_id == "req_1"
    assert msg.error == "overloaded"


def test_user_message_origin_variants() -> None:
    msg = message_adapter.validate_python({
        "type": "user",
        "message": {"role": "user", "content": "hi"},
        "parent_tool_use_id": None,
        "origin": {"kind": "observer", "from": "a", "senderTaskId": "t1"},
    })
    assert isinstance(msg, UserMessage)
    assert msg.origin is not None
    assert msg.origin.kind == "observer"


def test_result_message_new_fields() -> None:
    msg = message_adapter.validate_python({
        **BASE,
        "type": "result",
        "subtype": "success",
        "duration_ms": 1,
        "duration_api_ms": 1,
        "is_error": False,
        "num_turns": 1,
        "total_cost_usd": 0.0,
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": 1,
            "output_tokens": 1,
            "cache_creation": {"ephemeral_1h_input_tokens": 3, "ephemeral_5m_input_tokens": 0},
            "service_tier": "standard",
        },
        "terminal_reason": "turn_setup_failed",
        "user_message_uuids": ["a", "b"],
        "ttft_ms": 12.5,
    })
    assert isinstance(msg, ResultSuccessMessage)
    assert msg.user_message_uuids == ["a", "b"]
    assert msg.usage.cache_creation is not None
    assert msg.usage.cache_creation.ephemeral_1h_input_tokens == 3


def test_no_session_persistence_flag() -> None:
    args = to_cli_args(ClaudeAgentOptions(session=NewSession(persist=False)))
    assert "--no-session-persistence" in args
    assert "--no-persist-session" not in args


def test_resume_drops_turn_flag() -> None:
    session = ResumeSession(session_id="s", at_message="m1", drops_turn="u1")
    args = to_cli_args(ClaudeAgentOptions(session=session))
    assert "--resume-session-at=m1" in args
    assert "--resume-drops-turn=u1" in args


def test_thinking_flags() -> None:
    opts = ClaudeAgentOptions(thinking=ThinkingConfigAdaptive(display="omitted"))
    args = to_cli_args(opts)
    assert "--thinking=adaptive" in args
    assert args[args.index("--thinking-display") + 1] == "omitted"
    assert "--thinking=disabled" in to_cli_args(
        ClaudeAgentOptions(thinking=ThinkingConfigDisabled())
    )


def test_new_cli_option_flags() -> None:
    opts = ClaudeAgentOptions(
        permission_prompts="none",
        project_config_root="/repo",
        plugins=[SdkPluginConfig(path="/p", skip_mcp_discovery=True)],
    )
    args = to_cli_args(opts)
    assert args[args.index("--permission-prompts") + 1] == "none"
    assert "--project-config-root=/repo" in args
    assert args[args.index("--plugin-dir-no-mcp") + 1] == "/p"


def test_status_message_carries_user_message_uuids() -> None:
    """CLI 2.1.330 sends ``user_message_uuids`` on status (and init) messages."""
    data = {
        "type": "system",
        "subtype": "status",
        "status": "requesting",
        "user_message_uuids": ["m1"],
        **BASE,
    }
    message = message_adapter.validate_python(data)
    assert isinstance(message, StatusSystemMessage)
    assert message.user_message_uuids == ["m1"]


def test_stream_event_carries_owed_rows() -> None:
    """CLI 2.1.330 sends the internal ``owed_rows`` on stream events."""
    data = {
        "type": "stream_event",
        "event": {"type": "message_stop"},
        "parent_tool_use_id": None,
        "user_message_uuids": ["m1"],
        "owed_rows": [],
        **BASE,
    }
    message = message_adapter.validate_python(data)
    assert isinstance(message, StreamEvent)
    assert message.owed_rows == []


def test_result_carries_first_request_tokens() -> None:
    """CLI 2.1.330 reports the first model call's prompt size on success results."""
    data = {
        "type": "result",
        "subtype": "success",
        "duration_ms": 10,
        "duration_api_ms": 8,
        "is_error": False,
        "num_turns": 1,
        "result": "ok",
        "total_cost_usd": 0.0,
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 1, "output_tokens": 1, "service_tier": "standard"},
        "request_sent_wall_ms": 1795000000000,
        "first_request_input_tokens": 51568,
        "first_request_cache_read_input_tokens": 41324,
        **BASE,
    }
    message = message_adapter.validate_python(data)
    assert isinstance(message, ResultSuccessMessage)
    assert (message.first_request_input_tokens, message.first_request_cache_read_input_tokens) == (
        51568,
        41324,
    )
