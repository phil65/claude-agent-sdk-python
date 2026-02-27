"""Content blocks, message types, and stream events."""

from __future__ import annotations

from collections.abc import Sequence  # noqa: TC003
from dataclasses import dataclass
import re
from typing import TYPE_CHECKING, Annotated, Any, Literal, NotRequired, TypedDict

# from anthropic.types import MessageParam
from anthropic.types.model import Model  # noqa: TC002
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
from clawd_code_sdk.models.mcp import McpConnectionStatus  # noqa: TC001
from clawd_code_sdk.models.output_types import ToolUseResult  # noqa: TC001

from .base import (  # noqa: TC001
    ApiKeySource,
    CompactionTrigger,
    PermissionMode,
    StopReason,
    TaskStatus,
    ToolName,
)


if TYPE_CHECKING:
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

ErrorSubType = Literal[
    "error_during_execution",
    "error_max_turns",
    "error_max_budget_usd",
    "error_max_structured_output_retries",
]
Outcome = Literal["success", "error", "cancelled"]


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
    """Base class for messages."""

    uuid: str
    session_id: str


@dataclass(kw_only=True)
class BaseSystemMessage(BaseMessage):
    """Base class for all system messages."""

    type: Literal["system"] = "system"


@dataclass(kw_only=True)
class UserMessage(BaseMessage):
    """User message."""

    type: Literal["user"] = "user"
    content: str | Sequence[ContentBlock]
    parent_tool_use_id: str | None = None
    tool_use_result: (
        Sequence[ToolUseResult | dict[str, Any]] | ToolUseResult | dict[str, Any] | str | None
    ) = None
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
    model: Model | str
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
    """MCP server status."""

    name: str
    status: McpConnectionStatus


@dataclass(kw_only=True)
class Plugin:
    """Claude code plugin."""

    name: str
    path: str


@dataclass(kw_only=True)
class InitSystemMessage(BaseSystemMessage):
    """System init message with session metadata."""

    subtype: Literal["init"] = "init"
    apiKeySource: ApiKeySource | None  # noqa: N815
    cwd: str
    tools: list[str]
    mcp_servers: list[McpServerStatus]
    model: Model
    permissionMode: PermissionMode  # noqa: N815
    slash_commands: list[str]
    output_style: Literal["default", "json"] | str  # noqa: PYI051
    claude_code_version: str
    agents: list[str]
    skills: list[str]
    plugins: list[Plugin]
    fast_mode_state: bool


@dataclass(kw_only=True)
class HookStartedSystemMessage(BaseSystemMessage):
    """System message emitted when a hook starts."""

    subtype: Literal["hook_started"] = "hook_started"
    hook_id: str
    hook_name: str
    hook_event: str


@dataclass(kw_only=True)
class StatusSystemMessage(BaseSystemMessage):
    """System status message."""

    subtype: Literal["status"] = "status"
    status: Literal["compacting"] | None
    permissionMode: PermissionMode | None = None  # noqa: N815


class TriggerMetadata(TypedDict):
    """Trigger metadata."""

    trigger: CompactionTrigger
    pre_tokens: int


@dataclass(kw_only=True)
class CompactBoundarySystemMessage(BaseSystemMessage):
    """System message emitted at compaction boundaries."""

    subtype: Literal["compact_boundary"] = "compact_boundary"
    compact_metadata: TriggerMetadata


class RateLimitInfo(TypedDict):
    """Rate limit information."""

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
class TaskStartedSystemMessage(BaseSystemMessage):
    """System message emitted when a subagent task starts."""

    subtype: Literal["task_started"] = "task_started"
    task_id: str
    tool_use_id: str | None = None
    description: str
    task_type: str | None = None


@dataclass(kw_only=True)
class TaskNotificationSystemMessage(BaseSystemMessage):
    """System message emitted when a subagent task completes, fails, or stops."""

    subtype: Literal["task_notification"] = "task_notification"
    task_id: str
    status: TaskStatus
    output_file: str
    summary: str
    tool_use_id: str | None = None


class TaskProgressUsage(TypedDict):
    """Usage info for a task progress update."""

    total_tokens: int
    tool_uses: int
    duration_ms: int


@dataclass(kw_only=True)
class TaskProgressSystemMessage(BaseSystemMessage):
    """System message emitted periodically with task progress updates."""

    subtype: Literal["task_progress"] = "task_progress"
    task_id: str
    tool_use_id: str | None = None
    description: str
    usage: TaskProgressUsage
    last_tool_name: ToolName | str | None = None


class FilePersistedEntry(TypedDict):
    """A single file that was persisted."""

    filename: str
    file_id: str


class FilePersistedFailure(TypedDict):
    """A file that failed to persist."""

    filename: str
    error: str


@dataclass(kw_only=True)
class FilesPersistedSystemMessage(BaseSystemMessage):
    """System message emitted when files have been persisted."""

    subtype: Literal["files_persisted"] = "files_persisted"
    files: list[FilePersistedEntry]
    failed: list[FilePersistedFailure]
    processed_at: str


