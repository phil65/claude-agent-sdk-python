"""List stored Claude Code sessions with metadata."""

from __future__ import annotations

import logging
from pathlib import Path  # noqa: TC003

import anyenv


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
                stripped = line.strip()
                if not stripped:
                    continue
                # Quick string check before parsing
                if "gitBranch" not in stripped and "git_branch" not in stripped:
                    continue
                try:
                    match anyenv.load_json(stripped, return_type=dict):
                        case {"gitBranch": str(branch)} | {"git_branch": str(branch)} if branch:
                            return branch
                except anyenv.JsonLoadError:
                    continue
    except OSError:
        pass
    return None


def _extract_session_metadata(session_path: Path) -> tuple[str | None, str | None]:
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
                        entry = anyenv.load_json(line, return_type=dict)
                        if summary := entry.get("summary"):
                            custom_title = str(summary)
                    except anyenv.JsonLoadError:
                        pass

                elif first_prompt is None and ('"type":"user"' in line or '"type": "user"' in line):
                    try:
                        match anyenv.load_json(line, return_type=dict):
                            case {"message": {"content": str(content)}}:
                                if first_line := content.split("\n")[0].strip():
                                    first_prompt = first_line
                    except anyenv.JsonLoadError:
                        pass

                # Stop early when we have both
                if custom_title is not None and first_prompt is not None:
                    break
    except OSError:
        pass

    return custom_title, first_prompt
