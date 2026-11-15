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
from clawd_code_sdk.models.input_types import ReportFindingsFinding  # noqa: TC001
from clawd_code_sdk.models.usage import (
    AgentServerToolUse as AgentServerToolUse,  # noqa: TC001, PLC0414
)


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
    citations: NotRequired[list[Any] | None]
    """Citations attached to the text block."""


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
    inference_geo: NotRequired[str | None]
    """Inference geography."""
    speed: NotRequired[str | None]
    """Speed mode."""
    iterations: NotRequired[Any]
    """Per-iteration usage."""
    output_tokens_details: NotRequired[AgentOutputTokensDetails | None]
    """Breakdown of output tokens."""
    fallback_credit: NotRequired[Any]
    """Fallback credit info."""


class AgentOutputTokensDetails(TypedDict):
    """Breakdown of output tokens of an agent task."""

    thinking_tokens: NotRequired[int | None]
    """Number of thinking tokens."""


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
    frameCount: NotRequired[int]
    """Number of frames."""


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
    resolvedModel: NotRequired[str]
    """Model the agent ran on."""
    modelsUsed: NotRequired[list[str]]
    """Ordered distinct models used (length > 1 means a mid-run swap)."""
    totalToolUseCount: int
    """Total number of tool calls made."""
    totalDurationMs: int
    """Total execution duration in milliseconds."""
    totalTokens: int
    """Total tokens used."""
    usage: AgentOutputUsage
    """Detailed token usage statistics."""
    toolsUsed: NotRequired[list[str]]
    """Names of the tools the agent used."""
    toolStats: NotRequired[ToolStats]
    """Tool usage statistics."""
    prompt: str
    """The prompt that was given to the agent."""
    worktreePath: NotRequired[str]
    """Worktree the agent ran in (isolation="worktree")."""
    worktreeBranch: NotRequired[str]
    """Branch of the agent's worktree."""


class AgentAsyncLaunchedOutput(TypedDict):
    """Output from the Task tool when an agent was launched asynchronously."""

    status: Literal["async_launched"]
    """Indicates the agent was launched in the background."""
    isAsync: NotRequired[Literal[True]]
    """Always True for async-launched agents."""
    agentId: str
    """The ID of the async agent."""
    description: str
    """The description of the task."""
    resolvedModel: NotRequired[str]
    """Model in use at the backgrounding transition."""
    modelsUsed: NotRequired[list[str]]
    """Ordered distinct models used before backgrounding."""
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


class AgentRemoteLaunchedOutput(TypedDict):
    """Output from the Agent tool when an agent was launched in a remote (cloud) session."""

    status: Literal["remote_launched"]
    """Indicates the agent was launched remotely."""
    taskId: str
    """The ID of the remote agent task."""
    sessionUrl: str
    """The URL of the cloud session."""
    description: str
    """The description of the task."""
    prompt: str
    """The prompt for the agent."""
    outputFile: str
    """Path to the output file for checking agent progress."""


AgentOutput = (
    AgentCompletedOutput | AgentAsyncLaunchedOutput | AgentRemoteLaunchedOutput
)  # | AgentQueuedToRunningOutput


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
    staleReadFileStateHint: NotRequired[str]
    """Model-facing note listing readFileState entries whose mtime bumped during this command."""
    # tokenSaverOutput: NotRequired[str]
    # """Compressed output sent to model when token-saver is active (UI still uses stdout)."""
    ghRateLimitHint: NotRequired[str]
    """Model-facing sys-reminder appended when a gh cmd reports a GitHub API rate-limit error."""
    timedOutAfterMs: NotRequired[float]
    """Set when the command hit its timeout and was auto-backgrounded; the timeout in ms."""
    backgroundCwdHint: NotRequired[str]
    """Note that the session cwd was not changed by a backgrounded directory-change command."""
    backgroundEndsWithFinalResponse: NotRequired[Literal[True]]
    """True when this backgrounded command is terminated at its caller's final response."""
    backgroundWakesOwner: NotRequired[Literal[True]]
    """True when the subagent owning this backgrounded command is woken by its end."""
    gitOperation: NotRequired[BashGitOperation]
    """Structured classification of git/gh operations detected in this command."""


class BashGitCommit(TypedDict):
    """A git commit detected in a Bash command."""

    sha: str
    kind: Literal["committed", "amended", "cherry-picked"]
    branch: NotRequired[str]


