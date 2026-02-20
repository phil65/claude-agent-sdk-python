"""Query class for handling bidirectional control protocol."""

from __future__ import annotations

from contextlib import suppress
import logging
import math
import os
from typing import TYPE_CHECKING, Any

import anyenv
import anyio
from pydantic import BaseModel

from clawd_code_sdk.models import (
    ControlResponse,
    PermissionResultAllow,
    SDKControlInitializeRequest,
    SDKControlInterruptRequest,
    SDKControlMcpMessageRequest,
    SDKControlPermissionRequest,
    SDKControlResponse,
    SDKControlRewindFilesRequest,
    SDKControlSetPermissionModeRequest,
    SDKControlStopTaskRequest,
    SDKHookCallbackRequest,
    ToolPermissionContext,
    parse_control_request,
)
from clawd_code_sdk.models.mcp import JSONRPCError, JSONRPCErrorResponse, JSONRPCResultResponse
from clawd_code_sdk.models.server_info import ClaudeCodeServerInfo


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterable, AsyncIterator, Callable, Iterator

    from anyio.abc import CancelScope, TaskGroup
    from mcp.server import Server as McpServer
    from mcp.types import ContentBlock

    from clawd_code_sdk._internal.transport import Transport
    from clawd_code_sdk.models import ControlRequestUnion, PermissionMode
    from clawd_code_sdk.models.agents import AgentDefinition
    from clawd_code_sdk.models.hooks import HookEvent, HookMatcher
    from clawd_code_sdk.models.mcp import JSONRPCMessage, JSONRPCResponse, RequestId
    from clawd_code_sdk.models.messages import UserPromptMessage
    from clawd_code_sdk.models.permissions import CanUseTool, PermissionResult

logger = logging.getLogger(__name__)


def get_jsonrpc_request_id(message: JSONRPCMessage) -> RequestId:
    """Extract the request ID from a JSON-RPC message.

    Falls back to 0 if the message has no id (e.g. notifications).
    """
    raw_id = message.get("id")
    if isinstance(raw_id, str | int):
        return raw_id
    return 0


