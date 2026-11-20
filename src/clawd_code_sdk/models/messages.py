"""Content blocks, message types, and stream events."""

from __future__ import annotations

from collections.abc import Sequence
import re
from typing import TYPE_CHECKING, Annotated, Any, Literal, NotRequired, TypedDict

from anthropic.types.beta import (
    BetaInputJSONDelta,
    BetaMessageDeltaUsage,
    BetaRawContentBlockDeltaEvent,
    BetaRawContentBlockStartEvent,
    BetaRawMessageDeltaEvent,
    BetaRawMessageStreamEvent,
    BetaStopReason,  # noqa: TC002
    BetaTextBlock as ATextBlock,
    BetaTextDelta,
    BetaThinkingBlock as AThinkingBlock,
    BetaThinkingDelta,
    BetaToolUseBlock as AToolUseBlock,
)
from anthropic.types.beta.beta_raw_message_delta_event import Delta as BetaRawMessageDelta
from pydantic import BaseModel, ConfigDict, Field

from clawd_code_sdk._errors import (
    APIError,
    AuthenticationError,
    BillingError,
    InvalidRequestError,
    RateLimitError,
    ServerError,
)
from clawd_code_sdk.models.base import (  # noqa: TC001
    IS_DEV,
    AssistantMessageError,
    ClaudeCodeBaseModel,
    FastModeDisabledReason,
    FastModeState,
    StartupFailureReason,
    StopReason,
    TerminalReason,
    ToolName,
)
from clawd_code_sdk.models.content_blocks import AssistantMessageContent, MessageParam, TextBlock
from clawd_code_sdk.models.context_usage import SDKContextUsage, SDKUsageReport
from clawd_code_sdk.models.input_types import ToolInput  # noqa: TC001
from clawd_code_sdk.models.output_types import SDKDeferredToolUse, ToolUseResult
from clawd_code_sdk.models.usage import ModelUsage, Usage


if TYPE_CHECKING:
    from logfire._internal.integrations.llm_providers.semconv import MessagePart, OutputMessage

    from clawd_code_sdk.models.content_blocks import AssistantContentBlock, UserContentBlock


# Message types
ErrorSubType = Literal[
    "error_during_execution",
    "error_max_turns",
    "error_max_budget_usd",
    "error_max_structured_output_retries",
]
RateLimitType = Literal[
    "five_hour",
    "seven_day",
    "seven_day_opus",
    "seven_day_sonnet",
    "seven_day_overage_included",
    "overage",
]
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
    "fetch_error",
    "unknown",
]
MessagePriority = Literal["now", "next", "later"]


class HumanMessageOrigin(ClaudeCodeBaseModel):
    """Human message origin."""

    kind: Literal["human"] = "human"


class ChannelMessageOrigin(ClaudeCodeBaseModel):
    """Channel message origin."""

    kind: Literal["channel"] = "channel"
    server: str


class PeerMessageOrigin(ClaudeCodeBaseModel):
    """Peer message origin."""

    kind: Literal["peer"] = "peer"
    from_: str = Field(..., alias="from")
    from_mode: Literal["bypass", "prompting"] | None = None
    name: str | None = None
    from_session: str | None = None
    sender_task_id: str | None = None
    body: str | None = None
    verified_peer_pid: int | None = None


class TaskNotificationMessageOrigin(ClaudeCodeBaseModel):
    """Task notification message origin."""

    kind: Literal["task-notification"] = "task-notification"
    subkind: (
        Literal["scheduled-trigger", "peer-send-message", "projects-relay", "session-inbox"] | None
    ) = None
    fire_reason: str | None = None
    run_id: str | None = None


class CoordinatorMessageOrigin(ClaudeCodeBaseModel):
    """Coordinator message origin."""

    kind: Literal["coordinator"] = "coordinator"


class UnclassifiedMessageOrigin(ClaudeCodeBaseModel):
    """Unclassified message origin."""

    kind: Literal["unclassified"] = "unclassified"


