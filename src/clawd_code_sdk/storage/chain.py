"""Reconstruct conversation threads from the ``parentUuid`` chain of a transcript.

Every entry that takes part in the chain derives from :class:`ClaudeEntryBase`
(user, assistant, attachment, system, progress, saved-hook-context). The chain
regularly runs through non-message entries, so walks index all of them.

A turn that runs tools in parallel forks the chain: Claude Code writes one
assistant entry per content block (all sharing the API ``message.id``), and each
tool-result entry's parent is the assistant entry holding its own ``tool_use``.
A plain walk from the leaf only follows the branch the next turn continued from
and loses the other calls and results; :func:`resolve_chain` puts them back
(as upstream's ``get_session_messages`` and Claude Code itself do).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from clawd_code_sdk.models import ToolResultBlock, ToolUseBlock
from clawd_code_sdk.storage.models import (
    ClaudeAssistantEntry,
    ClaudeChainEntry,
    ClaudeEntryBase,
    ClaudeUserEntry,
)


if TYPE_CHECKING:
    from collections.abc import Iterable

    from clawd_code_sdk.storage.models import ClaudeJSONLEntry


def index_chain_entries(entries: Iterable[ClaudeJSONLEntry]) -> dict[str, ClaudeChainEntry]:
    """Index all chain entries by ``uuid``, in file order."""
    return {entry.uuid: entry for entry in entries if isinstance(entry, ClaudeChainEntry)}


def find_leaf(entries: Iterable[ClaudeJSONLEntry]) -> ClaudeChainEntry | None:
    """The last main-thread user/assistant entry in file order.

    Sidechain, meta and team entries are skipped unless nothing else is there.
    """
    last: ClaudeChainEntry | None = None
    last_main: ClaudeChainEntry | None = None
    for entry in entries:
        if not isinstance(entry, ClaudeUserEntry | ClaudeAssistantEntry):
            continue
        last = entry
        if not entry.is_sidechain and not entry.is_meta and not entry.team_name:
            last_main = entry
    return last_main or last


def walk_ancestry(
    index: dict[str, ClaudeChainEntry], uuid: str, *, include_start: bool = True
) -> list[ClaudeChainEntry]:
    """Entries from ``uuid`` back to the root (leaf first), following ``parent_uuid``.

    Stops at a missing parent or a cycle. ``logical_parent_uuid`` (set across
    compaction boundaries) is not followed.
    """
    chain: list[ClaudeChainEntry] = []
    seen: set[str] = set()
    current = index.get(uuid)
    while current is not None and current.uuid not in seen:
        seen.add(current.uuid)
        chain.append(current)
        current = index.get(current.parent_uuid) if current.parent_uuid else None
    return chain if include_start else chain[1:]


def resolve_chain(
    entries: Iterable[ClaudeJSONLEntry],
    leaf_uuid: str | None = None,
    *,
    recover_parallel_tool_calls: bool = True,
) -> list[ClaudeChainEntry]:
    """The thread ending at ``leaf_uuid`` (default: :func:`find_leaf`), root first.

    The result contains every chain entry on the thread, including attachments
    and system entries; filter by type for messages only.

    Args:
        entries: Entries of one transcript, in file order.
        leaf_uuid: Entry to end the thread at.
        recover_parallel_tool_calls: Put back the tool calls and results of
            parallel tool turns that the ``parentUuid`` walk skips.
    """
    entry_list = list(entries)
    index = index_chain_entries(entry_list)
    if leaf_uuid is None:
        leaf = find_leaf(entry_list)
        if leaf is None:
            return []
        leaf_uuid = leaf.uuid
    chain = walk_ancestry(index, leaf_uuid)
    chain.reverse()
    if recover_parallel_tool_calls:
        chain = _recover_parallel_tool_calls(index, chain)
    return chain


def _tool_use_ids(entry: ClaudeAssistantEntry) -> list[str]:
    content = entry.message.content
    if isinstance(content, str):
        return []
    return [block.id for block in content if isinstance(block, ToolUseBlock)]


def _answered_ids(entry: ClaudeUserEntry) -> list[str]:
    content = entry.message.content
    if isinstance(content, str):
        return []
    return [block.tool_use_id for block in content if isinstance(block, ToolResultBlock)]


def _same_writer(a: ClaudeEntryBase, b: ClaudeEntryBase) -> bool:
    return a.is_sidechain == b.is_sidechain and a.agent_id == b.agent_id


def _recover_parallel_tool_calls(
    index: dict[str, ClaudeChainEntry], chain: list[ClaudeChainEntry]
) -> list[ClaudeChainEntry]:
    """Insert off-chain siblings and tool results of each on-chain API response.

    Recovered entries go right after the response's last on-chain entry: first
    the missing assistant entries, then the tool results, each in timestamp
    order. A result is only recovered if it answers a call that is not answered
    yet, so duplicates and results of abandoned branches stay out.
    """
    on_chain = {entry.uuid for entry in chain}
    anchors: dict[str, str] = {}  # message id -> uuid of last on-chain entry
    for entry in chain:
        if isinstance(entry, ClaudeAssistantEntry):
            anchors[entry.message.id] = entry.uuid
    if not anchors:
        return chain

    siblings: dict[str, list[ClaudeAssistantEntry]] = {}
    results_by_parent: dict[str, list[ClaudeUserEntry]] = {}
    for entry in index.values():
        match entry:
            case ClaudeAssistantEntry() if entry.message.id in anchors:
                siblings.setdefault(entry.message.id, []).append(entry)
            case ClaudeUserEntry() if entry.is_tool_result and entry.uuid not in on_chain:
                parents = {entry.parent_uuid, entry.source_tool_assistant_uuid}
                for parent in filter(None, parents):
                    results_by_parent.setdefault(parent, []).append(entry)

    answered = {
        call_id
        for entry in chain
        if isinstance(entry, ClaudeUserEntry)
        for call_id in _answered_ids(entry)
    }
    inserts: dict[str, list[ClaudeChainEntry]] = {}
    for message_id, anchor in anchors.items():
        group = siblings.get(message_id, [])
        calls = {call_id for member in group for call_id in _tool_use_ids(member)}
        missing_siblings = [m for m in group if m.uuid not in on_chain]
        results: list[ClaudeUserEntry] = []
        for member in group:
            for result in results_by_parent.get(member.uuid, []):
                call_ids = set(_answered_ids(result))
                if not _same_writer(result, member) or not call_ids & calls:
                    continue
                if call_ids <= answered:
                    continue
                answered |= call_ids
                results.append(result)
        if not missing_siblings and not results:
            continue
        missing_siblings.sort(key=lambda e: e.timestamp)
        results.sort(key=lambda e: e.timestamp)
        inserts[anchor] = [*missing_siblings, *results]

    if not inserts:
        return chain
    result_chain: list[ClaudeChainEntry] = []
    for entry in chain:
        result_chain.append(entry)
        result_chain.extend(inserts.get(entry.uuid, ()))
    return result_chain
