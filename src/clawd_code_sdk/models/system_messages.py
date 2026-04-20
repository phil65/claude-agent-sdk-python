"""System message types."""

from __future__ import annotations

import sys
from typing import Annotated, Literal, NotRequired, TypedDict

from anthropic.types.model import Model
from pydantic import BaseModel, ConfigDict, Discriminator, Field, TypeAdapter

from clawd_code_sdk.models import McpConnectionStatus
from clawd_code_sdk.models.base import (  # noqa: TC001
    ApiKeySource,
    AssistantMessageError,
    CompactionTrigger,
    FastModeState,
    PermissionMode,
    TaskStatus,
    ToolName,
)


IS_DEV = "pytest" in sys.modules


Outcome = Literal["success", "error", "cancelled"]
SessionState = Literal["idle", "running", "requires_action"]
SDKStatus = Literal["compacting", "requesting"] | None


class Plugin(BaseModel):
    """Claude code plugin."""

    name: str
    path: str


class TaskProgressUsage(TypedDict):
    """Usage info for a task progress update."""

    total_tokens: int
    tool_uses: int
    duration_ms: int


class McpServerStatus(BaseModel):
    """MCP server status."""

    name: str
    status: McpConnectionStatus


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
    scope: Literal["personal", "team"]
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
    agents: list[str]
    skills: list[str]
    plugins: list[Plugin]
    fast_mode_state: FastModeState | None = None
    """Whether fast mode was enabled."""


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


class PreservedSegment(TypedDict):
    """Relink info for preserved messages during compaction."""

    head_uuid: str
    anchor_uuid: str
    tail_uuid: str


class TriggerMetadata(TypedDict):
    """Trigger metadata."""

    trigger: CompactionTrigger
    pre_tokens: int
    post_tokens: NotRequired[int]
    duration_ms: NotRequired[float]
    preserved_segment: NotRequired[PreservedSegment]


class CompactBoundarySystemMessage(BaseSystemMessage):
    """System message emitted at compaction boundaries."""

    subtype: Literal["compact_boundary"] = "compact_boundary"
    compact_metadata: TriggerMetadata


class TaskStartedSystemMessage(BaseSystemMessage):
    """System message emitted when a subagent task starts."""

    subtype: Literal["task_started"] = "task_started"
    task_id: str
    tool_use_id: str | None = None
    description: str
    task_type: str | None = None
    workflow_name: str | None = None
    """meta.name from the workflow script (e.g. 'spec').

    Only set when task_type is 'local_workflow'."""
    prompt: str | None = None
    skip_transcript: bool | None = None
    """Whether to skip this message in the transcript."""


class Patch(BaseModel):
    """Patch for updating a task's status and metadata."""

    status: Literal["pending", "running", "completed", "failed", "killed"] | None = None
    description: str | None = None
    end_time: float | None = None
    total_paused_ms: int | None = None
    error: str | None = None
    is_backgrounded: bool | None = None


class TaskUpdatedSystemMessage(BaseSystemMessage):
    """System message emitted when a subagent task was updated."""

    subtype: Literal["task_updated"] = "task_updated"
    task_id: str
    patch: Patch


class TaskNotificationSystemMessage(BaseSystemMessage):
    """System message emitted when a subagent task completes, fails, or stops."""

    subtype: Literal["task_notification"] = "task_notification"
    task_id: str
    status: TaskStatus
    output_file: str
    summary: str
    tool_use_id: str | None = None
    usage: TaskProgressUsage | None = None
    skip_transcript: bool | None = None
    """Whether to skip this message in the transcript."""


class TaskProgressSystemMessage(BaseSystemMessage):
    """System message emitted periodically with task progress updates."""

    subtype: Literal["task_progress"] = "task_progress"
    task_id: str
    tool_use_id: str | None = None
    description: str
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


class APIRetrySystemMessage(BaseSystemMessage):
    """System message emitted when an API call fails and is retried."""

    subtype: Literal["api_retry"] = "api_retry"
    attempt: int
    max_retries: int
    retry_delay_ms: float
    error_status: int | None
    error: AssistantMessageError


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
)

SystemMessages = Annotated[SystemMessageUnion, Discriminator("subtype")]

system_message_adapter: TypeAdapter[SystemMessages] = TypeAdapter(SystemMessages)
