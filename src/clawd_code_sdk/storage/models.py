"""Claude Code storage models.

Pydantic models for Claude Code's JSONL transcript format, enabling
interoperability between agentpool and Claude Code.

Key features:
- JSONL-based conversation logs per project
- Multi-agent support (main + sub-agents)
- Message ancestry tracking
- Conversation forking and branching
- Discriminated unions for type-safe parsing

See ARCHITECTURE.md for detailed documentation of the storage format.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Discriminator, Field, Tag

from clawd_code_sdk.models import ToolUseResult
from clawd_code_sdk.models.base import ClaudeCodeBaseModel, StopReason
from clawd_code_sdk.models.content_blocks import (
    ContentBlock,
    ImageBlock,
    ImageSource,
    TextBlock,
    ToolResultBlock,
)


# See https://github.com/daaain/claude-code-log/blob/main/claude_code_log/models.py

UserType = Literal["external", "internal"]
MCPToolCallStatus = Literal["started", "completed", "failed"]


class ClaudeUsage(BaseModel):
    """Token usage from Claude API response."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    service_tier: str | None = None
    server_tool_use: dict[str, Any] | None = None

    def add(self, other: ClaudeUsage) -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cache_creation_input_tokens += other.cache_creation_input_tokens
        self.cache_read_input_tokens += other.cache_read_input_tokens


# =============================================================================
# Message models (role-based)
# =============================================================================


class ClaudeApiMessage(BaseModel):
    """Claude API assistant message structure."""

    model: str
    id: str
    type: Literal["message"] = "message"
    role: Literal["assistant"]
    content: str | Sequence[ContentBlock]
    stop_reason: StopReason | None = None
    stop_sequence: str | None = None
    usage: ClaudeUsage = Field(default_factory=ClaudeUsage)


class ClaudeUserMessage(BaseModel):
    """User message content."""

    role: Literal["user"]
    content: str | Sequence[ContentBlock]
    usage: ClaudeUsage | None = None
    """Usage info (for type compatibility with ClaudeApiMessage)."""


# =============================================================================
# JSONL entry base
# =============================================================================


class ClaudeEntryBase(ClaudeCodeBaseModel):
    """Common fields shared across user/assistant/system/saved_hook_context entries."""

    uuid: str
    parent_uuid: str | None = None
    session_id: str
    timestamp: str

    # Context
    cwd: str = ""
    git_branch: str | None = None
    version: str = ""

    # Metadata
    user_type: UserType = "external"
    is_sidechain: bool = False
    is_meta: bool | None = None
    agent_id: str | None = None


# =============================================================================
# User / Assistant entries
# =============================================================================


class ClaudeMessageEntryBase(ClaudeEntryBase):
    """Base for user/assistant message entries with message payload."""

    message: ClaudeApiMessage | ClaudeUserMessage

    is_compact_summary: bool | None = None
    request_id: str | None = None


class ClaudeUserEntry(ClaudeMessageEntryBase):
    """User message entry."""

    type: Literal["user"]
    tool_use_result: (
        list[ToolUseResult | dict[str, Any]] | ToolUseResult | dict[str, Any] | str | None
    ) = None


class ClaudeAssistantEntry(ClaudeMessageEntryBase):
    """Assistant message entry."""

    type: Literal["assistant"]
    is_api_error_message: bool | None = None


ClaudeEntry = ClaudeUserEntry | ClaudeAssistantEntry


# =============================================================================
# Queue operation entries (discriminated by "operation")
# =============================================================================


class ClaudeDocumentContent(ClaudeCodeBaseModel):
    """Document content block."""

    type: Literal["document"]
    source: ImageSource


type ClaudeQueueContent = str | TextBlock | ImageBlock | ClaudeDocumentContent | ToolResultBlock


class ClaudeEnqueueOperation(ClaudeCodeBaseModel):
    """Enqueue operation with content."""

    type: Literal["queue-operation"]
    operation: Literal["enqueue"]
    content: str | list[str | ClaudeQueueContent] | None = None
    session_id: str
    timestamp: str


