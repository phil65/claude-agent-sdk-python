"""Permission system types."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from clawd_code_sdk.models.base import (
    ClaudeCodeBaseModel,
    ElicitationAction,  # noqa: TC001
    ElicitationMode,  # noqa: TC001
    PermissionBehavior,
    PermissionMode,
)
from clawd_code_sdk.models.input_types import AskUserQuestionInput, ToolInput


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
    """Context information for tool permission callbacks."""

    tool_use_id: str
    """Unique identifier for this specific tool call within the assistant message.

    Multiple tool calls in the same assistant message will have different tool_use_ids.
    """

    signal: Any | None = None
    """Reserved for future abort signal support. Currently always None."""

    suggestions: list[PermissionUpdate] = field(default_factory=list)
    """Permission suggestions from CLI for updating permissions.

    So the user won't be prompted again for this tool during this session.
    """

    blocked_path: str | None = None
    """The file path that triggered the permission request, if applicable.

    For example, when a Bash command tries to access a path outside allowed directories.
    """

    title: str | None = None
    """Full permission prompt sentence rendered by the bridge.

    E.g. "Claude wants to read foo.txt". Use this as the primary prompt
    text when present instead of reconstructing from toolName+input.
    """

    display_name: str | None = None
    """Short noun phrase for the tool action (e.g. "Read file").

    Suitable for button labels or compact UI.
    """

    description: str | None = None
    """Human-readable subtitle from the bridge.

    E.g. "Claude will have read and write access to files in ~/Downloads".
    """


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

OnUserQuestion = Callable[
    [AskUserQuestionInput, ToolPermissionContext], Awaitable[PermissionResult]
]
"""Callback for handling AskUserQuestion elicitation requests.

Called when Claude asks the user a clarifying question.
The callback should return a PermissionResultAllow with updated_input
containing the answers, or a PermissionResultDeny to cancel.
"""


@dataclass
class ElicitationRequest:
    """Elicitation request from an MCP server, asking the SDK consumer for user input."""

    server_name: str
    """Name of the MCP server requesting elicitation."""
    message: str
    """Message to display to the user."""
    mode: ElicitationMode | None = None
    """Elicitation mode: 'form' for structured input, 'url' for browser-based auth."""
    url: str | None = None
    """URL to open (only for 'url' mode)."""
    elicitation_id: str | None = None
    """Elicitation ID for correlating URL elicitations with completion notifications."""
    requested_schema: dict[str, Any] | None = None
    """JSON Schema for the requested input (only for 'form' mode)."""


@dataclass
class ElicitationResult:
    """Elicitation response from the SDK consumer."""

    action: ElicitationAction
    """The action taken: accept, decline, or cancel."""
    content: dict[str, Any] | None = None
    """Form field values (only for 'accept' action with 'form' mode)."""


OnElicitation = Callable[[ElicitationRequest], Awaitable[ElicitationResult]]
"""Callback for handling MCP elicitation requests.

Called when an MCP server requests user input and no hook handles it.
If not provided, elicitation requests will be declined automatically.
"""
