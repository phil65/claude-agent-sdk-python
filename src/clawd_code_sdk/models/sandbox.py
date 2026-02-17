"""Sandbox configuration types."""

from __future__ import annotations

from typing import TypedDict


# Sandbox configuration types
class SandboxNetworkConfig(TypedDict, total=False):
    """Network configuration for sandbox.

    Attributes:
        allowUnixSockets: Unix socket paths accessible in sandbox (e.g., SSH agents).
        allowAllUnixSockets: Allow all Unix sockets (less secure).
        allowLocalBinding: Allow binding to localhost ports (macOS only).
        httpProxyPort: HTTP proxy port if bringing your own proxy.
        socksProxyPort: SOCKS5 proxy port if bringing your own proxy.
    """

    allowUnixSockets: list[str]
    allowAllUnixSockets: bool
    allowLocalBinding: bool
    httpProxyPort: int
    socksProxyPort: int


class SandboxIgnoreViolations(TypedDict, total=False):
    """Violations to ignore in sandbox.

    Attributes:
        file: File paths for which violations should be ignored.
        network: Network hosts for which violations should be ignored.
    """

    file: list[str]
    network: list[str]


class SandboxSettings(TypedDict, total=False):
    """Sandbox settings configuration.

    This controls how Claude Code sandboxes bash commands for filesystem
    and network isolation.

    **Important:** Filesystem and network restrictions are configured via permission
    rules, not via these sandbox settings:
    - Filesystem read restrictions: Use Read deny rules
    - Filesystem write restrictions: Use Edit allow/deny rules
    - Network restrictions: Use WebFetch allow/deny rules

    Attributes:
        enabled: Enable bash sandboxing (macOS/Linux only). Default: False
        autoAllowBashIfSandboxed: Auto-approve bash commands when sandboxed. Default: True
        excludedCommands: Commands that should run outside the sandbox (e.g., ["git", "docker"])
        allowUnsandboxedCommands: Allow commands to bypass sandbox via dangerouslyDisableSandbox.
            When False, all commands must run sandboxed (or be in excludedCommands). Default: True
        network: Network configuration for sandbox.
        ignoreViolations: Violations to ignore.
        enableWeakerNestedSandbox: Enable weaker sandbox for unprivileged Docker environments
            (Linux only). Reduces security. Default: False

    Example:
        ```python
        sandbox_settings: SandboxSettings = {
            "enabled": True,
            "autoAllowBashIfSandboxed": True,
            "excludedCommands": ["docker"],
            "network": {
                "allowUnixSockets": ["/var/run/docker.sock"],
                "allowLocalBinding": True
            }
        }
        ```
    """

    enabled: bool
    autoAllowBashIfSandboxed: bool
    excludedCommands: list[str]
    allowUnsandboxedCommands: bool
    network: SandboxNetworkConfig
    ignoreViolations: SandboxIgnoreViolations
    enableWeakerNestedSandbox: bool
