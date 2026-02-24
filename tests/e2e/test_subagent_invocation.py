"""End-to-end test for subagent invocation via AgentDefinition.

Verifies that when the main agent dispatches work to a subagent defined
via AgentDefinition, the SDK emits the expected task lifecycle messages
(task_started, task_notification) and that the subagent actually runs.
"""

from __future__ import annotations

import pytest

from clawd_code_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    InitSystemMessage,
    Message,
    ResultMessage,
)
from clawd_code_sdk.models.messages import (
    TaskNotificationSystemMessage,
    TaskStartedSystemMessage,
)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_subagent_task_lifecycle():
    """Test that invoking a subagent produces task_started and task_notification messages.

    Defines a simple subagent, asks the main agent to call it, and verifies:
    1. The subagent appears in the init message
    2. A TaskStartedSystemMessage is emitted when the subagent begins
    3. A TaskNotificationSystemMessage is emitted when the subagent completes
    4. The task_id is consistent between started and notification
    5. The main agent's response includes output from the subagent
    """
    options = ClaudeAgentOptions(
        agents={
            "echo-agent": AgentDefinition(
                description="A simple echo agent that repeats what you say",
                prompt=(
                    "You are an echo agent. When given a message, respond with "
                    "exactly: 'ECHO: ' followed by the message. Nothing else."
                ),
            )
        },
        max_turns=10,
        permission_mode="bypassPermissions",
    )

    messages: list[Message] = []
    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            "Use the echo-agent subagent with the message 'pineapple'. "
            "Include the subagent's response in your reply."
        )
        async for msg in client.receive_response():
            messages.append(msg)

    # 1. Verify agent was registered
    init_msgs = [m for m in messages if isinstance(m, InitSystemMessage)]
    assert init_msgs, "Should have received an InitSystemMessage"
    assert "echo-agent" in init_msgs[0].agents

    # 2. Check for task lifecycle messages
    task_started = [m for m in messages if isinstance(m, TaskStartedSystemMessage)]
    task_notifications = [m for m in messages if isinstance(m, TaskNotificationSystemMessage)]

    assert task_started, (
        "Should have received at least one TaskStartedSystemMessage "
        f"(got message types: {[type(m).__name__ for m in messages]})"
    )
    assert task_notifications, (
        "Should have received at least one TaskNotificationSystemMessage "
        f"(got message types: {[type(m).__name__ for m in messages]})"
    )

    # 3. Verify task_id consistency
    started_task_ids = {m.task_id for m in task_started}
    notified_task_ids = {m.task_id for m in task_notifications}
    assert started_task_ids & notified_task_ids, (
        f"task_id should match between started ({started_task_ids}) "
        f"and notification ({notified_task_ids})"
    )

    # 4. Verify notification status
    completed = [m for m in task_notifications if m.status == "completed"]
    assert completed, (
        f"At least one task should have completed, got statuses: "
        f"{[m.status for m in task_notifications]}"
    )

    # 5. Verify the main agent's response includes subagent output
    response_text = ""
    for msg in messages:
        if isinstance(msg, AssistantMessage) and not hasattr(msg, "parent_tool_use_id"):
            for block in msg.content:
                if hasattr(block, "text"):
                    response_text += block.text

    response_lower = response_text.lower()
    assert "pineapple" in response_lower, (
        f"Response should include 'pineapple' from the echo agent, got: {response_text[:500]}"
    )

    # 6. Verify we got a final result
    result_msgs = [m for m in messages if isinstance(m, ResultMessage)]
    assert result_msgs, "Should have received a ResultMessage"
