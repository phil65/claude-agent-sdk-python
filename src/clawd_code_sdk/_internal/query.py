"""Query class for handling bidirectional control protocol."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import replace
import logging
import math
import os
from typing import TYPE_CHECKING, Any, Self, cast

import anyenv
import anyio

from clawd_code_sdk._errors import ClaudeSDKError, ControlRequestError, ControlRequestTimeoutError
from clawd_code_sdk._internal.transport.subprocess_cli import SubprocessCLITransport
from clawd_code_sdk.mcp_utils import process_mcp_request
from clawd_code_sdk.models import (
    AskUserQuestionInput,
    ClaudeCodeServerInfo,
    ClaudeOAuthWaitForCompletionResponse,
    ControlErrorResponse,
    ControlResponse,
    JSONRPCError,
    JSONRPCErrorResponse,
    McpSdkServerConfigWithInstance,
    PermissionResultAllow,
    SDKControlElicitationRequest,
    SDKControlInitializeRequest,
    SDKControlInterruptRequest,
    SDKControlMcpMessageRequest,
    SDKControlPermissionRequest,
    SDKControlResponse,
    SDKControlRewindFilesRequest,
    SDKControlSetPermissionModeRequest,
    SDKControlStopTaskRequest,
    SDKHookCallbackRequest,
    SideQuestionResponse,
    ToolPermissionContext,
    control_request_adapter,
)


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterator

    from mcp.server import Server as McpServer

    from clawd_code_sdk._internal.transport import Transport
    from clawd_code_sdk.models import (
        AgentDefinition,
        CanUseTool,
        ClaudeAgentOptions,
        ClaudeCodeAgentInfo,
        ControlRequestUnion,
        HookCallback,
        HookEvent,
        HookMatcher,
        JSONRPCMessage,
        JSONRPCResponse,
        OnElicitation,
        OnUserQuestion,
        PermissionMode,
        PermissionResult,
        RequestId,
    )

logger = logging.getLogger(__name__)


def get_jsonrpc_request_id(message: JSONRPCMessage) -> RequestId:
    """Extract the request ID from a JSON-RPC message if available. Falls back to 0."""
    raw_id = message.get("id")
    return raw_id if isinstance(raw_id, str | int) else 0


class Query:
    """Handles bidirectional control protocol on top of Transport.

    This class manages:
    - Control request/response routing
    - Hook callbacks
    - Tool permission callbacks
    - Message streaming
    - Initialization handshake
    """

    def __init__(
        self,
        transport: Transport,
        can_use_tool: CanUseTool | None = None,
        on_user_question: OnUserQuestion | None = None,
        on_elicitation: OnElicitation | None = None,
        hooks: dict[HookEvent, list[HookMatcher]] | None = None,
        sdk_mcp_servers: dict[str, McpServer] | None = None,
        initialize_timeout: float = 60.0,
        agents: dict[str, AgentDefinition] | None = None,
        system_prompt: str | None = None,
        append_system_prompt: str | None = None,
        exclude_dynamic_sections: bool | None = None,
        json_schema: dict[str, Any] | None = None,
        prompt_suggestions: bool | None = None,
        agent_progress_summaries: bool | None = None,
    ):
        """Initialize Query with transport and callbacks.

        Args:
            transport: Low-level transport for I/O
            can_use_tool: Optional callback for tool permission requests
            on_user_question: Optional callback for AskUserQuestion elicitation
            on_elicitation: Optional callback for MCP elicitation requests
            hooks: Optional hook configurations
            sdk_mcp_servers: Optional SDK MCP server instances
            initialize_timeout: Timeout in seconds for the initialize request
            agents: Optional agent definitions to send via initialize
            system_prompt: Optional system prompt to send via initialize
            append_system_prompt: Optional text to append to preset system prompt
            exclude_dynamic_sections: Exclude dynamic sections from the system prompt
            json_schema: Optional JSON schema for structured output
            prompt_suggestions: Optional flag to enable prompt suggestions
            agent_progress_summaries: Optional flag to enable agent progress summaries
        """
        self._initialize_timeout = initialize_timeout
        self.transport = transport
        self.can_use_tool = can_use_tool
        self.on_user_question = on_user_question
        self.on_elicitation = on_elicitation
        self.hooks: dict[HookEvent, list[dict[str, Any]]] = {
            event: [m.model_dump(exclude_none=True) for m in matchers]
            for event, matchers in (hooks or {}).items()
        }
        self.sdk_mcp_servers = sdk_mcp_servers or {}
        self._agents = agents
        self._system_prompt = system_prompt
        self._append_system_prompt = append_system_prompt
        self._exclude_dynamic_sections = exclude_dynamic_sections
        self._json_schema = json_schema
        self._prompt_suggestions = prompt_suggestions
        self._agent_progress_summaries = agent_progress_summaries
        # Control protocol state
        self.pending_control_responses: dict[str, anyio.Event] = {}
        self.pending_control_results: dict[str, dict[str, Any] | Exception] = {}
        self.hook_callbacks: dict[str, HookCallback] = {}
        self.next_callback_id = 0
        self._request_counter = 0
        # Message stream
        self._message_send, self._message_receive = anyio.create_memory_object_stream[
            dict[str, Any]
        ](max_buffer_size=math.inf)
        self._read_task: asyncio.Task[None] | None = None
        self._child_tasks: set[asyncio.Task[Any]] = set()
        self._inflight_requests: dict[str, asyncio.Task[Any]] = {}
        self._closed = False
        self._initialization_result: ClaudeCodeServerInfo | None = None
        # Track first result for proper stream closure with SDK MCP servers
        self._first_result_event = anyio.Event()

    @classmethod
    def from_options(cls, options: ClaudeAgentOptions, transport: Transport | None = None) -> Query:
        # Extract SDK MCP servers from options
        if options.instrument:
            from clawd_code_sdk.instrumentation import inject_tracing_hooks

            hooks = inject_tracing_hooks(options.hooks)
        else:
            hooks = options.hooks or {}

        # If on_permission is a callback, extract it for Query and replace with
        # "stdio" so the CLI routes permission requests through the control protocol.
        if callable(options.on_permission):
            can_use_tool = options.on_permission
            options = replace(options, on_permission="stdio")
        else:
            can_use_tool = None

        sdk_mcp_servers = {}
        if isinstance(options.mcp_servers, dict):
            for name, config in options.mcp_servers.items():
                if isinstance(config, McpSdkServerConfigWithInstance):
                    sdk_mcp_servers[name] = config.instance

        # Calculate initialize timeout from CLAUDE_CODE_STREAM_CLOSE_TIMEOUT env var if set
        # CLAUDE_CODE_STREAM_CLOSE_TIMEOUT is in milliseconds, convert to seconds
        initialize_timeout_ms = int(os.environ.get("CLAUDE_CODE_STREAM_CLOSE_TIMEOUT", "60000"))
        initialize_timeout = max(initialize_timeout_ms / 1000.0, 60.0)
        # Extract system prompt for initialize request
        system_prompt: str | None = None
        append_system_prompt: str | None = None
        if options.system_prompt is None:
            if not options.include_builtin_system_prompt:
                system_prompt = ""  # Clear the builtin prompt
            # else: send nothing, CLI uses its default builtin prompt
        elif options.include_builtin_system_prompt:
            append_system_prompt = options.system_prompt
        else:
            system_prompt = options.system_prompt

        # Create Query to handle control protocol
        return cls(
            transport=transport or SubprocessCLITransport(options=options),
            can_use_tool=can_use_tool,  # ty:ignore[invalid-argument-type]
            on_user_question=options.on_user_question,
            on_elicitation=options.on_elicitation,
            hooks=hooks,
            sdk_mcp_servers=sdk_mcp_servers,
            initialize_timeout=initialize_timeout,
            agents=options.agents,
            system_prompt=system_prompt,
            append_system_prompt=append_system_prompt,
            exclude_dynamic_sections=options.exclude_dynamic_sections,
            json_schema=options.get_json_schema(),
            prompt_suggestions=options.prompt_suggestions,
            agent_progress_summaries=options.agent_progress_summaries,
        )

    @property
    def initialized(self) -> bool:
        return self._initialization_result is not None

    async def initialize(self) -> ClaudeCodeServerInfo:
        """Initialize control protocol.

        Returns:
            Parsed server info with supported commands and capabilities
        """
        # Build hooks configuration for initialization
        hooks_config: dict[HookEvent, Any] = {}
        for event, matchers in self.hooks.items():
            if not matchers:
                continue
            hooks_config[event] = []
            for matcher in matchers:
                callback_ids = []
                for callback in matcher.get("hooks", []):
                    callback_id = f"hook_{self.next_callback_id}"
                    self.next_callback_id += 1
                    self.hook_callbacks[callback_id] = callback
                    callback_ids.append(callback_id)
                matcher_cfg = {"matcher": matcher.get("matcher"), "hookCallbackIds": callback_ids}
                if matcher.get("timeout") is not None:
                    matcher_cfg["timeout"] = matcher.get("timeout")
                hooks_config[event].append(matcher_cfg)
        request = SDKControlInitializeRequest(
            hooks=hooks_config or None,
            agents={name: i.to_wire_model() for name, i in (self._agents or {}).items()} or None,
            system_prompt=self._system_prompt,
            append_system_prompt=self._append_system_prompt,
            json_schema=self._json_schema,
            prompt_suggestions=self._prompt_suggestions,
            exclude_dynamic_sections=self._exclude_dynamic_sections,
            sdk_mcp_servers=list(self.sdk_mcp_servers.keys()) or None,
            agent_progress_summaries=self._agent_progress_summaries,
        ).model_dump(by_alias=True, exclude_none=True)
        # Use longer timeout for initialize since MCP servers may take time to start
        response = await self._send_control_request(request, timeout=self._initialize_timeout)
        self._initialization_result = ClaudeCodeServerInfo.model_validate(response)
        return self._initialization_result

    async def start(self) -> None:
        """Start reading messages from transport."""
        if self._read_task is None:
            loop = asyncio.get_running_loop()
            self._read_task = loop.create_task(self._read_messages())

    def spawn_task(self, coro: Any) -> asyncio.Task[Any]:
        """Spawn a child task that will be cancelled on close()."""
        loop = asyncio.get_running_loop()
        task = loop.create_task(coro)
        self._child_tasks.add(task)
        task.add_done_callback(self._child_tasks.discard)
        return task

    def _spawn_control_request_handler(self, request_id: str, coro: Any) -> None:
        """Spawn a control request handler and track it for cancellation."""
        task = self.spawn_task(coro)
        self._inflight_requests[request_id] = task

        def _done(_t: asyncio.Task[Any]) -> None:
            self._inflight_requests.pop(request_id, None)

        task.add_done_callback(_done)

    async def _read_messages(self) -> None:
        """Read messages from transport and route them."""
        try:
            async for message in self.transport.read_messages():
                if self._closed:
                    break

                match message:
                    case {
                        "type": "control_response",
                        "response": {"request_id": request_id, "subtype": "error", "error": error},
                    } if request_id in self.pending_control_responses:
                        event = self.pending_control_responses[request_id]
                        self.pending_control_results[request_id] = ControlRequestError(
                            error, subtype="error"
                        )
                        event.set()

                    case {
                        "type": "control_response",
                        "response": {"request_id": request_id} as response,
                    } if request_id in self.pending_control_responses:
                        event = self.pending_control_responses[request_id]
                        self.pending_control_results[request_id] = response
                        event.set()
                    case {"type": "control_response"} as msg:
                        logger.info("unhandled control message: %s", msg)
                    case {"type": "control_request"}:
                        req_id = message["request_id"]
                        req = control_request_adapter.validate_python(message["request"])
                        self._spawn_control_request_handler(
                            req_id, self._handle_control_request(req_id, req)
                        )
                    case {"type": "control_cancel_request"}:
                        if (cancel_id := message.get("request_id")) and (
                            inflight := self._inflight_requests.pop(cancel_id, None)
                        ):
                            inflight.cancel()
                    case {"type": "result"}:
                        self._first_result_event.set()
                        await self._message_send.send(message)
                    case _:
                        # Regular SDK messages go to the stream
                        await self._message_send.send(message)

        except anyio.get_cancelled_exc_class():
            # Task was cancelled - this is expected behavior
            logger.debug("Read task cancelled")
            raise  # Re-raise to properly handle cancellation
        except Exception as e:
            logger.exception("Fatal error in message reader")
            # Signal all pending control requests so they fail fast instead of timing out
            for request_id, event in list(self.pending_control_responses.items()):
                if request_id not in self.pending_control_results:
                    self.pending_control_results[request_id] = e
                    event.set()
            # Put error in stream so iterators can handle it
            await self._message_send.send({"type": "error", "error": str(e)})
        finally:
            # Always signal end of stream
            await self._message_send.send({"type": "end"})

    async def _handle_control_request(
        self,
        request_id: str,
        request_data: ControlRequestUnion,
    ) -> None:
        """Handle incoming control request from CLI."""
        response_data: dict[str, Any] = {}
        try:
            match request_data:
                case SDKControlPermissionRequest() as req:
                    result = await self._handle_permission_request(req)
                    response_data = result.model_dump(by_alias=True, exclude_none=True)
                case SDKHookCallbackRequest() as req:
                    response_data = await self._handle_hook_callback(req)
                case SDKControlMcpMessageRequest(server_name=server_name, message=message):
                    mcp_resp = await self._handle_sdk_mcp_request(server_name, message)
                    response_data = {"mcp_response": mcp_resp}
                case SDKControlElicitationRequest() as req:
                    response_data = await self._handle_elicitation_request(req)
                case (
                    SDKControlInitializeRequest()
                    | SDKControlSetPermissionModeRequest()
                    | SDKControlRewindFilesRequest()
                    | SDKControlStopTaskRequest()
                    | SDKControlInterruptRequest()  # No response data needed
                ):
                    pass  # Handled elsewhere
            dct = ControlResponse(subtype="success", request_id=request_id, response=response_data)
            success_response = SDKControlResponse(type="control_response", response=dct)
            await self.write_json(success_response)

        except asyncio.CancelledError:
            # Request was cancelled via control_cancel_request; the CLI has
            # already abandoned this request, so don't write a response.
            raise
        except Exception as e:
            response = ControlErrorResponse(subtype="error", request_id=request_id, error=str(e))
            error_response = SDKControlResponse(type="control_response", response=response)
            await self.write_json(error_response)

    async def _handle_permission_request(
        self, req: SDKControlPermissionRequest
    ) -> PermissionResult:
        """Handle a tool permission request.

        Dispatches AskUserQuestion to on_user_question if set,
        otherwise falls through to can_use_tool for backwards compatibility.
        """
        context = ToolPermissionContext.from_permission_request(req)
        # Dispatch elicitation requests to dedicated callback if available
        if req.tool_name == "AskUserQuestion" and self.on_user_question:
            input_data = cast(AskUserQuestionInput, req.input)
            result = await self.on_user_question(input_data, context)
        else:
            if not self.can_use_tool:
                raise RuntimeError("canUseTool callback is not provided")
            result = await self.can_use_tool(req.tool_name, req.input, context)
        if isinstance(result, PermissionResultAllow) and result.updated_input is None:
            result.updated_input = req.input
        return result

    async def _handle_elicitation_request(
        self, req: SDKControlElicitationRequest
    ) -> dict[str, Any]:
        """Handle an MCP elicitation request.

        If on_elicitation callback is set, dispatches to it.
        Otherwise, automatically declines the elicitation.
        """
        if not self.on_elicitation:
            # Auto-decline if no callback is set
            return {"action": "decline"}
        result = await self.on_elicitation(req)
        return result.model_dump(mode="json", exclude_none=True)

    async def _handle_hook_callback(self, req: SDKHookCallbackRequest) -> dict[str, Any]:
        """Handle a hook callback request."""
        if not (callback := self.hook_callbacks.get(req.callback_id)):
            raise RuntimeError(f"No hook callback found for ID: {req.callback_id}")

        hook_output = await callback(req.input, req.tool_use_id, {"signal": None})
        # Strip trailing underscores from Python-safe names (async_, continue_) for CLI
        return {k.rstrip("_"): v for k, v in hook_output.items()}

    async def _send_control_request(
        self, request: dict[str, Any], timeout: float = 60.0
    ) -> dict[str, Any]:
        """Send control request to CLI and wait for response.

        Args:
            request: The control request to send
            timeout: Timeout in seconds to wait for response (default 60s)
        """
        # Generate unique request ID
        self._request_counter += 1
        request_id = f"req_{self._request_counter}_{os.urandom(4).hex()}"
        # Create event for response
        event = anyio.Event()
        self.pending_control_responses[request_id] = event
        # Build and send request
        control_request = {"type": "control_request", "request_id": request_id, "request": request}
        await self.write_json(control_request)
        # Wait for response
        try:
            with anyio.fail_after(timeout):
                await event.wait()

            result = self.pending_control_results.pop(request_id)
            self.pending_control_responses.pop(request_id, None)

            if isinstance(result, Exception):
                raise result

            response_data = result.get("response", {})
            return response_data if isinstance(response_data, dict) else {}
        except TimeoutError as e:
            self.pending_control_responses.pop(request_id, None)
            self.pending_control_results.pop(request_id, None)
            subtype = request.get("subtype")
            raise ControlRequestTimeoutError(
                f"Control request timeout: {subtype}", subtype=subtype
            ) from e

    async def _handle_sdk_mcp_request(
        self, server_name: str, message: JSONRPCMessage
    ) -> JSONRPCResponse:
        """Handle an MCP request for an SDK server.

        This acts as a bridge between JSONRPC messages from the CLI
        and the in-process MCP server. Ideally the MCP SDK would provide
        a method to handle raw JSONRPC, but for now we route manually.

        Args:
            server_name: Name of the SDK MCP server
            message: The JSONRPC message

        Returns:
            The response message
        """
        if server_name not in self.sdk_mcp_servers:
            dct = JSONRPCError(code=-32601, message=f"Server '{server_name}' not found")
            return JSONRPCErrorResponse(
                jsonrpc="2.0", id=get_jsonrpc_request_id(message), error=dct
            )
        server = self.sdk_mcp_servers[server_name]
        return await process_mcp_request(message, server)

    async def supported_agents(self) -> list[ClaudeCodeAgentInfo]:
        """Get the list of available subagents for the current session."""
        if self._initialization_result is None:
            raise RuntimeError("Not initialized. Call initialize() first.")
        return self._initialization_result.agents

    async def get_mcp_status(self) -> dict[str, Any]:
        """Get current MCP server connection status."""
        return await self._send_control_request({"subtype": "mcp_status"})

    async def set_mcp_servers(self, servers: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """Add, replace, or remove MCP servers dynamically."""
        return await self._send_control_request({"subtype": "mcp_set_servers", "servers": servers})

    async def mcp_reconnect(self, server_name: str) -> dict[str, Any]:
        """Reconnect to an MCP server."""
        req = {"subtype": "mcp_reconnect", "serverName": server_name}
        return await self._send_control_request(req)

    async def mcp_toggle(self, server_name: str, *, enabled: bool) -> dict[str, Any]:
        """Enable or disable an MCP server."""
        req = {"subtype": "mcp_toggle", "serverName": server_name, "enabled": enabled}
        return await self._send_control_request(req)

    async def set_max_thinking_tokens(self, max_thinking_tokens: int) -> dict[str, Any]:
        """Set the maximum number of thinking tokens."""
        req = {"subtype": "set_max_thinking_tokens", "max_thinking_tokens": max_thinking_tokens}
        return await self._send_control_request(req)

    async def interrupt(self) -> dict[str, Any]:
        """Send interrupt control request."""
        return await self._send_control_request({"subtype": "interrupt"})

    async def set_permission_mode(self, mode: PermissionMode) -> dict[str, Any]:
        """Change permission mode."""
        return await self._send_control_request({"subtype": "set_permission_mode", "mode": mode})

    async def set_model(self, model: str | None) -> dict[str, Any]:
        """Change the AI model."""
        return await self._send_control_request({"subtype": "set_model", "model": model})

    async def cancel_async_message(self, message_uuid: str) -> dict[str, Any]:
        """Drop a pending async user message from the command queue by uuid."""
        return await self._send_control_request(
            {"subtype": "cancel_async_message", "message_uuid": message_uuid}
        )

    async def stop_task(self, task_id: str) -> dict[str, Any]:
        """Stop a running task."""
        return await self._send_control_request({"subtype": "stop_task", "task_id": task_id})

    async def channel_enable(self, server_name: str) -> dict[str, Any]:
        """Enable MCP channel notifications for a marketplace plugin server."""
        req = {"subtype": "channel_enable", "serverName": server_name}
        return await self._send_control_request(req)

    async def end_session(self) -> dict[str, Any]:
        """End the current session."""
        return await self._send_control_request({"subtype": "end_session"})

    async def remote_control(self, *, enabled: bool) -> dict[str, Any]:
        """Toggle the remote control REPL bridge for external session access.

        When enabled, starts a bridge that allows remote clients to send prompts,
        permission responses, interrupts, and model changes into the session.
        The response includes ``session_url``, ``connect_url``, and
        ``environment_id`` when enabling.
        """
        req = {"subtype": "remote_control", "enabled": enabled}
        return await self._send_control_request(req)

    async def apply_flag_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        """Apply runtime flag settings."""
        req = {"subtype": "apply_flag_settings", "settings": settings}
        return await self._send_control_request(req)

    async def get_settings(self) -> dict[str, Any]:
        """Get the effective merged settings and raw per-source settings."""
        return await self._send_control_request({"subtype": "get_settings"})

    async def get_context_usage(self) -> dict[str, Any]:
        """Get a breakdown of current context window usage by category."""
        return await self._send_control_request({"subtype": "get_context_usage"})

    async def mcp_authenticate(self, server_name: str) -> dict[str, Any]:
        """Trigger OAuth authentication for an MCP server."""
        req = {"subtype": "mcp_authenticate", "serverName": server_name}
        return await self._send_control_request(req)

    async def mcp_clear_auth(self, server_name: str) -> dict[str, Any]:
        """Clear OAuth credentials for an MCP server."""
        req = {"subtype": "mcp_clear_auth", "serverName": server_name}
        return await self._send_control_request(req)

    async def mcp_oauth_callback_url(self, server_name: str, callback_url: str) -> dict[str, Any]:
        """Provide an OAuth redirect callback URL to complete an MCP server OAuth flow."""
        req = {
            "subtype": "mcp_oauth_callback_url",
            "serverName": server_name,
            "callbackUrl": callback_url,
        }
        return await self._send_control_request(req)

    async def claude_oauth_wait_for_completion(self) -> ClaudeOAuthWaitForCompletionResponse:
        """Wait for an in-progress Claude OAuth flow to complete.

        Returns account details (email, organization, subscriptionType, etc.)
        once the OAuth flow finishes.
        """
        data = await self._send_control_request({"subtype": "claude_oauth_wait_for_completion"})
        return ClaudeOAuthWaitForCompletionResponse.model_validate(data)

    async def side_question(self, question: str) -> SideQuestionResponse:
        """Send a side question to the model using the current conversation context.

        The model answers the question without it being added to the main
        conversation history.

        Args:
            question: The question to ask the model.
        """
        data = await self._send_control_request({"subtype": "side_question", "question": question})
        return SideQuestionResponse.model_validate(data)

    async def rewind_files(self, user_message_id: str) -> dict[str, Any]:
        """Rewind tracked files to their state at a specific user message.

        Requires file checkpointing to be enabled via the `enable_file_checkpointing` option.

        Args:
            user_message_id: UUID of the user message to rewind to
        """
        req = {"subtype": "rewind_files", "user_message_id": user_message_id}
        return await self._send_control_request(req)

    async def seed_read_state(self, path: str, mtime: int) -> None:
        """Seed the CLI's readFileState cache with a path+mtime entry.

        Use when the client observed a Read that has since been removed from context
        (e.g. by snip), so a subsequent Edit won't fail "file not read yet".
        If the file changed on disk since the given mtime, the seed is skipped
        and Edit will correctly require a fresh Read.

        Args:
            path: Path to the file that was previously Read
            mtime: File mtime (floored ms) at the time of the observed Read
        """
        req = {"subtype": "seed_read_state", "path": path, "mtime": mtime}
        await self._send_control_request(req)

    async def receive_messages(self) -> AsyncGenerator[dict[str, Any]]:
        """Receive SDK messages (not control messages)."""
        async for message in self._message_receive:
            # Check for special messages
            match message.get("type"):
                case "end":
                    break
                case "error":
                    raise ClaudeSDKError(message.get("error", "Unknown error"))
                case _:
                    yield message

    async def close(self) -> None:
        """Close the query and transport."""
        if self._closed:
            return
        self._closed = True

        for task in list(self._child_tasks):
            task.cancel()
        if self._read_task is not None and not self._read_task.done():
            self._read_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._read_task
        self._read_task = None

        await self.transport.close()
        # clean up
        self.hook_callbacks.clear()
        self.pending_control_responses.clear()
        self.pending_control_results.clear()
        with suppress(Exception):
            await self._message_send.aclose()
        with suppress(Exception):
            await self._message_receive.aclose()

    # Make Query an async context manager
    async def __aenter__(self) -> Self:
        """Enter async context - starts reading messages."""
        await self.start()
        return self

    async def __aexit__(self, *args: object) -> bool:
        """Exit async context - closes the query."""
        await self.close()
        return False

    # Make Query an async iterator
    def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        """Return async iterator for messages."""
        return self.receive_messages()

    async def __anext__(self) -> dict[str, Any]:
        """Get next message."""
        async for message in self.receive_messages():
            return message
        raise StopAsyncIteration

    async def write_json(self, data: Any) -> None:
        """Write a JSON-serializable object to the transport."""
        await self.transport.write(anyenv.dump_json(data) + "\n")
