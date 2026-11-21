"""The generate_session_title control request."""

from __future__ import annotations

from typing import Any, cast

import pytest

from clawd_code_sdk import ClaudeAgentOptions, ClaudeSDKClient
from clawd_code_sdk.models import SDKControlGenerateSessionTitleRequest


class _TitleQuery:
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.requests: list[Any] = []

    async def _send_control_request(self, request: Any) -> dict[str, Any]:
        self.requests.append(request)
        return self.response


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (
            {"title": "ACP subprocess tests hanging on Windows CI"},
            "ACP subprocess tests hanging on Windows CI",
        ),
        ({"title": None}, None),  # The text was too short to title
        ({"title": ""}, None),
    ],
)
async def test_generate_session_title(response: dict[str, Any], expected: str | None) -> None:
    client = ClaudeSDKClient(ClaudeAgentOptions())
    query = _TitleQuery(response)
    client._query = cast(Any, query)

    title = await client.generate_session_title("Our CI fails on Windows ...")

    assert title == expected
    assert query.requests == [
        SDKControlGenerateSessionTitleRequest(
            description="Our CI fails on Windows ...", persist=False
        )
    ]
    assert query.requests[0].model_dump(by_alias=True, exclude_none=True) == {
        "subtype": "generate_session_title",
        "description": "Our CI fails on Windows ...",
        "persist": False,
    }
