"""How setting_sources reaches the CLI (upstream #822)."""

from clawd_code_sdk import ClaudeAgentOptions
from clawd_code_sdk._internal.transport.subprocess_utils import to_cli_args


def test_setting_sources_omitted_by_default() -> None:
    args = to_cli_args(ClaudeAgentOptions())
    assert not any(a.startswith("--setting-sources") for a in args)


def test_setting_sources_empty_list_disables_all() -> None:
    args = to_cli_args(ClaudeAgentOptions(setting_sources=[]))
    assert "--setting-sources=" in args


def test_setting_sources_single_token() -> None:
    args = to_cli_args(ClaudeAgentOptions(setting_sources=["user", "project"]))
    assert "--setting-sources=user,project" in args
