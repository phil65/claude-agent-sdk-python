"""Hook conversion helper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from clawd_code_sdk import HookMatcher
    from clawd_code_sdk.models import HookEvent


def convert_hooks_to_internal_format(
    hooks: dict[HookEvent, list[HookMatcher]],
) -> dict[str, list[dict[str, Any]]]:
    """Convert HookMatcher format to internal Query format."""
    internal_hooks: dict[str, list[dict[str, Any]]] = {}
    for event, matchers in hooks.items():
        internal_hooks[event] = []
        for matcher in matchers:
            # Convert HookMatcher to internal dict format
            internal_matcher: dict[str, Any] = {"matcher": matcher.matcher, "hooks": matcher.hooks}
            if matcher.timeout is not None:
                internal_matcher["timeout"] = matcher.timeout
            internal_hooks[event].append(internal_matcher)
    return internal_hooks
