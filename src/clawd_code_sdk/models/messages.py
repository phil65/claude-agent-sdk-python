"""Content blocks, message types, and stream events."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import TYPE_CHECKING, Any, Literal, TypedDict


if TYPE_CHECKING:
    from collections.abc import Sequence

    from anthropic.types import RawMessageStreamEvent

    from clawd_code_sdk.anthropic_types import ToolResultContentBlock
    from clawd_code_sdk.input_types import ToolInput

    from .base import ApiKeySource, PermissionMode, StopReason


# Content block types
@dataclass
class TextBlock:
    """Text content block."""

    text: str


@dataclass
class ThinkingBlock:
    """Thinking content block."""

    thinking: str
    signature: str


@dataclass
class ToolUseBlock:
    """Tool use content block."""

    id: str
    name: str
    input: dict[str, Any]
    caller: str | None = None


@dataclass
class ToolResultBlock:
    """Tool result content block."""

    tool_use_id: str
    content: str | list[ToolResultContentBlock] | None = None
    is_error: bool | None = None


ContentBlock = TextBlock | ThinkingBlock | ToolUseBlock | ToolResultBlock


# Message types
AssistantMessageError = Literal[
    "authentication_failed",
    "billing_error",
    "rate_limit",
    "invalid_request",
    "server_error",
    "unknown",
]


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
    apiKeySource: ApiKeySource  # noqa: N815
    cwd: str
    tools: list[str]
    mcp_servers: list[McpServerStatus]
    model: str
    permissionMode: PermissionMode  # noqa: N815
    slash_commands: list[str]
    output_style: str
    claude_code_version: str
    agents: dict[str, dict[str, Any]]
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
