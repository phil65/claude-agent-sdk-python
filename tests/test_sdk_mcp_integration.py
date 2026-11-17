"""Integration tests for SDK MCP server support.

All tests drive servers through the same path the CLI uses: raw JSON-RPC
messages routed by ``Query._handle_sdk_mcp_request`` into the in-memory MCP
bridge. They therefore run unchanged on mcp 1.x and 2.x.
"""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Any

from mcp.types import ToolAnnotations

from clawd_code_sdk import create_sdk_mcp_server, tool
from clawd_code_sdk._internal.mcp_compat import MCP_MAJOR
from clawd_code_sdk._internal.query import Query
from clawd_code_sdk._internal.transport import Transport


if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from mcp.server import Server


class _NullTransport(Transport):
    async def connect(self) -> None:
        pass

    async def write(self, data: str) -> None:
        pass

    async def read_messages(self) -> AsyncIterator[dict[str, Any]]:
        return
        yield

    async def close(self) -> None:
        pass

    async def end_input(self) -> None:
        pass


_INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 0,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "claude-code", "version": "test"},
    },
}


async def _connected_query(servers: dict[str, Server]) -> Query:
    query = Query(transport=_NullTransport(), sdk_mcp_servers=servers)
    for name in servers:
        response = await query._handle_sdk_mcp_request(name, _INITIALIZE)  # type: ignore[arg-type]
        assert response is not None
        assert "result" in response, response
        ack = await query._handle_sdk_mcp_request(  # type: ignore[arg-type]
            name, {"jsonrpc": "2.0", "method": "notifications/initialized"}
        )
        assert ack is None
    return query


async def _call(
    query: Query, server: str, method: str, params: dict[str, Any] | None = None, id_: int = 1
) -> dict[str, Any]:
    message: dict[str, Any] = {"jsonrpc": "2.0", "id": id_, "method": method}
    if params is not None:
        message["params"] = params
    response = await query._handle_sdk_mcp_request(server, message)  # type: ignore[arg-type]
    assert response is not None
    return dict(response)


async def test_list_and_call_tools():
    executions: list[dict[str, Any]] = []

    @tool("greet_user", "Greets a user by name", {"name": str})
    async def greet_user(args: dict[str, Any]) -> dict[str, Any]:
        executions.append(args)
        return {"content": [{"type": "text", "text": f"Hello, {args['name']}!"}]}

    @tool("add_numbers", "Adds two numbers", {"a": float, "b": float})
    async def add_numbers(args: dict[str, Any]) -> dict[str, Any]:
        return {"content": [{"type": "text", "text": f"{args['a'] + args['b']}"}]}

    config = create_sdk_mcp_server("test-sdk-server", tools=[greet_user, add_numbers])
    query = await _connected_query({"test": config.instance})
    try:
        listed = await _call(query, "test", "tools/list")
        tools = {t["name"]: t for t in listed["result"]["tools"]}
        assert set(tools) == {"greet_user", "add_numbers"}
        assert tools["greet_user"]["inputSchema"]["properties"]["name"]["type"] == "string"
        assert "name" in tools["greet_user"]["inputSchema"]["required"]

        called = await _call(
            query, "test", "tools/call", {"name": "greet_user", "arguments": {"name": "Alice"}}, 2
        )
        result = called["result"]
        assert result["content"] == [{"type": "text", "text": "Hello, Alice!"}]
        assert not result.get("isError", False)
        assert executions == [{"name": "Alice"}]
    finally:
        await query.close()


async def test_initialize_advertises_tools_capability():
    @tool("noop", "Does nothing", {})
    async def noop(args: dict[str, Any]) -> dict[str, Any]:
        return {"content": []}

    config = create_sdk_mcp_server("caps", tools=[noop])
    query = Query(transport=_NullTransport(), sdk_mcp_servers={"caps": config.instance})
    try:
        response = await query._handle_sdk_mcp_request("caps", _INITIALIZE)  # type: ignore[arg-type]
        assert response is not None
        assert "tools" in response["result"]["capabilities"]  # type: ignore[typeddict-item]
        assert response["result"]["serverInfo"]["name"] == "caps"  # type: ignore[typeddict-item]
    finally:
        await query.close()


