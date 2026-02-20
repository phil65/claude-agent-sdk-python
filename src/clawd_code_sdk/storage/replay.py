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

import json as _json
from typing import TYPE_CHECKING, Literal

from clawd_code_sdk.models.content_blocks import (
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
)
from clawd_code_sdk.models.messages import (
    AssistantMessage,
    StreamEvent,
    ToolProgressMessage,
    UserMessage,
)
from clawd_code_sdk.storage.helpers import read_session
from clawd_code_sdk.storage.models import (
    ClaudeApiMessage,
    ClaudeAssistantEntry,
    ClaudeImageBlock,
    ClaudeProgressEntry,
    ClaudeSummaryEntry,
    ClaudeTextBlock,
    ClaudeThinkingBlock,
    ClaudeToolProgressData,
    ClaudeToolResultBlock,
    ClaudeToolUseBlock,
    ClaudeUsage,
    ClaudeUserEntry,
)


if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence
    from pathlib import Path

    from anthropic.types import RawMessageStreamEvent

    from clawd_code_sdk.models.content_blocks import ContentBlock
    from clawd_code_sdk.models.messages import Message
    from clawd_code_sdk.storage.models import ClaudeContentBlock, ClaudeJSONLEntry


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
        case ClaudeThinkingBlock(thinking=thinking, signature=signature):
            return ThinkingBlock(thinking=thinking, signature=signature or "")
        case ClaudeToolUseBlock(id=block_id, name=name, input=tool_input):
            return ToolUseBlock(id=block_id, name=name, input=tool_input)
        case ClaudeToolResultBlock(tool_use_id=tool_use_id, content=content, is_error=is_error):
            return ToolResultBlock(tool_use_id=tool_use_id, content=content, is_error=is_error)
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
    content = _convert_content_blocks(entry.message.content)
    # AssistantMessage.content must be Sequence[ContentBlock], not str.
    return AssistantMessage(
        content=[TextBlock(text=content)] if isinstance(content, str) else content,
        model=entry.message.model if isinstance(entry.message, ClaudeApiMessage) else "unknown",
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


def _convert_summary_entry(entry: ClaudeSummaryEntry) -> UserMessage:
    """Convert a summary entry to a synthetic UserMessage."""
    return UserMessage(
        uuid=entry.leaf_uuid,
        session_id=entry.session_id or "",
        content=entry.summary,
        isSynthetic=True,
    )


# =============================================================================
# Synthetic StreamEvent construction
# =============================================================================


def _make_stream_event(event: RawMessageStreamEvent, *, session_id: str, uuid: str) -> StreamEvent:
    """Wrap an Anthropic raw stream event into a wire-format StreamEvent."""
    return StreamEvent(event=event, session_id=session_id, uuid=uuid)


def _make_message_start(*, msg_id: str, model: str, session_id: str, uuid: str) -> StreamEvent:
    """Create a synthetic message_start StreamEvent."""
    from anthropic.types import (
        Message as AnthropicMessage,
        RawMessageStartEvent,
        Usage as AnthropicUsage,
    )

    message = AnthropicMessage(
        id=msg_id,
        type="message",
        role="assistant",
        content=[],
        model=model,
        usage=AnthropicUsage(input_tokens=0, output_tokens=0),
    )
    start_event = RawMessageStartEvent(type="message_start", message=message)
    return _make_stream_event(start_event, session_id=session_id, uuid=uuid)


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

    usage = MessageDeltaUsage(output_tokens=0)
    delta = RawMessageDelta(stop_reason=_coerce_stop_reason(stop_reason), stop_sequence=None)
    delta_event = RawMessageDeltaEvent(type="message_delta", delta=delta, usage=usage)
    return _make_stream_event(delta_event, session_id=session_id, uuid=uuid)


def _make_message_stop(*, session_id: str, uuid: str) -> StreamEvent:
    """Create a synthetic message_stop StreamEvent."""
    from anthropic.types import RawMessageStopEvent

    stop_event = RawMessageStopEvent(type="message_stop")
    return _make_stream_event(stop_event, session_id=session_id, uuid=uuid)


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
        case ClaudeToolUseBlock(id=block_id, name=name):
            content_block = AToolUseBlock(type="tool_use", id=block_id, name=name, input={})
        case _:
            # No stream event for tool_result or image blocks
            content_block = ATextBlock(type="text", text="")
    start_event = RawContentBlockStartEvent(
        type="content_block_start", index=index, content_block=content_block
    )
    return _make_stream_event(start_event, session_id=session_id, uuid=uuid)


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
    delta_event = RawContentBlockDeltaEvent(type="content_block_delta", index=index, delta=delta)
    return _make_stream_event(delta_event, session_id=session_id, uuid=uuid)


def _make_block_stop(*, index: int, session_id: str, uuid: str) -> StreamEvent:
    """Create a synthetic content_block_stop StreamEvent."""
    from anthropic.types import RawContentBlockStopEvent

    stop_event = RawContentBlockStopEvent(type="content_block_stop", index=index)
    return _make_stream_event(stop_event, session_id=session_id, uuid=uuid)


# =============================================================================
# Replay iterators
# =============================================================================


def _is_tool_result_entry(entry: ClaudeUserEntry) -> bool:
    """Check if a user entry is a synthetic tool_result (vs. an actual user prompt)."""
    if isinstance(entry.message.content, str):
        return False
    return all(b.type == "tool_result" for b in entry.message.content)


def _replay_basic(
    entries: Iterable[ClaudeJSONLEntry],
    *,
    include_progress: bool,
    include_summaries: bool = False,
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
            case ClaudeSummaryEntry() if include_summaries:
                yield _convert_summary_entry(entry)


def _get_assistant_msg_id(entry: ClaudeAssistantEntry) -> str | None:
    """Extract the API message ID from an assistant entry."""
    return entry.message.id if isinstance(entry.message, ClaudeApiMessage) else None


def _get_assistant_model(entry: ClaudeAssistantEntry) -> str:
    """Extract the model name from an assistant entry."""
    return entry.message.model if isinstance(entry.message, ClaudeApiMessage) else "unknown"


def _get_assistant_stop_reason(entry: ClaudeAssistantEntry) -> str | None:
    """Extract the stop reason from an assistant entry."""
    return entry.message.stop_reason if isinstance(entry.message, ClaudeApiMessage) else None


def _get_first_stored_block(entry: ClaudeAssistantEntry) -> ClaudeContentBlock | None:
    """Get the first content block from a stored assistant entry."""
    return content[0] if isinstance((content := entry.message.content), list) and content else None


def _replay_with_stream_events(
    entries: Iterable[ClaudeJSONLEntry],
    *,
    include_progress: bool,
    include_summaries: bool = False,
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
        match entry_list[i]:
            case ClaudeAssistantEntry() as entry:
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
                    match entry_list[i]:
                        case ClaudeUserEntry() as e if _is_tool_result_entry(e):
                            yield _convert_user_entry(e)
                            i += 1
                        case ClaudeProgressEntry() as e if include_progress:
                            if (msg := _convert_progress_entry(e)) is not None:
                                yield msg
                            i += 1
                        case ClaudeProgressEntry():
                            i += 1
                        case _:
                            break

                # → message_stop
                yield _make_message_stop(
                    session_id=last_assistant.session_id, uuid=last_assistant.uuid
                )

            case ClaudeUserEntry() as entry:
                yield _convert_user_entry(entry)
                i += 1

            case ClaudeProgressEntry() as entry if include_progress:
                if (msg := _convert_progress_entry(entry)) is not None:
                    yield msg
                i += 1

            case ClaudeSummaryEntry() as entry if include_summaries:
                yield _convert_summary_entry(entry)
                i += 1

            case _:
                i += 1  # Skip non-message entries (queue ops, etc.)


# Entry types that carry a uuid for parent-chain traversal
_UuidEntry = ClaudeUserEntry | ClaudeAssistantEntry | ClaudeProgressEntry


def _resolve_thread(
    entries: list[ClaudeJSONLEntry],
    leaf_uuid: str | None = None,
) -> list[ClaudeJSONLEntry]:
    """Resolve a conversation thread by walking the parent_uuid chain.

    Given a list of entries and an optional leaf UUID, returns only the entries
    that form a single conversation thread from root to leaf. Entries without
    a uuid (summaries, queue ops, file history) are excluded.

    If ``leaf_uuid`` is None, the last entry with a uuid in the list is used.
    """
    by_uuid: dict[str, ClaudeJSONLEntry] = {}
    last_uuid: str | None = None
    for jsonl_entry in entries:
        match jsonl_entry:
            case ClaudeUserEntry() | ClaudeAssistantEntry() | ClaudeProgressEntry():
                by_uuid[jsonl_entry.uuid] = jsonl_entry
                last_uuid = jsonl_entry.uuid

    target = leaf_uuid or last_uuid
    if target is None:
        return []

    # Walk backwards from leaf to root
    chain: list[ClaudeJSONLEntry] = []
    current: str | None = target
    seen: set[str] = set()
    while current is not None and current not in seen:
        seen.add(current)
        entry = by_uuid.get(current)
        if entry is None:
            break
        chain.append(entry)
        match entry:
            case ClaudeUserEntry() | ClaudeAssistantEntry() | ClaudeProgressEntry():
                current = entry.parent_uuid
            case _:
                current = None

    chain.reverse()
    return chain


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
    include_summaries: bool = False,
    exclude_sidechains: bool = False,
    leaf_uuid: str | None = None,
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
        include_summaries: If True, yield summary entries as synthetic
            UserMessage instances (with ``isSynthetic=True``) at their
            file-order position.
        exclude_sidechains: If True, skip entries marked as sidechain
            (internal Claude Code context-retrieval calls).
        leaf_uuid: If set, resolve the conversation thread by walking
            parent_uuid chains from this leaf to the root. Only entries
            on that chain are replayed. If None, file order is used.

    Yields:
        Wire-format Message objects (UserMessage, AssistantMessage,
        StreamEvent, and optionally ToolProgressMessage).
    """
    if leaf_uuid is not None:
        entries = _resolve_thread(list(entries), leaf_uuid=leaf_uuid)
    if exclude_sidechains:
        entries = _filter_sidechains(entries)
    if include_stream_events:
        yield from _replay_with_stream_events(
            entries, include_progress=include_progress, include_summaries=include_summaries
        )
    else:
        yield from _replay_basic(
            entries, include_progress=include_progress, include_summaries=include_summaries
        )


def replay_session(
    session_path: Path,
    *,
    include_progress: bool = False,
    include_stream_events: bool = False,
    include_summaries: bool = False,
    exclude_sidechains: bool = False,
    leaf_uuid: str | None = None,
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
        include_summaries: If True, include summary entries.
        exclude_sidechains: If True, skip sidechain entries.
        leaf_uuid: If set, resolve the thread from this leaf UUID.

    Yields:
        Wire-format Message objects in conversation order.
    """
    entries = read_session(session_path)
    yield from replay_entries(
        entries,
        include_progress=include_progress,
        include_stream_events=include_stream_events,
        include_summaries=include_summaries,
        exclude_sidechains=exclude_sidechains,
        leaf_uuid=leaf_uuid,
    )


# =============================================================================
# Usage extraction
# =============================================================================


def extract_usage(entries: Iterable[ClaudeJSONLEntry]) -> ClaudeUsage:
    """Extract deduplicated aggregate token usage from stored entries.

    Storage duplicates usage data across all content-block entries that
    share the same API ``message.id``. This function deduplicates by
    ``message.id`` and sums across all unique API calls.

    Args:
        entries: JSONL entries (from ``read_session`` or similar).

    Returns:
        Aggregate :class:`~clawd_code_sdk.storage.models.ClaudeUsage`
        with deduplicated totals.
    """
    seen_ids: set[str] = set()
    total = ClaudeUsage()
    for entry in entries:
        if not isinstance(entry, ClaudeAssistantEntry):
            continue
        msg = entry.message
        if not isinstance(msg, ClaudeApiMessage):
            continue
        if msg.id in seen_ids:
            continue
        seen_ids.add(msg.id)
        total.input_tokens += msg.usage.input_tokens
        total.output_tokens += msg.usage.output_tokens
        total.cache_creation_input_tokens += msg.usage.cache_creation_input_tokens
        total.cache_read_input_tokens += msg.usage.cache_read_input_tokens
    return total
