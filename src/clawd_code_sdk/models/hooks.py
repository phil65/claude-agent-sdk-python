"""Hook system types: inputs, outputs, matchers, and callbacks."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import field
from typing import Any, Literal, NotRequired, TypedDict

from pydantic import BaseModel

from clawd_code_sdk.models.base import (  # noqa: TC001
    AssistantMessageError,
    CompactionTrigger,
    ElicitationAction,
    ElicitationMode,
    HookPermissionDecision,
)
from clawd_code_sdk.models.permissions import PermissionUpdate  # noqa: TC001


HookEvent = Literal[
    "PreToolUse",
    "PostToolUse",
    "PostToolUseFailure",
    "UserPromptSubmit",
    "Stop",
    "StopFailure",
    "SubagentStop",
    "UserPromptExpansion",
    "PreCompact",
    "PostCompact",
    "Notification",
    "SubagentStart",
    "PermissionRequest",
    "PermissionDenied",
    "SessionStart",
    "SessionEnd",
    "Setup",
    "TeammateIdle",
    "TaskCreated",
    "TaskCompleted",
    "Elicitation",
    "ElicitationResult",
    "ConfigChange",
    "WorktreeCreate",
    "WorktreeRemove",
    "InstructionsLoaded",
    "CwdChanged",
    "FileChanged",
]
LoadReason = Literal["session_start", "nested_traversal", "path_glob_match", "include", "compact"]
SessionEndReason = Literal[
    "clear",
    "resume",
    "logout",
    "prompt_input_exit",
    "other",
    "bypass_permissions_disabled",
]
# ---------------------------------------------------------------------------
# Declarative hook handler configs (for agent/skill frontmatter & settings)
# ---------------------------------------------------------------------------
# These TypedDicts represent the JSON-serializable hook handler format used in
# agent definitions, skill frontmatter, and settings files. They are distinct
# from HookCallback (Python callables used for programmatic SDK hooks).
#
# See https://code.claude.com/docs/en/hooks#hook-handler-fields

# Functional syntax required because "async" is a Python keyword.
CommandHookHandler = TypedDict(
    "CommandHookHandler",
    {
        "type": Literal["command"],
        "command": str,
        "timeout": NotRequired[float],
        "async": NotRequired[bool],
        "statusMessage": NotRequired[str],
        "once": NotRequired[bool],
    },
)
"""Bash command hook handler.

See https://code.claude.com/docs/en/hooks#command-hook-fields
"""


class PromptHookHandler(TypedDict):
    """LLM prompt hook handler.

    See https://code.claude.com/docs/en/hooks#prompt-and-agent-hook-fields
    """

    type: Literal["prompt"]
    prompt: str
    model: NotRequired[str]
    timeout: NotRequired[float]
    statusMessage: NotRequired[str]
    once: NotRequired[bool]


class AgentHookHandler(TypedDict):
    """Agent hook handler with multi-turn tool access.

    See https://code.claude.com/docs/en/hooks#agent-based-hooks
    """

    type: Literal["agent"]
    prompt: str
    model: NotRequired[str]
    timeout: NotRequired[float]
    statusMessage: NotRequired[str]


HookHandler = CommandHookHandler | PromptHookHandler | AgentHookHandler
"""Union of all declarative hook handler types."""


class HookMatcherConfig(TypedDict):
    """Declarative hook matcher for agent/skill/settings hook configuration.

    See https://code.claude.com/docs/en/hooks#matcher-patterns
    """

    matcher: NotRequired[str | None]
    hooks: list[HookHandler]


# Hook config type for AgentDefinition.hooks
AgentHooksConfig = dict[HookEvent, list[HookMatcherConfig]]
"""Type alias for the hooks field on AgentDefinition.

Maps hook event names to lists of matcher configs. Example::

    hooks: AgentHooksConfig = {
        "PreToolUse": [
            {
                "matcher": "Bash",
                "hooks": [{"type": "command", "command": "./check.sh"}],
            }
        ],
    }
