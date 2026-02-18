"""MCP server and plugin configuration types."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, NotRequired, TypedDict


if TYPE_CHECKING:
    from mcp.server import Server as McpServer


RequestId = str | int
JSONRPC_VERSION = "2.0"


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
    params: NotRequired[dict[str, object]]


class JSONRPCNotification(TypedDict):
    """A JSON-RPC notification which does not expect a response."""

    jsonrpc: str
    method: str
    params: NotRequired[dict[str, object]]


class JSONRPCResultResponse(TypedDict):
    """A successful (non-error) response to a request."""

    jsonrpc: str
    id: RequestId
    result: dict[str, object]


class JSONRPCErrorResponse(TypedDict):
    """A response to a request that indicates an error occurred."""

    jsonrpc: str
    id: NotRequired[RequestId]
    error: JSONRPCError


JSONRPCResponse = JSONRPCResultResponse | JSONRPCErrorResponse

JSONRPCMessage = JSONRPCRequest | JSONRPCNotification | JSONRPCResponse


# MCP Server config
class McpStdioServerConfig(TypedDict):
    """MCP stdio server configuration."""

    type: NotRequired[Literal["stdio"]]  # Optional for backwards compatibility
    command: str
    args: NotRequired[list[str]]
    env: NotRequired[dict[str, str]]


class McpSSEServerConfig(TypedDict):
    """MCP SSE server configuration."""

    type: Literal["sse"]
    url: str
    headers: NotRequired[dict[str, str]]


class McpHttpServerConfig(TypedDict):
    """MCP HTTP server configuration."""

    type: Literal["http"]
    url: str
    headers: NotRequired[dict[str, str]]


class McpSdkServerConfig(TypedDict):
    """SDK MCP server configuration."""

    type: Literal["sdk"]
    name: str
    instance: McpServer


ExternalMcpServerConfig = McpStdioServerConfig | McpSSEServerConfig | McpHttpServerConfig

McpServerConfig = (
    McpStdioServerConfig | McpSSEServerConfig | McpHttpServerConfig | McpSdkServerConfig
)


class SdkPluginConfig(TypedDict):
    """SDK plugin configuration.

    Currently only local plugins are supported via the 'local' type.
    """

    type: Literal["local"]
    path: str
