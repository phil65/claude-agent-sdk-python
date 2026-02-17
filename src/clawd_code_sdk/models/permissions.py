"""Permission system types."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from clawd_code_sdk.input_types import ToolInput


if TYPE_CHECKING:
    from .base import PermissionMode


# Permission Update types (matching TypeScript SDK)
PermissionUpdateDestination = Literal["userSettings", "projectSettings", "localSettings", "session"]

PermissionBehavior = Literal["allow", "deny", "ask"]


@dataclass
class PermissionRuleValue:
    """Permission rule value."""

    tool_name: str
    rule_content: str | None = None


@dataclass
class PermissionUpdate:
    """Permission update configuration."""

    type: Literal[
        "addRules",
        "replaceRules",
        "removeRules",
        "setMode",
        "addDirectories",
        "removeDirectories",
    ]
    rules: list[PermissionRuleValue] | None = None
    behavior: PermissionBehavior | None = None
    mode: PermissionMode | None = None
    directories: list[str] | None = None
    destination: PermissionUpdateDestination | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert PermissionUpdate to dictionary format matching TypeScript control protocol."""
        result: dict[str, Any] = {"type": self.type}
        # Add destination for all variants
        if self.destination is not None:
            result["destination"] = self.destination

        # Handle different type variants
        if self.type in ["addRules", "replaceRules", "removeRules"]:
            # Rules-based variants require rules and behavior
            if self.rules is not None:
                result["rules"] = [
                    {"toolName": r.tool_name, "ruleContent": r.rule_content} for r in self.rules
                ]
            if self.behavior is not None:
                result["behavior"] = self.behavior

        elif self.type == "setMode":
            # Mode variant requires mode
            if self.mode is not None:
                result["mode"] = self.mode

        elif self.type in ["addDirectories", "removeDirectories"]:
            # Directory variants require directories
            if self.directories is not None:
                result["directories"] = self.directories

        return result


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
    updated_input: ToolInput | None = None
    updated_permissions: list[PermissionUpdate] | None = None


@dataclass
class PermissionResultDeny:
    """Deny permission result."""

    behavior: Literal["deny"] = "deny"
    message: str = ""
    interrupt: bool = False


PermissionResult = PermissionResultAllow | PermissionResultDeny

CanUseTool = Callable[[str, ToolInput, ToolPermissionContext], Awaitable[PermissionResult]]
