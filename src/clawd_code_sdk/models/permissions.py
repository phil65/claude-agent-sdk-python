"""Permission system types."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from clawd_code_sdk.models import ToolInput


if TYPE_CHECKING:
    from .base import PermissionMode


# Permission Update types (matching TypeScript SDK)
PermissionUpdateDestination = Literal[
    "userSettings",
    "projectSettings",
    "localSettings",
    "session",
    "cliArg",
]

PermissionBehavior = Literal["allow", "deny", "ask"]


@dataclass
class PermissionRuleValue:
    """Permission rule value."""

    tool_name: str
    rule_content: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert PermissionRuleValue to dictionary format matching TypeScript control protocol."""
        return {"toolName": self.tool_name, "ruleContent": self.rule_content}


@dataclass(kw_only=True)
class BasePermissionUpdate:
    """Permission update configuration."""

    type: str
    destination: PermissionUpdateDestination


@dataclass(kw_only=True)
class RulePermissionUpdate(BasePermissionUpdate):
    """Permission update configuration."""

    type: Literal["addRules", "replaceRules", "removeRules"]
    rules: list[PermissionRuleValue]
    behavior: PermissionBehavior | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert PermissionUpdate to dictionary format matching TypeScript control protocol."""
        result: dict[str, Any] = {"type": self.type}
        # Add destination for all variants
        result["destination"] = self.destination
        result["rules"] = [r.to_dict() for r in self.rules]
        result["behavior"] = self.behavior
        return result


@dataclass(kw_only=True)
class DirectoryPermissionUpdate(BasePermissionUpdate):
    """Permission update configuration."""

    type: Literal["addDirectories", "removeDirectories"]
    directories: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert PermissionUpdate to dictionary format matching TypeScript control protocol."""
        result: dict[str, Any] = {"type": self.type}
        result["destination"] = self.destination
        result["directories"] = self.directories
        return result


@dataclass(kw_only=True)
class ModePermissionUpdate(BasePermissionUpdate):
    """Permission update configuration."""

    type: Literal["setMode"]
    mode: PermissionMode

    def to_dict(self) -> dict[str, Any]:
        """Convert PermissionUpdate to dictionary format matching TypeScript control protocol."""
        result: dict[str, Any] = {"type": self.type}
        result["destination"] = self.destination
        result["mode"] = self.mode
        return result


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
    suggestions: list[PermissionUpdate] = field(
        default_factory=list
    )  # Permission suggestions from CLI
    blocked_path: str | None = None


# Match TypeScript's PermissionResult structure
@dataclass
class PermissionResultAllow:
    """Allow permission result."""

    behavior: Literal["allow"] = "allow"
    updated_input: ToolInput | dict[str, Any] | None = None
    updated_permissions: list[PermissionUpdate] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert PermissionResultAllow to dictionary format matching TypeScript control protocol."""
        result: dict[str, Any] = {"behavior": self.behavior}
        if self.updated_input is not None:
            result["updatedInput"] = self.updated_input
        if self.updated_permissions is not None:
            result["updatedPermissions"] = [p.to_dict() for p in self.updated_permissions]
        return result


@dataclass
class PermissionResultDeny:
    """Deny permission result."""

    behavior: Literal["deny"] = "deny"
    message: str = ""
    interrupt: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert PermissionResultDeny to dictionary format matching TypeScript control protocol."""
        return asdict(self)


PermissionResult = PermissionResultAllow | PermissionResultDeny

CanUseTool = Callable[[str, ToolInput, ToolPermissionContext], Awaitable[PermissionResult]]
