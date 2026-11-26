"""System message types."""

from __future__ import annotations

import sys
from typing import Annotated, Any, Literal, NotRequired, TypedDict

from anthropic.types.model import Model
from pydantic import BaseModel, ConfigDict, Discriminator, Field, TypeAdapter

from clawd_code_sdk.models import McpConnectionStatus
from clawd_code_sdk.models.base import (
    ApiKeySource,
    AssistantMessageError,
    CompactionTrigger,
    FastModeDisabledReason,
    FastModeState,
    PermissionMode,
    ReasoningEffort,
    TaskStatus,
    ToolName,
)
from clawd_code_sdk.models.server_info import ClaudeCodeCommandInfo


IS_DEV = "pytest" in sys.modules


Outcome = Literal["success", "error", "cancelled"]
SessionState = Literal["idle", "running", "requires_action"]
SDKStatus = Literal["compacting", "requesting"] | None


class Plugin(BaseModel):
    """Claude code plugin."""

    name: str
    path: str
    version: str | None = None


class PluginManagedLock(TypedDict):
    """Managed-settings lock info for a plugin that failed to load."""

    plugin_enabled: bool
    name: str
    marketplace: NotRequired[str]


class PluginError(TypedDict):
    """Plugin load error reported in the init message."""

    plugin: str
    type: str
    message: str
    path: NotRequired[str]
    managed_lock: NotRequired[PluginManagedLock]


class McpResourceLink(TypedDict):
    """MCP resource link attached to a task notification."""

    uri: str
    name: str
    title: NotRequired[str]
    description: NotRequired[str]
    mimeType: NotRequired[str]
    size: NotRequired[int]
    annotations: NotRequired[dict[str, object]]


class TaskProgressUsage(TypedDict):
    """Usage info for a task progress update."""

    total_tokens: int
    tool_uses: int
    duration_ms: int


class McpServerStatus(BaseModel):
    """MCP server status."""

    name: str
    status: McpConnectionStatus
    source: str | None = None


class FilePersistedEntry(TypedDict):
    """A single file that was persisted."""

    filename: str
    file_id: str


class FilePersistedFailure(TypedDict):
    """A file that failed to persist."""

    filename: str
    error: str


class BaseSystemMessage(BaseModel):
    """Base class for all system messages."""

    model_config = ConfigDict(extra="forbid" if IS_DEV else "ignore")

    type: Literal["system"] = "system"
    uuid: str
    session_id: str


class NotificationSystemMessage(BaseSystemMessage):
    """Loop-side text notification.

    Mirrors the interactive REPL notification queue (key/priority/timeout).
    JSX notifications are not emitted on this channel.
    """

    subtype: Literal["notification"] = "notification"
    key: str
    text: str
    priority: Literal["low", "medium", "high", "immediate"]
    color: str | None = None
    timeout_ms: int | None = None


class Memory(BaseModel):
    """Agent memory."""

    path: str
    """Absolute or synthesis sentinel path."""
    scope: Literal["personal", "team", "organization"]
    content: str | None = None


class MemoryRecallSystemMessage(BaseSystemMessage):
    """Emitted when the memory recall supervisor surfaces relevant memories into the turn.

    Mirrors the CLI relevant_memories attachment so SDK renderers can show
    "Recalled from memory" inline.
    """

    subtype: Literal["memory_recall"] = "memory_recall"
    mode: Literal["select", "synthesize"]
    """Mode of memory recall."""
    memories: list[Memory]
    """List of memory objects."""


class ElicitationCompleteMessage(BaseSystemMessage):
    """System message emitted when an MCP elicitation completes."""

    subtype: Literal["elicitation_complete"] = "elicitation_complete"
    mcp_server_name: str
    elicitation_id: str


class LocalCommandOutputMessage(BaseSystemMessage):
    """Output from a local slash command (e.g. /voice, /cost).

    Displayed as assistant-style text in the transcript.
    """

    subtype: Literal["local_command_output"] = "local_command_output"
    content: str


class SessionKey(TypedDict):
    """Identifies a session transcript or subagent transcript in the store."""

    projectKey: str
    """Caller-defined scope. Default: sanitized cwd."""
    sessionId: str
    subpath: str | None
    """Set for subagent files, None for main transcript."""


