"""The apply_flag_settings control request sends only the settings that were set."""

from typing import Any, cast

from clawd_code_sdk import ClaudeAgentOptions, ClaudeSDKClient
from clawd_code_sdk.models.control import SDKControlApplyFlagSettingsRequest
from clawd_code_sdk.models.settings import ClaudeCodeSettings


class _RecordingQuery:
    def __init__(self) -> None:
        self.requests: list[Any] = []

    async def _send_control_request(self, request: Any) -> dict[str, Any]:
        self.requests.append(request)
        return {}


async def test_only_set_fields_are_sent() -> None:
    client = ClaudeSDKClient(ClaudeAgentOptions())
    query = _RecordingQuery()
    client._query = cast(Any, query)

    await client.apply_flag_settings(ClaudeCodeSettings(effort_level="low"))

    assert query.requests == [SDKControlApplyFlagSettingsRequest(settings={"effortLevel": "low"})]
