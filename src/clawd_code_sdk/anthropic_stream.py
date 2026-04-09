"""Adapter that translates Claude Code event streams to Anthropic raw stream events.

Converts the multi-turn ``receive_response()`` message stream into a sequence
of ``BetaRawMessageStreamEvent`` objects, identical to what the Anthropic SDK
emits during streaming.

Live ``StreamEvent`` messages are passed through directly.  ``AssistantMessage``
messages that arrive *without* preceding stream events (non-streaming mode,
replays, reconnection) are synthesized into the full event sequence
(message_start → content_block_start → delta → stop → message_delta → message_stop).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, assert_never

from anthropic.types.beta import (
    BetaMessage,
    BetaRawContentBlockStartEvent,
    BetaRawContentBlockStopEvent,
    BetaRawMessageDeltaEvent,
    BetaRawMessageStartEvent,
    BetaRawMessageStopEvent,
    BetaTextBlock as ATextBlock,
    BetaTextDelta,
    BetaThinkingBlock as AThinkingBlock,
    BetaThinkingDelta,
    BetaToolUseBlock as AToolUseBlock,
    BetaUsage,
)
from anthropic.types.beta.beta_raw_content_block_delta_event import (
    BetaRawContentBlockDeltaEvent,
)
from anthropic.types.beta.beta_raw_message_delta_event import Delta as BetaRawMessageDelta

from clawd_code_sdk.models import (
    AssistantMessage,
    StreamEvent,
)
from clawd_code_sdk.models.content_blocks import (
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
)


if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from anthropic.types.beta import (
        BetaInputJSONDelta as BetaInputJSONDeltaType,
        BetaRawMessageStreamEvent,
    )

    from clawd_code_sdk.models import Message


async def to_anthropic_events(
    messages: AsyncIterator[Message],
) -> AsyncIterator[BetaRawMessageStreamEvent]:
    """Convert a Claude Code message stream to Anthropic raw stream events.

    Handles two cases:

    1. **Live streaming** — ``StreamEvent`` messages whose ``.event`` is already
       a ``BetaRawMessageStreamEvent``.  These are yielded as-is.

    2. **Completed messages** — ``AssistantMessage`` that arrive without
       preceding ``StreamEvent`` (non-streaming, reconnection, replays).
       These are decomposed into the full synthetic event sequence.

    All other message types (``UserMessage``, ``ResultMessage``,
    ``ToolProgressMessage``, system messages, etc.) are silently skipped.

    Args:
        messages: Async iterator of Claude Code messages, typically from
            ``client.receive_response()`` or ``client.receive_messages()``.

    Yields:
        ``BetaRawMessageStreamEvent`` in the same order and structure
        as a native Anthropic streaming response.
    """
    saw_stream_events = False

    async for msg in messages:
        if isinstance(msg, StreamEvent):
            saw_stream_events = True
            yield msg.event

        elif isinstance(msg, AssistantMessage):
            if saw_stream_events:
                # Stream events already covered this message — the
                # AssistantMessage is the completed snapshot.  Skip it
                # so we don't duplicate content.
                #
                # Reset for the next LLM call in the agentic loop.
                saw_stream_events = False
                continue

            # No stream events preceded this message — synthesize the
            # full event sequence from the completed content blocks.
            for event in _synthesize_events(msg):
                yield event
            saw_stream_events = False


def _synthesize_events(
    msg: AssistantMessage,
) -> list[BetaRawMessageStreamEvent]:
    """Synthesize a complete Anthropic event sequence from a completed message."""
    events: list[BetaRawMessageStreamEvent] = []
    am = msg.message

    # message_start
    beta_msg = BetaMessage(
        id=am.id,
        type="message",
        role="assistant",
        content=[],
        model=am.model,
        stop_reason=None,
        stop_sequence=None,
        usage=BetaUsage(input_tokens=0, output_tokens=0),
    )
    events.append(BetaRawMessageStartEvent(type="message_start", message=beta_msg))

    # content blocks
    for index, block in enumerate(am.content):
        # content_block_start
        start_block = _to_anthropic_block(block)
        if start_block is None:
            continue
        events.append(
            BetaRawContentBlockStartEvent(
                type="content_block_start",
                index=index,
                content_block=start_block,
            )
        )

        # content_block_delta
        delta = _to_anthropic_delta(block)
        if delta is not None:
            events.append(
                BetaRawContentBlockDeltaEvent(
                    type="content_block_delta",
                    index=index,
                    delta=delta,
                )
            )

        # content_block_stop
        events.append(BetaRawContentBlockStopEvent(type="content_block_stop", index=index))

    # message_delta
    from anthropic.types.beta import BetaMessageDeltaUsage

    events.append(
        BetaRawMessageDeltaEvent(
            type="message_delta",
            delta=BetaRawMessageDelta(stop_reason=am.stop_reason),
            usage=BetaMessageDeltaUsage(output_tokens=0),
        )
    )

    # message_stop
    events.append(BetaRawMessageStopEvent(type="message_stop"))

    return events


def _to_anthropic_block(
    block: TextBlock | ThinkingBlock | ToolUseBlock,
) -> ATextBlock | AThinkingBlock | AToolUseBlock | None:
    """Convert a content block to its Anthropic start-event form (empty content)."""
    match block:
        case TextBlock():
            return ATextBlock(type="text", text="")
        case ThinkingBlock():
            return AThinkingBlock(type="thinking", thinking="", signature="")
        case ToolUseBlock():
            return AToolUseBlock(type="tool_use", id=block.id, name=block.name, input={})
        case _ as unreachable:
            assert_never(unreachable)


def _to_anthropic_delta(
    block: TextBlock | ThinkingBlock | ToolUseBlock,
) -> BetaTextDelta | BetaThinkingDelta | BetaInputJSONDeltaType | None:
    """Convert a content block's content into a single delta event."""
    from anthropic.types.beta import BetaInputJSONDelta

    match block:
        case TextBlock(text=text) if text:
            return BetaTextDelta(type="text_delta", text=text)
        case ThinkingBlock(thinking=thinking) if thinking:
            return BetaThinkingDelta(type="thinking_delta", thinking=thinking)
        case ToolUseBlock(input=input_) if input_:
            return BetaInputJSONDelta(
                type="input_json_delta",
                partial_json=json.dumps(input_),
            )
        case _:
            return None
