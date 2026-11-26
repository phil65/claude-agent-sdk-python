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
from functools import cache
from typing import TYPE_CHECKING, Annotated, Any, Literal, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Discriminator, Field, Tag

from clawd_code_sdk.models import (
    AssistantContentBlock,
    ImageBlock,
    ImageSource,
    TextBlock,
    ToolResultBlock,
    ToolUseResult,
    Usage,
    UserContentBlock,
)
from clawd_code_sdk.models.base import ClaudeCodeBaseModel, StopReason
from clawd_code_sdk.models.output_types import AgentServerToolUse, ServiceTier  # noqa: TC001


if TYPE_CHECKING:
    from collections.abc import Iterable


# See https://github.com/daaain/claude-code-log/blob/main/claude_code_log/models.py

UserType = Literal["external", "internal"]
MCPToolCallStatus = Literal["started", "completed", "failed"]


class ClaudeUsage(Usage):
    """Token usage from Claude API response, with additional storage fields."""

    service_tier: ServiceTier | None = None
    server_tool_use: AgentServerToolUse | None = None

    @classmethod
    def from_entries(cls, entries: Iterable[ClaudeJSONLEntry]) -> ClaudeUsage:
        """Extract deduplicated aggregate token usage from stored entries.

        Storage duplicates usage data across all content-block entries that
        share the same API ``message.id``. This deduplicates by ``message.id``
        and sums across all unique API calls.
        """
        seen_ids: set[str] = set()
        total = cls()
        for entry in entries:
            if not isinstance(entry, ClaudeAssistantEntry):
                continue
            msg = entry.message
            if msg.id in seen_ids:
                continue
            seen_ids.add(msg.id)
            total.accumulate(msg.usage)
        return total


# =============================================================================
# Message models (role-based)
# =============================================================================


class ClaudeStorageModel(ClaudeCodeBaseModel):
    """Base for transcript models: fields these models don't know are kept.

    Claude Code adds fields often. Keeping them (instead of ignoring them) means a
    read entry is written back unchanged, e.g. when a session is copied or forked.
    """

    model_config = ConfigDict(extra="allow")


class ClaudeApiMessage(BaseModel):
    """Claude API assistant message structure."""

    model_config = ConfigDict(extra="allow")

    model: str
    id: str
    type: Literal["message"] = "message"
    role: Literal["assistant"]
    content: str | Sequence[AssistantContentBlock]
    stop_reason: StopReason | None = None
    stop_sequence: str | None = None
    usage: ClaudeUsage = Field(default_factory=ClaudeUsage)
    container: dict[str, Any] | None = None
    """Code execution container info, if the response used one."""
    stop_details: dict[str, Any] | None = None
    context_management: dict[str, Any] | None = None
    """Context edits the API applied (e.g. cleared tool results)."""
    diagnostics: dict[str, Any] | None = None
    """API diagnostics such as ``cache_miss_reason``."""
    input_transformations: list[dict[str, Any]] | None = None
    """Transformations the API applied to the request input."""


class ClaudeUserMessage(BaseModel):
    """User message content."""

    model_config = ConfigDict(extra="allow")

    role: Literal["user"]
    content: str | Sequence[UserContentBlock]
    usage: ClaudeUsage | None = None
    """Usage info (for type compatibility with ClaudeApiMessage)."""


# =============================================================================
# JSONL entry base
# =============================================================================


