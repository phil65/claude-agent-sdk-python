"""SDK control protocol types."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, Literal, TypedDict, assert_never

from pydantic import BaseModel, ConfigDict, Discriminator, Field, TypeAdapter
from pydantic.alias_generators import to_camel

from clawd_code_sdk.models.agents import AgentWireDefinition
from clawd_code_sdk.models.base import (
    ClaudeCodeBaseModel,
    EffortLevel,
    ElicitationMode,
    ModelName,
    PermissionMode,
)
from clawd_code_sdk.models.context_usage import UsageRateLimits, UsageReportSession
from clawd_code_sdk.models.hooks import HookEvent, HookInput
from clawd_code_sdk.models.mcp import (
    ExternalMcpServerConfig,
    JSONRPCMessage,
    McpServerStatusEntry,
    SdkPluginConfig,
)
from clawd_code_sdk.models.permissions import PermissionUpdate
from clawd_code_sdk.models.server_info import (
    ClaudeCodeAccountInfo,
    ClaudeCodeAgentInfo,
    ClaudeCodeCommandInfo,
)


if TYPE_CHECKING:
    import mcp.types

DecisionReasonType = Literal[
    "rule",
    "mode",
    "subcommandResults",
    "permissionPromptTool",
    "hook",
    "asyncAgent",
    "sandboxOverride",
    "workingDir",
    "safetyCheck",
    "classifier",
    "other",
]


class _ControlBase(BaseModel):
    """Frozen base for all SDK control request models."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)


# SDK Control Protocol
class SDKControlInterruptRequest(_ControlBase):
    """SDK control interrupt request."""

    subtype: Literal["interrupt"] = "interrupt"
    cancel_queued: bool | None = None
    """Also cancel queued (not yet started) user messages."""


class SDKControlInterruptResponse(BaseModel):
    """Response to an interrupt request."""

    still_queued: list[str] = Field(default_factory=list)
    """UUIDs of user messages still queued after the interrupt."""
    cancelled: list[str] | None = None
    """UUIDs of queued user messages that were cancelled."""


class SDKControlPermissionRequest(_ControlBase):
    """SDK control permission request."""

    subtype: Literal["can_use_tool"] = "can_use_tool"
    tool_name: str
    input: dict[str, Any]
    permission_suggestions: list[PermissionUpdate] | None = None
    blocked_path: str | None = None
    decision_reason: str | None = None
    title: str | None = None
    display_name: str | None = None
    tool_use_id: str
    agent_id: str | None = None
    description: str | None = None
    decision_reason_type: DecisionReasonType | None = None
    """Structured discriminator for why auto-mode escalated.

    Lets SDK hosts make policy (e.g. auto-deny safetyCheck) without parsing decision_reason text.
    For compound bash commands this is "subcommandResults" even when a safetyCheck is nested inside
    — check classifier_approvable for that case.
    """
    classifier_approvable: bool | None = None
    """Set when a safetyCheck is present anywhere in the decision reason
    (including nested inside subcommandResults for compound bash).
    false = at least one safety check requires manual approval
    (e.g. Windows path bypass, dangerous rm);
    true = all safety checks MAY be classifier-approved
    (e.g. sensitive-file paths). Absent when no safetyCheck is involved."""


