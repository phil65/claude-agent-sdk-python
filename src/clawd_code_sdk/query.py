"""Query function for one-shot interactions with Claude Code."""

from __future__ import annotations

from typing import TYPE_CHECKING

from clawd_code_sdk.client import ClaudeSDKClient
from clawd_code_sdk.models import ClaudeAgentOptions


if TYPE_CHECKING:
    from collections.abc import AsyncIterable, AsyncIterator

    from clawd_code_sdk._internal.transport import Transport
    from clawd_code_sdk.models import Message, UserPromptMessage


async def query(
    *,
    prompt: str | AsyncIterable[UserPromptMessage],
    options: ClaudeAgentOptions | None = None,
    transport: Transport | None = None,
) -> AsyncIterator[Message]:
    """Query Claude Code for one-shot interactions.

    Convenience wrapper around ClaudeSDKClient for simple, stateless queries.
    For interactive, stateful conversations, use ClaudeSDKClient directly.

    Args:
        prompt: The prompt to send to Claude. Can be a string for single-shot queries
                or an AsyncIterable[UserPromptMessage] for streaming input.
        options: Optional configuration (defaults to ClaudeAgentOptions() if None).
        transport: Optional transport implementation override.

    Yields:
        Messages from the conversation

    Example:
        ```python
        async for message in query(prompt="What is the capital of France?"):
            print(message)
        ```
    """
    options = options or ClaudeAgentOptions()
    client = ClaudeSDKClient(options=options, transport=transport)
    try:
        await client.connect()
        await client.query(prompt)
        async for message in client.receive_response():
            yield message
    finally:
        await client.disconnect()