async def test_handler_exception_becomes_error_result():
    @tool("fail", "Always fails", {})
    async def fail_tool(args: dict[str, Any]) -> dict[str, Any]:
        raise ValueError("Expected error")

    config = create_sdk_mcp_server("error-test", tools=[fail_tool])
    query = await _connected_query({"error": config.instance})
    try:
        response = await _call(query, "error", "tools/call", {"name": "fail", "arguments": {}})
        assert response["result"]["isError"] is True
        assert "Expected error" in response["result"]["content"][0]["text"]
    finally:
        await query.close()


async def test_is_error_flag_from_handler_is_propagated():
    @tool("soft_fail", "Reports an error", {})
    async def soft_fail(args: dict[str, Any]) -> dict[str, Any]:
        return {"content": [{"type": "text", "text": "nope"}], "is_error": True}

    config = create_sdk_mcp_server("soft", tools=[soft_fail])
    query = await _connected_query({"soft": config.instance})
    try:
        response = await _call(query, "soft", "tools/call", {"name": "soft_fail", "arguments": {}})
        assert response["result"]["isError"] is True
    finally:
        await query.close()


async def test_invalid_arguments_and_unknown_tool():
    calls: list[dict[str, Any]] = []

    @tool("typed", "Needs an int", {"count": int})
    async def typed(args: dict[str, Any]) -> dict[str, Any]:
        calls.append(args)
        return {"content": [{"type": "text", "text": "ok"}]}

    config = create_sdk_mcp_server("validate", tools=[typed])
    query = await _connected_query({"v": config.instance})
    try:
        invalid = await _call(
            query, "v", "tools/call", {"name": "typed", "arguments": {"count": "x"}}
        )
        assert invalid["result"]["isError"] is True
        assert invalid["result"]["content"][0]["text"].startswith("Input validation error")
        assert calls == []

        unknown = await _call(query, "v", "tools/call", {"name": "missing", "arguments": {}}, 2)
        assert unknown["result"]["isError"] is True
        assert "not found" in unknown["result"]["content"][0]["text"]
    finally:
        await query.close()


async def test_unknown_server_returns_jsonrpc_error():
    query = Query(transport=_NullTransport(), sdk_mcp_servers={})
    try:
        response = await _call(query, "nope", "tools/list")
        assert response["error"]["code"] == -32601
    finally:
        await query.close()


async def test_image_content_support():
    png_data = base64.b64encode(b"\x89PNG\r\n\x1a\nfake").decode()

    @tool("generate_chart", "Generates a chart", {"title": str})
    async def generate_chart(args: dict[str, Any]) -> dict[str, Any]:
        return {
            "content": [
                {"type": "text", "text": f"Generated chart: {args['title']}"},
                {"type": "image", "data": png_data, "mimeType": "image/png"},
            ]
        }

    config = create_sdk_mcp_server("image-test-server", tools=[generate_chart])
    query = await _connected_query({"img": config.instance})
    try:
        response = await _call(
            query, "img", "tools/call", {"name": "generate_chart", "arguments": {"title": "Sales"}}
        )
        content = response["result"]["content"]
        assert content[0] == {"type": "text", "text": "Generated chart: Sales"}
        assert content[1]["type"] == "image"
        assert content[1]["data"] == png_data
        assert content[1]["mimeType"] == "image/png"
    finally:
        await query.close()


async def test_document_content_support():
    pdf_data = base64.b64encode(b"%PDF-1.0\n%%EOF").decode()

    @tool("read_document", "Reads a PDF document", {"filename": str})
    async def read_document(args: dict[str, Any]) -> dict[str, Any]:
        return {
            "content": [
                {"type": "text", "text": f"Document: {args['filename']}"},
                {
                    "type": "document",
                    "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_data},
                },
            ]
        }

    config = create_sdk_mcp_server("document-test-server", tools=[read_document])
    query = await _connected_query({"doc": config.instance})
    try:
        response = await _call(
            query,
            "doc",
            "tools/call",
            {"name": "read_document", "arguments": {"filename": "a.pdf"}},
        )
        content = response["result"]["content"]
        assert content[0] == {"type": "text", "text": "Document: a.pdf"}
        assert content[1] == {
            "type": "document",
            "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_data},
        }
    finally:
        await query.close()


