"""Session objects for storage."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Self, TypedDict

from pydantic import BaseModel, ConfigDict

from clawd_code_sdk.list_sessions import _extract_session_metadata, _read_git_branch_from_tail


if TYPE_CHECKING:
    from pathlib import Path


class SDKSessionInfo(BaseModel):
    """Session metadata returned by list_sessions."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    """Unique session identifier (UUID)."""

    summary: str
    """Display title for the session: custom title, auto-generated summary, or first prompt."""

    last_modified: int
    """Last modified time in milliseconds since epoch."""

    file_size: int | None = None
    """Session file size in bytes."""

    custom_title: str | None = None
    """User-set session title via /rename."""

    first_prompt: str | None = None
    """First meaningful user prompt in the session."""

    git_branch: str | None = None
    """Git branch at the end of the session."""

    cwd: str | None = None
    """Working directory for the session."""

    tag: str | None = None
    """User-set session tag."""

    created_at: float | None = None
    """Creation time in milliseconds since epoch."""

    @classmethod
    def from_session_file(cls, session_path: Path, project_cwd: str | None) -> Self:
        """Build an SDKSessionInfo from a session JSONL file.

        Args:
            session_path: Path to the ``.jsonl`` session file.
            project_cwd: Working directory derived from the project folder name,
                or None if unknown.

        Returns:
            Populated SDKSessionInfo, or None if the file cannot be read.
        """
        stat = session_path.stat()
        custom_title, first_prompt = _extract_session_metadata(session_path)
        # Get git branch from the tail of the file.
        # The raw JSONL uses camelCase ("gitBranch") per ClaudeCodeBaseModel alias config.
        # Not all entry types carry gitBranch, so we scan backward until we find one.
        # Build display summary: prefer custom title, then first prompt, then session ID
        return cls(
            session_id=session_path.stem,
            summary=custom_title or first_prompt or session_path.stem,
            last_modified=int(stat.st_mtime * 1000),  # milliseconds since epoch,
            file_size=stat.st_size,
            custom_title=custom_title,
            first_prompt=first_prompt,
            git_branch=_read_git_branch_from_tail(session_path),
            cwd=project_cwd,
        )


class SessionMessage(TypedDict):
    """A message from a session transcript.

    Returned by ``get_session_messages`` for reading historical session data.
    """

    type: Literal["user", "assistant", "system"]
    uuid: str
    session_id: str
    message: Any
    # timestamp: str
    parent_tool_use_id: str | None