class ClaudeEntryBase(ClaudeStorageModel):
    """Base of all entries that take part in the ``parentUuid`` chain.

    User, assistant, attachment, system, progress and saved-hook-context entries all link
    to their predecessor through ``parent_uuid``. The chain regularly runs through
    non-message entries (an assistant entry's parent is often an attachment or a system
    entry), so code walking the chain should index every ``ClaudeEntryBase`` by ``uuid``,
    not only user and assistant entries. See :mod:`clawd_code_sdk.storage.chain`.
    """

    uuid: str
    parent_uuid: str | None = None
    logical_parent_uuid: str | None = None
    """Preserves logical parent when parentUuid is nullified for session breaks."""
    session_id: str
    timestamp: str

    # Context
    cwd: str = ""
    git_branch: str | None = None
    version: str = ""
    entrypoint: str | None = None
    """CLAUDE_CODE_ENTRYPOINT — distinguishes cli/sdk-ts/sdk-py/etc."""
    slug: str | None = None
    """Session slug for files like plans (used for resume)."""

    # Metadata
    user_type: UserType = "external"
    is_sidechain: bool = False
    is_meta: bool | None = None
    agent_id: str | None = None
    team_name: str | None = None
    """Team name if this is a spawned agent session."""
    agent_name: str | None = None
    """Agent's custom name (from /rename or swarm)."""
    agent_color: str | None = None
    """Agent's color (from /rename or swarm)."""
    prompt_id: str | None = None
    """Correlates with OTel prompt.id for user prompt messages."""
    data_flow_on: bool | None = None


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
    message: ClaudeUserMessage
    tool_use_result: (
        list[ToolUseResult | dict[str, Any]] | ToolUseResult | dict[str, Any] | str | None
    ) = None
    source_tool_assistant_uuid: str | None = Field(default=None, alias="sourceToolAssistantUUID")
    """For tool results: uuid of the assistant entry holding the ``tool_use`` this answers."""
    source_tool_use_id: str | None = Field(default=None, alias="sourceToolUseID")
    """ID of the tool use that produced this message (e.g. skill or command expansions)."""
    permission_mode: str | None = None
    """Permission mode active when the prompt was sent."""
    permission_decision: dict[str, Any] | None = None
    """How the tool call this result answers was permitted (decision, source, reason)."""
    tool_denial_kind: str | None = None
    """Why the tool call was denied (``user-rejected``, ``permission-rule``, ...)."""
    sandboxed: bool | None = None
    """Whether the tool call ran in the sandbox."""
    prompt_source: str | None = None
    """Where the prompt came from (``typed``, ``sdk``, ``queued``, ``system``)."""
    turn_origin: str | None = None
    """What started the turn (``human``, ``sdk``, ``task_notification``, ``peer``, ...)."""
    origin: dict[str, Any] | None = None
    """Origin of the message, keyed by ``kind``."""
    turn_position: dict[str, int] | None = None
    """``turnIndex`` / ``promptIndex`` of the prompt within the session."""
    interrupted_message_id: str | None = None
    is_visible_in_transcript_only: bool | None = None
    is_virtual: bool | None = None
    image_paste_ids: list[int] | None = None
    mcp_meta: dict[str, Any] | None = None
    """``_meta`` / ``structuredContent`` of an MCP tool result."""

    @property
    def is_tool_result(self) -> bool:
        """Whether this is a synthetic tool_result entry (vs. an actual user prompt)."""
        if isinstance(self.message.content, str):
            return False
        return all(b.type == "tool_result" for b in self.message.content)


class ClaudeAssistantEntry(ClaudeMessageEntryBase):
    """Assistant message entry."""

    type: Literal["assistant"]
    message: ClaudeApiMessage
    is_api_error_message: bool | None = None
    error: str | None = None
    """Error category for API error messages (``rate_limit``, ``billing_error``, ...)."""
    api_error_status: int | None = None
    """HTTP status of the failed API request."""
    api_error_type: str | None = None
    api_error: str | None = None
    is_aborted_mid_stream: bool | None = None
    requested_model: str | None = None
    """Model that was asked for (``message.model`` is the one that answered)."""
    effort: str | None = None
    per_turn_effort: str | None = None
    advisor_model: str | None = None
    made_by: str | None = None
    """``model`` for model output, ``other`` for synthetic messages."""
    api_block_index: int | None = None
    """Index of this entry's content block within the API response."""
    request_ref: str | None = None
    """Reference to the ``api-request`` entry this response answers."""
    thinking_duration_ms: int | None = None
    thinking_display: str | None = None
    tool_input_stream_ms: int | None = None
    attribution_agent: str | None = None
    attribution_skill: str | None = None
    attribution_plugin: str | None = None
    attribution_mcp_server: str | None = None
    attribution_mcp_tool: str | None = None


