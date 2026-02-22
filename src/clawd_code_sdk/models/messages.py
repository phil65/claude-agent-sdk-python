"""Content blocks, message types, and stream events."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import TYPE_CHECKING, Annotated, Any, Literal, NotRequired, TypedDict

from pydantic import Discriminator, TypeAdapter

from clawd_code_sdk._errors import (
    APIError,
    AuthenticationError,
    BillingError,
    InvalidRequestError,
    RateLimitError,
    ServerError,
)
from clawd_code_sdk.models.content_blocks import ContentBlock, TextBlock  # noqa: TC001

from .base import ApiKeySource, PermissionMode, StopReason  # noqa: TC001


if TYPE_CHECKING:
    from collections.abc import Sequence

    from anthropic.types import RawMessageStreamEvent

    from clawd_code_sdk.models import ToolInput


# Message types
AssistantMessageError = Literal[
    "authentication_failed",
    "billing_error",
    "rate_limit",
    "invalid_request",
    "server_error",
    "unknown",
]


class UserPromptMessageContent(TypedDict):
    """Inner message content for a user prompt."""

    role: Literal["user"]
    """Message role, always 'user'."""
    content: str
    """The text content of the message."""


class UserPromptMessage(TypedDict):
    """A user prompt message sent over the wire to the Claude Code CLI.

    Used as the element type for streaming prompt iterables.
    """

    type: Literal["user"]
    """Message type, always 'user'."""
    message: UserPromptMessageContent
    """The message content."""
    parent_tool_use_id: NotRequired[str | None]
    """Optional parent tool use ID for tool result responses."""
    session_id: NotRequired[str]
    """Session identifier. Auto-injected if not provided."""


@dataclass(kw_only=True)
class BaseMessage:
    uuid: str
    session_id: str


@dataclass(kw_only=True)
class UserMessage(BaseMessage):
    """User message."""

    type: Literal["user"] = "user"
    content: str | Sequence[ContentBlock]
    parent_tool_use_id: str | None = None
    tool_use_result: list[dict[str, Any]] | dict[str, Any] | str | None = None
    isReplay: bool | None = None  # noqa: N815
    isSynthetic: bool | None = None  # noqa: N815

    def parse_command_output(self) -> str | None:
        content = self.content if isinstance(self.content, str) else ""
        # Extract content from <local-command-stdout> or <local-command-stderr>
        pattern = r"<local-command-(?:stdout|stderr)>(.*?)</local-command-(?:stdout|stderr)>"
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1) if match else None


@dataclass(kw_only=True)
class AssistantMessage:
    """Assistant message with content blocks."""

    type: Literal["assistant"] = "assistant"
    content: Sequence[ContentBlock]
    model: str
    parent_tool_use_id: str | None = None
    error: AssistantMessageError | None = None
    session_id: str | None = None  # not sure these two are needed.
    uuid: str | None = None

    def raise_if_api_error(self) -> None:
        """Raise the appropriate API exception if error is set.

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
        if self.error is None:
            return
        error_message = next(
            (block.text for block in self.content if isinstance(block, TextBlock)),
            "An API error occurred",
        )
        match self.error:
            case "authentication_failed":
                raise AuthenticationError(error_message, self.model)
            case "billing_error":
                raise BillingError(error_message, self.model)
            case "rate_limit":
                raise RateLimitError(error_message, self.model)
            case "invalid_request":
                raise InvalidRequestError(error_message, self.model)
            case "server_error":
                raise ServerError(error_message, self.model)
            case _ as unknown:
                # Handle "unknown" or any future error types
                raise APIError(error_message, unknown, self.model)


@dataclass(kw_only=True)
class McpServerStatus:
    name: str
    status: str


@dataclass(kw_only=True)
class Plugin:
    name: str
    path: str


@dataclass(kw_only=True)
class SystemMessage(BaseMessage):
    """System message with metadata."""

    type: Literal["system"] = "system"
    subtype: Literal["init"] = "init"
    apiKeySource: ApiKeySource | None = None  # noqa: N815
    cwd: str
    tools: list[str]
    mcp_servers: list[McpServerStatus]
    model: str
    permissionMode: PermissionMode  # noqa: N815
    slash_commands: list[str]
    output_style: Literal["default", "json"]
    claude_code_version: str
    agents: list[str]
    skills: list[str]
    plugins: list[Plugin]
    fast_mode_state: bool


@dataclass(kw_only=True)
class HookStartedSystemMessage(BaseMessage):
    """System message with metadata."""

    type: Literal["system"] = "system"
    subtype: Literal["hook_started"] = "hook_started"
    hook_id: str | None = None
    hook_name: str | None = None
    hook_event: str | None = None


@dataclass(kw_only=True)
class StatusSystemMessage(BaseMessage):
    """System status message."""

    type: Literal["system"] = "system"
    subtype: Literal["status"] = "status"
    status: Literal["compacting"] | str | None


class TriggerMetadata(TypedDict):
    trigger: Literal["auto", "manual"]
    pre_tokens: int


@dataclass(kw_only=True)
class CompactBoundarySystemMessage(BaseMessage):
    """System message with metadata."""

    type: Literal["system"] = "system"
    subtype: Literal["compact_boundary"] = "compact_boundary"
    compact_metadata: TriggerMetadata


class RateLimitInfo(TypedDict):
    status: Literal["allowed", "rejected"]
    resetsAt: int
    rateLimitType: Literal["five_hour", "twenty_four_hour"]
    overageStatus: Literal["allowed", "rejected"]
    overageDisabledReason: Literal["org_level_disabled", "user_level_disabled"]
    isUsingOverage: bool


