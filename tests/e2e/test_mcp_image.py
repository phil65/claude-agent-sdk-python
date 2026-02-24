"""End-to-end test for MCP tool returning image content over the wire.

Tests whether image content blocks from an external MCP server
(FastMCP stdio) are correctly received through the Claude Code CLI.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import TYPE_CHECKING, Any

import pytest

from clawd_code_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    UserMessage,
)
from clawd_code_sdk.models.content_blocks import ToolResultBlock, ToolUseBlock


if TYPE_CHECKING:
    from clawd_code_sdk.models.messages import Message


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_mcp_image_tool_wire_format():
    """Test that image content from an MCP tool flows through the wire protocol.

    Configures Claude Code with a FastMCP stdio server that has a single tool
    returning a PNG image, then asks Claude to call it and inspects what
    content blocks come back.
    """
    mcp_server_path = str(Path(__file__).parent.parent / "tests" / "mcp_server.py")

    options = ClaudeAgentOptions(
        mcp_servers={
            "image_test": {
                "type": "stdio",
                "command": sys.executable,
                "args": [mcp_server_path],
            },
        },
        allowed_tools=["mcp__image_test__get_test_image"],
        permission_mode="bypassPermissions",
        allow_dangerously_skip_permissions=True,
        max_turns=3,
    )

    messages: list[Message] = []
    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            "Call the mcp__image_test__get_test_image tool and describe what you see."
        )
        async for message in client.receive_response():
            messages.append(message)

    # Verify we got a result
    result_messages = [m for m in messages if isinstance(m, ResultMessage)]
    assert result_messages, f"No ResultMessage. Got: {[type(m).__name__ for m in messages]}"
    assert not result_messages[0].is_error, f"Query error: {result_messages[0].errors}"

    # Inspect all content blocks from assistant and user messages
    all_content_blocks: list[dict[str, Any]] = []
    for msg in messages:
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                all_content_blocks.append(
                    {
                        "source": "assistant",
                        "type": block.type,
                        "block": block,
                    }
                )
        elif isinstance(msg, UserMessage) and isinstance(msg.content, list):
            for block in msg.content:
                all_content_blocks.append(
                    {
                        "source": "user",
                        "type": block.type,
                        "block": block,
                    }
                )

    # We expect at least a tool_use block (Claude calling the tool)
    tool_use_blocks = [b for b in all_content_blocks if b["type"] == "tool_use"]
    assert tool_use_blocks, "No tool_use blocks found - Claude didn't call the MCP tool"

    # Verify the tool_use targeted our MCP tool
    tool_use_block = tool_use_blocks[0]["block"]
    assert isinstance(tool_use_block, ToolUseBlock)
    assert tool_use_block.name == "mcp__image_test__get_test_image"

    # Find tool_result blocks and verify image content via get_parsed_content()
    tool_result_blocks = [b for b in all_content_blocks if b["type"] == "tool_result"]
    assert tool_result_blocks, "No tool_result blocks found"

    result_block = tool_result_blocks[0]["block"]
    assert isinstance(result_block, ToolResultBlock)
    assert isinstance(result_block.content, list), "Expected list content in tool result"

    # Parse into typed Anthropic SDK content blocks
    parsed = result_block.get_parsed_content()
    assert isinstance(parsed, list)
    assert len(parsed) >= 1

    # Find the image block in parsed content
    image_params = [b for b in parsed if isinstance(b, dict) and b.get("type") == "image"]
    assert image_params, f"No image block in parsed content: {[type(b).__name__ for b in parsed]}"

    image_param = image_params[0]
    # BetaImageBlockParam is a TypedDict with source.type, source.data, source.media_type
    assert image_param["type"] == "image"
    assert "source" in image_param
    assert image_param["source"]["type"] == "base64"
    assert image_param["source"]["media_type"] == "image/png"
    assert len(image_param["source"]["data"]) > 0, "Image data should not be empty"