def convert_hooks_to_internal_format(
    hooks: dict[HookEvent, list[HookMatcher]],
) -> dict[str, list[dict[str, Any]]]:
    """Convert HookMatcher format to internal Query format."""
    internal_hooks: dict[str, list[dict[str, Any]]] = {}
    for event, matchers in hooks.items():
        internal_hooks[event] = []
        for matcher in matchers:
            # Convert HookMatcher to internal dict format
            internal_matcher: dict[str, Any] = {"matcher": matcher.matcher, "hooks": matcher.hooks}
            if matcher.timeout is not None:
                internal_matcher["timeout"] = matcher.timeout
            internal_hooks[event].append(internal_matcher)
    return internal_hooks


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
        hooks: dict[HookEvent, list[HookMatcher]] | None = None,
        sdk_mcp_servers: dict[str, McpServer] | None = None,
        initialize_timeout: float = 60.0,
        agents: dict[str, AgentDefinition] | None = None,
        system_prompt: str | None = None,
        append_system_prompt: str | None = None,
        json_schema: dict[str, Any] | None = None,
        prompt_suggestions: bool | None = None,
    ):
        """Initialize Query with transport and callbacks.

        Args:
            transport: Low-level transport for I/O
            can_use_tool: Optional callback for tool permission requests
            hooks: Optional hook configurations
            sdk_mcp_servers: Optional SDK MCP server instances
            initialize_timeout: Timeout in seconds for the initialize request
            agents: Optional agent definitions to send via initialize
            system_prompt: Optional system prompt to send via initialize
            append_system_prompt: Optional text to append to preset system prompt
            json_schema: Optional JSON schema for structured output
            prompt_suggestions: Optional flag to enable prompt suggestions
        """
        self._initialize_timeout = initialize_timeout
        self.transport = transport
        self.can_use_tool = can_use_tool
        self.hooks = convert_hooks_to_internal_format(hooks) if hooks else {}
        self.sdk_mcp_servers = sdk_mcp_servers or {}
        self._agents = {name: agent_def.to_dict() for name, agent_def in (agents or {}).items()}
        self._system_prompt = system_prompt
        self._append_system_prompt = append_system_prompt
        self._json_schema = json_schema
        self._prompt_suggestions = prompt_suggestions
        # Control protocol state
        self.pending_control_responses: dict[str, anyio.Event] = {}
        self.pending_control_results: dict[str, dict[str, Any] | Exception] = {}
        self.hook_callbacks: dict[str, Callable[..., Any]] = {}
        self.next_callback_id = 0
        self._request_counter = 0
        # Message stream
        self._message_send, self._message_receive = anyio.create_memory_object_stream[
            dict[str, Any]
        ](max_buffer_size=math.inf)
        self._tg: TaskGroup | None = None
        self._initialized = False
        self._closed = False
        self._initialization_result: ClaudeCodeServerInfo | None = None
        # Track first result for proper stream closure with SDK MCP servers
        self._first_result_event = anyio.Event()
        self._stream_close_timeout = (
            float(os.environ.get("CLAUDE_CODE_STREAM_CLOSE_TIMEOUT", "60000")) / 1000.0
        )  # Convert ms to seconds
        # Cancel scope for the reader task - can be cancelled from any task context
        # This fixes the RuntimeError when async generator cleanup happens in a different task
        self._reader_cancel_scope: CancelScope | None = None
        self._reader_task_started = anyio.Event()
        # Track whether we entered the task group in this task
        # Used to determine if we can safely call __aexit__()
        self._tg_entered_in_current_task = False

    async def initialize(self) -> ClaudeCodeServerInfo:
        """Initialize control protocol.

        Returns:
            Parsed server info with supported commands and capabilities
        """
        # Build hooks configuration for initialization
        hooks_config: dict[str, Any] = {}
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

        # Send initialize request
        request: dict[str, Any] = {"subtype": "initialize", "hooks": hooks_config or None}
        if self._agents:
            request["agents"] = self._agents
        if self.sdk_mcp_servers:
            request["sdkMcpServers"] = list(self.sdk_mcp_servers.keys())
        if self._system_prompt is not None:
            request["systemPrompt"] = self._system_prompt
        if self._append_system_prompt is not None:
            request["appendSystemPrompt"] = self._append_system_prompt
        if self._json_schema is not None:
            request["jsonSchema"] = self._json_schema
        if self._prompt_suggestions is not None:
            request["promptSuggestions"] = self._prompt_suggestions

        # Use longer timeout for initialize since MCP servers may take time to start
        response = await self._send_control_request(request, timeout=self._initialize_timeout)
        self._initialized = True
        self._initialization_result = ClaudeCodeServerInfo.model_validate(response)
        return self._initialization_result

    async def start(self) -> None:
        """Start reading messages from transport.

        This method starts background tasks for reading messages. The task lifecycle
        is managed using a CancelScope that can be safely cancelled from any async
        task context, avoiding the RuntimeError that occurs when task group
        __aexit__() is called from a different task than __aenter__().
        """
        if self._tg is None:
            # Create a task group for spawning background tasks
            self._tg = anyio.create_task_group()
            await self._tg.__aenter__()
            self._tg_entered_in_current_task = True
            # Start the reader with its own cancel scope that can be cancelled safely
            self._tg.start_soon(self._read_messages_with_cancel_scope)

    async def _read_messages_with_cancel_scope(self) -> None:
        """Wrapper for _read_messages that sets up a cancellable scope.

        This wrapper creates a CancelScope that can be cancelled from any task
        context, solving the issue where async generator cleanup happens in a
        different task than where the task group was entered.
        """
        self._reader_cancel_scope = anyio.CancelScope()
        self._reader_task_started.set()
        with self._reader_cancel_scope:
            await self._read_messages()

    async def _read_messages(self) -> None:
        """Read messages from transport and route them."""
        try:
            async for message in self.transport.read_messages():
                if self._closed:
                    break

                match message.get("type"):
                    case "control_response":
                        response = message.get("response", {})
                        request_id = response.get("request_id")
                        if request_id in self.pending_control_responses:
                            event = self.pending_control_responses[request_id]
                            if response.get("subtype") == "error":
                                msg = response.get("error", "Unknown error")
                                self.pending_control_results[request_id] = Exception(msg)
                            else:
                                self.pending_control_results[request_id] = response
                            event.set()

                    case "control_request":
                        if tg := self._tg:
                            tg.start_soon(
                                self._handle_control_request,
                                message["request_id"],
                                parse_control_request(message["request"]),
                            )
                    case "control_cancel_request":  # TODO: Implement cancellation support
                        pass

                    case "result":  # Track results for proper stream closure
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
            logger.error(f"Fatal error in message reader: {e}")
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
                    response_data = result.to_dict()
                case SDKHookCallbackRequest() as req:
                    response_data = await self._handle_hook_callback(req)
                case SDKControlMcpMessageRequest(server_name=server_name, message=message):
                    mcp_resp = await self._handle_sdk_mcp_request(server_name, message)
                    response_data = {"mcp_response": mcp_resp}
                case SDKControlInterruptRequest():
                    pass  # No response data needed
                case (
                    SDKControlInitializeRequest()
                    | SDKControlSetPermissionModeRequest()
                    | SDKControlRewindFilesRequest()
                    | SDKControlStopTaskRequest()
                ):
                    pass  # Handled elsewhere
            dct = ControlResponse(subtype="success", request_id=request_id, response=response_data)
            success_response = SDKControlResponse(type="control_response", response=dct)
            await self.transport.write(anyenv.dump_json(success_response) + "\n")

        except Exception as e:
            response = {"subtype": "error", "request_id": request_id, "error": str(e)}
            error_response = SDKControlResponse(type="control_response", response=response)
            await self.transport.write(anyenv.dump_json(error_response) + "\n")

    async def _handle_permission_request(
        self, req: SDKControlPermissionRequest
    ) -> PermissionResult:
        """Handle a tool permission request."""
        if not self.can_use_tool:
            raise RuntimeError("canUseTool callback is not provided")

        context = ToolPermissionContext(
            tool_use_id=req.tool_use_id,
            signal=None,
            suggestions=req.permission_suggestions or [],
            blocked_path=req.blocked_path,
        )

        result = await self.can_use_tool(req.tool_name, req.input, context)
        if isinstance(result, PermissionResultAllow) and result.updated_input is None:
            result.updated_input = req.input
        return result

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
        await self.transport.write(anyenv.dump_json(control_request) + "\n")
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
            raise Exception(f"Control request timeout: {request.get('subtype')}") from e

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
            return {"jsonrpc": "2.0", "id": get_jsonrpc_request_id(message), "error": dct}

        server = self.sdk_mcp_servers[server_name]
        return await process_mcp_request(message, server)

    async def get_mcp_status(self) -> dict[str, Any]:
        """Get current MCP server connection status."""
        return await self._send_control_request({"subtype": "mcp_status"})

    async def set_mcp_servers(self, servers: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """Add, replace, or remove MCP servers dynamically."""
        return await self._send_control_request({"subtype": "mcp_set_servers", "servers": servers})

    async def mcp_reconnect(self, server_name: str) -> None:
        """Reconnect to an MCP server.

        Args:
            server_name: Name of the MCP server to reconnect
        """
        await self._send_control_request({"subtype": "mcp_reconnect", "serverName": server_name})

    async def mcp_toggle(self, server_name: str, *, enabled: bool) -> None:
        """Enable or disable an MCP server."""
        await self._send_control_request(
            {"subtype": "mcp_toggle", "serverName": server_name, "enabled": enabled}
        )

    async def set_max_thinking_tokens(self, max_thinking_tokens: int) -> None:
        """Set the maximum number of thinking tokens."""
        await self._send_control_request(
            {
                "subtype": "set_max_thinking_tokens",
                "max_thinking_tokens": max_thinking_tokens,
            }
        )

    async def interrupt(self) -> None:
        """Send interrupt control request."""
        await self._send_control_request({"subtype": "interrupt"})

    async def set_permission_mode(self, mode: PermissionMode) -> None:
        """Change permission mode."""
        await self._send_control_request({"subtype": "set_permission_mode", "mode": mode})

    async def set_model(self, model: str | None) -> None:
        """Change the AI model."""
        await self._send_control_request({"subtype": "set_model", "model": model})

    async def stop_task(self, task_id: str) -> None:
        """Stop a running task.

        Args:
            task_id: ID of the task to stop
        """
        await self._send_control_request({"subtype": "stop_task", "task_id": task_id})

    async def rewind_files(self, user_message_id: str) -> None:
        """Rewind tracked files to their state at a specific user message.

        Requires file checkpointing to be enabled via the `enable_file_checkpointing` option.

        Args:
            user_message_id: UUID of the user message to rewind to
        """
        await self._send_control_request(
            {"subtype": "rewind_files", "user_message_id": user_message_id}
        )

    async def stream_input(self, stream: AsyncIterable[UserPromptMessage]) -> None:
        """Stream input messages to transport.

        If SDK MCP servers or hooks are present, waits for the first result
        before closing stdin to allow bidirectional control protocol communication.
        """
        try:
            async for message in stream:
                if self._closed:
                    break
                await self.transport.write(anyenv.dump_json(message) + "\n")

            # If we have SDK MCP servers or hooks that need bidirectional communication,
            # wait for first result before closing the channel
            has_hooks = bool(self.hooks)
            if self.sdk_mcp_servers or has_hooks:
                logger.debug(
                    f"Waiting for first result before closing stdin "
                    f"(sdk_mcp_servers={len(self.sdk_mcp_servers)}, has_hooks={has_hooks})"
                )
                try:
                    with anyio.move_on_after(self._stream_close_timeout):
                        await self._first_result_event.wait()
                        logger.debug("Received first result, closing input stream")
                except Exception:
                    logger.debug("Timed out waiting for first result, closing input stream")

            # After all messages sent (and result received if needed), end input
            await self.transport.end_input()
        except Exception as e:
            logger.debug(f"Error streaming input: {e}")

    async def receive_messages(self) -> AsyncGenerator[dict[str, Any]]:
        """Receive SDK messages (not control messages)."""
        async for message in self._message_receive:
            # Check for special messages
            match message.get("type"):
                case "end":
                    break
                case "error":
                    raise Exception(message.get("error", "Unknown error"))
                case _:
                    yield message

    async def close(self) -> None:
        """Close the query and transport.

        This method safely cleans up resources, handling the case where cleanup
        happens in a different async task context than where start() was called.
        This commonly occurs during async generator cleanup (e.g., when breaking
        out of an `async for` loop or when asyncio.run() shuts down).

        The fix uses two mechanisms:
        1. A CancelScope for the reader task that can be cancelled from any context
        2. Suppressing the RuntimeError that occurs when task group __aexit__()
           is called from a different task than __aenter__()
        """
        if self._closed:
            return
        self._closed = True

        # Cancel the reader task via its cancel scope (safe from any task context)
        if self._reader_cancel_scope is not None:
            self._reader_cancel_scope.cancel()

        # Handle task group cleanup
        if self._tg is not None:
            # Always cancel the task group's scope to stop any running tasks
            self._tg.cancel_scope.cancel()

            # Try to properly exit the task group, but handle the case where
            # we're in a different task context than where __aenter__() was called
            try:
                with suppress(anyio.get_cancelled_exc_class()):
                    await self._tg.__aexit__(None, None, None)
            except RuntimeError as e:
                # Handle "Attempted to exit cancel scope in a different task"
                # This happens during async generator cleanup when Python's GC
                # runs the finally block in a different task context.
                if "different task" in str(e):
                    logger.debug(
                        "Task group cleanup skipped due to cross-task context "
                        "(this is expected during async generator cleanup)"
                    )
                else:
                    raise
            finally:
                self._tg = None
                self._tg_entered_in_current_task = False

        await self.transport.close()

    # Make Query an async context manager
    async def __aenter__(self) -> Query:
        """Enter async context - starts reading messages."""
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool:
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


async def process_mcp_request(message: JSONRPCMessage, server: McpServer) -> JSONRPCResponse:
    from mcp.types import CallToolRequest, CallToolRequestParams, CallToolResult, ListToolsRequest

    method = message.get("method")
    assert isinstance(method, str)
    msg_id = get_jsonrpc_request_id(message)
    try:
        # TODO: Python MCP SDK lacks the Transport abstraction that TypeScript has.
        # TypeScript: server.connect(transport) allows custom transports
        # Python: server.run(read_stream, write_stream) requires actual streams
        #
        # This forces us to manually route methods. When Python MCP adds Transport
        # support, we can refactor to match the TypeScript approach.
        match method:
            case "initialize":
                # Handle MCP initialization - hardcoded for tools only, no listChanged
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},  # Tools capability without listChanged
                    "serverInfo": {"name": server.name, "version": server.version or "1.0.0"},
                }
                return JSONRPCResultResponse(jsonrpc="2.0", id=msg_id, result=result)

            case "tools/list" if handler := server.request_handlers.get(ListToolsRequest):
                request = ListToolsRequest()
                result = await handler(request)
                # Convert MCP result to JSONRPC response
                tools_data = []
                for tool in result.root.tools:  # type: ignore[union-attr]
                    tool_data: dict[str, Any] = {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": (
                            tool.inputSchema.model_dump()
                            if isinstance(tool.inputSchema, BaseModel)
                            else tool.inputSchema
                        ),
                    }
                    if annots := tool.annotations:
                        tool_data["annotations"] = annots.model_dump(exclude_none=True)
                    tools_data.append(tool_data)
                return JSONRPCResultResponse(jsonrpc="2.0", id=msg_id, result={"tools": tools_data})

            case "tools/call" if handler := server.request_handlers.get(CallToolRequest):
                params = message.get("params", {})
                assert isinstance(params, dict)
                call_params = CallToolRequestParams(**params)  # pyright: ignore[reportArgumentType]
                call_request = CallToolRequest(params=call_params)
                result = await handler(call_request)
                # Convert MCP result to JSONRPC response
                assert isinstance(result.root, CallToolResult)
                content = list(process_content_blocks(result.root.content))
                response_data: dict[str, Any] = {"content": content}
                if result.root.isError:
                    response_data["is_error"] = True
                return JSONRPCResultResponse(jsonrpc="2.0", id=msg_id, result=response_data)
            case "notifications/initialized":
                # Handle initialized notification - just acknowledge it
                return JSONRPCResultResponse(jsonrpc="2.0", id=msg_id, result={})
            # Add more methods here as MCP SDK adds them (resources, prompts, etc.)
            # This is the limitation Ashwin pointed out - we have to manually update
            case _:
                error = JSONRPCError(code=-32601, message=f"Method '{method}' not found")
                return JSONRPCErrorResponse(jsonrpc="2.0", id=msg_id, error=error)

    except Exception as e:
        error = JSONRPCError(code=-32603, message=str(e))
        return JSONRPCErrorResponse(jsonrpc="2.0", id=msg_id, error=error)


