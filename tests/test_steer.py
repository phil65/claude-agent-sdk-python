"""Steering a running query: uuid-stamped messages, lifecycle frames, cost per query."""

from typing import TYPE_CHECKING, Any, cast

from clawd_code_sdk import ClaudeAgentOptions, ClaudeSDKClient
from clawd_code_sdk.models import CommandLifecycleMessage, message_adapter


if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class _FakeQuery:
    """Records written messages and replays the given CLI messages."""

    def __init__(self, messages: list[dict[str, Any]] | None = None) -> None:
        self.written: list[dict[str, Any]] = []
        self.messages = messages or []

    async def write_json(self, data: dict[str, Any]) -> None:
        self.written.append(data)

    async def receive_messages(self) -> AsyncIterator[dict[str, Any]]:
        for message in self.messages:
            yield message


def _client(query: _FakeQuery) -> ClaudeSDKClient:
    client = ClaudeSDKClient(ClaudeAgentOptions())
    client._query = cast(Any, query)
    return client


def _result(total_cost: float, output_tokens: int) -> dict[str, Any]:
    return {
        "type": "result",
        "subtype": "success",
        "uuid": "r",
        "session_id": "s",
        "duration_ms": 1,
        "duration_api_ms": 1,
        "is_error": False,
        "num_turns": 1,
        "total_cost_usd": total_cost,
        "usage": {"input_tokens": 1, "output_tokens": output_tokens},
        "stop_reason": "end_turn",
    }


async def test_steer_keeps_counting_the_running_query() -> None:
    # The interrupted cycle's result, then the steered message's cycle
    query = _FakeQuery([_result(0.25, 10), _result(0.75, 5)])
    client = _client(query)
    await client.query("count to 300")
    message_uuid = await client.steer("stop and say BANANA")

    async for _ in client.receive_messages():
        pass

    first, steered = query.written
    assert "uuid" not in first
    assert steered["uuid"] == message_uuid
    assert steered["priority"] == "now"
    assert steered["message"]["content"] == [{"type": "text", "text": "stop and say BANANA"}]
    # Both cycles count for the query
    assert client.query_cost == 0.75
    assert client.query_usage.output_tokens == 15


async def test_query_with_uuid() -> None:
    query = _FakeQuery()
    await _client(query).query("hi", uuid="u1", priority="next")
    assert query.written[0]["uuid"] == "u1"
    assert query.written[0]["priority"] == "next"


def test_command_lifecycle_frame() -> None:
    frame = {
        "type": "command_lifecycle",
        "command_uuid": "c9c43ffb",
        "state": "queued",
        "uuid": "7751841f",
        "session_id": "466f26ed",
    }
    assert message_adapter.validate_python(frame) == CommandLifecycleMessage(
        uuid="7751841f", command_uuid="c9c43ffb", state="queued", session_id="466f26ed"
    )
