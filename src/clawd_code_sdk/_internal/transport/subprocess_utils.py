"""Subprocess transport implementation using Claude Code CLI."""

from __future__ import annotations

from contextlib import suppress
import dataclasses
import functools
import logging
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING, Any, assert_never

import anyenv
import anyio
import anyio.abc

from clawd_code_sdk._errors import (
    CLIJSONDecodeError as SDKJSONDecodeError,
    CLINotFoundError,
)
from clawd_code_sdk.models import (
    ContinueLatest,
    FromPR,
    NewSession,
    ResumeSession,
    SdkPluginConfig,
    ThinkingConfigAdaptive,
    ThinkingConfigDisabled,
    ThinkingConfigEnabled,
)


if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from anyio.streams.text import TextReceiveStream

    from clawd_code_sdk.models import ClaudeAgentOptions


logger = logging.getLogger(__name__)

MINIMUM_CLAUDE_CODE_VERSION = "2.0.0"

# Platform-specific process creation flags
# On Windows, CREATE_NO_WINDOW prevents a visible console window from appearing
# when spawning the CLI subprocess, which improves UX for GUI applications
CREATION_FLAGS = (
    subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW")
    else 0
)


async def check_claude_version(cli_path: str | Path) -> None:
    """Check Claude Code version and warn if below minimum."""
    proc = None
    try:
        with anyio.fail_after(2):  # 2 second timeout
            proc = await anyio.open_process([cli_path, "-v"], creationflags=CREATION_FLAGS)
            if proc.stdout:
                stdout_bytes = await proc.stdout.receive()
                version_output = stdout_bytes.decode().strip()
                if match := re.match(r"([0-9]+\.[0-9]+\.[0-9]+)", version_output):
                    version = match.group(1)
                    version_parts = [int(x) for x in version.split(".")]
                    min_parts = [int(x) for x in MINIMUM_CLAUDE_CODE_VERSION.split(".")]
                    if version_parts < min_parts:
                        logger.warning(
                            "Claude Code version %s at %s is unsupported in the Agent SDK. "
                            "Minimum required version is %s. "
                            "Some features may not work correctly.",
                            version,
                            cli_path,
                            MINIMUM_CLAUDE_CODE_VERSION,
                        )
    except Exception:
        pass
    finally:
        if proc:
            with suppress(Exception):
                proc.terminate()
            with suppress(Exception):
                await proc.wait()


@functools.cache
def find_bundled_cli() -> str | None:
    """Find bundled CLI binary if it exists."""
    # Determine the CLI binary name based on platform
    cli_name = "claude.exe" if platform.system() == "Windows" else "claude"
    # Get the path to the bundled CLI
    # The _bundled directory is in the same package as this module
    bundled_path = Path(__file__).parent.parent.parent / "_bundled" / cli_name
    if bundled_path.exists() and bundled_path.is_file():
        logger.info("Using bundled Claude Code CLI: %s", bundled_path)
        return str(bundled_path)
    return None


@functools.cache
def find_cli() -> str:
    """Find Claude Code CLI binary."""
    # First, check for bundled CLI
    if bundled_cli := find_bundled_cli():
        return bundled_cli

    # Fall back to system-wide search
    if cli := shutil.which("claude"):
        return cli
    home_path = Path.home()
    locations = [
        home_path / ".npm-global/bin/claude",
        Path("/usr/local/bin/claude"),
        home_path / ".local/bin/claude",
        home_path / "node_modules/.bin/claude",
        home_path / ".yarn/bin/claude",
        home_path / ".claude/local/claude",
    ]
    for path in locations:
        if path.exists() and path.is_file():
            return str(path)

    raise CLINotFoundError(
        "Claude Code not found. Install with:\n"
        "  npm install -g @anthropic-ai/claude-code\n"
        "\nIf already installed locally, try:\n"
        '  export PATH="$HOME/node_modules/.bin:$PATH"\n'
        "\nOr provide the path via ClaudeAgentOptions:\n"
        "  ClaudeAgentOptions(cli_path='/path/to/claude')"
    )


