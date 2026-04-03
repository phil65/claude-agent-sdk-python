"""Replay Claude Code sessions from stored JSONL transcripts.

Reassembles stored JSONL entries into SDK Message types, enabling consumers
to process historical sessions with the same code that handles live streams.
Storage and wire formats share the same content block types, so no conversion
is needed at the block level.

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
    - InitSystemMessage(init): Session initialization metadata (tools, model, etc.).
    - RateLimitMessage: Rate limit events are transient.

Partially reconstructible (with ``include_result=True``):
    - ResultMessage: Synthetic messages are emitted at each turn boundary.
      Token usage (deduplicated) and error status are available. Cost
      (``total_cost_usd``), duration (``duration_ms``, ``duration_api_ms``),
      and ``model_usage`` are not stored and are set to zero/None.

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
from typing import TYPE_CHECKING, assert_never

from anthropic.types.beta import BetaMessage, BetaRawMessageStartEvent, BetaUsage

from clawd_code_sdk.models import (
    AssistantMessage,
    AssistantMessageContent,
    ImageBlock,
    MessageParam,
    ResultErrorMessage,
    ResultSuccessMessage,
    StreamEvent,
    TextBlock,
    ThinkingBlock,
    ToolProgressMessage,
    ToolResultBlock,
    ToolUseBlock,
    Usage,
    UserMessage,
)
from clawd_code_sdk.storage.helpers import read_session
from clawd_code_sdk.storage.models import (
    ClaudeApiMessage,
    ClaudeAssistantEntry,
    ClaudeProgressEntry,
    ClaudeSummaryEntry,
    ClaudeToolProgressData,
    ClaudeUsage,
    ClaudeUserEntry,
)


if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence
    from pathlib import Path

    from clawd_code_sdk.models import AssistantContentBlock, ContentBlock, Message, StopReason
    from clawd_code_sdk.storage.models import ClaudeJSONLEntry


# =============================================================================
# Entry conversion (storage → wire format)
# =============================================================================


def _convert_user_entry(entry: ClaudeUserEntry) -> UserMessage:
    """Convert a stored user entry to a wire-format UserMessage."""
    return UserMessage(
        uuid=entry.uuid,
        session_id=entry.session_id,
        message=MessageParam(content=entry.message.content, role="user"),
        tool_use_result=entry.tool_use_result,
        is_replay=True,
    )


def _convert_assistant_entry(entry: ClaudeAssistantEntry) -> AssistantMessage:
    """Convert a stored assistant entry to a wire-format AssistantMessage."""
    raw = entry.message.content
    blocks: Sequence[AssistantContentBlock] = (
        [TextBlock(text=raw)] if isinstance(raw, str) else list(raw)
    )
    model = entry.message.model
    msg_id = entry.message.id
    return AssistantMessage(
        message=AssistantMessageContent(content=blocks, model=model, id=msg_id),
        uuid=entry.uuid,
        session_id=entry.session_id,
        error="unknown" if entry.is_api_error_message else None,
    )


def _convert_progress_entry(
    entry: ClaudeProgressEntry, data: ClaudeToolProgressData
) -> ToolProgressMessage:
    """Convert a stored tool_progress entry to a wire-format ToolProgressMessage."""
    return ToolProgressMessage(
        uuid=entry.uuid,
        session_id=entry.session_id,
        tool_use_id=data.tool_use_id or "",
        tool_name=data.tool_name or "",
        parent_tool_use_id=data.parent_tool_use_id,
        elapsed_time_seconds=data.elapsed_time_seconds or 0.0,
    )


def _convert_summary_entry(entry: ClaudeSummaryEntry) -> UserMessage:
    """Convert a summary entry to a synthetic UserMessage."""
    return UserMessage(
        uuid=entry.leaf_uuid,
        session_id=entry.session_id or "",
        message=MessageParam(content=entry.summary, role="user"),
        is_synthetic=True,
    )


# =============================================================================
# Synthetic StreamEvent construction
# =============================================================================


def _make_message_start(*, msg_id: str, model: str, session_id: str, uuid: str) -> StreamEvent:
    """Create a synthetic message_start StreamEvent."""
    message = BetaMessage(
        id=msg_id,
        type="message",
        role="assistant",
        content=[],
        model=model,
        usage=BetaUsage(input_tokens=0, output_tokens=0),
    )
    start_event = BetaRawMessageStartEvent(type="message_start", message=message)
    return StreamEvent(event=start_event, session_id=session_id, uuid=uuid)


def _make_block_start(
    block: ContentBlock,
    *,
    index: int,
    session_id: str,
    uuid: str,
) -> Iterator[StreamEvent]:
    """Create a synthetic content_block_start StreamEvent for a stored block."""
    match block:
        case TextBlock():
            yield StreamEvent.block_start_text(index=index, session_id=session_id, uuid=uuid)
        case ThinkingBlock():
            yield StreamEvent.block_start_thinking(index=index, session_id=session_id, uuid=uuid)
        case ToolUseBlock(id=block_id, name=name):
            yield StreamEvent.block_start_tool_use(
                tool_use_id=block_id, name=name, index=index, session_id=session_id, uuid=uuid
            )
        case ToolResultBlock() | ImageBlock():
            return
        case _ as unreachable:
            assert_never(unreachable)


def _make_block_delta(
    block: ContentBlock,
    *,
    index: int,
    session_id: str,
    uuid: str,
) -> Iterator[StreamEvent]:
    """Create a synthetic content_block_delta StreamEvent with full block content."""
    match block:
        case TextBlock(text=text):
            yield StreamEvent.block_text_delta(
                text=text,
                index=index,
                session_id=session_id,
                uuid=uuid,
            )
        case ThinkingBlock(thinking=thinking):
            yield StreamEvent.block_thinking_delta(
                thinking=thinking,
                index=index,
                session_id=session_id,
                uuid=uuid,
            )
        case ToolUseBlock(input=input_):
            yield StreamEvent.block_tool_json_delta(
                partial_json=_json.dumps(input_),
                index=index,
                session_id=session_id,
                uuid=uuid,
            )
        case ToolResultBlock() | ImageBlock():
            return
        case _ as unreachable:
            assert_never(unreachable)


def _make_synthetic_result(
    turn_entries: Sequence[ClaudeJSONLEntry],
) -> ResultSuccessMessage | ResultErrorMessage:
    """Create a synthetic ResultMessage from a turn's stored entries.

    Reconstructs what is available from storage:
    - ``usage``: Deduplicated token counts from ``ClaudeApiMessage.usage``.
    - ``is_error`` / ``subtype``: From ``is_api_error_message``.
    - ``stop_reason``: From the last assistant entry's API stop_reason
      (often ``None`` in practice — storage rarely preserves it).
    - ``num_turns``: Number of distinct API calls (unique ``message.id``).

    Fields that cannot be reconstructed are set to zero or ``None``:
    ``duration_ms``, ``duration_api_ms``, ``total_cost_usd``, ``model_usage``.
    """
    seen_msg_ids: set[str] = set()
    total_usage = ClaudeUsage()
    last_uuid = ""
    session_id = ""
    is_error = False
    stop_reason: StopReason | None = None

    for entry in turn_entries:
        match entry:
            case ClaudeAssistantEntry(
                message=ClaudeApiMessage(id=msg_id, stop_reason=reason, usage=usage),
                uuid=last_uuid,
                session_id=session_id,
                is_api_error_message=is_api_error_message,
            ):
                if is_api_error_message:
                    is_error = True
                if msg_id not in seen_msg_ids:
                    seen_msg_ids.add(msg_id)
                    total_usage.accumulate(usage)
                if reason is not None:
                    stop_reason = reason

    token_usage = Usage(
        input_tokens=total_usage.input_tokens,
        output_tokens=total_usage.output_tokens,
        cache_creation_input_tokens=total_usage.cache_creation_input_tokens,
        cache_read_input_tokens=total_usage.cache_read_input_tokens,
    )
    common = {
        "uuid": last_uuid or "synthetic",
        "session_id": session_id,
        "duration_ms": 0,
        "duration_api_ms": 0,
        "is_error": is_error,
        "num_turns": len(seen_msg_ids),
        "total_cost_usd": 0.0,
        "usage": token_usage,
        "stop_reason": stop_reason,
    }
    if is_error:
        return ResultErrorMessage(**common, subtype="error_during_execution")  # type: ignore[arg-type]
    return ResultSuccessMessage(**common)  # type: ignore[arg-type]


# =============================================================================
# Replay iterators
# =============================================================================


def _replay_basic(
    entries: Iterable[ClaudeJSONLEntry],
    *,
    include_progress: bool,
    include_summaries: bool = False,
    include_result: bool = False,
) -> Iterator[Message]:
    """Replay entries without stream events (basic mode)."""
    turn_entries: list[ClaudeJSONLEntry] = []

    for entry in entries:
        match entry:
            case ClaudeUserEntry() if not entry.is_tool_result:
                # Non-tool-result user entry = new turn boundary
                if include_result and turn_entries:
                    yield _make_synthetic_result(turn_entries)
                turn_entries = []
                yield _convert_user_entry(entry)
            case ClaudeUserEntry():
                # Tool-result user entry — part of current turn
                turn_entries.append(entry)
                yield _convert_user_entry(entry)
            case ClaudeAssistantEntry():
                turn_entries.append(entry)
                yield _convert_assistant_entry(entry)
            case ClaudeProgressEntry(data=ClaudeToolProgressData() as data) if include_progress:
                yield _convert_progress_entry(entry, data)
            case ClaudeSummaryEntry() if include_summaries:
                yield _convert_summary_entry(entry)

    # Emit result for the final turn
    if include_result and turn_entries:
        yield _make_synthetic_result(turn_entries)


def _get_assistant_msg_id(entry: ClaudeAssistantEntry) -> str | None:
    """Extract the API message ID from an assistant entry."""
    return entry.message.id if isinstance(entry.message, ClaudeApiMessage) else None


def _get_assistant_model(entry: ClaudeAssistantEntry) -> str:
    """Extract the model name from an assistant entry."""
    return entry.message.model if isinstance(entry.message, ClaudeApiMessage) else "unknown"


def _get_assistant_stop_reason(entry: ClaudeAssistantEntry) -> StopReason | None:
    """Extract the stop reason from an assistant entry."""
    return entry.message.stop_reason if isinstance(entry.message, ClaudeApiMessage) else None


def _replay_with_stream_events(
    entries: Iterable[ClaudeJSONLEntry],
    *,
    include_progress: bool,
    include_summaries: bool = False,
    include_result: bool = False,
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
        ResultMessage (synthetic, if include_result)
    """
    entry_list = list(entries)
    i = 0
    turn_entries: list[ClaudeJSONLEntry] = []

    while i < len(entry_list):
        match entry_list[i]:
            case ClaudeAssistantEntry(uuid=uuid, session_id=session_id) as entry:
                # Start of an API response group — collect all entries with same msg_id
                msg_id = _get_assistant_msg_id(entry) or uuid
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
                turn_entries.extend(group)
                # Get stop_reason from the last entry in the group
                last_assistant = group[-1]
                assert isinstance(last_assistant, ClaudeAssistantEntry)
                stop_reason = _get_assistant_stop_reason(last_assistant)
                # → message_start
                yield _make_message_start(
                    msg_id=msg_id,
                    model=model,
                    session_id=session_id,
                    uuid=uuid,
                )

                # → per-block events
                for block_index, assistant_entry in enumerate(group):
                    assert isinstance(assistant_entry, ClaudeAssistantEntry)
                    stored_block = (
                        c[0]
                        if isinstance((c := assistant_entry.message.content), list) and c
                        else None
                    )

                    if stored_block is not None:
                        yield from _make_block_start(
                            stored_block,
                            index=block_index,
                            session_id=assistant_entry.session_id,
                            uuid=assistant_entry.uuid,
                        )
                        yield from _make_block_delta(
                            stored_block,
                            index=block_index,
                            session_id=assistant_entry.session_id,
                            uuid=assistant_entry.uuid,
                        )

                    yield _convert_assistant_entry(assistant_entry)

                    if stored_block is not None:
                        yield StreamEvent.block_stop(
                            index=block_index,
                            session_id=assistant_entry.session_id,
                            uuid=assistant_entry.uuid,
                        )
                # → message_delta
                yield StreamEvent.message_delta(
                    stop_reason=stop_reason,
                    session_id=last_assistant.session_id,
                    uuid=last_assistant.uuid,
                )

                # Collect tool_result user entries that follow this group
                while i < len(entry_list):
                    match entry_list[i]:
                        case ClaudeUserEntry() as e if e.is_tool_result:
                            yield _convert_user_entry(e)
                            i += 1
                        case ClaudeProgressEntry(data=ClaudeToolProgressData() as data) as e if (
                            include_progress
                        ):
                            yield _convert_progress_entry(e, data)
                            i += 1
                        case ClaudeProgressEntry():
                            i += 1
                        case _:
                            break

                # → message_stop
                yield StreamEvent.message_stop(
                    session_id=last_assistant.session_id, uuid=last_assistant.uuid
                )

            case ClaudeUserEntry() as entry:
                # Non-tool-result user entry = new turn boundary
                # (tool_result entries are consumed inside the assistant group above)
                if include_result and turn_entries:
                    yield _make_synthetic_result(turn_entries)
                turn_entries = []
                yield _convert_user_entry(entry)
                i += 1

            case ClaudeProgressEntry(data=ClaudeToolProgressData() as data) as entry if (
                include_progress
            ):
                yield _convert_progress_entry(entry, data)
                i += 1

            case ClaudeSummaryEntry() as entry if include_summaries:
                yield _convert_summary_entry(entry)
                i += 1

            case _:
                i += 1  # Skip non-message entries (queue ops, etc.)

    # Emit result for the final turn
    if include_result and turn_entries:
        yield _make_synthetic_result(turn_entries)


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
    include_result: bool = False,
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
        include_result: If True, emit a synthetic ``ResultMessage`` at
            the end of each conversational turn. The synthetic message
            includes deduplicated token usage and error status from
            storage. Fields not available in storage (``total_cost_usd``,
            ``duration_ms``, ``duration_api_ms``) are set to zero/None.
        exclude_sidechains: If True, skip entries marked as sidechain
            (internal Claude Code context-retrieval calls).
        leaf_uuid: If set, resolve the conversation thread by walking
            parent_uuid chains from this leaf to the root. Only entries
            on that chain are replayed. If None, file order is used.

    Yields:
        Wire-format Message objects (UserMessage, AssistantMessage,
        StreamEvent, ResultMessage, and optionally ToolProgressMessage).
    """
    if leaf_uuid is not None:
        entries = _resolve_thread(list(entries), leaf_uuid=leaf_uuid)
    if exclude_sidechains:
        entries = _filter_sidechains(entries)
    if include_stream_events:
        yield from _replay_with_stream_events(
            entries,
            include_progress=include_progress,
            include_summaries=include_summaries,
            include_result=include_result,
        )
    else:
        yield from _replay_basic(
            entries,
            include_progress=include_progress,
            include_summaries=include_summaries,
            include_result=include_result,
        )


def replay_session(
    session_path: Path,
    *,
    include_progress: bool = False,
    include_stream_events: bool = False,
    include_summaries: bool = False,
    include_result: bool = False,
    exclude_sidechains: bool = False,
    leaf_uuid: str | None = None,
) -> Iterator[Message]:
    """Replay a stored session file as wire-format Messages.

    Reads a JSONL session file and yields its entries converted to
    wire-format Message objects. The sequence matches what a live
    ``receive_messages()`` call would produce, minus token-level deltas
    and terminal events (RateLimitMessage). When ``include_result=True``,
    a synthetic ``ResultMessage`` is emitted at each turn boundary with
    whatever data is available in storage.

    Args:
        session_path: Path to the .jsonl session file.
        include_progress: If True, also yield ToolProgressMessage entries.
        include_stream_events: If True, inject synthetic StreamEvent
            messages around each content block (see :func:`replay_entries`).
        include_summaries: If True, include summary entries.
        include_result: If True, emit synthetic ResultMessage at each
            turn boundary (see :func:`replay_entries`).
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
        include_result=include_result,
        exclude_sidechains=exclude_sidechains,
        leaf_uuid=leaf_uuid,
    )
