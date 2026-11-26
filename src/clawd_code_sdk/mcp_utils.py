"""In-process (SDK) MCP servers: the ``@tool`` decorator and ``create_sdk_mcp_server``.

Servers built here are regular ``mcp.server.Server`` instances. The SDK serves
them to the CLI through mcp's own in-memory transport (see
``clawd_code_sdk._internal.sdk_mcp_bridge``), which works on mcp 1.x and 2.x.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING, Any, assert_never

import jsonschema
from mcp.types import CallToolResult, Tool
from pydantic import TypeAdapter, create_model

from clawd_code_sdk._internal.mcp_compat import build_tool_server
from clawd_code_sdk.models import McpSdkServerConfigWithInstance


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from mcp.types import ToolAnnotations


logger = logging.getLogger(__name__)

DOCUMENT_URI_PREFIX = "document://"
"""URI scheme marking an embedded resource that carries an Anthropic document block."""


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
    max_result_size_chars: int | None = None


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
    max_result_size_chars: int | None = None,
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
        max_result_size_chars: Optional size (in characters) up to which Claude Code
            keeps the tool's result inline instead of persisting it with a preview.

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
            max_result_size_chars=max_result_size_chars,
        )

    return decorator


def create_sdk_mcp_server(
    name: str,
    version: str = "1.0.0",
    tools: list[SdkMcpTool[Any]] | None = None,
) -> McpSdkServerConfigWithInstance:
    """Create an in-process MCP server that runs within your Python application.

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
        ClaudeAgentOptions.mcp_servers. Its ``instance`` is a regular
        ``mcp.server.Server`` that the SDK connects to Claude Code over an
        in-memory MCP transport.

    Example:
        Simple calculator server:
        >>> @tool("add", "Add numbers", {"a": float, "b": float})
        ... async def add(args):
        ...     return {"content": [{"type": "text", "text": f"Sum: {args['a'] + args['b']}"}]}
        >>>
        >>> calculator = create_sdk_mcp_server(name="calculator", tools=[add])
        >>> options = ClaudeAgentOptions(mcp_servers={"calc": calculator})

        Bringing your own server: any ``mcp.server.Server`` built with the
        installed ``mcp`` package can be used in place of this helper, and the
        requests it handles (tools, resources, prompts, ...) are served.
        Requests and notifications the server sends to the client (sampling,
        elicitation, roots, logging, progress, list_changed) are not forwarded:
        >>> from mcp.server import Server
        >>> my_server = Server("mine")  # register handlers with the mcp API
        >>> config = McpSdkServerConfigWithInstance(name="mine", instance=my_server)

    Notes:
        - Tool arguments are validated against the tool's input schema. Unknown
          tools, invalid arguments and exceptions raised by a handler are all
          reported to Claude as error results rather than failing the request.
        - Works with both mcp 1.x and mcp 2.x.
    """
    tool_defs = tools or []
    tools_by_name = {tool_def.name: tool_def for tool_def in tool_defs}
    schemas = {tool_def.name: build_input_schema(tool_def.input_schema) for tool_def in tool_defs}
    wire_tools = [
        Tool.model_validate({
            "name": tool_def.name,
            "title": tool_def.title,
            "description": tool_def.description,
            "inputSchema": schemas[tool_def.name],
            "outputSchema": tool_def.output_schema,
            "annotations": tool_def.annotations,
            "_meta": build_tool_meta(tool_def),
        })
        for tool_def in tool_defs
    ]

    async def run_tool(tool_name: str, arguments: dict[str, Any]) -> CallToolResult:
        # The SDK owns these semantics so a tool behaves the same on every
        # supported mcp version: unknown tools, invalid arguments and handler
        # failures all come back as isError results the model can read, never
        # as protocol errors.
        tool_def = tools_by_name.get(tool_name)
        if tool_def is None:
            return _tool_error_result(f"Tool '{tool_name}' not found")
        try:
            try:
                jsonschema.validate(instance=arguments, schema=schemas[tool_name])
            except jsonschema.ValidationError as e:
                return _tool_error_result(f"Input validation error: {e.message}")
            result = await tool_def.handler(arguments)
            return CallToolResult.model_validate({
                "content": convert_tool_content(result.get("content", [])),
                "isError": bool(result.get("is_error", False)),
            })
        except Exception as e:
            return _tool_error_result(str(e))

    server = build_tool_server(name, version, wire_tools, run_tool)
    return McpSdkServerConfigWithInstance(name=name, instance=server)


def build_input_schema(input_schema: type | dict[str, Any]) -> dict[str, Any]:
    """Turn a tool's declared input_schema into the JSON Schema sent on the wire.

    Accepts a full JSON Schema dict, a dict mapping parameter names to Python
    types (all required), or a type (TypedDict, dataclass, pydantic model).
    """
    match input_schema:
        case dict() as dct if isinstance(dct.get("type"), str) and isinstance(
            dct.get("properties"), dict
        ):
            return dct
        case dict() as mapping:
            # Simple dict mapping names to types - build a Pydantic model.
            # This handles required/optional, nested types, unions, etc.
            fields = {k: (v, ...) for k, v in mapping.items()}
            model = create_model("Input", **fields)  # type: ignore[call-overload]  # ty:ignore[no-matching-overload]
            return TypeAdapter(model).json_schema()
        case type() as tp:
            return TypeAdapter(tp).json_schema()
        case _ as unreachable:
            assert_never(unreachable)


def build_tool_meta(tool_def: SdkMcpTool[Any]) -> dict[str, Any] | None:
    """Build the ``_meta`` dict sent with a tool definition.

    Client-specific hints travel in ``_meta`` under namespaced keys because MCP
    clients drop annotation fields they do not know. Claude Code reads:

    - ``anthropic/maxResultSizeChars``: the size up to which a tool result is
      kept inline rather than persisted with a preview (``max_result_size_chars``,
      or a ``maxResultSizeChars`` field on the annotations object, which only
      survives as an extra field on mcp 1.x),
    - ``anthropic/alwaysLoad``: never defer the tool behind tool search,
    - ``anthropic/searchHint``: extra text for tool search to match on.

    Explicit ``meta`` from the tool definition is merged last and wins.
    """
    meta: dict[str, Any] = {}
    if tool_def.max_result_size_chars is not None:
        meta["anthropic/maxResultSizeChars"] = tool_def.max_result_size_chars
    elif tool_def.annotations is not None:
        # Covers both an extra field and a field declared on a subclass.
        dumped = tool_def.annotations.model_dump(by_alias=True)
        if (max_size := dumped.get("maxResultSizeChars")) is not None:
            meta["anthropic/maxResultSizeChars"] = max_size
    if tool_def.always_load is not None:
        meta["anthropic/alwaysLoad"] = tool_def.always_load
    if tool_def.search_hint is not None:
        meta["anthropic/searchHint"] = tool_def.search_hint
    if tool_def.meta:
        meta.update(tool_def.meta)
    return meta or None


def _tool_error_result(message: str) -> CallToolResult:
    return CallToolResult.model_validate({
        "content": [{"type": "text", "text": message}],
        "isError": True,
    })


def convert_tool_content(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map the content of a tool handler's result dict to MCP content blocks.

    - text, image and audio blocks pass through;
    - ``document`` blocks (Anthropic format) are carried as an embedded blob
      resource with a ``document://`` URI and restored to a document block
      on the way to the CLI (see ``restore_document_blocks``);
    - resource links and text resources are flattened to text, which is what
      the CLI renders;
    - other binary resources and unknown block types are dropped with a warning.
    """
    content: list[dict[str, Any]] = []
    for item in items:
        match item:
            case {"type": "text" | "image" | "audio"}:
                content.append(item)
            case {"type": "document", "source": dict() as source}:
                content.append({
                    "type": "resource",
                    "resource": {
                        "uri": f"{DOCUMENT_URI_PREFIX}{source.get('type', 'base64')}",
                        "mimeType": source.get("media_type", "application/pdf"),
                        "blob": source.get("data", ""),
                    },
                })
            case {"type": "resource_link"}:
                parts = [
                    str(part)
                    for part in (item.get("name"), item.get("uri"), item.get("description"))
                    if part
                ]
                text = "\n".join(parts) if parts else "Resource link"
                content.append({"type": "text", "text": text})
            case {"type": "resource", "resource": {"text": str() as text}}:
                content.append({"type": "text", "text": text})
            case {"type": "resource"}:
                logger.warning("Binary embedded resource cannot be converted to text, skipping")
            case _:
                logger.warning(
                    "Unsupported content type %r in tool result, skipping", item.get("type")
                )
    return content


def restore_document_blocks(response: dict[str, Any]) -> dict[str, Any]:
    """Rewrite document resources in a ``tools/call`` JSON-RPC response for the CLI.

    Embedded blob resources with a ``document://`` URI or a PDF mime type are
    turned back into Anthropic ``document`` blocks, which Claude Code passes
    on to the model. Every other part of the response is left untouched.
    """
    match response:
        case {"result": {"content": list() as content} as result}:
            pass
        case _:
            return response
    restored: list[Any] = []
    changed = False
    for block in content:
        match block:
            case {
                "type": "resource",
                "resource": {"uri": str() as uri, "blob": str() as data} as resource,
            } if (
                uri.startswith(DOCUMENT_URI_PREFIX) or resource.get("mimeType") == "application/pdf"
            ):
                source_type = (
                    uri.removeprefix(DOCUMENT_URI_PREFIX)
                    if uri.startswith(DOCUMENT_URI_PREFIX)
                    else "base64"
                )
                media_type = resource.get("mimeType", "application/pdf")
                source = {"type": source_type, "media_type": media_type, "data": data}
                restored.append({"type": "document", "source": source})
                changed = True
            case _:
                restored.append(block)
    if not changed:
        return response
    return {**response, "result": {**result, "content": restored}}
