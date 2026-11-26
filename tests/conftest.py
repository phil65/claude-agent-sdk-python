"""Pytest configuration for tests."""

import os
from pathlib import Path
from typing import Any

import pytest


# Unknown CLI message types fail the suite instead of being skipped
os.environ.setdefault("CLAWD_STRICT_MESSAGES", "1")

_MSG_COUNTER = 0

_E2E_DIR = Path(__file__).parent / "e2e"


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark every test under tests/e2e/ as e2e (they need a real CLI and an API key).

    Runs before the `-m` deselection, so CI (`not e2e`) never runs one, even unmarked.
    """
    for item in items:
        if item.path.is_relative_to(_E2E_DIR):
            item.add_marker(pytest.mark.e2e)


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
