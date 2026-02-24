"""ClaudeAgentOptions and session configuration types."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal


if TYPE_CHECKING:
    from collections.abc import Callable

    from clawd_code_sdk.models.base import ModelName

    from .agents import AgentDefinition, SystemPromptPreset, ToolsPreset
    from .base import PermissionMode, ReasoningEffort, SettingSource, ThinkingConfig
    from .hooks import HookEvent, HookMatcher
    from .mcp import McpServerConfig, SdkPluginConfig
    from .permissions import CanUseTool
    from .sandbox import SandboxSettings

logger = logging.getLogger(__name__)


# ============================================================================
# Session configuration
# ============================================================================


@dataclass(kw_only=True)
class NewSession:
    """Start a fresh session.

    Attributes:
        session_id: Deterministic session ID, or None to auto-generate a UUID.
        persist: Whether to persist the session to disk.
    """

    mode: Literal["new"] = "new"
    session_id: str | None = None
    persist: bool = True


@dataclass(kw_only=True)
class ResumeSession:
    """Resume an existing session by ID.

    Attributes:
        session_id: The session ID to resume.
        fork: If True, fork to a new session ID instead of continuing in-place.
        at_message: Resume from a specific message UUID within the session.
        persist: Whether to persist the session to disk.
    """

    mode: Literal["resume"] = "resume"
    session_id: str
    fork: bool = False
    at_message: str | None = None
    persist: bool = True


@dataclass(kw_only=True)
class ContinueLatest:
    """Continue the most recent conversation.

    Attributes:
        fork: If True, fork to a new session ID instead of continuing in-place.
        persist: Whether to persist the session to disk.
    """

    mode: Literal["continue"] = "continue"
    fork: bool = False
    persist: bool = True


SessionConfig = NewSession | ResumeSession | ContinueLatest
"""Union of all session configuration types.