ClaudeEntry = ClaudeUserEntry | ClaudeAssistantEntry


# =============================================================================
# Queue operation entries (discriminated by "operation")
# =============================================================================


class ClaudeDocumentContent(ClaudeStorageModel):
    """Document content block."""

    type: Literal["document"]
    source: ImageSource


type ClaudeQueueContent = str | TextBlock | ImageBlock | ClaudeDocumentContent | ToolResultBlock


class ClaudeEnqueueOperation(ClaudeStorageModel):
    """Enqueue operation with content."""

    type: Literal["queue-operation"]
    operation: Literal["enqueue"]
    content: str | list[str | ClaudeQueueContent] | None = None
    session_id: str
    timestamp: str


class ClaudeDequeueOperation(ClaudeStorageModel):
    """Dequeue operation."""

    type: Literal["queue-operation"]
    operation: Literal["dequeue"]
    session_id: str
    timestamp: str


class ClaudeRemoveOperation(ClaudeStorageModel):
    """Remove operation (steering input)."""

    type: Literal["queue-operation"]
    operation: Literal["remove"]
    content: str | list[str | ClaudeQueueContent] | None = None
    session_id: str
    timestamp: str
    reason: str | None = None
    """Why the item left the queue (``absorbed_mid_turn``, ``delivered_to_agent``)."""
    command_uuid: str | None = None
    delivery_id: str | None = None


class ClaudePopAllOperation(ClaudeStorageModel):
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


class ClaudeHookInfo(ClaudeStorageModel):
    """Hook info in stop_hook_summary."""

    command: str
    duration_ms: int | None = None


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
    message_count: int | None = None
    pending_background_agent_count: int | None = None


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
    command_run: dict[str, Any] | None = None
    """The command and its arguments."""
    context_usage: dict[str, Any] | None = None
    """Context window breakdown (for ``/context``)."""
    is_display_only: bool | None = None


class ClaudeStopHookSummaryEntry(ClaudeSystemEntryBase):
    """System entry summarizing hook execution at turn end."""

    subtype: Literal["stop_hook_summary"]
    hook_count: int | None = None
    hook_infos: list[ClaudeHookInfo] | None = None
    hook_errors: list[Any] | None = None
    prevented_continuation: bool | None = None
    stop_reason: str | None = None
    has_output: bool | None = None
    level: str | None = None
    tool_use_id: str | None = Field(default=None, alias="toolUseID")
    hook_additional_context: list[Any] | None = None
    failed_hook_error_indexes: list[int] | None = None


class ClaudeAwaySummaryEntry(ClaudeSystemEntryBase):
    """System entry recapping the session for a user returning after a break."""

    subtype: Literal["away_summary"]
    content: str | None = None


class ClaudeInformationalEntry(ClaudeSystemEntryBase):
    """Informational notice shown in the transcript."""

    subtype: Literal["informational"]
    content: str | None = None
    level: str | None = None
    launched_agent_id: str | None = None


class ClaudeModelRefusalFallbackEntry(ClaudeSystemEntryBase):
    """The model refused and the request was retried with a fallback model.

    ``retracted_message_uuids`` are the messages the refusal withdrew from the conversation.
    """

    subtype: Literal["model_refusal_fallback"]
    content: str | None = None
    level: str | None = None
    trigger: str | None = None
    direction: str | None = None
    scope: str | None = None
    original_model: str | None = None
    fallback_model: str | None = None
    request_id: str | None = None
    api_refusal_category: str | None = None
    api_refusal_explanation: str | None = None
    api_refusal_cyber_verification: dict[str, Any] | None = None
    retracted_message_uuids: list[str] | None = None
    refused_user_message_uuid: str | None = None


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
            | ClaudeAwaySummaryEntry()
            | ClaudeInformationalEntry()
            | ClaudeModelRefusalFallbackEntry()
        ) as entry:
            subtype = entry.subtype
        case ClaudeGenericSystemEntry() as entry:
            subtype = entry.subtype
    if subtype in _KNOWN_SYSTEM_SUBTYPES:
        return subtype
    return "__generic__"