class BashGitPush(TypedDict):
    """A git push detected in a Bash command."""

    branch: str


class BashGitBranchOperation(TypedDict):
    """A branch merge/rebase detected in a Bash command."""

    ref: str
    action: Literal["merged", "rebased"]


class BashGitPullRequest(TypedDict):
    """A gh PR operation detected in a Bash command."""

    number: int
    url: NotRequired[str]
    action: Literal[
        "created",
        "edited",
        "merged",
        "commented",
        "closed",
        "reopened",
        "ready",
        "draft",
        "auto-merge-enabled",
        "auto-merge-disabled",
    ]


class BashGitOperation(TypedDict):
    """Git/gh operations detected in a Bash command."""

    commit: NotRequired[BashGitCommit]
    push: NotRequired[BashGitPush]
    branch: NotRequired[BashGitBranchOperation]
    pr: NotRequired[BashGitPullRequest]


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


class ArtifactReadMarker(TypedDict):
    """Marks a read/fetched artifact as viewed."""

    slug: str
    ver: NotRequired[str]
    seeded: NotRequired[Literal[False]]


class ReadPartsPage(TypedDict):
    """A rendered page image of a document read in parts."""

    base64: str
    mediaType: MimeType
    error: NotRequired[str]


class AskUserQuestionAnnotation(TypedDict):
    """Per-question annotation attached to an AskUserQuestion answer."""

    preview: NotRequired[str]
    notes: NotRequired[str]
    unanswered: NotRequired[Literal["skipped", "replied_in_chat", "dismissed"]]


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
    truncatedByTokenCap: NotRequired[bool]
    """True when a whole-file read was auto-paginated because it exceeded the token cap."""


class ReadTextOutput(TypedDict):
    """``tool_use_result`` for the Read tool (text files)."""

    type: Literal["text"]
    file: ReadFileInfo
    artifactRead: NotRequired[ArtifactReadMarker]
    """Set when the read file is an artifact that now counts as viewed."""


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
    firstPage: NotRequired[int]
    """First page number included as page images in the model-facing tool_result."""
    pages: NotRequired[list[ReadPartsPage]]
    """Page images (only present transiently in-process, absent on emitted results)."""


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
    staged: NotRequired[bool]
    """Whether the edit was staged instead of written."""


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
    staged: NotRequired[bool]
    """Whether the write was staged instead of written."""


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
    totalMatches: NotRequired[int]
    """Total matches before truncation (a lower bound when countIsComplete is false)."""
    countIsComplete: NotRequired[bool]
    """Whether totalMatches is exact."""
    timedOut: NotRequired[bool]
    """Whether the search timed out (results may be partial)."""


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
    totalFiles: NotRequired[int]
    """Total matching files before pagination."""
    totalLines: NotRequired[int]
    """Total matching lines before pagination."""
    timedOut: NotRequired[bool]
    """Whether the search timed out (results may be partial)."""


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
    old_source: NotRequired[str]
    """The original source of the cell before the edit."""


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
    artifactRead: NotRequired[ArtifactReadMarker]
    """Set when the fetched URL is an artifact that now counts as viewed."""


# ---------------------------------------------------------------------------
# WebSearch
# ---------------------------------------------------------------------------


class WebSearchHit(TypedDict):
    """A single search result hit."""

    title: str
    url: str
    snippet: NotRequired[str]
    """Snippet of the search hit."""


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
    searchCount: NotRequired[int]
    """Number of searches performed."""


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
    response: NotRequired[str]
    """Free-text response from the user."""
    annotations: NotRequired[dict[str, AskUserQuestionAnnotation]]
    """Per-question annotations from the user, keyed by question text."""
    afkTimeoutMs: NotRequired[float]
    """Set when the question timed out because the user was away (ms)."""


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

McpOutput = str | list[dict[str, Any]] | dict[str, Any]
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
    error: NotRequired[str]
    """Error message when the resource could not be read."""


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
# Tools added in SDK 0.3.x
# ---------------------------------------------------------------------------