@dataclass(kw_only=True)
class HookProgressSystemMessage(BaseSystemMessage):
    """Progress update from a running hook."""

    subtype: Literal["hook_progress"] = "hook_progress"
    hook_id: str
    hook_name: str
    hook_event: str
    stdout: str
    stderr: str
    output: str


@dataclass(kw_only=True)
class HookResponseSystemMessage(BaseSystemMessage):
    """System message emitted when a hook completes."""

    subtype: Literal["hook_response"] = "hook_response"
    hook_id: str
    hook_name: str
    hook_event: str
    outcome: Outcome
    exit_code: int | None = None
    stderr: str
    stdout: str
    output: str


class ModelUsage(TypedDict):
    """Cumulative token usage per model, accumulated across the entire session."""

    inputTokens: int
    outputTokens: int
    cacheReadInputTokens: int
    cacheCreationInputTokens: int
    webSearchRequests: int
    costUSD: float
    contextWindow: int
    maxOutputTokens: int


class SDKPermissionDenial(TypedDict):
    """Permission denial from Claude API response."""

    tool_name: ToolName | str
    tool_use_id: str
    tool_input: ToolInput | dict[str, Any]


class Usage(TypedDict):
    """Token usage from the last API call only (per-turn, not cumulative)."""

    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int


@dataclass(kw_only=True)
class BaseResultMessage(BaseMessage):
    """Base result message with cost and usage information.

    Note: Fields use inconsistent scoping. See per-field docs for details.
    """

    type: Literal["result"] = "result"
    duration_ms: int
    """Wall-clock time for this query only (per-query)."""
    duration_api_ms: int
    """Cumulative API time across the entire session."""
    is_error: bool
    num_turns: int
    """Number of model turns in this query only (per-query)."""
    total_cost_usd: float
    """Cumulative cost across the entire session."""
    usage: Usage
    """Token usage from the last API call only (per-turn)."""
    stop_reason: StopReason | None
    modelUsage: dict[str, ModelUsage]  # noqa: N815
    """Cumulative token usage per model across the entire session."""
    permission_denials: list[SDKPermissionDenial]


@dataclass(kw_only=True)
class ResultSuccessMessage(BaseResultMessage):
    """Successful result message."""

    subtype: Literal["success"] = "success"
    result: str | None = None
    structured_output: Any = None


@dataclass(kw_only=True)
class ResultErrorMessage(BaseResultMessage):
    """Error result message."""

    subtype: ErrorSubType
    errors: list[str] | None = None


ResultMessage = ResultSuccessMessage | ResultErrorMessage


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
    tool_use_id: str
    tool_name: str
    parent_tool_use_id: str | None
    elapsed_time_seconds: float
    task_id: str | None = None


@dataclass(kw_only=True)
class ToolUseSummaryMessage(BaseMessage):
    """Summary of preceding tool uses."""

    type: Literal["tool_use_summary"] = "tool_use_summary"
    summary: str
    preceding_tool_use_ids: list[str]


@dataclass(kw_only=True)
class AuthStatusMessage(BaseMessage):
    """Authentication status update."""

    type: Literal["auth_status"] = "auth_status"
    isAuthenticating: bool = False  # noqa: N815
    output: list[str] | None = None
    error: str | None = None


@dataclass(kw_only=True)
class SDKSessionInfo:
    """Session metadata returned by list_sessions.

    Contains summary information about a stored session without
    loading the full conversation history.
    """

    session_id: str
    """Unique session identifier (UUID)."""

    summary: str
    """Display title for the session: custom title, auto-generated summary, or first prompt."""

    last_modified: int
    """Last modified time in milliseconds since epoch."""

    file_size: int
    """Session file size in bytes."""

    custom_title: str | None = None
    """User-set session title via /rename."""

    first_prompt: str | None = None
    """First meaningful user prompt in the session."""

    git_branch: str | None = None
    """Git branch at the end of the session."""

    cwd: str | None = None
    """Working directory for the session."""


SystemMessageUnion = Annotated[
    InitSystemMessage
    | HookStartedSystemMessage
    | StatusSystemMessage
    | CompactBoundarySystemMessage
    | HookProgressSystemMessage
    | HookResponseSystemMessage
    | TaskStartedSystemMessage
    | TaskNotificationSystemMessage
    | TaskProgressSystemMessage
    | FilesPersistedSystemMessage,
    Discriminator("subtype"),
]

system_message_adapter: TypeAdapter[SystemMessageUnion] = TypeAdapter(SystemMessageUnion)


Message = (
    UserMessage
    | AssistantMessage
    | InitSystemMessage
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
    | TaskProgressSystemMessage
    | FilesPersistedSystemMessage
    | ToolProgressMessage
    | ToolUseSummaryMessage
    | AuthStatusMessage
)