class ObserverMessageOrigin(ClaudeCodeBaseModel):
    """Message injected by an observer agent."""

    kind: Literal["observer"] = "observer"
    from_: str = Field(..., alias="from")
    sender_task_id: str


class AutoContinuationMessageOrigin(ClaudeCodeBaseModel):
    """Message synthesized for an automatic continuation."""

    kind: Literal["auto-continuation"] = "auto-continuation"


class ObserverActivityMessageOrigin(ClaudeCodeBaseModel):
    """Observer activity message origin."""

    kind: Literal["observer-activity"] = "observer-activity"


SDKMessageOrigin = Annotated[
    HumanMessageOrigin
    | ChannelMessageOrigin
    | PeerMessageOrigin
    | TaskNotificationMessageOrigin
    | CoordinatorMessageOrigin
    | UnclassifiedMessageOrigin
    | ObserverMessageOrigin
    | AutoContinuationMessageOrigin
    | ObserverActivityMessageOrigin,
    Field(discriminator="kind"),
]


class RateLimitInfo(ClaudeCodeBaseModel):
    """Rate limit information."""

    status: RateLimitStatus
    resets_at: int | None = None
    rate_limit_type: RateLimitType | None = None
    utilization: float | None = None
    overage_status: RateLimitStatus | None = None
    overage_resets_at: int | None = None
    overage_disabled_reason: OverAgeDisabledReason | None = None
    is_using_overage: bool | None = None
    overage_in_use: bool | None = None
    overage_enabled: bool | None = None
    surpassed_threshold: float | None = None
    limit_scope: Literal["service", "channel", "group_pool"] | None = None
    error_code: Literal["credits_required"] | None = None
    can_user_purchase_credits: bool | None = None
    has_chargeable_saved_payment_method: bool | None = None
    unified_windows: dict[str, Any] | None = None
    """Per-window utilization/status (e.g. ``five_hour``, ``seven_day``); undocumented."""


class SDKPermissionDenial(TypedDict):
    """Permission denial from Claude API response."""

    tool_name: ToolName | str
    tool_use_id: str
    tool_input: ToolInput | dict[str, Any]


class BaseMessage(BaseModel):
    """Base class for messages."""

    model_config = ConfigDict(
        extra="forbid" if IS_DEV else "ignore", arbitrary_types_allowed=True, populate_by_name=True
    )

    uuid: str


class FileAttachment(BaseModel):
    """Attachment for a message."""

    file_uuid: str
    file_name: str


class UserMessage(BaseModel):
    """User message."""

    model_config = ConfigDict(
        extra="forbid" if IS_DEV else "ignore", arbitrary_types_allowed=True, populate_by_name=True
    )
    type: Literal["user"] = "user"
    uuid: str | None = None
    """Always set for incoming user messages, can be omitted for objects created in query()."""
    session_id: str | None = None
    parent_tool_use_id: str | None = None
    tool_use_result: (
        Sequence[ToolUseResult | dict[str, Any]] | ToolUseResult | dict[str, Any] | str | None
    ) = None
    is_replay: bool | None = Field(default=None, validation_alias="isReplay")
    is_synthetic: bool | None = Field(default=None, validation_alias="isSynthetic")
    priority: MessagePriority | None = None
    message: MessageParam
    timestamp: str | None = None
    file_attachments: list[FileAttachment] | None = None
    origin: SDKMessageOrigin | None = None
    should_query: bool | None = Field(default=None, validation_alias="shouldQuery")
    client_composed: bool | None = None
    """Set when the host composed this message (as opposed to the user typing it)."""
    pasted_content: list[Any] | None = None
    inline_pastes: list[str] | None = None
    agent_id: str | None = None
    """Subagent ID when this message belongs to a subagent transcript."""
    subagent_type: str | None = None
    task_description: str | None = None
    tool_result_meta: list[ToolResultMeta] | None = None
    """Per-tool-result metadata, e.g. how permission was decided (undocumented)."""

    @property
    def content(self) -> str | Sequence[UserContentBlock]:
        """Return the message content."""
        return self.message.content

    def parse_command_output(self) -> str | None:
        """Extract output from legacy XML-tagged command output in user messages."""
        content = self.content if isinstance(self.content, str) else ""
        pattern = r"<local-command-(?:stdout|stderr)>(.*?)</local-command-(?:stdout|stderr)>"
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1) if match else None


