"""System message types."""

from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from anthropic.types.model import Model
from pydantic import BaseModel, ConfigDict, Discriminator, TypeAdapter

from clawd_code_sdk.models import McpConnectionStatus
from clawd_code_sdk.models.base import (  # noqa: TC001
    ApiKeySource,
    CompactionTrigger,
    FastModeState,
    PermissionMode,
    TaskStatus,
    ToolName,
)


Outcome = Literal["success", "error", "cancelled"]


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

    model_config = ConfigDict(extra="forbid")

    type: Literal["system"] = "system"
    uuid: str
    session_id: str


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
    status: Literal["compacting"] | None
    permissionMode: PermissionMode | None = None  # noqa: N815


class TriggerMetadata(TypedDict):
    """Trigger metadata."""

    trigger: CompactionTrigger
    pre_tokens: int


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


class TaskNotificationSystemMessage(BaseSystemMessage):
    """System message emitted when a subagent task completes, fails, or stops."""

    subtype: Literal["task_notification"] = "task_notification"
    task_id: str
    status: TaskStatus
    output_file: str
    summary: str
    tool_use_id: str | None = None


class TaskProgressSystemMessage(BaseSystemMessage):
    """System message emitted periodically with task progress updates."""

    subtype: Literal["task_progress"] = "task_progress"
    task_id: str
    tool_use_id: str | None = None
    description: str
    usage: TaskProgressUsage
    last_tool_name: ToolName | str | None = None


SystemMessageUnion = (
    InitSystemMessage
    | HookStartedSystemMessage
    | StatusSystemMessage
    | CompactBoundarySystemMessage
    | HookProgressSystemMessage
    | HookResponseSystemMessage
    | TaskStartedSystemMessage
    | TaskNotificationSystemMessage
    | TaskProgressSystemMessage
    | FilesPersistedSystemMessage
    | ElicitationCompleteMessage
    | LocalCommandOutputMessage
)

SystemMessages = Annotated[
    InitSystemMessage
    | HookStartedSystemMessage
    | StatusSystemMessage
    | CompactBoundarySystemMessage
    | HookProgressSystemMessage
    | HookResponseSystemMessage
    | TaskStartedSystemMessage
    | TaskNotificationSystemMessage
    | TaskProgressSystemMessage
    | FilesPersistedSystemMessage
    | ElicitationCompleteMessage
    | LocalCommandOutputMessage,
    Discriminator("subtype"),
]

system_message_adapter: TypeAdapter[SystemMessages] = TypeAdapter(SystemMessages)
