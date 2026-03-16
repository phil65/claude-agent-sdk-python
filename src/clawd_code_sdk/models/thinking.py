"""Thinking configuration models."""

from __future__ import annotations

from typing import Literal

from clawd_code_sdk.models.base import ClaudeCodeBaseModel


ThinkingDisplay = Literal["summarized", "omitted"]


# Thinking configuration types
class ThinkingConfigAdaptive(ClaudeCodeBaseModel):
    """Adaptive thinking configuration - model decides thinking budget."""

    type: Literal["adaptive"] = "adaptive"

    display: ThinkingDisplay | None = None
    """Controls how thinking content appears in the response.
    When set to `summarized`, thinking is returned normally. When set to `omitted`,
    thinking content is redacted but a signature is returned for multi-turn
    continuity. Defaults to `summarized`.
    """


class ThinkingConfigEnabled(ClaudeCodeBaseModel):
    """Enabled thinking configuration with explicit token budget."""

    type: Literal["enabled"] = "enabled"

    budget_tokens: int
    """Determines how many tokens Claude can use for its internal reasoning process.
    Larger budgets can enable more thorough analysis for complex problems, improving
    response quality.
    Must be ≥1024 and less than `max_tokens`.
    See
    [extended thinking](https://docs.claude.com/en/docs/build-with-claude/extended-thinking)
    for details.
    """

    display: ThinkingDisplay | None = None
    """Controls how thinking content appears in the response.
    When set to `summarized`, thinking is returned normally. When set to `omitted`,
    thinking content is redacted but a signature is returned for multi-turn
    continuity. Defaults to `summarized`.
    """


class ThinkingConfigDisabled(ClaudeCodeBaseModel):
    """Disabled thinking configuration."""

    type: Literal["disabled"] = "disabled"


ThinkingConfig = ThinkingConfigAdaptive | ThinkingConfigEnabled | ThinkingConfigDisabled