def process_content_blocks(content: list[ContentBlock]) -> Iterator[dict[str, Any]]:
    from mcp.types import (
        AudioContent,
        BlobResourceContents,
        EmbeddedResource,
        ImageContent,
        ResourceLink,
        TextContent,
        TextResourceContents,
    )

    for item in content:
        match item:
            case TextContent(text=text):
                yield {"type": "text", "text": text}
            case ImageContent(data=data, mimeType=mime) | AudioContent(data=data, mimeType=mime):
                yield {"type": "image", "data": data, "mimeType": mime}
            case ResourceLink():
                pass
            case EmbeddedResource(
                resource=BlobResourceContents(mimeType=mime, uri=uri)
                | TextResourceContents(mimeType=mime, uri=uri) as resource
            ):
                # EmbeddedResource - check if it's a document (PDF, etc.)
                uri_str = str(uri)
                if uri_str.startswith("document://") or mime == "application/pdf":
                    # Convert EmbeddedResource to Anthropic document format
                    typ = (
                        uri_str.removeprefix("document://")
                        if uri_str.startswith("document://")
                        else "base64"
                    )
                    data = resource.blob if isinstance(resource, BlobResourceContents) else ""
                    dct = {"type": typ, "media_type": mime, "data": data}
                    yield {"type": "document", "source": dct}
