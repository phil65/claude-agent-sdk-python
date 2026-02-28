"""Query function for one-shot interactions with Claude Code."""

from __future__ import annotations

from typing import TYPE_CHECKING

from clawd_code_sdk.client import ClaudeSDKClient
from clawd_code_sdk.models import ClaudeAgentOptions


if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from clawd_code_sdk._internal.transport import Transport
    from clawd_code_sdk.models import Message
    from clawd_code_sdk.models.messages import UserImagePrompt, UserTextPrompt


async def query(
    *prompts: str | UserTextPrompt | UserImagePrompt,
    options: ClaudeAgentOptions | None = None,
    transport: Transport | None = None,
) -> AsyncIterator[Message]:
    """Query Claude Code for one-shot interactions.

    Convenience wrapper around ClaudeSDKClient for simple, stateless queries.
    For interactive, stateful conversations, use ClaudeSDKClient directly.

    Args:
        *prompts: One or more content blocks to send. Strings are automatically
                  converted to UserTextPrompt.
        options: Optional configuration (defaults to ClaudeAgentOptions() if None).
        transport: Optional transport implementation override.

    Yields:
        Messages from the conversation

    Example:
        ```python
        async for message in query("What is the capital of France?"):
            print(message)
        ```
    """
    options = options or ClaudeAgentOptions()
    client = ClaudeSDKClient(options=options, transport=transport)
    try:
        await client.connect()
        await client.query(*prompts)
        async for message in client.receive_response():
            yield message
    finally:
        await client.disconnect()
