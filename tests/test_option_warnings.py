"""CanUseToolShadowedWarning: on_permission set, but options auto-approve before it runs."""

from __future__ import annotations

from typing import Any
import warnings

import pytest

from clawd_code_sdk import CanUseToolShadowedWarning, ClaudeAgentOptions, ClaudeSDKClient
from clawd_code_sdk._internal.option_warnings import (
    can_use_tool_shadowed_message,
    warn_if_can_use_tool_shadowed,
    whole_tool_allowed,
)
from clawd_code_sdk.models import PermissionResultAllow


async def _allow(tool_name: str, input_data: dict[str, Any], context: Any) -> PermissionResultAllow:
    return PermissionResultAllow()


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        ("Read", "Read"),
        ("Read()", "Read"),
        ("Read(*)", "Read"),
        ("mcp__srv__tool", "mcp__srv__tool"),
        ("Bash(ls:*)", None),
        ("Read(/tmp/**)", None),
        # Malformed: the CLI reads the whole string as a tool name, matching nothing
        ("Bash(ls:*", None),
        ("Read(*x", None),
        ("(*)", None),
        ("", None),
        ("   ", None),
    ],
)
def test_whole_tool_allowed(entry: str, expected: str | None) -> None:
    assert whole_tool_allowed(entry) == expected


def test_bypass_permissions_takes_precedence() -> None:
    message = can_use_tool_shadowed_message("bypassPermissions", ["Read"])
    assert message is not None
    assert "bypassPermissions" in message
    assert "Read" not in message


def test_names_shadowed_tools_once() -> None:
    message = can_use_tool_shadowed_message(None, ["Read", "Read()", "Grep(*)", "Bash(ls:*)"])
    assert message is not None
    assert "will not be invoked for: Read, Grep." in message


@pytest.mark.parametrize("mode", [None, "default", "acceptEdits", "plan"])
def test_silent_without_shadowing(mode: Any) -> None:
    assert can_use_tool_shadowed_message(mode, ["Bash(ls:*)"]) is None
    assert can_use_tool_shadowed_message(mode, []) is None


def test_warns_only_with_a_callback() -> None:
    shadowing = {"allowed_tools": ["Read"], "permission_mode": "bypassPermissions"}
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        warn_if_can_use_tool_shadowed(ClaudeAgentOptions(**shadowing))  # ty:ignore[invalid-argument-type]
        tool_name = ClaudeAgentOptions(on_permission="mcp__perm__ask", **shadowing)  # ty:ignore[invalid-argument-type]
        warn_if_can_use_tool_shadowed(tool_name)
        # Plain construction never warns
        ClaudeAgentOptions(on_permission=_allow, **shadowing)  # ty:ignore[invalid-argument-type]
    with pytest.warns(CanUseToolShadowedWarning, match="Read"):
        warn_if_can_use_tool_shadowed(
            ClaudeAgentOptions(on_permission=_allow, allowed_tools=["Read"])
        )


async def test_connect_warns() -> None:
    options = ClaudeAgentOptions(
        on_permission=_allow,
        permission_mode="bypassPermissions",
        allow_dangerously_skip_permissions=True,
    )

    class _Stop(Exception):  # noqa: N818
        pass

    class _Transport:
        async def connect(self) -> None:
            raise _Stop

    client = ClaudeSDKClient(options, transport=_Transport())  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]
    with pytest.warns(CanUseToolShadowedWarning, match="bypassPermissions"), pytest.raises(_Stop):
        await client.connect()
