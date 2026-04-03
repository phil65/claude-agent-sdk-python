# Claude Agent SDK for Python

An improved fork of the official [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/python) with stronger type safety and additional features.
(API still quite similar to the official one)

## Installation

```bash
uv add clawd-code-sdk
```

**Prerequisites:**

- Python 3.13+

## Quick Start

```python
import anyio
from clawd_code_sdk import ClaudeSDKClient

async def main():
    async for message in ClaudeSDKClient.one_shot("What is 2 + 2?"):
        print(message)

anyio.run(main)
```

## Basic Usage

### One-shot queries

`ClaudeSDKClient.one_shot()` is the simplest way to query Claude Code.
It handles connection lifecycle automatically and yields response messages:

```python
from clawd_code_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock

# Simple query
async for message in ClaudeSDKClient.one_shot("Hello Claude"):
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                print(block.text)

# With options
options = ClaudeAgentOptions(
    system_prompt="You are a helpful assistant",
    max_turns=1,
)

async for message in ClaudeSDKClient.one_shot("Tell me a joke", options=options):
    print(message)
```

### Interactive sessions

`ClaudeSDKClient` supports bidirectional, interactive conversations with Claude
Code. Unlike `one_shot()`, it additionally enables **custom tools**, **hooks**,
and multi-turn conversations within the same session.

```python
from clawd_code_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock

options = ClaudeAgentOptions(max_turns=3)

async with ClaudeSDKClient(options=options) as client:
    # First turn
    await client.query("What is 2 + 2?")
    async for message in client.receive_response():
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text)

    # Follow-up in the same session
    await client.query("Now multiply that by 3")
    async for message in client.receive_response():
        print(message)
```

## Message Sequence

When you call `client.query()` and iterate `client.receive_response()`,
messages arrive in this order:

```
SessionStateChangedMessage  state=running     # session starts processing
InitSystemMessage           subtype=init      # session metadata (tools, model, cwd)
StreamEvent                                   # raw Anthropic SSE events (deltas)
StreamEvent                                   # ...
AssistantMessage                              # complete assistant turn (text, thinking, tool use)
StreamEvent                                   # more streaming if multi-turn
AssistantMessage                              # another complete turn
ResultSuccessMessage        subtype=success   # final result with usage/cost
SessionStateChangedMessage  state=idle        # session fully done — iterator stops here
```

Key points:

- **`receive_response()`** automatically terminates when the session
  transitions to `idle` — the authoritative signal that the CLI has fully
  finished (held-back results flushed, background agents exited).
- **`StreamEvent`** wraps raw Anthropic streaming events (`message_start`,
  `content_block_delta`, etc.). Useful for real-time UI updates.
- **`AssistantMessage`** contains complete content blocks (`TextBlock`,
  `ThinkingBlock`, `ToolUseBlock`) — no need to reassemble from deltas.
- **Hook messages** (`HookStartedSystemMessage`, `HookResponseSystemMessage`)
  may appear at any point if hooks are configured.
- **`ResultSuccessMessage`** / **`ResultErrorMessage`** carry token usage
  and cost information.

## Configuration

### Tools

```python
options = ClaudeAgentOptions(
    tools=["Read", "Write", "Bash"],           # tools available to the agent
    allowed_tools=["Read", "Write", "Bash"],   # auto-approved (no permission prompt)
    disallowed_tools=["WebFetch"],             # completely removed from context
    permission_mode="acceptEdits",             # auto-accept file edits
)
```

### Working Directory

```python
from pathlib import Path

options = ClaudeAgentOptions(
    cwd="/path/to/project",        # or Path("/path/to/project")
    add_dirs=["/other/project"],   # additional working directories
)
```

### Model and Thinking

```python
from clawd_code_sdk import ClaudeAgentOptions, ThinkingConfigEnabled

options = ClaudeAgentOptions(
    model="sonnet",
    fallback_model="haiku",
    thinking=ThinkingConfigEnabled(budget_tokens=10_000),
    effort="high",
)
```

### Session Management

```python
from clawd_code_sdk import ClaudeAgentOptions, NewSession, ResumeSession, ContinueLatest

# Fresh session (default)
options = ClaudeAgentOptions(session=NewSession())

# Resume by ID
options = ClaudeAgentOptions(session=ResumeSession(session_id="abc-123"))

# Or shorthand
options = ClaudeAgentOptions(session="abc-123")

# Continue most recent
options = ClaudeAgentOptions(session=ContinueLatest())
```

### Structured Output

```python
from pydantic import BaseModel

class Joke(BaseModel):
    setup: str
    punchline: str

options = ClaudeAgentOptions(
    output_schema=Joke,  # accepts Pydantic models, dataclasses, TypedDicts, or raw dicts
)
```

## MCP Servers

### In-Process SDK Servers

