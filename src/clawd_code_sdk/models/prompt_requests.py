from __future__ import annotations

from typing import NotRequired, TypedDict


# from anthropic.types import MessageParam


class PromptRequestOption(TypedDict):
    """An option in a prompt request."""

    key: str
    """Unique key for this option, returned in the response."""
    label: str
    """Display text for this option."""
    description: NotRequired[str]
    """Optional description shown below the label."""


class PromptRequest(TypedDict):
    """Prompt request sent to the SDK consumer."""

    prompt: str
    """Request ID. Presence of this key marks the line as a prompt request."""
    message: str
    """The prompt message to display to the user."""
    options: list[PromptRequestOption]
    """Available options for the user to choose from."""


class PromptResponse(TypedDict):
    """Response to a prompt request."""

    prompt_response: str
    """The request ID from the corresponding prompt request."""
    selected: str
    """The key of the selected option."""
