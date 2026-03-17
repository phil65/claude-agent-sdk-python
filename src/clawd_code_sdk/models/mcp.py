"""MCP server and plugin configuration types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, NotRequired, TypedDict

from pydantic import Field

from clawd_code_sdk.models.base import ClaudeCodeBaseModel


if TYPE_CHECKING:
    from mcp.server import Server as McpServer


RequestId = str | int

McpConnectionStatus = Literal["connected", "pending", "failed", "needs-auth", "disabled"]


# JSON-RPC types (from MCP specification)


class JSONRPCError(TypedDict):
    """A JSON-RPC error object."""

    code: int
    message: str
    data: NotRequired[object]


class JSONRPCRequest(TypedDict):
    """A JSON-RPC request that expects a response."""

    jsonrpc: str
    id: RequestId
    method: str
    params: NotRequired[dict[str, Any]]


class JSONRPCNotification(TypedDict):
    """A JSON-RPC notification which does not expect a response."""

    jsonrpc: str
    method: str
    params: NotRequired[dict[str, Any]]


class JSONRPCResultResponse(TypedDict):
    """A successful (non-error) response to a request."""

    jsonrpc: str
    id: RequestId
    result: dict[str, Any]


class JSONRPCErrorResponse(TypedDict):
    """A response to a request that indicates an error occurred."""

    jsonrpc: str
    id: NotRequired[RequestId]
    error: JSONRPCError


JSONRPCResponse = JSONRPCResultResponse | JSONRPCErrorResponse

JSONRPCMessage = JSONRPCRequest | JSONRPCNotification | JSONRPCResponse


# MCP Server config


@dataclass(kw_only=True)
class McpStdioServerConfig:
    """MCP stdio server configuration."""

    type: Literal["stdio"] = "stdio"
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


@dataclass(kw_only=True)
class McpSSEServerConfig:
    """MCP SSE server configuration."""

    type: Literal["sse"] = "sse"
    url: str
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(kw_only=True)
class McpHttpServerConfig:
    """MCP HTTP server configuration."""

    type: Literal["http"] = "http"
    url: str
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(kw_only=True)
class McpSdkServerConfig:
    """SDK MCP server configuration (serializable, no instance)."""

    type: Literal["sdk"] = "sdk"
    name: str


@dataclass(kw_only=True)
class McpSdkServerConfigWithInstance(McpSdkServerConfig):
    """SDK MCP server config with a live McpServer instance. Not serializable."""

    instance: McpServer = field(repr=False)


ExternalMcpServerConfig = McpStdioServerConfig | McpSSEServerConfig | McpHttpServerConfig
McpServerConfig = (
    McpStdioServerConfig | McpSSEServerConfig | McpHttpServerConfig | McpSdkServerConfigWithInstance
)


@dataclass(kw_only=True)
class McpClaudeAIProxyServerConfig:
    """MCP Claude AI proxy server configuration."""

    type: Literal["claudeai-proxy"] = "claudeai-proxy"
    url: str
    id: str


McpServerConfigForProcessTransport = (
    McpStdioServerConfig | McpSSEServerConfig | McpHttpServerConfig | McpSdkServerConfig
)

McpServerStatusConfig = McpServerConfigForProcessTransport | McpClaudeAIProxyServerConfig


class McpSetServersResult(ClaudeCodeBaseModel):
    """Result of a setMcpServers operation."""

    added: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    errors: dict[str, str] = Field(default_factory=dict)


class SdkPluginConfig(ClaudeCodeBaseModel):
    """SDK plugin configuration.

    Currently only local plugins are supported via the 'local' type.
    """

    type: Literal["local"] = "local"
    path: str


# Pydantic models for MCP status responses


class ToolAnnotations(ClaudeCodeBaseModel):
    """Additional properties describing a Tool to clients."""

    # title: str | None = None
    # """A human-readable title for the tool."""

    read_only: bool | None = None
    """Read-only hint."""

    destructive: bool | None = None
    """Destructive hint."""

    # idempotent: bool | None = None
    # """Idempodent hint."""

    open_world: bool | None = None
    """Open-world hint."""


class McpToolStatus(ClaudeCodeBaseModel):
    """Status information for a single MCP tool."""

    name: str
    description: str | None = None
    annotations: ToolAnnotations = Field(default_factory=ToolAnnotations)


class McpServerVersionInfo(ClaudeCodeBaseModel):
    """Server version information returned in MCP status."""

    name: str
    version: str


class McpServerStatusEntry(ClaudeCodeBaseModel):
    """Status information for a single MCP server."""

    name: str
    status: McpConnectionStatus
    server_info: McpServerVersionInfo | None = None
    error: str | None = None
    config: McpServerStatusConfig | None = None
    scope: Literal["project", "user", "local", "claudeai", "managed"] | str | None = None  # noqa: PYI051
    tools: list[McpToolStatus] = Field(default_factory=list)


class McpStatusResponse(ClaudeCodeBaseModel):
    """Response from get_mcp_status() containing all MCP server statuses."""

    mcp_servers: list[McpServerStatusEntry] = Field(default_factory=list)
