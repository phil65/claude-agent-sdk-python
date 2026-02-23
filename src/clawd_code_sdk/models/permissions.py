"""Permission system types."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from clawd_code_sdk.models import ToolInput
from clawd_code_sdk.models.base import (
    ClaudeCodeBaseModel,
    PermissionBehavior,  # noqa: TC001
    PermissionMode,  # noqa: TC001
)


# Permission Update types (matching TypeScript SDK)
PermissionUpdateDestination = Literal[
    "userSettings",
    "projectSettings",
    "localSettings",
    "session",
    "cliArg",
]


class PermissionRuleValue(ClaudeCodeBaseModel):
    """Permission rule value."""

    tool_name: str
    rule_content: str | None = None


class BasePermissionUpdate(ClaudeCodeBaseModel):
    """Permission update configuration."""

    destination: PermissionUpdateDestination


class RulePermissionUpdate(BasePermissionUpdate):
    """Permission update configuration."""

    type: Literal["addRules", "replaceRules", "removeRules"]
    rules: list[PermissionRuleValue]
    behavior: PermissionBehavior | None = None


class DirectoryPermissionUpdate(BasePermissionUpdate):
    """Permission update configuration."""

    type: Literal["addDirectories", "removeDirectories"]
    directories: list[str]


class ModePermissionUpdate(BasePermissionUpdate):
    """Permission update configuration."""

    type: Literal["setMode"]
    mode: PermissionMode


PermissionUpdate = RulePermissionUpdate | DirectoryPermissionUpdate | ModePermissionUpdate


# Tool callback types
@dataclass
class ToolPermissionContext:
    """Context information for tool permission callbacks.

    Attributes:
        tool_use_id: Unique identifier for this specific tool call within the
            assistant message. Multiple tool calls in the same assistant message
            will have different tool_use_ids.
        signal: Reserved for future abort signal support. Currently always None.
        suggestions: Permission suggestions from CLI for updating permissions
            so the user won't be prompted again for this tool during this session.
        blocked_path: The file path that triggered the permission request, if
            applicable. For example, when a Bash command tries to access a path
            outside allowed directories.
    """

    tool_use_id: str
    signal: Any | None = None  # Future: abort signal support
    suggestions: list[PermissionUpdate] = field(default_factory=list)  # suggestions from CLI
    blocked_path: str | None = None


# Match TypeScript's PermissionResult structure
class PermissionResultAllow(ClaudeCodeBaseModel):
    """Allow permission result."""

    behavior: Literal["allow"] = "allow"
    updated_input: dict[str, Any] | None = None
    updated_permissions: list[PermissionUpdate] | None = None


class PermissionResultDeny(ClaudeCodeBaseModel):
    """Deny permission result."""

    behavior: Literal["deny"] = "deny"
    message: str = ""
    interrupt: bool = False


PermissionResult = PermissionResultAllow | PermissionResultDeny

CanUseTool = Callable[
    [str, ToolInput | dict[str, Any], ToolPermissionContext], Awaitable[PermissionResult]
]
