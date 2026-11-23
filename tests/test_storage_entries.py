"""Entry types and fields of current Claude Code transcripts load into typed models."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from pydantic import TypeAdapter

from clawd_code_sdk.storage.helpers import read_session, write_entry
from clawd_code_sdk.storage.models import (
    ClaudeAssistantEntry,
    ClaudeAttachmentEntry,
    ClaudeAwaySummaryEntry,
    ClaudeCostStateEntry,
    ClaudeDerivedFromEntry,
    ClaudeEntryBase,
    ClaudeFileHistoryDeltaEntry,
    ClaudeForkContextRefEntry,
    ClaudeJSONLEntry,
    ClaudePermissionModeEntry,
    ClaudeProgressEntry,
    ClaudeRelocatedEntry,
    ClaudeTurnDurationEntry,
    ClaudeUnknownEntry,
    ClaudeUserEntry,
)


if TYPE_CHECKING:
    from pathlib import Path


ADAPTER = TypeAdapter[ClaudeJSONLEntry](ClaudeJSONLEntry)
COMMON = {
    "sessionId": "s1",
    "timestamp": "2026-01-01T00:00:00.000Z",
    "cwd": "/tmp/project",
    "version": "3.0.0",
    "userType": "external",
    "isSidechain": False,
}


def _entry(**data: Any) -> dict[str, Any]:
    return {**COMMON, **data}


def test_attachment_entries_are_chain_entries() -> None:
    data = _entry(
        type="attachment",
        uuid="a1",
        parentUuid="u1",
        attachment={"type": "hook_success", "hookName": "SessionStart", "exitCode": 0},
    )
    entry = ADAPTER.validate_python(data)
    assert isinstance(entry, ClaudeAttachmentEntry)
    assert isinstance(entry, ClaudeEntryBase)
    assert (entry.uuid, entry.parent_uuid) == ("a1", "u1")
    assert entry.attachment.type == "hook_success"
    assert entry.attachment.model_extra == {"hookName": "SessionStart", "exitCode": 0}


def test_attachment_payload_round_trips(tmp_path: Path) -> None:
    payload = {"type": "date", "date": "2026-01-01", "changed": True}
    data = _entry(type="attachment", uuid="a1", parentUuid=None, attachment=payload)
    path = tmp_path / "s.jsonl"
    path.write_text(json.dumps(data) + "\n")
    [entry] = read_session(path)
    copy = tmp_path / "copy.jsonl"
    write_entry(copy, entry)
    assert json.loads(copy.read_text())["attachment"] == payload


def test_progress_entries_are_chain_entries() -> None:
    data = _entry(
        type="progress",
        uuid="p1",
        parentUuid="u1",
        toolUseID="toolu_1",
        parentToolUseID="toolu_0",
        data={"type": "hook_progress", "hookEvent": "PreToolUse"},
    )
    entry = ADAPTER.validate_python(data)
    assert isinstance(entry, ClaudeProgressEntry)
    assert isinstance(entry, ClaudeEntryBase)
    assert (entry.tool_use_id, entry.parent_tool_use_id) == ("toolu_1", "toolu_0")


def test_system_subtypes() -> None:
    away = ADAPTER.validate_python(
        _entry(type="system", subtype="away_summary", uuid="x", content="recap", isMeta=True)
    )
    assert isinstance(away, ClaudeAwaySummaryEntry)
    turn = ADAPTER.validate_python(
        _entry(type="system", subtype="turn_duration", uuid="y", durationMs=5, messageCount=3)
    )
    assert isinstance(turn, ClaudeTurnDurationEntry)
    assert turn.message_count == 3


def test_tool_result_entry_fields() -> None:
    data = _entry(
        type="user",
        uuid="u2",
        parentUuid="a1",
        message={
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "toolu_1", "content": "ok"}],
        },
        sourceToolAssistantUUID="a1",
        permissionDecision={"decision": "allow", "source": "rule"},
        sandboxed=True,
    )
    entry = ADAPTER.validate_python(data)
    assert isinstance(entry, ClaudeUserEntry)
    assert entry.source_tool_assistant_uuid == "a1"
    assert entry.sandboxed is True
    dumped = entry.model_dump(by_alias=True)
    assert dumped["sourceToolAssistantUUID"] == "a1"


def test_assistant_entry_fields() -> None:
    data = _entry(
        type="assistant",
        uuid="a1",
        parentUuid="u1",
        requestId="req_1",
        requestedModel="claude-x",
        apiErrorStatus=429,
        error="rate_limit",
        message={
            "model": "claude-x",
            "id": "msg_1",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "hi"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 1, "output_tokens": 2},
            "container": None,
            "context_management": None,
        },
    )
    entry = ADAPTER.validate_python(data)
    assert isinstance(entry, ClaudeAssistantEntry)
    assert (entry.requested_model, entry.api_error_status, entry.error) == (
        "claude-x",
        429,
        "rate_limit",
    )


def test_session_metadata_entries() -> None:
    mode = ADAPTER.validate_python(
        {"type": "permission-mode", "permissionMode": "plan", "sessionId": "s1"}
    )
    assert isinstance(mode, ClaudePermissionModeEntry)
    assert mode.permission_mode == "plan"

    cost = ADAPTER.validate_python(
        {
            "type": "cost-state",
            "sessionId": "s1",
            "totalCostUSD": 1.5,
            "totalAPIDuration": 100,
            "totalAPIDurationWithoutRetries": 90,
            "totalToolDuration": 10,
            "totalLinesAdded": 3,
            "totalLinesRemoved": 1,
            "totalDuration": 200,
            "startTime": 1,
            "hasUnknownModelCost": False,
            "modelUsage": {
                "claude-x": {
                    "inputTokens": 1,
                    "outputTokens": 2,
                    "cacheReadInputTokens": 3,
                    "cacheCreationInputTokens": 4,
                    "cacheCreationEphemeral5mInputTokens": 4,
                    "cacheCreationEphemeral1hInputTokens": 0,
                    "thinkingTokens": 0,
                    "webSearchRequests": 0,
                    "costUSD": 1.5,
                }
            },
        }
    )
    assert isinstance(cost, ClaudeCostStateEntry)
    assert cost.total_cost_usd == 1.5
    assert cost.model_usage["claude-x"].cache_creation_ephemeral_5m_input_tokens == 4

    relocated = ADAPTER.validate_python(
        {"type": "relocated", "relocatedCwd": "/new", "sessionId": "s1"}
    )
    assert isinstance(relocated, ClaudeRelocatedEntry)

    derived = ADAPTER.validate_python(
        {
            "type": "derived-from",
            "v": 1,
            "sessionId": "s1",
            "sessions": [{"id": "s0", "type": "claude_code_session", "via": "clear"}],
        }
    )
    assert isinstance(derived, ClaudeDerivedFromEntry)
    assert derived.sessions[0].via == "clear"

    fork = ADAPTER.validate_python(
        {
            "type": "fork-context-ref",
            "agentId": "ag1",
            "parentSessionId": "s0",
            "parentLastUuid": "u9",
            "contextLength": 12,
        }
    )
    assert isinstance(fork, ClaudeForkContextRefEntry)

    delta = ADAPTER.validate_python(
        {
            "type": "file-history-delta",
            "messageId": "m2",
            "snapshotMessageId": "m1",
            "trackingPath": "src/a.py",
            "backup": {
                "backupFileName": None,
                "version": 1,
                "backupTime": "2026-01-01T00:00:00.000Z",
                "realParentDir": "/tmp/project/src",
            },
            "timestamp": "2026-01-01T00:00:00.000Z",
        }
    )
    assert isinstance(delta, ClaudeFileHistoryDeltaEntry)
    assert delta.backup.backup_file_name is None


def _write_lines(path: Path, *rows: dict[str, Any]) -> Path:
    path.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows))
    return path


def test_extract_title_prefers_custom_then_ai_title(tmp_path: Path) -> None:
    from clawd_code_sdk.storage.helpers import extract_title

    prompt = _entry(type="user", uuid="u1", message={"role": "user", "content": "Fix the bug"})
    ai = {"type": "ai-title", "sessionId": "s1", "aiTitle": "Bug fixing"}
    custom = {"type": "custom-title", "sessionId": "s1", "customTitle": "My title"}
    assert extract_title(_write_lines(tmp_path / "a.jsonl", prompt)) == "Fix the bug"
    assert extract_title(_write_lines(tmp_path / "b.jsonl", prompt, ai)) == "Bug fixing"
    assert extract_title(_write_lines(tmp_path / "c.jsonl", prompt, ai, custom)) == "My title"
    task = {"type": "task-summary", "sessionId": "s1", "summary": "busy", "timestamp": "t"}
    assert extract_title(_write_lines(tmp_path / "d.jsonl", task, prompt)) == "Fix the bug"
    assert extract_title(tmp_path / "missing.jsonl") is None
    assert extract_title(_write_lines(tmp_path / "e.jsonl", prompt), max_chars=3) == "Fix..."


def test_project_dir_names_match_claude_code() -> None:
    from clawd_code_sdk.storage.helpers import encode_project_path, path_to_claude_dir_name

    assert encode_project_path("/home/user/project") == "-home-user-project"
    assert encode_project_path("/home/user/.config/my_app") == "-home-user--config-my-app"
    long_name = path_to_claude_dir_name("/x" * 150)
    assert len(long_name) > 200
    assert long_name.startswith("-x-x")


def test_invalid_known_entry_is_kept_as_unknown(tmp_path: Path) -> None:
    """A known type that doesn't match its model is kept, not dropped."""
    broken = _entry(type="assistant", uuid="a1", parentUuid=None, message={"role": "assistant"})
    path = _write_lines(tmp_path / "s.jsonl", broken)
    [entry] = read_session(path)
    assert isinstance(entry, ClaudeUnknownEntry)
    assert entry.type == "assistant"
    copy = tmp_path / "copy.jsonl"
    write_entry(copy, entry)
    assert json.loads(copy.read_text()) == broken


