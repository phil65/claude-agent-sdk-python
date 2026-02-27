"""End-to-end tests for subagent invocation via AgentDefinition.

Verifies that when the main agent dispatches work to a subagent defined
via AgentDefinition, the SDK emits the expected task lifecycle messages
and that the subagent actually runs.

Foreground subagents emit task_started and fold output back into AssistantMessage.
Background subagents emit task_started, launch asynchronously, and the main agent
uses TaskOutput to retrieve results.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from clawd_code_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    InitSystemMessage,
    ResultMessage,
)
from clawd_code_sdk.models import TextBlock
from clawd_code_sdk.models.messages import TaskStartedSystemMessage, UserMessage


if TYPE_CHECKING:
    from clawd_code_sdk import Message


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_subagent_task_lifecycle():
    """Test that invoking a foreground subagent produces the expected messages.

    Defines a simple subagent, asks the main agent to call it, and verifies:
    1. The subagent appears in the init message
    2. A TaskStartedSystemMessage is emitted when the subagent begins
    3. The main agent's response includes output from the subagent
    4. A ResultMessage is received at the end
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

    # 2. Verify the subagent was started
    task_started = [m for m in messages if isinstance(m, TaskStartedSystemMessage)]
    assert task_started, (
        "Should have received at least one TaskStartedSystemMessage "
        f"(got message types: {[type(m).__name__ for m in messages]})"
    )

    # 3. Verify task metadata
    started = task_started[0]
    assert started.task_id, "task_id should be non-empty"
    assert started.description, "description should be non-empty"

    # 4. Verify the main agent's response includes subagent output
    response_text = ""
    for msg in messages:
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    response_text += block.text

    response_lower = response_text.lower()
    assert "pineapple" in response_lower, (
        f"Response should include 'pineapple' from the echo agent, got: {response_text[:500]}"
    )

    # 5. Verify we got a final result
    result_msgs = [m for m in messages if isinstance(m, ResultMessage)]
    assert result_msgs, "Should have received a ResultMessage"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_background_subagent_lifecycle():
    """Test that a background subagent launches asynchronously.

    Defines a subagent with background=True, asks the main agent to call it,
    and verifies:
    1. The subagent appears in the init message
    2. A TaskStartedSystemMessage is emitted
    3. The Task tool result indicates async launch (isAsync=True)
    4. The main agent uses TaskOutput to retrieve the result
    5. The final response includes the subagent's output
    """
    options = ClaudeAgentOptions(
        agents={
            "echo-agent": AgentDefinition(
                description="A simple echo agent that repeats what you say",
                prompt=(
                    "You are an echo agent. When given a message, respond with "
                    "exactly: 'ECHO: ' followed by the message. Nothing else."
                ),
                background=True,
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

    # 2. Verify the subagent was started
    task_started = [m for m in messages if isinstance(m, TaskStartedSystemMessage)]
    assert task_started, (
        "Should have received at least one TaskStartedSystemMessage "
        f"(got message types: {[type(m).__name__ for m in messages]})"
    )
    started = task_started[0]
    assert started.task_id, "task_id should be non-empty"

    # 3. Verify async launch via tool result
    user_msgs = [m for m in messages if isinstance(m, UserMessage)]
    async_results = [
        m
        for m in user_msgs
        if isinstance(m.tool_use_result, dict) and m.tool_use_result.get("isAsync") is True
    ]
    assert async_results, (
        "Should have a tool_use_result with isAsync=True indicating background launch"
    )

    # 4. Verify TaskOutput was used to retrieve the result
    response_text = ""
    for msg in messages:
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    response_text += block.text

    response_lower = response_text.lower()
    assert "pineapple" in response_lower, (
        f"Response should include 'pineapple' from the echo agent, got: {response_text[:500]}"
    )

    # 5. Verify we got a final result
    result_msgs = [m for m in messages if isinstance(m, ResultMessage)]
    assert result_msgs, "Should have received a ResultMessage"


if __name__ == "__main__":
    pytest.main([__file__, "-vv", "-m", "e2e"])