_KNOWN_SYSTEM_SUBTYPES: frozenset[str] = frozenset({
    "compact_boundary",
    "turn_duration",
    "api_error",
    "local_command",
    "stop_hook_summary",
    "away_summary",
    "informational",
    "model_refusal_fallback",
})

ClaudeSystemEntry = Annotated[
    Annotated[ClaudeCompactBoundaryEntry, Tag("compact_boundary")]
    | Annotated[ClaudeTurnDurationEntry, Tag("turn_duration")]
    | Annotated[ClaudeApiErrorEntry, Tag("api_error")]
    | Annotated[ClaudeLocalCommandEntry, Tag("local_command")]
    | Annotated[ClaudeStopHookSummaryEntry, Tag("stop_hook_summary")]
    | Annotated[ClaudeAwaySummaryEntry, Tag("away_summary")]
    | Annotated[ClaudeInformationalEntry, Tag("informational")]
    | Annotated[ClaudeModelRefusalFallbackEntry, Tag("model_refusal_fallback")]
    | Annotated[ClaudeGenericSystemEntry, Tag("__generic__")],
    Discriminator(_system_entry_discriminator),
]
"""Discriminated union of system entry subtypes with generic fallback."""


# =============================================================================
# Summary entry
# =============================================================================


class ClaudeSummaryEntry(ClaudeStorageModel):
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


class ClaudeFileHistorySnapshot(ClaudeStorageModel):
    """Snapshot data in file history entry."""

    message_id: str
    tracked_file_backups: dict[str, Any]
    timestamp: str
    has_untracked_changes: bool | None = None


class ClaudeFileHistoryEntry(ClaudeStorageModel):
    """File history snapshot entry."""

    type: Literal["file-history-snapshot"]
    message_id: str
    snapshot: ClaudeFileHistorySnapshot | dict[str, Any]
    is_snapshot_update: bool = False


# =============================================================================
# Progress entries (data discriminated by "type")
# =============================================================================


class ClaudeMcpProgressData(ClaudeStorageModel):
    """Progress data for MCP tool operations."""

    type: Literal["mcp_progress"]
    status: MCPToolCallStatus | None = None
    server_name: str | None = None
    tool_name: str | None = None
    elapsed_time_ms: int | None = None


class ClaudeBashProgressData(ClaudeStorageModel):
    """Progress data for bash tool operations."""

    type: Literal["bash_progress"]
    output: str | None = None
    full_output: str | None = None
    elapsed_time_seconds: int | None = None
    total_lines: int | None = None


class ClaudeHookProgressData(ClaudeStorageModel):
    """Progress data for hook operations."""

    type: Literal["hook_progress"]
    hook_event: str | None = None
    hook_name: str | None = None
    command: str | None = None
    prompt_text: str | None = None
    status_message: str | None = None


class ClaudeWaitingForTaskData(ClaudeStorageModel):
    """Progress data for waiting task operations."""

    type: Literal["waiting_for_task"]
    task_description: str | None = None
    task_type: str | None = None


class ClaudeAgentProgressData(ClaudeStorageModel):
    """Progress data for agent/subagent operations."""

    type: Literal["agent_progress"]
    prompt: str | None = None
    agent_id: str | None = None
    message: dict[str, Any] | None = None
    normalized_messages: list[dict[str, Any]] | None = None
    resume: dict[str, Any] | None = None


class ClaudeQueryUpdateData(ClaudeStorageModel):
    """Progress data for search query updates."""

    type: Literal["query_update"]
    query: str


class ClaudeSearchResultsReceivedData(ClaudeStorageModel):
    """Progress data for search results received."""

    type: Literal["search_results_received"]
    result_count: int
    query: str


class ClaudeSkillProgressData(ClaudeStorageModel):
    """Progress data for skill operations."""

    type: Literal["skill_progress"]
    prompt: str | None = None
    agent_id: str | None = None


class ClaudeTaskProgressData(ClaudeStorageModel):
    """Progress data for task tracking."""

    type: Literal["task_progress"]
    task_id: str | None = None
    task_type: str | None = None
    message: str | None = None