class SDKControlInitializeRequest(_ControlBase):
    """SDK control initialize request."""

    subtype: Literal["initialize"] = "initialize"
    hooks: dict[HookEvent, Any] | None = None
    agents: dict[str, AgentWireDefinition] | None = None
    sdk_mcp_servers: list[str] | None = Field(default=None, serialization_alias="sdkMcpServers")
    mcp_servers: dict[str, dict[str, Any]] | None = Field(
        default=None, serialization_alias="mcpServers"
    )
    """Servers for Claude Code to run or connect to, as one ``--mcp-config`` item would hold
    them; read only at launch under ``--await-initialize`` (``mcp_servers_applied``)."""
    system_prompt: list[str] | None = Field(default=None, serialization_alias="systemPrompt")
    append_system_prompt: str | None = Field(default=None, serialization_alias="appendSystemPrompt")
    exclude_dynamic_sections: bool | None = Field(
        default=None,
        serialization_alias="excludeDynamicSections",
    )
    """When true, omit per-user dynamic sections from the cached system prompt.

    Omits info like working directory, auto-memory path and re-inject them as the first usermessage.
    Lets cross-user prompt caching hit on a static system prompt prefix.
    Tradeoff: the model sees this context slightly later in the prompt,
    so steering on the working directory and memory location is marginally less authoritative.
    Has no effect when a custom (non-preset) system prompt is in use."""
    json_schema: dict[str, Any] | None = Field(default=None, serialization_alias="jsonSchema")
    prompt_suggestions: bool | None = Field(default=None, serialization_alias="promptSuggestions")
    agent_progress_summaries: bool | None = Field(
        default=None, serialization_alias="agentProgressSummaries"
    )
    title: str | None = None
    """Custom session title.

    When provided, the session uses this title and skips automatic title generation.
    Has no effect on the persisted title when resuming an existing session."""
    skills: list[str] | None = None
    """When provided, only given skills are loaded into the main session system prompt.

    Uses the same rules as AgentDefinition.skills:
    exact name, plugin-qualified name, or ":name" suffix.
    Omit to load every discovered skill.
    Applies to the main session only; subagents use AgentDefinition.skills."""
    plan_mode_instructions: str | None = Field(
        default=None,
        serialization_alias="planModeInstructions",
    )
    """Custom workflow body for the plan-mode system reminder."""
    system_prompt_snapshot: bool | None = Field(
        default=None, serialization_alias="systemPromptSnapshot"
    )
    forward_subagent_text: bool | None = Field(
        default=None, serialization_alias="forwardSubagentText"
    )
    tool_aliases: dict[str, str] | None = Field(default=None, serialization_alias="toolAliases")
    per_task_stop_affordance: bool | None = Field(
        default=None, serialization_alias="perTaskStopAffordance"
    )
    supported_dialog_kinds: list[str] | None = Field(
        default=None, serialization_alias="supportedDialogKinds"
    )


class SDKControlSetPermissionModeRequest(_ControlBase):
    """SDK control set permission mode request."""

    subtype: Literal["set_permission_mode"] = "set_permission_mode"
    mode: PermissionMode


class SDKHookCallbackRequest(_ControlBase):
    """SDK hook callback request."""

    subtype: Literal["hook_callback"] = "hook_callback"
    callback_id: str
    input: HookInput
    tool_use_id: str | None = None


class SDKControlMcpMessageRequest(_ControlBase):
    """SDK control MCP message request."""

    subtype: Literal["mcp_message"] = "mcp_message"
    server_name: str
    message: JSONRPCMessage


class SDKControlRewindFilesRequest(_ControlBase):
    """SDK control rewind files request."""

    subtype: Literal["rewind_files"] = "rewind_files"
    user_message_id: str
    dry_run: bool | None = None


class SDKControlCancelAsyncMessageRequest(_ControlBase):
    """Drops a pending async user message from the command queue by uuid."""

    subtype: Literal["cancel_async_message"] = "cancel_async_message"
    message_uuid: str


class SDKControlSeedReadStateRequest(_ControlBase):
    """Seeds the readFileState cache with a path+mtime entry.

    Use when a prior Read was removed from context (e.g. by snip) so Edit
    validation would fail despite the client having observed the Read.
    """

    subtype: Literal["seed_read_state"] = "seed_read_state"
    path: str
    mtime: int


class SDKControlStopTaskRequest(_ControlBase):
    """SDK control stop task request."""

    subtype: Literal["stop_task"] = "stop_task"
    task_id: str


class SDKControlApplyFlagSettingsRequest(_ControlBase):
    """SDK control apply flag settings request."""

    subtype: Literal["apply_flag_settings"] = "apply_flag_settings"
    settings: dict[str, Any]


class SDKControlSetModelRequest(_ControlBase):
    """Sets the model to use for subsequent conversation turns."""

    subtype: Literal["set_model"] = "set_model"
    model: ModelName | str | None = None


class SDKControlSetMaxThinkingTokensRequest(_ControlBase):
    """Sets the maximum number of thinking tokens for extended thinking."""

    subtype: Literal["set_max_thinking_tokens"] = "set_max_thinking_tokens"
    max_thinking_tokens: int | None = None
    thinking_display: Literal["summarized", "omitted", "highlights"] | None = None


