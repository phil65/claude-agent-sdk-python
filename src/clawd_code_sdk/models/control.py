"""SDK control protocol types."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, Literal, TypedDict, assert_never

from pydantic import BaseModel, ConfigDict, Discriminator, Field, TypeAdapter

from clawd_code_sdk.models.agents import AgentWireDefinition
from clawd_code_sdk.models.base import (
    ClaudeCodeBaseModel,
    EffortLevel,
    ElicitationMode,
    ModelName,
    PermissionMode,
)
from clawd_code_sdk.models.hooks import HookEvent, HookInput
from clawd_code_sdk.models.mcp import ExternalMcpServerConfig, JSONRPCMessage
from clawd_code_sdk.models.permissions import PermissionUpdate
from clawd_code_sdk.models.server_info import ClaudeCodeAccountInfo


if TYPE_CHECKING:
    import mcp.types


class _ControlBase(BaseModel):
    """Frozen base for all SDK control request models."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)


# SDK Control Protocol
class SDKControlInterruptRequest(_ControlBase):
    """SDK control interrupt request."""

    subtype: Literal["interrupt"] = "interrupt"


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


class SDKControlInitializeRequest(_ControlBase):
    """SDK control initialize request."""

    subtype: Literal["initialize"] = "initialize"
    hooks: dict[HookEvent, Any] | None = None
    agents: dict[str, AgentWireDefinition] | None = None
    sdk_mcp_servers: list[str] | None = Field(default=None, serialization_alias="sdkMcpServers")
    system_prompt: str | None = Field(default=None, serialization_alias="systemPrompt")
    append_system_prompt: str | None = Field(default=None, serialization_alias="appendSystemPrompt")
    json_schema: dict[str, Any] | None = Field(default=None, serialization_alias="jsonSchema")
    prompt_suggestions: bool | None = Field(default=None, serialization_alias="promptSuggestions")
    agent_progress_summaries: bool | None = Field(
        default=None, serialization_alias="agentProgressSummaries"
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


class SDKControlMcpStatusRequest(_ControlBase):
    """Requests the current status of all MCP server connections."""

    subtype: Literal["mcp_status"] = "mcp_status"


class SDKControlMcpSetServersRequest(_ControlBase):
    """Replaces the set of dynamically managed MCP servers."""

    subtype: Literal["mcp_set_servers"] = "mcp_set_servers"
    servers: dict[str, ExternalMcpServerConfig]


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

    def to_mcp(self) -> mcp.types.ElicitRequestParams:
        """Convert to the corresponding MCP elicitation request params."""
        from mcp.types import ElicitRequestFormParams, ElicitRequestURLParams

        match self.mode:
            case "url":
                assert self.url is not None
                assert self.elicitation_id is not None
                return ElicitRequestURLParams(
                    message=self.message,
                    url=self.url,
                    elicitationId=self.elicitation_id,
                )
            case "form":
                assert self.requested_schema is not None
                return ElicitRequestFormParams(
                    message=self.message,
                    requestedSchema=self.requested_schema,
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
        """Create from MCP elicitation request params."""
        from mcp.types import ElicitRequestFormParams, ElicitRequestURLParams

        match params:
            case ElicitRequestURLParams(url=url, message=message, elicitationId=id_):
                return cls(
                    mcp_server_name=mcp_server_name,
                    message=message,
                    mode="url",
                    url=url,
                    elicitation_id=id_,
                )
            case ElicitRequestFormParams(message=message, requestedSchema=schema):
                return cls(
                    mcp_server_name=mcp_server_name,
                    message=message,
                    mode="form",
                    requested_schema=dict(schema),
                )
            case _ as unreachable:
                assert_never(unreachable)


class SDKControlGetSettingsRequest(_ControlBase):
    """Returns the effective merged settings and the raw per-source settings."""

    subtype: Literal["get_settings"] = "get_settings"


class SDKControlSetProactiveRequest(_ControlBase):
    """Sets proactive mode configuration."""

    subtype: Literal["set_proactive"] = "set_proactive"


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


ControlRequestUnion = Annotated[
    SDKControlInterruptRequest
    | SDKControlPermissionRequest
    | SDKControlInitializeRequest
    | SDKControlSetPermissionModeRequest
    | SDKControlSetModelRequest
    | SDKControlSetMaxThinkingTokensRequest
    | SDKControlMcpStatusRequest
    | SDKHookCallbackRequest
    | SDKControlMcpMessageRequest
    | SDKControlRewindFilesRequest
    | SDKControlCancelAsyncMessageRequest
    | SDKControlSeedReadStateRequest
    | SDKControlMcpSetServersRequest
    | SDKControlMcpReconnectRequest
    | SDKControlMcpToggleRequest
    | SDKControlChannelEnableRequest
    | SDKControlEndSessionRequest
    | SDKControlMcpAuthenticateRequest
    | SDKControlMcpClearAuthRequest
    | SDKControlMcpOAuthCallbackUrlRequest
    | SDKControlRemoteControlRequest
    | SDKControlSetProactiveRequest
    | SDKControlClaudeOAuthWaitForCompletionRequest
    | SDKControlSideQuestionRequest
    | SDKControlStopTaskRequest
    | SDKControlApplyFlagSettingsRequest
    | SDKControlGetSettingsRequest
    | SDKControlElicitationRequest,
    Discriminator("subtype"),
]

control_request_adapter = TypeAdapter[ControlRequestUnion](ControlRequestUnion)


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