class ApiErrorParams(ClaudeCodeBaseModel):
    """Parameters of an API error, present only for the error kinds that have any (undocumented)."""

    effort: str | None = None
    """Effort level the API refused (effort_requires_thinking)."""
    provider: (
        Literal[
            "bedrock",
            "anthropicAws",
            "mantle",
            "anthropicGoogleCloud",
            "vertex",
            "foundry",
            "gateway",
        ]
        | None
    ) = None
    remedy: (
        Literal[
            "refresh_command",
            "refresh_credentials",
            "adc",
            "gateway_token",
            "host_managed",
            "model_access",
        ]
        | None
    ) = None
    media: Literal["image", "document"] | None = None
    """Kind of block the API refused (media_removed)."""
    media_reason: Literal["unprocessable", "unsupported_by_model", "media_budget"] | None = None
    rate_limit_info: RateLimitInfo | None = None
    cut: Literal["output_limit", "context_window"] | None = None


class ToolUseMeta(ClaudeCodeBaseModel):
    """Display metadata for a tool_use block in an assistant message (undocumented)."""

    id: str
    """ID of the tool_use block this metadata belongs to."""
    tool_name: str
    """Name of the tool (without MCP server prefix)."""
    display_name: str | None = None
    """Human-readable tool name."""
    server_display_name: str | None = None
    """Display name of the MCP server providing the tool."""


class AssistantMessage(BaseModel):
    """Assistant message with content blocks."""

    model_config = ConfigDict(extra="forbid" if IS_DEV else "ignore", arbitrary_types_allowed=True)

    type: Literal["assistant"] = "assistant"
    message: AssistantMessageContent
    parent_tool_use_id: str | None = None
    error: AssistantMessageError | None = None
    session_id: str | None = None
    uuid: str | None = None
    request_id: str | None = None
    """API request ID that produced this message."""
    user_message_uuid: str | None = None
    """UUID of the user message this assistant message responds to."""
    user_message_uuids: list[str] | None = None
    """UUIDs of all user messages this assistant message responds to (batched turns)."""
    resume_reason: str | None = None
    resumed_from_incomplete_thinking: bool | None = None
    supersedes: list[str] | None = None
    """UUIDs of previously emitted assistant messages this one replaces."""
    aborted: bool | None = None
    """Set when the turn was aborted while this message was streaming."""
    agent_id: str | None = None
    subagent_type: str | None = None
    task_description: str | None = None
    timestamp: str | None = None
    context_usage: SDKContextUsage | None = None
    usage_report: SDKUsageReport | None = None
    wire_tool_inputs: dict[str, dict[str, Any]] | None = None
    """Tool inputs as sent on the wire, keyed by tool_use ID (undocumented)."""
    wire_ingest_context: dict[str, dict[str, Any]] | None = None
    """Per-tool_use ingest context (e.g. cwd), keyed by tool_use ID (undocumented)."""
    thinking_duration_ms: float | None = None
    """How long the model spent thinking for this message (undocumented)."""
    thinking_display: str | None = None
    """Active thinking display mode (undocumented)."""
    tool_use_meta: list[ToolUseMeta] | None = None
    """Display metadata for the tool_use blocks in this message (undocumented)."""
    is_api_error_message: bool | None = None
    """True when this assistant message wraps an API error (undocumented)."""
    api_error_status: int | None = None
    """HTTP status code of the API error when `is_api_error_message` is true."""
    api_error_type: str | None = None
    """The `error.type` of the API error response body, e.g. `rate_limit_error`."""
    api_error_origin: Literal["first_party"] | None = None
    """`first_party` when Anthropic's own API sent the error response."""
    api_error_params: ApiErrorParams | None = None
    """Parameters of the API error, for the error kinds that have any."""

    @property
    def content(self) -> Sequence[AssistantContentBlock]:
        """Return the message content blocks."""
        return self.message.content

    @property
    def model(self) -> str:
        """Return the model name."""
        return self.message.model

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
            case "rate_limit" | "overloaded":
                raise RateLimitError(error_message, self.model)
            case "invalid_request":
                raise InvalidRequestError(error_message, self.model)
            case "server_error":
                raise ServerError(error_message, self.model)
            case "oauth_org_not_allowed" | "account_on_hold" | "verification_required":
                raise AuthenticationError(error_message, self.model)
            case "model_not_found":
                raise InvalidRequestError(error_message, self.model)
            case _ as unknown:
                raise APIError(error_message, unknown, self.model)

    def to_otel(self) -> OutputMessage:
        """Convert SDK content block objects into semconv OutputMessages."""
        from logfire._internal.integrations.llm_providers.semconv import OutputMessage

        from clawd_code_sdk.models.content_blocks import is_server_block, server_block_to_otel

        parts: list[MessagePart] = []
        for block in self.content:
            if is_server_block(block):
                if (part := server_block_to_otel(block)) is not None:
                    parts.append(part)
            else:
                parts.append(block.to_otel())
        return OutputMessage(role="assistant", parts=parts)


