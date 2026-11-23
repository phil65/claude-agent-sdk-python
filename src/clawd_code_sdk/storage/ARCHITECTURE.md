# Claude Code Storage Architecture

How Claude Code persists sessions on disk, and how this package models it.
Verified against transcripts written by Claude Code 2.x/3.x (late 2026). Claude Code
changes the format often: new entry types, new fields, sometimes renamed keys. The models
are lenient (unknown fields are ignored, unknown entry types load as
`ClaudeUnknownEntry`), so new versions keep loading.

## Directory Structure

```
~/.claude/                                 # $CLAUDE_CONFIG_DIR if set
├── projects/
│   └── {sanitized-cwd}/                   # one directory per working directory
│       ├── {sessionId}.jsonl              # main session transcript
│       ├── {sessionId}/
│       │   ├── subagents/
│       │   │   ├── agent-{agentId}.jsonl      # subagent transcript (may be nested,
│       │   │   └── agent-{agentId}.meta.json  #   e.g. subagents/workflows/{runId}/)
│       │   └── tool-results/              # large tool outputs moved out of the transcript
│       ├── sessions-index.json            # cached listing (firstPrompt, messageCount, ...)
│       └── memory/                        # auto-memory files (MEMORY.md, ...)
├── file-history/{sessionId}/{hash}@v{n}   # file backups for rewind (see file-history entries)
├── sessions/{pid}.json                    # registry of running Claude Code processes
├── session-env/{sessionId}/               # per-session environment state (usually empty)
├── todos/{sessionId}-agent-{agentId}.json # legacy TodoWrite state (newer versions rarely write it)
├── history.jsonl                          # prompt history: display, pastedContents, project,
│                                          #   sessionId, timestamp
└── settings.json
```

### Project directory names

The working directory is sanitized: every non-alphanumeric character becomes `-`
(`/home/user/.config/app` → `-home-user--config-app`). Names longer than 200 characters are
truncated and get a hash suffix. The mapping is lossy; `decode_project_path` only guesses.
The real `cwd` is recorded on most entries. Sessions can also live under the directory of
another git worktree of the same repository. `list_sessions` and friends search those too.

### Subagents

Each subagent (Agent/Task tool) writes its own transcript under
`{sessionId}/subagents/agent-{agentId}.jsonl`. Its entries carry the parent `sessionId`, an
`agentId` and `isSidechain: true`. The `.meta.json` sidecar records `agentType`,
`description`, `model`, `spawnDepth` and `toolUseId`, which is the id of the Agent
`tool_use` in the parent session that spawned it. `get_subagent_messages` exposes it as
`SessionMessage.parent_tool_use_id`.

## Transcript format

One JSON object per line, appended in write order. Keys are camelCase (a few are
snake_case or uppercase-suffixed, e.g. `toolUseID`, `sourceToolAssistantUUID`).

### Chain entries

These entries have `uuid`, `parentUuid`, `sessionId`, `timestamp`, `cwd`, `version`,
`gitBranch`, `userType`, `entrypoint`, `isSidechain` and optional `agentId`, `slug`,
`isMeta`, `teamName`. They derive from `ClaudeEntryBase`. `ClaudeChainEntry` is the union
of all of them.

| `type` | Model | Notes |
|---|---|---|
| `user` | `ClaudeUserEntry` | prompts *and* tool results (`message.content` holds `tool_result` blocks; `toolUseResult` has the structured result; `sourceToolAssistantUUID` points at the assistant entry with the call) |
| `assistant` | `ClaudeAssistantEntry` | **one entry per content block**; all blocks of one API response share `message.id` and `requestId`, and each repeats the response's `usage` |
| `attachment` | `ClaudeAttachmentEntry` | context added to the prompt: hook output (`hook_success`, ...), files, edited files, reminders, date, deferred tool lists, task status, ... (`attachment.type`). Most common entry type |
| `system` | `ClaudeSystemEntry` (by `subtype`) | `turn_duration`, `stop_hook_summary`, `compact_boundary`, `away_summary`, `local_command`, `api_error`, `informational`, `model_refusal_fallback`, else `ClaudeGenericSystemEntry` |
| `progress` | `ClaudeProgressEntry` | older versions only: tool/hook/agent progress |
| `saved_hook_context` | `ClaudeSavedHookContextEntry` | |

### Metadata entries

These entries have no `uuid` and are not part of the chain. Most are "last one wins".

