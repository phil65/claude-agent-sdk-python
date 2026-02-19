"""Claude SDK for Python."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic import AnyUrl

from clawd_code_sdk.models import McpSdkServerConfig


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from mcp.types import ToolAnnotations


MMAPPING = {
    str: {"type": "string"},
    int: {"type": "integer"},
    float: {"type": "number"},
    bool: {"type": "boolean"},
}


@dataclass
class SdkMcpTool[T]:
    """Definition for an SDK MCP tool."""

    name: str
    description: str
    input_schema: type[T] | dict[str, Any]
    handler: Callable[[T], Awaitable[dict[str, Any]]]
    annotations: ToolAnnotations | None = None


def tool(
    name: str,
    description: str,
    input_schema: type | dict[str, Any],
    annotations: ToolAnnotations | None = None,
) -> Callable[[Callable[[Any], Awaitable[dict[str, Any]]]], SdkMcpTool[Any]]:
    """Decorator for defining MCP tools with type safety.

    Creates a tool that can be used with SDK MCP servers. The tool runs
    in-process within your Python application, providing better performance
    than external MCP servers.

    Args:
        name: Unique identifier for the tool. This is what Claude will use
            to reference the tool in function calls.
        description: Human-readable description of what the tool does.
            This helps Claude understand when to use the tool.
        input_schema: Schema defining the tool's input parameters.
            Can be either:
            - A dictionary mapping parameter names to types (e.g., {"text": str})
            - A TypedDict class for more complex schemas
            - A JSON Schema dictionary for full validation

    Returns:
        A decorator function that wraps the tool implementation and returns
        an SdkMcpTool instance ready for use with create_sdk_mcp_server().

    Notes:
        - The tool function must be async
        - The function receives a single dict argument with the input parameters
        - The function should return a dict with a "content" key containing the response
        - Errors can be indicated by including "is_error": True in the response
    """

    def decorator(handler: Callable[[Any], Awaitable[dict[str, Any]]]) -> SdkMcpTool[Any]:
        return SdkMcpTool(
            name=name,
            description=description,
            input_schema=input_schema,
            handler=handler,
            annotations=annotations,
        )

    return decorator


def create_sdk_mcp_server(
    name: str,
    version: str = "1.0.0",
    tools: list[SdkMcpTool[Any]] | None = None,
) -> McpSdkServerConfig:
    """Create an in-process MCP server that runs within your Python application.

    Server lifecycle is managed automatically by the SDK
    Unlike external MCP servers that run as separate processes, SDK MCP servers
    run directly in your application's process. This provides:
    - Better performance (no IPC overhead)
    - Simpler deployment (single process)
    - Easier debugging (same process)
    - Direct access to your application's state

    Args:
        name: Unique identifier for the server. This name is used to reference
            the server in the mcp_servers configuration.
        version: Server version string. Defaults to "1.0.0". This is for
            informational purposes and doesn't affect functionality.
        tools: List of SdkMcpTool instances created with the @tool decorator.
            These are the functions that Claude can call through this server.
            If None or empty, the server will have no tools (rarely useful).

    Returns:
        McpSdkServerConfig: A configuration object that can be passed to
        ClaudeAgentOptions.mcp_servers. This config contains the server
        instance and metadata needed for the SDK to route tool calls.

    Example:
        Simple calculator server:
        >>> @tool("add", "Add numbers", {"a": float, "b": float})
        ... async def add(args):
        ...     return {"content": [{"type": "text", "text": f"Sum: {args['a'] + args['b']}"}]}
        >>>
        >>> @tool("multiply", "Multiply numbers", {"a": float, "b": float})
        ... async def multiply(args):
        ...     return {"content": [{"type": "text", "text": f"Product: {args['a'] * args['b']}"}]}
        >>>
        >>> calculator = create_sdk_mcp_server(
        ...     name="calculator",
        ...     version="2.0.0",
        ...     tools=[add, multiply]
        ... )
        >>>
        >>> # Use with Claude
        >>> options = ClaudeAgentOptions(
        ...     mcp_servers={"calc": calculator},
        ...     allowed_tools=["add", "multiply"]
        ... )

        Server with application state access:
        >>> class DataStore:
        ...     def __init__(self):
        ...         self.items = []
        ...
        >>> store = DataStore()
        >>>
        >>> @tool("add_item", "Add item to store", {"item": str})
        ... async def add_item(args):
        ...     store.items.append(args["item"])
        ...     return {"content": [{"type": "text", "text": f"Added: {args['item']}"}]}
        >>>
        >>> server = create_sdk_mcp_server("store", tools=[add_item])
    """
    from mcp.server import Server
    from mcp.types import BlobResourceContents, EmbeddedResource, ImageContent, TextContent, Tool

    # Create MCP server instance
    server = Server(name, version=version)

    # Register tools if provided
    if tools:
        # Store tools for access in handlers
        tool_map = {tool_def.name: tool_def for tool_def in tools}

        # Register list_tools handler to expose available tools
        @server.list_tools()  # type: ignore[no-untyped-call,untyped-decorator]
        async def list_tools() -> list[Tool]:
            """Return the list of available tools."""
            tool_list = []
            for tool_def in tools:
                # Convert input_schema to JSON Schema format
                if isinstance(tool_def.input_schema, dict):
                    # Check if it's already a JSON schema
                    if "type" in tool_def.input_schema and "properties" in tool_def.input_schema:
                        schema = tool_def.input_schema
                    else:
                        # Simple dict mapping names to types - convert to JSON schema
                        properties = {}
                        for param_name, param_type in tool_def.input_schema.items():
                            properties[param_name] = MMAPPING.get(param_type, {"type": "string"})
                        required = list(properties.keys())
                        schema = {"type": "object", "properties": properties, "required": required}
                else:
                    # For TypedDict or other types, create basic schema
                    schema = {"type": "object", "properties": {}}
                mcp_tool = Tool(
                    name=tool_def.name,
                    description=tool_def.description,
                    inputSchema=schema,
                    annotations=tool_def.annotations,
                )
                tool_list.append(mcp_tool)
            return tool_list

        # Register call_tool handler to execute tools
        @server.call_tool()  # type: ignore[untyped-decorator]
        async def call_tool(name: str, arguments: dict[str, Any]) -> Any:
            """Execute a tool by name with given arguments."""
            if name not in tool_map:
                raise ValueError(f"Tool '{name}' not found")

            tool_def = tool_map[name]
            result = await tool_def.handler(arguments)
            # Convert result to MCP format
            # The decorator expects us to return the content, not a CallToolResult
            # It will wrap our return value in CallToolResult
            content: list[TextContent | ImageContent | EmbeddedResource] = []
            for item in result.get("content", []):
                match item:
                    case {"type": "text", "text": text}:
                        content.append(TextContent(type="text", text=text))
                    case {"type": "image", "data": data, "mimeType": mimeType}:
                        content.append(ImageContent(type="image", data=data, mimeType=mimeType))
                    case {"type": "document"}:
                        # Convert document to EmbeddedResource with BlobResourceContents
                        # This preserves document data through MCP for conversion to
                        # Anthropic document format in query.py
                        source = item.get("source", {})
                        blob = BlobResourceContents(
                            uri=AnyUrl(f"document://{source.get('type', 'base64')}"),
                            mimeType=source.get("media_type", "application/pdf"),
                            blob=source.get("data", ""),
                        )
                        content.append(EmbeddedResource(type="resource", resource=blob))

            # Return just the content list - the decorator wraps it
            return content

    # Return SDK server configuration
    return McpSdkServerConfig(type="sdk", name=name, instance=server)
