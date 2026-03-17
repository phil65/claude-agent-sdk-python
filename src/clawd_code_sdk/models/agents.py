"""Agent definitions and preset configurations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, TypedDict

from anthropic.types import Model
from pydantic import Field

from clawd_code_sdk.models.base import ClaudeCodeBaseModel, ModelName, SettingSource
from clawd_code_sdk.models.hooks import AgentHooksConfig
from clawd_code_sdk.models.mcp import ExternalMcpServerConfig, McpServerConfigForProcessTransport


# Agent MCP server spec: either a string name or a {name: config} dict.
# Matches the TypeScript type: AgentMcpServerSpec =
# string | Record<string, McpServerConfigForProcessTransport>
# Matches the TypeScript type: AgentMcpServerSpec =
# string | Record<string, McpServerConfigForProcessTransport>
AgentMcpServerSpec = str | dict[str, McpServerConfigForProcessTransport]


class AgentInfo(ClaudeCodeBaseModel):
    """Information about an available subagent that can be invoked via the Agent tool."""

    name: str
    """Agent type identifier (e.g., "Explore")."""

    description: str
    """Description of when to use this agent."""

    model: Model | str | None = None
    """Model alias this agent uses. If omitted, inherits the parent's model."""


class ToolsPreset(TypedDict):
    """Tools preset configuration."""

    type: Literal["preset"]
    preset: Literal["claude_code"]


class AgentWireDefinition(ClaudeCodeBaseModel):
    """Wire-format agent definition matching the CLI control protocol.

    This is the strict camelCase representation sent over the wire
    in the initialize request. Fields match the TypeScript AgentDefinition.
    """

    description: str
    prompt: str
    tools: list[str] | None = None
    model: ModelName | Literal["inherit"] | str | None = None  # noqa: PYI051
    memory: SettingSource | None = None
    mcp_servers: list[AgentMcpServerSpec] | None = None
    disallowed_tools: list[str] | None = None
    critical_system_reminder_experimental: str | None = Field(
        default=None, serialization_alias="criticalSystemReminder_EXPERIMENTAL"
    )
    skills: list[str] | None = None
    max_turns: int | None = None
    background: bool | None = None
    hooks: AgentHooksConfig | None = None


class AgentDefinition(ClaudeCodeBaseModel):
    """User-facing agent definition configuration.

    Accepts ergonomic Python inputs (e.g. dict-style mcp_servers)
    and converts to the wire format via ``to_wire()``.
    """

    description: str
    prompt: str
    tools: list[str] | None = None
    model: ModelName | Literal["inherit"] | str | None = None  # noqa: PYI051
    memory: SettingSource | None = None
    mcp_servers: Mapping[str, ExternalMcpServerConfig | None] | None = None
    """MCP servers for this agent.

    Maps server names to configs. Use ``None`` as the value to reference
    a server already configured in settings::

        {
            "git": McpStdioServerConfig(command="uvx", args=["mcp-server-git"]),
            "already-configured": None,  # reference by name
        }
    """
    disallowed_tools: list[str] | None = None
    critical_system_reminder_experimental: str | None = Field(
        default=None, alias="criticalSystemReminder_EXPERIMENTAL"
    )
    skills: list[str] | None = None
    max_turns: int | None = None
    background: bool | None = None
    hooks: AgentHooksConfig | None = None

    def to_wire(self) -> dict[str, Any]:
        """Serialize to the wire-format dict for the CLI control protocol.

        Converts dict-style mcp_servers to the array format the CLI expects:
        ``{"git": config}`` -> ``[{"git": config}]``

        Returns a camelCase dict with None values excluded.
        """
        mcp: list[AgentMcpServerSpec] | None = None
        if self.mcp_servers is not None:
            mcp = [
                name if config is None else {name: config}
                for name, config in self.mcp_servers.items()
            ]
        return AgentWireDefinition(
            description=self.description,
            prompt=self.prompt,
            tools=self.tools,
            model=self.model,
            memory=self.memory,
            mcp_servers=mcp,
            disallowed_tools=self.disallowed_tools,
            critical_system_reminder_experimental=self.critical_system_reminder_experimental,
            skills=self.skills,
            max_turns=self.max_turns,
            background=self.background,
            hooks=self.hooks,
        ).model_dump(by_alias=True, exclude_none=True)
