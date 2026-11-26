"""SubprocessCLITransport.close() must not leak cancellation into the caller.

Regression test for 1.2.0: tearing down the stderr reader inside the shielded
close() scope cancelled the host task, surfacing as a stray CancelledError
after close() returned.
"""

import asyncio
import stat
import sys
import textwrap
from typing import TYPE_CHECKING

import anyio
import pytest

from clawd_code_sdk._internal.transport.subprocess_cli import (
    _ACTIVE_CHILDREN,
    SubprocessCLITransport,
)
from clawd_code_sdk.models import ClaudeAgentOptions


if TYPE_CHECKING:
    from pathlib import Path


# The fake CLIs are shebang scripts: Windows cannot execute them.
posix_only = pytest.mark.skipif(
    sys.platform == "win32", reason="the fake CLI is a shebang script; Windows cannot execute it"
)


def _fake_cli(tmp_path: Path) -> Path:
    """A stand-in CLI: writes to stderr, then waits for stdin EOF."""
    script = tmp_path / "fake-claude"
    script.write_text(
        textwrap.dedent(
            f"""\
            #!{sys.executable}
            import sys
            sys.stderr.write("starting up\\n")
            sys.stderr.flush()
            sys.stdin.read()
            """
        )
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


@posix_only
async def test_close_does_not_cancel_caller(tmp_path: Path) -> None:
    stderr_lines: list[str] = []
    options = ClaudeAgentOptions(cli_path=_fake_cli(tmp_path), stderr=stderr_lines.append)
    transport = SubprocessCLITransport(options=options)
    await transport.connect()
    process = transport._process
    assert process is not None
    assert process in _ACTIVE_CHILDREN
    await anyio.sleep(0.2)  # let the stderr reader pick up the line

    await transport.close()

    # A leaked cancellation would be delivered at the next checkpoint.
    await asyncio.sleep(0)
    await anyio.sleep(0.01)
    assert asyncio.current_task() is not None
    assert not asyncio.current_task().cancelling()  # type: ignore[union-attr]
    assert process.returncode is not None
    assert process not in _ACTIVE_CHILDREN
    assert stderr_lines == ["starting up"]


@posix_only
async def test_close_from_cancelled_scope_still_reaps_child(tmp_path: Path) -> None:
    options = ClaudeAgentOptions(cli_path=_fake_cli(tmp_path))
    transport = SubprocessCLITransport(options=options)
    await transport.connect()
    process = transport._process
    assert process is not None

    with anyio.CancelScope() as scope:
        scope.cancel()
        await transport.close()

    assert process.returncode is not None
    assert process not in _ACTIVE_CHILDREN


def _chatty_cli(tmp_path: Path) -> Path:
    """A stand-in CLI that flushes 1 MB to stdout after stdin EOF, then exits 0."""
    script = tmp_path / "chatty-claude"
    script.write_text(
        textwrap.dedent(
            f"""\
            #!{sys.executable}
            import sys
            sys.stdin.read()
            line = '{{"type": "stream_event"}}' + " " * 1000 + "\\n"
            for _ in range(1000):
                sys.stdout.write(line)
            sys.stdout.flush()
            """
        )
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


@posix_only
async def test_close_drains_stdout_while_the_cli_exits(tmp_path: Path) -> None:
    """Unread stdout filled the pipe: the CLI blocked and was SIGTERMed after 5 s."""
    transport = SubprocessCLITransport(options=ClaudeAgentOptions(cli_path=_chatty_cli(tmp_path)))
    await transport.connect()
    process = transport._process
    assert process is not None
    loop = asyncio.get_running_loop()
    start = loop.time()
    await transport.close()
    assert process.returncode == 0
    assert loop.time() - start < 4


def test_stderr_tail_is_bounded() -> None:
    transport = SubprocessCLITransport()
    for i in range(10_000):
        transport._stderr_lines.append(str(i))
    assert len(transport._stderr_lines) <= 1000
    assert transport._stderr_lines[-1] == "9999"
