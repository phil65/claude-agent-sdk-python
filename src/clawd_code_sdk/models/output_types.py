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

from clawd_code_sdk.models import AskUserQuestionOption, TodoItem  # noqa: TC001
from clawd_code_sdk.models.base import ToolName  # noqa: TC001


# ---------------------------------------------------------------------------
# Agent (Task tool)
# ---------------------------------------------------------------------------
ServiceTier = Literal["standard", "priority", "batch"]


class SDKDeferredToolUse(TypedDict):
    """A deferred tool use from a completed agent result."""

    id: str
    """Tool use ID."""
    name: str
    """Tool name."""
    input: dict[str, Any]
    """Tool input parameters."""


MimeType = Literal["image/jpeg", "image/png", "image/gif", "image/webp"]
Status = Literal["running", "completed", "failed"]


class AgentOutputTextContent(TypedDict):
    """A text content block in agent output."""

    type: Literal["text"]
    """Content type, always 'text'."""
    text: str
    """The text content."""


class AgentServerToolUse(TypedDict):
    """Server-side tool usage statistics."""

    web_search_requests: int
    """Number of web search requests made."""
    web_fetch_requests: int
    """Number of web fetch requests made."""


class AgentCacheCreation(TypedDict):
    """Cache creation token statistics."""

    ephemeral_1h_input_tokens: int
    """Tokens for 1-hour ephemeral cache entries."""
    ephemeral_5m_input_tokens: int
    """Tokens for 5-minute ephemeral cache entries."""


class AgentOutputUsage(TypedDict):
    """Token usage statistics from an agent task."""

    input_tokens: int
    """Number of input tokens consumed."""
    output_tokens: int
    """Number of output tokens generated."""
    cache_creation_input_tokens: int | None
    """Tokens used to create cache entries."""
    cache_read_input_tokens: int | None
    """Tokens read from cache."""
    server_tool_use: AgentServerToolUse | None
    """Server-side tool usage statistics."""
    service_tier: ServiceTier | None
    """Service tier used for the request."""
    cache_creation: AgentCacheCreation | None
    """Cache creation statistics."""


class ToolStats(TypedDict):
    """Tool usage statistics from an agent task."""

    readCount: int
    """Number of read tool calls."""
    searchCount: int
    """Number of search tool calls."""
    bashCount: int
    """Number of bash tool calls."""
    editFileCount: int
    """Number of edit file tool calls."""
    linesAdded: int
    """Number of lines added by edit file tool calls."""
    linesRemoved: int
    """Number of lines removed by edit file tool calls."""
    otherToolCount: int
    """Number of other tool calls."""


class AgentCompletedOutput(TypedDict):
    """Output from the Task tool when the agent completed successfully."""

    status: Literal["completed"]
    """Agent completion status."""
    agentId: str
    """ID of the agent that ran."""
    agentType: NotRequired[str]
    """Type of the agent that ran."""
    content: list[AgentOutputTextContent]
    """Text content blocks produced by the agent."""
    totalToolUseCount: int
    """Total number of tool calls made."""
    totalDurationMs: int
    """Total execution duration in milliseconds."""
    totalTokens: int
    """Total tokens used."""
    usage: AgentOutputUsage
    """Detailed token usage statistics."""
    toolStats: NotRequired[ToolStats]
    """Tool usage statistics."""
    prompt: str
    """The prompt that was given to the agent."""


class AgentAsyncLaunchedOutput(TypedDict):
    """Output from the Task tool when an agent was launched asynchronously."""

    status: Literal["async_launched"]
    """Indicates the agent was launched in the background."""
    isAsync: Literal[True]
    """Always True for async-launched agents."""
    agentId: str
    """The ID of the async agent."""
    description: str
    """The description of the task."""
    prompt: str
    """The prompt for the agent."""
    outputFile: str
    """Path to the output file for checking agent progress."""
    canReadOutputFile: NotRequired[bool]
    """Whether the calling agent has Read/Bash tools to check progress."""


# class AgentQueuedToRunningOutput(TypedDict):
#     """Output from the Task tool when an agent is queued to run."""

#     status: Literal["queued_to_running"]
#     """Indicates the agent is queued to run."""
#     agentId: str
#     """The ID of the async agent."""
#     prompt: str
#     """The prompt for the agent."""


AgentOutput = AgentCompletedOutput | AgentAsyncLaunchedOutput  # | AgentQueuedToRunningOutput


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
    assistantAutoBackgrounded: NotRequired[bool]
    """True if assistant-mode auto-backgrounded a long-running blocking command."""
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
    staleReadFileStateHint: NotRequired[str]
    """Model-facing note listing readFileState entries whose mtime bumped during this command."""
    # tokenSaverOutput: NotRequired[str]
    # """Compressed output sent to model when token-saver is active (UI still uses stdout)."""