def to_cli_args(options: ClaudeAgentOptions) -> list[str]:

    cmd = []
    match options.tools:
        case []:
            cmd.extend(["--tools", ""])
        case list() as tools:
            cmd.extend(["--tools", ",".join(tools)])
        case {"type": "preset"}:
            cmd.extend(["--tools", "default"])

    if options.allowed_tools is not None:
        cmd.extend(["--allowedTools", ",".join(options.allowed_tools)])

    if options.max_turns:
        cmd.extend(["--max-turns", str(options.max_turns)])

    if options.max_budget_usd is not None:
        cmd.extend(["--max-budget-usd", str(options.max_budget_usd)])

    if options.task_budget is not None:
        cmd.extend(["--task-budget", str(options.task_budget)])

    if options.disallowed_tools:
        cmd.extend(["--disallowedTools", ",".join(options.disallowed_tools)])

    if options.model:
        cmd.extend(["--model", options.model])

    if options.fallback_model:
        cmd.extend(["--fallback-model", options.fallback_model])

    if options.context_1m:
        cmd.extend(["--betas", "context-1m-2025-08-07"])

    if isinstance(options.on_permission, str):
        cmd.extend(["--permission-prompt-tool", options.on_permission])

    if options.permission_mode:
        cmd.extend(["--permission-mode", options.permission_mode])

    session = options.get_session()
    match session:
        case NewSession(session_id=str() as sid):
            cmd.extend(["--session-id", sid])
        case NewSession():
            pass
        case ResumeSession(session_id=sid, fork=fork, at_message=at_msg):
            cmd.extend(["--resume", sid])
            if fork:
                cmd.append("--fork-session")
            if at_msg is not None:
                cmd.extend(["--resume-session-at", at_msg])
        case ContinueLatest(fork=fork):
            cmd.append("--continue")
            if fork:
                cmd.append("--fork-session")
        case FromPR(pr=pr, fork=fork):
            cmd.extend(["--from-pr", str(pr)])
            if fork:
                cmd.append("--fork-session")
        case _ as unreachable:
            assert_never(unreachable)

    if not session.persist:
        cmd.append("--no-persist-session")

    # Handle settings and sandbox: merge sandbox into settings if both are provided
    if settings_value := options.build_settings_value():
        cmd.extend(["--settings", settings_value])

    if options.add_dirs:
        # Convert all paths to strings and add each directory
        for directory in options.add_dirs:
            cmd.extend(["--add-dir", str(directory)])

    match options.mcp_servers:
        case dict() as servers if servers:
            servers_for_cli = {
                name: {k: v for k, v in dataclasses.asdict(cfg).items() if k != "instance"}
                for name, cfg in servers.items()
            }
            dct = anyenv.dump_json({"mcpServers": servers_for_cli})
            cmd.extend(["--mcp-config", dct])
        case str() | Path() as path if str(path):
            cmd.extend(["--mcp-config", str(path)])

    if options.agent:
        cmd.extend(["--agent", options.agent])

    if options.allow_dangerously_skip_permissions:
        cmd.append("--dangerously-skip-permissions")

    if options.debug_file:
        cmd.extend(["--debug-file", options.debug_file])

    if options.strict_mcp_config:
        cmd.append("--strict-mcp-config")

    if options.include_hook_events:
        cmd.append("--include-hook-events")

    if options.replay_user_messages:
        cmd.append("--replay-user-messages")

    match options.worktree:
        case True:
            cmd.append("--worktree")
        case str():
            cmd.extend(["--worktree", options.worktree])

    if options.chrome:
        cmd.append("--chrome")

    if options.setting_sources:
        sources_value = ",".join(options.setting_sources or [])
        cmd.extend(["--setting-sources", sources_value])

    # Add plugin directories
    for plugin in options.plugins:
        match plugin:
            case SdkPluginConfig():
                cmd.extend(["--plugin-dir", plugin.path])
            case _:
                raise ValueError(f"Unsupported plugin type: {plugin.type}")

    # Add extra args for future CLI flags
    for flag, value in options.extra_args.items():
        flags = [f"--{flag}"] if value is None else [f"--{flag}", value]
        cmd.extend(flags)

    # Resolve thinking config → --max-thinking-tokens
    match options.thinking:
        case ThinkingConfigAdaptive():
            cmd.extend(["--max-thinking-tokens", "32000"])
        case ThinkingConfigEnabled(budget_tokens=budget):
            cmd.extend(["--max-thinking-tokens", str(budget)])
        case ThinkingConfigDisabled():
            cmd.extend(["--max-thinking-tokens", "0"])

    if options.effort is not None:
        cmd.extend(["--effort", options.effort])

    if options.disable_parallel_tool_use:
        cmd.append("--disable-parallel-tool-use")
    # Always use streaming mode with stdin (matching TypeScript SDK)
    # This allows agents and other large configs to be sent via initialize request
    return cmd


