"""Pytest configuration for tests."""

import os
from typing import Any

import pytest


_MSG_COUNTER = 0


def make_beta_message(
    content: list[dict[str, Any]],
    model: str = "claude-opus-4-1-20250805",
    **kwargs: Any,
) -> dict[str, Any]:
    """Create a wire-format message dict matching BetaMessage shape."""
    global _MSG_COUNTER  # noqa: PLW0603
    _MSG_COUNTER += 1
    return {
        "id": f"msg_test_{_MSG_COUNTER:04d}",
        "type": "message",
        "role": "assistant",
        "content": content,
        "model": model,
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 5},
        **kwargs,
    }


@pytest.fixture(scope="session", autouse=True)
def unset_anthropic_api_key():
    os.environ["ANTHROPIC_API_KEY"] = ""