class RateLimitMessage(BaseMessage):
    """Rate limit event message."""

    type: Literal["rate_limit_event"] = "rate_limit_event"
    subtype: Literal["rate_limit"] = "rate_limit"
    session_id: str
    rate_limit_info: RateLimitInfo


PostQueuedBehind = Literal["durable_post", "ephemeral_post", "retry_backoff", "hold", "none"]


class SubagentRequestedCounts(TypedDict):
    """How subagents were requested to run."""

    background: int
    foreground: int
    unset: int


class SubagentKilledCounts(TypedDict):
    """Who killed subagents."""

    parent: int
    user: int
    system: int


class SubagentRefusedCounts(TypedDict):
    """Why subagent spawns were refused."""

    depth_limit: int
    concurrency_limit: int
    budget: int


class SubagentStats(TypedDict):
    """Subagent statistics for the turn (undocumented)."""

    spawned: int
    requested: SubagentRequestedCounts
    started_in_background: int
    max_depth: int
    spawned_by_subagents: int
    completed: int
    failed: int
    killed: SubagentKilledCounts
    refused: SubagentRefusedCounts
    by_type: dict[str, Any]


class ToolPermissionDecisionMeta(TypedDict):
    """How a tool call's permission was decided."""

    decision: str
    source: str
    reason_type: NotRequired[str]


class ToolResultMeta(TypedDict):
    """Per-tool-result metadata attached to user messages (undocumented)."""

    id: str
    permission_decision: NotRequired[ToolPermissionDecisionMeta]


class InvalidConfigFile(TypedDict):
    """Details about a config file that failed to parse at startup."""

    path: str
    is_global: bool
    backup_searched: bool
    backup_path: NotRequired[str]


