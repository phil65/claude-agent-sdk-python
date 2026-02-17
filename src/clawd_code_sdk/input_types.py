"""Tool input type definitions for Claude Code built-in tools.

These TypedDicts define the input schemas for all built-in Claude Code tools.
They represent the JSON wire format and can be used for type-safe tool interactions.
"""

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict


# --- Task (Agent) ---


class AgentInput(TypedDict):
    """Input for the Task tool. Launches a new agent to handle complex, multi-step tasks."""

    description: str
    """A short (3-5 word) description of the task."""
    prompt: str
    """The task for the agent to perform."""
    subagent_type: str
    """The type of specialized agent to use for this task."""


# --- AskUserQuestion ---


class AskUserQuestionOption(TypedDict):
    """A single option for a user question."""

    label: str
    """Display text for this option (1-5 words)."""
    description: str
    """Explanation of what this option means."""


class AskUserQuestion(TypedDict):
    """A single question to ask the user."""

    question: str
    """The complete question to ask. Should be clear, specific, and end with a question mark."""
    header: str
    """Very short label displayed as a chip/tag (max 12 chars)."""
    options: list[AskUserQuestionOption]
    """The available choices (2-4 options). An "Other" option is automatically provided."""
    multiSelect: bool
    """Set to true to allow multiple selections."""


class AskUserQuestionInput(TypedDict):
    """Input for the AskUserQuestion tool."""

    questions: list[AskUserQuestion]
    """Questions to ask the user (1-4 questions)."""
    answers: NotRequired[dict[str, str]]
    """User answers populated by the permission system.

    Maps question text to selected option label(s).
    Multi-select answers are comma-separated.
    """


# --- Bash ---


class BashInput(TypedDict):
    """Input for the Bash tool. Executes bash commands in a persistent shell session."""

    command: str
    """The command to execute."""
    timeout: NotRequired[int]
    """Optional timeout in milliseconds (max 600000)."""
    description: NotRequired[str]
    """Clear, concise description of what this command does in 5-10 words."""
    run_in_background: NotRequired[bool]
    """Set to true to run this command in the background."""


# --- BashOutput ---


class BashOutputInput(TypedDict):
    """Input for the BashOutput tool. Retrieves output from a background bash shell."""

    bash_id: str
    """The ID of the background shell to retrieve output from."""
    filter: NotRequired[str]
    """Optional regex to filter output lines."""


# --- Edit ---


class FileEditInput(TypedDict):
    """Input for the Edit tool. Performs exact string replacements in files."""

    file_path: str
    """The absolute path to the file to modify."""
    old_string: str
    """The text to replace."""
    new_string: str
    """The text to replace it with (must be different from old_string)."""
    replace_all: NotRequired[bool]
    """Replace all occurrences of old_string (default false)."""


# --- Read ---


class FileReadInput(TypedDict):
    """Input for the Read tool. Reads files including text, images, PDFs, and notebooks."""

    file_path: str
    """The absolute path to the file to read."""
    offset: NotRequired[int]
    """The line number to start reading from."""
    limit: NotRequired[int]
    """The number of lines to read."""


# --- Write ---


class FileWriteInput(TypedDict):
    """Input for the Write tool. Writes a file to the local filesystem."""

    file_path: str
    """The absolute path to the file to write."""
    content: str
    """The content to write to the file."""


# --- Glob ---


class GlobInput(TypedDict):
    """Input for the Glob tool. Fast file pattern matching."""

    pattern: str
    """The glob pattern to match files against."""
    path: NotRequired[str]
    """The directory to search in (defaults to cwd)."""


# --- Grep ---


# GrepInput uses the functional TypedDict form because the TypeScript interface
# uses ripgrep-style flag names ("-i", "-n", "-B", "-A", "-C") that are not
# valid Python identifiers.
GrepInput = TypedDict(
    "GrepInput",
    {
        "pattern": str,
        "path": NotRequired[str],
        "glob": NotRequired[str],
        "type": NotRequired[str],
        "output_mode": NotRequired[Literal["content", "files_with_matches", "count"]],
        "-i": NotRequired[bool],
        "-n": NotRequired[bool],
        "-B": NotRequired[int],
        "-A": NotRequired[int],
        "-C": NotRequired[int],
        "head_limit": NotRequired[int],
        "multiline": NotRequired[bool],
    },
)
"""Input for the Grep tool. Powerful search built on ripgrep with regex support."""


