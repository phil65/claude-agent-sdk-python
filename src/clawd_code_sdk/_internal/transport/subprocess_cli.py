"""Subprocess transport implementation using Claude Code CLI."""

from __future__ import annotations

import asyncio
import atexit
from collections import deque
from contextlib import suppress
import logging
import os
from pathlib import Path
import platform
import signal
from typing import TYPE_CHECKING, Any

import anyio
import anyio.abc
from anyio.streams.text import TextReceiveStream, TextSendStream
from anyio.to_thread import run_sync

from clawd_code_sdk._errors import CLIConnectionError, CLINotFoundError, ProcessError
from clawd_code_sdk._internal.transport import Transport
from clawd_code_sdk._internal.transport.subprocess_utils import (
    CREATION_FLAGS,
    LineFramer,
    find_cli,
    get_env_vars,
    parse_stream,
    reject_windows_batch_cli,
    to_cli_args,
)
from clawd_code_sdk.models import ClaudeAgentOptions


if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from anyio.abc import Process


logger = logging.getLogger(__name__)

_DEFAULT_MAX_BUFFER_SIZE = 10 * 1024 * 1024  # 1MB buffer limit
_STDERR_TAIL_LINES = 1000
"""stderr lines kept for the ProcessError message."""

_ACTIVE_CHILDREN: set[Process] = set()
"""CLI processes that have not been reaped yet (terminated on interpreter exit)."""


def _kill_active_children() -> None:
    """Terminate CLI children still alive when the parent exits (upstream #916).

    The CLI runs in its own session (``start_new_session=True``), so it does
    not receive the terminal's SIGHUP and would otherwise outlive a parent that
    crashed or exited without awaiting ``close()``.
    """
    for proc in list(_ACTIVE_CHILDREN):
        with suppress(Exception):
            proc.send_signal(signal.SIGTERM)  # On Windows anyio maps this to terminate()
    _ACTIVE_CHILDREN.clear()


atexit.register(_kill_active_children)