Define tools as Python functions that run in-process — no subprocess management
or IPC overhead:

```python
from clawd_code_sdk import tool, create_sdk_mcp_server, ClaudeAgentOptions, ClaudeSDKClient

@tool("greet", "Greet a user", {"name": str})
async def greet_user(args):
    return {"content": [{"type": "text", "text": f"Hello, {args['name']}!"}]}

server = create_sdk_mcp_server(
    name="my-tools",
    version="1.0.0",
    tools=[greet_user],
)

options = ClaudeAgentOptions(
    mcp_servers={"tools": server},
    allowed_tools=["mcp__tools__greet"],
)

async with ClaudeSDKClient(options=options) as client:
    await client.query("Greet Alice")
    async for msg in client.receive_response():
        print(msg)
```

### External Servers

```python
from clawd_code_sdk import McpStdioServerConfig, McpHttpServerConfig

options = ClaudeAgentOptions(
    mcp_servers={
        # Subprocess (stdio)
        "git": McpStdioServerConfig(command="uvx", args=["mcp-server-git"]),
        # HTTP
        "remote": McpHttpServerConfig(url="https://mcp.example.com/sse"),
    }
)
```

### Mixed Servers

SDK and external servers can be used together:

```python
options = ClaudeAgentOptions(
    mcp_servers={
        "internal": sdk_server,                                              # in-process
        "git": McpStdioServerConfig(command="uvx", args=["mcp-server-git"]), # subprocess
    }
)
```

## Hooks

Hooks are Python callbacks that the Claude Code CLI invokes at specific points
of the agent loop. They enable deterministic processing and automated feedback.

Each hook event has strongly-typed input/output types:

```python
from clawd_code_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    HookMatcher,
    PreToolUseHookInput,
    HookContext,
)

async def check_bash_command(
    input_data: PreToolUseHookInput,
    tool_use_id: str | None,
    context: HookContext,
):
    tool_input = input_data["tool_input"]
    command = tool_input.get("command", "")
    if "rm -rf" in command:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Dangerous command blocked",
            }
        }
    return {}

options = ClaudeAgentOptions(
    allowed_tools=["Bash"],
    hooks={
        "PreToolUse": [
            HookMatcher(matcher="Bash", hooks=[check_bash_command]),
        ],
    },
)

async with ClaudeSDKClient(options=options) as client:
    await client.query("Run echo hello")
    async for msg in client.receive_response():
        print(msg)
```

### Available Hook Events

| Event | When it fires |
|-------|---------------|
| `PreToolUse` | Before a tool executes (can deny/modify) |
| `PostToolUse` | After a tool succeeds |
| `PostToolUseFailure` | After a tool fails |
| `UserPromptSubmit` | When a user prompt is submitted |
| `Stop` / `StopFailure` | When the agent stops or fails to stop |
| `SubagentStart` / `SubagentStop` | Subagent lifecycle |
| `SessionStart` / `SessionEnd` | Session lifecycle |
| `Notification` | Agent notifications |
| `PermissionRequest` / `PermissionDenied` | Permission events |
| `PreCompact` / `PostCompact` | Context compaction |
| `Elicitation` / `ElicitationResult` | MCP elicitation |
| `TaskCreated` / `TaskCompleted` | Task lifecycle |
| `FileChanged` / `CwdChanged` | Filesystem events |