class BaseResultMessage(BaseMessage):
    """Base result message with cost and usage information.

    Note: Fields use inconsistent scoping. See per-field docs for details.
    """

    type: Literal["result"] = "result"
    session_id: str
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
    model_usage: dict[str, ModelUsage] = Field(default_factory=dict, validation_alias="modelUsage")
    """Cumulative token usage per model across the entire session."""
    permission_denials: list[SDKPermissionDenial] = []
    """Permission denials from the last API call only (per-turn)."""
    fast_mode_state: FastModeState | None = None
    """Whether fast mode was enabled."""
    terminal_reason: TerminalReason | None = None
    """Why the query loop terminated.

    Unset when the loop was bypassed (local slash command) or interrupted externally
    (budget/retry limits checked between yields).
    """
    fast_mode_disabled_reason: FastModeDisabledReason | None = None
    queued_turn_count: int | None = None
    """Number of turns still queued after this result."""
    user_message_uuid: str | None = None
    """UUID of the user message that started this turn."""
    user_message_uuids: list[str] | None = None
    """UUIDs of all user messages handled in this turn."""
    resume_reason: str | None = None
    result_index: int | None = None
    credential_expires_at: str | None = None
    origin: SDKMessageOrigin | None = None
    model_usage_since_last_result: dict[str, ModelUsage] | None = None
    """Per-model usage accrued since the previous result (undocumented)."""
    process_turn_index: int | None = None
    """Index of this turn within the CLI process (undocumented)."""
    safety_stops: int | None = None
    """Number of safety stops during the turn (undocumented)."""
    subagent_stats: SubagentStats | None = None
    """Subagent statistics for the turn (undocumented)."""
    turn_start_resume_kind: str | None = None
    """How the turn started relative to a resume, e.g. "none" (undocumented)."""
    # Timing diagnostics (undocumented; maps of phase name -> milliseconds/counters)
    time_to_request_cpu_ms: float | None = None
    time_to_request_loop_lag_ms: float | None = None
    time_to_request_major_faults: int | None = None
    time_to_request_phases_ms: dict[str, float] | None = None
    input_attachments_detail: dict[str, float | str] | None = None
    tool_schema_build_detail: dict[str, float] | None = None
    message_normalization_detail: dict[str, float] | None = None
    request_build_detail: dict[str, float] | None = None


class ResultSuccessMessage(BaseResultMessage):
    """Successful result message."""

    subtype: Literal["success"] = "success"
    result: str | None = None
    structured_output: Any = None
    deferred_tool_use: SDKDeferredToolUse | None = None
    api_error_status: int | None = None
    local_command: str | None = None
    """Set when the turn was a local slash command (no model call)."""
    warm_spare_claimed: bool | None = None
    time_origin_ms: float | None = None
    time_to_request_ms: float | None = None
    time_to_request_from_spawn_ms: float | None = None
    request_sent_wall_ms: float | None = None
    ttft_ms: float | None = None
    ttft_stream_ms: float | None = None
    first_content_frame_ms: float | None = None
    first_stream_post_ms: float | None = None
    first_stream_post_wall_ms: float | None = None
    first_stream_post_queue_wait_ms: float | None = None
    first_stream_post_queued_behind: PostQueuedBehind | None = None
    first_text_post_ms: float | None = None
    first_text_post_wall_ms: float | None = None
    first_text_post_queue_wait_ms: float | None = None
    first_text_post_queued_behind: PostQueuedBehind | None = None


class ResultErrorMessage(BaseResultMessage):
    """Error result message."""

    subtype: ErrorSubType
    errors: list[str] | None = None
    startup_failure_reason: StartupFailureReason | None = None
    invalid_config_file: InvalidConfigFile | None = None


ResultMessage = ResultSuccessMessage | ResultErrorMessage


