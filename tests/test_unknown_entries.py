"""Entries of types the models don't know load as ClaudeUnknownEntry, unchanged."""

import json
from typing import TYPE_CHECKING

from pydantic import TypeAdapter

from clawd_code_sdk.storage.helpers import read_session, write_entry
from clawd_code_sdk.storage.models import (
    ClaudeJSONLEntry,
    ClaudeLastPromptEntry,
    ClaudeUnknownEntry,
    known_entry_types,
)


if TYPE_CHECKING:
    from pathlib import Path


ADAPTER = TypeAdapter[ClaudeJSONLEntry](ClaudeJSONLEntry)
UNKNOWN = {"type": "future-entry", "someField": "value", "sessionId": "s1"}


def test_unknown_entry_types_load_with_their_data() -> None:
    entry = ADAPTER.validate_python(UNKNOWN)
    assert isinstance(entry, ClaudeUnknownEntry)
    assert entry.type == "future-entry"
    assert entry.model_dump() == UNKNOWN


def test_known_entry_types_keep_their_models() -> None:
    entry = ADAPTER.validate_python({"type": "last-prompt", "lastPrompt": "hi", "sessionId": "s1"})
    assert isinstance(entry, ClaudeLastPromptEntry)
    assert {"user", "assistant", "system", "queue-operation", "last-prompt"} <= known_entry_types()


def test_last_prompt_entries_without_the_prompt() -> None:
    """Newer Claude Code versions write only the message the prompt led to."""
    entry = ADAPTER.validate_python({"type": "last-prompt", "leafUuid": "u1", "sessionId": "s1"})
    assert isinstance(entry, ClaudeLastPromptEntry)
    assert (entry.last_prompt, entry.leaf_uuid) == (None, "u1")


def test_unknown_entries_read_and_write_back_unchanged(tmp_path: Path) -> None:
    path = tmp_path / "session.jsonl"
    path.write_text(json.dumps(UNKNOWN) + "\n")
    [entry] = read_session(path)
    copy = tmp_path / "copy.jsonl"
    write_entry(copy, entry)
    assert json.loads(copy.read_text()) == UNKNOWN
