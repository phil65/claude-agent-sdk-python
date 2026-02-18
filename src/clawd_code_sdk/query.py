"""Query function for one-shot interactions with Claude Code."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from clawd_code_sdk._internal.client import InternalClient
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
    """
    Query Claude Code for one-shot or unidirectional streaming interactions.

    This function is ideal for simple, stateless queries where you don't need
    bidirectional communication or conversation management. For interactive,
    stateful conversations, use ClaudeSDKClient instead.

    Key differences from ClaudeSDKClient:
    - **Unidirectional**: Send all messages upfront, receive all responses
    - **Stateless**: Each query is independent, no conversation state
    - **Simple**: Fire-and-forget style, no connection management
    - **No interrupts**: Cannot interrupt or send follow-up messages

    Args:
        prompt: The prompt to send to Claude. Can be a string for single-shot queries
                or an AsyncIterable[UserPromptMessage] for streaming mode.
        options: Optional configuration (defaults to ClaudeAgentOptions() if None).
                 Set options.permission_mode to control tool execution:
                 - 'default': CLI prompts for dangerous tools
                 - 'acceptEdits': Auto-accept file edits
                 - 'bypassPermissions': Allow all tools (use with caution)
                 Set options.cwd for working directory.
        transport: Optional transport implementation. If provided, this will be used
                  instead of the default transport selection based on options.
                  The transport will be automatically configured with the prompt and options.

    Yields:
        Messages from the conversation

    Example - Simple query:
        ```python
        # One-off question
        async for message in query(prompt="What is the capital of France?"):
            print(message)
        ```

    Example - With options:
        ```python
        # Code generation with specific settings
        async for message in query(
            prompt="Create a Python web server",
            options=ClaudeAgentOptions(
                system_prompt="You are an expert Python developer",
                cwd="/home/user/project"
            )
        ):
            print(message)
        ```

    Example - Streaming mode (still unidirectional):
        ```python
        async def prompts():
            yield {"type": "user", "message": {"role": "user", "content": "Hello"}}
            yield {"type": "user", "message": {"role": "user", "content": "How are you?"}}

        # All prompts are sent, then all responses received
        async for message in query(prompt=prompts()):
            print(message)
        ```

    Example - With custom transport:
        ```python
        from clawd_code_sdk import query, Transport

        class MyCustomTransport(Transport):
            # Implement custom transport logic
            pass

        transport = MyCustomTransport()
        async for message in query(
            prompt="Hello",
            transport=transport
        ):
            print(message)
        ```

    """
    options = options or ClaudeAgentOptions()
    os.environ["CLAUDE_CODE_ENTRYPOINT"] = "sdk-py"
    client = InternalClient()
    async for message in client.process_query(prompt=prompt, options=options, transport=transport):
        yield message
