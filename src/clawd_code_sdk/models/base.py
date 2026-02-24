"""Base type aliases, literals, and thinking configuration types."""

from __future__ import annotations

from typing import Literal, TypedDict

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


class ClaudeCodeBaseModel(BaseModel):
    """Base model for all Claude Code Pydantic models."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel, extra="forbid")


# Thinking configuration types
class ThinkingConfigAdaptive(TypedDict):
    """Adaptive thinking configuration - model decides thinking budget."""

    type: Literal["adaptive"]


class ThinkingConfigEnabled(TypedDict):
    """Enabled thinking configuration with explicit token budget."""

    type: Literal["enabled"]
    budget_tokens: int


class ThinkingConfigDisabled(TypedDict):
    """Disabled thinking configuration."""

    type: Literal["disabled"]


ThinkingConfig = ThinkingConfigAdaptive | ThinkingConfigEnabled | ThinkingConfigDisabled
