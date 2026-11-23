"""Chain reconstruction through non-message entries and parallel tool calls."""

from __future__ import annotations

from typing import Any

from pydantic import TypeAdapter

from clawd_code_sdk.models import AssistantMessage, UserMessage
from clawd_code_sdk.storage.chain import (
    find_leaf,
    index_chain_entries,
    resolve_chain,
    walk_ancestry,
)
from clawd_code_sdk.storage.models import ClaudeJSONLEntry
from clawd_code_sdk.storage.replay import replay_entries


ADAPTER = TypeAdapter[list[ClaudeJSONLEntry]](list[ClaudeJSONLEntry])
_clock = iter(range(10_000))


def _base(uuid: str, parent: str | None, **extra: Any) -> dict[str, Any]:
    ts = f"2026-01-01T00:00:{next(_clock):05d}Z"
    return {"uuid": uuid, "parentUuid": parent, "sessionId": "s1", "timestamp": ts, **extra}


def user(uuid: str, parent: str | None, text: str = "hi") -> dict[str, Any]:
    return _base(uuid, parent, type="user", message={"role": "user", "content": text})


def result(uuid: str, parent: str, call_id: str, source: str | None = None) -> dict[str, Any]:
    content = [{"type": "tool_result", "tool_use_id": call_id, "content": "ok"}]
    extra = {"sourceToolAssistantUUID": source} if source else {}
    return _base(uuid, parent, type="user", message={"role": "user", "content": content}, **extra)


def assistant(uuid: str, parent: str, msg_id: str, call_id: str | None = None) -> dict[str, Any]:
    block = (
        {"type": "tool_use", "id": call_id, "name": "Read", "input": {}}
        if call_id
        else {"type": "text", "text": "done"}
    )
    message = {"model": "m", "id": msg_id, "role": "assistant", "content": [block]}
    return _base(uuid, parent, type="assistant", message=message)


def attachment(uuid: str, parent: str | None) -> dict[str, Any]:
    return _base(uuid, parent, type="attachment", attachment={"type": "date", "date": "x"})


def system(uuid: str, parent: str) -> dict[str, Any]:
    return _base(uuid, parent, type="system", subtype="turn_duration", durationMs=1)


def load(*rows: dict[str, Any]) -> list[ClaudeJSONLEntry]:
    return ADAPTER.validate_python(list(rows))


def uuids(entries: list[Any]) -> list[str]:
    return [e.uuid for e in entries]


def test_chain_runs_through_attachments_and_system_entries() -> None:
    entries = load(
        attachment("at1", None),
        user("u1", "at1"),
        attachment("at2", "u1"),
        assistant("a1", "at2", "msg_1"),
        system("sy1", "a1"),
        user("u2", "sy1"),
        assistant("a2", "u2", "msg_2"),
    )
    assert uuids(resolve_chain(entries)) == ["at1", "u1", "at2", "a1", "sy1", "u2", "a2"]
    index = index_chain_entries(entries)
    assert uuids(walk_ancestry(index, "a2")) == ["a2", "u2", "sy1", "a1", "at2", "u1", "at1"]
    assert uuids(walk_ancestry(index, "a2", include_start=False))[0] == "u2"


def test_find_leaf_prefers_main_thread() -> None:
    side = assistant("side", "a1", "msg_s")
    side["isSidechain"] = True
    entries = load(user("u1", None), assistant("a1", "u1", "msg_1"), side)
    leaf = find_leaf(entries)
    assert leaf is not None
    assert leaf.uuid == "a1"


def test_parallel_tool_calls_and_results_are_recovered() -> None:
    # One response with three parallel tool calls, written as three chained entries.
    # Each result's parent is its own call; the next turn continues from the last result.
    entries = load(
        user("u1", None),
        assistant("c1", "u1", "msg_1", "t1"),
        assistant("c2", "c1", "msg_1", "t2"),
        assistant("c3", "c2", "msg_1", "t3"),
        result("r1", "c1", "t1"),
        result("r3", "c3", "t3"),
        result("r2", "c2", "t2"),
        assistant("a2", "r2", "msg_2"),
    )
    # The missing call goes right after the response's last on-chain entry, then the results.
    assert uuids(resolve_chain(entries)) == ["u1", "c1", "c2", "c3", "r1", "r3", "r2", "a2"]
    # Without recovery the walk only sees one branch.
    plain = uuids(resolve_chain(entries, recover_parallel_tool_calls=False))
    assert plain == ["u1", "c1", "c2", "r2", "a2"]


def test_recovery_ignores_abandoned_responses_and_duplicates() -> None:
    entries = load(
        user("u1", None),
        assistant("old", "u1", "msg_old", "t0"),  # abandoned branch (e.g. retried request)
        result("rold", "old", "t0"),
        assistant("c1", "u1", "msg_1", "t1"),
        result("r1", "c1", "t1"),
        result("dup", "c1", "t1"),  # second result for an answered call
        assistant("a2", "r1", "msg_2"),
    )
    assert uuids(resolve_chain(entries)) == ["u1", "c1", "r1", "a2"]


def test_replay_with_leaf_walks_through_attachments() -> None:
    entries = load(
        user("u1", None),
        attachment("at1", "u1"),
        assistant("a1", "at1", "msg_1"),
        user("u2", "a1", "again"),
        attachment("at2", "u2"),
        assistant("a2", "at2", "msg_2"),
    )
    messages = list(replay_entries(entries, leaf_uuid="a2"))
    kinds = [type(m) for m in messages]
    assert kinds == [UserMessage, AssistantMessage, UserMessage, AssistantMessage]


def test_chain_entry_union_covers_all_chain_models() -> None:
    from typing import get_args

    from clawd_code_sdk.storage import models

    chain_models = {
        obj
        for obj in vars(models).values()
        if isinstance(obj, type)
        and issubclass(obj, models.ClaudeEntryBase)
        and "type" in obj.model_fields
        and not obj.__name__.endswith("Base")
    }
    assert chain_models == set(get_args(models.ClaudeChainEntry))


def test_messages_withdrawn_by_a_refusal_are_left_out() -> None:
    refusal = _base(
        "sy1",
        "a1",
        type="system",
        subtype="model_refusal_fallback",
        content="retried with a fallback model",
        retractedMessageUuids=["a1"],
        refusedUserMessageUuid="u1",
    )
    entries = load(
        user("u1", None),
        assistant("a1", "u1", "msg_1"),
        refusal,
        assistant("a2", "sy1", "msg_2"),
    )
    # The walk passes through the withdrawn message, but it is not returned.
    assert uuids(resolve_chain(entries)) == ["u1", "sy1", "a2"]
    assert "a1" in uuids(walk_ancestry(index_chain_entries(entries), "a2"))
