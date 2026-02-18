"""Internal client implementation."""

from __future__ import annotations

from collections.abc import AsyncIterable
from contextlib import aclosing
from dataclasses import replace
import logging
from typing import TYPE_CHECKING

import anyenv

from clawd_code_sdk._internal.message_parser import parse_message
from clawd_code_sdk._internal.query import Query
from clawd_code_sdk._internal.transport.subprocess_cli import SubprocessCLITransport
from clawd_code_sdk.models import AssistantMessage


if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from clawd_code_sdk._internal.transport import Transport
    from clawd_code_sdk.models import ClaudeAgentOptions, Message, UserPromptMessage

logger = logging.getLogger(__name__)


class InternalClient:
    """Internal client implementation."""

    def __init__(self) -> None:
        """Initialize the internal client."""

    async def process_query(
        self,
        prompt: str | AsyncIterable[UserPromptMessage],
        options: ClaudeAgentOptions,
        transport: Transport | None = None,
    ) -> AsyncIterator[Message]:
        """Process a query through transport and Query."""
        # Validate and configure permission settings (matching TypeScript SDK logic)
        options.validate()
        final_opts = options
        if options.can_use_tool:
            # canUseTool callback requires streaming mode (AsyncIterable prompt)
            if isinstance(prompt, str):
                raise ValueError(
                    "can_use_tool callback requires streaming mode. "
                    "Please provide prompt as an AsyncIterable instead of a string."
                )

            # Automatically set permission_prompt_tool_name to "stdio" for control protocol
            final_opts = replace(options, permission_prompt_tool_name="stdio")
        # Use provided transport or create subprocess transport
        chosen_transport = transport or SubprocessCLITransport(prompt=prompt, options=final_opts)
        # Connect transport
        await chosen_transport.connect()
        # Extract SDK MCP servers from configured options
        sdk_mcp_servers = {}
        if isinstance(final_opts.mcp_servers, dict):
            for name, config in final_opts.mcp_servers.items():
                if config.get("type") == "sdk":
                    sdk_mcp_servers[name] = config["instance"]  # type: ignore[typeddict-item]

        # Create Query to handle control protocol
        # Always use streaming mode internally (matching TypeScript SDK)
        # This ensures agents are always sent via initialize request
        query = Query(
            transport=chosen_transport,
            is_streaming_mode=True,  # Always streaming internally
            can_use_tool=final_opts.can_use_tool,
            hooks=final_opts.hooks,
            sdk_mcp_servers=sdk_mcp_servers,
            agents=final_opts.agents,
        )

        try:
            # Start reading messages
            await query.start()
            # Always initialize to send agents via stdin (matching TypeScript SDK)
            await query.initialize()
            # Handle prompt input
            if isinstance(prompt, str):
                # For string prompts, write user message to stdin after initialize
                # (matching TypeScript SDK behavior)
                user_message: UserPromptMessage = {
                    "type": "user",
                    "session_id": "",
                    "message": {"role": "user", "content": prompt},
                    "parent_tool_use_id": None,
                }
                await chosen_transport.write(anyenv.dump_json(user_message) + "\n")
                await chosen_transport.end_input()
            elif isinstance(prompt, AsyncIterable) and query._tg:
                # Stream input in background for async iterables
                query._tg.start_soon(query.stream_input, prompt)

            # Yield parsed messages
            # Use aclosing() for proper async generator cleanup
            async with aclosing(query.receive_messages()) as messages:
                async for data in messages:
                    message = parse_message(data)
                    # Check if this is an AssistantMessage with an API error
                    if isinstance(message, AssistantMessage) and message.error is not None:
                        message.raise_api_error()

                    # TODO: Verify if usage limit messages set the error field or come as
                    # plain text. If they come as plain text without error field, uncomment
                    # this block to detect and raise BillingError for usage limits.
                    # if isinstance(message, AssistantMessage) and message.error is None:
                    #     for block in message.content:
                    #         if isinstance(block, TextBlock):
                    #             if (
                    #                 "You've hit your limit" in block.text
                    #                 and "resets" in block.text
                    #             ):
                    #                 raise BillingError(block.text, message.model)
                    #             break

                    yield message

        except GeneratorExit:
            # Handle early termination of the async generator gracefully
            # This occurs when the caller breaks out of the async for loop
            logger.debug("process_query generator closed early by caller")
        finally:
            await query.close()
