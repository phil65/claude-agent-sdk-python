"""End-to-end tests for agents and setting sources with real Claude API calls."""

import asyncio
import json
from pathlib import Path
import sys
import tempfile

import pytest

from clawd_code_sdk import (
    AgentDefinition,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    SystemMessage,
)


def generate_large_agents(
    num_agents: int = 20, prompt_size_kb: int = 12
) -> dict[str, AgentDefinition]:
    """Generate multiple agents with large prompts for testing.

    Args:
        num_agents: Number of agents to generate
        prompt_size_kb: Size of each agent's prompt in KB

    Returns:
        Dictionary of agent name -> AgentDefinition
    """
    agents = {}
    for i in range(num_agents):
        # Generate a large prompt with some structure
        prompt_content = f"You are test agent #{i}. " + ("x" * (prompt_size_kb * 1024))
        agents[f"large-agent-{i}"] = AgentDefinition(
            description=f"Large test agent #{i} for stress testing",
            prompt=prompt_content,
        )
    return agents


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_agent_definition():
    """Test that custom agent definitions work in streaming mode."""
    options = ClaudeAgentOptions(
        agents={
            "test-agent": AgentDefinition(
                description="A test agent for verification",
                prompt="You are a test agent. Always respond with 'Test agent activated'",
                tools=["Read"],
                model="sonnet",
            )
        },
        max_turns=1,
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("What is 2 + 2?")

        # Check that agent is available in init message
        async for message in client.receive_response():
            if isinstance(message, SystemMessage):
                agents = message.agents
                assert isinstance(agents, list), (
                    f"agents should be a list of strings, got: {type(agents)}"
                )
                assert "test-agent" in agents, f"test-agent should be available, got: {agents}"
                break


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_agent_definition_with_query_function():
    """Test that custom agent definitions work with the query() function.

    Both ClaudeSDKClient and query() now use streaming mode internally,
    sending agents via the initialize request.
    """
    from clawd_code_sdk import query

    options = ClaudeAgentOptions(
        agents={
            "test-agent-query": AgentDefinition(
                description="A test agent for query function verification",
                prompt="You are a test agent.",
            )
        },
        max_turns=1,
    )

    # Use query() with string prompt
    found_agent = False
    async for message in query(prompt="What is 2 + 2?", options=options):
        if isinstance(message, SystemMessage):
            agents = message.agents
            assert "test-agent-query" in agents, (
                f"test-agent-query should be available, got: {agents}"
            )
            found_agent = True
            break

    assert found_agent, "Should have received init message with agents"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_large_agents_with_query_function():
    """Test large agent definitions (260KB+) work with query() function.

    Since we now always use streaming mode internally (matching TypeScript SDK),
    large agents are sent via the initialize request through stdin with no
    size limits.
    """
    from clawd_code_sdk import query

    # Generate 20 agents with 13KB prompts each = ~260KB total
    agents = generate_large_agents(num_agents=20, prompt_size_kb=13)
    options = ClaudeAgentOptions(agents=agents, max_turns=1)
    # Use query() with string prompt - agents still go via initialize
    found_agents = []
    async for message in query(prompt="What is 2 + 2?", options=options):
        if isinstance(message, SystemMessage):
            found_agents = message.agents
            break

    # Check all our agents are registered
    for agent_name in agents:
        assert agent_name in found_agents, (
            f"{agent_name} should be registered. "
            f"Found: {found_agents[:5]}... ({len(found_agents)} total)"
        )


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_filesystem_agent_loading():
    """Test that filesystem-based agents load via setting_sources and produce full response.

    This is the core test for issue #406. It verifies that when using
    setting_sources=["project"] with a .claude/agents/ directory containing
    agent definitions, the SDK:
    1. Loads the agents (they appear in init message)
    2. Produces a full response with AssistantMessage
    3. Completes with a ResultMessage

    The bug in #406 causes the iterator to complete after only the
    init SystemMessage, never yielding AssistantMessage or ResultMessage.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a temporary project with a filesystem agent
        project_dir = Path(tmpdir)
        agents_dir = project_dir / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        # Create a test agent file
        agent_file = agents_dir / "fs-test-agent.md"
        agent_file.write_text(
            """---
name: fs-test-agent
description: A filesystem test agent for SDK testing
tools: Read
---

# Filesystem Test Agent

You are a simple test agent. When asked a question, provide a brief, helpful answer.
"""
        )

        options = ClaudeAgentOptions(
            setting_sources=["project"],
            cwd=project_dir,
            max_turns=1,
        )

        messages = []
        async with ClaudeSDKClient(options=options) as client:
            await client.query("Say hello in exactly 3 words")
            async for msg in client.receive_response():
                messages.append(msg)

        # Must have at least init, assistant, result
        message_types = [type(m).__name__ for m in messages]

        assert "SystemMessage" in message_types, "Missing SystemMessage (init)"
        assert "AssistantMessage" in message_types, (
            f"Missing AssistantMessage - got only: {message_types}. "
            "This may indicate issue #406 (silent failure with filesystem agents)."
        )
        assert "ResultMessage" in message_types, "Missing ResultMessage"

        # Find the init message and check for the filesystem agent
        for msg in messages:
            if isinstance(msg, SystemMessage):
                agents = msg.agents
                # Agents are returned as strings (just names)
                assert "fs-test-agent" in agents, (
                    f"fs-test-agent not loaded from filesystem. Found: {agents}"
                )
                break

        # On Windows, wait for file handles to be released before cleanup
        if sys.platform == "win32":
            await asyncio.sleep(0.5)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_setting_sources_default():
    """Test that default (no setting_sources) loads no settings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a temporary project with local settings
        project_dir = Path(tmpdir)
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir(parents=True)

        # Create local settings with custom outputStyle
        settings_file = claude_dir / "settings.local.json"
        settings_file.write_text('{"outputStyle": "local-test-style"}')

        # Don't provide setting_sources - should default to no settings
        options = ClaudeAgentOptions(
            cwd=project_dir,
            max_turns=1,
        )

        async with ClaudeSDKClient(options=options) as client:
            await client.query("What is 2 + 2?")

            # Check that settings were NOT loaded
            async for message in client.receive_response():
                if isinstance(message, SystemMessage):
                    output_style = message.output_style
                    assert output_style != "local-test-style", (
                        f"outputStyle should NOT be from local settings (default is no settings), got: {output_style}"
                    )
                    assert output_style == "default", (
                        f"outputStyle should be 'default', got: {output_style}"
                    )
                    break

        # On Windows, wait for file handles to be released before cleanup
        if sys.platform == "win32":
            await asyncio.sleep(0.5)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_setting_sources_user_only():
    """Test that setting_sources=['user'] excludes project settings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a temporary project with a slash command
        project_dir = Path(tmpdir)
        commands_dir = project_dir / ".claude" / "commands"
        commands_dir.mkdir(parents=True)

        test_command = commands_dir / "testcmd.md"
        test_command.write_text(
            """---
description: Test command
---

This is a test command.
"""
        )

        # Use setting_sources=["user"] to exclude project settings
        options = ClaudeAgentOptions(
            setting_sources=["user"],
            cwd=project_dir,
            max_turns=1,
        )

        async with ClaudeSDKClient(options=options) as client:
            await client.query("What is 2 + 2?")

            # Check that project command is NOT available
            async for message in client.receive_response():
                if isinstance(message, SystemMessage):
                    commands = message.slash_commands
                    assert "testcmd" not in commands, (
                        f"testcmd should NOT be available with user-only sources, got: {commands}"
                    )
                    break

        # On Windows, wait for file handles to be released before cleanup
        if sys.platform == "win32":
            await asyncio.sleep(0.5)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_setting_sources_project_included():
    """Test that setting_sources=['user', 'project'] includes project settings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a temporary project with local settings
        project_dir = Path(tmpdir)
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir(parents=True)

        # Create local settings with custom outputStyle
        settings_file = claude_dir / "settings.local.json"
        settings_file.write_text('{"outputStyle": "local-test-style"}')

        # Use setting_sources=["user", "project", "local"] to include local settings
        options = ClaudeAgentOptions(
            setting_sources=["user", "project", "local"],
            cwd=project_dir,
            max_turns=1,
        )

        async with ClaudeSDKClient(options=options) as client:
            await client.query("What is 2 + 2?")

            # Check that settings WERE loaded
            async for message in client.receive_response():
                if isinstance(message, SystemMessage):
                    output_style = message.output_style
                    assert output_style == "local-test-style", (
                        f"outputStyle should be from local settings, got: {output_style}"
                    )
                    break

        # On Windows, wait for file handles to be released before cleanup
        if sys.platform == "win32":
            await asyncio.sleep(0.5)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_large_agent_definitions_via_initialize():
    """Test that large agent definitions (250KB+) are sent via initialize request.

    This test verifies the fix for the issue where large agent definitions
    would previously trigger a temp file workaround with @filepath. Now they
    are sent via the initialize control request through stdin, which has no
    size limit.

    The test:
    1. Generates 20 agents with ~13KB prompts each (~260KB total)
    2. Creates an SDK client with these agents
    3. Verifies all agents are registered and available
    """
    from dataclasses import asdict

    # Generate 20 agents with 13KB prompts each = ~260KB total
    agents = generate_large_agents(num_agents=20, prompt_size_kb=13)

    # Calculate total size to verify we're testing the right thing
    total_size = sum(
        len(json.dumps({k: v for k, v in asdict(agent).items() if v is not None}))
        for agent in agents.values()
    )
    assert total_size > 250_000, f"Test agents should be >250KB, got {total_size / 1024:.1f}KB"

    options = ClaudeAgentOptions(
        agents=agents,
        max_turns=1,
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("List available agents")

        # Check that all agents are available in init message
        async for message in client.receive_response():
            if isinstance(message, SystemMessage):
                registered_agents = message.agents
                assert isinstance(registered_agents, list), (
                    f"agents should be a list, got: {type(registered_agents)}"
                )

                # Verify all our agents are registered
                for agent_name in agents:
                    assert agent_name in registered_agents, (
                        f"{agent_name} should be registered. "
                        f"Found: {registered_agents[:5]}... ({len(registered_agents)} total)"
                    )

                # All agents should be there
                assert len(registered_agents) >= len(agents), (
                    f"Expected at least {len(agents)} agents, got {len(registered_agents)}"
                )
                break


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_agent_definition_with_memory_cross_session():
    """Test that a subagent with memory persists information across separate sessions.

    This test verifies that the memory field on AgentDefinition enables
    persistent cross-session learning:

    1. Session 1: Define a subagent with memory='local', tell it to remember a code word
    2. Session 2: New client with same subagent definition, ask it to recall the code word
    3. Verify the subagent remembered the code word across sessions
    """
    import uuid as uuid_mod

    from clawd_code_sdk import AssistantMessage, TextBlock

    # Use a unique code word so there's no way the model guesses it
    code_word = f"ZEPHYR{uuid_mod.uuid4().hex[:8].upper()}"

    agents = {
        "memory-agent": AgentDefinition(
            description="A note-taking agent that remembers things across sessions",
            prompt=(
                "You are a note-taking agent. When told to remember something, "
                "commit it to memory. When asked to recall, retrieve it from memory. "
                "Always include the exact text you were asked to remember in your response."
            ),
            memory="local",
        )
    }

    # Session 1: Store the code word via the memory-agent subagent
    options1 = ClaudeAgentOptions(
        agents=agents,
        max_turns=10,
        permission_mode="bypassPermissions",
    )

    async with ClaudeSDKClient(options=options1) as client:
        await client.query(
            f"Use the memory-agent subagent to remember this code word: {code_word}. "
            "Tell it to store this in its memory for later recall."
        )
        async for message in client.receive_response():
            pass  # Consume all messages

    # Session 2: New client, ask the memory-agent to recall the code word
    options2 = ClaudeAgentOptions(
        agents=agents,
        max_turns=10,
        permission_mode="bypassPermissions",
    )

    async with ClaudeSDKClient(options=options2) as client:
        await client.query(
            "Use the memory-agent subagent and ask it to recall the code word "
            "it was asked to remember in a previous session. "
            "Include the exact code word in your response."
        )

        response_text = ""
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response_text += block.text

        assert code_word in response_text, (
            f"Expected the code word '{code_word}' to appear in the response, "
            f"indicating the subagent remembered it across sessions. "
            f"Response was: {response_text[:500]}"
        )


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_agent_definition_without_memory_no_cross_session_recall():
    """Test that a subagent WITHOUT memory does NOT persist info across sessions.

    This is the negative control for test_agent_definition_with_memory_cross_session.
    Without the memory field, the subagent should have no way to recall a code word
    from a previous session.

    1. Session 1: Define a subagent WITHOUT memory, tell it to remember a code word
    2. Session 2: New client with same subagent definition, ask it to recall
    3. Verify the code word does NOT appear in the response
    """
    import uuid as uuid_mod

    from clawd_code_sdk import AssistantMessage, TextBlock

    # Use a unique code word so there's no way the model guesses it
    code_word = f"QUASAR{uuid_mod.uuid4().hex[:8].upper()}"

    agents = {
        "forgetful-agent": AgentDefinition(
            description="A note-taking agent (no persistent memory)",
            prompt=(
                "You are a note-taking agent. When told to remember something, "
                "acknowledge it. When asked to recall something from a previous session, "
                "be honest that you have no memory of previous sessions."
            ),
            # NOTE: no memory field set
        )
    }

    # Session 1: Tell the agent to remember the code word
    options1 = ClaudeAgentOptions(
        agents=agents,
        max_turns=10,
        permission_mode="bypassPermissions",
    )

    async with ClaudeSDKClient(options=options1) as client:
        await client.query(
            f"Use the forgetful-agent subagent to remember this code word: {code_word}. "
            "Tell it to store this for later recall."
        )
        async for message in client.receive_response():
            pass  # Consume all messages

    # Session 2: New client, ask the agent to recall the code word
    options2 = ClaudeAgentOptions(
        agents=agents,
        max_turns=10,
        permission_mode="bypassPermissions",
    )

    async with ClaudeSDKClient(options=options2) as client:
        await client.query(
            "Use the forgetful-agent subagent and ask it to recall the code word "
            "it was asked to remember in a previous session. "
            "Include the exact code word in your response if you remember it."
        )

        response_text = ""
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response_text += block.text

        assert code_word not in response_text, (
            f"The code word '{code_word}' should NOT appear in the response "
            f"because the subagent has no persistent memory. "
            f"Response was: {response_text[:500]}"
        )


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_agent_definition_with_mcp_servers():
    """Test that a subagent with mcpServers has access to the MCP server's tools.

    This test verifies that the mcp_servers field on AgentDefinition correctly
    provides MCP tools to the subagent:

    1. Define a subagent with mcp_servers pointing to mcp-server-git
    2. Ask the main agent to call the subagent and have it list or use git tools
    3. Verify the response mentions git-related tools/functionality
    """
    from clawd_code_sdk import AssistantMessage, TextBlock

    options = ClaudeAgentOptions(
        agents={
            "git-agent": AgentDefinition(
                description="An agent with git MCP tools",
                prompt=(
                    "You are a git helper agent with access to git MCP tools. "
                    "When asked about your tools, list the git-related tools you have available."
                ),
                mcp_servers=[
                    {"git": {"command": "uvx", "args": ["mcp-server-git"]}},
                ],
            )
        },
        max_turns=10,
        permission_mode="bypassPermissions",
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            "Use the git-agent subagent and ask it what git-related tools it has available. "
            "Include the tool names in your response."
        )

        response_text = ""
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response_text += block.text

        response_lower = response_text.lower()
        # mcp-server-git exposes tools like git_status, git_log, git_diff, etc.
        git_tool_names = [
            "git_status",
            "git_log",
            "git_diff",
            "git_commit",
            "git_add",
            "git_branch",
            "git_checkout",
            "git_show",
        ]
        found_tools = [name for name in git_tool_names if name in response_lower]
        assert found_tools, (
            f"Expected the response to mention at least one git MCP tool "
            f"({', '.join(git_tool_names)}), but got: {response_text[:500]}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
