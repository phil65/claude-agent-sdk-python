"""Content blocks, message types, and stream events."""

from typing import Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field

from clawd_code_sdk.models.base import IS_DEV, ClaudeCodeBaseModel


class AgentServerToolUse(TypedDict):
    """Server-side tool usage statistics."""

    web_search_requests: int
    """Number of web search requests made."""
    web_fetch_requests: int
    """Number of web fetch requests made."""


class ModelUsage(ClaudeCodeBaseModel):
    """Cumulative token usage per model, accumulated across the entire session."""

    input_tokens: int
    output_tokens: int
    thinking_tokens: int | None = None
    cache_read_input_tokens: int
    cache_creation_input_tokens: int
    cache_creation_ephemeral5m_input_tokens: int | None = Field(
        default=None, alias="cacheCreationEphemeral5mInputTokens"
    )
    cache_creation_ephemeral1h_input_tokens: int | None = Field(
        default=None, alias="cacheCreationEphemeral1hInputTokens"
    )
    web_search_requests: int
    cost_usd: float = Field(default=..., alias="costUSD")
    context_window: int
    max_output_tokens: int
    canonical_model: str | None = None
    provider: str | None = None
    cost_basis: Literal["list", "managed", "unknown"] | None = None


class CacheCreationUsage(BaseModel):
    """Cache-write tokens split by TTL."""

    model_config = ConfigDict(extra="forbid" if IS_DEV else "ignore")

    ephemeral_5m_input_tokens: int = 0
    ephemeral_1h_input_tokens: int = 0


class OutputTokensDetails(BaseModel):
    """Breakdown of output tokens."""

    model_config = ConfigDict(extra="forbid" if IS_DEV else "ignore")

    thinking_tokens: int = 0


class UsageIteration(BaseModel):
    """Usage of a single API iteration within a turn."""

    model_config = ConfigDict(extra="forbid" if IS_DEV else "ignore")

    type: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_creation: CacheCreationUsage | None = None


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
    cache_creation: CacheCreationUsage | None = None
    """Cache-write tokens split by TTL."""
    server_tool_use: AgentServerToolUse | None = None
    """Server-side tool usage counters."""
    output_tokens_details: OutputTokensDetails | None = None
    """Breakdown of output tokens."""
    service_tier: str | None = None
    """Service tier the request was served on (e.g. "standard")."""
    inference_geo: str | None = None
    """Inference geography (e.g. "global")."""
    speed: str | None = None
    """Speed mode (e.g. "standard", "fast")."""
    iterations: list[UsageIteration] | None = None
    """Per-iteration usage for the turn."""
    fallback_credit: Any = None
    """Fallback credit info (may be null)."""
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
