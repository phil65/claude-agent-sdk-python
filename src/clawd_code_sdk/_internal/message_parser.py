"""Message parser for Claude Code SDK responses."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import TypeAdapter

from clawd_code_sdk._errors import MessageParseError
from clawd_code_sdk.models import (
    AssistantMessage,
    CompactBoundarySystemMessage,
    HookResponseSystemMessage,
    HookStartedSystemMessage,
    ResultMessage,
    StatusSystemMessage,
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
    from clawd_code_sdk.models import ContentBlock, Message

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
    match data:
        case {"type": "user", "message": {"content": content}, **user_data}:
            content_ = [to_block(i) for i in content] if isinstance(content, list) else content
            return UserMessage(content=content_, **user_data)
        case {"type": "assistant", "message": message}:
            # Check for error at top level first, then inside message
            return AssistantMessage(
                content=[to_block(i) for i in message["content"]],
                model=message["model"],
                parent_tool_use_id=data.get("parent_tool_use_id"),
                error=data.get("error") or message.get("error"),
            )

        case {"type": "system", "subtype": "init", **system_data}:
            return SystemMessage(**system_data)
        case {"type": "system", "subtype": "hook_started", **system_data}:
            return HookStartedSystemMessage(**system_data)
        case {"type": "system", "subtype": "hook_response", **system_data}:
            return HookResponseSystemMessage(**system_data)
        case {"type": "system", "subtype": "compact_boundary", **compact_data}:
            return CompactBoundarySystemMessage(**compact_data)
        case {"type": "system", "subtype": "status", **compact_data}:
            return StatusSystemMessage(**compact_data)

        case {"type": "result", **result_data}:
            try:
                return ResultMessage(**result_data)
            except TypeError as e:
                msg = f"Missing required field in result message: {e}"
                raise MessageParseError(msg, data) from e
        case {"type": "stream_event", "event": event, **event_data}:
            from anthropic.types import RawMessageStreamEvent

            try:
                event = TypeAdapter(RawMessageStreamEvent).validate_python(event)
                return StreamEvent(event=event, **event_data)
            except TypeError as e:
                msg = f"Missing required field in stream_event message: {e}"
                raise MessageParseError(msg, data) from e
        # case {"type": "compact_boundary"}:
        case {"type": unknown_type}:
            raise MessageParseError(f"Unknown message type: {unknown_type}", data)
        case dict():
            raise MessageParseError("Message missing 'type' field", data)
        case _ as unknown_type:
            typ = type(unknown_type).__name__  # type: ignore[unreachable]
            raise MessageParseError(f"Invalid message data type: expected dict, got {typ}", data)


def to_block(data: dict[str, Any]) -> ContentBlock:
    match data:
        case {"type": "text", **text_data}:
            return TextBlock(**text_data)
        case {"type": "tool_use", **tool_use_data}:
            return ToolUseBlock(**tool_use_data)
        case {"type": "tool_result", "content": content, **tool_result_data}:
            result_content = _parse_tool_result_content(content)
            return ToolResultBlock(content=result_content, **tool_result_data)
        case {"type": "thinking", **thinking_data}:
            return ThinkingBlock(**thinking_data)
        case _:
            raise ValueError(f"Unknown block type: {data['type']}")