See the [Claude Code Hooks Reference](https://docs.anthropic.com/en/docs/claude-code/hooks)
for full documentation.

## Multimodal Prompts

Send images, PDFs, and text together using typed prompt classes:

```python
from clawd_code_sdk import (
    ClaudeSDKClient,
    UserImageURLPrompt,
    UserDocumentPrompt,
    UserPlainTextDocumentPrompt,
)

async with ClaudeSDKClient() as client:
    await client.query(
        UserImageURLPrompt(url="https://example.com/chart.png"),
        "What does this chart show?",
    )
    async for msg in client.receive_response():
        print(msg)
```

## Subagents

Define subagents with their own prompts, tools, and MCP servers:

```python
from clawd_code_sdk import ClaudeAgentOptions, ClaudeSDKClient, AgentDefinition, McpStdioServerConfig

options = ClaudeAgentOptions(
    agents={
        "researcher": AgentDefinition(
            description="A research agent with web access",
            prompt="You are a research assistant.",
            tools=["WebFetch", "Read"],
        ),
        "git-agent": AgentDefinition(
            description="An agent with git tools",
            prompt="You are a git helper.",
            mcp_servers={"git": McpStdioServerConfig(command="uvx", args=["mcp-server-git"])},
        ),
    },
    max_turns=10,
)
```

## Types

### Message Types

| Type | Description |
|------|-------------|
| `AssistantMessage` | Claude's response (text, thinking, tool use) |
| `UserMessage` | Echoed user messages |
| `StreamEvent` | Raw Anthropic SSE streaming events |
| `InitSystemMessage` | Session metadata (tools, model, cwd) |
| `ResultSuccessMessage` | Successful completion with usage |
| `ResultErrorMessage` | Error completion |
| `SessionStateChangedMessage` | Session state transitions |
| `HookStartedSystemMessage` | Hook execution started |
| `HookResponseSystemMessage` | Hook execution completed |

### Content Block Types

| Type | Appears in |
|------|------------|
| `TextBlock` | Assistant and user messages |
| `ThinkingBlock` | Assistant messages (when thinking enabled) |
| `ToolUseBlock` | Assistant messages |
| `ToolResultBlock` | User messages |
| `ImageBlock` | User messages |

The SDK provides role-specific narrowed types:

- `AssistantContentBlock` = `TextBlock | ThinkingBlock | ToolUseBlock`
- `UserContentBlock` = `TextBlock | ToolResultBlock | ImageBlock`
- `ContentBlock` = full 5-type union (for storage/serialization)

See [src/clawd_code_sdk/models/content_blocks.py](src/clawd_code_sdk/models/content_blocks.py)
for complete type definitions.

## Error Handling

```python
from clawd_code_sdk import (
    ClaudeSDKError,      # Base error
    CLINotFoundError,    # Claude Code not installed
    CLIConnectionError,  # Connection issues
    ProcessError,        # Process failed
    CLIJSONDecodeError,  # JSON parsing issues
    BillingError,        # Insufficient credits
    RateLimitError,      # Rate limited
    AuthenticationError, # Invalid API key
)

try:
    async for message in ClaudeSDKClient.one_shot("Hello"):
        pass
except CLINotFoundError:
    print("Please install Claude Code")
except ProcessError as e:
    print(f"Process failed with exit code: {e.exit_code}")
```

See [src/clawd_code_sdk/\_errors.py](src/clawd_code_sdk/_errors.py) for all error types.

## Available Tools

See the [Claude Code documentation](https://docs.anthropic.com/en/docs/claude-code/settings#tools-available-to-claude) for a complete list of available tools.

## Migrating from Claude Code SDK

If you're upgrading from the Claude Code SDK (versions < 0.1.0), please see the [CHANGELOG.md](CHANGELOG.md#010) for details on breaking changes and new features, including:

- `ClaudeCodeOptions` → `ClaudeAgentOptions` rename
- Merged system prompt configuration
- Settings isolation and explicit control
- New programmatic subagents and session forking features

## Development

If you're contributing to this project, run the initial setup script to install git hooks:

```bash
./scripts/initial-setup.sh
```

This installs a pre-push hook that runs lint checks before pushing, matching the CI workflow. To skip the hook temporarily, use `git push --no-verify`.

### Building Wheels Locally

To build wheels with the bundled Claude Code CLI:

```bash
# Install build dependencies
pip install build twine

# Build wheel with bundled CLI
python scripts/build_wheel.py

# Build with specific version
python scripts/build_wheel.py --version 0.1.4

# Build with specific CLI version
python scripts/build_wheel.py --cli-version 2.0.0

# Clean bundled CLI after building
python scripts/build_wheel.py --clean

# Skip CLI download (use existing)
python scripts/build_wheel.py --skip-download
```

The build script:

1. Downloads Claude Code CLI for your platform
2. Bundles it in the wheel
3. Builds both wheel and source distribution
4. Checks the package with twine

See `python scripts/build_wheel.py --help` for all options.

### Release Workflow

The package is published to PyPI via the GitHub Actions workflow in `.github/workflows/publish.yml`. To create a new release:

1. **Trigger the workflow** manually from the Actions tab with two inputs:
   - `version`: The package version to publish (e.g., `0.1.5`)
   - `claude_code_version`: The Claude Code CLI version to bundle (e.g., `2.0.0` or `latest`)

2. **The workflow will**:
   - Build platform-specific wheels for macOS, Linux, and Windows
   - Bundle the specified Claude Code CLI version in each wheel
   - Build a source distribution
   - Publish all artifacts to PyPI
   - Create a release branch with version updates
   - Open a PR to main with:
     - Updated `pyproject.toml` version
     - Updated `src/clawd_code_sdk/_version.py`
     - Updated `src/clawd_code_sdk/_cli_version.py` with bundled CLI version
     - Auto-generated `CHANGELOG.md` entry

3. **Review and merge** the release PR to update main with the new version information

The workflow tracks both the package version and the bundled CLI version separately, allowing you to release a new package version with an updated CLI without code changes.

## License and terms

Use of this SDK is governed by Anthropic's [Commercial Terms of Service](https://www.anthropic.com/legal/commercial-terms), including when you use it to power products and services that you make available to your own customers and end users, except to the extent a specific component or dependency is covered by a different license as indicated in that component's LICENSE file.
