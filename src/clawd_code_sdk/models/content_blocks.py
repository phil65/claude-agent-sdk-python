"""Content blocks, message types, and stream events."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import Discriminator, TypeAdapter


if TYPE_CHECKING:
    from clawd_code_sdk.anthropic_types import ToolResultContentBlock


# Content block types
@dataclass
class TextBlock:
    """Text content block."""

    type: Literal["text"] = field(default="text", repr=False)
    text: str = ""


@dataclass
class ThinkingBlock:
    """Thinking content block."""

    type: Literal["thinking"] = field(default="thinking", repr=False)
    thinking: str = ""
    signature: str = ""


@dataclass
class ToolUseBlock:
    """Tool use content block."""

    type: Literal["tool_use"] = field(default="tool_use", repr=False)
    id: str = ""
    name: str = ""
    input: dict[str, Any] = field(default_factory=dict)
    caller: dict[str, str] | None = None


@dataclass
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

_content_block_adapter: TypeAdapter[ContentBlock] = TypeAdapter(ContentBlock)


def parse_content_block(data: dict[str, Any]) -> ContentBlock:
    """Parse a raw dict into a typed ContentBlock dataclass."""
    return _content_block_adapter.validate_python(data)
