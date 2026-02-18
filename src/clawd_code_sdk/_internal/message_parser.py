"""Message parser for Claude Code SDK responses."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import TypeAdapter

from clawd_code_sdk._errors import MessageParseError
from clawd_code_sdk.models import (
    AssistantMessage,
    ResultMessage,
    StreamEvent,
    UserMessage,
    parse_content_block,
    parse_system_message,
)
from clawd_code_sdk.models.messages import (
    AuthStatusMessage,
    RateLimitMessage,
    ToolProgressMessage,
    ToolUseSummaryMessage,
)


if TYPE_CHECKING:
    from clawd_code_sdk.models import Message

logger = logging.getLogger(__name__)


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
            content_ = (
                [parse_content_block(i) for i in content] if isinstance(content, list) else content
            )
            return UserMessage(content=content_, **user_data)
        case {"type": "assistant", "message": message}:
            # Check for error at top level first, then inside message
            return AssistantMessage(
                content=[parse_content_block(i) for i in message["content"]],
                model=message["model"],
                parent_tool_use_id=data.get("parent_tool_use_id"),
                error=data.get("error") or message.get("error"),
            )

        case {"type": "system", **system_data}:
            try:
                return parse_system_message(system_data)
            except Exception as e:
                raise MessageParseError(f"Failed to parse system message: {e}", data) from e

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
        case {"type": "rate_limit_event", **event_data}:
            try:
                return RateLimitMessage(**event_data)
            except TypeError as e:
                msg = f"Missing required field in result message: {e}"
                raise MessageParseError(msg, data) from e
        case {"type": "tool_progress", **progress_data}:
            return ToolProgressMessage(**progress_data)
        case {"type": "tool_use_summary", **summary_data}:
            return ToolUseSummaryMessage(**summary_data)
        case {"type": "auth_status", **auth_data}:
            # Convert camelCase isAuthenticating to snake_case
            if "isAuthenticating" in auth_data:
                auth_data["is_authenticating"] = auth_data.pop("isAuthenticating")
            return AuthStatusMessage(**auth_data)
        case {"type": unknown_type}:
            raise MessageParseError(f"Unknown message type: {unknown_type}", data)
        case dict():
            raise MessageParseError("Message missing 'type' field", data)
        case _ as unknown_type:
            typ = type(unknown_type).__name__  # type: ignore[unreachable]
            raise MessageParseError(f"Invalid message data type: expected dict, got {typ}", data)
