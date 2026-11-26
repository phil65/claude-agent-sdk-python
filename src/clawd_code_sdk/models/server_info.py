"""Pydantic models for Claude Code server info structures."""

from typing import Any, Literal

from anthropic.types import Model
from pydantic import Field

from clawd_code_sdk.models.base import (
    ClaudeCodeBaseModel,
    EffortLevel,
    FastModeDisabledReason,
    FastModeState,
)


ApiProvider = Literal[
    "firstParty",
    "bedrock",
    "vertex",
    "foundry",
    "anthropicAws",
    "anthropicGoogleCloud",
    "mantle",
    "gateway",
]


class ClaudeCodeModelInfo(ClaudeCodeBaseModel):
    """Information about an available AI model from Claude Code."""

    value: str
    """Model identifier used in API calls (e.g., "default", "opus", "haiku")."""

    display_name: str
    """Human-readable display name (e.g., "Opus", "Default (recommended)")."""

    description: str
    """Full description including capabilities and pricing."""

    supports_effort: bool | None = None
    """Whether the model supports effort setting."""

    supported_effort_levels: list[EffortLevel] | None = None
    """Supported effort levels."""

    supports_adaptive_thinking: bool | None = None
    """Whether the model supports adaptive thinking."""

    supports_fast_mode: bool | None = None
    """Whether the model supports fast mode."""

    supports_auto_mode: bool | None = None
    """Whether the model supports auto mode."""

    supports_thinking_off: bool | None = None
    """Whether thinking can be turned off for the model."""

    disabled: bool | None = None
    """Visible but not selectable (only set for entries in ``unavailable_models``)."""

    resolved_model: str | None = None
    """Concrete model ID this entry resolves to (e.g. for aliases)."""


class ClaudeCodeCommandInfo(ClaudeCodeBaseModel):
    """Information about an available slash command from Claude Code."""

    name: str
    """Command name without the / prefix (e.g., "compact", "review")."""

    description: str
    """Full description of what the command does."""

    argument_hint: str
    """Usage hint for command arguments (may be empty string)."""

    aliases: list[str] | None = None
    """Alternate names that resolve to the command (e.g., /cost / /stats both resolve to /usage)."""

    builtin: bool | None = None
    """Whether this is a built-in command (as opposed to a skill/plugin/custom command)."""


class ClaudeCodeAccountInfo(ClaudeCodeBaseModel):
    """Account information from Claude Code."""

    email: str | None = None
    """User email address."""

    subscription_type: str | None = None
    """Subscription type (e.g., "Claude API")."""

    token_source: str | None = None
    """Where tokens come from (e.g., "claude.ai")."""

    api_key_source: str | None = None
    """Where API key comes from (e.g., "ANTHROPIC_API_KEY")."""

    organization: str | None = None
    """Organization name."""

    api_provider: ApiProvider | None = None
    """Active API backend.

    Anthropic OAuth login only applies when "firstParty"; for 3P providers
    the other fields are absent and auth is external (AWS creds, gcloud ADC, etc.).
    """


class ClaudeCodeAgentInfo(ClaudeCodeBaseModel):
    """Information about an available subagent from Claude Code server."""

    name: str
    """Agent type identifier (e.g., "Explore")."""

    description: str
    """Description of when to use this agent."""

    model: Model | str | None = None
    """Model alias this agent uses. If omitted, inherits the parent's model."""


class AuthConflict(ClaudeCodeBaseModel):
    """Sources of the auth token and API key when both are configured."""

    token_source: str
    api_key_source: str


class FeedbackMode(ClaudeCodeBaseModel):
    """Feedback collection mode."""

    kind: str


