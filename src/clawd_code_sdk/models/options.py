"""ClaudeAgentOptions and session configuration types."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, assert_never


if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from clawd_code_sdk.models import OnElicitation, OnUserQuestion
    from clawd_code_sdk.models.agents import AgentDefinition, ToolsPreset
    from clawd_code_sdk.models.base import (
        ModelName,
        PermissionMode,
        ReasoningEffort,
        SettingSource,
        ToolName,
    )
    from clawd_code_sdk.models.hooks import HookEvent, HookMatcher
    from clawd_code_sdk.models.mcp import McpServerConfig, SdkPluginConfig
    from clawd_code_sdk.models.permissions import CanUseTool
    from clawd_code_sdk.models.settings import ClaudeCodeSettings, Sandbox
    from clawd_code_sdk.models.thinking import ThinkingConfig

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class AskUserQuestionToolConfig:
    """Configuration for the AskUserQuestion tool."""

    preview_format: Literal["markdown", "html"] | None = None
    """Content format for the preview field on question options."""


@dataclass(kw_only=True)
class ToolConfig:
    """Per-tool configuration for built-in tools."""

    ask_user_question: AskUserQuestionToolConfig | None = None


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


@dataclass
class ClaudeAgentOptions:
    """Query options for Claude SDK."""

    # Tools
    tools: list[ToolName | str] | ToolsPreset | None = None
    """Tools available to the agent."""
    allowed_tools: list[ToolName | str] | None = None
    """Tools which execute without prompting for permission."""
    disallowed_tools: list[ToolName | str] | None = None
    """Tools that are removed from agent context and cant be used."""
    enable_agent_teams: bool = False
    """Enable the experimental agent teams feature."""
    disable_parallel_tool_use: bool = False
    """Disable parallel too use (only one tool_use block per response)."""
    tool_config: ToolConfig | None = None
    """Per-tool configuration for built-in tools."""
    enable_tool_search: bool | int | Literal["auto"] | None = None
    """Enable or disable MCP tool search.

    When many MCP tools are configured, tool definitions can consume a
    significant portion of the context window. Tool search dynamically
    loads tools on-demand instead of preloading all of them.

    - ``True``: Always enabled.
    - ``False``: Always disabled, all MCP tools loaded upfront.
    - ``"auto"``: Activates when MCP tools exceed 10% of context (default behavior).
    - ``int``: Auto-activates at this percentage threshold (e.g. ``5`` for 5%).
    - ``None`` (default): Uses Claude Code's default (auto at 10%).

    Requires models that support ``tool_reference`` blocks (Sonnet 4+, Opus 4+).
    """
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
    on_permission: CanUseTool | str | None = None
    """Permission handler for tool execution.

    Accepts either:
    - A callback function (``CanUseTool``): The SDK routes permission requests
      through the control protocol to this callback. Automatically adds
      ``--permission-prompt-tool stdio`` to the CLI.
    - A string: Name of an MCP tool to handle permission prompts
      (passed as ``--permission-prompt-tool <name>`` to the CLI).
    - ``None``: Default behavior.

    Interaction with ``permission_mode``:

    - ``"default"``: All tool calls are routed to this handler.
    - ``"acceptEdits"``: All tool calls are routed to this handler.
      The handler is responsible for implementing the auto-approve-edits policy.
    - ``"plan"``: Only the synthetic ``ExitPlanMode`` tool is routed here.
      Actual modification tools are blocked by the CLI before reaching the handler.
    - ``"dontAsk"``: This handler is NEVER invoked. The CLI auto-denies all
      tools not pre-approved via the permissions config internally.
    - ``"bypassPermissions"``: This handler is NEVER invoked. The CLI
      auto-approves all tools internally.
    """
    on_user_question: OnUserQuestion | None = None
    """Callback for handling AskUserQuestion elicitation requests.

    Called when Claude asks the user a clarifying question via the
    AskUserQuestion tool. If not set, these requests fall through
    to on_permission (if it's a callback) for backwards compatibility.
    """
    on_elicitation: OnElicitation | None = None
    """Callback for handling MCP elicitation requests.

    Called when an MCP server requests user input (form fields, URL auth, etc.)
    and no hook handles the request first.

    If not provided, elicitation requests that aren't handled by hooks will
    be declined automatically.
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
    task_budget: int | None = None
    """API-side task budget in tokens.

    When set, the model is made aware of its remaining token budget so it can
    pace tool use and wrap up before the limit.  The CLI sends this as
    ``output_config.task_budget`` with the ``task-budgets-2026-03-13`` beta
    header automatically.
    """
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
    settings: str | Path | ClaudeCodeSettings | None = None
    """Settings configuration.

    Accepts:
    - A ``str`` or ``Path``: interpreted as a path to a settings JSON file.
    - A ``ClaudeCodeSettings`` instance: serialized to JSON automatically.
    - ``None``: no explicit settings.
    """
    setting_sources: list[SettingSource] | None = None
    """List of sources to load settings from."""
    sandbox: Sandbox | None = None
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
    """Whether to create prompt suggestions."""
    agent_progress_summaries: bool | None = None
    """Enable periodic AI-generated progress summaries for running subagents.

    When True, the subagent's conversation is forked every ~30s to produce a short
    present-tense description (e.g. 'Analyzing authentication module'), emitted
    on task_progress events via the summary field. The fork reuses the
    subagent's model and prompt cache, so cost is typically minimal.

    Applies to both foreground and background subagents. Defaults to False.
    """
    replay_user_messages: bool | None = None
    """Whether to replay user messages in the session."""
    worktree: bool | str = False
    """Create a new git worktree for the session (with optional name)."""

    def build_settings_value(self) -> str | None:
        """Build the CLI ``--settings`` value, merging sandbox if provided.

        Returns:
            A JSON string, a file path, or None.
        """
        import anyenv

        from clawd_code_sdk.models.settings import ClaudeCodeSettings as _Settings

        # Resolve settings to a dict (or pass through as file path)
        match self.settings:
            case _Settings() as model:
                settings_obj = model.model_dump(by_alias=True, exclude_none=True)
            case str() | Path() as path if self.sandbox and Path(path).exists():
                with Path(path).open(encoding="utf-8") as f:
                    settings_obj = json.load(f)
            case str() | Path() as path if self.sandbox:
                logger.warning("Settings file not found: %s", path)
                settings_obj = {}
            case str() | Path() as path:  # No sandbox to merge, pass file path directly to CLI
                return str(path)
            case None:
                settings_obj = {}
            case _ as unreachable:
                assert_never(unreachable)

        # Merge sandbox settings
        if self.sandbox is not None:
            settings_obj["sandbox"] = self.sandbox.model_dump(by_alias=True, exclude_none=True)

        return anyenv.dump_json(settings_obj) if settings_obj else None

    def get_json_schema(self) -> dict[str, Any] | None:
        from pydantic import TypeAdapter

        match self.output_schema:
            case type() as typ:
                return TypeAdapter(typ).json_schema()
            case dict() as schema:
                return schema
            case None:
                return None
            case _ as unreachable:
                assert_never(unreachable)

    def get_session(self) -> SessionConfig:
        match self.session:
            case None:
                return NewSession()
            case str() as session_id:
                return ResumeSession(session_id=session_id)
            case NewSession() | ResumeSession() | ContinueLatest() | FromPR() as config:
                return config
            case _ as unreachable:
                assert_never(unreachable)
