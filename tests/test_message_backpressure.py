"""The message stream between reader and consumer is bounded (back-pressure)."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

from clawd_code_sdk._internal.query import Query
from clawd_code_sdk._internal.transport import Transport
from clawd_code_sdk.models import SDKControlInterruptRequest


if TYPE_CHECKING:
    from collections.abc import AsyncIterator

BOUND = 5
TOTAL = 50


class _CountingTransport(Transport):
    """Yields `TOTAL` messages as fast as the reader takes them, then control frames."""

    def __init__(self) -> None:
        self.yielded = 0
        self.inbox: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

    async def connect(self) -> None:
        pass

    async def write(self, data: str) -> None:
        message = json.loads(data)
        if message.get("type") == "control_request":
            response = {"subtype": "success", "request_id": message["request_id"]}
            self.inbox.put_nowait({"type": "control_response", "response": response})

    async def read_messages(self) -> AsyncIterator[dict[str, Any]]:
        for i in range(TOTAL):
            self.yielded += 1
            yield {"type": "stream_event", "n": i}
        while (frame := await self.inbox.get()) is not None:
            yield frame

    async def close(self) -> None:
        self.inbox.put_nowait(None)

    async def end_input(self) -> None:
        pass


async def _settle() -> None:
    for _ in range(20):
        await asyncio.sleep(0)


async def test_reader_blocks_at_the_bound_for_a_slow_consumer() -> None:
    transport = _CountingTransport()
    query = Query(transport=transport, max_buffered_messages=BOUND)
    await query.start()
    try:
        await _settle()
        # The reader holds one message it can't hand over yet.
        assert transport.yielded <= BOUND + 1
        received = []
        async for message in query.receive_messages():
            received.append(message["n"])
            if len(received) == TOTAL:
                break
        assert received == list(range(TOTAL))
    finally:
        await query.close()


async def test_control_responses_still_arrive_when_the_buffer_is_full() -> None:
    transport = _CountingTransport()
    query = Query(transport=transport, max_buffered_messages=BOUND)
    await query.start()
    try:
        await _settle()
        # Nobody consumes, yet the reader must read past the messages to the response.
        async with asyncio.timeout(2):
            await query._send_control_request(SDKControlInterruptRequest())
        received = [m["n"] async for m in _take(query, TOTAL)]
        assert received == list(range(TOTAL))
    finally:
        await query.close()


async def _take(query: Query, count: int) -> AsyncIterator[dict[str, Any]]:
    taken = 0
    async for message in query.receive_messages():
        yield message
        taken += 1
        if taken == count:
            return
