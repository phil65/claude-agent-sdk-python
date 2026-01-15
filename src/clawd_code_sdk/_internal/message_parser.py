"""Message parser for Claude Code SDK responses."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from .._errors import MessageParseError
from ..types import (
    AssistantMessage,
    ContentBlock,
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

logger = logging.getLogger(__name__)


def _parse_content_block(block: dict[str, Any]) -> ContentBlock:
    """Parse a content block from raw dict to typed model.

    Args:
        block: Raw content block dictionary

    Returns:
        Parsed ContentBlock

    Raises:
        MessageParseError: If block type is unknown or validation fails
    """
    block_type = block.get("type")
    try:
        match block_type:
            case "text":
                return TextBlock.model_validate(block)
            case "thinking":
                return ThinkingBlock.model_validate(block)
            case "tool_use":
                return ToolUseBlock.model_validate(block)
            case "tool_result":
                return ToolResultBlock.model_validate(block)
            case _:
                raise MessageParseError(
                    f"Unknown content block type: {block_type}", block
                )
    except ValidationError as e:
        raise MessageParseError(
            f"Validation failed for {block_type} block: {e}", block
        ) from e


def parse_message(data: dict[str, Any]) -> Message:
    """Parse message from CLI output into typed Message objects.

    Args:
        data: Raw message dictionary from CLI output

    Returns:
        Parsed Message object

    Raises:
        MessageParseError: If parsing fails or message type is unrecognized
    """
    if not isinstance(data, dict):
        raise MessageParseError(
            f"Invalid message data type (expected dict, got {type(data).__name__})",
            data,
        )

    message_type = data.get("type")
    if not message_type:
        raise MessageParseError("Message missing 'type' field", data)

    try:
        match message_type:
            case "user":
                message_data = data.get("message", {})
                raw_content = message_data.get("content")

                if isinstance(raw_content, list):
                    content: str | list[ContentBlock] = [
                        _parse_content_block(block) for block in raw_content
                    ]
                else:
                    content = raw_content

                return UserMessage.model_validate(
                    {
                        "content": content,
                        "uuid": data.get("uuid"),
                        "parent_tool_use_id": data.get("parent_tool_use_id"),
                    }
                )

            case "assistant":
                message_data = data.get("message", {})
                raw_content = message_data.get("content", [])

                content_blocks: list[ContentBlock] = [
                    _parse_content_block(block) for block in raw_content
                ]

                return AssistantMessage.model_validate(
                    {
                        "content": content_blocks,
                        "model": message_data["model"],
                        "parent_tool_use_id": data.get("parent_tool_use_id"),
                        "error": message_data.get("error"),
                    }
                )

            case "system":
                return SystemMessage.model_validate(
                    {
                        "subtype": data["subtype"],
                        "data": data,
                    }
                )

            case "result":
                return ResultMessage.model_validate(
                    {
                        "subtype": data["subtype"],
                        "duration_ms": data["duration_ms"],
                        "duration_api_ms": data["duration_api_ms"],
                        "is_error": data["is_error"],
                        "num_turns": data["num_turns"],
                        "session_id": data["session_id"],
                        "total_cost_usd": data.get("total_cost_usd"),
                        "usage": data.get("usage"),
                        "result": data.get("result"),
                        "structured_output": data.get("structured_output"),
                    }
                )

            case "stream_event":
                return StreamEvent.model_validate(
                    {
                        "uuid": data["uuid"],
                        "session_id": data["session_id"],
                        "event": data["event"],
                        "parent_tool_use_id": data.get("parent_tool_use_id"),
                    }
                )

            case _:
                raise MessageParseError(f"Unknown message type: {message_type}", data)

    except KeyError as e:
        raise MessageParseError(
            f"Missing required field in {message_type} message: {e}", data
        ) from e
    except ValidationError as e:
        raise MessageParseError(
            f"Validation failed for {message_type} message: {e}", data
        ) from e
