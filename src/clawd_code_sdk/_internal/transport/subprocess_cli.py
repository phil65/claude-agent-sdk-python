"""Subprocess transport implementation using Claude Code CLI."""

from __future__ import annotations

from contextlib import suppress
import logging
import os
from pathlib import Path
import platform
from typing import TYPE_CHECKING, Any

import anyio
import anyio.abc
from anyio.streams.text import TextReceiveStream, TextSendStream

from clawd_code_sdk._errors import CLIConnectionError, CLINotFoundError, ProcessError
from clawd_code_sdk._internal.transport import Transport
from clawd_code_sdk._internal.transport.subprocess_utils import (
    CREATION_FLAGS,
    check_claude_version,
    find_cli,
    get_env_vars,
    parse_stream,
    to_cli_args,
)
from clawd_code_sdk.models import ClaudeAgentOptions


if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from anyio.abc import Process


logger = logging.getLogger(__name__)

_DEFAULT_MAX_BUFFER_SIZE = 10 * 1024 * 1024  # 1MB buffer limit


class SubprocessCLITransport(Transport):
    """Subprocess transport using Claude Code CLI."""

    def __init__(
        self,
        options: ClaudeAgentOptions | None = None,
    ):
        self._options = options or ClaudeAgentOptions()
        self._cli_path = str(opts) if (opts := self._options.cli_path) is not None else None
        self._process: Process | None = None
        self._stdout_stream: TextReceiveStream | None = None
        self._stdin_stream: TextSendStream | None = None
        self._stderr_stream: TextReceiveStream | None = None
        self._stderr_task_group: anyio.abc.TaskGroup | None = None
        self._ready = False
        self._exit_error: Exception | None = None  # Track process exit errors
        self._max_buffer_size = self._options.max_buffer_size or _DEFAULT_MAX_BUFFER_SIZE
        self._stderr_lines: list[str] = []
        self._write_lock: anyio.Lock = anyio.Lock()

    def _build_command(self) -> list[str]:
        """Build CLI command with arguments."""
        if self._cli_path is None:
            raise CLINotFoundError("CLI path not resolved. Call connect() first.")
        cmd = [
            self._cli_path,
            "--output-format",
            "stream-json",
            "--verbose",
            "--input-format",
            "stream-json",
            "--include-partial-messages",
            "--enable-auto-mode",
        ]
        cmd.extend(to_cli_args(self._options))
        return cmd

    async def connect(self) -> None:
        """Start subprocess."""
        from anyio.to_thread import run_sync

        if self._process:
            return
        if self._cli_path is None:
            self._cli_path = await run_sync(find_cli)
        if not os.environ.get("CLAUDE_AGENT_SDK_SKIP_VERSION_CHECK"):
            await check_claude_version(self._cli_path)

        cmd = self._build_command()
        # Remove CLAUDECODE from parent environment to prevent nesting detection
        # This allows SDK usage from within Claude Code (hooks, plugins, subagents)
        parent_env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        # Merge environment variables: system -> user -> SDK required
        process_env = {
            **parent_env,
            "CLAUDE_CODE_ENTRYPOINT": "sdk-py",
            # "CLAUDE_CODE_SDK_VERSION": "xyz",
            **get_env_vars(self._options),
        }
        # Always pipe stderr so we can capture it for error reporting.
        # The callback and debug mode flags control whether lines are
        # forwarded in real-time, but we always collect them.
        try:
            self._process = await anyio.open_process(
                cmd,
                cwd=self._options.cwd,
                env=process_env,
                user=self._options.user if platform.system() != "Windows" else None,
                start_new_session=True,
                creationflags=CREATION_FLAGS,
            )

            if self._process.stdout:
                self._stdout_stream = TextReceiveStream(self._process.stdout, errors="replace")

            # Setup stderr stream if piped
            if self._process.stderr:
                self._stderr_stream = TextReceiveStream(self._process.stderr, errors="replace")
                # Start async task to read stderr
                self._stderr_task_group = anyio.create_task_group()
                await self._stderr_task_group.__aenter__()
                self._stderr_task_group.start_soon(self._handle_stderr)

            # Setup stdin for streaming (always used now)
            if self._process.stdin:
                self._stdin_stream = TextSendStream(self._process.stdin)

            self._ready = True

        except FileNotFoundError as e:
            # Check if the error comes from the working directory or the CLI
            if (cwd := self._options.cwd) and not Path(cwd).exists():
                error = CLIConnectionError(f"Working directory does not exist: {cwd}")
                self._exit_error = error
                raise error from e
            error = CLINotFoundError(f"Claude Code not found at: {self._cli_path}")
            self._exit_error = error
            raise error from e
        except Exception as e:
            error = CLIConnectionError(f"Failed to start Claude Code: {e}")
            self._exit_error = error
            raise error from e

    async def _handle_stderr(self) -> None:
        """Handle stderr stream - read and invoke callbacks."""
        if not self._stderr_stream:
            return

        try:
            async for line in self._stderr_stream:
                line_str = line.rstrip()
                if not line_str:
                    continue

                # Always collect stderr lines for error reporting
                self._stderr_lines.append(line_str)
                # Call the stderr callback if provided
                if self._options.stderr:
                    self._options.stderr(line_str)
        except anyio.ClosedResourceError:
            pass  # Stream closed, exit normally
        except Exception:
            pass  # Ignore other errors during stderr reading

    async def close(self) -> None:
        """Close the transport and clean up resources."""
        if not self._process:
            self._ready = False
            return

        # Close stderr task group if active
        if self._stderr_task_group:
            with suppress(Exception):
                self._stderr_task_group.cancel_scope.cancel()
                await self._stderr_task_group.__aexit__(None, None, None)
            self._stderr_task_group = None

        # Close stdin stream (acquire lock to prevent race with concurrent writes)
        async with self._write_lock:
            self._ready = False  # Set inside lock to prevent TOCTOU with write()
            if self._stdin_stream:
                with suppress(Exception):
                    await self._stdin_stream.aclose()
                self._stdin_stream = None

        if self._stderr_stream:
            with suppress(Exception):
                await self._stderr_stream.aclose()
            self._stderr_stream = None

        # Wait for process to exit gracefully after stdin EOF,
        # giving the CLI time to flush the session transcript.
        # Only resort to SIGTERM if it doesn't exit in time.
        if self._process.returncode is None:
            try:
                with anyio.fail_after(5):
                    await self._process.wait()
            except TimeoutError:
                # Graceful shutdown timed out — force terminate
                with suppress(ProcessLookupError):
                    self._process.terminate()
                try:
                    with anyio.fail_after(5):
                        await self._process.wait()
                except TimeoutError:
                    # SIGTERM handler blocked — force kill (SIGKILL)
                    with suppress(ProcessLookupError):
                        self._process.kill()
                    with suppress(Exception):
                        await self._process.wait()

        self._process = None
        self._stdout_stream = None
        self._stdin_stream = None
        self._stderr_stream = None
        self._exit_error = None

    async def write(self, data: str) -> None:
        """Write raw data to the transport."""
        async with self._write_lock:
            # All checks inside lock to prevent TOCTOU races with close()/end_input()
            if not self._ready or not self._stdin_stream:
                raise CLIConnectionError("ProcessTransport is not ready for writing")

            if self._process and self._process.returncode is not None:
                raise CLIConnectionError(
                    f"Cannot write to terminated process: {self._process.returncode=}"
                )

            if self._exit_error:
                raise CLIConnectionError(
                    f"Cannot write to process: {self._exit_error=}"
                ) from self._exit_error

            try:
                await self._stdin_stream.send(data)
            except Exception as e:
                self._ready = False
                self._exit_error = CLIConnectionError(f"Failed to write to process stdin: {e}")
                raise self._exit_error from e

    async def end_input(self) -> None:
        """End the input stream (close stdin)."""
        async with self._write_lock:
            if self._stdin_stream:
                with suppress(Exception):
                    await self._stdin_stream.aclose()
                self._stdin_stream = None

    async def read_messages(self) -> AsyncIterator[dict[str, Any]]:
        """Read and parse messages from the transport."""
        if not self._process or not self._stdout_stream:
            raise CLIConnectionError("Not connected")

        # Process stdout messages
        try:
            async for message in parse_stream(self._stdout_stream, self._max_buffer_size):
                yield message
        except anyio.ClosedResourceError:
            pass
        except GeneratorExit:  # Client disconnected
            pass

        try:  # Check process completion and handle errors
            returncode = await self._process.wait()
        except Exception:
            returncode = -1

        # Wait for stderr reader to finish draining
        if self._stderr_task_group:
            with suppress(Exception):
                with anyio.move_on_after(5):
                    self._stderr_task_group.cancel_scope.cancel()
                    await self._stderr_task_group.__aexit__(None, None, None)
            self._stderr_task_group = None

        # Use exit code for error detection
        if returncode:
            stderr = "\n".join(self._stderr_lines) if self._stderr_lines else None
            self._exit_error = ProcessError("Command failed", exit_code=returncode, stderr=stderr)
            raise self._exit_error
