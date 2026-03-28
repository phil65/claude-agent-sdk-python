"""Content block types shared by both wire-format messages and JSONL storage.

Claude Code uses the same content block schema on the wire (SDK ↔ CLI JSON
messages) and in persisted JSONL session transcripts.  A single set of models
therefore serves both purposes, avoiding a redundant conversion layer.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Annotated, Any, Literal, assert_never, cast

from anthropic.types.beta.beta_tool_use_block import Caller
from pydantic import BaseModel, ConfigDict, Discriminator

from clawd_code_sdk.models import ToolInput
from clawd_code_sdk.models.base import ClaudeCodeBaseModel, StopReason, ToolName


if TYPE_CHECKING:
    from logfire._internal.integrations.llm_providers.semconv import (
        BlobPart,
        ReasoningPart,
        TextPart,
        ToolCallPart,
        ToolCallResponsePart,
    )

    from clawd_code_sdk.anthropic_types import ToolResultContentBlock

# =============================================================================
# Content block types
# =============================================================================


class BaseContentBlock(BaseModel):
    """Shared base for all content block types."""

    # extra="allow": storage JSONL includes all union fields on every block
    # with null for fields belonging to other block types.
    model_config = ConfigDict(extra="allow", defer_build=True)


class TextBlock(BaseContentBlock):
    """Text content block."""

    type: Literal["text"] = "text"
    text: str

    def to_otel(self) -> TextPart:
        from logfire._internal.integrations.llm_providers.semconv import TextPart

        return TextPart(type="text", content=self.text)


class ThinkingBlock(BaseContentBlock):
    """Thinking/reasoning content block."""

    type: Literal["thinking"] = "thinking"
    thinking: str
    signature: str = ""

    def to_otel(self) -> ReasoningPart:
        from logfire._internal.integrations.llm_providers.semconv import ReasoningPart

        return ReasoningPart(type="reasoning", content=self.thinking)


class ToolUseBlock(BaseContentBlock):
    """Tool use content block."""

    type: Literal["tool_use"] = "tool_use"
    id: str = ""
    name: ToolName | str = ""
    input: ToolInput | dict[str, Any] = {}
    caller: Caller | None = None

    def to_otel(self) -> ToolCallPart:
        from logfire._internal.integrations.llm_providers.semconv import ToolCallPart

        args = cast(dict[str, Any], self.input)
        return ToolCallPart(type="tool_call", id=self.id, name=self.name, arguments=args)


class ToolResultBlock(BaseContentBlock):
    """Tool result content block."""

    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str = ""
    content: str | list[dict[str, Any]] | None = None  # BetaContentBlock
    is_error: bool | None = None

    def get_parsed_content(self) -> list[ToolResultContentBlock] | str | None:
        # TODO: or is it anthropic.types.beta.beta_tool_result_block_param.Content?
        from clawd_code_sdk.anthropic_types import validate_tool_result_content

        if self.content is None or isinstance(self.content, str):
            return self.content
        # Validate list content against Anthropic SDK types
        return validate_tool_result_content(self.content)

    def extract_text(self) -> str:
        """Extract text content from this tool result."""
        match self.content:
            case None:
                return ""
            case str():
                return self.content
            case list():
                text_parts = [tc.get("text", "") for tc in self.content if tc.get("type") == "text"]
                return "\n".join(text_parts)
            case _ as unreachable:
                assert_never(unreachable)

    def to_otel(self) -> ToolCallResponsePart:
        from logfire._internal.integrations.llm_providers.semconv import ToolCallResponsePart

        res = {"content": self.content} if isinstance(self.content, list) else self.content
        return ToolCallResponsePart(
            type="tool_call_response", id=self.tool_use_id or "", response=res
        )


class ImageSource(BaseContentBlock):
    """Base64-encoded image source data."""

    type: Literal["base64"]
    media_type: str
    data: str


class ImageBlock(BaseContentBlock):
    """Image content block (storage-only, not emitted on the wire)."""

    type: Literal["image"] = "image"
    source: ImageSource

    def to_otel(self) -> BlobPart:
        from logfire._internal.integrations.llm_providers.semconv import BlobPart

        return BlobPart(
            type="blob",
            content=self.source.data,
            media_type=self.source.media_type,
            modality="image",
        )


# =============================================================================
# Unions and adapters
# =============================================================================

ContentBlock = Annotated[
    TextBlock | ThinkingBlock | ToolUseBlock | ToolResultBlock | ImageBlock,
    Discriminator("type"),
]


# =============================================================================
# Message-level models
# =============================================================================


class MessageParam(ClaudeCodeBaseModel):
    """Replacement for Anthropic MessageParam which serializes to our own content blocks."""

    content: Sequence[ContentBlock] | str
    role: Literal["user", "assistant"]
    model_config = ConfigDict(extra="allow")


class AssistantMessageContent(ClaudeCodeBaseModel):
    """Assistant message payload mirroring ``anthropic.types.beta.BetaMessage``.

    Uses our own ``ContentBlock`` types instead of the Anthropic SDK's
    ``BetaContentBlock`` variants. Extra fields from the wire format
    (e.g. ``container``, ``context_management``) are preserved via ``extra="allow"``.
    """

    id: str
    type: Literal["message"] = "message"
    role: Literal["assistant"] = "assistant"
    content: Sequence[ContentBlock]
    model: str
    stop_reason: StopReason | None = None
    stop_sequence: str | None = None
    model_config = ConfigDict(extra="allow")