class SDKControlMcpStatusRequest(_ControlBase):
    """Requests the current status of all MCP server connections."""

    subtype: Literal["mcp_status"] = "mcp_status"
    live_reply: bool | None = Field(default=None, serialization_alias="liveReply")


class SDKControlMcpSetServersRequest(_ControlBase):
    """Replaces the set of dynamically managed MCP servers."""

    subtype: Literal["mcp_set_servers"] = "mcp_set_servers"
    servers: dict[str, ExternalMcpServerConfig]


class SDKControlReloadPluginsRequest(_ControlBase):
    """Reloads plugins from disk and returns the refreshed session components."""

    subtype: Literal["reload_plugins"] = "reload_plugins"
    hold_on_cache_impact: bool | None = None
    """Don't apply the reload if it would change the tool list the prompt cache depends on."""
    add_plugins: list[SdkPluginConfig] | None = None
    """Additional plugins to load as part of the reload."""
    refuse_if_busy: bool | None = None


class PluginInfo(ClaudeCodeBaseModel):
    """Information about a loaded plugin."""

    name: str
    path: str
    source: str | None = None
    version: str | None = None


class ReloadPluginsCacheImpact(BaseModel):
    """How a reload would change the session's tool list."""

    mcp_servers_added: list[str]
    mcp_servers_removed: list[str]
    lsp_tool_change: Literal["adds", "may-add", "removes", "may-remove"] | None


class SDKControlReloadPluginsResponse(ClaudeCodeBaseModel):
    """Refreshed commands, agents, plugins, and MCP server status after reload."""

    commands: list[ClaudeCodeCommandInfo]
    """List of available slash commands."""

    agents: list[ClaudeCodeAgentInfo]
    """List of available subagents."""

    plugins: list[PluginInfo]
    mcp_servers: list[McpServerStatusEntry]
    error_count: int
    held: bool | None = None
    """True when the reload was held back because of cache impact."""
    cache_impact: ReloadPluginsCacheImpact | None = None


class SDKControlMcpReconnectRequest(_ControlBase):
    """Reconnects a disconnected or failed MCP server."""

    subtype: Literal["mcp_reconnect"] = "mcp_reconnect"
    server_name: str = Field(serialization_alias="serverName")


class SDKControlMcpToggleRequest(_ControlBase):
    """Enables or disables an MCP server."""

    subtype: Literal["mcp_toggle"] = "mcp_toggle"
    server_name: str = Field(serialization_alias="serverName")
    enabled: bool


class SDKControlChannelEnableRequest(_ControlBase):
    """Enables MCP channel notifications for a marketplace plugin server."""

    subtype: Literal["channel_enable"] = "channel_enable"
    server_name: str = Field(serialization_alias="serverName")


class SDKControlEndSessionRequest(_ControlBase):
    """Ends the current session."""

    subtype: Literal["end_session"] = "end_session"


class SDKControlRenameSessionRequest(_ControlBase):
    """Sets the user-facing title for the current session."""

    subtype: Literal["rename_session"] = "rename_session"
    title: str
    source: Literal["remote", "host"] | None = None
    session_id: str | None = None


class SDKControlGenerateSessionTitleRequest(_ControlBase):
    """Generates a title for a session from a description of it."""

    subtype: Literal["generate_session_title"] = "generate_session_title"
    description: str
    """Text to title, e.g. the conversation's latest user and assistant text."""
    persist: bool | None = None
    """Store the title as the current session's title. A session that has one already
    (the CLI titles new sessions itself) returns it instead of generating another."""


class SDKControlMcpAuthenticateRequest(_ControlBase):
    """Authenticates with an MCP server."""

    subtype: Literal["mcp_authenticate"] = "mcp_authenticate"
    server_name: str


class SDKControlMcpClearAuthRequest(_ControlBase):
    """Clears authentication for an MCP server."""

    subtype: Literal["mcp_clear_auth"] = "mcp_clear_auth"
    server_name: str


class SDKControlMcpOAuthCallbackUrlRequest(_ControlBase):
    """Provides an OAuth redirect callback URL to complete an MCP server OAuth flow.

    Sent by the SDK to the CLI with the full redirect URL (containing the
    authorization code) after the user completes browser-based OAuth.
    """

    subtype: Literal["mcp_oauth_callback_url"] = "mcp_oauth_callback_url"
    server_name: str
    callback_url: str


