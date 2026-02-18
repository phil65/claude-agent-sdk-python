"""ClaudeAgentOptions - main options dataclass."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from .agents import AgentDefinition, SystemPromptPreset, ToolsPreset
    from .base import PermissionMode, ReasoningEffort, SdkBeta, SettingSource, ThinkingConfig
    from .hooks import HookEvent, HookMatcher
    from .mcp import McpServerConfig, SdkPluginConfig
    from .permissions import CanUseTool
    from .sandbox import SandboxSettings


@dataclass
class ClaudeAgentOptions:
    """Query options for Claude SDK."""

    tools: list[str] | ToolsPreset | None = None
    allowed_tools: list[str] = field(default_factory=list)
    system_prompt: str | SystemPromptPreset | None = None
    mcp_servers: dict[str, McpServerConfig] | str | Path = field(default_factory=dict)
    permission_mode: PermissionMode | None = None
    session_id: str | None = None
    continue_conversation: bool = False
    resume: str | None = None
    max_turns: int | None = None
    max_budget_usd: float | None = None
    disallowed_tools: list[str] = field(default_factory=list)
    model: str | None = None
    fallback_model: str | None = None
    # Beta features - see https://docs.anthropic.com/en/api/beta-headers
    betas: list[SdkBeta] = field(default_factory=list)
    permission_prompt_tool_name: str | None = None
    cwd: str | Path | None = None
    cli_path: str | Path | None = None
    settings: str | None = None
    add_dirs: list[str | Path] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    extra_args: dict[str, str | None] = field(default_factory=dict)  # Pass arbitrary CLI flags
    max_buffer_size: int | None = None  # Max bytes when buffering CLI stdout
    stderr: Callable[[str], None] | None = None  # Callback for stderr output from CLI
    can_use_tool: CanUseTool | None = None  # Tool permission callback
    hooks: dict[HookEvent, list[HookMatcher]] | None = None  # Hook configurations
    user: str | None = None
    # When true resumed sessions will fork to a new session ID rather than
    # continuing the previous session.
    fork_session: bool = False
    agents: dict[str, AgentDefinition] | None = None  # Agent definitions for custom agents
    setting_sources: list[SettingSource] | None = None  # Setting sources to load
    # Sandbox configuration for bash command isolation.
    # Filesystem and network restrictions are derived from permission rules (Read/Edit/WebFetch),
    # not from these sandbox settings.
    sandbox: SandboxSettings | None = None
    plugins: list[SdkPluginConfig] = field(default_factory=list)  # Plugin configurations
    thinking: ThinkingConfig | None = None  # Controls extended thinking behavior.
    effort: ReasoningEffort | None = None  # Effort level for thinking depth.
    # Output format for structured outputs (matches Messages API structure)
    # Example: {"type": "json_schema", "schema": {"type": "object", "properties": {...}}}
    output_format: dict[str, Any] | None = None
    # Enable file checkpointing to track file changes during the session.
    # When enabled, files can be rewound to their state at any user message
    # using `ClaudeSDKClient.rewind_files()`.
    enable_file_checkpointing: bool = False
    # Agent name for the main thread. The agent must be defined in `agents` or settings.
    agent: str | None = None
    # When false, disables session persistence to disk.
    persist_session: bool | None = None
    # Must be True when using permission_mode='bypassPermissions'.
    allow_dangerously_skip_permissions: bool = False
    # Resume from a specific message UUID (use with `resume`).
    resume_session_at: str | None = None
    # Enable debug mode for the Claude Code process.
    debug: bool = False
    # Write debug logs to a specific file path. Implicitly enables debug mode.
    debug_file: str | None = None
    # Enforce strict validation of MCP server configurations.
    strict_mcp_config: bool = False

    def validate(self) -> None:
        """Validate option constraints.

        Raises:
            ValueError: If mutually exclusive options are set.
        """
        if self.can_use_tool and self.permission_prompt_tool_name:
            msg = (
                "can_use_tool callback cannot be used with permission_prompt_tool_name. "
                "Please use one or the other."
            )
            raise ValueError(msg)