class ClaudeToolProgressData(ClaudeStorageModel):
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


class ClaudeProgressEntry(ClaudeEntryBase):
    """Progress entry for tracking tool execution status (older Claude Code versions)."""

    type: Literal["progress"]
    data: ClaudeProgressData
    tool_use_id: str | None = Field(default=None, alias="toolUseID")
    parent_tool_use_id: str | None = Field(default=None, alias="parentToolUseID")


# =============================================================================
# Attachment entry
# =============================================================================


class ClaudeAttachment(BaseModel):
    """Attachment payload, discriminated by ``type``.

    Claude Code has dozens of attachment types (``hook_success``, ``file``,
    ``edited_text_file``, ``deferred_tools_delta``, ``date``, ``task_status``, ...) and adds
    new ones often, so the payload is kept as-is: the type is typed, everything else is
    available as extra fields (``model_extra``) and written back unchanged.
    """

    model_config = ConfigDict(extra="allow")

    type: str


class ClaudeAttachmentEntry(ClaudeEntryBase):
    """Context attached to the conversation (hook output, file contents, reminders, ...).

    Attachment entries are part of the ``parentUuid`` chain: assistant and user entries
    often have an attachment as their parent, so chain walks must pass through them.
    """

    type: Literal["attachment"]
    attachment: ClaudeAttachment
    rendered: list[Any] | None = None
    """How the attachment was rendered into the prompt, if recorded."""
    rendered_role: str | None = None
    rendered_beside_tool_result: bool | None = None
    rendered_in_human_turn: list[Any] | None = None


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


class ClaudeLastPromptEntry(ClaudeStorageModel):
    """Last prompt entry tracking the most recent user prompt."""

    type: Literal["last-prompt"]
    last_prompt: str | None = None
    """The prompt; newer entries mark only the message it led to (``leaf_uuid``)."""
    leaf_uuid: str | None = None
    session_id: str
    explicit: bool | None = None


# =============================================================================
# PR link entry
# =============================================================================


class ClaudePrLinkEntry(ClaudeStorageModel):
    """PR link entry recording a pull request created during a session."""

    type: Literal["pr-link"]
    session_id: str
    pr_number: int
    pr_url: str
    pr_repository: str
    timestamp: str


# =============================================================================
# Custom title entry
# =============================================================================


class ClaudeCustomTitleEntry(ClaudeStorageModel):
    """User-set custom title for a session."""

    type: Literal["custom-title"]
    session_id: str
    custom_title: str


# =============================================================================
# AI title entry
# =============================================================================


class ClaudeAiTitleEntry(ClaudeStorageModel):
    """AI-generated session title.

    Distinct from ClaudeCustomTitleEntry: user renames always win over
    AI titles in read preference.
    """

    type: Literal["ai-title"]
    session_id: str
    ai_title: str


# =============================================================================
# Task summary entry
# =============================================================================


class ClaudeTaskSummaryEntry(ClaudeStorageModel):
    """Periodic fork-generated summary of what the agent is currently doing.

    Written every min(5 steps, 2min) by forking the main thread mid-turn
    so ``claude ps`` can show something more useful than the last user prompt.
    """

    type: Literal["task-summary"]
    session_id: str
    summary: str
    timestamp: str


# =============================================================================
# Tag entry
# =============================================================================


class ClaudeTagEntry(ClaudeStorageModel):
    """Session tag entry (searchable in /resume)."""

    type: Literal["tag"]
    session_id: str
    tag: str


# =============================================================================
# Agent name / color / setting entries
# =============================================================================


class ClaudeAgentNameEntry(ClaudeStorageModel):
    """Agent's custom name (from /rename or swarm)."""

    type: Literal["agent-name"]
    session_id: str
    agent_name: str


class ClaudeAgentColorEntry(ClaudeStorageModel):
    """Agent's color (from /rename or swarm)."""

    type: Literal["agent-color"]
    session_id: str
    agent_color: str


class ClaudeAgentSettingEntry(ClaudeStorageModel):
    """Agent definition used (from --agent flag or settings.agent)."""

    type: Literal["agent-setting"]
    session_id: str
    agent_setting: str