class SDKControlRemoteControlRequest(_ControlBase):
    """Toggles the remote control REPL bridge for external session access.

    When enabled, starts a bridge that allows remote clients to send prompts,
    permission responses, interrupts, and model changes into the session.
    The response includes ``session_url``, ``connect_url``, and
    ``environment_id`` when enabling.
    """

    subtype: Literal["remote_control"] = "remote_control"
    enabled: bool = False


class RemoteControlResponse(BaseModel):
    """Response from enabling remote control.

    Contains the URLs and identifiers needed for remote clients to connect
    to the session.
    """

    session_url: str
    """URL for the remote control session."""

    connect_url: str
    """URL for remote clients to connect to the session."""

    environment_id: str
    """Identifier for the environment hosting the session."""


class McpAuthenticateResponse(ClaudeCodeBaseModel):
    """Response from authenticating with an MCP server."""

    auth_url: str | None = None
    """OAuth authorization URL for the user to visit, if user action is required."""

    requires_user_action: bool
    """Whether the user needs to complete an OAuth flow in the browser."""


class ClaudeOAuthWaitForCompletionResponse(ClaudeCodeBaseModel):
    """Response from waiting for a Claude OAuth flow to complete."""

    account: ClaudeCodeAccountInfo
    """Authenticated account details."""


class SideQuestionResponse(ClaudeCodeBaseModel):
    """Response from a side question."""

    response: str | None = None
    """The model's answer, or None if no context was available."""


class AppliedSettings(BaseModel):
    """The currently applied model and effort settings."""

    model: ModelName | str
    """The active model identifier."""

    effort: EffortLevel | None = None
    """The active effort level, or None if not set."""


class SettingsSource(BaseModel):
    """A single settings source with its raw settings."""

    source: str
    """The source name (e.g. 'user', 'project', 'flagSettings')."""

    settings: dict[str, Any]
    """The raw settings from this source."""


class GetSettingsResponse(BaseModel):
    """Response from get_settings() containing effective and per-source settings."""

    effective: dict[str, Any]
    """The merged effective settings (ClaudeCodeSettings shape, camelCase keys)."""

    sources: list[SettingsSource]
    """Raw settings from each source."""

    applied: AppliedSettings
    """The currently applied model and effort."""


class SDKControlElicitationRequest(_ControlBase):
    """Requests the SDK consumer to handle an MCP elicitation (user input request)."""

    subtype: Literal["elicitation"] = "elicitation"
    mcp_server_name: str
    """Name of the MCP server requesting elicitation."""
    message: str
    """Message to display to the user."""
    mode: ElicitationMode | None = None
    """Elicitation mode: 'form' for structured input, 'url' for browser-based auth."""
    url: str | None = None
    """URL to open (only for 'url' mode)."""
    elicitation_id: str | None = None
    """Elicitation ID for correlating URL elicitations with completion notifications."""
    requested_schema: dict[str, Any] | None = None
    """JSON Schema for the requested input (only for 'form' mode)."""
    title: str | None = None
    """Permission-display title from the MCP server's _meta['anthropic/permissionDisplay'].

    Mirrors can_use_tool.title so SDK consumers can render elicitation-driven permission prompts
    with structured headers instead of parsing `message`.
    """
    display_name: str | None = None
    """Short tool/server label from `_meta['anthropic/permissionDisplay'].displayName`."""
    description: str | None = None
    """Permission-display description from `_meta['anthropic/permissionDisplay'].description`."""

    def to_mcp(self) -> mcp.types.ElicitRequestParams:
        """Convert to the corresponding MCP elicitation request params.

        Built from the wire format (camelCase keys, ``_meta``), which both
        mcp 1.x and 2.x accept, so this works on either major.
        """
        from mcp.types import ElicitRequestFormParams, ElicitRequestURLParams

        meta = {
            "anthropic/permissionDisplay": {
                "title": self.title,
                "displayName": self.display_name,
                "description": self.description,
            }
        }
        match self.mode:
            case "url":
                assert self.url is not None
                assert self.elicitation_id is not None
                return ElicitRequestURLParams.model_validate(
                    {
                        "mode": "url",
                        "message": self.message,
                        "url": self.url,
                        "elicitationId": self.elicitation_id,
                        "_meta": meta,
                    }
                )
            case "form":
                assert self.requested_schema is not None
                return ElicitRequestFormParams.model_validate(
                    {
                        "mode": "form",
                        "message": self.message,
                        "requestedSchema": self.requested_schema,
                        "_meta": meta,
                    }
                )
            case None:
                raise ValueError("mode must be 'url' or 'form'")
            case _ as unreachable:
                assert_never(unreachable)

    @classmethod
    def from_mcp(
        cls,
        params: mcp.types.ElicitRequestParams,
        mcp_server_name: str,
    ) -> SDKControlElicitationRequest:
        """Create from MCP elicitation request params (mcp 1.x or 2.x)."""
        wire = params.model_dump(by_alias=True, mode="json", exclude_none=True)
        display = (wire.get("_meta") or {}).get("anthropic/permissionDisplay") or {}
        common: dict[str, Any] = {
            "mcp_server_name": mcp_server_name,
            "message": wire["message"],
            "title": display.get("title"),
            "display_name": display.get("displayName"),
            "description": display.get("description"),
        }
        match wire:
            case {"url": str() as url, "elicitationId": str() as elicitation_id}:
                return cls(**common, mode="url", url=url, elicitation_id=elicitation_id)
            case {"requestedSchema": dict() as schema}:
                return cls(**common, mode="form", requested_schema=schema)
            case _:
                raise ValueError(f"Unsupported elicitation params: {sorted(wire)}")


