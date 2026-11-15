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
    # "delegate",  # Delegate mode, restricts to only Teammate and Task tools
    "dontAsk",  # Don't prompt for permissions, deny if not pre-approved
    "auto",  # Auto-approves tool calls with background safety checks
]
SdkBeta = Literal["context-1m-2025-08-07"]  # see https://docs.anthropic.com/en/api/beta-headers
ModelName = Literal["sonnet", "opus", "haiku"]
PermissionBehavior = Literal["allow", "deny", "ask"]
HookPermissionDecision = Literal["allow", "deny", "ask", "defer"]
ReasoningEffort = Literal["low", "medium", "high", "xhigh", "max"]
TaskStatus = Literal["completed", "failed", "stopped"]
CompactionTrigger = Literal["auto", "manual"]
ElicitationMode = Literal["form", "url"]
ElicitationAction = Literal["accept", "decline", "cancel"]
FastModeState = Literal["off", "cooldown", "on"]
PermissionDecisionClassification = Literal["user_temporary", "user_permanent", "user_reject"]
EffortLevel = Literal["low", "medium", "high", "xhigh", "max"]
AssistantMessageError = Literal[
    "authentication_failed",
    "oauth_org_not_allowed",
    "account_on_hold",
    "verification_required",
    "billing_error",
    "rate_limit",
    "overloaded",
    "invalid_request",
    "model_not_found",
    "server_error",
    "unknown",
    "max_output_tokens",
    "cloud_credential_error",
]
StopReason = Literal[
    "end_turn",
    "max_tokens",
    "stop_sequence",
    "tool_use",
    "pause_turn",
    "refusal",
    "model_context_window_exceeded",
]
ApiKeySource = Literal[
    "ANTHROPIC_API_KEY",
    "apiKeyHelper",
    "/login managed key",
    "none",
    "user",
    "project",
    "org",
    "temporary",
    "oauth",
    "env",
    "config",
]
SettingSource = Literal["user", "project", "local"]
ToolName = Literal[
    "Agent",
    "Artifact",
    "AskUserQuestion",
    "Bash",
    "ClaudeDesign",
    "CronCreate",
    "CronDelete",
    "CronList",
    "Edit",
    "EndConversation",
    "EnterPlanMode",
    "EnterWorktree",
    "ExitPlanMode",
    "ExitWorktree",
    "Glob",
    "Grep",
    "ListAgents",
    "ListMcpResourcesTool",
    "LSP",
    "Monitor",
    "NotebookEdit",
    "OfferChromeSetup",
    "PowerShell",
    "Projects",
    "propose_skills",
    "ProposeGoal",
    "PushNotification",
    "Read",
    "ReadMcpResourceDirTool",
    "ReadMcpResourceTool",
    "ReadNotifications",
    "RemoteTrigger",
    "ReportFindings",
    "ScheduleWakeup",
    "SendFeedback",
    "SendMessage",
    "SendUserFile",
    "SendUserMessage",
    "ShareOnboardingGuide",
    "ShowOnboardingRolePicker",
    "Skill",
    "SubagentHandback",
    "TaskCreate",
    "TaskGet",
    "TaskList",
    "TaskStop",
    "TaskUpdate",
    "TodoWrite",
    "ToolSearch",
    "WaitForMcpServers",
    "WebFetch",
    "WebSearch",
    "Workflow",
    "Write",
    # Legacy names (still accepted by older CLIs / aliases)
    "Task",
    "TaskOutput",
    "BashOutput",
    "KillBash",
    "ListMcpResources",
    "ReadMcpResource",
    "SubscribeMcpResource",
    "UnsubscribeMcpResource",
    "SubscribePolling",
    "UnsubscribePolling",
    "Config",
]
TerminalReason = Literal[
    "blocking_limit",
    "rapid_refill_breaker",
    "prompt_too_long",
    "image_error",
    "model_error",
    "api_error",
    "malformed_tool_use_exhausted",
    "aborted_streaming",
    "aborted_tools",
    "stop_hook_prevented",
    "hook_stopped",
    "tool_deferred",
    "max_turns",
    "background_requested",
    "completed",
    "budget_exhausted",
    "structured_output_retry_exhausted",
    "tool_deferred_unavailable",
    "turn_setup_failed",
]
FastModeDisabledReason = Literal[
    "free",
    "preference",
    "extra_usage_disabled",
    "network_error",
    "unknown",
    "not_first_party",
    "disabled_by_env",
    "model_not_allowed",
    "sdk_opt_in_required",
    "pending",
]
StartupFailureReason = Literal[
    "org_pin_api_key_conflict",
    "provider_not_allowed",
    "org_verify_failed",
    "org_pin_mismatch",
    "managed_settings_invalid",
    "remote_settings_required_unavailable",
    "gateway_signin_required",
    "gateway_access_denied",
    "proxy_invalid",
    "temp_dir_unusable",
    "cwd_unavailable",
    "shell_tool_missing",
    "session_held_by_background",
    "worktree_resume_refused",
    "worktree_unverified",
    "cli_version_too_old",
    "bypass_root",
    "org_config_required_unavailable",
    "org_config_refused",
    "sandbox_required_unavailable",
    "initialize_not_first",
    "config_file_invalid",
    "managed_settings_not_delivered",
]
IS_DEV = "pytest" in sys.modules
SYSTEM_PROMPT_DYNAMIC_BOUNDARY = "__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__"


class ClaudeCodeBaseModel(BaseModel):
    """Base model for all Claude Code Pydantic models."""

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        extra="forbid" if IS_DEV else "ignore",
        defer_build=True,
        use_attribute_docstrings=True,
    )
