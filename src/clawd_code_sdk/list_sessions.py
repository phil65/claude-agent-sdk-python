"""List stored Claude Code sessions with metadata."""

from __future__ import annotations

import logging
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING

import anyenv

from clawd_code_sdk.models.messages import SDKSessionInfo
from clawd_code_sdk.storage.helpers import (
    decode_project_path,
    get_claude_projects_dir,
    path_to_claude_dir_name,
)


if TYPE_CHECKING:
    from clawd_code_sdk.models.options import ListSessionsOptions

logger = logging.getLogger(__name__)


def _read_git_branch_from_tail(path: Path) -> str | None:
    """Read git branch from the last entries of a JSONL file.

    Reads from the end of the file for efficiency. Scans backward
    through the last chunk of lines to find an entry with a
    ``gitBranch`` field (not all entry types carry it).

    Args:
        path: Path to the JSONL file.

    Returns:
        The git branch string, or None if not found.
    """
    try:
        with path.open("rb") as f:
            f.seek(0, 2)
            size = f.tell()
            if size == 0:
                return None
            chunk_size = min(size, 32768)
            f.seek(-chunk_size, 2)
            data = f.read().decode("utf-8", errors="ignore")
            lines = data.strip().split("\n")
            for line in reversed(lines):
                line = line.strip()
                if not line:
                    continue
                # Quick string check before parsing
                if "gitBranch" not in line and "git_branch" not in line:
                    continue
                try:
                    entry: dict[str, object] = anyenv.load_json(line, return_type=dict)
                    branch = entry.get("gitBranch") or entry.get("git_branch")
                    if isinstance(branch, str) and branch:
                        return branch
                except anyenv.JsonLoadError:
                    continue
    except OSError:
        pass
    return None


def _extract_session_metadata(
    session_path: Path,
) -> tuple[str | None, str | None]:
    """Extract custom_title and first_prompt from a session file.

    Reads the file line by line, stopping as early as possible.
    Summary entries provide the custom title; the first user message
    provides the first prompt.

    Args:
        session_path: Path to the JSONL session file.

    Returns:
        A ``(custom_title, first_prompt)`` tuple.
    """
    custom_title: str | None = None
    first_prompt: str | None = None

    try:
        with session_path.open(encoding="utf-8", errors="ignore") as fp:
            for line in fp:
                if '"type":"summary"' in line or '"type": "summary"' in line:
                    try:
                        entry: dict[str, object] = anyenv.load_json(line, return_type=dict)
                        if summary := entry.get("summary"):
                            custom_title = str(summary)
                    except anyenv.JsonLoadError:
                        pass

                elif first_prompt is None and ('"type":"user"' in line or '"type": "user"' in line):
                    try:
                        entry = anyenv.load_json(line, return_type=dict)
                        msg = entry.get("message")
                        if isinstance(msg, dict):
                            content = msg.get("content", "")
                            if isinstance(content, str) and content:
                                first_line = content.split("\n")[0].strip()
                                if first_line:
                                    first_prompt = first_line
                    except anyenv.JsonLoadError:
                        pass

                # Stop early when we have both
                if custom_title is not None and first_prompt is not None:
                    break
    except OSError:
        pass

    return custom_title, first_prompt


def _build_session_info(session_path: Path, project_cwd: str | None) -> SDKSessionInfo | None:
    """Build an SDKSessionInfo from a session JSONL file.

    Args:
        session_path: Path to the ``.jsonl`` session file.
        project_cwd: Working directory derived from the project folder name,
            or None if unknown.

    Returns:
        Populated SDKSessionInfo, or None if the file cannot be read.
    """
    try:
        stat = session_path.stat()
    except OSError:
        return None

    session_id = session_path.stem
    last_modified = int(stat.st_mtime * 1000)  # milliseconds since epoch
    file_size = stat.st_size

    custom_title, first_prompt = _extract_session_metadata(session_path)

    # Get git branch from the tail of the file.
    # The raw JSONL uses camelCase ("gitBranch") per ClaudeCodeBaseModel alias config.
    # Not all entry types carry gitBranch, so we scan backward until we find one.
    git_branch = _read_git_branch_from_tail(session_path)

    # Build display summary: prefer custom title, then first prompt, then session ID
    summary = custom_title or first_prompt or session_id

    return SDKSessionInfo(
        session_id=session_id,
        summary=summary,
        last_modified=last_modified,
        file_size=file_size,
        custom_title=custom_title,
        first_prompt=first_prompt,
        git_branch=git_branch,
        cwd=project_cwd,
    )


def _list_session_files_for_dir(directory: str) -> list[tuple[Path, str | None]]:
    """List session files for a specific project directory.

    Args:
        directory: Filesystem path of the project.

    Returns:
        List of ``(session_path, cwd)`` tuples.
    """
    projects_dir = get_claude_projects_dir()
    dir_name = path_to_claude_dir_name(directory)
    project_dir = projects_dir / dir_name
    if not project_dir.is_dir():
        return []
    return [(p, directory) for p in project_dir.glob("*.jsonl")]


def _list_all_session_files() -> list[tuple[Path, str | None]]:
    """List session files across all projects.

    Returns:
        List of ``(session_path, cwd)`` tuples where cwd is decoded
        from the project directory name.
    """
    projects_dir = get_claude_projects_dir()
    if not projects_dir.is_dir():
        return []
    results: list[tuple[Path, str | None]] = []
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        cwd = decode_project_path(project_dir.name)
        for session_file in project_dir.glob("*.jsonl"):
            results.append((session_file, cwd))
    return results


def list_sessions(options: ListSessionsOptions | None = None) -> list[SDKSessionInfo]:
    """List sessions with metadata.

    When ``dir`` is provided in *options*, returns sessions for that project
    directory and its git worktrees. When omitted, returns sessions across
    all projects.

    Args:
        options: Optional filtering/limiting options.

    Returns:
        Session metadata sorted by last modified time (newest first).

    Example::

        from clawd_code_sdk import list_sessions

        # List sessions for a specific project
        sessions = list_sessions({"dir": "/path/to/project"})

        # List all sessions across all projects
        all_sessions = list_sessions()
    """
    opts = options or {}
    directory = opts.get("dir")
    limit = opts.get("limit")

    # Collect session files
    session_files: list[tuple[Path, str | None]]
    if directory is not None:
        session_files = _list_session_files_for_dir(directory)
    else:
        session_files = _list_all_session_files()

    # Build session info for each file
    sessions: list[SDKSessionInfo] = []
    for session_path, cwd in session_files:
        info = _build_session_info(session_path, cwd)
        if info is not None:
            sessions.append(info)

    # Sort by last_modified descending (newest first)
    sessions.sort(key=lambda s: s.last_modified, reverse=True)

    # Apply limit
    if limit is not None and limit > 0:
        sessions = sessions[:limit]

    return sessions