class SDKControlGetContextUsageRequest(_ControlBase):
    """Requests a breakdown of current context window usage by category."""

    subtype: Literal["get_context_usage"] = "get_context_usage"
    detail: Literal["summary", "full"] | None = None


class SDKControlGetSessionCostRequest(_ControlBase):
    """Requests the formatted session cost summary (the same text as /usage)."""

    subtype: Literal["get_session_cost"] = "get_session_cost"


class SDKControlGetSettingsRequest(_ControlBase):
    """Returns the effective merged settings and the raw per-source settings."""

    subtype: Literal["get_settings"] = "get_settings"


class SDKControlSetProactiveRequest(_ControlBase):
    """Sets proactive mode configuration."""

    subtype: Literal["set_proactive"] = "set_proactive"


class SDKControlSetColorRequest(_ControlBase):
    """Sets the session accent color. Accepts an agent color name or "default" to reset."""

    subtype: Literal["set_color"] = "set_color"
    color: str


class SDKControlClaudeOAuthWaitForCompletionRequest(_ControlBase):
    """Waits for an in-progress Claude OAuth flow to complete.

    Unlike ``claude_oauth_callback``, this does not provide an authorization
    code — it simply waits for the existing OAuth flow (started by
    ``claude_authenticate``) to finish.  The response contains the
    authenticated account details.
    """

    subtype: Literal["claude_oauth_wait_for_completion"] = "claude_oauth_wait_for_completion"


class SDKControlSideQuestionRequest(_ControlBase):
    """Sends a side question to the model using the current conversation context.

    This allows the SDK consumer to ask the model a question without adding
    it to the main conversation history.  The CLI executes the question
    against the current context and returns the model's response.
    """

    subtype: Literal["side_question"] = "side_question"
    question: str


class SDKControlRequestUserDialogRequest(_ControlBase):
    """Requests the SDK consumer to render a tool-driven blocking dialog + return user choice."""

    subtype: Literal["request_user_dialog"] = "request_user_dialog"
    dialog_kind: str
    payload: dict[str, Any]
    tool_use_id: str | None = None


class SDKControlFileSuggestionsRequest(_ControlBase):
    """Requests at-mention file autocomplete suggestions for a partial path prefix.

    Returns the same fuzzy-matched results the TUI shows.
    """

    subtype: Literal["file_suggestions"] = "file_suggestions"
    query: str


class SDKControlReadFileRequest(_ControlBase):
    """Read a file from the session filesystem for the remote sidebar viewer.

    Path is resolved against cwd and gated by the same read-permission rules as the Read tool.
    """

    subtype: Literal["read_file"] = "read_file"
    path: str
    max_bytes: int | None = None
    encoding: Literal["utf-8", "base64"] | None = None


class SDKControlReadFileResponse(_ControlBase):
    """File contents for the remote sidebar viewer."""

    contents: str
    abs_path: str
    truncated: bool | None = None
    encoding: Literal["base64"] | None = None
    lossy: bool | None = None
    """True when non-UTF-8 bytes were replaced while decoding."""
    model_config = ConfigDict(alias_generator=to_camel)


