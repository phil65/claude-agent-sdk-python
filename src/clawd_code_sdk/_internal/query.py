"""Query class for handling bidirectional control protocol."""

from __future__ import annotations

import asyncio
from collections import deque
from contextlib import suppress
from dataclasses import replace
import logging
import os
from typing import TYPE_CHECKING, Any, Self, assert_never, cast

import anyenv
import anyio
from pydantic import ValidationError

from clawd_code_sdk._errors import (
    ClaudeSDKError,
    CLIConnectionError,
    ControlRequestError,
    ControlRequestTimeoutError,
    MessageParseError,
    ProcessError,
    ResultError,
    error_result_text,
)
from clawd_code_sdk._internal.sdk_mcp_bridge import SdkMcpBridge
from clawd_code_sdk._internal.transport.subprocess_cli import SubprocessCLITransport
from clawd_code_sdk.mcp_utils import restore_document_blocks
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
from clawd_code_sdk.models.control import SDKControlRequestUserDialogRequest


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterator, Callable

    from mcp.server import Server as McpServer

    from clawd_code_sdk._internal.transport import Transport
    from clawd_code_sdk.models import (
        CanUseTool,
        ClaudeAgentOptions,
        HookCallback,
        HookEvent,
        HookMatcher,
        JSONRPCMessage,
        JSONRPCResponse,
        OnElicitation,
        OnUserQuestion,
        OutgoingControlRequest,
        PermissionResult,
        RequestId,
        SDKControlRequest,
    )
    from clawd_code_sdk.models.control import SdkMcpServerManifest

logger = logging.getLogger(__name__)

_warned_control_subtypes: set[str] = set()

MANIFEST_CAPTURE_TIMEOUT = 10.0
"""Seconds an in-process MCP server gets to answer the handshake captured for the CLI."""

MAX_BUFFERED_MESSAGES = 1000
"""Messages read ahead of the consumer before the reader stops reading (back-pressure)."""


class _MessageBuffer:
    """Messages from the reader to the consumer, bounded for back-pressure.

    At the bound, ``put`` waits for the consumer, so the CLI's output piles up in its
    pipe and the CLI blocks on write instead of the SDK growing memory. Exception: while
    one of our control requests awaits its response (``may_overflow``), the reader keeps
    reading past the bound, since the response comes through the same stream and the
    caller may well be the consumer. The excess is drained once the consumer goes on.
    """

    def __init__(self, bound: int, may_overflow: Callable[[], bool]) -> None:
        self._items: deque[dict[str, Any]] = deque()
        self._bound = bound
        self._may_overflow = may_overflow
        self._space = asyncio.Event()
        self._data = asyncio.Event()
        self._closed = False

    def __len__(self) -> int:
        return len(self._items)

    async def put(self, message: dict[str, Any], *, force: bool = False) -> None:
        """Append ``message``, waiting while the buffer is full (unless ``force``)."""
        if self._closed:
            return
        while (
            not force
            and not self._closed
            and len(self._items) >= self._bound
            and not self._may_overflow()
        ):
            self._space.clear()
            await self._space.wait()
        self._items.append(message)
        self._data.set()

    async def get(self) -> dict[str, Any] | None:
        """Next message, or None once the buffer is closed."""
        while not self._items:
            if self._closed:
                return None
            self._data.clear()
            await self._data.wait()
        message = self._items.popleft()
        self._space.set()
        return message

    def wake(self) -> None:
        """Re-check the bound (a control request started: the reader may overflow)."""
        self._space.set()

    def close(self) -> None:
        """Drop what's buffered; ``get`` returns None from now on."""
        self._closed = True
        self._items.clear()
        self._space.set()
        self._data.set()