class ClaudeDequeueOperation(ClaudeCodeBaseModel):
    """Dequeue operation."""

    type: Literal["queue-operation"]
    operation: Literal["dequeue"]
    session_id: str
    timestamp: str


class ClaudeRemoveOperation(ClaudeCodeBaseModel):
    """Remove operation (steering input)."""

    type: Literal["queue-operation"]
    operation: Literal["remove"]
    content: str | list[str | ClaudeQueueContent] | None = None
    session_id: str
    timestamp: str


class ClaudePopAllOperation(ClaudeCodeBaseModel):
    """PopAll operation - clears all queued content."""

    type: Literal["queue-operation"]
    operation: Literal["popAll"]
    content: str
    session_id: str
    timestamp: str


ClaudeQueueOperationEntry = Annotated[
    ClaudeEnqueueOperation | ClaudeDequeueOperation | ClaudeRemoveOperation | ClaudePopAllOperation,
    Field(discriminator="operation"),
]


# =============================================================================
# System entries (discriminated by "subtype")
# =============================================================================


class ClaudeSystemEntryBase(ClaudeEntryBase):
    """Common fields shared across all system entry subtypes."""

    type: Literal["system"]
    slug: str | None = None


class ClaudeHookInfo(ClaudeCodeBaseModel):
    """Hook info in stop_hook_summary."""

    command: str


class ClaudeCompactBoundaryEntry(ClaudeSystemEntryBase):
    """System entry emitted when conversation is compacted."""

    subtype: Literal["compact_boundary"]
    content: str | None = None
    level: str | None = None
    logical_parent_uuid: str | None = None
    compact_metadata: dict[str, Any] | None = None


class ClaudeTurnDurationEntry(ClaudeSystemEntryBase):
    """System entry recording the duration of a turn."""

    subtype: Literal["turn_duration"]
    duration_ms: int | None = None


class ClaudeApiErrorEntry(ClaudeSystemEntryBase):
    """System entry for API errors with retry information."""

    subtype: Literal["api_error"]
    level: str | None = None
    error: dict[str, Any] | None = None
    retry_in_ms: float | None = None
    retry_attempt: int | None = None
    max_retries: int | None = None


class ClaudeLocalCommandEntry(ClaudeSystemEntryBase):
    """System entry for local slash commands."""

    subtype: Literal["local_command"]
    content: str | None = None
    level: str | None = None


class ClaudeStopHookSummaryEntry(ClaudeSystemEntryBase):
    """System entry summarizing hook execution at turn end."""

    subtype: Literal["stop_hook_summary"]
    hook_count: int | None = None
    hook_infos: list[ClaudeHookInfo] | None = None
    hook_errors: list[Any] | None = None
    prevented_continuation: bool | None = None
    stop_reason: str | None = None
    has_output: bool | None = None


class ClaudeGenericSystemEntry(ClaudeSystemEntryBase):
    """Fallback for unknown or future system entry subtypes.

    Claude Code keeps adding new system subtypes. This model captures
    any subtype not explicitly modeled, preserving all data as optional fields.
    """

    subtype: str | None = None
    content: str | None = None
    level: str | None = None

    # Fields that may appear on various subtypes
    duration_ms: int | None = None
    is_compact_summary: bool | None = None
    logical_parent_uuid: str | None = None
    compact_metadata: dict[str, Any] | None = None
    hook_count: int | None = None
    hook_infos: list[ClaudeHookInfo] | None = None
    hook_errors: list[Any] | None = None
    prevented_continuation: bool | None = None
    stop_reason: str | None = None
    has_output: bool | None = None
    error: dict[str, Any] | None = None
    retry_in_ms: float | None = None
    retry_attempt: int | None = None
    max_retries: int | None = None
    tool_use_id: str | None = Field(default=None, alias="toolUseID")
    tool_use_result: (
        list[ToolUseResult | dict[str, Any]] | ToolUseResult | dict[str, Any] | str | None
    ) = None


