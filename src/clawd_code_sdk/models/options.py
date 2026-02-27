"""ClaudeAgentOptions and session configuration types."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, TypedDict


if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from clawd_code_sdk.models.base import ModelName
    from clawd_code_sdk.models.permissions import OnUserQuestion

    from .agents import AgentDefinition, ToolsPreset
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
class BaseSessionConfig:
    """Common fields for all session configurations."""

    persist: bool = True
    """Whether to persist the session to disk."""


@dataclass(kw_only=True)
class NewSession(BaseSessionConfig):
    """Start a fresh session."""

    mode: Literal["new"] = "new"
    session_id: str | None = None
    """Deterministic session ID, or None to auto-generate a UUID."""


@dataclass(kw_only=True)
class ResumeSession(BaseSessionConfig):
    """Resume an existing session by ID."""

    mode: Literal["resume"] = "resume"
    session_id: str
    """The session ID to resume."""
    fork: bool = False
    """If True, fork to a new session ID instead of continuing in-place."""
    at_message: str | None = None
    """Resume from a specific message UUID within the session."""


@dataclass(kw_only=True)
class ContinueLatest(BaseSessionConfig):
    """Continue the most recent conversation."""

    mode: Literal["continue"] = "continue"
    fork: bool = False
    """If True, fork to a new session ID instead of continuing in-place."""


@dataclass(kw_only=True)
class FromPR(BaseSessionConfig):
    """Resume sessions linked to a specific GitHub PR.

    Accepts a PR number or URL. Sessions are automatically linked
    when created via ``gh pr create``.
    """

    mode: Literal["from_pr"] = "from_pr"
    pr: int | str
    """PR number or URL."""
    fork: bool = False
    """If True, fork to a new session ID instead of continuing in-place."""


SessionConfig = NewSession | ResumeSession | ContinueLatest | FromPR
"""Union of all session configuration types.

Can also be specified as a plain ``str``, which is a shortcut for
``ResumeSession(session_id=str)``.
"""


class ListSessionsOptions(TypedDict, total=False):
    """Options for listing sessions.

    When ``dir`` is provided, returns sessions for that project directory
    and its git worktrees. When omitted, returns sessions across all projects.
    """

    dir: str
    """Directory to list sessions for.

    When provided, returns sessions for this project directory
    (and its git worktrees). When omitted, returns sessions
    across all projects.
    """

    limit: int
    """Maximum number of sessions to return."""


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
        case BaseSessionConfig() as config:
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
    on_user_question: OnUserQuestion | None = None
    """Callback for handling AskUserQuestion elicitation requests.

    Called when Claude asks the user a clarifying question via the
    AskUserQuestion tool. If not set, these requests fall through
    to can_use_tool (if set) for backwards compatibility.
    """
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
    max_buffer_size: int = 10 * 1024 * 1024
    """Max bytes when buffering CLI stdout."""
    stderr: Callable[[str], None] | None = None
    """Callback for stderr output from CLI."""
    env: dict[str, str] = field(default_factory=dict)
    """Environment variables for the CLI subprocess."""
    user: str | None = None
    """User for the AnyIO process."""
    # CWD
    add_dirs: Sequence[str | Path] = field(default_factory=list)
    """Add additional working directories."""
    cwd: str | Path | None = None
    """The working directory for the agent."""
    # Settings
    settings: str | None = None
    """Path to a settings JSON file or a JSON string."""
    setting_sources: list[SettingSource] | None = None
    """List of sources to load settings from."""
    sandbox: SandboxSettings | None = None
    """Sandbox configuration for bash command isolation.

    Filesystem and network restrictions are derived from permission rules (Read/Edit/WebFetch),
    not from these sandbox settings.
    """
    debug_file: str | None = None
    """Write debug logs to a specific file path. Implicitly enables debug mode."""
    # Agent config
    system_prompt: str | None = None
    """System prompt for the agent."""
    include_builtin_system_prompt: bool = True
    """Whether to include Claude Code's builtin system prompt.

    When True (default) and system_prompt is set, it is appended to the
    builtin system prompt. When False, the system_prompt replaces it entirely.
    """
    hooks: dict[HookEvent, list[HookMatcher]] | None = None
    """Hook configurations."""
    agents: dict[str, AgentDefinition] | None = None
    """SubAgent definitions."""
    plugins: list[SdkPluginConfig] = field(default_factory=list)
    """"Plugin configurations to load."""
    output_schema: dict[str, Any] | type | None = None
    """JSON schema for structured output.

    Accepts either a JSON schema dict or a Python type (Pydantic model,
    dataclass, TypedDict, etc.) which will be converted to a JSON schema
    automatically.

    When set, Claude will return responses conforming to this schema.

    Examples:
        # As a dict
        output_schema={"type": "object", "properties": {"name": {"type": "string"}}}
        # As a type
        output_schema=MyPydanticModel
    """
    # Other
    enable_file_checkpointing: bool = False
    """Enable file checkpointing to track file changes during the session.

    When enabled, files can be rewound to their state at any user message
    using `ClaudeSDKClient.rewind_files()`.
    """
    agent: str | None = None
    """Agent name for the main thread. The agent must be defined in `agents` or settings."""
    context_1m: bool = False
    """Enable 1M token context window (Sonnet 4/4.5 only)."""
    prompt_suggestions: bool | None = None
    """Whether to  create prompt suggestions."""
    worktree: bool | str = False
    """Create a new git worktree for the session (with optional name)."""
    enable_agent_teams: bool = False
    """Enable the experimental agent teams feature."""

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
