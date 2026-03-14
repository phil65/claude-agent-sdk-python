"""E2E tests for SDK MCP resource support (in-process servers).

Tests whether MCP resources registered on SDK servers can be listed and read.
"""

from __future__ import annotations

import pytest

from clawd_code_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
)
from clawd_code_sdk.models import ToolUseBlock


@pytest.mark.e2e
@pytest.mark.skip(
    reason="CLI does not route ListMcpResources/ReadMcpResource to SDK servers yet. "
    "The SDK correctly advertises resources capability and routes resources/list + "
    "resources/read, but the CLI only sends tools/list and tools/call for SDK servers."
)
async def test_sdk_mcp_resource_list_and_read():
    """Test that resources on an SDK MCP server can be listed and read."""
    from mcp.server.fastmcp import FastMCP

    from clawd_code_sdk.models import McpSdkServerConfigWithInstance

    mcp = FastMCP("sdk_res_test")

    @mcp.resource("test://greeting")
    def get_greeting() -> str:
        return "Hello from SDK MCP resource!"

    @mcp.tool()
    def ping() -> str:
        """Simple ping tool."""
        return "pong"

    server_config = McpSdkServerConfigWithInstance(
        type="sdk", name="sdk_res", instance=mcp._mcp_server
    )

    options = ClaudeAgentOptions(
        mcp_servers={"sdk_res": server_config},
        permission_mode="bypassPermissions",
        allow_dangerously_skip_permissions=True,
        allowed_tools=["ListMcpResources", "ReadMcpResource", "mcp__sdk_res__ping"],
        max_turns=5,
        enable_tool_search=False,
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            "Use ListMcpResources to list resources, then ReadMcpResource "
            "to read 'test://greeting' from 'sdk_res'."
        )
        messages = [msg async for msg in client.receive_response()]

    result_messages = [m for m in messages if isinstance(m, ResultMessage)]
    assert result_messages
    assert not result_messages[0].is_error

    tool_uses = [
        block.name
        for msg in messages
        if isinstance(msg, AssistantMessage)
        for block in msg.content
        if isinstance(block, ToolUseBlock)
    ]
    resource_tools_used = [t for t in tool_uses if "Resource" in t]
    assert resource_tools_used, f"No resource tools used. Tools: {tool_uses}"


if __name__ == "__main__":
    pytest.main([__file__, "-vv", "-m", "e2e"])