Can also be specified as a plain ``str``, which is a shortcut for
``ResumeSession(session_id=str)``.
"""


def resolve_session_config(value: str | SessionConfig | None) -> SessionConfig:
    """Normalize a session config value.

    Args:
        value: A SessionConfig instance, a session ID string (shortcut for
            ResumeSession), or None (defaults to NewSession).

    Returns:
        A concrete SessionConfig instance.
    """
    match value:
        case None:
            return NewSession()
        case str() as session_id:
            return ResumeSession(session_id=session_id)
        case NewSession() | ResumeSession() | ContinueLatest() as config:
            return config


# ============================================================================
# Main options
# ============================================================================


@dataclass
class ClaudeAgentOptions:
    """Query options for Claude SDK."""

    # Tools
    tools: list[str] | ToolsPreset | None = None
    """Tools available to the agent."""
    allowed_tools: list[str] | None = None
    """Tools which execute without prompting for permission."""
    disallowed_tools: list[str] | None = None
    """Tools that are removed from agent context and cant be used."""
    # MCP
    mcp_servers: dict[str, McpServerConfig] | str | Path = field(default_factory=dict)
    """MCP servers for the agent."""
    chrome: bool = False
    """Add the chrome-tools MCP server (-> Claude Code browser extension) to the agent."""
    strict_mcp_config: bool = False
    """Enforce strict validation of MCP server configurations."""
    # Permissions
    permission_mode: PermissionMode | None = None
    """Permission mode."""
    allow_dangerously_skip_permissions: bool = False
    """Must be True when using permission_mode='bypassPermissions'."""
    permission_prompt_tool_name: str | None = None
    """MCP tool to handle permission prompts."""
    can_use_tool: CanUseTool | None = None
    """Tool permission callback."""
    # Session
    session: str | SessionConfig | None = None
    """Session configuration.

    Controls how the CLI session is started:
    - ``None`` or ``NewSession()``: Start a fresh session.
    - ``"session-id"`` or ``ResumeSession(session_id="...")``: Resume by ID.
    - ``ContinueLatest()``: Continue the most recent conversation.
    """
    # Limits
    max_turns: int | None = None
    """Maximum allowed amount of agentic turns."""
    max_budget_usd: float | None = None
    """Maximum amount of USD budget which may be consumed."""
    # Model
    model: ModelName | str | None = None
    """Session model."""
    fallback_model: ModelName | str | None = None
    """Fallback model in case default one is overloaded."""
    # Thinking
    thinking: ThinkingConfig | None = None
    """Controls thinking behavior."""
    effort: ReasoningEffort | None = None
    """Effort level for thinking depth."""
    # CLI SubProcess
    cli_path: str | Path | None = None
    """CLI path override (auto-detects by default)."""
    extra_args: dict[str, str | None] = field(default_factory=dict)
    """Arbitrary extra CLI flags."""
    max_buffer_size: int | None = None
    """Max bytes when buffering CLI stdout."""
    stderr: Callable[[str], None] | None = None
    """Callback for stderr output from CLI."""
    env: dict[str, str] = field(default_factory=dict)
    """Environment variables for the CLI subprocess."""
    user: str | None = None
    """User for the AnyIO process."""
    # Other
    settings: str | None = None
    """Path to a settings JSON file or a JSON string."""
    add_dirs: list[str | Path] = field(default_factory=list)
    """Add additional working directories."""
    cwd: str | Path | None = None
    """The working directory for the agent."""
    hooks: dict[HookEvent, list[HookMatcher]] | None = None
    """Hook configurations."""
    agents: dict[str, AgentDefinition] | None = None
    """SubAgent definitions."""
    setting_sources: list[SettingSource] | None = None
    """List of sources to load settings from."""
    sandbox: SandboxSettings | None = None
    """Sandbox configuration for bash command isolation.

    Filesystem and network restrictions are derived from permission rules (Read/Edit/WebFetch),
    not from these sandbox settings.
    """
    plugins: list[SdkPluginConfig] = field(default_factory=list)
    """"Plugin configurations to load."""
    output_format: dict[str, Any] | None = None
    """Output format for structured outputs (matches Messages API structure)

    Example: {"type": "json_schema", "schema": {"type": "object", "properties": {...}}}
    """
    enable_file_checkpointing: bool = False
    """Enable file checkpointing to track file changes during the session.

    When enabled, files can be rewound to their state at any user message
    using `ClaudeSDKClient.rewind_files()`.
    """
    system_prompt: str | SystemPromptPreset | None = None
    """System prompt for the agent."""
    agent: str | None = None
    """Agent name for the main thread. The agent must be defined in `agents` or settings."""

    debug_file: str | None = None
    """Write debug logs to a specific file path. Implicitly enables debug mode."""
    context_1m: bool = False
    """Enable 1M token context window (Sonnet 4/4.5 only)."""
    prompt_suggestions: bool | None = None
    """Whether to  create prompt suggestions."""
    worktree: bool | str = False
    """Create a new git worktree for the session (with optional name)."""

    def build_settings_value(self) -> str | None:
        """Build settings value, merging sandbox settings if provided.

        Returns the settings value as either:
        - A JSON string (if sandbox is provided or settings is JSON)
        - A file path (if only settings path is provided without sandbox)
        - None if neither settings nor sandbox is provided
        """
        import anyenv

        has_settings = self.settings is not None
        has_sandbox = self.sandbox is not None

        if not has_settings and not has_sandbox:
            return None

        # If only settings path and no sandbox, pass through as-is
        if has_settings and not has_sandbox:
            return self.settings

        # If we have sandbox settings, we need to merge into a JSON object
        settings_obj: dict[str, Any] = {}

        if has_settings:
            assert self.settings is not None
            settings_str = self.settings.strip()
            # Check if settings is a JSON string or a file path
            if settings_str.startswith("{") and settings_str.endswith("}"):
                settings_obj = anyenv.load_json(settings_str)
            else:
                settings_path = Path(settings_str)
                if settings_path.exists():
                    with settings_path.open(encoding="utf-8") as f:
                        settings_obj = json.load(f)
                else:
                    logger.warning("Settings file not found: %s", settings_path)

        # Merge sandbox settings
        if has_sandbox:
            assert self.sandbox is not None
            settings_obj["sandbox"] = self.sandbox.model_dump(by_alias=True, exclude_none=True)

        return anyenv.dump_json(settings_obj)

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