def _system_entry_discriminator(data: Any) -> str:
    """Discriminator function for system entry subtypes.

    Routes known subtypes to their typed models, falls back to generic.
    Pydantic calls this with a dict (from JSON) or a model instance (re-validation).
    """
    subtype: str | None = None
    match data:
        case dict():
            subtype = data.get("subtype") or data.get("sub_type")
        case (
            ClaudeCompactBoundaryEntry()
            | ClaudeTurnDurationEntry()
            | ClaudeApiErrorEntry()
            | ClaudeLocalCommandEntry()
            | ClaudeStopHookSummaryEntry()
        ) as entry:
            subtype = entry.subtype
        case ClaudeGenericSystemEntry() as entry:
            subtype = entry.subtype
    if subtype in _KNOWN_SYSTEM_SUBTYPES:
        return subtype
    return "__generic__"


_KNOWN_SYSTEM_SUBTYPES: frozenset[str] = frozenset(
    {
        "compact_boundary",
        "turn_duration",
        "api_error",
        "local_command",
        "stop_hook_summary",
    }
)

ClaudeSystemEntry = Annotated[
    Annotated[ClaudeCompactBoundaryEntry, Tag("compact_boundary")]
    | Annotated[ClaudeTurnDurationEntry, Tag("turn_duration")]
    | Annotated[ClaudeApiErrorEntry, Tag("api_error")]
    | Annotated[ClaudeLocalCommandEntry, Tag("local_command")]
    | Annotated[ClaudeStopHookSummaryEntry, Tag("stop_hook_summary")]
    | Annotated[ClaudeGenericSystemEntry, Tag("__generic__")],
    Discriminator(_system_entry_discriminator),
]
"""Discriminated union of system entry subtypes with generic fallback."""


# =============================================================================
# Summary entry
# =============================================================================


class ClaudeSummaryEntry(ClaudeCodeBaseModel):
    """Summary entry (conversation summary)."""

    type: Literal["summary"]
    leaf_uuid: str
    summary: str
    cwd: str | None = None
    session_id: str | None = None
    """Summaries may not have a session_id."""


# =============================================================================
# File history snapshot entry
# =============================================================================


class ClaudeFileHistorySnapshot(ClaudeCodeBaseModel):
    """Snapshot data in file history entry."""

    message_id: str
    tracked_file_backups: dict[str, Any]
    timestamp: str


class ClaudeFileHistoryEntry(ClaudeCodeBaseModel):
    """File history snapshot entry."""

    type: Literal["file-history-snapshot"]
    message_id: str
    snapshot: ClaudeFileHistorySnapshot | dict[str, Any]
    is_snapshot_update: bool = False


# =============================================================================
# Progress entries (data discriminated by "type")
# =============================================================================


class ClaudeMcpProgressData(ClaudeCodeBaseModel):
    """Progress data for MCP tool operations."""

    type: Literal["mcp_progress"]
    status: MCPToolCallStatus | None = None
    server_name: str | None = None
    tool_name: str | None = None
    elapsed_time_ms: int | None = None


class ClaudeBashProgressData(ClaudeCodeBaseModel):
    """Progress data for bash tool operations."""

    type: Literal["bash_progress"]
    output: str | None = None
    full_output: str | None = None
    elapsed_time_seconds: int | None = None
    total_lines: int | None = None


class ClaudeHookProgressData(ClaudeCodeBaseModel):
    """Progress data for hook operations."""

    type: Literal["hook_progress"]
    hook_event: str | None = None
    hook_name: str | None = None
    command: str | None = None
    prompt_text: str | None = None
    status_message: str | None = None


class ClaudeWaitingForTaskData(ClaudeCodeBaseModel):
    """Progress data for waiting task operations."""

    type: Literal["waiting_for_task"]
    task_description: str | None = None
    task_type: str | None = None


class ClaudeAgentProgressData(ClaudeCodeBaseModel):
    """Progress data for agent/subagent operations."""

    type: Literal["agent_progress"]
    prompt: str | None = None
    agent_id: str | None = None
    message: dict[str, Any] | None = None
    normalized_messages: list[dict[str, Any]] | None = None
    resume: dict[str, Any] | None = None


