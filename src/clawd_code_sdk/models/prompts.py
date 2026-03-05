"""Content blocks, message types, and stream events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


# from anthropic.types import MessageParam


ImageMediaType = Literal["image/png", "image/jpeg", "image/gif", "image/webp"]
DocumentMediaType = Literal["application/pdf"]
PlainTextMediaType = Literal["text/plain"]


@dataclass
class UserTextPrompt:
    """A text-only user prompt."""

    text: str

    def to_content_block(self) -> dict[str, Any]:
        """Return the Anthropic API content block dict."""
        return {"type": "text", "text": self.text}


@dataclass
class UserImagePrompt:
    """A user prompt containing a single base64-encoded image."""

    image_data: str
    """Base64-encoded image data."""
    media_type: ImageMediaType
    """MIME type of the image."""

    def to_content_block(self) -> dict[str, Any]:
        """Return the Anthropic API content block dict."""
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": self.media_type,
                "data": self.image_data,
            },
        }


@dataclass
class UserImageURLPrompt:
    """A user prompt containing an image referenced by URL."""

    url: str
    """Public URL of the image."""

    def to_content_block(self) -> dict[str, Any]:
        """Return the Anthropic API content block dict."""
        return {
            "type": "image",
            "source": {
                "type": "url",
                "url": self.url,
            },
        }


@dataclass
class UserDocumentPrompt:
    """A user prompt containing a base64-encoded PDF document."""

    document_data: str
    """Base64-encoded PDF data."""
    media_type: DocumentMediaType = "application/pdf"
    """MIME type of the document."""
    title: str | None = None
    """Optional document title."""
    context: str | None = None
    """Optional context about the document."""

    def to_content_block(self) -> dict[str, Any]:
        """Return the Anthropic API content block dict."""
        block: dict[str, Any] = {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": self.media_type,
                "data": self.document_data,
            },
        }
        if self.title is not None:
            block["title"] = self.title
        if self.context is not None:
            block["context"] = self.context
        return block


@dataclass
class UserDocumentURLPrompt:
    """A user prompt containing a PDF document referenced by URL."""

    url: str
    """Public URL of the PDF document."""
    title: str | None = None
    """Optional document title."""
    context: str | None = None
    """Optional context about the document."""

    def to_content_block(self) -> dict[str, Any]:
        """Return the Anthropic API content block dict."""
        block: dict[str, Any] = {
            "type": "document",
            "source": {
                "type": "url",
                "url": self.url,
            },
        }
        if self.title is not None:
            block["title"] = self.title
        if self.context is not None:
            block["context"] = self.context
        return block


@dataclass
class UserPlainTextDocumentPrompt:
    """A user prompt containing a plain text document."""

    data: str
    """The plain text content."""
    media_type: PlainTextMediaType = "text/plain"
    """MIME type (always text/plain)."""
    title: str | None = None
    """Optional document title."""
    context: str | None = None
    """Optional context about the document."""

    def to_content_block(self) -> dict[str, Any]:
        """Return the Anthropic API content block dict."""
        block: dict[str, Any] = {
            "type": "document",
            "source": {
                "type": "text",
                "media_type": self.media_type,
                "data": self.data,
            },
        }
        if self.title is not None:
            block["title"] = self.title
        if self.context is not None:
            block["context"] = self.context
        return block


@dataclass
class UserFilePrompt:
    """A user prompt referencing a file uploaded via the Anthropic Files API."""

    file_id: str
    """Anthropic file identifier (e.g. 'file_abc123')."""
    title: str | None = None
    """Optional document title."""
    context: str | None = None
    """Optional context about the document."""

    def to_content_block(self) -> dict[str, Any]:
        """Return the Anthropic API content block dict."""
        block: dict[str, Any] = {
            "type": "document",
            "source": {
                "type": "file",
                "file_id": self.file_id,
            },
        }
        if self.title is not None:
            block["title"] = self.title
        if self.context is not None:
            block["context"] = self.context
        return block


UserPrompt = (
    UserTextPrompt
    | UserImagePrompt
    | UserImageURLPrompt
    | UserDocumentPrompt
    | UserDocumentURLPrompt
    | UserPlainTextDocumentPrompt
    | UserFilePrompt
)
"""Union type for all user prompt dataclasses."""
