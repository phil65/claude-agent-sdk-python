"""SDK control protocol types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, Literal, TypedDict

from pydantic import Discriminator, TypeAdapter

from .agents import AgentDefinition  # noqa: TC001
from .base import PermissionMode  # noqa: TC001
from .hooks import HookEvent, HookInput  # noqa: TC001
from .mcp import JSONRPCMessage  # noqa: TC001


# SDK Control Protocol
@dataclass(frozen=True, slots=True, kw_only=True)
class SDKControlInterruptRequest:
    subtype: Literal["interrupt"] = "interrupt"


@dataclass(frozen=True, slots=True, kw_only=True)
class SDKControlPermissionRequest:
    subtype: Literal["can_use_tool"] = "can_use_tool"
    tool_name: str
    input: dict[str, Any]  # TODO: Should be ToolInput, but with total=False?
    tool_use_id: str
    permission_suggestions: list[Any] | None = None
    blocked_path: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class SDKControlInitializeRequest:
    subtype: Literal["initialize"] = "initialize"
    hooks: dict[HookEvent, Any] | None = None
    agents: dict[str, AgentDefinition] | None = None
    sdk_mcp_servers: list[str] | None = None
    system_prompt: str | None = None
    append_system_prompt: str | None = None
    json_schema: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class SDKControlSetPermissionModeRequest:
    subtype: Literal["set_permission_mode"] = "set_permission_mode"
    mode: PermissionMode


@dataclass(frozen=True, slots=True, kw_only=True)
class SDKHookCallbackRequest:
    subtype: Literal["hook_callback"] = "hook_callback"
    callback_id: str
    input: HookInput
    tool_use_id: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class SDKControlMcpMessageRequest:
    subtype: Literal["mcp_message"] = "mcp_message"
    server_name: str
    message: JSONRPCMessage


@dataclass(frozen=True, slots=True, kw_only=True)
class SDKControlRewindFilesRequest:
    subtype: Literal["rewind_files"] = "rewind_files"
    user_message_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SDKControlStopTaskRequest:
    subtype: Literal["stop_task"] = "stop_task"
    task_id: str


ControlRequestUnion = Annotated[
    SDKControlInterruptRequest
    | SDKControlPermissionRequest
    | SDKControlInitializeRequest
    | SDKControlSetPermissionModeRequest
    | SDKHookCallbackRequest
    | SDKControlMcpMessageRequest
    | SDKControlRewindFilesRequest
    | SDKControlStopTaskRequest,
    Discriminator("subtype"),
]

_control_request_adapter: TypeAdapter[ControlRequestUnion] = TypeAdapter(ControlRequestUnion)


def parse_control_request(data: dict[str, Any]) -> ControlRequestUnion:
    """Parse a raw dict into a typed control request dataclass."""
    return _control_request_adapter.validate_python(data)


@dataclass(frozen=True, slots=True)
class SDKControlRequest:
    type: Literal["control_request"]
    request_id: str
    request: ControlRequestUnion


class ControlResponse(TypedDict):
    subtype: Literal["success"]
    request_id: str
    response: dict[str, Any] | None


class ControlErrorResponse(TypedDict):
    subtype: Literal["error"]
    request_id: str
    error: str


class SDKControlResponse(TypedDict):
    type: Literal["control_response"]
    response: ControlResponse | ControlErrorResponse
