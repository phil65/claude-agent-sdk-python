"""Launch flags and initialize request fields that follow the upstream SDK (0.3.331)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from clawd_code_sdk import ClaudeAgentOptions, create_sdk_mcp_server, tool
from clawd_code_sdk._internal.query import Query
from clawd_code_sdk._internal.transport import Transport
from clawd_code_sdk._internal.transport.subprocess_utils import to_cli_args
from clawd_code_sdk.models.mcp import McpServerToolPolicy, SdkPluginConfig


if TYPE_CHECKING:
    from collections.abc import AsyncIterator


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


def test_plugins_go_as_flags_by_default() -> None:
    options = ClaudeAgentOptions(plugins=[SdkPluginConfig(path="/p")], mcp_servers={})
    args = to_cli_args(options)
    assert args[args.index("--plugin-dir") + 1] == "/p"
    assert "--await-initialize" not in args
    assert options.initialize_plugins() is None


def test_plugins_in_the_initialize_request() -> None:
    plugins = [SdkPluginConfig(path="/p"), SdkPluginConfig(path="/q", skip_mcp_discovery=True)]
    options = ClaudeAgentOptions(plugins=plugins, plugin_delivery="initialize", mcp_servers={})
    args = to_cli_args(options)
    assert "--plugin-dir" not in args
    assert "--plugin-dir-no-mcp" not in args
    assert args.count("--await-initialize") == 1  # The CLI reads them at launch
    assert options.initialize_plugins() == [
        {"type": "local", "path": "/p"},
        {"type": "local", "path": "/q", "skipMcpDiscovery": True},
    ]


def test_sdk_server_settings_are_sent_by_server() -> None:
    plain = create_sdk_mcp_server("plain")
    tuned = create_sdk_mcp_server("tuned")
    tuned.timeout = 30_000
    tuned.tools = [McpServerToolPolicy(name="delete", permission_policy="always_ask")]
    options = ClaudeAgentOptions(mcp_servers={"plain": plain, "tuned": tuned})
    assert options.sdk_mcp_server_configs() == {
        "tuned": {
            "timeout": 30_000,
            "tools": [{"name": "delete", "permission_policy": "always_ask"}],
        }
    }


async def test_in_process_servers_are_handshaken_for_the_cli() -> None:
    @tool("greet", "Greet someone", {"name": str})
    async def greet(args: dict[str, Any]) -> dict[str, Any]:
        return {"content": [{"type": "text", "text": f"Hello, {args['name']}!"}]}

    config = create_sdk_mcp_server("greeter", tools=[greet])
    query = Query(transport=_NullTransport(), sdk_mcp_servers={"greeter": config.instance})
    try:
        manifests = await query.capture_sdk_mcp_manifests()
        assert manifests is not None
        manifest = manifests["greeter"]
        assert manifest["initializeResult"]["protocolVersion"]
        assert [t["name"] for t in manifest["toolsListResult"]["tools"]] == ["greet"]
        # The CLI then calls tools over mcp_message, without a handshake of its own
        message = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": "greet", "arguments": {"name": "Ada"}},
        }
        response = await query._handle_sdk_mcp_request("greeter", message)  # type: ignore[arg-type]
        assert response is not None
        assert response["result"]["content"][0]["text"] == "Hello, Ada!"
    finally:
        await query.close()


async def test_no_in_process_servers_no_manifests() -> None:
    query = Query(transport=_NullTransport())
    try:
        assert await query.capture_sdk_mcp_manifests() is None
    finally:
        await query.close()
