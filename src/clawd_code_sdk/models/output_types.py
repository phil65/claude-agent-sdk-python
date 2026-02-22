"""Tool output type definitions matching the actual ``tool_use_result`` wire format.

These TypedDicts describe the structured data that the Claude Code CLI attaches
to ``UserMessage.tool_use_result`` after each tool execution. This is the real
data available to SDK consumers — richer than the plain-text summary the model
sees in ``ToolResultBlock.content``.

The shapes are derived from the ``ToolOutputSchemas`` type definitions in the
``@anthropic-ai/claude-agent-sdk`` npm package (auto-generated from JSON Schema).
"""

from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict

from clawd_code_sdk.models.input_types import AskUserQuestionOption, TodoItem  # noqa: TC001


# ---------------------------------------------------------------------------
# Agent (Task tool)
# ---------------------------------------------------------------------------


class AgentOutputTextContent(TypedDict):
    """A text content block in agent output."""

    type: Literal["text"]
    text: str


class AgentServerToolUse(TypedDict):
    """Server-side tool usage statistics."""

    web_search_requests: int
    web_fetch_requests: int


class AgentCacheCreation(TypedDict):
    """Cache creation token statistics."""

    ephemeral_1h_input_tokens: int
    ephemeral_5m_input_tokens: int


class AgentOutputUsage(TypedDict):
    """Token usage statistics from an agent task."""

    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int | None
    cache_read_input_tokens: int | None
    server_tool_use: AgentServerToolUse | None
    service_tier: Literal["standard", "priority", "batch"] | None
    cache_creation: AgentCacheCreation | None


class AgentCompletedOutput(TypedDict):
    """Output from the Task tool when the agent completed successfully."""

    status: Literal["completed"]
    agentId: str
    content: list[AgentOutputTextContent]
    totalToolUseCount: int
    totalDurationMs: int
    totalTokens: int
    usage: AgentOutputUsage
    prompt: str


class AgentAsyncLaunchedOutput(TypedDict):
    """Output from the Task tool when an agent was launched asynchronously."""

    status: Literal["async_launched"]
    agentId: str
    description: str
    prompt: str
    outputFile: str
    canReadOutputFile: NotRequired[bool]


class AgentSubAgentEnteredOutput(TypedDict):
    """Output from the Task tool when entering a sub-agent context."""

    status: Literal["sub_agent_entered"]
    description: str
    message: str


AgentOutput = AgentCompletedOutput | AgentAsyncLaunchedOutput | AgentSubAgentEnteredOutput


# ---------------------------------------------------------------------------
# Bash
# ---------------------------------------------------------------------------


class BashOutput(TypedDict):
    """``tool_use_result`` for the Bash tool."""

    stdout: str
    """Standard output from the command."""
    stderr: str
    """Standard error from the command."""
    interrupted: bool
    """Whether the command was interrupted."""
    isImage: NotRequired[bool]
    """Whether the output is an image."""
    noOutputExpected: NotRequired[bool]
    """Whether the command is expected to produce no output on success."""
    backgroundTaskId: NotRequired[str]
    """Task ID when ``run_in_background=true`` was used."""
    backgroundedByUser: NotRequired[bool]
    """True if the user manually backgrounded the command with Ctrl+B."""
    rawOutputPath: NotRequired[str]
    """Path to raw output file for large MCP tool outputs."""
    dangerouslyDisableSandbox: NotRequired[bool]
    """Whether sandbox mode was overridden."""
    returnCodeInterpretation: NotRequired[str]
    """Semantic interpretation for non-error exit codes with special meaning."""
    structuredContent: NotRequired[list[Any]]
    """Structured content blocks."""
    persistedOutputPath: NotRequired[str]
    """Path to persisted full output (when output is too large for inline)."""
    persistedOutputSize: NotRequired[int]
    """Total size of the output in bytes (when output is too large for inline)."""


# ---------------------------------------------------------------------------
# TaskOutput (checking background tasks — tool name "TaskOutput")
# ---------------------------------------------------------------------------


class TaskInfo(TypedDict):
    """Information about a background task."""

    task_id: str
    task_type: str
    status: str
    description: str
    output: str
    exitCode: int | None


