"""Claude SDK for Python."""

from __future__ import annotations


from ._errors import (
    APIError,
    AuthenticationError,
    BillingError,
    ClaudeSDKError,
    CLIConnectionError,
    CLIJSONDecodeError,
    CLINotFoundError,
    InvalidRequestError,
    ProcessError,
    RateLimitError,
    ServerError,
)
from ._internal.transport import Transport
from ._version import __version__
from .anthropic_types import ToolResultContentBlock
from .client import ClaudeSDKClient
from .models import (
    AgentDefinition,
    AssistantMessage,
    BaseHookInput,
    CanUseTool,
    ClaudeAgentOptions,
    ContentBlock,
    HookCallback,
    HookContext,
    HookInput,
    HookJSONOutput,
    HookMatcher,
    McpSdkServerConfig,
    McpServerConfig,
    Message,
    NotificationHookInput,
    NotificationHookSpecificOutput,
    PermissionMode,
    PermissionRequestHookInput,
    PermissionRequestHookSpecificOutput,
    PermissionResult,
    PermissionResultAllow,
    PermissionResultDeny,
    PermissionUpdate,
    PostToolUseFailureHookInput,
    PostToolUseFailureHookSpecificOutput,
    PostToolUseHookInput,
    PreCompactHookInput,
    PreToolUseHookInput,
    ResultMessage,
    SandboxIgnoreViolations,
    SandboxNetworkConfig,
    SandboxSettings,
    SdkBeta,
    SdkPluginConfig,
    SettingSource,
    StopHookInput,
    SubagentStartHookInput,
    SubagentStartHookSpecificOutput,
    SubagentStopHookInput,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ThinkingConfig,
    ThinkingConfigAdaptive,
    ThinkingConfigDisabled,
    ThinkingConfigEnabled,
    ToolPermissionContext,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    UserPromptMessage,
    UserPromptMessageContent,
    UserPromptSubmitHookInput,
)
from .query import query
from .mcp_utils import SdkMcpTool, tool, create_sdk_mcp_server

# MCP Server Support

__cli_version__ = "2.1.11"


__all__ = [
    # Main exports
    "query",
    "__version__",
    # Transport
    "Transport",
    "ClaudeSDKClient",
    # Types
    "PermissionMode",
    "McpServerConfig",
    "McpSdkServerConfig",
    "UserMessage",
    "UserPromptMessage",
    "UserPromptMessageContent",
    "AssistantMessage",
    "SystemMessage",
    "ResultMessage",
    "Message",
    "ClaudeAgentOptions",
    "TextBlock",
    "ThinkingBlock",
    "ToolUseBlock",
    "ToolResultContentBlock",
    "ToolResultBlock",
    "ContentBlock",
    # Tool callbacks
    "CanUseTool",
    "ToolPermissionContext",
    "PermissionResult",
    "PermissionResultAllow",
    "PermissionResultDeny",
    "PermissionUpdate",
    # Hook support
    "HookCallback",
    "HookContext",
    "HookInput",
    "BaseHookInput",
    "PreToolUseHookInput",
    "PostToolUseHookInput",
    "PostToolUseFailureHookInput",
    "PostToolUseFailureHookSpecificOutput",
    "UserPromptSubmitHookInput",
    "StopHookInput",
    "SubagentStopHookInput",
    "PreCompactHookInput",
    "NotificationHookInput",
    "SubagentStartHookInput",
    "PermissionRequestHookInput",
    "NotificationHookSpecificOutput",
    "SubagentStartHookSpecificOutput",
    "PermissionRequestHookSpecificOutput",
    "HookJSONOutput",
    "HookMatcher",
    # Agent support
    "AgentDefinition",
    "SettingSource",
    # Thinking configuration
    "ThinkingConfig",
    "ThinkingConfigAdaptive",
    "ThinkingConfigEnabled",
    "ThinkingConfigDisabled",
    # Plugin support
    "SdkPluginConfig",
    # Beta support
    "SdkBeta",
    # Sandbox support
    "SandboxSettings",
    "SandboxNetworkConfig",
    "SandboxIgnoreViolations",
    # MCP Server Support
    "create_sdk_mcp_server",
    "tool",
    "SdkMcpTool",
    # Errors
    "ClaudeSDKError",
    "CLIConnectionError",
    "CLINotFoundError",
    "ProcessError",
    "CLIJSONDecodeError",
    # API Errors
    "APIError",
    "AuthenticationError",
    "BillingError",
    "RateLimitError",
    "InvalidRequestError",
    "ServerError",
]
