"""Tests for Claude SDK client functionality."""

import asyncio
import json
from unittest.mock import AsyncMock

import anyio
import pytest

from clawd_code_sdk import (
    APIError,
    AssistantMessage,
    AuthenticationError,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    InvalidRequestError,
    RateLimitError,
    ServerError,
    query,
)
from clawd_code_sdk.models.mcp import McpServerStatusEntry, McpStatusResponse


def create_mock_transport_with_messages(messages: list[dict]):
    """Create a mock transport that handles initialization and returns messages.

    Args:
        messages: List of message dicts to return after initialization
    """
    mock_transport = AsyncMock()
    mock_transport.connect = AsyncMock()
    mock_transport.close = AsyncMock()
    mock_transport.end_input = AsyncMock()

    # Track written messages to simulate control protocol responses
    written_messages: list[str] = []

    async def mock_write(data: str) -> None:
        written_messages.append(data)

    mock_transport.write = AsyncMock(side_effect=mock_write)

    async def mock_receive():
        # Wait for initialization request
        await asyncio.sleep(0.01)

        # Find and respond to initialization request
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
                            "response": {
                                "commands": [],
                                "outputStyle": "default",
                                "pid": 12345,
                            },
                        },
                    }
                    break
            except (json.JSONDecodeError, KeyError, AttributeError):
                pass

        # Yield all messages
        for message in messages:
            yield message

    mock_transport.read_messages = mock_receive
    return mock_transport


class TestQueryFunction:
    """Test the main query function."""

    def test_query_single_prompt(self):
        """Test query with a single prompt."""

        async def _test():
            test_messages = [
                {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "4"}],
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
            mock_transport = create_mock_transport_with_messages(test_messages)

            messages = []
            async for msg in query(prompt="What is 2+2?", transport=mock_transport):
                messages.append(msg)

            assert len(messages) == 2
            assert isinstance(messages[0], AssistantMessage)
            assert messages[0].content[0].text == "4"

        anyio.run(_test)

    def test_query_with_options(self):
        """Test query with various options."""

        async def _test():
            test_messages = [
                {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "Hello!"}],
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
            mock_transport = create_mock_transport_with_messages(test_messages)

            options = ClaudeAgentOptions(
                allowed_tools=["Read", "Write"],
                system_prompt="You are helpful",
                permission_mode="acceptEdits",
                max_turns=5,
            )

            messages = []
            async for msg in query(prompt="Hi", options=options, transport=mock_transport):
                messages.append(msg)

            assert len(messages) == 2
            assert isinstance(messages[0], AssistantMessage)
            assert messages[0].content[0].text == "Hello!"

        anyio.run(_test)

    def test_query_with_cwd(self):
        """Test query with custom working directory."""

        async def _test():
            test_messages = [
                {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "Done"}],
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
            mock_transport = create_mock_transport_with_messages(test_messages)

            options = ClaudeAgentOptions(cwd="/custom/path")
            messages = []
            async for msg in query(prompt="test", options=options, transport=mock_transport):
                messages.append(msg)

            assert len(messages) == 2
            assert isinstance(messages[0], AssistantMessage)
            assert messages[0].content[0].text == "Done"

        anyio.run(_test)


class TestAPIErrorRaising:
    """Test that API errors are raised as exceptions."""

    def test_invalid_request_error_raised(self):
        """Test that invalid_request errors are raised as InvalidRequestError."""

        async def _test():
            error_message = {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": "API Error: The provided model identifier is invalid.",
                        }
                    ],
                    "model": "claude-invalid-model",
                    "error": "invalid_request",
                },
            }
            mock_transport = create_mock_transport_with_messages([error_message])

            with pytest.raises(InvalidRequestError) as exc_info:
                async for _ in query(prompt="test", transport=mock_transport):
                    pass

            assert exc_info.value.error_type == "invalid_request"
            assert exc_info.value.model == "claude-invalid-model"
            assert "model identifier" in str(exc_info.value).lower()

        anyio.run(_test)

    def test_rate_limit_error_raised(self):
        """Test that rate_limit errors are raised as RateLimitError."""

        async def _test():
            error_message = {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": "API Error: Rate limit exceeded",
                        }
                    ],
                    "model": "claude-sonnet-4-5-20250514",
                    "error": "rate_limit",
                },
            }
            mock_transport = create_mock_transport_with_messages([error_message])

            with pytest.raises(RateLimitError) as exc_info:
                async for _ in query(prompt="test", transport=mock_transport):
                    pass

            assert exc_info.value.error_type == "rate_limit"

        anyio.run(_test)

    def test_authentication_error_raised(self):
        """Test that authentication_failed errors are raised as AuthenticationError."""

        async def _test():
            error_message = {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "API Error: Invalid API key"}],
                    "model": "claude-sonnet-4-5-20250514",
                    "error": "authentication_failed",
                },
            }
            mock_transport = create_mock_transport_with_messages([error_message])

            with pytest.raises(AuthenticationError) as exc_info:
                async for _ in query(prompt="test", transport=mock_transport):
                    pass

            assert exc_info.value.error_type == "authentication_failed"

        anyio.run(_test)

    def test_server_error_raised(self):
        """Test that server_error errors are raised as ServerError (529 Overloaded)."""

        async def _test():
            error_message = {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": "API Error: Repeated 529 Overloaded errors",
                        }
                    ],
                    "model": "claude-sonnet-4-5-20250514",
                    "error": "server_error",
                },
            }
            mock_transport = create_mock_transport_with_messages([error_message])

            with pytest.raises(ServerError) as exc_info:
                async for _ in query(prompt="test", transport=mock_transport):
                    pass

            assert exc_info.value.error_type == "server_error"

        anyio.run(_test)

    def test_unknown_error_raised_as_base(self):
        """Test that unknown error types are raised as base APIError."""

        async def _test():
            error_message = {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Unknown error"}],
                    "model": "claude-sonnet-4-5-20250514",
                    "error": "unknown",
                },
            }
            mock_transport = create_mock_transport_with_messages([error_message])

            with pytest.raises(APIError) as exc_info:
                async for _ in query(prompt="test", transport=mock_transport):
                    pass

            assert exc_info.value.error_type == "unknown"

        anyio.run(_test)

    def test_messages_without_error_pass_through(self):
        """Test that normal messages without errors are yielded normally."""

        async def _test():
            test_messages = [
                {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "Hello!"}],
                        "model": "claude-sonnet-4-5-20250514",
                    },
                },
                {
                    "type": "result",
                    "uuid": "msg-002",
                    "subtype": "success",
                    "duration_ms": 1000,
                    "duration_api_ms": 800,
                    "is_error": False,
                    "num_turns": 1,
                    "session_id": "test-session",
                    "total_cost_usd": 0.001,
                },
            ]
            mock_transport = create_mock_transport_with_messages(test_messages)

            messages = []
            async for msg in query(prompt="test", transport=mock_transport):
                messages.append(msg)

            assert len(messages) == 2
            assert isinstance(messages[0], AssistantMessage)
            assert messages[0].content[0].text == "Hello!"

        anyio.run(_test)


