"""Content blocks, message types, and stream events."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import ConfigDict, Discriminator, TypeAdapter

from clawd_code_sdk.models import ToolInput  # noqa: TC001
from clawd_code_sdk.models.base import ClaudeCodeBaseModel, ToolName  # noqa: TC001


if TYPE_CHECKING:
    from clawd_code_sdk.anthropic_types import ToolResultContentBlock


# Content block types
@dataclass(kw_only=True)
class TextBlock:
    """Text content block."""

    type: Literal["text"] = field(default="text", repr=False)
    text: str


@dataclass(kw_only=True)
class ThinkingBlock:
    """Thinking content block."""

    type: Literal["thinking"] = field(default="thinking", repr=False)
    thinking: str
    signature: str


@dataclass(kw_only=True)
class ToolUseBlock:
    """Tool use content block."""

    type: Literal["tool_use"] = field(default="tool_use", repr=False)
    id: str = ""
    name: ToolName | str = ""
    input: ToolInput | dict[str, Any] = field(default_factory=dict)
    caller: dict[str, str] | None = None


@dataclass(kw_only=True)
class ToolResultBlock:
    """Tool result content block."""

    type: Literal["tool_result"] = field(default="tool_result", repr=False)
    tool_use_id: str = ""
    content: str | list[dict[str, Any]] | None = None
    is_error: bool | None = None

    def get_parsed_content(self) -> list[ToolResultContentBlock] | str | None:
        from clawd_code_sdk.anthropic_types import validate_tool_result_content

        if self.content is None or isinstance(self.content, str):
            return self.content
        # Validate list content against Anthropic SDK types
        return validate_tool_result_content(self.content)


ContentBlock = Annotated[
    TextBlock | ThinkingBlock | ToolUseBlock | ToolResultBlock,
    Discriminator("type"),
]

content_block_adapter: TypeAdapter[ContentBlock] = TypeAdapter(ContentBlock)


class MessageParam(ClaudeCodeBaseModel):
    """Replacement for Anthropic MessageParam which serializes to our own content blocks."""

    content: Sequence[ContentBlock] | str
    model_config = ConfigDict(extra="allow")
