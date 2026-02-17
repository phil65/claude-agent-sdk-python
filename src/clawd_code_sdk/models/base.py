"""Base type aliases, literals, and thinking configuration types."""

from __future__ import annotations

from typing import Literal, TypedDict


# Permission modes
# - 'default': Standard behavior, prompts for dangerous operations
# - 'acceptEdits': Auto-accept file edit operations
# - 'bypassPermissions': Bypass all permission checks (requires allowDangerouslySkipPermissions)
# - 'plan': Planning mode, no actual tool execution
# - 'delegate': Delegate mode, restricts to only Teammate and Task tools
# - 'dontAsk': Don't prompt for permissions, deny if not pre-approved
PermissionMode = Literal[
    "default", "acceptEdits", "bypassPermissions", "plan", "delegate", "dontAsk"
]

# SDK Beta features - see https://docs.anthropic.com/en/api/beta-headers
SdkBeta = Literal[
    "context-1m-2025-08-07",  # Extended 1M context window
    "clear-thinking-20250115",  # Clear thinking blocks from previous turns to reduce token usage
]

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
ApiKeySource = Literal["user", "project", "org", "temporary"]

# Agent definitions
SettingSource = Literal["user", "project", "local"]


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