class RefreshMcpTools(TypedDict):
    """```` entry of RefreshMcpTools."""

    server: str
    """Server name"""
    status: Literal["refreshed", "error", "not_connected"]
    """refreshed: tool list re-queried and applied.

    error: the re-query failed and the previous tool set was kept. not_connected: the server has no
    live connection to query (this tool never dials).
    """
    toolCount: NotRequired[int]
    """Number of tools now available from this server"""
    added: NotRequired[list[str]]
    """Tool names this refresh added"""
    removed: NotRequired[list[str]]
    """Tool names this refresh removed"""
    error: NotRequired[str]
    """Why the refresh failed or the server was unavailable"""


RefreshMcpToolsOutput = list[RefreshMcpTools]


class ArtifactUrlStored(TypedDict):
    """``stored`` entry of ArtifactUrl."""

    contract: str
    preferredContract: NotRequired[str]
    capabilities: NotRequired[dict[str, Any]]
    carried: NotRequired[bool]
    read: NotRequired[str]


class ArtifactUrlOutput(TypedDict):
    """Artifact tool output (Url variant)."""

    url: str
    path: str
    artifact_id: NotRequired[str]
    title: NotRequired[str]
    version: NotRequired[str]
    capabilities: NotRequired[Any]
    stored: NotRequired[ArtifactUrlStored]
    warnings: NotRequired[list[str]]
    publishesRemaining: NotRequired[float]
    publishesResetAt: NotRequired[float]
    contract: NotRequired[str]
    updated: NotRequired[bool]
    owned: NotRequired[bool]
    icon: NotRequired[str]
    faviconSent: NotRequired[Literal[True]]
    iconDropped: NotRequired[Literal[True]]
    audience: NotRequired[str]
    seq: NotRequired[float]
    unchanged: NotRequired[Literal[True]]
    liveSubscription: NotRequired[str]
    pinned: NotRequired[bool]


class ArtifactArtifactsArtifact(TypedDict):
    """``artifact`` entry of ArtifactArtifacts."""

    title: str
    url: str
    favicon: NotRequired[str]
    updatedAt: NotRequired[str]
    rel: NotRequired[Literal["mine", "shared"]]
    external: NotRequired[Literal[True]]
    role: NotRequired[Literal["editor", "commenter", "reader", "viewer"]]
    outsidersMayHaveWritten: NotRequired[Literal[True]]
    pinned: NotRequired[bool]


class ArtifactArtifactsOutput(TypedDict):
    """Artifact tool output (Artifacts variant)."""

    artifacts: list[ArtifactArtifactsArtifact]
    truncated: NotRequired[bool]
    total: NotRequired[int]
    total_at_least: NotRequired[Literal[True]]
    next_page_token: NotRequired[str]
    pins_enabled: NotRequired[bool]
    scope: NotRequired[Literal["shared", "all"]]
    external_listed: NotRequired[Literal[True]]


class ArtifactReadRead(TypedDict):
    """``read`` entry of ArtifactRead."""

    url: str
    bytes: int
    code: float
    codeText: str
    result: str
    durationMs: float
    title: NotRequired[str]


class ArtifactReadArtifactRead(TypedDict):
    """``artifactRead`` entry of ArtifactRead."""

    slug: str
    ver: NotRequired[str]
    seeded: NotRequired[Literal[False]]


class ArtifactReadOutput(TypedDict):
    """Artifact tool output (Read variant)."""

    read: ArtifactReadRead
    owned: NotRequired[bool]
    artifactRead: NotRequired[ArtifactReadArtifactRead]


class ArtifactWatchWatch(TypedDict):
    """``watch`` entry of ArtifactWatch."""

    url: str
    watching: bool
    outcome: str
    reason: NotRequired[str]
    durable_skip_reason: NotRequired[str]
    task_id: NotRequired[str]
    since: NotRequired[float]
    token_expires_at: NotRequired[float]
    rail: NotRequired[str]
    trigger_id: NotRequired[str]
    durable_since: NotRequired[str]
    status: NotRequired[int]
    detail: NotRequired[str]
    note: NotRequired[str]
    events: NotRequired[list[str]]


class ArtifactWatchOutput(TypedDict):
    """Artifact tool output (Watch variant)."""

    watch: ArtifactWatchWatch


class ArtifactUnwatchUnwatch(TypedDict):
    """``unwatch`` entry of ArtifactUnwatch."""

    url: str
    was_watching: bool


class ArtifactUnwatchOutput(TypedDict):
    """Artifact tool output (Unwatch variant)."""

    unwatch: ArtifactUnwatchUnwatch


