"""E2E test: parse all local Claude Code JSONL session files."""

from __future__ import annotations

import pytest

from clawd_code_sdk.storage.helpers import get_claude_projects_dir, read_session


@pytest.mark.e2e
def test_parse_all_local_sessions() -> None:
    """Read every JSONL session under ~/.claude/projects and assert zero parse errors."""
    projects_dir = get_claude_projects_dir()
    if not projects_dir.exists():
        pytest.skip("No Claude projects directory found")

    session_files = list(projects_dir.rglob("*.jsonl"))
    if not session_files:
        pytest.skip("No session files found")

    total_entries = 0
    for session_file in session_files:
        entries = read_session(session_file)
        total_entries += len(entries)

    assert total_entries > 0, "Expected at least one parsed entry"
