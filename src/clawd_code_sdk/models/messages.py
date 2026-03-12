"""Content blocks, message types, and stream events."""

from __future__ import annotations

from collections.abc import Sequence
import re
from typing import Any, Literal, NotRequired, TypedDict

from anthropic.types import RawMessageStreamEvent
from anthropic.types.model import Model
from pydantic import BaseModel, ConfigDict

from clawd_code_sdk._errors import (
    APIError,
    AuthenticationError,
    BillingError,
    InvalidRequestError,
    RateLimitError,
    ServerError,
)
from clawd_code_sdk.models.base import FastModeState, StopReason, ToolName  # noqa: TC001
from clawd_code_sdk.models.content_blocks import ContentBlock, TextBlock
from clawd_code_sdk.models.input_types import ToolInput  # noqa: TC001
from clawd_code_sdk.models.output_types import ToolUseResult


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
RateLimitType = Literal["five_hour", "seven_day", "seven_day_opus", "seven_day_sonnet"]
RateLimitStatus = Literal["allowed", "allowed_warning", "rejected"]
OverAgeDisabledReason = Literal[
    "overage_not_provisioned",
    "org_level_disabled",
    "org_level_disabled_until",
    "out_of_credits",
    "seat_tier_level_disabled",
    "member_level_disabled",
    "seat_tier_zero_credit_limit",
    "group_zero_credit_limit",
    "member_zero_credit_limit",
    "org_service_level_disabled",
    "org_service_zero_credit_limit",
    "no_limits_configured",
    "unknown",
]


class SDKSessionInfo(BaseModel):
    """Session metadata returned by list_sessions."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    """Unique session identifier (UUID)."""

    summary: str
    """Display title for the session: custom title, auto-generated summary, or first prompt."""

    last_modified: int
    """Last modified time in milliseconds since epoch."""

    file_size: int | None = None
    """Session file size in bytes."""

    custom_title: str | None = None
    """User-set session title via /rename."""

    first_prompt: str | None = None
    """First meaningful user prompt in the session."""

    git_branch: str | None = None
    """Git branch at the end of the session."""

    cwd: str | None = None
    """Working directory for the session."""

    tag: str | None = None
    """User-set session tag."""

    created_at: float | None = None
    """Creation time in milliseconds since epoch."""


class RateLimitInfo(TypedDict):
    """Rate limit information."""

    status: RateLimitStatus
    resetsAt: NotRequired[int]
    rateLimitType: NotRequired[RateLimitType]
    utilization: NotRequired[float]
    overageStatus: NotRequired[RateLimitStatus]
    overageResetsAt: NotRequired[int]
    overageDisabledReason: NotRequired[OverAgeDisabledReason]
    isUsingOverage: NotRequired[bool]
    surpassedThreshold: NotRequired[float]


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


class Usage(BaseModel):
    """Token usage counters.

    Used both for per-turn snapshots (on ResultMessage) and as an accumulator
    (on ClaudeSDKClient.query_usage / session_usage).
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Sum of all token fields."""
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_creation_input_tokens
            + self.cache_read_input_tokens
        )

    def accumulate(self, usage: Usage) -> None:
        """Add another Usage's values to this one."""
        self.input_tokens += usage.input_tokens
        self.output_tokens += usage.output_tokens
        self.cache_creation_input_tokens += usage.cache_creation_input_tokens
        self.cache_read_input_tokens += usage.cache_read_input_tokens

    def reset(self) -> None:
        """Reset all counters to zero."""
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_creation_input_tokens = 0
        self.cache_read_input_tokens = 0


class BaseMessage(BaseModel):
    """Base class for messages."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    uuid: str
    session_id: str


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
    priority: Literal["now", "next", "later"] | None = None

    def parse_command_output(self) -> str | None:
        """Extract output from legacy XML-tagged command output in user messages."""
        content = self.content if isinstance(self.content, str) else ""
        pattern = r"<local-command-(?:stdout|stderr)>(.*?)</local-command-(?:stdout|stderr)>"
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1) if match else None


class AssistantMessage(BaseModel):
    """Assistant message with content blocks."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    type: Literal["assistant"] = "assistant"
    content: Sequence[ContentBlock]
    model: Model | str
    parent_tool_use_id: str | None = None
    error: AssistantMessageError | None = None
    session_id: str | None = None
    uuid: str | None = None

    def raise_if_api_error(self) -> None:
        """Raise the appropriate API exception if error is set."""
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
                raise APIError(error_message, unknown, self.model)


class RateLimitMessage(BaseMessage):
    """Rate limit event message."""

    type: Literal["rate_limit_event"] = "rate_limit_event"
    subtype: Literal["rate_limit"] = "rate_limit"
    rate_limit_info: RateLimitInfo


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
    modelUsage: dict[str, ModelUsage] = {}  # noqa: N815
    """Cumulative token usage per model across the entire session."""
    permission_denials: list[SDKPermissionDenial] = []
    """Permission denials from the last API call only (per-turn)."""
    fast_mode_state: FastModeState | None = None
    """Whether fast mode was enabled."""


class ResultSuccessMessage(BaseResultMessage):
    """Successful result message."""

    subtype: Literal["success"] = "success"
    result: str | None = None
    structured_output: Any = None


class ResultErrorMessage(BaseResultMessage):
    """Error result message."""

    subtype: ErrorSubType
    errors: list[str] | None = None


ResultMessage = ResultSuccessMessage | ResultErrorMessage


class StreamEvent(BaseMessage):
    """Stream event for partial message updates during streaming."""

    type: Literal["stream_event"] = "stream_event"
    event: RawMessageStreamEvent
    parent_tool_use_id: str | None = None

    @classmethod
    def block_stop(cls, *, index: int, session_id: str, uuid: str) -> StreamEvent:
        """Create a synthetic content_block_stop StreamEvent."""
        from anthropic.types import RawContentBlockStopEvent

        stop_event = RawContentBlockStopEvent(type="content_block_stop", index=index)
        return StreamEvent(event=stop_event, session_id=session_id, uuid=uuid)

    @classmethod
    def message_stop(cls, *, session_id: str, uuid: str) -> StreamEvent:
        """Create a synthetic message_stop StreamEvent."""
        from anthropic.types import RawMessageStopEvent

        stop_event = RawMessageStopEvent(type="message_stop")
        return StreamEvent(event=stop_event, session_id=session_id, uuid=uuid)


class ToolProgressMessage(BaseMessage):
    """Progress update for a running tool."""

    type: Literal["tool_progress"] = "tool_progress"
    tool_use_id: str
    tool_name: str
    parent_tool_use_id: str | None
    elapsed_time_seconds: float
    task_id: str | None = None


class ToolUseSummaryMessage(BaseMessage):
    """Summary of preceding tool uses."""

    type: Literal["tool_use_summary"] = "tool_use_summary"
    summary: str
    preceding_tool_use_ids: list[str]


class AuthStatusMessage(BaseMessage):
    """Authentication status update."""

    type: Literal["auth_status"] = "auth_status"
    isAuthenticating: bool = False  # noqa: N815
    output: list[str] | None = None
    error: str | None = None


class PromptSuggestionMessage(BaseMessage):
    """Predicted next user prompt, emitted after each turn when promptSuggestions is enabled."""

    type: Literal["prompt_suggestion"] = "prompt_suggestion"
    suggestion: str


MiscMessages = (
    UserMessage
    | AssistantMessage
    | ResultMessage
    | StreamEvent
    | RateLimitMessage
    | ToolProgressMessage
    | ToolUseSummaryMessage
    | AuthStatusMessage
    | PromptSuggestionMessage
)
