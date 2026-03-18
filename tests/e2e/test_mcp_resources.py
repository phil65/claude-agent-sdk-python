"""E2E tests for MCP resource support.

Tests whether MCP resources can be listed and read through external MCP servers.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

from clawd_code_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
)
from clawd_code_sdk.models import McpStdioServerConfig


@pytest.mark.e2e
async def test_external_mcp_resource_list_and_read():
    """Test that resources from an external MCP server can be listed and read."""
    mcp_server_path = str(Path(__file__).parent.parent / "mcp_server.py")

    options = ClaudeAgentOptions(
        mcp_servers={
            "res_test": McpStdioServerConfig(
                command=sys.executable,
                args=[mcp_server_path],
            ),
        },
        permission_mode="bypassPermissions",
        allow_dangerously_skip_permissions=True,
        allowed_tools=[
            "ListMcpResources",
            "ReadMcpResource",
        ],
        max_turns=5,
        enable_tool_search=False,
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            "First, use the ListMcpResources tool to list available MCP resources. "
            "Then use ReadMcpResource to read the 'test://greeting' resource from "
            "the 'res_test' server. Report what you find."
        )
        messages = [msg async for msg in client.receive_response()]

    # Check we got a result
    result_messages = [m for m in messages if isinstance(m, ResultMessage)]
    assert result_messages, f"No ResultMessage. Got: {[type(m).__name__ for m in messages]}"
    assert not result_messages[0].is_error

    # Look for evidence that resources were accessed
    all_text = []
    for msg in messages:
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if hasattr(block, "text"):
                    all_text.append(block.text)  # noqa: PERF401

    combined = " ".join(all_text).lower()
    assert "hello from mcp resource" in combined or "greeting" in combined, (
        f"Expected resource content in response. Got: {combined[:500]}"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-vv", "-m", "e2e"])
