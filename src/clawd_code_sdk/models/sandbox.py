"""Sandbox configuration types."""

from __future__ import annotations

from .base import ClaudeCodeBaseModel


class SandboxNetworkConfig(ClaudeCodeBaseModel):
    """Network configuration for sandbox."""

    allow_unix_sockets: list[str] | None = None
    """Unix socket paths accessible in sandbox (e.g., SSH agents)."""

    allow_all_unix_sockets: bool | None = None
    """Allow all Unix sockets (less secure)."""

    allow_local_binding: bool | None = None
    """Allow binding to localhost ports (macOS only)."""

    http_proxy_port: int | None = None
    """HTTP proxy port if bringing your own proxy."""

    socks_proxy_port: int | None = None
    """SOCKS5 proxy port if bringing your own proxy."""


class SandboxIgnoreViolations(ClaudeCodeBaseModel):
    """Violations to ignore in sandbox."""

    file: list[str] | None = None
    """File paths for which violations should be ignored."""

    network: list[str] | None = None
    """Network hosts for which violations should be ignored."""


class SandboxSettings(ClaudeCodeBaseModel):
    """Sandbox settings configuration.

    This controls how Claude Code sandboxes bash commands for filesystem
    and network isolation.

    **Important:** Filesystem and network restrictions are configured via permission
    rules, not via these sandbox settings:
    - Filesystem read restrictions: Use Read deny rules
    - Filesystem write restrictions: Use Edit allow/deny rules
    - Network restrictions: Use WebFetch allow/deny rules

    Example:
        ```python
        sandbox_settings = SandboxSettings(
            enabled=True,
            auto_allow_bash_if_sandboxed=True,
            excluded_commands=["docker"],
            network=SandboxNetworkConfig(
                allow_unix_sockets=["/var/run/docker.sock"],
                allow_local_binding=True,
            ),
        )
        ```
    """

    enabled: bool | None = None
    """Enable bash sandboxing (macOS/Linux only)."""

    auto_allow_bash_if_sandboxed: bool | None = None
    """Auto-approve bash commands when sandboxed."""

    excluded_commands: list[str] | None = None
    """Commands that should run outside the sandbox (e.g., ``["git", "docker"]``)."""

    allow_unsandboxed_commands: bool | None = None
    """Allow commands to bypass sandbox via ``dangerouslyDisableSandbox``.

    When False, all commands must run sandboxed (or be in ``excluded_commands``).
    """

    network: SandboxNetworkConfig | None = None
    """Network configuration for sandbox."""

    ignore_violations: SandboxIgnoreViolations | None = None
    """Violations to ignore."""

    enable_weaker_nested_sandbox: bool | None = None
    """Enable weaker sandbox for unprivileged Docker environments (Linux only).

    Reduces security.
    """
