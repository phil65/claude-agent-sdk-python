"""Claude Code storage provider.

See ARCHITECTURE.md for detailed documentation of the storage format.
"""

from contextlib import contextmanager
import functools
import gc
import json
import logging
import threading
from typing import TYPE_CHECKING, Any

import anyenv
from pydantic import TypeAdapter, ValidationError


if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    from clawd_code_sdk.storage.models import ClaudeJSONLEntry


logger = logging.getLogger(__name__)


@functools.cache
def _entry_adapter() -> TypeAdapter[ClaudeJSONLEntry]:
    """Build the entry adapter once: constructing it takes ~80 ms."""
    from clawd_code_sdk.storage.models import ClaudeJSONLEntry

    return TypeAdapter[ClaudeJSONLEntry](ClaudeJSONLEntry)


_gc_lock = threading.Lock()
_gc_state = {"depth": 0, "was_enabled": False}


@contextmanager
def _gc_paused() -> Generator[None]:
    """Pause the cyclic garbage collector while bulk-building objects.

    Loading a large transcript creates hundreds of thousands of container objects, which
    triggers repeated full collections that find nothing to free (about half the load time
    on a 230 MB transcript). The previous state is restored afterwards.
    """
    # gc.disable() is process-wide: overlapping loads (threads) share one pause, and
    # the GC comes back only when the last of them ends, if it was on before the first.
    with _gc_lock:
        if _gc_state["depth"] == 0:
            _gc_state["was_enabled"] = gc.isenabled()
            gc.disable()
        _gc_state["depth"] += 1
    try:
        yield
    finally:
        with _gc_lock:
            _gc_state["depth"] -= 1
            if _gc_state["depth"] == 0 and _gc_state["was_enabled"]:
                gc.enable()


def write_entry(session_path: Path, entry: ClaudeJSONLEntry) -> None:
    """Append an entry to a session file."""
    session_path.parent.mkdir(parents=True, exist_ok=True)
    with session_path.open("a", encoding="utf-8") as f:
        f.write(_entry_to_json(entry) + "\n")


def _entry_to_json(entry: ClaudeJSONLEntry) -> str:
    """Serialize an entry the way Claude Code writes it.

    Fields that are ``None`` and were never set (neither read from a file nor passed
    in) are left out, at every nesting level, so the many optional fields don't show
    up as ``null``. Fields that were set keep their value, ``null`` included, so read
    entries round-trip unchanged. ``parentUuid`` is always written: Claude Code
    writes ``null`` for the first entry of a chain.
    """
    from clawd_code_sdk.storage.models import ClaudeEntryBase

    full = entry.model_dump(mode="json", by_alias=True)
    explicit = entry.model_dump(mode="json", by_alias=True, exclude_unset=True)
    data = _drop_unset_nulls(full, explicit)
    if isinstance(entry, ClaudeEntryBase):
        data["parentUuid"] = full.get("parentUuid")
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False)


def _drop_unset_nulls(full: Any, explicit: Any) -> Any:
    """Drop ``None`` values from ``full`` that ``explicit`` (an exclude_unset dump) lacks."""
    if isinstance(full, dict):
        given = explicit if isinstance(explicit, dict) else {}
        return {
            key: _drop_unset_nulls(value, given.get(key))
            for key, value in full.items()
            if value is not None or key in given
        }
    if isinstance(full, list):
        given_items = explicit if isinstance(explicit, list) and len(explicit) == len(full) else []
        return [
            _drop_unset_nulls(value, given_items[i] if given_items else None)
            for i, value in enumerate(full)
        ]
    return full


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

    from clawd_code_sdk.storage.models import ClaudeUnknownEntry

    adapter = _entry_adapter()
    # Bytes, not text: the JSON parser takes bytes, so decoding every line first is wasted work.
    with _gc_paused(), session_path.open("rb") as f:
        for raw_line in f:
            if not raw_line.strip():
                continue
            try:
                data = anyenv.load_json(raw_line, return_type=dict)
                entry = adapter.validate_python(data)
                entries.append(entry)
            except (anyenv.JsonLoadError, TypeError) as e:  # TypeError: not an object
                msg = "Failed to parse JSONL line (path: %s, error: %s, raw_line: %s)"
                logger.warning(msg, str(session_path), str(e), raw_line.decode(errors="replace"))
            except ValidationError as e:
                # A known type that doesn't match its model (a new field shape, say):
                # keep the line as an unknown entry instead of losing it.
                msg = "Failed to validate JSONL entry, keeping it unparsed (path: %s, error: %s)"
                logger.warning(msg, str(session_path), str(e))
                if isinstance(data.get("type"), str):
                    entries.append(ClaudeUnknownEntry.model_validate(data))
    return entries


