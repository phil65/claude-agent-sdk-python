"""The permission flags passed to the CLI."""

from __future__ import annotations

from clawd_code_sdk import ClaudeAgentOptions
from clawd_code_sdk._internal.transport.subprocess_utils import to_cli_args


def test_allowing_bypass_does_not_start_in_bypass() -> None:
    """``--allow-…`` permits switching to bypassPermissions; the other flag starts in it."""
    args = to_cli_args(
        ClaudeAgentOptions(permission_mode="default", allow_dangerously_skip_permissions=True)
    )
    assert "--allow-dangerously-skip-permissions" in args
    assert "--dangerously-skip-permissions" not in args
    assert args[args.index("--permission-mode") + 1] == "default"
