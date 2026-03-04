# Subagent Stream Behavior

How the Claude Code CLI emits messages when subagents are invoked via the `Agent` tool.

## Stream architecture

```
CLI subprocess  ──stdout──▶  _read_messages()  ──▶  MemoryObjectStream(∞)  ──▶  receive_messages()
```

All messages — main agent, foreground subagents, background tasks — go through
a single unbounded stream. `receive_response()` stops at the first `ResultMessage`.

## Foreground subagent (`background=False` or omitted)

The subagent runs synchronously within the main agent's turn. Its individual
tool calls and results are fully visible on the stream, tagged with
`parent_tool_use_id` linking them back to the `Agent` tool call.

```
AssistantMessage          tool_use: Agent {subagent_type, prompt}
TaskStartedSystemMessage  task_id, task_type: "local_agent"
UserMessage               subagent's prompt text (parent_tool_use_id set)
                          ┌─────────────────────────────────────────────┐
                          │  Subagent's inner loop (fully visible):     │
                          │                                             │
AssistantMessage          │  tool_use: Bash {command: "echo DONE"}      │
                          │  (parent_tool_use_id set)                   │
UserMessage               │  tool_result: "DONE"                        │
                          │  (parent_tool_use_id set)                   │
                          │  ... more tool calls if needed ...          │
                          └─────────────────────────────────────────────┘
UserMessage               Agent tool result:
                            tool_use_result.status: "completed"
                            tool_use_result.content: subagent's final output
                            tool_use_result.usage: full token breakdown
AssistantMessage          main agent's response incorporating the result
ResultSuccessMessage      single result for the whole turn
```

Key properties:
- Subagent messages carry `parent_tool_use_id` → can be correlated to the Agent call
- Every tool call and result from the subagent is streamed individually
- Full usage breakdown (per-token, per-tier) in the final `tool_use_result`

## Background subagent (`background=True`)

The subagent runs concurrently. The CLI holds the main turn open until the
background task completes — it does **not** send a `ResultMessage` for the main
agent independently. The subagent's inner workings are opaque.

```
AssistantMessage          tool_use: Agent {subagent_type, prompt, run_in_background: true}
TaskStartedSystemMessage  task_id, task_type: "local_agent"
UserMessage               tool_result:
                            tool_use_result.status: "async_launched"
                            tool_use_result.outputFile: /tmp/.../tasks/<id>.output
AssistantMessage          main agent's immediate response (e.g. "DISPATCHED")

                          ... subagent runs (no individual messages visible) ...

TaskProgressSystemMessage aggregate stats:
                            description, last_tool_name
                            usage: {total_tokens, tool_uses, duration_ms}
TaskNotificationSystemMessage
                          task_id, status: "completed"
                          summary: one-line text
                          usage: {total_tokens, tool_uses, duration_ms}
InitSystemMessage         new inner turn (main agent processes the completion)
AssistantMessage          main agent's response to the task result
ResultSuccessMessage      single result for the whole turn
```

Key properties:
- No `parent_tool_use_id` on messages after the initial launch
- No individual tool calls or results from the subagent
- Only aggregate usage stats (`total_tokens`, `tool_uses` count, `duration_ms`)
- `last_tool_name` in TaskProgress is the only hint at what the subagent did
- The `outputFile` path can be read for the subagent's detailed output

## ResultMessage count

In both modes, the CLI emits exactly **one** `ResultMessage` per prompt turn.
For background tasks, the CLI waits for the task to complete and the main agent
to process the notification before sending it.

This means `receive_response()` (which stops at the first `ResultMessage`) is
safe — there is no orphaned second `ResultMessage` that could desync the stream.

## Foreground vs background summary

| Aspect | Foreground | Background |
|---|---|---|
| Subagent tool calls visible | Yes (full AssistantMessage) | No |
| Subagent tool results visible | Yes (UserMessage) | No |
| `parent_tool_use_id` on messages | Yes | No (only on initial launch) |
| Progress/notification messages | No | Yes (TaskProgress, TaskNotification) |
| How result arrives | UserMessage with `tool_use_result` | TaskNotificationSystemMessage with summary |
| Usage detail | Full token breakdown | Aggregate totals only |
| ResultMessages per turn | 1 | 1 |
