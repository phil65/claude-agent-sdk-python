"""SDK control protocol types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, Literal, TypedDict

from pydantic import Discriminator, TypeAdapter

from clawd_code_sdk.models.agents import AgentDefinition  # noqa: TC001
from clawd_code_sdk.models.base import ElicitationMode, PermissionMode  # noqa: TC001
from clawd_code_sdk.models.hooks import HookEvent, HookInput  # noqa: TC001
from clawd_code_sdk.models.mcp import ExternalMcpServerConfig, JSONRPCMessage  # noqa: TC001


# SDK Control Protocol
@dataclass(frozen=True, slots=True, kw_only=True)
class SDKControlInterruptRequest:
    """SDK control interrupt request."""

    subtype: Literal["interrupt"] = "interrupt"


@dataclass(frozen=True, slots=True, kw_only=True)
class SDKControlPermissionRequest:
    """SDK control permission request."""

    subtype: Literal["can_use_tool"] = "can_use_tool"
    tool_name: str
    input: dict[str, Any]
    tool_use_id: str
    permission_suggestions: list[Any] | None = None
    blocked_path: str | None = None
    decision_reason: str | None = None
    agent_id: str | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class SDKControlInitializeRequest:
    """SDK control initialize request."""

    subtype: Literal["initialize"] = "initialize"
    hooks: dict[HookEvent, Any] | None = None
    agents: dict[str, AgentDefinition] | None = None
    sdk_mcp_servers: list[str] | None = None
    system_prompt: str | None = None
    append_system_prompt: str | None = None
    json_schema: dict[str, Any] | None = None
    prompt_suggestions: bool | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class SDKControlSetPermissionModeRequest:
    """SDK control set permission mode request."""

    subtype: Literal["set_permission_mode"] = "set_permission_mode"
    mode: PermissionMode


@dataclass(frozen=True, slots=True, kw_only=True)
class SDKHookCallbackRequest:
    """SDK hook callback request."""

    subtype: Literal["hook_callback"] = "hook_callback"
    callback_id: str
    input: HookInput
    tool_use_id: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class SDKControlMcpMessageRequest:
    """SDK control MCP message request."""

    subtype: Literal["mcp_message"] = "mcp_message"
    server_name: str
    message: JSONRPCMessage


@dataclass(frozen=True, slots=True, kw_only=True)
class SDKControlRewindFilesRequest:
    """SDK control rewind files request."""

    subtype: Literal["rewind_files"] = "rewind_files"
    user_message_id: str
    dry_run: bool | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class SDKControlStopTaskRequest:
    """SDK control stop task request."""

    subtype: Literal["stop_task"] = "stop_task"
    task_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SDKControlApplyFlagSettingsRequest:
    """SDK control apply flag settings request."""

    subtype: Literal["apply_flag_settings"] = "apply_flag_settings"
    settings: dict[str, Any]


@dataclass(frozen=True, slots=True, kw_only=True)
class SDKControlSetModelRequest:
    """Sets the model to use for subsequent conversation turns."""

    subtype: Literal["set_model"] = "set_model"
    model: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class SDKControlSetMaxThinkingTokensRequest:
    """Sets the maximum number of thinking tokens for extended thinking."""

    subtype: Literal["set_max_thinking_tokens"] = "set_max_thinking_tokens"
    max_thinking_tokens: int | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class SDKControlMcpStatusRequest:
    """Requests the current status of all MCP server connections."""

    subtype: Literal["mcp_status"] = "mcp_status"


@dataclass(frozen=True, slots=True, kw_only=True)
class SDKControlMcpSetServersRequest:
    """Replaces the set of dynamically managed MCP servers."""

    subtype: Literal["mcp_set_servers"] = "mcp_set_servers"
    servers: dict[str, ExternalMcpServerConfig]


@dataclass(frozen=True, slots=True, kw_only=True)
class SDKControlMcpReconnectRequest:
    """Reconnects a disconnected or failed MCP server."""

    subtype: Literal["mcp_reconnect"] = "mcp_reconnect"
    server_name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SDKControlMcpToggleRequest:
    """Enables or disables an MCP server."""

    subtype: Literal["mcp_toggle"] = "mcp_toggle"
    server_name: str
    enabled: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class SDKControlMcpAuthenticateRequest:
    """Authenticates with an MCP server."""

    subtype: Literal["mcp_authenticate"] = "mcp_authenticate"
    server_name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SDKControlMcpClearAuthRequest:
    """Clears authentication for an MCP server."""

    subtype: Literal["mcp_clear_auth"] = "mcp_clear_auth"
    server_name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SDKControlMcpOAuthCallbackUrlRequest:
    """Provides an OAuth redirect callback URL to complete an MCP server OAuth flow.

    Sent by the SDK to the CLI with the full redirect URL (containing the
    authorization code) after the user completes browser-based OAuth.
    """

    subtype: Literal["mcp_oauth_callback_url"] = "mcp_oauth_callback_url"
    server_name: str
    callback_url: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SDKControlRemoteControlRequest:
    """Toggles the remote control REPL bridge for external session access.

    When enabled, starts a bridge that allows remote clients to send prompts,
    permission responses, interrupts, and model changes into the session.
    The response includes ``session_url``, ``connect_url``, and
    ``environment_id`` when enabling.
    """

    subtype: Literal["remote_control"] = "remote_control"
    enabled: bool = False


@dataclass(frozen=True, slots=True, kw_only=True)
class SDKControlElicitationRequest:
    """Requests the SDK consumer to handle an MCP elicitation (user input request)."""

    subtype: Literal["elicitation"] = "elicitation"
    mcp_server_name: str
    message: str
    mode: ElicitationMode | None = None
    url: str | None = None
    elicitation_id: str | None = None
    requested_schema: dict[str, Any] | None = None


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
    | SDKControlMcpSetServersRequest
    | SDKControlMcpReconnectRequest
    | SDKControlMcpToggleRequest
    | SDKControlMcpAuthenticateRequest
    | SDKControlMcpClearAuthRequest
    | SDKControlMcpOAuthCallbackUrlRequest
    | SDKControlRemoteControlRequest
    | SDKControlStopTaskRequest
    | SDKControlApplyFlagSettingsRequest
    | SDKControlElicitationRequest,
    Discriminator("subtype"),
]

control_request_adapter: TypeAdapter[ControlRequestUnion] = TypeAdapter(ControlRequestUnion)


@dataclass(frozen=True, slots=True)
class SDKControlRequest:
    """SDK control request."""

    type: Literal["control_request"]
    request_id: str
    request: ControlRequestUnion


@dataclass(frozen=True, slots=True)
class SDKControlCancelRequest:
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
