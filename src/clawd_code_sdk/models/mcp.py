"""MCP server and plugin configuration types."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, NotRequired, TypedDict


if TYPE_CHECKING:
    from mcp.server import Server as McpServer


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