class ArtifactWatchesWatchTaskId(TypedDict):
    """``watch`` variant of ArtifactWatches (TaskId)."""

    url: str
    task_id: str
    since: float
    explicit: bool
    connected: bool
    connecting: NotRequired[bool]
    token_expires_at: float
    armed_via: NotRequired[str]


class ArtifactWatchesWatchTriggerId(TypedDict):
    """``watch`` variant of ArtifactWatches (TriggerId)."""

    url: str
    rail: Literal["durable_wake"]
    trigger_id: str
    since: str
    events: NotRequired[list[str]]
    restored: NotRequired[bool]


class ArtifactWatchesWatchStopKind(TypedDict):
    """``watch`` variant of ArtifactWatches (StopKind)."""

    url: str
    rail: Literal["live_stopped"]
    since: NotRequired[float]
    explicit: NotRequired[bool]
    armed_via: NotRequired[str]
    stop_kind: str


class ArtifactWatchesArm(TypedDict):
    """``arm`` entry of ArtifactWatches."""

    url: str
    rail: NotRequired[str]
    state: str
    reconnect: NotRequired[bool]
    failures: NotRequired[float]
    max_failures: NotRequired[float]
    next_in_s: NotRequired[float]
    last_failure: NotRequired[str]
    reason: NotRequired[str]
    detail: NotRequired[str]
    server_message: NotRequired[str]
    at: NotRequired[float]


class ArtifactWatchesOutput(TypedDict):
    """Artifact tool output (Watches variant)."""

    watches: list[
        ArtifactWatchesWatchTaskId | ArtifactWatchesWatchTriggerId | ArtifactWatchesWatchStopKind
    ]
    filter_url: NotRequired[str]
    arms: NotRequired[list[ArtifactWatchesArm]]


class ArtifactAssetUploadWritten(TypedDict):
    """``written`` entry of ArtifactAssetUpload."""

    url: str


class ArtifactAssetUploadAssetUpload(TypedDict):
    """``asset_upload`` entry of ArtifactAssetUpload."""

    id: str
    url: str
    size_bytes: int
    content_type: str
    sha256: NotRequired[str]
    file_name: str


class ArtifactAssetUploadOutput(TypedDict):
    """Artifact tool output (AssetUpload variant)."""

    written: NotRequired[ArtifactAssetUploadWritten]
    owned: NotRequired[bool]
    asset_upload: ArtifactAssetUploadAssetUpload


class ArtifactAssetUploadsWritten(TypedDict):
    """``written`` entry of ArtifactAssetUploads."""

    url: str


class ArtifactAssetUploadsAssetUploadsResultId(TypedDict):
    """``result`` variant of ArtifactAssetUploadsAssetUploads (Id)."""

    file_path: str
    status: Literal["uploaded"]
    id: str
    url: str
    size_bytes: int
    content_type: str
    sha256: NotRequired[str]
    file_name: str


class ArtifactAssetUploadsAssetUploadsResultReason(TypedDict):
    """``result`` variant of ArtifactAssetUploadsAssetUploads (Reason)."""

    file_path: str
    status: Literal["failed", "not_attempted"]
    reason: str
    message: str
    may_be_stored: NotRequired[Literal[True]]


class ArtifactAssetUploadsAssetUploads(TypedDict):
    """``asset_uploads`` entry of ArtifactAssetUploads."""

    url: str
    results: list[
        ArtifactAssetUploadsAssetUploadsResultId
        | ArtifactAssetUploadsAssetUploadsResultReason
        | list[
            ArtifactAssetUploadsAssetUploadsResultId | ArtifactAssetUploadsAssetUploadsResultReason
        ]
    ]
    """@minItems 1 @maxItems 25"""


class ArtifactAssetUploadsOutput(TypedDict):
    """Artifact tool output (AssetUploads variant)."""

    written: NotRequired[ArtifactAssetUploadsWritten]
    owned: NotRequired[bool]
    asset_uploads: ArtifactAssetUploadsAssetUploads


class ArtifactAssetListAssetListAsset(TypedDict):
    """``asset`` entry of ArtifactAssetListAssetList."""

    id: str
    url: str
    content_type: str
    size_bytes: int
    sha256: NotRequired[str]
    created_at: str


