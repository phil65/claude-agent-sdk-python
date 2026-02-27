"""End-to-end tests for hook callbacks with real Claude API calls."""

from __future__ import annotations

import pytest

from clawd_code_sdk import ClaudeAgentOptions, ClaudeSDKClient, ThinkingConfigAdaptive


@pytest.mark.e2e
async def test_compact() -> None:
    opts = ClaudeAgentOptions(thinking=ThinkingConfigAdaptive()
    client = ClaudeSDKClient(opts)
    await client.connect()
    await client.query("hello")
    async for msg in client.receive_response():
        print(msg)
    await client.query("/compact")
    async for msg in client.receive_response():
        print(msg)


if __name__ == "__main__":
    pytest.main([__file__, "-vv", "-m", "e2e"])
