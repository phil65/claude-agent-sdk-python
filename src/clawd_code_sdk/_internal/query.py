"""Query class for handling bidirectional control protocol."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import replace
import logging
import math
import os
from typing import TYPE_CHECKING, Any, Self, assert_never, cast

import anyenv
import anyio

from clawd_code_sdk._errors import ClaudeSDKError, ControlRequestError, ControlRequestTimeoutError
from clawd_code_sdk._internal.transport.subprocess_cli import SubprocessCLITransport
from clawd_code_sdk.mcp_utils import process_mcp_request
from clawd_code_sdk.models import (
    AskUserQuestionInput,
    ControlErrorResponse,
    ControlResponse,
    JSONRPCError,
    JSONRPCErrorResponse,
    McpSdkServerConfigWithInstance,
    PermissionResultAllow,
    SDKControlElicitationRequest,
    SDKControlMcpMessageRequest,
    SDKControlPermissionRequest,
    SDKControlResponse,
    SDKHookCallbackRequest,
    ToolPermissionContext,
    incoming_control_request_adapter,
)


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterator

    from mcp.server import Server as McpServer

    from clawd_code_sdk._internal.transport import Transport
    from clawd_code_sdk.models import (
        CanUseTool,
        ClaudeAgentOptions,
        HookCallback,
        HookEvent,
        HookMatcher,
        IncomingControlRequest,
        JSONRPCMessage,
        JSONRPCResponse,
        OnElicitation,
        OnUserQuestion,
        OutgoingControlRequest,
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
    ):
        """Initialize Query with transport and callbacks.

        Args:
            transport: Low-level transport for I/O
            can_use_tool: Optional callback for tool permission requests
            on_user_question: Optional callback for AskUserQuestion elicitation
            on_elicitation: Optional callback for MCP elicitation requests
            hooks: Optional hook configurations
            sdk_mcp_servers: Optional SDK MCP server instances
        """
        self.transport = transport
        self.can_use_tool = can_use_tool
        self.on_user_question = on_user_question
        self.on_elicitation = on_elicitation
        self.hooks: dict[HookEvent, list[dict[str, Any]]] = {
            event: [m.model_dump(exclude_none=True) for m in matchers]
            for event, matchers in (hooks or {}).items()
        }
        self.sdk_mcp_servers = sdk_mcp_servers or {}
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
        # Track first result for proper stream closure with SDK MCP servers
        self._first_result_event = anyio.Event()

    @classmethod
    def from_options(cls, options: ClaudeAgentOptions, transport: Transport | None = None) -> Query:
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

        # Create Query to handle control protocol
        return cls(
            transport=transport or SubprocessCLITransport(options=options),
            can_use_tool=can_use_tool,  # ty:ignore[invalid-argument-type]
            on_user_question=options.on_user_question,
            on_elicitation=options.on_elicitation,
            hooks=hooks,
            sdk_mcp_servers=sdk_mcp_servers,
        )

    def build_hooks_config(self) -> dict[HookEvent, Any] | None:
        """Register hook callbacks and return the hooks config for initialization.

        Processes the raw hooks configuration, assigns callback IDs to each hook
        callback, and stores them in the internal dispatch table.

        Returns:
            Hooks configuration dict for the initialize request, or None if empty.
        """
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
        return hooks_config or None

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
                    case {"type": "control_request", "request_id": req_id, "request": request}:
                        req = incoming_control_request_adapter.validate_python(request)
                        coro = self._handle_control_request(req_id, req)
                        self._spawn_control_request_handler(req_id, coro)
                    case {"type": "control_cancel_request"}:
                        if (cancel_id := message.get("request_id")) and (
                            inflight := self._inflight_requests.pop(cancel_id, None)
                        ):
                            inflight.cancel()
                    case {"type": "result"}:
                        self._first_result_event.set()
                        await self._message_send.send(message)
                    case _:  # Regular SDK messages go to the stream
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
        request_data: IncomingControlRequest,
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
                case _ as unreachable:
                    assert_never(unreachable)
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
        self, request: OutgoingControlRequest, timeout: float = 60.0
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
        control_request = {
            "type": "control_request",
            "request_id": request_id,
            "request": request.model_dump(by_alias=True, exclude_none=True),
        }
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
            subtype = request.subtype
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
            id_ = get_jsonrpc_request_id(message)
            return JSONRPCErrorResponse(jsonrpc="2.0", id=id_, error=dct)
        server = self.sdk_mcp_servers[server_name]
        return await process_mcp_request(message, server)

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