# --- KillBash ---


class KillShellInput(TypedDict):
    """Input for the KillBash tool. Kills a running background bash shell."""

    shell_id: str
    """The ID of the background shell to kill."""


# --- NotebookEdit ---


class NotebookEditInput(TypedDict):
    """Input for the NotebookEdit tool. Edits cells in Jupyter notebook files."""

    notebook_path: str
    """The absolute path to the Jupyter notebook file."""
    new_source: str
    """The new source for the cell."""
    cell_id: NotRequired[str]
    """The ID of the cell to edit."""
    cell_type: NotRequired[Literal["code", "markdown"]]
    """The type of the cell (code or markdown)."""
    edit_mode: NotRequired[Literal["replace", "insert", "delete"]]
    """The type of edit (replace, insert, delete)."""


# --- WebFetch ---


class WebFetchInput(TypedDict):
    """Input for the WebFetch tool. Fetches content from a URL and processes it with AI."""

    url: str
    """The URL to fetch content from."""
    prompt: str
    """The prompt to run on the fetched content."""


# --- WebSearch ---


class WebSearchInput(TypedDict):
    """Input for the WebSearch tool. Searches the web and returns formatted results."""

    query: str
    """The search query to use."""
    allowed_domains: NotRequired[list[str]]
    """Only include results from these domains."""
    blocked_domains: NotRequired[list[str]]
    """Never include results from these domains."""


# --- TodoWrite ---


class TodoItem(TypedDict):
    """A single todo item."""

    content: str
    """The task description."""
    status: Literal["pending", "in_progress", "completed"]
    """The task status."""
    activeForm: str
    """Active form of the task description."""


class TodoWriteInput(TypedDict):
    """Input for the TodoWrite tool. Creates and manages a structured task list."""

    todos: list[TodoItem]
    """The updated todo list."""


# --- ExitPlanMode ---


class ExitPlanModeInput(TypedDict):
    """Input for the ExitPlanMode tool. Exits planning mode for user approval."""

    plan: str
    """The plan to run by the user for approval."""


# --- ListMcpResources ---


class ListMcpResourcesInput(TypedDict):
    """Input for the ListMcpResources tool. Lists available MCP resources."""

    server: NotRequired[str]
    """Optional server name to filter resources by."""


# --- ReadMcpResource ---


class ReadMcpResourceInput(TypedDict):
    """Input for the ReadMcpResource tool. Reads a specific MCP resource from a server."""

    server: str
    """The MCP server name."""
    uri: str
    """The resource URI to read."""


# --- Union type ---

ToolInput = (
    AgentInput
    | AskUserQuestionInput
    | BashInput
    | BashOutputInput
    | FileEditInput
    | FileReadInput
    | FileWriteInput
    | GlobInput
    | GrepInput
    | KillShellInput
    | NotebookEditInput
    | WebFetchInput
    | WebSearchInput
    | TodoWriteInput
    | ExitPlanModeInput
    | ListMcpResourcesInput
    | ReadMcpResourceInput
)

#: Mapping from tool name to its input type.
TOOL_INPUT_TYPES: dict[str, type[ToolInput]] = {
    "Task": AgentInput,
    "AskUserQuestion": AskUserQuestionInput,
    "Bash": BashInput,
    "BashOutput": BashOutputInput,
    "Edit": FileEditInput,
    "Read": FileReadInput,
    "Write": FileWriteInput,
    "Glob": GlobInput,
    "Grep": GrepInput,
    "KillBash": KillShellInput,
    "NotebookEdit": NotebookEditInput,
    "WebFetch": WebFetchInput,
    "WebSearch": WebSearchInput,
    "TodoWrite": TodoWriteInput,
    "ExitPlanMode": ExitPlanModeInput,
    "ListMcpResources": ListMcpResourcesInput,
    "ReadMcpResource": ReadMcpResourceInput,
}