class SubprocessCLITransport(Transport):
    """Subprocess transport using Claude Code CLI."""

    def __init__(self, options: ClaudeAgentOptions | None = None) -> None:
        self._options = options or ClaudeAgentOptions()
        self._cli_path = str(opts) if (opts := self._options.cli_path) is not None else None
        self._process: Process | None = None
        self._stdout_stream: TextReceiveStream | None = None
        self._stdin_stream: TextSendStream | None = None
        self._stderr_stream: TextReceiveStream | None = None
        self._stderr_task: asyncio.Task[None] | None = None
        self._ready = False
        self._exit_error: Exception | None = None  # Track process exit errors
        self._max_buffer_size = self._options.max_buffer_size or _DEFAULT_MAX_BUFFER_SIZE
        # Only the tail is needed (for ProcessError); the CLI runs with --verbose.
        self._stderr_lines: deque[str] = deque(maxlen=_STDERR_TAIL_LINES)
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
        if self._process:
            return
        if self._cli_path is None:
            self._cli_path = await run_sync(find_cli)
        # Before anything spawns it
        reject_windows_batch_cli(self._cli_path)

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

        # Propagate active OTEL trace context to the CLI so its spans
        # parent under the caller's distributed trace. No-op if
        # opentelemetry-api is not installed or there's no active span.
        try:
            from opentelemetry import propagate

            carrier: dict[str, str] = {}
            propagate.inject(carrier)
            if "traceparent" in carrier:
                # Active span present: scrub stale inherited W3C context
                # (CI/k8s ambient env) before writing the fresh values, so
                # an inherited TRACESTATE isn't paired with a new
                # TRACEPARENT. Explicit ClaudeAgentOptions.env always wins.
                # Gate on the traceparent key (not carrier truthiness) so a
                # baggage-only / non-W3C carrier doesn't scrub a valid
                # inherited TRACEPARENT.
                for key in ("TRACEPARENT", "TRACESTATE"):
                    if key not in self._options.env:
                        process_env.pop(key, None)
                for k, v in carrier.items():
                    key = k.upper()
                    if key not in self._options.env:
                        process_env[key] = v
        except Exception:
            logger.debug("OTEL trace context injection failed", exc_info=True)

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
            _ACTIVE_CHILDREN.add(self._process)

            if self._process.stdout:
                self._stdout_stream = TextReceiveStream(self._process.stdout, errors="replace")

            # Setup stderr stream if piped
            if self._process.stderr:
                self._stderr_stream = TextReceiveStream(self._process.stderr, errors="replace")
                # Read stderr in a standalone task. A task group entered here and
                # exited in close()/read_messages() would span two call sites (and
                # possibly two tasks), and cancelling its scope would cancel the
                # caller itself.
                self._stderr_task = asyncio.get_running_loop().create_task(self._handle_stderr())

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

        def emit(line: str) -> None:
            line_str = line.rstrip()
            if not line_str:
                return
            # Always collect stderr lines for error reporting
            self._stderr_lines.append(line_str)
            # Isolate the callback per line so a raise in user code doesn't end
            # the loop and silently drop every later line.
            if self._options.stderr:
                try:
                    self._options.stderr(line_str)
                except Exception:
                    logger.debug("stderr callback raised; continuing", exc_info=True)

        # `options.stderr` receives lines, but the stream yields chunks, so frame
        # the lines here rather than handing over whatever a read returned.
        framer = LineFramer()
        try:
            async for chunk in self._stderr_stream:
                for line in framer.push(chunk):
                    emit(line)
                # A producer that never emits a newline can't grow the buffer
                # without bound; flush it as a partial line instead.
                if framer.pending_len > self._max_buffer_size:
                    emit(framer.flush())
        except anyio.ClosedResourceError:
            pass  # Stream closed, exit normally
        except Exception:
            logger.debug("stderr stream read failed", exc_info=True)
        finally:
            # In a `finally` so the last partial line still arrives when close()
            # cancels this task. `emit` is synchronous, so it is safe during
            # cancellation unwind.
            emit(framer.flush())

    async def _stop_stderr_reader(self, grace: float) -> None:
        """Stop the stderr reader task, giving it ``grace`` seconds to finish on its own."""
        task, self._stderr_task = self._stderr_task, None
        if task is None:
            return
        if not task.done() and grace > 0:
            await asyncio.wait({task}, timeout=grace)
        if not task.done():
            task.cancel()
            await asyncio.wait({task})

    def _discard_stdout(self) -> asyncio.Task[None] | None:
        """Start reading (and dropping) stdout until EOF; None if there is none."""
        stream = self._stdout_stream
        if stream is None:
            return None

        async def discard() -> None:
            with suppress(Exception):
                async for _ in stream:
                    pass

        return asyncio.get_running_loop().create_task(discard())

    async def close(self) -> None:
        """Close the transport and clean up resources.

        The whole body runs inside a shielded cancel scope (upstream #1082).
        Cleanup is routinely reached while the caller's task is being cancelled
        (e.g. ``async with ClaudeSDKClient()`` unwinding on cancel), and an
        unshielded close() would abort at the first await, before the
        terminate/kill escalation ran, orphaning the CLI child. Every await in
        the scope is bounded (~20s worst case), so cancellation is delayed but
        never blocked.

        A raw asyncio cancellation (``asyncio.timeout``, a bare ``task.cancel()``)
        is not deferred by an anyio shield. For that case the ``finally`` keeps a
        still-running child in ``_ACTIVE_CHILDREN`` for the atexit reaper
        instead of dropping it.
        """
        if not self._process:
            self._ready = False
            return

        process = self._process
        with anyio.CancelScope(shield=True):
            # Stop the stderr reader (it flushes its last partial line on cancel)
            await self._stop_stderr_reader(grace=0)

            # Close stdin stream (hold the write lock to prevent a race with
            # concurrent writes). Bounded: a writer blocked on a full stdin pipe
            # must not pin the shielded scope forever.
            lock_held = False
            with anyio.move_on_after(5):
                await self._write_lock.acquire()
                lock_held = True
            try:
                self._ready = False  # Set inside lock to prevent TOCTOU with write()
                if self._stdin_stream:
                    with suppress(Exception):
                        await self._stdin_stream.aclose()
                    self._stdin_stream = None
            finally:
                if lock_held:
                    self._write_lock.release()

            if self._stderr_stream:
                with suppress(Exception):
                    await self._stderr_stream.aclose()
                self._stderr_stream = None

            # Wait for process to exit gracefully after stdin EOF,
            # giving the CLI time to flush the session transcript.
            # Only resort to SIGTERM if it doesn't exit in time.
            # Nobody reads stdout anymore: discard it meanwhile, or a CLI still
            # streaming (partial messages) fills the pipe and blocks instead of exiting.
            drain = self._discard_stdout() if process.returncode is None else None
            try:
                if process.returncode is None:
                    try:
                        with anyio.fail_after(5):
                            await process.wait()
                    except TimeoutError:
                        # Graceful shutdown timed out - force terminate
                        with suppress(ProcessLookupError):
                            process.terminate()
                        try:
                            with anyio.fail_after(5):
                                await process.wait()
                        except TimeoutError:
                            # SIGTERM handler blocked - force kill (SIGKILL)
                            with suppress(ProcessLookupError):
                                process.kill()
                            with suppress(Exception), anyio.fail_after(5):
                                await process.wait()
            finally:
                if drain is not None:
                    drain.cancel()
                    await asyncio.wait({drain})
                # Only stop tracking a child we actually reaped. A still-running
                # process stays in the set so the atexit reaper gets a chance at it.
                if process.returncode is not None:
                    _ACTIVE_CHILDREN.discard(process)

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

        # The process has exited, so stderr reaches EOF shortly: let the reader
        # drain what is left before stopping it.
        await self._stop_stderr_reader(grace=5)

        # Use exit code for error detection
        if returncode:
            stderr = "\n".join(self._stderr_lines) if self._stderr_lines else None
            self._exit_error = ProcessError("Command failed", exit_code=returncode, stderr=stderr)
            raise self._exit_error
