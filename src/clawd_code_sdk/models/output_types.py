"""Tool output type definitions for Claude Code built-in tools.

These TypedDicts define the output schemas for all built-in Claude Code tools.
They represent the JSON wire format and can be used for type-safe tool result handling.
"""

from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict


# --- Task (Agent) ---


class TaskOutputUsage(TypedDict):
    """Token usage statistics from a subagent task."""

    input_tokens: int
    """Number of input tokens consumed."""
    output_tokens: int
    """Number of output tokens generated."""
    cache_creation_input_tokens: NotRequired[int]
    """Tokens used to create cache entries."""
    cache_read_input_tokens: NotRequired[int]
    """Tokens read from cache."""


class TaskOutput(TypedDict):
    """Output from the Task tool."""

    result: str
    """Final result message from the subagent."""
    usage: NotRequired[TaskOutputUsage]
    """Token usage statistics."""
    total_cost_usd: NotRequired[float]
    """Total cost in USD."""
    duration_ms: NotRequired[int]
    """Execution duration in milliseconds."""


# --- AskUserQuestion ---


class AskUserQuestionOutput(TypedDict):
    """Output from the AskUserQuestion tool."""

    questions: list[dict[str, Any]]
    """The questions that were asked."""
    answers: dict[str, str]
    """User answers. Maps question text to answer string.

    Multi-select answers are comma-separated.
    """


# --- Bash ---


class BashOutput(TypedDict):
    """Output from the Bash tool."""

    output: str
    """Combined stdout and stderr output."""
    exitCode: int
    """Exit code of the command."""
    killed: NotRequired[bool]
    """Whether the command was killed due to timeout."""
    shellId: NotRequired[str]
    """Shell ID for background processes."""


# --- BashOutput ---


class BashOutputToolOutput(TypedDict):
    """Output from the BashOutput tool."""

    output: str
    """New output since last check."""
    status: Literal["running", "completed", "failed"]
    """Current shell status."""
    exitCode: NotRequired[int]
    """Exit code (when completed)."""


# --- Edit ---


class EditOutput(TypedDict):
    """Output from the Edit tool."""

    message: str
    """Confirmation message."""
    replacements: int
    """Number of replacements made."""
    file_path: str
    """File path that was edited."""


# --- Read ---


class TextFileOutput(TypedDict):
    """Output from the Read tool for text files."""

    content: str
    """File contents with line numbers."""
    total_lines: int
    """Total number of lines in file."""
    lines_returned: int
    """Lines actually returned."""


class ImageFileOutput(TypedDict):
    """Output from the Read tool for image files."""

    image: str
    """Base64 encoded image data."""
    mime_type: str
    """Image MIME type."""
    file_size: int
    """File size in bytes."""


class PDFPageImage(TypedDict):
    """An image extracted from a PDF page."""

    image: str
    """Base64 encoded image data."""
    mime_type: str
    """Image MIME type."""


class PDFPage(TypedDict):
    """A single page from a PDF file."""

    page_number: int
    """1-based page number."""
    text: NotRequired[str]
    """Extracted text content."""
    images: NotRequired[list[PDFPageImage]]
    """Images extracted from this page."""


class PDFFileOutput(TypedDict):
    """Output from the Read tool for PDF files."""

    pages: list[PDFPage]
    """Array of page contents."""
    total_pages: int
    """Total number of pages."""


class NotebookCell(TypedDict):
    """A single cell from a Jupyter notebook."""

    cell_type: Literal["code", "markdown"]
    """Cell type."""
    source: str
    """Cell source content."""
    outputs: NotRequired[list[Any]]
    """Cell outputs (for code cells)."""
    execution_count: NotRequired[int]
    """Execution count (for code cells)."""


class NotebookFileOutput(TypedDict):
    """Output from the Read tool for Jupyter notebooks."""

    cells: list[NotebookCell]
    """Jupyter notebook cells."""
    metadata: NotRequired[dict[str, Any]]
    """Notebook metadata."""


ReadOutput = TextFileOutput | ImageFileOutput | PDFFileOutput | NotebookFileOutput


# --- Write ---


class WriteOutput(TypedDict):
    """Output from the Write tool."""

    message: str
    """Success message."""
    bytes_written: int
    """Number of bytes written."""
    file_path: str
    """File path that was written."""


# --- Glob ---


class GlobOutput(TypedDict):
    """Output from the Glob tool."""

    matches: list[str]
    """Array of matching file paths."""
    count: int
    """Number of matches found."""
    search_path: str
    """Search directory used."""


# --- Grep ---


class GrepMatch(TypedDict):
    """A single grep match with context."""

    file: str
    """File path containing the match."""
    line_number: NotRequired[int]
    """Line number of the match."""
    line: str
    """The matching line."""
    before_context: NotRequired[list[str]]
    """Lines before the match."""
    after_context: NotRequired[list[str]]
    """Lines after the match."""


class GrepContentOutput(TypedDict):
    """Output from the Grep tool in content mode."""

    matches: list[GrepMatch]
    """Matching lines with context."""
    total_matches: int
    """Total number of matches."""