class MirrorErrorSystemMessage(BaseSystemMessage):
    """Emitted when SessionStore.append() rejects or times out for a transcript-mirror batch.

    The batch is dropped (at-most-once delivery);
    this surfaces the failure so consumers are not silent on data loss.
    """

    subtype: Literal["mirror_error"] = "mirror_error"
    error: str
    key: SessionKey


class FilesPersistedSystemMessage(BaseSystemMessage):
    """System message emitted when files have been persisted."""

    subtype: Literal["files_persisted"] = "files_persisted"
    files: list[FilePersistedEntry]
    failed: list[FilePersistedFailure]
    processed_at: str


class HookProgressSystemMessage(BaseSystemMessage):
    """Progress update from a running hook."""

    subtype: Literal["hook_progress"] = "hook_progress"
    hook_id: str
    hook_name: str
    hook_event: str
    stdout: str
    stderr: str
    output: str


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


class InitSystemMessage(BaseSystemMessage):
    """System init message with session metadata."""

    subtype: Literal["init"] = "init"
    api_key_source: ApiKeySource | None = Field(..., validation_alias="apiKeySource")
    cwd: str
    tools: list[ToolName | str]
    mcp_servers: list[McpServerStatus]
    model: Model
    permission_mode: PermissionMode = Field(..., validation_alias="permissionMode")
    slash_commands: list[str]
    output_style: Literal["default", "json"] | str  # noqa: PYI051
    claude_code_version: str
    agents: list[str] | None = None
    skills: list[str]
    plugins: list[Plugin]
    plugin_errors: list[PluginError] | None = None
    betas: list[str] | None = None
    terminal_slash_commands: list[str] | None = None
    fast_mode_state: FastModeState | None = None
    """Whether fast mode was enabled."""
    fast_mode_disabled_reason: FastModeDisabledReason | None = None
    effort: ReasoningEffort | None = None
    view_mode: Literal["focus", "default"] | None = None
    capabilities: list[str] | None = None
    memory_paths: dict[str, str] | None = None
    """Auto-memory directories by kind (undocumented)."""
    original_cwd: str | None = None
    """The cwd the session was started in (undocumented)."""
    additional_directories: list[str] | None = None
    """Extra working directories added to the session (undocumented)."""
    messaging_socket_path: str | None = None
    """Path of the CLI's local messaging socket (undocumented)."""
    analytics_disabled: bool | None = None
    product_feedback_disabled: bool | None = None
    per_turn_effort_active: bool | None = None
    ultrathink_available: bool | None = None
    ultrathink_typed_raises: bool | None = None
    served_by_anthropic: bool | None = None
    """Whether requests are served by Anthropic directly (undocumented)."""
    startup_timing: dict[str, Any] | None = None
    """Startup timing diagnostics (undocumented, nested phase timings)."""
    user_message_uuids: list[str] | None = None
    """Client uuids of the user messages the turn takes in (undocumented, CLI 2.1.330+)."""


class HookStartedSystemMessage(BaseSystemMessage):
    """System message emitted when a hook starts."""

    subtype: Literal["hook_started"] = "hook_started"
    hook_id: str
    hook_name: str
    hook_event: str


class StatusSystemMessage(BaseSystemMessage):
    """System status message."""

    subtype: Literal["status"] = "status"
    status: SDKStatus
    permission_mode: PermissionMode | None = Field(None, validation_alias="permissionMode")
    compact_result: Literal["success", "failed"] | None = None
    compact_error: str | None = None
    user_message_uuids: list[str] | None = None
    """Client uuids of the user messages the turn takes in (undocumented, CLI 2.1.330+)."""


class PreservedSegment(TypedDict):
    """Relink info for preserved messages during compaction."""

    head_uuid: str
    anchor_uuid: str
    tail_uuid: str


class PreservedMessages(TypedDict):
    """Messages preserved verbatim across compaction."""

    anchor_uuid: str
    uuids: list[str]


class TriggerMetadata(TypedDict):
    """Trigger metadata."""

    trigger: CompactionTrigger
    pre_tokens: int
    post_tokens: NotRequired[int]
    duration_ms: NotRequired[float]
    preserved_segment: NotRequired[PreservedSegment]
    preserved_messages: NotRequired[PreservedMessages]


