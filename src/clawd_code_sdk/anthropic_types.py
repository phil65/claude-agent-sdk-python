"""Anthropic SDK types for tool result content blocks.

This module defines a discriminated union of all possible content types
that can appear in tool results from the Anthropic SDK. These types are
used to provide proper typing for ToolResultBlock.content.
"""

from __future__ import annotations

from typing import Annotated

from anthropic.types import (
    TextBlock,
    WebSearchResultBlock,
    WebSearchToolResultError,
)
from anthropic.types.beta import (
    BetaBashCodeExecutionResultBlock,
    BetaBashCodeExecutionToolResultError,
    BetaCodeExecutionResultBlock,
    BetaCodeExecutionToolResultError,
    BetaImageBlockParam,
    BetaTextEditorCodeExecutionCreateResultBlock,
    BetaTextEditorCodeExecutionStrReplaceResultBlock,
    BetaTextEditorCodeExecutionToolResultError,
    BetaTextEditorCodeExecutionViewResultBlock,
    BetaToolReferenceBlock,
    BetaToolSearchToolResultError,
    BetaToolSearchToolSearchResultBlock,
    BetaWebFetchBlock,
    BetaWebFetchToolResultErrorBlock,
)
from pydantic import Field, TypeAdapter

# Union of all possible content types that can appear in tool results.
# These are the inner content blocks, not the outer tool result wrapper.
# Discriminated by the "type" field.
#
# Type discriminator values:
# - "text" -> TextBlock
# - "image" -> BetaImageBlockParam (TypedDict, no Pydantic model exists)
# - "tool_reference" -> BetaToolReferenceBlock
# - "tool_search_tool_search_result" -> BetaToolSearchToolSearchResultBlock
# - "tool_search_tool_result_error" -> BetaToolSearchToolResultError
# - "web_search_result" -> WebSearchResultBlock
# - "web_search_tool_result_error" -> WebSearchToolResultError
# - "web_fetch_result" -> BetaWebFetchBlock
# - "web_fetch_tool_result_error" -> BetaWebFetchToolResultErrorBlock
# - "code_execution_result" -> BetaCodeExecutionResultBlock
# - "code_execution_tool_result_error" -> BetaCodeExecutionToolResultError
# - "bash_code_execution_result" -> BetaBashCodeExecutionResultBlock
# - "bash_code_execution_tool_result_error" -> BetaBashCodeExecutionToolResultError
# - "text_editor_code_execution_view_result" -> BetaTextEditorCodeExecutionViewResultBlock
# - "text_editor_code_execution_create_result" -> BetaTextEditorCodeExecutionCreateResultBlock
# - "text_editor_code_execution_str_replace_result" -> BetaTextEditorCodeExecutionStrReplaceResultBlock
# - "text_editor_code_execution_tool_result_error" -> BetaTextEditorCodeExecutionToolResultError
ToolResultContentBlock = Annotated[
    TextBlock
    | BetaImageBlockParam
    | BetaToolReferenceBlock
    | BetaToolSearchToolSearchResultBlock
    | BetaToolSearchToolResultError
    | WebSearchResultBlock
    | WebSearchToolResultError
    | BetaWebFetchBlock
    | BetaWebFetchToolResultErrorBlock
    | BetaCodeExecutionResultBlock
    | BetaCodeExecutionToolResultError
    | BetaBashCodeExecutionResultBlock
    | BetaBashCodeExecutionToolResultError
    | BetaTextEditorCodeExecutionViewResultBlock
    | BetaTextEditorCodeExecutionCreateResultBlock
    | BetaTextEditorCodeExecutionStrReplaceResultBlock
    | BetaTextEditorCodeExecutionToolResultError,
    Field(discriminator="type"),
]

# TypeAdapter for validating lists of tool result content blocks
tool_result_content_adapter: TypeAdapter[list[ToolResultContentBlock]] = TypeAdapter(
    list[ToolResultContentBlock]
)


def validate_tool_result_content(
    content: list[dict[str, object]],
) -> list[ToolResultContentBlock]:
    """Validate and parse raw tool result content into typed blocks.

    Args:
        content: Raw list of content block dictionaries from CLI output

    Returns:
        List of validated and typed content blocks
    """
    return tool_result_content_adapter.validate_python(content)