class ArtifactAssetListAssetListUsage(TypedDict):
    """``usage`` entry of ArtifactAssetListAssetList."""

    files: float
    bytes: int
    max_files: float
    max_bytes: int


class ArtifactAssetListAssetList(TypedDict):
    """``asset_list`` entry of ArtifactAssetList."""

    url: str
    assets: list[ArtifactAssetListAssetListAsset]
    """@maxItems 1000"""
    usage: ArtifactAssetListAssetListUsage
    next: NotRequired[str]
    cowritten: NotRequired[Literal[True]]
    outside_writer: NotRequired[Literal[True]]


class ArtifactAssetListOutput(TypedDict):
    """Artifact tool output (AssetList variant)."""

    asset_list: ArtifactAssetListAssetList


class ArtifactAssetReadAssetRead(TypedDict):
    """``asset_read`` entry of ArtifactAssetRead."""

    id: str
    path: str
    size_bytes: int
    content_type: str
    sha256: str
    cowritten: NotRequired[Literal[True]]
    outside_writer: NotRequired[Literal[True]]
    public_read: NotRequired[Literal[True]]
    foreign: NotRequired[Literal[True]]


class ArtifactAssetReadOutput(TypedDict):
    """Artifact tool output (AssetRead variant)."""

    asset_read: ArtifactAssetReadAssetRead


class ArtifactAssetDeleteWritten(TypedDict):
    """``written`` entry of ArtifactAssetDelete."""

    url: str


class ArtifactAssetDeleteAssetDelete(TypedDict):
    """``asset_delete`` entry of ArtifactAssetDelete."""

    id: str
    deleted: bool


class ArtifactAssetDeleteOutput(TypedDict):
    """Artifact tool output (AssetDelete variant)."""

    written: NotRequired[ArtifactAssetDeleteWritten]
    owned: NotRequired[bool]
    asset_delete: ArtifactAssetDeleteAssetDelete


class ArtifactPinPin(TypedDict):
    """``pin`` entry of ArtifactPin."""

    action: Literal["pin", "unpin"]
    url: str
    pinned: bool
    title: NotRequired[str]


class ArtifactPinOutput(TypedDict):
    """Artifact tool output (Pin variant)."""

    pin: ArtifactPinPin


ArtifactOutput = (
    ArtifactUrlOutput
    | ArtifactArtifactsOutput
    | ArtifactReadOutput
    | ArtifactWatchOutput
    | ArtifactUnwatchOutput
    | ArtifactWatchesOutput
    | ArtifactAssetUploadOutput
    | ArtifactAssetUploadsOutput
    | ArtifactAssetListOutput
    | ArtifactAssetReadOutput
    | ArtifactAssetDeleteOutput
    | ArtifactPinOutput
)


class ProjectsProjectInfoDoc(TypedDict):
    """``doc`` entry of ProjectsProjectInfo."""

    path: str
    created_at: str | None


class ProjectsProjectInfoFile(TypedDict):
    """``file`` entry of ProjectsProjectInfo."""

    path: str
    file_kind: str
    created_at: str | None


class ProjectsProjectInfoSyncSource(TypedDict):
    """``sync_source`` entry of ProjectsProjectInfo."""

    type: str | None
    config: dict[str, Any]


class ProjectsProjectInfoKnowledge(TypedDict):
    """``knowledge`` entry of ProjectsProjectInfo."""

    knowledge_size: int
    max_knowledge_size: int


class ProjectsProjectInfoOutput(TypedDict):
    """Projects tool output (ProjectInfo variant)."""

    method: Literal["project_info"]
    notice: NotRequired[str]
    local_file: NotRequired[str]
    name: str
    description: str
    instructions: str
    docs: list[ProjectsProjectInfoDoc]
    files: NotRequired[list[ProjectsProjectInfoFile]]
    sync_sources: NotRequired[list[ProjectsProjectInfoSyncSource]]
    knowledge: ProjectsProjectInfoKnowledge


class ProjectsProjectReadOutput(TypedDict):
    """Projects tool output (ProjectRead variant)."""

    method: Literal["project_read"]
    notice: NotRequired[str]
    path: str
    file_kind: NotRequired[str]
    content: NotRequired[str]
    local_file: NotRequired[str]
    created_at: str | None