class ClaudeQueryUpdateData(ClaudeCodeBaseModel):
    """Progress data for search query updates."""

    type: Literal["query_update"]
    query: str


class ClaudeSearchResultsReceivedData(ClaudeCodeBaseModel):
    """Progress data for search results received."""

    type: Literal["search_results_received"]
    result_count: int
    query: str


class ClaudeSkillProgressData(ClaudeCodeBaseModel):
    """Progress data for skill operations."""

    type: Literal["skill_progress"]
    prompt: str | None = None
    agent_id: str | None = None


class ClaudeTaskProgressData(ClaudeCodeBaseModel):
    """Progress data for task tracking."""

    type: Literal["task_progress"]
    task_id: str | None = None
    task_type: str | None = None
    message: str | None = None


class ClaudeToolProgressData(ClaudeCodeBaseModel):
    """Progress data for tool execution (SDK format)."""

    type: Literal["tool_progress"]
    tool_use_id: str | None = None
    tool_name: str | None = None
    parent_tool_use_id: str | None = None
    elapsed_time_seconds: float | None = None
    session_id: str | None = None


ClaudeProgressData = Annotated[
    ClaudeMcpProgressData
    | ClaudeBashProgressData
    | ClaudeHookProgressData
    | ClaudeWaitingForTaskData
    | ClaudeAgentProgressData
    | ClaudeQueryUpdateData
    | ClaudeSearchResultsReceivedData
    | ClaudeSkillProgressData
    | ClaudeTaskProgressData
    | ClaudeToolProgressData,
    Field(discriminator="type"),
]


class ClaudeProgressEntry(ClaudeCodeBaseModel):
    """Progress entry for tracking tool execution status."""

    type: Literal["progress"]
    uuid: str
    slug: str | None = None
    parent_uuid: str | None = None
    session_id: str
    timestamp: str
    data: ClaudeProgressData
    tool_use_id: str | None = None
    parent_tool_use_id: str | None = None
    agent_id: str | None = None
    # Common fields
    cwd: str = ""
    git_branch: str = ""
    version: str = ""
    user_type: UserType = "external"
    is_sidechain: bool = False


# =============================================================================
# Saved hook context entry
# =============================================================================


class ClaudeSavedHookContextEntry(ClaudeEntryBase):
    """Saved hook context entry.

    Stores hook context data (e.g. injected system prompts from hooks)
    persisted alongside the conversation.
    """

    type: Literal["saved_hook_context"]
    content: list[str] | str | None = None
    hook_name: str | None = None
    hook_event: str | None = None
    tool_use_id: str | None = Field(default=None, alias="toolUseID")


# =============================================================================
# Last prompt entry
# =============================================================================


class ClaudeLastPromptEntry(ClaudeCodeBaseModel):
    """Last prompt entry tracking the most recent user prompt."""

    type: Literal["last-prompt"]
    last_prompt: str = Field(alias="lastPrompt")
    session_id: str = Field(alias="sessionId")


# =============================================================================
# PR link entry
# =============================================================================


class ClaudePrLinkEntry(ClaudeCodeBaseModel):
    """PR link entry recording a pull request created during a session."""

    type: Literal["pr-link"]
    session_id: str = Field(alias="sessionId")
    pr_number: int = Field(alias="prNumber")
    pr_url: str = Field(alias="prUrl")
    pr_repository: str = Field(alias="prRepository")
    timestamp: str


# =============================================================================
# Top-level discriminated union
# =============================================================================

ClaudeJSONLEntry = Annotated[
    ClaudeUserEntry
    | ClaudeAssistantEntry
    | ClaudeQueueOperationEntry
    | ClaudeSystemEntry
    | ClaudeSummaryEntry
    | ClaudeFileHistoryEntry
    | ClaudeProgressEntry
    | ClaudeSavedHookContextEntry
    | ClaudeLastPromptEntry
    | ClaudePrLinkEntry,
    Field(discriminator="type"),
]
"""Discriminated union for all JSONL entry types."""
