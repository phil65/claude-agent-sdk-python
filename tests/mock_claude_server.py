"""Mock Claude CLI server for testing async iterable message streaming.

Reads JSON-RPC messages from stdin, handles the initialize control request,
collects user messages, validates that exactly 2 were received, and emits
a success result on stdout.
"""

from __future__ import annotations

import json
import sys

from clawd_code_sdk.models import ModelUsage


def main() -> None:
    stdin_messages: list[str] = []

    while True:
        line = sys.stdin.readline()
        if not line:
            break

        try:
            msg = json.loads(line.strip())
            # Handle control requests
            if msg.get("type") == "control_request":
                request_id = msg.get("request_id")
                request = msg.get("request", {})

                # Send control response for initialize
                if request.get("subtype") == "initialize":
                    response = {
                        "type": "control_response",
                        "response": {
                            "subtype": "success",
                            "request_id": request_id,
                            "response": {
                                "commands": [],
                                "output_style": "default",
                            },
                        },
                    }
                    print(json.dumps(response))
                    sys.stdout.flush()
            else:
                stdin_messages.append(line.strip())
        except (json.JSONDecodeError, KeyError):
            stdin_messages.append(line.strip())

    # Verify we got 2 user messages
    assert len(stdin_messages) == 2, f"Expected 2 messages, got {len(stdin_messages)}"
    assert '"First"' in stdin_messages[0]
    assert '"Second"' in stdin_messages[1]

    # Output a valid result
    result = {
        "type": "result",
        "uuid": "msg-004",
        "subtype": "success",
        "duration_ms": 100,
        "duration_api_ms": 50,
        "is_error": False,
        "num_turns": 1,
        "session_id": "test",
        "total_cost_usd": 0.001,
        "stop_reason": None,
        "permission_denials": [],
        "modelUsage": {
            "opus": ModelUsage(
                inputTokens=100,
                outputTokens=50,
                cacheReadInputTokens=0,
                cacheCreationInputTokens=0,
                webSearchRequests=0,
                costUSD=0.001,
                contextWindow=0,
                maxOutputTokens=0,
            )
        },
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        },
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