"""


# Hook input types - strongly typed for each hook event
class BaseHookInput(TypedDict):
    """Base hook input fields present across many hook events."""

    session_id: str
    transcript_path: str
    cwd: str
    permission_mode: NotRequired[str]


class PreToolUseHookInput(BaseHookInput):
    """Input data for PreToolUse hook events."""

    hook_event_name: Literal["PreToolUse"]
    tool_name: str
    tool_input: dict[str, Any]
    tool_use_id: str
    agent_id: NotRequired[str]
    agent_type: NotRequired[str]


class PostToolUseHookInput(BaseHookInput):
    """Input data for PostToolUse hook events."""

    hook_event_name: Literal["PostToolUse"]
    tool_name: str
    tool_input: dict[str, Any]
    tool_response: Any
    tool_use_id: str
    agent_id: NotRequired[str]
    agent_type: NotRequired[str]


class PostToolUseFailureHookInput(BaseHookInput):
    """Input data for PostToolUseFailure hook events."""

    hook_event_name: Literal["PostToolUseFailure"]
    tool_name: str
    tool_input: dict[str, Any]
    tool_use_id: str
    error: str
    is_interrupt: NotRequired[bool]
    agent_id: NotRequired[str]
    agent_type: NotRequired[str]


class UserPromptSubmitHookInput(BaseHookInput):
    """Input data for UserPromptSubmit hook events."""

    hook_event_name: Literal["UserPromptSubmit"]
    prompt: str
    session_title: NotRequired[str]


class StopHookInput(BaseHookInput):
    """Input data for Stop hook events."""

    hook_event_name: Literal["Stop"]
    stop_hook_active: bool


class StopFailureHookInput(BaseHookInput):
    """Input data for StopFailure hook events."""

    hook_event_name: Literal["StopFailure"]
    error: AssistantMessageError
    error_details: NotRequired[str]
    last_assistant_message: NotRequired[str]


class SubagentStopHookInput(BaseHookInput):
    """Input data for SubagentStop hook events."""

    hook_event_name: Literal["SubagentStop"]
    stop_hook_active: bool
    agent_id: str
    agent_transcript_path: str
    agent_type: str


class PreCompactHookInput(BaseHookInput):
    """Input data for PreCompact hook events."""

    hook_event_name: Literal["PreCompact"]
    trigger: CompactionTrigger
    custom_instructions: str | None


class PostCompactHookInput(BaseHookInput):
    """Input data for PostCompact hook events."""

    hook_event_name: Literal["PostCompact"]
    trigger: CompactionTrigger
    compact_summary: str


class NotificationHookInput(BaseHookInput):
    """Input data for Notification hook events."""

    hook_event_name: Literal["Notification"]
    message: str
    title: NotRequired[str]
    notification_type: str


class SubagentStartHookInput(BaseHookInput):
    """Input data for SubagentStart hook events."""

    hook_event_name: Literal["SubagentStart"]
    agent_id: str
    agent_type: str


class PermissionRequestHookInput(BaseHookInput):
    """Input data for PermissionRequest hook events."""

    hook_event_name: Literal["PermissionRequest"]
    tool_name: str
    tool_input: dict[str, Any]
    permission_suggestions: NotRequired[list[PermissionUpdate]]
    agent_id: NotRequired[str]
    agent_type: NotRequired[str]


class PermissionDeniedHookInput(BaseHookInput):
    """Input data for PermissionDenied hook events."""

    hook_event_name: Literal["PermissionDenied"]
    tool_name: str
    tool_input: Any
    tool_use_id: str
    reason: str


class SessionStartHookInput(BaseHookInput):
    """Input data for SessionStart hook events."""

    hook_event_name: Literal["SessionStart"]
    source: Literal["startup", "resume", "clear", "compact"]
    agent_type: NotRequired[str]
    model: NotRequired[str]


class SessionEndHookInput(BaseHookInput):
    """Input data for SessionEnd hook events."""

    hook_event_name: Literal["SessionEnd"]
    reason: SessionEndReason


class SetupHookInput(BaseHookInput):
    """Input data for Setup hook events."""

    hook_event_name: Literal["Setup"]
    trigger: Literal["init", "maintenance"]


class TeammateIdleHookInput(BaseHookInput):
    """Input data for TeammateIdle hook events."""

    hook_event_name: Literal["TeammateIdle"]
    teammate_name: str
    team_name: str


class TaskCompletedHookInput(BaseHookInput):
    """Input data for TaskCompleted hook events."""

    hook_event_name: Literal["TaskCompleted"]
    task_id: str
    task_subject: str
    task_description: NotRequired[str]
    teammate_name: NotRequired[str]
    team_name: NotRequired[str]


class TaskCreatedHookInput(BaseHookInput):
    """Input data for TaskCreated hook events."""

    hook_event_name: Literal["TaskCreated"]
    task_id: str
    task_subject: str
    task_description: NotRequired[str]
    teammate_name: NotRequired[str]
    team_name: NotRequired[str]


class ConfigChangeHookInput(BaseHookInput):
    """Input data for ConfigChange hook events."""

    hook_event_name: Literal["ConfigChange"]
    source: Literal[
        "user_settings", "project_settings", "local_settings", "policy_settings", "skills"
    ]
    file_path: NotRequired[str]


class WorktreeCreateHookInput(BaseHookInput):
    """Input data for WorktreeCreate hook events."""

    hook_event_name: Literal["WorktreeCreate"]
    name: str


class WorktreeRemoveHookInput(BaseHookInput):
    """Input data for WorktreeRemove hook events."""

    hook_event_name: Literal["WorktreeRemove"]
    worktree_path: str


class ElicitationHookInput(BaseHookInput):
    """Input data for Elicitation hook events."""

    hook_event_name: Literal["Elicitation"]
    mcp_server_name: str
    message: str
    mode: NotRequired[ElicitationMode]
    url: NotRequired[str]
    elicitation_id: NotRequired[str]
    requested_schema: NotRequired[dict[str, Any]]


class ElicitationResultHookInput(BaseHookInput):
    """Input data for ElicitationResult hook events."""

    hook_event_name: Literal["ElicitationResult"]
    mcp_server_name: str
    elicitation_id: NotRequired[str]
    mode: NotRequired[ElicitationMode]
    action: ElicitationAction
    content: NotRequired[dict[str, Any]]


class InstructionsLoadedHookInput(BaseHookInput):
    """Input data for InstructionsLoaded hook events."""

    hook_event_name: Literal["InstructionsLoaded"]
    file_path: str
    memory_type: Literal["User", "Project", "Local", "Managed"]
    load_reason: LoadReason
    globs: NotRequired[list[str]]
    trigger_file_path: NotRequired[str]
    parent_file_path: NotRequired[str]


class CwdChangedHookInput(BaseHookInput):
    """Input data for CwdChanged hook events."""

    hook_event_name: Literal["CwdChanged"]
    old_cwd: str
    new_cwd: str


class FileChangedHookInput(BaseHookInput):
    """Input data for FileChanged hook events."""

    hook_event_name: Literal["FileChanged"]
    file_path: str
    event: Literal["change", "add", "unlink"]


class UserPromptExpansionHookInput(BaseHookInput):
    """Input data for UserPromptExpansion hook events."""

    hook_event_name: Literal["UserPromptExpansion"]
    expansion_type: Literal["slash_command", "mcp_prompt"]
    command_name: str
    command_args: str
    command_source: NotRequired[str]
    prompt: str


# Union type for all hook inputs
HookInput = (
    PreToolUseHookInput
    | PostToolUseHookInput
    | PostToolUseFailureHookInput
    | UserPromptSubmitHookInput
    | StopHookInput
    | StopFailureHookInput
    | SubagentStopHookInput
    | PreCompactHookInput
    | PostCompactHookInput
    | NotificationHookInput
    | SubagentStartHookInput
    | PermissionRequestHookInput
    | PermissionDeniedHookInput
    | SessionStartHookInput
    | SessionEndHookInput
    | SetupHookInput
    | TeammateIdleHookInput
    | TaskCreatedHookInput
    | TaskCompletedHookInput
    | ElicitationHookInput
    | ElicitationResultHookInput
    | ConfigChangeHookInput
    | InstructionsLoadedHookInput
    | WorktreeCreateHookInput
    | WorktreeRemoveHookInput
    | CwdChangedHookInput
    | FileChangedHookInput
    | UserPromptExpansionHookInput
)


# Hook-specific output types
class PreToolUseHookSpecificOutput(TypedDict):
    """Hook-specific output for PreToolUse events."""

    hookEventName: Literal["PreToolUse"]
    permissionDecision: NotRequired[HookPermissionDecision]
    permissionDecisionReason: NotRequired[str]
    updatedInput: NotRequired[dict[str, Any]]
    additionalContext: NotRequired[str]


class PostToolUseHookSpecificOutput(TypedDict):
    """Hook-specific output for PostToolUse events."""

    hookEventName: Literal["PostToolUse"]
    additionalContext: NotRequired[str]
    updatedMCPToolOutput: NotRequired[Any]


class PostToolUseFailureHookSpecificOutput(TypedDict):
    """Hook-specific output for PostToolUseFailure events."""

    hookEventName: Literal["PostToolUseFailure"]
    additionalContext: NotRequired[str]


class UserPromptSubmitHookSpecificOutput(TypedDict):
    """Hook-specific output for UserPromptSubmit events."""

    hookEventName: Literal["UserPromptSubmit"]
    additionalContext: NotRequired[str]
    sessionTitle: NotRequired[str]


class SessionStartHookSpecificOutput(TypedDict):
    """Hook-specific output for SessionStart events."""

    hookEventName: Literal["SessionStart"]
    additionalContext: NotRequired[str]
    initialUserMessage: NotRequired[str]
    watchPaths: NotRequired[list[str]]


class NotificationHookSpecificOutput(TypedDict):
    """Hook-specific output for Notification events."""

    hookEventName: Literal["Notification"]
    additionalContext: NotRequired[str]


class SubagentStartHookSpecificOutput(TypedDict):
    """Hook-specific output for SubagentStart events."""

    hookEventName: Literal["SubagentStart"]
    additionalContext: NotRequired[str]


class PermissionDeniedHookSpecificOutput(TypedDict):
    """Hook-specific output for PermissionDenied events."""

    hookEventName: Literal["PermissionDenied"]
    retry: NotRequired[bool]


class PermissionRequestHookSpecificOutput(TypedDict):
    """Hook-specific output for PermissionRequest events."""

    hookEventName: Literal["PermissionRequest"]
    decision: dict[str, Any]


class ElicitationHookSpecificOutput(TypedDict):
    """Hook-specific output for Elicitation events."""

    hookEventName: Literal["Elicitation"]
    action: NotRequired[ElicitationAction]
    content: NotRequired[dict[str, Any]]


class ElicitationResultHookSpecificOutput(TypedDict):
    """Hook-specific output for ElicitationResult events."""

    hookEventName: Literal["ElicitationResult"]
    action: NotRequired[ElicitationAction]
    content: NotRequired[dict[str, Any]]


class WorktreeCreateHookSpecificOutput(TypedDict):
    """Hook-specific output for WorktreeCreate events."""

    hookEventName: Literal["WorktreeCreate"]
    worktreePath: str


class CwdChangedHookSpecificOutput(TypedDict):
    """Hook-specific output for CwdChanged events."""

    hookEventName: Literal["CwdChanged"]
    watchPaths: NotRequired[list[str]]


class FileChangedHookSpecificOutput(TypedDict):
    """Hook-specific output for FileChanged events."""

    hookEventName: Literal["FileChanged"]
    watchPaths: NotRequired[list[str]]


class UserPromptExpansionHookSpecificOutput(TypedDict):
    """Hook-specific output for UserPromptExpansion events."""

    hookEventName: Literal["UserPromptExpansion"]
    additionalContext: NotRequired[str]


HookSpecificOutput = (
    PreToolUseHookSpecificOutput
    | PostToolUseHookSpecificOutput
    | PostToolUseFailureHookSpecificOutput
    | PermissionDeniedHookSpecificOutput
    | UserPromptSubmitHookSpecificOutput
    | SessionStartHookSpecificOutput
    | NotificationHookSpecificOutput
    | SubagentStartHookSpecificOutput
    | PermissionRequestHookSpecificOutput
    | ElicitationHookSpecificOutput
    | ElicitationResultHookSpecificOutput
    | CwdChangedHookSpecificOutput
    | FileChangedHookSpecificOutput
    | WorktreeCreateHookSpecificOutput
    | UserPromptExpansionHookSpecificOutput
)


# See https://docs.anthropic.com/en/docs/claude-code/hooks#advanced%3A-json-output
# for documentation of the output types.
#
# IMPORTANT: The Python SDK uses `async_` and `continue_` (with underscores) to avoid
# Python keyword conflicts. These fields are automatically converted to `async` and
# `continue` when sent to the CLI. You should use the underscore versions in your
# Python code.
class AsyncHookJSONOutput(TypedDict):
    """Async hook output that defers hook execution.

    Fields:
        async_: Set to True to defer hook execution. Note: This is converted to
            "async" when sent to the CLI - use "async_" in your Python code.
        asyncTimeout: Optional timeout in milliseconds for the async operation.
    """

    async_: Literal[True]  # Using async_ to avoid Python keyword (converted to "async" for CLI)
    asyncTimeout: NotRequired[int]


class SyncHookJSONOutput(TypedDict):
    """Synchronous hook output with control and decision fields.

    This defines the structure for hook callbacks to control execution and provide
    feedback to Claude.

    Common Control Fields:
        continue_: Whether Claude should proceed after hook execution (default: True).
            Note: This is converted to "continue" when sent to the CLI.
        suppressOutput: Hide stdout from transcript mode (default: False).
        stopReason: Message shown when continue is False.

    Decision Fields:
        decision: Set to "block" to indicate blocking behavior.
        systemMessage: Warning message displayed to the user.
        reason: Feedback message for Claude about the decision.

    Hook-Specific Output:
        hookSpecificOutput: Event-specific controls (e.g., permissionDecision for
            PreToolUse, additionalContext for PostToolUse).

    Note: The CLI documentation shows field names without underscores ("async", "continue"),
    but Python code should use the underscore versions ("async_", "continue_") as they
    are automatically converted.
    """

    # Common control fields
    continue_: NotRequired[bool]  # Avoid name clash (converted to "continue" for CLI)
    suppressOutput: NotRequired[bool]
    stopReason: NotRequired[str]
    # Decision fields
    # Note: "approve" is deprecated for PreToolUse (use permissionDecision instead)
    # For other hooks, only "block" is meaningful
    decision: NotRequired[Literal["block"]]
    systemMessage: NotRequired[str]
    reason: NotRequired[str]
    # Hook-specific outputs
    hookSpecificOutput: NotRequired[HookSpecificOutput]


HookJSONOutput = AsyncHookJSONOutput | SyncHookJSONOutput


class HookContext(TypedDict):
    """Context information for hook callbacks.

    Fields:
        signal: Reserved for future abort signal support. Currently always None.
    """

    signal: Any | None  # Future: abort signal support


HookCallback = Callable[
    # HookCallback input parameters:
    # - input: Strongly-typed hook input with discriminated unions based on hook_event_name
    # - tool_use_id: Optional tool use identifier
    # - context: Hook context with abort signal support (currently placeholder)
    [HookInput, str | None, HookContext],
    Awaitable[HookJSONOutput],
]


# Hook matcher configuration
class HookMatcher(BaseModel):
    """Hook matcher configuration."""

    # See https://docs.anthropic.com/en/docs/claude-code/hooks#structure for the
    # expected string value. For example, for PreToolUse, the matcher can be
    # a tool name like "Bash" or a combination of tool names like
    # "Write|MultiEdit|Edit".
    matcher: str | None = None
    # A list of Python functions with function signature HookCallback
    hooks: Sequence[HookCallback] = field(default_factory=list)
    # Timeout in seconds for all hooks in this matcher (default: 60)
    timeout: float | None = None