# =============================================================================
# Mode entry
# =============================================================================


class ClaudeModeEntry(ClaudeStorageModel):
    """Session mode entry for coordinator/normal detection."""

    type: Literal["mode"]
    session_id: str
    mode: Literal["coordinator", "normal"]


# =============================================================================
# Worktree state entry
# =============================================================================


class ClaudePersistedWorktreeSession(ClaudeStorageModel):
    """Worktree session state persisted to the transcript for resume."""

    original_cwd: str
    worktree_path: str
    worktree_name: str
    worktree_branch: str | None = None
    original_branch: str | None = None
    original_head_commit: str | None = None
    session_id: str
    tmux_session_name: str | None = None
    hook_based: bool | None = None


class ClaudeWorktreeStateEntry(ClaudeStorageModel):
    """Records whether the session is currently inside a worktree.

    Last-wins: an enter writes the session, an exit writes null.
    On --resume, restored only if the worktreePath still exists on disk.
    """

    type: Literal["worktree-state"]
    session_id: str
    worktree_session: ClaudePersistedWorktreeSession | None = None


# =============================================================================
# Content replacement entry
# =============================================================================


class ClaudeContentReplacementRecord(ClaudeStorageModel):
    """Records content blocks replaced with smaller stubs for prompt cache stability."""

    kind: Literal["tool-result"]
    tool_use_id: str
    replacement: str


class ClaudeContentReplacementEntry(ClaudeStorageModel):
    """Content replacement entry for resume reconstruction.

    When agentId is set, the record belongs to a subagent sidechain;
    when absent, it's main-thread.
    """

    type: Literal["content-replacement"]
    session_id: str
    agent_id: str | None = None
    replacements: list[ClaudeContentReplacementRecord]


# =============================================================================
# Attribution snapshot entry
# =============================================================================


class ClaudeFileAttributionState(ClaudeStorageModel):
    """Per-file attribution state tracking Claude's character contributions."""

    content_hash: str
    """SHA-256 hash of file content."""
    claude_contribution: int
    """Characters written by Claude."""
    mtime: int
    """File modification time."""


class ClaudeAttributionSnapshotEntry(ClaudeStorageModel):
    """Attribution snapshot tracking character-level contributions for commit attribution."""

    type: Literal["attribution-snapshot"]
    message_id: str
    surface: str
    """Client surface (cli, ide, web, api)."""
    file_states: dict[str, ClaudeFileAttributionState]
    prompt_count: int | None = None
    prompt_count_at_last_commit: int | None = None
    permission_prompt_count: int | None = None
    permission_prompt_count_at_last_commit: int | None = None
    escape_count: int | None = None
    escape_count_at_last_commit: int | None = None


# =============================================================================
# Speculation accept entry
# =============================================================================


class ClaudeSpeculationAcceptEntry(ClaudeStorageModel):
    """Records a speculation accept with time saved."""

    type: Literal["speculation-accept"]
    timestamp: str
    time_saved_ms: int


# =============================================================================
# Context collapse entries
# =============================================================================


class ClaudeContextCollapseCommitEntry(ClaudeStorageModel):
    """Persisted context-collapse commit.

    The archived messages themselves are NOT persisted — they're already
    in the transcript as ordinary user/assistant messages. Only enough is
    persisted to reconstruct the splice instruction and summary placeholder.
    """

    type: Literal["marble-origami-commit"]
    session_id: str
    collapse_id: str
    """16-digit collapse ID."""
    summary_uuid: str
    """The summary placeholder's uuid."""
    summary_content: str
    """Full `<collapsed id="...">text</collapsed>` string for the placeholder."""
    summary: str
    """Plain summary text."""
    first_archived_uuid: str
    """Span start boundary."""
    last_archived_uuid: str
    """Span end boundary."""


class ClaudeContextCollapseStagedSpan(ClaudeStorageModel):
    """A staged span within a context collapse snapshot."""

    start_uuid: str
    end_uuid: str
    summary: str
    risk: float
    staged_at: int