class SDKControlBackgroundTasksRequest(_ControlBase):
    """Moves running foreground tasks (or one tool use) to the background."""

    subtype: Literal["background_tasks"] = "background_tasks"
    tool_use_id: str | None = None


class SDKControlGetTaskOutputRequest(_ControlBase):
    """Reads the output collected so far for a background task."""

    subtype: Literal["get_task_output"] = "get_task_output"
    task_id: str


class SDKControlGetTaskOutputResponse(BaseModel):
    """Output of a background task."""

    output: str
    total_bytes: int
    truncated: bool


class SDKControlGetUsageRequest(_ControlBase):
    """Requests the structured usage report (session cost + rate limits). Experimental."""

    subtype: Literal["get_usage"] = "get_usage"
    skip_behaviors: bool | None = None


class SDKControlGetUsageResponse(ClaudeCodeBaseModel):
    """Structured /usage data: session totals and plan rate-limit windows. Experimental."""

    session: UsageReportSession
    """Cost and usage accumulated by the current session."""
    subscription_type: str | None
    """claude.ai plan (e.g. "pro", "max"), None without a subscription."""
    rate_limits_available: bool
    """False when plan limits do not apply (API key, Bedrock, Vertex, ...)."""
    rate_limits: UsageRateLimits | None
    behaviors: dict[str, Any] | None = None
    """What contributes to usage, from a scan of local transcripts (None if skipped)."""


class SDKControlGetBinaryVersionRequest(_ControlBase):
    """Requests the version of the running Claude Code binary."""

    subtype: Literal["get_binary_version"] = "get_binary_version"


class SDKControlListModelsRequest(_ControlBase):
    """Requests the list of available models."""

    subtype: Literal["list_models"] = "list_models"


class SDKControlReloadSkillsRequest(_ControlBase):
    """Re-scans skills from disk."""

    subtype: Literal["reload_skills"] = "reload_skills"


class SDKControlReloadSkillsResponse(BaseModel):
    """Skills after reload."""

    skills: list[ClaudeCodeCommandInfo]


class SDKControlReloadOutputStylesRequest(_ControlBase):
    """Re-scans output styles from disk."""

    subtype: Literal["reload_output_styles"] = "reload_output_styles"


class SDKControlReloadOutputStylesResponse(BaseModel):
    """Output styles after reload."""

    available_output_styles: list[str]


class SDKControlMcpReadResourceRequest(_ControlBase):
    """Reads a resource from a connected MCP server."""

    subtype: Literal["mcp_read_resource"] = "mcp_read_resource"
    server_name: str = Field(serialization_alias="serverName")
    uri: str


class McpResourceContents(BaseModel):
    """A single resource content entry."""

    model_config = ConfigDict(populate_by_name=True)

    uri: str
    mime_type: str | None = Field(default=None, alias="mimeType")
    text: str | None = None
    blob: str | None = None
    meta: dict[str, Any] | None = Field(default=None, alias="_meta")


class SDKControlMcpReadResourceResponse(BaseModel):
    """Contents of an MCP resource."""

    contents: list[McpResourceContents]


class SDKControlUpdateSettingsRequest(_ControlBase):
    """Writes settings to the local or user settings file."""

    subtype: Literal["update_settings"] = "update_settings"
    source: Literal["localSettings", "userSettings"]
    settings: dict[str, Any]


class SDKControlListPermissionRulesRequest(_ControlBase):
    """Lists the effective permission rules."""

    subtype: Literal["list_permission_rules"] = "list_permission_rules"


class SDKControlRegisterRepoRootRequest(_ControlBase):
    """Registers an additional repository root (like /add-dir)."""

    subtype: Literal["register_repo_root"] = "register_repo_root"
    directory: str
    reload_claude_md: bool | None = None
    reload_plugins: bool | None = None
    reload_skills: bool | None = None


class SDKControlGetHooksListingRequest(_ControlBase):
    """Requests the listing of configured hooks (same data as /hooks)."""

    subtype: Literal["get_hooks_listing"] = "get_hooks_listing"


