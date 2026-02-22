"""Tests for Session and SessionManager."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
import json
from unittest.mock import AsyncMock

import anyio
import pytest

from clawd_code_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
)
from clawd_code_sdk.session import (
    ConversationTurn,
    Session,
    SessionManager,
    SessionSnapshot,
    ToolCallSummary,
)


def _create_mock_transport_with_messages(messages: list[dict]) -> AsyncMock:
    """Create a mock transport that handles initialization and returns messages."""
    mock_transport = AsyncMock()
    mock_transport.connect = AsyncMock()
    mock_transport.close = AsyncMock()
    mock_transport.end_input = AsyncMock()

    written_messages: list[str] = []

    async def mock_write(data: str) -> None:
        written_messages.append(data)

    mock_transport.write = AsyncMock(side_effect=mock_write)

    async def mock_receive():
        await asyncio.sleep(0.01)

        for msg_str in written_messages:
            try:
                msg = json.loads(msg_str.strip())
                if (
                    msg.get("type") == "control_request"
                    and msg.get("request", {}).get("subtype") == "initialize"
                ):
                    yield {
                        "type": "control_response",
                        "response": {
                            "request_id": msg.get("request_id"),
                            "subtype": "success",
                            "response": {
                                "commands": [],
                                "outputStyle": "default",
                                "pid": 12345,
                            },
                        },
                    }
                    break
            except (json.JSONDecodeError, KeyError, AttributeError):
                pass

        for message in messages:
            yield message

    mock_transport.read_messages = mock_receive
    return mock_transport


ASSISTANT_MSG = {
    "type": "assistant",
    "message": {
        "role": "assistant",
        "content": [{"type": "text", "text": "Hello, world!"}],
        "model": "claude-sonnet-4-5-20250514",
    },
}

TOOL_USE_MSG = {
    "type": "assistant",
    "message": {
        "role": "assistant",
        "content": [
            {"type": "text", "text": "Let me read that."},
            {
                "type": "tool_use",
                "id": "tool-123",
                "name": "Read",
                "input": {"path": "/tmp/test.py"},
            },
        ],
        "model": "claude-sonnet-4-5-20250514",
    },
}

RESULT_MSG = asdict(
    ResultMessage(
        uuid="msg-001",
        session_id="test-session",
        subtype="success",
        duration_ms=1500,
        duration_api_ms=1200,
        is_error=False,
        num_turns=1,
        total_cost_usd=0.005,
        usage={
            "input_tokens": 200,
            "output_tokens": 100,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        },
    )
)


class TestToolCallSummary:
    """Test ToolCallSummary dataclass."""

    def test_frozen(self):
        summary = ToolCallSummary(tool_use_id="t1", tool_name="Read", input={"path": "/x"})
        assert summary.tool_use_id == "t1"
        assert summary.tool_name == "Read"
        assert summary.input == {"path": "/x"}
        with pytest.raises(AttributeError):
            summary.tool_name = "Write"  # type: ignore[misc]


class TestConversationTurn:
    """Test ConversationTurn dataclass."""

    def test_frozen(self):
        result = ResultMessage(
            uuid="r1",
            session_id="s1",
            subtype="success",
            duration_ms=100,
            duration_api_ms=80,
            is_error=False,
            num_turns=1,
            total_cost_usd=0.01,
            usage={
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
        )
        turn = ConversationTurn(
            messages=(),
            result=result,
            text="hello",
            tool_calls=(),
            cost_usd=0.01,
            duration_ms=100,
        )
        assert turn.text == "hello"
        assert turn.cost_usd == 0.01
        with pytest.raises(AttributeError):
            turn.text = "bye"  # type: ignore[misc]


class TestSession:
    """Test Session lifecycle and methods."""

    def test_initial_state(self):
        """Session starts in CREATED state."""
        mock_transport = _create_mock_transport_with_messages([])
        from clawd_code_sdk import ClaudeSDKClient

        client = ClaudeSDKClient(transport=mock_transport)
        session = Session("test-id", client)

        assert session.session_id == "test-id"
        assert session.state == "created"
        assert session.turns == []
        assert session.total_cost_usd == 0.0
        assert session.client is client

    def test_snapshot(self):
        """Snapshot reflects current state."""
        mock_transport = _create_mock_transport_with_messages([])
        from clawd_code_sdk import ClaudeSDKClient

        client = ClaudeSDKClient(
            options=ClaudeAgentOptions(model="claude-sonnet-4-5-20250514", cwd="/tmp"),
            transport=mock_transport,
        )
        session = Session("snap-id", client)
        snap = session.snapshot

        assert isinstance(snap, SessionSnapshot)
        assert snap.session_id == "snap-id"
        assert snap.state == "created"
        assert snap.model == "claude-sonnet-4-5-20250514"
        assert snap.cwd == "/tmp"
        assert snap.turn_count == 0
        assert snap.total_cost_usd == 0.0

    def test_send_requires_idle_state(self):
        """send() raises if session is not IDLE."""

        async def _test():
            mock_transport = _create_mock_transport_with_messages([])
            from clawd_code_sdk import ClaudeSDKClient

            client = ClaudeSDKClient(transport=mock_transport)
            session = Session("test-id", client)
            # State is CREATED, not IDLE
            with pytest.raises(RuntimeError, match="expected 'idle'"):
                async for _ in session.send("hi"):
                    pass

        anyio.run(_test)

    def test_send_streams_and_collects_turn(self):
        """send() yields messages and records a ConversationTurn."""

        async def _test():
            transport = _create_mock_transport_with_messages([ASSISTANT_MSG, RESULT_MSG])

            async with SessionManager() as mgr:
                session = await mgr.create_session("s1", transport=transport)
                assert session.state == "idle"

                messages = []
                async for msg in session.send("hello"):
                    messages.append(msg)

                assert len(messages) == 2
                assert isinstance(messages[0], AssistantMessage)
                assert isinstance(messages[1], ResultMessage)

                assert len(session.turns) == 1
                turn = session.turns[0]
                assert turn.text == "Hello, world!"
                assert turn.cost_usd == 0.005
                assert turn.duration_ms == 1500
                assert turn.tool_calls == ()
                assert session.state == "idle"

        anyio.run(_test)

    def test_send_with_tool_calls(self):
        """send() extracts tool calls from assistant messages."""

        async def _test():
            transport = _create_mock_transport_with_messages([TOOL_USE_MSG, RESULT_MSG])

            async with SessionManager() as mgr:
                session = await mgr.create_session("s1", transport=transport)

                messages = [msg async for msg in session.send("read file")]

                assert len(messages) == 2
                assert len(session.turns) == 1
                turn = session.turns[0]
                assert turn.text == "Let me read that."
                assert len(turn.tool_calls) == 1
                tc = turn.tool_calls[0]
                assert tc.tool_use_id == "tool-123"
                assert tc.tool_name == "Read"
                assert tc.input == {"path": "/tmp/test.py"}

        anyio.run(_test)

    def test_send_and_collect(self):
        """send_and_collect() returns a ConversationTurn directly."""

        async def _test():
            transport = _create_mock_transport_with_messages([ASSISTANT_MSG, RESULT_MSG])

            async with SessionManager() as mgr:
                session = await mgr.create_session("s1", transport=transport)
                turn = await session.send_and_collect("hello")

                assert isinstance(turn, ConversationTurn)
                assert turn.text == "Hello, world!"
                assert turn.cost_usd == 0.005

        anyio.run(_test)

    def test_close_is_idempotent(self):
        """Closing a session twice doesn't raise."""

        async def _test():
            transport = _create_mock_transport_with_messages([])

            async with SessionManager() as mgr:
                session = await mgr.create_session("s1", transport=transport)
                await session.close()
                assert session.state == "disconnected"
                await session.close()  # second close is fine
                assert session.state == "disconnected"

        anyio.run(_test)

    def test_total_cost_accumulates(self):
        """total_cost_usd sums across turns."""

        async def _test():
            result2 = {**RESULT_MSG, "total_cost_usd": 0.010, "uuid": "msg-002"}
            # Transport that returns two rounds of messages
            transport1 = _create_mock_transport_with_messages(
                [ASSISTANT_MSG, RESULT_MSG, ASSISTANT_MSG, result2]
            )

            async with SessionManager() as mgr:
                session = await mgr.create_session("s1", transport=transport1)
                await session.send_and_collect("first")
                # After first turn, need to send another query
                # The transport will yield the next assistant+result pair
                await session.send_and_collect("second")

                assert session.total_cost_usd == pytest.approx(0.015)

        anyio.run(_test)


