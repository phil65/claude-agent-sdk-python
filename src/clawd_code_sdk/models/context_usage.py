"""Context window usage breakdown models."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from clawd_code_sdk.models.base import ClaudeCodeBaseModel
from clawd_code_sdk.models.usage import ModelUsage, Usage


ContextUsageCategoryId = Literal[
    "system_prompt",
    "system_tools",
    "mcp_tools",
    "mcp_instructions",
    "mcp_tools_deferred",
    "system_tools_deferred",
    "custom_agents",
    "memory_files",
    "skills",
    "messages",
    "autocompact_buffer",
    "compact_buffer",
    "free_space",
]
ContextUsageKind = Literal["used", "free", "buffer", "deferred"]


class ContextUsageCategory(ClaudeCodeBaseModel):
    """A single category in the context usage breakdown."""

    id: ContextUsageCategoryId | None = None
    name: str
    tokens: int
    color: str
    is_deferred: bool | None = None
    kind: ContextUsageKind | None = None


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


class ContextUsageMcpInstructions(ClaudeCodeBaseModel):
    """MCP server instructions contributing to context usage."""

    server_name: str
    tokens: int


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
    plugin_id: str | None = None
    path: str | None = None
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
    plugin_name: str | None = None
    plugin_id: str | None = None
    path: str | None = None
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
    redirected_context_tokens: int
    unattributed_tokens: int
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
    mcp_instructions: list[ContextUsageMcpInstructions] | None = None
    deferred_builtin_tools: list[ContextUsageDeferredBuiltinTool] | None = None
    system_tools: list[ContextUsageSystemTool] | None = None
    system_prompt_sections: list[ContextUsageSystemPromptSection] | None = None
    agents: list[ContextUsageAgent]
    slash_commands: ContextUsageSlashCommands | None = None
    skills: ContextUsageSkills | None = None
    auto_compact_threshold: int | None = None
    autocompact_source: str | None = Field(default=None, alias="autocompactSource")
    """Where the auto-compact threshold came from, e.g. "model-default" (undocumented)."""
    is_auto_compact_enabled: bool
    message_breakdown: ContextUsageMessageBreakdown | None = None
    api_usage: Usage | None = None


# --- Compact context usage snapshot attached to assistant messages (snake_case wire format) ---


class SDKContextUsageOverLimit(ClaudeCodeBaseModel):
    """How far the context is over its limit."""

    tokens_over: int
    kind: Literal["hard_limit", "compaction_window"]


class SDKContextUsageCategory(ClaudeCodeBaseModel):
    """A category in the compact context usage snapshot."""

    name: str
    tokens: int
    kind: ContextUsageKind


class SDKContextUsageMcpTool(ClaudeCodeBaseModel):
    """MCP tool entry in the compact context usage snapshot."""

    name: str
    server_name: str
    tokens: int


class SDKContextUsageMemoryFile(ClaudeCodeBaseModel):
    """Memory file entry in the compact context usage snapshot."""

    path: str
    type: str
    tokens: int


class SDKContextUsageAgent(ClaudeCodeBaseModel):
    """Agent entry in the compact context usage snapshot."""

    agent_type: str
    source: str
    tokens: int


class SDKContextUsageSkill(ClaudeCodeBaseModel):
    """Skill entry in the compact context usage snapshot."""

    name: str
    source: str
    plugin_name: str | None = None
    tokens: int


class SDKContextUsage(ClaudeCodeBaseModel):
    """Compact context usage snapshot, attached to assistant messages."""

    model: str
    total_tokens: int
    raw_max_tokens: int
    percentage: float
    over_limit: SDKContextUsageOverLimit | None = None
    categories: list[SDKContextUsageCategory]
    mcp_tools: list[SDKContextUsageMcpTool]
    memory_files: list[SDKContextUsageMemoryFile]
    agents: list[SDKContextUsageAgent]
    skills: list[SDKContextUsageSkill] | None = None


# --- Usage report (session cost + rate limits) attached to assistant messages ---


class UsageReportSession(ClaudeCodeBaseModel):
    """Session-level cost/usage totals."""

    total_cost_usd: float
    total_api_duration_ms: float
    total_duration_ms: float
    total_lines_added: int
    total_lines_removed: int
    model_usage: dict[str, ModelUsage]


class UsageReportDisplayName(ClaudeCodeBaseModel):
    """Wrapper holding a display name."""

    display_name: str


class UsageReportLimitScope(ClaudeCodeBaseModel):
    """Scope of a rate limit."""

    model: UsageReportDisplayName | None = None
    surface: UsageReportDisplayName | None = None


class UsageReportLimit(ClaudeCodeBaseModel):
    """A single rate limit entry."""

    kind: str
    group: str
    percent: float
    resets_at: str | None
    scope: UsageReportLimitScope | None = None
    severity: str
    is_active: bool


class UsageReportExtraUsage(ClaudeCodeBaseModel):
    """Extra (overage) usage state."""

    is_enabled: bool
    monthly_limit: float | None
    used_credits: float | None
    utilization: float | None
    currency: str | None = None


class UsageReportRateLimits(ClaudeCodeBaseModel):
    """Rate limit state."""

    limits: list[UsageReportLimit] | None
    extra_usage: UsageReportExtraUsage | None = None


class SDKUsageReport(ClaudeCodeBaseModel):
    """Session usage report (same data as /usage)."""

    session: UsageReportSession
    rate_limits: UsageReportRateLimits | None
