"""Advisory warnings about option combinations (upstream #1081)."""

from typing import TYPE_CHECKING
import warnings

from clawd_code_sdk._errors import CanUseToolShadowedWarning


if TYPE_CHECKING:
    from collections.abc import Sequence

    from clawd_code_sdk.models import ClaudeAgentOptions, PermissionMode


def whole_tool_allowed(entry: str) -> str | None:
    """Return the tool an ``allowed_tools`` entry allows outright, else None.

    Mirrors the CLI's rule parser: an entry allows a whole tool when it has no
    ``(...)`` specifier (``"Read"``), or when the specifier is empty or a lone
    wildcard (``"Read()"``, ``"Read(*)"``). A real specifier (``"Bash(ls:*)"``)
    only allows matching invocations. Malformed entries fall back to the whole
    string as a tool name in the CLI, so they match nothing and are ignored.
    """
    if not entry.strip():
        return None
    open_index = entry.find("(")
    if open_index == -1:
        return entry
    if open_index == 0 or not entry.endswith(")"):
        return None
    return entry[:open_index] if entry[open_index + 1 : -1] in ("", "*") else None


def can_use_tool_shadowed_message(
    permission_mode: PermissionMode | None,
    allowed_tools: Sequence[str],
) -> str | None:
    """Return the shadowing warning for these options, or None."""
    if permission_mode == "bypassPermissions":
        return (
            "on_permission will not be invoked: permission_mode 'bypassPermissions' "
            "auto-approves every tool call (except explicit deny rules) before the callback "
            "is consulted. To gate every tool call, use a PreToolUse hook instead."
        )
    # Deduplicate while keeping the order: "Read" and "Read()" are the same tool
    shadowed = list(dict.fromkeys(t for e in allowed_tools if (t := whole_tool_allowed(e))))
    if not shadowed:
        return None
    return (
        f"on_permission will not be invoked for: {', '.join(shadowed)}. An allowed_tools "
        "entry that allows a whole tool auto-approves it before the callback is consulted. "
        "To gate every tool call, use a PreToolUse hook, or narrow the entry so calls fall "
        "through to on_permission. Allow rules from settings files can also shadow the "
        "callback but are not visible here."
    )


def warn_if_can_use_tool_shadowed(options: ClaudeAgentOptions) -> None:
    """Warn if a permission callback is set but options auto-approve calls before it runs.

    Advisory only: shadowing can be intentional (a callback meant for the tools outside
    ``allowed_tools``). ``stacklevel=2`` attributes the warning to the SDK's connect(), so
    the default filter shows a given message once per process.
    """
    if not callable(options.on_permission):
        return
    message = can_use_tool_shadowed_message(options.permission_mode, options.allowed_tools or [])
    if message is not None:
        warnings.warn(message, CanUseToolShadowedWarning, stacklevel=2)
