"""Tests for the additions of @anthropic-ai/claude-agent-sdk 0.3.332 / Claude Code 2.1.332."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

from clawd_code_sdk import ClaudeSDKClient
from clawd_code_sdk.models import (
    SDKControlSetPermissionModeResponse,
    SDKHookCallbackRequest,
    incoming_control_request_adapter,
)


def test_pre_skill_shell_command_hook_callback_parses() -> None:
    hook_input: dict[str, Any] = {
        "session_id": "s1",
        "transcript_path": "/tmp/t.jsonl",
        "cwd": "/tmp",
        "hook_event_name": "PreSkillShellCommand",
        "tool_name": "Bash",
        "tool_input": {"command": "git status"},
        "tool_use_id": "skill-cmd-1",
        "command_name": "commit",
        "invoked_by": "claude",
    }
    request = {"subtype": "hook_callback", "callback_id": "hook_0", "input": hook_input}
    parsed = incoming_control_request_adapter.validate_python(request)
    assert isinstance(parsed, SDKHookCallbackRequest)
    assert parsed.input["hook_event_name"] == "PreSkillShellCommand"
    assert parsed.input["tool_input"] == {"command": "git status"}  # ty:ignore[invalid-key]


async def test_set_permission_mode_returns_effective_mode() -> None:
    client = ClaudeSDKClient()
    query = MagicMock()
    query._send_control_request = AsyncMock(return_value={"mode": "default"})
    client._query = query
    response = await client.set_permission_mode("bypassPermissions")
    assert response == SDKControlSetPermissionModeResponse(mode="default")


async def test_set_permission_mode_without_payload() -> None:
    client = ClaudeSDKClient()
    query = MagicMock()
    query._send_control_request = AsyncMock(return_value={})
    client._query = query
    assert await client.set_permission_mode("plan") is None
