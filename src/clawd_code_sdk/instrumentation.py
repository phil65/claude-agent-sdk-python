from __future__ import annotations

from typing import TYPE_CHECKING, Any

from logfire._internal.integrations.llm_providers.semconv import (
    CONVERSATION_ID,
    ERROR_TYPE,
    INPUT_MESSAGES,
    OPERATION_NAME,
    OUTPUT_MESSAGES,
    PROVIDER_NAME,
    REQUEST_MODEL,
    RESPONSE_MODEL,
    SYSTEM,
    SYSTEM_INSTRUCTIONS,
    TOOL_CALL_ARGUMENTS,
    TOOL_CALL_ID,
    TOOL_CALL_RESULT,
    TOOL_NAME,
    ChatMessage,
    OutputMessage,
    ToolCallResponsePart,
)
from opentelemetry import context as context_api, trace as trace_api


if TYPE_CHECKING:
    from logfire._internal.integrations.llm_providers.semconv import MessagePart, TextPart
    from logfire._internal.main import Logfire, LogfireSpan

    from clawd_code_sdk.models import AssistantMessage, ResultMessage
    from clawd_code_sdk.models.content_blocks import ToolResultBlock, ToolUseBlock


class ConversationState:
    """Per-conversation state for instrumenting a receive_response iteration.

    All instrumentation is driven from the event loop in
    ``receive_response_instrumented`` — no hooks or thread-locals needed.
    """

    def __init__(
        self,
        *,
        logfire: Logfire,
        root_span: LogfireSpan,
        input_messages: list[ChatMessage],
        system_instructions: list[TextPart] | None = None,
    ) -> None:
        self.logfire = logfire
        self.root_span = root_span
        self.active_tool_spans: dict[str, LogfireSpan] = {}
        self._current_span: LogfireSpan | None = None
        # Running conversation history — each chat span gets the full history as input.
        self._history: list[ChatMessage] = list(input_messages)
        # Track current span's output parts for merging consecutive messages.
        self._current_output_parts: list[MessagePart] = []
        self._system_instructions = system_instructions
        self.model: str | None = None

    def add_tool_result(self, tool_use_id: str, tool_name: str, result: Any) -> None:
        """Record a tool result to include in the next chat span's input messages."""
        part = ToolCallResponsePart(
            type="tool_call_response", id=tool_use_id, name=tool_name, response=result
        )
        msg = ChatMessage(role="tool", parts=[part])  # ty:ignore[invalid-argument-type]
        self._history.append(msg)

    def open_chat_span(self) -> None:
        """Open a new chat span — call when the LLM starts processing."""
        self.close_chat_span()

        span_data: dict[str, Any] = {
            OPERATION_NAME: "chat",
            PROVIDER_NAME: "anthropic",
            SYSTEM: "anthropic",
        }
        if self._history:
            span_data[INPUT_MESSAGES] = list(self._history)
        if self._system_instructions:
            span_data[SYSTEM_INSTRUCTIONS] = self._system_instructions

        self._current_span = self.logfire.span("chat", **span_data)
        self._current_span._start()  # pyright: ignore[reportPrivateUsage]
        self._current_output_parts = []

    def close_chat_span(self) -> None:
        """Close the current chat span without opening a new one."""
        if self._current_span is not None:
            if self._current_output_parts:
                self._history.append(
                    ChatMessage(role="assistant", parts=list(self._current_output_parts))
                )
            self._current_span._end()  # pyright: ignore[reportPrivateUsage]
            self._current_span = None
            self._current_output_parts = []

    def handle_user_message(self) -> None:
        """Handle UserMessage: open a new chat span for the next LLM call."""
        self.open_chat_span()

    def handle_assistant_message(self, message: AssistantMessage) -> None:
        """Handle AssistantMessage: add output and usage to the current chat span."""
        if self._current_span is None:
            return

        output_messages = [message.to_otel()]
        new_parts = output_messages[0]["parts"] if output_messages else []
        self._current_output_parts.extend(new_parts)
        output_message = OutputMessage(role="assistant", parts=self._current_output_parts)
        self._current_span.set_attribute(OUTPUT_MESSAGES, [output_message])
        if model := message.model:
            self.model = model
            self._current_span.set_attribute(REQUEST_MODEL, model)
            self._current_span.set_attribute(RESPONSE_MODEL, model)
            self._current_span.message = f"chat {model}"
            self._current_span.update_name(f"chat {model}")  # type: ignore[attr-defined]  # ty:ignore[unresolved-attribute]
        if error := message.error:
            self._current_span.set_attribute(ERROR_TYPE, str(error))
            self._current_span.set_level("error")

    def open_tool_spans(self, blocks: list[ToolUseBlock]) -> None:
        """Open tool execution spans for each ToolUseBlock in an AssistantMessage.

        Closes the current chat span first (chat is done, tools are about to run),
        then creates child spans under the root span for each tool call.
        """
        if not blocks:
            return

        self.close_chat_span()

        otel_span = self.root_span._span  # pyright: ignore[reportPrivateUsage]
        if otel_span is None:
            return
        parent_ctx = trace_api.set_span_in_context(otel_span)
        token = context_api.attach(parent_ctx)
        try:
            for block in blocks:
                span_name = f"execute_tool {block.name}"
                span = self.logfire.span(span_name)
                span.set_attributes(
                    {
                        OPERATION_NAME: "execute_tool",
                        TOOL_NAME: block.name,
                        TOOL_CALL_ID: block.id,
                        TOOL_CALL_ARGUMENTS: block.input,
                    }
                )
                span._start()  # pyright: ignore[reportPrivateUsage]
                self.active_tool_spans[block.id] = span
        finally:
            context_api.detach(token)

    def close_tool_spans(self, results: list[ToolResultBlock]) -> None:
        """Close tool spans using ToolResultBlocks from a UserMessage.

        Records results/errors on each span and adds tool results to conversation
        history for the next chat span.
        """
        for result_block in results:
            span = self.active_tool_spans.pop(result_block.tool_use_id, None)
            if span is None:
                continue

            result_text = result_block.extract_text()
            if result_block.is_error:
                span.set_attribute(ERROR_TYPE, result_text)
                span.set_level("error")
            else:
                span.set_attribute(TOOL_CALL_RESULT, result_text)
            span._end()  # pyright: ignore[reportPrivateUsage]

            # Record tool result for the next chat span's input messages.
            # Use tool_use_id as the name since ToolResultBlock doesn't carry the tool name;
            # the tool name is already on the span from open_tool_spans.
            self.add_tool_result(result_block.tool_use_id, result_block.tool_use_id, result_text)

    def close(self) -> None:
        """Close chat span and end any orphaned tool spans."""
        self.close_chat_span()
        for span in self.active_tool_spans.values():
            span._end()  # pyright: ignore[reportPrivateUsage]
        self.active_tool_spans.clear()


def record_result(span: LogfireSpan, msg: ResultMessage) -> None:
    """Record ResultMessage data onto the root span."""
    attrs: dict[str, Any] = {}
    attrs.update(msg.usage.to_otel())
    attrs["operation.cost"] = float(msg.total_cost_usd)
    attrs[CONVERSATION_ID] = msg.session_id
    attrs["num_turns"] = msg.num_turns
    attrs["duration_ms"] = msg.duration_ms

    span.set_attributes(attrs)
    if msg.is_error:
        span.set_level("error")