class TaskOutputResult(TypedDict):
    """``tool_use_result`` for the TaskOutput tool (background task polling)."""

    retrieval_status: str
    """Status of the retrieval: ``"not_ready"``, ``"ready"``, etc."""
    task: TaskInfo


# ---------------------------------------------------------------------------
# TaskStop
# ---------------------------------------------------------------------------


class TaskStopOutput(TypedDict):
    """``tool_use_result`` for the TaskStop tool."""

    message: str
    task_id: str
    task_type: str
    command: NotRequired[str]


# ---------------------------------------------------------------------------
# ExitPlanMode
# ---------------------------------------------------------------------------


class ExitPlanModeOutput(TypedDict):
    """``tool_use_result`` for the ExitPlanMode tool."""

    plan: str | None
    """The plan that was presented to the user."""
    isAgent: bool
    filePath: NotRequired[str]
    """The file path where the plan was saved."""
    hasTaskTool: NotRequired[bool]
    """Whether the Task tool is available in the current context."""
    awaitingLeaderApproval: NotRequired[bool]
    """When true, the teammate has sent a plan approval request to the team leader."""
    requestId: NotRequired[str]
    """Unique identifier for the plan approval request."""


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


class ReadFileInfo(TypedDict):
    """Nested file info inside a Read tool result (text mode)."""

    filePath: str
    content: str
    numLines: int
    startLine: int
    totalLines: int


class ReadTextOutput(TypedDict):
    """``tool_use_result`` for the Read tool (text files)."""

    type: Literal["text"]
    file: ReadFileInfo


class ReadImageDimensions(TypedDict):
    """Image dimension info for coordinate mapping."""

    originalWidth: NotRequired[int]
    originalHeight: NotRequired[int]
    displayWidth: NotRequired[int]
    displayHeight: NotRequired[int]


class ReadImageFileInfo(TypedDict):
    """Nested file info for image reads."""

    base64: str
    """Base64-encoded image data."""
    type: Literal["image/jpeg", "image/png", "image/gif", "image/webp"]
    """The MIME type of the image."""
    originalSize: int
    """Original file size in bytes."""
    dimensions: NotRequired[ReadImageDimensions]


class ReadImageOutput(TypedDict):
    """``tool_use_result`` for the Read tool (image files)."""

    type: Literal["image"]
    file: ReadImageFileInfo


class ReadNotebookFileInfo(TypedDict):
    """Nested file info for notebook reads."""

    filePath: str
    cells: list[Any]


class ReadNotebookOutput(TypedDict):
    """``tool_use_result`` for the Read tool (Jupyter notebooks)."""

    type: Literal["notebook"]
    file: ReadNotebookFileInfo


class ReadPdfFileInfo(TypedDict):
    """Nested file info for PDF reads."""

    filePath: str
    base64: str
    """Base64-encoded PDF data."""
    originalSize: int


class ReadPdfOutput(TypedDict):
    """``tool_use_result`` for the Read tool (PDF files)."""

    type: Literal["pdf"]
    file: ReadPdfFileInfo


class ReadPartsFileInfo(TypedDict):
    """Nested file info for PDF parts (extracted page images)."""

    filePath: str
    originalSize: int
    count: int
    """Number of pages extracted."""
    outputDir: str
    """Directory containing extracted page images."""


class ReadPartsOutput(TypedDict):
    """``tool_use_result`` for the Read tool (PDF parts extraction)."""

    type: Literal["parts"]
    file: ReadPartsFileInfo


ReadOutput = ReadTextOutput | ReadImageOutput | ReadNotebookOutput | ReadPdfOutput | ReadPartsOutput


# ---------------------------------------------------------------------------
# Edit
# ---------------------------------------------------------------------------


class StructuredPatchHunk(TypedDict):
    """A single hunk in a structured patch."""

    oldStart: int
    oldLines: int
    newStart: int
    newLines: int
    lines: list[str]
    """Diff lines prefixed with ``' '`` (context), ``'+'`` (added), or ``'-'`` (removed)."""


class GitDiff(TypedDict):
    """Git diff information for a file change."""

    filename: str
    status: Literal["modified", "added"]
    additions: int
    deletions: int
    changes: int
    patch: str


