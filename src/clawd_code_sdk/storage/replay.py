"""Replay Claude Code sessions from stored JSONL transcripts.

Converts stored JSONL entries back into wire-format Message types,
enabling consumers to process historical sessions with the same code
that handles live streams.

The storage format saves one entry per content block, chained via parentUuid.
This module preserves that granularity: each stored assistant entry becomes
one AssistantMessage with a single content block, matching the live wire
behavior (where --include-partial-messages yields one AssistantMessage per
content block as it completes).

When ``include_stream_events=True``, synthetic ``StreamEvent`` messages are
injected around each content block to reproduce the structural envelope of
a live stream. Each text/thinking block gets a single delta containing the
full content (since token-level deltas are not preserved in storage).

Not reconstructible from storage:
    - Token-level streaming granularity (deltas are synthetic, one per block).
    - ResultMessage: Cost, aggregated usage, and duration data are not stored.
    - SystemMessage(init): Session initialization metadata (tools, model, etc.).
    - RateLimitMessage: Rate limit events are transient.

Example::

    from pathlib import Path
    from clawd_code_sdk.models.content_blocks import TextBlock, ToolUseBlock
    from clawd_code_sdk.models.messages import AssistantMessage, StreamEvent, UserMessage
    from clawd_code_sdk.storage.replay import replay_session

    for message in replay_session(
        Path("~/.claude/projects/-proj/session.jsonl"),
        include_stream_events=True,
    ):
        match message:
            case StreamEvent(event=event) if event.type == "content_block_delta":
                delta = event.delta
                if hasattr(delta, "text"):
                    print(delta.text, end="", flush=True)
            case AssistantMessage(content=blocks):
                pass  # Already handled via deltas
            case UserMessage(content=str() as text):
                print(f"User: {text}")
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
import json as _json
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from clawd_code_sdk.models.content_blocks import (
    ContentBlock,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
)
from clawd_code_sdk.models.messages import (
    AssistantMessage,
    Message,
    StreamEvent,
    ToolProgressMessage,
    UserMessage,
)
from clawd_code_sdk.storage.helpers import read_session
from clawd_code_sdk.storage.models import (
    ClaudeApiMessage,
    ClaudeAssistantEntry,
    ClaudeContentBlock,
    ClaudeImageBlock,
    ClaudeProgressEntry,
    ClaudeTextBlock,
    ClaudeThinkingBlock,
    ClaudeToolProgressData,
    ClaudeToolResultBlock,
    ClaudeToolUseBlock,
    ClaudeUserEntry,
)


if TYPE_CHECKING:
    from collections.abc import Iterable

    from anthropic.types import RawMessageStreamEvent

    from clawd_code_sdk.storage.models import ClaudeJSONLEntry


# =============================================================================
# Content block conversion (storage → wire format)
# =============================================================================


def _convert_content_block(block: ClaudeContentBlock) -> ContentBlock | None:
    """Convert a stored content block to a wire-format ContentBlock.

    Returns None for block types with no wire-format equivalent (e.g. images).
    """
    match block:
        case ClaudeTextBlock():
            return TextBlock(text=block.text)
        case ClaudeThinkingBlock():
            return ThinkingBlock(
                thinking=block.thinking,
                signature=block.signature or "",
            )
        case ClaudeToolUseBlock():
            return ToolUseBlock(
                id=block.id,
                name=block.name,
                input=block.input,
            )
        case ClaudeToolResultBlock():
            return ToolResultBlock(
                tool_use_id=block.tool_use_id,
                content=block.content,
                is_error=block.is_error,
            )
        case ClaudeImageBlock():
            # No wire-format ContentBlock for images; they typically appear
            # inside tool_result content as nested dicts, not as top-level blocks.
            return None


def _convert_content_blocks(
    content: str | list[ClaudeContentBlock],
) -> str | Sequence[ContentBlock]:
    """Convert message content, handling both string and block-list forms."""
    if isinstance(content, str):
        return content
    blocks: list[ContentBlock] = []
    for block in content:
        if (converted := _convert_content_block(block)) is not None:
            blocks.append(converted)
    return blocks


# =============================================================================
# Entry conversion (storage → wire format)
# =============================================================================


def _convert_user_entry(entry: ClaudeUserEntry) -> UserMessage:
    """Convert a stored user entry to a wire-format UserMessage."""
    content = _convert_content_blocks(entry.message.content)
    return UserMessage(
        uuid=entry.uuid,
        session_id=entry.session_id,
        content=content,
        tool_use_result=entry.tool_use_result,
        isReplay=True,
    )


def _convert_assistant_entry(entry: ClaudeAssistantEntry) -> AssistantMessage:
    """Convert a stored assistant entry to a wire-format AssistantMessage."""
    msg = entry.message
    model = msg.model if isinstance(msg, ClaudeApiMessage) else "unknown"
    content = _convert_content_blocks(msg.content)
    # AssistantMessage.content must be Sequence[ContentBlock], not str.
    if isinstance(content, str):
        content = [TextBlock(text=content)]
    return AssistantMessage(
        content=content,
        model=model,
        uuid=entry.uuid,
        session_id=entry.session_id,
        error="unknown" if entry.is_api_error_message else None,
    )


def _convert_progress_entry(entry: ClaudeProgressEntry) -> ToolProgressMessage | None:
    """Convert a stored progress entry to a wire-format ToolProgressMessage.

    Only converts tool_progress data; returns None for other progress types
    (bash_progress, mcp_progress, hook_progress, etc.).
    """
    if not isinstance(entry.data, ClaudeToolProgressData):
        return None
    return ToolProgressMessage(
        uuid=entry.uuid,
        session_id=entry.session_id,
        tool_use_id=entry.data.tool_use_id or "",
        tool_name=entry.data.tool_name or "",
        parent_tool_use_id=entry.data.parent_tool_use_id,
        elapsed_time_seconds=entry.data.elapsed_time_seconds or 0.0,
    )


# =============================================================================
# Synthetic StreamEvent construction
# =============================================================================


def _make_stream_event(
    event: RawMessageStreamEvent,
    *,
    session_id: str,
    uuid: str,
) -> StreamEvent:
    """Wrap an Anthropic raw stream event into a wire-format StreamEvent."""
    return StreamEvent(event=event, session_id=session_id, uuid=uuid)


def _make_message_start(
    *,
    msg_id: str,
    model: str,
    session_id: str,
    uuid: str,
) -> StreamEvent:
    """Create a synthetic message_start StreamEvent."""
    from anthropic.types import (
        Message as AnthropicMessage,
        RawMessageStartEvent,
        Usage as AnthropicUsage,
    )

    return _make_stream_event(
        RawMessageStartEvent(
            type="message_start",
            message=AnthropicMessage(
                id=msg_id,
                type="message",
                role="assistant",
                content=[],
                model=model,
                stop_reason=None,
                stop_sequence=None,
                usage=AnthropicUsage(input_tokens=0, output_tokens=0),
            ),
        ),
        session_id=session_id,
        uuid=uuid,
    )


# Anthropic SDK stop reason literal type
_AnthropicStopReason = Literal[
    "end_turn", "max_tokens", "stop_sequence", "tool_use", "pause_turn", "refusal"
]

_VALID_STOP_REASONS: frozenset[str] = frozenset(
    {"end_turn", "max_tokens", "stop_sequence", "tool_use", "pause_turn", "refusal"}
)


def _coerce_stop_reason(value: str | None) -> _AnthropicStopReason | None:
    """Coerce a stored stop_reason string to the Anthropic SDK literal type."""
    if value is not None and value in _VALID_STOP_REASONS:
        return value  # type: ignore[return-value]
    return None


def _make_message_delta(
    *,
    stop_reason: str | None,
    session_id: str,
    uuid: str,
) -> StreamEvent:
    """Create a synthetic message_delta StreamEvent."""
    from anthropic.types import MessageDeltaUsage, RawMessageDeltaEvent
    from anthropic.types.raw_message_delta_event import Delta as RawMessageDelta

    return _make_stream_event(
        RawMessageDeltaEvent(
            type="message_delta",
            delta=RawMessageDelta(stop_reason=_coerce_stop_reason(stop_reason), stop_sequence=None),
            usage=MessageDeltaUsage(output_tokens=0),
        ),
        session_id=session_id,
        uuid=uuid,
    )


def _make_message_stop(*, session_id: str, uuid: str) -> StreamEvent:
    """Create a synthetic message_stop StreamEvent."""
    from anthropic.types import RawMessageStopEvent

    return _make_stream_event(
        RawMessageStopEvent(type="message_stop"),
        session_id=session_id,
        uuid=uuid,
    )


def _make_block_start(
    block: ClaudeContentBlock,
    *,
    index: int,
    session_id: str,
    uuid: str,
) -> StreamEvent:
    """Create a synthetic content_block_start StreamEvent for a stored block."""
    from anthropic.types import (
        RawContentBlockStartEvent,
        TextBlock as ATextBlock,
        ThinkingBlock as AThinkingBlock,
        ToolUseBlock as AToolUseBlock,
    )

    content_block: ATextBlock | AToolUseBlock | AThinkingBlock
    match block:
        case ClaudeTextBlock():
            content_block = ATextBlock(type="text", text="")
        case ClaudeThinkingBlock():
            content_block = AThinkingBlock(type="thinking", thinking="", signature="")
        case ClaudeToolUseBlock():
            content_block = AToolUseBlock(type="tool_use", id=block.id, name=block.name, input={})
        case _:
            # No stream event for tool_result or image blocks
            content_block = ATextBlock(type="text", text="")

    return _make_stream_event(
        RawContentBlockStartEvent(
            type="content_block_start", index=index, content_block=content_block
        ),
        session_id=session_id,
        uuid=uuid,
    )


def _make_block_delta(
    block: ClaudeContentBlock,
    *,
    index: int,
    session_id: str,
    uuid: str,
) -> StreamEvent:
    """Create a synthetic content_block_delta StreamEvent with full block content."""
    from anthropic.types import InputJSONDelta, RawContentBlockDeltaEvent, TextDelta, ThinkingDelta

    delta: TextDelta | InputJSONDelta | ThinkingDelta
    match block:
        case ClaudeTextBlock():
            delta = TextDelta(type="text_delta", text=block.text)
        case ClaudeThinkingBlock():
            delta = ThinkingDelta(type="thinking_delta", thinking=block.thinking)
        case ClaudeToolUseBlock():
            delta = InputJSONDelta(type="input_json_delta", partial_json=_json.dumps(block.input))
        case _:
            delta = TextDelta(type="text_delta", text="")

    return _make_stream_event(
        RawContentBlockDeltaEvent(type="content_block_delta", index=index, delta=delta),
        session_id=session_id,
        uuid=uuid,
    )


def _make_block_stop(*, index: int, session_id: str, uuid: str) -> StreamEvent:
    """Create a synthetic content_block_stop StreamEvent."""
    from anthropic.types import RawContentBlockStopEvent

    return _make_stream_event(
        RawContentBlockStopEvent(type="content_block_stop", index=index),
        session_id=session_id,
        uuid=uuid,
    )


# =============================================================================
# Replay iterators
# =============================================================================


def _is_tool_result_entry(entry: ClaudeUserEntry) -> bool:
    """Check if a user entry is a synthetic tool_result (vs. an actual user prompt)."""
    content = entry.message.content
    if isinstance(content, str):
        return False
    return all(b.type == "tool_result" for b in content)


def _replay_basic(
    entries: Iterable[ClaudeJSONLEntry],
    *,
    include_progress: bool,
) -> Iterator[Message]:
    """Replay entries without stream events (basic mode)."""
    for entry in entries:
        match entry:
            case ClaudeUserEntry():
                yield _convert_user_entry(entry)
            case ClaudeAssistantEntry():
                yield _convert_assistant_entry(entry)
            case ClaudeProgressEntry() if include_progress:
                if (msg := _convert_progress_entry(entry)) is not None:
                    yield msg


def _get_assistant_msg_id(entry: ClaudeAssistantEntry) -> str | None:
    """Extract the API message ID from an assistant entry."""
    msg = entry.message
    return msg.id if isinstance(msg, ClaudeApiMessage) else None


def _get_assistant_model(entry: ClaudeAssistantEntry) -> str:
    """Extract the model name from an assistant entry."""
    msg = entry.message
    return msg.model if isinstance(msg, ClaudeApiMessage) else "unknown"


def _get_assistant_stop_reason(entry: ClaudeAssistantEntry) -> str | None:
    """Extract the stop reason from an assistant entry."""
    msg = entry.message
    return msg.stop_reason if isinstance(msg, ClaudeApiMessage) else None


def _get_first_stored_block(entry: ClaudeAssistantEntry) -> ClaudeContentBlock | None:
    """Get the first content block from a stored assistant entry."""
    msg = entry.message
    content = msg.content
    if isinstance(content, list) and content:
        return content[0]
    return None


def _replay_with_stream_events(
    entries: Iterable[ClaudeJSONLEntry],
    *,
    include_progress: bool,
) -> Iterator[Message]:
    """Replay entries with synthetic StreamEvent injection.

    Groups consecutive assistant entries by their API message ID to
    reconstruct the message-level envelope (message_start/delta/stop).
    Within each group, emits content_block_start, a single
    content_block_delta with the full content, the AssistantMessage,
    and content_block_stop for each block.

    The resulting sequence matches the live wire format structure::

        message_start
          content_block_start (index=0)
          content_block_delta (full content as single delta)
          AssistantMessage
          content_block_stop (index=0)
          content_block_start (index=1)
          content_block_delta
          AssistantMessage
          content_block_stop (index=1)
        message_delta (with stop_reason)
        UserMessage (tool_result, if any)
        message_stop
    """
    entry_list = list(entries)
    i = 0

    while i < len(entry_list):
        entry = entry_list[i]

        if isinstance(entry, ClaudeAssistantEntry):
            # Start of an API response group — collect all entries with same msg_id
            msg_id = _get_assistant_msg_id(entry) or entry.uuid
            model = _get_assistant_model(entry)

            # Find extent of this group (consecutive assistant entries with same msg_id)
            group_start = i
            while i < len(entry_list):
                e = entry_list[i]
                if isinstance(e, ClaudeAssistantEntry) and _get_assistant_msg_id(e) == msg_id:
                    i += 1
                else:
                    break
            group = entry_list[group_start:i]

            # Get stop_reason from the last entry in the group
            last_assistant = group[-1]
            assert isinstance(last_assistant, ClaudeAssistantEntry)
            stop_reason = _get_assistant_stop_reason(last_assistant)

            # → message_start
            yield _make_message_start(
                msg_id=msg_id,
                model=model,
                session_id=entry.session_id,
                uuid=entry.uuid,
            )

            # → per-block events
            for block_index, assistant_entry in enumerate(group):
                assert isinstance(assistant_entry, ClaudeAssistantEntry)
                stored_block = _get_first_stored_block(assistant_entry)

                if stored_block is not None:
                    yield _make_block_start(
                        stored_block,
                        index=block_index,
                        session_id=assistant_entry.session_id,
                        uuid=assistant_entry.uuid,
                    )
                    yield _make_block_delta(
                        stored_block,
                        index=block_index,
                        session_id=assistant_entry.session_id,
                        uuid=assistant_entry.uuid,
                    )

                yield _convert_assistant_entry(assistant_entry)

                if stored_block is not None:
                    yield _make_block_stop(
                        index=block_index,
                        session_id=assistant_entry.session_id,
                        uuid=assistant_entry.uuid,
                    )

            # → message_delta
            yield _make_message_delta(
                stop_reason=stop_reason,
                session_id=last_assistant.session_id,
                uuid=last_assistant.uuid,
            )

            # Collect tool_result user entries that follow this group
            while i < len(entry_list):
                e = entry_list[i]
                if isinstance(e, ClaudeUserEntry) and _is_tool_result_entry(e):
                    yield _convert_user_entry(e)
                    i += 1
                elif isinstance(e, ClaudeProgressEntry) and include_progress:
                    if (msg := _convert_progress_entry(e)) is not None:
                        yield msg
                    i += 1
                elif isinstance(e, ClaudeProgressEntry):
                    i += 1  # Skip progress entries when not included
                else:
                    break

            # → message_stop
            yield _make_message_stop(
                session_id=last_assistant.session_id,
                uuid=last_assistant.uuid,
            )

        elif isinstance(entry, ClaudeUserEntry):
            yield _convert_user_entry(entry)
            i += 1

        elif isinstance(entry, ClaudeProgressEntry) and include_progress:
            if (msg := _convert_progress_entry(entry)) is not None:
                yield msg
            i += 1

        else:
            i += 1  # Skip non-message entries (queue ops, summaries, etc.)


def _filter_sidechains(
    entries: Iterable[ClaudeJSONLEntry],
) -> Iterator[ClaudeJSONLEntry]:
    """Filter out sidechain entries."""
    for entry in entries:
        match entry:
            case ClaudeUserEntry(is_sidechain=True) | ClaudeAssistantEntry(is_sidechain=True):
                continue
            case ClaudeProgressEntry(is_sidechain=True):
                continue
            case _:
                yield entry


def replay_entries(
    entries: Iterable[ClaudeJSONLEntry],
    *,
    include_progress: bool = False,
    include_stream_events: bool = False,
    exclude_sidechains: bool = False,
) -> Iterator[Message]:
    """Replay stored JSONL entries as wire-format Messages.

    Yields UserMessage and AssistantMessage in file order, preserving
    the one-entry-per-content-block granularity of the storage format.

    Args:
        entries: JSONL entries to replay (from read_session or similar).
        include_progress: If True, also yield ToolProgressMessage for
            tool_progress entries.
        include_stream_events: If True, inject synthetic StreamEvent
            messages (message_start/stop, content_block_start/delta/stop)
            around each content block. Each text/thinking block gets a
            single delta with the full content. Useful for consumers that
            expect the full stream envelope structure.
        exclude_sidechains: If True, skip entries marked as sidechain
            (internal Claude Code context-retrieval calls).

    Yields:
        Wire-format Message objects (UserMessage, AssistantMessage,
        StreamEvent, and optionally ToolProgressMessage).
    """
    if exclude_sidechains:
        entries = _filter_sidechains(entries)
    if include_stream_events:
        yield from _replay_with_stream_events(entries, include_progress=include_progress)
    else:
        yield from _replay_basic(entries, include_progress=include_progress)


def replay_session(
    session_path: Path,
    *,
    include_progress: bool = False,
    include_stream_events: bool = False,
    exclude_sidechains: bool = False,
) -> Iterator[Message]:
    """Replay a stored session file as wire-format Messages.

    Reads a JSONL session file and yields its entries converted to
    wire-format Message objects. The sequence matches what a live
    ``receive_messages()`` call would produce, minus token-level deltas
    and terminal events (ResultMessage, RateLimitMessage).

    Args:
        session_path: Path to the .jsonl session file.
        include_progress: If True, also yield ToolProgressMessage entries.
        include_stream_events: If True, inject synthetic StreamEvent
            messages around each content block (see :func:`replay_entries`).
        exclude_sidechains: If True, skip sidechain entries.

    Yields:
        Wire-format Message objects in conversation order.
    """
    entries = read_session(session_path)
    yield from replay_entries(
        entries,
        include_progress=include_progress,
        include_stream_events=include_stream_events,
        exclude_sidechains=exclude_sidechains,
    )
