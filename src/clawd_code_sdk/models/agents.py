"""Agent definitions and preset configurations."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Any, Literal, NotRequired, TypedDict


if TYPE_CHECKING:
    from .mcp import ExternalMcpServerConfig

# Agent MCP server spec: either a string name or a {name: config} dict.
# Matches the TypeScript type: AgentMcpServerSpec = string | Record<string, McpServerConfigForProcessTransport>
AgentMcpServerSpec = str | dict[str, Any]

# Fields on AgentDefinition that need snake_case -> camelCase conversion
_FIELD_RENAMES: dict[str, str] = {
    "mcp_servers": "mcpServers",
}


class SystemPromptPreset(TypedDict):
    """System prompt preset configuration."""

    type: Literal["preset"]
    preset: Literal["claude_code"]
    append: NotRequired[str]


class ToolsPreset(TypedDict):
    """Tools preset configuration."""

    type: Literal["preset"]
    preset: Literal["claude_code"]


@dataclass
class AgentDefinition:
    """Agent definition configuration."""

    description: str
    prompt: str
    tools: list[str] | None = None
    model: Literal["sonnet", "opus", "haiku", "inherit"] | None = None
    memory: Literal["user", "project", "local"] | None = None
    mcp_servers: list[AgentMcpServerSpec] | dict[str, ExternalMcpServerConfig] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict suitable for the CLI wire format.

        Drops None values and converts Python field names to the camelCase keys
        expected by the Claude Code CLI (e.g. mcp_servers -> mcpServers).

        For mcp_servers, accepts either:
        - A dict mapping server names to configs (Pythonic) -> converted to
          [{name: config}, ...] array for the CLI
        - A list of AgentMcpServerSpec (raw CLI format) -> passed through as-is
        """
        result: dict[str, Any] = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if value is None:
                continue
            key = _FIELD_RENAMES.get(f.name, f.name)
            # Convert dict-style mcp_servers to the array format the CLI expects
            if f.name == "mcp_servers" and isinstance(value, dict):
                value = [{name: config} for name, config in value.items()]
            result[key] = value
        return result
