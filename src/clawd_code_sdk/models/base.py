"""Base type aliases, literals, and thinking configuration types."""

from __future__ import annotations

import sys
from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


PermissionMode = Literal[
    "default",  #  Standard behavior, prompts for dangerous operations
    "acceptEdits",  # Auto-accept file edit operations
    "bypassPermissions",  # Bypass all permission checks (requires allowDangerouslySkipPermissions)
    "plan",  # Planning mode, no actual tool execution
    "delegate",  # Delegate mode, restricts to only Teammate and Task tools
    "dontAsk",  # Don't prompt for permissions, deny if not pre-approved
]
SdkBeta = Literal["context-1m-2025-08-07"]  # see https://docs.anthropic.com/en/api/beta-headers
ModelName = Literal["sonnet", "opus", "haiku"]
PermissionBehavior = Literal["allow", "deny", "ask"]
ReasoningEffort = Literal["low", "medium", "high", "max"]
TaskStatus = Literal["completed", "failed", "stopped"]
CompactionTrigger = Literal["auto", "manual"]
ElicitationMode = Literal["form", "url"]
ElicitationAction = Literal["accept", "decline", "cancel"]

StopReason = Literal[
    "end_turn",
    "max_tokens",
    "stop_sequence",
    "tool_use",
    "pause_turn",
    "refusal",
    "model_context_window_exceeded",
]
ApiKeySource = Literal["none", "env", "config", "ANTHROPIC_API_KEY"]
SettingSource = Literal["user", "project", "local"]
ToolName = Literal[
    "Task",
    "TaskOutput",
    "Bash",
    "Glob",
    "Grep",
    "ExitPlanMode",
    "Read",
    "Edit",
    "Write",
    "NotebookEdit",
    "WebFetch",
    "TodoWrite",
    "WebSearch",
    "TaskStop",
    "AskUserQuestion",
    "Skill",
    "EnterPlanMode",
    "EnterWorktree",
    "ToolSearch",
]
IS_DEV = "pytest" in sys.modules


class ClaudeCodeBaseModel(BaseModel):
    """Base model for all Claude Code Pydantic models."""

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        extra="forbid" if IS_DEV else "ignore",
    )


# Thinking configuration types
class ThinkingConfigAdaptive(ClaudeCodeBaseModel):
    """Adaptive thinking configuration - model decides thinking budget."""

    type: Literal["adaptive"] = "adaptive"


class ThinkingConfigEnabled(ClaudeCodeBaseModel):
    """Enabled thinking configuration with explicit token budget."""

    type: Literal["enabled"] = "enabled"
    budget_tokens: int


class ThinkingConfigDisabled(ClaudeCodeBaseModel):
    """Disabled thinking configuration."""

    type: Literal["disabled"] = "disabled"


ThinkingConfig = ThinkingConfigAdaptive | ThinkingConfigEnabled | ThinkingConfigDisabled