class ProjectsProjectSearchHit(TypedDict):
    """``hit`` entry of ProjectsProjectSearch."""

    name: NotRequired[str]
    doc_uuid: NotRequired[str]
    text: NotRequired[str]
    image_attached: NotRequired[bool]
    page: NotRequired[int]


class ProjectsProjectSearchOutput(TypedDict):
    """Projects tool output (ProjectSearch variant)."""

    method: Literal["project_search"]
    notice: NotRequired[str]
    rag: bool
    hits: NotRequired[list[ProjectsProjectSearchHit]]
    docs: NotRequired[list[str]]


class ProjectsProjectWriteOutput(TypedDict):
    """Projects tool output (ProjectWrite variant)."""

    method: Literal["project_write"]
    notice: NotRequired[str]
    path: str
    doc_uuid: str
    replaced: bool
    present_to_user: NotRequired[bool]
    local_path: NotRequired[str]


class ProjectsProjectDeleteOutput(TypedDict):
    """Projects tool output (ProjectDelete variant)."""

    method: Literal["project_delete"]
    notice: NotRequired[str]
    path: str
    deleted: bool


class ProjectsProjectMemoryListFile(TypedDict):
    """``file`` entry of ProjectsProjectMemoryList."""

    path: str
    size_bytes: int
    updated_at: str | None
    truncated: bool


class ProjectsProjectMemoryListOutput(TypedDict):
    """Projects tool output (ProjectMemoryList variant)."""

    method: Literal["project_memory_list"]
    notice: NotRequired[str]
    files: list[ProjectsProjectMemoryListFile]
    truncated: bool


class ProjectsProjectMemoryReadOutput(TypedDict):
    """Projects tool output (ProjectMemoryRead variant)."""

    method: Literal["project_memory_read"]
    notice: NotRequired[str]
    path: str
    content: NotRequired[str]
    local_file: NotRequired[str]
    size_bytes: int
    updated_at: str | None
    truncated: bool


ProjectsOutput = (
    ProjectsProjectInfoOutput
    | ProjectsProjectReadOutput
    | ProjectsProjectSearchOutput
    | ProjectsProjectWriteOutput
    | ProjectsProjectDeleteOutput
    | ProjectsProjectMemoryListOutput
    | ProjectsProjectMemoryReadOutput
)


class ReadMcpResourceDirResource(TypedDict):
    """``resource`` entry of ReadMcpResourceDir."""

    uri: str
    """Child resource URI"""
    name: str
    """Child resource name"""
    mimeType: NotRequired[str]
    """Child MIME type"""


class ReadMcpResourceDirOutput(TypedDict):
    """Output of the ReadMcpResourceDir tool."""

    resources: list[ReadMcpResourceDirResource]
    """Direct children of the directory resource.

    Subdirectories appear with mimeType "inode/directory".
    """
    error: NotRequired[str]
    """Human-readable error when the server could not list the directory"""


class ReportFindingsOutput(TypedDict):
    """Output of the ReportFindings tool."""

    count: int
    """Number of findings reported"""
    level: NotRequired[Literal["low", "medium", "high", "xhigh", "max"]]
    """Effort level the review ran at"""
    findings: list[ReportFindingsFinding]
    """Echoed for the result body"""


class SendFeedbackOutput(TypedDict):
    """Output of the SendFeedback tool."""

    success: bool
    message: str


class TaskCreateTask(TypedDict):
    """``task`` entry of TaskCreate."""

    id: str
    subject: str
    description: NotRequired[str]
    """The task's description as saved.

    It can differ from the tool_use input if Claude Code corrects a malformed call or a PreToolUse
    hook changes the input. Absent in results from older Claude Code versions.
    """


class TaskCreateOutput(TypedDict):
    """Output of the TaskCreate tool."""

    task: TaskCreateTask


class TaskGetTask(TypedDict):
    """``task`` entry of TaskGet."""

    id: str
    subject: str
    description: str
    status: Literal["pending", "in_progress", "completed"]
    blocks: list[str]
    blockedBy: list[str]


class TaskGetOutput(TypedDict):
    """Output of the TaskGet tool."""

    task: TaskGetTask | None


TaskUpdateStatusChange = TypedDict(
    "TaskUpdateStatusChange",
    {
        "from": str,
        "to": str,
    },
)