class EditOutput(TypedDict):
    """``tool_use_result`` for the Edit tool."""

    filePath: str
    oldString: str
    newString: str
    originalFile: str
    structuredPatch: list[StructuredPatchHunk]
    userModified: bool
    replaceAll: bool
    gitDiff: NotRequired[GitDiff]


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


class WriteOutput(TypedDict):
    """``tool_use_result`` for the Write tool."""

    type: Literal["create", "update"]
    filePath: str
    content: str
    structuredPatch: list[StructuredPatchHunk]
    originalFile: str | None
    gitDiff: NotRequired[GitDiff]


# ---------------------------------------------------------------------------
# Glob
# ---------------------------------------------------------------------------


class GlobOutput(TypedDict):
    """``tool_use_result`` for the Glob tool."""

    durationMs: int
    numFiles: int
    filenames: list[str]
    truncated: bool
    """Whether results were truncated (limited to 100 files)."""


# ---------------------------------------------------------------------------
# Grep
# ---------------------------------------------------------------------------


class GrepOutput(TypedDict):
    """``tool_use_result`` for the Grep tool (all modes)."""

    mode: NotRequired[Literal["content", "files_with_matches", "count"]]
    numFiles: int
    filenames: list[str]
    content: NotRequired[str]
    """Matching lines (content mode)."""
    numLines: NotRequired[int]
    """Number of matching lines (content mode)."""
    numMatches: NotRequired[int]
    """Number of matches (count mode)."""
    appliedLimit: NotRequired[int]
    """The head_limit that was applied."""
    appliedOffset: NotRequired[int]
    """The offset that was applied."""


# ---------------------------------------------------------------------------
# NotebookEdit
# ---------------------------------------------------------------------------


class NotebookEditOutput(TypedDict):
    """``tool_use_result`` for the NotebookEdit tool."""

    new_source: str
    cell_id: NotRequired[str]
    cell_type: Literal["code", "markdown"]
    language: str
    edit_mode: str
    error: NotRequired[str]
    notebook_path: str
    original_file: str
    """The original notebook content before modification."""
    updated_file: str
    """The updated notebook content after modification."""


# ---------------------------------------------------------------------------
# WebFetch
# ---------------------------------------------------------------------------


class WebFetchOutput(TypedDict):
    """``tool_use_result`` for the WebFetch tool."""

    bytes: int
    """Size of the fetched content in bytes."""
    code: int
    """HTTP response code."""
    codeText: str
    """HTTP response code text."""
    result: str
    """Processed result from applying the prompt to the content."""
    durationMs: int
    url: str


# ---------------------------------------------------------------------------
# WebSearch
# ---------------------------------------------------------------------------


class WebSearchHit(TypedDict):
    """A single search result hit."""

    title: str
    url: str


class WebSearchToolResult(TypedDict):
    """A structured search result entry."""

    tool_use_id: str
    content: list[WebSearchHit]


class WebSearchOutput(TypedDict):
    """``tool_use_result`` for the WebSearch tool."""

    query: str
    results: list[WebSearchToolResult | str]
    """Search results and/or text commentary from the model."""
    durationSeconds: float


# ---------------------------------------------------------------------------
# AskUserQuestion
# ---------------------------------------------------------------------------


class AskUserQuestionItem(TypedDict):
    """A single question that was asked."""

    question: str
    header: str
    options: list[AskUserQuestionOption]
    multiSelect: bool


class AskUserQuestionOutput(TypedDict):
    """``tool_use_result`` for the AskUserQuestion tool."""

    questions: list[AskUserQuestionItem]
    answers: dict[str, str]
    """Maps question text to answer string. Multi-select answers are comma-separated."""


# ---------------------------------------------------------------------------
# TodoWrite
# ---------------------------------------------------------------------------


class TodoWriteOutput(TypedDict):
    """``tool_use_result`` for the TodoWrite tool."""

    oldTodos: list[TodoItem]
    newTodos: list[TodoItem]


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------

McpOutput = str
"""Output from a generic MCP tool call (plain string)."""


class McpResourceEntry(TypedDict):
    """A single MCP resource entry."""

    uri: str
    name: str
    mimeType: NotRequired[str]
    description: NotRequired[str]
    server: str