class StreamEvent(BaseMessage):
    """Stream event for partial message updates during streaming."""

    type: Literal["stream_event"] = "stream_event"
    session_id: str
    event: BetaRawMessageStreamEvent
    parent_tool_use_id: str | None = None
    ttft_ms: float | None = None
    user_message_uuid: str | None = None
    user_message_uuids: list[str] | None = None
    resume_reason: str | None = None
    api_message_id: str | None = None
    """ID of the API message this event belongs to (undocumented)."""
    thinking_display: str | None = None
    """Active thinking display mode (undocumented)."""

    @classmethod
    def block_stop(cls, *, index: int, session_id: str, uuid: str) -> StreamEvent:
        """Create a synthetic content_block_stop StreamEvent."""
        from anthropic.types.beta import BetaRawContentBlockStopEvent

        stop_event = BetaRawContentBlockStopEvent(type="content_block_stop", index=index)
        return StreamEvent(event=stop_event, session_id=session_id, uuid=uuid)

    @classmethod
    def message_stop(cls, *, session_id: str, uuid: str) -> StreamEvent:
        """Create a synthetic message_stop StreamEvent."""
        from anthropic.types.beta import BetaRawMessageStopEvent

        stop_event = BetaRawMessageStopEvent(type="message_stop")
        return StreamEvent(event=stop_event, session_id=session_id, uuid=uuid)

    @classmethod
    def block_start_text(cls, *, index: int, session_id: str, uuid: str) -> StreamEvent:
        """Create a synthetic content_block_start StreamEvent for a text block."""
        content_block = ATextBlock(type="text", text="")
        start_event = BetaRawContentBlockStartEvent(
            type="content_block_start", index=index, content_block=content_block
        )
        return StreamEvent(event=start_event, session_id=session_id, uuid=uuid)

    @classmethod
    def block_start_thinking(cls, *, index: int, session_id: str, uuid: str) -> StreamEvent:
        """Create a synthetic content_block_start StreamEvent for a thinking block."""
        content_block = AThinkingBlock(type="thinking", thinking="", signature="")
        start_event = BetaRawContentBlockStartEvent(
            type="content_block_start", index=index, content_block=content_block
        )
        return StreamEvent(event=start_event, session_id=session_id, uuid=uuid)

    @classmethod
    def block_start_tool_use(
        cls, *, tool_use_id: str, name: str, index: int, session_id: str, uuid: str
    ) -> StreamEvent:
        """Create a synthetic content_block_start StreamEvent for a tool_use block."""
        content_block = AToolUseBlock(type="tool_use", id=tool_use_id, name=name, input={})
        start_event = BetaRawContentBlockStartEvent(
            type="content_block_start", index=index, content_block=content_block
        )
        return StreamEvent(event=start_event, session_id=session_id, uuid=uuid)

    @classmethod
    def block_text_delta(cls, *, text: str, index: int, session_id: str, uuid: str) -> StreamEvent:
        """Create a synthetic content_block_delta StreamEvent with full block content."""
        delta_event = BetaRawContentBlockDeltaEvent(
            type="content_block_delta",
            index=index,
            delta=BetaTextDelta(type="text_delta", text=text),
        )
        return StreamEvent(event=delta_event, session_id=session_id, uuid=uuid)

    @classmethod
    def block_thinking_delta(
        cls,
        *,
        thinking: str,
        index: int,
        session_id: str,
        uuid: str,
    ) -> StreamEvent:
        """Create a synthetic content_block_delta StreamEvent with full block content."""
        delta_event = BetaRawContentBlockDeltaEvent(
            type="content_block_delta",
            index=index,
            delta=BetaThinkingDelta(type="thinking_delta", thinking=thinking),
        )
        return StreamEvent(event=delta_event, session_id=session_id, uuid=uuid)

    @classmethod
    def block_tool_json_delta(
        cls,
        *,
        partial_json: str,
        index: int,
        session_id: str,
        uuid: str,
    ) -> StreamEvent:
        """Create a synthetic content_block_delta StreamEvent with full block content."""
        delta_event = BetaRawContentBlockDeltaEvent(
            type="content_block_delta",
            index=index,
            delta=BetaInputJSONDelta(type="input_json_delta", partial_json=partial_json),
        )
        return StreamEvent(event=delta_event, session_id=session_id, uuid=uuid)

    @classmethod
    def message_delta(
        cls,
        *,
        stop_reason: BetaStopReason | None,
        session_id: str,
        uuid: str,
    ) -> StreamEvent:
        """Create a synthetic message_delta StreamEvent."""
        usage = BetaMessageDeltaUsage(output_tokens=0)
        delta = BetaRawMessageDelta(stop_reason=stop_reason)
        delta_event = BetaRawMessageDeltaEvent(type="message_delta", delta=delta, usage=usage)
        return StreamEvent(event=delta_event, session_id=session_id, uuid=uuid)


