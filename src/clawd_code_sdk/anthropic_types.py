"""Anthropic SDK types for tool result content blocks.

This module re-exports BetaContentBlock from the Anthropic SDK as the
canonical union type for content blocks in tool results. BetaImageBlockParam
is included because image content in MCP tool results uses the input
(Param) type rather than an output block type.
"""

from __future__ import annotations

from anthropic.types.beta import BetaContentBlock, BetaImageBlockParam
from pydantic import TypeAdapter


# Union of content types that can appear in tool results.
# BetaContentBlock covers all server-side tool output blocks.
# BetaImageBlockParam covers image content from MCP tools (TypedDict, not a model).
ToolResultContentBlock = BetaContentBlock | BetaImageBlockParam

_tool_result_content_adapter: TypeAdapter[list[ToolResultContentBlock]] | None = None


def _get_adapter() -> TypeAdapter[list[ToolResultContentBlock]]:
    global _tool_result_content_adapter  # noqa: PLW0603
    if _tool_result_content_adapter is None:
        _tool_result_content_adapter = TypeAdapter(list[ToolResultContentBlock])
    return _tool_result_content_adapter


def validate_tool_result_content(content: list[dict[str, object]]) -> list[ToolResultContentBlock]:
    """Validate and parse raw tool result content into typed blocks.

    Args:
        content: Raw list of content block dictionaries from CLI output

    Returns:
        List of validated and typed content blocks
    """
    return _get_adapter().validate_python(content)