ListMcpResourcesOutput = list[McpResourceEntry]
"""``tool_use_result`` for the ListMcpResources tool."""


class ReadMcpResourceContentItem(TypedDict):
    """A single content item from an MCP resource."""

    uri: str
    mimeType: NotRequired[str]
    text: NotRequired[str]


class ReadMcpResourceOutput(TypedDict):
    """``tool_use_result`` for the ReadMcpResource tool."""

    contents: list[ReadMcpResourceContentItem]


class SubscribeMcpResourceOutput(TypedDict):
    """``tool_use_result`` for the SubscribeMcpResource tool."""

    subscribed: bool
    subscriptionId: str


class UnsubscribeMcpResourceOutput(TypedDict):
    """``tool_use_result`` for the UnsubscribeMcpResource tool."""

    unsubscribed: bool


class SubscribePollingOutput(TypedDict):
    """``tool_use_result`` for the SubscribePolling tool."""

    subscribed: bool
    subscriptionId: str


class UnsubscribePollingOutput(TypedDict):
    """``tool_use_result`` for the UnsubscribePolling tool."""

    unsubscribed: bool


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class ConfigOutput(TypedDict):
    """``tool_use_result`` for the Config tool."""

    success: bool
    operation: NotRequired[Literal["get", "set"]]
    setting: NotRequired[str]
    value: NotRequired[Any]
    previousValue: NotRequired[Any]
    newValue: NotRequired[Any]
    error: NotRequired[str]


# ---------------------------------------------------------------------------
# EnterWorktree
# ---------------------------------------------------------------------------


class EnterWorktreeOutput(TypedDict):
    """``tool_use_result`` for the EnterWorktree tool."""

    worktreePath: str
    worktreeBranch: NotRequired[str]
    message: str


# ---------------------------------------------------------------------------
# Union of all tool_use_result types
# ---------------------------------------------------------------------------

ToolUseResult = (
    AgentOutput
    | BashOutput
    | TaskOutputResult
    | TaskStopOutput
    | ExitPlanModeOutput
    | ReadOutput
    | EditOutput
    | WriteOutput
    | GlobOutput
    | GrepOutput
    | NotebookEditOutput
    | WebFetchOutput
    | WebSearchOutput
    | AskUserQuestionOutput
    | TodoWriteOutput
    | ReadMcpResourceOutput
    | SubscribeMcpResourceOutput
    | UnsubscribeMcpResourceOutput
    | SubscribePollingOutput
    | UnsubscribePollingOutput
    | ConfigOutput
    | EnterWorktreeOutput
)

#: Backwards-compatible aliases for names previously in ``tool_use_results.py``.
WriteToolUseResult = WriteOutput
EditToolUseResult = EditOutput
ReadToolUseResult = ReadTextOutput
BashToolUseResult = BashOutput
TodoUseResultItem = TodoItem
TodoWriteToolUseResult = TodoWriteOutput


#: Mapping from tool name to its ``tool_use_result`` type.
TOOL_USE_RESULT_TYPES: dict[str, type[Any]] = {
    "Task": AgentCompletedOutput,
    "Bash": BashOutput,
    "TaskOutput": TaskOutputResult,
    "TaskStop": TaskStopOutput,
    "ExitPlanMode": ExitPlanModeOutput,
    "Read": ReadTextOutput,
    "Edit": EditOutput,
    "Write": WriteOutput,
    "Glob": GlobOutput,
    "Grep": GrepOutput,
    "NotebookEdit": NotebookEditOutput,
    "WebFetch": WebFetchOutput,
    "WebSearch": WebSearchOutput,
    "AskUserQuestion": AskUserQuestionOutput,
    "TodoWrite": TodoWriteOutput,
    "ListMcpResources": McpResourceEntry,
    "ReadMcpResource": ReadMcpResourceOutput,
    "SubscribeMcpResource": SubscribeMcpResourceOutput,
    "UnsubscribeMcpResource": UnsubscribeMcpResourceOutput,
    "SubscribePolling": SubscribePollingOutput,
    "UnsubscribePolling": UnsubscribePollingOutput,
    "Config": ConfigOutput,
    "EnterWorktree": EnterWorktreeOutput,
}