class SubagentRetry(TypedDict):
    """Retry info when a subagent's API call is being retried."""

    agent_id: str
    attempt: int
    max_retries: int
    retry_delay_ms: float
    error_status: int | None
    error_category: str


class ToolProgressMessage(BaseMessage):
    """Progress update for a running tool."""

    type: Literal["tool_progress"] = "tool_progress"
    session_id: str
    tool_use_id: str
    tool_name: str
    parent_tool_use_id: str | None
    elapsed_time_seconds: float
    task_id: str | None = None
    heartbeat: bool | None = None
    """Keep-alive tick with no new progress."""
    subagent_type: str | None = None
    subagent_retry: SubagentRetry | None = None


class ToolUseSummaryMessage(BaseMessage):
    """Summary of preceding tool uses."""

    type: Literal["tool_use_summary"] = "tool_use_summary"
    session_id: str
    summary: str
    preceding_tool_use_ids: list[str]


class AuthStatusMessage(BaseMessage):
    """Authentication status update."""

    type: Literal["auth_status"] = "auth_status"
    session_id: str
    is_authenticating: bool = Field(False, validation_alias="isAuthenticating")
    output: list[str] | None = None
    error: str | None = None


class ConversationResetMessage(BaseMessage):
    """Emitted when the CLI starts a new conversation within the same session.

    E.g. after /clear, exiting plan mode into a fresh context, or onboarding.
    """

    type: Literal["conversation_reset"] = "conversation_reset"
    session_id: str
    new_conversation_id: str
    trigger: Literal["clear", "plan_mode_exit", "fresh_session", "onboarding"] | None = None
    user_message_uuid: str | None = None
    timestamp: str | None = None


CommandLifecycleState = Literal[
    "queued", "started", "completed", "cancelled", "discarded", "refused"
]
"""Where a uuid-stamped user message is in the CLI's command queue."""


class CommandLifecycleMessage(BaseMessage):
    """Progress of a user message that was sent with a ``uuid`` (capability ``msg_lifecycle_v1``).

    ``queued``: waiting behind the running work. ``started``: taken in (the cycle it starts,
    or the running cycle it was folded into). ``completed``: its work ended (after the
    result for a message that started a cycle, before it for one folded into a cycle).
    ``cancelled``: an interrupt stopped it. ``discarded`` / ``refused``: dropped before it ran.
    """

    type: Literal["command_lifecycle"] = "command_lifecycle"
    command_uuid: str
    """The ``uuid`` the message was sent with."""
    state: CommandLifecycleState
    session_id: str


class PromptSuggestionMessage(BaseMessage):
    """Predicted next user prompt, emitted after each turn when promptSuggestions is enabled."""

    type: Literal["prompt_suggestion"] = "prompt_suggestion"
    session_id: str
    suggestion: str


class StreamlinedTextMessage(BaseMessage):
    """Streamlined text message.

    Replaces AssistantMessage in streamlined output.
    Text content is preserved, thinking and tool_use blocks are removed.
    """

    type: Literal["streamlined_text"] = "streamlined_text"
    text: str
    session_id: str


class StreamlinedToolUseSummaryMessage(BaseMessage):
    """Streamlined tool use summary.

    Replaces tool_use blocks in streamlined output
    with a cumulative summary string.
    """

    type: Literal["streamlined_tool_use_summary"] = "streamlined_tool_use_summary"
    tool_summary: str
    session_id: str


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
    | ConversationResetMessage
    | CommandLifecycleMessage
    | StreamlinedTextMessage
    | StreamlinedToolUseSummaryMessage
)
