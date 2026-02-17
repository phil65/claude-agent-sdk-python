"""Claude Code storage provider.

See ARCHITECTURE.md for detailed documentation of the storage format.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import anyenv
from pydantic import TypeAdapter

from clawd_code_sdk.storage.models import ClaudeJSONLEntry


if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


def write_entry(session_path: Path, entry: ClaudeJSONLEntry) -> None:
    """Append an entry to a session file."""
    session_path.parent.mkdir(parents=True, exist_ok=True)
    with session_path.open("a", encoding="utf-8") as f:
        f.write(entry.model_dump_json(by_alias=True) + "\n")


def count_session_messages(session_path: Path) -> int:
    """Count user/assistant messages in a session without full validation.

    Only parses JSON to check the 'type' field, skipping Pydantic validation.

    Args:
        session_path: Path to the JSONL session file

    Returns:
        Number of user/assistant message entries
    """
    count = 0
    with session_path.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                data = anyenv.load_json(stripped, return_type=dict)
                if data.get("type") in ("user", "assistant"):
                    count += 1
            except anyenv.JsonLoadError:
                pass
    return count


def read_session(session_path: Path) -> list[ClaudeJSONLEntry]:
    """Read all entries from a session file."""
    entries: list[ClaudeJSONLEntry] = []
    if not session_path.exists():
        return entries

    adapter = TypeAdapter[ClaudeJSONLEntry](ClaudeJSONLEntry)
    with session_path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            stripped = raw_line.strip()
            if not stripped:
                continue
            try:
                data = anyenv.load_json(stripped, return_type=dict)
                entry = adapter.validate_python(data)
                entries.append(entry)
            except anyenv.JsonLoadError as e:
                logger.warning(
                    "Failed to parse JSONL line (path: %s, error: %s, raw_line: %s)",
                    str(session_path),
                    str(e),
                    raw_line,
                )
    return entries


def get_claude_data_dir() -> Path:
    """Get the Claude Code data directory path.

    Claude Code stores data in ~/.claude rather than the XDG data directory.
    """
    from pathlib import Path

    return Path.home() / ".claude"


def get_claude_projects_dir() -> Path:
    """Get the Claude Code projects directory path."""
    return get_claude_data_dir() / "projects"


def path_to_claude_dir_name(project_path: str) -> str:
    """Convert a filesystem path to Claude Code's directory naming format.

    Claude Code replaces '/' with '-', so '/home/user/project' becomes '-home-user-project'.

    Args:
        project_path: The filesystem path

    Returns:
        The Claude Code directory name format
    """
    return project_path.replace("/", "-")


def get_latest_session(project_path: str) -> Path | None:
    """Get the most recent session file for a project.

    Args:
        project_path: The project path

    Returns:
        Path to the latest session file, or None if no sessions exist
    """
    sessions = list_project_sessions(project_path)
    return sessions[0] if sessions else None


def list_project_sessions(project_path: str) -> list[Path]:
    """List all session files for a project.

    Args:
        project_path: The project path (will be converted to Claude's format)

    Returns:
        List of session file paths, sorted by modification time (newest first)
    """
    projects_dir = get_claude_projects_dir()
    project_dir_name = path_to_claude_dir_name(project_path)
    project_dir = projects_dir / project_dir_name

    if not project_dir.exists():
        return []

    sessions = list(project_dir.glob("*.jsonl"))
    return sorted(sessions, key=lambda p: p.stat().st_mtime, reverse=True)


def encode_project_path(path: str) -> str:
    """Encode a project path to Claude's format.

    Claude encodes paths by replacing / with - and prepending -.
    Example: /home/user/project -> -home-user-project
    """
    return path.replace("/", "-")


def decode_project_path(encoded: str) -> str:
    """Decode a Claude project path back to filesystem path.

    Example: -home-user-project -> /home/user/project
    """
    encoded = encoded.removeprefix("-")
    return "/" + encoded.replace("-", "/")


def extract_title(session_path: Path, max_chars: int = 60) -> str | None:
    """Extract title from session file efficiently.

    Looks for a summary entry first, then falls back to the first line
    of the first user message. Stops reading as soon as a title is found.

    Args:
        session_path: Path to the JSONL session file
        max_chars: Maximum characters for title (truncates with '...')

    Returns:
        Extracted title or None if no suitable content found
    """
    if not session_path.exists():
        return None

    try:
        with session_path.open(encoding="utf-8", errors="ignore") as fp:
            for line in fp:
                # Summary entries take priority
                if '"type":"summary"' in line:
                    try:
                        entry = anyenv.load_json(line, return_type=dict)
                        if summary := entry.get("summary"):
                            return str(summary)
                    except anyenv.JsonLoadError:
                        pass

                # First user message as fallback - stop here
                if '"type":"user"' in line:
                    try:
                        entry = anyenv.load_json(line, return_type=dict)
                        msg = entry.get("message", {})
                        content = msg.get("content", "")
                        if isinstance(content, str) and content:
                            # Use first line only, strip whitespace
                            first_line = content.split("\n")[0].strip()
                            if len(first_line) > max_chars:
                                return first_line[:max_chars] + "..."
                            return first_line if first_line else None
                    except anyenv.JsonLoadError:
                        pass
                    break  # Stop after first user message
    except OSError:
        pass

    return None


# def parse_entry(line: str) -> ClaudeCodeEntry | None:
#     """Parse a single JSONL line into a Claude Code entry.

#     Args:
#         line: A single line from the JSONL file

#     Returns:
#         Parsed entry or None if the line is empty or unparseable
#     """
#     line = line.strip()
#     if not line:
#         return None

#     data = anyenv.load_json(line, return_type=dict)
#     try:
#         return _entry_adapter.validate_python(data)
#     except ValidationError:
#         return None


# def load_session(session_path: Path) -> list[ClaudeCodeEntry]:
#     """Load all entries from a Claude Code session file.

#     Args:
#         session_path: Path to the .jsonl session file

#     Returns:
#         List of parsed entries
#     """
#     with session_path.open() as f:
#         return [entry for line in f if (entry := parse_entry(line))]


# def get_main_conversation(
#     entries: list[ClaudeCodeEntry],
#     *,
#     include_sidechains: bool = False,
# ) -> list[ClaudeCodeMessageEntry]:
#     """Extract the main conversation thread from entries.

#     Claude Code supports forking conversations via parentUuid. This function
#     follows the parent chain to reconstruct the main conversation, optionally
#     including or excluding sidechain messages.

#     Args:
#         entries: All entries from the session
#         include_sidechains: If True, include sidechain entries. If False (default),
#             only include the main conversation thread.

#     Returns:
#         Entries in conversation order, following the parent chain
#     """
#     # Filter to message entries (not queue operations)
#     message_entries: list[ClaudeCodeMessageEntry] = [
#         e
#         for e in entries
#         if isinstance(e, ClaudeCodeUserEntry | ClaudeCodeAssistantEntry | ClaudeCodeSummary)
#     ]

#     if not message_entries:
#         return []

#     # Build children lookup
#     children: dict[str | None, list[ClaudeCodeMessageEntry]] = {}
#     for entry in message_entries:
#         parent = entry.parent_uuid
#         children.setdefault(parent, []).append(entry)

#     # Find root(s) - entries with no parent
#     roots = children.get(None, [])

#     if not roots:
#         # No roots found, fall back to file order
#         if include_sidechains:
#             return message_entries
#         return [e for e in message_entries if not e.is_sidechain]

#     # Walk the tree, preferring non-sidechain entries
#     result: list[ClaudeCodeMessageEntry] = []

#     def walk(entry: ClaudeCodeMessageEntry) -> None:
#         if include_sidechains or not entry.is_sidechain:
#             result.append(entry)

#         # Get children of this entry
#         entry_children = children.get(entry.uuid, [])

#         # Sort children: non-sidechains first, then by timestamp
#         entry_children.sort(key=lambda e: (e.is_sidechain, e.timestamp))

#         for child in entry_children:
#             walk(child)

#     # Start from roots (sorted by timestamp)
#     roots.sort(key=lambda e: e.timestamp)
#     for root in roots:
#         walk(root)

#     return result
