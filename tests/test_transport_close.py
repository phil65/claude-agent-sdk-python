"""SubprocessCLITransport.close() must not leak cancellation into the caller.

Regression test for 1.2.0: tearing down the stderr reader inside the shielded
close() scope cancelled the host task, surfacing as a stray CancelledError
after close() returned.
"""

from __future__ import annotations

import asyncio
import stat
import sys
import textwrap
from typing import TYPE_CHECKING

import anyio

from clawd_code_sdk._internal.transport.subprocess_cli import (
    _ACTIVE_CHILDREN,
    SubprocessCLITransport,
)
from clawd_code_sdk.models import ClaudeAgentOptions


if TYPE_CHECKING:
    from pathlib import Path


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