class TaskUpdateOutput(TypedDict):
    """Output of the TaskUpdate tool."""

    success: bool
    taskId: str
    updatedFields: list[str]
    error: NotRequired[str]
    statusChange: NotRequired[TaskUpdateStatusChange]


class TaskListTask(TypedDict):
    """``task`` entry of TaskList."""

    id: str
    subject: str
    status: Literal["pending", "in_progress", "completed"]
    owner: NotRequired[str]
    blockedBy: list[str]


class TaskListOutput(TypedDict):
    """Output of the TaskList tool."""

    tasks: list[TaskListTask]


class RemoteTriggerOutput(TypedDict):
    """Output of the RemoteTrigger tool."""

    status: int
    json: str
    summary: NotRequired[str]


class ShowOnboardingRolePickerOutput(TypedDict):
    """Output of the ShowOnboardingRolePicker tool."""

    role: NotRequired[str]
    dismissed: NotRequired[bool]


class OfferChromeSetupOutput(TypedDict):
    """Output of the OfferChromeSetup tool."""

    outcome: Literal["connected", "not_now", "no_attempt_yet"]


class ReadNotificationsNotification(TypedDict):
    """``notification`` entry of ReadNotifications."""

    notification_id: str
    """Server-assigned stable id — the dedup key across redeliveries."""
    origin: str
    """Server-attested source token: "github_webhook" | "trigger_fire" | "mcp_send_message" (open
    set; unknown well-formed tokens pass through verbatim, off-grammar values coerce to
    "unknown").
    """
    queued_at: str
    """RFC3339 timestamp of when the backend queued it."""
    content: str
    """Verbatim notification body."""
    arrived_at: NotRequired[str]
    """RFC3339 timestamp, by this machine's clock, of when the notification reached this session's
    queue.

    Missing from results saved before this field existed.
    """


class ReadNotificationsOutput(TypedDict):
    """Output of the ReadNotifications tool."""

    notifications: list[ReadNotificationsNotification]
    remaining: float
    """Notifications still queued after this drain (drains are size-budgeted); call the tool again
    to read them.
    """
    read_at: NotRequired[str]
    """RFC3339 timestamp, by this machine's clock, of when this call read the queue.

    Missing from results saved before this field existed.
    """


class ScheduleWakeupOutput(TypedDict):
    """Output of the ScheduleWakeup tool."""

    scheduledFor: float
    """Epoch ms timestamp when the next wakeup will fire"""
    clampedDelaySeconds: float
    """Actual delay used after clamping to runtime bounds"""
    wasClamped: bool
    """True if the requested delaySeconds was outside [60, 3600]"""
    stopped: NotRequired[bool]
    """True when the model ended the loop via `stop: true`"""
    cancelledWakeups: NotRequired[float]
    """How many pending dynamic-loop wakeups stop:true cancelled.

    0 means nothing was pending — a recurring /loop cron is not cancelled by stop:true.
    """


class MonitorOutput(TypedDict):
    """Output of the Monitor tool."""

    taskId: str
    """ID of the background monitor task."""
    timeoutMs: float
    """Timeout deadline in milliseconds (0 when persistent)."""
    persistent: NotRequired[bool]
    """No timeout — runs until TaskStop or session end."""


class ProposeSkillsOutput(TypedDict):
    """Output of the ProposeSkills tool."""

    proposalCount: int
    """Number of proposals shown on the review card"""


class ProposeGoalOutput(TypedDict):
    """Output of the ProposeGoal tool."""

    condition: str
    """The condition shown to the user for approval, or set directly when ask_user was false"""
    askUser: bool
    """Whether the user was asked for approval (true) or the goal was set directly (false)"""


class WorkflowOutput(TypedDict):
    """Output of the Workflow tool."""

    status: Literal["async_launched", "remote_launched"]
    taskId: str
    taskType: NotRequired[Literal["local_workflow", "remote_agent"]]
    """TaskType of the registered background task — 'local_workflow' for in-process runs,
    'remote_agent' when remote:true dispatches to CCR.

    Set on all new writes; absent only on transcripts written before this field existed.
    """
    workflowName: NotRequired[str]
    """meta.name from the workflow script — same value as task_started.workflow_name.

    Set on all new writes; absent only on transcripts written before this field existed.
    """
    runId: NotRequired[str]
    """Local workflow run identifier for resumeFromRunId.

    Absent for remote_launched (the CCR session URL is the resume handle there) and on transcripts
    written before this field existed.
    """
    summary: NotRequired[str]
    transcriptDir: NotRequired[str]
    """Directory where subagent transcripts are written during execution"""
    scriptPath: NotRequired[str]
    """Path to the persisted workflow script for this invocation.

    Editable via Write/Edit; pass back as `scriptPath` to re-run without resending the script.
    """
    sessionUrl: NotRequired[str]
    """CCR session URL when status is remote_launched"""
    warning: NotRequired[str]
    """Non-blocking heads-up (e.g.

    local git state diverges from the pushed branch the cloud session will clone)
    """
    error: NotRequired[str]
    """Set if syntax check failed"""


