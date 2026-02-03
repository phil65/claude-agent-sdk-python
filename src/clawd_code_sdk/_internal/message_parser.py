"""Message parser for Claude Code SDK responses."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from clawd_code_sdk._errors import MessageParseError
from clawd_code_sdk.types import (
    AssistantMessage,
    Message,
    ResultMessage,
    StreamEvent,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

if TYPE_CHECKING:
    from clawd_code_sdk.anthropic_types import ToolResultContentBlock

logger = logging.getLogger(__name__)


def _parse_tool_result_content(
    raw_content: str | list[dict[str, Any]] | None,
) -> str | list[ToolResultContentBlock] | None:
    """Parse and validate tool result content.

    Args:
        raw_content: Raw content from CLI (string, list of dicts, or None)

    Returns:
        Validated content (string, list of typed blocks, or None)
    """

    from clawd_code_sdk.anthropic_types import validate_tool_result_content

    if raw_content is None or isinstance(raw_content, str):
        return raw_content
    # Validate list content against Anthropic SDK types
    return validate_tool_result_content(raw_content)


def parse_message(data: dict[str, Any]) -> Message:
    """
    Parse message from CLI output into typed Message objects.

    Args:
        data: Raw message dictionary from CLI output

    Returns:
        Parsed Message object

    Raises:
        MessageParseError: If parsing fails or message type is unrecognized
    """
    match data.get("type"):
        case None:
            raise MessageParseError("Message missing 'type' field", data)
        case "user":
            parent_tool_use_id = data.get("parent_tool_use_id")
            tool_use_result = data.get("tool_use_result")
            uuid = data.get("uuid")
            try:
                if isinstance(data["message"]["content"], list):
                    blocks = [to_block(i) for i in data["message"]["content"]]
                    return UserMessage(
                        content=blocks,
                        uuid=uuid,
                        parent_tool_use_id=parent_tool_use_id,
                        tool_use_result=tool_use_result,
                    )
                return UserMessage(
                    content=data["message"]["content"],
                    uuid=uuid,
                    parent_tool_use_id=parent_tool_use_id,
                    tool_use_result=tool_use_result,
                )
            except KeyError as e:
                msg = f"Missing required field in user message: {e}"
                raise MessageParseError(msg, data) from e

        case "assistant":
            try:
                blocks = [to_block(i) for i in data["message"]["content"]]
                # Check for error at top level first, then inside message
                error = data.get("error") or data["message"].get("error")
                return AssistantMessage(
                    content=blocks,
                    model=data["message"]["model"],
                    parent_tool_use_id=data.get("parent_tool_use_id"),
                    error=error,
                )
            except KeyError as e:
                raise MessageParseError(
                    f"Missing required field in assistant message: {e}", data
                ) from e

        case "system":
            try:
                return SystemMessage(subtype=data["subtype"], data=data)
            except KeyError as e:
                msg = f"Missing required field in system message: {e}"
                raise MessageParseError(msg, data) from e

        case "result":
            try:
                return ResultMessage(
                    subtype=data["subtype"],
                    duration_ms=data["duration_ms"],
                    duration_api_ms=data["duration_api_ms"],
                    is_error=data["is_error"],
                    num_turns=data["num_turns"],
                    session_id=data["session_id"],
                    total_cost_usd=data.get("total_cost_usd"),
                    usage=data.get("usage"),
                    result=data.get("result"),
                    structured_output=data.get("structured_output"),
                    errors=data.get("errors"),
                )
            except KeyError as e:
                msg = f"Missing required field in result message: {e}"
                raise MessageParseError(msg, data) from e

        case "stream_event":
            try:
                return StreamEvent(
                    uuid=data["uuid"],
                    session_id=data["session_id"],
                    event=data["event"],
                    parent_tool_use_id=data.get("parent_tool_use_id"),
                )
            except KeyError as e:
                msg = f"Missing required field in stream_event message: {e}"
                raise MessageParseError(msg, data) from e

        case _ as unknown_type:
            raise MessageParseError(f"Unknown message type: {unknown_type}", data)


def to_block(
    data: dict[str, Any],
) -> TextBlock | ToolUseBlock | ToolResultBlock | ThinkingBlock:
    match data["type"]:
        case "text":
            return TextBlock(text=data["text"])
        case "tool_use":
            return ToolUseBlock(id=data["id"], name=data["name"], input=data["input"])

        case "tool_result":
            return ToolResultBlock(
                tool_use_id=data["tool_use_id"],
                content=_parse_tool_result_content(data.get("content")),
                is_error=data.get("is_error"),
            )
        case "thinking":
            return ThinkingBlock(thinking=data["thinking"], signature=data["signature"])
        case _:
            raise ValueError(f"Unknown block type: {data['type']}")
