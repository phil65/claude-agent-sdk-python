"""Fine-grained tool streaming: when the SDK sets CLAUDE_CODE_ENABLE_FINE_GRAINED_TOOL_STREAMING."""

from __future__ import annotations

import pytest

from clawd_code_sdk import ClaudeAgentOptions
from clawd_code_sdk._internal.transport.subprocess_utils import (
    FINE_GRAINED_TOOL_STREAMING_ENV as KEY,
    fine_grained_tool_streaming_env,
    get_env_vars,
    uses_first_party_api,
)


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({}, True),
        ({"ANTHROPIC_BASE_URL": ""}, True),
        ({"ANTHROPIC_BASE_URL": "https://api.anthropic.com"}, True),
        ({"ANTHROPIC_BASE_URL": "https://api.anthropic.com/"}, True),
        ({"ANTHROPIC_BASE_URL": "https://proxy.example.com"}, False),
        ({"ANTHROPIC_BASE_URL": "https://api.anthropic.com:8443"}, False),
        ({"ANTHROPIC_BASE_URL": "https://api.anthropic.com.evil.test"}, False),
        ({"ANTHROPIC_BASE_URL": "not a url"}, False),
        ({"CLAUDE_CODE_USE_BEDROCK": "1"}, False),
        ({"CLAUDE_CODE_USE_VERTEX": "true"}, False),
        ({"CLAUDE_CODE_USE_FOUNDRY": "1"}, False),
        ({"CLAUDE_CODE_USE_BEDROCK": "0"}, True),
        ({"CLAUDE_CODE_USE_VERTEX": ""}, True),
    ],
)
def test_uses_first_party_api(env: dict[str, str], expected: bool) -> None:
    assert uses_first_party_api(env) is expected


def test_forced_values_ignore_the_environment() -> None:
    proxy = {"ANTHROPIC_BASE_URL": "https://proxy.example.com"}
    assert fine_grained_tool_streaming_env(True, environ=proxy) == "1"
    assert fine_grained_tool_streaming_env(False, environ={}) == "0"


def test_auto() -> None:
    assert fine_grained_tool_streaming_env("auto", environ={}) == "1"
    # Bedrock / Vertex / proxy: leave the CLI's default
    bedrock = {"CLAUDE_CODE_USE_BEDROCK": "1"}
    assert fine_grained_tool_streaming_env("auto", environ=bedrock) is None
    assert fine_grained_tool_streaming_env("auto", bedrock, environ={}) is None
    proxy = {"ANTHROPIC_BASE_URL": "https://proxy.example.com"}
    assert fine_grained_tool_streaming_env("auto", proxy, environ={}) is None
    # options.env can also point back at first-party
    first_party = {"ANTHROPIC_BASE_URL": "https://api.anthropic.com"}
    assert fine_grained_tool_streaming_env("auto", first_party, environ=proxy) == "1"
    # A value in the parent environment is passed through untouched
    assert fine_grained_tool_streaming_env("auto", environ={KEY: "0"}) is None


def test_get_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("ANTHROPIC_BASE_URL", "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", KEY):
        monkeypatch.delenv(name, raising=False)
    assert get_env_vars(ClaudeAgentOptions())[KEY] == "1"
    assert get_env_vars(ClaudeAgentOptions(fine_grained_tool_streaming=False))[KEY] == "0"
    vertex = ClaudeAgentOptions(env={"CLAUDE_CODE_USE_VERTEX": "1"})
    assert KEY not in get_env_vars(vertex)
    # An explicit env value beats the option
    explicit = ClaudeAgentOptions(fine_grained_tool_streaming=True, env={KEY: "0"})
    assert get_env_vars(explicit)[KEY] == "0"
