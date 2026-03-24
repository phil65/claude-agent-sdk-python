"""Mock Claude CLI server for testing message streaming.

Reads JSON-RPC messages from stdin, handles the initialize control request,
validates the user message, and emits a success result on stdout.
"""

from __future__ import annotations

import json
import sys

from clawd_code_sdk.models.messages import ModelUsage, ResultSuccessMessage, Usage


def main() -> None:
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

            elif msg.get("type") == "user":
                # Validate the user message content contains both prompts
                content = msg.get("message", {}).get("content", [])
                assert isinstance(content, list), f"Expected list content, got {type(content)}"
                texts = [b["text"] for b in content if b.get("type") == "text"]
                assert "First" in texts, f"Expected 'First' in {texts}"
                assert "Second" in texts, f"Expected 'Second' in {texts}"

                # Output a valid result
                result = ResultSuccessMessage(
                    uuid="msg-004",
                    session_id="test",
                    duration_ms=100,
                    duration_api_ms=50,
                    is_error=False,
                    num_turns=1,
                    total_cost_usd=0.001,
                    stop_reason=None,
                    model_usage={
                        "opus": ModelUsage(
                            input_tokens=100,
                            output_tokens=50,
                            cache_read_input_tokens=0,
                            cache_creation_input_tokens=0,
                            web_search_requests=0,
                            cost_usd=0.001,  # pyright: ignore[reportCallIssue]
                            context_window=0,
                            max_output_tokens=0,
                        )
                    },
                    usage=Usage(
                        input_tokens=100,
                        output_tokens=50,
                        cache_creation_input_tokens=0,
                        cache_read_input_tokens=0,
                    ),
                ).model_dump(by_alias=True)
                print(json.dumps(result))
                sys.stdout.flush()
                break
        except (json.JSONDecodeError, KeyError):
            pass


if __name__ == "__main__":
    main()
