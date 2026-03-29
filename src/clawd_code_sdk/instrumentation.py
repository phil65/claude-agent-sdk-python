from __future__ import annotations

import threading
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
from logfire._internal.utils import handle_internal_errors
from opentelemetry import context as context_api, trace as trace_api

from clawd_code_sdk import HookMatcher


if TYPE_CHECKING:
    from logfire._internal.integrations.llm_providers.semconv import MessagePart, TextPart
    from logfire._internal.main import Logfire, LogfireSpan

    from clawd_code_sdk.models import (
        AssistantMessage,
        HookContext,
        HookEvent,
        PostToolUseFailureHookInput,
        PostToolUseHookInput,
        PreToolUseHookInput,
        ResultMessage,
        SyncHookJSONOutput,
    )


# ---------------------------------------------------------------------------
# Thread-local storage for per-conversation state.
#
# The Claude Agent SDK uses anyio internally, and anyio tasks don't propagate
# contextvars from the parent. This means OTel's context propagation breaks
# for hook callbacks. We use threading.local() as a workaround — storing a
# single ConversationState object that hooks retrieve.
# ---------------------------------------------------------------------------
_thread_local = threading.local()


def get_state() -> ConversationState | None:
    return getattr(_thread_local, "state", None)


def set_state(state: ConversationState) -> None:
    _thread_local.state = state


def clear_state() -> None:
    if hasattr(_thread_local, "state"):
        delattr(_thread_local, "state")


async def pre_tool_use_hook(
    input_data: PreToolUseHookInput,
    tool_use_id: str | None,
    _context: HookContext,
) -> SyncHookJSONOutput:
    """Create a child span when a tool execution starts."""
    if not tool_use_id:
        return {}

    with handle_internal_errors:  # ty:ignore[invalid-context-manager]
        state = get_state()
        if state is None:
            return {}

        tool_name = input_data["tool_name"]
        # Close the current chat span so it doesn't overlap with tool execution.
        state.close_chat_span()
        # Temporarily attach root span context so the new span is parented correctly,
        # then immediately detach. We can't keep the context attached because hooks
        # run in different async contexts (anyio tasks) and detaching later would fail.
        otel_span = state.root_span._span  # pyright: ignore[reportPrivateUsage]
        if otel_span is None:
            return {}
        parent_ctx = trace_api.set_span_in_context(otel_span)
        token = context_api.attach(parent_ctx)
        try:
            span_name = f"execute_tool {tool_name}"
            span = state.logfire.span(span_name)
            span.set_attributes(
                {
                    OPERATION_NAME: "execute_tool",
                    TOOL_NAME: tool_name,
                    TOOL_CALL_ID: tool_use_id,
                    TOOL_CALL_ARGUMENTS: input_data["tool_input"],
                }
            )
            span._start()  # pyright: ignore[reportPrivateUsage]
            state.active_tool_spans[tool_use_id] = span
        finally:
            context_api.detach(token)

    return {}


async def post_tool_use_hook(
    input_data: PostToolUseHookInput,
    tool_use_id: str | None,
    _context: HookContext,
) -> SyncHookJSONOutput:
    """End the tool span after successful execution."""
    if not tool_use_id:
        return {}

    with handle_internal_errors:  # ty:ignore[invalid-context-manager]
        state = get_state()
        if state is None:
            return {}

        span = state.active_tool_spans.pop(tool_use_id, None)
        if not span:
            return {}

        tool_response = input_data["tool_response"]
        if tool_response is not None:
            span.set_attribute(TOOL_CALL_RESULT, tool_response)
        span._end()  # pyright: ignore[reportPrivateUsage]

        # Record tool result for the next chat span's input messages
        tool_name = str(input_data["tool_name"])
        state.add_tool_result(
            tool_use_id, tool_name, tool_response if tool_response is not None else ""
        )

    return {}


async def post_tool_use_failure_hook(
    input_data: PostToolUseFailureHookInput,
    tool_use_id: str | None,
    _context: HookContext,
) -> SyncHookJSONOutput:
    """End the tool span with an error after failed execution."""
    if not tool_use_id:
        return {}

    with handle_internal_errors:  # ty:ignore[invalid-context-manager]
        state = get_state()
        if state is None:
            return {}

        span = state.active_tool_spans.pop(tool_use_id, None)
        if not span:
            return {}

        error = str(input_data["error"])
        span.set_attribute(ERROR_TYPE, error)
        span.set_level("error")
        span._end()  # pyright: ignore[reportPrivateUsage]
        # Record the error as a tool result so the next turn's input is complete.
        state.add_tool_result(tool_use_id, input_data["tool_name"], error)

    return {}


# ---------------------------------------------------------------------------
# Instrumentation entry point.
# ---------------------------------------------------------------------------


def inject_tracing_hooks(
    hooks: dict[HookEvent, list[HookMatcher]] | None = None,
) -> dict[HookEvent, list[HookMatcher]]:
    """Return a copy of *hooks* with logfire tracing hooks prepended."""
    result: dict[HookEvent, list[HookMatcher]] = (
        {k: list(v) for k, v in hooks.items()} if hooks else {}
    )
    with handle_internal_errors:  # ty:ignore[invalid-context-manager]
        for event in ("PreToolUse", "PostToolUse", "PostToolUseFailure"):
            result.setdefault(event, [])
        result["PreToolUse"].insert(0, HookMatcher(matcher=None, hooks=[pre_tool_use_hook]))  # type: ignore[list-item]  # ty:ignore[invalid-argument-type]
        result["PostToolUse"].insert(0, HookMatcher(matcher=None, hooks=[post_tool_use_hook]))  # type: ignore[list-item]  # ty:ignore[invalid-argument-type]
        result["PostToolUseFailure"].insert(
            0,
            HookMatcher(matcher=None, hooks=[post_tool_use_failure_hook]),  # type: ignore[list-item]  # ty:ignore[invalid-argument-type]
        )
    return result


class ConversationState:
    """Per-conversation state stored in thread-local during a receive_response iteration.

    Holds everything hooks need: the root span, logfire instance, active tool spans,
    chat span lifecycle, and conversation history. This keeps all mutable state in one
    object instead of scattered across globals and thread-local attributes.
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
        # Start without entering context — chat spans don't need to be on the
        # context stack, and this allows close_chat_span() to be called safely
        # from hooks running in different async contexts.
        self._current_span._start()  # pyright: ignore[reportPrivateUsage]
        self._current_output_parts = []

    def close_chat_span(self) -> None:
        """Close the current chat span without opening a new one.

        Safe to call from hooks (different async contexts) because chat spans
        are never entered into the OTel context stack.
        """
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
            # Update span name to include model.
            self._current_span.message = f"chat {model}"
            self._current_span.update_name(f"chat {model}")  # type: ignore[attr-defined]  # ty:ignore[unresolved-attribute]
        # self._current_span.set_attributes(usage.to_otel(partial=True))
        if error := message.error:
            self._current_span.set_attribute(ERROR_TYPE, str(error))
            self._current_span.set_level("error")

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
