"""Internal client implementation."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterable, AsyncIterator
from contextlib import aclosing
from dataclasses import asdict, replace
from typing import Any

import anyenv

from .._errors import (
    APIError,
    AuthenticationError,
    BillingError,
    InvalidRequestError,
    RateLimitError,
    ServerError,
)
from ..types import (
    AssistantMessage,
    ClaudeAgentOptions,
    HookEvent,
    HookMatcher,
    Message,
    TextBlock,
)
from .message_parser import parse_message
from .query import Query
from .transport import Transport
from .transport.subprocess_cli import SubprocessCLITransport

logger = logging.getLogger(__name__)


def _extract_error_message(message: AssistantMessage) -> str:
    """Extract the error message text from an AssistantMessage.

    When the API returns an error, the error text is typically in the
    first TextBlock of the message content.

    Args:
        message: The AssistantMessage containing the error.

    Returns:
        The error message text, or a default message if none found.
    """
    for block in message.content:
        if isinstance(block, TextBlock):
            return block.text
    return "An API error occurred"


def _raise_api_error(message: AssistantMessage) -> None:
    """Raise the appropriate API exception for an AssistantMessage with an error.

    This function converts the error field on an AssistantMessage into a proper
    Python exception that can be caught and handled programmatically.

    Args:
        message: The AssistantMessage with error field set.

    Raises:
        AuthenticationError: For authentication_failed errors (401).
        BillingError: For billing_error errors.
        RateLimitError: For rate_limit errors (429).
        InvalidRequestError: For invalid_request errors (400).
        ServerError: For server_error errors (500/529).
        APIError: For unknown error types.
    """
    error_type = message.error
    error_message = _extract_error_message(message)
    model = message.model

    match error_type:
        case "authentication_failed":
            raise AuthenticationError(error_message, model)
        case "billing_error":
            raise BillingError(error_message, model)
        case "rate_limit":
            raise RateLimitError(error_message, model)
        case "invalid_request":
            raise InvalidRequestError(error_message, model)
        case "server_error":
            raise ServerError(error_message, model)
        case _:
            # Handle "unknown" or any future error types
            raise APIError(error_message, error_type or "unknown", model)


class InternalClient:
    """Internal client implementation."""

    def __init__(self) -> None:
        """Initialize the internal client."""

    def _convert_hooks_to_internal_format(
        self, hooks: dict[HookEvent, list[HookMatcher]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Convert HookMatcher format to internal Query format."""
        internal_hooks: dict[str, list[dict[str, Any]]] = {}
        for event, matchers in hooks.items():
            internal_hooks[event] = []
            for matcher in matchers:
                # Convert HookMatcher to internal dict format
                internal_matcher: dict[str, Any] = {
                    "matcher": matcher.matcher,
                    "hooks": matcher.hooks,
                }
                if matcher.timeout is not None:
                    internal_matcher["timeout"] = matcher.timeout
                internal_hooks[event].append(internal_matcher)
        return internal_hooks

    async def process_query(
        self,
        prompt: str | AsyncIterable[dict[str, Any]],
        options: ClaudeAgentOptions,
        transport: Transport | None = None,
    ) -> AsyncIterator[Message]:
        """Process a query through transport and Query."""

        # Validate and configure permission settings (matching TypeScript SDK logic)
        configured_options = options
        if options.can_use_tool:
            # canUseTool callback requires streaming mode (AsyncIterable prompt)
            if isinstance(prompt, str):
                raise ValueError(
                    "can_use_tool callback requires streaming mode. "
                    "Please provide prompt as an AsyncIterable instead of a string."
                )

            # canUseTool and permission_prompt_tool_name are mutually exclusive
            if options.permission_prompt_tool_name:
                raise ValueError(
                    "can_use_tool callback cannot be used with permission_prompt_tool_name. "
                    "Please use one or the other."
                )

            # Automatically set permission_prompt_tool_name to "stdio" for control protocol
            configured_options = replace(options, permission_prompt_tool_name="stdio")

        # Use provided transport or create subprocess transport
        if transport is not None:
            chosen_transport = transport
        else:
            chosen_transport = SubprocessCLITransport(
                prompt=prompt,
                options=configured_options,
            )

        # Connect transport
        await chosen_transport.connect()

        # Extract SDK MCP servers from configured options
        sdk_mcp_servers = {}
        if configured_options.mcp_servers and isinstance(
            configured_options.mcp_servers, dict
        ):
            for name, config in configured_options.mcp_servers.items():
                if isinstance(config, dict) and config.get("type") == "sdk":
                    sdk_mcp_servers[name] = config["instance"]  # type: ignore[typeddict-item]

        # Convert agents to dict format for initialize request
        agents_dict = None
        if configured_options.agents:
            agents_dict = {
                name: {k: v for k, v in asdict(agent_def).items() if v is not None}
                for name, agent_def in configured_options.agents.items()
            }

        # Create Query to handle control protocol
        # Always use streaming mode internally (matching TypeScript SDK)
        # This ensures agents are always sent via initialize request
        query = Query(
            transport=chosen_transport,
            is_streaming_mode=True,  # Always streaming internally
            can_use_tool=configured_options.can_use_tool,
            hooks=self._convert_hooks_to_internal_format(configured_options.hooks)
            if configured_options.hooks
            else None,
            sdk_mcp_servers=sdk_mcp_servers,
            agents=agents_dict,
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
                user_message = {
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
                    if (
                        isinstance(message, AssistantMessage)
                        and message.error is not None
                    ):
                        _raise_api_error(message)

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
