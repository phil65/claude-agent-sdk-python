"""Parsing of every Messages API content block type in assistant and user messages."""

from typing import Any, get_args

from anthropic.types.beta import BetaContentBlock
import pytest

from clawd_code_sdk.anthropic_stream import _synthesize_events
from clawd_code_sdk.models import (
    SERVER_CONTENT_BLOCK_TYPES,
    AssistantMessage,
    DocumentBlock,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
    UserMessage,
    message_adapter,
)
from clawd_code_sdk.models.content_blocks import is_server_block, server_block_to_otel


SERVER_BLOCKS: dict[str, dict[str, Any]] = {
    "redacted_thinking": {"type": "redacted_thinking", "data": "EmwKAhgBEgy3va3pzix/LafPsn4a"},
    "server_tool_use": {
        "type": "server_tool_use",
        "id": "srvtoolu_01",
        "name": "web_search",
        "input": {"query": "python 3.14"},
    },
    "web_search_tool_result": {
        "type": "web_search_tool_result",
        "tool_use_id": "srvtoolu_01",
        "content": [
            {
                "type": "web_search_result",
                "title": "Python 3.14",
                "url": "https://python.org",
                "encrypted_content": "abc",
                "page_age": None,
            }
        ],
    },
    "web_fetch_tool_result": {
        "type": "web_fetch_tool_result",
        "tool_use_id": "srvtoolu_02",
        "content": {"type": "web_fetch_tool_result_error", "error_code": "url_not_accessible"},
    },
    "code_execution_tool_result": {
        "type": "code_execution_tool_result",
        "tool_use_id": "srvtoolu_03",
        "content": {
            "type": "code_execution_result",
            "stdout": "1",
            "stderr": "",
            "return_code": 0,
            "content": [],
        },
    },
    "mcp_tool_use": {
        "type": "mcp_tool_use",
        "id": "mcptoolu_01",
        "name": "search",
        "server_name": "docs",
        "input": {"q": "x"},
    },
    "mcp_tool_result": {
        "type": "mcp_tool_result",
        "tool_use_id": "mcptoolu_01",
        "is_error": False,
        "content": [{"type": "text", "text": "found"}],
    },
    "container_upload": {"type": "container_upload", "file_id": "file_01"},
}


def _assistant(*blocks: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "assistant",
        "session_id": "s",
        "uuid": "u",
        "parent_tool_use_id": None,
        "message": {
            "id": "msg_01",
            "type": "message",
            "role": "assistant",
            "model": "claude-sonnet-5",
            "stop_reason": None,
            "stop_sequence": None,
            "content": list(blocks),
        },
    }


@pytest.mark.parametrize("block_type", sorted(SERVER_BLOCKS))
def test_assistant_message_accepts_api_block(block_type: str) -> None:
    message = message_adapter.validate_python(_assistant(SERVER_BLOCKS[block_type]))
    assert isinstance(message, AssistantMessage)
    (block,) = message.content
    assert is_server_block(block)
    assert block.type == block_type


def test_every_anthropic_content_block_type_is_accepted() -> None:
    """New Messages API block types must fail here, not at runtime."""
    own = {TextBlock, ThinkingBlock, ToolUseBlock}
    own_types = {cls.model_fields["type"].default for cls in own}
    covered = own_types | {cls.model_fields["type"].default for cls in SERVER_CONTENT_BLOCK_TYPES}
    api_types = {
        cls.model_fields["type"].default for cls in get_args(get_args(BetaContentBlock)[0])
    }
    assert api_types <= covered


def test_mixed_assistant_content_keeps_order() -> None:
    data = _assistant(
        {"type": "thinking", "thinking": "hmm", "signature": "sig"},
        SERVER_BLOCKS["server_tool_use"],
        SERVER_BLOCKS["web_search_tool_result"],
        {"type": "text", "text": "Done."},
    )
    message = message_adapter.validate_python(data)
    assert isinstance(message, AssistantMessage)
    assert [b.type for b in message.content] == [
        "thinking",
        "server_tool_use",
        "web_search_tool_result",
        "text",
    ]


def test_api_blocks_convert_to_stream_events_and_otel() -> None:
    message = message_adapter.validate_python(
        _assistant(SERVER_BLOCKS["server_tool_use"], SERVER_BLOCKS["web_search_tool_result"])
    )
    assert isinstance(message, AssistantMessage)
    events = _synthesize_events(message)
    starts = [e for e in events if e.type == "content_block_start"]
    assert [s.content_block.type for s in starts] == ["server_tool_use", "web_search_tool_result"]
    tool_use, tool_result = message.content
    assert is_server_block(tool_use)
    assert is_server_block(tool_result)
    call = server_block_to_otel(tool_use)
    response = server_block_to_otel(tool_result)
    assert call is not None
    assert call["type"] == "tool_call"
    assert response is not None
    assert response["type"] == "tool_call_response"
    otel = message.to_otel()
    assert [p["type"] for p in otel["parts"]] == ["tool_call", "tool_call_response"]


@pytest.mark.parametrize(
    "source",
    [
        {"type": "base64", "media_type": "application/pdf", "data": "JVBERi0x"},
        {"type": "text", "media_type": "text/plain", "data": "hello"},
        {"type": "url", "url": "https://example.com/a.pdf"},
        {"type": "file", "file_id": "file_01"},
    ],
)
def test_user_message_accepts_document(source: dict[str, Any]) -> None:
    data = {
        "type": "user",
        "session_id": "s",
        "uuid": "u",
        "parent_tool_use_id": None,
        "message": {
            "role": "user",
            "content": [
                {"type": "document", "source": source, "title": "Spec"},
                {"type": "text", "text": "Summarize this"},
            ],
        },
    }
    message = message_adapter.validate_python(data)
    assert isinstance(message, UserMessage)
    assert not isinstance(message.content, str)
    document = message.content[0]
    assert isinstance(document, DocumentBlock)
    assert document.source.type == source["type"]
    assert document.title == "Spec"


def test_image_block_otel_part_uses_logfire_field_names() -> None:
    """Logfire 6 names the field ``mime_type`` (it was ``media_type`` in 4.32-5.x)."""
    import typing

    from logfire._internal.integrations.llm_providers.semconv import BlobPart

    from clawd_code_sdk.models.content_blocks import ImageBlock, ImageSource

    block = ImageBlock(source=ImageSource(type="base64", media_type="image/png", data="aGk="))
    part = block.to_otel()
    assert set(part) <= set(typing.get_type_hints(BlobPart))
    assert part["mime_type"] == "image/png"