class CronCreateOutput(TypedDict):
    """Output of the CronCreate tool."""

    id: str
    humanSchedule: str
    recurring: bool
    durable: NotRequired[bool]
    nextFireAt: NotRequired[float]
    """Epoch ms of the job's next run, the scheduler's per-job offset included"""


class CronDeleteOutput(TypedDict):
    """Output of the CronDelete tool."""

    id: str
    endedLoopWakeup: NotRequired[Literal[True]]


class CronListJob(TypedDict):
    """``job`` entry of CronList."""

    id: str
    cron: str
    humanSchedule: str
    prompt: str
    recurring: NotRequired[bool]
    durable: NotRequired[bool]
    nextFireAt: NotRequired[float]
    """Epoch ms of the job's next run, the scheduler's per-job offset included"""


class CronListOutput(TypedDict):
    """Output of the CronList tool."""

    jobs: list[CronListJob]


class PushNotificationOutput(TypedDict):
    """Output of the PushNotification tool."""

    message: str
    pushSent: NotRequired[bool]
    localSent: NotRequired[bool]
    disabledReason: NotRequired[Literal["config_off", "user_present", "no_transport"]]
    sentAt: NotRequired[str]
    """ISO timestamp captured at tool execution on the emitting process.

    Optional — resumed sessions replay pre-sentAt outputs verbatim.
    """


class ClaudeDesignOutput(TypedDict):
    """Output of the ClaudeDesign tool."""

    operation: str
    content: list[dict[str, Any]]
    isError: NotRequired[bool]


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
    | RefreshMcpToolsOutput
    | ArtifactOutput
    | ProjectsOutput
    | ReadMcpResourceDirOutput
    | ReportFindingsOutput
    | SendFeedbackOutput
    | TaskCreateOutput
    | TaskGetOutput
    | TaskUpdateOutput
    | TaskListOutput
    | RemoteTriggerOutput
    | ShowOnboardingRolePickerOutput
    | OfferChromeSetupOutput
    | ReadNotificationsOutput
    | ScheduleWakeupOutput
    | MonitorOutput
    | ProposeSkillsOutput
    | ProposeGoalOutput
    | WorkflowOutput
    | CronCreateOutput
    | CronDeleteOutput
    | CronListOutput
    | PushNotificationOutput
    | ClaudeDesignOutput
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
    # Current (0.3.x) tool names
    "Agent": AgentCompletedOutput,
    "ReadMcpResourceTool": ReadMcpResourceOutput,
    "ReadMcpResourceDirTool": ReadMcpResourceDirOutput,
    "ReportFindings": ReportFindingsOutput,
    "SendFeedback": SendFeedbackOutput,
    "TaskCreate": TaskCreateOutput,
    "TaskGet": TaskGetOutput,
    "TaskUpdate": TaskUpdateOutput,
    "TaskList": TaskListOutput,
    "Workflow": WorkflowOutput,
    "CronCreate": CronCreateOutput,
    "CronDelete": CronDeleteOutput,
    "CronList": CronListOutput,
    "ScheduleWakeup": ScheduleWakeupOutput,
    "RemoteTrigger": RemoteTriggerOutput,
    "ShowOnboardingRolePicker": ShowOnboardingRolePickerOutput,
    "OfferChromeSetup": OfferChromeSetupOutput,
    "ReadNotifications": ReadNotificationsOutput,
    "Monitor": MonitorOutput,
    "propose_skills": ProposeSkillsOutput,
    "ProposeGoal": ProposeGoalOutput,
    "PushNotification": PushNotificationOutput,
    "ClaudeDesign": ClaudeDesignOutput,
}
