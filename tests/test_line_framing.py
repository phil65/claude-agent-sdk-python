"""Regression tests for NDJSON line framing (upstream #1083).

anyio's TextReceiveStream yields chunks, not lines. Stripping chunks used to
drop whitespace wherever a read boundary fell inside a JSON string value.
"""

import json
from typing import Any

import anyio
import pytest

from clawd_code_sdk._errors import CLIJSONDecodeError
from clawd_code_sdk._internal.transport.subprocess_utils import LineFramer, parse_stream


class _ChunkStream:
    def __init__(self, chunks: list[str]) -> None:
        self._chunks = chunks

    def __aiter__(self) -> _ChunkStream:
        return self

    async def __anext__(self) -> str:
        if not self._chunks:
            raise StopAsyncIteration
        return self._chunks.pop(0)


async def _parse(chunks: list[str], max_buffer_size: int = 10_000_000) -> list[dict[str, Any]]:
    stream: Any = _ChunkStream(chunks)
    return [msg async for msg in parse_stream(stream, max_buffer_size)]


@pytest.mark.parametrize("boundary", [1, 7, 12, 13, 14, 40])
def test_whitespace_at_chunk_boundary_is_preserved(boundary: int) -> None:
    text = "word " * 20 + "\t tail  "
    line = json.dumps({"type": "assistant", "text": text}) + "\n"
    # Put the read boundary right next to a space inside the string value.
    cut = line.index("word ") + boundary
    messages = anyio.run(_parse, [line[:cut], line[cut:]])
    assert messages == [{"type": "assistant", "text": text}]


def test_many_small_chunks_reassemble_exactly() -> None:
    text = " a  b   c " * 1000
    line = json.dumps({"type": "x", "text": text}) + "\n"
    chunks = [line[i : i + 3] for i in range(0, len(line), 3)]
    assert anyio.run(_parse, chunks) == [{"type": "x", "text": text}]


def test_trailing_message_without_newline_is_yielded() -> None:
    assert anyio.run(_parse, ['{"a": 1}\n{"b": 2}']) == [{"a": 1}, {"b": 2}]


def test_truncated_trailing_json_is_dropped() -> None:
    assert anyio.run(_parse, ['{"a": 1}\n{"b": ']) == [{"a": 1}]


def test_non_json_lines_are_skipped() -> None:
    chunks = ["[SandboxDebug] hello\n", '{"a": 1}\r\n', "\n", "   \n"]
    assert anyio.run(_parse, chunks) == [{"a": 1}]


def test_corrupt_complete_line_raises() -> None:
    with pytest.raises(CLIJSONDecodeError):
        anyio.run(_parse, ['{"a": oops}\n'])


def test_buffer_limit_applies_to_incomplete_line() -> None:
    with pytest.raises(CLIJSONDecodeError):
        anyio.run(_parse, ['{"a": "' + "x" * 200], 100)


def test_line_framer_keeps_partial_tail() -> None:
    framer = LineFramer()
    assert framer.push("ab") == []
    assert framer.push("c\nde") == ["abc"]
    assert framer.pending_len == 2
    assert framer.push("\n\nf") == ["de", ""]
    assert framer.flush() == "f"
    assert framer.pending_len == 0
