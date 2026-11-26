"""ClaudeAgentOptions and session configuration types."""

import dataclasses
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
    title: str | None = None
    """Title for the session, or None to auto-generate a title."""


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
    drops_turn: str | None = None
    """Guard for truncating resume (``--resume-drops-turn``).

    Declares the user message UUID of the turn that ``at_message`` is expected to
    drop. The CLI refuses the resume if the truncation would discard anything else.
    Only meaningful together with ``at_message``.
    """


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
    # title: str | None = None
    # """Title for the session, or None to auto-generate a title."""


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
    fine_grained_tool_streaming: bool | Literal["auto"] = "auto"
    """Stream tool input to the client as the model writes it (fine-grained tool streaming).

    With it, ``stream_event`` messages carry tool input JSON as it is generated, so a UI can
    show a long ``Write``/``Edit`` input live and the tool call starts sooner. It saves no
    tokens. The partial tool input JSON is not validated by the API, and some endpoints
    reject the request with HTTP 400 (proxies / gateways, some models on Bedrock and Vertex).

    - ``"auto"`` (default): on when the CLI talks to Anthropic's API directly (no
      ``CLAUDE_CODE_USE_BEDROCK`` / ``_VERTEX`` / other provider env, ``ANTHROPIC_BASE_URL``
      unset or ``api.anthropic.com``); otherwise the CLI's own default applies.
    - ``True`` / ``False``: force it on / off.

    ``CLAUDE_CODE_ENABLE_FINE_GRAINED_TOOL_STREAMING`` in ``env`` overrides this option.
    """
    # MCP
    mcp_servers: dict[str, McpServerConfig] | str | Path = field(default_factory=dict)
    """MCP servers for the agent."""
    mcp_servers_delivery: Literal["argv", "initialize"] = "initialize"
    """How the ``mcp_servers`` that Claude Code runs or connects to (stdio, SSE, HTTP) reach it.

    - ``"initialize"`` (default): in the initialize request over stdin (the CLI is started
      with ``--await-initialize``), so server ``env`` and ``headers`` stay off the command
      line, where other users of the machine can read them. Needs Claude Code 2.1.261 or
      newer; connecting fails if the CLI does not take them (``mcp_servers_applied``).
    - ``"argv"``: in one ``--mcp-config`` flag, for older Claude Code. Deprecated upstream.

    In-process servers (``McpSdkServerConfigWithInstance``) and an ``mcp_servers`` file path
    are not affected, and a launch with ``--sdk-url`` in ``extra_args`` always uses
    ``--mcp-config``, as that session cannot read the request at launch.
    """
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

    Tools that ``allowed_tools`` allows outright (``"Read"``, ``"Read()"``, ``"Read(*)"``)
    never reach the handler either. Connecting emits a ``CanUseToolShadowedWarning`` when
    a callback is set together with ``"bypassPermissions"`` or such entries.
    """
    on_user_question: OnUserQuestion | None = None
    """Callback for handling AskUserQuestion elicitation requests.

    Called when Claude asks the user a clarifying question via the
    AskUserQuestion tool. If not set, these requests fall through
    to on_permission (if it's a callback) for backwards compatibility.
    """
    permission_prompts: Literal["host", "none"] | None = None
    """Who answers permission prompts.

    ``"host"`` (default): this process, through ``on_permission``.
    ``"none"``: nobody - permission mode, rules and hooks still decide, and anything
    that would otherwise prompt is denied immediately.
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
    project_config_root: str | Path | None = None
    """The trusted checkout that ``cwd`` is a worktree of.

    Project settings, ``.mcp.json``, the ``.claude`` config trees and
    ``CLAUDE_PROJECT_DIR`` come from here instead of ``cwd``. Absolute path.
    """
    # Settings
    settings: str | Path | ClaudeCodeSettings | None = None
    """Settings configuration.

    Accepts:
    - A ``str`` or ``Path``: interpreted as a path to a settings JSON file.
    - A ``ClaudeCodeSettings`` instance: serialized to JSON automatically.
    - ``None``: no explicit settings.
    """
    setting_sources: list[SettingSource] | None = None
    """Sources to load filesystem settings from.

    None loads the CLI's defaults (user, project, local); ``[]`` loads none.
    """
    skills: list[str] | None = None
    """List of skills to use for the agent."""
    sandbox: Sandbox | None = None
    """Sandbox configuration for bash command isolation.

    Filesystem and network restrictions are derived from permission rules (Read/Edit/WebFetch),
    not from these sandbox settings.
    """
    debug_file: str | None = None
    """Write debug logs to a specific file path. Implicitly enables debug mode."""
    # Agent config
    system_prompt: str | list[str] | None = None
    """System prompt for the agent."""
    include_builtin_system_prompt: bool = True
    """Whether to include Claude Code's builtin system prompt.


    When True (default) and system_prompt is set, it is appended to the
    builtin system prompt. When False, the system_prompt replaces it entirely.
    """
    exclude_dynamic_sections: bool | None = None
    """Whether to exclude dynamic sections from the system prompt."""
    system_prompt_snapshot: bool | None = None
    """Snapshot the system prompt on the first request and reuse it verbatim.

    Keeps the prompt byte-identical across requests and resumes (better cache hits).
    """
    plan_mode_instructions: str | None = None
    """Custom workflow body for the plan-mode system reminder."""

    hooks: dict[HookEvent, list[HookMatcher]] | None = None
    """Hook configurations."""
    agents: dict[str, AgentDefinition] | None = None
    """SubAgent definitions."""
    plugins: list[SdkPluginConfig] = field(default_factory=list)
    """"Plugin configurations to load."""
    plugin_delivery: Literal["argv", "initialize"] = "argv"
    """How ``plugins`` reach Claude Code.

    - ``"argv"`` (default): one ``--plugin-dir`` flag per plugin. Works with any Claude Code
      version, but the command line grows with the plugin count (Windows refuses one past
      32,767 characters).
    - ``"initialize"``: in the initialize request over stdin (the CLI is started with
      ``--await-initialize``); connecting fails if the CLI does not load them
      (``plugins_applied``). A launch with ``--sdk-url`` in ``extra_args`` always uses argv.
    """
    capture_sdk_mcp_manifests: bool = True
    """Do the in-process MCP servers' handshake before connecting and send its results.

    The initialize request then carries each server's ``initialize`` and first
    ``tools/list`` results (``sdkMcpServerManifests``), so the CLI connects them without
    control round trips before the first turn. A server whose handshake fails, or that the
    CLI does not take, is handshaken over the control channel as before. Off when the
    ``CLAUDE_AGENT_SDK_DISABLE_MCP_MANIFESTS`` environment variable is set (as upstream).
    """
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
    include_hook_events: bool = False
    """Include hook lifecycle events in the output stream.

    When True, ``hook_started``, ``hook_progress``, and ``hook_response`` system
    messages will be emitted for all hook event types. SessionStart and Setup
    hook events are always emitted regardless of this setting.
    """
    replay_user_messages: bool | None = None
    """Whether to replay user messages in the session."""
    forward_subagent_text: bool = False
    """Forward subagent text and thinking blocks as messages with ``parent_tool_use_id`` set.

    By default only tool_use/tool_result blocks from subagents are emitted.
    """
    verbatim_prompts: bool = False
    """Send every user message with ``client_composed: true``.

    The CLI then delivers the prompt text as written: no ``@path`` expansion and
    no slash-command dispatch. Requires Claude Code 2.1.248+.
    """
    tool_aliases: dict[str, str] | None = None
    """Redirect built-in tool names to other tools, e.g. ``{"Bash": "mcp__ws__bash"}``.

    Single-hop; complementary to ``disallowed_tools``, not a replacement.
    """
    per_task_stop_affordance: bool | None = None
    """Declare that this consumer can stop individual background tasks (``stop_task``).

    When declared, an interrupt only aborts the current turn and spares running
    background agents/workflows.
    """
    worktree: bool | str = False
    """Create a new git worktree for the session (with optional name)."""
    instrument: bool = False
    """Whether to instrument the session with tracing hooks."""

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
            case str() | Path() as value if self.sandbox:
                settings_obj = self._load_settings_for_sandbox_merge(value)
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

    def _load_settings_for_sandbox_merge(self, value: str | Path) -> dict[str, Any]:
        """Load ``settings`` (inline JSON or a file) so sandbox can be merged into it.

        Fails closed (upstream #1426): if the settings cannot be loaded, the CLI
        must not start with the sandbox settings alone, silently missing the
        caller's permission rules and hooks. A relative path is resolved against
        ``cwd``, as the CLI does when it reads the file itself.

        Raises:
            CLIConnectionError: If the settings are missing, unreadable, invalid
                JSON, or not a JSON object.
        """
        from clawd_code_sdk._errors import CLIConnectionError

        if isinstance(value, str) and value.lstrip().startswith("{"):
            try:
                loaded = json.loads(value)
            except json.JSONDecodeError as e:
                # The inline value is not logged or echoed: it can hold secrets.
                msg = f"Inline settings JSON is invalid (line {e.lineno}, column {e.colno})"
                raise CLIConnectionError(msg) from None
            source = "Inline settings JSON"
        else:
            path = Path(value)
            if not path.is_absolute() and self.cwd is not None:
                path = Path(self.cwd) / path
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
            except OSError as e:
                msg = f"Cannot read settings file {path} to merge sandbox settings: {e}"
                raise CLIConnectionError(msg) from e
            except json.JSONDecodeError as e:
                msg = f"Settings file {path} is not valid JSON: {e}"
                raise CLIConnectionError(msg) from e
            source = f"Settings file {path}"
        if not isinstance(loaded, dict):
            raise CLIConnectionError(f"{source} must contain a JSON object")
        return loaded

    def initialize_mcp_servers(self) -> dict[str, dict[str, Any]] | None:
        """The servers to send in the initialize request, or None to send none there."""
        if self.mcp_servers_delivery != "initialize" or "sdk-url" in self.extra_args:
            return None
        if not isinstance(self.mcp_servers, dict):
            return None
        servers = {
            name: _serialize_mcp_server(config)
            for name, config in self.mcp_servers.items()
            if config.type != "sdk"
        }
        return servers or None

    def initialize_plugins(self) -> list[dict[str, Any]] | None:
        """The plugins to send in the initialize request, or None to pass them as flags."""
        if self.plugin_delivery != "initialize" or "sdk-url" in self.extra_args:
            return None
        plugins = [p.model_dump(by_alias=True, exclude_none=True) for p in self.plugins]
        return plugins or None

    def reads_initialize_at_launch(self) -> bool:
        """Whether the CLI waits for the initialize request (``--await-initialize``)."""
        return self.initialize_mcp_servers() is not None or self.initialize_plugins() is not None

    def sdk_mcp_server_configs(self) -> dict[str, dict[str, Any]] | None:
        """Settings of the in-process MCP servers (timeout, tool policy), by server name."""
        from clawd_code_sdk.models.mcp import McpSdkServerConfig

        if not isinstance(self.mcp_servers, dict):
            return None
        configs: dict[str, dict[str, Any]] = {}
        for name, config in self.mcp_servers.items():
            if not isinstance(config, McpSdkServerConfig):
                continue
            settings: dict[str, Any] = {}
            if config.timeout is not None:
                settings["timeout"] = config.timeout
            if config.tools is not None:
                settings["tools"] = [
                    {k: v for k, v in dataclasses.asdict(t).items() if v is not None}
                    for t in config.tools
                ]
            if settings:
                configs[name] = settings
        return configs or None

    def argv_mcp_servers(self) -> dict[str, dict[str, Any]]:
        """The servers for ``--mcp-config``.

        All of them, or only the in-process ones when the others go in the initialize request.
        """
        if not isinstance(self.mcp_servers, dict):
            return {}
        in_initialize = self.initialize_mcp_servers() is not None
        return {
            name: _serialize_mcp_server(config)
            for name, config in self.mcp_servers.items()
            if not in_initialize or config.type == "sdk"
        }

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


def _serialize_mcp_server(config: McpServerConfig) -> dict[str, Any]:
    """A server config as the CLI takes it: no live instance, no unset fields."""
    return {
        key: value
        for key, value in dataclasses.asdict(config).items()
        if key != "instance" and value is not None
    }
