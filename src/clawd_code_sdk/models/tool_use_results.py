"""Tool use result types from the Claude Code CLI.

These TypedDicts define the internal result structures that the Claude Code CLI
attaches to user messages as ``tool_use_result``. This is a **CLI-internal format**
intended for UI rendering — it is *not* the same as the tool output schemas that
the LLM sees (those are in ``output_types.py``).

The shapes here carry richer data (original file content, structured patches,
separate stdout/stderr, etc.) that is useful for downstream consumers like
protocol adapters (OpenCode, AG-UI) but never sent back to the model.
"""

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict


# --- Write ---


class WriteToolUseResult(TypedDict):
    """Internal CLI result for the Write tool."""

    filePath: str
    """Absolute path of the written file."""
    content: str
    """Content that was written."""


# --- Edit ---


class StructuredPatchHunk(TypedDict):
    """A single hunk in a structured patch."""

    oldStart: int
    """Starting line number in the original file."""
    oldLines: int
    """Number of lines in the original file."""
    newStart: int
    """Starting line number in the new file."""
    newLines: int
    """Number of lines in the new file."""
    lines: list[str]
    """Diff lines prefixed with ' ' (context), '+' (added), or '-' (removed)."""


class EditToolUseResult(TypedDict):
    """Internal CLI result for the Edit tool."""

    filePath: str
    """Absolute path of the edited file."""
    originalFile: NotRequired[str]
    """Full content of the file before the edit."""
    oldString: NotRequired[str]
    """The text that was replaced."""
    newString: NotRequired[str]
    """The replacement text."""
    structuredPatch: NotRequired[list[StructuredPatchHunk]]
    """Structured patch describing the changes."""


# --- Read ---


class ReadFileInfo(TypedDict):
    """Nested file info inside a Read tool result."""

    filePath: str
    """Absolute path of the file."""
    content: str
    """File content (possibly truncated)."""
    numLines: NotRequired[int]
    """Number of lines returned."""
    startLine: NotRequired[int]
    """Starting line number (1-based)."""
    totalLines: NotRequired[int]
    """Total number of lines in the file."""


class ReadToolUseResult(TypedDict):
    """Internal CLI result for the Read tool."""

    file: ReadFileInfo
    """Nested file information."""


# --- Bash ---


class BashToolUseResult(TypedDict):
    """Internal CLI result for the Bash tool."""

    stdout: NotRequired[str]
    """Standard output from the command."""
    stderr: NotRequired[str]
    """Standard error from the command."""
    interrupted: NotRequired[bool]
    """Whether the command was interrupted."""


# --- TodoWrite ---


class TodoUseResultItem(TypedDict):
    """A single todo item in the CLI result."""

    content: str
    """The task description."""
    status: Literal["pending", "in_progress", "completed"]
    """The task status."""


class TodoWriteToolUseResult(TypedDict):
    """Internal CLI result for the TodoWrite tool."""

    newTodos: list[TodoUseResultItem]
    """The updated list of todos."""


# --- Union type ---

ToolUseResult = (
    WriteToolUseResult
    | EditToolUseResult
    | ReadToolUseResult
    | BashToolUseResult
    | TodoWriteToolUseResult
)