async def _handshake(name: str, bridge: SdkMcpBridge) -> SdkMcpServerManifest | None:
    """``name``'s handshake results (initialize, first tools/list), or None if it errs."""
    from mcp.types import LATEST_PROTOCOL_VERSION

    from clawd_code_sdk._version import __version__

    params = {
        "protocolVersion": LATEST_PROTOCOL_VERSION,
        "capabilities": {},
        "clientInfo": {"name": "clawd-code-sdk", "version": __version__},
    }
    request = {"jsonrpc": "2.0", "id": f"manifest:{name}:initialize", "method": "initialize"}
    answer = await bridge.handle({**request, "params": params})
    if answer is None or not isinstance(result := answer.get("result"), dict):
        logger.warning("SDK MCP server %r answered initialize with an error: %s", name, answer)
        return None
    await bridge.handle({"jsonrpc": "2.0", "method": "notifications/initialized"})
    manifest: SdkMcpServerManifest = {"initializeResult": result}
    capabilities = result.get("capabilities")
    if isinstance(capabilities, dict) and capabilities.get("tools") is not None:
        listing = {"jsonrpc": "2.0", "id": f"manifest:{name}:tools-list", "method": "tools/list"}
        listed = await bridge.handle(listing)
        tools = listed.get("result") if listed is not None else None
        if isinstance(tools, dict) and tools.get("nextCursor") is None:  # Not paginated
            manifest["toolsListResult"] = tools
    return manifest


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
        max_buffered_messages: int = MAX_BUFFERED_MESSAGES,
    ) -> None:
        """Initialize Query with transport and callbacks.

        Args:
            transport: Low-level transport for I/O
            can_use_tool: Optional callback for tool permission requests
            on_user_question: Optional callback for AskUserQuestion elicitation
            on_elicitation: Optional callback for MCP elicitation requests
            hooks: Optional hook configurations
            sdk_mcp_servers: Optional SDK MCP server instances
            max_buffered_messages: Messages read ahead of a slow consumer before the
                reader waits for it (see `_MessageBuffer`)
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
        # One bridge per SDK server for the lifetime of this Query (mcp 1.x and 2.x)
        self._sdk_mcp_bridges = {
            name: SdkMcpBridge(name, server) for name, server in self.sdk_mcp_servers.items()
        }
        # Control protocol state
        self.pending_control_responses: dict[str, anyio.Event] = {}
        self.pending_control_results: dict[str, dict[str, Any] | Exception] = {}
        self.hook_callbacks: dict[str, HookCallback] = {}
        self.next_callback_id = 0
        self._request_counter = 0
        # Message stream (bounded; control responses are routed by the reader itself)
        self._messages = _MessageBuffer(
            max_buffered_messages, may_overflow=lambda: bool(self.pending_control_responses)
        )
        self._read_task: asyncio.Task[None] | None = None
        self._child_tasks: set[asyncio.Task[Any]] = set()
        self._inflight_requests: dict[str, asyncio.Task[Any]] = {}
        self._closed = False
        # Set when the message reader ends: later control requests fail with it at once.
        self._reader_error: Exception | None = None
        # Track first result for proper stream closure with SDK MCP servers
        self._first_result_event = anyio.Event()
        # The last result frame if it had is_error and nothing but the post-turn
        # session_state_changed marker followed it. A ProcessError while this is
        # set is the CLI's deliberate non-zero exit after that error result.
        self._last_error_result: dict[str, Any] | None = None

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
                if matcher.get("on_failure") is not None:
                    matcher_cfg["onFailure"] = matcher.get("on_failure")
                hooks_config[event].append(matcher_cfg)
        return hooks_config or None

    async def capture_sdk_mcp_manifests(
        self, timeout: float = MANIFEST_CAPTURE_TIMEOUT
    ) -> dict[str, SdkMcpServerManifest] | None:
        """Handshake the in-process MCP servers here, for the initialize request.

        Each server gets ``initialize`` (no client capabilities), ``notifications/initialized``
        and, if it has tools, ``tools/list``; the results go to the CLI verbatim
        (``sdkMcpServerManifests``), which then connects the servers without control round
        trips. The bridges' sessions stay up, so the CLI's ``mcp_message`` traffic goes on
        as before (also a handshake of its own). A server that fails or takes longer than
        ``timeout`` seconds is left out: the CLI handshakes it over the control channel.
        """
        manifests: dict[str, SdkMcpServerManifest] = {}

        async def capture(name: str, bridge: SdkMcpBridge) -> None:
            try:
                with anyio.fail_after(timeout):
                    if (manifest := await _handshake(name, bridge)) is not None:
                        manifests[name] = manifest
            except Exception as exc:
                logger.warning("SDK MCP server %r: no manifest (%s), CLI handshakes it", name, exc)

        async with anyio.create_task_group() as tg:
            for name, bridge in self._sdk_mcp_bridges.items():
                tg.start_soon(capture, name, bridge)
        return manifests or None

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
                        # Validated in the handler: a request the SDK can't parse is
                        # answered with an error instead of ending the reader.
                        coro = self._handle_control_request(req_id, request)
                        self._spawn_control_request_handler(req_id, coro)
                    case {"type": "control_cancel_request"}:
                        if (cancel_id := message.get("request_id")) and (
                            inflight := self._inflight_requests.pop(cancel_id, None)
                        ):
                            inflight.cancel()
                    case {"type": "result"}:
                        self._first_result_event.set()
                        self._last_error_result = message if message.get("is_error") else None
                        await self._messages.put(message)
                    case {"type": "system", "subtype": "session_state_changed"}:
                        await self._messages.put(message)
                    case _:  # Regular SDK messages go to the stream
                        # The conversation moved on: a ProcessError now is a fresh
                        # crash, not the exit that follows an error result.
                        self._last_error_result = None
                        await self._messages.put(message)

        except anyio.get_cancelled_exc_class():
            # Task was cancelled - this is expected behavior
            logger.debug("Read task cancelled")
            raise  # Re-raise to properly handle cancellation
        except Exception as e:
            # After an is_error result the CLI exits non-zero on purpose. The
            # trailing ProcessError says nothing beyond the exit code, so replace
            # it with a ResultError carrying what the CLI already reported.
            pending_error: Exception = e
            if isinstance(e, ProcessError) and self._last_error_result is not None:
                text = error_result_text(self._last_error_result)
                pending_error = ResultError(
                    f"Claude Code returned an error result: {text}",
                    data=self._last_error_result,
                    exit_code=e.exit_code,
                )
                pending_error.__cause__ = e
                logger.debug("Replacing ProcessError (exit code %s) with ResultError", e.exit_code)
            else:
                logger.exception("Fatal error in message reader")
            # This includes an `initialize` still in flight when the CLI reports
            # an error result during startup (e.g. a refused resume).
            self._fail_control_requests(pending_error)
            # Put the typed error in the stream so iterators re-raise it as-is
            error_msg = {"type": "error", "error": str(pending_error), "exception": pending_error}
            await self._messages.put(error_msg, force=True)
        finally:
            # Also after a clean end of stdout: nothing will answer anymore.
            self._fail_control_requests(CLIConnectionError("Claude Code CLI output ended"))
            # Always signal end of stream
            await self._messages.put({"type": "end"}, force=True)

    def _fail_control_requests(self, error: Exception) -> None:
        """Fail pending and later control requests fast instead of letting them time out."""
        if self._reader_error is None:
            self._reader_error = error
        for request_id, event in list(self.pending_control_responses.items()):
            if request_id not in self.pending_control_results:
                self.pending_control_results[request_id] = error
                event.set()

    async def _handle_control_request(self, request_id: str, request: Any) -> None:
        """Handle incoming control request from CLI."""
        try:
            request_data = incoming_control_request_adapter.validate_python(request)
        except ValidationError as e:
            await self._reject_control_request(request_id, request, e)
            return
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
                    # JSON-RPC notifications get no reply, but the control
                    # request that carried one still expects an ack.
                    ack = {"jsonrpc": "2.0", "result": {}}
                    response_data = {"mcp_response": mcp_resp if mcp_resp is not None else ack}
                case SDKControlElicitationRequest() as req:
                    response_data = await self._handle_elicitation_request(req)
                case SDKControlRequestUserDialogRequest(dialog_kind=kind):
                    # The SDK declares no supportedDialogKinds, so the CLI shouldn't send
                    # one. The spec: never answer an undeclared kind (the CLI withdraws it).
                    logger.warning("Ignoring request_user_dialog %r: no dialog support", kind)
                    return
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

    async def _reject_control_request(
        self, request_id: str, request: Any, error: ValidationError
    ) -> None:
        """Answer a control request the SDK doesn't model (or whose shape changed)."""
        from clawd_code_sdk.client import strict_messages

        subtype = request.get("subtype") if isinstance(request, dict) else None
        text = f"unsupported control request: {subtype}"
        response = ControlErrorResponse(subtype="error", request_id=request_id, error=text)
        await self.write_json(SDKControlResponse(type="control_response", response=response))
        if strict_messages():
            exc = MessageParseError(f"Invalid control request {subtype!r}: {error}", request)
            error_msg = {"type": "error", "error": str(exc), "exception": exc}
            await self._messages.put(error_msg, force=True)
        elif str(subtype) not in _warned_control_subtypes:
            _warned_control_subtypes.add(str(subtype))
            logger.warning("Answered an unsupported control request %r: %s", subtype, error)

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
        self, request: OutgoingControlRequest, timeout: float | None = 60.0
    ) -> dict[str, Any]:
        """Send control request to CLI and wait for response.

        A request that times out or whose caller is cancelled is withdrawn with a
        ``control_cancel_request``, so the CLI can stop the work.

        Args:
            request: The control request to send
            timeout: Seconds to wait for the response (default 60s; None waits forever)
        """
        if self._reader_error is not None:
            raise self._reader_error
        # Generate unique request ID
        self._request_counter += 1
        request_id = f"req_{self._request_counter}_{os.urandom(4).hex()}"
        # Create event for response
        event = anyio.Event()
        self.pending_control_responses[request_id] = event
        self._messages.wake()  # A reader waiting at the bound must read on to the response
        # Build and send request
        control_request = {
            "type": "control_request",
            "request_id": request_id,
            "request": request.model_dump(by_alias=True, exclude_none=True),
        }
        sent = answered = False
        try:
            await self.write_json(control_request)
            sent = True
            with anyio.fail_after(timeout):
                await event.wait()
            answered = True
            result = self.pending_control_results[request_id]
            if isinstance(result, Exception):
                raise result
            response_data = result.get("response", {})
            return response_data if isinstance(response_data, dict) else {}
        except TimeoutError as e:
            subtype = request.subtype
            raise ControlRequestTimeoutError(
                f"Control request timeout: {subtype}", subtype=subtype
            ) from e
        finally:
            self.pending_control_responses.pop(request_id, None)
            self.pending_control_results.pop(request_id, None)
            if sent and not answered and self._reader_error is None and not self._closed:
                self.spawn_task(self._withdraw_control_request(request_id))

    async def _withdraw_control_request(self, request_id: str) -> None:
        """Tell the CLI we no longer wait for ``request_id`` (best effort, no reply)."""
        with suppress(Exception):
            await self.write_json({"type": "control_cancel_request", "request_id": request_id})

    async def _handle_sdk_mcp_request(
        self, server_name: str, message: JSONRPCMessage
    ) -> JSONRPCResponse | None:
        """Route a JSON-RPC message from the CLI to the named SDK MCP server.

        Returns the JSON-RPC response for requests, or ``None`` when the
        message was a notification or response and there is nothing to send
        back. A message that cannot be delivered at all (unknown server,
        malformed JSON-RPC, a session that went away underneath it) is
        answered with a JSON-RPC error so the CLI's MCP client can fail that
        one request.

        Args:
            server_name: Name of the SDK MCP server
            message: The JSONRPC message
        """
        id_ = get_jsonrpc_request_id(message)
        if (bridge := self._sdk_mcp_bridges.get(server_name)) is None:
            error = JSONRPCError(code=-32601, message=f"Server '{server_name}' not found")
            return JSONRPCErrorResponse(jsonrpc="2.0", id=id_, error=error)
        try:
            response = await bridge.handle(dict(message))
        except Exception as e:
            error = JSONRPCError(code=-32603, message=str(e) or type(e).__name__)
            return JSONRPCErrorResponse(jsonrpc="2.0", id=id_, error=error)
        if response is None:
            return None
        return cast("JSONRPCResponse", restore_document_blocks(response))

    async def receive_messages(self) -> AsyncGenerator[dict[str, Any]]:
        """Receive SDK messages (not control messages)."""
        while (message := await self._messages.get()) is not None:
            # Check for special messages
            match message.get("type"):
                case "end":
                    break
                case "error":
                    if isinstance(exc := message.get("exception"), Exception):
                        raise exc
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

        for bridge in self._sdk_mcp_bridges.values():
            with suppress(Exception):
                await bridge.aclose()
        await self.transport.close()
        # clean up
        self.hook_callbacks.clear()
        self.pending_control_responses.clear()
        self.pending_control_results.clear()
        self._messages.close()

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

    async def write_json(
        self,
        data: SDKControlResponse | SDKControlRequest | dict[str, Any],
    ) -> None:
        """Write a JSON-serializable object to the transport."""
        await self.transport.write(anyenv.dump_json(data) + "\n")
