"""Benchmark different Pydantic parsing strategies for SDK messages.

Usage:
    1. Record messages by setting env var before running the agent:
       CLAWD_RECORD_MESSAGES=/tmp/recorded_messages.jsonl

    2. Run this benchmark against the recorded data:
       uv run python scripts/benchmark_parsing.py /tmp/recorded_messages.jsonl
"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path
import sys
import time
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from clawd_code_sdk.models import message_adapter


if TYPE_CHECKING:
    from pydantic import TypeAdapter

    from clawd_code_sdk.models import Message


def load_messages(path: Path) -> list[dict[str, Any]]:
    """Load recorded raw message dicts from JSONL file."""
    messages = []
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped:
            messages.append(json.loads(stripped))
    print(f"Loaded {len(messages)} messages from {path}")

    # Show message type distribution
    type_counts: dict[str, int] = {}
    for msg in messages:
        t = msg.get("type", "<unknown>")
        type_counts[t] = type_counts.get(t, 0) + 1
    for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {count}")
    print()
    return messages


def benchmark_validate_python(
    adapter: TypeAdapter[Message], messages: list[dict[str, Any]], iterations: int
) -> float:
    """Benchmark TypeAdapter.validate_python()."""
    start = time.perf_counter()
    for _ in range(iterations):
        for msg in messages:
            with contextlib.suppress(ValidationError):
                adapter.validate_python(msg)
    return time.perf_counter() - start


def benchmark_validate_json(
    adapter: TypeAdapter[Message],
    json_bytes_list: list[bytes],
    iterations: int,
) -> float:
    """Benchmark TypeAdapter.validate_json()."""
    start = time.perf_counter()
    for _ in range(iterations):
        for data in json_bytes_list:
            with contextlib.suppress(ValidationError):
                adapter.validate_json(data)
    return time.perf_counter() - start


def benchmark_json_then_validate(
    adapter: TypeAdapter[Message],
    json_bytes_list: list[bytes],
    iterations: int,
) -> float:
    """Benchmark json.loads() + validate_python() (current approach)."""
    start = time.perf_counter()
    for _ in range(iterations):
        for data in json_bytes_list:
            try:
                d = json.loads(data)
                adapter.validate_python(d)
            except (ValidationError, json.JSONDecodeError):
                pass
    return time.perf_counter() - start


def benchmark_dump_python(
    adapter: TypeAdapter[Message],
    parsed_messages: list[Message],
    iterations: int,
) -> float:
    """Benchmark TypeAdapter.dump_python() (serialization)."""
    start = time.perf_counter()
    for _ in range(iterations):
        for msg in parsed_messages:
            adapter.dump_python(msg)
    return time.perf_counter() - start


def benchmark_dump_json(
    adapter: TypeAdapter[Message],
    parsed_messages: list[Message],
    iterations: int,
) -> float:
    """Benchmark TypeAdapter.dump_json() (serialization to JSON bytes)."""
    start = time.perf_counter()
    for _ in range(iterations):
        for msg in parsed_messages:
            adapter.dump_json(msg)
    return time.perf_counter() - start


def benchmark_model_dump(
    parsed_messages: list[Message],
    iterations: int,
) -> float:
    """Benchmark model.model_dump() (per-instance serialization)."""
    start = time.perf_counter()
    for _ in range(iterations):
        for msg in parsed_messages:
            msg.model_dump()  # type: ignore[union-attr]
    return time.perf_counter() - start


def benchmark_model_construct(
    messages: list[dict[str, Any]],
    iterations: int,
) -> float:
    """Benchmark model_construct() — no validation, manual dispatch + direct attribute set."""
    from clawd_code_sdk.models import (
        AssistantMessage,
        InitSystemMessage,
        ResultSuccessMessage,
        StreamEvent,
        UserMessage,
    )

    type_map: dict[str, type] = {
        "stream_event": StreamEvent,
        "assistant": AssistantMessage,
        "user": UserMessage,
        "system": InitSystemMessage,
        "result": ResultSuccessMessage,
    }
    start = time.perf_counter()
    for _ in range(iterations):
        for msg in messages:
            cls = type_map.get(msg.get("type", ""))
            if cls:
                cls.model_construct(**msg)
    return time.perf_counter() - start


def benchmark_no_validation(messages: list[dict[str, Any]], iterations: int) -> float:
    """Benchmark raw dict access without any Pydantic parsing (baseline)."""
    start = time.perf_counter()
    for _ in range(iterations):
        for msg in messages:
            _ = msg.get("type")
            _ = msg.get("message", {})
    return time.perf_counter() - start


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <recorded_messages.jsonl> [iterations]")
        sys.exit(1)

    path = Path(sys.argv[1])
    iterations = int(sys.argv[2]) if len(sys.argv) > 2 else 100

    if not path.exists():
        print(f"Error: {path} not found")
        sys.exit(1)

    messages = load_messages(path)
    if not messages:
        print("No messages to benchmark")
        sys.exit(1)

    json_bytes_list = [json.dumps(m).encode() for m in messages]
    total_msgs = len(messages) * iterations

    print(f"Benchmarking {len(messages)} messages x {iterations} iterations = {total_msgs} total")
    print(f"{'Strategy':<40} {'Total (s)':>10} {'per msg (µs)':>14} {'msgs/sec':>12}")
    print("-" * 80)

    # 1. Current approach: validate_python(dict)
    elapsed = benchmark_validate_python(message_adapter, messages, iterations)
    print(
        f"{'validate_python(dict)':<40} {elapsed:>10.3f}"
        f" {elapsed / total_msgs * 1e6:>14.1f} {total_msgs / elapsed:>12.0f}"
    )

    # 2. validate_json(bytes) — skips json.loads, Pydantic parses JSON directly
    elapsed = benchmark_validate_json(message_adapter, json_bytes_list, iterations)
    print(
        f"{'validate_json(bytes)':<40} {elapsed:>10.3f}"
        f" {elapsed / total_msgs * 1e6:>14.1f} {total_msgs / elapsed:>12.0f}"
    )

    # 3. json.loads + validate_python (simulates reading from transport)
    elapsed = benchmark_json_then_validate(message_adapter, json_bytes_list, iterations)
    print(
        f"{'json.loads + validate_python':<40} {elapsed:>10.3f}"
        f" {elapsed / total_msgs * 1e6:>14.1f} {total_msgs / elapsed:>12.0f}"
    )

    # 4. Parse once for serialization benchmarks
    parsed = [message_adapter.validate_python(m) for m in messages]

    # 5. dump_python (serialization to dict)
    elapsed = benchmark_dump_python(message_adapter, parsed, iterations)
    print(
        f"{'dump_python (to dict)':<40} {elapsed:>10.3f}"
        f" {elapsed / total_msgs * 1e6:>14.1f} {total_msgs / elapsed:>12.0f}"
    )

    # 6. dump_json (serialization to JSON bytes)
    elapsed = benchmark_dump_json(message_adapter, parsed, iterations)
    print(
        f"{'dump_json (to bytes)':<40} {elapsed:>10.3f}"
        f" {elapsed / total_msgs * 1e6:>14.1f} {total_msgs / elapsed:>12.0f}"
    )

    # 7. model_dump (per-instance)
    elapsed = benchmark_model_dump(parsed, iterations)
    print(
        f"{'model.model_dump()':<40} {elapsed:>10.3f}"
        f" {elapsed / total_msgs * 1e6:>14.1f} {total_msgs / elapsed:>12.0f}"
    )

    # 8. model_construct (no validation, manual type dispatch)
    elapsed = benchmark_model_construct(messages, iterations)
    print(
        f"{'model_construct (no validation)':<40} {elapsed:>10.3f}"
        f" {elapsed / total_msgs * 1e6:>14.1f} {total_msgs / elapsed:>12.0f}"
    )

    # 9. Raw dict access (baseline)
    elapsed = benchmark_no_validation(messages, iterations)
    print(
        f"{'raw dict access (baseline)':<40} {elapsed:>10.3f}"
        f" {elapsed / total_msgs * 1e6:>14.1f} {total_msgs / elapsed:>12.0f}"
    )


if __name__ == "__main__":
    main()
