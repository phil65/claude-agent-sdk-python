"""Content blocks, message types, and stream events."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from clawd_code_sdk.models.base import IS_DEV, ClaudeCodeBaseModel


class ModelUsage(ClaudeCodeBaseModel):
    """Cumulative token usage per model, accumulated across the entire session."""

    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int
    cache_creation_input_tokens: int
    web_search_requests: int
    cost_usd: float = Field(default=..., alias="costUSD")
    context_window: int
    max_output_tokens: int


class Usage(BaseModel):
    """Token usage counters.

    Used both for per-turn snapshots (on ResultMessage) and as an accumulator
    (on ClaudeSDKClient.query_usage / session_usage).
    """

    input_tokens: int = 0
    """The number of input tokens which were used."""
    output_tokens: int = 0
    """The number of output tokens which were used."""
    cache_creation_input_tokens: int = 0
    """The number of input tokens used to create the cache entry."""
    cache_read_input_tokens: int = 0
    """The number of input tokens read from the cache."""
    model_config = ConfigDict(extra="forbid" if IS_DEV else "ignore", use_attribute_docstrings=True)

    @property
    def total_tokens(self) -> int:
        """Sum of all token fields."""
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_creation_input_tokens
            + self.cache_read_input_tokens
        )

    def accumulate(self, usage: Usage) -> None:
        """Add another Usage's values to this one."""
        self.input_tokens += usage.input_tokens
        self.output_tokens += usage.output_tokens
        self.cache_creation_input_tokens += usage.cache_creation_input_tokens
        self.cache_read_input_tokens += usage.cache_read_input_tokens

    def reset(self) -> None:
        """Reset all counters to zero."""
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_creation_input_tokens = 0
        self.cache_read_input_tokens = 0

    def to_otel(self, *, partial: bool = False) -> dict[str, int]:
        """Extract usage metrics from a Claude usage object or dict.

        Args:
            usage: A usage object or dict from the SDK.
            partial: If True, prefix attribute names with ``gen_ai.usage.partial.``
                instead of ``gen_ai.usage.``. Used for chat spans where per-message
                usage from the SDK is unreliable.
        """
        prefix = "gen_ai.usage.partial." if partial else "gen_ai.usage."
        result: dict[str, int] = {}
        # input_tokens is the *total* input token count.
        # The Anthropic API's input_tokens only counts uncached tokens,
        # so we sum input + cache_read + cache_creation to get the actual total.
        input_tokens = self.input_tokens
        cache_read = self.cache_read_input_tokens
        cache_creation = self.cache_creation_input_tokens
        if total_input := (input_tokens + cache_read + cache_creation):
            result[f"{prefix}input_tokens"] = total_input

        result[f"{prefix}output_tokens"] = self.output_tokens

        if cache_read:
            result[f"{prefix}cache_read.input_tokens"] = cache_read
        if cache_creation:
            result[f"{prefix}cache_creation.input_tokens"] = cache_creation

        return result
