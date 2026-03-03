"""Thinking configuration models."""

from __future__ import annotations

from typing import Literal

from clawd_code_sdk.models.base import ClaudeCodeBaseModel


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