class ClaudeContextCollapseSnapshotEntry(ClaudeStorageModel):
    """Snapshot of staged queue and spawn trigger state.

    Unlike commits (append-only, replay-all), snapshots are last-wins —
    only the most recent snapshot entry is applied on restore.
    """

    type: Literal["marble-origami-snapshot"]
    session_id: str
    staged: list[ClaudeContextCollapseStagedSpan]
    armed: bool
    """Spawn trigger state."""
    last_spawn_tokens: int


# =============================================================================
# Session metadata entries (no uuid; last-wins unless noted)
# =============================================================================


class ClaudePermissionModeEntry(ClaudeStorageModel):
    """Permission mode of the session (last wins)."""

    type: Literal["permission-mode"]
    session_id: str
    permission_mode: str


class ClaudeModelCostUsage(ClaudeStorageModel):
    """Per-model token usage and cost in a cost-state entry."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_creation_ephemeral_5m_input_tokens: int = Field(
        default=0, alias="cacheCreationEphemeral5mInputTokens"
    )
    cache_creation_ephemeral_1h_input_tokens: int = Field(
        default=0, alias="cacheCreationEphemeral1hInputTokens"
    )
    thinking_tokens: int = 0
    web_search_requests: int = 0
    cost_usd: float = Field(default=0.0, alias="costUSD")


class ClaudeCostStateEntry(ClaudeStorageModel):
    """Accumulated cost and duration of the session, for restoring ``/cost`` on resume.

    Snapshot semantics: the last entry holds the session totals.
    """

    type: Literal["cost-state"]
    session_id: str
    total_cost_usd: float = Field(alias="totalCostUSD")
    total_api_duration: int = Field(default=0, alias="totalAPIDuration")
    """Milliseconds spent in API requests."""
    total_api_duration_without_retries: int = Field(
        default=0, alias="totalAPIDurationWithoutRetries"
    )
    total_tool_duration: int = 0
    total_duration: int = 0
    total_lines_added: int = 0
    total_lines_removed: int = 0
    start_time: int | None = None
    """Epoch milliseconds."""
    model_usage: dict[str, ClaudeModelCostUsage] = Field(default_factory=dict)
    has_unknown_model_cost: bool = False


class ClaudeToolsUsedEntry(ClaudeStorageModel):
    """Names of the tools used in the session."""

    type: Literal["tools-used"]
    session_id: str
    tools: list[str]


class ClaudeRelocatedEntry(ClaudeStorageModel):
    """The session continued in another working directory."""

    type: Literal["relocated"]
    session_id: str
    relocated_cwd: str


class ClaudeDerivedSession(ClaudeStorageModel):
    """A session this session was derived from."""

    id: str
    type: str
    via: str
    """How it was derived (``compact``, ``clear``, ``resume``, ``subprocess``, ...)."""
    started: str | None = None


class ClaudeDerivedFromEntry(ClaudeStorageModel):
    """Records the sessions this session continues (after /clear, compaction, resume)."""

    type: Literal["derived-from"]
    session_id: str
    v: int | None = None
    sessions: list[ClaudeDerivedSession]


class ClaudeForkContextRefEntry(ClaudeStorageModel):
    """A forked subagent's reference to the parent conversation it inherited."""

    type: Literal["fork-context-ref"]
    agent_id: str | None = None
    parent_session_id: str
    parent_last_uuid: str
    """Last parent-session message the fork's context includes."""
    context_length: int | None = None


class ClaudeFileBackup(ClaudeStorageModel):
    """A backed-up file version in ``~/.claude/file-history/<sessionId>/``."""

    backup_file_name: str | None = None
    """``None`` when the file did not exist at that point."""
    version: int
    backup_time: str
    real_parent_dir: str | None = None


class ClaudeFileHistoryDeltaEntry(ClaudeStorageModel):
    """Adds one file backup to an earlier file-history snapshot."""

    type: Literal["file-history-delta"]
    message_id: str
    snapshot_message_id: str
    tracking_path: str
    backup: ClaudeFileBackup
    timestamp: str


# =============================================================================
# Top-level discriminated union
# =============================================================================

