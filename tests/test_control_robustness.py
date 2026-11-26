"""Control protocol robustness: bad CLI requests, dead reader, cancelled requests."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

import pytest

from clawd_code_sdk import ClaudeSDKClient
from clawd_code_sdk._errors import (
    CLIConnectionError,
    ControlRequestError,
    ControlRequestTimeoutError,
    MessageParseError,
)
from clawd_code_sdk._internal.query import Query
from clawd_code_sdk._internal.transport import Transport
from clawd_code_sdk.models import SDKControlInterruptRequest, incoming_control_request_adapter
from clawd_code_sdk.models.control import SDKControlRequestUserDialogRequest
from clawd_code_sdk.session import Session


if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable


class _QueueTransport(Transport):
    """Frames are pushed by the test (or by ``respond``); writes are recorded."""

    def __init__(self, respond: Callable[[dict[str, Any]], list[Any]] | None = None) -> None:
        self.inbox: asyncio.Queue[Any] = asyncio.Queue()
        self.written: list[dict[str, Any]] = []
        self.closed = False
        self._respond = respond

    async def connect(self) -> None:
        pass

    async def write(self, data: str) -> None:
        message = json.loads(data)
        self.written.append(message)
        for frame in self._respond(message) if self._respond else []:
            self.inbox.put_nowait(frame)

    async def read_messages(self) -> AsyncIterator[dict[str, Any]]:
        while True:
            frame = await self.inbox.get()
            if frame is None:
                return
            if isinstance(frame, BaseException):
                raise frame
            yield frame

    async def close(self) -> None:
        self.closed = True
        self.inbox.put_nowait(None)

    async def end_input(self) -> None:
        pass

    def responses(self) -> list[dict[str, Any]]:
        return [m["response"] for m in self.written if m.get("type") == "control_response"]


ASSISTANT = {"type": "assistant", "message": {"content": []}}


async def _next_message(query: Query) -> dict[str, Any]:
    async for message in query.receive_messages():
        return message
    raise AssertionError("stream ended")


async def _settle() -> None:
    for _ in range(5):
        await asyncio.sleep(0)


async def test_unknown_control_request_answered_with_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("CLAWD_STRICT_MESSAGES", raising=False)
    transport = _QueueTransport()
    query = Query(transport=transport)
    await query.start()
    try:
        request = {"subtype": "some_new_subtype"}
        transport.inbox.put_nowait({
            "type": "control_request",
            "request_id": "r1",
            "request": request,
        })
        transport.inbox.put_nowait(ASSISTANT)
        assert await asyncio.wait_for(_next_message(query), 5) == ASSISTANT
        await _settle()
        [response] = transport.responses()
        assert response["subtype"] == "error"
        assert response["request_id"] == "r1"
        assert "some_new_subtype" in response["error"]
    finally:
        await query.close()


async def test_unknown_control_request_raises_in_strict_mode():
    transport = _QueueTransport()
    query = Query(transport=transport)
    await query.start()
    try:
        transport.inbox.put_nowait({
            "type": "control_request",
            "request_id": "r1",
            "request": {"subtype": "some_new_subtype"},
        })
        with pytest.raises(MessageParseError):
            await asyncio.wait_for(_next_message(query), 5)
        await _settle()
        assert transport.responses()[0]["subtype"] == "error"  # the CLI is answered anyway
    finally:
        await query.close()


def test_request_user_dialog_is_an_incoming_request():
    req = incoming_control_request_adapter.validate_python({
        "subtype": "request_user_dialog",
        "dialog_kind": "refusal_fallback_prompt",
        "payload": {},
    })
    assert isinstance(req, SDKControlRequestUserDialogRequest)


async def test_connect_failure_closes_the_transport():
    def respond(message: dict[str, Any]) -> list[Any]:
        if message.get("type") != "control_request":
            return []
        rid = message["request_id"]
        response = {"subtype": "error", "request_id": rid, "error": "boom"}
        return [{"type": "control_response", "response": response}]

    transport = _QueueTransport(respond)
    with pytest.raises(ControlRequestError):
        async with ClaudeSDKClient(transport=transport):
            pass
    assert transport.closed


async def test_requests_fail_fast_after_the_reader_died():
    transport = _QueueTransport()
    query = Query(transport=transport)
    await query.start()
    try:
        transport.inbox.put_nowait(None)  # the CLI's stdout ended
        await _settle()
        loop = asyncio.get_running_loop()
        start = loop.time()
        with pytest.raises(CLIConnectionError):
            await query._send_control_request(SDKControlInterruptRequest(), timeout=5)
        assert loop.time() - start < 1
    finally:
        await query.close()


async def test_cancelled_request_is_withdrawn():
    transport = _QueueTransport()
    query = Query(transport=transport)
    await query.start()
    try:
        task = asyncio.create_task(query._send_control_request(SDKControlInterruptRequest()))
        await _settle()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await _settle()
        assert query.pending_control_responses == {}
        assert query.pending_control_results == {}
        request_id = transport.written[0]["request_id"]
        assert {"type": "control_cancel_request", "request_id": request_id} in transport.written
    finally:
        await query.close()


async def test_timed_out_request_is_withdrawn():
    transport = _QueueTransport()
    query = Query(transport=transport)
    await query.start()
    try:
        with pytest.raises(ControlRequestTimeoutError):
            await query._send_control_request(SDKControlInterruptRequest(), timeout=0.05)
        await _settle()
        request_id = transport.written[0]["request_id"]
        assert {"type": "control_cancel_request", "request_id": request_id} in transport.written
    finally:
        await query.close()


async def test_long_calls_take_a_timeout():
    transport = _QueueTransport()
    client = ClaudeSDKClient(transport=transport)
    client._query = query = Query(transport=transport)
    await query.start()
    try:
        for call in (
            client.side_question("q", timeout=0.05),
            client.call_tool("t", timeout=0.05),
            client.generate_session_title("d", timeout=0.05),
            client.claude_oauth_wait_for_completion(timeout=0.05),
        ):
            with pytest.raises(ControlRequestTimeoutError):
                await call
    finally:
        await query.close()


class _FakeClient:
    """Enough of ClaudeSDKClient for Session.send: one endless response."""

    def __init__(self) -> None:
        self.interrupted = False
        self.options = type("Options", (), {"model": None, "cwd": None})()

    async def query(self, prompt: str) -> None:
        pass

    async def receive_response(self) -> AsyncIterator[Any]:
        while not self.interrupted:  # the rest of an interrupted turn is drained
            yield ASSISTANT
            await asyncio.sleep(0)

    async def interrupt(self) -> None:
        self.interrupted = True


async def test_session_send_break_returns_to_idle():
    session = Session("s", _FakeClient())  # type: ignore[arg-type]
    session._state = "idle"
    async with asyncio.timeout(5):
        stream = session.send("hi")
        async for _ in stream:
            break
        await stream.aclose()
    assert session.snapshot.state == "idle"
    assert session._client.interrupted  # type: ignore[attr-defined]
    session._client.interrupted = False  # type: ignore[attr-defined]
    # and usable again
    stream = session.send("again")
    async for _ in stream:
        break
    await stream.aclose()


class _TurnClient:
    """A fake client whose turn ends with a result message (or runs until interrupted)."""

    def __init__(self, *, endless: bool = False, slow_query: bool = False) -> None:
        from clawd_code_sdk.models import message_adapter

        from .test_session import RESULT_MSG

        self.result = message_adapter.validate_python(RESULT_MSG)
        self.endless = endless
        self.slow_query = slow_query
        self.interrupts = 0
        self.interrupt_error: BaseException | None = None
        self.options = type("Options", (), {"model": None, "cwd": None})()

    async def query(self, prompt: str) -> None:
        if self.slow_query:
            await asyncio.sleep(10)

    async def receive_response(self) -> AsyncIterator[Any]:
        if self.endless:
            while not self.interrupts:
                yield ASSISTANT
                await asyncio.sleep(0.01)
        yield self.result

    async def interrupt(self) -> None:
        self.interrupts += 1
        if self.interrupt_error is not None:
            raise self.interrupt_error


def _session(client: _TurnClient) -> Session:
    session = Session("s", client)  # type: ignore[arg-type]
    session._state = "idle"
    return session


async def test_break_on_the_result_keeps_the_turn():
    """Stopping at the ResultMessage is a finished turn: recorded, nothing interrupted."""
    from clawd_code_sdk.models import ResultMessage

    client = _TurnClient()
    session = _session(client)
    async with asyncio.timeout(2):
        stream = session.send("hi")
        async for message in stream:
            if isinstance(message, ResultMessage):
                break
        await stream.aclose()
    assert len(session.turns) == 1
    assert client.interrupts == 0
    assert session.state == "idle"


async def test_failed_interrupt_leaves_the_session_in_error():
    client = _TurnClient(endless=True)
    client.interrupt_error = CLIConnectionError("CLI died")
    session = _session(client)
    stream = session.send("hi")
    async for _ in stream:
        break
    await stream.aclose()
    assert session.state == "error"


async def test_anyio_timeout_still_finishes_the_turn():
    """A level-triggered anyio cancel scope doesn't cut the cleanup short."""
    import anyio

    client = _TurnClient(endless=True)
    session = _session(client)
    with anyio.move_on_after(0.05):
        async for _ in session.send("hi"):
            pass
    assert client.interrupts == 1
    assert session.state == "idle"


async def test_cancel_before_the_prompt_was_sent_does_not_wait_for_a_turn():
    client = _TurnClient(slow_query=True)
    session = _session(client)

    async def consume() -> None:
        async for _ in session.send("hi"):
            pass

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    task.cancel()
    async with asyncio.timeout(2):  # not INTERRUPT_DRAIN_TIMEOUT
        with pytest.raises(asyncio.CancelledError):
            await task
    assert client.interrupts == 0
    assert session.state == "idle"


async def test_connect_cut_short_by_anyio_timeout_cleans_up():
    """Under a level-triggered anyio scope the cleanup still runs to its end."""
    import anyio

    transport = _QueueTransport()  # never answers initialize
    client = ClaudeSDKClient(transport=transport)
    with anyio.move_on_after(0.1):
        await client.connect()
    assert transport.closed
    assert client._query is None
