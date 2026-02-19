"""Tests for Claude SDK transport layer."""

from __future__ import annotations

from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
from subprocess import PIPE
import sys
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import anyio
from anyio.streams.text import TextSendStream
import pytest

from clawd_code_sdk._errors import CLIConnectionError, CLINotFoundError
from clawd_code_sdk._internal.transport.subprocess_cli import SubprocessCLITransport
from clawd_code_sdk.models import AgentDefinition, ClaudeAgentOptions


if TYPE_CHECKING:
    from collections.abc import AsyncIterable

    from clawd_code_sdk import SandboxSettings
    from clawd_code_sdk.models.messages import UserPromptMessage

DEFAULT_CLI_PATH = "/usr/bin/claude"


def make_options(**kwargs: Any) -> ClaudeAgentOptions:
    """Construct options using the standard CLI path unless overridden."""
    cli_path = kwargs.pop("cli_path", DEFAULT_CLI_PATH)
    return ClaudeAgentOptions(cli_path=cli_path, **kwargs)


class TestSubprocessCLITransport:
    """Test subprocess transport implementation."""

    def test_find_cli_not_found(self):
        """Test CLI not found error."""
        with (
            patch("shutil.which", return_value=None),
            patch("pathlib.Path.exists", return_value=False),
            pytest.raises(CLINotFoundError) as exc_info,
        ):
            SubprocessCLITransport(prompt="test", options=ClaudeAgentOptions())

        assert "Claude Code not found" in str(exc_info.value)

    def test_build_command_basic(self):
        """Test building basic CLI command."""
        transport = SubprocessCLITransport(prompt="Hello", options=make_options())
        cmd = transport._build_command()
        assert cmd[0] == "/usr/bin/claude"
        assert "--output-format" in cmd
        assert "stream-json" in cmd
        # Always use streaming mode (matching TypeScript SDK)
        assert "--input-format" in cmd
        assert "--print" not in cmd  # Never use --print anymore
        # system_prompt is now sent via initialize request, not CLI args
        assert "--system-prompt" not in cmd

    def test_cli_path_accepts_pathlib_path(self):
        """Test that cli_path accepts pathlib.Path objects."""
        path = Path("/usr/bin/claude")
        opts = ClaudeAgentOptions(cli_path=path)
        transport = SubprocessCLITransport(prompt="Hello", options=opts)
        # Path object is converted to string, compare with str(path)
        assert transport._cli_path == str(path)

    def test_build_command_system_prompt_not_in_cli_args(self):
        """Test that system prompt is not passed as CLI arg (sent via initialize request)."""
        for system_prompt in [
            "Be helpful",
            {"type": "preset", "preset": "claude_code"},
            {"type": "preset", "preset": "claude_code", "append": "Be concise."},
        ]:
            opts = make_options(system_prompt=system_prompt)
            transport = SubprocessCLITransport(prompt="test", options=opts)
            cmd = transport._build_command()
            assert "--system-prompt" not in cmd
            assert "--append-system-prompt" not in cmd

    def test_build_command_with_options(self):
        """Test building CLI command with options."""
        transport = SubprocessCLITransport(
            prompt="test",
            options=make_options(
                allowed_tools=["Read", "Write"],
                disallowed_tools=["Bash"],
                model="claude-sonnet-4-5",
                permission_mode="acceptEdits",
                max_turns=5,
            ),
        )

        cmd = transport._build_command()
        assert "--allowedTools" in cmd
        assert "Read,Write" in cmd
        assert "--disallowedTools" in cmd
        assert "Bash" in cmd
        assert "--model" in cmd
        assert "claude-sonnet-4-5" in cmd
        assert "--permission-mode" in cmd
        assert "acceptEdits" in cmd
        assert "--max-turns" in cmd
        assert "5" in cmd

    def test_build_command_with_fallback_model(self):
        """Test building CLI command with fallback_model option."""
        opts = make_options(model="opus", fallback_model="sonnet")
        transport = SubprocessCLITransport(prompt="test", options=opts)
        cmd = transport._build_command()
        assert "--model" in cmd
        assert "opus" in cmd
        assert "--fallback-model" in cmd
        assert "sonnet" in cmd

    def test_build_command_with_thinking_enabled(self):
        """Test building CLI command with thinking config."""
        opts = make_options(thinking={"type": "enabled", "budget_tokens": 5000})
        transport = SubprocessCLITransport(prompt="test", options=opts)
        cmd = transport._build_command()
        assert "--max-thinking-tokens" in cmd
        assert "5000" in cmd

    def test_build_command_with_thinking_adaptive(self):
        """Test building CLI command with adaptive thinking config."""
        opts = make_options(thinking={"type": "adaptive"})
        transport = SubprocessCLITransport(prompt="test", options=opts)
        cmd = transport._build_command()
        assert "--max-thinking-tokens" in cmd
        assert "32000" in cmd

    def test_build_command_with_thinking_disabled(self):
        """Test building CLI command with disabled thinking config."""
        opts = make_options(thinking={"type": "disabled"})
        transport = SubprocessCLITransport(prompt="test", options=opts)
        cmd = transport._build_command()
        assert "--max-thinking-tokens" in cmd
        assert "0" in cmd

    def test_build_command_with_effort(self):
        """Test building CLI command with effort option."""
        opts = make_options(effort="high")
        transport = SubprocessCLITransport(prompt="test", options=opts)
        cmd = transport._build_command()
        assert "--effort" in cmd
        assert "high" in cmd

    def test_build_command_with_context_1m(self):
        """Test building CLI command with context_1m option."""
        opts = make_options(context_1m=True)
        transport = SubprocessCLITransport(prompt="test", options=opts)
        cmd = transport._build_command()
        assert "--betas" in cmd
        betas_index = cmd.index("--betas")
        assert cmd[betas_index + 1] == "context-1m-2025-08-07"

    def test_build_command_without_context_1m(self):
        """Test that --betas is not added when context_1m is False."""
        transport = SubprocessCLITransport(prompt="test", options=make_options())
        cmd = transport._build_command()
        assert "--betas" not in cmd

    def test_build_command_with_add_dirs(self):
        """Test building CLI command with add_dirs option."""
        dir1 = "/path/to/dir1"
        dir2 = Path("/path/to/dir2")
        opts = make_options(add_dirs=[dir1, dir2])
        transport = SubprocessCLITransport(prompt="test", options=opts)
        cmd = transport._build_command()
        # Check that both directories are in the command
        assert "--add-dir" in cmd
        add_dir_indices = [i for i, x in enumerate(cmd) if x == "--add-dir"]
        assert len(add_dir_indices) == 2
        # The directories should appear after --add-dir flags
        dirs_in_cmd = [cmd[i + 1] for i in add_dir_indices]
        assert dir1 in dirs_in_cmd
        assert str(dir2) in dirs_in_cmd

    def test_session_continuation(self):
        """Test session continuation options."""
        opts = make_options(continue_conversation=True, resume="session-123")
        transport = SubprocessCLITransport(prompt="Continue from before", options=opts)
        cmd = transport._build_command()
        assert "--continue" in cmd
        assert "--resume" in cmd
        assert "session-123" in cmd

    def test_build_command_with_session_id(self):
        """Test building CLI command with session_id option."""
        opts = make_options(session_id="my-session-uuid")
        transport = SubprocessCLITransport(prompt="test", options=opts)
        cmd = transport._build_command()
        assert "--session-id" in cmd
        assert "my-session-uuid" in cmd

    def test_connect_close(self):
        """Test connect and close lifecycle."""

        async def _test():
            with patch("anyio.open_process") as mock_exec:
                # Mock version check process
                mock_version_process = MagicMock()
                mock_version_process.stdout = MagicMock()
                mock_version_process.stdout.receive = AsyncMock(return_value=b"2.0.0 (Claude Code)")
                mock_version_process.terminate = MagicMock()
                mock_version_process.wait = AsyncMock()
                # Mock main process
                mock_process = MagicMock()
                mock_process.returncode = None
                mock_process.terminate = MagicMock()
                mock_process.wait = AsyncMock()
                mock_process.stdout = MagicMock()
                mock_process.stderr = MagicMock()
                # Mock stdin with aclose method
                mock_stdin = MagicMock()
                mock_stdin.aclose = AsyncMock()
                mock_process.stdin = mock_stdin
                # Return version process first, then main process
                mock_exec.side_effect = [mock_version_process, mock_process]
                transport = SubprocessCLITransport(prompt="test", options=make_options())
                await transport.connect()
                assert transport._process is not None
                await transport.close()
                mock_process.terminate.assert_called_once()

        anyio.run(_test)

    def test_read_messages(self):
        """Test reading messages from CLI output."""
        # This test is simplified to just test the transport creation
        # The full async stream handling is tested in integration tests
        transport = SubprocessCLITransport(prompt="test", options=make_options())
        # The transport now just provides raw message reading via read_messages()
        # So we just verify the transport can be created and basic structure is correct
        assert transport._prompt == "test"
        assert transport._cli_path == "/usr/bin/claude"

    def test_connect_with_nonexistent_cwd(self):
        """Test that connect raises CLIConnectionError when cwd doesn't exist."""

        async def _test():
            opts = make_options(cwd="/this/directory/does/not/exist")
            transport = SubprocessCLITransport(prompt="test", options=opts)
            with pytest.raises(CLIConnectionError) as exc_info:
                await transport.connect()

            assert "/this/directory/does/not/exist" in str(exc_info.value)

        anyio.run(_test)

    def test_build_command_with_settings_file(self):
        """Test building CLI command with settings as file path."""
        opts = make_options(settings="/path/to/settings.json")
        transport = SubprocessCLITransport(prompt="test", options=opts)
        cmd = transport._build_command()
        assert "--settings" in cmd
        assert "/path/to/settings.json" in cmd

    def test_build_command_with_settings_json(self):
        """Test building CLI command with settings as JSON object."""
        settings_json = '{"permissions": {"allow": ["Bash(ls:*)"]}}'
        opts = make_options(settings=settings_json)
        transport = SubprocessCLITransport(prompt="test", options=opts)
        cmd = transport._build_command()
        assert "--settings" in cmd
        assert settings_json in cmd

    def test_build_command_with_extra_args(self):
        """Test building CLI command with extra_args for future flags."""
        args = {"new-flag": "value", "boolean-flag": None, "another-option": "test-value"}
        opts = make_options(extra_args=args)
        transport = SubprocessCLITransport(prompt="test", options=opts)
        cmd = transport._build_command()
        cmd_str = " ".join(cmd)
        # Check flags with values
        assert "--new-flag value" in cmd_str
        assert "--another-option test-value" in cmd_str
        # Check boolean flag (no value)
        assert "--boolean-flag" in cmd
        # Make sure boolean flag doesn't have a value after it
        boolean_idx = cmd.index("--boolean-flag")
        # Either it's the last element or the next element is another flag
        assert boolean_idx == len(cmd) - 1 or cmd[boolean_idx + 1].startswith("--")

    def test_build_command_with_mcp_servers(self):
        """Test building CLI command with mcp_servers option."""
        mcp_servers = {
            "test-server": {
                "type": "stdio",
                "command": "/path/to/server",
                "args": ["--option", "value"],
            }
        }
        opts = make_options(mcp_servers=mcp_servers)
        transport = SubprocessCLITransport(prompt="test", options=opts)
        cmd = transport._build_command()
        # Find the --mcp-config flag and its value
        assert "--mcp-config" in cmd
        mcp_idx = cmd.index("--mcp-config")
        mcp_config_value = cmd[mcp_idx + 1]

        # Parse the JSON and verify structure
        config = json.loads(mcp_config_value)
        assert "mcpServers" in config
        assert config["mcpServers"] == mcp_servers

    def test_build_command_with_mcp_servers_as_file_path(self):
        """Test building CLI command with mcp_servers as file path."""
        # Test with string path
        string_path = "/path/to/mcp-config.json"
        opts = make_options(mcp_servers=string_path)
        transport = SubprocessCLITransport(prompt="test", options=opts)
        cmd = transport._build_command()
        assert "--mcp-config" in cmd
        mcp_idx = cmd.index("--mcp-config")
        assert cmd[mcp_idx + 1] == string_path
        # Test with Path object
        path_obj = Path("/path/to/mcp-config.json")
        opts = make_options(mcp_servers=path_obj)
        transport = SubprocessCLITransport(prompt="test", options=opts)
        cmd = transport._build_command()
        assert "--mcp-config" in cmd
        mcp_idx = cmd.index("--mcp-config")
        # Path object gets converted to string, compare with str(path_obj)
        assert cmd[mcp_idx + 1] == str(path_obj)

    def test_build_command_with_mcp_servers_as_json_string(self):
        """Test building CLI command with mcp_servers as JSON string."""
        json_config = '{"mcpServers": {"server": {"type": "stdio", "command": "test"}}}'
        opts = make_options(mcp_servers=json_config)
        transport = SubprocessCLITransport(prompt="test", options=opts)
        cmd = transport._build_command()
        assert "--mcp-config" in cmd
        mcp_idx = cmd.index("--mcp-config")
        assert cmd[mcp_idx + 1] == json_config

    def test_env_vars_passed_to_subprocess(self):
        """Test that custom environment variables are passed to the subprocess."""

        async def _test():
            test_value = f"test-{uuid.uuid4().hex[:8]}"
            custom_env = {"MY_TEST_VAR": test_value}
            options = make_options(env=custom_env)
            # Mock the subprocess to capture the env argument
            with patch("anyio.open_process", new_callable=AsyncMock) as mock_open_process:
                # Mock version check process
                mock_version_process = MagicMock()
                mock_version_process.stdout = MagicMock()
                mock_version_process.stdout.receive = AsyncMock(return_value=b"2.0.0 (Claude Code)")
                mock_version_process.terminate = MagicMock()
                mock_version_process.wait = AsyncMock()
                # Mock main process
                mock_process = MagicMock()
                mock_process.stdout = MagicMock()
                mock_stdin = MagicMock()
                mock_stdin.aclose = AsyncMock()  # Add async aclose method
                mock_process.stdin = mock_stdin
                mock_process.returncode = None
                # Return version process first, then main process
                mock_open_process.side_effect = [mock_version_process, mock_process]
                transport = SubprocessCLITransport(prompt="test", options=options)
                await transport.connect()
                # Verify open_process was called twice (version check + main process)
                assert mock_open_process.call_count == 2
                # Check the second call (main process) for env vars
                second_call_kwargs = mock_open_process.call_args_list[1].kwargs
                assert "env" in second_call_kwargs
                env_passed = second_call_kwargs["env"]
                # Check that custom env var was passed
                assert env_passed["MY_TEST_VAR"] == test_value
                # Verify SDK identifier is present
                assert "CLAUDE_CODE_ENTRYPOINT" in env_passed
                assert env_passed["CLAUDE_CODE_ENTRYPOINT"] == "sdk-py"
                # Verify system env vars are also included with correct values
                if "PATH" in os.environ:
                    assert "PATH" in env_passed
                    assert env_passed["PATH"] == os.environ["PATH"]

        anyio.run(_test)

    def test_connect_as_different_user(self):
        """Test connect as different user."""

        async def _test():
            custom_user = "claude"
            options = make_options(user=custom_user)

            # Mock the subprocess to capture the env argument
            with patch("anyio.open_process", new_callable=AsyncMock) as mock_open_process:
                # Mock version check process
                mock_version_process = MagicMock()
                mock_version_process.stdout = MagicMock()
                mock_version_process.stdout.receive = AsyncMock(return_value=b"2.0.0 (Claude Code)")
                mock_version_process.terminate = MagicMock()
                mock_version_process.wait = AsyncMock()

                # Mock main process
                mock_process = MagicMock()
                mock_process.stdout = MagicMock()
                mock_stdin = MagicMock()
                mock_stdin.aclose = AsyncMock()  # Add async aclose method
                mock_process.stdin = mock_stdin
                mock_process.returncode = None
                # Return version process first, then main process
                mock_open_process.side_effect = [mock_version_process, mock_process]
                transport = SubprocessCLITransport(prompt="test", options=options)
                await transport.connect()
                # Verify open_process was called twice (version check + main process)
                assert mock_open_process.call_count == 2
                # Check the second call (main process) for user
                second_call_kwargs = mock_open_process.call_args_list[1].kwargs
                assert "user" in second_call_kwargs
                user_passed = second_call_kwargs["user"]
                # Check that user was passed
                assert user_passed == "claude"

        anyio.run(_test)

    def test_build_command_with_sandbox_only(self):
        """Test building CLI command with sandbox settings (no existing settings)."""
        import json

        sandbox: SandboxSettings = {
            "enabled": True,
            "autoAllowBashIfSandboxed": True,
            "network": {
                "allowLocalBinding": True,
                "allowUnixSockets": ["/var/run/docker.sock"],
            },
        }
        opts = make_options(sandbox=sandbox)
        transport = SubprocessCLITransport(prompt="test", options=opts)
        cmd = transport._build_command()
        # Should have --settings with sandbox merged in
        assert "--settings" in cmd
        settings_idx = cmd.index("--settings")
        settings_value = cmd[settings_idx + 1]
        # Parse and verify
        parsed = json.loads(settings_value)
        assert "sandbox" in parsed
        assert parsed["sandbox"]["enabled"] is True
        assert parsed["sandbox"]["autoAllowBashIfSandboxed"] is True
        assert parsed["sandbox"]["network"]["allowLocalBinding"] is True
        assert parsed["sandbox"]["network"]["allowUnixSockets"] == ["/var/run/docker.sock"]

    def test_build_command_with_sandbox_and_settings_json(self):
        """Test building CLI command with sandbox merged into existing settings JSON."""
        # Existing settings as JSON string
        existing_settings = '{"permissions": {"allow": ["Bash(ls:*)"]}, "verbose": true}'
        sandbox: SandboxSettings = {"enabled": True, "excludedCommands": ["git", "docker"]}
        opts = make_options(settings=existing_settings, sandbox=sandbox)
        transport = SubprocessCLITransport(prompt="test", options=opts)
        cmd = transport._build_command()
        # Should have merged settings
        assert "--settings" in cmd
        settings_idx = cmd.index("--settings")
        settings_value = cmd[settings_idx + 1]
        parsed = json.loads(settings_value)
        # Original settings should be preserved
        assert parsed["permissions"] == {"allow": ["Bash(ls:*)"]}
        assert parsed["verbose"] is True
        # Sandbox should be merged in
        assert "sandbox" in parsed
        assert parsed["sandbox"]["enabled"] is True
        assert parsed["sandbox"]["excludedCommands"] == ["git", "docker"]

    def test_build_command_with_settings_file_and_no_sandbox(self):
        """Test that settings file path is passed through when no sandbox."""
        opts = make_options(settings="/path/to/settings.json")
        transport = SubprocessCLITransport(prompt="test", options=opts)
        cmd = transport._build_command()
        # Should pass path directly, not parse it
        assert "--settings" in cmd
        settings_idx = cmd.index("--settings")
        assert cmd[settings_idx + 1] == "/path/to/settings.json"

    def test_build_command_sandbox_minimal(self):
        """Test sandbox with minimal configuration."""
        sandbox: SandboxSettings = {"enabled": True}
        opts = make_options(sandbox=sandbox)
        transport = SubprocessCLITransport(prompt="test", options=opts)
        cmd = transport._build_command()
        assert "--settings" in cmd
        settings_idx = cmd.index("--settings")
        settings_value = cmd[settings_idx + 1]
        parsed = json.loads(settings_value)
        assert parsed == {"sandbox": {"enabled": True}}

    def test_sandbox_network_config(self):
        """Test sandbox with full network configuration."""
        sandbox: SandboxSettings = {
            "enabled": True,
            "network": {
                "allowUnixSockets": ["/tmp/ssh-agent.sock"],
                "allowAllUnixSockets": False,
                "allowLocalBinding": True,
                "httpProxyPort": 8080,
                "socksProxyPort": 8081,
            },
        }
        opts = make_options(sandbox=sandbox)
        transport = SubprocessCLITransport(prompt="test", options=opts)
        cmd = transport._build_command()
        settings_idx = cmd.index("--settings")
        settings_value = cmd[settings_idx + 1]
        parsed = json.loads(settings_value)
        network = parsed["sandbox"]["network"]
        assert network["allowUnixSockets"] == ["/tmp/ssh-agent.sock"]
        assert network["allowAllUnixSockets"] is False
        assert network["allowLocalBinding"] is True
        assert network["httpProxyPort"] == 8080
        assert network["socksProxyPort"] == 8081

    def test_build_command_with_tools_array(self):
        """Test building CLI command with tools as array of tool names."""
        opts = make_options(tools=["Read", "Edit", "Bash"])
        transport = SubprocessCLITransport(prompt="test", options=opts)
        cmd = transport._build_command()
        assert "--tools" in cmd
        tools_idx = cmd.index("--tools")
        assert cmd[tools_idx + 1] == "Read,Edit,Bash"

    def test_build_command_with_tools_empty_array(self):
        """Test building CLI command with tools as empty array (disables all tools)."""
        opts = make_options(tools=[])
        transport = SubprocessCLITransport(prompt="test", options=opts)
        cmd = transport._build_command()
        assert "--tools" in cmd
        tools_idx = cmd.index("--tools")
        assert cmd[tools_idx + 1] == ""

    def test_build_command_with_tools_preset(self):
        """Test building CLI command with tools preset."""
        opts = make_options(tools={"type": "preset", "preset": "claude_code"})
        transport = SubprocessCLITransport(prompt="test", options=opts)
        cmd = transport._build_command()
        assert "--tools" in cmd
        tools_idx = cmd.index("--tools")
        assert cmd[tools_idx + 1] == "default"

    def test_build_command_without_tools(self):
        """Test building CLI command without tools option (default None)."""
        transport = SubprocessCLITransport(prompt="test", options=make_options())
        cmd = transport._build_command()
        assert "--tools" not in cmd

    def test_concurrent_writes_are_serialized(self):
        """Test that concurrent write() calls are serialized by the lock.

        When parallel subagents invoke MCP tools, they trigger concurrent write()
        calls. Without the _write_lock, trio raises BusyResourceError.

        Uses a real subprocess with the same stream setup as production:
        process.stdin -> TextSendStream
        """

        async def _test():
            # Create a real subprocess that consumes stdin (cross-platform)
            process = await anyio.open_process(
                [sys.executable, "-c", "import sys; sys.stdin.read()"],
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE,
            )

            try:
                transport = SubprocessCLITransport(
                    prompt="test",
                    options=ClaudeAgentOptions(cli_path="/usr/bin/claude"),
                )

                # Same setup as production: TextSendStream wrapping process.stdin
                transport._ready = True
                transport._process = MagicMock(returncode=None)
                assert process.stdin
                transport._stdin_stream = TextSendStream(process.stdin)
                # Spawn concurrent writes - the lock should serialize them
                num_writes = 10
                errors: list[Exception] = []

                async def do_write(i: int):
                    try:
                        await transport.write(f'{{"msg": {i}}}\n')
                    except Exception as e:
                        errors.append(e)

                async with anyio.create_task_group() as tg:
                    for i in range(num_writes):
                        tg.start_soon(do_write, i)

                # All writes should succeed - the lock serializes them
                assert len(errors) == 0, f"Got errors: {errors}"
            finally:
                process.terminate()
                await process.wait()

        anyio.run(_test, backend="trio")

    def test_concurrent_writes_fail_without_lock(self):
        """Verify that without the lock, concurrent writes cause BusyResourceError.

        Uses a real subprocess with the same stream setup as production.
        """

        async def _test():

            # Create a real subprocess that consumes stdin (cross-platform)
            process = await anyio.open_process(
                [sys.executable, "-c", "import sys; sys.stdin.read()"],
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE,
            )

            try:
                opts = ClaudeAgentOptions(cli_path="/usr/bin/claude")
                transport = SubprocessCLITransport(prompt="test", options=opts)
                # Same setup as production
                transport._ready = True
                transport._process = MagicMock(returncode=None)
                assert process.stdin
                transport._stdin_stream = TextSendStream(process.stdin)

                # Replace lock with no-op to trigger the race condition
                class NoOpLock:
                    @asynccontextmanager
                    async def __call__(self):
                        yield

                    async def __aenter__(self):
                        return self

                    async def __aexit__(self, *args):
                        pass

                transport._write_lock = NoOpLock()  # pyright: ignore[reportAttributeAccessIssue]
                # Spawn concurrent writes - should fail without lock
                num_writes = 10
                errors: list[Exception] = []

                async def do_write(i: int):
                    try:
                        await transport.write(f'{{"msg": {i}}}\n')
                    except Exception as e:
                        errors.append(e)

                async with anyio.create_task_group() as tg:
                    for i in range(num_writes):
                        tg.start_soon(do_write, i)

                # Should have gotten errors due to concurrent access
                assert len(errors) > 0, "Expected errors from concurrent access, but got none"

                # Check that at least one error mentions the concurrent access
                error_strs = [str(e) for e in errors]
                assert any("another task" in s for s in error_strs), (
                    f"Expected 'another task' error, got: {error_strs}"
                )
            finally:
                process.terminate()
                await process.wait()

        anyio.run(_test, backend="trio")

    def test_build_command_agents_always_via_initialize(self):
        """Test that --agents is NEVER passed via CLI.

        Matching TypeScript SDK behavior, agents are always sent via the
        initialize request through stdin, regardless of prompt type.
        """
        agents = {
            "test-agent": AgentDefinition(
                description="A test agent",
                prompt="You are a test agent",
            )
        }
        # Test with string prompt
        opts = make_options(agents=agents)
        transport = SubprocessCLITransport(prompt="Hello", options=opts)
        cmd = transport._build_command()
        assert "--agents" not in cmd
        assert "--input-format" in cmd
        assert "stream-json" in cmd

        # Test with async iterable prompt
        async def fake_stream() -> AsyncIterable[UserPromptMessage]:
            yield {"type": "user", "message": {"role": "user", "content": "test"}}

        transport2 = SubprocessCLITransport(
            prompt=fake_stream(),
            options=make_options(agents=agents),
        )
        cmd2 = transport2._build_command()
        assert "--agents" not in cmd2
        assert "--input-format" in cmd2
        assert "stream-json" in cmd2

    def test_build_command_always_uses_streaming(self):
        """Test that streaming mode is always used, even for string prompts.

        Matching TypeScript SDK behavior, we always use --input-format stream-json
        so that agents and other large configs can be sent via initialize request.
        """
        # String prompt should still use streaming
        transport = SubprocessCLITransport(prompt="Hello", options=make_options())
        cmd = transport._build_command()
        assert "--input-format" in cmd
        assert "stream-json" in cmd
        assert "--print" not in cmd

    def test_build_command_large_agents_work(self):
        """Test that large agent definitions work without size limits.

        Since agents are sent via initialize request through stdin,
        there are no ARG_MAX or command line length limits.
        """
        # Create a large agent definition (50KB prompt)
        large_prompt = "x" * 50000
        agents = {"large-agent": AgentDefinition(description="A large agent", prompt=large_prompt)}
        opts = make_options(agents=agents)
        transport = SubprocessCLITransport(prompt="Hello", options=opts)
        cmd = transport._build_command()
        # --agents should not be in command (sent via initialize)
        assert "--agents" not in cmd
        # No @filepath references should exist
        cmd_str = " ".join(cmd)
        assert "@" not in cmd_str

    def test_agent_definition_memory_field_serialization(self):
        """Test that AgentDefinition memory field is included in serialization.

        The memory field controls persistent cross-session learning for subagents.
        When set, it should appear in the serialized dict sent via initialize.
        When None (default), it should be omitted.
        """
        # memory=None (default) should be omitted from serialized output
        agent_no_memory = AgentDefinition(
            description="Agent without memory",
            prompt="You are a test agent",
        )
        serialized = agent_no_memory.to_dict()
        assert "memory" not in serialized
        assert serialized == {
            "description": "Agent without memory",
            "prompt": "You are a test agent",
        }
        # memory="user" should be included
        agent_user_memory = AgentDefinition(
            description="Agent with user memory",
            prompt="You remember things per-user",
            memory="user",
        )
        serialized = agent_user_memory.to_dict()
        assert serialized["memory"] == "user"
        # memory="project" should be included
        agent_project_memory = AgentDefinition(
            description="Agent with project memory",
            prompt="You remember things per-project",
            memory="project",
        )
        serialized = agent_project_memory.to_dict()
        assert serialized["memory"] == "project"
        # memory="local" should be included
        agent_local_memory = AgentDefinition(
            description="Agent with local memory",
            prompt="You remember things locally",
            memory="local",
        )
        serialized = agent_local_memory.to_dict()
        assert serialized["memory"] == "local"

    def test_agent_definition_memory_field_with_all_fields(self):
        """Test that memory field works alongside all other AgentDefinition fields."""
        agent = AgentDefinition(
            description="Full agent",
            prompt="You are a full agent",
            tools=["Read", "Write"],
            model="sonnet",
            memory="project",
        )
        serialized = agent.to_dict()
        assert serialized == {
            "description": "Full agent",
            "prompt": "You are a full agent",
            "tools": ["Read", "Write"],
            "model": "sonnet",
            "memory": "project",
        }

    def test_agent_definition_memory_passed_to_query_initialize(self):
        """Test that memory field is included in the initialize request agents dict.

        The Query class serializes agents using to_dict() and filters out None values.
        This test verifies the same logic produces the correct output.
        """
        agents = {
            "memory-agent": AgentDefinition(
                description="Agent with memory",
                prompt="You remember things",
                memory="user",
            ),
            "no-memory-agent": AgentDefinition(
                description="Agent without memory",
                prompt="You forget things",
            ),
        }

        # Replicate the serialization logic from Query.__init__
        agents_dict = {name: agent_def.to_dict() for name, agent_def in agents.items()}

        assert agents_dict["memory-agent"]["memory"] == "user"
        assert "memory" not in agents_dict["no-memory-agent"]

    def test_agent_definition_mcp_servers_field_serialization(self):
        """Test that AgentDefinition mcp_servers field serializes as 'mcpServers'.

        The CLI expects 'mcpServers' as an array of AgentMcpServerSpec.
        When mcp_servers is None (default), it should be omitted entirely.
        A dict input is converted to [{name: config}, ...] array format.
        """
        # mcp_servers=None (default) should be omitted from serialized output
        agent_no_mcp = AgentDefinition(
            description="Agent without MCP servers",
            prompt="You are a test agent",
        )
        serialized = agent_no_mcp.to_dict()
        assert "mcpServers" not in serialized
        assert "mcp_servers" not in serialized

        # Dict-style mcp_servers should serialize as mcpServers array
        agent_with_mcp = AgentDefinition(
            description="Agent with MCP servers",
            prompt="You have MCP tools",
            mcp_servers={
                "git": {"command": "uvx", "args": ["mcp-server-git"]},
            },
        )
        serialized = agent_with_mcp.to_dict()
        assert "mcpServers" in serialized
        assert "mcp_servers" not in serialized
        assert serialized["mcpServers"] == [
            {"git": {"command": "uvx", "args": ["mcp-server-git"]}},
        ]

    def test_agent_definition_mcp_servers_list_passthrough(self):
        """Test that list-style mcp_servers is passed through as-is.

        Users can provide the raw CLI format (array of string | {name: config})
        directly, and it should be serialized without conversion.
        """
        # List with string references
        agent_str = AgentDefinition(
            description="Agent with server references",
            prompt="You have tools",
            mcp_servers=["my-server"],
        )
        serialized = agent_str.to_dict()
        assert serialized["mcpServers"] == ["my-server"]

        # List with dict configs
        agent_dict = AgentDefinition(
            description="Agent with server configs",
            prompt="You have tools",
            mcp_servers=[{"git": {"command": "uvx", "args": ["mcp-server-git"]}}],
        )
        serialized = agent_dict.to_dict()
        assert serialized["mcpServers"] == [
            {"git": {"command": "uvx", "args": ["mcp-server-git"]}},
        ]

        # Mixed list
        agent_mixed = AgentDefinition(
            description="Agent with mixed servers",
            prompt="You have tools",
            mcp_servers=[
                "shared-server",
                {"git": {"command": "uvx", "args": ["mcp-server-git"]}},
            ],
        )
        serialized = agent_mixed.to_dict()
        assert serialized["mcpServers"] == [
            "shared-server",
            {"git": {"command": "uvx", "args": ["mcp-server-git"]}},
        ]

    def test_agent_definition_mcp_servers_with_all_fields(self):
        """Test that mcp_servers works alongside all other AgentDefinition fields."""
        agent = AgentDefinition(
            description="Full agent",
            prompt="You are a full agent",
            tools=["Read"],
            model="sonnet",
            memory="project",
            mcp_servers={
                "git": {"command": "uvx", "args": ["mcp-server-git"]},
            },
        )
        serialized = agent.to_dict()
        assert serialized == {
            "description": "Full agent",
            "prompt": "You are a full agent",
            "tools": ["Read"],
            "model": "sonnet",
            "memory": "project",
            "mcpServers": [
                {"git": {"command": "uvx", "args": ["mcp-server-git"]}},
            ],
        }

    def test_agent_definition_mcp_servers_multiple_servers(self):
        """Test that multiple MCP servers serialize as array entries."""
        agent = AgentDefinition(
            description="Multi-MCP agent",
            prompt="You have many tools",
            mcp_servers={
                "git": {"command": "uvx", "args": ["mcp-server-git"]},
                "remote": {"type": "sse", "url": "http://localhost:8080/sse"},
            },
        )
        serialized = agent.to_dict()
        assert "mcpServers" in serialized
        assert len(serialized["mcpServers"]) == 2
        # Each dict entry becomes a separate array element
        assert {"git": {"command": "uvx", "args": ["mcp-server-git"]}} in serialized["mcpServers"]
        assert {"remote": {"type": "sse", "url": "http://localhost:8080/sse"}} in serialized[
            "mcpServers"
        ]
