"""Claude SDK Client for interacting with Claude Code."""

from __future__ import annotations

from dataclasses import replace
import os
from typing import TYPE_CHECKING, Any, Self

import anyenv
from pydantic import TypeAdapter

from clawd_code_sdk._errors import CLIConnectionError
from clawd_code_sdk.models import (
    AccumulatedUsage,
    ClaudeAgentOptions,
    ResultMessage,
)
from clawd_code_sdk.models.mcp import McpStatusResponse
from clawd_code_sdk.models.messages import (
    AssistantMessage,
    ResultErrorMessage,
    ResultSuccessMessage,
    UserTextPrompt,
)


if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from clawd_code_sdk import Transport
    from clawd_code_sdk._internal.query import Query
    from clawd_code_sdk.models import Message, PermissionMode
    from clawd_code_sdk.models.mcp import McpServerConfig
    from clawd_code_sdk.models.messages import (
        UserImagePrompt,
    )
    from clawd_code_sdk.models.server_info import ClaudeCodeServerInfo


class ClaudeSDKClient:
    """Client for bidirectional, interactive conversations with Claude Code.

    Key features:
    - **Bidirectional**: Send and receive messages at any time
    - **Stateful**: Maintains conversation context across messages
    - **Interactive**: Send follow-ups based on responses
    - **Control flow**: Support for interrupts and session management

    Caveat: As of v0.0.21, you cannot use a ClaudeSDKClient instance across
    different async runtime contexts (e.g., different trio nurseries or asyncio
    task groups). The client internally maintains a persistent anyio task group
    for reading messages that remains active from connect() until disconnect().
    This means you must complete all operations with the client within the same
    async context where it was connected. Ideally, this limitation should not
    exist.
    """

    def __init__(
        self,
        options: ClaudeAgentOptions | None = None,
        transport: Transport | None = None,
    ):
        """Initialize Claude SDK client."""
        options = options or ClaudeAgentOptions()
        self.options = options
        self._custom_transport = transport
        self._transport: Transport | None = None
        self._query: Query | None = None
        self.session_usage: AccumulatedUsage = AccumulatedUsage()
        """Cumulative token usage across all queries in this session."""
        self.query_usage: AccumulatedUsage = AccumulatedUsage()
        """Token usage for the current/last query only (reset on each query() call)."""
        os.environ["CLAUDE_CODE_ENTRYPOINT"] = "sdk-py-client"

    def _ensure_connected(self) -> Query:
        """Return the active Query, raising if not connected."""
        if not self._query:
            raise CLIConnectionError("Not connected. Call connect() first.")
        return self._query

    async def connect(self) -> None:
        """Connect to Claude Code CLI and initialize the session."""
        from clawd_code_sdk._internal.query import Query
        from clawd_code_sdk._internal.transport.subprocess_cli import SubprocessCLITransport

        # Validate and configure permission settings (matching TypeScript SDK logic)
        self.options.validate()

        if self.options.can_use_tool:
            # Automatically set permission_prompt_tool_name to "stdio" for control protocol
            options = replace(self.options, permission_prompt_tool_name="stdio")
        else:
            options = self.options

        # Use provided custom transport or create subprocess transport
        tp = self._custom_transport or SubprocessCLITransport(options=options)
        self._transport = tp
        await self._transport.connect()
        # Extract SDK MCP servers from options
        sdk_mcp_servers = {}
        if isinstance(self.options.mcp_servers, dict):
            for name, config in self.options.mcp_servers.items():
                if config.get("type") == "sdk":
                    sdk_mcp_servers[name] = config["instance"]  # type: ignore[typeddict-item]

        # Calculate initialize timeout from CLAUDE_CODE_STREAM_CLOSE_TIMEOUT env var if set
        # CLAUDE_CODE_STREAM_CLOSE_TIMEOUT is in milliseconds, convert to seconds
        initialize_timeout_ms = int(os.environ.get("CLAUDE_CODE_STREAM_CLOSE_TIMEOUT", "60000"))
        initialize_timeout = max(initialize_timeout_ms / 1000.0, 60.0)
        # Extract system prompt for initialize request
        system_prompt: str | None = None
        append_system_prompt: str | None = None
        if self.options.system_prompt is None:
            if not self.options.include_builtin_system_prompt:
                system_prompt = ""  # Clear the builtin prompt
            # else: send nothing, CLI uses its default builtin prompt
        elif self.options.include_builtin_system_prompt:
            append_system_prompt = self.options.system_prompt
        else:
            system_prompt = self.options.system_prompt

        # JSON schema for structured output
        json_schema: dict[str, Any] | None
        match self.options.output_schema:
            case type() as typ:
                json_schema = TypeAdapter(typ).json_schema()
            case dict() as schema:
                json_schema = schema
            case None:
                json_schema = None

        # Create Query to handle control protocol
        self._query = Query(
            transport=self._transport,
            can_use_tool=self.options.can_use_tool,
            on_user_question=self.options.on_user_question,
            hooks=self.options.hooks,
            sdk_mcp_servers=sdk_mcp_servers,
            initialize_timeout=initialize_timeout,
            agents=self.options.agents,
            system_prompt=system_prompt,
            append_system_prompt=append_system_prompt,
            json_schema=json_schema,
            prompt_suggestions=self.options.prompt_suggestions,
        )
        # Start reading messages and initialize
        await self._query.start()
        await self._query.initialize()

    async def receive_messages(self) -> AsyncIterator[Message]:
        """Receive all messages from Claude."""
        from clawd_code_sdk._internal.message_parser import parse_message

        query = self._ensure_connected()
        async for data in query.receive_messages():
            message = parse_message(data)
            match message:
                case AssistantMessage():
                    message.raise_if_api_error()
                case ResultSuccessMessage() | ResultErrorMessage():
                    self.query_usage.accumulate(message.usage)
                    self.session_usage.accumulate(message.usage)
            yield message

    async def query(
        self,
        *prompts: str | UserTextPrompt | UserImagePrompt,
        session_id: str = "default",
        parent_tool_use_id: str | None = None,
    ) -> None:
        """Send a new user message with one or more content blocks.

        Args:
            *prompts: One or more content blocks. Strings are converted to
                UserTextPrompt automatically. Pass multiple to combine, e.g.
                ``query(image_prompt, "What's in this image?")``.
            session_id: Session identifier for the message.
            parent_tool_use_id: If responding to a tool use, the tool_use block ID.
        """
        self.query_usage.reset()
        self._ensure_connected()
        if not self._transport:
            raise CLIConnectionError("Not connected. Call connect() first.")
        if not prompts:
            return
        # Collect content blocks
        blocks = [UserTextPrompt(text=p) if isinstance(p, str) else p for p in prompts]
        # Single text block → plain string, otherwise list of content block dicts
        message_content: str | list[dict[str, Any]]
        if len(blocks) == 1 and isinstance(blocks[0], UserTextPrompt):
            message_content = blocks[0].text
        else:
            message_content = [b.to_content_block() for b in blocks]
        wire_message = {
            "type": "user",
            "message": {"role": "user", "content": message_content},
            "parent_tool_use_id": parent_tool_use_id,
            "session_id": session_id,
        }
        await self._transport.write(anyenv.dump_json(wire_message) + "\n")

    async def interrupt(self) -> None:
        """Send interrupt signal (only works with streaming mode)."""
        query = self._ensure_connected()
        await query.interrupt()

    async def set_permission_mode(self, mode: PermissionMode) -> None:
        """Change permission mode during conversation (only works with streaming mode).

        Args:
            mode: The permission mode to set. Valid options:
                - 'default': CLI prompts for dangerous tools
                - 'acceptEdits': Auto-accept file edits
                - 'plan': Plan mode for planning tasks
                - 'bypassPermissions': Allow all tools (use with caution)
        """
        query = self._ensure_connected()
        await query.set_permission_mode(mode)

    async def set_model(self, model: str | None = None) -> None:
        """Change the AI model during conversation (only works with streaming mode).

        Args:
            model: The model to use, or None to use default. Example: 'claude-sonnet-4-5'
        """
        query = self._ensure_connected()
        await query.set_model(model)

    async def stop_task(self, task_id: str) -> None:
        """Stop a running task."""
        query = self._ensure_connected()
        await query.stop_task(task_id)

    async def rewind_files(self, user_message_id: str) -> None:
        """Rewind tracked files to their state at a specific user message.

        Requires:
            - `enable_file_checkpointing=True` to track file changes
            - `extra_args={"replay-user-messages": None}` to receive UserMessage
              objects with `uuid` in the response stream

        Args:
            user_message_id: UUID of the user message to rewind to. This should be
                the `uuid` field from a `UserMessage` received during the conversation.

        Example:
            ```python
            options = ClaudeAgentOptions(
                enable_file_checkpointing=True,
                extra_args={"replay-user-messages": None},
            )
            async with ClaudeSDKClient(options) as client:
                await client.query("Make some changes to my files")
                async for msg in client.receive_response():
                    if isinstance(msg, UserMessage) and msg.uuid:
                        checkpoint_id = msg.uuid  # Save this for later

                # Later, rewind to that point
                await client.rewind_files(checkpoint_id)
            ```
        """
        query = self._ensure_connected()
        await query.rewind_files(user_message_id)

    async def get_mcp_status(self) -> McpStatusResponse:
        """Get current MCP server connection status.

        Returns:
            Validated MCP status response containing server statuses,
            configurations, tools, and connection information.
        """
        query = self._ensure_connected()
        result = await query.get_mcp_status()
        return McpStatusResponse.model_validate(result)

    async def set_mcp_servers(self, servers: dict[str, McpServerConfig]) -> dict[str, Any]:
        """Add, replace, or remove MCP servers dynamically mid-session.

        Allows dynamic registration of MCP servers without restarting the session.
        Pass an empty dict to remove all dynamic servers.

        The server name is automatically injected from the dict key into each
        config, so callers don't need to specify it redundantly.

        Args:
            servers: Dictionary mapping server names to server configurations.
                Values are typed MCP server configs (McpStdioServerConfig,
                McpSSEServerConfig, McpHttpServerConfig, or McpSdkServerConfig).

        Returns:
            Dictionary with results:
            - 'added': List of server names that were added
            - 'removed': List of server names that were removed
            - 'errors': Dict mapping server names to error messages (if any)
        """
        query = self._ensure_connected()
        wire_servers: dict[str, dict[str, Any]] = {}
        for name, config in servers.items():
            server_dict = dict(config)
            server_dict["name"] = name
            wire_servers[name] = server_dict
        return await query.set_mcp_servers(wire_servers)

    async def mcp_reconnect(self, server_name: str) -> None:
        """Reconnect to an MCP server."""
        query = self._ensure_connected()
        await query.mcp_reconnect(server_name)

    async def mcp_toggle(self, server_name: str, *, enabled: bool) -> None:
        """Enable or disable an MCP server."""
        query = self._ensure_connected()
        await query.mcp_toggle(server_name, enabled=enabled)

    async def set_max_thinking_tokens(self, max_thinking_tokens: int) -> None:
        """Set the maximum number of thinking tokens for extended thinking."""
        query = self._ensure_connected()
        await query.set_max_thinking_tokens(max_thinking_tokens)

    async def get_server_info(self) -> ClaudeCodeServerInfo | None:
        """Get server initialization info including available commands and output styles.

        Returns initialization information from the Claude Code server including:
        - Available commands (slash commands, system commands, etc.)
        - Current and available output styles
        - Server capabilities

        Returns:
            Parsed server info, or None if not yet initialized
        """
        query = self._ensure_connected()
        return query._initialization_result

    async def receive_response(self) -> AsyncIterator[Message]:
        """Receive messages from Claude until and including a ResultMessage.

        This async iterator yields all messages in sequence and automatically terminates
        after yielding a ResultMessage (which indicates the response is complete).
        It's a convenience method over receive_messages() for single-response workflows.

        **Stopping Behavior:**
        - Yields each message as it's received
        - Terminates immediately after yielding a ResultMessage
        - The ResultMessage IS included in the yielded messages
        - If no ResultMessage is received, the iterator continues indefinitely

        Yields:
            Message: Each message received

        Example:
            ```python
            async with ClaudeSDKClient() as client:
                await client.query("What's the capital of France?")

                async for msg in client.receive_response():
                    if isinstance(msg, AssistantMessage):
                        for block in msg.content:
                            if isinstance(block, TextBlock):
                                print(f"Claude: {block.text}")
                    elif isinstance(msg, ResultMessage):
                        print(f"Cost: ${msg.total_cost_usd:.4f}")
                        # Iterator will terminate after this message
            ```

        Note:
            To collect all messages: `messages = [msg async for msg in client.receive_response()]`
            The final message in the list will always be a ResultMessage.
        """
        async for message in self.receive_messages():
            yield message
            if isinstance(message, ResultMessage):
                return

    async def disconnect(self) -> None:
        """Disconnect from Claude."""
        if self._query:
            await self._query.close()
            self._query = None
        self._transport = None

    async def __aenter__(self) -> Self:
        """Enter async context - automatically connects with empty stream for interactive use."""
        await self.connect()
        return self

    async def __aexit__(self, *args: object) -> None:
        """Exit async context - always disconnects."""
        await self.disconnect()


if __name__ == "__main__":
    import asyncio

    from clawd_code_sdk.models import ThinkingConfigAdaptive

    os.environ["ANTHROPIC_API_KEY"] = ""

    async def main() -> None:
        opts = ClaudeAgentOptions(thinking=ThinkingConfigAdaptive())
        client = ClaudeSDKClient(opts)
        await client.connect()
        await client.query("ultrathink")
        async for msg in client.receive_response():
            print(msg)
        await client.query("/compact")
        async for msg in client.receive_response():
            print(msg)

    asyncio.run(main())
