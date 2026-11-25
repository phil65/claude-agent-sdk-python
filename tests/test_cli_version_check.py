"""The CLI version check reads the version from initialize / system init, no `claude -v`."""

from __future__ import annotations

import logging
import stat
import sys
import textwrap
from typing import TYPE_CHECKING, Any, cast

import anyio
import pytest

from clawd_code_sdk import ClaudeAgentOptions, ClaudeSDKClient
from clawd_code_sdk._internal.transport.subprocess_cli import SubprocessCLITransport
from clawd_code_sdk._internal.transport.subprocess_utils import check_claude_version


if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path


LOGGER = "clawd_code_sdk._internal.transport.subprocess_utils"


def _init_message(version: str) -> dict[str, Any]:
    return {
        "type": "system",
        "subtype": "init",
        "uuid": "u",
        "session_id": "s",
        "apiKeySource": None,
        "cwd": "/",
        "tools": [],
        "mcp_servers": [],
        "model": "claude-sonnet-4-5",
        "permissionMode": "default",
        "slash_commands": [],
        "output_style": "default",
        "claude_code_version": version,
        "skills": [],
        "plugins": [],
    }


class _FakeQuery:
    def __init__(self, response: dict[str, Any], messages: list[dict[str, Any]]) -> None:
        self.response = response
        self.messages = messages
        self.sdk_mcp_servers: dict[str, Any] = {}

    def build_hooks_config(self) -> None:
        return None

    async def capture_sdk_mcp_manifests(self) -> None:
        return None

    async def _send_control_request(self, request: Any, timeout: float = 0) -> dict[str, Any]:
        return self.response

    async def receive_messages(self) -> AsyncIterator[dict[str, Any]]:
        for message in self.messages:
            yield message


async def _run(response: dict[str, Any], messages: list[dict[str, Any]]) -> None:
    client = ClaudeSDKClient(ClaudeAgentOptions())
    client._query = cast(Any, _FakeQuery(response, messages))
    await client._initialize()
    async for _ in client.receive_messages():
        pass


@pytest.fixture(autouse=True)
def _version_check_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLAUDE_AGENT_SDK_SKIP_VERSION_CHECK", raising=False)


def _warnings(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.name == LOGGER]


@pytest.mark.parametrize(
    ("version", "warning"),
    [
        ("2.1.332", None),
        ("2.0.0", None),
        ("10.0.0", None),
        ("1.9.99", "unsupported"),
        ("1.0.0 (Claude Code)", "unsupported"),
        (None, "Could not determine"),
        ("garbage", "Could not determine"),
    ],
)
def test_check_claude_version(
    caplog: pytest.LogCaptureFixture, version: str | None, warning: str | None
) -> None:
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        check_claude_version(version)
    messages = _warnings(caplog)
    if warning is None:
        assert messages == []
    else:
        assert len(messages) == 1
        assert warning in messages[0]


def test_skip_env(caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_AGENT_SDK_SKIP_VERSION_CHECK", "1")
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        check_claude_version("1.0.0")
    assert _warnings(caplog) == []


async def test_version_from_initialize_response(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        # The init message is not checked again
        await _run({"claude_code_version": "1.5.0"}, [_init_message("1.6.0")])
    messages = _warnings(caplog)
    assert len(messages) == 1
    assert "1.5.0" in messages[0]


async def test_falls_back_to_init_message(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        await _run({}, [_init_message("1.6.0"), _init_message("1.7.0")])
    messages = _warnings(caplog)
    assert len(messages) == 1
    assert "1.6.0" in messages[0]


async def test_current_cli_does_not_warn(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        await _run({"claude_code_version": "2.1.332"}, [_init_message("2.1.332")])
    assert _warnings(caplog) == []


async def test_connect_spawns_the_cli_once(tmp_path: Path) -> None:
    calls = tmp_path / "calls"
    script = tmp_path / "fake-claude"
    script.write_text(
        textwrap.dedent(
            f"""\
            #!{sys.executable}
            import sys
            with open({str(calls)!r}, "a") as f:
                f.write(" ".join(sys.argv[1:]) + "\\n")
            sys.stdin.read()
            """
        )
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    transport = SubprocessCLITransport(ClaudeAgentOptions(cli_path=script))
    await transport.connect()
    await anyio.sleep(0.3)
    await transport.close()
    lines = calls.read_text().splitlines()
    assert len(lines) == 1
    assert "-v" not in lines[0].split()