def get_claude_data_dir() -> Path:
    """Get the Claude Code data directory (``$CLAUDE_CONFIG_DIR``, default ``~/.claude``)."""
    from clawd_code_sdk._internal.sessions import _get_claude_config_home_dir

    return _get_claude_config_home_dir()


def get_claude_projects_dir() -> Path:
    """Get the Claude Code projects directory path."""
    return get_claude_data_dir() / "projects"


def path_to_claude_dir_name(project_path: str) -> str:
    """Convert a filesystem path to Claude Code's project directory name.

    Claude Code replaces every non-alphanumeric character with '-', so
    '/home/user/my.project' becomes '-home-user-my-project'. Names longer than
    200 characters are truncated and get a hash suffix.

    Args:
        project_path: The filesystem path

    Returns:
        The Claude Code directory name format
    """
    from clawd_code_sdk._internal.sessions import _sanitize_path

    return _sanitize_path(project_path)


def get_latest_session(project_path: str) -> Path | None:
    """Get the path for the most recent session file for given project if existing."""
    sessions = list_project_session_files(project_path)
    return sessions[0] if sessions else None


def list_project_session_files(project_path: str) -> list[Path]:
    """List all session files for given project path, sorted by modification time (newest first)."""
    projects_dir = get_claude_projects_dir()
    project_dir_name = path_to_claude_dir_name(project_path)
    project_dir = projects_dir / project_dir_name

    if not project_dir.exists():
        return []

    sessions = list(project_dir.glob("*.jsonl"))
    return sorted(sessions, key=lambda p: p.stat().st_mtime, reverse=True)


def encode_project_path(path: str) -> str:
    """Encode a project path to Claude's format (see :func:`path_to_claude_dir_name`).

    Example: /home/user/.config/project -> -home-user--config-project
    """
    return path_to_claude_dir_name(path)


def decode_project_path(encoded: str) -> str:
    """Decode a Claude project path back to filesystem path (best effort).

    The encoding is lossy ('-', '.', '_' and '/' all become '-'), so this is only
    a guess; prefer the ``cwd`` recorded in the session's entries.

    Example: -home-user-project -> /home/user/project
    """
    encoded = encoded.removeprefix("-")
    return "/" + encoded.replace("-", "/")


def extract_title(session_path: Path, max_chars: int = 60) -> str | None:
    """Extract a display title from a session file without parsing all of it.

    Reads only the head and tail of the file. Preference order: the last
    user-set title (``custom-title``), the last AI-generated title
    (``ai-title``), a legacy ``summary`` entry, then the first meaningful
    user prompt.

    Args:
        session_path: Path to the JSONL session file
        max_chars: Maximum characters for title (truncates with '...')

    Returns:
        Extracted title or None if no suitable content found
    """
    from clawd_code_sdk._internal.sessions import (
        _extract_first_prompt_from_head,
        _extract_last_json_string_field,
        _read_session_lite,
    )

    lite = _read_session_lite(session_path)
    if lite is None:
        return None
    head, tail = lite.head, lite.tail
    # Only legacy summary entries: other entry types carry a "summary" key too.
    summary_line = next((ln for ln in head.split("\n") if ln.startswith('{"type":"summary"')), "")
    title = (
        _extract_last_json_string_field(tail, "customTitle")
        or _extract_last_json_string_field(head, "customTitle")
        or _extract_last_json_string_field(tail, "aiTitle")
        or _extract_last_json_string_field(head, "aiTitle")
        or _extract_last_json_string_field(summary_line, "summary")
        or _extract_first_prompt_from_head(head).split("\n")[0].strip()
    )
    if not title:
        return None
    return title[:max_chars] + "..." if len(title) > max_chars else title


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