class CompactBoundarySystemMessage(BaseSystemMessage):
    """System message emitted at compaction boundaries."""

    subtype: Literal["compact_boundary"] = "compact_boundary"
    compact_metadata: TriggerMetadata


class TaskStartedSystemMessage(BaseSystemMessage):
    """System message emitted when a subagent task starts."""

    subtype: Literal["task_started"] = "task_started"
    task_id: str
    run_id: str | None = None
    tool_use_id: str | None = None
    description: str
    subagent_type: str | None = None
    is_backgrounded: bool | None = None
    spawn_depth: int | None = None
    parent_task_id: str | None = None
    task_type: str | None = None
    workflow_name: str | None = None
    """meta.name from the workflow script (e.g. 'spec').

    Only set when task_type is 'local_workflow'."""
    prompt: str | None = None
    skip_transcript: bool | None = None
    """Whether to skip this message in the transcript."""
    ambient: bool | None = None


class Patch(BaseModel):
    """Patch for updating a task's status and metadata."""

    status: Literal["pending", "running", "completed", "failed", "killed", "paused"] | None = None
    description: str | None = None
    end_time: float | None = None
    total_paused_ms: int | None = None
    error: str | None = None
    is_backgrounded: bool | None = None


class TaskUpdatedSystemMessage(BaseSystemMessage):
    """System message emitted when a subagent task was updated."""

    subtype: Literal["task_updated"] = "task_updated"
    task_id: str
    run_id: str | None = None
    patch: Patch


class TaskNotificationSystemMessage(BaseSystemMessage):
    """System message emitted when a subagent task completes, fails, or stops."""

    subtype: Literal["task_notification"] = "task_notification"
    task_id: str
    run_id: str | None = None
    status: TaskStatus
    reason: Literal["worker_restart"] | None = None
    output_file: str
    summary: str
    tool_use_id: str | None = None
    usage: TaskProgressUsage | None = None
    resource_links: list[McpResourceLink] | None = None
    skip_transcript: bool | None = None
    """Whether to skip this message in the transcript."""
    ambient: bool | None = None


class TaskProgressSystemMessage(BaseSystemMessage):
    """System message emitted periodically with task progress updates."""

    subtype: Literal["task_progress"] = "task_progress"
    task_id: str
    run_id: str | None = None
    tool_use_id: str | None = None
    description: str
    subagent_type: str | None = None
    usage: TaskProgressUsage
    last_tool_name: ToolName | str | None = None
    summary: str | None = None
    """AI-generated progress summary when agentProgressSummaries is enabled."""


class SessionStateChangedMessage(BaseSystemMessage):
    """System message emitted when session state changes.

    'idle' fires after heldBackResult flushes and the bg-agent do-while exits —
    authoritative turn-over signal.
    """

    subtype: Literal["session_state_changed"] = "session_state_changed"
    state: SessionState


class NoResponseInfo(TypedDict):
    """Timing info for an API call that never responded."""

    waited_ms: float
    retry_wait_ms: float


class APIRetrySystemMessage(BaseSystemMessage):
    """System message emitted when an API call fails and is retried."""

    subtype: Literal["api_retry"] = "api_retry"
    attempt: int
    max_retries: int
    retry_delay_ms: float
    error_status: int | None
    error: AssistantMessageError
    no_response: NoResponseInfo | None = None
    """Set when the retry was triggered by the API not responding at all."""


class ControlRequestProgressMessage(BaseSystemMessage):
    """Progress for a long-running control request (e.g. side question)."""

    subtype: Literal["control_request_progress"] = "control_request_progress"
    request_id: str
    status: Literal["started", "api_retry"]
    attempt: int | None = None
    max_retries: int | None = None
    retry_delay_ms: float | None = None
    error_status: int | None = None


class ModelRefusalFallbackMessage(BaseSystemMessage):
    """Emitted when a model refusal triggered a switch to a fallback model."""

    subtype: Literal["model_refusal_fallback"] = "model_refusal_fallback"
    trigger: Literal["refusal"]
    direction: Literal["retry", "revert", "sticky"]
    scope: Literal["session", "local"] | None = None
    original_model: str
    fallback_model: str
    request_id: str | None
    api_refusal_category: str | None = None
    api_refusal_explanation: str | None = None
    retracted_message_uuids: list[str] | None = None
    refused_user_message_uuid: str | None = None
    content: str


