"""Session objects for storage."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


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

    created_at: int | None = None
    """Creation time in milliseconds since epoch."""

    archived: bool | None = None
    """Whether the session has been archived."""


class SessionMessage(BaseModel):
    """A message from a session transcript.

    Returned by ``get_session_messages`` for reading historical session data.
    """

    type: Literal["user", "assistant", "system"]
    uuid: str
    session_id: str
    message: Any
    # timestamp: str
    parent_tool_use_id: str | None = None
    """For subagent messages: id of the Agent ``tool_use`` in the parent session that spawned
    the subagent (from its ``.meta.json`` sidecar). ``None`` for top-level session messages."""
    parent_agent_id: str | None = None
    """For messages of nested subagents: agent id of the subagent that spawned this one."""
