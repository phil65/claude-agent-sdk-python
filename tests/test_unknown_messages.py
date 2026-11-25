"""Unknown CLI message types: skipped with a warning by default, raised in strict mode."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

import pytest

from clawd_code_sdk import ClaudeAgentOptions, ClaudeSDKClient
from clawd_code_sdk._errors import MessageParseError
from clawd_code_sdk.client import _warned_unknown_kinds, unknown_message_kind


if TYPE_CHECKING:
    from collections.abc import AsyncIterator


_STATUS = {"type": "system", "subtype": "status", "status": None, "uuid": "u", "session_id": "s"}


class _FakeQuery:
    def __init__(self, messages: list[dict[str, Any]]) -> None:
        self.messages = messages

    async def receive_messages(self) -> AsyncIterator[dict[str, Any]]:
        for message in self.messages:
            yield message


async def _collect(messages: list[dict[str, Any]]) -> list[Any]:
    client = ClaudeSDKClient(ClaudeAgentOptions())
    client._query = cast(Any, _FakeQuery(messages))
    return [m async for m in client.receive_messages()]


@pytest.fixture
def lenient(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLAWD_STRICT_MESSAGES", raising=False)
    _warned_unknown_kinds.clear()


def test_unknown_message_kind() -> None:
    assert unknown_message_kind({"type": "banana"}) == "banana"
    assert unknown_message_kind({"type": "system", "subtype": "banana"}) == "system/banana"
    assert unknown_message_kind(_STATUS) is None
    # Malformed known types and non-dicts are not "unknown"
    assert unknown_message_kind({"type": "result", "subtype": "success"}) is None
    assert unknown_message_kind({"message": {}}) is None
    assert unknown_message_kind("x") is None


@pytest.mark.usefixtures("lenient")
async def test_unknown_types_are_skipped_and_warned_once(caplog: pytest.LogCaptureFixture) -> None:
    unknown = [{"type": "banana"}, {"type": "banana"}, {"type": "system", "subtype": "kiwi"}]
    with caplog.at_level(logging.WARNING, logger="clawd_code_sdk.client"):
        messages = await _collect([*unknown, _STATUS])
    assert len(messages) == 1
    assert messages[0].subtype == "status"
    warnings = [r.getMessage() for r in caplog.records]
    assert len(warnings) == 2
    assert "'banana'" in warnings[0]
    assert "'system/kiwi'" in warnings[1]


@pytest.mark.usefixtures("lenient")
async def test_malformed_known_type_still_raises() -> None:
    with pytest.raises(MessageParseError):
        await _collect([{"type": "result", "subtype": "success"}])


@pytest.mark.parametrize("value", ["1", "true", "YES", "on"])
async def test_strict_mode_raises(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("CLAWD_STRICT_MESSAGES", value)
    with pytest.raises(MessageParseError, match="banana"):
        await _collect([{"type": "banana"}, _STATUS])


@pytest.mark.parametrize("value", ["0", "false", ""])
async def test_falsy_values_are_lenient(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("CLAWD_STRICT_MESSAGES", value)
    assert len(await _collect([{"type": "banana"}, _STATUS])) == 1
