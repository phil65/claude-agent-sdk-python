"""Agent definitions and preset configurations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal, TypedDict

from anthropic.types import Model
from pydantic import Field

from clawd_code_sdk.models.base import (
    ClaudeCodeBaseModel,
    ModelName,
    PermissionMode,
    ReasoningEffort,
    SettingSource,
    ToolName,
)
from clawd_code_sdk.models.hooks import AgentHooksConfig
from clawd_code_sdk.models.mcp import McpServerConfigForProcessTransport


# Agent MCP server spec: either a string name or a {name: config} dict.
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
    in the initialize request.

    The CLI's *public* Zod schema (``sdk.d.ts``) only defines::

        description, prompt, tools, disallowedTools, model, mcpServers,
        criticalSystemReminder_EXPERIMENTAL, skills, maxTurns

    However, the CLI's *internal* parse schema (``Rff`` / ``parseAgentFromJson``)
    also accepts these additional fields, which are fully functional::

        memory, background, hooks, effort, permissionMode, isolation
    """

    description: str
    prompt: str
    tools: list[ToolName | str] | None = None
    model: ModelName | Literal["inherit"] | str | None = None  # noqa: PYI051
    memory: SettingSource | None = None
    mcp_servers: Sequence[AgentMcpServerSpec] | None = None
    disallowed_tools: list[ToolName | str] | None = None
    critical_system_reminder_experimental: str | None = Field(
        default=None, serialization_alias="criticalSystemReminder_EXPERIMENTAL"
    )
    skills: list[str] | None = None
    max_turns: int | None = None
    background: bool | None = None
    hooks: AgentHooksConfig | None = None
    effort: ReasoningEffort | int | None = None
    permission_mode: PermissionMode | None = None
    isolation: Literal["worktree"] | None = None


class AgentDefinition(ClaudeCodeBaseModel):
    """User-facing agent definition configuration.

    Accepts ergonomic Python inputs (e.g. dict-style mcp_servers)
    and converts to the wire format via ``to_wire()``.
    """

    description: str = Field(..., title="Agent Description", examples=["QA Assistant"])
    """A brief description of the agent's purpose."""

    prompt: str = Field(..., title="Agent Prompt", examples=["Do XY"])
    """The prompt to use for this agent."""

    tools: list[ToolName | str] | None = Field(default=None, title="Agent Tools", examples=["Bash"])
    """The tools this agent has access to."""

    model: ModelName | Literal["inherit"] | str | None = Field(  # noqa: PYI051
        default=None,
        title="Agent Model",
        examples=["sonnet"],
    )
    """The model to use for this agent."""

    memory: SettingSource | None = Field(
        default=None,
        title="Agent Memory",
        examples=["user", "project"],
    )
    """Persistent cross-session memory scope for this agent."""
    mcp_servers: Mapping[str, McpServerConfigForProcessTransport | None] | None = None
    """MCP servers for this agent.

    Maps server names to configs. Use ``None`` as the value to reference
    a server already configured in settings::
    """

    disallowed_tools: list[ToolName | str] | None = Field(
        default=None,
        title="Disallowed Tools",
        examples=["Bash"],
    )
    """Tools this agent is not allowed to use."""

    critical_system_reminder_experimental: str | None = Field(
        default=None,
        title="Critical System Reminder",
        alias="criticalSystemReminder_EXPERIMENTAL",
    )
    """Critical system reminder message to display to the user."""

    skills: list[str] | None = Field(default=None, title="Skills", examples=["my-skill"])
    """Skills this agent has."""

    max_turns: int | None = Field(default=None, title="Max Turns")
    """Maximum number of agentic turns (API round-trips) before stopping."""

    background: bool | None = Field(default=None, title="Run in Background")
    """Whether this agent runs in the background."""

    hooks: AgentHooksConfig | None = Field(default=None, title="Agent Hooks")
    """Hook configurations for this agent."""

    effort: ReasoningEffort | int | None = Field(
        default=None,
        title="Reasoning effort",
        examples=["high"],
    )
    """Effort level for thinking depth."""

    permission_mode: PermissionMode | None = Field(
        default=None,
        title="Permission Mode",
        examples=["bypassPermissions"],
    )
    """Permission mode for this agent."""

    isolation: Literal["worktree"] | None = Field(
        default=None,
        title="Isolation Mode",
        examples=["worktree"],
    )
    """Isolation mode. ``"worktree"`` runs the agent in a separate git worktree."""

    def to_wire(self) -> dict[str, Any]:
        """Serialize to the wire-format dict for the CLI control protocol.

        Converts dict-style mcp_servers to the array format the CLI expects:
        ``{"git": config}`` -> ``[{"git": config}]``

        Returns a camelCase dict with None values excluded.
        """
        model = self.to_wire_model()
        return model.model_dump(by_alias=True, exclude_none=True)

    def to_wire_model(self) -> AgentWireDefinition:
        """Serialize to the wire-format dict for the CLI control protocol.

        Converts dict-style mcp_servers to the array format the CLI expects:
        ``{"git": config}`` -> ``[{"git": config}]``

        Returns a camelCase dict with None values excluded.
        """
        mcp = [
            name if config is None else {name: config}
            for name, config in (self.mcp_servers or {}).items()
        ]
        return AgentWireDefinition(
            description=self.description,
            prompt=self.prompt,
            tools=self.tools,
            model=self.model,
            memory=self.memory,
            mcp_servers=mcp or None,
            disallowed_tools=self.disallowed_tools,
            critical_system_reminder_experimental=self.critical_system_reminder_experimental,
            skills=self.skills,
            max_turns=self.max_turns,
            background=self.background,
            hooks=self.hooks,
            effort=self.effort,
            permission_mode=self.permission_mode,
            isolation=self.isolation,
        )
