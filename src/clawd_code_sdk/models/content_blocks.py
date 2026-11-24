"""Content block types shared by both wire-format messages and JSONL storage.

Claude Code uses the same content block schema on the wire (SDK ↔ CLI JSON
messages) and in persisted JSONL session transcripts.  A single set of models
therefore serves both purposes, avoiding a redundant conversion layer.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Annotated, Any, Literal, TypeIs, assert_never, cast, get_args

from anthropic.types import Model
from anthropic.types.beta import (
    BetaAdvisorToolResultBlock,
    BetaBashCodeExecutionToolResultBlock,
    BetaCodeExecutionToolResultBlock,
    BetaCompactionBlock,
    BetaContainerUploadBlock,
    BetaFallbackBlock,
    BetaMCPToolListingBlock,
    BetaMCPToolResultBlock,
    BetaMCPToolUseBlock,
    BetaRedactedThinkingBlock,
    BetaServerToolUseBlock,
    BetaTextEditorCodeExecutionToolResultBlock,
    BetaToolSearchToolResultBlock,
    BetaWebFetchToolResultBlock,
    BetaWebSearchToolResultBlock,
)
from anthropic.types.beta.beta_tool_use_block import Caller
from pydantic import BaseModel, ConfigDict, Discriminator

from clawd_code_sdk.models import ToolInput
from clawd_code_sdk.models.base import ClaudeCodeBaseModel, StopReason, ToolName


if TYPE_CHECKING:
    from logfire._internal.integrations.llm_providers.semconv import (
        BlobPart,
        MessagePart,
        ReasoningPart,
        TextPart,
        ToolCallPart,
        ToolCallResponsePart,
    )

    from clawd_code_sdk.models.anthropic_types import ToolResultContentBlock

# =============================================================================
# Content block types
# =============================================================================
ImageMediaType = Literal["image/jpeg", "image/png", "image/gif", "image/webp"]


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
        from clawd_code_sdk.models.anthropic_types import validate_tool_result_content

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

    type: Literal["base64"] = "base64"
    media_type: ImageMediaType
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
            mime_type=self.source.media_type,
            modality="image",
        )


class Base64PDFSource(BaseContentBlock):
    """Base64-encoded PDF document."""

    type: Literal["base64"] = "base64"
    media_type: Literal["application/pdf"] = "application/pdf"
    data: str


class PlainTextSource(BaseContentBlock):
    """Plain text document."""

    type: Literal["text"] = "text"
    media_type: Literal["text/plain"] = "text/plain"
    data: str


class URLPDFSource(BaseContentBlock):
    """PDF document referenced by URL."""

    type: Literal["url"] = "url"
    url: str


class FileDocumentSource(BaseContentBlock):
    """Document uploaded through the Files API."""

    type: Literal["file"] = "file"
    file_id: str


class ContentDocumentSource(BaseContentBlock):
    """Document made of content blocks (text / images)."""

    type: Literal["content"] = "content"
    content: str | list[dict[str, Any]]


type DocumentSource = Annotated[
    Base64PDFSource | PlainTextSource | URLPDFSource | FileDocumentSource | ContentDocumentSource,
    Discriminator("type"),
]


class DocumentBlock(BaseContentBlock):
    """Document content block (e.g. an attached PDF) in a user message."""

    type: Literal["document"] = "document"
    source: DocumentSource
    title: str | None = None
    context: str | None = None
    citations: dict[str, Any] | None = None


# =============================================================================
# Unions and adapters
# =============================================================================

type ServerContentBlock = (
    BetaRedactedThinkingBlock
    | BetaServerToolUseBlock
    | BetaWebSearchToolResultBlock
    | BetaWebFetchToolResultBlock
    | BetaAdvisorToolResultBlock
    | BetaCodeExecutionToolResultBlock
    | BetaBashCodeExecutionToolResultBlock
    | BetaTextEditorCodeExecutionToolResultBlock
    | BetaToolSearchToolResultBlock
    | BetaMCPToolUseBlock
    | BetaMCPToolResultBlock
    | BetaContainerUploadBlock
    | BetaCompactionBlock
    | BetaFallbackBlock
    | BetaMCPToolListingBlock
)
"""Assistant content blocks produced by the API itself (server tools, MCP connector, ...).

