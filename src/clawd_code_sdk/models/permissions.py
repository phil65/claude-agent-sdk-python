"""Permission system types."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from clawd_code_sdk.models.base import (
    ClaudeCodeBaseModel,
    ElicitationAction,  # noqa: TC001
    PermissionBehavior,
    PermissionMode,
)
from clawd_code_sdk.models.input_types import AskUserQuestionInput, ToolInput


if TYPE_CHECKING:
    import mcp.types


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

    # signal: Any | None = None
    # """Reserved for future abort signal support. Currently always None."""

    agent_id: str | None = None
    """The agent that initiated the tool call, if in a multi-agent setup."""

    decision_reason: str | None = None
    """Why the CLI triggered the permission check."""

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
class ElicitationResult:
    """Elicitation response from the SDK consumer."""

    action: ElicitationAction
    """The action taken: accept, decline, or cancel."""
    content: dict[str, Any] | None = None
    """Form field values (only for 'accept' action with 'form' mode)."""

    def to_mcp(self) -> mcp.types.ElicitResult:
        """Convert to the MCP ElicitResult type."""
        import mcp.types

        return mcp.types.ElicitResult(action=self.action, content=self.content)

    @classmethod
    def from_mcp(cls, result: mcp.types.ElicitResult) -> ElicitationResult:
        """Create from an MCP ElicitResult."""
        return cls(action=result.action, content=result.content)
