"""Integration tests for Claude SDK.

These tests verify end-to-end functionality with mocked CLI responses.
"""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import anyio
import pytest

from clawd_code_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    CLINotFoundError,
    ResultMessage,
    query,
)
from clawd_code_sdk.models import ToolUseBlock


def create_mock_transport(messages: list[dict]):
    """Create a mock transport that handles initialization and returns messages."""
    mock_transport = AsyncMock()
    mock_transport.connect = AsyncMock()
    mock_transport.close = AsyncMock()
    mock_transport.end_input = AsyncMock()
    mock_transport.is_ready = Mock(return_value=True)

    written_messages: list[str] = []

    async def mock_write(data: str) -> None:
        written_messages.append(data)

    mock_transport.write = AsyncMock(side_effect=mock_write)

    async def mock_receive():
        await asyncio.sleep(0.01)
        for msg_str in written_messages:
            try:
                msg = json.loads(msg_str.strip())
                if (
                    msg.get("type") == "control_request"
                    and msg.get("request", {}).get("subtype") == "initialize"
                ):
                    yield {
                        "type": "control_response",
                        "response": {
                            "request_id": msg.get("request_id"),
                            "subtype": "success",
                            "commands": [],
                            "output_style": "default",
                        },
                    }
                    break
            except (json.JSONDecodeError, KeyError, AttributeError):
                pass

        for message in messages:
            yield message

    mock_transport.read_messages = mock_receive
    return mock_transport


class TestIntegration:
    """End-to-end integration tests."""

    def test_simple_query_response(self):
        """Test a simple query with text response."""

        async def _test():
            test_messages = [
                {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "2 + 2 equals 4"}],
                        "model": "claude-opus-4-1-20250805",
                    },
                },
                {
                    "type": "result",
                    "uuid": "msg-001",
                    "subtype": "success",
                    "duration_ms": 1000,
                    "duration_api_ms": 800,
                    "is_error": False,
                    "num_turns": 1,
                    "session_id": "test-session",
                    "total_cost_usd": 0.001,
                },
            ]
            mock_transport = create_mock_transport(test_messages)

            messages = []
            async for msg in query(prompt="What is 2 + 2?", transport=mock_transport):
                messages.append(msg)

            assert len(messages) == 2
            assert isinstance(messages[0], AssistantMessage)
            assert len(messages[0].content) == 1
            assert messages[0].content[0].text == "2 + 2 equals 4"
            assert isinstance(messages[1], ResultMessage)
            assert messages[1].total_cost_usd == 0.001
            assert messages[1].session_id == "test-session"

        anyio.run(_test)

    def test_query_with_tool_use(self):
        """Test query that uses tools."""

        async def _test():
            test_messages = [
                {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [
                            {"type": "text", "text": "Let me read that file for you."},
                            {
                                "type": "tool_use",
                                "id": "tool-123",
                                "name": "Read",
                                "input": {"file_path": "/test.txt"},
                            },
                        ],
                        "model": "claude-opus-4-1-20250805",
                    },
                },
                {
                    "type": "result",
                    "uuid": "msg-002",
                    "subtype": "success",
                    "duration_ms": 1500,
                    "duration_api_ms": 1200,
                    "is_error": False,
                    "num_turns": 1,
                    "session_id": "test-session-2",
                    "total_cost_usd": 0.002,
                },
            ]
            mock_transport = create_mock_transport(test_messages)

            messages = []
            async for msg in query(
                prompt="Read /test.txt",
                options=ClaudeAgentOptions(allowed_tools=["Read"]),
                transport=mock_transport,
            ):
                messages.append(msg)

            assert len(messages) == 2
            assert isinstance(messages[0], AssistantMessage)
            assert len(messages[0].content) == 2
            assert messages[0].content[0].text == "Let me read that file for you."
            assert isinstance(messages[0].content[1], ToolUseBlock)
            assert messages[0].content[1].name == "Read"
            assert messages[0].content[1].input["file_path"] == "/test.txt"

        anyio.run(_test)

    def test_cli_not_found(self):
        """Test handling when CLI is not found."""

        async def _test():
            with (
                patch("shutil.which", return_value=None),
                patch("pathlib.Path.exists", return_value=False),
                pytest.raises(CLINotFoundError) as exc_info,
            ):
                async for _ in query(prompt="test"):
                    pass

            assert "Claude Code not found" in str(exc_info.value)

        anyio.run(_test)

    def test_continuation_option(self):
        """Test query with continue_conversation option."""

        async def _test():
            test_messages = [
                {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [
                            {"type": "text", "text": "Continuing from previous conversation"}
                        ],
                        "model": "claude-opus-4-1-20250805",
                    },
                },
                {
                    "type": "result",
                    "uuid": "msg-003",
                    "subtype": "success",
                    "duration_ms": 500,
                    "duration_api_ms": 400,
                    "is_error": False,
                    "num_turns": 1,
                    "session_id": "test-session",
                    "total_cost_usd": 0.001,
                },
            ]
            mock_transport = create_mock_transport(test_messages)

            messages = []
            async for msg in query(
                prompt="Continue",
                options=ClaudeAgentOptions(continue_conversation=True),
                transport=mock_transport,
            ):
                messages.append(msg)

            assert len(messages) == 2
            assert isinstance(messages[0], AssistantMessage)
            assert messages[0].content[0].text == "Continuing from previous conversation"

        anyio.run(_test)

    def test_max_budget_usd_option(self):
        """Test query with max_budget_usd option."""

        async def _test():
            test_messages = [
                {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "Starting to read..."}],
                        "model": "claude-opus-4-1-20250805",
                    },
                },
                {
                    "type": "result",
                    "uuid": "msg-003",
                    "subtype": "error_max_budget_usd",
                    "duration_ms": 500,
                    "duration_api_ms": 400,
                    "is_error": False,
                    "num_turns": 1,
                    "session_id": "test-session-budget",
                    "total_cost_usd": 0.0002,
                    "usage": {
                        "input_tokens": 100,
                        "output_tokens": 50,
                    },
                },
            ]
            mock_transport = create_mock_transport(test_messages)

            messages = []
            async for msg in query(
                prompt="Read the readme",
                options=ClaudeAgentOptions(max_budget_usd=0.0001),
                transport=mock_transport,
            ):
                messages.append(msg)

            assert len(messages) == 2
            assert isinstance(messages[1], ResultMessage)
            assert messages[1].subtype == "error_max_budget_usd"
            assert messages[1].is_error is False
            assert messages[1].total_cost_usd == 0.0002
            assert messages[1].total_cost_usd > 0

        anyio.run(_test)