These use the Anthropic SDK's models directly; clawd has no extra behaviour for them.
"""

SERVER_CONTENT_BLOCK_TYPES: tuple[type[BaseModel], ...] = get_args(ServerContentBlock.__value__)
"""Runtime tuple of :data:`ServerContentBlock` members (for ``isinstance`` checks)."""


def is_server_block(block: object) -> TypeIs[ServerContentBlock]:
    """Whether a content block was produced by the API itself (see :data:`ServerContentBlock`)."""
    return isinstance(block, SERVER_CONTENT_BLOCK_TYPES)


def server_block_to_otel(block: ServerContentBlock) -> MessagePart | None:
    """OpenTelemetry semconv part for an API-produced block (None if it has no equivalent)."""
    from logfire._internal.integrations.llm_providers.semconv import (
        ReasoningPart,
        ToolCallPart,
        ToolCallResponsePart,
    )

    match block:
        case BetaRedactedThinkingBlock():
            return ReasoningPart(type="reasoning", content="[redacted]")
        case (
            BetaServerToolUseBlock(id=tool_id, name=name, input=input_)
            | BetaMCPToolUseBlock(id=tool_id, name=name, input=input_)
        ):
            return ToolCallPart(type="tool_call", id=tool_id, name=name, arguments=input_)
        case (
            BetaWebSearchToolResultBlock(tool_use_id=tool_id)
            | BetaWebFetchToolResultBlock(tool_use_id=tool_id)
            | BetaAdvisorToolResultBlock(tool_use_id=tool_id)
            | BetaCodeExecutionToolResultBlock(tool_use_id=tool_id)
            | BetaBashCodeExecutionToolResultBlock(tool_use_id=tool_id)
            | BetaTextEditorCodeExecutionToolResultBlock(tool_use_id=tool_id)
            | BetaToolSearchToolResultBlock(tool_use_id=tool_id)
            | BetaMCPToolResultBlock(tool_use_id=tool_id)
        ):
            response = block.model_dump(mode="json", exclude={"type", "tool_use_id"})
            return ToolCallResponsePart(type="tool_call_response", id=tool_id, response=response)
        case (
            BetaContainerUploadBlock()
            | BetaCompactionBlock()
            | BetaFallbackBlock()
            | BetaMCPToolListingBlock()
        ):
            return None
        case _ as unreachable:
            assert_never(unreachable)


AssistantContentBlock = Annotated[
    TextBlock | ThinkingBlock | ToolUseBlock | ServerContentBlock,
    Discriminator("type"),
]
"""Content blocks that appear in assistant messages (any Messages API block type)."""

UserContentBlock = Annotated[
    TextBlock | ToolResultBlock | ImageBlock | DocumentBlock,
    Discriminator("type"),
]
"""Content blocks that appear in user messages."""

ContentBlock = Annotated[
    TextBlock
    | ThinkingBlock
    | ToolUseBlock
    | ToolResultBlock
    | ImageBlock
    | DocumentBlock
    | ServerContentBlock,
    Discriminator("type"),
]
"""All content block types (used for storage/JSONL which doesn't distinguish by role)."""


# =============================================================================
# Message-level models
# =============================================================================


class MessageParam(ClaudeCodeBaseModel):
    """User message payload wrapping content blocks.

    Only used for user-role messages; assistant messages use
    :class:`AssistantMessageContent`.
    """

    content: Sequence[UserContentBlock] | str
    role: Literal["user"] = "user"
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
    content: Sequence[AssistantContentBlock]
    model: Model | str
    stop_reason: StopReason | None = None
    stop_sequence: str | None = None
    model_config = ConfigDict(extra="allow")