class TestSessionManager:
    """Test SessionManager operations."""

    def test_create_session_auto_id(self):
        """create_session with no ID generates a UUID."""

        async def _test():
            transport = _create_mock_transport_with_messages([])

            async with SessionManager() as mgr:
                session = await mgr.create_session(transport=transport)
                assert len(session.session_id) == 32  # hex UUID
                assert session.state == "idle"

        anyio.run(_test)

    def test_create_session_duplicate_raises(self):
        """Creating a session with an existing ID raises ValueError."""

        async def _test():
            t1 = _create_mock_transport_with_messages([])
            t2 = _create_mock_transport_with_messages([])

            async with SessionManager() as mgr:
                await mgr.create_session("dup", transport=t1)
                with pytest.raises(ValueError, match="already exists"):
                    await mgr.create_session("dup", transport=t2)

        anyio.run(_test)

    def test_create_session_without_connect(self):
        """create_session(connect=False) leaves session in CREATED state."""

        async def _test():
            transport = _create_mock_transport_with_messages([])

            async with SessionManager() as mgr:
                session = await mgr.create_session("lazy", transport=transport, connect=False)
                assert session.state == "created"

        anyio.run(_test)

    def test_get_session_and_getitem(self):
        """get_session() and __getitem__ return the same session."""

        async def _test():
            transport = _create_mock_transport_with_messages([])

            async with SessionManager() as mgr:
                session = await mgr.create_session("x", transport=transport)
                assert mgr.get_session("x") is session
                assert mgr["x"] is session

        anyio.run(_test)

    def test_get_session_missing_raises(self):
        """get_session() raises KeyError for unknown ID."""

        async def _test():
            async with SessionManager() as mgr:
                with pytest.raises(KeyError, match="not found"):
                    mgr.get_session("nope")
                with pytest.raises(KeyError):
                    mgr["nope"]

        anyio.run(_test)

    def test_contains_len_iter(self):
        """__contains__, __len__, __iter__ work correctly."""

        async def _test():
            t1 = _create_mock_transport_with_messages([])
            t2 = _create_mock_transport_with_messages([])

            async with SessionManager() as mgr:
                await mgr.create_session("a", transport=t1)
                await mgr.create_session("b", transport=t2)

                assert "a" in mgr
                assert "c" not in mgr
                assert len(mgr) == 2
                assert sorted(mgr) == ["a", "b"]

        anyio.run(_test)

    def test_sessions_property_is_copy(self):
        """sessions property returns a copy, not the internal dict."""

        async def _test():
            transport = _create_mock_transport_with_messages([])

            async with SessionManager() as mgr:
                await mgr.create_session("x", transport=transport)
                sessions_copy = mgr.sessions
                sessions_copy.clear()
                assert len(mgr) == 1  # internal dict unaffected

        anyio.run(_test)

    def test_active_sessions(self):
        """active_sessions only includes IDLE/RESPONDING sessions."""

        async def _test():
            t1 = _create_mock_transport_with_messages([])
            t2 = _create_mock_transport_with_messages([])

            async with SessionManager() as mgr:
                s1 = await mgr.create_session("active", transport=t1)
                await mgr.create_session("lazy", transport=t2, connect=False)

                active = mgr.active_sessions
                assert "active" in active
                assert "lazy" not in active

                await s1.close()
                assert len(mgr.active_sessions) == 0

        anyio.run(_test)

    def test_close_session_removes(self):
        """close_session() disconnects and removes the session."""

        async def _test():
            transport = _create_mock_transport_with_messages([])

            async with SessionManager() as mgr:
                await mgr.create_session("x", transport=transport)
                assert "x" in mgr
                await mgr.close_session("x")
                assert "x" not in mgr
                assert len(mgr) == 0

        anyio.run(_test)

    def test_close_session_missing_raises(self):
        """close_session() raises KeyError for unknown ID."""

        async def _test():
            async with SessionManager() as mgr:
                with pytest.raises(KeyError):
                    await mgr.close_session("nope")

        anyio.run(_test)

    def test_close_all(self):
        """close_all() disconnects and removes all sessions."""

        async def _test():
            t1 = _create_mock_transport_with_messages([])
            t2 = _create_mock_transport_with_messages([])

            async with SessionManager() as mgr:
                await mgr.create_session("a", transport=t1)
                await mgr.create_session("b", transport=t2)
                await mgr.close_all()
                assert len(mgr) == 0

        anyio.run(_test)

    def test_context_manager_closes_all(self):
        """Exiting the context manager closes all sessions."""

        async def _test():
            transport = _create_mock_transport_with_messages([])

            mgr = SessionManager()
            async with mgr:
                session = await mgr.create_session("x", transport=transport)

            # After context exit, session should be disconnected
            assert session.state == "disconnected"
            assert len(mgr) == 0

        anyio.run(_test)

    def test_max_concurrent_sessions(self):
        """max_concurrent_sessions enforces the limit."""

        async def _test():
            t1 = _create_mock_transport_with_messages([])
            t2 = _create_mock_transport_with_messages([])

            async with SessionManager(max_concurrent_sessions=1) as mgr:
                await mgr.create_session("a", transport=t1)
                with pytest.raises(RuntimeError, match="Maximum concurrent sessions"):
                    await mgr.create_session("b", transport=t2)

        anyio.run(_test)

    def test_max_concurrent_sessions_respects_disconnected(self):
        """Disconnected sessions don't count toward the limit."""

        async def _test():
            t1 = _create_mock_transport_with_messages([])
            t2 = _create_mock_transport_with_messages([])

            async with SessionManager(max_concurrent_sessions=1) as mgr:
                s1 = await mgr.create_session("a", transport=t1)
                await s1.close()
                # Now slot is free
                s2 = await mgr.create_session("b", transport=t2)
                assert s2.state == "idle"

        anyio.run(_test)

    def test_total_cost_usd(self):
        """total_cost_usd sums across all sessions."""

        async def _test():
            t1 = _create_mock_transport_with_messages([ASSISTANT_MSG, RESULT_MSG])
            result2 = {**RESULT_MSG, "total_cost_usd": 0.010, "uuid": "msg-002"}
            t2 = _create_mock_transport_with_messages([ASSISTANT_MSG, result2])

            async with SessionManager() as mgr:
                s1 = await mgr.create_session("a", transport=t1)
                s2 = await mgr.create_session("b", transport=t2)
                await s1.send_and_collect("hi")
                await s2.send_and_collect("hi")

                assert mgr.total_cost_usd == pytest.approx(0.015)

        anyio.run(_test)

    def test_snapshots(self):
        """snapshots() returns a dict of SessionSnapshot for all sessions."""

        async def _test():
            t1 = _create_mock_transport_with_messages([])
            t2 = _create_mock_transport_with_messages([])

            async with SessionManager() as mgr:
                await mgr.create_session("a", transport=t1)
                await mgr.create_session("b", transport=t2, connect=False)

                snaps = mgr.snapshots()
                assert set(snaps.keys()) == {"a", "b"}
                assert isinstance(snaps["a"], SessionSnapshot)
                assert snaps["a"].state == "idle"
                assert snaps["b"].state == "created"

        anyio.run(_test)

    def test_resume_session(self):
        """resume_session() sets continue_conversation and session_id."""

        async def _test():
            transport = _create_mock_transport_with_messages([])

            async with SessionManager() as mgr:
                session = await mgr.resume_session("prev-session-id", transport=transport)
                assert session.session_id == "prev-session-id"
                assert session.client.options.session_id == "prev-session-id"
                assert session.client.options.continue_conversation is True
                assert session.state == "idle"

        anyio.run(_test)

    def test_resume_session_with_options(self):
        """resume_session() merges caller options with resume fields."""

        async def _test():
            transport = _create_mock_transport_with_messages([])
            opts = ClaudeAgentOptions(model="claude-sonnet-4-5-20250514")

            async with SessionManager() as mgr:
                session = await mgr.resume_session("prev-id", options=opts, transport=transport)
                assert session.client.options.model == "claude-sonnet-4-5-20250514"
                assert session.client.options.session_id == "prev-id"
                assert session.client.options.continue_conversation is True

        anyio.run(_test)