def test_write_entry_omits_unset_optional_fields(tmp_path: Path) -> None:
    entry = ClaudeUserEntry.model_validate(
        _entry(type="user", uuid="u1", message={"role": "user", "content": "hi"})
    )
    entry_without_parent = entry.model_copy()
    path = tmp_path / "s.jsonl"
    write_entry(path, entry_without_parent)
    written = json.loads(path.read_text())
    assert written["parentUuid"] is None  # always written, like Claude Code does
    assert all(value is not None for key, value in written.items() if key != "parentUuid")
    assert written["message"] == {"role": "user", "content": "hi"}  # nested too


def test_write_entry_keeps_nulls_read_from_file(tmp_path: Path) -> None:
    row = _entry(
        type="user",
        uuid="u1",
        parentUuid=None,
        gitBranch=None,
        message={"role": "user", "content": "hi"},
    )
    path = _write_lines(tmp_path / "s.jsonl", row)
    [entry] = read_session(path)
    copy = tmp_path / "copy.jsonl"
    write_entry(copy, entry)
    assert json.loads(copy.read_text()) == row


def test_unknown_fields_survive_a_round_trip(tmp_path: Path) -> None:
    """Fields the models don't know (new Claude Code versions add them often) are kept."""
    row = _entry(
        type="user",
        uuid="u1",
        parentUuid=None,
        someNewFlag=True,
        message={"role": "user", "content": "hi", "someNewMessageField": 1},
    )
    path = _write_lines(tmp_path / "s.jsonl", row)
    [entry] = read_session(path)
    copy = tmp_path / "copy.jsonl"
    write_entry(copy, entry)
    assert json.loads(copy.read_text()) == row


def test_tool_results_keep_wire_keys_and_unknown_fields(tmp_path: Path) -> None:
    """Tool results are TypedDicts named as on the wire: no camelCase renaming on write."""
    usage = {
        "input_tokens": 5,
        "output_tokens": 7,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 3,
        "server_tool_use": None,
        "service_tier": "standard",
        "cache_creation": None,
    }
    result = {
        "status": "completed",
        "agentId": "agent-1",
        "content": [{"type": "text", "text": "done"}],
        "totalToolUseCount": 0,
        "totalDurationMs": 1,
        "totalTokens": 12,
        "usage": usage,
        "prompt": "do it",
        "someNewResultField": True,
    }
    row = _entry(
        type="user",
        uuid="u1",
        parentUuid=None,
        message={"role": "user", "content": "hi"},
        toolUseResult=result,
    )
    path = _write_lines(tmp_path / "s.jsonl", row)
    [entry] = read_session(path)
    copy = tmp_path / "copy.jsonl"
    write_entry(copy, entry)
    assert json.loads(copy.read_text()) == row
