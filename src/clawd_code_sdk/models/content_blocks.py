"""Content block types shared by both wire-format messages and JSONL storage.

Claude Code uses the same content block schema on the wire (SDK ↔ CLI JSON
messages) and in persisted JSONL session transcripts.  A single set of models
therefore serves both purposes, avoiding a redundant conversion layer.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Annotated, Any, Literal

from anthropic.types.beta.beta_tool_use_block import Caller
from pydantic import BaseModel, ConfigDict, Discriminator, TypeAdapter

from clawd_code_sdk.models import ToolInput
from clawd_code_sdk.models.base import ClaudeCodeBaseModel, StopReason, ToolName


if TYPE_CHECKING:
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


class ThinkingBlock(BaseContentBlock):
    """Thinking/reasoning content block."""

    type: Literal["thinking"] = "thinking"
    thinking: str
    signature: str = ""


class ToolUseBlock(BaseContentBlock):
    """Tool use content block."""

    type: Literal["tool_use"] = "tool_use"
    id: str = ""
    name: ToolName | str = ""
    input: ToolInput | dict[str, Any] = {}
    caller: Caller | None = None


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
        if self.content is None:
            return ""
        if isinstance(self.content, str):
            return self.content
        text_parts = [
            tc.get("text", "")
            for tc in self.content
            if isinstance(tc, dict) and tc.get("type") == "text"
        ]
        return "\n".join(text_parts)


class ImageSource(BaseContentBlock):
    """Base64-encoded image source data."""

    type: Literal["base64"]
    media_type: str
    data: str


class ImageBlock(BaseContentBlock):
    """Image content block (storage-only, not emitted on the wire)."""

    type: Literal["image"] = "image"
    source: ImageSource


# =============================================================================
# Unions and adapters
# =============================================================================

ContentBlock = Annotated[
    TextBlock | ThinkingBlock | ToolUseBlock | ToolResultBlock | ImageBlock,
    Discriminator("type"),
]

content_block_adapter = TypeAdapter[ContentBlock](ContentBlock)


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
