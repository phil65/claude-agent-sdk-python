"""Claude SDK Client for interacting with Claude Code."""

from __future__ import annotations

from dataclasses import asdict, replace
import os
from typing import TYPE_CHECKING, Any, Literal, Self, cast

from clawd_code_sdk._errors import CLIConnectionError
from clawd_code_sdk._internal.query import Query
from clawd_code_sdk._internal.transport.subprocess_cli import SubprocessCLITransport
from clawd_code_sdk.models import (
    AssistantMessage,
    ClaudeAgentOptions,
    GetSettingsResponse,
    McpAuthenticateResponse,
    McpSdkServerConfigWithInstance,
    McpSetServersResult,
    McpStatusResponse,
    RemoteControlResponse,
    ResultErrorMessage,
    ResultMessage,
    ResultSuccessMessage,
    SDKControlGetContextUsageResponse,
    SessionStateChangedMessage,
    StatusSystemMessage,
    Usage,
    UserMessage,
    UserTextPrompt,
)


if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from clawd_code_sdk import Transport
    from clawd_code_sdk.models import (
        ClaudeCodeAgentInfo,
        ClaudeCodeServerInfo,
        ClaudeCodeSettings,
        ClaudeOAuthWaitForCompletionResponse,
        McpServerConfig,
        Message,
        PermissionMode,
        SessionState,
        SideQuestionResponse,
        UserPrompt,
    )


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
        self.session_usage: Usage = Usage()
        self.session_state: SessionState = "idle"
        """Cumulative token usage across all queries in this session."""
        self.query_usage: Usage = Usage()
        """Token usage for the current/last query only (reset on each query() call)."""
        self.session_cost: float = 0.0
        """Cumulative cost in USD across all queries in this session."""
        self.query_cost: float = 0.0
        """Cost in USD for the current/last query only (reset on each query() call)."""
        self.status: Literal["compacting"] | None = None
        """Current client status, or None when idle."""

        self._logfire_prompt: str | None = None
        if self.options.instrument:
            from clawd_code_sdk.instrumentation import inject_tracing_hooks

            inject_tracing_hooks(self.options)

    def _ensure_connected(self) -> Query:
        """Return the active Query, raising if not connected."""
        if not self._query:
            raise CLIConnectionError("Not connected. Call connect() first.")
        return self._query

    async def connect(self) -> None:
        """Connect to Claude Code CLI and initialize the session."""
        # If on_permission is a callback, extract it for Query and replace with
        # "stdio" so the CLI routes permission requests through the control protocol.
        if callable(self.options.on_permission):
            can_use_tool = self.options.on_permission
            options = replace(self.options, on_permission="stdio")
        else:
            can_use_tool = None
            options = self.options

        # Use provided custom transport or create subprocess transport
        tp = self._custom_transport or SubprocessCLITransport(options=options)
        self._transport = tp
        await self._transport.connect()
        # Extract SDK MCP servers from options
        sdk_mcp_servers = {}
        if isinstance(self.options.mcp_servers, dict):
            for name, config in self.options.mcp_servers.items():
                if isinstance(config, McpSdkServerConfigWithInstance):
                    sdk_mcp_servers[name] = config.instance

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

        # Create Query to handle control protocol
        self._query = Query(
            transport=self._transport,
            can_use_tool=can_use_tool,  # ty:ignore[invalid-argument-type]
            on_user_question=self.options.on_user_question,
            on_elicitation=self.options.on_elicitation,
            hooks=self.options.hooks,
            sdk_mcp_servers=sdk_mcp_servers,
            initialize_timeout=initialize_timeout,
            agents=self.options.agents,
            system_prompt=system_prompt,
            append_system_prompt=append_system_prompt,
            json_schema=self.options.get_json_schema(),
            prompt_suggestions=self.options.prompt_suggestions,
            agent_progress_summaries=self.options.agent_progress_summaries,
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
                case StatusSystemMessage(status=status):
                    self.status = status
                case SessionStateChangedMessage(state=state):
                    self.session_state = state
                case (
                    ResultSuccessMessage(usage=usage, total_cost_usd=total_cost)
                    | ResultErrorMessage(usage=usage, total_cost_usd=total_cost)
                ):
                    self.query_usage.accumulate(usage)
                    self.session_usage.accumulate(usage)
                    # total_cost_usd is cumulative; derive per-query cost as delta
                    self.query_cost = total_cost - self.session_cost
                    self.session_cost = total_cost
            yield message

    async def query(
        self,
        *prompts: str | UserPrompt,
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
        prompt = prompts[0] if prompts else None
        self._logfire_prompt = str(prompt)
        self.query_usage.reset()
        self.query_cost = 0.0
        self._ensure_connected()
        if not self._query:
            raise CLIConnectionError("Not connected. Call connect() first.")
        if not prompts:
            raise ValueError("At least one prompt is required")
        # Collect content blocks
        blocks = [UserTextPrompt(text=p) if isinstance(p, str) else p for p in prompts]
        message_content = [cast(dict[str, Any], b.to_content_block()) for b in blocks]
        wire_message = {
            "type": "user",
            "message": {"role": "user", "content": message_content},
            "parent_tool_use_id": parent_tool_use_id,
            "session_id": session_id,
        }
        await self._query.write_json(wire_message)

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

    async def cancel_async_message(self, message_uuid: str) -> None:
        """Drop a pending async user message from the command queue by uuid."""
        query = self._ensure_connected()
        await query.cancel_async_message(message_uuid)

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

    async def seed_read_state(self, path: str, mtime: int) -> None:
        """Seed the CLI's readFileState cache with a path+mtime entry.

        Use when the client observed a Read that has since been removed from context
        (e.g. by snip), so a subsequent Edit won't fail "file not read yet".

        Args:
            path: Path to the file that was previously Read
            mtime: File mtime (floored ms) at the time of the observed Read
        """
        query = self._ensure_connected()
        await query.seed_read_state(path, mtime)

    async def get_mcp_status(self) -> McpStatusResponse:
        """Get current MCP server connection status.

        Returns:
            Validated MCP status response containing server statuses,
            configurations, tools, and connection information.
        """
        query = self._ensure_connected()
        result = await query.get_mcp_status()
        return McpStatusResponse.model_validate(result)

    async def set_mcp_servers(self, servers: dict[str, McpServerConfig]) -> McpSetServersResult:
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
            server_dict = asdict(config)
            server_dict["name"] = name
            wire_servers[name] = server_dict
        result = await query.set_mcp_servers(wire_servers)
        return McpSetServersResult.model_validate(result)

    async def mcp_reconnect(self, server_name: str) -> None:
        """Reconnect to an MCP server."""
        query = self._ensure_connected()
        await query.mcp_reconnect(server_name)

    async def mcp_toggle(self, server_name: str, *, enabled: bool) -> None:
        """Enable or disable an MCP server."""
        query = self._ensure_connected()
        await query.mcp_toggle(server_name, enabled=enabled)

    async def end_session(self) -> None:
        """End the current session."""
        query = self._ensure_connected()
        await query.end_session()

    async def remote_control(self, *, enabled: bool) -> RemoteControlResponse | None:
        """Toggle the remote control REPL bridge for external session access.

        When enabled, starts a bridge that allows remote clients to send prompts,
        permission responses, interrupts, and model changes into the session.

        Returns:
            A ``RemoteControlResponse`` with session URLs and environment ID
            when enabling, or ``None`` when disabling.
        """
        query = self._ensure_connected()
        result = await query.remote_control(enabled=enabled)
        if not result:
            return None
        return RemoteControlResponse.model_validate(result)

    async def apply_flag_settings(self, settings: ClaudeCodeSettings) -> None:
        """Apply runtime settings overrides without restarting the session.

        Flag settings are an in-memory settings source that gets merged with
        other sources (user, project, etc.) to produce the effective settings.

        Args:
            settings: Settings to apply. Only non-None fields will be sent.
        """
        query = self._ensure_connected()
        serialized = settings.model_dump(by_alias=True, exclude_none=True)
        await query.apply_flag_settings(serialized)

    async def get_settings(self) -> GetSettingsResponse:
        """Get the effective merged settings and raw per-source settings."""
        query = self._ensure_connected()
        result = await query.get_settings()
        return GetSettingsResponse.model_validate(result)

    async def get_context_usage(self) -> SDKControlGetContextUsageResponse:
        """Get a breakdown of current context window usage by category."""
        query = self._ensure_connected()
        result = await query.get_context_usage()
        return SDKControlGetContextUsageResponse.model_validate(result)

    async def mcp_authenticate(self, server_name: str) -> McpAuthenticateResponse:
        """Trigger OAuth authentication for an MCP server.

        Returns:
            Response indicating whether user action is required and the auth URL if so.
        """
        query = self._ensure_connected()
        result = await query.mcp_authenticate(server_name)
        return McpAuthenticateResponse.model_validate(result)

    async def mcp_clear_auth(self, server_name: str) -> None:
        """Clear OAuth credentials for an MCP server."""
        query = self._ensure_connected()
        await query.mcp_clear_auth(server_name)

    async def mcp_oauth_callback_url(self, server_name: str, callback_url: str) -> None:
        """Provide an OAuth redirect callback URL to complete an MCP server OAuth flow.

        After the user completes browser-based OAuth, call this with the full
        redirect URL (containing the authorization code) to finish the flow.
        """
        query = self._ensure_connected()
        await query.mcp_oauth_callback_url(server_name, callback_url)

    async def claude_oauth_wait_for_completion(self) -> ClaudeOAuthWaitForCompletionResponse:
        """Wait for an in-progress Claude OAuth flow to complete.

        Returns:
            Account details (email, organization, subscriptionType, etc.).
        """
        query = self._ensure_connected()
        return await query.claude_oauth_wait_for_completion()

    async def side_question(self, question: str) -> SideQuestionResponse:
        """Send a side question to the model using the current conversation context.

        The model answers the question without it being added to the main
        conversation history.

        Args:
            question: The question to ask the model.

        Returns:
            The model's answer, or None if no context was available.
        """
        query = self._ensure_connected()
        return await query.side_question(question)

    async def set_max_thinking_tokens(self, max_thinking_tokens: int) -> None:
        """Set the maximum number of thinking tokens for extended thinking."""
        query = self._ensure_connected()
        await query.set_max_thinking_tokens(max_thinking_tokens)

    async def supported_agents(self) -> list[ClaudeCodeAgentInfo]:
        """Get the list of available subagents for the current session.

        Returns:
            List of available agents with their names, descriptions, and configuration.
        """
        query = self._ensure_connected()
        return await query.supported_agents()

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

    async def receive_response_instrumented(
        self, wait_for_idle: bool = False
    ) -> AsyncIterator[Message]:
        from logfire import Logfire
        from logfire._internal.integrations.llm_providers.semconv import (
            INPUT_MESSAGES,
            OPERATION_NAME,
            PROVIDER_NAME,
            REQUEST_MODEL,
            RESPONSE_MODEL,
            SYSTEM,
            SYSTEM_INSTRUCTIONS,
            ChatMessage,
            TextPart,
        )
        from logfire._internal.utils import handle_internal_errors

        from clawd_code_sdk.instrumentation import (
            ConversationState,
            clear_state,
            record_result,
            set_state,
        )

        logfire_instance = Logfire()
        logfire_claude = logfire_instance.with_settings(custom_scope_suffix="clawd_code_sdk")

        input_messages: list[ChatMessage] = []
        if prompt := self._logfire_prompt:
            part = TextPart(type="text", content=prompt)
            input_messages = [ChatMessage(role="user", parts=[part])]  # ty:ignore[invalid-argument-type]

        span_data: dict[str, Any] = {
            OPERATION_NAME: "invoke_agent",
            PROVIDER_NAME: "anthropic",
            SYSTEM: "anthropic",
        }
        if input_messages:
            span_data[INPUT_MESSAGES] = input_messages
        if self.options and (system_prompt := self.options.system_prompt):
            text = str(system_prompt)
            span_data[SYSTEM_INSTRUCTIONS] = [TextPart(type="text", content=text)]

        with logfire_claude.span("invoke_agent", **span_data) as root_span:
            state = ConversationState(
                logfire=logfire_claude,
                root_span=root_span,
                input_messages=input_messages,
                system_instructions=span_data.get(SYSTEM_INSTRUCTIONS),
            )
            set_state(state)
            # Open the first chat span now — the LLM call starts at query time.
            state.open_chat_span()

            try:
                async for msg in self.receive_response(wait_for_idle=wait_for_idle):
                    with handle_internal_errors:  # ty:ignore[invalid-context-manager]
                        match msg:
                            case AssistantMessage():
                                state.handle_assistant_message(msg)
                            case UserMessage():
                                state.handle_user_message()
                            case ResultSuccessMessage() | ResultErrorMessage():
                                record_result(root_span, msg)
                                if state.model:
                                    root_span.set_attribute(REQUEST_MODEL, state.model)
                                    root_span.set_attribute(RESPONSE_MODEL, state.model)
                            case _:
                                pass
                    yield msg
            finally:
                state.close()
                clear_state()

    async def receive_response(self, *, wait_for_idle: bool = False) -> AsyncIterator[Message]:
        """Receive messages from Claude until the response is complete.

        This async iterator yields all messages in sequence and automatically terminates
        after yielding a ResultMessage (which indicates the response is complete).
        It's a convenience method over receive_messages() for single-response workflows.

        **Stopping Behavior:**
        - Yields each message as it's received
        - By default, terminates immediately after yielding a ResultMessage
        - When ``wait_for_idle=True``, continues yielding until the session
          transitions to ``idle`` state (the authoritative turn-over signal)
        - The ResultMessage IS included in the yielded messages
        - If no ResultMessage is received, the iterator continues indefinitely

        Args:
            wait_for_idle: If True, keep yielding messages after ResultMessage
                until a ``session_state_changed`` message with ``state='idle'``
                is received. This guarantees the CLI has fully finished its
                turn (held-back results flushed, background agent loops exited)
                before the iterator terminates.

        Yields:
            Message: Each message received

        Note:
            To collect all messages: `messages = [msg async for msg in client.receive_response()]`
            The final message in the list will always be a ResultMessage (or
            SessionStateChangedMessage when ``wait_for_idle=True``).
        """
        async for message in self.receive_messages():
            yield message
            if wait_for_idle:
                if isinstance(message, SessionStateChangedMessage) and message.state == "idle":
                    return
            elif isinstance(message, ResultMessage):
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