def get_env_vars(options: ClaudeAgentOptions) -> dict[str, str]:
    process_env = options.env

    # Enable file checkpointing if requested
    if options.enable_file_checkpointing:
        process_env["CLAUDE_CODE_ENABLE_SDK_FILE_CHECKPOINTING"] = "true"

    # Enable experimental agent teams feature
    if options.enable_agent_teams:
        process_env["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"] = "1"

    # Control ToolSearch behavior
    match options.enable_tool_search:
        case bool() as flag:
            process_env["ENABLE_TOOL_SEARCH"] = str(flag).lower()
        case "auto":
            process_env["ENABLE_TOOL_SEARCH"] = "auto"
        case int() as threshold:
            process_env["ENABLE_TOOL_SEARCH"] = f"auto:{threshold}"
        case None:
            pass

    # Set question preview format from toolConfig
    if (
        (opts := options.tool_config)
        and opts.ask_user_question
        and (fmt := opts.ask_user_question.preview_format)
    ):
        process_env["CLAUDE_CODE_QUESTION_PREVIEW_FORMAT"] = fmt
    # Enable fine-grained tool streaming. --include-partial-messages emits
    # stream_event messages, but tool input parameters are still buffered
    # by the API unless eager_input_streaming is also enabled at the
    # per-tool level via this env var.
    process_env.setdefault("CLAUDE_CODE_ENABLE_FINE_GRAINED_TOOL_STREAMING", "1")
    process_env.setdefault("CLAUDE_CODE_EMIT_SESSION_STATE_EVENTS", "1")
    # MCP_CONNECTION_NONBLOCKING=true
    if cwd := options.cwd:
        process_env["PWD"] = str(cwd)
    return process_env


async def parse_stream(
    stream: TextReceiveStream,
    max_buffer_size: int,
) -> AsyncIterator[dict[str, Any]]:
    json_buffer = ""
    async for line in stream:
        line_str = line.strip()
        if not line_str:
            continue

        # Accumulate partial JSON until we can parse it
        # Note: TextReceiveStream can truncate long lines, so we need to buffer
        # and speculatively parse until we get a complete JSON object
        for json_line in line_str.split("\n"):
            stripped = json_line.strip()
            if not stripped:
                continue
            # Skip non-JSON lines (e.g. [SandboxDebug]) when not
            # mid-parse — they corrupt the buffer otherwise (#347).
            if not json_buffer and not stripped.startswith("{"):
                logger.debug(
                    "Skipping non-JSON line from CLI stdout: %s",
                    json_line[:200],
                )
                continue

            # Keep accumulating partial JSON until we can parse it
            json_buffer += stripped

            if len(json_buffer) > max_buffer_size:
                buffer_length = len(json_buffer)
                json_buffer = ""
                raise SDKJSONDecodeError(
                    f"JSON message exceeded {max_buffer_size=}b",
                    ValueError(f"{buffer_length=} exceeds {max_buffer_size=}"),
                )

            try:
                data = anyenv.load_json(json_buffer, return_type=dict)
                json_buffer = ""
                yield data
            except anyenv.JsonLoadError:
                # We are speculatively decoding the buffer until we get
                # a full JSON object. If there is an actual issue, we
                # raise an error after exceeding the configured limit.
                continue