KnownClaudeJSONLEntry = Annotated[
    ClaudeUserEntry
    | ClaudeAssistantEntry
    | ClaudeQueueOperationEntry
    | ClaudeSystemEntry
    | ClaudeSummaryEntry
    | ClaudeFileHistoryEntry
    | ClaudeProgressEntry
    | ClaudeSavedHookContextEntry
    | ClaudeLastPromptEntry
    | ClaudePrLinkEntry
    | ClaudeCustomTitleEntry
    | ClaudeAiTitleEntry
    | ClaudeTaskSummaryEntry
    | ClaudeTagEntry
    | ClaudeAgentNameEntry
    | ClaudeAgentColorEntry
    | ClaudeAgentSettingEntry
    | ClaudeModeEntry
    | ClaudeWorktreeStateEntry
    | ClaudeContentReplacementEntry
    | ClaudeAttributionSnapshotEntry
    | ClaudeSpeculationAcceptEntry
    | ClaudeContextCollapseCommitEntry
    | ClaudeContextCollapseSnapshotEntry
    | ClaudeAttachmentEntry
    | ClaudePermissionModeEntry
    | ClaudeCostStateEntry
    | ClaudeToolsUsedEntry
    | ClaudeRelocatedEntry
    | ClaudeDerivedFromEntry
    | ClaudeForkContextRefEntry
    | ClaudeFileHistoryDeltaEntry,
    Field(discriminator="type"),
]
"""Discriminated union of the JSONL entry types these models know."""


ClaudeChainEntry = (
    ClaudeUserEntry
    | ClaudeAssistantEntry
    | ClaudeAttachmentEntry
    | ClaudeCompactBoundaryEntry
    | ClaudeTurnDurationEntry
    | ClaudeApiErrorEntry
    | ClaudeLocalCommandEntry
    | ClaudeStopHookSummaryEntry
    | ClaudeAwaySummaryEntry
    | ClaudeInformationalEntry
    | ClaudeModelRefusalFallbackEntry
    | ClaudeGenericSystemEntry
    | ClaudeProgressEntry
    | ClaudeSavedHookContextEntry
)
"""The loaded entry types that take part in the ``parentUuid`` chain.

All of them derive from :class:`ClaudeEntryBase` (which exposes ``uuid`` and
``parent_uuid``). The union works with ``isinstance`` to narrow a :data:`ClaudeJSONLEntry`.
"""


class ClaudeUnknownEntry(BaseModel):
    """An entry of a type these models don't know, kept as it is.

    Claude Code adds entry types often (``api-request``, ``atis-latch``, ...); they
    load as this instead of failing, and are written back unchanged.
    """

    model_config = ConfigDict(extra="allow")

    type: str


def _entry_tags(annotation: Any) -> set[str]:
    """The ``type`` tags of the entry models in ``annotation`` (unions and models)."""
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return _entry_tags(annotation.model_fields["type"].annotation)
    if get_origin(annotation) is Literal:
        return {arg for arg in get_args(annotation) if isinstance(arg, str)}
    return {tag for arg in get_args(annotation) for tag in _entry_tags(arg)}


@cache
def chain_entry_types() -> frozenset[str]:
    """The ``type`` tags of :data:`ClaudeChainEntry` (entries that take part in the chain)."""
    return frozenset(_entry_tags(ClaudeChainEntry))


@cache
def known_entry_types() -> frozenset[str]:
    """The ``type`` tags of :data:`KnownClaudeJSONLEntry`."""
    return frozenset(_entry_tags(KnownClaudeJSONLEntry))


def _entry_kind(value: Any) -> str:
    match value:
        case ClaudeUnknownEntry():
            return "unknown"
        case BaseModel():
            return "known"
        case {"type": str(tag)} if tag in known_entry_types():
            return "known"
        case _:
            return "unknown"


ClaudeJSONLEntry = Annotated[
    Annotated[KnownClaudeJSONLEntry, Tag("known")] | Annotated[ClaudeUnknownEntry, Tag("unknown")],
    Discriminator(_entry_kind),
]
"""A JSONL entry: one of the known types, else :class:`ClaudeUnknownEntry`."""
