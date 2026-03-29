"""Claude SDK for Python."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, assert_never

from mcp.types import ListToolsResult
from pydantic import AnyUrl, TypeAdapter, create_model

from clawd_code_sdk.models import (
    JSONRPCError,
    JSONRPCErrorResponse,
    JSONRPCResultResponse,
    McpSdkServerConfigWithInstance,
)


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterator

    from mcp.server import Server as McpServer
    from mcp.types import ContentBlock, ToolAnnotations

    from clawd_code_sdk.models import JSONRPCMessage, JSONRPCResponse


@dataclass
class SdkMcpTool[T]:
    """Definition for an SDK MCP tool."""

    name: str
    description: str
    input_schema: type[T] | dict[str, Any]
    handler: Callable[[T], Awaitable[dict[str, Any]]]
    title: str | None = None
    annotations: ToolAnnotations | None = None
    output_schema: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None
    search_hint: str | None = None
    always_load: bool | None = None


def tool(
    name: str,
    description: str,
    input_schema: type | dict[str, Any],
    *,
    title: str | None = None,
    annotations: ToolAnnotations | None = None,
    output_schema: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
    search_hint: str | None = None,
    always_load: bool | None = None,
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
        title: Optional human-readable display name for the tool.
            If not set, clients typically use the name.
        annotations: Optional annotations for the tool.
        output_schema: Optional JSON Schema describing the tool's output format.
        meta: Optional metadata dict sent as ``_meta`` on the tool definition.
        search_hint: Optional hint text for tool search/discovery.
        always_load: Optional flag indicating whether the tool should always be loaded.

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
            title=title,
            annotations=annotations,
            output_schema=output_schema,
            meta=meta,
            search_hint=search_hint,
            always_load=always_load,
        )

    return decorator


def create_sdk_mcp_server(
    name: str,
    version: str = "1.0.0",
    tools: list[SdkMcpTool[Any]] | None = None,
) -> McpSdkServerConfigWithInstance:
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
        McpSdkServerConfigWithInstance: A configuration object that can be passed to
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
    from mcp.types import (
        AudioContent,
        BlobResourceContents,
        EmbeddedResource,
        ImageContent,
        ResourceLink,
        TextContent,
        Tool,
    )

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
                match tool_def.input_schema:
                    case {"type": _typ, "properties": _props} as dct:
                        schema = dct
                    case dict() as input_schema:
                        # Simple dict mapping names to types - build a Pydantic model
                        # This handles required/optional, nested types, unions, etc.

                        fields = {k: (v, ...) for k, v in input_schema.items()}
                        model = create_model("Input", **fields)  # type: ignore[call-overload]  # ty:ignore[no-matching-overload]
                        schema = TypeAdapter(model).json_schema()
                    case type() as tp:
                        schema = TypeAdapter(tp).json_schema()
                    case _ as unreachable:
                        assert_never(unreachable)  # ty:ignore[type-assertion-failure]
                mcp_tool = Tool(
                    name=tool_def.name,
                    title=tool_def.title,
                    description=tool_def.description,
                    inputSchema=schema,  # type: ignore[arg-type]
                    outputSchema=tool_def.output_schema,
                    annotations=tool_def.annotations,
                )
                tool_list.append(mcp_tool)
            return tool_list

        # Register call_tool handler to execute tools
        @server.call_tool()  # type: ignore[untyped-decorator]
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[ContentBlock]:
            """Execute a tool by name with given arguments."""
            if name not in tool_map:
                raise ValueError(f"Tool '{name}' not found")

            tool_def = tool_map[name]
            result = await tool_def.handler(arguments)
            # Convert result to MCP format
            # The decorator expects us to return the content, not a CallToolResult
            # It will wrap our return value in CallToolResult
            content: list[ContentBlock] = []
            for item in result.get("content", []):
                match item:
                    case {"type": "text"}:
                        content.append(TextContent.model_validate(item))
                    case {"type": "image"}:
                        content.append(ImageContent.model_validate(item))
                    case {"type": "audio"}:
                        content.append(AudioContent.model_validate(item))
                    case {"type": "resource_link"}:
                        content.append(ResourceLink.model_validate(item))
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
    return McpSdkServerConfigWithInstance(type="sdk", name=name, instance=server)


def _detect_capabilities(server: McpServer) -> dict[str, Any]:
    """Detect which MCP capabilities a server supports based on registered handlers."""
    from mcp.types import (
        CallToolRequest,
        GetPromptRequest,
        ListPromptsRequest,
        ListResourcesRequest,
        ListResourceTemplatesRequest,
        ListToolsRequest,
        ReadResourceRequest,
    )

    capabilities: dict[str, Any] = {}
    handlers = server.request_handlers
    if handlers.get(ListToolsRequest) or handlers.get(CallToolRequest):
        capabilities["tools"] = {}
    if (
        handlers.get(ListResourcesRequest)
        or handlers.get(ReadResourceRequest)
        or handlers.get(ListResourceTemplatesRequest)
    ):
        capabilities["resources"] = {}
    if handlers.get(ListPromptsRequest) or handlers.get(GetPromptRequest):
        capabilities["prompts"] = {}
    return capabilities


async def process_mcp_request(message: JSONRPCMessage, server: McpServer) -> JSONRPCResponse:
    from mcp.types import (
        CallToolRequest,
        CallToolRequestParams,
        CallToolResult,
        GetPromptRequest,
        GetPromptRequestParams,
        GetPromptResult,
        ListPromptsRequest,
        ListPromptsResult,
        ListResourcesRequest,
        ListResourcesResult,
        ListResourceTemplatesRequest,
        ListResourceTemplatesResult,
        ListToolsRequest,
        ReadResourceRequest,
        ReadResourceRequestParams,
        ReadResourceResult,
    )

    raw_id = message.get("id")
    msg_id = raw_id if isinstance(raw_id, str | int) else 0
    try:
        # TODO: Python MCP SDK lacks the Transport abstraction that TypeScript has.
        # TypeScript: server.connect(transport) allows custom transports
        # Python: server.run(read_stream, write_stream) requires actual streams
        #
        # This forces us to manually route methods. When Python MCP adds Transport
        # support, we can refactor to match the TypeScript approach.
        match message:
            case {"method": "initialize"}:
                # Handle MCP initialization - hardcoded for tools only, no listChanged
                init_result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": _detect_capabilities(server),
                    "serverInfo": {"name": server.name, "version": server.version or "1.0.0"},
                }
                return JSONRPCResultResponse(jsonrpc="2.0", id=msg_id, result=init_result)

            case {"method": "tools/list"} if handler := server.request_handlers.get(
                ListToolsRequest
            ):
                request = ListToolsRequest()
                result = await handler(request)
                assert isinstance(result.root, ListToolsResult)
                # Convert MCP result to JSONRPC response
                data = [i.model_dump(exclude_none=True, by_alias=True) for i in result.root.tools]
                return JSONRPCResultResponse(jsonrpc="2.0", id=msg_id, result={"tools": data})

            case {"method": "tools/call", "params": dict() as params} if (
                handler := server.request_handlers.get(CallToolRequest)
            ):
                call_params = CallToolRequestParams(**params)
                call_request = CallToolRequest(params=call_params)
                result = await handler(call_request)
                # Convert MCP result to JSONRPC response
                assert isinstance(result.root, CallToolResult)
                content = list(process_content_blocks(result.root.content))
                response_data: dict[str, Any] = {"content": content}
                if result.root.isError:
                    response_data["is_error"] = True
                return JSONRPCResultResponse(jsonrpc="2.0", id=msg_id, result=response_data)
            case {"method": "resources/list"} if handler := server.request_handlers.get(
                ListResourcesRequest
            ):
                list_resources_request = ListResourcesRequest()
                result = await handler(list_resources_request)
                assert isinstance(result.root, ListResourcesResult)
                data = [
                    r.model_dump(exclude_none=True, by_alias=True) for r in result.root.resources
                ]
                return JSONRPCResultResponse(jsonrpc="2.0", id=msg_id, result={"resources": data})

            case {"method": "resources/read", "params": dict() as params} if (
                handler := server.request_handlers.get(ReadResourceRequest)
            ):
                read_params = ReadResourceRequestParams(**params)
                read_resource_request = ReadResourceRequest(params=read_params)
                result = await handler(read_resource_request)
                assert isinstance(result.root, ReadResourceResult)
                contents = [
                    c.model_dump(exclude_none=True, by_alias=True) for c in result.root.contents
                ]
                return JSONRPCResultResponse(
                    jsonrpc="2.0", id=msg_id, result={"contents": contents}
                )

            case {"method": "resources/templates/list"} if handler := server.request_handlers.get(
                ListResourceTemplatesRequest
            ):
                list_templates_request = ListResourceTemplatesRequest()
                result = await handler(list_templates_request)
                assert isinstance(result.root, ListResourceTemplatesResult)
                data = [
                    t.model_dump(exclude_none=True, by_alias=True)
                    for t in result.root.resourceTemplates
                ]
                return JSONRPCResultResponse(
                    jsonrpc="2.0", id=msg_id, result={"resourceTemplates": data}
                )

            case {"method": "prompts/list"} if handler := server.request_handlers.get(
                ListPromptsRequest
            ):
                list_prompts_request = ListPromptsRequest()
                result = await handler(list_prompts_request)
                assert isinstance(result.root, ListPromptsResult)
                data = [p.model_dump(exclude_none=True, by_alias=True) for p in result.root.prompts]
                return JSONRPCResultResponse(jsonrpc="2.0", id=msg_id, result={"prompts": data})

            case {"method": "prompts/get", "params": dict() as params} if (
                handler := server.request_handlers.get(GetPromptRequest)
            ):
                get_params = GetPromptRequestParams(**params)
                get_prompt_request = GetPromptRequest(params=get_params)
                result = await handler(get_prompt_request)
                assert isinstance(result.root, GetPromptResult)
                return JSONRPCResultResponse(
                    jsonrpc="2.0",
                    id=msg_id,
                    result=result.root.model_dump(exclude_none=True, by_alias=True),
                )

            case {"method": "notifications/initialized"}:
                # Handle initialized notification - just acknowledge it
                return JSONRPCResultResponse(jsonrpc="2.0", id=msg_id, result={})
            case {"method": method}:
                error = JSONRPCError(code=-32601, message=f"Method '{method}' not found")
                return JSONRPCErrorResponse(jsonrpc="2.0", id=msg_id, error=error)
            case _ as msg:
                error = JSONRPCError(code=-32601, message=f"Invalid JSON message {msg}")
                return JSONRPCErrorResponse(jsonrpc="2.0", id=msg_id, error=error)
    except Exception as e:
        error = JSONRPCError(code=-32603, message=str(e))
        return JSONRPCErrorResponse(jsonrpc="2.0", id=msg_id, error=error)


def process_content_blocks(content: list[ContentBlock]) -> Iterator[dict[str, Any]]:
    from mcp.types import (
        AudioContent,
        BlobResourceContents,
        EmbeddedResource,
        ImageContent,
        ResourceLink,
        TextContent,
        TextResourceContents,
    )

    for item in content:
        match item:
            case TextContent() | ImageContent() | AudioContent():
                yield item.model_dump(exclude_none=True, by_alias=True)
            case EmbeddedResource(
                resource=BlobResourceContents(mimeType=mime, uri=uri)
                | TextResourceContents(mimeType=mime, uri=uri) as resource
            ) if (uri_str := str(uri)).startswith("document://") or mime == "application/pdf":
                # EmbeddedResource - check if it's a document (PDF, etc.)
                typ = (
                    uri_str.removeprefix("document://")
                    if uri_str.startswith("document://")
                    else "base64"
                )
                data = resource.blob if isinstance(resource, BlobResourceContents) else ""
                dct = {"type": typ, "media_type": mime, "data": data}
                yield {"type": "document", "source": dct}
            case ResourceLink() | EmbeddedResource():
                pass
            case _ as unreachable:
                assert_never(unreachable)