# ---------------------------------------------------------------------------
# TaskOutput (checking background tasks — tool name "TaskOutput")
# ---------------------------------------------------------------------------


class TaskInfo(TypedDict):
    """Information about a background task."""

    task_id: str
    task_type: Literal["local_bash", "agent"]
    status: Status
    description: str
    output: str
    exitCode: int | None


class TaskOutputResult(TypedDict):
    """``tool_use_result`` for the TaskOutput tool (background task polling)."""

    retrieval_status: Literal["completed", "timeout", "running"]
    """Status of the retrieval."""
    task: TaskInfo


# ---------------------------------------------------------------------------
# BashOutput (checking background shells — tool name "BashOutput")
# ---------------------------------------------------------------------------


class BashOutputOutput(TypedDict):
    """``tool_use_result`` for the BashOutput tool (background shell output retrieval).

    Not part of the official SDK ToolOutputSchemas as of SDK v0.2.62.
    Shape derived from: https://github.com/kzahel/yepanywhere/blob/main/packages/shared/src/claude-sdk-schema/tool/ToolResultSchemas.ts
    """

    shellId: NotRequired[str]
    """ID of the background shell."""
    command: NotRequired[str]
    """The command that was executed."""
    status: NotRequired[Status]
    """Current status of the command."""
    exitCode: NotRequired[int | None]
    """Exit code of the command, or None if still running."""
    stdout: NotRequired[str]
    """Standard output."""
    stderr: NotRequired[str]
    """Standard error."""
    stdoutLines: NotRequired[int]
    """Number of lines in stdout."""
    stderrLines: NotRequired[int]
    """Number of lines in stderr."""
    timestamp: NotRequired[str]
    """Timestamp of the output."""


# ---------------------------------------------------------------------------
# KillShell (kill background shell — tool name "KillBash")
# ---------------------------------------------------------------------------


class KillShellOutput(TypedDict):
    """``tool_use_result`` for the KillBash tool.

    Not part of the official SDK ToolOutputSchemas as of SDK v0.2.62.
    Shape derived from: https://github.com/kzahel/yepanywhere/blob/main/packages/shared/src/claude-sdk-schema/tool/ToolResultSchemas.ts
    """

    message: NotRequired[str]
    """Status message."""
    shell_id: NotRequired[str]
    """ID of the shell that was killed."""


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
    planWasEdited: NotRequired[bool]
    """Whether the plan was edited by the user."""
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
    """The path to the file that was read."""
    content: str
    """The read content of the file."""
    numLines: int
    """The number of lines read."""
    startLine: int
    """The line number where reading started from."""
    totalLines: int
    """The total number of lines in the file."""
    # resultWasTruncated: NotRequired[bool]
    # """Whether the result was truncated due to the maximum token limit."""


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
    type: MimeType
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


class FileUnchangedOutput(TypedDict):
    """Read tool output when the file has not changed."""

    type: Literal["file_unchanged"]
    filePath: str


ReadOutput = (
    ReadTextOutput
    | ReadImageOutput
    | ReadNotebookOutput
    | ReadPdfOutput
    | ReadPartsOutput
    | FileUnchangedOutput
)


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
    originalFile: str | None
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
    userModified: NotRequired[bool]


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
    """The questions that were asked."""

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
    """Resource URI."""
    name: str
    """Resource name."""
    description: NotRequired[str]
    """Resource description."""
    mimeType: NotRequired[str]
    """Resource MIME type."""
    server: str
    """Server providing this resource."""


ListMcpResourcesOutput = list[McpResourceEntry]
"""``tool_use_result`` for the ListMcpResources tool."""


class ReadMcpResourceContentItem(TypedDict):
    """A single content item from an MCP resource."""

    uri: str
    """Resource URI."""
    mimeType: NotRequired[str]
    """Content MIME type."""
    text: NotRequired[str]
    """Text content."""


class ReadMcpResourceOutput(TypedDict):
    """``tool_use_result`` for the ReadMcpResource tool."""

    contents: list[ReadMcpResourceContentItem]
    """Resource contents."""


# class SubscribeMcpResourceOutput(TypedDict):
#     """Output from subscribing to an MCP resource."""

#     subscribed: bool
#     """Whether the subscription was successful."""
#     subscriptionId: str
#     """Unique identifier for this subscription."""


# class UnsubscribeMcpResourceOutput(TypedDict):
#     """Output from unsubscribing from an MCP resource."""

#     unsubscribed: bool
#     """Whether the unsubscription was successful."""


# class SubscribePollingOutput(TypedDict):
#     """Output from subscribing to a polling resource."""

#     subscribed: bool
#     """Whether the subscription was successful."""
#     subscriptionId: str
#     """Unique identifier for this subscription."""