| `type` | Model | Content |
|---|---|---|
| `custom-title` / `ai-title` | `ClaudeCustomTitleEntry` / `ClaudeAiTitleEntry` | session title (user rename wins over AI title) |
| `last-prompt` | `ClaudeLastPromptEntry` | latest prompt, or just `leafUuid` |
| `tag` | `ClaudeTagEntry` | session tag (`""` clears it) |
| `mode`, `permission-mode` | `ClaudeModeEntry`, `ClaudePermissionModeEntry` | coordinator/normal, permission mode |
| `cost-state` | `ClaudeCostStateEntry` | session totals: cost, API/tool durations, lines changed, per-model usage |
| `tools-used` | `ClaudeToolsUsedEntry` | tool names used |
| `pr-link` | `ClaudePrLinkEntry` | PR created in the session |
| `worktree-state` | `ClaudeWorktreeStateEntry` | entered/exited worktree |
| `relocated` | `ClaudeRelocatedEntry` | session continued in another cwd |
| `derived-from` | `ClaudeDerivedFromEntry` | sessions this one continues (`via`: `clear`, `compact`, `resume`, ...) |
| `fork-context-ref` | `ClaudeForkContextRefEntry` | forked subagent's reference to the parent conversation |
| `queue-operation` | `ClaudeQueueOperationEntry` (by `operation`) | prompts queued while a turn runs: `enqueue`, `dequeue`, `remove`, `popAll` |
| `file-history-snapshot` / `file-history-delta` | `ClaudeFileHistoryEntry` / `ClaudeFileHistoryDeltaEntry` | backups in `~/.claude/file-history/` per user message, for rewind |
| `content-replacement` | `ClaudeContentReplacementEntry` | tool results replaced by stubs |
| `attribution-snapshot`, `task-summary`, `agent-name`, `agent-color`, `agent-setting`, `speculation-accept`, `marble-origami-commit`, `marble-origami-snapshot` | see `models.py` | |

Loaded as `ClaudeUnknownEntry` on purpose because they are internal or bulky:
`api-request`, `api-request-blob`, `api-request-shape` (request recording),
`atis-latch`, `session-owner` (account/org ids), `data-flow-records`,
`data-flow-incomplete`.

## The parentUuid chain

Every chain entry points at its predecessor through `parentUuid`. The conversation is the
path from a leaf back to the root, **not** the file order:

- The chain runs through non-message entries. An assistant entry's parent is often an
  attachment or a system entry. Walks must index every `ClaudeChainEntry`, not only
  user/assistant entries, or they stop after one step.
- Branches: rewinding, editing a prompt, or retrying leaves abandoned branches in the
  file. The current thread ends at the last main-thread user/assistant entry.
- Parallel tool calls fork the chain. N parallel `tool_use` blocks are N chained
  assistant entries. Each `tool_result` entry's parent is its own call's entry, and the
  next turn continues from only one of them. A plain walk loses the other calls and
  results. `storage.chain.resolve_chain` (and `get_session_messages`) put them back after
  the response.
- Compaction: a `compact_boundary` system entry starts a new root (`parentUuid: null`,
  `logicalParentUuid` points at the pre-compaction leaf) and is followed by a user entry
  with `isCompactSummary: true`. Walks do not follow `logicalParentUuid`, so the thread
  starts at the compaction.
- Sidechains: `isSidechain: true` entries belong to subagents (in older versions they
  were in the main file; now they live in `subagents/`).

Helpers in `clawd_code_sdk.storage.chain`: `index_chain_entries`, `find_leaf`,
`walk_ancestry` and `resolve_chain`. `replay_entries(..., leaf_uuid=...)` uses them.

## Reading and writing

- `storage.helpers.read_session(path)` loads a transcript into typed entries. Lines that
  fail validation are logged and skipped.
- `storage.helpers.write_entry(path, entry)` appends one entry (by alias).
- `storage.helpers.extract_title(path)` gets a display title from the file's head and tail
  (custom title, then AI title, then the first prompt).
- `storage.replay.replay_session(path)` turns a transcript back into SDK messages.
- `list_sessions`, `get_session_info`, `get_session_messages`, `list_subagents`,
  `get_subagent_messages`, `rename_session`, `tag_session`, `delete_session` and
  `fork_session` (in `clawd_code_sdk._internal`) work on raw dicts and read only what they
  need (head/tail for listings).