def _create_control_protocol_transport(
    control_responses: dict[str, dict],
) -> AsyncMock:
    """Create a mock transport that handles initialization and responds to control requests.

    Args:
        control_responses: Mapping of control request subtype to response payload.
            The "initialize" subtype is handled automatically.
    """
    mock_transport = AsyncMock()
    mock_transport.connect = AsyncMock()
    mock_transport.close = AsyncMock()
    mock_transport.end_input = AsyncMock()

    written_messages: list[str] = []

    async def mock_write(data: str) -> None:
        written_messages.append(data)

    mock_transport.write = AsyncMock(side_effect=mock_write)

    init_response = {
        "subtype": "success",
        "response": {
            "commands": [],
            "outputStyle": "default",
            "pid": 12345,
        },
    }
    all_responses = {"initialize": init_response, **control_responses}

    async def mock_receive():
        last_check = 0
        timeout_counter = 0
        while timeout_counter < 200:
            await asyncio.sleep(0.01)
            timeout_counter += 1

            for msg_str in written_messages[last_check:]:
                try:
                    msg = json.loads(msg_str.strip())
                    if msg.get("type") != "control_request":
                        continue
                    subtype = msg.get("request", {}).get("subtype")
                    if subtype in all_responses:
                        yield {
                            "type": "control_response",
                            "response": {
                                "request_id": msg.get("request_id"),
                                **all_responses[subtype],
                            },
                        }
                except (json.JSONDecodeError, KeyError, AttributeError):
                    pass
            last_check = len(written_messages)

    mock_transport.read_messages = mock_receive
    return mock_transport


class TestGetMcpStatus:
    """Test get_mcp_status returns validated McpStatusResponse."""

    def test_get_mcp_status_parses_response(self):
        """Test that get_mcp_status returns a validated McpStatusResponse."""

        async def _test():
            mcp_status_payload = {
                "subtype": "success",
                "response": {
                    "mcpServers": [
                        {
                            "name": "git",
                            "status": "connected",
                            "serverInfo": {"name": "mcp-git", "version": "1.26.0"},
                            "config": {
                                "type": "stdio",
                                "command": "uvx",
                                "args": ["mcp-server-git"],
                            },
                            "scope": "dynamic",
                            "tools": [
                                {"name": "git_status", "annotations": {}},
                                {"name": "git_log", "annotations": {}},
                            ],
                        }
                    ]
                },
            }
            mock_transport = _create_control_protocol_transport({"mcp_status": mcp_status_payload})

            client = ClaudeSDKClient(transport=mock_transport)
            await client.connect()
            try:
                status = await client.get_mcp_status()

                assert isinstance(status, McpStatusResponse)
                assert len(status.mcp_servers) == 1

                server = status.mcp_servers[0]
                assert isinstance(server, McpServerStatusEntry)
                assert server.name == "git"
                assert server.status == "connected"
                assert server.scope == "dynamic"
                assert server.server_info is not None
                assert server.server_info.name == "mcp-git"
                assert server.server_info.version == "1.26.0"
                assert server.config == {
                    "type": "stdio",
                    "command": "uvx",
                    "args": ["mcp-server-git"],
                }
                assert len(server.tools) == 2
                assert server.tools[0].name == "git_status"
                assert server.tools[1].name == "git_log"
            finally:
                await client.disconnect()

        anyio.run(_test)

    def test_get_mcp_status_empty_servers(self):
        """Test get_mcp_status with no MCP servers configured."""

        async def _test():
            mcp_status_payload = {
                "subtype": "success",
                "response": {"mcpServers": []},
            }
            mock_transport = _create_control_protocol_transport({"mcp_status": mcp_status_payload})

            client = ClaudeSDKClient(transport=mock_transport)
            await client.connect()
            try:
                status = await client.get_mcp_status()

                assert isinstance(status, McpStatusResponse)
                assert len(status.mcp_servers) == 0
            finally:
                await client.disconnect()

        anyio.run(_test)