# class UnsubscribePollingOutput(TypedDict):
#     """Output from unsubscribing from a polling resource."""

#     unsubscribed: bool
#     """Whether the unsubscription was successful."""


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class ConfigOutput(TypedDict):
    """Output from the Config tool."""

    success: bool
    """Whether the operation succeeded."""
    operation: NotRequired[Literal["get", "set"]]
    """The config operation that was performed."""
    setting: NotRequired[str]
    """The setting name."""
    value: NotRequired[Any]
    """The current or requested value."""
    previousValue: NotRequired[Any]
    """The previous value (for set operations)."""
    newValue: NotRequired[Any]
    """The new value (for set operations)."""
    error: NotRequired[str]
    """Error message if the operation failed."""


# ---------------------------------------------------------------------------
# Skill
# ---------------------------------------------------------------------------


class SkillOutput(TypedDict):
    """``tool_use_result`` for the Skill tool.

    Not part of the official SDK ToolOutputSchemas as of SDK v0.2.62.
    Shape derived from empirical testing.
    """

    success: bool
    """Whether the skill was invoked successfully."""
    commandName: str
    """The name of the skill that was invoked."""
    allowedTools: list[ToolName | str]
    """Tools that the skill is allowed to use."""


# ---------------------------------------------------------------------------
# EnterPlanMode
# ---------------------------------------------------------------------------


class EnterPlanModeOutput(TypedDict):
    """``tool_use_result`` for the EnterPlanMode tool.

    Not part of the official SDK ToolOutputSchemas as of SDK v0.2.62.
    Shape derived from empirical testing.
    """

    message: str
    """A message indicating that plan mode was entered."""


# ---------------------------------------------------------------------------
# ToolSearch
# ---------------------------------------------------------------------------


class ToolReference(TypedDict):
    """A single tool reference returned by ToolSearch."""

    type: Literal["tool_reference"]
    """Always 'tool_reference'."""
    tool_name: str
    """The fully qualified tool name."""


class ToolSearchOutput(TypedDict):
    """``tool_use_result`` for the ToolSearch tool.

    The result is a list of tool_reference content blocks returned
    inside the tool_result content array.
    """

    references: list[ToolReference]
    """Matched tool references."""


# ---------------------------------------------------------------------------
# EnterWorktree
# ---------------------------------------------------------------------------


class EnterWorktreeOutput(TypedDict):
    """``tool_use_result`` for the EnterWorktree tool."""

    worktreePath: str
    """The path to the worktree."""
    worktreeBranch: NotRequired[str]
    """The branch of the worktree."""
    message: str
    """A message indicating the result of the operation."""


class ExitWorktreeOutput(TypedDict):
    """``tool_use_result`` for the ExitWorktree tool."""

    action: Literal["keep", "remove"]
    """The action that was taken."""
    originalCwd: str
    """The original working directory before the worktree was entered."""
    worktreePath: str
    """The path to the worktree."""
    worktreeBranch: NotRequired[str]
    """The branch of the worktree."""
    tmuxSessionName: NotRequired[str]
    """The tmux session name if applicable."""
    discardedFiles: NotRequired[int]
    """Number of files discarded."""
    discardedCommits: NotRequired[int]
    """Number of commits discarded."""
    message: str
    """A message indicating the result of the operation."""


# ---------------------------------------------------------------------------
# Union of all tool_use_result types
# ---------------------------------------------------------------------------

ToolUseResult = (
    AgentOutput
    | BashOutput
    | BashOutputOutput
    | KillShellOutput
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
    # | SubscribeMcpResourceOutput
    # | UnsubscribeMcpResourceOutput
    # | SubscribePollingOutput
    # | UnsubscribePollingOutput
    | ConfigOutput
    | EnterWorktreeOutput
    | ExitWorktreeOutput
    | SkillOutput
    | EnterPlanModeOutput
    | ToolSearchOutput
    | McpResourceEntry
)

#: Mapping from tool name to its ``tool_use_result`` type.
TOOL_USE_RESULT_TYPES: dict[ToolName, type[ToolUseResult]] = {
    "Task": AgentCompletedOutput,
    "Bash": BashOutput,
    "BashOutput": BashOutputOutput,
    "KillBash": KillShellOutput,
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
    # "SubscribeMcpResource": SubscribeMcpResourceOutput,
    # "UnsubscribeMcpResource": UnsubscribeMcpResourceOutput,
    # "SubscribePolling": SubscribePollingOutput,
    # "UnsubscribePolling": UnsubscribePollingOutput,
    "Config": ConfigOutput,
    "EnterWorktree": EnterWorktreeOutput,
    "ExitWorktree": ExitWorktreeOutput,
    "Skill": SkillOutput,
    "EnterPlanMode": EnterPlanModeOutput,
    "ToolSearch": ToolSearchOutput,
}
