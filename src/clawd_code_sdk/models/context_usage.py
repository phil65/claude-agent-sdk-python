"""Context window usage breakdown models."""

from __future__ import annotations

from clawd_code_sdk.models.base import ClaudeCodeBaseModel
from clawd_code_sdk.models.usage import Usage


class ContextUsageCategory(ClaudeCodeBaseModel):
    """A single category in the context usage breakdown."""

    name: str
    tokens: int
    color: str
    is_deferred: bool | None = None


class ContextUsageGridCell(ClaudeCodeBaseModel):
    """A single cell in the context usage grid visualization."""

    color: str
    is_filled: bool
    category_name: str
    tokens: int
    percentage: float
    square_fullness: float


class ContextUsageMemoryFile(ClaudeCodeBaseModel):
    """A memory file contributing to context usage."""

    path: str
    type: str
    tokens: int


class ContextUsageMcpTool(ClaudeCodeBaseModel):
    """An MCP tool contributing to context usage."""

    name: str
    server_name: str
    tokens: int
    is_loaded: bool | None = None


class ContextUsageDeferredBuiltinTool(ClaudeCodeBaseModel):
    """A deferred builtin tool contributing to context usage."""

    name: str
    tokens: int
    is_loaded: bool


class ContextUsageSystemTool(ClaudeCodeBaseModel):
    """A system tool contributing to context usage."""

    name: str
    tokens: int


class ContextUsageSystemPromptSection(ClaudeCodeBaseModel):
    """A system prompt section contributing to context usage."""

    name: str
    tokens: int


class ContextUsageAgent(ClaudeCodeBaseModel):
    """An agent contributing to context usage."""

    agent_type: str
    source: str
    tokens: int


class ContextUsageSlashCommands(ClaudeCodeBaseModel):
    """Slash commands context usage summary."""

    total_commands: int
    included_commands: int
    tokens: int


class ContextUsageSkillFrontmatter(ClaudeCodeBaseModel):
    """A single skill's frontmatter contributing to context usage."""

    name: str
    source: str
    tokens: int


class ContextUsageSkills(ClaudeCodeBaseModel):
    """Skills context usage summary."""

    total_skills: int
    included_skills: int
    tokens: int
    skill_frontmatter: list[ContextUsageSkillFrontmatter]


class ContextUsageToolCallBreakdown(ClaudeCodeBaseModel):
    """Token breakdown for a specific tool call type."""

    name: str
    call_tokens: int
    result_tokens: int


class ContextUsageAttachmentBreakdown(ClaudeCodeBaseModel):
    """Token breakdown for a specific attachment type."""

    name: str
    tokens: int


class ContextUsageMessageBreakdown(ClaudeCodeBaseModel):
    """Breakdown of message tokens by category."""

    tool_call_tokens: int
    tool_result_tokens: int
    attachment_tokens: int
    assistant_message_tokens: int
    user_message_tokens: int
    tool_calls_by_type: list[ContextUsageToolCallBreakdown]
    attachments_by_type: list[ContextUsageAttachmentBreakdown]


class SDKControlGetContextUsageResponse(ClaudeCodeBaseModel):
    """Breakdown of current context window usage by category."""

    categories: list[ContextUsageCategory]
    total_tokens: int
    max_tokens: int
    raw_max_tokens: int
    percentage: float
    grid_rows: list[list[ContextUsageGridCell]]
    model: str
    memory_files: list[ContextUsageMemoryFile]
    mcp_tools: list[ContextUsageMcpTool]
    deferred_builtin_tools: list[ContextUsageDeferredBuiltinTool] | None = None
    system_tools: list[ContextUsageSystemTool] | None = None
    system_prompt_sections: list[ContextUsageSystemPromptSection] | None = None
    agents: list[ContextUsageAgent]
    slash_commands: ContextUsageSlashCommands | None = None
    skills: ContextUsageSkills | None = None
    auto_compact_threshold: int | None = None
    is_auto_compact_enabled: bool
    message_breakdown: ContextUsageMessageBreakdown | None = None
    api_usage: Usage | None = None
