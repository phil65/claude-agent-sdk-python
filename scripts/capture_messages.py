"""Capture raw wire-format messages from a Claude Code session.

Runs a quick query ("Read README.md and summarize it in 2 sentences")
and saves all raw message dicts to a JSONL file for benchmarking.

Usage:
    uv run python scripts/capture_messages.py [output_path]
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import anyio

from clawd_code_sdk import ClaudeSDKClient
from clawd_code_sdk.models import ClaudeAgentOptions


OUTPUT_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/recorded_messages.jsonl")


async def main() -> None:
    OUTPUT_PATH.unlink(missing_ok=True)

    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        allow_dangerously_skip_permissions=True,
    )
    client = ClaudeSDKClient(options=options)

    raw_messages: list[dict] = []

    async with client:
        query = client._query
        assert query is not None
        original_receive = query.receive_messages

        async def recording_receive():  # type: ignore[override]
            async for data in original_receive():
                raw_messages.append(data)
                yield data

        query.receive_messages = recording_receive  # type: ignore[assignment]

        await client.query(
            "Read the file README.md and give me a 2-sentence summary. "
            "Use the Read tool to read the file."
        )
        async for msg in client.receive_response():
            print(f"  [{type(msg).__name__}] {str(msg)[:120]}")

    with OUTPUT_PATH.open("w") as f:
        for msg in raw_messages:
            f.write(json.dumps(msg) + "\n")

    print(f"\nCaptured {len(raw_messages)} messages to {OUTPUT_PATH}")


if __name__ == "__main__":
    anyio.run(main)
