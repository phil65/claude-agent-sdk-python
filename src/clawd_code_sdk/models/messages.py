"""Content blocks, message types, and stream events."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import TYPE_CHECKING, Annotated, Any, Literal, TypedDict

from pydantic import Discriminator, TypeAdapter

from clawd_code_sdk._errors import (
    APIError,
    AuthenticationError,
    BillingError,
    InvalidRequestError,
    RateLimitError,
    ServerError,
)

from .base import ApiKeySource, PermissionMode, StopReason  # noqa: TC001


if TYPE_CHECKING:
    from collections.abc import Sequence

    from anthropic.types import RawMessageStreamEvent

    from clawd_code_sdk.anthropic_types import ToolResultContentBlock
    from clawd_code_sdk.input_types import ToolInput


# Message types
AssistantMessageError = Literal[
    "authentication_failed",
    "billing_error",
    "rate_limit",
    "invalid_request",
    "server_error",
    "unknown",
]


# Content block types
@dataclass
class TextBlock:
    """Text content block."""

    type: Literal["text"] = field(default="text", repr=False)
    text: str = ""


@dataclass
class ThinkingBlock:
    """Thinking content block."""

    type: Literal["thinking"] = field(default="thinking", repr=False)
    thinking: str = ""
    signature: str = ""


@dataclass
class ToolUseBlock:
    """Tool use content block."""

    type: Literal["tool_use"] = field(default="tool_use", repr=False)
    id: str = ""
    name: str = ""
    input: dict[str, Any] = field(default_factory=dict)
    caller: str | None = None


@dataclass
class ToolResultBlock:
    """Tool result content block."""

    type: Literal["tool_result"] = field(default="tool_result", repr=False)
    tool_use_id: str = ""
    content: str | list[dict[str, Any]] | None = None
    is_error: bool | None = None

    def get_parsed_content(self) -> list[ToolResultContentBlock] | str | None:
        from clawd_code_sdk.anthropic_types import validate_tool_result_content

        if self.content is None or isinstance(self.content, str):
            return self.content
        # Validate list content against Anthropic SDK types
        return validate_tool_result_content(self.content)


ContentBlock = Annotated[
    TextBlock | ThinkingBlock | ToolUseBlock | ToolResultBlock,
    Discriminator("type"),
]

_content_block_adapter: TypeAdapter[ContentBlock] = TypeAdapter(ContentBlock)


def parse_content_block(data: dict[str, Any]) -> ContentBlock:
    """Parse a raw dict into a typed ContentBlock dataclass."""
    return _content_block_adapter.validate_python(data)


@dataclass(kw_only=True)
class UserMessage:
    """User message."""

    content: str | Sequence[ContentBlock]
    uuid: str | None = None
    parent_tool_use_id: str | None = None
    tool_use_result: dict[str, Any] | None = None
    session_id: str
    isReplay: bool | None = None  # noqa: N815

    def parse_command_output(self) -> str | None:
        content = self.content if isinstance(self.content, str) else ""
        # Extract content from <local-command-stdout> or <local-command-stderr>
        pattern = r"<local-command-(?:stdout|stderr)>(.*?)</local-command-(?:stdout|stderr)>"
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1) if match else None


@dataclass(kw_only=True)
class AssistantMessage:
    """Assistant message with content blocks."""

    content: Sequence[ContentBlock]
    model: str
    parent_tool_use_id: str | None = None
    error: AssistantMessageError | None = None

    def raise_api_error(self) -> None:
        """Raise the appropriate API exception for an AssistantMessage with an error.

        This function converts the error field on an AssistantMessage into a proper
        Python exception that can be caught and handled programmatically.

        Args:
            message: The AssistantMessage with error field set.

        Raises:
            AuthenticationError: For authentication_failed errors (401).
            BillingError: For billing_error errors.
            RateLimitError: For rate_limit errors (429).
            InvalidRequestError: For invalid_request errors (400).
            ServerError: For server_error errors (500/529).
            APIError: For unknown error types.
        """
        error_type = self.error
        error_message = self._extract_error_message()
        model = self.model

        match error_type:
            case "authentication_failed":
                raise AuthenticationError(error_message, model)
            case "billing_error":
                raise BillingError(error_message, model)
            case "rate_limit":
                raise RateLimitError(error_message, model)
            case "invalid_request":
                raise InvalidRequestError(error_message, model)
            case "server_error":
                raise ServerError(error_message, model)
            case _:
                # Handle "unknown" or any future error types
                raise APIError(error_message, error_type or "unknown", model)

    def _extract_error_message(self) -> str:
        """Extract the error message text from an AssistantMessage.

        When the API returns an error, the error text is typically in the
        first TextBlock of the message content.

        Args:
            message: The AssistantMessage containing the error.

        Returns:
            The error message text, or a default message if none found.
        """
        return next(
            (block.text for block in self.content if isinstance(block, TextBlock)),
            "An API error occurred",
        )


@dataclass
class McpServerStatus:
    name: str
    status: str


@dataclass(kw_only=True)
class SystemMessage:
    """System message with metadata."""

    subtype: Literal["init"] = "init"
    uuid: str
    session_id: str
    apiKeySource: ApiKeySource | None = None  # noqa: N815
    cwd: str
    tools: list[str]
    mcp_servers: list[McpServerStatus]
    model: str
    permissionMode: PermissionMode  # noqa: N815
    slash_commands: list[str]
    output_style: str
    claude_code_version: str
    agents: list[str]
    skills: list[str]
    plugins: list[str]
    fast_mode_state: bool


@dataclass(kw_only=True)
class HookStartedSystemMessage:
    """System message with metadata."""

    subtype: Literal["hook_started"] = "hook_started"
    hook_id: str | None = None
    hook_name: str | None = None
    hook_event: str | None = None
    uuid: str
    session_id: str


@dataclass(kw_only=True)
class StatusSystemMessage:
    """System status message."""

    subtype: Literal["status"] = "status"
    status: Literal["compacting"] | str | None
    session_id: str
    uuid: str


class TriggerMetadata(TypedDict):
    trigger: Literal["auto", "manual"]
    pre_tokens: int


@dataclass(kw_only=True)
class CompactBoundarySystemMessage:
    """System message with metadata."""

    subtype: Literal["compact_boundary"] = "compact_boundary"
    compact_metadata: TriggerMetadata
    session_id: str
    uuid: str


@dataclass(kw_only=True)
class HookResponseSystemMessage:
    """System message with metadata."""

    subtype: Literal["hook_response"] = "hook_response"
    hook_id: str
    hook_name: str
    hook_event: str
    uuid: str
    session_id: str
    outcome: Literal["success", "failure"]  # need to verify
    exit_code: int
    stderr: str
    stdout: str
    output: str


class ModelUsage(TypedDict):
    inputTokens: int
    outputTokens: int
    cacheReadInputTokens: int


class SDKPermissionDenial(TypedDict):
    tool_name: str
    tool_use_id: str
    tool_input: ToolInput


class Usage(TypedDict):
    """Token usage from Claude API response."""

    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int


@dataclass
class ResultMessage:
    """Result message with cost and usage information."""

    subtype: str
    duration_ms: int
    duration_api_ms: int
    is_error: bool
    num_turns: int
    session_id: str
    uuid: str | None = None
    total_cost_usd: float | None = None
    usage: Usage | None = None
    result: str | None = None
    structured_output: Any = None
    errors: list[str] | None = None
    stop_reason: StopReason | None = None
    modelUsage: dict[str, ModelUsage] | None = None  # noqa: N815
    permission_denials: list[SDKPermissionDenial] | None = None


@dataclass
class StreamEvent:
    """Stream event for partial message updates during streaming."""

    uuid: str
    session_id: str
    event: RawMessageStreamEvent
    parent_tool_use_id: str | None = None


SystemMessageUnion = Annotated[
    SystemMessage
    | HookStartedSystemMessage
    | StatusSystemMessage
    | CompactBoundarySystemMessage
    | HookResponseSystemMessage,
    Discriminator("subtype"),
]

_system_message_adapter: TypeAdapter[SystemMessageUnion] = TypeAdapter(SystemMessageUnion)


def parse_system_message(data: dict[str, Any]) -> SystemMessageUnion:
    """Parse a raw dict into a typed system message dataclass."""
    return _system_message_adapter.validate_python(data)


Message = (
    UserMessage
    | AssistantMessage
    | SystemMessage
    | ResultMessage
    | StreamEvent
    | HookStartedSystemMessage
    | HookResponseSystemMessage
    | CompactBoundarySystemMessage
    | StatusSystemMessage
)
