"""MCP servers sent in the initialize request (`mcp_servers_delivery="initialize"`)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import anyio
import pytest

from clawd_code_sdk import ClaudeSDKClient
from clawd_code_sdk._errors import CLIConnectionError
from clawd_code_sdk._internal.transport import Transport
from clawd_code_sdk.models import ClaudeAgentOptions, McpStdioServerConfig


if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class _InitializeTransport(Transport):
    """Answers the initialize request with `answer` and records what was sent."""

    def __init__(self, answer: dict[str, Any]) -> None:
        self.answer = answer
        self.sent: list[dict[str, Any]] = []
        self._send, self._receive = anyio.create_memory_object_stream[dict[str, Any]](10)

    async def connect(self) -> None:
        pass

    async def write(self, data: str) -> None:
        message = json.loads(data)
        self.sent.append(message)
        if message.get("type") == "control_request":
            response = {"subtype": "success", "request_id": message["request_id"]}
            await self._send.send(
                {
                    "type": "control_response",
                    "response": response | {"response": self.answer},
                }
            )

    async def read_messages(self) -> AsyncIterator[dict[str, Any]]:
        async for message in self._receive:
            yield message

    async def close(self) -> None:
        self._send.close()

    async def end_input(self) -> None:
        pass


def _options() -> ClaudeAgentOptions:
    server = McpStdioServerConfig(command="/srv", env={"TOKEN": "s3cret"})
    return ClaudeAgentOptions(mcp_servers={"stdio": server})


async def test_servers_are_sent_and_must_be_applied() -> None:
    transport = _InitializeTransport({"mcp_servers_applied": True})
    client = ClaudeSDKClient(_options(), transport=transport)
    await client.connect()
    await client.disconnect()
    [initialize] = [m for m in transport.sent if m.get("type") == "control_request"]
    servers = initialize["request"]["mcpServers"]
    assert servers == {
        "stdio": {"type": "stdio", "command": "/srv", "args": [], "env": {"TOKEN": "s3cret"}}
    }


@pytest.mark.parametrize("answer", [{}, {"mcp_servers_applied": False}])
async def test_connecting_fails_when_the_cli_does_not_take_them(answer: dict[str, Any]) -> None:
    client = ClaudeSDKClient(_options(), transport=_InitializeTransport(answer))
    with pytest.raises(CLIConnectionError, match="mcp_servers_delivery"):
        await client.connect()
    await client.disconnect()


async def test_argv_delivery_sends_none_in_initialize() -> None:
    options = _options()
    options.mcp_servers_delivery = "argv"
    transport = _InitializeTransport({})
    client = ClaudeSDKClient(options, transport=transport)
    await client.connect()
    await client.disconnect()
    [initialize] = [m for m in transport.sent if m.get("type") == "control_request"]
    assert "mcpServers" not in initialize["request"]
