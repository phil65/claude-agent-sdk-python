"""Session manager for managing multiple Claude SDK client sessions."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal
import uuid

from clawd_code_sdk.client import ClaudeSDKClient
from clawd_code_sdk.models import ClaudeAgentOptions as Opts
from clawd_code_sdk.models.content_blocks import TextBlock, ToolUseBlock
from clawd_code_sdk.models.input_types import ToolInput  # noqa: TC001
from clawd_code_sdk.models.messages import AssistantMessage, ResultMessage


if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from clawd_code_sdk._internal.transport import Transport
    from clawd_code_sdk.models import ClaudeAgentOptions, Message, PermissionMode


SessionState = Literal[
    "created",
    "connecting",
    "idle",
    "responding",
    "disconnected",
    "error",
]


@dataclass(frozen=True)
class ToolCallSummary:
    """Summary of a single tool invocation within a conversation turn."""

    tool_use_id: str
    tool_name: str
    input: ToolInput | dict[str, Any]


@dataclass(frozen=True)
class ConversationTurn:
    """Collected result of a single send/receive cycle."""

    messages: tuple[Message, ...]
    result: ResultMessage
    text: str
    tool_calls: tuple[ToolCallSummary, ...]
    cost_usd: float | None
    duration_ms: int


@dataclass(frozen=True)
class SessionSnapshot:
    """Read-only snapshot of session metadata at a point in time."""

    session_id: str
    state: SessionState
    model: str | None
    cwd: str | None
    created_at: datetime
    last_activity: datetime
    turn_count: int
    total_cost_usd: float


def _extract_turn(messages: list[Message], result: ResultMessage) -> ConversationTurn:
    """Build a ConversationTurn from collected messages and a result."""
    text_parts: list[str] = []
    tool_calls: list[ToolCallSummary] = []

    for msg in messages:
        match msg:
            case AssistantMessage(content=content):
                for block in content:
                    match block:
                        case TextBlock(text=text):
                            text_parts.append(text)
                        case ToolUseBlock(id=tool_id, name=name, input=inp):
                            call = ToolCallSummary(tool_use_id=tool_id, tool_name=name, input=inp)
                            tool_calls.append(call)

    return ConversationTurn(
        messages=tuple(messages),
        result=result,
        text="".join(text_parts),
        tool_calls=tuple(tool_calls),
        cost_usd=result.total_cost_usd,
        duration_ms=result.duration_ms,
    )


class Session:
    """A managed Claude session wrapping a ClaudeSDKClient.

    Not constructed directly — use ``SessionManager.create_session()``.
    """

    def __init__(self, session_id: str, client: ClaudeSDKClient) -> None:
        self._session_id = session_id
        self._client = client
        self._state: SessionState = "created"
        self._turns: list[ConversationTurn] = []
        self._created_at = datetime.now(UTC)
        self._last_activity = self._created_at

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def state(self) -> SessionState:
        return self._state

    @property
    def client(self) -> ClaudeSDKClient:
        """Access the underlying client for low-level operations."""
        return self._client

    @property
    def turns(self) -> list[ConversationTurn]:
        """All completed conversation turns in this session."""
        return list(self._turns)

    @property
    def total_cost_usd(self) -> float:
        """Accumulated cost across all turns."""
        return sum(t.cost_usd for t in self._turns if t.cost_usd is not None)

    @property
    def snapshot(self) -> SessionSnapshot:
        """Current metadata snapshot."""
        return SessionSnapshot(
            session_id=self._session_id,
            state=self._state,
            model=self._client.options.model,
            cwd=str(self._client.options.cwd) if self._client.options.cwd else None,
            created_at=self._created_at,
            last_activity=self._last_activity,
            turn_count=len(self._turns),
            total_cost_usd=self.total_cost_usd,
        )

    async def send(self, prompt: str) -> AsyncIterator[Message]:
        """Send a prompt and stream response messages.

        Combines ``client.query()`` + ``client.receive_response()`` into one call.
        Yields every message including the final ``ResultMessage``, then stops.
        The completed ``ConversationTurn`` is appended to ``self.turns``.

        Raises:
            RuntimeError: If the session is not in IDLE state.
        """
        if self._state != "idle":
            msg = (
                f"Cannot send: session {self._session_id!r} is in state "
                f"{self._state!r}, expected 'idle'"
            )
            raise RuntimeError(msg)

        self._state = "responding"
        self._last_activity = datetime.now(UTC)
        collected: list[Message] = []

        try:
            await self._client.query(prompt)
            async for message in self._client.receive_response():
                collected.append(message)
                yield message
                if isinstance(message, ResultMessage):
                    turn = _extract_turn(collected, message)
                    self._turns.append(turn)
                    self._last_activity = datetime.now(UTC)
            self._state = "idle"
        except Exception:
            self._state = "error"
            raise

    async def send_and_collect(self, prompt: str) -> ConversationTurn:
        """Send a prompt and return the full collected response.

        Convenience for cases where streaming is not needed.

        Raises:
            RuntimeError: If the session is not in IDLE state or no
                ResultMessage was received.
        """
        last_turn_count = len(self._turns)
        async for _ in self.send(prompt):
            pass
        if len(self._turns) <= last_turn_count:
            msg = "No ResultMessage received — response may have been interrupted"
            raise RuntimeError(msg)
        return self._turns[-1]

    async def interrupt(self) -> None:
        """Send interrupt signal to the current response."""
        await self._client.interrupt()

    async def set_model(self, model: str | None = None) -> None:
        """Change the AI model during conversation."""
        await self._client.set_model(model)

    async def set_permission_mode(self, mode: PermissionMode) -> None:
        """Change permission mode during conversation."""
        await self._client.set_permission_mode(mode)

    async def set_max_thinking_tokens(self, max_thinking_tokens: int) -> None:
        """Set the maximum number of thinking tokens."""
        await self._client.set_max_thinking_tokens(max_thinking_tokens)

    async def close(self) -> None:
        """Disconnect and release resources. Idempotent."""
        if self._state == "disconnected":
            return
        try:
            await self._client.disconnect()
        finally:
            self._state = "disconnected"


class SessionManager:
    """Manages multiple concurrent Claude SDK sessions.

    Usage::

        async with SessionManager() as manager:
            s1 = await manager.create_session("coding", options=opts)
            turn = await s1.send_and_collect("Explain this codebase")
            print(turn.text)

            s2 = await manager.create_session("review", options=opts, prompt="Review my PR")
            async for msg in s2.send("What issues did you find?"):
                ...
    """

    def __init__(self, *, max_concurrent_sessions: int | None = None) -> None:
        """Initialize the session manager.

        Args:
            max_concurrent_sessions: Optional cap on simultaneous connected
                sessions. ``create_session`` raises if exceeded.
        """
        self._sessions: dict[str, Session] = {}
        self._max_concurrent_sessions = max_concurrent_sessions

    # ── Session lifecycle ────────────────────────────────────────

    async def create_session(
        self,
        session_id: str | None = None,
        *,
        options: ClaudeAgentOptions | None = None,
        transport: Transport | None = None,
        prompt: str | None = None,
        connect: bool = True,
    ) -> Session:
        """Create and optionally connect a new session.

        Args:
            session_id: Explicit ID, or auto-generated UUID if None.
            options: Session-specific options.
            transport: Optional custom transport.
            prompt: If provided, sent as the initial prompt on connect.
            connect: If True (default), connect immediately.

        Raises:
            ValueError: If session_id already exists.
            RuntimeError: If max_concurrent_sessions would be exceeded.
        """
        sid = session_id or uuid.uuid4().hex
        if sid in self._sessions:
            msg = f"Session {sid!r} already exists"
            raise ValueError(msg)

        if self._max_concurrent_sessions is not None:
            active_count = sum(
                1
                for s in self._sessions.values()
                if s.state in ("idle", "responding", "connecting")
            )
            if active_count >= self._max_concurrent_sessions:
                msg = f"Maximum concurrent sessions ({self._max_concurrent_sessions}) reached"
                raise RuntimeError(msg)

        client = ClaudeSDKClient(options=options, transport=transport)
        session = Session(sid, client)
        self._sessions[sid] = session

        if connect:
            session._state = "connecting"
            try:
                await client.connect(prompt)
                session._state = "idle"
                session._last_activity = datetime.now(UTC)
            except Exception:
                session._state = "error"
                raise

        return session

    async def resume_session(
        self,
        session_id: str,
        *,
        options: ClaudeAgentOptions | None = None,
        transport: Transport | None = None,
    ) -> Session:
        """Resume a previously persisted session by ID.

        Sets ``continue_conversation=True`` and ``session_id`` on the options,
        then connects.

        Args:
            session_id: The session ID to resume.
            options: Session-specific options (``session_id`` and
                ``continue_conversation`` are set automatically).
            transport: Optional custom transport.

        Raises:
            ValueError: If session_id already exists in this manager.
        """
        base = options or Opts()
        merged = replace(base, session_id=session_id, continue_conversation=True)
        return await self.create_session(
            session_id=session_id,
            options=merged,
            transport=transport,
        )

    # ── Session access ───────────────────────────────────────────

    def get_session(self, session_id: str) -> Session:
        """Get a session by ID.

        Raises:
            KeyError: If session_id not found.
        """
        try:
            return self._sessions[session_id]
        except KeyError:
            msg = f"Session {session_id!r} not found"
            raise KeyError(msg) from None

    def __getitem__(self, session_id: str) -> Session:
        """Alias for ``get_session()``."""
        return self.get_session(session_id)

    def __contains__(self, session_id: str) -> bool:
        return session_id in self._sessions

    def __len__(self) -> int:
        return len(self._sessions)

    def __iter__(self) -> Iterator[str]:
        """Iterate over session IDs."""
        return iter(self._sessions)

    @property
    def sessions(self) -> dict[str, Session]:
        """All sessions (any state). Returns a copy."""
        return dict(self._sessions)

    @property
    def active_sessions(self) -> dict[str, Session]:
        """Sessions in IDLE or RESPONDING state."""
        return {sid: s for sid, s in self._sessions.items() if s.state in ("idle", "responding")}

    # ── Cleanup ──────────────────────────────────────────────────

    async def close_session(self, session_id: str) -> None:
        """Close and remove a specific session.

        Raises:
            KeyError: If session_id not found.
        """
        session = self.get_session(session_id)
        await session.close()
        del self._sessions[session_id]

    async def close_all(self) -> None:
        """Close all sessions. Errors during individual closes are suppressed."""
        for session in list(self._sessions.values()):
            with contextlib.suppress(Exception):
                await session.close()
        self._sessions.clear()

    # ── Aggregate stats ──────────────────────────────────────────

    @property
    def total_cost_usd(self) -> float:
        """Sum of costs across all sessions."""
        return sum(s.total_cost_usd for s in self._sessions.values())

    def snapshots(self) -> dict[str, SessionSnapshot]:
        """Snapshots of all sessions."""
        return {sid: s.snapshot for sid, s in self._sessions.items()}

    # ── Context manager ──────────────────────────────────────────

    async def __aenter__(self) -> SessionManager:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close_all()