@dataclass(kw_only=True)
class RateLimitMessage(BaseMessage):
    """Rate limit event message."""

    type: Literal["rate_limit_event"] = "rate_limit_event"
    subtype: Literal["rate_limit"] = "rate_limit"
    rate_limit_info: RateLimitInfo


@dataclass(kw_only=True)
class TaskStartedSystemMessage(BaseMessage):
    """System message emitted when a subagent task starts."""

    type: Literal["system"] = "system"
    subtype: Literal["task_started"] = "task_started"
    task_id: str = ""
    tool_use_id: str | None = None
    description: str = ""
    task_type: str | None = None


@dataclass(kw_only=True)
class TaskNotificationSystemMessage(BaseMessage):
    """System message emitted when a subagent task completes, fails, or stops."""

    type: Literal["system"] = "system"
    subtype: Literal["task_notification"] = "task_notification"
    task_id: str = ""
    status: Literal["completed", "failed", "stopped"] = "completed"
    output_file: str = ""
    summary: str = ""
    tool_use_id: str | None = None


class FilePersistedEntry(TypedDict):
    """A single file that was persisted."""

    filename: str
    file_id: str


class FilePersistedFailure(TypedDict):
    """A file that failed to persist."""

    filename: str
    error: str


@dataclass(kw_only=True)
class FilesPersistedSystemMessage(BaseMessage):
    """System message emitted when files have been persisted."""

    type: Literal["system"] = "system"
    subtype: Literal["files_persisted"] = "files_persisted"
    files: list[FilePersistedEntry] | None = None
    failed: list[FilePersistedFailure] | None = None
    processed_at: str = ""
    uuid: str = ""
    session_id: str = ""


@dataclass(kw_only=True)
class HookProgressSystemMessage(BaseMessage):
    """Progress update from a running hook."""

    type: Literal["system"] = "system"
    subtype: Literal["hook_progress"] = "hook_progress"
    hook_id: str = ""
    hook_name: str = ""
    hook_event: str = ""
    stdout: str = ""
    stderr: str = ""
    output: str = ""


@dataclass(kw_only=True)
class HookResponseSystemMessage(BaseMessage):
    """System message with metadata."""

    type: Literal["system"] = "system"
    subtype: Literal["hook_response"] = "hook_response"
    hook_id: str
    hook_name: str
    hook_event: str
    outcome: Literal["success", "failure"]  # need to verify
    exit_code: int
    stderr: str
    stdout: str
    output: str


class CacheCreation(TypedDict):
    ephemeral_1h_input_tokens: int
    ephemeral_5m_input_tokens: int


class ServerToolUse(TypedDict):
    web_search_requests: int
    web_fetch_requests: int
    service_tier: Literal["standard", "priority"]
    cache_creation: CacheCreation
    inference_geo: Literal["not_available"] | str
    iterations: list[Any]
    speed: str


class ModelUsage(TypedDict):
    inputTokens: int
    outputTokens: int
    cacheReadInputTokens: int
    cacheCreationInputTokens: int
    webSearchRequests: int
    costUSD: float
    contextWindow: int
    maxOutputTokens: int
    server_tool_use: ServerToolUse


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


@dataclass(kw_only=True)
class ResultMessage(BaseMessage):
    """Result message with cost and usage information."""

    type: Literal["result"] = "result"
    subtype: str
    duration_ms: int
    duration_api_ms: int
    is_error: bool
    num_turns: int
    total_cost_usd: float | None = None
    usage: Usage | None = None
    result: str | None = None
    structured_output: Any = None
    errors: list[str] | None = None
    stop_reason: StopReason | None = None
    modelUsage: dict[str, ModelUsage] | None = None  # noqa: N815
    permission_denials: list[SDKPermissionDenial] | None = None


@dataclass(kw_only=True)
class StreamEvent(BaseMessage):
    """Stream event for partial message updates during streaming."""

    type: Literal["stream_event"] = "stream_event"
    event: RawMessageStreamEvent
    parent_tool_use_id: str | None = None


@dataclass(kw_only=True)
class ToolProgressMessage(BaseMessage):
    """Progress update for a running tool."""

    type: Literal["tool_progress"] = "tool_progress"
    tool_use_id: str = ""
    tool_name: str = ""
    parent_tool_use_id: str | None = None
    elapsed_time_seconds: float = 0.0


@dataclass(kw_only=True)
class ToolUseSummaryMessage(BaseMessage):
    """Summary of preceding tool uses."""

    type: Literal["tool_use_summary"] = "tool_use_summary"
    summary: str = ""
    preceding_tool_use_ids: list[str] | None = None


@dataclass(kw_only=True)
class AuthStatusMessage(BaseMessage):
    """Authentication status update."""

    type: Literal["auth_status"] = "auth_status"
    isAuthenticating: bool = False  # noqa: N815
    output: list[str] | None = None
    error: str | None = None


SystemMessageUnion = Annotated[
    SystemMessage
    | HookStartedSystemMessage
    | StatusSystemMessage
    | CompactBoundarySystemMessage
    | HookProgressSystemMessage
    | HookResponseSystemMessage
    | TaskStartedSystemMessage
    | TaskNotificationSystemMessage
    | FilesPersistedSystemMessage,
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
    | RateLimitMessage
    | HookStartedSystemMessage
    | HookProgressSystemMessage
    | HookResponseSystemMessage
    | CompactBoundarySystemMessage
    | StatusSystemMessage
    | TaskStartedSystemMessage
    | TaskNotificationSystemMessage
    | FilesPersistedSystemMessage
    | ToolProgressMessage
    | ToolUseSummaryMessage
    | AuthStatusMessage
)
