"""A refused resume / error result surfaces as ResultError (upstream #1198/#1205)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import anyio
import pytest

from clawd_code_sdk import ProcessError, ResultError
from clawd_code_sdk._errors import error_result_text
from clawd_code_sdk._internal.query import Query
from clawd_code_sdk._internal.transport import Transport
from clawd_code_sdk.models import SDKControlInitializeRequest


if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class _ScriptedTransport(Transport):
    """Yields the given frames, then fails like a CLI exiting with code 1."""

    def __init__(self, frames: list[dict[str, Any]]) -> None:
        self._frames = frames

    async def connect(self) -> None:
        pass

    async def write(self, data: str) -> None:
        pass

    async def read_messages(self) -> AsyncIterator[dict[str, Any]]:
        for frame in self._frames:
            await anyio.sleep(0)
            yield frame
        raise ProcessError("Command failed", exit_code=1)

    async def close(self) -> None:
        pass

    async def end_input(self) -> None:
        pass


_REFUSED = {
    "type": "result",
    "subtype": "error_during_execution",
    "is_error": True,
    "errors": ["Resume rejected by --resume-drops-turn: entry abc is not part of turn"],
}


async def test_pending_initialize_fails_with_result_text() -> None:
    query = Query(transport=_ScriptedTransport([_REFUSED]))
    await query.start()
    try:
        with pytest.raises(ResultError) as exc_info:
            await query._send_control_request(SDKControlInitializeRequest(), timeout=5)
        assert "Resume rejected" in str(exc_info.value)
        assert exc_info.value.exit_code == 1
        assert exc_info.value.data["subtype"] == "error_during_execution"
    finally:
        await query.close()


async def test_stream_reraises_typed_result_error() -> None:
    query = Query(transport=_ScriptedTransport([_REFUSED]))
    await query.start()
    try:
        received: list[dict[str, Any]] = []

        async def drain() -> None:
            async for message in query.receive_messages():
                received.append(message)  # noqa: PERF401

        with pytest.raises(ResultError):
            await drain()
        assert received == [_REFUSED]
    finally:
        await query.close()


async def test_crash_after_progress_stays_process_error() -> None:
    frames = [_REFUSED, {"type": "assistant", "message": {"content": []}}]
    query = Query(transport=_ScriptedTransport(frames))
    await query.start()
    try:
        with pytest.raises(ProcessError) as exc_info:
            async for _ in query.receive_messages():
                pass
        assert not isinstance(exc_info.value, ResultError)
    finally:
        await query.close()


@pytest.mark.parametrize(
    ("frame", "expected"),
    [
        ({"errors": ["a", "b"], "result": "r"}, "a; b"),
        ({"errors": [], "result": " API Error: 529 "}, "API Error: 529"),
        ({"subtype": "error_max_turns"}, "error_max_turns"),
        ({"subtype": "success", "api_error_status": 500}, "API error (HTTP 500)"),
        ({"subtype": "success"}, "unknown error"),
    ],
)
def test_error_result_text(frame: dict[str, Any], expected: str) -> None:
    assert error_result_text(frame) == expected