class SDKControlSetHasSubscribersRequest(_ControlBase):
    """Tells the CLI whether anyone is watching the session output."""

    subtype: Literal["set_has_subscribers"] = "set_has_subscribers"
    has_subscribers: bool | None


class SDKControlMcpCallRequest(_ControlBase):
    """Invokes an MCP tool via the subprocess MCP client without a model turn.

    No permission check (control channel is trusted, same as other subtypes).
    SDK-type MCP servers (config.type === "sdk") are rejected — they are caller-provided,
    so the caller can invoke them directly without the subprocess round-trip.
    Result content passes through the same processing as model-turn MCP calls.
    Session expiry is not retried automatically; callers can mcp_reconnect and retry.
    UrlElicitationRequired (-32042) tries Elicitation hooks;
    if no hook resolves, the call errors with the URL in the message
    — open it out-of-band, then retry mcp_call.
    """

    subtype: Literal["mcp_call"] = "mcp_call"
    tool: str
    arguments: dict[str, Any] | None = None


IncomingControlRequest = Annotated[
    SDKControlPermissionRequest
    | SDKHookCallbackRequest
    | SDKControlMcpMessageRequest
    | SDKControlElicitationRequest,
    Discriminator("subtype"),
]

OutgoingControlRequest = Annotated[
    SDKControlInterruptRequest
    | SDKControlInitializeRequest
    | SDKControlSetPermissionModeRequest
    | SDKControlSetModelRequest
    | SDKControlSetMaxThinkingTokensRequest
    | SDKControlMcpStatusRequest
    | SDKControlMcpSetServersRequest
    | SDKControlReloadPluginsRequest
    | SDKControlMcpReconnectRequest
    | SDKControlMcpToggleRequest
    | SDKControlChannelEnableRequest
    | SDKControlRenameSessionRequest
    | SDKControlGenerateSessionTitleRequest
    | SDKControlEndSessionRequest
    | SDKControlMcpAuthenticateRequest
    | SDKControlMcpClearAuthRequest
    | SDKControlFileSuggestionsRequest
    | SDKControlMcpOAuthCallbackUrlRequest
    | SDKControlRemoteControlRequest
    | SDKControlSetProactiveRequest
    | SDKControlClaudeOAuthWaitForCompletionRequest
    | SDKControlSideQuestionRequest
    | SDKControlStopTaskRequest
    | SDKControlApplyFlagSettingsRequest
    | SDKControlGetContextUsageRequest
    | SDKControlGetSessionCostRequest
    | SDKControlGetSettingsRequest
    | SDKControlRewindFilesRequest
    | SDKControlCancelAsyncMessageRequest
    | SDKControlSeedReadStateRequest
    | SDKControlReadFileRequest
    | SDKControlMcpCallRequest
    | SDKControlBackgroundTasksRequest
    | SDKControlGetTaskOutputRequest
    | SDKControlGetUsageRequest
    | SDKControlGetBinaryVersionRequest
    | SDKControlListModelsRequest
    | SDKControlReloadSkillsRequest
    | SDKControlReloadOutputStylesRequest
    | SDKControlMcpReadResourceRequest
    | SDKControlUpdateSettingsRequest
    | SDKControlListPermissionRulesRequest
    | SDKControlRegisterRepoRootRequest
    | SDKControlGetHooksListingRequest
    | SDKControlSetHasSubscribersRequest,
    Discriminator("subtype"),
]

ControlRequestUnion = Annotated[
    IncomingControlRequest | OutgoingControlRequest,
    Discriminator("subtype"),
]

incoming_control_request_adapter = TypeAdapter[IncomingControlRequest](IncomingControlRequest)


class SDKControlRequest(_ControlBase):
    """SDK control request."""

    type: Literal["control_request"]
    request_id: str
    request: ControlRequestUnion


class SDKControlCancelRequest(_ControlBase):
    """Cancels a currently open control request."""

    type: Literal["control_cancel_request"]
    request_id: str


class ControlResponse(TypedDict):
    """Control response."""

    subtype: Literal["success"]
    request_id: str
    response: dict[str, Any] | None


class ControlErrorResponse(TypedDict):
    """Control Error response."""

    subtype: Literal["error"]
    request_id: str
    error: str


class SDKControlResponse(TypedDict):
    """SDK Control response."""

    type: Literal["control_response"]
    response: ControlResponse | ControlErrorResponse