class ModelRefusalNoFallbackMessage(BaseSystemMessage):
    """Emitted when the model refused and no fallback model is available."""

    subtype: Literal["model_refusal_no_fallback"] = "model_refusal_no_fallback"
    original_model: str
    request_id: str | None
    api_refusal_category: str | None = None
    api_refusal_explanation: str | None = None
    refused_user_message_uuid: str | None = None
    content: str


class BackgroundTask(TypedDict):
    """A background task in the background_tasks_changed snapshot."""

    task_id: str
    run_id: NotRequired[str]
    task_type: str
    subagent_type: NotRequired[str]
    description: str
    parent_task_id: NotRequired[str]
    ambient: NotRequired[bool]


class BackgroundTasksChangedMessage(BaseSystemMessage):
    """Full snapshot of running background tasks, emitted whenever the set changes."""

    subtype: Literal["background_tasks_changed"] = "background_tasks_changed"
    tasks: list[BackgroundTask]


class ThinkingTokensMessage(BaseSystemMessage):
    """Running estimate of thinking tokens for the current turn."""

    subtype: Literal["thinking_tokens"] = "thinking_tokens"
    estimated_tokens: int
    estimated_tokens_delta: int
    user_message_uuid: str | None = None


class WorkerShuttingDownMessage(BaseSystemMessage):
    """Emitted when the CLI worker is shutting down."""

    subtype: Literal["worker_shutting_down"] = "worker_shutting_down"
    reason: str


class CommandsChangedMessage(BaseSystemMessage):
    """Emitted when the set of available slash commands changes."""

    subtype: Literal["commands_changed"] = "commands_changed"
    commands: list[ClaudeCodeCommandInfo]


class PermissionDeniedSystemMessage(BaseSystemMessage):
    """Emitted when a tool call was denied by the permission system."""

    subtype: Literal["permission_denied"] = "permission_denied"
    tool_name: ToolName | str
    tool_use_id: str
    agent_id: str | None = None
    decision_reason_type: str | None = None
    decision_reason: str | None = None
    message: str


class InformationalSystemMessage(BaseSystemMessage):
    """Informational text from the CLI (notices, suggestions, warnings)."""

    subtype: Literal["informational"] = "informational"
    content: str
    level: Literal["info", "notice", "suggestion", "warning"]
    tool_use_id: str | None = None
    prevent_continuation: bool | None = None
    tag: str | None = None


class SessionWritesLostMessage(BaseSystemMessage):
    """Emitted when writes were lost due to a full disk or exceeded quota."""

    subtype: Literal["session_writes_lost"] = "session_writes_lost"
    error_code: Literal["ENOSPC", "EDQUOT"]
    lost: list[Literal["transcript", "global_config"]]
    transcript_session_ids: list[str] | None = None


class PluginInstallSystemMessage(BaseSystemMessage):
    """System message emitted when a plugin is installed."""

    subtype: Literal["plugin_install"] = "plugin_install"
    status: Literal["started", "installed", "failed", "completed"]
    name: str | None = None
    error: str | None = None


SystemMessageUnion = (
    InitSystemMessage
    | HookStartedSystemMessage
    | StatusSystemMessage
    | CompactBoundarySystemMessage
    | HookProgressSystemMessage
    | HookResponseSystemMessage
    | TaskStartedSystemMessage
    | TaskNotificationSystemMessage
    | MirrorErrorSystemMessage
    | PluginInstallSystemMessage
    | TaskProgressSystemMessage
    | NotificationSystemMessage
    | MemoryRecallSystemMessage
    | TaskUpdatedSystemMessage
    | SessionStateChangedMessage
    | FilesPersistedSystemMessage
    | ElicitationCompleteMessage
    | LocalCommandOutputMessage
    | APIRetrySystemMessage
    | ControlRequestProgressMessage
    | ModelRefusalFallbackMessage
    | ModelRefusalNoFallbackMessage
    | BackgroundTasksChangedMessage
    | ThinkingTokensMessage
    | WorkerShuttingDownMessage
    | CommandsChangedMessage
    | PermissionDeniedSystemMessage
    | InformationalSystemMessage
    | SessionWritesLostMessage
)

SystemMessages = Annotated[SystemMessageUnion, Discriminator("subtype")]

system_message_adapter: TypeAdapter[SystemMessages] = TypeAdapter(SystemMessages)