class ClaudeCodeServerInfo(ClaudeCodeBaseModel):
    """Complete server initialization info from Claude Code.

    This is returned by the Claude Code server during initialization and contains
    all available capabilities including models, commands, output styles, and
    account information.
    """

    models: list[ClaudeCodeModelInfo] = Field(default_factory=list)
    """List of available AI models."""

    commands: list[ClaudeCodeCommandInfo] = Field(default_factory=list)
    """List of available slash commands."""

    output_style: str = Field(default="default")
    """Current output style setting."""

    available_output_styles: list[str] = Field(default_factory=list)
    """List of all available output styles."""

    unavailable_models: list[ClaudeCodeModelInfo] | None = None
    """Models the account can see but not select (e.g. excluded by org ZDR settings)."""

    account: ClaudeCodeAccountInfo | None = Field(default=None)
    """Account and authentication information."""

    auth_conflict: AuthConflict | None = None
    """Set when both an auth token and an API key are configured (source names only)."""

    current_model: str | None = None
    """The CLI's active model at connect time."""

    agents: list[ClaudeCodeAgentInfo] = Field(default_factory=list)
    """List of available subagents."""

    fast_mode_state: FastModeState | None = None
    """Fast mode state: off, in cooldown after rate limit, or actively enabled."""

    fast_mode_disabled_reason: FastModeDisabledReason | None = None
    """Why fast mode is unavailable, if it is."""

    claude_code_version: str | None = None
    """Version of the Claude Code process answering initialize."""

    capabilities: list[str] | None = None
    """Feature capability tags supported by the CLI (undocumented, informational)."""

    current_permission_mode: str | None = None
    """Permission mode the session is currently in (undocumented)."""

    session_state: str | None = None
    """Current session state, e.g. "idle" (undocumented)."""

    user_output_styles_dir: str | None = None
    """Directory for user-defined output styles (undocumented)."""

    feedback_mode: FeedbackMode | None = None
    """How the CLI collects feedback (undocumented)."""

    analytics_disabled: bool | None = None
    other_hook_ask_outranks_host: bool | None = None
    remote_control_available: bool | None = None
    remote_control_auto_enable: bool | None = None
    remote_control_auto_connect_default: bool | None = None
    remote_control_auto_on_by_default: bool | None = None
    ide_rc_auto_enable_gate: bool | None = None

    hooks_applied: bool | None = None
    """False when the process was already running and did not register SDK hooks."""

    hook_on_failure_supported: bool | None = None
    """Whether the CLI honors ``on_failure`` on hook matchers."""

    hooks_when_unanswered_kept: int | None = None
    """Number of registered hook matchers whose ``whenUnanswered`` the CLI kept."""

    code_running_mcp_tools_applied: dict[str, list[str]] | None = None
    """MCP tools declared via ``codeRunningMcpTools``, keyed by server name."""

    managed_settings_applied: bool | None = None
    """Whether the initialize's ``managedSettings`` match the ones stored at launch."""

    mcp_servers_applied: bool | None = None
    """Whether the initialize's ``mcpServers`` match the set read at launch."""

    host_worded_asks: bool | None = None
    """Desktop host only: PreToolUse asks are sent to the host as can_use_tool requests."""

    workspace_trust_recorded: bool | None = None
    """Outcome of the ``workspaceTrust`` attestation."""

    inbound_read_receipts: bool | None = None
    """Remote Control hosts only: client messages get processing/processed receipts."""

    permission_mode_from_default_fallback: bool | None = None
    """IDE hosts only: permission mode is auto because no settings source configured one."""

    auto_default_nudge: str | None = None
    """IDE hosts only: the defaultMode the auto-default nudge offers to replace."""

    footer_indicator: dict[str, Any] | None = None
    """The terminal's configured footer pill (undocumented structure)."""

    feedback_survey_config: dict[str, Any] | None = None
    """Present only when the host may show the feedback survey (undocumented structure)."""

    survey_followup_box: dict[str, Any] | None = None
    """Survey follow-up config for VS Code/desktop hosts (undocumented structure)."""

    claude_in_chrome_at_startup: bool | None = None
    """Whether an IDE host should connect Claude in Chrome when the session starts."""

    claude_in_chrome_prompt_disabled: bool | None = None
    """True when CLAUDE_CODE_DISABLE_CFC_PROMPT is set."""

    plugins_applied: bool | None = None
    """Whether every plugin sent via initialize is loaded."""

    sdk_mcp_manifests_parked: (
        dict[
            str,
            Literal[
                "parked",
                "already_connected",
                "protocol_version_mismatch",
                "malformed",
                "not_honoured",
            ],
        ]
        | None
    ) = None

    pid: int | None = None
    """Process id."""
