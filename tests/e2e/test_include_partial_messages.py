"""End-to-end tests for include_partial_messages option with real Claude API calls.

These tests verify that the SDK properly handles partial message streaming,
including StreamEvent parsing and message interleaving.
"""

from anthropic.types.beta import BetaRawContentBlockDeltaEvent, BetaThinkingDelta
import pytest

from clawd_code_sdk import ClaudeSDKClient
from clawd_code_sdk.models import (
    AssistantMessage,
    ClaudeAgentOptions,
    InitSystemMessage,
    ResultMessage,
    StreamEvent,
    TextBlock,
    ThinkingBlock,
    ThinkingConfigEnabled,
)


@pytest.mark.e2e
async def test_include_partial_messages_stream_events():
    """Test that include_partial_messages produces StreamEvent messages."""
    options = ClaudeAgentOptions(model="sonnet", max_turns=2, env={"MAX_THINKING_TOKENS": "8000"})

    async with ClaudeSDKClient(options) as client:
        # Send a simple prompt that will generate streaming response with thinking
        await client.query("Think of three jokes, then tell one")
        collected_messages = [i async for i in client.receive_response()]

    # Verify we got the expected message types
    message_types = [type(msg).__name__ for msg in collected_messages]
    # Should have an InitSystemMessage somewhere early in the sequence
    init_msgs = [msg for msg in collected_messages if isinstance(msg, InitSystemMessage)]
    assert len(init_msgs) == 1, f"Expected exactly one InitSystemMessage, got {len(init_msgs)}"
    assert init_msgs[0].subtype == "init"
    # Should have multiple StreamEvent messages
    stream_events = [msg for msg in collected_messages if isinstance(msg, StreamEvent)]
    assert len(stream_events) > 0, "No StreamEvent messages received"
    # Check for expected StreamEvent types
    event_types = [event.event.type for event in stream_events]
    assert "message_start" in event_types, "No message_start StreamEvent"
    assert "content_block_start" in event_types, "No content_block_start StreamEvent"
    assert "content_block_delta" in event_types, "No content_block_delta StreamEvent"
    assert "content_block_stop" in event_types, "No content_block_stop StreamEvent"
    assert "message_stop" in event_types, "No message_stop StreamEvent"
    # Should have AssistantMessage messages with thinking and text
    assistant_msgs = [msg for msg in collected_messages if isinstance(msg, AssistantMessage)]
    assert len(assistant_msgs) >= 1, "No AssistantMessage received"
    # Check for thinking block in at least one AssistantMessage
    has_thinking = any(any(isinstance(b, ThinkingBlock) for b in m.content) for m in assistant_msgs)
    assert has_thinking, "No ThinkingBlock found in AssistantMessages"
    # Check for text block (the joke) in at least one AssistantMessage
    has_text = any(any(isinstance(b, TextBlock) for b in msg.content) for msg in assistant_msgs)
    assert has_text, "No TextBlock found in AssistantMessages"
    # Should contain a ResultMessage
    result_msgs = [msg for msg in collected_messages if isinstance(msg, ResultMessage)]
    assert len(result_msgs) >= 1, "No ResultMessage received"
    assert result_msgs[-1].subtype == "success"


@pytest.mark.e2e
async def test_include_partial_messages_thinking_deltas():
    """Test that thinking content is streamed incrementally via deltas."""
    thinking = ThinkingConfigEnabled(budget_tokens=8000)
    options = ClaudeAgentOptions(model="claude-sonnet-4-5", max_turns=2, thinking=thinking)
    async with ClaudeSDKClient(options) as client:
        await client.query("Ultrathink step by step about what 2 + 2 equals")
        thinking_deltas = [
            msg.event.delta.thinking
            async for msg in client.receive_response()
            if (
                isinstance(msg, StreamEvent)
                and isinstance(msg.event, BetaRawContentBlockDeltaEvent)
                and isinstance(msg.event.delta, BetaThinkingDelta)
            )
        ]

    # Should have received multiple thinking deltas
    assert len(thinking_deltas) > 0, "No thinking deltas received"
    # Combined thinking should form coherent text
    combined_thinking = "".join(thinking_deltas)
    assert len(combined_thinking) > 10, "Thinking content too short"
    # Should contain some reasoning about the calculation
    assert "2" in combined_thinking.lower(), "Thinking doesn't mention the numbers"


if __name__ == "__main__":
    pytest.main([__file__, "-vv", "-m", "e2e"])