class GrepFilesOutput(TypedDict):
    """Output from the Grep tool in files_with_matches mode."""

    files: list[str]
    """Files containing matches."""
    count: int
    """Number of files with matches."""


class GrepCountEntry(TypedDict):
    """Match count for a single file."""

    file: str
    """File path."""
    count: int
    """Number of matches in this file."""


class GrepCountOutput(TypedDict):
    """Output from the Grep tool in count mode."""

    counts: list[GrepCountEntry]
    """Match counts per file."""
    total: int
    """Total matches across all files."""


GrepOutput = GrepContentOutput | GrepFilesOutput | GrepCountOutput


# --- KillBash ---


class KillBashOutput(TypedDict):
    """Output from the KillBash tool."""

    message: str
    """Success message."""
    shell_id: str
    """ID of the killed shell."""


# --- NotebookEdit ---


class NotebookEditOutput(TypedDict):
    """Output from the NotebookEdit tool."""

    message: str
    """Success message."""
    edit_type: Literal["replaced", "inserted", "deleted"]
    """Type of edit performed."""
    cell_id: NotRequired[str]
    """Cell ID that was affected."""
    total_cells: int
    """Total cells in notebook after edit."""


# --- WebFetch ---


class WebFetchOutput(TypedDict):
    """Output from the WebFetch tool."""

    response: str
    """AI model's response to the prompt."""
    url: str
    """URL that was fetched."""
    final_url: NotRequired[str]
    """Final URL after redirects."""
    status_code: NotRequired[int]
    """HTTP status code."""


# --- WebSearch ---


class WebSearchResult(TypedDict):
    """A single web search result."""

    title: str
    """Result title."""
    url: str
    """Result URL."""
    snippet: str
    """Result snippet."""
    metadata: NotRequired[dict[str, Any]]
    """Additional metadata if available."""


class WebSearchOutput(TypedDict):
    """Output from the WebSearch tool."""

    results: list[WebSearchResult]
    """Search results."""
    total_results: int
    """Total number of results."""
    query: str
    """The query that was searched."""


# --- TodoWrite ---


class TodoWriteStats(TypedDict):
    """Current todo task statistics."""

    total: int
    """Total number of tasks."""
    pending: int
    """Number of pending tasks."""
    in_progress: int
    """Number of in-progress tasks."""
    completed: int
    """Number of completed tasks."""


class TodoWriteOutput(TypedDict):
    """Output from the TodoWrite tool."""

    message: str
    """Success message."""
    stats: TodoWriteStats
    """Current todo statistics."""


# --- ExitPlanMode ---


class ExitPlanModeOutput(TypedDict):
    """Output from the ExitPlanMode tool."""

    message: str
    """Confirmation message."""
    approved: NotRequired[bool]
    """Whether user approved the plan."""


# --- ListMcpResources ---


class McpResourceInfo(TypedDict):
    """Information about an available MCP resource."""

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


class ListMcpResourcesOutput(TypedDict):
    """Output from the ListMcpResources tool."""

    resources: list[McpResourceInfo]
    """Available resources."""
    total: int
    """Total number of resources."""


# --- ReadMcpResource ---


class McpResourceContent(TypedDict):
    """Content of an MCP resource."""

    uri: str
    """Resource URI."""
    mimeType: NotRequired[str]
    """Content MIME type."""
    text: NotRequired[str]
    """Text content."""
    blob: NotRequired[str]
    """Base64 encoded binary content."""


class ReadMcpResourceOutput(TypedDict):
    """Output from the ReadMcpResource tool."""

    contents: list[McpResourceContent]
    """Resource contents."""
    server: str
    """Server that provided the resource."""


# --- Union type ---

ToolOutput = (
    TaskOutput
    | AskUserQuestionOutput
    | BashOutput
    | BashOutputToolOutput
    | EditOutput
    | ReadOutput
    | WriteOutput
    | GlobOutput
    | GrepOutput
    | KillBashOutput
    | NotebookEditOutput
    | WebFetchOutput
    | WebSearchOutput
    | TodoWriteOutput
    | ExitPlanModeOutput
    | ListMcpResourcesOutput
    | ReadMcpResourceOutput
)

#: Mapping from tool name to its output type.
TOOL_OUTPUT_TYPES: dict[str, type[ToolOutput]] = {
    "Task": TaskOutput,
    "AskUserQuestion": AskUserQuestionOutput,
    "Bash": BashOutput,
    "BashOutput": BashOutputToolOutput,
    "Edit": EditOutput,
    "Read": TextFileOutput,
    "Write": WriteOutput,
    "Glob": GlobOutput,
    "Grep": GrepContentOutput,
    "KillBash": KillBashOutput,
    "NotebookEdit": NotebookEditOutput,
    "WebFetch": WebFetchOutput,
    "WebSearch": WebSearchOutput,
    "TodoWrite": TodoWriteOutput,
    "ExitPlanMode": ExitPlanModeOutput,
    "ListMcpResources": ListMcpResourcesOutput,
    "ReadMcpResource": ReadMcpResourceOutput,
}