async def test_resource_link_is_flattened_to_text():
    @tool("link", "Returns a link", {})
    async def link(args: dict[str, Any]) -> dict[str, Any]:
        return {
            "content": [
                {"type": "resource_link", "name": "spec", "uri": "file:///spec.md"},
            ]
        }

    config = create_sdk_mcp_server("links", tools=[link])
    query = await _connected_query({"l": config.instance})
    try:
        response = await _call(query, "l", "tools/call", {"name": "link", "arguments": {}})
        assert response["result"]["content"] == [{"type": "text", "text": "spec\nfile:///spec.md"}]
    finally:
        await query.close()


async def test_tool_annotations_and_meta():
    @tool(
        "read_data",
        "Reads data",
        {"source": str},
        annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
        always_load=True,
        search_hint="data reader",
        meta={"custom/key": 1},
    )
    async def read_data(args: dict[str, Any]) -> dict[str, Any]:
        return {"content": [{"type": "text", "text": "data"}]}

    @tool("big", "Large output", {}, max_result_size_chars=500_000)
    async def big(args: dict[str, Any]) -> dict[str, Any]:
        return {"content": []}

    @tool("plain", "No annotations", {})
    async def plain(args: dict[str, Any]) -> dict[str, Any]:
        return {"content": []}

    config = create_sdk_mcp_server("annotations", tools=[read_data, big, plain])
    query = await _connected_query({"a": config.instance})
    try:
        listed = await _call(query, "a", "tools/list")
        tools = {t["name"]: t for t in listed["result"]["tools"]}
        assert tools["read_data"]["annotations"]["readOnlyHint"] is True
        assert tools["read_data"]["annotations"]["openWorldHint"] is False
        assert tools["read_data"]["_meta"] == {
            "anthropic/alwaysLoad": True,
            "anthropic/searchHint": "data reader",
            "custom/key": 1,
        }
        assert tools["big"]["_meta"] == {"anthropic/maxResultSizeChars": 500_000}
        assert "_meta" not in tools["plain"]
        assert "annotations" not in tools["plain"]
    finally:
        await query.close()


def _resource_server() -> Server:
    """A hand-built lowlevel server exposing one resource, on either mcp major."""
    from mcp.server import Server
    from mcp.types import (
        ListResourcesResult,
        ReadResourceResult,
        Resource,
        TextResourceContents,
    )

    resource = Resource(uri="test://greeting", name="greeting")  # type: ignore[arg-type]
    contents = TextResourceContents(uri="test://greeting", text="Hello from resource!")  # type: ignore[arg-type]

    if MCP_MAJOR >= 2:

        async def on_list_resources(ctx: Any, params: Any) -> ListResourcesResult:
            return ListResourcesResult(resources=[resource])

        async def on_read_resource(ctx: Any, params: Any) -> ReadResourceResult:
            return ReadResourceResult(contents=[contents])

        server_cls: Any = Server
        built: Server = server_cls(
            "res_test", on_list_resources=on_list_resources, on_read_resource=on_read_resource
        )
        return built

    legacy: Any = Server("res_test")

    @legacy.list_resources()
    async def list_resources() -> list[Resource]:
        return [resource]

    @legacy.read_resource()
    async def read_resource(uri: Any) -> str:
        return "Hello from resource!"

    built_legacy: Server = legacy
    return built_legacy


async def test_custom_server_resources():
    query = await _connected_query({"res": _resource_server()})
    try:
        listed = await _call(query, "res", "resources/list")
        resources = listed["result"]["resources"]
        assert [r["uri"] for r in resources] == ["test://greeting"]

        read = await _call(query, "res", "resources/read", {"uri": "test://greeting"}, 2)
        assert read["result"]["contents"][0]["text"] == "Hello from resource!"
    finally:
        await query.close()


async def test_closed_bridge_rejects_messages():
    @tool("noop", "Does nothing", {})
    async def noop(args: dict[str, Any]) -> dict[str, Any]:
        return {"content": []}

    config = create_sdk_mcp_server("closing", tools=[noop])
    query = await _connected_query({"c": config.instance})
    await query.close()
    response = await _call(query, "c", "tools/list")
    assert response["error"]["code"] == -32603
    assert "closed" in response["error"]["message"]
