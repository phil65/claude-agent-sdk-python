import type { BetaMessage } from '@anthropic-ai/sdk/resources/beta/messages/messages.mjs';
import type { BetaRawMessageStreamEvent } from '@anthropic-ai/sdk/resources/beta/messages/messages.mjs';
import type { BetaUsage } from '@anthropic-ai/sdk/resources/beta/messages/messages.mjs';
import type { CallToolResult } from '@modelcontextprotocol/sdk/types.js';
import type { ChildProcess } from 'child_process';
import type { ElicitResult } from '@modelcontextprotocol/sdk/types.js';
import type { JSONRPCMessage } from '@modelcontextprotocol/sdk/types.js';
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import type { MessageParam } from '@anthropic-ai/sdk/resources';
import type { Readable } from 'stream';
import type { SpawnOptions as SpawnOptions_2 } from 'child_process';
import type { ToolAnnotations } from '@modelcontextprotocol/sdk/types.js';
import type { UUID } from 'crypto';
import type { Writable } from 'stream';
import * as z from 'zod/v4';
import type { ZodRawShape } from 'zod/v3';
import type { ZodRawShape as ZodRawShape_2 } from 'zod/v4';

export declare class AbortError extends Error {
}

/**
 * Information about the logged in user's account.
 */
export declare type AccountInfo = {
    email?: string;
    organization?: string;
    subscriptionType?: string;
    tokenSource?: string;
    apiKeySource?: string;
    /**
     * Active API backend. Anthropic OAuth login only applies when "firstParty"; for 3P providers the other fields are absent and auth is external (AWS creds, gcloud ADC, etc.). "gateway" means the CLI is authenticated against an enterprise gateway.
     */
    apiProvider?: 'firstParty' | 'bedrock' | 'vertex' | 'foundry' | 'anthropicAws' | 'anthropicGoogleCloud' | 'mantle' | 'gateway';
};

/**
 * Definition for a custom subagent that can be invoked via the Agent tool.
 */
export declare type AgentDefinition = {
    /**
     * Natural language description of when to use this agent
     */
    description: string;
    /**
     * Array of allowed tool names. If omitted, inherits all tools from parent. Note: passing 'Skill' here is deprecated — use the `skills` field instead.
     */
    tools?: string[];
    /**
     * Array of tool names to explicitly disallow for this agent. MCP server-level specs (mcp__server, mcp__server__*, mcp__*) remove every tool from the named server (or all MCP tools).
     */
    disallowedTools?: string[];
    /**
     * The agent's system prompt
     */
    prompt: string;
    /**
     * Model alias (e.g. 'fable', 'opus', 'sonnet', 'haiku') or full model ID (e.g. 'claude-fable-5'). 'inherit' uses the main model; if omitted, uses the default subagent model when one is configured, else the main model
     */
    model?: string;
    /**
     * MCP servers for this agent, by name or as inline config. Passing a createSdkMcpServer() server here is deprecated. It is ignored with a warning and will be an error in a later release, so put it in the top-level mcpServers option.
     */
    mcpServers?: AgentMcpServerSpec[];
    /**
     * Experimental: Critical reminder added to system prompt
     */
    criticalSystemReminder_EXPERIMENTAL?: string;
    /**
     * Array of skill names to preload into the agent context
     */
    skills?: string[];
    /**
     * Auto-submitted as the first user turn when this agent is the main thread agent. Slash commands are processed. Prepended to any user-provided prompt.
     */
    initialPrompt?: string;
    /**
     * Maximum number of agentic turns (API round-trips) before stopping
     */
    maxTurns?: number;
    /**
     * Token count at which this agent compacts its own conversation when it runs as a subagent. It only lowers the window the subagent would otherwise inherit. No effect on the main session agent.
     */
    autoCompactWindow?: number;
    /**
     * Run this agent as a background task (non-blocking, fire-and-forget) when invoked
     */
    background?: boolean;
    /**
     * Run this agent without the user, project and local CLAUDE.md instruction files when it runs as a subagent; managed policy files are kept. For agents that take everything they need from the delegation prompt. No effect on the main session agent.
     */
    omitClaudeMd?: boolean;
    /**
     * Scope for auto-loading agent memory files. 'user' - ~/.claude/agent-memory/<agentType>/, 'project' - .claude/agent-memory/<agentType>/, 'local' - .claude/agent-memory-local/<agentType>/
     */
    memory?: 'user' | 'project' | 'local';
    /**
     * Reasoning effort level for this agent. Either a named level or an integer
     */
    effort?: ('low' | 'medium' | 'high' | 'xhigh' | 'max') | number;
    /**
     * Permission mode controlling how tool executions are handled
     */
    permissionMode?: PermissionMode;
    /**
     * Agent type auto-spawned as a background observer whenever this agent runs, or a comma-separated list of up to four, none of whose names has a comma. An observer receives read-only activity digests and reports via the ObserverReport tool; it never participates in the task.
     */
    observer?: string;
    /**
     * Supplemental postamble appended (after the harness-owned default) to each activity digest sent to the observer. Blank values are ignored.
     */
    observerMessage?: string;
};

/**
 * Information about an available subagent that can be invoked via the Task tool.
 */
export declare type AgentInfo = {
    /**
     * Agent type identifier (e.g., "Explore")
     */
    name: string;
    /**
     * Description of when to use this agent
     */
    description: string;
    /**
     * Model this agent uses: an alias or model ID, or 'inherit' for the parent's model. If omitted, uses the default subagent model when one is configured, else the parent's model
     */
    model?: string;
};

export declare type AgentMcpServerSpec = string | Record<string, McpServerConfigForProcessTransport>;

export declare type AnyZodRawShape = ZodRawShape | ZodRawShape_2;

/**
 * Where the credential used for API requests came from: 'ANTHROPIC_API_KEY' (environment variable), 'apiKeyHelper' (the configured helper command), '/login managed key' (an API key created and stored by /login with an Anthropic Console account), or 'none' (no API key in use - e.g. claude.ai OAuth login, a bearer token, or a third-party cloud provider). 'user' | 'project' | 'org' | 'temporary' | 'oauth' are legacy members that current CLIs never emit; they remain only so the type stays backward compatible.
 */
export declare type ApiKeySource = 'ANTHROPIC_API_KEY' | 'apiKeyHelper' | '/login managed key' | 'none' | 'user' | 'project' | 'org' | 'temporary' | 'oauth';

/**
 * Archive a session. It stays on disk, and `listSessions` still returns it,
 * with `archived: true`. A prompt sent in the session later unarchives it.
 * Does not change the transcript or stop a process that runs the session.
 *
 * Throws if the session is not found, or if `sessionStore` is passed: the mark
 * is kept in a file beside the local transcript, which a store does not hold.
 *
 * @param sessionId - UUID of the session
 * @param options - `{ dir?: string }` project path; omit to search all projects
 */
export declare function archiveSession(_sessionId: string, _options?: SessionMutationOptions): Promise<void>;

export declare type AsyncHookJSONOutput = {
    async: true;
    asyncTimeout?: number;
};

export declare type BackgroundTaskSummary = {
    id: string;
    /**
     * Friendly task-type label (e.g. 'shell', 'subagent', 'monitor', 'workflow'). Falls back to the raw discriminant for unknown types.
     */
    type: string;
    status: string;
    /**
     * Free-text description. Capped at 1000 chars; clipped values append an in-string "… [+N chars]" marker.
     */
    description: string;
    /**
     * Shell command line. Only present for 'shell' tasks. Capped at 1000 chars with the same "… [+N chars]" marker.
     */
    command?: string;
    /**
     * Subagent type name. Only present for 'subagent' tasks.
     */
    agent_type?: string;
    /**
     * MCP server name. Only present for 'monitor' / 'MCP task' tasks.
     */
    server?: string;
    /**
     * MCP tool name. Only present for 'monitor' / 'MCP task' tasks.
     */
    tool?: string;
    /**
     * Workflow name. Only present for 'workflow' tasks.
     */
    name?: string;
};

export declare type BaseHookInput = {
    session_id: string;
    transcript_path: string;
    cwd: string;
    /**
     * UUID correlating a user prompt with all subsequent events until the next prompt. Same value emitted on OpenTelemetry events as the `prompt.id` attribute, so hook output can be joined to OTel events at prompt grain. Absent until the first user input of the process lifetime.
     */
    prompt_id?: string;
    permission_mode?: string;
    /**
     * Subagent identifier. Present only when the hook fires from within a subagent (e.g., a tool called by an AgentTool worker). Absent for the main thread, even in --agent sessions. Use this field (not agent_type) to distinguish subagent calls from main-thread calls.
     */
    agent_id?: string;
    /**
     * Agent type name (e.g., "general-purpose", "code-reviewer"). Present when the hook fires from within a subagent (alongside agent_id), or on the main thread of a session started with --agent (without agent_id).
     */
    agent_type?: string;
    /**
     * Reasoning effort applied to the current turn. Same shape as StatusLineCommandInput.effort. Present for hooks that fire within a tool-use context (PreToolUse, PostToolUse, Stop, SubagentStop, etc.) on a model that supports the effort parameter; absent for session-lifecycle hooks and models without effort support.
     */
    effort?: {
        /**
         * Active effort level for the current turn (e.g., "low", "medium", "high", "xhigh", "max"), after any silent downgrade for the selected model. Also exposed to hook commands and Bash as the CLAUDE_EFFORT env var.
         */
        level: string;
    };
};

export declare type BaseOutputFormat = {
    type: OutputFormatType;
};

/**
 * Names of built-in tools, as permission rules, hook matchers, `tools` and
 * `disallowedTools` spell them. A name is listed even where a platform or
 * setting turns its tool off. The list is not complete: the CLI has tools that
 * are not on it, so it cannot stand for "every tool". What a session has is
 * the `tools` field of its `system/init` message.
 *
 * @alpha
 */
export declare const BUILTIN_TOOL_NAMES: readonly ['Agent', 'Artifact', 'AskUserQuestion', 'Bash', 'ClaudeDesign', 'CronCreate', 'CronDelete', 'CronList', 'Edit', 'EndConversation', 'EnterPlanMode', 'EnterWorktree', 'ExitPlanMode', 'ExitWorktree', 'Glob', 'Grep', 'ListAgents', 'ListMcpResourcesTool', 'LSP', 'Monitor', 'NotebookEdit', 'OfferChromeSetup', 'PowerShell', 'Projects', 'propose_skills', 'PushNotification', 'Read', 'ReadMcpResourceDirTool', 'ReadMcpResourceTool', 'ReadNotifications', 'RemoteTrigger', 'ReportFindings', 'ScheduleWakeup', 'SendFeedback', 'SendMessage', 'SendUserFile', 'SendUserMessage', 'SetGoal', 'ShareOnboardingGuide', 'ShowOnboardingRolePicker', 'Skill', 'SubagentHandback', 'TaskCreate', 'TaskGet', 'TaskList', 'TaskStop', 'TaskUpdate', 'TodoWrite', 'ToolSearch', 'WaitForMcpServers', 'WebFetch', 'WebSearch', 'Workflow', 'Write'];

/**
 * Permission callback function for controlling tool usage.
 * Called before each tool execution to determine if it should be allowed.
 *
 * Return `null` ONLY after the consumer has already sent the
 * control_response out-of-band (e.g. a signed HTTP POST echoing
 * `requestId`); the SDK will skip its own transport write. Fail-closed: an
 * accidental null means no control_response is sent and the tool stays
 * blocked indefinitely — permission prompts have no park deadline.
 */
export declare type CanUseTool = (toolName: string, input: Record<string, unknown>, options: {
    /** Signaled if the operation should be aborted. */
    signal: AbortSignal;
    /**
     * Suggestions for updating permissions so that the user will not be
     * prompted again for this tool during this session.
     *
     * Typically if presenting the user an option 'always allow' or similar,
     * then this full set of suggestions should be returned as the
     * `updatedPermissions` in the PermissionResult.
     */
    suggestions?: PermissionUpdate[];
    /**
     * The file path that triggered the permission request, if applicable.
     * For example, when a Bash command tries to access a path outside allowed directories.
     */
    blockedPath?: string;
    /**
     * For `mcp__*` tools: the MCP server serving the tool and where its
     * definition came from. `source: 'sdk'` means one of the in-process
     * servers this SDK host registered (its `name` is the key you registered;
     * only the host can register one); any other value (`plugin`, `user`,
     * `project`, `local`, `dynamic`, `managed`, …) is a server from
     * configuration, whose `name` is the key as authored there — untrusted
     * text, escape it before display. Key trust decisions on `source`, not on
     * the name or the tool-name prefix. Absent for non-MCP tools and on CLIs
     * that predate the field.
     */
    mcpServer?: {
        name: string;
        source: string;
    };
    /** Explains why this permission request was triggered. */
    decisionReason?: string;



    /**
     * Full permission prompt sentence rendered by the bridge (e.g.
     * "Claude wants to read foo.txt"). Use this as the primary prompt
     * text when present instead of reconstructing from toolName+input.
     */
    title?: string;
    /**
     * Short noun phrase for the tool action (e.g. "Read file"), suitable
     * for button labels or compact UI.
     */
    displayName?: string;
    /**
     * Human-readable subtitle from the bridge (e.g. "Claude will have
     * read and write access to files in ~/Downloads").
     */
    description?: string;
    /**
     * The ask must not be approvable by a single stray keystroke: open the
     * prompt on its decline option and offer no one-key approve shortcut.
     */
    defaultToNo?: boolean;
    /**
     * The ask must not offer a persistent "don't ask again" choice: its rule
     * grants more than this ask's action, or a plugin started this call.
     */
    suppressAlwaysAllowRule?: boolean;
    /**
     * Unique identifier for this specific tool call within the assistant message.
     * Multiple tool calls in the same assistant message will have different toolUseIDs.
     */
    toolUseID: string;
    /** If running within the context of a sub-agent, the sub-agent's ID. */
    agentID?: string;

    /**
     * The control_request envelope's `request_id`. A control_response sent
     * out-of-band (e.g. a signed HTTP POST instead of the SDK's WS write)
     * must echo this value for the worker to match it.
     */
    requestId: string;
    /**
     * Set when a user-configured ask RULE (permissions.ask) forced this
     * prompt while the ask carries the tool's own decisionReason, or when
     * an ask rule reaches an MCP tool only under another name (such as a
     * connector's id, its claude.ai name, or Artifact for the Artifacts
     * server's tools), not the one given here. Hosts
     * making policy on the reason (e.g. auto-deny a safetyCheck) or
     * running host-side auto-approval should treat asks carrying this
     * field as rule-forced: the user's stated intent is a human prompt.
     */
    matchedAskRule?: {
        source: string;
        toolName: string;
        ruleContent?: string;
    };



}) => Promise<PermissionResult | null>;

/**
 * The per-session half of {@link Options}: what a host only knows once the
 * user has picked a folder and started the session. Everything else (the
 * executable, settings sources, tools, plugins, host-level MCP servers, hooks,
 * canUseTool, environment that the process reads during start-up) is given to
 * {@link prewarm} and is fixed for the life of the spare. A host whose
 * host-level options changed since it prewarmed must discard the spare and
 * start normally.
 * @alpha
 */
export declare type ClaimOptions = {
    /**
     * The session's working directory (required). A relative path resolves
     * against this process, as for `query()`; `~/…` is expanded by Claude Code.
     */
    cwd: string;
    /**
     * Per-session environment additions. Only variables the CLI accepts at
     * claim time (fresh OAuth/session tokens, the host's session id) — anything
     * the process reads during start-up belongs in the prewarm options' env,
     * and the claim is refused if it appears here.
     */
    env?: Record<string, string>;
    /** As `--add-dir`; relative entries resolve against `cwd`, missing ones are skipped. */
    additionalDirectories?: string[];
    model?: string;
    /**
     * As `Options.permissionMode`, sent as part of the claim itself: a mode
     * the process cannot take (`bypassPermissions` on a spare prewarmed without
     * `allowDangerouslySkipPermissions`, one the folder's settings disable)
     * refuses the claim — `claimed` rejects with `permission_mode_not_claimable`
     * (or `claim_failed`) and the prompt gets the `not_claimed` error result —
     * so a session never runs under a different mode than the one asked for.
     */
    permissionMode?: PermissionMode;
    maxThinkingTokens?: number | null;
    /**
     * Flag-tier settings overlay (e.g. `{ fastMode: true, effortLevel: 'high' }`),
     * applied as `applyFlagSettings` does. Because an overlay can carry
     * permission rules, a claim that has one holds the prompt until the process
     * has accepted the overlay (one round trip) and does not send it if the
     * overlay is refused: `claimed` then rejects with `settings_not_applied`
     * and the process is let go — start the session with `query()`. The overlay
     * is written ahead of the claim, so `disabledMcpjsonServers`,
     * `deniedMcpServers` and `enabledPlugins` decide which of the folder's
     * `.mcp.json` servers and plugins the claim starts, and a refusal stops the
     * claim, as does an invalid value that would leave one of those keys out of
     * force. `model`, `agent`, `fastMode`, `permissions`, `availableModels` and
     * `disableAutoMode` follow it: they are in force before the prompt you pass
     * to `claim()` is read, but the folder's SessionStart hooks, and a first
     * message such a hook hands the session, do not wait for them, and a refusal
     * of them comes after the folder's servers have started. One limit in this version:
     * keys that govern hooks (`hooks`, `disableAllHooks`,
     * `allowManagedHooksOnly`, `allowedHttpHookUrls`, `httpHookAllowedEnvVars`)
     * are refused — `claim()` throws before sending anything and the spare stays
     * parked; give those to `prewarm()` in `Options.settings`, where they are in
     * force before any hook as on a cold start. Servers from the user's or
     * managed configuration, and those running in the parked spare, are
     * `prewarm()`'s to govern.
     */
    settings?: Parameters<Query['applyFlagSettings']>[0];
    appendSystemPrompt?: string;
    title?: string;
    agents?: Record<string, AgentDefinition>;

};

export declare type ConfigChangeHookInput = BaseHookInput & {
    hook_event_name: 'ConfigChange';
    source: 'user_settings' | 'project_settings' | 'local_settings' | 'policy_settings' | 'skills';
    file_path?: string;
};

/**
 * Config scope for settings.
 */
export declare type ConfigScope = 'local' | 'user' | 'project';

/**
 * The request failed or was rejected (unknown subtype, invalid arguments, or an error while handling it).
 */
declare type ControlErrorResponse = {
    subtype: 'error';
    /**
     * The request_id of the control_request this answers.
     */
    request_id: string;
    /**
     * Human-readable failure description.
     */
    error: string;


    /**
     * can_use_tool requests this CLI process has issued and not yet resolved, so a client joining an already-initialized session learns about in-flight prompts. Always present (possibly empty) on a success `initialize` response from Claude Code v2.1.268 or later; earlier versions could omit it, so treat absence as an older CLI rather than as "nothing pending". A prompt inherited from a previous worker of the same session can remain answerable without appearing here and without a control_cancel_request; session_state "requires_action" on the same reply signals one the CLI is holding, but not every inherited prompt is signalled.
     */
    pending_permission_requests?: SDKControlRequest[];
    /**
     * request_user_dialog requests this CLI process has issued and not yet resolved (sibling of pending_permission_requests, with the same inherited-prompt caveat), so a client joining an already-initialized session can re-arm in-flight dialogs. Always present (possibly empty) on a success `initialize` response from Claude Code v2.1.268 or later; earlier versions could omit it, so treat absence as an older CLI rather than as "nothing pending". Receivers must tolerate the same request_id also arriving as a live or replayed control_request frame and render it once.
     */
    pending_user_dialog_requests?: SDKControlRequest[];
    /**
     * elicitation requests that this CLI process sent and that are not yet answered or withdrawn (sibling of pending_permission_requests), each as it was sent, so a client that joins after an MCP server asked can still show the question. Present (possibly empty) on a success `initialize` response when this CLI lists them, which not every session does yet; absence says nothing about what is pending. Receivers must tolerate the same request_id also arriving as a live or replayed control_request frame and render it once.
     */
    pending_elicitation_requests?: SDKControlRequest[];
};

/**
 * The request was handled.
 */
declare type ControlResponse = {
    subtype: 'success';
    /**
     * The request_id of the control_request this answers.
     */
    request_id: string;
    /**
     * The success payload, shaped as documented for the answered request's subtype; absent or {} for requests that are merely acknowledged.
     */
    response?: Record<string, unknown>;
    /**
     * can_use_tool requests this CLI process has issued and not yet resolved, so a client joining an already-initialized session learns about in-flight prompts. Always present (possibly empty) on a success `initialize` response from Claude Code v2.1.268 or later; earlier versions could omit it, so treat absence as an older CLI rather than as "nothing pending". A prompt inherited from a previous worker of the same session can remain answerable without appearing here and without a control_cancel_request; session_state "requires_action" on the same reply signals one the CLI is holding, but not every inherited prompt is signalled.
     */
    pending_permission_requests?: SDKControlRequest[];
    /**
     * request_user_dialog requests this CLI process has issued and not yet resolved (sibling of pending_permission_requests, with the same inherited-prompt caveat), so a client joining an already-initialized session can re-arm in-flight dialogs. Always present (possibly empty) on a success `initialize` response from Claude Code v2.1.268 or later; earlier versions could omit it, so treat absence as an older CLI rather than as "nothing pending". Receivers must tolerate the same request_id also arriving as a live or replayed control_request frame and render it once.
     */
    pending_user_dialog_requests?: SDKControlRequest[];
    /**
     * elicitation requests that this CLI process sent and that are not yet answered or withdrawn (sibling of pending_permission_requests), each as it was sent, so a client that joins after an MCP server asked can still show the question. Present (possibly empty) on a success `initialize` response when this CLI lists them, which not every session does yet; absence says nothing about what is pending. Receivers must tolerate the same request_id also arriving as a live or replayed control_request frame and render it once.
     */
    pending_elicitation_requests?: SDKControlRequest[];
};

declare namespace coreTypes {
    export {
        SandboxCredentialsConfig,
        SandboxFilesystemConfig,
        SandboxIgnoreViolations,
        SandboxNetworkConfig,
        SandboxSettings,
        NonNullableUsage,
        HOOK_EVENTS,
        EXIT_REASONS,
        SYSTEM_PROMPT_DYNAMIC_BOUNDARY,
        AccountInfo,
        AgentDefinition,
        AgentInfo,
        AgentMcpServerSpec,
        ApiKeySource,
        AsyncHookJSONOutput,
        BackgroundTaskSummary,
        BaseHookInput,
        BaseOutputFormat,
        ConfigChangeHookInput,
        ConfigScope,
        CwdChangedHookInput,
        CwdChangedHookSpecificOutput,
        DirectoryAddedHookInput,
        ElicitationHookInput,
        ElicitationHookSpecificOutput,
        ElicitationResultHookInput,
        ElicitationResultHookSpecificOutput,
        ExitReason,
        FastModeDisabledReason,
        FastModeState,
        FileChangedHookInput,
        FileChangedHookSpecificOutput,
        HookEvent,
        HookInput,
        HookJSONOutput,
        HookPermissionDecision,
        InstructionsLoadedHookInput,
        JsonSchemaOutputFormat,
        McpClaudeAIProxyServerConfig,
        McpHttpServerConfig,
        McpSSEServerConfig,
        McpSdkServerConfig,
        McpServerConfigForProcessTransport,
        McpServerProvenance,
        McpServerStatusConfig,
        McpServerStatus,
        McpServerToolPolicy,
        McpSetServersResult,
        McpStdioServerConfig,
        MessageDisplayHookInput,
        MessageDisplayHookSpecificOutput,
        ModelInfo,
        ModelUsage,
        NotificationHookInput,
        NotificationHookSpecificOutput,
        OutputFormat,
        OutputFormatType,
        PermissionBehavior,
        PermissionDecisionClassification,
        PermissionDeniedHookInput,
        PermissionDeniedHookSpecificOutput,
        PermissionMode,
        PermissionRequestHookInput,
        PermissionRequestHookSpecificOutput,
        PermissionResult,
        PermissionRuleValue,
        PermissionUpdateDestination,
        PermissionUpdate,
        PostCompactHookInput,
        PostModelSwitchHookInput,
        PostModelSwitchHookSpecificOutput,
        PostToolBatchHookInput,
        PostToolBatchHookSpecificOutput,
        PostToolBatchToolCall,
        PostToolUseFailureHookInput,
        PostToolUseFailureHookSpecificOutput,
        PostToolUseHookInput,
        PostToolUseHookSpecificOutput,
        PreCompactHookInput,
        PreModelSwitchHookInput,
        PreModelSwitchHookSpecificOutput,
        PreToolUseHookInput,
        PreToolUseHookSpecificOutput,
        RewindFilesResult,
        SDKAPIRetryMessage,
        SDKActiveGoalMessage,
        SDKAssistantMessageError,
        SDKAssistantMessage,
        SDKAuthStatusMessage,
        SDKBackgroundTasksChangedMessage,
        SDKCommandsChangedMessage,
        SDKCompactBoundaryMessage,
        SDKContextUsageCategory,
        SDKContextUsage,
        SDKControlRequestProgressMessage,
        SDKConversationResetMessage,
        SDKDeferredToolUse,
        SDKElicitationCompleteMessage,
        SDKFilesPersistedEvent,
        SDKHookProgressMessage,
        SDKHookResponseMessage,
        SDKHookStartedMessage,
        SDKInformationalMessage,
        SDKLocalCommandOutputMessage,
        SDKMcpResourceLink,
        SDKMemoryRecallMessage,
        SDKMessageOrigin,
        SDKMessage,
        SDKMirrorErrorMessage,
        SDKModelRefusalFallbackMessage,
        SDKModelRefusalNoFallbackMessage,
        SDKNotificationMessage,
        SDKPartialAssistantMessage,
        SDKPermissionDenial,
        SDKPermissionDeniedMessage,
        SDKPluginInstallMessage,
        SDKPromptSuggestionMessage,
        SDKRateLimitEvent,
        SDKRateLimitInfo,
        SDKResultError,
        SDKResultMessage,
        SDKResultSuccess,
        SDKSessionInfo,
        SDKSessionStateChangedMessage,
        SDKSessionWritesLostMessage,
        SDKSettingsParseError,
        SDKStartupFailureReason,
        SDKStatusMessage,
        SDKStatus,
        SDKSystemMessage,
        SDKTaskNotificationMessage,
        SDKTaskProgressMessage,
        SDKTaskStartedMessage,
        SDKTaskUpdatedMessage,
        SDKThinkingTokensMessage,
        SDKToolProgressMessage,
        SDKToolUseSummaryMessage,
        SDKUsageReport,
        SDKUserMessageReplay,
        SDKUserMessage,
        SDKWorkerShuttingDownMessage,
        SdkBeta,
        SdkPluginConfig,
        SessionCronSummary,
        SessionEndHookInput,
        SessionStartHookInput,
        SessionStartHookSpecificOutput,
        SettingSource,
        SetupHookInput,
        SetupHookSpecificOutput,
        SlashCommand,
        StopFailureHookInput,
        StopHookInput,
        StopHookSpecificOutput,
        SubagentStartHookInput,
        SubagentStartHookSpecificOutput,
        SubagentStopHookInput,
        SubagentStopHookSpecificOutput,
        SyncHookJSONOutput,
        TaskCompletedHookInput,
        TaskCreatedHookInput,
        TeammateIdleHookInput,
        TerminalReason,
        ThinkingAdaptive,
        ThinkingConfig,
        ThinkingDisabled,
        ThinkingEnabled,
        UserPromptExpansionHookInput,
        UserPromptExpansionHookSpecificOutput,
        UserPromptSubmitHookInput,
        UserPromptSubmitHookSpecificOutput,
        WorktreeCreateHookInput,
        WorktreeCreateHookSpecificOutput,
        WorktreeRemoveHookInput
    }
}

/**
 * Creates an MCP server instance that can be used with the SDK transport.
 * This allows SDK users to define custom tools that run in the same process.
 *
 * Tool calls are bounded by the MCP tool-call timeout — `options.timeout`
 * (ms) for this server, else the MCP_TOOL_TIMEOUT env var, effectively
 * unbounded by default.
 *
 * A tool in `options.tools` whose input schema cannot be converted to JSON
 * Schema is left out of the server's tool list, with one warning naming it (a
 * process warning with code CLAUDE_SDK_MCP_TOOL_SCHEMA_UNCONVERTIBLE, or
 * console.warn where there is no process.emitWarning); its other tools load.
 */
export declare function createSdkMcpServer(_options: CreateSdkMcpServerOptions): McpSdkServerConfigWithInstance;

declare type CreateSdkMcpServerOptions = {
    name: string;
    version?: string;
    /**
     * Server instructions returned from `initialize` and surfaced to the model
     * as an MCP instructions block. When proxying a real MCP server through the
     * SDK transport, pass the underlying server's `getInstructions()` here so
     * it isn't dropped.
     */
    instructions?: string;
    tools?: Array<SdkMcpToolDefinition<any>>;
    /**
     * When true, all tools from this server are always included in the prompt
     * and never deferred behind tool search. Applied via
     * `_meta['anthropic/alwaysLoad']` on each tool. Equivalent to
     * `defer_loading: false` on the API. Per-tool `tool({ alwaysLoad })` still
     * works and is OR'd with this.
     */
    alwaysLoad?: boolean;
    /**
     * Per-server tool-call timeout in milliseconds. Overrides the
     * MCP_TOOL_TIMEOUT environment variable for this server. Hard wall-clock
     * limit per call; progress notifications do not extend it. Values below
     * 1000ms are ignored (falls through to MCP_TOOL_TIMEOUT or the default).
     * Applies when the server is first registered; changing it for an
     * already-registered server has no effect until it is removed and re-added.
     */
    timeout?: number;
};

export declare type CwdChangedHookInput = BaseHookInput & {
    hook_event_name: 'CwdChanged';
    old_cwd: string;
    new_cwd: string;
};

export declare type CwdChangedHookSpecificOutput = {
    hookEventName: 'CwdChanged';
    watchPaths?: string[];
};

/**
 * Delete a session. Deletes data only on this computer, or only in
 * `sessionStore` when one is passed, not anything stored by Anthropic.
 *
 * With `sessionStore`: calls `sessionStore.delete()` if implemented; no-op
 * otherwise (per the SessionStore contract — appropriate for WORM/append-only
 * backends).
 *
 * Without `sessionStore`: removes `{sessionId}.jsonl` and the `{sessionId}/`
 * subagent-transcript subdirectory from the local projects dir. Throws if the
 * session is not found. If the subdirectory cannot be removed, throws after
 * the transcript is already deleted. A repeat call then throws "not found",
 * so delete the subdirectory yourself.
 *
 * @param sessionId - UUID of the session
 * @param options - `{ dir?, sessionStore? }`
 */
export declare function deleteSession(_sessionId: string, _options?: SessionMutationOptions): Promise<void>;

/**
 * What {@link matchDeniedModels} answers.
 *
 * @alpha
 */
export declare type DeniedModelsMatch = {
    /** For each model asked about, in order: whether an entry blocks it. */
    denied: boolean[];
    /** The CLI's notes on entries: why one was ignored, or what one blocks where that may surprise. And a note on what was asked about but is no model name. */
    warnings: string[];
};

export declare type DirectoryAddedHookInput = BaseHookInput & {
    hook_event_name: 'DirectoryAdded';
    /**
     * Absolute path of the directory that was added.
     */
    directory: string;
    /**
     * How the directory was added: "slash_command" for /add-dir, "register_repo_root" for the SDK control_request.
     */
    source: 'slash_command' | 'register_repo_root';
};

/**
 * Effort level for controlling how much thinking/reasoning Claude applies.
 *
 * @see https://platform.claude.com/docs/en/build-with-claude/effort
 */
export declare type EffortLevel = 'low' | 'medium' | 'high' | 'xhigh' | 'max';

/**
 * Hook input for the Elicitation event. Fired when an MCP server requests user input. Hooks can auto-respond (accept/decline) instead of showing the dialog.
 */
export declare type ElicitationHookInput = BaseHookInput & {
    hook_event_name: 'Elicitation';
    mcp_server_name: string;
    message: string;
    mode?: 'form' | 'url';
    url?: string;
    elicitation_id?: string;
    requested_schema?: Record<string, unknown>;
};

/**
 * Hook-specific output for the Elicitation event. Return this to programmatically accept or decline an MCP elicitation request.
 */
export declare type ElicitationHookSpecificOutput = {
    hookEventName: 'Elicitation';
    action?: 'accept' | 'decline' | 'cancel';
    content?: Record<string, unknown>;
};

/**
 * Elicitation request from an MCP server, asking the SDK consumer for user input.
 */
export declare type ElicitationRequest = {
    /** Name of the MCP server requesting elicitation */
    serverName: string;
    /** Message to display to the user */
    message: string;
    /** Elicitation mode: 'form' for structured input, 'url' for browser-based auth */
    mode?: 'form' | 'url';
    /** URL to open (only for 'url' mode) */
    url?: string;
    /** Elicitation ID for correlating URL elicitations with completion notifications (URL mode only) */
    elicitationId?: string;
    /** JSON Schema for the requested input (only for 'form' mode) */
    requestedSchema?: Record<string, unknown>;
    /** Permission-display title from MCP `_meta['anthropic/permissionDisplay']` — header for elicitation-driven permission prompts */
    title?: string;
    /** Short tool/server label from MCP `_meta['anthropic/permissionDisplay'].displayName` */
    displayName?: string;
    /** Permission-display subtitle from MCP `_meta['anthropic/permissionDisplay'].description` */
    description?: string;
};

/**
 * Elicitation response from the SDK consumer.
 * Re-exported from the MCP SDK for convenience.
 */
export declare type ElicitationResult = ElicitResult;

/**
 * Hook input for the ElicitationResult event. Fired after the user responds to an MCP elicitation. Hooks can observe or override the response before it is sent to the server.
 */
export declare type ElicitationResultHookInput = BaseHookInput & {
    hook_event_name: 'ElicitationResult';
    mcp_server_name: string;
    elicitation_id?: string;
    mode?: 'form' | 'url';
    action: 'accept' | 'decline' | 'cancel';
    content?: Record<string, unknown>;
};

/**
 * Hook-specific output for the ElicitationResult event. Return this to override the action or content before the response is sent to the MCP server.
 */
export declare type ElicitationResultHookSpecificOutput = {
    hookEventName: 'ElicitationResult';
    action?: 'accept' | 'decline' | 'cancel';
    content?: Record<string, unknown>;
};

export declare const EXIT_REASONS: readonly ['clear', 'resume', 'logout', 'prompt_input_exit', 'other'];

export declare type ExitReason = 'clear' | 'resume' | 'logout' | 'prompt_input_exit' | 'other';

/**
 * Why fast mode can't serve right now. Absent when nothing blocks it (a request may still choose standard speed). A paused-after-rate-limit run is not here; it rides fast_mode_state as 'cooldown'.
 */
export declare type FastModeDisabledReason = 'free' | 'preference' | 'extra_usage_disabled' | 'network_error' | 'unknown' | 'not_first_party' | 'disabled_by_env' | 'model_not_allowed' | 'sdk_opt_in_required' | 'pending';

/**
 * Fast mode state: off, in cooldown after rate limit, or actively enabled.
 */
export declare type FastModeState = 'off' | 'cooldown' | 'on';

export declare type FileChangedHookInput = BaseHookInput & {
    hook_event_name: 'FileChanged';
    file_path: string;
    event: 'change' | 'add' | 'unlink';
};

export declare type FileChangedHookSpecificOutput = {
    hookEventName: 'FileChanged';
    watchPaths?: string[];
};

/**
 * Apply the same trust-tier filter the CLI applies before honoring escalating
 * permission modes from settings: if `permissions.defaultMode` is escalating
 * (`bypassPermissions`/`auto`/`acceptEdits`) AND was set by a repo-committed
 * tier (`project`), drop it from the returned `effective`.
 *
 * @alpha
 */
export declare function filterEscalatingDefaultMode(_resolved: ResolvedSettings): Settings;

/**
 * Fold a batch of appended entries into the running summary for `key`.
 *
 * Stores call this from inside `append()` to keep a {@link SessionSummaryEntry}
 * sidecar up to date without re-reading the transcript. `prev` is the previous
 * summary for the same key (or `undefined` for the first append). The returned
 * `data` blob is opaque to the store — persist it verbatim.
 *
 * Set-once fields (`isSidechain`, `createdAt`, `cwd`, `firstPrompt`) freeze on
 * first sight; last-wins fields (`customTitle`, `aiTitle`, `lastPrompt`,
 * `summaryHint`, `gitBranch`, `tag`) overwrite on every appearance.
 *
 * `mtime` is NOT derived from entry timestamps — the adapter MUST stamp it at
 * persist time using the same clock it uses for `listSessions().mtime`. Pass
 * it via `options.mtime`; when omitted, the previous summary's `mtime` is
 * preserved (use this only when re-folding the same sidecar without a new
 * persist). See {@link SessionSummaryEntry.mtime} for the contract.
 * @alpha
 */
export declare function foldSessionSummary(prev: SessionSummaryEntry | undefined, key: SessionKey, entries: SessionStoreEntry[], options?: {
    mtime?: number;
}): SessionSummaryEntry;

/**
 * Fork a session into a new branch with fresh UUIDs.
 *
 * Copies transcript messages from the source session into a new session file,
 * remapping every message UUID and preserving the parentUuid chain. Supports
 * `upToMessageId` for branching from a specific point in the conversation.
 *
 * Forked sessions start without undo history (file-history snapshots are not
 * copied).
 *
 * @param sessionId - UUID of the source session
 * @param options - `{ dir?, upToMessageId?, title? }`
 * @returns `{ sessionId }` — UUID of the new forked session
 */
export declare function forkSession(_sessionId: string, _options?: ForkSessionOptions): Promise<ForkSessionResult>;

/**
 * Options for forking a session into a new branch.
 */
export declare type ForkSessionOptions = SessionMutationOptions & {
    /**
     * Slice transcript up to the message whose `uuid` field equals this value
     * (inclusive). If omitted, full copy. Obtain the value from
     * {@link SessionMessage.uuid} via `getSessionMessages()`, or from the
     * `uuid` you supplied on a streamed {@link SDKUserMessage}. With a compaction
     * summary's id, the fork leaves out the messages kept after that summary.
     * With the id of a `compact_boundary` message that a compaction wrote, or of a
     * queued prompt or other non-message entry stored between that boundary and
     * its summary, the fork ends before the boundary, and has no messages if none
     * came before it. With the id of a boundary written by rewinding behind a
     * compaction, the fork keeps that boundary and the messages it kept.
     */
    upToMessageId?: string;
    /** Custom title for the fork. If omitted, derives from original title + " (fork)". */
    title?: string;
};

/**
 * Result of a fork operation.
 */
export declare type ForkSessionResult = {
    /** New session UUID. Resumable via `query({ options: { resume: sessionId } })`. */
    sessionId: string;
};

/**
 * Reads metadata for a single session by ID. Unlike `listSessions`, this only
 * reads the single session file rather than every session in the project.
 * Returns undefined if the session file is not found, is a sidechain session,
 * or has no extractable summary.
 *
 * @param sessionId - UUID of the session
 * @param options - `{ dir?: string }` project path; omit to search all project directories
 */
export declare function getSessionInfo(_sessionId: string, _options?: GetSessionInfoOptions): Promise<SDKSessionInfo | undefined>;

/**
 * Options for getSessionInfo.
 */
export declare type GetSessionInfoOptions = {
    /**
     * Project directory path (same semantics as `listSessions({ dir })`).
     * When omitted, all project directories are searched for the session file.
     */
    dir?: string;
    /**
     * When provided, load session info from this store instead of the local
     * filesystem.
     * @alpha
     */
    sessionStore?: SessionStore;
};

/**
 * Reads a session's conversation messages from its JSONL transcript file.
 *
 * Parses the transcript, builds the conversation chain via parentUuid links,
 * and returns user/assistant messages in chronological order. Set
 * `includeSystemMessages: true` in options to also include system messages.
 *
 * @param sessionId - UUID of the session to read
 * @param options - Optional dir, limit, offset, and includeSystemMessages
 * @returns Array of messages, or empty array if session not found
 */
export declare function getSessionMessages(_sessionId: string, _options?: GetSessionMessagesOptions): Promise<SessionMessage[]>;

/**
 * Options for retrieving session messages.
 */
export declare type GetSessionMessagesOptions = {
    /** Project directory to find the session in. If omitted, searches all projects. */
    dir?: string;
    /** Maximum number of messages to return. */
    limit?: number;
    /** Number of messages to skip from the start. */
    offset?: number;
    /**
     * When true, include system messages (e.g., compact boundaries, informational
     * notices) in the returned list alongside user/assistant messages.
     * Defaults to false for backwards compatibility.
     */
    includeSystemMessages?: boolean;
    /**
     * When provided, load session messages from this store instead of the
     * local filesystem.
     * @alpha
     */
    sessionStore?: SessionStore;
};

/**
 * Reads a subagent's conversation messages from its JSONL transcript file.
 *
 * Parses the subagent transcript, builds the conversation chain via parentUuid
 * links, and returns user/assistant messages in chronological order.
 *
 * @param sessionId - UUID of the parent session
 * @param agentId - ID of the subagent
 * @param options - Optional dir, limit, and offset
 * @returns Array of user/assistant messages, or empty array if not found
 */
export declare function getSubagentMessages(_sessionId: string, _agentId: string, _options?: GetSubagentMessagesOptions): Promise<SessionMessage[]>;

/**
 * Options for retrieving subagent messages.
 */
export declare type GetSubagentMessagesOptions = {
    /** Project directory to find the session in. If omitted, searches all projects. */
    dir?: string;
    /** Maximum number of messages to return. */
    limit?: number;
    /** Number of messages to skip from the start. */
    offset?: number;
    /**
     * When provided, load subagent messages from this store instead of the
     * local filesystem.
     * @alpha
     */
    sessionStore?: SessionStore;
};

export declare const HOOK_EVENTS: readonly ['PreToolUse', 'PostToolUse', 'PostToolUseFailure', 'PostToolBatch', 'Notification', 'UserPromptSubmit', 'UserPromptExpansion', 'SessionStart', 'SessionEnd', 'Stop', 'StopFailure', 'SubagentStart', 'SubagentStop', 'PreCompact', 'PostCompact', 'PreModelSwitch', 'PostModelSwitch', 'PermissionRequest', 'PermissionDenied', 'Setup', 'TeammateIdle', 'TaskCreated', 'TaskCompleted', 'Elicitation', 'ElicitationResult', 'ConfigChange', 'WorktreeCreate', 'WorktreeRemove', 'InstructionsLoaded', 'CwdChanged', 'FileChanged', 'DirectoryAdded', 'MessageDisplay'];

/**
 * Hook callback function for responding to events during execution.
 */
export declare type HookCallback = (input: HookInput, toolUseID: string | undefined, options: {
    signal: AbortSignal;
}) => Promise<HookJSONOutput>;

/**
 * Hook callback matcher containing hook callbacks and optional pattern matching.
 */
export declare interface HookCallbackMatcher {
    matcher?: string;
    hooks: HookCallback[];
    /** Timeout in seconds for all hooks in this matcher */
    timeout?: number;
    /**
     * What a failure of these hooks does: one throws, or returns output that
     * fails validation. `'continue'` (default): the failure is reported in a
     * warning message and the action goes ahead. `'block'`: the action the event
     * guards (a tool call, a permission request, a prompt) is blocked. Ignored on
     * Stop, SubagentStop, TaskCompleted and TeammateIdle. With `'block'`, the
     * query fails at startup on a Claude Code that does not support the option
     * and on a session already running that did not register these hooks, and
     * the first prompt is sent only once those checks have passed.
     */
    onFailure?: 'continue' | 'block';



}

export declare type HookEvent = 'PreToolUse' | 'PostToolUse' | 'PostToolUseFailure' | 'PostToolBatch' | 'Notification' | 'UserPromptSubmit' | 'UserPromptExpansion' | 'SessionStart' | 'SessionEnd' | 'Stop' | 'StopFailure' | 'SubagentStart' | 'SubagentStop' | 'PreCompact' | 'PostCompact' | 'PreModelSwitch' | 'PostModelSwitch' | 'PermissionRequest' | 'PermissionDenied' | 'Setup' | 'TeammateIdle' | 'TaskCreated' | 'TaskCompleted' | 'Elicitation' | 'ElicitationResult' | 'ConfigChange' | 'WorktreeCreate' | 'WorktreeRemove' | 'InstructionsLoaded' | 'CwdChanged' | 'FileChanged' | 'DirectoryAdded' | 'MessageDisplay';

export declare type HookInput = PreToolUseHookInput | PostToolUseHookInput | PostToolUseFailureHookInput | PostToolBatchHookInput | PermissionDeniedHookInput | NotificationHookInput | UserPromptSubmitHookInput | UserPromptExpansionHookInput | SessionStartHookInput | SessionEndHookInput | StopHookInput | StopFailureHookInput | SubagentStartHookInput | SubagentStopHookInput | PreCompactHookInput | PostCompactHookInput | PreModelSwitchHookInput | PostModelSwitchHookInput | PermissionRequestHookInput | SetupHookInput | TeammateIdleHookInput | TaskCreatedHookInput | TaskCompletedHookInput | ElicitationHookInput | ElicitationResultHookInput | ConfigChangeHookInput | InstructionsLoadedHookInput | WorktreeCreateHookInput | WorktreeRemoveHookInput | CwdChangedHookInput | FileChangedHookInput | DirectoryAddedHookInput | MessageDisplayHookInput;

export declare type HookJSONOutput = AsyncHookJSONOutput | SyncHookJSONOutput;

export declare type HookPermissionDecision = 'allow' | 'deny' | 'ask' | 'defer';

/**
 * Copy a local JSONL session into a SessionStore.
 *
 * Reads the session file (and optionally subagent transcripts) from disk
 * and calls `store.append()` for each. Entries are appended in batches of
 * `batchSize` to avoid backend payload limits; the store's `append()` is
 * called multiple times per session. Useful for migrating existing local
 * sessions to a remote backend.
 *
 * @alpha
 * @param sessionId - UUID of the local session to import
 * @param store - Destination SessionStore
 * @param options - `{ dir?, includeSubagents?, batchSize? }`
 */
export declare function importSessionToStore(_sessionId: string, _store: SessionStore, _options?: ImportSessionToStoreOptions): Promise<void>;

/**
 * Options for importing a local JSONL session into a SessionStore.
 * @alpha
 */
export declare type ImportSessionToStoreOptions = {
    /**
     * Project directory path (same semantics as `listSessions({ dir })`).
     * When omitted, all project directories are searched for the session file
     * and the destination projectKey is derived from the resolved cwd.
     */
    dir?: string;
    /**
     * If true, also import subagent transcripts. Default: true.
     */
    includeSubagents?: boolean;
    /**
     * Maximum entries per `store.append()` call. Entries are appended in
     * batches of this size to avoid backend payload limits; the store's
     * `append()` is called multiple times per session. Default: 500.
     */
    batchSize?: number;
};

export declare type InferShape<T extends AnyZodRawShape> = {
    [K in keyof T]: T[K] extends {
        _output: infer O;
    } ? O : never;
} & {};

/**
 * In-memory SessionStore implementation for testing and development.
 * Stores entries in a Map keyed by a composite string.
 * Not suitable for production -- data is lost when the process exits.
 * @alpha
 */
export declare class InMemorySessionStore implements SessionStore {
    private store;
    private mtimes;
    private summaries;
    private lastMtime;
    private keyToString;
    append(key: SessionKey, entries: SessionStoreEntry[]): Promise<void>;
    load(key: SessionKey): Promise<SessionStoreEntry[] | null>;
    listSessions(projectKey: string): Promise<Array<{
        sessionId: string;
        mtime: number;
    }>>;
    listSessionSummaries(projectKey: string): Promise<SessionSummaryEntry[]>;
    delete(key: SessionKey): Promise<void>;
    listSubkeys(key: {
        projectKey: string;
        sessionId: string;
    }): Promise<string[]>;
    /** Test helper -- get all entries for a key */
    getEntries(key: SessionKey): SessionStoreEntry[];
    /** Test helper -- number of stored sessions (main transcripts only) */
    get size(): number;
    /** Test helper -- clear all stored data */
    clear(): void;
}

export declare type InstructionsLoadedHookInput = BaseHookInput & {
    hook_event_name: 'InstructionsLoaded';
    file_path: string;
    memory_type: 'User' | 'Project' | 'Local' | 'Managed';
    load_reason: 'session_start' | 'nested_traversal' | 'path_glob_match' | 'include' | 'compact';
    globs?: string[];
    trigger_file_path?: string;
    parent_file_path?: string;
};

export declare type JsonSchemaOutputFormat = {
    type: 'json_schema';
    schema: Record<string, unknown>;
};

/**
 * Former names that permission rules, hook matchers, `tools` and
 * `disallowedTools` still accept, each mapped to the tool's current name. An
 * entry is dropped when its tool is removed.
 *
 * @alpha
 */
export declare const LEGACY_TOOL_NAME_ALIASES: Readonly<Record<string, string>>;

/**
 * List sessions with metadata.
 *
 * When `dir` is provided, returns sessions for that project directory
 * and its git worktrees. When omitted, returns sessions across all
 * projects.
 *
 * Use `limit` and `offset` for pagination.
 *
 * @example
 * ```typescript
 * // List sessions for a specific project
 * const sessions = await listSessions({ dir: '/path/to/project' })
 *
 * // Paginate
 * const page1 = await listSessions({ limit: 50 })
 * const page2 = await listSessions({ limit: 50, offset: 50 })
 * ```
 */
export declare function listSessions(_options?: ListSessionsOptions): Promise<SDKSessionInfo[]>;

/**
 * Options for listing sessions.
 */
export declare type ListSessionsOptions = {
    /**
     * Directory to list sessions for. When provided, returns sessions for
     * this project directory (and optionally its git worktrees). When omitted,
     * returns sessions across all projects.
     */
    dir?: string;
    /** Maximum number of sessions to return. */
    limit?: number;
    /**
     * Number of sessions to skip from the start of the sorted result set.
     * Use with `limit` for pagination. Defaults to 0.
     */
    offset?: number;
    /**
     * When `dir` is provided and the directory is inside a git repository,
     * include sessions from all git worktree paths. Defaults to `true`.
     *
     * Only applies when reading from the local filesystem.
     */
    includeWorktrees?: boolean;
    /**
     * Include programmatic/headless sessions (SDK entrypoints `sdk-cli`,
     * `sdk-ts`, `sdk-py`) and daemon/daemon-worker sessions. Defaults to
     * `true` for backward compatibility — SDK consumers enumerating their
     * own sessions see them. IDE session pickers pass `false` for parity
     * with terminal `/resume`.
     *
     * Only applies when reading from the local filesystem; ignored when
     * `sessionStore` is provided.
     */
    includeProgrammatic?: boolean;
    /**
     * When provided, list sessions from this store instead of the local
     * filesystem. Requires `store.listSessions` to be defined.
     * @alpha
     */
    sessionStore?: SessionStore;
};

/**
 * Lists subagent IDs for a given session by scanning the subagents directory.
 *
 * Subagent transcripts are stored at
 * `~/.claude/projects/<dir>/<sessionId>/subagents/agent-<agentId>.jsonl`.
 *
 * @param sessionId - UUID of the session
 * @param options - Optional dir to narrow the project search
 * @returns Array of subagent ID strings, or empty array if none found
 */
export declare function listSubagents(_sessionId: string, _options?: ListSubagentsOptions): Promise<string[]>;

/**
 * Options for listing subagents.
 */
export declare type ListSubagentsOptions = {
    /** Project directory to find the session in. If omitted, searches all projects. */
    dir?: string;
    /**
     * When provided, list subagents from this store instead of the local
     * filesystem. Requires `store.listSubkeys` to be defined.
     * @alpha
     */
    sessionStore?: SessionStore;
};

/**
 * Say which of `models` a managed `deniedModels` list blocks, without spawning
 * the Claude CLI. Pass `effective.deniedModels` from {@link resolveSettings}.
 * Nothing throws: a bad list or entry is ignored, a bad model is `false`, and
 * `models` that isn't a list gets an empty `denied`; `warnings` notes each.
 *
 * @remarks
 * **Not the CLI's enforcement: grant nothing by it.** It compares model IDs
 * with entries alone. `true` means that this version's CLI refuses the model
 * too; `false` promises nothing: the CLI also judges what an alias or a custom
 * name stands for, a model's other names, path tails and `modelOverrides`.
 *
 * @alpha
 */
export declare function matchDeniedModels(_models: readonly string[], _deniedModels: readonly string[] | undefined): Promise<DeniedModelsMatch>;

export declare type McpClaudeAIProxyServerConfig = {
    type: 'claudeai-proxy';
    url: string;
    id: string;
    /**
     * Per-server tool-call timeout in milliseconds. Overrides the MCP_TOOL_TIMEOUT environment variable for this server. Hard wall-clock limit per call; progress notifications do not extend it. Values below 1000ms are ignored (falls through to MCP_TOOL_TIMEOUT or the default).
     */
    timeout?: number;
};

export declare type McpHttpServerConfig = {
    type: 'http';
    url: string;
    headers?: Record<string, string>;
    tools?: McpServerToolPolicy[];
    /**
     * Per-server tool-call timeout in milliseconds. Overrides the MCP_TOOL_TIMEOUT environment variable for this server. Hard wall-clock limit per call; progress notifications do not extend it. Values below 1000ms are ignored (falls through to MCP_TOOL_TIMEOUT or the default).
     */
    timeout?: number;


    /**
     * When true, all tools from this server are always included in the prompt and never deferred behind tool search, except a tool the server itself lists with _meta anthropic/alwaysLoad set to false. Equivalent to setting defer_loading: false on the API. When false, all tools from this server are deferred behind tool search. Default: tools are deferred when tool search is enabled. As a side effect, true also blocks startup until the server is connected (capped at the standard 5s connect timeout) even though MCP startup is otherwise non-blocking by default, since the tools must be present when the turn-1 prompt is built.
     */
    alwaysLoad?: boolean;

};

export declare type McpSdkServerConfig = {
    type: 'sdk';
    name: string;
    /**
     * Per-server tool-call timeout in milliseconds. Overrides the MCP_TOOL_TIMEOUT environment variable for this server. Hard wall-clock limit per call; progress notifications do not extend it. Values below 1000ms are ignored (falls through to MCP_TOOL_TIMEOUT or the default). Applies when the server is first registered; changing it for an already-registered server has no effect until it is removed and re-added.
     */
    timeout?: number;






    /**
     * Per-tool permission policy the host declares for this server's tools (not the tool definitions passed to createSdkMcpServer). always_ask: the CLI asks the host (canUseTool or the permission prompt tool) before each call, even where an allow rule or allowedTools covers the tool, and under bypassPermissions outside a hosted remote session (CLAUDE_CODE_REMOTE); under dontAsk the call is denied; in auto mode the classifier decides, except that by default a tool annotated destructiveHint still asks. always_deny: calls are denied, except a mod's own ($.tool.call, $.mcp.call). always_allow and org_max_permission are ignored on sdk servers; grant allows with allowedTools or canUseTool. Read from initialize (sdkMcpServerConfigs) and from each mcp_set_servers entry that names the server. On the wire an entry without tools states no policy: on initialize the stored list and the rules stand; on mcp_set_servers the rules are replaced without them. The Agent SDK always re-sends the registered list. An entry whose policy is not one of the three asks; an entry without a string name is dropped and the rest apply; a value that is not a list reads as absent.
     */
    tools?: McpServerToolPolicy[];
};

/**
 * MCP SDK server config with an actual McpServer instance.
 * Not serializable - contains a live McpServer object.
 */
export declare type McpSdkServerConfigWithInstance = McpSdkServerConfig & {
    instance: McpServer;
};

/**
 * Union of all MCP server config types, including those with non-serializable instances.
 */
export declare type McpServerConfig = McpStdioServerConfig | McpSSEServerConfig | McpHttpServerConfig | McpSdkServerConfigWithInstance;

export declare type McpServerConfigForProcessTransport = McpStdioServerConfig | McpSSEServerConfig | McpHttpServerConfig | McpSdkServerConfig;

/**
 * The MCP server serving this tool, for `mcp__*` tools: `name` is the server's config key (for `source: "sdk"`, exactly the name the SDK host registered in `sdkMcpServers` / `mcp_set_servers`; for any other source, the key as authored in that configuration — untrusted text, the same value `mcp_status` and system/init report, to be escaped before display), `source` is where its definition came from — `sdk` (an in-process server the SDK host runs; only the host can register one, so a configured server of the same name never reads `sdk`), `plugin` (a server a plugin ships or registers at runtime), or a config scope (`user`, `project`, `local`, `dynamic` for --mcp-config / `mcp_set_servers` process servers, `managed`, `enterprise`, `claudeai`, `agent`). Key trust on `source`, not on the name or the tool-name prefix. Absent for non-MCP tools.
 */
export declare type McpServerProvenance = {
    name: string;
    /**
     * sdk | plugin | user | project | local | dynamic | managed | enterprise | claudeai | agent — an open set; treat unknown values as an unrecognized configured source, never as sdk.
     */
    source: string;
};

/**
 * Status information for an MCP server connection.
 */
export declare type McpServerStatus = {
    /**
     * Server name as configured
     */
    name: string;
    /**
     * Current connection status
     */
    status: 'connected' | 'failed' | 'needs-auth' | 'pending' | 'disabled';
    /**
     * Server information (available when connected)
     */
    serverInfo?: {
        name: string;
        version: string;
    };
    /**
     * Error message (available when status is 'failed')
     */
    error?: string;

    /**
     * Server configuration (includes URL for HTTP/SSE servers)
     */
    config?: McpServerStatusConfig;




    /**
     * Configuration scope (e.g., project, user, local, claudeai, managed)
     */
    scope?: string;
    /**
     * Where the server definition came from: sdk (an in-process server the SDK host registered — only the host can register one), plugin (a server a plugin ships or registers at runtime), or the config scope (user, project, local, dynamic, managed, enterprise, claudeai, agent). Key trust on this, not on the name. Absent on CLIs that predate the field.
     */
    source?: string;
    /**
     * Tools provided by this server (available when connected)
     */
    tools?: {
        name: string;
        description?: string;
        annotations?: {
            readOnly?: boolean;
            destructive?: boolean;
            openWorld?: boolean;
        };
        /**
         * The MCP Apps (SEP-1865) members of the tool's `_meta`, for a host that renders the tool's `ui://` resource, under the keys the server used: `ui` (an object: `resourceUri`, a `ui://` string; `visibility`, an array of 'model' | 'app'; and any other member the server sent) and the deprecated flat `ui/resourceUri` (a `ui://` string). Each is validated and size-bounded, and withheld if it fails. Of a `ui` that fails, only `visibility` still arrives: the 'model' and 'app' entries the server listed, or `[]` (neither audience) if `ui` is not an object or `visibility` not an array; `null` counts as absent. So a tool with no `visibility` declared none. A CLI that does not advertise `mcp_call_result_not_for_model_v1` may withhold a failed `ui` whole. Every other `_meta` key is withheld. Present only on a tool that declares one, from CLIs that advertise `mcp_tool_ui_meta_v1`.
         */
        _meta?: Record<string, unknown>;
    }[];


};

export declare type McpServerStatusConfig = McpServerConfigForProcessTransport | McpClaudeAIProxyServerConfig;

/**
 * Per-tool permission policy for an MCP server: carried on mcp_set_servers for remote (http/sse) servers, and on mcp_set_servers or initialize (sdkMcpServerConfigs) for host-registered sdk servers, where only always_ask and always_deny take effect.
 */
export declare type McpServerToolPolicy = {
    name: string;
    permission_policy?: 'always_allow' | 'always_ask' | 'always_deny';
    /**
     * Org admin's per-tool ceiling. Drives the auto-mode isOrgAskCeiling gate so an admin 'ask' cap forces a user prompt even in auto mode.
     */
    org_max_permission?: 'allow' | 'ask' | 'blocked';
};

/**
 * Result of a setMcpServers operation.
 */
export declare type McpSetServersResult = {
    /**
     * Names of servers that were added
     */
    added: string[];
    /**
     * Names of servers that were removed
     */
    removed: string[];
    /**
     * Map of server names to error messages for servers that failed to connect
     */
    errors: Record<string, string>;
};

export declare type McpSSEServerConfig = {
    type: 'sse';
    url: string;
    headers?: Record<string, string>;
    tools?: McpServerToolPolicy[];
    /**
     * Per-server tool-call timeout in milliseconds. Overrides the MCP_TOOL_TIMEOUT environment variable for this server. Hard wall-clock limit per call; progress notifications do not extend it. Values below 1000ms are ignored (falls through to MCP_TOOL_TIMEOUT or the default).
     */
    timeout?: number;


    /**
     * When true, all tools from this server are always included in the prompt and never deferred behind tool search, except a tool the server itself lists with _meta anthropic/alwaysLoad set to false. Equivalent to setting defer_loading: false on the API. When false, all tools from this server are deferred behind tool search. Default: tools are deferred when tool search is enabled. As a side effect, true also blocks startup until the server is connected (capped at the standard 5s connect timeout) even though MCP startup is otherwise non-blocking by default, since the tools must be present when the turn-1 prompt is built.
     */
    alwaysLoad?: boolean;

};

export declare type McpStdioServerConfig = {
    type?: 'stdio';
    command: string;
    args?: string[];
    env?: Record<string, string>;
    /**
     * Per-server tool-call timeout in milliseconds. Overrides the MCP_TOOL_TIMEOUT environment variable for this server. Hard wall-clock limit per call; progress notifications do not extend it. Values below 1000ms are ignored (falls through to MCP_TOOL_TIMEOUT or the default).
     */
    timeout?: number;
    /**
     * When true, all tools from this server are always included in the prompt and never deferred behind tool search, except a tool the server itself lists with _meta anthropic/alwaysLoad set to false. Equivalent to setting defer_loading: false on the API. When false, all tools from this server are deferred behind tool search. Default: tools are deferred when tool search is enabled. As a side effect, true also blocks startup until the server is connected (capped at the standard 5s connect timeout) even though MCP startup is otherwise non-blocking by default, since the tools must be present when the turn-1 prompt is built.
     */
    alwaysLoad?: boolean;

};

/**
 * Hook input for the MessageDisplay event. Fired with each batch of newly completed lines while an assistant message streams. Display-only: the stored message and what the model sees are untouched.
 */
export declare type MessageDisplayHookInput = BaseHookInput & {
    hook_event_name: 'MessageDisplay';
    /**
     * UUID of the current turn.
     */
    turn_id: string;
    /**
     * UUID of the assistant message being displayed. Stable across every flush of the same message. Not the API msg_… id.
     */
    message_id: string;
    /**
     * Zero-based index of this delta within the message. Increments by one per flush.
     */
    index: number;
    /**
     * True on the message's last flush. Exactly one flush per message has it.
     */
    final: boolean;
    /**
     * The newly completed lines since the prior flush. Always whole lines, except on the final flush which may end mid-line. The delta of the final flush is empty when the message ends on a newline; treat final as the end-of-message signal regardless.
     */
    delta: string;
};

/**
 * Hook-specific output for the MessageDisplay event. Display-only: replaces the delta on screen without changing the stored message.
 */
export declare type MessageDisplayHookSpecificOutput = {
    hookEventName: 'MessageDisplay';
    /**
     * Text displayed in place of the delta. Omit (or return the delta unchanged) to display the original.
     */
    displayContent?: string;
};

/**
 * Information about an available model.
 */
export declare type ModelInfo = {
    /**
     * Model identifier to use in API calls
     */
    value: string;
    /**
     * Canonical wire model id this row's `value` resolves to (e.g. 'sonnet' → 'claude-sonnet-5'). Lets hosts match a persisted explicit id against the alias row that covers it.
     */
    resolvedModel?: string;
    /**
     * Human-readable display name
     */
    displayName: string;
    /**
     * Description of the model's capabilities
     */
    description: string;
    /**
     * Whether this model supports effort levels
     */
    supportsEffort?: boolean;
    /**
     * Available effort levels for this model
     */
    supportedEffortLevels?: ('low' | 'medium' | 'high' | 'xhigh' | 'max')[];
    /**
     * Whether this model supports adaptive thinking (Claude decides when and how much to think)
     */
    supportsAdaptiveThinking?: boolean;
    /**
     * Whether this model supports fast mode
     */
    supportsFastMode?: boolean;
    /**
     * Whether this model supports auto mode
     */
    supportsAutoMode?: boolean;



};

export declare type ModelUsage = {
    inputTokens: number;
    outputTokens: number;
    /**
     * Thinking tokens, already counted inside outputTokens. Counts only turns run on CLI versions that record this field: absent when none did, and partial for a resumed session that began on an older version.
     */
    thinkingTokens?: number;
    cacheReadInputTokens: number;
    cacheCreationInputTokens: number;
    /**
     * Cache writes with a 5-minute lifetime, already counted inside cacheCreationInputTokens. This and cacheCreationEphemeral1hInputTokens can add up to less than cacheCreationInputTokens, because a response that does not report how long its cache writes live adds to neither. costUSD prices those writes at the 5-minute rate. Counts only turns run on CLI versions that record this field: absent when none did, and an undercount when part of the session ran on an older version.
     */
    cacheCreationEphemeral5mInputTokens?: number;
    /**
     * Cache writes with a 1-hour lifetime, already counted inside cacheCreationInputTokens. costUSD prices them at the 1-hour rate when the model's price table has one. The built-in list prices do. A managed-settings modelPricing row does not: its one cache-write rate applies to both lifetimes. costUSD never uses the 1-hour rate for a response that a fallback model served after a refusal. Absent or an undercount in the same cases as cacheCreationEphemeral5mInputTokens.
     */
    cacheCreationEphemeral1hInputTokens?: number;
    webSearchRequests: number;
    costUSD: number;
    contextWindow: number;
    maxOutputTokens: number;
    /**
     * Canonical model id used for the pricing lookup (e.g. 'claude-opus-4-7'). May differ from the raw model string this entry is keyed by (provider-specific ids, aliases).
     */
    canonicalModel?: string;
    /**
     * API provider that served this model (e.g. 'firstParty', 'bedrock', 'vertex', 'foundry', 'anthropicAws', 'mantle', 'gateway').
     */
    provider?: string;
    /**
     * Which price table the most recent request for this model was priced at: Claude Code's built-in list prices ('list'), the organization's managed-settings modelPricing rates or multiplier ('managed'), or neither ('unknown' — no pricing row and no built-in price matched the model ID, so costUSD is a guess at the default model's rate). Overwritten per request like canonicalModel, so a consumer that differences the cumulative costUSD per turn gets that turn's basis. Absent until this process has priced a request for the model (e.g. right after --resume) and on builds that predate the field; treat as 'list'.
     */
    costBasis?: 'list' | 'managed' | 'unknown';
};

export declare type NonNullableUsage = {
    [K in keyof BetaUsage]: K extends 'fallback_credit' ? BetaUsage[K] : NonNullable<BetaUsage[K]>;
};

export declare type NotificationHookInput = BaseHookInput & {
    hook_event_name: 'Notification';
    message: string;
    title?: string;
    notification_type: string;
};

export declare type NotificationHookSpecificOutput = {
    hookEventName: 'Notification';
    additionalContext?: string;
};

/**
 * Callback for handling MCP elicitation requests.
 * Called when an MCP server requests user input and no hook handles it.
 *
 * Return `null` ONLY after the consumer has already sent the
 * control_response out-of-band (e.g. a signed HTTP POST echoing
 * `requestId`); the SDK will skip its own transport write. Same contract as
 * {@link CanUseTool}. Fail-closed: an accidental null means no response is
 * sent and the elicitation stays pending until the server times it out.
 */
export declare type OnElicitation = (request: ElicitationRequest, options: {
    signal: AbortSignal;
    /**
     * The control_request envelope's `request_id`. A control_response sent
     * out-of-band (e.g. a signed HTTP POST instead of the SDK's WS write)
     * must echo this value for the worker to match it.
     */
    requestId: string;
}) => Promise<ElicitationResult | null>;

/**
 * Callback for handling `request_user_dialog` control requests.
 * Called when the CLI asks the host to render a blocking dialog.
 * If not provided, the dialog is left unanswered so a renderer-bearing
 * client (or the worker's park deadline) can settle it.
 *
 * Return `null` ONLY after the consumer has already sent the
 * control_response out-of-band (e.g. a signed HTTP POST echoing
 * `requestId`); the SDK will skip its own transport write. Same contract as
 * {@link CanUseTool}. Fail-closed: an accidental null means no response is
 * sent and the dialog stays parked until the worker's deadline.
 */
export declare type OnUserDialog = (request: UserDialogRequest, options: {
    signal: AbortSignal;
    /**
     * The control_request envelope's `request_id`. A control_response sent
     * out-of-band (e.g. a signed HTTP POST instead of the SDK's WS write)
     * must echo this value for the worker to match it.
     */
    requestId: string;
}) => Promise<UserDialogResult | null>;

/**
 * Options for the query function.
 * Contains callbacks and other non-serializable fields.
 */
export declare type Options = {
    /**
     * Controller for cancelling the query. When aborted, the query will stop
     * and clean up resources.
     */
    abortController?: AbortController;
    /**
     * Additional directories Claude can access beyond the current working directory.
     * Paths should be absolute.
     */
    additionalDirectories?: string[];
    /**
     * The trusted checkout `cwd` is a worktree of. Project settings (hooks,
     * permissions), `.mcp.json`, the `.claude` config trees (commands, agents,
     * skills, workflows, routines, output-styles; a routine cannot be
     * activated with it)
     * and `CLAUDE_PROJECT_DIR` come from here instead of `cwd`, so whatever
     * the branch checked out in `cwd` carries is not what the session runs.
     * Absolute path.
     */
    projectConfigRoot?: string;
    /**
     * Agent name for the main thread. When specified, the agent's system prompt,
     * tool restrictions, and model will be applied to the main conversation.
     * The agent must be defined either in the `agents` option or in settings.
     *
     * This is equivalent to the `--agent` CLI flag.
     *
     * @example
     * ```typescript
     * agent: 'code-reviewer',
     * agents: {
     *   'code-reviewer': {
     *     description: 'Reviews code for best practices',
     *     prompt: 'You are a code reviewer...'
     *   }
     * }
     * ```
     */
    agent?: string;
    /**
     * Programmatically define custom subagents that can be invoked via the Agent tool.
     * Keys are agent names, values are agent definitions.
     *
     * @example
     * ```typescript
     * agents: {
     *   'test-runner': {
     *     description: 'Runs tests and reports results',
     *     prompt: 'You are a test runner...',
     *     tools: ['Read', 'Grep', 'Glob', 'Bash']
     *   }
     * }
     * ```
     */
    agents?: Record<string, AgentDefinition>;
    /**
     * List of tool names that are auto-allowed without prompting for permission.
     * These tools will execute automatically without asking the user for approval.
     * To restrict which tools are available, use the `tools` option instead.
     *
     * Note: passing `'Skill'` here is deprecated — use the `skills` option instead.
     */
    allowedTools?: string[];
    /**
     * Custom permission handler for controlling tool usage. Called before each
     * tool execution to determine if it should be allowed, denied, or prompt the user.
     */
    canUseTool?: CanUseTool;
    /**
     * Continue the most recent conversation in the current directory instead of starting a new one.
     * Mutually exclusive with `resume`.
     */
    continue?: boolean;
    /**
     * Current working directory for the session. Defaults to `process.cwd()`.
     */
    cwd?: string;
    /**
     * List of tool names that are disallowed. These tools will be removed
     * from the model's context and cannot be used, even if they would
     * otherwise be allowed.
     */
    disallowedTools?: string[];
    /**
     * Map of tool-name aliases applied before name resolution. When the
     * model emits a `tool_use` whose name is a key in this map, the tool
     * execution path resolves the mapped name instead.
     *
     * This lets SDK consumers redirect built-in tool names to their own
     * tools. For example, a host that runs Bash inside a remote sandbox via
     * an MCP tool can set `{ Bash: 'mcp__workspace__bash' }` so that if the
     * model emits `Bash` (e.g. because a skill document instructed it to),
     * the call is routed to the MCP tool instead of failing as unknown.
     *
     * The redirect is single-hop: an alias that points at another aliased
     * name resolves that target literally rather than following a chain, so
     * cycles like `{A: 'B', B: 'A'}` cannot loop.
     *
     * `toolAliases` is complementary to `disallowedTools`, not a replacement
     * for it: the alias only affects name-based lookup of model-emitted
     * `tool_use` blocks, whereas `disallowedTools` also blocks harness-internal
     * direct calls that hold the tool object without a name lookup.
     *
     * @example
     * ```typescript
     * toolAliases: { Bash: 'mcp__workspace__bash' }
     * ```
     */
    toolAliases?: Record<string, string>;

    /**
     * Specify the base set of available built-in tools.
     * - `string[]` - Array of specific tool names (e.g., `['Bash', 'Read', 'Edit']`)
     * - `[]` (empty array) - Disable all built-in tools
     * - `{ type: 'preset'; preset: 'claude_code' }` - Use all default Claude Code tools
     *
     * Note: native builds may provide search via Bash `find`/`grep` instead of the
     * dedicated Grep/Glob tools. List Grep/Glob here or in `allowedTools` to get them.
     */
    tools?: string[] | {
        type: 'preset';
        preset: 'claude_code';
    };
    /**
     * Environment variables for the Claude Code process.
     *
     * When set, this value REPLACES the subprocess environment entirely — it is
     * not merged with `process.env`. Spread `process.env` yourself if the
     * subprocess still needs inherited variables like `PATH`, `HOME`, or
     * `ANTHROPIC_API_KEY`. When omitted, the subprocess inherits `process.env`.
     *
     * SDK consumers can identify their app/library to include in the User-Agent header by setting:
     * - `CLAUDE_AGENT_SDK_CLIENT_APP` - Your app/library identifier (e.g., "my-app/1.0.0", "my-library/2.1")
     *
     * @example
     * ```typescript
     * env: { ...process.env, CLAUDE_AGENT_SDK_CLIENT_APP: 'my-app/1.0.0' }
     * ```
     */
    env?: {
        [envVar: string]: string | undefined;
    };
    /**
     * JavaScript runtime to use for executing Claude Code.
     * Auto-detected if not specified.
     */
    executable?: 'bun' | 'deno' | 'node';
    /**
     * Additional arguments to pass to the JavaScript runtime executable.
     */
    executableArgs?: string[];
    /**
     * Additional CLI arguments to pass to Claude Code.
     * Keys are argument names (without --), values are argument values.
     * Use `null` for boolean flags.
     */
    extraArgs?: Record<string, string | null>;
    /**
     * Fallback model(s) to use if the primary model is overloaded or
     * unavailable. Accepts a comma-separated list to try each in order. The
     * primary model is re-tried at the start of each user turn, so a temporary
     * outage doesn't permanently demote the session.
     */
    fallbackModel?: string;
    /**
     * Enable file checkpointing to track file changes during the session.
     * When enabled, files can be rewound to their state at any user message
     * using `Query.rewindFiles()`.
     *
     * File checkpointing creates backups of files before they are modified,
     * allowing you to restore them to previous states.
     */
    enableFileCheckpointing?: boolean;
    /**
     * Per-tool configuration for built-in tools.
     *
     * @example
     * ```typescript
     * toolConfig: {
     *   askUserQuestion: { previewFormat: 'html' }
     * }
     * ```
     */
    toolConfig?: ToolConfig;
    /**
     * When true, resumed sessions will fork to a new session ID rather than
     * continuing the previous session. Use with `resume`.
     */
    forkSession?: boolean;
    /**
     * Enable beta features. Currently supported:
     * - `'context-1m-2025-08-07'` - Enable 1M token context window (Sonnet 4/4.5 only)
     *
     * @see https://platform.claude.com/docs/en/api/beta-headers
     */
    betas?: SdkBeta[];
    /**
     * Hook callbacks for responding to various events during execution.
     * Hooks can modify behavior, add context, or implement custom logic.
     *
     * @example
     * ```typescript
     * hooks: {
     *   PreToolUse: [{
     *     hooks: [async (input) => ({ continue: true })]
     *   }]
     * }
     * ```
     */
    hooks?: Partial<Record<HookEvent, HookCallbackMatcher[]>>;
    /**
     * Callback for handling MCP elicitation requests.
     * Called when an MCP server requests user input (form fields, URL auth, etc.)
     * and no hook handles the request first.
     *
     * If not provided, elicitation requests that aren't handled by hooks will
     * be declined automatically.
     *
     * @example
     * ```typescript
     * onElicitation: async (request) => {
     *   if (request.mode === 'url') {
     *     // Handle URL-based auth
     *     return { action: 'accept' }
     *   }
     *   // Provide form values
     *   return { action: 'accept', content: { name: 'Test' } }
     * }
     * ```
     */
    onElicitation?: OnElicitation;
    /**
     * Callback for handling `request_user_dialog` control requests — blocking
     * dialogs the CLI asks the host to render. Each `dialogKind` defines its
     * own payload and result shape.
     *
     * When the host answers `{behavior: 'cancelled'}` — the required answer
     * for an unrecognized `dialogKind` — the CLI applies the dialog's default
     * behavior. If the callback is not provided at all, the SDK sends no
     * answer: on a multi-client session another attached client may be the
     * declared renderer, and an auto-reply from this one would settle the
     * dialog out from under it. An unanswered dialog is bounded by the CLI's
     * park deadline.
     */
    onUserDialog?: OnUserDialog;
    /**
     * Dialog kinds this consumer's `onUserDialog` can actually render
     * (`request_user_dialog` `dialog_kind` values, e.g.
     * 'refusal_fallback_prompt'). Declare only kinds your UI genuinely
     * displays and answers. Providing `onUserDialog` alone does NOT opt the
     * consumer into receiving dialogs — the CLI only emits a dialog kind
     * declared here.
     *
     * The CLI fails closed on absence: a dialog kind not declared here is
     * never emitted to this session — the flow behind it degrades to its
     * no-dialog behavior instead (for 'refusal_fallback_prompt', the classic
     * refusal error message ends the turn). Omitting the option entirely
     * means no dialogs are emitted, even with `onUserDialog` wired.
     *
     * Requires `onUserDialog`; passing a non-empty list without the callback
     * throws at option intake. On multi-client (remote) sessions the first
     * attached client's declaration wins for the worker's lifetime, and the
     * winning declaration is persisted to worker metadata so it survives
     * worker restarts (restored as a default that the next epoch's first
     * explicit declaration overrides).
     */
    supportedDialogKinds?: string[];
    /**
     * Declares that this consumer renders a per-task stop control wired to
     * the `stop_task` control request, so the user can stop an individual
     * background task.
     *
     * When declared, an interrupt on an open-input (interactive
     * stream-json) session spares running background agents/workflows —
     * Stop only aborts the current turn, and tasks are stopped one at a
     * time through the consumer's own affordance. Closed-input exception:
     * on a one-shot run (the string `prompt` form and `-p`, which close
     * stdin), hold-back tasks are still killed when the held result is
     * released, regardless of this declaration — with stdin closed, a
     * `stop_task` control could never be delivered, so the fail-closed
     * kill stands. The CLI also fails closed on absence: without the
     * declaration, an interrupt kills background tasks, because a spared
     * runaway task would otherwise be unstoppable from this consumer short
     * of ending the session. First-attached-client
     * wins on multi-client sessions; later initializes do not change it.
     */
    perTaskStopAffordance?: boolean;


    /**
     * When false, disables session persistence to disk. Sessions will not be
     * saved to ~/.claude/projects/ and cannot be resumed later. Useful for
     * ephemeral or automated workflows where session history is not needed.
     *
     * @default true
     */
    persistSession?: boolean;
    /**
     * Mirror session transcripts to an external store. When set, the subprocess
     * still writes to CLAUDE_CONFIG_DIR (set it to /tmp for ephemeral local copy)
     * AND emits entries to this adapter via dual-write.
     *
     * Cannot be used with persistSession: false -- local writes are required
     * for the mirror to function (the mirror hook fires after local write success).
     *
     * Default: undefined (no mirroring, today's behavior).
     * @alpha
     */
    sessionStore?: SessionStore;
    /**
     * Controls how aggressively transcript entries are flushed to
     * {@link Options.sessionStore}. Defaults to `'batched'`. Ignored when
     * `sessionStore` is not set.
     *
     * @alpha
     */
    sessionStoreFlush?: SessionStoreFlush;
    /**
     * Timeout for each `sessionStore.load()` / `sessionStore.listSubkeys()` call
     * during resume materialization. If the adapter doesn't settle within this
     * window the query fails with a clear error instead of hanging the iterator
     * forever (the deferred-spawn path otherwise has no upper bound).
     *
     * @default 60_000
     * @alpha
     */
    loadTimeoutMs?: number;
    /**
     * Include hook lifecycle events in the output stream.
     * When true, `hook_started`, `hook_progress`, and `hook_response` system
     * messages will be emitted for all hook event types (PreToolUse, PostToolUse,
     * Stop, etc.). SessionStart and Setup hook events are always emitted
     * regardless of this setting.
     *
     * @default false
     */
    includeHookEvents?: boolean;
    /**
     * Include partial/streaming message events in the output.
     * When true, `SDKPartialAssistantMessage` events will be emitted during streaming.
     */
    includePartialMessages?: boolean;
    /**
     * Forward subagent text and thinking blocks as assistant/user messages with
     * `parent_tool_use_id` set. By default, only tool_use/tool_result blocks from
     * subagents are emitted (enough for a heartbeat counter). When true, the full
     * subagent conversation is forwarded so consumers can render a nested transcript.
     */
    forwardSubagentText?: boolean;
    /**
     * Send every user message with `client_composed: true`, so the CLI delivers
     * the prompt text as written: no `@path` file-mention expansion and no
     * slash-command dispatch. Use when prompt text is assembled from content
     * the end user did not type. Covers string prompts, streamed messages and
     * `Query.streamInput()`. While the option is on there is no per-message
     * opt-out; for per-turn control, leave it off and set `client_composed: true`
     * on individual streamed messages instead.
     *
     * On current CLIs a turn delivered this way also skips the CLI's turn-start
     * attachment pass as a whole: `@server:resource` MCP mentions are not
     * expanded either, and the prompt is sent without the context the CLI
     * normally attaches alongside it (nested `CLAUDE.md` and rules files, skill
     * and tool listings, and the CLI's other per-turn reminders). The pass the
     * CLI runs between tool calls is unaffected, so most of that context arrives
     * after the turn's first tool call rather than with the prompt. Narrowing
     * the skip to `@path` expansion and slash-command dispatch alone is
     * CLI-side follow-up work.
     *
     * Requires Claude Code 2.1.248 or later; older CLIs ignore the field.
     *
     * @default false
     */
    verbatimPrompts?: boolean;
    /**
     * Controls Claude's thinking/reasoning behavior.
     *
     * - `{ type: 'adaptive' }` — Claude decides when and how much to think (Opus 4.6+).
     *   This is the default for models that support it.
     * - `{ type: 'enabled', budgetTokens: number }` — Fixed thinking token budget (older models)
     * - `{ type: 'disabled' }` — No extended thinking
     *
     * When set, takes precedence over the deprecated `maxThinkingTokens`.
     *
     * @see https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking
     */
    thinking?: ThinkingConfig;
    /**
     * Controls how much effort Claude puts into its response.
     * Works with adaptive thinking to guide thinking depth.
     *
     * @see https://platform.claude.com/docs/en/build-with-claude/effort
     */
    effort?: EffortLevel;
    /**
     * Maximum number of tokens the model can use for its thinking/reasoning process.
     * Helps control cost and latency for complex tasks.
     *
     * @deprecated Use `thinking` instead. On Opus 4.6, this is treated as on/off
     * (0 = disabled, any other value = adaptive). For explicit control, use
     * `thinking: { type: 'adaptive' }` or `thinking: { type: 'enabled', budgetTokens: N }`.
     */
    maxThinkingTokens?: number;
    /**
     * Maximum number of conversation turns before the query stops.
     * A turn consists of a user message and assistant response.
     */
    maxTurns?: number;
    /**
     * Maximum budget in USD for the query. The query will stop if this
     * budget is exceeded, returning an `error_max_budget_usd` result.
     */
    maxBudgetUsd?: number;
    /**
     * API-side task budget in tokens. When set, the model is made aware of
     * its remaining token budget so it can pace tool use and wrap up before
     * the limit. Sent as `output_config.task_budget` with the
     * `task-budgets-2026-03-13` beta header.
     * @alpha
     */
    taskBudget?: {
        total: number;
    };
    /**
     * MCP (Model Context Protocol) server configurations.
     * Keys are server names, values are server configurations.
     *
     * Servers that Claude Code runs or connects to (stdio, SSE, HTTP) reach it on its command
     * line unless `mcpServersDelivery` is `'initialize'`; see that option's deprecation notice.
     *
     * @example
     * ```typescript
     * mcpServers: {
     *   'my-server': {
     *     command: 'node',
     *     args: ['./my-mcp-server.js']
     *   }
     * }
     * ```
     */
    mcpServers?: Record<string, McpServerConfig>;
    /**
     * How the `mcpServers` that Claude Code runs or connects to (stdio, SSE, HTTP) reach it.
     * In-process servers (`createSdkMcpServer`) are not affected.
     * - `'argv'` (default) - Sent in one `--mcp-config` flag: works with any Claude Code version,
     *   but puts server `env` and `headers` on the command line, which other users of the
     *   machine can read.
     * - `'initialize'` - Sent over stdin in the initialize request, so `env` and `headers` stay
     *   off the command line. The prompt waits for Claude Code's answer, and an error answer ends
     *   the session. Requires the Claude Code bundled with this SDK or newer: an older one started
     *   through `pathToClaudeCodeExecutable` or `spawnClaudeCodeProcess` exits at startup with an
     *   unknown-option error (before 2.1.261), or has its session ended by this SDK with an error
     *   naming this option. `initializationResult().mcp_servers_applied` is true when Claude Code
     *   took the servers at launch, which does not mean each connected.
     *
     * A launch given `--sdk-url` (through `extraArgs` or `executableArgs`) always uses
     * `--mcp-config`, because that session cannot read the request at launch.
     *
     * Deprecation notice: sending these servers on the command line is deprecated, and a future
     * release changes the default to `'initialize'`. An app that starts its own Claude Code through
     * `pathToClaudeCodeExecutable` or `spawnClaudeCodeProcess` should update it to at least the
     * bundled version and set `'initialize'`, or set `'argv'` to stay on the command line; while it
     * leaves this option unset, this SDK emits a `DeprecationWarning` once per process (code
     * `CLAUDE_SDK_MCP_SERVERS_ARGV_DEPRECATED`). Apps that use the bundled Claude Code need not
     * update it, get no warning, and can set `'initialize'` now.
     *
     * @default 'argv'
     */
    mcpServersDelivery?: 'argv' | 'initialize';
    /**
     * Claude model to use. Defaults to the CLI default model.
     * Examples: 'claude-sonnet-5', 'claude-opus-4-8', 'claude-fable-5'
     */
    model?: string;
    /**
     * Output format configuration for structured responses.
     * When specified, the agent will return structured data matching the schema.
     *
     * @example
     * ```typescript
     * outputFormat: {
     *   type: 'json_schema',
     *   schema: { type: 'object', properties: { result: { type: 'string' } } }
     * }
     * ```
     */
    outputFormat?: OutputFormat;
    /**
     * Path to the Claude Code executable. Uses the built-in executable if not specified.
     */
    pathToClaudeCodeExecutable?: string;
    /**
     * Permission mode for the session. When omitted, Claude Code picks the
     * starting mode as it does for `claude -p`: a `permissions.defaultMode`
     * from the settings the session loads, else `'auto'` where that is the
     * default (and `'default'` where auto mode is unavailable). Pass
     * `'default'` to keep manual approvals through `canUseTool` (on a cloud
     * create or attach, `'default'` leaves the session's own mode).
     * - `'default'` - Standard permission behavior, prompts for dangerous operations
     * - `'acceptEdits'` - Auto-accept file edit operations
     * - `'bypassPermissions'` - Bypass all permission checks (requires `allowDangerouslySkipPermissions`)
     * - `'plan'` - Planning mode, no execution of tools
     * - `'dontAsk'` - Don't prompt for permissions, deny if not pre-approved
     * - `'auto'` - A model classifier approves or denies each call, prompting through `canUseTool` when it cannot decide
     */
    permissionMode?: PermissionMode;
    /**
     * Custom workflow instructions for plan mode. When `permissionMode` is
     * `'plan'`, this string replaces the default code-implementation workflow
     * body in the plan-mode system reminder. The CLI still wraps it with the
     * read-only enforcement preamble and the ExitPlanMode protocol footer.
     */
    planModeInstructions?: string;
    /**
     * Must be set to `true` when using `permissionMode: 'bypassPermissions'`.
     * This is a safety measure to ensure intentional bypassing of permissions.
     */
    allowDangerouslySkipPermissions?: boolean;
    /**
     * MCP tool name to use for permission prompts. When set, permission requests
     * will be routed through this MCP tool instead of the default handler.
     */
    permissionPromptToolName?: string;
    /**
     * Who answers permission prompts. `'host'` (default): this process, through
     * `canUseTool` or `permissionPromptToolName`. `'none'`: nobody — the
     * permission mode (including auto mode's classifier), rules and hooks still
     * decide, and anything that would otherwise prompt is denied immediately
     * with a message telling Claude the session has no approval surface;
     * `canUseTool` is never called.
     */
    permissionPrompts?: 'host' | 'none';
    /**
     * Load plugins for this session. Plugins provide custom commands, agents,
     * skills, and hooks that extend Claude Code's capabilities.
     *
     * Currently only local plugins are supported via the 'local' type.
     *
     * @example
     * ```typescript
     * plugins: [
     *   { type: 'local', path: './my-plugin' },
     *   { type: 'local', path: '/absolute/path/to/plugin' }
     * ]
     * ```
     */
    plugins?: SdkPluginConfig[];
    /**
     * How `plugins` reach the Claude Code process.
     * - `'argv'` (default) - One `--plugin-dir <path>` flag per plugin. Works
     *   with any Claude Code version, but the command line grows with the
     *   plugin count and Windows refuses to start a process whose command line
     *   exceeds 32,767 characters.
     * - `'initialize'` - The list is sent over stdin in the initialize request
     *   and Claude Code is started with `--await-initialize`, so the command
     *   line does not depend on the plugin count. Loading is otherwise
     *   identical. Requires Claude Code 2.1.261 or newer (the binary bundled
     *   with this SDK qualifies); an older binary exits at startup with an
     *   unknown-option error. `initializationResult().plugins_applied` reports
     *   whether every listed plugin is loaded in the process.
     */
    pluginDelivery?: 'argv' | 'initialize';





    /**
     * Enable prompt suggestions. When true, the agent emits a `prompt_suggestion`
     * message after each turn with a predicted next user prompt.
     *
     * Delivery semantics:
     * - At most one `prompt_suggestion` per turn; arrives after the `result` message.
     * - Consumers must keep iterating the stream after `result` to receive it.
     * - Suppressed on the first turn, after API errors, in plan mode, by the
     *   `CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION=false` env var, and when the user
     *   has `promptSuggestionEnabled: false` in settings.json (the env var wins
     *   over the setting).
     * - Also suppressed while the account is near or at its plan usage limit.
     *   `CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION=true` keeps them on in the
     *   near-limit case; at the limit they stay off.
     * - Suggestions piggyback on the parent's prompt cache, making them nearly free.
     */
    promptSuggestions?: boolean;
    /**
     * Enable periodic AI-generated progress summaries for running subagents. When
     * true, the subagent's conversation is forked every ~30s to produce a short
     * present-tense description (e.g. "Analyzing authentication module"), emitted
     * on `task_progress` events via the `summary` field. The fork reuses the
     * subagent's model and prompt cache.
     *
     * Summaries are not a heartbeat. None is made while the conversation is
     * unchanged. A summary can also be delayed by up to 5 minutes while the
     * subagent is waiting for a model response and its prompt cache is likely cold
     * (no response yet, or none begun in the last 4.5 minutes). If the subagent
     * finishes first, that summary is not sent.
     *
     * Applies to both foreground and background subagents. Defaults to false.
     * The `CLAUDE_CODE_DISABLE_AGENT_PROGRESS_SUMMARIES=1` env var turns
     * summaries off even when this option is true.
     */
    agentProgressSummaries?: boolean;

    /**
     * Session ID to resume. Loads the conversation history from the specified session.
     */
    resume?: string;
    /**
     * Use a specific session ID for the conversation instead of an auto-generated one.
     * Must be a valid UUID. Cannot be used with `continue` or `resume` unless
     * `forkSession` is also set (to specify a custom ID for the forked session).
     */
    sessionId?: string;
    /**
     * When resuming, only resume messages up to and including the message with this UUID.
     * Use with `resume`. This allows you to resume from a specific point in the conversation.
     * Accepts any chain-entry UUID — typically `SDKAssistantMessage.uuid`, but
     * end-turn tool sessions and transcript-only appends need a later entry's
     * UUID (see `resumeDropsTurn` for the fork-point guidance).
     */
    resumeSessionAt?: string;
    /**
     * With `resumeSessionAt`: declares the prompt UUID of the turn this
     * truncating resume intends to discard. The CLI validates at fork time
     * that every entry past the `resumeSessionAt` point is attributable to
     * that turn, and refuses the resume (an `error_during_execution` result
     * whose message starts with `Resume rejected by --resume-drops-turn:`)
     * when the discarded range contains anything else — e.g. a queued user
     * message or task notification the session absorbed mid-turn that the
     * caller's view of the conversation had not yet observed. Omit to keep
     * the unvalidated truncation behavior.
     *
     * Consumers MUST map a refusal (match on the message prefix above) to
     * their rewind-recovery path — clear the pending fork target and resume
     * plainly, keeping the evidence — not retry: the refusal is
     * deterministic, so re-sending the same fork request fails forever.
     *
     * End-turn tool sessions (`outputFormat: {type: 'json_schema'}`, or any
     * MCP tool using `_meta['claude/endTurn']`): a completed turn there ends
     * on a successful tool_result carrier — with no trailing assistant
     * message — followed by a `structured_output` attachment holding the
     * turn's actual output (the carrier's data is a placeholder). Fork at
     * the LAST entry of the turn being kept — the `structured_output`
     * attachment when present, else the carrier — not the last assistant
     * UUID; `resumeSessionAt` accepts any chain UUID. Forking earlier
     * leaves the carrier or attachment in the discarded range, and the
     * validator deliberately refuses: both are the kept turn's own payload,
     * and dropping either would discard kept-turn output (the attachment is
     * its sole persisted copy) or leave its tool_use dangling.
     *
     * The same fork-past-your-appends rule applies to plain (non-synthetic)
     * `shouldQuery: false` transcript appends (e.g. CCD bash mode): they
     * persist as bare user entries, so a fork point that leaves one in the
     * discarded range refuses. Fork at or after your own last append.
     *
     * PRINT/HEADLESS LANE ONLY: the pair is consumed exclusively by the
     * headless boot path (print-mode CLI, Agent SDK, ProcessTransport). An
     * interactive `claude --resume` boot and background-job worker boots
     * ignore both options — the resume loads the full chain with no
     * truncation, no guard, and no error — so callers must not pass the
     * pair outside print mode and expect an armed guard (rejecting it on
     * those lanes is tracked follow-up work).
     *
     * General rule subsuming all of the above: fork at the KEPT turn's last
     * chain entry, whatever it is — `resumeSessionAt` accepts any chain
     * UUID. This also covers interrupted turns that completed one or more
     * tools before Esc: the completed (non-error) tool_result in the tail
     * is kept-turn payload and deliberately refuses at an assistant-UUID
     * fork point, while the marker / cancel-batch entries after it are
     * skippable — so fork at the last entry and the refusal never fires.
     */
    resumeDropsTurn?: string;
    /**
     * Sandbox settings for command execution isolation.
     *
     * When enabled, commands are executed in a sandboxed environment that restricts
     * filesystem and network access. This provides an additional security layer.
     *
     * Access restrictions can be set here (`filesystem`, `network`, `credentials`);
     * filesystem and network restrictions also come from `Read`, `Edit` and
     * `WebFetch` permission rules, and Claude Code applies both.
     *
     * **Dependency check:** When this option sets `enabled: true`,
     * `failIfUnavailable` defaults to `true` unless this option or an inline
     * `settings` sandbox block sets it: if sandbox dependencies are missing (e.g.
     * `bubblewrap` on Linux) or the platform is unsupported, `query()` emits an
     * error result and exits rather than silently running commands unsandboxed.
     * Set `failIfUnavailable: false` to allow graceful degradation.
     *
     * **Invalid settings:** one value that fails validation rejects all of
     * `settings`, this option included. With `enabled: true`, `query()` then emits
     * the same error result and exits, unless `failIfUnavailable` is `false`.
     *
     * **With `settings`:** when `settings` is given inline (an object or JSON string,
     * not a file path) and has its own `sandbox` block, this option is merged into
     * it. A value this option sets replaces the value at the same path, and a
     * value it does not set is kept, with two exceptions: a
     * `filesystem.disabled: true` is dropped when this option sets `filesystem` or
     * a `credentials.files` deny entry, since it would switch those off; and a
     * `network.httpProxyPort` or `network.socksProxyPort` is dropped when this
     * option sets `network.allowedDomains`, a `network.deniedDomains` entry or
     * `network.strictAllowlist: true` and does not set that port itself, since
     * traffic through your own proxy is not checked against those lists. Nested
     * objects merge key by key, except `ripgrep` and
     * `network.tlsTerminate`, which this option replaces whole; and the restriction
     * lists (`filesystem.denyRead`, `filesystem.denyWrite`, `network.deniedDomains`,
     * `credentials.files`, `credentials.envVars`) from both are combined instead, a
     * `deny` from either side winning over a `mask` for the same credential path or
     * variable. A `settings` file path cannot be combined with this option.
     *
     * @example Enable sandboxing with auto-allow
     * ```typescript
     * sandbox: {
     *   enabled: true,
     *   autoAllowBashIfSandboxed: true
     * }
     * ```
     *
     * @example Configure network options
     * ```typescript
     * sandbox: {
     *   enabled: true,
     *   network: {
     *     allowLocalBinding: true,
     *     allowUnixSockets: ['/var/run/docker.sock']
     *   }
     * }
     * ```
     *
     * @see https://code.claude.com/docs/en/settings#sandbox-settings
     */
    sandbox?: SandboxSettings;
    /**
     * Additional settings to apply. Accepts either a path to a settings JSON file
     * or a settings object. These are loaded into the "flag settings" layer,
     * which has the highest priority among user-controlled settings.
     *
     * Equivalent to the `--settings` CLI flag.
     *
     * @example Inline settings object
     * ```typescript
     * settings: { model: 'claude-sonnet-5', permissions: { allow: ['Bash(*)'] } }
     * ```
     *
     * @example Path to settings file
     * ```typescript
     * settings: '/path/to/settings.json'
     * ```
     */
    settings?: string | Settings;
    /**
     * Policy-tier settings supplied by the spawning parent process. When an
     * IT-controlled managed-settings tier (server / MDM / managed-settings.json)
     * exists on the user's machine, these are **dropped by default** — they only
     * layer in if that admin opts in via `parentSettingsBehavior: 'merge'` in
     * their managed settings (a gateway-mode session that Claude Desktop's Code
     * tab launches merges them by default; `'first-wins'` in the highest-priority
     * managed source turns that off). Even when opted in, the value is filtered
     * restrictive-only: permissive arrays (`permissions.allow`,
     * `additionalDirectories`, …) that would widen an existing admin lock are
     * silently dropped; the only-listed-allowed lists (`allowedMcpServers`,
     * `availableModels`, `strictKnownMarketplaces`) apply only where the admin
     * tier sets none, while denylists (`deniedMcpServers`,
     * `blockedMarketplaces`) are kept and union with the admin's. With no admin
     * tier present, these apply as the sole policy tier (still filtered
     * restrictive-only — non-allowlisted keys are dropped regardless).
     *
     * Two hook keys are filtered by value rather than kept as written:
     * `disableAllHooks: true` binds as `allowManagedHooksOnly: true`, so the
     * machine administrator's own hooks keep running where the embedder's tier
     * cannot stop them — and because an enterprise configuration often yields
     * a boolean as text, any value but `false` and `"false"` binds it the same
     * way — and `allowedHttpHookUrls` / `httpHookAllowedEnvVars`
     * bind only as the empty list (admit nothing) — a non-empty one is dropped,
     * because these lists union across settings sources and would widen an
     * admin's. For the same reason an empty list binds only where no other
     * source sets one; pair it with `allowManagedHooksOnly` to stop a project's
     * HTTP hooks outright.
     *
     * Intended for embedding applications (e.g. desktop apps) that derive
     * lockdown settings from their own enterprise configuration and need to
     * enforce them on the spawned subprocess without writing root-owned files.
     *
     * @example
     * ```typescript
     * managedSettings: {
     *   sandbox: { network: { allowManagedDomainsOnly: true } }
     * }
     * ```
     */
    managedSettings?: Settings;



    /**
     * Control which filesystem settings to load.
     * - `'user'` - Global user settings (`~/.claude/settings.json`)
     * - `'project'` - Project settings (`.claude/settings.json`)
     * - `'local'` - Local settings (`.claude/settings.local.json`)
     *
     * When omitted, all sources are loaded (matches CLI defaults).
     * Pass `[]` to disable filesystem settings (SDK isolation mode).
     * Must include `'project'` to load CLAUDE.md files.
     */
    settingSources?: SettingSource[];
    /**
     * Skills to enable for the main session. This is the single place to turn
     * skills on; you do not need to add `'Skill'` to `allowedTools` yourself
     * when using this option.
     *
     * - omitted (default): no SDK auto-configuration. The CLI's own defaults
     *   still apply, so this is **not** "skills off."
     * - `'all'`: enable every discovered skill.
     * - `string[]`: enable only the listed skills. Names match the SKILL.md
     *   `name` / directory name, or `plugin:skill` for plugin-qualified skills.
     *
     * This is a context filter, not a sandbox: unlisted skills are hidden from
     * the model's listing and rejected by the Skill tool, but their files
     * remain on disk and are reachable via Read/Bash. Do not store secrets in
     * skill files.
     *
     * @example
     * ```typescript
     * skills: 'all'
     * skills: ['pdf', 'docx']
     * ```
     */
    skills?: string[] | 'all';
    /**
     * Enable debug mode for the Claude Code process.
     * When true, enables verbose debug logging (equivalent to `--debug` CLI flag).
     * Debug logs are written to a file (see `debugFile` option) or to stderr.
     *
     * You can also capture debug output via the `stderr` callback.
     */
    debug?: boolean;
    /**
     * Write debug logs to a specific file path.
     * Implicitly enables debug mode. Equivalent to `--debug-file <path>` CLI flag.
     */
    debugFile?: string;
    /**
     * Callback for stderr output from the Claude Code process.
     * Useful for debugging and logging.
     */
    stderr?: (data: string) => void;
    /**
     * Only use MCP servers passed via the `mcpServers` option (and servers
     * declared by explicitly-passed agent definitions in `agents`), ignoring
     * all other MCP configurations: project `.mcp.json`, user settings,
     * plugins, and on-disk agent frontmatter — including subagent frontmatter
     * MCP. Maps to the CLI `--strict-mcp-config` flag.
     */
    strictMcpConfig?: boolean;
    /**
     * System prompt configuration.
     * - `string` - Use a custom system prompt
     * - `string[]` - Use a custom system prompt as an array of blocks; include
     *   `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` as a standalone element to mark the
     *   split between the static (globally-cacheable) prefix and the dynamic
     *   (session-specific) suffix. Blocks before the marker are eligible for
     *   cross-session prompt caching; blocks after it are not.
     * - `{ type: 'preset', preset: 'claude_code' }` - Use Claude Code's default system prompt
     * - `{ type: 'preset', preset: 'claude_code', append: '...' }` - Use default prompt with appended instructions
     * - `{ type: 'preset', preset: 'claude_code', excludeDynamicSections: true }` -
     *   Strip per-user dynamic sections (working directory, auto-memory, git
     *   status) from the system prompt so it stays static and cacheable across
     *   users. The stripped content is re-injected as the first user message so
     *   the model still has access to it.
     *
     *   Use this when many users in your fleet share the same system prompt and
     *   you want the prompt-caching prefix to hit cross-user. Tradeoffs:
     *   - The working-directory, memory-path, and git-status context is
     *     marginally less authoritative for steering the model (it appears in
     *     a user message instead of the system prompt).
     *   - The first user message becomes slightly larger.
     *   - Has no effect when `systemPrompt` is a string (custom prompt).
     *
     * @example Custom prompt
     * ```typescript
     * systemPrompt: 'You are a helpful coding assistant.'
     * ```
     *
     * @example Custom prompt with cache boundary
     * ```typescript
     * import { SYSTEM_PROMPT_DYNAMIC_BOUNDARY } from '@anthropic-ai/claude-agent-sdk'
     * systemPrompt: [
     *   staticInstructions,
     *   SYSTEM_PROMPT_DYNAMIC_BOUNDARY,
     *   sessionContext,
     * ]
     * ```
     *
     * @example Default with additions
     * ```typescript
     * systemPrompt: {
     *   type: 'preset',
     *   preset: 'claude_code',
     *   append: 'Always explain your reasoning.'
     * }
     * ```
     *
     * @example Cacheable prompt for multi-user fleets
     * ```typescript
     * systemPrompt: {
     *   type: 'preset',
     *   preset: 'claude_code',
     *   excludeDynamicSections: true,
     * }
     * ```
     *
     * `snapshot` — whether the conversation's system prompt is recorded once (in
     * the session transcript) and reused verbatim on every later request and
     * `resume` / `continue`, instead of being rendered fresh each time.
     * **Recommended: `snapshot: true`.** A system prompt that changes
     * mid-conversation (a CLI upgrade between launches, a flag flip, a different
     * `append`) invalidates the prompt prefix and, with extended thinking,
     * discards the model's earlier reasoning; a recorded prompt cannot change
     * until the conversation is compacted. (It also keeps the API prompt-cache
     * prefix stable.)
     *
     * How it interacts with `append` (and a custom `prompt`):
     * - **Omitted or `snapshot: true` (the default):** Claude Code renders its
     *   prompt with your `append` (or your custom `prompt`) on the
     *   conversation's first request, sends that, and records it; every later
     *   request and `resume` / `continue` sends the record as-is — a different
     *   `append` or `prompt` passed on a later launch of the same session is
     *   ignored until compaction or a new session.
     * - **`snapshot: false`:** never record; render fresh every request — for
     *   iterating on prompt text, or a host that must change its append within
     *   a session.
     * A bare string / `string[]` prompt follows the default; use
     * `{ type: 'custom', prompt, snapshot: false }` to opt it out.
     * With a recorded prompt, a mid-session model switch or `set_settings`
     * agent/system-prompt change does not change the prompt either; it takes
     * effect at the next compaction or in a new session. System-prompt
     * recording is rolling out: where it is not yet enabled for the account
     * (and on Bedrock / Vertex / Foundry today) `snapshot` is accepted and has no
     * effect, so it is safe to set now.
     *
     * @example Recommended: preset with an append, recorded for the conversation
     * ```typescript
     * systemPrompt: {
     *   type: 'preset',
     *   preset: 'claude_code',
     *   append: 'Always explain your reasoning.',
     *   snapshot: true,
     * }
     * ```
     *
     * @example Custom prompt, recorded for the conversation
     * ```typescript
     * systemPrompt: { type: 'custom', prompt: 'You are a release bot.', snapshot: true }
     * ```
     */
    systemPrompt?: string | string[] | {
        type: 'custom';
        prompt: string | string[];
        snapshot?: boolean;
    } | {
        type: 'preset';
        preset: 'claude_code';
        append?: string;
        excludeDynamicSections?: boolean;
        snapshot?: boolean;
    };
    /**
     * Custom title for a new session. When provided, the session uses this title
     * instead of auto-generating one from the first user message.
     *
     * When resuming via `resume` or `continue`, the resumed session's persisted
     * title takes precedence — use `renameSession()` to retitle an existing
     * session.
     */
    title?: string;


    /**
     * Custom function to spawn the Claude Code process.
     * Use this to run Claude Code in VMs, containers, or remote environments.
     *
     * When provided, this function is called instead of the default local spawn.
     * The default behavior checks if the executable exists before spawning.
     *
     * @example
     * ```typescript
     * spawnClaudeCodeProcess: (options) => {
     *   // Custom spawn logic for VM execution
     *   // options contains: command, args, cwd, env, signal
     *   // `signal` is forwarded — it aborts only AFTER the SDK's
     *   // stdin-EOF + ~2 s grace window, so passing it to spawn()/your
     *   // VM API is safe (force-kill fires after the graceful chance).
     *   return myVMProcess; // Must satisfy SpawnedProcess interface
     * }
     * ```
     */
    spawnClaudeCodeProcess?: (options: SpawnOptions) => SpawnedProcess;
};

/**
 * Emitted on the same severity:'error' path as the usage-limit bucket, but
 * the condition is an org policy, not an exhausted limit — consumers route
 * these to org-disabled presentation, never the usage-limit card.
 *
 * @alpha
 */
export declare const ORG_POLICY_LIMIT_PREFIXES: readonly ['This service is disabled for your org'];

export declare type OutputFormat = JsonSchemaOutputFormat;

export declare type OutputFormatType = 'json_schema';

export declare type PermissionBehavior = 'allow' | 'deny' | 'ask';

/**
 * Classification of this permission decision for telemetry. SDK hosts that prompt users (desktop apps, IDEs) should set this to reflect what actually happened: user_temporary for allow-once, user_permanent for always-allow (both the click and later cache hits), user_reject for deny. If unset, the CLI infers conservatively (temporary for allow, reject for deny). The vocabulary matches tool_decision OTel events (monitoring-usage docs).
 */
export declare type PermissionDecisionClassification = 'user_temporary' | 'user_permanent' | 'user_reject';

export declare type PermissionDeniedHookInput = BaseHookInput & {
    hook_event_name: 'PermissionDenied';
    tool_name: string;
    tool_input: unknown;
    tool_use_id: string;
    reason: string;
    mcp_server?: McpServerProvenance;
};

export declare type PermissionDeniedHookSpecificOutput = {
    hookEventName: 'PermissionDenied';
    retry?: boolean;
};

/**
 * Permission mode for controlling how tool executions are handled. 'default' - Standard behavior, prompts for dangerous operations. 'acceptEdits' - Auto-accept file edit operations. 'bypassPermissions' - Bypass all permission checks (requires allowDangerouslySkipPermissions). 'plan' - Planning mode, no actual tool execution. 'dontAsk' - Don't prompt for permissions, deny if not pre-approved. 'auto' - Use a model classifier to approve/deny permission prompts.
 */
export declare type PermissionMode = 'default' | 'acceptEdits' | 'bypassPermissions' | 'plan' | 'dontAsk' | 'auto';

export declare type PermissionRequestHookInput = BaseHookInput & {
    hook_event_name: 'PermissionRequest';
    tool_name: string;
    tool_input: unknown;
    permission_suggestions?: PermissionUpdate[];
    mcp_server?: McpServerProvenance;


};

export declare type PermissionRequestHookSpecificOutput = {
    hookEventName: 'PermissionRequest';
    decision: {
        behavior: 'allow';
        updatedInput?: Record<string, unknown>;
        updatedPermissions?: PermissionUpdate[];
    } | {
        behavior: 'deny';
        message?: string;
        interrupt?: boolean;
    };
};

export declare type PermissionResult = {
    behavior: 'allow';
    updatedInput?: Record<string, unknown>;
    updatedPermissions?: PermissionUpdate[];
    toolUseID?: string;
    decisionClassification?: PermissionDecisionClassification;
} | {
    behavior: 'deny';
    message: string;
    interrupt?: boolean;
    toolUseID?: string;
    decisionClassification?: PermissionDecisionClassification;
};

export declare type PermissionRuleValue = {
    toolName: string;
    ruleContent?: string;
};

export declare type PermissionUpdate = {
    type: 'addRules';
    rules: PermissionRuleValue[];
    behavior: PermissionBehavior;
    destination: PermissionUpdateDestination;
} | {
    type: 'replaceRules';
    rules: PermissionRuleValue[];
    behavior: PermissionBehavior;
    destination: PermissionUpdateDestination;
} | {
    type: 'removeRules';
    rules: PermissionRuleValue[];
    behavior: PermissionBehavior;
    destination: PermissionUpdateDestination;
} | {
    type: 'setMode';
    mode: PermissionMode;
    destination: PermissionUpdateDestination;
} | {
    type: 'addDirectories';
    directories: string[];
    destination: PermissionUpdateDestination;
} | {
    type: 'removeDirectories';
    directories: string[];
    destination: PermissionUpdateDestination;
};

export declare type PermissionUpdateDestination = 'userSettings' | 'projectSettings' | 'localSettings' | 'session' | 'cliArg';

/**
 * Which policy sub-source supplied a `'managed'` value.
 * @alpha
 */
export declare type PolicySettingsOrigin = 'helper' | 'remote' | 'plist' | 'hklm' | 'file' | 'parent' | 'hkcu';

export declare type PostCompactHookInput = BaseHookInput & {
    hook_event_name: 'PostCompact';
    trigger: 'manual' | 'auto';
    /**
     * The conversation summary produced by compaction
     */
    compact_summary: string;
};

export declare type PostModelSwitchHookInput = (BaseHookInput & {
    hook_event_name: 'PostModelSwitch';
}) & {
    /**
     * Resolved model id the session was running before the switch
     */
    from_model: string;
    /**
     * Resolved model id the session runs after the switch
     */
    to_model: string;
    /**
     * What was asked for (alias such as "opus", a full id, or null for "default")
     */
    requested_model: string | null;
    /**
     * command: /model <name>, the /config Model row, or enabling fast mode when that promotes the model; picker: an interactive model picker; sdk: headless set_model (SDK, Remote Control, IDE); auto: automatic fallback or other programmatic change; resume: model restored while resuming a session
     */
    source: 'command' | 'picker' | 'sdk' | 'auto' | 'resume';
    /**
     * Prompt tokens the next request re-sends: the last main-thread response's input + cache_read + cache_creation + output tokens (0 before the first response; for a server-side tool loop, its last iteration's window, not the summed totals)
     */
    context_tokens: number;
    /**
     * Whether the current model's prompt cache is likely still warm (a switch then forfeits it)
     */
    prompt_cache_warm: boolean;
    cache_ttl: '5m' | '1h';
    /**
     * Estimated cost of re-caching context_tokens on to_model at its cache-write rate — the managed modelPricing when set, otherwise list price; excludes the response
     */
    estimated_cache_write_usd: number;
    /**
     * configured: priced at the managed modelPricing setting; catalog: list price; default: to_model unknown, the default tier was assumed
     */
    pricing: 'configured' | 'catalog' | 'default';
};

export declare type PostModelSwitchHookSpecificOutput = {
    hookEventName: 'PostModelSwitch';
    /**
     * Reaches the model with the next request the new model serves
     */
    additionalContext?: string;
};

/**
 * Hook input for the PostToolBatch event. Fired once after every tool call in a batch has resolved, before the next model request. PostToolUse fires per-tool and may run concurrently for parallel tool calls; PostToolBatch fires exactly once with the full batch.
 */
export declare type PostToolBatchHookInput = BaseHookInput & {
    hook_event_name: 'PostToolBatch';
    tool_calls: PostToolBatchToolCall[];
};

export declare type PostToolBatchHookSpecificOutput = {
    hookEventName: 'PostToolBatch';
    additionalContext?: string;
};

export declare type PostToolBatchToolCall = {
    tool_name: string;
    tool_input: unknown;
    tool_use_id: string;
    tool_response?: unknown;
};

export declare type PostToolUseFailureHookInput = BaseHookInput & {
    hook_event_name: 'PostToolUseFailure';
    tool_name: string;
    tool_input: unknown;
    tool_use_id: string;
    error: string;
    is_interrupt?: boolean;
    /**
     * Tool execution time in milliseconds. Excludes permission-prompt and hook time.
     */
    duration_ms?: number;
    mcp_server?: McpServerProvenance;
};

export declare type PostToolUseFailureHookSpecificOutput = {
    hookEventName: 'PostToolUseFailure';
    additionalContext?: string;
};

export declare type PostToolUseHookInput = BaseHookInput & {
    hook_event_name: 'PostToolUse';
    tool_name: string;
    tool_input: unknown;
    tool_response: unknown;
    tool_use_id: string;
    /**
     * Tool execution time in milliseconds. Excludes permission-prompt and hook time.
     */
    duration_ms?: number;
    mcp_server?: McpServerProvenance;
};

export declare type PostToolUseHookSpecificOutput = {
    hookEventName: 'PostToolUse';
    additionalContext?: string;
    /**
     * Host-asserted context shown to the auto-mode permission classifier alongside this tool call's result. In the live session the classifier may weigh a user statement relayed here as user intent (it can satisfy a consent bar a user turn would satisfy, never a hard boundary); values restored from saved session state are treated as unverified context only. Relay discipline is the host's obligation: put ONLY genuine user statements in intent-bearing positions — never tool output or model text dressed as one. Capped at 2000 UTF-16 code units, a budget shared across all hooks that contribute to one call (surrogate-pair-safe; emoji and other astral characters count as two). Honored on synchronous hook responses only: an async hook's late response arrives after the result message is frozen and this field in it is silently ignored. Security note: do not copy untrusted tool output or third-party text into it blindly — content placed here reaches the permission classifier with host-application framing. Applies only to calls the classifier transcript shows: read-only lookups the transcript omits (file reads, searches) and remote-engine shells produce no per-result line, and context attached to them is silently unused. Not a delivery channel: it is bound to a single call id and sized for a short assertion, not for relaying messages or events. Rewrite integrity: if this assertion describes output you are rewriting, return it in the SAME hook result as the rewrite — it is then dropped automatically if your rewrite is rejected or superseded by a later hook's rewrite; assertions returned without a rewrite are never invalidated by other hooks' rewrites, so a non-rewriting hook should assert only what holds regardless of other hooks' rewrites — hosts that need an assertion bound to exact output bytes should make it in the hook that produces those bytes. (Do NOT return an identity rewrite just to pair an assertion: hooks run in parallel on the ORIGINAL output, so an identity rewrite competes last-write-wins with sibling rewrites and can clobber a real redaction.)
     */
    classifierContext?: string;
    /**
     * Replaces the tool output before it is sent to the model
     */
    updatedToolOutput?: unknown;
    /**
     * Replaces the output for MCP tools only. Prefer updatedToolOutput, which works for all tools
     */
    updatedMCPToolOutput?: unknown;
};

export declare type PreCompactHookInput = BaseHookInput & {
    hook_event_name: 'PreCompact';
    trigger: 'manual' | 'auto';
    custom_instructions: string | null;
};

export declare type PreModelSwitchHookInput = (BaseHookInput & {
    hook_event_name: 'PreModelSwitch';
}) & {
    /**
     * Resolved model id the session was running before the switch
     */
    from_model: string;
    /**
     * Resolved model id the session runs after the switch
     */
    to_model: string;
    /**
     * What was asked for (alias such as "opus", a full id, or null for "default")
     */
    requested_model: string | null;
    /**
     * command: /model <name>, the /config Model row, or enabling fast mode when that promotes the model; picker: an interactive model picker; sdk: headless set_model (SDK, Remote Control, IDE)
     */
    source: 'command' | 'picker' | 'sdk';
    /**
     * Prompt tokens the next request re-sends: the last main-thread response's input + cache_read + cache_creation + output tokens (0 before the first response; for a server-side tool loop, its last iteration's window, not the summed totals)
     */
    context_tokens: number;
    /**
     * Whether the current model's prompt cache is likely still warm (a switch then forfeits it)
     */
    prompt_cache_warm: boolean;
    cache_ttl: '5m' | '1h';
    /**
     * Estimated cost of re-caching context_tokens on to_model at its cache-write rate — the managed modelPricing when set, otherwise list price; excludes the response
     */
    estimated_cache_write_usd: number;
    /**
     * configured: priced at the managed modelPricing setting; catalog: list price; default: to_model unknown, the default tier was assumed
     */
    pricing: 'configured' | 'catalog' | 'default';
};

export declare type PreModelSwitchHookSpecificOutput = {
    hookEventName: 'PreModelSwitch';
    /**
     * Same contract as PreToolUse: allow proceeds (skipping the interactive cache-miss confirm), deny cancels the switch, ask asks the user to confirm (a headless session refuses instead)
     */
    permissionDecision?: 'allow' | 'deny' | 'ask';
    permissionDecisionReason?: string;
};

export declare type PreToolUseHookInput = BaseHookInput & {
    hook_event_name: 'PreToolUse';
    tool_name: string;
    tool_input: unknown;
    tool_use_id: string;
    mcp_server?: McpServerProvenance;
};

export declare type PreToolUseHookSpecificOutput = {
    hookEventName: 'PreToolUse';
    permissionDecision?: HookPermissionDecision;
    permissionDecisionReason?: string;
    updatedInput?: Record<string, unknown>;
    additionalContext?: string;

};

/**
 * Start a Claude Code process as a parked **spare** before the session it
 * will serve is known, and bind it later with {@link SpareProcess.claim}.
 *
 * What runs now, at `prewarm()`: process start, module load, config, auth,
 * tools, user-level skills/plugins/commands, the host-level MCP servers in
 * `options.mcpServers` (including in-process SDK servers and their
 * handshakes), hooks and `canUseTool` registration, the initialize handshake —
 * everything `startup()` does, in a private parking directory under the
 * user's config home (or `options.cwd` if given, which is never the
 * session's folder). A host whose `spawnClaudeCodeProcess` runs Claude Code on
 * another machine or in a container must pass `options.cwd`: a directory that
 * exists there (the default one is created on this machine). What waits
 * for the claim: the working directory, SessionStart hooks, session
 * registration, CLAUDE.md and git context, the transcript location. While
 * parked the process holds roughly 230–260 MB and is otherwise idle.
 *
 * What a claim can set ({@link ClaimOptions}): `cwd`, `additionalDirectories`,
 * `model`, `permissionMode`, `maxThinkingTokens`, a flag-settings overlay
 * (`settings`, e.g. effort, permission rules or which of the folder's MCP
 * servers may start — but not hook settings; those go in `Options.settings`
 * here), `appendSystemPrompt`, `title`, `agents`, and
 * three environment variables (`CLAUDE_CODE_OAUTH_TOKEN`,
 * `CLAUDE_CODE_SESSION_ACCESS_TOKEN`, `CLAUDE_CODE_HOST_SESSION_ID`). Everything
 * else — the executable, `settingSources`, `env` the process reads at
 * start-up, `systemPrompt` presets, `mcpServers`, `hooks`, `canUseTool`,
 * `skills`, `allowedTools`/`disallowedTools`, a main-thread `agent`, plugins —
 * is fixed at `prewarm()`: keep one spare per distinct set of those, and when
 * they change (sign-out, settings that alter them, an updated executable)
 * `close()` the spare and prewarm again.
 *
 * Not every claim can be honoured: the process refuses a folder whose project
 * or local settings set `env`, `agent`, `model`, `fallbackModel` (or
 * `permissions.defaultMode` when no `permissionMode` was given at prewarm or
 * claim), a `permissionMode` it cannot take
 * (it travels inside the claim so this fails closed), a `settings` overlay it
 * cannot apply (the prompt is held until the overlay is accepted, so this
 * fails closed too), an environment key outside the three above, a network
 * path, or a missing folder; a parked process can also die. Without
 * `projectConfigRoot` it also refuses every claim when the project or local
 * settings of `options.cwd` set `env`, `model`, `fallbackModel` or (with no
 * `permissionMode` at prewarm or claim) `permissions.defaultMode`. And it
 * refuses every folder other than `options.cwd` when those settings or a
 * `.claude/agents` folder (in `options.cwd`, above it up to its repository
 * root or to the home folder outside one, or in `additionalDirectories`)
 * supplied the main-thread agent: pass `projectConfigRoot`, or park spares
 * where none of that applies. In all of those
 * {@link SpareProcess.claimed} rejects, the process goes away on its own
 * (`close()` only releases its in-process MCP servers and callbacks sooner),
 * and this version leaves the fallback to the host: start that session with
 * `query()` as before. One rejection is different: `option_not_applied`
 * means only `model` or `maxThinkingTokens` was refused — the prompt was
 * sent and the session is running, so do not start it again. A CLI too old
 * to know `--await-claim` makes `prewarm()` itself reject.
 *
 * Compared with `startup()`: `startup()` needs the session's folder and
 * options up front and saves only the spawn; `prewarm()` needs neither and
 * also keeps tools, plugins and MCP handshakes off the first message.
 *
 * After a claim the Query's `initializationResult()`, `supportedAgents()`,
 * `supportedCommands()` and `accountInfo()` describe the claimed session,
 * not the parking directory ({@link SpareProcess.claim} names the one limit:
 * the snapshot predates `model`/`settings`).
 *
 * @example
 * ```typescript
 * const spare = await prewarm({ options: hostLevelOptions })
 * // …later, when the user starts a session in `folder`:
 * const q = spare.claim({ prompt, options: { cwd: folder, model } })
 * spare.claimed.catch((e: Error) => {
 *   // refused, died or overlay refused: fall back to query(); on
 *   // option_not_applied the session is already running without that option
 *   if (!e.message.startsWith('option_not_applied')) startNormally()
 * })
 * for await (const message of q) { … }
 * ```
 * @alpha
 */
export declare function prewarm(_params?: {
    options?: Options;
    /**
     * The most time, in milliseconds, to wait for the spare process to
     * initialize; it counts throughout. Defaults to 60000.
     */
    initializeTimeoutMs?: number;
}): Promise<SpareProcess>;

/**
 * Per-key provenance entry.
 * @alpha
 */
export declare type ProvenanceEntry = {
    source: ResolvedSettingSource;
    /** Absolute path to the settings file, for filesystem-backed sources. */
    path?: string;
    /** Which policy sub-source supplied the value, when `source === 'managed'`. */
    policyOrigin?: PolicySettingsOrigin;
};

declare const PublishedSandboxSettingsSchema: () => z.ZodObject<{
    enabled: z.ZodOptional<z.ZodBoolean>;
    failIfUnavailable: z.ZodOptional<z.ZodBoolean>;
    autoAllowBashIfSandboxed: z.ZodOptional<z.ZodBoolean>;
    allowUnsandboxedCommands: z.ZodOptional<z.ZodBoolean>;
    network: z.ZodOptional<z.ZodObject<{
        allowedDomains: z.ZodOptional<z.ZodArray<z.ZodString>>;
        deniedDomains: z.ZodOptional<z.ZodArray<z.ZodString>>;
        strictAllowlist: z.ZodOptional<z.ZodBoolean>;
        allowManagedDomainsOnly: z.ZodOptional<z.ZodBoolean>;
        allowUnixSockets: z.ZodOptional<z.ZodArray<z.ZodString>>;
        allowAllUnixSockets: z.ZodOptional<z.ZodBoolean>;
        allowLocalBinding: z.ZodOptional<z.ZodBoolean>;
        allowMachLookup: z.ZodOptional<z.ZodArray<z.ZodString>>;
        httpProxyPort: z.ZodOptional<z.ZodNumber>;
        socksProxyPort: z.ZodOptional<z.ZodNumber>;
        tlsTerminate: z.ZodOptional<z.ZodObject<{
            caCertPath: z.ZodOptional<z.ZodString>;
            caKeyPath: z.ZodOptional<z.ZodString>;
        }, z.core.$strip>>;
    }, z.core.$strip>>;
    filesystem: z.ZodOptional<z.ZodObject<{
        allowWrite: z.ZodOptional<z.ZodArray<z.ZodString>>;
        denyWrite: z.ZodOptional<z.ZodArray<z.ZodString>>;
        denyRead: z.ZodOptional<z.ZodArray<z.ZodString>>;
        allowRead: z.ZodOptional<z.ZodArray<z.ZodString>>;
        allowManagedReadPathsOnly: z.ZodOptional<z.ZodBoolean>;
        disabled: z.ZodOptional<z.ZodBoolean>;
    }, z.core.$strip>>;
    credentials: z.ZodOptional<z.ZodObject<{
        files: z.ZodOptional<z.ZodArray<z.ZodPreprocess<z.ZodObject<{
            path: z.ZodString;
            mode: z.ZodEnum<{
                deny: "deny";
                mask: "mask";
            }>;
            extract: z.ZodOptional<z.ZodString>;
            onExtractNoMatch: z.ZodOptional<z.ZodEnum<{
                deny: "deny";
                error: "error";
                warn: "warn";
            }>>;
            decode: z.ZodOptional<z.ZodEnum<{
                jwt: "jwt";
            }>>;
            maskClaims: z.ZodOptional<z.ZodArray<z.ZodString>>;
            maskDuplicates: z.ZodOptional<z.ZodBoolean>;
            injectHosts: z.ZodOptional<z.ZodArray<z.ZodString>>;
        }, z.core.$strip>, unknown>>>;
        envVars: z.ZodOptional<z.ZodArray<z.ZodPreprocess<z.ZodObject<{
            name: z.ZodString;
            mode: z.ZodEnum<{
                deny: "deny";
                mask: "mask";
            }>;
            extract: z.ZodOptional<z.ZodString>;
            onExtractNoMatch: z.ZodOptional<z.ZodEnum<{
                deny: "deny";
                error: "error";
                warn: "warn";
            }>>;
            decode: z.ZodOptional<z.ZodEnum<{
                jwt: "jwt";
            }>>;
            maskClaims: z.ZodOptional<z.ZodArray<z.ZodString>>;
            injectHosts: z.ZodOptional<z.ZodArray<z.ZodString>>;
        }, z.core.$strip>, unknown>>>;
        allowPlaintextInject: z.ZodOptional<z.ZodBoolean>;
        awsPairs: z.ZodOptional<z.ZodArray<z.ZodObject<{
            accessKeyIdVar: z.ZodString;
            secretAccessKeyVar: z.ZodString;
            sessionTokenVar: z.ZodOptional<z.ZodString>;
        }, z.core.$strip>>>;
        sigv4: z.ZodOptional<z.ZodObject<{
            streaming: z.ZodOptional<z.ZodEnum<{
                deny: "deny";
                passthrough: "passthrough";
            }>>;
            presigned: z.ZodOptional<z.ZodEnum<{
                deny: "deny";
                passthrough: "passthrough";
            }>>;
            sigv4a: z.ZodOptional<z.ZodEnum<{
                deny: "deny";
                passthrough: "passthrough";
            }>>;
        }, z.core.$strip>>;
    }, z.core.$strip>>;
    ignoreViolations: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodArray<z.ZodString>>>;
    enableWeakerNestedSandbox: z.ZodOptional<z.ZodBoolean>;
    allowNestedUserNamespaces: z.ZodOptional<z.ZodBoolean>;
    enableWeakerNetworkIsolation: z.ZodOptional<z.ZodBoolean>;
    allowAppleEvents: z.ZodOptional<z.ZodBoolean>;
    excludedCommands: z.ZodOptional<z.ZodArray<z.ZodString>>;
    ripgrep: z.ZodOptional<z.ZodObject<{
        command: z.ZodString;
        args: z.ZodOptional<z.ZodArray<z.ZodString>>;
    }, z.core.$strip>>;
    bwrapPath: z.ZodCatch<z.ZodOptional<z.ZodPreprocess<z.ZodString, unknown>>>;
    socatPath: z.ZodCatch<z.ZodOptional<z.ZodPreprocess<z.ZodString, unknown>>>;
}, z.core.$loose>;

/**
 * Query interface with methods for controlling query execution.
 * Extends AsyncGenerator and has methods, so not serializable.
 */
export declare interface Query extends AsyncGenerator<SDKMessage, void> {
    /**
     * Control Requests
     * The following methods are control requests, and are only supported when
     * streaming input/output is used.
     */
    /**
     * Interrupt the current query execution. The query will stop processing
     * and return control to the caller. On CLIs advertising the
     * `interrupt_receipt_v1` capability (system/init `capabilities`) the
     * resolved value is the interrupt receipt — `still_queued` uuids of async
     * user messages that WILL still run unless cancelled first. Older CLIs
     * resolve to `undefined`.
     */
    interrupt(): Promise<SDKControlInterruptResponse | undefined>;
    /**
     * Change the permission mode for the current session.
     * Only available in streaming input mode.
     *
     * @param mode - The new permission mode to set
     */
    setPermissionMode(mode: PermissionMode): Promise<void>;
    /**
     * Pin (or clear, with mode:null) a per-MCP-server permission-mode
     * override. Tighten-only: only 'default' | 'auto' | null are accepted;
     * the override applies only when the session mode would already
     * auto-allow (bypassPermissions/auto), so it can never widen privilege.
     * Only available in streaming input mode.
     *
     * @param serverName - The MCP server name (must match the name the server
     *   was registered under)
     * @param mode - 'default' to force per-action prompts, 'auto' to route
     *   through the auto-mode classifier, or null to clear the override
     * @returns An object with an optional `warning` — set when `serverName`
     *   does not match any currently known MCP server. For a set, the
     *   override is stored regardless and applies once a server with that
     *   exact name connects; the warning is informational (typo detection).
     */
    setMcpPermissionModeOverride(serverName: string, mode: 'default' | 'auto' | null): Promise<{
        warning?: string;
    }>;



    /**
     * Change the model used for subsequent responses.
     * Only available in streaming input mode.
     *
     * @param model - The model identifier to use, or undefined to use the default
     */
    setModel(model?: string): Promise<void>;
    /**
     * Set the maximum number of thinking tokens the model is allowed to use
     * when generating its response. This can be used to limit the amount of
     * tokens the model uses for its response, which can help control cost and
     * latency.
     *
     * Use `null` to clear any previously set limit and allow the model to
     * use the default maximum thinking tokens.
     *
     * @deprecated Use the `thinking` option in `query()` instead. On Opus 4.6,
     * this is treated as on/off (0 = disabled, any other value = adaptive).
     * For explicit control, use `thinking: { type: 'adaptive' }` or
     * `thinking: { type: 'enabled', budgetTokens: N }`.
     *
     * @param maxThinkingTokens - Maximum tokens for thinking, or null to clear the limit
     * @param thinkingDisplay - Optional thinking display mode for the rest of
     * the session: a value replaces the session display mode, `null` clears
     * that override so Claude Code's default display handling applies again,
     * and when omitted the display mode from session start (`thinking.display`
     * / `--thinking-display`) is kept — a session started with thinking
     * disabled has none, so re-enabling without this param gets that default.
     * `'highlights'` (the API's one-line thinking titles) is honored by the API
     * only for Anthropic-hosted remote sessions; when the session cannot send it
     * to the API the promise rejects and the display stays as it was, while
     * `maxThinkingTokens` still applies.
     */
    setMaxThinkingTokens(maxThinkingTokens: number | null, thinkingDisplay?: 'summarized' | 'omitted' | 'highlights' | null): Promise<void>;
    /**
     * Merge settings into the flag settings layer. This is the inline `settings`
     * option of `query()`, applied mid-session. Flag settings sit above
     * user/project/local and below managed policy settings in precedence order.
     *
     * Successive calls shallow-merge top-level keys — a second call with
     * `{permissions: {...}}` replaces the entire `permissions` object from a
     * prior call. Pass `null` for a key to clear it from the flag layer and
     * fall back to lower-precedence sources (`undefined` is dropped by JSON
     * serialization and has no effect). Four keys instead reset session state
     * and restore neither a `query()` option nor a settings-file value.
     * `effortLevel` goes to the model's default effort, `model` to Claude Code's
     * default model (not `ANTHROPIC_MODEL` or `settings.model`), `agent` to no
     * main-thread agent, and `ultracode` to off with the current effort kept.
     * Only available in streaming input mode.
     *
     * Rejects if a value would make Claude Code discard the flag settings layer:
     * nothing in that call applies, including its valid keys, and settings from
     * earlier calls stay in force. Catch the rejection. A value Claude Code ignores
     * on its own does not reject, and its key still replaces the earlier value: a
     * `permissions` object whose only deny rule is malformed leaves no deny rules.
     *
     * `ultracode: true` or `false` turns ultracode on or off and leaves the
     * effort level alone. An `effortLevel` that moves the session to a
     * different level, sent without an `ultracode` key, also turns ultracode
     * off; send both keys to change the level and keep it on.
     *
     * @param settings - A partial settings object to merge into the flag
     * settings. `effortLevel` also accepts `'max'` (never written to settings
     * files, so the persisted {@link Settings.effortLevel} excludes it): it is
     * session-only, runs as `'high'` on a model without `'max'` support, and
     * runs no higher than the organization's effort limit for the model.
     */
    applyFlagSettings(settings: {
        [K in keyof Settings]?: K extends 'effortLevel' ? EffortLevel | null : Settings[K] | null;
    }): Promise<void>;
    /**
     * Merge settings into a settings FILE through the CLI's own writer — the
     * same path /config uses (canonical store root, gitignore upkeep,
     * hardened write) — and live-apply them. Unlike applyFlagSettings, which
     * only touches the session-scoped flag layer. The handler accepts only an
     * explicit key allowlist per file (localSettings: outputStyle; userSettings:
     * effortLevel, saved for the session's current model as /effort saves it,
     * without setting the running session's level) with string values — deletion is not
     * supported — and refuses remote transports and sessions whose
     * --setting-sources exclude the target source. Rejects with the gate's or
     * writer's error otherwise.
     */
    updateSettings(source: 'localSettings' | 'userSettings', settings: Record<string, unknown>): Promise<void>;
    /**
     * Get the full initialization result, including supported commands, models,
     * account info, and output style configuration: the first-connect answer,
     * or, on a Query returned by a pre-warmed spare's `claim()`, the claimed
     * session's.
     *
     * @returns The complete initialization response
     */
    initializationResult(): Promise<SDKControlInitializeResponse>;
    /**
     * Re-send the `initialize` control request to an already-running CLI.
     *
     * Use this after a transport gap (e.g. reattaching to a daemon whose
     * ring buffer evicted frames during a disconnect): the CLI's response
     * carries any `can_use_tool` / `request_user_dialog` control requests
     * the loop is still blocked on, and the SDK redelivers them to
     * `canUseTool` / `onUserDialog`. In-flight request_ids are deduped
     * SDK-side, but callbacks should be idempotent per request_id since a
     * request whose response was lost in the gap will be dispatched again.
     *
     * Over stdio the CLI also re-registers this query's hooks from the
     * re-sent request (the response reports `hooks_applied: true`; CLIs that
     * predate that field ignore hooks here) and resolves any hook callback it
     * was still waiting on itself — cancelling it at this host, denying a
     * pending PreToolUse with a retry notice and blocking a pending prompt —
     * since it cannot tell whether the re-sent callback ids still name the
     * same hooks. Expect one denied-then-retried tool call or one prompt to
     * re-send if the call races an unanswered hook.
     *
     * Unlike {@link Query.initializationResult}, this always sends a fresh request
     * rather than returning the cached result.
     *
     * @returns A fresh initialization response
     */
    reinitialize(): Promise<SDKControlInitializeResponse>;

    /**
     * Get the list of available skills for the current session.
     *
     * @returns Array of available skills with their names and descriptions
     */
    supportedCommands(): Promise<SlashCommand[]>;
    /**
     * Get the list of available models.
     *
     * @returns Array of model information including display names and descriptions
     */
    supportedModels(): Promise<ModelInfo[]>;
    /**
     * Get the list of available subagents for the current session.
     *
     * @returns Array of available agents with their names, descriptions, and configuration
     */
    supportedAgents(): Promise<AgentInfo[]>;
    /**
     * Get the current status of all configured MCP servers.
     *
     * @returns Array of MCP server statuses (connected, failed, needs-auth, pending)
     */
    mcpServerStatus(): Promise<McpServerStatus[]>;
    /**
     * Get a breakdown of current context window usage by category
     * (system prompt, tools, messages, MCP tools, memory files, etc.).
     *
     * `detail: 'full'` counts each category with the token-count API;
     * `'summary'` answers from the last response's usage and local estimates
     * without the per-category token-count calls. Defaults to `'full'`.
     *
     * @returns Context usage breakdown including token counts per category and total usage
     */
    getContextUsage(opts?: {
        detail?: 'summary' | 'full';
    }): Promise<SDKControlGetContextUsageResponse>;
    /**
     * Get the structured data behind the `/usage` command: session cost and
     * token usage totals plus claude.ai plan rate-limit utilization windows
     * (5-hour, 7-day, per-model) when available. `rate_limits_available` is
     * false (and `rate_limits` null) for API key, Bedrock, Vertex, and other
     * sessions where plan limits do not apply.
     *
     * `skipBehaviors: true` skips the scan of local transcripts that fills the
     * response's `behaviors` section (it is null in the answer), for callers
     * that need only the plan rate limits. Defaults to scanning.
     *
     * EXPERIMENTAL: this API is unstable and may change or be removed in any
     * release without notice — do not rely on it yet. The method name will
     * change when the API is stabilized.
     *
     * @returns Structured session cost/usage data and plan rate-limit utilization
     */
    usage_EXPERIMENTAL_MAY_CHANGE_DO_NOT_RELY_ON_THIS_API_YET(opts?: {
        skipBehaviors?: boolean;
    }): Promise<SDKControlGetUsageResponse>;











    /**
     * Read a file from the session's filesystem for the remote sidebar
     * viewer. Path is resolved against cwd and gated by the same
     * read-permission rules as the Read tool. Returns null on permission
     * denial, missing file, or transport error.
     *
     * @param path - File path (relative to cwd or absolute)
     * @param options - Optional maxBytes cap (default 1MB) and encoding
     *   (default utf-8; pass 'base64' for binary files like images)
     */
    readFile(path: string, options?: {
        maxBytes?: number;
        encoding?: 'utf-8' | 'base64';
    }): Promise<SDKControlReadFileResponse | null>;

    /**
     * Reload plugins from disk and return the refreshed commands, agents,
     * plugins, and MCP server status.
     *
     * With `holdOnCacheImpact`, the CLI first runs the check the interactive
     * /reload-plugins makes: when applying would change the session's tool
     * list while the conversation's prompt cache depends on it, nothing is
     * applied and the response carries `held: true` with `cache_impact`
     * describing what applying would change; call again without the option
     * to apply anyway.
     *
     * With `addPlugins`, the reload also loads those plugins, as if each had
     * been in the `plugins` option at launch; plugins already loaded stay. Each
     * path must be absolute.
     *
     * With `refuseIfBusy`, a request that finds the session busy reloads nothing:
     * the promise rejects with an error whose `errorCode` is
     * 'reload_plugins_busy', and the caller asks again once the session is idle.
     * Busy: a turn is running or queued, a permission prompt taken over from an
     * earlier process is unanswered, or background work such as an agent or a
     * workflow, or an in-process teammate, is still at work; a background shell
     * command alone is not busy.
     * For a host whose request can arrive late. Only a CLI whose `system/init`
     * lists the capability `reload_plugins_refuse_if_busy_v1` is sure to honor
     * the option: any other may serve the request, in a turn too.
     *
     * @returns The refreshed session components after plugin reload, or the
     * unchanged ones with `held: true` when the reload was held
     */
    reloadPlugins(options?: {
        holdOnCacheImpact?: boolean;
        addPlugins?: SdkPluginConfig[];
        refuseIfBusy?: boolean;
    }): Promise<SDKControlReloadPluginsResponse>;
    /**
     * Reload skills from disk and return the refreshed skill list.
     *
     * @returns The refreshed skill commands after reload
     */
    reloadSkills(): Promise<SDKControlReloadSkillsResponse>;
    /**
     * Re-read the output-style directories from disk and return the refreshed
     * style names. A style file written while the session runs is otherwise
     * invisible to it until the next session. Also drops the shared
     * markdown-file scan cache, so agents, skills and routines re-read their
     * directories on their next use.
     *
     * @returns The refreshed output style names (built-in and custom)
     */
    reloadOutputStyles(): Promise<SDKControlReloadOutputStylesResponse>;
    /**
     * Get information about the authenticated account.
     *
     * @returns Account information including email, organization, and subscription type
     */
    accountInfo(): Promise<AccountInfo>;
    /**
     * Rewind tracked files to their state at a specific user message.
     * Requires file checkpointing to be enabled via the `enableFileCheckpointing` option.
     *
     * @param userMessageId - UUID of the user message to rewind to
     * @param options - Options object with optional `dryRun` boolean to preview changes without modifying files
     * @returns Object with canRewind boolean, optional error message, and file change statistics
     */
    rewindFiles(userMessageId: string, options?: {
        dryRun?: boolean;
    }): Promise<RewindFilesResult>;
    /**
     * Seed the CLI's readFileState cache with a path+mtime entry. Use when
     * the client observed a Read that has since been removed from context
     * (e.g. by snip), so a subsequent Edit won't fail "file not read yet".
     * If the file changed on disk since the given mtime, the seed is skipped
     * and Edit will correctly require a fresh Read.
     *
     * @param path - Path to the file that was previously Read
     * @param mtime - File mtime (floored ms) at the time of the observed Read
     */
    seedReadState(path: string, mtime: number): Promise<void>;









    /**
     * Reconnect an MCP server by name.
     * Throws on failure.
     *
     * @param serverName - The name of the MCP server to reconnect
     */
    reconnectMcpServer(serverName: string): Promise<void>;
    /**
     * Enable or disable an MCP server by name.
     * Throws on failure.
     *
     * @param serverName - The name of the MCP server to toggle
     * @param enabled - Whether the server should be enabled
     */
    toggleMcpServer(serverName: string, enabled: boolean): Promise<void>;
    /**
     * Read one MCP Apps (SEP-1865) UI resource from a connected MCP server the
     * CLI itself dialed, so the host can render a tool's widget. `uri` must use
     * the `ui://` scheme, typically the `_meta.ui.resourceUri` a tool
     * declares. The contents are untrusted third-party HTML: render them
     * sandboxed. Requires a CLI that advertises `mcp_read_resource_v1` in
     * `system/init.capabilities`. Throws on failure.
     *
     * @param serverName - The server's name, as `mcpServerStatus()` reports it
     * @param uri - A `ui://` resource URI
     * @alpha
     */
    readMcpResource(serverName: string, uri: string): Promise<SDKControlMcpReadResourceResponse>;






    /**
     * Dynamically set the MCP servers for this session.
     * This replaces the servers added by earlier calls to this method, and all
     * in-process SDK servers (including any passed in the `mcpServers` option),
     * with the provided set. Servers that are removed will be disconnected, and
     * new servers will be connected.
     *
     * Supports both process-based servers (stdio, sse, http) and SDK servers (in-process).
     * SDK servers are handled locally in the SDK process, while process-based servers
     * are managed by the CLI subprocess.
     *
     * Note: Outside a cloud session, a call that leaves out a stdio, sse or http
     * server passed in the `mcpServers` option does not disconnect it or list it
     * in the result's `removed` list, unless an earlier call to this method named
     * that server. To be able to remove a server later, add it with this method
     * instead of in `mcpServers`.
     *
     * Servers configured via settings files are not affected. A `.mcp.json` or
     * local-scope server of the session's current folder stays up when omitted,
     * unless enterprise policy denies it; once a call has named such a server, a
     * later call that omits it removes it. Servers introduced by plugins are also
     * exempt: they are managed by the plugin system, so omitting them from a call
     * does NOT remove them — they keep running (unless enterprise policy denies
     * the server) and are simply absent from the result's `removed` list. Naming a
     * plugin server explicitly in a call still replaces it. Because of these
     * exceptions, `setMcpServers({})` does not guarantee that a session has no MCP
     * servers left.
     *
     * @param servers - Record of server name to configuration. Pass an empty object to remove the servers this method replaces.
     * @returns Information about which servers were added, removed, and any connection errors
     */
    setMcpServers(servers: Record<string, McpServerConfig>): Promise<McpSetServersResult>;
    /**
     * Stream input messages to the query.
     * Used internally for multi-turn conversations.
     *
     * @param stream - Async iterable of user messages to send
     */
    streamInput(stream: AsyncIterable<SDKUserMessage>): Promise<void>;
    /**
     * Stop a running task. A task_notification with status 'stopped' will be emitted.
     * @param taskId - The task ID from task_notification events
     */
    stopTask(taskId: string): Promise<void>;
    /**
     * Background in-flight foreground tasks (Bash commands and subagents).
     * With `toolUseId`, targets the single task started by that tool_use
     * block; without it, backgrounds all foreground tasks — equivalent to
     * pressing Ctrl+B in the terminal. Each blocking tool call returns
     * immediately with a "running in the background" tool_result and the
     * turn continues; the task keeps running and emits a task_notification
     * when it settles.
     * @param toolUseId - Optional tool_use block id to target a single task
     * @returns true when at least one task was backgrounded; false only
     *   when `toolUseId` was given and it matched no foreground task
     * @throws when background tasks are disabled for the session
     *   (`CLAUDE_CODE_DISABLE_BACKGROUND_TASKS`) — nothing is backgrounded
     */
    backgroundTasks(toolUseId?: string): Promise<boolean>;
    /**
     * Close the query and terminate the underlying process.
     * This forcefully ends the query, cleaning up all resources including
     * pending requests, MCP transports, and the CLI subprocess.
     *
     * Use this when you need to abort a query that is still running.
     * After calling close(), no further messages will be received.
     */
    close(): void;
}

export declare function query(_params: {
    prompt: string | AsyncIterable<SDKUserMessage>;
    options?: Options;
}): Query;

/**
 * Rename a session. Appends a custom-title entry to the session's JSONL file.
 * @param sessionId - UUID of the session
 * @param title - New title
 * @param options - `{ dir?: string }` project path; omit to search all projects
 */
export declare function renameSession(_sessionId: string, _title: string, _options?: SessionMutationOptions): Promise<void>;

/**
 * Result of {@link resolveSettings}.
 * @alpha
 */
export declare type ResolvedSettings = {
    /** Merged settings after applying all enabled sources in precedence order. */
    effective: Settings;
    /** For each top-level key in `effective`, which source supplied the value. */
    provenance: Partial<Record<keyof Settings, ProvenanceEntry>>;
    /**
     * Per-source raw settings, low→high precedence. Use this when per-top-level
     * provenance is too coarse (e.g. checking which tier set a nested key).
     */
    sources: Array<{
        source: ResolvedSettingSource;
        settings: Settings;
        path?: string;
        policyOrigin?: PolicySettingsOrigin;
    }>;
    /**
     * What became of this machine's own policy sources, in the host's own read
     * (not a Claude Code session's). `effective`, `provenance` and `sources` show
     * a source that was not read as absent, so a host that enforces managed
     * settings reads this first. An SDK that predates the member leaves it out,
     * which says nothing either way.
     */
    machinePolicy?: {
        /**
         * `false`, or the kinds of source that may be there and did not load:
         * `'profile'` (a macOS MDM profile), `'registry'` (the Windows HKLM policy
         * value; under WSL also the Windows folder's managed-settings files while
         * WSL does not inherit them), `'file'` (the managed-settings file or a
         * drop-in). Call again to try again: the file is read at every call, the
         * other two once their last read is 30 minutes old (6 hours on native
         * Windows while no registry value is held and reg.exe's last queries of HKLM
         * and HKCU both exited with code 1), or sooner after one that gave no answer
         * or was set aside; once one read has answered, a later read that fails
         * leaves this as it was. A source that the 30-minute
         * read finds gone counts so once a second read agrees, which the first call
         * 30 seconds or more later makes; outside WSL, a profile, or a value that
         * reg.exe handed over, that fails to load where neither of the two, nor a
         * per-user value (HKCU), held policy is named. `false` is no proof: a
         * registry query that fails for good shows as an absent value, and under
         * WSL a `wslInheritsWindowsSettings` that is neither true nor false is not
         * named.
         */
        didNotLoad: false | Array<'profile' | 'registry' | 'file'>;
    };
};

/**
 * Source that contributed an effective setting value. Filesystem sources use
 * the same names as {@link SettingSource}; `'managed'` is the policy tier
 * (managed-settings.json / `managedSettings` option); `'flag'` is the
 * `--settings` CLI flag tier.
 * @alpha
 */
export declare type ResolvedSettingSource = SettingSource | 'managed' | 'flag';

/**
 * Resolve the effective Claude Code settings for the given options using the
 * same merge engine as the CLI, without spawning the Claude CLI. Useful for
 * inspecting what configuration a `query()` call would see.
 *
 * @remarks
 * This reports the **raw settings cascade**, not a security decision. Two
 * caveats:
 *
 * - **The policy tier matches CLI startup** (managed-settings.json,
 *   remote-cached managed settings, MDM via macOS plist / Windows
 *   HKLM/HKCU, and `managedSettings`) **except** the admin-configured
 *   `policyHelper` subprocess is not executed. MDM resolution may invoke
 *   `plutil` (macOS, when an MDM plist exists) or `reg.exe` (Windows/WSL)
 *   on the first call per process, and again at later calls. If your
 *   deployment relies on policyHelper to inject managed settings, results will
 *   differ.
 * - **`permissions.defaultMode` is reported as-is across all tiers**
 *   including project. The CLI applies a separate trust filter before
 *   honoring escalating modes (`bypassPermissions`, `auto`, `acceptEdits`)
 *   from repo-committed files; pass the result through
 *   {@link filterEscalatingDefaultMode} before acting on `defaultMode`.
 *
 * @alpha
 */
export declare function resolveSettings(_opts?: ResolveSettingsOptions): Promise<ResolvedSettings>;

/**
 * Options for {@link resolveSettings}.
 * @alpha
 */
export declare type ResolveSettingsOptions = {
    /**
     * Directory to resolve project/local settings relative to. Defaults to the
     * current process's working directory.
     */
    cwd?: string;
    /**
     * Which filesystem settings sources to load. When omitted, all sources are
     * loaded (matches CLI defaults). Pass `[]` to skip user/project/local
     * sources — the managed-settings policy tier is still read from disk.
     */
    settingSources?: SettingSource[];
    /**
     * Restrictive policy-tier settings — equivalent to `Options.managedSettings`
     * on `query()`. Feeds the lowest-precedence policy sub-source and is
     * filtered through a restrictive-key allowlist (`allowManaged*Only` locks,
     * `permissions.deny`/`ask`, sandbox restrictions); non-restrictive keys
     * such as `model`, `env`, `cleanupPeriodDays` are silently dropped.
     */
    managedSettings?: Settings;
    /**
     * Server-managed settings payload (the result of fetching
     * `/api/claude_code/settings`). Feeds the `'remote'` policy sub-source —
     * same trust level as the on-disk cache it replaces, so non-restrictive
     * keys flow through unfiltered. Use this when the embedding host has a
     * fresher result than the CLI's `~/.claude/remote-settings.json` cache.
     */
    serverManagedSettings?: Settings;
};

/**
 * Result of a rewindFiles operation.
 */
export declare type RewindFilesResult = {
    canRewind: boolean;
    error?: string;
    filesChanged?: string[];
    insertions?: number;
    deletions?: number;
    /**
     * Count of tracked files NOT restored or deleted because a symlink, hard link, or other non-regular file was detected at the tracked path, its parent directory no longer resolves to where it pointed when the checkpoint was taken, it is behind a link in a folder that sandboxed commands can write, or its backup could not be safely read. Only populated by a real (non-dryRun) rewind — on a dryRun response the field is never set and the preview counts do not reflect link-safety refusals. Absent or 0 on a real rewind means no link-safety refusals occurred; other per-file failures (for example a missing backup file) are not counted here; they are reported in telemetry, and when every differing file fails to restore the rewind itself fails (canRewind: false).
     */
    skippedLinks?: number;
};

export declare type SandboxCredentialsConfig = NonNullable<z.infer<ReturnType<typeof SandboxCredentialsConfigSchema>>>;

declare const SandboxCredentialsConfigSchema: () => z.ZodOptional<z.ZodObject<{
    files: z.ZodOptional<z.ZodArray<z.ZodPreprocess<z.ZodObject<{
        path: z.ZodString;
        mode: z.ZodEnum<{
            deny: "deny";
            mask: "mask";
        }>;
        extract: z.ZodOptional<z.ZodString>;
        onExtractNoMatch: z.ZodOptional<z.ZodEnum<{
            deny: "deny";
            error: "error";
            warn: "warn";
        }>>;
        decode: z.ZodOptional<z.ZodEnum<{
            jwt: "jwt";
        }>>;
        maskClaims: z.ZodOptional<z.ZodArray<z.ZodString>>;
        maskDuplicates: z.ZodOptional<z.ZodBoolean>;
        injectHosts: z.ZodOptional<z.ZodArray<z.ZodString>>;
    }, z.core.$strip>, unknown>>>;
    envVars: z.ZodOptional<z.ZodArray<z.ZodPreprocess<z.ZodObject<{
        name: z.ZodString;
        mode: z.ZodEnum<{
            deny: "deny";
            mask: "mask";
        }>;
        extract: z.ZodOptional<z.ZodString>;
        onExtractNoMatch: z.ZodOptional<z.ZodEnum<{
            deny: "deny";
            error: "error";
            warn: "warn";
        }>>;
        decode: z.ZodOptional<z.ZodEnum<{
            jwt: "jwt";
        }>>;
        maskClaims: z.ZodOptional<z.ZodArray<z.ZodString>>;
        injectHosts: z.ZodOptional<z.ZodArray<z.ZodString>>;
    }, z.core.$strip>, unknown>>>;
    allowPlaintextInject: z.ZodOptional<z.ZodBoolean>;
    awsPairs: z.ZodOptional<z.ZodArray<z.ZodObject<{
        accessKeyIdVar: z.ZodString;
        secretAccessKeyVar: z.ZodString;
        sessionTokenVar: z.ZodOptional<z.ZodString>;
    }, z.core.$strip>>>;
    sigv4: z.ZodOptional<z.ZodObject<{
        streaming: z.ZodOptional<z.ZodEnum<{
            deny: "deny";
            passthrough: "passthrough";
        }>>;
        presigned: z.ZodOptional<z.ZodEnum<{
            deny: "deny";
            passthrough: "passthrough";
        }>>;
        sigv4a: z.ZodOptional<z.ZodEnum<{
            deny: "deny";
            passthrough: "passthrough";
        }>>;
    }, z.core.$strip>>;
}, z.core.$strip>>;

export declare type SandboxFilesystemConfig = NonNullable<z.infer<ReturnType<typeof SandboxFilesystemConfigSchema>>>;

/**
 * Filesystem configuration schema for sandbox.
 */
declare const SandboxFilesystemConfigSchema: () => z.ZodOptional<z.ZodObject<{
    allowWrite: z.ZodOptional<z.ZodArray<z.ZodString>>;
    denyWrite: z.ZodOptional<z.ZodArray<z.ZodString>>;
    denyRead: z.ZodOptional<z.ZodArray<z.ZodString>>;
    allowRead: z.ZodOptional<z.ZodArray<z.ZodString>>;
    allowManagedReadPathsOnly: z.ZodOptional<z.ZodBoolean>;
    disabled: z.ZodOptional<z.ZodBoolean>;
}, z.core.$strip>>;

export declare type SandboxIgnoreViolations = NonNullable<SandboxSettings['ignoreViolations']>;

export declare type SandboxNetworkConfig = NonNullable<z.infer<ReturnType<typeof SandboxNetworkConfigSchema>>>;

/**
 * Network configuration schema for sandbox.
 */
declare const SandboxNetworkConfigSchema: () => z.ZodOptional<z.ZodObject<{
    allowedDomains: z.ZodOptional<z.ZodArray<z.ZodString>>;
    deniedDomains: z.ZodOptional<z.ZodArray<z.ZodString>>;
    strictAllowlist: z.ZodOptional<z.ZodBoolean>;
    allowManagedDomainsOnly: z.ZodOptional<z.ZodBoolean>;
    allowUnixSockets: z.ZodOptional<z.ZodArray<z.ZodString>>;
    allowAllUnixSockets: z.ZodOptional<z.ZodBoolean>;
    allowLocalBinding: z.ZodOptional<z.ZodBoolean>;
    allowMachLookup: z.ZodOptional<z.ZodArray<z.ZodString>>;
    httpProxyPort: z.ZodOptional<z.ZodNumber>;
    socksProxyPort: z.ZodOptional<z.ZodNumber>;
    tlsTerminate: z.ZodOptional<z.ZodObject<{
        caCertPath: z.ZodOptional<z.ZodString>;
        caKeyPath: z.ZodOptional<z.ZodString>;
    }, z.core.$strip>>;
}, z.core.$strip>>;

export declare type SandboxSettings = z.infer<ReturnType<typeof PublishedSandboxSettingsSchema>>;

/**
 * Emitted when the user's /goal Stop hook reports met (clears) or not-yet-met (bumps iterations + last_reason). Any surface with a goal indicator re-renders from this. value is null when the goal is cleared. From internal QueryEvent 'active_goal'.
 */
export declare type SDKActiveGoalMessage = {
    type: 'active_goal';
    value: {
        condition: string;
        iterations: number;
        set_at: number;
        tokens_at_start: number;
        last_reason?: string;
    } | null;
    uuid: UUID;
    session_id: string;
};

/**
 * Emitted when an API request fails with a retryable error and will be retried after a delay. error_status is null for connection errors (e.g. timeouts) that had no HTTP response.
 */
export declare type SDKAPIRetryMessage = {
    type: 'system';
    subtype: 'api_retry';
    attempt: number;
    max_retries: number;
    retry_delay_ms: number;
    error_status: number | null;
    error: SDKAssistantMessageError;
    /**
     * Present only when the API sent no response headers within the first-byte window (CLAUDE_STREAM_FIRST_BYTE_TIMEOUT_MS): waited_ms is how long the failed attempt waited for headers, retry_wait_ms how long the retry will wait for them. For this cause max_retries is its own cap (normally one retry), not the session budget.
     */
    no_response?: {
        waited_ms: number;
        retry_wait_ms: number;
    };
    uuid: UUID;
    session_id: string;
};

/**
 * An assistant message. While a response streams the CLI emits one assistant message per completed content block, so several consecutive assistant messages can share message.id and each carries just that block in message.content; on those, message.stop_reason is null and message.usage is not final — the turn's stop reason and total usage arrive on the result message. parent_tool_use_id is non-null when the message was produced inside a subagent started by that tool_use.
 */
export declare type SDKAssistantMessage = {
    type: 'assistant';
    /**
     * Shaped like an Anthropic Messages API Message object (role "assistant"): id, model, content blocks (text, thinking, tool_use, ...), stop_reason and usage. When streamed, content typically holds the single block this message delivers and stop_reason is still null — see SDKAssistantMessage. See the Messages API reference for the block types.
     */
    message: BetaMessage;
    parent_tool_use_id: string | null;
    error?: SDKAssistantMessageError;
    uuid: UUID;

    session_id: string;
    request_id?: string;

    /**
     * Client uuid of the user message this turn is answering (submitMessage options.uuid), stamped on an assistant message each time that send changes — the turn's FIRST top-level assistant message (which may carry only a thinking block, or be a synthetic API-error message), and then, for a turn started by a synthetic (meta) prompt, the first assistant message after each queued user message folded in mid-turn (the fold takes the echo over); with --include-partial-messages the turn's first non-ping stream event is stamped too, independently (see SDKPartialAssistantMessage), so the same uuid may appear on both — either binds the reply to the send it answers without waiting for the result; the server keeps the first stamp it sees per uuid. A turn started by a typed prompt keeps that uuid for its whole turn, so it stamps once per frame kind. A meta turn's own uuid is stamped only when the host vouches it is the client event's own (on a hosted session, the uuid the session server persisted: delivered content such as a Slack owner ping, a Slack-bot observation or a client-injected synthetic turn), never for a prompt the CLI minted itself — except that a turn carrying resume_reason, such as the boot-time rescue turn re-running a turn a worker restart interrupted mid-way, stamps the interrupted turn's own last user prompt, the send it answers, where that can be vouched for (a turn that goes on from a permission answer or from in-flight tool calls may first re-send, unstamped, the assistant message that made those calls); either way a user message folded into a meta turn takes the echo over from it (the rescue turn absorbing messages sent while the session was down; a bot-observation turn absorbing a human's post), and the first reply frame of each kind after that fold carries the folded message's uuid — the first reply that message got. Wrapper-level sibling — never inside `message.content` — so it is not replayed to the model. Absent on every other frame of the turn, on subagent frames (parent_tool_use_id set), on turns that neither had a client uuid nor folded a user message in, and from older producers.
     */
    user_message_uuid?: string;
    /**
     * Client uuids of every user message whose prompt this turn has consumed so far, in consumption order — all members of a prompt batch the host merged into this one turn (several messages sent close together run as one turn whose user_message_uuid is the LAST member's), then any user message folded into the turn before this frame — so a consumer that sent any of them can bind this reply to its own send by finding its uuid anywhere in the list. Always contains user_message_uuid; at most 64 entries. Present exactly when user_message_uuid is, on the same frames; absent from older producers (fall back to user_message_uuid).
     */
    user_message_uuids?: string[];
    /**
     * Why this frame's turn continues one that a worker restart interrupted. Such a turn is the automatic re-run of the interrupted turn (CLAUDE_CODE_RESUME_INTERRUPTED_TURN), or one that goes on from the answer to the permission prompt the new worker took over, or from that turn's tool calls still in flight. The value is the host's CLAUDE_CODE_RESUME_REASON when it set one (host_draining, checkpoint_restore, container_recreated, …), else 'interrupted_turn'. Stamped on the same reply frames as user_message_uuid (which on such a turn names the interrupted turn's own last user prompt), so a consumer can tell its first reply from the interrupted attempt's. Absent on every other turn (also one that goes on from the answer to any other permission prompt), on thinking_tokens frames, and from older producers.
     */
    resume_reason?: string;
    /**
     * This turn continued the preceding truncated assistant turn inside its trailing signed thinking block (max-output-tokens recovery). Its thinking signatures are cumulative over that preceding thinking-only turn, so a history replayed through the bridge must carry this flag back for the normalizer to keep the run's prefix on the wire. Wrapper-level sibling — never inside `message.content` — so it is not replayed to the model.
     */
    resumed_from_incomplete_thinking?: true;
    /**
     * Uuids of earlier messages that this message replaces: after a refusal fallback, or after a response whose tool call could not be parsed. It can name user messages too, such as a refused attempt's tool results. Remove the named messages when this one arrives. After a refusal fallback it is idempotent with the end-of-turn model_refusal_fallback notice.
     */
    supersedes?: UUID[];
    /**
     * True when this assistant message was truncated by an interrupt/abort before the stream completed: stop_reason was never received and the content may end mid-word. Absent on normally completed messages.
     */
    aborted?: true;
    /**
     * ID of the subagent that produced this message: the `task_id` of its task events, unchanged when the subagent is resumed. Absent on main-thread messages.
     */
    agent_id?: string;
    /**
     * Subagent type that produced this message.
     */
    subagent_type?: string;
    /**
     * Description of the subagent task that produced this message.
     */
    task_description?: string;





    /**
     * ISO timestamp of when this content block finished on the originating process. One API assistant turn may produce several assistant messages sharing a message.id, each with its own timestamp. Uses the originating host's clock, so it's for display only; do not order messages by this field. Older emitters omit it; consumers should fall back to receive time.
     */
    timestamp?: string;

    /**
     * Structured twin of the /context report, carried on the synthetic assistant message that delivers the markdown table. Present only on /context results from CLIs new enough to attach it; the markdown in message.content remains the canonical fallback. Wrapper-level sibling — never inside `message.content` — so it is not replayed to the model.
     */
    context_usage?: SDKContextUsage;
    /**
     * Structured twin of the /usage report, carried on the synthetic assistant message that delivers its text: the session totals, the plan's usage rows and extra-usage spend, for remote clients that render a card from data. Present only on /usage results from CLIs new enough to attach it and from claude.ai-subscriber sessions; the text in message.content remains the canonical fallback. Wrapper-level sibling — never inside `message.content` — so it is not replayed to the model.
     */
    usage_report?: SDKUsageReport;





















};

export declare type SDKAssistantMessageError = 'authentication_failed' | 'oauth_org_not_allowed' | 'account_on_hold' | 'verification_required' | 'billing_error' | 'rate_limit' | 'overloaded' | 'invalid_request' | 'model_not_found' | 'server_error' | 'unknown' | 'max_output_tokens' | 'cloud_credential_error';

export declare type SDKAuthStatusMessage = {
    type: 'auth_status';
    isAuthenticating: boolean;
    output: string[];
    error?: string;
    uuid: UUID;
    session_id: string;
};

/**
 * The full set of live background tasks, emitted whenever membership changes (start, completion, kill, a foreground agent being backgrounded) or an entry's `ambient` flag or `parent_task_id` changes. A level signal, unlike the task_started/task_notification edge bookends: consumers that only need 'is background work running' should replace their set with each payload rather than pairing edges, so a missed bookend cannot wedge a stale running indicator. Ordering relative to the bookends for the same transition is unspecified (in practice a task that starts in the background joins the level before its task_started, and a finishing task leaves it after its task_updated and task_notification), so do not correlate it with the edge stream. The level is per-process: nothing is emitted at startup, so consumers must reset to the empty set whenever the session's CLI process (re)starts and let the next membership change repopulate it. A host that re-initializes an already-running process (a repeated `initialize` control request, e.g. after reconnecting) is sent a snapshot of the current set right behind the success response to that request, even when it is empty, so it need not wait for a change; CLIs that predate this send nothing there.
 */
export declare type SDKBackgroundTasksChangedMessage = {
    type: 'system';
    subtype: 'background_tasks_changed';
    /**
     * Every live background task after the change. REPLACE semantics: swap your set for this payload.
     */
    tasks: {
        task_id: string;
        /**
         * Id of one run of the task: equal on every task_* event, background_tasks_changed entry and saved notification (its origin.runId) of that run. A resumed task keeps its task_id and gets a new one. The run ids of one task sort, by plain string comparison, in the order the runs opened; a frame that names a run sorting before the one a reader shows is late. Nothing else about the format is promised. Absent for a task this process did not register, and from CLIs that predate it.
         */
        run_id?: string;
        task_type: string;
        /**
         * Agent type of a local_agent task, such as "general-purpose" or a custom agent's name; "main-session" for a backgrounded main session. Not set on other tasks.
         */
        subagent_type?: string;
        description: string;
        /**
         * task_id of the subagent (local_agent) task whose agent launched this subagent, shell, monitor or workflow task. Absent when the launcher is the main thread, has no task_id of its own (a teammate, an agent inside a workflow), or is no longer tracked. A resumed subagent keeps its original parent. The parent may be a foreground or already-ended task, so treat an unknown id as no parent.
         */
        parent_task_id?: string;
        /**
         * True for tasks that are not activity (every skip_transcript task, plus every live-update watcher, requested or auto-started); hosts should exclude them from activity indicators.
         */
        ambient?: boolean;



    }[];
    uuid: UUID;
    session_id: string;
};

export declare type SdkBeta = 'context-1m-2025-08-07';

/**
 * Fire-and-forget push of the full slash-command list after a mid-session change (e.g. skills discovered dynamically as the agent works in a subdirectory). Clients should REPLACE their cached command list with this payload; supportedCommands() tracks the latest push, so a re-fetch returns the same fresh list.
 */
export declare type SDKCommandsChangedMessage = {
    type: 'system';
    subtype: 'commands_changed';
    commands: SlashCommand[];
    uuid: UUID;
    session_id: string;
};

export declare type SDKCompactBoundaryMessage = {
    type: 'system';
    subtype: 'compact_boundary';
    compact_metadata: {
        trigger: 'manual' | 'auto';
        pre_tokens: number;
        post_tokens?: number;

        duration_ms?: number;





        /**
         * Relink info for messagesToKeep. Loaders splice the preserved segment at anchor_uuid (summary for suffix-preserving, boundary for prefix-preserving partial compact) so resume includes preserved content. Unset when compaction summarizes everything (no messagesToKeep).
         */
        preserved_segment?: {
            head_uuid: UUID;
            anchor_uuid: UUID;
            tail_uuid: UUID;
        };
        /**
         * Ordered messagesToKeep UUIDs. Supersedes preserved_segment — readers look up each UUID directly and relink uuids[i] to uuids[i-1] (uuids[0] to anchor_uuid) instead of walking the parentUuid chain. Unset when compaction summarizes everything.
         */
        preserved_messages?: {
            anchor_uuid: UUID;
            uuids: UUID[];

        };
    };

    uuid: UUID;
    session_id: string;

};

/**
 * Structured twin of the /context report — the data a client needs to render the context-usage card without parsing the markdown table. Evolves additively (new optional fields); a breaking reshape would ship as a sibling field, so consumers can trust the fields they know.
 */
export declare type SDKContextUsage = {
    /**
     * Main-loop model the usage was computed for.
     */
    model: string;
    /**
     * Estimated tokens in use, unclamped — may exceed raw_max_tokens when over limit.
     */
    total_tokens: number;
    /**
     * The window usage is measured against: the resolved autocompact window — the model's believed limit, or a smaller compaction-policy window (a configured value, or e.g. the 200K boundary on 1M-window models).
     */
    raw_max_tokens: number;
    /**
     * Rounded total_tokens / raw_max_tokens, 0-100+.
     */
    percentage: number;
    /**
     * Present when total_tokens exceeds raw_max_tokens. kind says how the window was resolved, not whether the API will accept the next request: 'hard_limit' means the window is the model's believed limit (the API will refuse past it); 'compaction_window' means a compaction-policy window, which may or may not coincide with the model's hard limit.
     */
    over_limit?: {
        tokens_over: number;
        kind: 'hard_limit' | 'compaction_window';
    };
    categories: SDKContextUsageCategory[];
    mcp_tools: {
        /**
         * Wire name, e.g. "mcp__linear__create_issue".
         */
        name: string;
        server_name: string;
        tokens: number;
    }[];
    memory_files: {
        path: string;
        /**
         * Display label of the memory-file source, e.g. "Project" or "User".
         */
        type: string;
        tokens: number;
    }[];
    agents: {
        agent_type: string;
        /**
         * Raw source identifier, e.g. 'projectSettings', 'userSettings', 'plugin'. Built-in agents are excluded by the producer. Display labels are the renderer's concern.
         */
        source: string;
        tokens: number;
    }[];
    /**
     * Omitted when no skills contribute tokens.
     */
    skills?: {
        name: string;
        /**
         * Raw source identifier, e.g. 'userSettings', 'plugin', 'syncedSkills'.
         */
        source: string;
        plugin_name?: string;
        tokens: number;
    }[];
};

/**
 * One row of the /context usage-by-category breakdown. Rows may carry zero tokens; renderers typically hide those.
 */
export declare type SDKContextUsageCategory = {
    /**
     * Display name of the row as the CLI renders it, e.g. "Messages" or "MCP tools (deferred)". Use `kind` (not this name) to classify the row.
     */
    name: string;
    tokens: number;
    /**
     * What the row is: 'used' content occupies the window; 'free' is the remaining window; 'buffer' is the compaction reserve (autocompact or manual); 'deferred' rows are out-of-window tool schemas — listed for awareness, excluded from usage math.
     */
    kind: 'used' | 'free' | 'buffer' | 'deferred';
};

/**
 * Merges the provided settings into the flag settings layer, updating the active configuration.
 */
declare type SDKControlApplyFlagSettingsRequest = {
    subtype: 'apply_flag_settings';
    settings: Record<string, unknown>;
};

/**
 * Backgrounds in-flight foreground tasks (Bash commands and subagents). With tool_use_id, targets the single task started by that tool_use block; without it, backgrounds all foreground tasks — the control-request equivalent of pressing Ctrl+B in the terminal. Each blocking tool call returns immediately with a "running in the background" tool_result and the turn continues; the task keeps running and emits a task_notification when it settles.
 */
declare type SDKControlBackgroundTasksRequest = {
    subtype: 'background_tasks';
    /**
     * When set, backgrounds only the task whose originating tool_use block has this id. When omitted, backgrounds all foreground tasks (Ctrl+B semantics).
     */
    tool_use_id?: string;
};

/**
 * Drops a pending async user message from the command queue by uuid. No-op if already dequeued for execution. Also a no-op, on a worker that recognises held messages, for the queued re-run of an interrupted turn while that re-run also answers for other client messages, which cancelling it would close though nobody withdrew them; see the response.
 */
declare type SDKControlCancelAsyncMessageRequest = {
    subtype: 'cancel_async_message';
    message_uuid: string;
};

/**
 * Tells the other side that the sender no longer needs the answer to one of its own in-flight control_requests (for example a pending can_use_tool prompt after the turn was interrupted, or one that another client already answered). Either side may send it for a request it originated. The sender stops waiting at once and ignores any control_response that still arrives for that request_id; a receiver that can abort the work does so and may still reply (typically with an error), otherwise it simply completes the request. There is no reply to the cancel itself.
 */
declare type SDKControlCancelRequest = {
    type: 'control_cancel_request';
    /**
     * The request_id of the control_request being withdrawn.
     */
    request_id: string;


};

/**
 * Requests the SDK consumer to handle an MCP elicitation (user input request).
 */
declare type SDKControlElicitationRequest = {
    subtype: 'elicitation';
    mcp_server_name: string;
    message: string;
    mode?: 'form' | 'url';
    url?: string;
    elicitation_id?: string;
    requested_schema?: Record<string, unknown>;
    /**
     * requested_schema.properties' top-level keys in the order the MCP server listed them; absent for URL mode and when the schema has no properties object. For a host whose transport keeps no JSON object key order (a protobuf Struct, say). Names that look like array indices ("0", "1", …) come first, in JavaScript's object key order.
     */
    property_order?: string[];
    /**
     * Permission-display title from the MCP server's _meta['anthropic/permissionDisplay']. Mirrors can_use_tool.title so SDK consumers can render elicitation-driven permission prompts with structured headers instead of parsing `message`.
     */
    title?: string;
    /**
     * Short tool/server label from _meta['anthropic/permissionDisplay'].displayName. Mirrors can_use_tool.display_name.
     */
    display_name?: string;
    /**
     * Permission-display subtitle from _meta['anthropic/permissionDisplay'].description. Mirrors can_use_tool.description.
     */
    description?: string;
};

/**
 * Requests at-mention file autocomplete suggestions for a partial path prefix. Returns the same fuzzy-matched results the TUI shows.
 */
declare type SDKControlFileSuggestionsRequest = {
    subtype: 'file_suggestions';
    query: string;
};

/**
 * Requests the responder's CLI binary version. Used by /version in --remote mode so the thin client can show both its own and the remote container's version.
 */
declare type SDKControlGetBinaryVersionRequest = {
    subtype: 'get_binary_version';
};

/**
 * Requests a breakdown of current context window usage by category.
 */
declare type SDKControlGetContextUsageRequest = {
    subtype: 'get_context_usage';
    /**
     * 'full' counts each category with the token-count API; 'summary' answers from the last response's usage and local estimates without the per-category token-count calls. Defaults to 'full'.
     */
    detail?: 'summary' | 'full';
};

/**
 * Breakdown of current context window usage by category (system prompt, tools, messages, etc.).
 */
export declare type SDKControlGetContextUsageResponse = {
    categories: {
        /**
         * Which row this is. Stable where the English name is not: match a particular row on this. Absent from a CLI that predates it. A later CLI may add values: treat an unknown value as absent.
         */
        id?: 'system_prompt' | 'system_tools' | 'mcp_tools' | 'mcp_instructions' | 'mcp_tools_deferred' | 'system_tools_deferred' | 'custom_agents' | 'memory_files' | 'skills' | 'messages' | 'autocompact_buffer' | 'compact_buffer' | 'free_space';
        name: string;
        tokens: number;
        color: string;
        isDeferred?: boolean;
        /**
         * What the row is, the same classification the /context result's context_usage rows carry: 'used' content occupies the window; 'free' is the remaining window; 'buffer' is the compaction reserve; 'deferred' rows are out-of-window tool schemas. Classify on this, never on the English name.
         */
        kind: 'used' | 'free' | 'buffer' | 'deferred';
    }[];
    totalTokens: number;
    maxTokens: number;
    rawMaxTokens: number;
    percentage: number;
    gridRows: {
        color: string;
        isFilled: boolean;
        categoryName: string;
        tokens: number;
        percentage: number;
        squareFullness: number;
    }[][];
    model: string;
    memoryFiles: {
        path: string;
        type: string;
        tokens: number;
    }[];
    mcpTools: {
        name: string;
        serverName: string;
        tokens: number;
        isLoaded?: boolean;
    }[];
    /**
     * The 'mcp_instructions' row by server. Only the row's total is counted: each server's share of it is estimated from the length of its text. Present only where the CLI answers on its own stdio and no server stores or forwards the reply.
     */
    mcpInstructions?: {
        /**
         * Server name, as mcp_status reports it and mcp_toggle takes it (not normalized, unlike mcpTools[].serverName).
         */
        serverName: string;
        tokens: number;
    }[];
    deferredBuiltinTools?: {
        name: string;
        tokens: number;
        isLoaded: boolean;
    }[];
    systemTools?: {
        name: string;
        tokens: number;
    }[];
    systemPromptSections?: {
        name: string;
        tokens: number;
    }[];
    agents: {
        agentType: string;
        source: string;
        /**
         * Id of the providing plugin (its name and marketplace), when there is one. Present only where the CLI answers on its own stdio and no server stores or forwards the reply.
         */
        pluginId?: string;
        /**
         * Absolute path of the agent's file on the machine the CLI runs on, which over SSH or WSL is not the host's. Present only where the CLI answers on its own stdio and no server stores or forwards the reply: absent on cloud, self-hosted runner and Remote Control connections, and for an agent with no file.
         */
        path?: string;
        tokens: number;
    }[];
    slashCommands?: {
        totalCommands: number;
        includedCommands: number;
        tokens: number;
    };
    skills?: {
        totalSkills: number;
        includedSkills: number;
        tokens: number;
        skillFrontmatter: {
            name: string;
            source: string;
            /**
             * Name of the providing plugin, when there is one. Not unique across marketplaces: pluginId is.
             */
            pluginName?: string;
            /**
             * Id of the providing plugin (its name and marketplace), when there is one. Present only where the CLI answers on its own stdio and no server stores or forwards the reply.
             */
            pluginId?: string;
            /**
             * Absolute path of the skill's file on the machine the CLI runs on, which over SSH or WSL is not the host's. Present only where the CLI answers on its own stdio and no server stores or forwards the reply: absent on cloud, self-hosted runner and Remote Control connections, and for a skill with no file.
             */
            path?: string;
            tokens: number;
        }[];
    };
    autoCompactThreshold?: number;
    isAutoCompactEnabled: boolean;
    messageBreakdown?: {
        toolCallTokens: number;
        toolResultTokens: number;
        attachmentTokens: number;
        assistantMessageTokens: number;
        userMessageTokens: number;
        redirectedContextTokens: number;
        unattributedTokens: number;
        toolCallsByType: {
            name: string;
            callTokens: number;
            resultTokens: number;
        }[];
        attachmentsByType: {
            name: string;
            tokens: number;
        }[];
    };
    apiUsage: {
        input_tokens: number;
        output_tokens: number;
        cache_creation_input_tokens: number;
        cache_read_input_tokens: number;
    } | null;


};

/**
 * Returns the hooks listing the CLI's read-only /hooks menu renders: settings-file, session, and plugin hooks grouped by event and matcher, with display-ready strings (control characters revealed) and the policy and safe-mode state the menu banners on. A snapshot at request time; hosts re-request when their surface opens.
 */
declare type SDKControlGetHooksListingRequest = {
    subtype: 'get_hooks_listing';
};

/**
 * The hooks listing the CLI's /hooks menu renders, with display-ready strings.
 */
declare type SDKControlGetHooksListingResponse = {
    /**
     * Events that have at least one listed hook, in the /hooks menu’s lifecycle order.
     */
    events: {
        /**
         * Hook event name.
         */
        name: string;
        /**
         * One-line summary, as the /hooks event list shows.
         */
        summary: string;
        /**
         * Whether hooks on this event can carry a matcher.
         */
        supportsMatcher: boolean;
        /**
         * Number of listed hooks.
         */
        hookCount: number;
    }[];
    /**
     * One row per listed hook: events in lifecycle order, matchers in the menu’s priority order.
     */
    hooks: {
        event: string;
        /**
         * Matcher with control characters revealed; '' when the entry has none.
         */
        matcher: string;
        /**
         * Raw source name (userSettings, sessionHook, pluginHook, …).
         */
        source: string;
        /**
         * User-facing source description.
         */
        sourceLabel: string;
        pluginName?: string;
        /**
         * Hook type (command, prompt, agent, http, mcp_tool, …).
         */
        type: string;
        /**
         * List-row label: statusMessage when set, else the identity text; one line, control characters revealed.
         */
        displayText: string;
        /**
         * Identity text — the literal command/prompt/URL that runs, control characters revealed.
         */
        commandText: string;
        /**
         * Label for commandText (Command, Prompt, URL, …).
         */
        contentLabel: string;
        /**
         * If-condition, revealed, when set.
         */
        condition?: string;
        /**
         * Timeout in seconds.
         */
        timeout?: number;
        statusMessage?: string;
        runsOnce?: boolean;
        runsInBackground?: boolean;
        /**
         * True when the session's mode or policy keeps this hook from running (the policy block and safeMode/bareMode say why); absent on rows that run.
         */
        disabled?: true;
        /**
         * The entry as stored (raw matcher, '' when none, and raw hook object; no display escaping) for a host's edit form and as the target it names to `claude edit-hook`. Only on rows from a settings file this session reads and may write. HTTP header values are blanked (headersRedacted); a replace that sends no headers keeps the stored ones.
         */
        editable?: {
            matcher: string;
            config: Record<string, unknown>;
            headersRedacted?: true;
        };
    }[];
    /**
     * Every hook event in lifecycle order (name, the /hooks summary, whether its hooks take a matcher), for an add-hook form.
     */
    eventCatalog: {
        name: string;
        summary: string;
        supportsMatcher: boolean;
    }[];
    policy: {
        /**
         * Managed disableAllHooks — nothing runs at all.
         */
        disabledByPolicy: boolean;
        /**
         * Managed allowManagedHooksOnly — non-managed hooks are blocked and managed hooks are intentionally not listed.
         */
        managedOnly: boolean;
        /**
         * Managed strictPluginOnlyCustomization locks the hooks surface.
         */
        pluginOnly: boolean;
        /**
         * Effective disableAllHooks, whatever source set it.
         */
        allDisabled: boolean;
        /**
         * Hooks configured in managed settings (they run even under a non-managed disableAllHooks).
         */
        policyHookCount: number;
        /**
         * Present when a managed settings source exists but could not be read: what the organization configured is unknown, so edit_hook refuses every edit (fail-closed) and a host locks its editing controls, as it does under the three locks above.
         */
        policyUnreadable?: true;
    };
    /**
     * Present only when the session runs under --safe-mode.
     */
    safeMode?: {
        managedHooksStillApply: boolean;
        /**
         * How to leave safe mode, per its activation source.
         */
        exitHint: string;
    };
    /**
     * Present only under --bare / CLAUDE_CODE_SIMPLE with the hooks surface gated off: settings-file, flag, policy, and a person's plugin hooks never fire there; session hooks and the hooks of plugins managed settings enable still run.
     */
    bareMode?: {
        /**
         * How to leave bare mode, per its activation source.
         */
        exitHint: string;
    };
    /**
     * Settings files skipped by the merge — their hooks are neither listed nor running.
     */
    errors?: coreTypes.SDKSettingsParseError[];
};

/**
 * Requests the formatted session cost summary (the same text /usage prints in non-interactive mode). Used by the thin-client /usage dialog to show the remote container cost instead of the local $0.00.
 */
declare type SDKControlGetSessionCostRequest = {
    subtype: 'get_session_cost';
};

/**
 * Returns the effective merged settings and the raw per-source settings.
 */
declare type SDKControlGetSettingsRequest = {
    subtype: 'get_settings';
};

/**
 * Reads the end of one background shell or Monitor task's output: at most the last 8 KiB the command wrote, the same tail the terminal's /tasks detail view reads. Read-only and no model turn; a host polls it while the task runs, and can read it once more after the task ends. The output is whatever the command printed, escape sequences included: render it as plain text. Refused for a task_id that is neither a shell or Monitor task of this session nor shaped like one (an ended task's id whose file is gone reads as empty), and on a lane that redacts what it persists (a Remote Control bridge worker, a tenant worker).
 */
declare type SDKControlGetTaskOutputRequest = {
    subtype: 'get_task_output';
    /**
     * A shell or Monitor task of this session, running or ended: the task_id from task_started or background_tasks_changed.
     */
    task_id: string;




};

/**
 * Success payload answering get_task_output.
 */
declare type SDKControlGetTaskOutputResponse = {
    /**
     * The end of the output, decoded as UTF-8; empty when the command has written nothing yet.
     */
    output: string;
    /**
     * The size of the whole output in bytes.
     */
    total_bytes: number;
    /**
     * Whether output holds only the end of a longer output (the last 8 KiB).
     */
    truncated: boolean;






};

/**
 * Requests the structured /usage data: session cost/usage totals plus claude.ai plan rate-limit utilization when available. Experimental — the response shape may change.
 */
declare type SDKControlGetUsageRequest = {
    subtype: 'get_usage';
    /**
     * Skip the scan of local transcripts that produces the response's behaviors section (it is null in the answer). For callers that need only the plan rate limits, such as a usage meter; the scan reads every transcript touched in the last seven days.
     */
    skip_behaviors?: boolean;

};

/**
 * Structured /usage data: session cost/usage totals plus claude.ai plan rate-limit utilization. Experimental — the shape may change.
 */
export declare type SDKControlGetUsageResponse = {
    /**
     * Cost and usage accumulated by the current session.
     */
    session: {
        total_cost_usd: number;
        total_api_duration_ms: number;
        total_duration_ms: number;
        total_lines_added: number;
        total_lines_removed: number;
        model_usage: Record<string, coreTypes.ModelUsage>;
    };
    /**
     * Claude.ai subscription type ('pro', 'max', 'team', 'enterprise') or null for API key / 3P provider sessions.
     */
    subscription_type: string | null;
    /**
     * False when plan rate limits do not apply (API key, Bedrock, Vertex, or missing profile scope) — rate_limits will be null.
     */
    rate_limits_available: boolean;
    /**
     * Plan rate-limit utilization windows from the claude.ai usage endpoint, or null when unavailable.
     */
    rate_limits: {
        five_hour?: {
            /**
             * Percentage of the window used, 0-100.
             */
            utilization: number | null;
            /**
             * ISO 8601 timestamp when the window resets.
             */
            resets_at: string | null;
        } | null;
        seven_day?: {
            /**
             * Percentage of the window used, 0-100.
             */
            utilization: number | null;
            /**
             * ISO 8601 timestamp when the window resets.
             */
            resets_at: string | null;
        } | null;
        seven_day_oauth_apps?: {
            /**
             * Percentage of the window used, 0-100.
             */
            utilization: number | null;
            /**
             * ISO 8601 timestamp when the window resets.
             */
            resets_at: string | null;
        } | null;
        seven_day_opus?: {
            /**
             * Percentage of the window used, 0-100.
             */
            utilization: number | null;
            /**
             * ISO 8601 timestamp when the window resets.
             */
            resets_at: string | null;
        } | null;
        seven_day_sonnet?: {
            /**
             * Percentage of the window used, 0-100.
             */
            utilization: number | null;
            /**
             * ISO 8601 timestamp when the window resets.
             */
            resets_at: string | null;
        } | null;
        /**
         * Per-model weekly windows from the server limits[] array, filtered by the overage-included-models allowlist. Additive: absent when nothing is known about them (an answer served from cached data, or rows the allowlist hides); an empty array means the endpoint itself answered and listed no per-model weekly window at all for this account, before the allowlist was applied.
         */
        model_scoped?: {
            /**
             * Server-supplied label for the model bucket (e.g. 'Fable').
             */
            display_name: string;
            utilization: number | null;
            resets_at: string | null;
        }[];
        extra_usage?: {
            is_enabled: boolean;
            monthly_limit: number | null;
            used_credits: number | null;
            utilization: number | null;
            currency?: string | null;
        } | null;
    } | null;
    /**
     * What's contributing to limits usage, from a scan of local transcripts on this machine (the same data the /usage dialog renders): behavioral characteristics plus per-skill/agent/plugin/MCP-server attribution. Approximate, excludes other devices and claude.ai. Null for non-claude.ai-subscriber sessions (mirrors the dialog) or when the scan fails.
     */
    behaviors: {
        /**
         * Last 24 hours.
         */
        day: {
            /**
             * API requests found in local transcripts for this window.
             */
            request_count: number;
            /**
             * Distinct sessions observed in this window.
             */
            session_count: number;
            /**
             * Behavioral characteristics of local usage. Categories overlap — this is not a partition, so percentages do not sum to 100.
             */
            behaviors: {
                key: 'cache_miss' | 'long_context' | 'subagent_heavy' | 'high_parallel' | 'cron' | 'max_effort' | 'workflow' | 'always_on_context' | 'large_tool_results';
                /**
                 * Share of the weighted local usage attributed to this behavior, 0-100.
                 */
                pct: number;
                /**
                 * Requests in this window exhibiting the behavior.
                 */
                count: number;
            }[];
            /**
             * One recommended change per notable behavior or source, largest share first, worded for display.
             */
            recommendations?: {
                /**
                 * The behavior key, or 'agent', 'skill', 'plugin' or 'mcp_server' for a named source.
                 */
                key: string;
                /**
                 * Share of the weighted local usage this touches, 0-100.
                 */
                pct: number;
                /**
                 * What to do, verb first.
                 */
                title: string;
                /**
                 * A few words: what the scan saw, or the command to run.
                 */
                detail?: string;
            }[];
            /**
             * What one "fix" action does. Absent when nothing can be fixed in the session that answered.
             */
            fix?: {
                /**
                 * The recommendations it covers.
                 */
                keys: string[];
                /**
                 * User messages to send for the person, one each and in order, at priority 'later' so a running turn cannot reorder them: any /effort commands first, then one prompt for the rest, which goes with client_composed set.
                 */
                messages: string[];
            };
            agents: {
                name: string;
                /**
                 * Share of the weighted local usage attributed to this item, 0-100.
                 */
                pct: number;
            }[];
            skills: {
                name: string;
                /**
                 * Share of the weighted local usage attributed to this item, 0-100.
                 */
                pct: number;
            }[];
            plugins: {
                name: string;
                /**
                 * Share of the weighted local usage attributed to this item, 0-100.
                 */
                pct: number;
            }[];
            mcp_servers: {
                name: string;
                /**
                 * Share of the weighted local usage attributed to this item, 0-100.
                 */
                pct: number;
            }[];
        };
        /**
         * Last 7 days.
         */
        week: {
            /**
             * API requests found in local transcripts for this window.
             */
            request_count: number;
            /**
             * Distinct sessions observed in this window.
             */
            session_count: number;
            /**
             * Behavioral characteristics of local usage. Categories overlap — this is not a partition, so percentages do not sum to 100.
             */
            behaviors: {
                key: 'cache_miss' | 'long_context' | 'subagent_heavy' | 'high_parallel' | 'cron' | 'max_effort' | 'workflow' | 'always_on_context' | 'large_tool_results';
                /**
                 * Share of the weighted local usage attributed to this behavior, 0-100.
                 */
                pct: number;
                /**
                 * Requests in this window exhibiting the behavior.
                 */
                count: number;
            }[];
            /**
             * One recommended change per notable behavior or source, largest share first, worded for display.
             */
            recommendations?: {
                /**
                 * The behavior key, or 'agent', 'skill', 'plugin' or 'mcp_server' for a named source.
                 */
                key: string;
                /**
                 * Share of the weighted local usage this touches, 0-100.
                 */
                pct: number;
                /**
                 * What to do, verb first.
                 */
                title: string;
                /**
                 * A few words: what the scan saw, or the command to run.
                 */
                detail?: string;
            }[];
            /**
             * What one "fix" action does. Absent when nothing can be fixed in the session that answered.
             */
            fix?: {
                /**
                 * The recommendations it covers.
                 */
                keys: string[];
                /**
                 * User messages to send for the person, one each and in order, at priority 'later' so a running turn cannot reorder them: any /effort commands first, then one prompt for the rest, which goes with client_composed set.
                 */
                messages: string[];
            };
            agents: {
                name: string;
                /**
                 * Share of the weighted local usage attributed to this item, 0-100.
                 */
                pct: number;
            }[];
            skills: {
                name: string;
                /**
                 * Share of the weighted local usage attributed to this item, 0-100.
                 */
                pct: number;
            }[];
            plugins: {
                name: string;
                /**
                 * Share of the weighted local usage attributed to this item, 0-100.
                 */
                pct: number;
            }[];
            mcp_servers: {
                name: string;
                /**
                 * Share of the weighted local usage attributed to this item, 0-100.
                 */
                pct: number;
            }[];
        };
    } | null;
};

/**
 * Initializes the SDK session with hooks, MCP servers, and agent configuration.
 */
declare type SDKControlInitializeRequest = {
    subtype: 'initialize';
    hooks?: Partial<Record<coreTypes.HookEvent, SDKHookCallbackMatcher[]>>;
    sdkMcpServers?: string[];
    /**
     * Settings for the SDK-hosted MCP servers named in sdkMcpServers, keyed by server name. Sent as a separate field so a CLI that predates it ignores it; entries whose name is not in sdkMcpServers, and values that do not match this shape, are ignored rather than rejected. timeout, disableAutoBackground, connectorId, autoModeVerdictTools, remoteControlMetaKeys, dataFlowServer and onPersonsMachine apply when the server is first registered; tools (the per-tool permission policy) adds its ask and deny rules on every initialize that names the server. An initialize never removes a rule; mcp_set_servers replaces them.
     */
    sdkMcpServerConfigs?: Record<string, {
        /**
         * Per-server tool-call timeout in milliseconds. Overrides the MCP_TOOL_TIMEOUT environment variable for this server. Hard wall-clock limit per call; progress notifications do not extend it. Values below 1000ms are ignored (falls through to MCP_TOOL_TIMEOUT or the default). Applies when the server is first registered; changing it for an already-registered server has no effect until it is removed and re-added.
         */
        timeout?: number;






        /**
         * Per-tool permission policy the host declares for this server's tools (not the tool definitions passed to createSdkMcpServer). always_ask: the CLI asks the host (canUseTool or the permission prompt tool) before each call, even where an allow rule or allowedTools covers the tool, and under bypassPermissions outside a hosted remote session (CLAUDE_CODE_REMOTE); under dontAsk the call is denied; in auto mode the classifier decides, except that by default a tool annotated destructiveHint still asks. always_deny: calls are denied, except a mod's own ($.tool.call, $.mcp.call). always_allow and org_max_permission are ignored on sdk servers; grant allows with allowedTools or canUseTool. Read from initialize (sdkMcpServerConfigs) and from each mcp_set_servers entry that names the server. On the wire an entry without tools states no policy: on initialize the stored list and the rules stand; on mcp_set_servers the rules are replaced without them. The Agent SDK always re-sends the registered list. An entry whose policy is not one of the three asks; an entry without a string name is dropped and the rest apply; a value that is not a list reads as absent.
         */
        tools?: coreTypes.McpServerToolPolicy[];
    }>;
    /**
     * Optional, keyed by sdk server name (each key should also appear in sdkMcpServers; other keys are ignored). Unlike sdkMcpServerConfigs — host-declared settings the CLI keeps for the server's lifetime, same shape inline on mcp_set_servers — this is a one-shot cache of the servers' own handshake output: sent on initialize only, consumed by the connect that follows it, never retained. MCP handshake results the host already obtained from its in-process servers by delivering initialize + notifications/initialized (+ tools/list) to them itself before writing this request. For each such server the CLI answers its own MCP client's initialize and first tools/list from these results and skips the notifications/initialized round trip, so registering N in-process servers costs no mcp_message control round trips before the first turn; tools/call and everything after the handshake still flow as mcp_message exactly as before. The host MUST keep answering mcp_message for every server as if this field were absent: a CLI that predates the field ignores it and performs the full per-server handshake over the control channel, and a newer CLI does the same for any server whose entry is missing or malformed, whose initializeResult.protocolVersion differs from the MCP protocol version the CLI's client requests, or that the CLI had already connected. Entries apply only to the connect that follows this initialize; they are never retained for later reconnects. Over a remote session transport the CLI uses the field only when sdkMcpServerManifestsOrigin is set (see that field); a host on the CLI's own stream-json stdio transport needs no marker. sdk_mcp_manifests_parked in the response reports what became of each entry. Absent (older hosts, the Python SDK, browser clients): unchanged behaviour.
     */
    sdkMcpServerManifests?: Record<string, {
        /**
         * The server's verbatim JSON-RPC `initialize` result object (protocolVersion, capabilities, serverInfo, instructions, ...), exactly as the in-process server produced it when the host initialized it with no client capabilities — not re-serialized or schema-parsed by the host.
         */
        initializeResult: Record<string, unknown>;
        /**
         * The server's verbatim JSON-RPC `tools/list` result object. Omit when the initialize result does not advertise the tools capability, when the listing is paginated (nextCursor present), or when it could not be captured — the CLI then lists over the control channel as before.
         */
        toolsListResult?: Record<string, unknown>;
    }>;
    /**
     * The host's statement that it composed this request's sdkMcpServerManifests for this very send, from its servers' current state. Needed only by a host that reaches the CLI over a remote session transport, where an unmarked sdkMcpServerManifests is not used (a recorded registration could be handed to a later worker). The CLI also refuses a marked manifest whose session-stream frame is more than five minutes old, so capture the manifests when writing the request, not earlier. It declines them too when manifests are switched off in that CLI. Over a remote session it also declines them in three more cases: in any session other than an interactive Cowork chat started from claude.ai; until Anthropic has served that CLI its manifests switch on (so not before its feature flags load); and where the session service has not recently told the CLI that only the account owning the session can send events to it. sdk_mcp_manifests_parked in the response says what became of each entry. A value this CLI does not know counts as no marker. A host on the CLI's own stream-json stdio transport may omit this field; a host writing to the stdin of a remote-session worker cannot use manifests at all.
     */
    sdkMcpServerManifestsOrigin?: 'host_per_send';
    jsonSchema?: Record<string, unknown>;
    systemPrompt?: string[];
    appendSystemPrompt?: string;
    /**
     * Record the conversation's system prompt once and reuse it verbatim on every later request and resume. Omitted or true (the default): the prompt is rendered on the first request, systemPrompt or appendSystemPrompt included, and the record is sent as-is afterwards — even when a later launch passes different text — until compaction. false: never record; the prompt is rendered fresh every request. No effect where system-prompt recording is not yet enabled.
     */
    systemPromptSnapshot?: boolean;
    /**
     * Custom workflow body for the plan-mode system reminder. Replaces the default code-implementation phases; the CLI still wraps it with the read-only enforcement preamble and the ExitPlanMode protocol footer.
     */
    planModeInstructions?: string;

    /**
     * Map of tool-name aliases applied before name resolution. When the model emits a tool_use whose name is a key in this map, the tool execution path resolves the mapped name instead. Single-hop (no chains). See Options.toolAliases.
     */
    toolAliases?: Record<string, string>;

    /**
     * When true, omit per-user dynamic sections (working directory, auto-memory path) from the cached system prompt and re-inject them as the first user message. Lets cross-user prompt caching hit on a static system prompt prefix. Tradeoff: the model sees this context slightly later in the prompt, so steering on the working directory and memory location is marginally less authoritative. Has no effect when a custom (non-preset) system prompt is in use.
     */
    excludeDynamicSections?: boolean;
    agents?: Record<string, coreTypes.AgentDefinition>;
    /**
     * Custom session title. When provided, the session uses this title and skips automatic title generation. Has no effect on the persisted title when resuming an existing session.
     */
    title?: string;
    /**
     * When provided, only skills whose names match an entry are loaded into the main session system prompt, matching the exact canonical name (e.g. "my-plugin:my-skill") or a ":name" suffix of it. Display names and aliases do not match. Omit to load every discovered skill. Applies to the main session only; subagents use AgentDefinition.skills, which additionally resolves display names and aliases.
     */
    skills?: string[];

    promptSuggestions?: boolean;
    agentProgressSummaries?: boolean;
    forwardSubagentText?: boolean;
    /**
     * Dialog kinds (request_user_dialog `dialog_kind` values) this consumer's onUserDialog can actually render. The CLI treats ABSENCE as 'cannot display' and fails closed: without the kind declared here, a dialog-gated flow degrades to its no-dialog behavior (for 'refusal_fallback_prompt', the classic refusal error) instead of parking a dialog the consumer may mishandle. First-attached-client-wins on multi-client sessions; later initializes do not change it.
     */
    supportedDialogKinds?: string[];

    /**
     * Declares that this consumer renders a per-task stop control wired to the `stop_task` control request, so the user can stop an individual background task. When declared, an interrupt on an open-input (interactive stream-json) session spares running background agents/workflows (Stop only aborts the turn). Closed-input exception: a one-shot run (string prompt / -p closes stdin) still kills hold-back tasks at the held-result release regardless of the declaration — with stdin closed, a stop_task control could never be delivered, so the fail-closed kill stands. ABSENCE also fails closed: the interrupt kills background tasks, since the user would otherwise have no way to stop a runaway one. First-attached-client-wins on multi-client sessions; later initializes do not change it.
     */
    perTaskStopAffordance?: boolean;






    /**
     * Plugins to load for the session, in the same shape as the SDK `plugins` option: the stdin form of one --plugin-dir flag per entry (--plugin-dir-no-mcp when skipMcpDiscovery is set), so the launch command line does not grow with the plugin count. Loaded only by a CLI launched with --await-initialize, which reads this request during startup before any plugin work. Without that flag, on a repeated initialize, or over a remote session transport the field loads nothing; plugins_applied in the response reports whether the listed plugins are in fact loaded.
     */
    plugins?: coreTypes.SdkPluginConfig[];
    /**
     * MCP servers for Claude Code to run or connect to, keyed by server name: the serializable entries of the SDK `mcpServers` option (host-resident servers go in sdkMcpServers), as the stdin form of one --mcp-config item, which keeps server credentials (stdio `env`, http and sse `headers`) off the command line. Read only at launch under --await-initialize, and then handled as --mcp-config: an invalid entry is skipped and reported in system/init, not fatal; one difference is that a Claude Code process this one starts is not handed them. Without that flag, on a repeated initialize, or over a remote session transport it loads nothing; use mcp_set_servers in a running session. mcp_servers_applied in the response says whether these are the set read at launch.
     */
    mcpServers?: Record<string, coreTypes.McpServerConfigForProcessTransport>;






};

/**
 * Response from session initialization with available commands, models, and account info.
 */
export declare type SDKControlInitializeResponse = {
    commands: coreTypes.SlashCommand[];
    agents: coreTypes.AgentInfo[];
    output_style: string;
    available_output_styles: string[];

    models: coreTypes.ModelInfo[];

    /**
     * Information about the logged in user's account.
     */
    account: coreTypes.AccountInfo;





    /**
     * Whether the `hooks` this initialize carried were registered: true on a session's first initialize, and on a repeated initialize from the process that owns the CLI's stdin (its set replaces the one registered earlier); false when a repeated initialize's hooks were ignored (a client joining a remote session another client configured). Absent when the request carried no hooks, and on CLIs that predate the field — those ignored `hooks` on every repeated initialize.
     */
    hooks_applied?: boolean;
    /**
     * True on every initialize reply from a CLI that honors `onFailure` on hook matchers. Absent on CLIs that predate the option, which ignore it (a failed callback set to "block" lets the action run), and from responders that do not run the host's hooks. A host that sets "block" must not go on without it; the TypeScript SDK refuses the session. It says nothing of this request's hooks: `hooks_applied` does, and the TypeScript SDK also refuses a first initialize that reads `hooks_applied: false` when a matcher sets "block".
     */
    hook_on_failure_supported?: boolean;



    /**
     * Whether every plugin this initialize listed is loaded: true when each one is among the plugins the process loaded at launch (from `plugins` under --await-initialize, or from --plugin-dir), so a re-sent initialize naming the launch set also reads true; false otherwise. The `plugins` field never loads anything after launch. Absent when the request listed no plugins, and on CLIs that predate the field (those never read `plugins`).
     */
    plugins_applied?: boolean;



    /**
     * Whether the `mcpServers` in this initialize are the set the process read at launch under --await-initialize, so a re-sent initialize naming the same set also reads true; false otherwise. True says they were taken as an --mcp-config item, not that each one connected: a server missing from system/init mcp_servers was not loaded. The field loads nothing after launch. Absent when the request named none, and on CLIs that predate the field, which never read `mcpServers`: a host that sent servers must treat absence as not applied.
     */
    mcp_servers_applied?: boolean;


    /**
     * What became of each entry of this initialize's sdkMcpServerManifests, keyed by sdk server name, for the entries whose name is in sdkMcpServers. 'parked': kept for the connect that follows this reply, which answers the server's MCP initialize and first tools/list from it (a later failure to replay shows up as live mcp_message frames, as when no entry was sent). 'already_connected': this CLI already had a live client for the server. 'protocol_version_mismatch': initializeResult.protocolVersion is not the version this CLI's client requests. 'malformed': the entry is not of the documented shape, reported whether or not manifests were honoured (every name in sdkMcpServers gets this when the field itself is not an object); or an honoured entry is past the limits this CLI sets on a live answer. 'not_honoured': the CLI did not use the entry: manifests are switched off in this CLI, this remote session is not an interactive Cowork chat started from claude.ai, the session service has not recently told this remote-session worker that only the account owning the session can send events to it, or the request reached such a worker other than over its session stream (nothing for the host to change in any of these cases); or this CLI had read as many tool lists as it allows in a minute (send it again later); or it came over the session stream without sdkMcpServerManifestsOrigin or on a frame too old to trust (the host's to fix). Absent when the request carried no sdkMcpServerManifests or named no sdkMcpServers, and on CLIs that predate the field.
     */
    sdk_mcp_manifests_parked?: Record<string, 'parked' | 'already_connected' | 'protocol_version_mismatch' | 'malformed' | 'not_honoured'>;




    /**
     * Claude Code version of the process that runs this session's turns (the same value its system/init carries). Absent on CLIs that predate the field, and when the responder is not that process and does not know its version.
     */
    claude_code_version?: string;
    fast_mode_state?: coreTypes.FastModeState;
    fast_mode_disabled_reason?: coreTypes.FastModeDisabledReason;














};

/**
 * Interrupts the currently running conversation turn.
 */
declare type SDKControlInterruptRequest = {
    subtype: 'interrupt';

    /**
     * When true, the interrupt also cancels every uuid-stamped main-thread command still in the queue or already dequeued for the imminent turn but not yet reachable by the abort (the first-command prewait window) — the same set the response would otherwise list under `still_queued`. Each is closed with a terminal 'cancelled' lifecycle and listed on the response's `cancelled` field. `still_queued` is then empty, except that a client driving a hosted session lists there what it can no longer recall (a send already in flight to that session, or the first prompt the session was created with) and, when the session's own sweep then cancels one of those or a send it had already delivered, follows up with a command_lifecycle 'cancelled' frame for it. (The isFoldInFlight guard cancel_async_message uses does not apply here: this request also aborts the running turn, so a fold-in-flight uuid is never delivered and is swept with the rest. A fold-in-flight uuid's queued_command attachment may already appear in the aborted turn's transcript if the abort landed after the fold's attachment yield — pre-existing leave-queued semantics; it never runs as its own turn.) In a hosted session, a note that the session server itself added as context (shouldQuery false) may stay: it starts no turn and is listed under neither field. Uuid-less commands (task notifications, other than a passive notice that a task was stopped or paused, which stays queued) still in the queue are also dequeued but cannot be listed; a uuid-less command already in the prewait window is unreachable by either cancel leg — the first-command prewait latch covers it (this request latches exactly like a plain interrupt; see still_queued): its turn starts aborted. When false or absent, queued commands survive the interrupt and are listed under `still_queued` — the interrupt_receipt_v1 contract is unchanged. A Stop-means-stop-everything client (a remote UI's Stop button) sets this true so one round-trip halts the session; a wrapper that wants per-uuid control leaves it false and follows up with cancel_async_message. Advertised by the `interrupt_cancel_queued_v1` capability on system/init; older CLIs ignore the field and behave as if false.
     */
    cancel_queued?: boolean;





};

/**
 * Result of an interrupt operation. Advertised by the interrupt_receipt_v1 capability on system/init; older CLIs send an empty success response with no still_queued field.
 */
export declare type SDKControlInterruptResponse = {
    /**
     * Uuids of async user messages that survive this interrupt: commands still in the queue, plus any batch already dequeued for the imminent turn but not yet reachable by the abort, plus any user message this process has read but not yet queued, from its own input stream (held, for instance, while a model change is still being checked or behind start-up work; a message a Remote Control client sent that is still being ingested is not listed). An interrupt — plain or cancel_queued:true — that lands during the FIRST-command prewait window (before the first turn of the session has armed a controller) is additionally LATCHED, scoped to the user-intent work pending at that instant — the batch already dequeued and parked for the imminent turn, plus the user-intent main-thread commands then in the queue or held ahead of it (the work this list enumerates): the first turn to arm that carries any of that doomed work starts already aborted, exactly once, so the listed prewait batch is delivered into an immediately-aborted turn, its frames and result flowing through the normal abort path, instead of running to completion. A turn carrying none of it arms live and leaves the latch waiting: a system delivery turn (for example a replayed host event), or a prompt enqueued after the interrupt — post-interrupt work is never coalesced with the doomed work and never dies to the latch, so the Stop kills exactly what this receipt listed. A worker of a cloud session may treat a plain interrupt from a person differently. If it reads the interrupt before its first turn, while it holds a prompt from the worker before it, the interrupt stops the turn of that prompt, and listed messages that no turn has started then run. The latch is released when the doomed work is retired without arming: if a parked prewait batch is entirely cancelled, the latch is released even when other queued commands remain (those arm and run normally); with nothing parked, it is released once none of the doomed commands remains queued or held — work enqueued after the interrupt neither holds it up nor is aborted by it. Survivors that ride any later turn run normally. These WILL run (subject to that latch) unless cancelled first (or unless the request set cancel_queued:true, in which case every uuid-stamped survivor this process holds (less a context note of the server that stays, see cancel_queued) is removed, emitted a terminal `cancelled` synchronously, and listed under `cancelled` instead — leaving here only what a client driving a hosted session can no longer recall: a send already in flight to that session, or the first prompt the session was created with; a send that client still holds on its own machine behind a send gate (it waits there until that session is ready to take it) has not gone out, so it is withdrawn and listed under `cancelled` like a queued one, and cancel_async_message can withdraw it too, while a plain interrupt leaves it held and lists it here). Cancellation granularity: uuids still in the queue are individually cancellable via cancel_async_message (the re-run of an interrupted turn that also answers for other client messages only if this interrupt was for it; see the response to that request); a listed uuid whose message the process running the session (never a client driving a hosted session) still keeps out of its queue, behind a model change or start-up work, is not yet cancellable that way: cancel_async_message answers cancelled:false for it and plants a cancel-pending mark, which the drain honours once the message is queued and the mid-turn fold of a running turn does not; once a batch is dequeued and coalesced into one turn, cancelling a NON-representative member uuid is a no-op (its content still runs), while cancelling the batch-representative uuid drops the WHOLE coalesced batch — in both cases the cancel response reports cancelled:false because the message was no longer in the queue. Coverage caveats: only uuid-STAMPED messages appear (a message enqueued without a uuid still runs but is never listed, so [] does not mean "nothing will run"); only main-thread messages are listed (subagent-addressed messages are out of scope); and the list may include internally-enqueued uuids the client never sent (cron triggers, auto-resume continuations) — ignore unknown uuids rather than treating them as an error. Ordering: on a clean interrupt this receipt is written before the interrupted turn result; a turn that crashes during interrupt handling emits its error result on a direct-write path that may precede the receipt. Snapshot is taken synchronously with abort processing — probing the queue after the interrupted result instead always loses the race against the drain loop, which starts the next queued turn immediately.
     */
    still_queued: string[];



    /**
     * Present only when the request set cancel_queued:true, with one exception that the last sentence names — uuids of main-thread commands cancelled by this interrupt: every survivor that would otherwise have appeared under `still_queued` (less a server's context note that stays, see cancel_queued), including any uuid that was mid-fold at the interrupt instant (this request also aborts, so the fold never delivers it). Each listed uuid has been removed (queue-resident), dropped before it was queued (a message this process had read and was still holding), or marked cancel-pending (the first-command prewait window, closed by the drain loop's backstop) and emits a terminal 'cancelled' lifecycle synchronously at the first such interrupt (a repeat interrupt over the same parked batch re-lists the uuid idempotently without re-emitting); none will run. Where one of them is the re-run of an interrupted turn that also answered for other client messages whose re-sent copies had been set aside for it, those messages' uuids are listed behind the commands' too: they were in no queue and never under `still_queued`, each has its terminal 'cancelled' lifecycle, and a repeat interrupt does not list them again. Same coverage caveats as `still_queued` (uuid-stamped main-thread only; internally-enqueued uuids may appear). Advertised by the `interrupt_cancel_queued_v1` capability. The exception, in a remote session and behind a flag: an interrupt with neither cancel_queued nor for_user_message_uuids, which no service wrote, also carries this field where it cancelled messages that the server had sent again and that this process held aside to run later; it then lists those alone, and no capability advertises it.
     */
    cancelled?: string[];
};

/**
 * Requests the worker's selectable model catalog. Fulfills the caps.modelCatalog capability: in a remote thin-client session the worker's provider, settings cascade, and enforcement policy decide which models the session can run, so the thin client must ask rather than read its own getModelOptions().
 */
declare type SDKControlListModelsRequest = {
    subtype: 'list_models';
};

/**
 * Requests the session's live permission rules and workspace directories — the same data /permissions lists in the terminal: rules from settings files plus session-only approvals, slash-command grants, and --allowedTools flag rules, each with its source. A connection that stores its answers cuts these: see `withheld` on the state.
 */
declare type SDKControlListPermissionRulesRequest = {
    subtype: 'list_permission_rules';
};

/**
 * Success payload of list_permission_rules.
 */
export declare type SDKControlListPermissionRulesResponse = {
    /**
     * The session's live permission rules state, as list_permission_rules reports it. Cut when `withheld` is true.
     */
    state: SDKControlPermissionRulesState;
};

/**
 * Invokes an MCP tool via the subprocess MCP client without a model turn. No permission check (control channel is trusted, same as other subtypes) unless check_permissions is set. In a cloud session, tools on the user's own computer or browser are rejected. SDK-type MCP servers (config.type === "sdk") are rejected — they are caller-provided, so the caller can invoke them directly without the subprocess round-trip. Result content passes through the same processing as model-turn MCP calls, unless result_not_for_model is set. Session expiry is not retried automatically; callers can mcp_reconnect and retry. UrlElicitationRequired (-32042) tries Elicitation hooks; if no hook resolves, the call errors with the URL in the message — open it out-of-band, then retry mcp_call. STAGED calls (input_files/output_files declared) additionally stage lane rows in/out around the call — see the input_files describe. Staged failures come back as a success-subtype response whose staging field carries a typed error_code; subtype:error is emitted only when the call could not be attempted at all (server not connected, kill switch, dispatch failure) and means nothing ran. A target server that is not yet connected is brought up on demand: dispatch runs the deferred plugin/MCP startup resolution (the work a first model turn would have done) and waits up to 30s — shortened by expires_at when that is sooner — for the server to connect before answering "MCP server not connected", so a dispatch that races plugin startup (e.g. after an idle-wake reattach) succeeds instead of failing until a turn runs. Standard RPC semantics: a redelivered request_id supersedes the in-flight run (it is aborted and its response suppressed — exactly one response per request_id); conversion is idempotent, so re-running is safe. Cancellable via control_cancel_request.
 */
declare type SDKControlMcpCallRequest = {
    subtype: 'mcp_call';
    /**
     * Fully-qualified MCP tool name, e.g. mcp__server__tool_name. Plugin-hosted servers are ordinary MCP servers here — e.g. mcp__plugin_documents_docs__doc_export (server names are normalized: non-[a-zA-Z0-9_-] becomes _).
     */
    tool: string;
    /**
     * Tool arguments. When input_files/output_files are declared, any string VALUE that exactly equals "{{in:NAME}}" or "{{out:NAME}}" (whole string, not a substring) is replaced with the worker-chosen absolute path of that named staged file before the call; a token naming no declared file fails the request with staging error_code=tool_error, and every declared output's "{{out:NAME}}" token must appear in arguments (the substituted path is the only way the tool learns where to write, so an unreferenced output fails the request before the tool runs). With no files declared — including expires_at/timeout_ms-only staged calls — passed through unchanged.
     */
    arguments?: Record<string, unknown>;
    /**
     * RFC3339 deadline, REQUIRED when output_files are declared (a stale buffered drain must not overwrite rows written since). Sending expires_at routes the call through the staging engine, same as timeout_ms — the response gains a staging result. UNDELIVERED requests buffer durably and drain after reattach; a drain past this instant is dropped with staging error_code=expired instead of executing stale. Once delivered to a live worker the request is acked immediately and never redelivered — a worker killed mid-run surfaces as a missing response (apply your own deadline), not a later drain. An unparseable value is treated as already expired (fail closed).
     */
    expires_at?: string;
    /**
     * Tool-execution timeout (staging and collection have their own transport timeouts); with check_permissions it also bounds hooks and the wait for an answer. Clamped to [1000, 600000]; default 120000. Sending timeout_ms routes the call through the staging engine — so it is always enforced when present and the response carries a staging result; omit it for a plain call. Staged calls are POSIX-worker-only: on a Windows worker any staged-field call fails with a typed staging refusal.
     */
    timeout_ms?: number;

    /**
     * The caller hands the result to a program (a host that renders it, a script), not to a model, and bounds it itself. content is then the server's own content blocks as MCP defines them (the MCP SDK drops members it does not define), not what a model turn would be handed: no image is resized or put in the Messages API's shape, nothing is saved under tool-results, no embedded resource is flattened, and text blocks beside structuredContent stay. They are untrusted third-party data: any mimeType, images neither re-encoded nor bounded in pixels, each block's annotations and _meta unfiltered. The size check that protects a model's context is skipped too: no count_tokens request (which uploads the result), no truncation, no note in place of the content. Instead a result over 10485760 characters (content with its base64, structuredContent and _meta together) fails though the tool ran: a plain call answers the error subtype, a staged call staging.error_code tool_error with the text in detail, before its outputs are collected. A legacy toolResult still comes back as a string. Does not route the call through the staging engine. Absent or false: as before. Honoured only for a host on this process's own pipes, not over a remote transport nor on a lane that redacts what it persists. Feature-detected as `mcp_call_result_not_for_model_v1` in system/init.capabilities and in the initialize response's capabilities; where it is not said, and by a CLI without it, the member is ignored.
     */
    result_not_for_model?: boolean;
    /**
     * The call is someone else's (a page a host renders), so it is decided as the model's own call to this tool is, except that a slash command's allowed-tools and connector card answers never allow it, even during a turn: permission rules under every spelling, the permission mode, requiresUserInteraction, managed settings, and PreToolUse and PostToolUse hooks, which see the arguments and the result. An ask reaches the host as a can_use_tool control request; where no host can answer, and in dontAsk or plan mode, it is refused. A refused call never reaches the server: on a plain call the error subtype, on a staged call staging error_code=tool_error, each with text starting 'The tool did not run: '. The other refusals of mcp_call come first and keep their own words. A PostToolUse hook's rewrite replaces content and drops structuredContent and _meta. The result stays out of the model's context. Only a CLI that says mcp_call_check_permissions_v1 honours this member: an older one ignores it and runs the tool with no check. Honoured only on the pipes of the host that spawned the process; elsewhere the call is refused. A value that is not a boolean is refused.
     */
    check_permissions?: boolean;
    /**
     * Declaring input_files or output_files makes this a STAGED call: rows are fetched from the synced-file lane into a private per-request temp dir the WORKER chooses (random, per-UID — the caller never sees or computes paths; it references files via tokens in arguments), the tool runs, and declared outputs are written back as lane rows (durable-at-ack PUT). The response then carries a `staging` result the caller switches on.
     */
    input_files?: {
        /**
         * Handle referenced from arguments as "{{in:NAME}}". Unique within the request.
         */
        name: string;
        /**
         * Synced-file lane row to stage, e.g. /working/.cowork/originals/a.docx. A missing row fails with staging error_code=input_missing; the etag actually staged is echoed back in staging.inputs_used.
         */
        lane_path: string;
    }[];
    output_files?: {
        /**
         * Handle referenced from arguments as "{{out:NAME}}" — the tool is told (via the substituted path) where to write; the worker collects from exactly that path. Unique within the request.
         */
        name: string;
        /**
         * Synced-file lane row to write, e.g. /working/report.cd. Unique within the request (two outputs on one row would self-conflict under CAS). Outputs over the 25 MiB lane cap fail with staging error_code=output_too_large.
         */
        lane_path: string;
        /**
         * Opaque lane etag the output row must still carry for the write to land (CAS). Omitted = unconditional last-writer-wins (an empty string is rejected, not treated as unconditional). A row that moved since fails that output with staging error_code=output_conflict and the requested bytes are not written. Redelivery of a completed CAS write re-runs and conflicts with its own prior write — treat output_conflict on a retry as possible-prior-success and reconcile by etag.
         */
        if_match?: string;
    }[];
};

/**
 * Carries one MCP JSON-RPC message for an SDK-hosted MCP server (one named in initialize.sdkMcpServers or added later with mcp_set_servers). Flows in both directions: the CLI sends it to the client to reach the in-process server, and the client sends it to the CLI to deliver that server's own messages. When the client answers, the success response carries the server's JSON-RPC reply under mcp_response; the CLI acknowledges a client-sent one with an empty success.
 */
declare type SDKControlMcpMessageRequest = {
    subtype: 'mcp_message';
    server_name: string;
    /**
     * A JSON-RPC 2.0 message as defined by the Model Context Protocol (request, notification, or response object).
     */
    message: JSONRPCMessage;
};

/**
 * Reads one MCP Apps (SEP-1865) UI resource — a `ui://` URI, typically the `_meta.ui.resourceUri` a tool declares — from a connected MCP server the CLI itself dialed, with `resources/read`, for a host that renders it. Read-only and no model turn. The reply is untrusted third-party content (HTML): render it sandboxed. SDK-type MCP servers (config.type === "sdk") are rejected — they are caller-provided, so the caller can read them directly. Errors name the cause: a non-ui:// URI, an unknown server, in a cloud session a server on the user's own computer or browser, a server that managed policy blocks, that is disabled or that the project has not approved (the refusals mcp_reconnect gives), a server that is not connected (failed, pending or needs-auth: send mcp_reconnect; a connected server, or one still listed from the discovery cache, is read through the same connect path a tool call takes), a response over the size limit, or the server's own resources/read error (over a transport that stores frames, one fixed sentence in its place). Refused on a lane that redacts what it persists (a Remote Control bridge worker, a tenant worker) and by the client of a cloud-hosted session. Advertised as `mcp_read_resource_v1` in system/init.capabilities.
 */
declare type SDKControlMcpReadResourceRequest = {
    subtype: 'mcp_read_resource';
    /**
     * Server name, as mcp_status reports it (not normalized).
     */
    serverName: string;
    /**
     * The resource to read. Must use the ui:// scheme; any other URI is refused.
     */
    uri: string;
};

/**
 * The server's resources/read result for an mcp_read_resource request.
 */
export declare type SDKControlMcpReadResourceResponse = {
    contents: {
        uri: string;
        mimeType?: string;
        text?: string;
        /**
         * Base64, for a binary item.
         */
        blob?: string;
        /**
         * The content item's own `_meta` as the server sent it (MCP Apps puts the resource's `ui.csp` and `ui.permissions` here), minus keys under the CLI-reserved `com.anthropic/` prefix and `io.modelcontextprotocol/files` download targets: from a claude.ai connector, one that holds the download service's one-time token (every such target while connector downloads or their removal are on); from a server on a cloud session's MCP route, every such target.
         */
        _meta?: Record<string, unknown>;
    }[];
};

/**
 * Reconnects a disconnected or failed MCP server.
 */
declare type SDKControlMcpReconnectRequest = {
    subtype: 'mcp_reconnect';
    serverName: string;
};

/**
 * Replaces the set of dynamically managed MCP servers.
 */
declare type SDKControlMcpSetServersRequest = {
    subtype: 'mcp_set_servers';
    servers: Record<string, coreTypes.McpServerConfigForProcessTransport>;




};

/**
 * Requests the current status of all MCP server connections.
 */
declare type SDKControlMcpStatusRequest = {
    subtype: 'mcp_status';
    /**
     * When true and the CLI writes to the session through CCR (a cloud session's worker, or a Remote Control worker), the success reply is published only to the clients attached at that moment, as a control_response marked live_only: true on the session's unsequenced event stream, and is not stored with the session's events; a cloud session's worker that does not advertise `mcp_status_no_config_v1` embeds each server's configuration (URLs, headers, OAuth settings) in its rows. Set it only if your client reads control_response frames from that stream; a reply sent while its stream is down is lost and the request must be sent again; a reply too large to send in full leaves out each server's `tools`, `serverInfo` and `capabilities` and sends only how many tools it has, and one still over the live size limit comes back as a live error instead. Error replies other than that size-limit error, and every reply from hosts that do not send live replies (stdio hosts, and CLIs older than this field), are ordinary stored replies, so a client that sets it must accept either.
     */
    liveReply?: boolean;
};

/**
 * Enables or disables an MCP server.
 */
declare type SDKControlMcpToggleRequest = {
    subtype: 'mcp_toggle';
    serverName: string;
    enabled: boolean;
};

/**
 * Requests permission to use a tool with the given input.
 */
declare type SDKControlPermissionRequest = {
    subtype: 'can_use_tool';
    tool_name: string;
    mcp_server?: coreTypes.McpServerProvenance;
    input: Record<string, unknown>;
    permission_suggestions?: coreTypes.PermissionUpdate[];
    blocked_path?: string;
    /**
     * Human-readable reason the ask escalated, for the consent line of the host's dialog. For decision_reason_type "subcommandResults" (compound bash), this is the NESTED safety check's warning text — the wrapper itself has no text — preferring a check that requires manual approval (classifier_approvable false); treat it with the same display/policy care as a "safetyCheck" reason. May carry ANSI escapes; sanitize before rendering.
     */
    decision_reason?: string;
    /**
     * Structured discriminator for why auto-mode escalated. Lets SDK hosts make policy (e.g. auto-deny safetyCheck) without parsing decision_reason text. For compound bash commands this is "subcommandResults" even when a safetyCheck is nested inside — check classifier_approvable for that case, and see decision_reason: for this variant it carries the nested safety check's warning text.
     */
    decision_reason_type?: 'rule' | 'mode' | 'subcommandResults' | 'permissionPromptTool' | 'hook' | 'asyncAgent' | 'sandboxOverride' | 'workingDir' | 'safetyCheck' | 'classifier' | 'other';







    /**
     * Set when a safetyCheck is present anywhere in the decision reason (including nested inside subcommandResults for compound bash). false = at least one safety check requires manual approval (e.g. Windows path bypass, dangerous rm); true = all safety checks MAY be classifier-approved (e.g. sensitive-file paths). Absent when no safetyCheck is involved.
     */
    classifier_approvable?: boolean;
    /**
     * True when the dialog must not offer the persistent "don't ask again" row for this ask: accepting it would write a whole-tool allow rule broader than the ask's own verb (PermissionAskDecision.suppressAlwaysAllowRule), or the ask comes from a run a plugin started, where Claude Code saves no rule from the answer, not even for the session. Hosts rendering approve options should omit any persistent-rule affordance when set.
     */
    suppress_always_allow_rule?: boolean;

    /**
     * True when the ask must not be approvable by a single stray keystroke (PermissionAskDecision.defaultToNo): a terminal-style prompt opens on its decline option and takes no digit shortcut. Hosts rendering approve options should not pre-select approve when set.
     */
    default_to_no?: boolean;
    /**
     * Set when a user-configured ask RULE (permissions.ask) forced this prompt but the ask carries the tool's own decision_reason — the ask-rule substitution keeps the richer tool-minted ask, so the rule rides here instead of decision_reason_type 'rule'. May also be set, whatever the decision_reason, when an ask rule reaches an MCP tool only under another name (such as a connector's id, its claude.ai name, or Artifact for the Artifacts server's tools), not under the name in tool_name: a host that looks for the rule by that name does not find it. Hosts making policy on decision_reason_type (e.g. auto-deny safetyCheck) or running host-side auto-approval should treat asks carrying this field as rule-forced: the user's stated intent is a human prompt. Values are producer-authored but render-unsafe like decision_reason; sanitize before display.
     */
    matched_ask_rule?: {
        source: string;
        tool_name: string;
        rule_content?: string;
    };
    title?: string;
    display_name?: string;
    tool_use_id: string;
    agent_id?: string;

    description?: string;
    /**
     * True when one-tap Approve/Deny must not be offered: the tool's approval card IS the user-interaction surface (Tool.requiresUserInteraction(): the user responds on the card itself), OR the pending ask is localDisplayOnly (its consent disclosure cannot ride this wire and only the local dialog renders it), OR the auto-mode classifier blocked the call and it was handed to a person (decision_reason_type 'classifier' on a person-only ask), which no stored grant or automatic approval may answer, OR a grant keyed on the tool name must not answer it: the MCP server's name spells a claude.ai connector's key and the server came from neither claude.ai nor whoever launched the session, or, while Claude Code enforces grants, two tools of the server get that name, OR the SDK host worded the ask (title and description are its consent copy, which a push cannot carry whole), OR the ask stands in for the classifier's verdict on a call to Claude Desktop's Cowork shell, which no stored grant or automatic approval may answer. In each of those cases the user has to open the session to answer. Also true on the prompt raised at auto mode's limit of blocks in a row when the launch environment sets CLAUDE_CODE_HOST_ALLOW_RESETS_DENIAL_STREAK and nothing else takes the request_id off the pending_action: its Allow starts that count over, so no stored grant or automatic approval may answer it. The worker's own pending_action keeps its request_id; a Remote Control bridge's push for it still opens the session.
     */
    requires_user_interaction?: boolean;





};

/**
 * The session's live permission rules state, as list_permission_rules reports it. Cut when `withheld` is true.
 */
export declare type SDKControlPermissionRulesState = {
    rules: SDKPermissionRuleEntry[];
    workspaceDirectories: SDKPermissionWorkspaceDirectory[];
    /**
     * The session's original working directory.
     */
    originalCwd: string;
    /**
     * True when enterprise managed settings pin allowManagedPermissionRulesOnly: the session applies policy rules only, and rules from other settings files appear with notInEffect set.
     */
    managedOnly: boolean;

    /**
     * Settings parse and validation errors, as get_settings reports them. When non-empty, the listed files were skipped — their rules are not in the session and not listed above.
     */
    errors?: coreTypes.SDKSettingsParseError[];
    /**
     * True when this answer was cut because the connection stores its answers (a cloud or self-hosted session): `rules` holds only rows from settings sources and `mcpServerPolicy`, `workspaceDirectories` only folders from settings sources, each entry of `errors` only a fixed `message` and an empty `path`, and `parentSettingsIncluded` is absent. Where session folders are withheld, `workspaceDirectories` is empty, `originalCwd` is an empty string, and each rule other than a bare tool name the session can send loses its `description` and goes as `Tool(withheld)`, or as `(withheld)` where its tool name cannot be sent. An `ask` or `deny` rule of that last kind goes as `*(withheld)`, so a client that matches rules by tool name treats it as covering every tool. Absent from an answer that was not cut.
     */
    withheld?: boolean;
};

/**
 * Read a file from the session filesystem for the remote sidebar viewer. Path is resolved against cwd by default and gated by the same read-permission rules as the Read tool.
 */
declare type SDKControlReadFileRequest = {
    subtype: 'read_file';
    path: string;
    max_bytes?: number;
    /**
     * How to encode the bytes in `contents`. Defaults to utf-8 (lossy for binary); pass 'base64' to read images.
     */
    encoding?: 'utf-8' | 'base64';




};

/**
 * File contents for the remote sidebar viewer.
 */
export declare type SDKControlReadFileResponse = {
    contents: string;
    absPath: string;
    truncated?: boolean;
    /**
     * Set when the request asked for base64. Absent means utf-8 — including when an older CLI ignored the request's encoding field.
     */
    encoding?: 'base64';
    /**
     * Present on every utf-8 answer. True when the bytes read were not all valid UTF-8, so `contents` has U+FFFD where bytes were replaced and is not the file's own text: a binary file, text in another encoding, or a read cut inside a character, at its end when `truncated` is set, or at its start when `offset` is set. False when `contents` is exactly the bytes read, decoded, even if the file itself contains U+FFFD. Absent on a base64 answer, which is exact, and from an older CLI or tool container: a client that sees neither this nor `encoding: 'base64'` cannot tell whether `contents` is exact.
     */
    lossy?: boolean;







};

/**
 * Add a directory as a working-directory root and optionally reload CLAUDE.md, skills, and plugins. The directory must resolve to a strict subdirectory of cwd, or of a directory passed at launch via --add-dir / the SDK additionalDirectories option. A directory that is already a registered working directory (including a duplicate of an earlier request) is denied with an error; the registration pipeline and DirectoryAdded hooks do not re-run.
 */
declare type SDKControlRegisterRepoRootRequest = {
    subtype: 'register_repo_root';
    directory: string;
    reload_claude_md?: boolean;
    reload_plugins?: boolean;
    reload_skills?: boolean;
};

/**
 * Re-reads the output-style directories from disk (a style file written mid-session is otherwise invisible until the next session) and returns the refreshed style names. Also drops the shared markdown-file scan cache, so agents, skills and routines re-read their directories on their next use.
 */
declare type SDKControlReloadOutputStylesRequest = {
    subtype: 'reload_output_styles';
};

/**
 * Refreshed output style names after reload, built-in and custom, in the order the initialize response lists them.
 */
export declare type SDKControlReloadOutputStylesResponse = {
    available_output_styles: string[];
};

/**
 * Reloads plugins from disk and returns the refreshed session components.
 */
declare type SDKControlReloadPluginsRequest = {
    subtype: 'reload_plugins';
    /**
     * When true, the reload is not applied if applying it would change the session's tool list while the conversation's prompt cache depends on that list (the same check the interactive /reload-plugins makes before it asks for --force): the response then carries held: true and cache_impact, and the session keeps its current plugins. Default false: apply unconditionally.
     */
    hold_on_cache_impact?: boolean;
    /**
     * Plugins for the reload to load as well, in the same shape as the SDK `plugins` option: each entry joins the session as one more --plugin-dir would (--plugin-dir-no-mcp when skipMcpDiscovery is set). Plugins already loaded stay; nothing is removed. A held or failed reload adds none of them. Refused for a malformed list or a path that is not absolute, when managed settings set disableSideloadFlags, on a connection whose frames persist server-side (any Remote Control or cloud worker), in a cloud-hosted session, and when a running sandbox cannot keep shell commands out of the folders (always on Windows).
     */
    add_plugins?: coreTypes.SdkPluginConfig[];
    /**
     * When true, a request that finds the session busy reloads nothing and gets an error whose error_code is reload_plugins_busy; ask again once the session is idle. Busy: a turn is running or still ending, a message is queued for one, a permission prompt taken over from an earlier process is unanswered, background work that keeps the session at running (an agent, a workflow and the like) is live, or an in-process teammate is at work; a session that only waits for a background shell command is not busy. For a host whose request can arrive late, such as one that reaches the session over SSH: a reload changes the commands, agents, hooks and servers under a running turn, agent or teammate. Default false: the request is served in a turn too. Only `claude -p` reads it, and says so in system/init.capabilities (reload_plugins_refuse_if_busy_v1) to a host on its pipes; a CLI that does not say so may ignore the field.
     */
    refuse_if_busy?: boolean;
};

/**
 * Refreshed commands, agents, plugins, and MCP server status after reload.
 */
export declare type SDKControlReloadPluginsResponse = {
    commands: coreTypes.SlashCommand[];
    agents: coreTypes.AgentInfo[];
    plugins: {
        name: string;
        path: string;
        source?: string;
        /**
         * The plugin's version as declared in its plugin.json manifest, emitted verbatim (plugin-author-controlled — validate before trusting). Omitted when the manifest declares no version.
         */
        version?: string;
    }[];
    mcpServers: coreTypes.McpServerStatus[];
    error_count: number;
    /**
     * Present only when the request asked to hold on cache impact and this CLI ran the check. True: the reload was not applied, the lists above describe the session as it still is, and cache_impact says what applying would change. False: the check found no impact and the reload was applied. Absent: the request did not ask, or the CLI predates the option and applied the reload unchecked.
     */
    held?: boolean;
    /**
     * What applying the held reload would change in the session's tool list: plugin MCP servers it would register or drop (scoped plugin:<plugin>:<server> names, plugin-authored — validate before showing) and whether it would add or remove the LSP tool (the may- forms mean the preview could not fully see the pending plugin set). Present only with held: true.
     */
    cache_impact?: {
        mcp_servers_added: string[];
        mcp_servers_removed: string[];
        lsp_tool_change: ('adds' | 'may-add' | 'removes' | 'may-remove') | null;
    };
};

/**
 * Reloads skills from disk and returns the refreshed skill list.
 */
declare type SDKControlReloadSkillsRequest = {
    subtype: 'reload_skills';
};

/**
 * Refreshed skill commands after reload.
 */
export declare type SDKControlReloadSkillsResponse = {
    skills: coreTypes.SlashCommand[];
};

/**
 * Sets the user-facing title for the current session.
 */
declare type SDKControlRenameSessionRequest = {
    subtype: 'rename_session';
    title: string;
    /**
     * Who chose the title: 'remote' (the default) for a rename made on claude.ai and relayed to this process, 'host' for one the user made in the hosting application (an IDE), which the CLI counts as a user rename.
     */
    source?: 'remote' | 'host';
    /**
     * The session the title is for. When given and this process has since moved to another session (/clear, an in-session resume), the request is refused instead of naming the new session.
     */
    session_id?: string;

};

/**
 * Envelope for a control-protocol request, sent by either side on the same stream as the messages. The receiver normally answers with exactly one control_response carrying the same request_id (a few request types document when no answer is sent), and a requester ignores responses for request_ids it is not waiting on. Each request type's own documentation says which side sends it and what its success response carries.
 */
export declare type SDKControlRequest = {
    type: 'control_request';
    /**
     * Chosen by the sender, unique among its in-flight requests; the control_response (and any control_cancel_request) for this request echoes it.
     */
    request_id: string;
    request: SDKControlRequestInner;


};

declare type SDKControlRequestInner = SDKControlInterruptRequest | SDKControlPermissionRequest | SDKControlInitializeRequest | SDKControlSetPermissionModeRequest | SDKControlSetModelRequest | SDKControlSetMaxThinkingTokensRequest | SDKControlRenameSessionRequest | SDKControlSetColorRequest | SDKControlMcpStatusRequest | SDKControlGetContextUsageRequest | SDKControlGetSessionCostRequest | SDKControlListModelsRequest | SDKControlGetUsageRequest | SDKControlGetBinaryVersionRequest | SDKControlMcpCallRequest | SDKControlFileSuggestionsRequest | SDKHookCallbackRequest | SDKControlMcpMessageRequest | SDKControlRewindFilesRequest | SDKControlCancelAsyncMessageRequest | SDKControlReadFileRequest | SDKControlSeedReadStateRequest | SDKControlMcpSetServersRequest | SDKControlRegisterRepoRootRequest | SDKControlReloadPluginsRequest | SDKControlReloadSkillsRequest | SDKControlReloadOutputStylesRequest | SDKControlMcpReconnectRequest | SDKControlMcpToggleRequest | SDKControlSetHasSubscribersRequest | SDKControlStopTaskRequest | SDKControlBackgroundTasksRequest | SDKControlGetTaskOutputRequest | SDKControlApplyFlagSettingsRequest | SDKControlGetSettingsRequest | SDKControlGetHooksListingRequest | SDKControlUpdateSettingsRequest | SDKControlElicitationRequest | SDKControlRequestUserDialogRequest | SDKControlListPermissionRulesRequest | SDKControlMcpReadResourceRequest;

/**
 * Progress for a long-running client-originated control_request (currently only side_question), correlated by request_id. status 'started' means the worker accepted the request and launched the work; 'api_retry' carries the same retry counters as SDKAPIRetryMessage and is present only for that status.
 */
export declare type SDKControlRequestProgressMessage = {
    type: 'system';
    subtype: 'control_request_progress';
    /**
     * request_id of the in-flight control_request this progress belongs to.
     */
    request_id: string;
    status: 'started' | 'api_retry';
    attempt?: number;
    max_retries?: number;
    retry_delay_ms?: number;
    error_status?: number | null;
    uuid: UUID;
    session_id: string;
};

/**
 * Requests the SDK consumer to render a tool-driven blocking dialog and return the user choice. Used by tools that previously rendered Ink JSX via setToolJSX with an onDone callback.
 */
declare type SDKControlRequestUserDialogRequest = {
    subtype: 'request_user_dialog';
    /**
     * Identifier for the dialog the host should render. Open string union — new kinds may be added without bumping the protocol. A kind is only sent in sessions where some attached client declared it in initialize.supportedDialogKinds (declare exactly the kinds you can render); on multi-client transports the request still reaches every attached client. A host that receives a kind it did not declare must not answer it (an error-subtype response is discarded and the dialog stays pending) — never with {behavior: "cancelled"}, which is a real settlement treated as the user dismissing the dialog. An unanswered dialog is cancelled by the CLI after its dialog deadline; the CLI may send one that has no deadline, which stays up until it is answered or the CLI withdraws it with a control_cancel_request.
     */
    dialog_kind: string;
    /**
     * Dialog-specific data passed to the host renderer. Shape is defined per dialog_kind; the protocol transports it opaquely.
     */
    payload: Record<string, unknown>;
    tool_use_id?: string;
};

/**
 * Envelope for the single reply to a control_request, sent by whichever side received the request.
 */
export declare type SDKControlResponse = {
    type: 'control_response';
    response: ControlResponse | ControlErrorResponse;



};

/**
 * Rewinds file changes made since a specific user message.
 */
declare type SDKControlRewindFilesRequest = {
    subtype: 'rewind_files';
    user_message_id: string;
    dry_run?: boolean;
};

/**
 * Seeds the readFileState cache with a path+mtime entry. Use when a prior Read was removed from context so Edit validation would fail despite the client having observed the Read. The mtime lets the CLI detect if the file changed since the seeded Read — same staleness check as the normal path.
 */
declare type SDKControlSeedReadStateRequest = {
    subtype: 'seed_read_state';
    path: string;
    mtime: number;
};

/**
 * Sets the session accent color. Accepts an agent color name or "default" to reset.
 */
declare type SDKControlSetColorRequest = {
    subtype: 'set_color';
    color: string;
};

/**
 * Tells the CLI whether anybody is watching the output that the host reads from stream-json stdout and passes on. It matters only in a CLI started with CLAUDE_CODE_STREAM_EVENT_HOLD_MS, which holds most content_block_delta and thinking_tokens lines on stdout to join them, and with CLAUDE_CODE_STREAM_EVENT_NO_SUBSCRIBER_HOLD_MS: after false, each new wait of that hold lasts the second variable's time, if longer; after true or null, the first variable's time again. No line is dropped. The reply is an empty success, also where nothing changes, and like any other line it comes after the lines held so far, so each request ends the wait that is running: send one only when the answer changes, not after each message from your server. A new CLI process starts as watched, so send the answer again to each new process. An older CLI answers with the unsupported-subtype error, and a CLI that drives a cloud-hosted session refuses the request.
 */
declare type SDKControlSetHasSubscribersRequest = {
    subtype: 'set_has_subscribers';
    /**
     * false: nobody watches now. true: somebody does. null: the host does not know, which counts as true.
     */
    has_subscribers: boolean | null;
};

/**
 * Sets the maximum number of thinking tokens for extended thinking. When max_thinking_tokens is null, thinking resets to the session default: any mid-session budget override is cleared (back to the spawn-time budget, if one was set), and thinking stays off for sessions that have it disabled. When max_thinking_tokens is omitted, the budget is left as it is, so a request that only changes thinking_display can leave the field out. thinking_display optionally sets the thinking display mode for the rest of the session: a value replaces the session display mode, null clears that override so Claude Code's default display handling applies again, and when omitted the display mode from session start (--thinking-display) is kept. 'highlights' returns one short title per stretch of thinking instead of a prose summary. The API accepts it only from Claude Code sessions that Anthropic hosts; if the API rejects it, the session sends 'omitted' (no thinking text) in its place from then on. A request for 'highlights' gets an error reply after such a rejection, when experimental betas are off (CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS or organization policy), on a Claude 3 model (except on Microsoft Foundry), or on Amazon Bedrock (Mantle included), Google Vertex AI or a Claude apps gateway (API provider "gateway") with a model released before Claude Opus 4.7. The error names which of these it was; the display stays as it was, and max_thinking_tokens still applies when the request has it.
 */
declare type SDKControlSetMaxThinkingTokensRequest = {
    subtype: 'set_max_thinking_tokens';
    max_thinking_tokens?: number | null;
    thinking_display?: ('summarized' | 'omitted' | 'highlights') | null;
};

/**
 * Sets the model to use for subsequent conversation turns.
 */
declare type SDKControlSetModelRequest = {
    subtype: 'set_model';
    /**
     * Model to switch to. Omitted, null, or 'default' resets to the session default model.
     */
    model?: string | null;


};

/**
 * Sets the permission mode for tool execution handling.
 */
declare type SDKControlSetPermissionModeRequest = {
    subtype: 'set_permission_mode';
    /**
     * Permission mode for controlling how tool executions are handled. 'default' - Standard behavior, prompts for dangerous operations. 'acceptEdits' - Auto-accept file edit operations. 'bypassPermissions' - Bypass all permission checks (requires allowDangerouslySkipPermissions). 'plan' - Planning mode, no actual tool execution. 'dontAsk' - Don't prompt for permissions, deny if not pre-approved. 'auto' - Use a model classifier to approve/deny permission prompts.
     */
    mode: coreTypes.PermissionMode;



};

/**
 * Stops a running task.
 */
declare type SDKControlStopTaskRequest = {
    subtype: 'stop_task';
    task_id: string;
};

/**
 * Writes settings through the CLI's own writer. For localSettings, merges the given keys into the project's local settings file (canonical store root, gitignore upkeep, hardened write) and live-applies them — the same path /config uses; allowlist: outputStyle. For userSettings, takes effortLevel only and saves it as the default for the session's current model, under modelSettings as /effort saves it ('max' is session-only and is not written; the running session's level is not set here — send apply_flag_settings for that). Unlike apply_flag_settings, which only touches the session-scoped flag layer. Each file feeds hook and permission-rule loading, so each allowed key is a security decision. String values only (key deletion is not supported); refused on remote transports and in sessions whose --setting-sources exclude the target source.
 */
declare type SDKControlUpdateSettingsRequest = {
    subtype: 'update_settings';
    /**
     * Which settings file to write: the project's local settings file, where /config's writes land, or the user's settings file, which takes effortLevel only.
     */
    source: 'localSettings' | 'userSettings';
    settings: Record<string, unknown>;
};

/**
 * Emitted by /clear, plan-mode exit, fresh-session, and onboarding flows. The surface should mount a fresh transcript under new_conversation_id and reset any cached session title. From internal QueryEvent 'conversation_reset'.
 */
export declare type SDKConversationResetMessage = {
    type: 'conversation_reset';
    new_conversation_id: UUID;
    uuid: UUID;
    session_id: string;
    /**
     * What discarded the conversation: 'clear' is the /clear command (or its /reset and /new aliases), 'plan_mode_exit' is leaving plan mode with the clear-context option, 'fresh_session' is a flow that starts a fresh session to implement an approved plan, 'onboarding' is an onboarding flow re-run inside an existing session. Informational: a consumer should reset on every conversation_reset frame whatever this says, and treat an absent (older emitter) or unrecognized value as an unspecified reset.
     */
    trigger?: 'clear' | 'plan_mode_exit' | 'fresh_session' | 'onboarding';
    /**
     * Only with trigger 'clear': the uuid of the user message whose /clear was executed (the client's own uuid for that message when it came from a Remote Control or stream-json client, otherwise the uuid the CLI assigned to the typed command). Lets a consumer match this frame to a /clear message it has already seen, wiping once whichever arrives first, instead of relying on arrival order. Absent for the other triggers, when that uuid is not a canonical UUID, and from older emitters.
     */
    user_message_uuid?: string;

    /**
     * When the reset happened, as an ISO 8601 string in UTC read from the clock of the process that performed it. Meant for display, such as the time on a "conversation cleared" row, not for ordering frames. Absent from older emitters; a consumer can fall back to the time it received the frame.
     */
    timestamp?: string;
};

export declare type SDKDeferredToolUse = {
    id: string;
    name: string;
    input: Record<string, unknown>;
};

/**
 * Emitted when an MCP server confirms that a URL-mode elicitation is complete.
 */
export declare type SDKElicitationCompleteMessage = {
    type: 'system';
    subtype: 'elicitation_complete';
    mcp_server_name: string;
    elicitation_id: string;
    uuid: UUID;
    session_id: string;
};

export declare type SDKFilesPersistedEvent = {
    type: 'system';
    subtype: 'files_persisted';
    files: {
        filename: string;
        file_id: string;
    }[];
    failed: {
        filename: string;
        error: string;
    }[];
    processed_at: string;
    uuid: UUID;
    session_id: string;
};

/**
 * Configuration for matching and routing hook callbacks.
 */
declare type SDKHookCallbackMatcher = {
    matcher?: string;
    /**
     * Opaque ids chosen by the client, one per hook function it registered for this matcher. When the hook fires the CLI sends a hook_callback control request carrying one of these ids as callback_id; the client maps it back to its function.
     */
    hookCallbackIds: string[];
    timeout?: number;
    /**
     * What a failure of these callbacks does: the client answered the hook_callback request with an error, or with an answer that fails validation. 'continue' (default): the failure is reported and the action goes ahead. 'block': the failure counts as a block, as it does for a command hook, so the action the event guards (a tool call, a permission request, a prompt) is blocked. Ignored on Stop, SubagentStop, TaskCompleted and TeammateIdle.
     */
    onFailure?: 'continue' | 'block';



};

/**
 * Delivers a hook callback with its input data.
 */
declare type SDKHookCallbackRequest = {
    subtype: 'hook_callback';
    callback_id: string;
    input: coreTypes.HookInput;
    tool_use_id?: string;


};

export declare type SDKHookProgressMessage = {
    type: 'system';
    subtype: 'hook_progress';
    hook_id: string;
    hook_name: string;
    hook_event: string;
    stdout: string;
    stderr: string;
    output: string;

    uuid: UUID;
    session_id: string;
};

export declare type SDKHookResponseMessage = {
    type: 'system';
    subtype: 'hook_response';
    hook_id: string;
    hook_name: string;
    hook_event: string;
    output: string;
    stdout: string;
    stderr: string;
    exit_code?: number;
    outcome: 'success' | 'error' | 'cancelled';
    uuid: UUID;
    session_id: string;
};

export declare type SDKHookStartedMessage = {
    type: 'system';
    subtype: 'hook_started';
    hook_id: string;
    hook_name: string;
    hook_event: string;



    uuid: UUID;
    session_id: string;
};

/**
 * Generic text banner emitted by the loop — non-error status lines, hook feedback (e.g. a UserPromptSubmit hook's block reason), slash-command output. Hosts render `content` as plaintext at the given level.
 */
export declare type SDKInformationalMessage = {
    type: 'system';
    subtype: 'informational';
    content: string;
    /**
     * Render level. 'info' shows only in transcript mode; 'notice' renders in inactive gray; 'suggestion' and 'warning' are more prominent.
     */
    level: 'info' | 'notice' | 'suggestion' | 'warning';
    /**
     * Dedupes progress messages for the same tool use.
     */
    tool_use_id?: string;
    /**
     * When true, execution stops after this message (e.g. a Stop hook denied continuation).
     */
    prevent_continuation?: boolean;
    /**
     * Opaque feature tag on a line a host may treat specially; absent on ordinary lines. Hosts ignore values they do not know.
     */
    tag?: string;





    uuid: UUID;
    session_id: string;
};

/**
 * Liveness heartbeat. Either side may send it at any time (the CLI emits it periodically, for example while a long-running control request is in progress); receivers must ignore it. It has no payload. One use is not part of this schema: for startup() and prewarm() of the Agent SDK, which set CLAUDE_CODE_SDK_READS_STARTUP_MARKS, the CLI writes lines of this type with a `startup_mark` field, the name of a start-up checkpoint that it has passed, before the initialize response.
 */
declare type SDKKeepAliveMessage = {
    type: 'keep_alive';
};

/**
 * Output from a local slash command (e.g. /voice, /usage). Displayed as assistant-style text in the transcript.
 */
export declare type SDKLocalCommandOutputMessage = {
    type: 'system';
    subtype: 'local_command_output';
    content: string;
    uuid: UUID;
    session_id: string;
};

export declare type SDKMcpResourceLink = {
    uri: string;
    name: string;
    title?: string;
    description?: string;
    mimeType?: string;
    size?: number;
    annotations?: Record<string, unknown>;
};

/**
 * MCP tool definition for SDK servers.
 * Contains a handler function, so not serializable.
 * Supports both Zod 3 and Zod 4 schemas.
 */
export declare type SdkMcpToolDefinition<Schema extends AnyZodRawShape = AnyZodRawShape> = {
    name: string;
    description: string;
    inputSchema: Schema;
    annotations?: ToolAnnotations;
    _meta?: Record<string, unknown>;
    handler: (args: InferShape<Schema>, extra: unknown) => Promise<CallToolResult>;
};

/**
 * Emitted when the memory recall supervisor surfaces relevant memories into the turn. Mirrors the CLI relevant_memories attachment so SDK renderers can show "Recalled from memory" inline.
 */
export declare type SDKMemoryRecallMessage = {
    type: 'system';
    subtype: 'memory_recall';
    /**
     * How memories were surfaced: 'select' returns full file bodies chosen by the parallel selector; 'synthesize' returns a Sonnet-authored paragraph distilled from many tiny memories.
     */
    mode: 'select' | 'synthesize';
    memories: {
        /**
         * Absolute path to the memory file, a synthesis sentinel of the form `<synthesis:DIR>` when mode is 'synthesize', or an https URL when scope is 'organization'.
         */
        path: string;
        scope: 'personal' | 'team' | 'organization';
        /**
         * The surfaced memory body. Always present for 'synthesize' mode and 'organization' scope (neither has an on-disk path to lazy-load from); absent for file-backed 'select' entries (renderers lazy-load from path).
         */
        content?: string;
    }[];
    uuid: UUID;
    session_id: string;
};

/**
 * Every conversational and informational message the CLI emits on its output stream, discriminated by type (and subtype for system/result messages). Consumers should ignore types and subtypes they do not recognize: the set grows over time.
 */
export declare type SDKMessage = SDKAssistantMessage | SDKUserMessage | SDKUserMessageReplay | SDKResultMessage | SDKSystemMessage | SDKPartialAssistantMessage | SDKCompactBoundaryMessage | SDKStatusMessage | SDKAPIRetryMessage | SDKControlRequestProgressMessage | SDKModelRefusalFallbackMessage | SDKModelRefusalNoFallbackMessage | SDKLocalCommandOutputMessage | SDKHookStartedMessage | SDKHookProgressMessage | SDKHookResponseMessage | SDKPluginInstallMessage | SDKToolProgressMessage | SDKAuthStatusMessage | SDKTaskNotificationMessage | SDKTaskStartedMessage | SDKTaskUpdatedMessage | SDKTaskProgressMessage | SDKBackgroundTasksChangedMessage | SDKThinkingTokensMessage | SDKSessionStateChangedMessage | SDKWorkerShuttingDownMessage | SDKCommandsChangedMessage | SDKNotificationMessage | SDKFilesPersistedEvent | SDKToolUseSummaryMessage | SDKMemoryRecallMessage | SDKRateLimitEvent | SDKElicitationCompleteMessage | SDKPermissionDeniedMessage | SDKPromptSuggestionMessage | SDKMirrorErrorMessage | SDKInformationalMessage | SDKConversationResetMessage | SDKSessionWritesLostMessage;

/**
 * Provenance of a user-role message (peer session, team lead, channel). A host wrapping keyboard input must stamp {kind:'human'} explicitly — absent origin is treated as unattributed and fails closed at strict isHuman() trust gates.
 */
export declare type SDKMessageOrigin = {
    kind: 'human';
} | {
    kind: 'channel';
    server: string;
} | {
    kind: 'peer';
    from: string;
    /**
     * The SENDING session's permission class as declared by the host that injects this message on local stdin ('bypass' for sessions that run tools without asking, 'prompting' otherwise). Lets the recipient deliver a same-class message immediately while a cross-class or undeclared sender is still held at a recipient that runs without asking. Honored only from the injecting host on local stdin; absent when the host does not declare it.
     */
    fromMode?: 'bypass' | 'prompting';
    /**
     * Sender display name, normalized by the harness: Unicode control, format, surrogate, and line/paragraph-separator code points stripped (categories Cc/Cf/Cs/Zl/Zp — covers bidi controls, zero-width characters, and tag characters), trimmed, at most 64 code points (+ ellipsis, never splitting a surrogate pair). Sender-asserted display text (the addressable identity is `from`) — render it as reported speech, but no client-side character sanitization is needed. Absent when the wire is not exactly one harness-formed envelope and on messages from older senders.
     */
    name?: string;
    /**
     * The sender's host-openable session id (the envelope's `from-session` attribute — e.g. a desktop `local_<uuid>` or a cloud session `session_`/`ses_` id), set by the sender's host so a receiving UI can link this message back to the sending session. Sender-asserted like `from`: a navigation target only, never authority. Absent when the sender's host provides none and on messages from older senders.
     */
    fromSession?: string;

    /**
     * Task id of the in-process background subagent that sent this message, stamped by the harness from the sending loop (never from tool input). Absent for cross-session peers.
     */
    senderTaskId?: string;
    /**
     * Decoded message body with the peer envelope stripped — byte-exact with what the model sees. Present only when the turn is exactly one harness-formed envelope (or an in-process agent message), or when Claude Desktop declares it and the message text holds those exact bytes; render this instead of re-parsing the message text.
     */
    body?: string;
    /**
     * Kernel-verified pid of the process that connected to this session's cross-session messaging socket, read from the connection (SO_PEERCRED / LOCAL_PEERPID) — never from the payload. This identifies the CONNECTING process, which for relayed traffic (e.g. a daemon forwarding on another session's behalf) is the relay, not the message's author. Key sender identity on this, never on `from`: `from` is sender-authored and kept only for reply routing, so it is forgeable by any same-user process. Absent when unverifiable (Windows, non-UDS ingress) — never a wrong value. Pids are recyclable: provenance, not an authentication token.
     */
    verifiedPeerPid?: number;






} | {
    kind: 'task-notification';
    /**
     * Present when the delivery is the fired stored prompt of a scheduled task ('scheduled-trigger', stamped from server-asserted provenance, or declared by a local host for its own scheduled runs; the schedule attests storage, not authorship), the server's own notice of an event outside the session ('external-event', such as a webhook's; stamped only from server-asserted provenance, with the framing and authority of a delivery with no subkind; the text can quote a third party) or a coordinator co-member SendMessage delivery ('peer-send-message': model-authored text from another of the same user's sessions, verified by the server-stamped receiver co-membership — task-notification for prompt authority, but distinguishable so the receive-side crossSessionInbound setting can apply to it). The harness frames a scheduled-trigger delivery as the session's assigned task instead of the generic background-notification frame. Absent on plugin and background-event deliveries, and can be absent on webhook and PR-steward deliveries.
     */
    subkind?: 'scheduled-trigger' | 'peer-send-message' | 'projects-relay' | 'session-inbox' | 'external-event';
    /**
     * On a 'scheduled-trigger' delivery, why it fired: a short lowercase token such as 'scheduled', 'manual', 'retry', 'catch_up' or 'api'. Set by the server for cloud scheduled tasks, or declared by a local host for its own scheduled runs, which is honored only in a process the host started with CLAUDE_CODE_HOST_SCHEDULED_RUN=1 (a local host's value is kept only if it is 1 to 32 lowercase letters or underscores); absent when neither sent one.
     */
    fireReason?: string;

    /**
     * On a background task's own notification: the run_id its task_* events carried, as of when the notification was queued. Not part of the text the model reads.
     */
    runId?: string;

} | {
    kind: 'coordinator';
} | {
    kind: 'unclassified';
} | {
    kind: 'observer';
    from: string;
    senderTaskId: string;
} | {
    kind: 'auto-continuation';
} | {
    kind: 'observer-activity';
};

/**
 * Emitted when SessionStore.append() rejects or times out for a transcript-mirror batch after bounded retry (3 attempts with short backoff; timeouts are not retried). The batch is then dropped; this surfaces the failure so consumers are not silent on data loss.
 */
export declare type SDKMirrorErrorMessage = {
    type: 'system';
    subtype: 'mirror_error';
    error: string;
    key: {
        projectKey: string;
        sessionId: string;
        subpath?: string;
    };
    uuid: UUID;
    session_id: string;
};

/**
 * Emitted when the primary model ends the stream with stop_reason "refusal" and the turn is retried once on a fallback model (direction: "retry"). When `scope` is "session" (or absent — older CLIs), the swap is made persistent for the session; when `scope` is "local", only that subagent/side-question response came from the fallback model and the session model is unchanged. "revert" and "sticky" are retained in the enum for SDK-consumer compat and are no longer emitted.
 */
export declare type SDKModelRefusalFallbackMessage = {
    type: 'system';
    subtype: 'model_refusal_fallback';
    trigger: 'refusal';
    direction: 'retry' | 'revert' | 'sticky';
    /**
     * 'session': the main thread fell back and the session model is swapped. 'local': a subagent / side-question (/btw) / background fork fell back — only that response came from the fallback model and the session model is unchanged. Absent from older CLIs (treat as 'session').
     */
    scope?: 'session' | 'local';
    original_model: string;
    fallback_model: string;
    request_id: string | null;
    /**
     * The refusal category ('cyber', 'bio', …): stop_details.category from the refused API response (client lane), or the fallback block's server-gated trigger.category (server lane). Open string — new categories ship on the wire ahead of schema updates. null when neither source carried a category (normal, not an error). Absent when emitted by an older CLI.
     */
    api_refusal_category?: string | null;

    /**
     * stop_details.explanation from the refused API response (client lane only — the server-lane trigger carries no explanation). Unstable human prose — display only, never parse. null/absent when the response carried none, and always null on server-lane banners.
     */
    api_refusal_explanation?: string | null;

    /**
     * Wire uuids of the messages this fallback retracted — the refused partial as the consumer received it (one uuid per normalized SDK message; multi-block messages carry per-block derived uuids) plus any tombstoned tool_results. Emitted AFTER the retraction, so this is a resolution-time eviction signal: remove these messages from transcript state on receipt. Eviction is idempotent — unknown or already-removed uuids are a no-op. Absent when emitted by an older CLI.
     */
    retracted_message_uuids?: string[];
    /**
     * UUID of the user message the refused request was for — the rewind target and composer prefill for edit-and-retry. This is the message's own uuid as delivered on the replay ack (not a per-block normalized uuid). null when the refused turn was not human-authored (e.g. a background task notification or auto-continuation — nothing to edit-and-retry) or otherwise cannot be identified; absent from older CLIs.
     */
    refused_user_message_uuid?: string | null;
    content: string;
    uuid: UUID;
    session_id: string;
};

/**
 * Emitted when the model ends the stream with stop_reason "refusal" and no retry runs: no fallback model is configured, or per-category routing declined the retry (the mapped fallback target is unresolvable, or CLAUDE_CODE_REFUSAL_FALLBACK_CATCH_ALL is explicitly disabled and the refusal category has no fallback map entry). The structured counterpart to detecting stop_reason "refusal" on the assistant error frame. Not emitted when the retry ran or the user declined the retry dialog (model_refusal_fallback covers the retry case). Absent from older CLIs.
 */
export declare type SDKModelRefusalNoFallbackMessage = {
    type: 'system';
    subtype: 'model_refusal_no_fallback';
    original_model: string;
    request_id: string | null;
    api_refusal_category?: string | null;
    api_refusal_explanation?: string | null;
    refused_user_message_uuid?: string | null;
    content: string;
    uuid: UUID;
    session_id: string;
};

/**
 * Loop-side text notification. Mirrors the interactive REPL notification queue (key/priority/timeout). JSX notifications are not emitted on this channel.
 */
export declare type SDKNotificationMessage = {
    type: 'system';
    subtype: 'notification';
    key: string;
    text: string;
    priority: 'low' | 'medium' | 'high' | 'immediate';
    color?: string;
    timeout_ms?: number;
    uuid: UUID;
    session_id: string;
};

/**
 * An incremental streaming event for the assistant message being generated, emitted only when partial messages are requested (--include-partial-messages). The complete assistant message still follows as its own message.
 */
export declare type SDKPartialAssistantMessage = {
    type: 'stream_event';
    /**
     * One Anthropic Messages API streaming event (message_start, content_block_start, content_block_delta, content_block_stop, message_delta, message_stop) as defined for the streaming Messages API.
     */
    event: BetaRawMessageStreamEvent;
    parent_tool_use_id: string | null;
    uuid: UUID;
    session_id: string;
    ttft_ms?: number;




    /**
     * Client uuid of the user message this turn is answering (submitMessage options.uuid), stamped on a non-ping stream event each time that send changes: the turn's FIRST non-ping stream event (normally the frame that triggers the turn's initial ack), and, for a turn started by a synthetic (meta) prompt, the first non-ping stream event after each queued user message folded in mid-turn takes the echo over (see SDKAssistantMessage.user_message_uuid for the rule) — so a consumer can bind the reply stream to the send it answers without waiting for the result. A turn started by a typed prompt stamps only its first non-ping stream event; independently, its first complete assistant message is stamped as well (see SDKAssistantMessage.user_message_uuid), so the same uuid may appear on both. Absent on every other stream event of the turn, on turns that neither had a client uuid nor folded a user message in, and from older producers.
     */
    user_message_uuid?: string;
    /**
     * Client uuids of every user message whose prompt this turn has consumed so far, in consumption order — all members of a prompt batch the host merged into this one turn (several messages sent close together run as one turn whose user_message_uuid is the LAST member's), then any user message folded into the turn before this frame — so a consumer that sent any of them can bind this reply to its own send by finding its uuid anywhere in the list. Always contains user_message_uuid; at most 64 entries. Present exactly when user_message_uuid is, on the same frames; absent from older producers (fall back to user_message_uuid).
     */
    user_message_uuids?: string[];
    /**
     * Why this frame's turn continues one that a worker restart interrupted. Such a turn is the automatic re-run of the interrupted turn (CLAUDE_CODE_RESUME_INTERRUPTED_TURN), or one that goes on from the answer to the permission prompt the new worker took over, or from that turn's tool calls still in flight. The value is the host's CLAUDE_CODE_RESUME_REASON when it set one (host_draining, checkpoint_restore, container_recreated, …), else 'interrupted_turn'. Stamped on the same reply frames as user_message_uuid (which on such a turn names the interrupted turn's own last user prompt), so a consumer can tell its first reply from the interrupted attempt's. Absent on every other turn (also one that goes on from the answer to any other permission prompt), on thinking_tokens frames, and from older producers.
     */
    resume_reason?: string;

};

export declare type SDKPermissionDenial = {
    tool_name: string;
    tool_use_id: string;
    tool_input: Record<string, unknown>;
};

/**
 * Emitted when a tool call is auto-denied without an interactive permission prompt (e.g. auto-mode classifier, dontAsk mode, headless-agent auto-deny, or a deny rule). With a permission prompt surface (stdio/SDK canUseTool), the 'ask' path surfaces via a can_use_tool control_request and this event covers the 'deny' short-circuit. Without one (bare -p / SDK query() with no canUseTool), 'ask' decisions are terminal, so this event also covers those implicit denials. Best-effort advisory: in rare races a denial can book without a frame or a frame can lack a booking twin — result.permission_denials is the authoritative record. Denials that resolve before canUseTool runs — PreToolUse hook denies, deny-rule overrides of hook allow/ask decisions, and file-tool calls (Read, Edit, Write) refused by a path-scoped deny rule — are not covered here, and neither is the MCP --permission-prompt-tool surface (the prompt tool is the host there).
 */
export declare type SDKPermissionDeniedMessage = {
    type: 'system';
    subtype: 'permission_denied';
    tool_name: string;
    tool_use_id: string;
    /**
     * Subagent ID when the denied tool call originated inside a subagent. Mirrors can_use_tool for host-side routing.
     */
    agent_id?: string;
    /**
     * Discriminator from PermissionDecisionReason (e.g. 'classifier', 'asyncAgent', 'mode', 'rule').
     */
    decision_reason_type?: string;

    /**
     * Human-readable reason from the deciding component, when available.
     */
    decision_reason?: string;
    /**
     * The rejection message returned to the model in the tool_result.
     */
    message: string;
    uuid: UUID;
    session_id: string;
};

/**
 * The CLI's plain-language reading of a rule (e.g. "Any Bash command starting with npm run"), split into parts so hosts can render the rule-derived fragment the way the terminal does (bold). prefix and suffix are fixed words; emphasis is rule content — apply display hygiene (invisible-character escaping) before rendering it.
 */
export declare type SDKPermissionRuleDescription = {
    prefix: string;
    emphasis?: string;
    suffix?: string;
};

/**
 * One permission rule with its provenance and where it lives.
 */
export declare type SDKPermissionRuleEntry = {
    behavior: 'allow' | 'deny' | 'ask';
    /**
     * Where the rule comes from. Mirrors PermissionRuleSource (permissionRuleLookup.ts PERMISSION_RULE_SOURCES); the parity test in test/cli/headlessControl/listPermissionRules.test.ts keeps the two aligned.
     */
    source: 'userSettings' | 'projectSettings' | 'localSettings' | 'flagSettings' | 'policySettings' | 'cliArg' | 'command' | 'session' | 'mcpMount' | 'toolsNarrowing' | 'mcpServerPolicy' | 'hostCredential';
    /**
     * The stored rule string VERBATIM, exactly as the session holds it; where the state's `withheld` is true, the text may be cut. Two stored spellings that parse identically each get their own entry. Can carry invisible or control characters by design — escape at display.
     */
    rule: string;
    /**
     * Plain-language reading of the rule; absent where the terminal shows no subtitle either.
     */
    description?: SDKPermissionRuleDescription;
    /**
     * Where the rule lives: 'persistent' (userSettings/projectSettings/localSettings — saved in a settings file), 'session' (cliArg/session — in memory only, for the rest of this session), or 'readonly' (policySettings/flagSettings/command and every other source — the set the terminal's /permissions treats as read-only). Informational for hosts; this request never changes rules.
     */
    editability: 'persistent' | 'session' | 'readonly';
    /**
     * Present (true) when enterprise managed settings pin allowManagedPermissionRulesOnly and this rule, read from a non-policy settings file, is ignored by the session. Such rows are readonly.
     */
    notInEffect?: boolean;
};

/**
 * One additional working directory in the permission scope.
 */
export declare type SDKPermissionWorkspaceDirectory = {
    path: string;
    /**
     * Where the directory grant came from: a settings source (e.g. 'localSettings'), 'cliArg' (--add-dir), or 'session' (/add-dir, IDE workspace folders).
     */
    source: string;
};

/**
 * Configuration for loading a plugin.
 */
export declare type SdkPluginConfig = {
    /**
     * Plugin type. Currently only 'local' is supported
     */
    type: 'local';
    /**
     * Absolute or relative path to the plugin directory
     */
    path: string;
    /**
     * When true, the engine loads skills/hooks/agents/commands from this plugin but does NOT read its .mcp.json or manifest mcpServers. Use when the SDK host owns this plugin's MCP connections.
     */
    skipMcpDiscovery?: boolean;

};

/**
 * Headless plugin installation progress. installed/failed carry a per-marketplace name. Under CLAUDE_CODE_SYNC_PLUGIN_INSTALL started/completed bracket the whole install, ahead of init; without it the install runs in the background, so there is no bracket and a frame can come at any time, before or after init, or not at all if the process ends first. In the background case only the Claude desktop app gets them, once it asks for them, on a local transport (stdout). `error` comes without URL secrets; it is otherwise raw text: treat it as untrusted.
 */
export declare type SDKPluginInstallMessage = {
    type: 'system';
    subtype: 'plugin_install';
    status: 'started' | 'installed' | 'failed' | 'completed';
    name?: string;
    error?: string;
    uuid: UUID;
    session_id: string;
};

/**
 * Predicted next user prompt, emitted after each turn when promptSuggestions is enabled.
 */
export declare type SDKPromptSuggestionMessage = {
    type: 'prompt_suggestion';
    suggestion: string;
    uuid: UUID;
    session_id: string;
};

/**
 * Rate limit event emitted when rate limit info changes.
 */
export declare type SDKRateLimitEvent = {
    type: 'rate_limit_event';
    /**
     * Rate limit information for claude.ai subscription users.
     */
    rate_limit_info: SDKRateLimitInfo;
    uuid: UUID;
    session_id: string;
};

/**
 * Rate limit information for claude.ai subscription users.
 */
export declare type SDKRateLimitInfo = {
    status: 'allowed' | 'allowed_warning' | 'rejected';
    resetsAt?: number;
    rateLimitType?: 'five_hour' | 'seven_day' | 'seven_day_opus' | 'seven_day_sonnet' | 'seven_day_overage_included' | 'overage';
    utilization?: number;

    overageStatus?: 'allowed' | 'allowed_warning' | 'rejected';
    overageResetsAt?: number;
    overageDisabledReason?: 'overage_not_provisioned' | 'org_level_disabled' | 'org_level_disabled_until' | 'out_of_credits' | 'seat_tier_level_disabled' | 'member_level_disabled' | 'seat_tier_zero_credit_limit' | 'group_zero_credit_limit' | 'member_zero_credit_limit' | 'org_service_level_disabled' | 'no_limits_configured' | 'fetch_error' | 'unknown';
    isUsingOverage?: boolean;
    overageInUse?: boolean;
    overageEnabled?: boolean;
    surpassedThreshold?: number;




    /**
     * Which spend limit blocked the request when it is not the member's own cap: 'group_pool' means a pooled group budget shared by the member's team is used up (the denial otherwise looks like the member's own monthly cap). Absent on a plain member denial and from older CLIs.
     */
    limitScope?: 'service' | 'channel' | 'group_pool';

    errorCode?: 'credits_required';
    canUserPurchaseCredits?: boolean;
    hasChargeableSavedPaymentMethod?: boolean;


};

export declare type SDKResultError = {
    type: 'result';
    subtype: 'error_during_execution' | 'error_max_turns' | 'error_max_budget_usd' | 'error_max_structured_output_retries';
    duration_ms: number;
    duration_api_ms: number;
    is_error: boolean;
    num_turns: number;
    stop_reason: string | null;
    /**
     * Cumulative estimated cost in USD for this query() call, covering the same calls as modelUsage (billed permission classifier calls and stopped or cut calls included, which maxBudgetUsd / --max-budget-usd therefore counts) and sharing its lifecycle: cumulative across turns in streaming-input sessions — each result carries the running total so far, so read the latest result rather than summing across results. Crash/startup-error results may carry zeroed values, a resumed or forked session continues from the total its transcript saved, when it has one (so the first result already carries the earlier turns; maxBudgetUsd counts only the spend since this query() call started or last /clear), and a mid-session /clear resets the running total. An estimate, not a billing statement.
     */
    total_cost_usd: number;
    /**
     * MAIN AGENT LOOP ONLY — excludes Task subagent, sidechain, and auxiliary model calls, and is per-turn in streaming-input sessions. Prefer modelUsage for token/cost accounting.
     */
    usage: NonNullableUsage;
    /**
     * Per-model totals for every model call made through the query pipeline during this query() call — main loop, Task subagents, sidechains, and internal calls such as compaction and Workflow agents. Cumulative across turns in streaming-input sessions: each result carries the running total so far, so read the latest result rather than summing across results. Auto mode's permission classifier calls are included where they are billed (not on Pro, Max or Team plans, nor on a claude.ai sign-in whose plan cannot be read), and so is a call stopped or cut mid-response, with its output tokens estimated from what had streamed (low when a long tool call was being written, since the API holds a call's input until it is whole). Other internal helper calls outside the query pipeline (e.g. token-count probes) are excluded; crash/startup-error results may carry zeroed usage, a resumed or forked session continues from the totals its transcript saved, when it has them (so the first result already carries the earlier turns), and a mid-session /clear resets the running total. The correct field for token/cost accounting; treat it as an estimate, not a billing statement.
     */
    modelUsage: Record<string, ModelUsage>;



    permission_denials: SDKPermissionDenial[];
    /**
     * User-initiated sends still waiting in the command queue when this result was produced. Greater than 0 means at least one more user turn (and result) follows without further input, barring cancellation; 0 means none is pending, or the session is ending (end_session or a shutdown latched mid-turn discards the backlog). Queued sends may coalesce into fewer turns, so this counts pending sends, not remaining results. System-generated queue entries are not counted. Absent on fatal startup results and on surfaces without a command queue.
     */
    queued_turn_count?: number;
    errors: string[];

    /**
     * Set on the zeroed error_during_execution result a stream-json run writes before exiting on a known startup failure; errors carries the failure message. Failures that otherwise end with stderr alone write that result only when the host sets CLAUDE_CODE_STARTUP_FAILURE_RESULTS, except org_config_required_unavailable, org_config_refused and config_file_invalid, which every stream-json run writes. Absent on every other result, on startup failures without a known cause, and from older producers.
     */
    startup_failure_reason?: SDKStartupFailureReason;

    /**
     * Set when startup_failure_reason is config_file_invalid: the config file that did not parse and its backup, as separate fields. Read paths from here, never from the text of errors. Each path is in the form that the machine running Claude Code uses, which can differ from the host's. Absent on every other result and from older producers.
     */
    invalid_config_file?: {
        /**
         * The file that is not valid JSON.
         */
        path: string;
        /**
         * Whether this is Claude Code's global config file. Only that file has backups, and only its message says how to repair it.
         */
        is_global: boolean;
        /**
         * Whether Claude Code knows the result of its search for a backup of the file. True with no backup_path: it found none. False: the result is not known, or this is not the global config file.
         */
        backup_searched: boolean;
        /**
         * The backup that the message in errors names. Usually it parses and shows use. Where the search finds none that does, it is the newest that it found with an account, then the newest that holds anything, or at last the newest that does not parse or could not be read, which a person may be able to mend. So show it to a person, or check that it parses before you copy it over the file at path.
         */
        backup_path?: string;
    };
    /**
     * Client uuid of the user message that triggered this turn (submitMessage options.uuid), echoed back so a consumer can link this error result to the send it answers — the same join key the success variant echoes, carried alone (error turns have no request_sent_wall_ms to report). A delivery-failure result from the remote-session client echoes the failed send's queue key, which is client-minted when the host sent no uuid of its own. A synthetic/scheduled (meta) turn's own uuid is echoed only when the host vouches it is the client event's own (delivered content such as a Slack owner ping or a Slack-bot observation); a meta turn that folded queued user messages in mid-turn, vouched or not, echoes the LAST of them. Absent on turns that neither had a client uuid nor folded a user message in, on session-scoped failures with no single triggering send (a crashed worker's zeroed result), and from older producers.
     */
    user_message_uuid?: string;
    /**
     * Client uuids of every user message whose prompt this turn consumed, in consumption order — all members of a prompt batch the host merged into this one turn (several messages sent close together run as one turn whose user_message_uuid is the LAST member's), then any queued user message folded into the running turn between tool rounds, once taken off the queue — so a consumer that sent any of them can bind this result to its own send by finding its uuid anywhere in the list. Always contains user_message_uuid; at most 64 entries; can be longer than the list on the turn's first reply frame. Present when a headless turn that ran echoes user_message_uuid; absent on delivery-failure and zeroed results and from older producers (fall back to user_message_uuid).
     */
    user_message_uuids?: string[];
    /**
     * Why this turn continued one that a worker restart interrupted. Such a turn is the automatic re-run of the interrupted turn (CLAUDE_CODE_RESUME_INTERRUPTED_TURN), or one that goes on from the answer to the permission prompt the new worker took over, or from that turn's tool calls still in flight. The value is the host's CLAUDE_CODE_RESUME_REASON when it set one (host_draining, checkpoint_restore, container_recreated, …), else 'interrupted_turn'. Present on such a headless turn's result, success or error, with or without an echo (a turn whose opening user prompt could not be vouched for still carries the reason); absent on every other turn (also one that goes on from the answer to any other permission prompt), on the Remote Control bridge's per-turn synthetic results, and from older producers.
     */
    resume_reason?: string;




    terminal_reason?: TerminalReason;





    /**
     * Delivery sequence of this result within the run: how many results the run numbered before this one, starting at 0, in the order the process writes them. A result held back while background work finishes is numbered when it is finally written, not when its text was produced; a result whose write fails still consumes its number, so a gap in a stream-json sequence means a result was lost. Distinct from num_turns, which counts model round-trips within one turn. Numbered by the process that hosts the run (`claude -p`, stream-json): a local client relaying a cloud session passes the cloud session's numbering through and its own locally built error results carry none; the in-process engine surface does not number yet. Absent from older producers.
     */
    result_index?: number;
    /**
     * When the claude.ai credential this process's requests send ends for good, as an ISO 8601 instant, read as the result is written. For a stored claude.ai login it is the end of the login's refresh chain as stored at sign-in, which renewing the access token does not move. That date is the server's when it sent one and otherwise a 30-day estimate, and the real end can be up to 3 days earlier. The server is not asked, so a login revoked early still shows its date, and a date in the past means the login has probably ended, not that it has. Absent when no date is known, for every other credential (an API key, a token from the environment, another provider), on results this process did not number, and from older producers.
     */
    credential_expires_at?: string;
    fast_mode_state?: FastModeState;
    fast_mode_disabled_reason?: FastModeDisabledReason;
    origin?: SDKMessageOrigin;
    uuid: UUID;
    session_id: string;
};

/**
 * The outcome of a turn. The CLI emits exactly one result message per turn, after that turn's assistant, user and stream_event messages; treat it as the turn-complete signal (informational system messages such as task notifications, session state changes or prompt suggestions may still follow it). subtype "success" carries the final assistant text in result — or, with is_error true, the error text when the turn ended on an API error; the error subtypes say why the turn stopped early. In single-prompt (non-streaming-input) mode the process exits after the turn.
 */
export declare type SDKResultMessage = SDKResultSuccess | SDKResultError;

export declare type SDKResultSuccess = {
    type: 'result';
    subtype: 'success';
    duration_ms: number;
    duration_api_ms: number;
    ttft_ms?: number;
    ttft_stream_ms?: number;
    time_to_request_ms?: number;




































    user_message_uuid?: string;
    user_message_uuids?: string[];
    resume_reason?: string;
    local_command?: string;
    request_sent_wall_ms?: number;



    first_content_frame_ms?: number;
    first_stream_post_ms?: number;
    first_stream_post_ack_ms?: number;
    first_stream_post_queue_wait_ms?: number;
    first_stream_post_queued_behind?: 'durable_post' | 'ephemeral_post' | 'retry_backoff' | 'hold' | 'none';
    first_stream_post_wall_ms?: number;






    first_text_post_ms?: number;
    first_text_post_queue_wait_ms?: number;
    first_text_post_queued_behind?: 'durable_post' | 'ephemeral_post' | 'retry_backoff' | 'hold' | 'none';
    first_text_post_wall_ms?: number;



    time_to_request_from_spawn_ms?: number;
    warm_spare_claimed?: boolean;

    time_origin_ms?: number;



    is_error: boolean;
    api_error_status?: number | null;




    num_turns: number;
    result: string;
    stop_reason: string | null;
    /**
     * Cumulative estimated cost in USD for this query() call, covering the same calls as modelUsage (billed permission classifier calls and stopped or cut calls included, which maxBudgetUsd / --max-budget-usd therefore counts) and sharing its lifecycle: cumulative across turns in streaming-input sessions — each result carries the running total so far, so read the latest result rather than summing across results. Crash/startup-error results may carry zeroed values, a resumed or forked session continues from the total its transcript saved, when it has one (so the first result already carries the earlier turns; maxBudgetUsd counts only the spend since this query() call started or last /clear), and a mid-session /clear resets the running total. An estimate, not a billing statement.
     */
    total_cost_usd: number;
    /**
     * MAIN AGENT LOOP ONLY — excludes Task subagent, sidechain, and auxiliary model calls, and is per-turn in streaming-input sessions. Prefer modelUsage for token/cost accounting.
     */
    usage: NonNullableUsage;
    /**
     * Per-model totals for every model call made through the query pipeline during this query() call — main loop, Task subagents, sidechains, and internal calls such as compaction and Workflow agents. Cumulative across turns in streaming-input sessions: each result carries the running total so far, so read the latest result rather than summing across results. Auto mode's permission classifier calls are included where they are billed (not on Pro, Max or Team plans, nor on a claude.ai sign-in whose plan cannot be read), and so is a call stopped or cut mid-response, with its output tokens estimated from what had streamed (low when a long tool call was being written, since the API holds a call's input until it is whole). Other internal helper calls outside the query pipeline (e.g. token-count probes) are excluded; crash/startup-error results may carry zeroed usage, a resumed or forked session continues from the totals its transcript saved, when it has them (so the first result already carries the earlier turns), and a mid-session /clear resets the running total. The correct field for token/cost accounting; treat it as an estimate, not a billing statement.
     */
    modelUsage: Record<string, ModelUsage>;



    permission_denials: SDKPermissionDenial[];
    /**
     * User-initiated sends still waiting in the command queue when this result was produced. Greater than 0 means at least one more user turn (and result) follows without further input, barring cancellation; 0 means none is pending, or the session is ending (end_session or a shutdown latched mid-turn discards the backlog). Queued sends may coalesce into fewer turns, so this counts pending sends, not remaining results. System-generated queue entries are not counted. Absent on fatal startup results and on surfaces without a command queue.
     */
    queued_turn_count?: number;
    structured_output?: unknown;
    deferred_tool_use?: SDKDeferredToolUse;
    terminal_reason?: TerminalReason;




    /**
     * Delivery sequence of this result within the run: how many results the run numbered before this one, starting at 0, in the order the process writes them. A result held back while background work finishes is numbered when it is finally written, not when its text was produced; a result whose write fails still consumes its number, so a gap in a stream-json sequence means a result was lost. Distinct from num_turns, which counts model round-trips within one turn. Numbered by the process that hosts the run (`claude -p`, stream-json): a local client relaying a cloud session passes the cloud session's numbering through and its own locally built error results carry none; the in-process engine surface does not number yet. Absent from older producers.
     */
    result_index?: number;
    /**
     * When the claude.ai credential this process's requests send ends for good, as an ISO 8601 instant, read as the result is written. For a stored claude.ai login it is the end of the login's refresh chain as stored at sign-in, which renewing the access token does not move. That date is the server's when it sent one and otherwise a 30-day estimate, and the real end can be up to 3 days earlier. The server is not asked, so a login revoked early still shows its date, and a date in the past means the login has probably ended, not that it has. Absent when no date is known, for every other credential (an API key, a token from the environment, another provider), on results this process did not number, and from older producers.
     */
    credential_expires_at?: string;
    fast_mode_state?: FastModeState;
    fast_mode_disabled_reason?: FastModeDisabledReason;
    origin?: SDKMessageOrigin;
    uuid: UUID;
    session_id: string;
};

/**
 * Session metadata returned by listSessions and getSessionInfo.
 */
export declare type SDKSessionInfo = {
    /**
     * Unique session identifier (UUID).
     */
    sessionId: string;
    /**
     * Display title for the session: custom title, auto-generated summary, or first prompt.
     */
    summary: string;
    /**
     * Last modified time in integer milliseconds since epoch.
     */
    lastModified: number;
    /**
     * File size in bytes. Only populated for local JSONL storage.
     */
    fileSize?: number;
    /**
     * User-set session title via /rename.
     */
    customTitle?: string;
    /**
     * First meaningful user prompt in the session.
     */
    firstPrompt?: string;
    /**
     * Git branch at the end of the session.
     */
    gitBranch?: string;
    /**
     * Working directory for the session.
     */
    cwd?: string;
    /**
     * User-set session tag.
     */
    tag?: string;
    /**
     * Creation time in integer milliseconds since epoch, extracted from the first entry's timestamp.
     */
    createdAt?: number;
    /**
     * Whether the session is archived: false if it was and has been unarchived, or a prompt was sent in it since. Absent if it never was, and with a sessionStore.
     */
    archived?: boolean;
};

/**
 * Mirrors notifySessionStateChanged. 'idle' fires after heldBackResult flushes and the bg-agent do-while exits — authoritative turn-over signal.
 */
export declare type SDKSessionStateChangedMessage = {
    type: 'system';
    subtype: 'session_state_changed';
    state: 'idle' | 'running' | 'requires_action';
    uuid: UUID;
    session_id: string;
};

/**
 * The CLI could not save lines of a session transcript, changes to ~/.claude.json, or both, because the disk was full or its quota was used up. Sent at most once, as the CLI exits with status 0, after the last result if there was one. A run that exits 1, as after an error result, gets only the line on stderr; CLI 2.1.317 and some later releases sent this message there too. The results already received stand, and this message does not change the exit status. As on every message, session_id is the session the CLI is in; transcript_session_ids says whose transcript lost lines. Sent only with stream-json output on stdout, never under --sdk-url or a Claude Desktop entrypoint. Safe to ignore.
 */
export declare type SDKSessionWritesLostMessage = {
    type: 'system';
    subtype: 'session_writes_lost';
    /**
     * Why the writes failed. 'ENOSPC': the disk was full. 'EDQUOT': the disk quota was used up. When both kinds of write were lost for different reasons, the transcript's. More codes may be added.
     */
    error_code: 'ENOSPC' | 'EDQUOT';
    /**
     * What was not saved. 'transcript': lines of a session transcript, so resuming a session in transcript_session_ids may miss part of its conversation. 'global_config': changes this run made to ~/.claude.json. Never empty. More values may be added.
     */
    lost: ('transcript' | 'global_config')[];
    /**
     * The sessions whose transcripts lost lines, in the order each first lost one. Present only when 'transcript' is listed; never empty. Usually session_id alone. A CLI that started a new session after the loss, as /clear does, lists the earlier session, and lists session_id only if that session lost lines too.
     */
    transcript_session_ids?: string[];
    uuid: UUID;
    session_id: string;
};

/**
 * A settings file parse or validation error. When a settings.json file fails to parse (invalid JSON, JSON comments, schema mismatch), the file is skipped and any rules it contained — including permission allow/deny lists — are not applied.
 */
export declare type SDKSettingsParseError = {
    /**
     * Path to the settings file that failed to parse or validate.
     */
    file?: string;
    /**
     * Dot-notation path to the field with the error, or empty string for whole-file errors.
     */
    path: string;
    /**
     * Human-readable error message.
     */
    message: string;
};

/**
 * Why Claude Code refused to start, so a host can offer the fix instead of a retry. org_pin_api_key_conflict: managed settings pin a first-party or Cloud gateway sign-in, and an Anthropic API key or auth token is configured instead. provider_not_allowed: managed settings list the API providers this machine may use (allowedProviders), and the session is set up for one that is not listed. org_verify_failed: the sign-in's organization could not be verified against the pin (network, or a revoked token). org_pin_mismatch: the sign-in belongs to an organization the pin does not allow. managed_settings_invalid: managed policy settings could not be read, the pin names no organization, or managed model settings (deniedModels, or an availableModels list matched exactly) block the default model and leave no allowed model to use instead. remote_settings_required_unavailable: managed settings the organization requires could not be loaded. gateway_signin_required: the Cloud gateway ended this sign-in. gateway_access_denied: the Cloud gateway refused managed settings for this account. proxy_invalid: a proxy setting is not a complete URL. temp_dir_unusable: the per-user temp directory is unsafe or could not be created. cwd_unavailable: the working directory was deleted, moved or cannot be read, or (not on Windows) a folder name in its path is not valid UTF-8 and a different file, folder or link stands at the name Claude Code reads it as, for that folder or one above it; start from another directory, rename that folder, or remove the other entry. shell_tool_missing: Windows has no shell tool: Git Bash is missing, and PowerShell is missing or turned off by CLAUDE_CODE_USE_POWERSHELL_TOOL. session_held_by_background: the conversation to resume or continue is running as a background session. worktree_resume_refused: the resume was refused because the session's worktree failed its safety checks or the resume was launched from inside it; errors says whether a re-run continues without the worktree. worktree_unverified: the session's worktree could not be verified right now; retrying may succeed. cli_version_too_old: this Claude Code version is below the minimum Anthropic requires. bypass_root: bypass permissions mode was requested while running as root. org_config_required_unavailable: the organization requires its policy limits and managed settings before a session starts, and they could not be loaded (network, proxy, or an Anthropic error); retrying may succeed. org_config_refused: the organization requires its policy limits and managed settings, and Anthropic refused them for this sign-in (expired or revoked session, or the organization does not allow Claude Code for this account); signing in again or an admin's change is the fix, not a retry. sandbox_required_unavailable: a working sandbox is required and it cannot run in this session, for example because bubblewrap is missing or the platform is not supported; make the sandbox available or have the requirement changed. initialize_not_first: Claude Code was started with --await-initialize, and its first stdin line was not the initialize control request (another message, or not valid JSON). Either the host wrote something else first, or a wrapper script between the host and Claude Code read or changed that line; the fix is in the host or the wrapper script, not a retry. config_file_invalid: a configuration file read at start-up is not valid JSON; errors names the file and, for the global configuration file, how to restore or repair it, and invalid_config_file has the paths as fields. The file is left unchanged, and every start without a terminal is refused until it is repaired, so a retry alone does not help. managed_settings_not_delivered: Claude Code was started with --managed-settings-in-initialize and could not use the managed settings in the initialize control request. Stdin ended or failed first, or its first line was too long; the request has no managedSettings object, that object could not be used, or the request's plugins or mcpServers field is malformed; or the launch does not read that request at start-up or also passes --managed-settings. errors says which. Claude Code starts no session without them; the fix is in the host or in a wrapper script between it and Claude Code, not a retry. initialize_fields_not_delivered: as managed_settings_not_delivered, for --initialize-fields and the settings or disallowedTools that it names; also when a named field's own flag (--settings, --disallowedTools) is passed too.
 */
export declare type SDKStartupFailureReason = 'org_pin_api_key_conflict' | 'provider_not_allowed' | 'org_verify_failed' | 'org_pin_mismatch' | 'managed_settings_invalid' | 'remote_settings_required_unavailable' | 'gateway_signin_required' | 'gateway_access_denied' | 'proxy_invalid' | 'temp_dir_unusable' | 'cwd_unavailable' | 'shell_tool_missing' | 'session_held_by_background' | 'worktree_resume_refused' | 'worktree_unverified' | 'cli_version_too_old' | 'bypass_root' | 'org_config_required_unavailable' | 'org_config_refused' | 'sandbox_required_unavailable' | 'initialize_not_first' | 'config_file_invalid' | 'managed_settings_not_delivered' | 'initialize_fields_not_delivered';

export declare type SDKStatus = 'compacting' | 'requesting' | null;

export declare type SDKStatusMessage = {
    type: 'system';
    subtype: 'status';
    status: SDKStatus;
    permissionMode?: PermissionMode;
    compact_result?: 'success' | 'failed';
    compact_error?: string;




    uuid: UUID;
    session_id: string;
};

/**
 * Session metadata the CLI emits at the start of each turn, normally ahead of every other message of that turn: session_id, model, working directory, tools, MCP servers, slash commands, permission mode, and the capabilities list for feature detection.
 */
export declare type SDKSystemMessage = {
    type: 'system';
    subtype: 'init';
    agents?: string[];
    /**
     * Where the credential used for API requests came from: 'ANTHROPIC_API_KEY' (environment variable), 'apiKeyHelper' (the configured helper command), '/login managed key' (an API key created and stored by /login with an Anthropic Console account), or 'none' (no API key in use - e.g. claude.ai OAuth login, a bearer token, or a third-party cloud provider). 'user' | 'project' | 'org' | 'temporary' | 'oauth' are legacy members that current CLIs never emit; they remain only so the type stays backward compatible.
     */
    apiKeySource: ApiKeySource;

    betas?: string[];
    claude_code_version: string;
    cwd: string;
    tools: string[];
    mcp_servers: {
        name: string;
        status: string;
        /**
         * Where the server definition came from — same values as McpServerStatus.source (sdk | plugin | a config scope). Absent on CLIs that predate the field.
         */
        source?: string;
    }[];
    model: string;
    /**
     * Permission mode for controlling how tool executions are handled. 'default' - Standard behavior, prompts for dangerous operations. 'acceptEdits' - Auto-accept file edit operations. 'bypassPermissions' - Bypass all permission checks (requires allowDangerouslySkipPermissions). 'plan' - Planning mode, no actual tool execution. 'dontAsk' - Don't prompt for permissions, deny if not pre-approved. 'auto' - Use a model classifier to approve/deny permission prompts.
     */
    permissionMode: PermissionMode;
    slash_commands: string[];
    /**
     * Subset of slash_commands whose UX is bound to the local terminal (e.g. exit, statusline). Phone/remote UIs should hide these from command menus; desktop surfaces may keep them. Present only when non-empty; absent on CLIs that predate the field, and on sessions where no advertised command carries the tag.
     */
    terminal_slash_commands?: string[];
    output_style: string;
    skills: string[];
    plugins: {
        name: string;
        path: string;

        /**
         * The plugin's version as declared in its plugin.json manifest, emitted verbatim (plugin-author-controlled — validate before trusting). Omitted when the manifest declares no version.
         */
        version?: string;
    }[];
    /**
     * Plugin load-time errors. A plugin that did not load (an unmet dependency, a --plugin-dir entry that failed, a plugin enabled by managed settings that the loader could not load) is absent from `plugins[]`; a plugin that loaded without one of its components keeps its row and gets an entry here too. `plugin` is `name@marketplace`, or the positional `inline[N]` / `synced[N]` tag for a directory entry that failed before it had a name; `type` is a category from an open set (path-not-found, generic-error, manifest-validation-error, dependency-unsatisfied, hook-load-failed, …) — treat a value you do not recognize as a generic failure; `message` is display text; over a transport that may store its frames (a cloud worker or a self-hosted runner), an entry that is here only because managed settings enable the plugin carries one fixed sentence in its place, with no path or URL. The key is omitted when there are no errors; CI can fail on `(plugin_errors?.length ?? 0) > 0`. That check also trips on a machine that has no copy yet of a plugin enabled by managed settings, which is every run on a throwaway CI runner; CLAUDE_CODE_SYNC_PLUGIN_INSTALL=1 makes the first turn wait for the install. A Remote Control worker and the hosted worker always omit this key — plugin diagnostics stay in the local log there, so an omitted key does not assert a clean load.
     */
    plugin_errors?: {
        plugin: string;
        type: string;
        message: string;
        /**
         * Present only when a --plugin-dir, SDK `plugins` or synced directory entry did not load at all: the path of that entry, resolved against the cwd (for a directory, the value its `plugins[]` row would have carried; for a .zip, the archive; a --plugin-url entry carries none). `plugin` is then the positional `inline[N]` / `synced[N]` tag, so a host that mounts several directories pairs the error to its own by this path.
         */
        path?: string;
        /**
         * Present only when a managed-settings `enabledPlugins` entry dropped this --plugin-dir, SDK `plugins`, skills-directory or synced copy: the two halves of that entry, `name` and `marketplace`, and its value. `plugin_enabled` true: the entry turns that plugin on, and Claude Code does not accept this copy as that plugin. `plugin_enabled` false: the entry turns it off, and no directory copy of the name may load. Neither stops an install of the same name from another marketplace, which can load beside this row. `name` and `marketplace` are byte-exact, like `plugin`: control and bidi characters are not removed and the length is not bounded, so clean and bound them before showing them. `name` is as the entry spells it, which can differ from the copy (case, Unicode form, an earlier name of a built-in). `marketplace` is absent where the entry names no marketplace that an install could come from.
         */
        managed_lock?: {
            plugin_enabled: boolean;
            name: string;
            marketplace?: string;
        };
    }[];


    fast_mode_state?: FastModeState;
    fast_mode_disabled_reason?: FastModeDisabledReason;

    /**
     * The effort level set for the session's next message — after env overrides, session state, org caps and model-support downgrades; the same value get_settings reports as applied.effort. null when no effort parameter will be sent (a model without effort, CLAUDE_CODE_EFFORT_LEVEL=unset, or an internal numeric budget). Present on Remote Control bridge init frames (terminal- and Desktop/VS Code-hosted sessions); absent on hosts that do not publish it and on CLIs that predate the field. Re-emitted inits carry the current value — the newest frame wins.
     */
    effort?: ('low' | 'medium' | 'high' | 'xhigh' | 'max') | null;



    /**
     * Whether the session's transcript is in focus view ('focus': the model is told the user sees only its final message per turn, so clients may collapse each turn to the prompt and the final response; 'default' otherwise). Toggled by /focus, including over Remote Control. Present on Remote Control bridge init frames and on the per-turn init of headless stream-json runs (`claude rc` workers, -p, the SDK's subprocess transport); absent on hosts that do not publish it (the in-process engine) and on CLIs that predate the field. Re-emitted inits carry the current value — the newest frame wins.
     */
    view_mode?: 'focus' | 'default';
    /**
     * Protocol capabilities this CLI supports, so SDK consumers can feature-detect instead of version-sniffing. Open set — ignore unknown values; check each capability for exactly the behavior you use. 'interrupt_receipt_v1' = the interrupt control_response success payload carries still_queued (uuids of async user messages that survive the interrupt). 'interrupt_cancel_queued_v1' = the interrupt control_request honors cancel_queued:true (queued and pending-dispatch commands are cancelled alongside the abort, listed on the response's cancelled field; still_queued is then empty — including any uuid that was mid-fold at the interrupt instant, since this request also aborts and the fold never delivers it — except that a client driving a hosted session lists there what it can no longer recall: a send already in flight to that session, or the first prompt the session was created with). 'queued_notifications' = the CLI accepts inbound queued_notification stream messages and drains them via ReadNotifications (the cloud session backend reads this from the persisted init event to decide whether it may send them). 'ask_user_question_unanswered_v1' = an AskUserQuestion answer may set annotations[question].unanswered ('skipped' | 'replied_in_chat' | 'dismissed'), which the tool result echoes; send it only to a session that advertises this, since an older CLI on a strict host refuses the whole answer. A strict host also refuses an answer with a value outside these three; a new value will come with a new capability. 'reload_plugins_refuse_if_busy_v1' = the reload_plugins control request honors refuse_if_busy; a CLI that does not advertise this may ignore the field and serve the request in a turn too. Absent on older CLIs.
     */
    capabilities?: string[];
















    uuid: UUID;
    session_id: string;
};

export declare type SDKTaskNotificationMessage = {
    type: 'system';
    subtype: 'task_notification';
    task_id: string;
    /**
     * Id of one run of the task: equal on every task_* event, background_tasks_changed entry and saved notification (its origin.runId) of that run. A resumed task keeps its task_id and gets a new one. The run ids of one task sort, by plain string comparison, in the order the runs opened; a frame that names a run sorting before the one a reader shows is late. Nothing else about the format is promised. Absent for a task this process did not register, and from CLIs that predate it.
     */
    run_id?: string;
    tool_use_id?: string;
    status: 'completed' | 'failed' | 'stopped';
    /**
     * Machine-readable cause, set only when the task did not end through an ordinary completion, failure, or stop. 'worker_restart': the worker process restarted and the resumed process found the task orphaned (always with status 'stopped').
     */
    reason?: 'worker_restart';
    output_file: string;
    summary: string;

    usage?: {
        total_tokens: number;
        tool_uses: number;
        duration_ms: number;
    };
    /**
     * CLI-owned: for a backgrounded MCP task (task_type mcp_task) that completed, the `resource_link` content blocks of its final result — the files it returned by reference — collected from the raw result before the CLI renders it as the text the model reads. A backgrounded task's tool_result is the placeholder text and its real result arrives as this notification, so this is where a host learns which files that tool call produced; join to the originating call via tool_use_id. Same fields and caps as tool_use_result.resourceLinks (at most 50 links, 64 KiB serialized), absent when the result had none or the task is any other type. Never populated from the server's _meta.
     */
    resource_links?: SDKMcpResourceLink[];





    skip_transcript?: boolean;
    /**
     * True for tasks that are not activity (every skip_transcript task, plus every live-update watcher, requested or auto-started); hosts should exclude them from activity indicators.
     */
    ambient?: boolean;
    uuid: UUID;
    session_id: string;
};

export declare type SDKTaskProgressMessage = {
    type: 'system';
    subtype: 'task_progress';
    task_id: string;
    /**
     * Id of one run of the task: equal on every task_* event, background_tasks_changed entry and saved notification (its origin.runId) of that run. A resumed task keeps its task_id and gets a new one. The run ids of one task sort, by plain string comparison, in the order the runs opened; a frame that names a run sorting before the one a reader shows is late. Nothing else about the format is promised. Absent for a task this process did not register, and from CLIs that predate it.
     */
    run_id?: string;
    tool_use_id?: string;
    description: string;
    /**
     * Subagent type for Task tool subagents.
     */
    subagent_type?: string;
    usage: {
        total_tokens: number;
        tool_uses: number;
        duration_ms: number;
    };
    last_tool_name?: string;
    /**
     * A one-line status for the task's row. For a local_agent task it is the model-generated progress summary (only when the agentProgressSummaries option is on); for a backgrounded mcp_task it is the MCP server's own bounded status message, emitted once per change without any option. Render it when present regardless of task type.
     */
    summary?: string;



    uuid: UUID;
    session_id: string;
};

export declare type SDKTaskStartedMessage = {
    type: 'system';
    subtype: 'task_started';
    task_id: string;
    /**
     * Id of one run of the task: equal on every task_* event, background_tasks_changed entry and saved notification (its origin.runId) of that run. A resumed task keeps its task_id and gets a new one. The run ids of one task sort, by plain string comparison, in the order the runs opened; a frame that names a run sorting before the one a reader shows is late. Nothing else about the format is promised. Absent for a task this process did not register, and from CLIs that predate it.
     */
    run_id?: string;
    tool_use_id?: string;
    description: string;
    /**
     * Subagent type for Task tool subagents.
     */
    subagent_type?: string;
    /**
     * Whether the task was registered in the background (true) or in the foreground with the spawning tool call blocking on it (false). A resumed subagent is always registered in the background. A later move to the background arrives as task_updated patch.is_backgrounded. Set for local_agent and local_bash tasks.
     */
    is_backgrounded?: boolean;

    /**
     * Nesting depth of a spawned subagent (local_agent) task: 1 for a top-level spawn, N+1 when spawned from inside a depth-N agent. Not set on other tasks.
     */
    spawn_depth?: number;
    /**
     * task_id of the subagent (local_agent) task whose agent launched this subagent, shell, monitor or workflow task. Absent when the launcher is the main thread, has no task_id of its own (a teammate, an agent inside a workflow), or is no longer tracked. A resumed subagent keeps its original parent. The parent may be a foreground or already-ended task, so treat an unknown id as no parent.
     */
    parent_task_id?: string;
    task_type?: string;
    /**
     * meta.name from the workflow script (e.g. 'spec'). Only set when task_type is 'local_workflow'.
     */
    workflow_name?: string;
    /**
     * Text describing what this run was asked. Absent on a subagent run that Claude Code resumed with text of its own (such as a background task's notice); keep the prompt an earlier task_started gave. On a run that continues an interrupted turn, this is the task's description.
     */
    prompt?: string;
    /**
     * Ambient/housekeeping task. Consumers should hide this from the inline transcript; it may still appear in a tasks panel.
     */
    skip_transcript?: boolean;
    /**
     * True for tasks that are not activity (every skip_transcript task, plus every live-update watcher, requested or auto-started); hosts should exclude them from activity indicators.
     */
    ambient?: boolean;
    uuid: UUID;
    session_id: string;
};

export declare type SDKTaskUpdatedMessage = {
    type: 'system';
    subtype: 'task_updated';
    task_id: string;
    /**
     * Id of one run of the task: equal on every task_* event, background_tasks_changed entry and saved notification (its origin.runId) of that run. A resumed task keeps its task_id and gets a new one. The run ids of one task sort, by plain string comparison, in the order the runs opened; a frame that names a run sorting before the one a reader shows is late. Nothing else about the format is promised. Absent for a task this process did not register, and from CLIs that predate it.
     */
    run_id?: string;
    /**
     * Wire-safe subset of TaskState fields that changed. Excludes abortController, messages, result. Clients merge into their local task map.
     */
    patch: {
        status?: 'pending' | 'running' | 'completed' | 'failed' | 'killed' | 'paused';
        description?: string;
        end_time?: number;
        total_paused_ms?: number;
        error?: string;
        is_backgrounded?: boolean;
    };
    uuid: UUID;
    session_id: string;
};

/**
 * Live thinking-token estimate, digested from thinking_delta.estimated_tokens during the redacted-thinking phase (where the API otherwise streams only pings). estimated_tokens is the running total for the current thinking block; estimated_tokens_delta is the increment carried by this frame. Approximate progress for spinners/pills, not the authoritative billed output_tokens.
 */
export declare type SDKThinkingTokensMessage = {
    type: 'system';
    subtype: 'thinking_tokens';
    estimated_tokens: number;
    estimated_tokens_delta: number;
    /**
     * Client uuid of the user message that triggered this turn (submitMessage options.uuid), stamped on every thinking_tokens frame of a headless (stream-json / Agent SDK) turn so a consumer can attribute thinking progress to the send it answers before any reply frame arrives. On a synthetic/scheduled (meta) turn it names the last user message folded into the turn so far once one has been, else the turn's own uuid when the host vouches it is the client event's own (delivered content such as a Slack owner ping). Absent on turns that neither had a client uuid nor folded a user message in, on Remote Control (interactive terminal) sessions, and from older producers.
     */
    user_message_uuid?: string;
    uuid: UUID;
    session_id: string;
};

export declare type SDKToolProgressMessage = {
    type: 'tool_progress';
    tool_use_id: string;
    tool_name: string;
    parent_tool_use_id: string | null;
    elapsed_time_seconds: number;
    task_id?: string;
    uuid: UUID;
    session_id: string;
    heartbeat?: boolean;
    subagent_type?: string;
    subagent_retry?: {
        agent_id: string;
        attempt: number;
        max_retries: number;
        retry_delay_ms: number;
        error_status: number | null;
        error_category: string;
    };
};

export declare type SDKToolUseSummaryMessage = {
    type: 'tool_use_summary';
    summary: string;
    preceding_tool_use_ids: string[];
    uuid: UUID;
    session_id: string;

};

/**
 * Structured twin of a /usage result, carried beside its text: the session's totals, the plan's usage rows as the server sent them and the extra-usage spend, and nothing else from the usage body (the get_usage control reply carries the rest). Experimental — the shape may change.
 */
export declare type SDKUsageReport = {
    /**
     * Cost and usage accumulated by the current session.
     */
    session: {
        total_cost_usd: number;
        total_api_duration_ms: number;
        total_duration_ms: number;
        total_lines_added: number;
        total_lines_removed: number;
        model_usage: Record<string, ModelUsage>;
    };
    /**
     * The plan's usage rows and extra-usage spend from the claude.ai usage endpoint; null when the CLI could not fetch them (no plan on this lane, or a token without the profile scope).
     */
    rate_limits: {
        /**
         * The server's usage rows (the usage endpoint's limits[]), as sent: which meters apply, their scope, labels, severity and order are the server's, so a client renders them verbatim and a new meter needs no client release. Empty when the server reported no meters; null when the body carried no rows at all (a server that predates them). Null too while the usage fetch is failing: the rows here are only ever the server's current reply, so neither the row the CLI builds from rate-limit response headers for its own screen nor its snapshot of an earlier reply appears here.
         */
        limits: {
            /**
             * The server's meter kind, e.g. 'session', 'weekly_all' or 'weekly_scoped'. Classify a row on this, never on a label.
             */
            kind: string;
            /**
             * The server's row group, e.g. 'session' or 'weekly'; rows render grouped under it, in the server's order.
             */
            group: string;
            /**
             * Share of the window used, 0-100.
             */
            percent: number;
            /**
             * ISO 8601 timestamp when the window resets.
             */
            resets_at: string | null;
            /**
             * What a scoped row is for, a model or a surface, with the server's display label.
             */
            scope?: {
                model?: {
                    display_name: string;
                } | null;
                surface?: {
                    display_name: string;
                } | null;
            } | null;
            /**
             * The server's reading of the row for a meter's colour, e.g. 'normal', 'warning' or 'critical'. Every row here is the server's, so a client never grades a row itself.
             */
            severity: string;
            /**
             * The server's headline pick: the row a single-value indicator shows.
             */
            is_active: boolean;
        }[] | null;
        /**
         * Extra-usage (overage) spend for the billing period, when the plan has it. Amounts are in minor units of `currency` (cents for USD); is_enabled is false while extra usage cannot cover sends.
         */
        extra_usage?: {
            is_enabled: boolean;
            monthly_limit: number | null;
            used_credits: number | null;
            utilization: number | null;
            currency?: string | null;
        } | null;
    } | null;
};

/**
 * A user-role message. A client writes one to the CLI to submit a prompt (this starts a turn); the CLI emits them for user-role content it adds to the conversation itself, chiefly the tool_result blocks answering the assistant's tool_use blocks.
 */
export declare type SDKUserMessage = {
    type: 'user';
    /**
     * An Anthropic Messages API user message: a MessageParam with role "user" whose content is a string or an array of content blocks (text, image, document, tool_result, ...). See the Messages API reference for the block types.
     */
    message: MessageParam;
    parent_tool_use_id: string | null;
    isSynthetic?: boolean;
    /**
     * Structured tool output — the tool's full Output object, not the string content sent to the model. The shape is per-tool, keyed by the matching tool_use block's name (see the *Output types in toolTypes); MCP and dynamic tools carry their own shapes, so the field stays unknown-typed. For the Agent/Task tool the completed shape is the subagent's final report without the model-directed agentId/usage trailer, plus run totals — render from it instead of parsing the tool_result text. A call that stepped aside for a message the user sent (today a WebFetch or WebSearch call) carries `{ detachedToolCall: true }` in place of its Output: the call is still running, and its result reaches the model in a later turn.
     */
    tool_use_result?: unknown;
    priority?: 'now' | 'next' | 'later';

    origin?: SDKMessageOrigin;































    /**
     * When false, the message is appended to the transcript without triggering an assistant turn. It will be merged into the next user message that does query.
     */
    shouldQuery?: boolean;
    /**
     * ISO timestamp when the message was created on the originating process. Older emitters omit it; consumers should fall back to receive time.
     */
    timestamp?: string;


    /**
     * The client composed this turn from content the user did not type; the CLI delivers its text as written, with no `@path` file-mention expansion and no slash-command dispatch. On current CLIs the turn-start attachment pass is skipped as a whole: `@server:resource` MCP mentions are not expanded either, and the prompt is sent without the context the CLI normally attaches alongside it (nested `CLAUDE.md` and rules files, skill and tool listings, reminders); the pass the CLI runs between tool calls is unaffected.
     */
    client_composed?: true;


















    uuid?: UUID;
    /**
     * Content the user pasted into the prompt rather than typed: each entry a string or an array of content blocks. The CLI appends the text of each entry after the typed text, in order, and may wrap it in `<pasted_content>` tags. Blocks other than text are ignored; send images and documents in `message.content`. A list of over 1,000 entries and blocks in all is ignored.
     */
    pasted_content?: MessageParam['content'][];
    /**
     * Text the user pasted that is still in `message.content` where they put it: each entry one paste. The prompt is not changed by the host; the CLI may wrap each entry in `<pasted_content>` tags where it still stands in the last text block, or where a text block holds nothing else. It looks for the first 100 entries that are not blank. For a paste the host took out of `message`, use `pasted_content` instead.
     */
    inline_pastes?: string[];

    session_id?: string;
    /**
     * ID of the subagent that produced this message: the `task_id` of its task events, unchanged when the subagent is resumed. Absent on main-thread messages.
     */
    agent_id?: string;
    /**
     * Subagent type that produced this message.
     */
    subagent_type?: string;
    /**
     * Description of the subagent task that produced this message.
     */
    task_description?: string;


};

export declare type SDKUserMessageReplay = {
    type: 'user';
    /**
     * An Anthropic Messages API user message: a MessageParam with role "user" whose content is a string or an array of content blocks (text, image, document, tool_result, ...). See the Messages API reference for the block types.
     */
    message: MessageParam;
    parent_tool_use_id: string | null;
    isSynthetic?: boolean;
    /**
     * Structured tool output — the tool's full Output object, not the string content sent to the model. The shape is per-tool, keyed by the matching tool_use block's name (see the *Output types in toolTypes); MCP and dynamic tools carry their own shapes, so the field stays unknown-typed. For the Agent/Task tool the completed shape is the subagent's final report without the model-directed agentId/usage trailer, plus run totals — render from it instead of parsing the tool_result text. A call that stepped aside for a message the user sent (today a WebFetch or WebSearch call) carries `{ detachedToolCall: true }` in place of its Output: the call is still running, and its result reaches the model in a later turn.
     */
    tool_use_result?: unknown;
    priority?: 'now' | 'next' | 'later';

    origin?: SDKMessageOrigin;































    /**
     * When false, the message is appended to the transcript without triggering an assistant turn. It will be merged into the next user message that does query.
     */
    shouldQuery?: boolean;
    /**
     * ISO timestamp when the message was created on the originating process. Older emitters omit it; consumers should fall back to receive time.
     */
    timestamp?: string;


    /**
     * The client composed this turn from content the user did not type; the CLI delivers its text as written, with no `@path` file-mention expansion and no slash-command dispatch. On current CLIs the turn-start attachment pass is skipped as a whole: `@server:resource` MCP mentions are not expanded either, and the prompt is sent without the context the CLI normally attaches alongside it (nested `CLAUDE.md` and rules files, skill and tool listings, reminders); the pass the CLI runs between tool calls is unaffected.
     */
    client_composed?: true;


















    uuid: UUID;
    session_id: string;
    isReplay: true;
    file_attachments?: unknown[];
};

/**
 * Emitted by the bridge on opt-in graceful worker teardown (only when the teardown caller supplied a reason), before the heartbeat stops, so remote clients can show why the worker went away instead of waiting for heartbeat timeout. Absence is NOT a dead-host signal: handoffs (/update, /teleport, respawn), auto-disable, mode transitions, and internal fatal-error paths emit nothing by design. A dead host (battery, OOM, kill -9) never reaches teardown and never sends this either. NOTE: this event lands in the durable per-session event stream — a session that is later resumed may carry historical instances mid-stream. Clients MUST treat it as a live-tail signal only (honored when no further activity follows), not a one-shot session-lifetime fact.
 */
export declare type SDKWorkerShuttingDownMessage = {
    type: 'system';
    subtype: 'worker_shutting_down';
    /**
     * Short snake_case reason set by the host CLI (not user input), e.g. 'host_exit', 'remote_control_disabled'.
     */
    reason: string;
    uuid: UUID;
    session_id: string;
};

export declare type SessionCronSummary = {
    id: string;
    /**
     * Cron expression, e.g. "0 9 * * 1-5".
     */
    schedule: string;
    /**
     * False for one-shot wakeups whose cron field encodes a single fire time; true for tasks that re-fire on every match.
     */
    recurring: boolean;
    /**
     * Prompt text submitted when the cron fires. Capped at 1000 chars; clipped values append an in-string "… [+N chars]" marker.
     */
    prompt: string;
};

export declare type SessionEndHookInput = BaseHookInput & {
    hook_event_name: 'SessionEnd';
    reason: ExitReason;
};

/**
 * Identifies a session transcript or subagent transcript in the store.
 * Main transcripts have no subpath; subagent transcripts include a subpath
 * like 'subagents/agent-{id}' that mirrors the on-disk directory structure.
 * @alpha
 */
export declare type SessionKey = {
    /** Caller-defined scope. Default: sanitized cwd. Multi-tenant deployments
     *  should set this to a tenant ID or project name. Paths longer than 200
     *  characters are truncated and suffixed with a portable djb2 hash so the
     *  same path yields the same key under both Bun and Node.js. */
    projectKey: string;
    sessionId: string;
    /** Undefined = main transcript. Set for subagent files.
     *  Empty string is invalid — omit the field for the main transcript.
     *  Opaque to the adapter — just use it as a storage key suffix. */
    subpath?: string;
};

/**
 * A message from a session transcript.
 * Returned by `getSessionMessages` for reading historical session data.
 */
export declare type SessionMessage = {
    type: 'user' | 'assistant' | 'system';
    uuid: string;
    session_id: string;
    message: unknown;
    parent_tool_use_id: string | null;
    /**
     * agentId of the subagent that spawned this subagent, or null when this
     * message belongs to a depth-1 subagent (spawned by the main loop) or to
     * the main session itself. Sessions whose metadata lacks the field report
     * null.
     */
    parent_agent_id: string | null;
};

/**
 * Options shared by session mutation functions (renameSession, tagSession,
 * archiveSession, unarchiveSession, deleteSession, forkSession).
 */
export declare type SessionMutationOptions = {
    /**
     * Project directory path (same semantics as `listSessions({ dir })`).
     * When omitted, all project directories are searched for the session file.
     */
    dir?: string;
    /**
     * When provided, read/write session data via this store instead of the
     * local filesystem. archiveSession and unarchiveSession reject it.
     * @alpha
     */
    sessionStore?: SessionStore;
};

export declare type SessionStartHookInput = BaseHookInput & {
    hook_event_name: 'SessionStart';
    source: 'startup' | 'resume' | 'clear' | 'compact' | 'fork';
    agent_type?: string;
    model?: string;
    session_title?: string;
    /**
     * resume/fork: seconds since the resumed transcript's last assistant response
     */
    seconds_since_last_response?: number;
    /**
     * resume/fork: the resumed transcript's last response input + cache_read + cache_creation + output tokens (for a server-side tool loop, its last iteration's window, not the summed totals)
     */
    context_tokens?: number;
    /**
     * resume/fork: seconds_since_last_response exceeds the prompt-cache TTL, so the first request re-caches context_tokens
     */
    prompt_cache_likely_expired?: boolean;
    /**
     * resume/fork: estimated cost of re-caching context_tokens on the session model — the managed modelPricing when set, otherwise list price; excludes the response
     */
    estimated_cache_write_usd?: number;
};

export declare type SessionStartHookSpecificOutput = {
    hookEventName: 'SessionStart';
    additionalContext?: string;
    initialUserMessage?: string;
    sessionTitle?: string;
    watchPaths?: string[];
    /**
     * Re-scan skill and command directories after SessionStart hooks complete, so skills installed by the hook are available in the same session
     */
    reloadSkills?: boolean;
};

/**
 * Adapter for mirroring session transcripts to external storage.
 * The subprocess still writes to local disk (set CLAUDE_CONFIG_DIR=/tmp
 * for ephemeral local copy); the adapter receives a secondary copy.
 *
 * The SDK never deletes from your store unless you call deleteSession()
 * with delete? implemented. Retention is the adapter's responsibility —
 * implement TTL, S3 lifecycle policies, or scheduled cleanup according
 * to your compliance requirements (e.g., ZDR/HIPAA retention windows).
 * Local-disk transcripts under CLAUDE_CONFIG_DIR are swept by the
 * existing cleanupPeriodDays setting independently of this adapter.
 * @alpha
 */
export declare type SessionStore = {
    /**
     * Mirror a batch of transcript entries. Called AFTER the subprocess's
     * local write succeeds — durability is already guaranteed locally.
     *
     * Batches arrive at ~100ms cadence during active turns. Entries are
     * JSON-safe POJOs — one per line in the local JSONL file.
     *
     * Within a single process, persist entries in append-call order; across
     * concurrent processes, order is by storage commit time, not call time.
     *
     * Most entries carry a stable `uuid`. Adapters SHOULD treat `uuid` as an
     * idempotency key (upsert / ignore-duplicate) so that retries and
     * `importSessionToStore()` replays do not create duplicate rows. Entries
     * without a `uuid` (e.g. titles, tags, mode markers) should be appended
     * without dedup.
     *
     * Rejection is retried (3 attempts total) with short backoff; timeouts
     * (60s) are not retried since the in-flight call may still land. After
     * the final failure the batch is dropped and a `mirror_error` system
     * message is emitted. The subprocess continues unaffected.
     */
    append(key: SessionKey, entries: SessionStoreEntry[]): Promise<void>;
    /**
     * Load a full session for resume. Called once, in the SDK parent, before
     * subprocess spawn. The result is materialized to a temporary JSONL file;
     * the subprocess resumes from that file using its existing resume code.
     *
     * Return `null` for a key that was never written; adapters that cannot
     * distinguish "never written" from "emptied" (e.g. Redis LRANGE) may
     * return `null` for both. Returned entries must be deep-equal to what was
     * appended — byte-equal serialization is NOT required (e.g. Postgres
     * JSONB may reorder object keys); the SDK never hashes or byte-compares
     * entries.
     */
    load(key: SessionKey): Promise<SessionStoreEntry[] | null>;
    /**
     * List sessions for a projectKey. Returns IDs + modification times.
     * `mtime` is integer Unix epoch milliseconds (floor fractional sources);
     * adapters without native modification
     * time (e.g. Redis) must maintain their own index. Result order is
     * unspecified — the SDK sorts by mtime descending.
     * Optional — if undefined, listSessions() with a sessionStore throws.
     */
    listSessions?(projectKey: string): Promise<Array<{
        sessionId: string;
        mtime: number;
    }>>;
    /**
     * Return incrementally-maintained summaries for all sessions in one call.
     *
     * Stores should maintain these via {@link foldSessionSummary} inside
     * `append()`. When implemented, `listSessions({ sessionStore })` reads
     * all summary metadata in a single round-trip; when undefined, it falls
     * back to `listSessions()` + per-session `load()`.
     *
     * @remarks
     * Stores that maintain summaries inside `append()` MUST serialize sidecar
     * writes if `append()` calls can race for the same session — e.g., wrap the
     * read-fold-write in a transaction/CAS or hold a per-session lock.
     * `foldSessionSummary` is pure; concurrency control is the store's responsibility.
     * @alpha
     */
    listSessionSummaries?(projectKey: string): Promise<SessionSummaryEntry[]>;
    /**
     * Delete a session. Optional — if undefined, deletion is a no-op
     * (appropriate for WORM/append-only backends like S3).
     */
    delete?(key: SessionKey): Promise<void>;
    /**
     * List all subpath keys under a session (e.g., subagent transcripts).
     * Used during resume to discover and materialize all subagent data.
     * If undefined, resume only materializes the main transcript.
     */
    listSubkeys?(key: {
        projectKey: string;
        sessionId: string;
    }): Promise<string[]>;
};

/**
 * One JSONL transcript line as observed by a {@link SessionStore} adapter.
 *
 * The concrete entry shape is the on-disk transcript format (a large
 * discriminated union over `type` covering user/assistant messages, summaries,
 * titles, tags, mode changes, etc.). That union is CLI-internal and not part
 * of the SDK API surface, so this is exposed as a minimal structural supertype
 * — every entry has a string `type` discriminant, most carry a `uuid` and ISO
 * `timestamp`, and the rest of the payload is opaque JSON. Adapters should
 * treat entries as pass-through blobs; round-tripping `JSON.stringify` /
 * `JSON.parse` is the only required invariant.
 * @alpha
 */
export declare type SessionStoreEntry = {
    type: string;
    uuid?: string;
    timestamp?: string;
    [k: string]: unknown;
};

/**
 * Flush strategy for {@link Options.sessionStore} transcript mirroring.
 *
 * - `'batched'` (default): buffer transcript_mirror frames and flush at
 *   end-of-turn or when pending thresholds are exceeded.
 * - `'eager'`: schedule a background flush after every frame, giving
 *   near-real-time delivery to {@link SessionStore.append}. Each frame
 *   becomes its own `append()` batch (no coalescing), so adapters should
 *   be cheap per call.
 *
 * @alpha
 */
export declare type SessionStoreFlush = 'batched' | 'eager';

/**
 * Incrementally-maintained session summary.
 *
 * Stores update this on {@link SessionStore.append} via
 * {@link foldSessionSummary} and return the full set from
 * {@link SessionStore.listSessionSummaries}. Adapters never re-read
 * previously appended entries.
 * @alpha
 */
export declare type SessionSummaryEntry = {
    sessionId: string;
    /**
     * Storage write time of the sidecar on the adapter. Must share a clock
     * source with the `mtime` returned by `listSessions()` for this session —
     * typically file mtime, S3 LastModified, Postgres `updated_at`, or whatever
     * native timestamp the adapter surfaces. Do not derive from entry ISO
     * timestamps — entry timestamps and storage write times can differ by
     * batching and network latency, and conflating them defeats the staleness
     * check.
     */
    mtime: number;
    /** Opaque SDK-owned state. Stores MUST persist verbatim and MUST NOT interpret. */
    data: Record<string, unknown>;
};

/**
 * AUTO-GENERATED - DO NOT EDIT
 *
 * This file is auto-generated from the settings JSON schema.
 * To modify these types, edit SettingsSchema in src/utils/settings/types.ts and run:
 *
 *   bun scripts/generate-sdk-types.ts
 */
export declare interface Settings {
    /**
     * JSON Schema reference for Claude Code settings
     */
    $schema?: string;
    /**
     * Path to a script that outputs authentication values
     */
    apiKeyHelper?: string;
    /**
     * Shell command that outputs a Proxy-Authorization header value (EAP)
     */
    proxyAuthHelper?: string;
    /**
     * Path to a script that exports AWS credentials
     */
    awsCredentialExport?: string;
    /**
     * Path to a script that refreshes AWS authentication
     */
    awsAuthRefresh?: string;
    /**
     * Command to refresh GCP authentication (e.g., gcloud auth application-default login)
     */
    gcpAuthRefresh?: string;
    /**
     * Corporate launcher argv prefix for the background-agent supervisor, the sessions and workers it hosts, and the other covered background processes listed in the Claude Code corporate-launcher documentation. Equivalent to the CLAUDE_CODE_PROCESS_WRAPPER environment variable, which takes precedence when set. Honored from managed settings, a --settings/SDK-supplied settings file, and user settings, in that precedence order; project and local settings are ignored.
     */
    processWrapper?: string;
    /**
     * Executable that computes managed settings at startup. Honored only from admin-controlled policy sources.
     */
    policyHelper?: {
        /**
         * Absolute path to the helper executable
         */
        path: string;
        timeoutMs?: number;
        refreshIntervalMs?: 0 | number;
    };

    /**
     * Custom file suggestion configuration for \@ mentions
     */
    fileSuggestion?: {
        type: 'command';
        command: string;
    };
    /**
     * Whether file picker should respect .gitignore files (default: true). Note: .ignore files are always respected.
     */
    respectGitignore?: boolean;


    /**
     * Number of days to retain chat transcripts before automatic cleanup (default: 30). Minimum 1. Use a large value for long retention; use --no-session-persistence to disable transcript writes entirely. Cleanup deletes data only on this computer, not anything stored by Anthropic.
     */
    cleanupPeriodDays?: number;
    /**
     * Retention ceiling in days for session transcripts created or last written by a desktop-host surface (Claude Desktop, Cowork), which are otherwise exempt from the cleanupPeriodDays sweep. 0 (the default) means no ceiling: such transcripts are kept until deleted another way. Unlike cleanupPeriodDays, 0 is allowed because this setting never disables writes — it only bounds an exemption from deletion. The ceiling is a hard cap: it also bounds an active archive grace, so the grace window of a release marker never keeps files past the ceiling. Ignored when cleanupPeriodDays is managed by org policy. A ceiling at or below cleanupPeriodDays effectively disables the exemption: those transcripts age out on the regular cleanupPeriodDays schedule, so the effective retention is whichever of the two periods is longer. Cleanup deletes data only on this computer, not anything stored by Anthropic.
     */
    desktopSessionCleanupPeriodDays?: number;
    /**
     * Set to false to turn off syncing of the skills you have enabled on claude.ai. In your user settings (or managed settings): nothing more is downloaded, previously synced skills (~/.claude/skills/synced) can no longer be run, are hidden from every session started afterwards, and are moved to ~/.claude/skills/.trash at the next launch (deleted after cleanupPeriodDays; re-downloaded, not restored, if you re-enable). In .claude/settings.local.json or --settings: downloads stop and synced skills are blocked and hidden for sessions in that workspace or invocation only (nothing is moved). Not read from project settings (.claude/settings.json). Only false is honored — the feature is enabled server-side for your account, so setting true does not turn it on early. While it is on, synced skills are available in every session, re-synced about every 10 minutes while a session is in use and a quarter as often otherwise, and removed when you disable them on claude.ai. Only applies when signed in with your Claude account.
     */
    syncClaudeAiSkills?: boolean;
    /**
     * Set to false to turn off syncing of the plugins you have enabled on claude.ai. In your user settings (or managed settings): nothing more is downloaded, previously synced plugins (~/.claude/plugins/synced) are hidden from every session started afterwards and moved to ~/.claude/plugins/.trash at the next launch (deleted after cleanupPeriodDays; re-downloaded, not restored, if you re-enable). In .claude/settings.local.json or --settings: downloads stop and synced plugins are hidden for sessions in that workspace or invocation only (nothing is moved). Not read from project settings (.claude/settings.json). Only false is honored — the feature is enabled server-side for your account, so setting true does not turn it on early. While it is on, synced plugins load in every session like plugins you installed yourself (a plugin you installed with the same name takes precedence), are re-synced at each launch, and are removed when you disable them on claude.ai. Only applies when signed in with your Claude account.
     */
    syncClaudeAiPlugins?: boolean;
    /**
     * Per-skill description character cap in the skill listing sent to Claude (default: 1536). Descriptions longer than this are truncated. Raise to opt in to higher per-turn context cost.
     */
    skillListingMaxDescChars?: number;
    /**
     * Fraction of the context window (in characters) reserved for the skill listing sent to Claude (default: 0.01 = 1%). When the listing exceeds this, descriptions are shortened to fit. Raise to opt in to higher per-turn context cost.
     */
    skillListingBudgetFraction?: number;
    /**
     * When set to true in either admin-only Windows source — the HKLM SOFTWARE/Policies/ClaudeCode registry key or C:/Program Files/ClaudeCode/managed-settings.json — WSL reads managed settings from the full Windows policy chain (HKLM, C:/Program Files/ClaudeCode via DrvFs, HKCU) in addition to /etc/claude-code. Windows sources take priority. The flag is also required in HKCU itself for HKCU policy to apply on WSL (double opt-in: admin enables the chain, user confirms HKCU). On native Windows the flag has no effect.
     */
    wslInheritsWindowsSettings?: boolean;
    /**
     * Environment variables to set for Claude Code sessions
     */
    env?: {
        [k: string]: string;
    };
    /**
     * Customize attribution text for commits and PRs. Each field defaults to the standard Claude Code attribution if not set. Set to false to hide all attribution, the same as { "commit": "", "pr": "", "sessionUrl": false }. Setting it to true is the same as leaving it out. Older Claude Code versions reject true or false here, so use the object form in settings files shared across versions.
     */
    attribution?: boolean | {
        /**
         * Attribution text for git commits, including any trailers. Empty string hides attribution.
         */
        commit?: string;
        /**
         * Attribution text for pull request descriptions. Empty string hides attribution.
         */
        pr?: string;
        /**
         * Whether to append the claude.ai session link to commits and PRs created from web or Remote Control sessions (default: true). Set to false to omit the Claude-Session trailer and PR-body link.
         */
        sessionUrl?: boolean;
        [k: string]: unknown;
    };
    /**
     * The claude.ai Project this session names for your organization's usage reports: the Project's ID, starting with "claude_proj_" or "chan_", or the UUID of a "claude_proj_" Project. An empty string names none and stops lower-precedence files from naming one; the organization default still applies. A Project is sent only when Claude Code uses your claude.ai login, connects directly to the Anthropic API, is not in a cloud session, and CLAUDE_CODE_ATTRIBUTION_HEADER is not 0. CLAUDE_CODE_ATTRIBUTION_PROJECT takes precedence over it. Set in managed settings, it overrides people's own settings files. A project's .claude/settings.json and settings.local.json count only once the folder is trusted; for runs in a folder nobody has trusted, such as CI, use CLAUDE_CODE_ATTRIBUTION_PROJECT. Behind a Claude apps gateway that reports usage by group, name one of your groups instead, such as "payments"; CLAUDE_CODE_ATTRIBUTION_HEADER does not affect that.
     */
    attributionProject?: string;
    /**
     * Your organization's default for attributionProject. Only honored from managed settings (server-managed, MDM / OS policy, or managed-settings.json); ignored in user, project, local and --settings sources.
     */
    attributionProjectPolicy?: {
        /**
         * The Project used when neither CLAUDE_CODE_ATTRIBUTION_PROJECT nor attributionProject names one: its ID, starting with "claude_proj_" or "chan_", or the UUID of a "claude_proj_" Project. Behind a Claude apps gateway that reports usage by group, a group name instead.
         */
        default?: string;
    };
    /**
     * Deprecated: Use attribution instead. Whether to include Claude's co-authored by attribution in commits and PRs (defaults to true)
     */
    includeCoAuthoredBy?: boolean;
    /**
     * Include built-in commit and PR workflow instructions in Claude's system prompt (default: true)
     */
    includeGitInstructions?: boolean;
    /**
     * Tool usage permissions configuration
     */
    permissions?: {
        /**
         * List of permission rules for allowed operations
         */
        allow?: string[];
        /**
         * List of permission rules for denied operations
         */
        deny?: string[];
        /**
         * List of permission rules that should always prompt for confirmation
         */
        ask?: string[];
        /**
         * Default permission mode when Claude Code needs access ('manual' is accepted as an alias for 'default')
         */
        defaultMode?: 'acceptEdits' | 'auto' | 'bypassPermissions' | 'default' | 'dontAsk' | 'plan';
        /**
         * Disable the ability to bypass permission prompts
         */
        disableBypassPermissionsMode?: 'disable';
        /**
         * Refuse file-tool reads (Read, Grep, Glob, LSP) outside the working directories in every permission mode; true in any settings source wins. No allow rule lifts it. Also binds shell commands: one that names a path outside them is asked about in every mode, and the sandbox, where it is on, denies such reads. Also set when the user picks "block" on the one-time auto-mode prompt for a read outside the working directories.
         */
        blockReadsOutsideWorkingDirectories?: boolean;

        /**
         * Refuse file-tool writes (Write, Edit, NotebookEdit) outside the working directories in every permission mode; true in any settings source wins. No allow rule lifts it. Files that Claude Code keeps for the session are not refused: its plan files, scratchpad and background job folder, and the auto-memory of this project, unless a repository settings file points it elsewhere (a setting of the program that starts Claude Code can narrow this and the working directories). Nothing runs them unless the model asks. Also refuses file-tool writes to Claude Code settings files, inside the working directories too, and takes EnterWorktree and ExitWorktree, which move the working directory, out of the tools on offer (a setting of the program that starts Claude Code can keep them). Does not limit shell commands, MCP tools, the programs that hooks run, or the memory tools. Cloud sessions (Claude Code on the web), whose file tools run in a container that is itself the boundary, may not apply it.
         */
        blockWritesOutsideWorkingDirectories?: boolean;
        /**
         * For the program that starts Claude Code: read only from --settings and from settings that program sends while the session runs; ignored in user, project, local and managed settings. Absolute paths, each a folder with all below it or one file, that blockReadsOutsideWorkingDirectories lets through beside the working directories. It allows nothing: an allow rule, the permission mode or the user still decides each read, as with that setting off, and a shell command that hands such a path to a program is still asked about unless a Read allow rule covers it. The paths do not become working directories, so blockWritesOutsideWorkingDirectories refuses writes to them, and they are not told to MCP servers or to the model. Each path counts as written: a link in it is not followed and a pattern is not expanded, so list every spelling that a read may arrive by. Ignored: an entry that starts with ~, has a ".." segment or has white space at either end (as written or once normalized), a relative or network path, and the root of a filesystem. Does not change what sandboxed commands may read (sandbox.filesystem.allowRead does).
         */
        blockReadsExemptPaths?: string[];
        /**
         * For the program that starts Claude Code: read only from --settings and from settings that program sends while the session runs; ignored in user, project, local and managed settings. Absolute paths of working directories, each spelled exactly as it is passed, letter case included (the session folder, --add-dir, permissions.additionalDirectories). To decide what lies inside a listed working directory, Claude Code takes it as written and follows no link at it, so a link that later stands in its place gives the file tools no access to where the link leads. List real paths: the files of a listed path that runs through a link count as outside the working directories, because where they really are lies outside it. List a mapped network drive by its drive-letter path: Claude Code still derives the UNC form of that path by itself and adds it, as for any mapped drive. A file path that is itself spelled as a UNC path is judged as written, so a link on the share is not seen by that spelling. It adds no working directory and allows nothing. Once listed, a path stays so until the process ends, also if later settings leave it out. Ignored: an entry that is not already normalized (a relative path, one that starts with ~, a ".." segment, a separator at its end unless it is a filesystem root, forward slashes on Windows, white space at either end). Does not change what sandboxed commands may write.
         */
        workingDirectoriesAsGiven?: string[];
        /**
         * For the program that starts Claude Code: read only from --settings and from settings that program sends while the session runs; ignored in user, project, local and managed settings. Absolute paths, each a folder with all below it or one file, that blockReadsOutsideWorkingDirectories, blockFileToolReadsOutsideWorkingDirectories and blockWritesOutsideWorkingDirectories count as outside every working directory that holds them. A path is refused if it, or where its links lead, lies in a listed path, in any letter case, or above one that no Read deny rule covers (a Grep or Glob rooted there would walk into it; a deny rule keeps those two out, unless a "!" rule is also in force); for a search the path judged is its root, not each file found below it. Still let through: a working directory, or for reads a path of blockReadsExemptPaths, that is the listed path or lies inside it, and the files that Claude Code keeps for the session. It allows nothing, binds what those three settings bind, and does nothing with all of them off. Each path counts as written: a link in it is not followed, so list every spelling. Once listed, a path stays listed for the life of the process. Ignored: a relative path, and one that starts with ~, has a ".." segment or has white space at either end. Does not change what sandboxed commands may read or write.
         */
        workingDirectoriesExclude?: string[];
        /**
         * Disable auto mode
         */
        disableAutoMode?: 'disable';
        /**
         * Never wait for a person to answer a tool permission prompt: a call that would prompt is denied at once, the model is told, and the turn carries on. This is what --permission-prompts none does for -p, in every kind of session, subagents and agent teams included. Allow rules, the permission mode, auto mode's classifier and PermissionRequest hooks decide first, as they do without it; it only ever denies, and allows nothing. Claude's questions and plan mode's tools are not offered to the model, and an MCP server's request for input is cancelled unless an Elicitation hook answers it. An app or script that answers prompts through canUseTool or --permission-prompt-tool is not asked either: answer from a PermissionRequest hook instead. Read from user settings, --settings and managed settings; project and local settings are ignored, and true in any of those sources wins.
         */
        denyInsteadOfPrompting?: boolean;
        /**
         * Additional directories to include in the permission scope
         */
        additionalDirectories?: string[];
        [k: string]: unknown;
    };

    /**
     * Override the default model used by Claude Code
     */
    model?: string;
    /**
     * Fallback model(s) tried in order when the primary model is overloaded or unavailable. Each element accepts a model name or alias; "default" expands to the default model. CLI --fallback-model takes precedence.
     */
    fallbackModel?: string[];
    /**
     * Allowlist of models that users can select. Accepts family aliases ("opus" allows any opus version), version prefixes ("opus-4-5" allows that version and any model ID that extends it, so "claude-opus-5" also allows "claude-opus-5-5"), and full model IDs. An entry with a path before the model ID (a gateway route such as "route/claude-opus-5") does not allow the plain ID ("claude-opus-5"): list the plain ID too if some sessions send requests directly to the Anthropic API. If undefined, all models are available. If empty array, only the default model is available. Typically set in managed settings by enterprise administrators.
     */
    availableModels?: string[];
    /**
     * When true and availableModels is a non-empty array, the Default model selection is also constrained: if the default model for the user tier is not in availableModels, Default resolves to the first allowed availableModels entry instead. Has no effect when availableModels is unset or an empty array. Typically set in managed settings by enterprise administrators.
     */
    enforceAvailableModels?: boolean;
    /**
     * How availableModels entries match model IDs. "prefix" (the default) lets an entry also allow any model ID that extends it, so "claude-opus-5" allows "claude-opus-5-5". "exact" keeps that matching but stops a model ID entry from allowing other versions: "claude-opus-5" allows Opus 5 and its dated and -fast IDs, but not Opus 5.5 or a later release until it is listed, and a -latest ID needs a -latest entry. Family aliases ("opus") still allow the whole family; aliases whose model depends on the release or settings (best, opusplan, default) are ignored. With "exact" and a list that names at least one model, the Default option also uses only a listed model; if none can be used, Claude Code will not start. Haiku background models, and hooks and other helper requests that pick their own model, are not restricted (deniedModels covers them; allowManagedHooksOnly limits hooks). Read from managed settings only.
     */
    availableModelsMatch?: 'prefix' | 'exact';
    /**
     * Models users cannot select, even when availableModels allows them. A family alias ("opus") blocks that family. A model ID blocks that version in every spelling: dates, -fast and provider prefixes are ignored, so "claude-opus-5-5" blocks every Opus 5.5 ID but not Opus 5. An ID with no minor version ("claude-opus-5") also blocks later minor versions, as it allows them in availableModels. Aliases whose model depends on the release or settings (best, opusplan, default) are ignored. The Default option steps down past a blocked model; if the Default has no allowed model to step down to, Claude Code will not start. Read from managed settings only.
     */
    deniedModels?: string[];
    /**
     * Override mapping from Anthropic model ID (e.g. "claude-opus-4-6") to provider-specific model ID (e.g. a Bedrock inference profile ARN). Typically set in managed settings by enterprise administrators.
     */
    modelOverrides?: {
        [k: string]: string;
    };
    /**
     * Curate the /model picker: an ordered list of models with your own labels, independent of the built-in lineup and of Claude Code releases. availableModels still applies to these rows. Honored from managed, --settings/SDK, and user settings only (not from a project checkout); the highest-precedence of those that defines modelPicker wins outright (no merging across sources). Typically set in managed settings by enterprise administrators.
     */
    modelPicker?: {
        /**
         * Rows to show in the /model picker, in order.
         */
        options: {
            /**
             * Model to select, taken verbatim: an alias ("opus"), an Anthropic model ID, or a provider-format ID (Vertex, Bedrock, gateway). Same values --model accepts.
             */
            model: string;
            /**
             * Row title. Defaults to the model name.
             */
            label?: string;
            /**
             * Row subtitle. Defaults to a generic description.
             */
            description?: string;
            /**
             * For a model this version of Claude Code does not know: the ID of a model it does know (e.g. "claude-opus-4-8") whose client-side handling — prompt profile, capability and effort defaults — applies to it. Changes neither the row's label nor the model ID sent. Without it, a model-catalog row for a model this version does not know is not offered until Claude Code is updated.
             */
            behavesAs?: string;
        }[];
        /**
         * When true, the picker shows only the Default row and these options — the built-in lineup, gateway-discovered models and ANTHROPIC_CUSTOM_MODEL_OPTION are hidden. When false or unset, these options are added after the built-in lineup.
         */
        replaceBuiltInOptions?: boolean;
    };
    /**
     * Price usage at your organization's contracted rates instead of list price. Affects every spend figure Claude Code reports — /cost, the status line, the SDK total_cost_usd, --max-budget-usd, and the OpenTelemetry cost metric and events — which remain USD estimates, not an invoice (the per-Mtok price labels in /model stay at list). "overrides" maps a model ID to its USD-per-million-token rates (input, output, cacheRead, cacheWrite — all four required, each 0 to 10000; cacheWrite prices both 5-minute and 1-hour cache writes). A matching row is charged exactly as written; fast-mode and US-data-residency surcharges are not added on top. A key Claude Code itself uses for a built-in model — its ID such as "claude-sonnet-4-6", or its first-party, Bedrock (any or no region prefix), Vertex or Foundry ID — covers every dated and provider form of that model; any other key — a gateway model alias, or a spelling Claude Code does not itself use — matches that model ID only (case-insensitive), and such an exact match wins over a built-in row. On Bedrock an application inference profile is matched by its backing model. An invalid row or multiplier is reported and skipped; the rest still apply. "multiplier" in (0, 10] scales every computed cost, overridden or not (0.85 = 85% of the price, 1.2 = 120%). Only honored from managed settings (server-managed, MDM / OS policy, or managed-settings.json), or — when none of those sets it — when supplied by a host application that manages the model provider; ignored in user, project, local and --settings sources.
     */
    modelPricing?: {
        multiplier?: number;
        overrides?: {
            [k: string]: {
                input: number;
                output: number;
                cacheRead: number;
                cacheWrite: number;
            };
        };
    };
    /**
     * Whether to automatically approve all MCP servers in the project
     */
    enableAllProjectMcpServers?: boolean;
    /**
     * List of approved MCP servers from .mcp.json
     */
    enabledMcpjsonServers?: string[];
    /**
     * List of rejected MCP servers from .mcp.json
     */
    disabledMcpjsonServers?: string[];
    /**
     * When true in any settings source, claude.ai MCP cloud connectors are not auto-fetched or connected, and a claudeai-proxy server passed explicitly (e.g. via --mcp-config or the SDK mcpServers option) does not connect either. Where a managed or served source sets it, the connectors that the desktop app's Code tab hands to a session do not connect either, from the app version that shows them as turned off. Any-source-true wins: a project can opt out, but a project-level false cannot override a user-level true.
     */
    disableClaudeAiConnectors?: boolean;
    /**
     * Per-skill listing overrides keyed by skill name. "name-only" lists the skill without its description; "user-invocable-only" hides it from the model but keeps /name; "off" hides it from both. Absent = on.
     */
    skillOverrides?: {
        [k: string]: 'on' | 'name-only' | 'user-invocable-only' | 'off';
    };
    /**
     * Disable the skills and workflows that ship with Claude Code: bundled skills and workflows are removed entirely; built-in slash commands stay typable but are hidden from the model. Plugins, .claude/skills/, and .claude/commands/ are unaffected. Equivalent to CLAUDE_CODE_DISABLE_BUNDLED_SKILLS=1.
     */
    disableBundledSkills?: boolean;
    /**
     * MCP servers the organization provides to every user, keyed by server name, each with the .mcp.json entry shape; only "http" and "sse" servers are accepted (nothing that names a program to run, no ${VAR} references). Honored from managed settings only; users cannot remove them, deniedMcpServers still applies, and they need no allowedMcpServers entry. Not read in Claude Desktop's Code tab on a third-party deployment or in Cowork sessions, where Claude Desktop supplies and locks the session's MCP servers itself.
     */
    managedMcpServers?: {
        [k: string]: {
            [k: string]: unknown;
        };
    };
    /**
     * Enterprise allowlist of the MCP servers users may use. Governs servers users add (user, project and local config, --mcp-config, agent frontmatter, plugins, claude.ai connectors); servers the organization itself delivers (managedMcpServers, and managed-mcp.json entries with no ${VAR} in their command, args, url or header values) are allowed without being listed; a managed-mcp.json entry with ${VAR} in any of those must match this list. An entry found only in a project's .claude/settings.json or .claude/settings.local.json can admit a server the organization provides (managed-mcp.json, managedMcpServers, or a plugin that managed settings list in enabledPlugins) but can't keep one out. If undefined, all servers are allowed. If empty array, users can use no servers of their own. Denylist takes precedence - if a server is on both lists, it is denied.
     */
    allowedMcpServers?: {
        /**
         * Name of the MCP server that users are allowed to configure
         */
        serverName?: string;
        /**
         * Command array [command, ...args] to match exactly for allowed stdio servers
         *
         * \@minItems 1
         */
        serverCommand?: [string, ...string[]];
        /**
         * URL pattern with wildcard support (e.g., "https://*.example.com/*") for allowed remote MCP servers
         */
        serverUrl?: string;
    }[];
    /**
     * Enterprise denylist of MCP servers that are explicitly blocked. If a server is on the denylist, it will be blocked across all scopes including enterprise. An entry found only in a project's .claude/settings.json or .claude/settings.local.json does not apply to a server the organization provides (managed-mcp.json, managedMcpServers, or a plugin that managed settings list in enabledPlugins). Denylist takes precedence over allowlist - if a server is on both lists, it is denied.
     */
    deniedMcpServers?: {
        /**
         * Name of the MCP server that is explicitly blocked
         */
        serverName?: string;
        /**
         * Command array [command, ...args] to match exactly for blocked stdio servers
         *
         * \@minItems 1
         */
        serverCommand?: [string, ...string[]];
        /**
         * URL pattern with wildcard support (e.g., "https://*.example.com/*") for blocked remote MCP servers. A pattern with no query also blocks the URL with any query, or with a trailing slash added or, if its path has no wildcard, removed.
         */
        serverUrl?: string;
    }[];
    /**
     * Custom commands to run before/after tool executions
     */
    hooks?: {
        [k: string]: {
            /**
             * String pattern to match (e.g. tool names like "Write")
             */
            matcher?: string;
            /**
             * List of hooks to execute when the matcher matches
             */
            hooks: ({
                /**
                 * Shell command hook type
                 */
                type: 'command';
                /**
                 * Shell command to execute
                 */
                command: string;
                /**
                 * Argument list for exec form. When present, `command` is resolved as an executable and spawned directly with these arguments — no shell. Path placeholders like ${CLAUDE_PLUGIN_ROOT} are substituted per-element as plain strings, so paths with quotes, $, or backticks never reach a shell parser. When absent, `command` runs through a shell (bash on POSIX, PowerShell on Windows without Git Bash).
                 */
                args?: string[];
                /**
                 * Permission rule syntax to filter when this hook runs (e.g., "Bash(git *)"). Only runs if the tool call matches the pattern. Avoids spawning hooks for non-matching commands.
                 */
                if?: string;
                /**
                 * Shell interpreter. 'bash' uses your $SHELL (bash/zsh/sh); 'powershell' uses pwsh. Defaults to bash (powershell on Windows without Git Bash).
                 */
                shell?: 'bash' | 'powershell';
                /**
                 * Timeout in seconds for this specific command
                 */
                timeout?: number;
                /**
                 * What a failure of this hook does: it could not start (a missing script or plugin directory), timed out, exited with a code other than 0 or 2, or printed JSON that is invalid or fails validation. 'continue' (default): the failure is reported and the action goes ahead. 'block': the failure counts as exit code 2, so the action the event guards (a tool call, a permission request, a prompt) is blocked. Ignored for async hooks and on Stop, SubagentStop, TaskCompleted and TeammateIdle.
                 */
                onFailure?: 'continue' | 'block';
                /**
                 * Custom status message to display in spinner while hook runs
                 */
                statusMessage?: string;
                /**
                 * If true, hook runs once and is removed after execution
                 */
                once?: boolean;
                /**
                 * If true, hook runs in background without blocking
                 */
                async?: boolean;
                /**
                 * If true, hook runs in background and wakes the model on exit code 2 (blocking error). Implies async.
                 */
                asyncRewake?: boolean;




            } | {
                /**
                 * LLM prompt hook type
                 */
                type: 'prompt';
                /**
                 * Prompt to evaluate with LLM. Use $ARGUMENTS placeholder for hook input JSON.
                 */
                prompt: string;
                /**
                 * Permission rule syntax to filter when this hook runs (e.g., "Bash(git *)"). Only runs if the tool call matches the pattern. Avoids spawning hooks for non-matching commands.
                 */
                if?: string;
                /**
                 * Timeout in seconds for this specific prompt evaluation
                 */
                timeout?: number;
                /**
                 * Model to use for this prompt hook (e.g., "claude-sonnet-5"). If not specified, uses the default small fast model.
                 */
                model?: string;
                /**
                 * Sets the continue value for the decision:"block" produced when ok is false. Default false (turn ends). Whether continue:true lets the turn proceed depends on the event's decision:"block" semantics. On PostToolUse, the reason is fed back to Claude and the turn continues.
                 */
                continueOnBlock?: boolean;
                /**
                 * Custom status message to display in spinner while hook runs
                 */
                statusMessage?: string;
                /**
                 * If true, hook runs once and is removed after execution
                 */
                once?: boolean;
            } | {
                /**
                 * Agentic verifier hook type
                 */
                type: 'agent';
                /**
                 * Prompt describing what to verify (e.g. "Verify that unit tests ran and passed."). Use $ARGUMENTS placeholder for hook input JSON.
                 */
                prompt: string;
                /**
                 * Permission rule syntax to filter when this hook runs (e.g., "Bash(git *)"). Only runs if the tool call matches the pattern. Avoids spawning hooks for non-matching commands.
                 */
                if?: string;
                /**
                 * Timeout in seconds for agent execution (default 60)
                 */
                timeout?: number;
                /**
                 * Model to use for this agent hook (e.g., "claude-sonnet-5"). If not specified, uses Haiku.
                 */
                model?: string;
                /**
                 * Custom status message to display in spinner while hook runs
                 */
                statusMessage?: string;
                /**
                 * If true, hook runs once and is removed after execution
                 */
                once?: boolean;
            } | {
                /**
                 * HTTP hook type
                 */
                type: 'http';
                /**
                 * URL to POST the hook input JSON to
                 */
                url: string;
                /**
                 * Permission rule syntax to filter when this hook runs (e.g., "Bash(git *)"). Only runs if the tool call matches the pattern. Avoids spawning hooks for non-matching commands.
                 */
                if?: string;
                /**
                 * Timeout in seconds for this specific request
                 */
                timeout?: number;
                /**
                 * What a failure of this hook does: it could not start (a missing script or plugin directory), timed out, exited with a code other than 0 or 2, or printed JSON that is invalid or fails validation. 'continue' (default): the failure is reported and the action goes ahead. 'block': the failure counts as exit code 2, so the action the event guards (a tool call, a permission request, a prompt) is blocked. Ignored for async hooks and on Stop, SubagentStop, TaskCompleted and TeammateIdle.
                 */
                onFailure?: 'continue' | 'block';
                /**
                 * Additional headers to include in the request. Values may reference environment variables using $VAR_NAME or ${VAR_NAME} syntax (e.g., "Authorization": "Bearer $MY_TOKEN"). Only variables listed in allowedEnvVars will be interpolated. Content-Length and Transfer-Encoding given here are ignored: Claude Code works out the request's length from its body.
                 */
                headers?: {
                    [k: string]: string;
                };
                /**
                 * Explicit list of environment variable names that may be interpolated in header values. Only variables listed here will be resolved; all other $VAR references are left as empty strings. Required for env var interpolation to work.
                 */
                allowedEnvVars?: string[];
                /**
                 * Custom status message to display in spinner while hook runs
                 */
                statusMessage?: string;
                /**
                 * If true, hook runs once and is removed after execution
                 */
                once?: boolean;

            } | {
                /**
                 * MCP tool hook type
                 */
                type: 'mcp_tool';
                /**
                 * Name of an already-configured MCP server to invoke
                 */
                server: string;
                /**
                 * Name of the tool on that server to call
                 */
                tool: string;
                /**
                 * Arguments passed to the MCP tool. String values support ${path} interpolation from the hook input JSON (e.g. "${tool_input.file_path}").
                 */
                input?: {
                    [k: string]: unknown;
                };
                /**
                 * Permission rule syntax to filter when this hook runs (e.g., "Bash(git *)"). Only runs if the tool call matches the pattern. Avoids spawning hooks for non-matching commands.
                 */
                if?: string;
                /**
                 * Timeout in seconds for this specific tool call
                 */
                timeout?: number;
                /**
                 * What happens when this hook's call fails: its MCP server is not connected or not signed in, the call times out or returns an error, or the tool answers with JSON that fails validation. 'continue' (default): the failure is reported and the action goes ahead. 'block': the action the event guards (a tool call, a permission request, a prompt) is blocked each time, for as long as the call fails. With 'block', the tool must answer with a hook's JSON output, with {} or with nothing: plain text, an image, or JSON that holds none of a hook output's fields, or only 'reason', also counts as a failure. That does not hold on PreCompact and WorktreeCreate, where plain text is the hook's answer, or on events whose block stops nothing. Any other value reads as 'block'. Ignored on Setup, SessionStart, Stop, SubagentStop, TaskCompleted and TeammateIdle.
                 */
                onFailure?: 'continue' | 'block';
                /**
                 * Custom status message to display in spinner while hook runs
                 */
                statusMessage?: string;
                /**
                 * If true, hook runs once and is removed after execution
                 */
                once?: boolean;
            })[];
        }[];
    };
    /**
     * Git worktree configuration: the CLI --worktree flag, EnterWorktree and agent isolation, plus the location Claude Code Desktop uses for SSH-session worktrees on this machine.
     */
    worktree?: {
        /**
         * Directories to symlink from main repository to worktrees to avoid disk bloat. Must be explicitly configured - no directories are symlinked by default. Common examples: "node_modules", ".cache", ".bin"
         */
        symlinkDirectories?: string[];
        /**
         * Directories to include when creating worktrees, via git sparse-checkout (cone mode). Dramatically faster in large monorepos — only the listed paths are written to disk.
         */
        sparsePaths?: string[];
        /**
         * Which ref new worktrees branch from. 'fresh' (default) branches from origin/<default-branch> for a clean tree. 'head' branches from your current local HEAD so unpushed commits and feature-branch state are present. Applies to --worktree, EnterWorktree, and agent isolation.
         */
        baseRef?: 'fresh' | 'head';
        /**
         * Isolation mode for background sessions in this repo. 'worktree' (default) blocks Edit/Write in the main checkout until EnterWorktree is called. 'none' lets background jobs edit the working copy directly.
         */
        bgIsolation?: 'worktree' | 'none';
        /**
         * Directory under which Claude Code Desktop creates the worktrees of SSH sessions that run on this machine (an absolute path or one starting with ~/), instead of <project>/.claude/worktrees. Read by the desktop app from the SSH host user settings; a location chosen in the desktop app's SSH connection settings takes precedence. The CLI (--worktree, EnterWorktree, agent isolation) does not read it yet.
         */
        location?: string;
    };
    /**
     * Disable all hooks and statusLine execution: the hooks defined in settings files and by installed plugins. Features built into Claude Code are not hooks in this sense and keep working; each has its own switch.
     */
    disableAllHooks?: boolean;
    /**
     * Disable the reply check in Claude Tag sessions on a self-hosted runner. The check re-prompts Claude, at most four times a turn, when a turn ends without a call to one of Claude Tag's reply tools. It is not a hook, so disableAllHooks does not affect it. Disabling it also stops two messages to Claude that Anthropic's service can request for such a session: a nudge after a long stretch of work with no visible update, and a reminder added to prompts. Claude Code's built-in reminder to give progress updates, on models that have it, is then no longer held back. Set it in managed settings; false there keeps the check on. Everywhere else it is ignored and the check stays on. Has no effect on sessions that Anthropic hosts.
     */
    disableReplyCheck?: boolean;
    /**
     * Disable agent view (`claude agents`, `--bg`, /background, the on-demand daemon). Typically set in managed settings. Equivalent to CLAUDE_CODE_DISABLE_AGENT_VIEW=1.
     */
    disableAgentView?: boolean;
    /**
     * Disable Remote Control (claude.ai/code, `claude remote-control`, `--remote-control`/`--rc`, auto-start, and the in-session toggle). Typically set in managed settings.
     */
    disableRemoteControl?: boolean;
    /**
     * Disable the Workflows feature. Code Review on pull requests and /ultrareview run in Anthropic's cloud and are not stopped by this setting, except an /ultrareview that has to restart partway through. A machine that runs a review itself refuses it when that machine's own administrator set this, or CLAUDE_CODE_DISABLE_WORKFLOWS in an `env` block, in its managed settings (MDM, the managed-settings file or an administrator's policy helper). Set in the environment before Claude Code starts, CLAUDE_CODE_DISABLE_WORKFLOWS disables Workflows. Beyond the cases above it stops a review only when the review's own session starts with it set.
     */
    disableWorkflows?: boolean;
    /**
     * Deprecated: use enableArtifact: false. Still honored — true turns Artifacts off; false is ignored.
     */
    disableArtifact?: boolean;
    /**
     * Turn Artifacts on or off. Off in any of managed, --settings, or user settings wins; project and local settings can only turn it off. Unset defaults to on once the feature is available.
     */
    enableArtifact?: boolean;
    /**
     * Enable or disable the Workflows feature for this user. Unset = default by plan once the feature is available.
     */
    enableWorkflows?: boolean;
    /**
     * Advisory size guideline for the dynamic workflows Claude writes: "small" aims for fewer than 5 agents, "medium" fewer than 10, "large" fewer than 50, and "unrestricted" sends no guideline. Unset defaults to "medium", or "small" on Pro plans. A value here — including from managed settings — takes precedence over the "Dynamic workflow size" choice in /config, and that /config row is hidden while a settings file provides the key. This is a guideline, not an enforced limit.
     */
    workflowSizeGuideline?: 'unrestricted' | 'small' | 'medium' | 'large';
    /**
     * Enable the "ultracode" keyword trigger: including the keyword in a prompt opts that turn into the Workflow tool. Set to false to disable the trigger. Default: true.
     */
    workflowKeywordTriggerEnabled?: boolean;
    /**
     * Disable inline shell execution in skills and custom slash commands from user, project, or plugin sources. Commands are replaced with a placeholder instead of being run.
     */
    disableSkillShellExecution?: boolean;
    /**
     * Windows only. Set to true to keep every Bash command in a single argument to bash, so that endpoint security tools that match text in process command lines see it whole. Otherwise Claude Code may split a long command over several arguments. With true, a command of about 7,000 characters or more, or fewer if it is full of quotes, may reach bash cut short, and then usually fails with a syntax error. Only honored from managed settings; ignored in user, project, local and --settings sources.
     */
    disableWindowsBashCommandSplit?: boolean;
    /**
     * Default shell for input-box ! commands. Defaults to 'bash' on all platforms (no Windows auto-flip).
     */
    defaultShell?: 'bash' | 'powershell';
    /**
     * Whether the Bash tool shows a diff of the files a Bash command changed (PostToolUse Bash hooks get the changed-file list in tool_response). Set to false to turn that off. Default: off, except in auto and bypassPermissions modes when the Bash tool handles file edits or the model's configuration turns it on. Only user, flag or policy settings can turn it on in other modes.
     */
    bashEditDiffEnabled?: boolean;
    /**
     * How many characters of a successful Bash or PowerShell command's output Claude receives inline (default 30000; values clamp to 4000-128000). Output past this is saved to a file and Claude receives a short preview plus the path. When set, this also replaces BASH_MAX_OUTPUT_LENGTH, which on its own only sizes the read-back window.
     */
    bashOutputMaxChars?: number;
    /**
     * Deprecated: no longer has any effect (the TaskOutput tool was removed). Read a background task's output file with the Read tool instead.
     */
    taskOutputMaxChars?: number;
    /**
     * Whether Claude responds after an input-box ! bash command runs. Set to false to add the command output to context without a response. Default: true.
     */
    respondToBashCommands?: boolean;
    /**
     * When true (and set in managed settings), only hooks from managed settings and from plugins that managed settings enable run. User, project, and local hooks and the hooks of plugins the user installed are ignored. Features built into Claude Code are not hooks in this sense and keep working.
     */
    allowManagedHooksOnly?: boolean;
    /**
     * Allowlist of URL patterns that HTTP hooks may target. Supports * as a wildcard (e.g. "https://hooks.example.com/*"). When set, HTTP hooks with non-matching URLs are blocked. If undefined, all URLs are allowed. If empty array, no HTTP hooks are allowed. Arrays merge across settings sources (same semantics as allowedMcpServers). Where managed settings do not set this list, a list in any other settings file does not apply to hooks that managed settings define, or that come from a plugin they enable from a local folder they name.
     */
    allowedHttpHookUrls?: string[];
    /**
     * Allowlist of environment variable names HTTP hooks may interpolate into headers. When set, each hook's effective allowedEnvVars is the intersection with this list. If undefined, no restriction is applied. Arrays merge across settings sources (same semantics as allowedMcpServers). Where managed settings do not set this list, a list in any other settings file does not apply to hooks that managed settings define, or that come from a plugin they enable from a local folder they name.
     */
    httpHookAllowedEnvVars?: string[];
    /**
     * When true (and set in managed settings), permission rules from user, project, local, and --settings files and allow rules from --allowedTools are ignored; only managed settings can add allow rules through settings. The allowed-tools frontmatter of skills and custom commands from user, project, and --add-dir sources, and of plugins no managed setting vouches for, is ignored too. Plugins keep theirs only on an admin-backed channel: host-delivered --plugin-dir plugins (in Claude Desktop, only while this is not set by the organization's own managed settings), the official marketplace registered from its unpinned anthropics source, claude.ai-synced plugins Anthropic attests, the saved login organization's claude.ai-hosted marketplaces, marketplaces whose registered source managed extraKnownMarketplaces declares or an exact or owner-pinned (owner/*) strictKnownMarketplaces entry names at the path it pins (an npm marketplace source only when the registration and the declared entry pin the same registry, and a settings marketplace source only when every nested npm plugin entry pins one on a bare package name — unpinned, the package resolves through the member's own npm config, and a non-bare spelling packs as an exotic spec the pin does not bind, so nothing an entry names is what was fetched) (host and path patterns and enabledPlugins ids do not vouch); managed and bundled skills keep theirs. --disallowedTools, skill disallowed-tools, and other deny and ask rules from the command line or the current session still apply.
     */
    allowManagedPermissionRulesOnly?: boolean;
    /**
     * When true (and set in managed settings), allowedMcpServers is only read from managed settings. deniedMcpServers still merges from all sources, so users can deny servers for themselves, in user settings for a server the organization provides. Users can still add their own MCP servers, but only the admin-defined allowlist applies.
     */
    allowManagedMcpServersOnly?: boolean;
    /**
     * Claude desktop app only. Where your allow list and deny list apply to MCP servers added in the Claude desktop app. "code" (default): Your allow list also governs MCP servers added in the Claude desktop app, in Code tab sessions and the Artifact pane. "all": Your allow list and your deny list also govern MCP servers added in the Claude desktop app, in every tab (including Chat and Cowork). "off": Your allow list doesn't govern MCP servers added in the Claude desktop app. Read only from managed settings. Any other value counts as `all`. Where sources are merged or mixed, `off` counts as `all`. Leave the key out, or set it only in the managed source that holds your list. `deniedMcpServers` applies in Code tab sessions and the Artifact pane with every value, and in every tab with `all`. MCP servers sent to SSH hosts are not governed by these lists in this release. The Claude Code CLI reads nothing from this key, but written alone in a higher managed source it makes that source lead, and Claude Code skips the managed sources beneath it. Write it only beside the list it scopes.
     */
    desktopMcpServersListScope?: string;
    /**
     * When true (and set in managed settings), claude.ai cloud MCP connectors load alongside managed-mcp.json instead of being suppressed by its exclusive-control lockdown. Default off preserves the lockdown. Read from managed settings only.
     */
    allowAllClaudeAiMcps?: boolean;
    /**
     * When true (and set in device managed settings: MDM, the managed-settings.json file, or a policy helper those configure), the built-in Claude in Chrome MCP server can run alongside managed-mcp.json instead of being blocked by its exclusive-control lockdown. deniedMcpServers and the organization's Claude in Chrome setting still block it. Default off preserves the lockdown.
     */
    allowClaudeInChromeWithManagedMcp?: boolean;
    /**
     * When set in managed settings, blocks non-plugin customization sources for the listed surfaces. Array form locks specific surfaces (e.g. ["skills", "hooks"]); `true` locks all four; `false` is an explicit no-op. Blocked: ~/.claude/{surface}/, .claude/{surface}/ (project), settings.json hooks, .mcp.json. NOT blocked: managed (policySettings) sources, plugin-provided customizations. Composes with strictKnownMarketplaces for end-to-end admin control — plugins gated by marketplace allowlist, everything else blocked here.
     */
    strictPluginOnlyCustomization?: boolean | ('skills' | 'agents' | 'hooks' | 'mcp')[];
    /**
     * Custom status line display configuration
     */
    statusLine?: {
        type: 'command';
        command: string;
        padding?: number;
        /**
         * Re-run the status line command every N seconds in addition to event-driven updates
         */
        refreshInterval?: number;
        /**
         * Hide the built-in `-- INSERT --` / `-- VISUAL --` indicator below the prompt. Use this when your status line script renders `vim.mode` itself.
         */
        hideVimModeIndicator?: boolean;
    };
    /**
     * URL template for PR links in the footer link badges and inline messages. The detected git PR is rendered as the first footer-link badge. Placeholders: {host} {owner} {repo} {number} {url}. Example: "https://reviews.example.com/{owner}/{repo}/pull/{number}"
     */
    prUrlTemplate?: string;
    /**
     * Extra clickable footer badges that appear when a regex matches turn output (tool results and assistant responses). Read from user, flag, and managed settings only; ignored in project .claude/settings.json and local .claude/settings.local.json. At most 5 badges render; the oldest is displaced by newer matches and /clear removes them. Use to surface IDs printed by project CLIs as session links.
     */
    footerLinksRegexes?: ({
        /**
         * Config variant. This client understands "regex": matches turn output and builds a URL from named capture groups. Entries with other variants are preserved but skipped at runtime.
         */
        type: 'regex';
        /**
         * Regex matched against turn output (tool results and assistant text)
         */
        pattern: string;
        /**
         * Link target. {name} placeholders are filled from named regex capture groups, e.g. (?<id>...) -> {id}. Values are URL-encoded; the origin must be literal in the template. The scheme must be https, http, or a recognized editor or workspace deep-link scheme: vscode, vscode-insiders, cursor, windsurf, zed, jetbrains, idea, slack, linear, notion, figma.
         */
        url: string;
        /**
         * Badge text. {name} placeholders filled from named capture groups; defaults to the full match.
         */
        label?: string;
        [k: string]: unknown;
    } | {
        /**
         * Config variant discriminator for entries this client does not understand; the entry is preserved as-is and skipped at runtime.
         */
        type: string;
        [k: string]: unknown;
    })[];
    /**
     * Deprecated: still works, and will stop working in a future release. Custom per-subagent status line shown in the agent panel; receives row context as JSON on stdin
     */
    subagentStatusLine?: {
        type: 'command';
        command: string;
    };
    /**
     * Enabled plugins using plugin-id\@marketplace-id format. Example: { "formatter\@anthropic-tools": true }. Only true turns on a marketplace plugin: a list of versions is accepted but leaves it off. Settings precedence is user < project < local < flag < policy, so to disable a plugin that project settings enable, set it to false in .claude/settings.local.json — setting false in ~/.claude/settings.json is overridden by the project.
     */
    enabledPlugins?: {
        [k: string]: string[] | boolean | {
            [k: string]: unknown;
        };
    };
    /**
     * Managed plugins (plugin\@marketplace ids that managed enabledPlugins sets true) whose hooks run first, outermost, in the listed order: the first id listed sees every event before any other plugin and every result after it. Managed plugins from a local folder or a remote marketplace managed settings name, and not listed here or in appendPlugins, follow the listed ones; user, project and marketplace plugins come after those; then appendPlugins; then the built-in plugins. The bundled cc-plugin-sec-default\@builtin seats itself outermost (on a machine with managed settings and for Team and Enterprise organizations) unless this list is set, in which case list it where it should sit or leave it out. Name it there as sec-default\@builtin, the id every release reads, for as long as any machine in the organization may run a release from before its rename; a release that knows the new id reads either. Any other id that is not an enabled managed plugin is skipped; an id listed in both keys is prepended. Only honored from managed settings (or, on a machine with none, from user settings for your own plugins); ignored in project, local and --settings sources.
     */
    prependPlugins?: string[];
    /**
     * Managed plugins (plugin\@marketplace ids that managed enabledPlugins sets true) whose hooks run last among plugins, innermost, in the listed order: the last id listed sits just above the built-in plugins and sees each event as every other plugin left it. Only honored from managed settings (or, on a machine with none, from user settings for your own plugins); ignored in project, local and --settings sources.
     */
    appendPlugins?: string[];
    /**
     * Additional marketplaces to make available for this repository. Typically used in repository .claude/settings.json to ensure team members have required plugin sources.
     */
    extraKnownMarketplaces?: {
        [k: string]: {
            /**
             * Where to fetch the marketplace from
             */
            source: {
                source: 'url';
                /**
                 * Direct URL to marketplace.json file
                 */
                url: string;
                /**
                 * Custom HTTP headers (e.g., for authentication)
                 */
                headers?: {
                    [k: string]: string;
                };
                /**
                 * Command that prints a JSON object of HTTP headers (e.g. a short-lived auth token). Its output overrides `headers` and, like `headers`, is inherited by same-origin archive downloads from this marketplace. Runs from a fixed directory (the Claude config home, never the session's), so give a bare command found via PATH or an absolute path; it is re-run on later refreshes of this marketplace.
                 */
                headersHelper?: string;
            } | {
                source: 'github';
                /**
                 * GitHub repository in owner/repo format. ONLY in the managed-settings policy lists (strictKnownMarketplaces / blockedMarketplaces) the owner-wildcard form "owner/*" matches every repository under exactly that owner. Everywhere else (marketplace add, extraKnownMarketplaces, known_marketplaces.json) the value must name a single repository — a wildcard is taken literally and fails to clone.
                 */
                repo: string;
                /**
                 * Git branch, tag or full commit id to use (e.g., "main", "v1.0.0"). Defaults to repository default branch. A full commit id (40 or 64 lowercase hex digits) holds the marketplace at that commit: refreshes and auto-updates do not move it. A branch or tag of the repository must hold the commit. Plugins listed with a remote source follow that source unless they name a `sha`. Reserved Anthropic marketplace names do not accept a commit id.
                 */
                ref?: string;
                /**
                 * Path to marketplace.json within repo (defaults to .claude-plugin/marketplace.json)
                 */
                path?: string;
                /**
                 * Directories to include via git sparse-checkout (cone mode). Use for monorepos where the marketplace lives in a subdirectory. Example: [".claude-plugin", "plugins"]. If omitted, the full repository is cloned.
                 */
                sparsePaths?: string[];
                /**
                 * Has no effect; accepted so existing settings keep working. Claude Code's own git never downloads Git LFS content: LFS-tracked files in the marketplace repository are checked out as pointer files whether or not this is set, and adding or updating the marketplace says how many were. To fetch their content, run `git lfs pull` in the marketplace's checkout under ~/.claude/plugins/marketplaces/.
                 */
                skipLfs?: boolean;
            } | {
                source: 'git';
                /**
                 * Full git repository URL
                 */
                url: string;
                /**
                 * Git branch, tag or full commit id to use (e.g., "main", "v1.0.0"). Defaults to repository default branch. A full commit id (40 or 64 lowercase hex digits) holds the marketplace at that commit: refreshes and auto-updates do not move it. A branch or tag of the repository must hold the commit. Plugins listed with a remote source follow that source unless they name a `sha`. Reserved Anthropic marketplace names do not accept a commit id.
                 */
                ref?: string;
                /**
                 * Path to marketplace.json within repo (defaults to .claude-plugin/marketplace.json)
                 */
                path?: string;
                /**
                 * Directories to include via git sparse-checkout (cone mode). Use for monorepos where the marketplace lives in a subdirectory. Example: [".claude-plugin", "plugins"]. If omitted, the full repository is cloned.
                 */
                sparsePaths?: string[];
                /**
                 * Has no effect; accepted so existing settings keep working. Claude Code's own git never downloads Git LFS content: LFS-tracked files in the marketplace repository are checked out as pointer files whether or not this is set, and adding or updating the marketplace says how many were. To fetch their content, run `git lfs pull` in the marketplace's checkout under ~/.claude/plugins/marketplaces/.
                 */
                skipLfs?: boolean;
            } | {
                source: 'npm';
                /**
                 * npm package containing marketplace.json (e.g. "\@acme/claude-marketplace"). A scope wildcard such as "\@acme/*" still parses in a managed list, so a list that holds one stays valid, but it matches no marketplace package.
                 */
                package: string;
                /**
                 * Version or range to fetch (e.g. "1.4.0", "^1.4"); defaults to the latest dist-tag
                 */
                version?: string;
                /**
                 * Registry URL. When adding a marketplace: a one-off registry override (otherwise your npm configuration decides). Under allowManagedPermissionRulesOnly, an npm marketplace keeps plugin allowed-tools only when both the entry and the registration pin this same registry.
                 */
                registry?: string;
            } | {
                source: 'file';
                /**
                 * Local file path to marketplace.json
                 */
                path: string;
            } | {
                source: 'directory';
                /**
                 * Local directory containing .claude-plugin/marketplace.json
                 */
                path: string;
            } | {
                source: 'skills-dir';
            } | {
                source: 'hostPattern';
                /**
                 * Regex pattern to match the host/domain extracted from any marketplace source type. For github sources, matches against github.com. For git sources (SSH or HTTPS), extracts the hostname from the URL. Use in strictKnownMarketplaces to allow all marketplaces from a specific host (e.g., "^github\.mycompany\.com$").
                 */
                hostPattern: string;
            } | {
                source: 'pathPattern';
                /**
                 * Regex pattern matched against the .path field of file and directory sources. Use in strictKnownMarketplaces to allow filesystem-based marketplaces alongside hostPattern restrictions for network sources. Use ".*" to allow all filesystem paths, or a narrower pattern (e.g., "^/opt/approved/") to restrict to specific directories.
                 */
                pathPattern: string;
            } | {
                source: 'settings';
                /**
                 * Marketplace name. Must match the extraKnownMarketplaces key (enforced); the synthetic manifest is written under this name. Same validation as PluginMarketplaceSchema plus reserved-name rejection — validateOfficialNameSource runs after the disk write, too late to clean up.
                 */
                name: string;
                /**
                 * Plugin entries declared inline in settings.json
                 */
                plugins: {
                    /**
                     * Plugin name as it appears in the target repository
                     */
                    name: string;
                    /**
                     * Where to fetch the plugin from. Must be a remote source — relative paths have no marketplace repository to resolve against. Under allowManagedPermissionRulesOnly, a settings marketplace keeps its plugins' allowed-tools only when every npm entry here pins a `registry` on a bare package name; unpinned, the package resolves through the member's own npm config, and a non-bare spelling (an `npm:` alias, a `name\@range`, a URL or git spec) packs as an exotic spec the pin does not bind — either way the marketplace vouches no tool grants.
                     */
                    source: string | {
                        source: 'npm';
                        /**
                         * Package name (or url, or local path, or anything else that can be passed to `npm` as a package)
                         */
                        package: string;
                        /**
                         * Specific version or version range (e.g., ^1.0.0, ~2.1.0)
                         */
                        version?: string;
                        /**
                         * Custom NPM registry URL (defaults to using system default, likely npmjs.org)
                         */
                        registry?: string;
                    } | {
                        source: 'url';
                        /**
                         * Full git repository URL (https:// or git\@)
                         */
                        url: string;
                        /**
                         * Git branch or tag to use (e.g., "main", "v1.0.0"). Defaults to repository default branch.
                         */
                        ref?: string;
                        /**
                         * Specific commit SHA to use
                         */
                        sha?: string;
                    } | {
                        source: 'github';
                        /**
                         * GitHub repository in owner/repo format
                         */
                        repo: string;
                        /**
                         * Git branch or tag to use (e.g., "main", "v1.0.0"). Defaults to repository default branch.
                         */
                        ref?: string;
                        /**
                         * Specific commit SHA to use
                         */
                        sha?: string;
                    } | {
                        source: 'git-subdir';
                        /**
                         * Git repository: GitHub owner/repo shorthand, https://, or git\@ URL
                         */
                        url: string;
                        /**
                         * Subdirectory within the repo containing the plugin (e.g., "tools/claude-plugin"). Checked out sparsely — over https or ssh as a partial clone (--filter=tree:0) — to minimize bandwidth for monorepos.
                         */
                        path: string;
                        /**
                         * Git branch or tag to use (e.g., "main", "v1.0.0"). Defaults to repository default branch.
                         */
                        ref?: string;
                        /**
                         * Specific commit SHA to use
                         */
                        sha?: string;
                    } | {
                        source: 'archive';
                        /**
                         * HTTPS URL of a zip archive containing the plugin. The plugin root (the directory holding .claude-plugin/) may be at the top of the archive or nested one directory deep — a single wrapping directory is stripped.
                         */
                        url: string;
                        /**
                         * SHA-256 digest of the archive. When set, every download is verified against it and the install is refused on mismatch. It also serves as the version identity when neither plugin.json nor the marketplace entry declares a `version`. Recommended. Note the update signal is the version string (plugin.json version, else the entry version, else this digest) — changing only the digest while a version is declared does not trigger an update.
                         */
                        sha256?: string;
                    } | {
                        source: 'command';
                        /**
                         * Shell command that prints the absolute path of the plugin directory on stdout (exactly one line) and exits 0. It must leave a complete plugin in that directory before exiting; the directory is copied into the plugin cache, so the printed path may change between runs (it is re-resolved on every install and update, and once per session in the background). Runs through the platform shell (sh on macOS/Linux, cmd.exe on Windows) from the user's home directory with Claude Code's subprocess environment.
                         */
                        command: string;
                        /**
                         * Seconds to wait for the command before giving up (default: 60)
                         */
                        timeout?: number;
                        /**
                         * copy (default): the printed directory is copied into the plugin cache and content-hashed, so it may be deleted afterwards. link: the cache entry links to the printed directory in place (no copy, no size limit; macOS/Linux) — for large exports; the directory must then stay valid while Claude Code runs, and a different printed path is what signals new content.
                         */
                        mode?: 'copy' | 'link';
                    } | {
                        source: 'unsupported';
                        error?: string;
                    };
                    description?: string;
                    version?: string;
                    strict?: boolean;
                    /**
                     * Versions of its hosts this plugin runs on. "claude-code" is a semver range (e.g. ">=2.1.320"): outside it, the plugin is not installed, updated or loaded. Other keys are ignored.
                     */
                    engines?: {
                        [k: string]: unknown;
                    };
                    /**
                     * HTTP headers sent when downloading this entry's `archive` source.
                     */
                    headers?: {
                        [k: string]: string;
                    };
                    /**
                     * Command that prints a JSON object of HTTP headers for downloading this entry's `archive` source. Runs only when a user explicitly installs or updates this plugin. Unlike a catalog entry, an entry written here does not need `strict: false`: it is declared in a settings file, which has no manifest fields to inline. A declaration in project settings is not operator-authored, so request-routing and client-identity header names are still filtered there. Use an absolute path.
                     */
                    headersHelper?: string;
                }[];
                owner?: {
                    /**
                     * Display name of the plugin author or organization
                     */
                    name: string;
                    /**
                     * Contact email for support or feedback
                     */
                    email?: string;
                    /**
                     * Website, GitHub profile, or organization URL
                     */
                    url?: string;
                };
            };
            /**
             * Local cache path where marketplace manifest is stored (auto-generated if not provided)
             */
            installLocation?: string;
            /**
             * Whether to automatically update this marketplace and its installed plugins on startup
             */
            autoUpdate?: boolean;
            /**
             * Deprecated and ignored: settings that hold it still load. A plugin takes the organization tier when managed settings enable it and declare its marketplace with a remote source.
             */
            pluginDigests?: {
                [k: string]: string[];
            };
        };
    };
    /**
     * Alias for extraKnownMarketplaces: this key is read exactly as if it were spelled extraKnownMarketplaces. Do not set both in one file — if both appear, this key is ignored with a warning. Claude Code may rewrite this key as extraKnownMarketplaces when it updates the file. Clients older than this alias ignore it, so prefer extraKnownMarketplaces while older Claude Code versions still share the same settings.
     */
    additionalMarketplaces?: {
        [k: string]: {
            /**
             * Where to fetch the marketplace from
             */
            source: {
                source: 'url';
                /**
                 * Direct URL to marketplace.json file
                 */
                url: string;
                /**
                 * Custom HTTP headers (e.g., for authentication)
                 */
                headers?: {
                    [k: string]: string;
                };
                /**
                 * Command that prints a JSON object of HTTP headers (e.g. a short-lived auth token). Its output overrides `headers` and, like `headers`, is inherited by same-origin archive downloads from this marketplace. Runs from a fixed directory (the Claude config home, never the session's), so give a bare command found via PATH or an absolute path; it is re-run on later refreshes of this marketplace.
                 */
                headersHelper?: string;
            } | {
                source: 'github';
                /**
                 * GitHub repository in owner/repo format. ONLY in the managed-settings policy lists (strictKnownMarketplaces / blockedMarketplaces) the owner-wildcard form "owner/*" matches every repository under exactly that owner. Everywhere else (marketplace add, extraKnownMarketplaces, known_marketplaces.json) the value must name a single repository — a wildcard is taken literally and fails to clone.
                 */
                repo: string;
                /**
                 * Git branch, tag or full commit id to use (e.g., "main", "v1.0.0"). Defaults to repository default branch. A full commit id (40 or 64 lowercase hex digits) holds the marketplace at that commit: refreshes and auto-updates do not move it. A branch or tag of the repository must hold the commit. Plugins listed with a remote source follow that source unless they name a `sha`. Reserved Anthropic marketplace names do not accept a commit id.
                 */
                ref?: string;
                /**
                 * Path to marketplace.json within repo (defaults to .claude-plugin/marketplace.json)
                 */
                path?: string;
                /**
                 * Directories to include via git sparse-checkout (cone mode). Use for monorepos where the marketplace lives in a subdirectory. Example: [".claude-plugin", "plugins"]. If omitted, the full repository is cloned.
                 */
                sparsePaths?: string[];
                /**
                 * Has no effect; accepted so existing settings keep working. Claude Code's own git never downloads Git LFS content: LFS-tracked files in the marketplace repository are checked out as pointer files whether or not this is set, and adding or updating the marketplace says how many were. To fetch their content, run `git lfs pull` in the marketplace's checkout under ~/.claude/plugins/marketplaces/.
                 */
                skipLfs?: boolean;
            } | {
                source: 'git';
                /**
                 * Full git repository URL
                 */
                url: string;
                /**
                 * Git branch, tag or full commit id to use (e.g., "main", "v1.0.0"). Defaults to repository default branch. A full commit id (40 or 64 lowercase hex digits) holds the marketplace at that commit: refreshes and auto-updates do not move it. A branch or tag of the repository must hold the commit. Plugins listed with a remote source follow that source unless they name a `sha`. Reserved Anthropic marketplace names do not accept a commit id.
                 */
                ref?: string;
                /**
                 * Path to marketplace.json within repo (defaults to .claude-plugin/marketplace.json)
                 */
                path?: string;
                /**
                 * Directories to include via git sparse-checkout (cone mode). Use for monorepos where the marketplace lives in a subdirectory. Example: [".claude-plugin", "plugins"]. If omitted, the full repository is cloned.
                 */
                sparsePaths?: string[];
                /**
                 * Has no effect; accepted so existing settings keep working. Claude Code's own git never downloads Git LFS content: LFS-tracked files in the marketplace repository are checked out as pointer files whether or not this is set, and adding or updating the marketplace says how many were. To fetch their content, run `git lfs pull` in the marketplace's checkout under ~/.claude/plugins/marketplaces/.
                 */
                skipLfs?: boolean;
            } | {
                source: 'npm';
                /**
                 * npm package containing marketplace.json (e.g. "\@acme/claude-marketplace"). A scope wildcard such as "\@acme/*" still parses in a managed list, so a list that holds one stays valid, but it matches no marketplace package.
                 */
                package: string;
                /**
                 * Version or range to fetch (e.g. "1.4.0", "^1.4"); defaults to the latest dist-tag
                 */
                version?: string;
                /**
                 * Registry URL. When adding a marketplace: a one-off registry override (otherwise your npm configuration decides). Under allowManagedPermissionRulesOnly, an npm marketplace keeps plugin allowed-tools only when both the entry and the registration pin this same registry.
                 */
                registry?: string;
            } | {
                source: 'file';
                /**
                 * Local file path to marketplace.json
                 */
                path: string;
            } | {
                source: 'directory';
                /**
                 * Local directory containing .claude-plugin/marketplace.json
                 */
                path: string;
            } | {
                source: 'skills-dir';
            } | {
                source: 'hostPattern';
                /**
                 * Regex pattern to match the host/domain extracted from any marketplace source type. For github sources, matches against github.com. For git sources (SSH or HTTPS), extracts the hostname from the URL. Use in strictKnownMarketplaces to allow all marketplaces from a specific host (e.g., "^github\.mycompany\.com$").
                 */
                hostPattern: string;
            } | {
                source: 'pathPattern';
                /**
                 * Regex pattern matched against the .path field of file and directory sources. Use in strictKnownMarketplaces to allow filesystem-based marketplaces alongside hostPattern restrictions for network sources. Use ".*" to allow all filesystem paths, or a narrower pattern (e.g., "^/opt/approved/") to restrict to specific directories.
                 */
                pathPattern: string;
            } | {
                source: 'settings';
                /**
                 * Marketplace name. Must match the extraKnownMarketplaces key (enforced); the synthetic manifest is written under this name. Same validation as PluginMarketplaceSchema plus reserved-name rejection — validateOfficialNameSource runs after the disk write, too late to clean up.
                 */
                name: string;
                /**
                 * Plugin entries declared inline in settings.json
                 */
                plugins: {
                    /**
                     * Plugin name as it appears in the target repository
                     */
                    name: string;
                    /**
                     * Where to fetch the plugin from. Must be a remote source — relative paths have no marketplace repository to resolve against. Under allowManagedPermissionRulesOnly, a settings marketplace keeps its plugins' allowed-tools only when every npm entry here pins a `registry` on a bare package name; unpinned, the package resolves through the member's own npm config, and a non-bare spelling (an `npm:` alias, a `name\@range`, a URL or git spec) packs as an exotic spec the pin does not bind — either way the marketplace vouches no tool grants.
                     */
                    source: string | {
                        source: 'npm';
                        /**
                         * Package name (or url, or local path, or anything else that can be passed to `npm` as a package)
                         */
                        package: string;
                        /**
                         * Specific version or version range (e.g., ^1.0.0, ~2.1.0)
                         */
                        version?: string;
                        /**
                         * Custom NPM registry URL (defaults to using system default, likely npmjs.org)
                         */
                        registry?: string;
                    } | {
                        source: 'url';
                        /**
                         * Full git repository URL (https:// or git\@)
                         */
                        url: string;
                        /**
                         * Git branch or tag to use (e.g., "main", "v1.0.0"). Defaults to repository default branch.
                         */
                        ref?: string;
                        /**
                         * Specific commit SHA to use
                         */
                        sha?: string;
                    } | {
                        source: 'github';
                        /**
                         * GitHub repository in owner/repo format
                         */
                        repo: string;
                        /**
                         * Git branch or tag to use (e.g., "main", "v1.0.0"). Defaults to repository default branch.
                         */
                        ref?: string;
                        /**
                         * Specific commit SHA to use
                         */
                        sha?: string;
                    } | {
                        source: 'git-subdir';
                        /**
                         * Git repository: GitHub owner/repo shorthand, https://, or git\@ URL
                         */
                        url: string;
                        /**
                         * Subdirectory within the repo containing the plugin (e.g., "tools/claude-plugin"). Checked out sparsely — over https or ssh as a partial clone (--filter=tree:0) — to minimize bandwidth for monorepos.
                         */
                        path: string;
                        /**
                         * Git branch or tag to use (e.g., "main", "v1.0.0"). Defaults to repository default branch.
                         */
                        ref?: string;
                        /**
                         * Specific commit SHA to use
                         */
                        sha?: string;
                    } | {
                        source: 'archive';
                        /**
                         * HTTPS URL of a zip archive containing the plugin. The plugin root (the directory holding .claude-plugin/) may be at the top of the archive or nested one directory deep — a single wrapping directory is stripped.
                         */
                        url: string;
                        /**
                         * SHA-256 digest of the archive. When set, every download is verified against it and the install is refused on mismatch. It also serves as the version identity when neither plugin.json nor the marketplace entry declares a `version`. Recommended. Note the update signal is the version string (plugin.json version, else the entry version, else this digest) — changing only the digest while a version is declared does not trigger an update.
                         */
                        sha256?: string;
                    } | {
                        source: 'command';
                        /**
                         * Shell command that prints the absolute path of the plugin directory on stdout (exactly one line) and exits 0. It must leave a complete plugin in that directory before exiting; the directory is copied into the plugin cache, so the printed path may change between runs (it is re-resolved on every install and update, and once per session in the background). Runs through the platform shell (sh on macOS/Linux, cmd.exe on Windows) from the user's home directory with Claude Code's subprocess environment.
                         */
                        command: string;
                        /**
                         * Seconds to wait for the command before giving up (default: 60)
                         */
                        timeout?: number;
                        /**
                         * copy (default): the printed directory is copied into the plugin cache and content-hashed, so it may be deleted afterwards. link: the cache entry links to the printed directory in place (no copy, no size limit; macOS/Linux) — for large exports; the directory must then stay valid while Claude Code runs, and a different printed path is what signals new content.
                         */
                        mode?: 'copy' | 'link';
                    } | {
                        source: 'unsupported';
                        error?: string;
                    };
                    description?: string;
                    version?: string;
                    strict?: boolean;
                    /**
                     * Versions of its hosts this plugin runs on. "claude-code" is a semver range (e.g. ">=2.1.320"): outside it, the plugin is not installed, updated or loaded. Other keys are ignored.
                     */
                    engines?: {
                        [k: string]: unknown;
                    };
                    /**
                     * HTTP headers sent when downloading this entry's `archive` source.
                     */
                    headers?: {
                        [k: string]: string;
                    };
                    /**
                     * Command that prints a JSON object of HTTP headers for downloading this entry's `archive` source. Runs only when a user explicitly installs or updates this plugin. Unlike a catalog entry, an entry written here does not need `strict: false`: it is declared in a settings file, which has no manifest fields to inline. A declaration in project settings is not operator-authored, so request-routing and client-identity header names are still filtered there. Use an absolute path.
                     */
                    headersHelper?: string;
                }[];
                owner?: {
                    /**
                     * Display name of the plugin author or organization
                     */
                    name: string;
                    /**
                     * Contact email for support or feedback
                     */
                    email?: string;
                    /**
                     * Website, GitHub profile, or organization URL
                     */
                    url?: string;
                };
            };
            /**
             * Local cache path where marketplace manifest is stored (auto-generated if not provided)
             */
            installLocation?: string;
            /**
             * Whether to automatically update this marketplace and its installed plugins on startup
             */
            autoUpdate?: boolean;
            /**
             * Deprecated and ignored: settings that hold it still load. A plugin takes the organization tier when managed settings enable it and declare its marketplace with a remote source.
             */
            pluginDigests?: {
                [k: string]: string[];
            };
        };
    };
    /**
     * Enterprise strict list of allowed marketplace sources. When set in managed settings, ONLY these sources can be added as marketplaces. Entries match exactly, except that a github entry may use the owner-wildcard form {"source":"github","repo":"owner/*"} to allow every repository under that owner. The check happens BEFORE downloading, so blocked sources never touch the filesystem. Note: this is a policy gate only — it does NOT register marketplaces. To pre-register allowed marketplaces for users, also set extraKnownMarketplaces.
     */
    strictKnownMarketplaces?: ({
        source: 'url';
        /**
         * Direct URL to marketplace.json file
         */
        url: string;
        /**
         * Custom HTTP headers (e.g., for authentication)
         */
        headers?: {
            [k: string]: string;
        };
        /**
         * Command that prints a JSON object of HTTP headers (e.g. a short-lived auth token). Its output overrides `headers` and, like `headers`, is inherited by same-origin archive downloads from this marketplace. Runs from a fixed directory (the Claude config home, never the session's), so give a bare command found via PATH or an absolute path; it is re-run on later refreshes of this marketplace.
         */
        headersHelper?: string;
    } | {
        source: 'github';
        /**
         * GitHub repository in owner/repo format. ONLY in the managed-settings policy lists (strictKnownMarketplaces / blockedMarketplaces) the owner-wildcard form "owner/*" matches every repository under exactly that owner. Everywhere else (marketplace add, extraKnownMarketplaces, known_marketplaces.json) the value must name a single repository — a wildcard is taken literally and fails to clone.
         */
        repo: string;
        /**
         * Git branch, tag or full commit id to use (e.g., "main", "v1.0.0"). Defaults to repository default branch. A full commit id (40 or 64 lowercase hex digits) holds the marketplace at that commit: refreshes and auto-updates do not move it. A branch or tag of the repository must hold the commit. Plugins listed with a remote source follow that source unless they name a `sha`. Reserved Anthropic marketplace names do not accept a commit id.
         */
        ref?: string;
        /**
         * Path to marketplace.json within repo (defaults to .claude-plugin/marketplace.json)
         */
        path?: string;
        /**
         * Directories to include via git sparse-checkout (cone mode). Use for monorepos where the marketplace lives in a subdirectory. Example: [".claude-plugin", "plugins"]. If omitted, the full repository is cloned.
         */
        sparsePaths?: string[];
        /**
         * Has no effect; accepted so existing settings keep working. Claude Code's own git never downloads Git LFS content: LFS-tracked files in the marketplace repository are checked out as pointer files whether or not this is set, and adding or updating the marketplace says how many were. To fetch their content, run `git lfs pull` in the marketplace's checkout under ~/.claude/plugins/marketplaces/.
         */
        skipLfs?: boolean;
    } | {
        source: 'git';
        /**
         * Full git repository URL
         */
        url: string;
        /**
         * Git branch, tag or full commit id to use (e.g., "main", "v1.0.0"). Defaults to repository default branch. A full commit id (40 or 64 lowercase hex digits) holds the marketplace at that commit: refreshes and auto-updates do not move it. A branch or tag of the repository must hold the commit. Plugins listed with a remote source follow that source unless they name a `sha`. Reserved Anthropic marketplace names do not accept a commit id.
         */
        ref?: string;
        /**
         * Path to marketplace.json within repo (defaults to .claude-plugin/marketplace.json)
         */
        path?: string;
        /**
         * Directories to include via git sparse-checkout (cone mode). Use for monorepos where the marketplace lives in a subdirectory. Example: [".claude-plugin", "plugins"]. If omitted, the full repository is cloned.
         */
        sparsePaths?: string[];
        /**
         * Has no effect; accepted so existing settings keep working. Claude Code's own git never downloads Git LFS content: LFS-tracked files in the marketplace repository are checked out as pointer files whether or not this is set, and adding or updating the marketplace says how many were. To fetch their content, run `git lfs pull` in the marketplace's checkout under ~/.claude/plugins/marketplaces/.
         */
        skipLfs?: boolean;
    } | {
        source: 'npm';
        /**
         * npm package containing marketplace.json (e.g. "\@acme/claude-marketplace"). A scope wildcard such as "\@acme/*" still parses in a managed list, so a list that holds one stays valid, but it matches no marketplace package.
         */
        package: string;
        /**
         * Version or range to fetch (e.g. "1.4.0", "^1.4"); defaults to the latest dist-tag
         */
        version?: string;
        /**
         * Registry URL. When adding a marketplace: a one-off registry override (otherwise your npm configuration decides). Under allowManagedPermissionRulesOnly, an npm marketplace keeps plugin allowed-tools only when both the entry and the registration pin this same registry.
         */
        registry?: string;
    } | {
        source: 'file';
        /**
         * Local file path to marketplace.json
         */
        path: string;
    } | {
        source: 'directory';
        /**
         * Local directory containing .claude-plugin/marketplace.json
         */
        path: string;
    } | {
        source: 'skills-dir';
    } | {
        source: 'hostPattern';
        /**
         * Regex pattern to match the host/domain extracted from any marketplace source type. For github sources, matches against github.com. For git sources (SSH or HTTPS), extracts the hostname from the URL. Use in strictKnownMarketplaces to allow all marketplaces from a specific host (e.g., "^github\.mycompany\.com$").
         */
        hostPattern: string;
    } | {
        source: 'pathPattern';
        /**
         * Regex pattern matched against the .path field of file and directory sources. Use in strictKnownMarketplaces to allow filesystem-based marketplaces alongside hostPattern restrictions for network sources. Use ".*" to allow all filesystem paths, or a narrower pattern (e.g., "^/opt/approved/") to restrict to specific directories.
         */
        pathPattern: string;
    } | {
        source: 'settings';
        /**
         * Marketplace name. Must match the extraKnownMarketplaces key (enforced); the synthetic manifest is written under this name. Same validation as PluginMarketplaceSchema plus reserved-name rejection — validateOfficialNameSource runs after the disk write, too late to clean up.
         */
        name: string;
        /**
         * Plugin entries declared inline in settings.json
         */
        plugins: {
            /**
             * Plugin name as it appears in the target repository
             */
            name: string;
            /**
             * Where to fetch the plugin from. Must be a remote source — relative paths have no marketplace repository to resolve against. Under allowManagedPermissionRulesOnly, a settings marketplace keeps its plugins' allowed-tools only when every npm entry here pins a `registry` on a bare package name; unpinned, the package resolves through the member's own npm config, and a non-bare spelling (an `npm:` alias, a `name\@range`, a URL or git spec) packs as an exotic spec the pin does not bind — either way the marketplace vouches no tool grants.
             */
            source: string | {
                source: 'npm';
                /**
                 * Package name (or url, or local path, or anything else that can be passed to `npm` as a package)
                 */
                package: string;
                /**
                 * Specific version or version range (e.g., ^1.0.0, ~2.1.0)
                 */
                version?: string;
                /**
                 * Custom NPM registry URL (defaults to using system default, likely npmjs.org)
                 */
                registry?: string;
            } | {
                source: 'url';
                /**
                 * Full git repository URL (https:// or git\@)
                 */
                url: string;
                /**
                 * Git branch or tag to use (e.g., "main", "v1.0.0"). Defaults to repository default branch.
                 */
                ref?: string;
                /**
                 * Specific commit SHA to use
                 */
                sha?: string;
            } | {
                source: 'github';
                /**
                 * GitHub repository in owner/repo format
                 */
                repo: string;
                /**
                 * Git branch or tag to use (e.g., "main", "v1.0.0"). Defaults to repository default branch.
                 */
                ref?: string;
                /**
                 * Specific commit SHA to use
                 */
                sha?: string;
            } | {
                source: 'git-subdir';
                /**
                 * Git repository: GitHub owner/repo shorthand, https://, or git\@ URL
                 */
                url: string;
                /**
                 * Subdirectory within the repo containing the plugin (e.g., "tools/claude-plugin"). Checked out sparsely — over https or ssh as a partial clone (--filter=tree:0) — to minimize bandwidth for monorepos.
                 */
                path: string;
                /**
                 * Git branch or tag to use (e.g., "main", "v1.0.0"). Defaults to repository default branch.
                 */
                ref?: string;
                /**
                 * Specific commit SHA to use
                 */
                sha?: string;
            } | {
                source: 'archive';
                /**
                 * HTTPS URL of a zip archive containing the plugin. The plugin root (the directory holding .claude-plugin/) may be at the top of the archive or nested one directory deep — a single wrapping directory is stripped.
                 */
                url: string;
                /**
                 * SHA-256 digest of the archive. When set, every download is verified against it and the install is refused on mismatch. It also serves as the version identity when neither plugin.json nor the marketplace entry declares a `version`. Recommended. Note the update signal is the version string (plugin.json version, else the entry version, else this digest) — changing only the digest while a version is declared does not trigger an update.
                 */
                sha256?: string;
            } | {
                source: 'command';
                /**
                 * Shell command that prints the absolute path of the plugin directory on stdout (exactly one line) and exits 0. It must leave a complete plugin in that directory before exiting; the directory is copied into the plugin cache, so the printed path may change between runs (it is re-resolved on every install and update, and once per session in the background). Runs through the platform shell (sh on macOS/Linux, cmd.exe on Windows) from the user's home directory with Claude Code's subprocess environment.
                 */
                command: string;
                /**
                 * Seconds to wait for the command before giving up (default: 60)
                 */
                timeout?: number;
                /**
                 * copy (default): the printed directory is copied into the plugin cache and content-hashed, so it may be deleted afterwards. link: the cache entry links to the printed directory in place (no copy, no size limit; macOS/Linux) — for large exports; the directory must then stay valid while Claude Code runs, and a different printed path is what signals new content.
                 */
                mode?: 'copy' | 'link';
            } | {
                source: 'unsupported';
                error?: string;
            };
            description?: string;
            version?: string;
            strict?: boolean;
            /**
             * Versions of its hosts this plugin runs on. "claude-code" is a semver range (e.g. ">=2.1.320"): outside it, the plugin is not installed, updated or loaded. Other keys are ignored.
             */
            engines?: {
                [k: string]: unknown;
            };
            /**
             * HTTP headers sent when downloading this entry's `archive` source.
             */
            headers?: {
                [k: string]: string;
            };
            /**
             * Command that prints a JSON object of HTTP headers for downloading this entry's `archive` source. Runs only when a user explicitly installs or updates this plugin. Unlike a catalog entry, an entry written here does not need `strict: false`: it is declared in a settings file, which has no manifest fields to inline. A declaration in project settings is not operator-authored, so request-routing and client-identity header names are still filtered there. Use an absolute path.
             */
            headersHelper?: string;
        }[];
        owner?: {
            /**
             * Display name of the plugin author or organization
             */
            name: string;
            /**
             * Contact email for support or feedback
             */
            email?: string;
            /**
             * Website, GitHub profile, or organization URL
             */
            url?: string;
        };
    })[];
    /**
     * Alias for strictKnownMarketplaces (managed settings only): this key is read exactly as if it were spelled strictKnownMarketplaces. Do not set both in one file — if both appear, this key is ignored with a warning. Clients older than this alias ignore it, so keep using strictKnownMarketplaces when the allowlist must also bind older Claude Code versions.
     */
    allowedMarketplaces?: ({
        source: 'url';
        /**
         * Direct URL to marketplace.json file
         */
        url: string;
        /**
         * Custom HTTP headers (e.g., for authentication)
         */
        headers?: {
            [k: string]: string;
        };
        /**
         * Command that prints a JSON object of HTTP headers (e.g. a short-lived auth token). Its output overrides `headers` and, like `headers`, is inherited by same-origin archive downloads from this marketplace. Runs from a fixed directory (the Claude config home, never the session's), so give a bare command found via PATH or an absolute path; it is re-run on later refreshes of this marketplace.
         */
        headersHelper?: string;
    } | {
        source: 'github';
        /**
         * GitHub repository in owner/repo format. ONLY in the managed-settings policy lists (strictKnownMarketplaces / blockedMarketplaces) the owner-wildcard form "owner/*" matches every repository under exactly that owner. Everywhere else (marketplace add, extraKnownMarketplaces, known_marketplaces.json) the value must name a single repository — a wildcard is taken literally and fails to clone.
         */
        repo: string;
        /**
         * Git branch, tag or full commit id to use (e.g., "main", "v1.0.0"). Defaults to repository default branch. A full commit id (40 or 64 lowercase hex digits) holds the marketplace at that commit: refreshes and auto-updates do not move it. A branch or tag of the repository must hold the commit. Plugins listed with a remote source follow that source unless they name a `sha`. Reserved Anthropic marketplace names do not accept a commit id.
         */
        ref?: string;
        /**
         * Path to marketplace.json within repo (defaults to .claude-plugin/marketplace.json)
         */
        path?: string;
        /**
         * Directories to include via git sparse-checkout (cone mode). Use for monorepos where the marketplace lives in a subdirectory. Example: [".claude-plugin", "plugins"]. If omitted, the full repository is cloned.
         */
        sparsePaths?: string[];
        /**
         * Has no effect; accepted so existing settings keep working. Claude Code's own git never downloads Git LFS content: LFS-tracked files in the marketplace repository are checked out as pointer files whether or not this is set, and adding or updating the marketplace says how many were. To fetch their content, run `git lfs pull` in the marketplace's checkout under ~/.claude/plugins/marketplaces/.
         */
        skipLfs?: boolean;
    } | {
        source: 'git';
        /**
         * Full git repository URL
         */
        url: string;
        /**
         * Git branch, tag or full commit id to use (e.g., "main", "v1.0.0"). Defaults to repository default branch. A full commit id (40 or 64 lowercase hex digits) holds the marketplace at that commit: refreshes and auto-updates do not move it. A branch or tag of the repository must hold the commit. Plugins listed with a remote source follow that source unless they name a `sha`. Reserved Anthropic marketplace names do not accept a commit id.
         */
        ref?: string;
        /**
         * Path to marketplace.json within repo (defaults to .claude-plugin/marketplace.json)
         */
        path?: string;
        /**
         * Directories to include via git sparse-checkout (cone mode). Use for monorepos where the marketplace lives in a subdirectory. Example: [".claude-plugin", "plugins"]. If omitted, the full repository is cloned.
         */
        sparsePaths?: string[];
        /**
         * Has no effect; accepted so existing settings keep working. Claude Code's own git never downloads Git LFS content: LFS-tracked files in the marketplace repository are checked out as pointer files whether or not this is set, and adding or updating the marketplace says how many were. To fetch their content, run `git lfs pull` in the marketplace's checkout under ~/.claude/plugins/marketplaces/.
         */
        skipLfs?: boolean;
    } | {
        source: 'npm';
        /**
         * npm package containing marketplace.json (e.g. "\@acme/claude-marketplace"). A scope wildcard such as "\@acme/*" still parses in a managed list, so a list that holds one stays valid, but it matches no marketplace package.
         */
        package: string;
        /**
         * Version or range to fetch (e.g. "1.4.0", "^1.4"); defaults to the latest dist-tag
         */
        version?: string;
        /**
         * Registry URL. When adding a marketplace: a one-off registry override (otherwise your npm configuration decides). Under allowManagedPermissionRulesOnly, an npm marketplace keeps plugin allowed-tools only when both the entry and the registration pin this same registry.
         */
        registry?: string;
    } | {
        source: 'file';
        /**
         * Local file path to marketplace.json
         */
        path: string;
    } | {
        source: 'directory';
        /**
         * Local directory containing .claude-plugin/marketplace.json
         */
        path: string;
    } | {
        source: 'skills-dir';
    } | {
        source: 'hostPattern';
        /**
         * Regex pattern to match the host/domain extracted from any marketplace source type. For github sources, matches against github.com. For git sources (SSH or HTTPS), extracts the hostname from the URL. Use in strictKnownMarketplaces to allow all marketplaces from a specific host (e.g., "^github\.mycompany\.com$").
         */
        hostPattern: string;
    } | {
        source: 'pathPattern';
        /**
         * Regex pattern matched against the .path field of file and directory sources. Use in strictKnownMarketplaces to allow filesystem-based marketplaces alongside hostPattern restrictions for network sources. Use ".*" to allow all filesystem paths, or a narrower pattern (e.g., "^/opt/approved/") to restrict to specific directories.
         */
        pathPattern: string;
    } | {
        source: 'settings';
        /**
         * Marketplace name. Must match the extraKnownMarketplaces key (enforced); the synthetic manifest is written under this name. Same validation as PluginMarketplaceSchema plus reserved-name rejection — validateOfficialNameSource runs after the disk write, too late to clean up.
         */
        name: string;
        /**
         * Plugin entries declared inline in settings.json
         */
        plugins: {
            /**
             * Plugin name as it appears in the target repository
             */
            name: string;
            /**
             * Where to fetch the plugin from. Must be a remote source — relative paths have no marketplace repository to resolve against. Under allowManagedPermissionRulesOnly, a settings marketplace keeps its plugins' allowed-tools only when every npm entry here pins a `registry` on a bare package name; unpinned, the package resolves through the member's own npm config, and a non-bare spelling (an `npm:` alias, a `name\@range`, a URL or git spec) packs as an exotic spec the pin does not bind — either way the marketplace vouches no tool grants.
             */
            source: string | {
                source: 'npm';
                /**
                 * Package name (or url, or local path, or anything else that can be passed to `npm` as a package)
                 */
                package: string;
                /**
                 * Specific version or version range (e.g., ^1.0.0, ~2.1.0)
                 */
                version?: string;
                /**
                 * Custom NPM registry URL (defaults to using system default, likely npmjs.org)
                 */
                registry?: string;
            } | {
                source: 'url';
                /**
                 * Full git repository URL (https:// or git\@)
                 */
                url: string;
                /**
                 * Git branch or tag to use (e.g., "main", "v1.0.0"). Defaults to repository default branch.
                 */
                ref?: string;
                /**
                 * Specific commit SHA to use
                 */
                sha?: string;
            } | {
                source: 'github';
                /**
                 * GitHub repository in owner/repo format
                 */
                repo: string;
                /**
                 * Git branch or tag to use (e.g., "main", "v1.0.0"). Defaults to repository default branch.
                 */
                ref?: string;
                /**
                 * Specific commit SHA to use
                 */
                sha?: string;
            } | {
                source: 'git-subdir';
                /**
                 * Git repository: GitHub owner/repo shorthand, https://, or git\@ URL
                 */
                url: string;
                /**
                 * Subdirectory within the repo containing the plugin (e.g., "tools/claude-plugin"). Checked out sparsely — over https or ssh as a partial clone (--filter=tree:0) — to minimize bandwidth for monorepos.
                 */
                path: string;
                /**
                 * Git branch or tag to use (e.g., "main", "v1.0.0"). Defaults to repository default branch.
                 */
                ref?: string;
                /**
                 * Specific commit SHA to use
                 */
                sha?: string;
            } | {
                source: 'archive';
                /**
                 * HTTPS URL of a zip archive containing the plugin. The plugin root (the directory holding .claude-plugin/) may be at the top of the archive or nested one directory deep — a single wrapping directory is stripped.
                 */
                url: string;
                /**
                 * SHA-256 digest of the archive. When set, every download is verified against it and the install is refused on mismatch. It also serves as the version identity when neither plugin.json nor the marketplace entry declares a `version`. Recommended. Note the update signal is the version string (plugin.json version, else the entry version, else this digest) — changing only the digest while a version is declared does not trigger an update.
                 */
                sha256?: string;
            } | {
                source: 'command';
                /**
                 * Shell command that prints the absolute path of the plugin directory on stdout (exactly one line) and exits 0. It must leave a complete plugin in that directory before exiting; the directory is copied into the plugin cache, so the printed path may change between runs (it is re-resolved on every install and update, and once per session in the background). Runs through the platform shell (sh on macOS/Linux, cmd.exe on Windows) from the user's home directory with Claude Code's subprocess environment.
                 */
                command: string;
                /**
                 * Seconds to wait for the command before giving up (default: 60)
                 */
                timeout?: number;
                /**
                 * copy (default): the printed directory is copied into the plugin cache and content-hashed, so it may be deleted afterwards. link: the cache entry links to the printed directory in place (no copy, no size limit; macOS/Linux) — for large exports; the directory must then stay valid while Claude Code runs, and a different printed path is what signals new content.
                 */
                mode?: 'copy' | 'link';
            } | {
                source: 'unsupported';
                error?: string;
            };
            description?: string;
            version?: string;
            strict?: boolean;
            /**
             * Versions of its hosts this plugin runs on. "claude-code" is a semver range (e.g. ">=2.1.320"): outside it, the plugin is not installed, updated or loaded. Other keys are ignored.
             */
            engines?: {
                [k: string]: unknown;
            };
            /**
             * HTTP headers sent when downloading this entry's `archive` source.
             */
            headers?: {
                [k: string]: string;
            };
            /**
             * Command that prints a JSON object of HTTP headers for downloading this entry's `archive` source. Runs only when a user explicitly installs or updates this plugin. Unlike a catalog entry, an entry written here does not need `strict: false`: it is declared in a settings file, which has no manifest fields to inline. A declaration in project settings is not operator-authored, so request-routing and client-identity header names are still filtered there. Use an absolute path.
             */
            headersHelper?: string;
        }[];
        owner?: {
            /**
             * Display name of the plugin author or organization
             */
            name: string;
            /**
             * Contact email for support or feedback
             */
            email?: string;
            /**
             * Website, GitHub profile, or organization URL
             */
            url?: string;
        };
    })[];
    /**
     * Enterprise blocklist of marketplace sources. When set in managed settings, these sources are blocked from being added as marketplaces. Entries match exactly, except that a github entry may use the owner-wildcard form {"source":"github","repo":"owner/*"} to block every repository under that owner, and an entry naming a branch or tag in `ref` also blocks every full commit id in that repository. The check happens BEFORE downloading, so blocked sources never touch the filesystem.
     */
    blockedMarketplaces?: ({
        source: 'url';
        /**
         * Direct URL to marketplace.json file
         */
        url: string;
        /**
         * Custom HTTP headers (e.g., for authentication)
         */
        headers?: {
            [k: string]: string;
        };
        /**
         * Command that prints a JSON object of HTTP headers (e.g. a short-lived auth token). Its output overrides `headers` and, like `headers`, is inherited by same-origin archive downloads from this marketplace. Runs from a fixed directory (the Claude config home, never the session's), so give a bare command found via PATH or an absolute path; it is re-run on later refreshes of this marketplace.
         */
        headersHelper?: string;
    } | {
        source: 'github';
        /**
         * GitHub repository in owner/repo format. ONLY in the managed-settings policy lists (strictKnownMarketplaces / blockedMarketplaces) the owner-wildcard form "owner/*" matches every repository under exactly that owner. Everywhere else (marketplace add, extraKnownMarketplaces, known_marketplaces.json) the value must name a single repository — a wildcard is taken literally and fails to clone.
         */
        repo: string;
        /**
         * Git branch, tag or full commit id to use (e.g., "main", "v1.0.0"). Defaults to repository default branch. A full commit id (40 or 64 lowercase hex digits) holds the marketplace at that commit: refreshes and auto-updates do not move it. A branch or tag of the repository must hold the commit. Plugins listed with a remote source follow that source unless they name a `sha`. Reserved Anthropic marketplace names do not accept a commit id.
         */
        ref?: string;
        /**
         * Path to marketplace.json within repo (defaults to .claude-plugin/marketplace.json)
         */
        path?: string;
        /**
         * Directories to include via git sparse-checkout (cone mode). Use for monorepos where the marketplace lives in a subdirectory. Example: [".claude-plugin", "plugins"]. If omitted, the full repository is cloned.
         */
        sparsePaths?: string[];
        /**
         * Has no effect; accepted so existing settings keep working. Claude Code's own git never downloads Git LFS content: LFS-tracked files in the marketplace repository are checked out as pointer files whether or not this is set, and adding or updating the marketplace says how many were. To fetch their content, run `git lfs pull` in the marketplace's checkout under ~/.claude/plugins/marketplaces/.
         */
        skipLfs?: boolean;
    } | {
        source: 'git';
        /**
         * Full git repository URL
         */
        url: string;
        /**
         * Git branch, tag or full commit id to use (e.g., "main", "v1.0.0"). Defaults to repository default branch. A full commit id (40 or 64 lowercase hex digits) holds the marketplace at that commit: refreshes and auto-updates do not move it. A branch or tag of the repository must hold the commit. Plugins listed with a remote source follow that source unless they name a `sha`. Reserved Anthropic marketplace names do not accept a commit id.
         */
        ref?: string;
        /**
         * Path to marketplace.json within repo (defaults to .claude-plugin/marketplace.json)
         */
        path?: string;
        /**
         * Directories to include via git sparse-checkout (cone mode). Use for monorepos where the marketplace lives in a subdirectory. Example: [".claude-plugin", "plugins"]. If omitted, the full repository is cloned.
         */
        sparsePaths?: string[];
        /**
         * Has no effect; accepted so existing settings keep working. Claude Code's own git never downloads Git LFS content: LFS-tracked files in the marketplace repository are checked out as pointer files whether or not this is set, and adding or updating the marketplace says how many were. To fetch their content, run `git lfs pull` in the marketplace's checkout under ~/.claude/plugins/marketplaces/.
         */
        skipLfs?: boolean;
    } | {
        source: 'npm';
        /**
         * npm package containing marketplace.json (e.g. "\@acme/claude-marketplace"). A scope wildcard such as "\@acme/*" still parses in a managed list, so a list that holds one stays valid, but it matches no marketplace package.
         */
        package: string;
        /**
         * Version or range to fetch (e.g. "1.4.0", "^1.4"); defaults to the latest dist-tag
         */
        version?: string;
        /**
         * Registry URL. When adding a marketplace: a one-off registry override (otherwise your npm configuration decides). Under allowManagedPermissionRulesOnly, an npm marketplace keeps plugin allowed-tools only when both the entry and the registration pin this same registry.
         */
        registry?: string;
    } | {
        source: 'file';
        /**
         * Local file path to marketplace.json
         */
        path: string;
    } | {
        source: 'directory';
        /**
         * Local directory containing .claude-plugin/marketplace.json
         */
        path: string;
    } | {
        source: 'skills-dir';
    } | {
        source: 'hostPattern';
        /**
         * Regex pattern to match the host/domain extracted from any marketplace source type. For github sources, matches against github.com. For git sources (SSH or HTTPS), extracts the hostname from the URL. Use in strictKnownMarketplaces to allow all marketplaces from a specific host (e.g., "^github\.mycompany\.com$").
         */
        hostPattern: string;
    } | {
        source: 'pathPattern';
        /**
         * Regex pattern matched against the .path field of file and directory sources. Use in strictKnownMarketplaces to allow filesystem-based marketplaces alongside hostPattern restrictions for network sources. Use ".*" to allow all filesystem paths, or a narrower pattern (e.g., "^/opt/approved/") to restrict to specific directories.
         */
        pathPattern: string;
    } | {
        source: 'settings';
        /**
         * Marketplace name. Must match the extraKnownMarketplaces key (enforced); the synthetic manifest is written under this name. Same validation as PluginMarketplaceSchema plus reserved-name rejection — validateOfficialNameSource runs after the disk write, too late to clean up.
         */
        name: string;
        /**
         * Plugin entries declared inline in settings.json
         */
        plugins: {
            /**
             * Plugin name as it appears in the target repository
             */
            name: string;
            /**
             * Where to fetch the plugin from. Must be a remote source — relative paths have no marketplace repository to resolve against. Under allowManagedPermissionRulesOnly, a settings marketplace keeps its plugins' allowed-tools only when every npm entry here pins a `registry` on a bare package name; unpinned, the package resolves through the member's own npm config, and a non-bare spelling (an `npm:` alias, a `name\@range`, a URL or git spec) packs as an exotic spec the pin does not bind — either way the marketplace vouches no tool grants.
             */
            source: string | {
                source: 'npm';
                /**
                 * Package name (or url, or local path, or anything else that can be passed to `npm` as a package)
                 */
                package: string;
                /**
                 * Specific version or version range (e.g., ^1.0.0, ~2.1.0)
                 */
                version?: string;
                /**
                 * Custom NPM registry URL (defaults to using system default, likely npmjs.org)
                 */
                registry?: string;
            } | {
                source: 'url';
                /**
                 * Full git repository URL (https:// or git\@)
                 */
                url: string;
                /**
                 * Git branch or tag to use (e.g., "main", "v1.0.0"). Defaults to repository default branch.
                 */
                ref?: string;
                /**
                 * Specific commit SHA to use
                 */
                sha?: string;
            } | {
                source: 'github';
                /**
                 * GitHub repository in owner/repo format
                 */
                repo: string;
                /**
                 * Git branch or tag to use (e.g., "main", "v1.0.0"). Defaults to repository default branch.
                 */
                ref?: string;
                /**
                 * Specific commit SHA to use
                 */
                sha?: string;
            } | {
                source: 'git-subdir';
                /**
                 * Git repository: GitHub owner/repo shorthand, https://, or git\@ URL
                 */
                url: string;
                /**
                 * Subdirectory within the repo containing the plugin (e.g., "tools/claude-plugin"). Checked out sparsely — over https or ssh as a partial clone (--filter=tree:0) — to minimize bandwidth for monorepos.
                 */
                path: string;
                /**
                 * Git branch or tag to use (e.g., "main", "v1.0.0"). Defaults to repository default branch.
                 */
                ref?: string;
                /**
                 * Specific commit SHA to use
                 */
                sha?: string;
            } | {
                source: 'archive';
                /**
                 * HTTPS URL of a zip archive containing the plugin. The plugin root (the directory holding .claude-plugin/) may be at the top of the archive or nested one directory deep — a single wrapping directory is stripped.
                 */
                url: string;
                /**
                 * SHA-256 digest of the archive. When set, every download is verified against it and the install is refused on mismatch. It also serves as the version identity when neither plugin.json nor the marketplace entry declares a `version`. Recommended. Note the update signal is the version string (plugin.json version, else the entry version, else this digest) — changing only the digest while a version is declared does not trigger an update.
                 */
                sha256?: string;
            } | {
                source: 'command';
                /**
                 * Shell command that prints the absolute path of the plugin directory on stdout (exactly one line) and exits 0. It must leave a complete plugin in that directory before exiting; the directory is copied into the plugin cache, so the printed path may change between runs (it is re-resolved on every install and update, and once per session in the background). Runs through the platform shell (sh on macOS/Linux, cmd.exe on Windows) from the user's home directory with Claude Code's subprocess environment.
                 */
                command: string;
                /**
                 * Seconds to wait for the command before giving up (default: 60)
                 */
                timeout?: number;
                /**
                 * copy (default): the printed directory is copied into the plugin cache and content-hashed, so it may be deleted afterwards. link: the cache entry links to the printed directory in place (no copy, no size limit; macOS/Linux) — for large exports; the directory must then stay valid while Claude Code runs, and a different printed path is what signals new content.
                 */
                mode?: 'copy' | 'link';
            } | {
                source: 'unsupported';
                error?: string;
            };
            description?: string;
            version?: string;
            strict?: boolean;
            /**
             * Versions of its hosts this plugin runs on. "claude-code" is a semver range (e.g. ">=2.1.320"): outside it, the plugin is not installed, updated or loaded. Other keys are ignored.
             */
            engines?: {
                [k: string]: unknown;
            };
            /**
             * HTTP headers sent when downloading this entry's `archive` source.
             */
            headers?: {
                [k: string]: string;
            };
            /**
             * Command that prints a JSON object of HTTP headers for downloading this entry's `archive` source. Runs only when a user explicitly installs or updates this plugin. Unlike a catalog entry, an entry written here does not need `strict: false`: it is declared in a settings file, which has no manifest fields to inline. A declaration in project settings is not operator-authored, so request-routing and client-identity header names are still filtered there. Use an absolute path.
             */
            headersHelper?: string;
        }[];
        owner?: {
            /**
             * Display name of the plugin author or organization
             */
            name: string;
            /**
             * Contact email for support or feedback
             */
            email?: string;
            /**
             * Website, GitHub profile, or organization URL
             */
            url?: string;
        };
    })[];
    /**
     * Controls the `command` plugin source, whose plugin directory is produced by running a marketplace-declared command on this machine. true: command-sourced plugins are never installed, updated, or re-resolved (the command never runs). false: explicitly allowed. Unset: follows allowManagedHooksOnly — an org that restricts hook execution to managed settings gets command sources disabled too. Only honored from managed settings.
     */
    disableCommandPluginSources?: boolean;
    /**
     * When true (and set in managed settings), rejects the --plugin-dir, --plugin-url, --agents, and non-sdk --mcp-config CLI flags at startup. Closes the CLI-flag bypass of strictKnownMarketplaces. Pair with allowedMcpServers for per-server MCP control; this setting does not gate other MCP entry points (SDK setMcpServers, claude mcp add, .mcp.json). Also blocks surfaces that spawn the CLI with these flags internally (see settings documentation). Only honored from managed settings; ignored in user/project/local settings.
     */
    disableSideloadFlags?: boolean;
    /**
     * Marketplace names whose plugins may surface as contextual install suggestions (relevance-based tips). No marketplace-declared suggestions surface without this allowlist; the built-in tips for Anthropic's own plugins are unaffected. Only honored when set in managed settings (policy scope); the key is ignored in user, project, and local settings. A name only takes effect when the marketplace is registered on the machine AND its registered source is also declared in managed settings, either as the extraKnownMarketplaces entry for that name or as an entry of strictKnownMarketplaces. A marketplace registered from a different source under an allowlisted name is ignored. The official marketplace is exempt from the source requirement: allowlisting its name alone suffices, since that name can only register from the official Anthropic source.
     */
    pluginSuggestionMarketplaces?: string[];
    /**
     * Force a specific login method: "claudeai" for a Claude subscription (individual, Team, or Enterprise plans), "console" for Console billing, "gateway" for the Cloud gateway OIDC device flow
     */
    forceLoginMethod?: 'claudeai' | 'console' | 'gateway';
    /**
     * Cloud gateway URL to pre-fill during login, alongside forceLoginMethod: "gateway". Honored from admin-controlled managed settings (MDM / managed-settings.json / policy helper) and, on a machine with none of those, from your own user settings; ignored in project, local, flag, and remote-delivered settings.
     */
    forceLoginGatewayUrl?: string;
    /**
     * IPv4 CIDR blocks (at most 4, each /8 to /32, not overlapping) your Cloud gateway sits in: the public block your organization numbers its internal network from, which lets /login reach a gateway there. A block must lie entirely outside private space, where /login accepts a gateway without this key. /login accepts a gateway inside a listed block over a direct connection only, and only when this machine's own address on that connection is inside the same block, so /login must happen from a machine whose own address is inside the block (not through a proxy, VPN pool, container or NAT segment outside it). A bar against copied settings files, not proof of location. Honored only from admin-controlled managed settings (MDM / managed-settings.json / policy helper); ignored in user, project, and remote-delivered settings.
     */
    gatewayInternalNetworks?: string[];
    /**
     * Controls whether the SDK parent tier (Options.managedSettings / --managed-settings) layers under this admin tier. "first-wins" (the default, except in a gateway session Claude Desktop's Code tab launched, where "merge" is): parent is dropped — admin tiers are the only policy source. "merge": parent's restrictive-only-filtered settings union under the admin winner. Has no effect when no admin tier exists (parent applies as the sole policy tier, still filtered restrictive-only).
     */
    parentSettingsBehavior?: 'first-wins' | 'merge';
    /**
     * Controls how the managed settings sources compose. "first-wins" (default): the highest-priority source present (server-managed > MDM (managed plist / HKLM) > managed-settings.json) is the managed tier alone. "merge": every present source deep-merges with fixed precedence server-managed > MDM > managed-settings.json — scalars take the highest source's value (a restrictive boolean or enum — the allowManaged*Only locks, the disable* switches, the sandbox lock family — takes the strictest value any source sets) and arrays union, except fallbackModel, the restriction allowlists allowedMcpServers, allowedProviders, availableModels, strictKnownMarketplaces and allowedChannelPlugins, and sandbox.credentials.awsPairs and sandbox.ripgrep (the highest source that sets one owns it whole), modelOverrides (the whole map of the highest source that sets it, dropped when that source sits below the one that sets availableModels), managedMcpServers (server names union; a name set by two sources takes the higher source's whole entry), and the keys taken from the highest source only: the auth pins forceLoginOrgUUID, forceLoginMethod, forceLoginGatewayUrl and gatewayInternalNetworks, allowNestedModelAccessUnderForceLogin, the credential helpers apiKeyHelper, awsAuthRefresh, awsCredentialExport, gcpAuthRefresh, otelHeadersHelper and proxyAuthHelper, modelPicker, permissions.defaultMode, parentSettingsBehavior and the policyHelper configuration (env keeps its own per-key union). In both modes, a forceLoginOrgUUID, or a forceLoginMethod of claudeai or console, that this machine's own MDM policy or managed settings file sets applies ahead of server-managed settings. Honored only from the highest-priority source present; enable it only when every lower source is admin-controlled, since lower sources then contribute entries such as permissions.allow. HKCU and --managed-settings never take part in the merge.
     */
    managedSourcesBehavior?: 'first-wins' | 'merge';
    /**
     * Organization UUID to require for OAuth login. Accepts a single UUID string or an array of UUIDs (any one is permitted). When set in managed settings, login fails if the authenticated account does not belong to a listed organization.
     */
    forceLoginOrgUUID?: string | string[];
    /**
     * Self-hosted runner hosts only. Set to true to let a Claude Code started by a runner session's command use the runner's model access (--nested-model-access) when this machine's managed settings set forceLoginOrgUUID or forceLoginMethod. It asks the runner which organization the session owner's sign-in belongs to, and stops if the pin does not permit it or the runner does not answer. Without this key it is left signed out. Any program on the machine can pretend to be the runner, so with this key the pin is not a security boundary: set it on runner hosts only, never in a profile that reaches people's own computers. Honored only from this machine's own administrator sources (MDM, the managed settings file, or a policy helper that they name); ignored in server-managed, user, project, local and --settings sources.
     */
    allowNestedModelAccessUnderForceLogin?: boolean;
    /**
     * Managed settings only (managed-settings.json, MDM, or server-managed). The API providers Claude Code may use on this machine: "anthropic" (the Anthropic API on Anthropic's own host, via a claude.ai or Console sign-in or an API key; pair it with forceLoginMethod / forceLoginOrgUUID to require a sign-in), "bedrock", "vertex", "foundry", "anthropicAws", "mantle" (each meaning that provider's own service: its regional, FIPS, private-endpoint and sovereign-cloud hosts), "customEndpoint" (the Anthropic API or a cloud provider's API sent to some other host — ANTHROPIC_BASE_URL, that provider's ANTHROPIC_*_BASE_URL, a Foundry resource name that is not a bare name, or for Bedrock the AWS SDK's AWS_ENDPOINT_URL[_BEDROCK[_RUNTIME]] — such as an LLM gateway; admitted only for the value pinned in the "env" block of the same managed source), or "gateway" (the Cloud gateway sign-in). A session on a provider that is not listed is refused at startup, at login, and when it next contacts the API, with a message naming what selected the provider and the entry that would allow it. Under a list, where first-party traffic goes (ANTHROPIC_BASE_URL, a gateway sign-in) is honored only when the same managed source pins it in "env" (or forceLoginGatewayUrl), and a claude ssh tunnel into the machine is refused. A cloud provider's credential and tenancy variables, and the network path and TLS trust (HTTPS_PROXY, NODE_EXTRA_CA_CERTS, CLAUDE_CODE_CERT_STORE), are not judged by this list; set those for the fleet in the managed "env" block, whose values replace the user's. To route Bedrock through a gateway for a fleet, pin ANTHROPIC_BEDROCK_BASE_URL there (it is what the clients use, ahead of an endpoint_url in ~/.aws/config, which this list does not judge); the AWS SDK's AWS_ENDPOINT_URL* pins only sanction where the SDK's own clients go and never stand in for the "bedrock" entry. Unset allows every provider; an empty array allows none. Only a list in managed-settings.json or MDM is enforcement on the machine: it cannot be widened or hidden by server-managed settings and reaches every session. A list set only in the admin console reaches only sessions that fetch your server-managed settings — not a session on a cloud provider, another organization or a non-Anthropic ANTHROPIC_BASE_URL, one authenticating only with apiKeyHelper or ANTHROPIC_AUTH_TOKEN, a Pro/Max/Ultra login, --bare without an API key, or a first launch before the fetch lands — all conditions the user controls. Versions that predate this setting ignore it; pair it with a minimum-version policy on a mixed fleet. 'claude auth status' reports the Anthropic API as apiProvider "firstParty".
     */
    allowedProviders?: ('anthropic' | 'customEndpoint' | 'bedrock' | 'vertex' | 'foundry' | 'anthropicAws' | 'mantle' | 'gateway')[];
    /**
     * When set in managed settings, the CLI blocks startup until remote managed settings are freshly fetched, and exits if the fetch fails
     */
    forceRemoteSettingsRefresh?: boolean;
    /**
     * Path to a script that outputs OpenTelemetry headers
     */
    otelHeadersHelper?: string;
    /**
     * Controls the output style for assistant responses
     */
    outputStyle?: string;
    /**
     * Default transcript view mode on startup
     */
    viewMode?: 'default' | 'verbose' | 'focus';
    /**
     * Preferred language for Claude responses and voice dictation (e.g., "japanese", "spanish")
     */
    language?: string;
    /**
     * Skip the WebFetch blocklist check for enterprise environments with restrictive security policies
     */
    skipWebFetchPreflight?: boolean;
    sandbox?: {
        /**
         * Run Bash commands inside the sandbox. Default: false. When managed settings or a --settings file set allowUnsandboxedCommands: false, or managed settings set network.allowManagedDomainsOnly: true, and managed, --settings or user settings set true, false from project settings (.claude/settings.json and .claude/settings.local.json) is ignored (true there still applies).
         */
        enabled?: boolean;
        /**
         * Exit with an error at startup if sandbox.enabled is true but the sandbox cannot start (missing dependencies or unsupported platform). When false (default), a warning is shown and commands run unsandboxed. Intended for managed-settings deployments that require sandboxing as a hard gate. A Claude Code on the web, scheduled-task or Cowork cloud session (Anthropic's cloud container, which has no command sandbox) starts anyway with a warning: the container isolates it, and the sandbox.filesystem and sandbox.network rules in settings are not enforced there. When managed settings or a --settings file set allowUnsandboxedCommands: false, or managed settings set network.allowManagedDomainsOnly: true, and managed, --settings or user settings set true, false from project settings (.claude/settings.json and .claude/settings.local.json) is ignored (true there still applies).
         */
        failIfUnavailable?: boolean;
        /**
         * macOS and Linux/WSL only: approve a Bash command that will run inside the sandbox without a permission prompt, unless a deny rule, a command-specific ask rule or a safety check stops it. Default: false, so sandboxed commands go through the same permission flow as any other command. Has no effect on native Windows.
         */
        autoAllowBashIfSandboxed?: boolean;
        /**
         * Allow commands to run outside the sandbox via the dangerouslyDisableSandbox parameter. When false, the dangerouslyDisableSandbox parameter is completely ignored and all commands must run sandboxed. Default: true. A false in managed, --settings or user settings holds whatever project settings (.claude/settings.json and .claude/settings.local.json) say (false there still applies).
         */
        allowUnsandboxedCommands?: boolean;
        network?: {
            /**
             * Domains sandboxed commands may reach without a prompt (wildcards such as *.example.com supported). Merged with WebFetch(domain:…) allow rules and across settings sources. When managed settings or a --settings file set allowUnsandboxedCommands: false, or managed settings set network.allowManagedDomainsOnly: true, values from project settings (.claude/settings.json and .claude/settings.local.json) are ignored. With network.allowManagedDomainsOnly, only managed settings supply it.
             */
            allowedDomains?: string[];
            /**
             * Domains that are always blocked, even if matched by allowedDomains. Supports the same wildcard syntax as allowedDomains. Merged from all settings sources regardless of allowManagedDomainsOnly.
             */
            deniedDomains?: string[];
            /**
             * When true, the sandbox runtime deterministically denies hosts not in allowedDomains instead of prompting. Enforced for sandboxed commands only — in-process tools such as WebFetch are not gated by this setting. Only honored from user, managed/policy, or CLI (--settings) settings — project settings (.claude/settings.json and .claude/settings.local.json) are ignored, and while it is on their allowedDomains and WebFetch(domain:…) allow rules are left out of the allowlist.
             */
            strictAllowlist?: boolean;
            /**
             * When true (and set in managed settings), only allowedDomains and WebFetch(domain:...) allow rules from managed settings are respected. User, project, local, and flag settings domains are ignored. Denied domains are still respected from all sources.
             */
            allowManagedDomainsOnly?: boolean;
            /**
             * macOS only: Unix socket paths to allow. Ignored on Linux (seccomp cannot filter by path). Merged across settings sources. When managed settings or a --settings file set allowUnsandboxedCommands: false, or managed settings set network.allowManagedDomainsOnly: true, values from project settings (.claude/settings.json and .claude/settings.local.json) are ignored.
             */
            allowUnixSockets?: string[];
            /**
             * If true, allow all Unix sockets (disables blocking on both platforms). When managed settings or a --settings file set allowUnsandboxedCommands: false, or managed settings set network.allowManagedDomainsOnly: true, true from project settings (.claude/settings.json and .claude/settings.local.json) is ignored (false there still applies).
             */
            allowAllUnixSockets?: boolean;
            /**
             * macOS only: If true, sandboxed commands can bind to localhost ports. When managed settings or a --settings file set allowUnsandboxedCommands: false, or managed settings set network.allowManagedDomainsOnly: true, true from project settings (.claude/settings.json and .claude/settings.local.json) is ignored (false there still applies).
             */
            allowLocalBinding?: boolean;
            /**
             * macOS only: Additional XPC/Mach service names to allow looking up. Supports trailing-wildcard prefix matching (e.g., "com.apple.CoreSimulator.*"). Needed for tools that communicate via XPC such as the iOS Simulator or Playwright. Each entry lets sandboxed commands reach services outside the sandbox, and the sandbox does not confine what those services do for them. Merged across settings sources. When managed settings or a --settings file set allowUnsandboxedCommands: false, or managed settings set network.allowManagedDomainsOnly: true, values from project settings (.claude/settings.json and .claude/settings.local.json) are ignored.
             */
            allowMachLookup?: string[];
            /**
             * Local TCP port of your own HTTP proxy for sandboxed traffic, used instead of the proxy Claude Code runs. When managed settings or a --settings file set allowUnsandboxedCommands: false, network.deniedDomains or a WebFetch(domain:…) deny rule, when managed settings set network.allowManagedDomainsOnly: true, or when managed, --settings or user settings set network.strictAllowlist: true, values from project settings (.claude/settings.json and .claude/settings.local.json) are ignored. With network.allowManagedDomainsOnly, only managed settings may set it.
             */
            httpProxyPort?: number;
            /**
             * Local TCP port of your own SOCKS5 proxy for sandboxed traffic, used instead of the proxy Claude Code runs. When managed settings or a --settings file set allowUnsandboxedCommands: false, network.deniedDomains or a WebFetch(domain:…) deny rule, when managed settings set network.allowManagedDomainsOnly: true, or when managed, --settings or user settings set network.strictAllowlist: true, values from project settings (.claude/settings.json and .claude/settings.local.json) are ignored. With network.allowManagedDomainsOnly, only managed settings may set it.
             */
            socksProxyPort?: number;
            /**
             * [EXPERIMENTAL] Enable in-process TLS termination so the per-request filter can see HTTPS request bodies. Provide a CA cert+key, or omit both to have sandbox-runtime generate an ephemeral one for the session. On native Windows an ephemeral CA cannot pass the sandbox trust check, so omitting the paths uses a persistent CA managed by the sandbox runtime (set up and trusted via /sandbox install); configured paths are passed to the sandbox runtime verbatim, which rejects a bad or incomplete pair at sandbox initialization. Only honored from user, managed/policy, or CLI (`--settings`) settings — project settings (.claude/settings.json and .claude/settings.local.json) are ignored.
             */
            tlsTerminate?: {
                caCertPath?: string;
                caKeyPath?: string;
            };
        };
        filesystem?: {
            /**
             * Additional paths to allow writing within the sandbox. Merged with paths from Edit(...) allow permission rules. When managed settings or a --settings file set allowUnsandboxedCommands: false, or managed settings set network.allowManagedDomainsOnly: true, values from project settings (.claude/settings.json and .claude/settings.local.json) are ignored. When managed settings or a --settings file set filesystem.denyRead, a Read(…) deny rule or a credentials.files entry (deny or mask), a value from project settings (.claude/settings.json and .claude/settings.local.json) under or equal to a denied path, or spelled as a glob or a network path (UNC or automount), is ignored. A value inside a directory sandboxed commands can already write is re-checked before every command and dropped once it has been re-pointed into a denied read path.
             */
            allowWrite?: string[];
            /**
             * Additional paths to deny writing within the sandbox. Merged with paths from Edit(...) deny permission rules.
             */
            denyWrite?: string[];
            /**
             * Additional paths to deny reading within the sandbox. Merged with paths from Read(...) deny permission rules.
             */
            denyRead?: string[];
            /**
             * Paths to re-allow reading within denyRead regions. Takes precedence over denyRead for matching paths. When managed settings or a --settings file set allowUnsandboxedCommands: false, filesystem.denyRead, a Read(…) deny rule or a credentials.files entry (deny or mask), or managed settings set network.allowManagedDomainsOnly: true, a value from project settings (.claude/settings.json and .claude/settings.local.json) that would re-open a path managed, --settings or user settings deny reading is ignored, as is one spelled as a glob or a network path (UNC or automount); one carving out of the project's own denyRead still applies. A value inside a directory sandboxed commands can write is re-checked before every command and dropped once it has been re-pointed into a denied path.
             */
            allowRead?: string[];
            /**
             * When true (set in managed settings), only allowRead paths from policySettings are used.
             */
            allowManagedReadPathsOnly?: boolean;
            /**
             * macOS and Linux/WSL only: skip filesystem isolation entirely while keeping network and seccomp isolation. Ignored on native Windows, where the sandboxed process runs as a separate user with no inherent rights, so skipping the filesystem rules would withhold every access grant rather than loosen them — filesystem isolation stays on there. Sandboxed commands get unrestricted read/write access to the host filesystem; network egress is still confined to network.allowedDomains. Intended for deployments whose goal is egress control rather than filesystem containment. Does not change Bash prompting: sandbox.autoAllowBashIfSandboxed is independent and still defaults to false, so sandboxed commands keep going through the permission flow unless it is set to true. Drops the read protection from filesystem.denyRead and credentials.files deny entries for sandboxed commands, since both are enforced by the filesystem layer this turns off; credentials.files mask entries (sentinel binds) and credentials.envVars deny/mask are unaffected. Only honored from user, managed/policy, or CLI (`--settings`) settings — project settings (.claude/settings.json and .claude/settings.local.json) are ignored. If managed settings configure sandbox.filesystem at all, or list any sandbox.credentials.files deny entry, only managed settings can set this: an admin who deployed filesystem restrictions must not have them switched off by a user-writable file. (sandbox.credentials.envVars and credentials.files mask entries do not pin it — env scrubbing and sentinel binds are independent of the filesystem layer and survive this setting.) When unset, filesystem isolation stays on.
             */
            disabled?: boolean;
        };
        credentials?: {
            /**
             * Credential files or directories to protect. `deny` blocks reads inside the sandbox; `mask` substitutes a sentinel inside the sandbox (whole-file, or per-`extract` capture) and injects the real value at the proxy. On macOS and Windows `mask` degrades to `deny`.
             */
            files?: {
                /**
                 * Path to a credential file or directory. Same resolution as sandbox.filesystem.* paths: absolute, ~ expanded, or relative to the settings file root (project root for project settings, ~/.claude for user settings).
                 */
                path: string;
                /**
                 * Access mode for this path. `deny` blocks reads inside the sandbox; `mask` shows sandboxed commands a sentinel-substituted copy (whole-file, or only the spans captured by `extract`) and the host proxy swaps sentinel→real on egress to `injectHosts`. On macOS and Windows `mask` currently degrades to `deny`.
                 */
                mode: 'deny' | 'mask';
                /**
                 * Optional regex for structured masking when mode is `mask`. Applied globally to the file; capture group 1 of each match is a credential value, and only those captured spans are replaced with sentinels — the rest of the file is preserved so a tool that parses it (.netrc, JSON, YAML) still succeeds. Without `extract`, the entire file content is replaced with one sentinel (whole-file masking, suited to single-secret files). If the regex matches nothing, behavior is governed by `onExtractNoMatch` (default `warn`). Accepted but ignored for `deny`.
                 */
                extract?: string;
                /**
                 * What to do when `extract` matches nothing in the file — or, with `decode`, when no candidate survives verification. `warn` (default) emits a stderr warning and leaves the file readable as-is inside the sandbox (fail-open, for credentials that may be legitimately absent); `deny` degrades the entry to mode `deny` so the file is unreadable (fail-closed) — under `sandbox.filesystem.disabled` it is treated as `error`, since read-denies are dropped in that mode; `error` aborts at sandbox setup so nothing runs until the config is fixed. Only meaningful when mode is `mask` and `extract` or `decode` is set; accepted but ignored otherwise.
                 */
                onExtractNoMatch?: 'warn' | 'deny' | 'error';
                /**
                 * Optional encoded-credential format for `mask` mode. `jwt`: candidates are located with a built-in JWT regex (or the explicit `extract` pattern, if set), verified to actually be JWTs before masking, and replaced with a structurally valid fake JWT so client-side token parsing inside the sandbox keeps working. If no candidate verifies, behavior is governed by `onExtractNoMatch` (default `warn`). Accepted but ignored for `deny`.
                 */
                decode?: 'jwt';
                /**
                 * Names of top-level payload claims to mask inside each decoded value, instead of replacing the whole token. Each named claim present with a string value gets its own sentinel and the token is rebuilt around the modified payload; all other claims are preserved so a tool that decodes the token and reads a non-secret claim keeps working. Requires `decode`. If no named claim matches in any verified token, behavior is governed by `onExtractNoMatch` (default `warn`). Only meaningful when mode is `mask`; accepted but ignored for `deny`.
                 */
                maskClaims?: string[];
                /**
                 * If true, verbatim occurrences of each captured credential value outside the regex-matched spans are also replaced with the corresponding sentinel — for a secret repeated where the regex does not reach (e.g. pasted into a comment). Matches raw substrings, so short or common values may corrupt unrelated content; intended for long, high-entropy secrets. Defaults to false. Only meaningful when mode is `mask` and `extract` or `decode` is set; accepted but ignored otherwise.
                 */
                maskDuplicates?: boolean;
                /**
                 * Optional narrowing of where the proxy substitutes this credential. Only meaningful when mode is `mask`; accepted but ignored for `deny`. If unset, defaults to `network.allowedDomains` — the credential is injected at every reachable host. Each entry must be reachable via `network.allowedDomains` (sandbox-runtime validates this).
                 */
                injectHosts?: string[];
            }[];
            /**
             * Environment variables to protect. `deny` unsets the variable for sandboxed commands; `mask` substitutes a sentinel inside the sandbox and injects the real value at the proxy.
             */
            envVars?: {
                /**
                 * Environment variable name.
                 */
                name: string;
                /**
                 * Access mode for this environment variable. `deny` unsets the variable for sandboxed commands; `mask` shows sandboxed commands a sentinel value and the host proxy swaps sentinel→real on egress to `injectHosts`.
                 */
                mode: 'deny' | 'mask';
                /**
                 * Optional regex for structured masking when mode is `mask`. Applied globally to the value; capture group 1 of each match is a credential value, and only those captured spans are replaced with sentinels — the rest of the value is preserved so a tool that parses it (a `DATABASE_URL` connection string, a composite `KEY:SECRET` pair) still succeeds inside the sandbox. Without `extract`, the entire value is replaced with one sentinel (whole-value masking, suited to bare tokens). If the regex matches nothing, behavior is governed by `onExtractNoMatch` (default `warn`). Cannot be combined with `decode` (the decode path never consults it). Accepted but ignored for `deny`.
                 */
                extract?: string;
                /**
                 * What to do when `extract` matches nothing in the value. `warn` (default) emits a stderr warning and lets the variable pass through unmasked (fail-open, for credentials that may be legitimately absent); `deny` unsets the variable inside the sandbox (fail-closed); `error` aborts at sandbox setup so nothing runs until the config is fixed. Only meaningful when mode is `mask` and `extract` is set without `decode`. On a mask entry with `decode`, the runtime takes the decode path and never consults this field, so a fail-closed setting cannot be honored — `deny` and `error` are rejected there; only `warn` is accepted. In all other shapes the field is accepted but ignored.
                 */
                onExtractNoMatch?: 'warn' | 'deny' | 'error';
                /**
                 * Optional encoded-credential format for `mask` mode. `jwt`: the variable's whole value is verified to actually be a JWT and replaced with a structurally valid fake JWT so client-side token parsing inside the sandbox keeps working; the proxy swaps the whole fake token on egress. If the value does not verify, the variable is left unmasked with a stderr warning (fail-open). Cannot be combined with `extract` — the decode path never consults it. Accepted but ignored for `deny`.
                 */
                decode?: 'jwt';
                /**
                 * Names of top-level payload claims to mask inside the decoded value, instead of replacing the whole token. Each named claim present with a string value gets its own sentinel and the token is rebuilt around the modified payload; all other claims are preserved so claim-reading clients keep working. Requires `decode`. If no named claim matches, the variable is left unmasked with a stderr warning (fail-open). Only meaningful when mode is `mask`; accepted but ignored for `deny`.
                 */
                maskClaims?: string[];
                /**
                 * Optional narrowing of where the proxy substitutes this credential. Only meaningful when mode is `mask`; accepted but ignored for `deny`. If unset, defaults to `network.allowedDomains` — the credential is injected at every reachable host. A masked AWS secret key that signs requests is the exception: with no list it is never injected. Each entry must be reachable via `network.allowedDomains` (sandbox-runtime validates this).
                 */
                injectHosts?: string[];
            }[];
            /**
             * Allow sentinel→real substitution on the plain-HTTP proxy path. Defaults to false: without TLS termination the upstream identity is unverified and the credential travels in cleartext. Set only for trusted-network test fixtures. Only honored from user, managed/policy, or CLI (`--settings`) settings — project settings (.claude/settings.json and .claude/settings.local.json) are ignored.
             */
            allowPlaintextInject?: boolean;
            /**
             * Explicit groupings of masked env vars into AWS credential pairs for SigV4 re-signing, for non-standard variable names. The conventional AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN trio is paired automatically when masked. Only honored from user, managed/policy, or CLI (`--settings`) settings — project settings (.claude/settings.json and .claude/settings.local.json) are ignored. A member is only usable when its env var is forwarded as a whole-value `mask` entry (an entry carrying `extract` or `decode` does not qualify — re-signing needs the whole real value). A pair whose key id or secret member is unusable never re-signs: it is dropped, unless it names a conventional AWS variable, in which case it is forwarded as an inert suppressor so implicit auto-pairing stays overridden. A pair whose ONLY unusable member is the session token still re-signs, without an x-amz-security-token (temporary-credential requests fail upstream until the entry is fixed).
             */
            awsPairs?: {
                /**
                 * Name of the masked env var holding the AWS access key id.
                 */
                accessKeyIdVar: string;
                /**
                 * Name of the masked env var holding the AWS secret access key.
                 */
                secretAccessKeyVar: string;
                /**
                 * Optional name of the masked env var holding the AWS session token (temporary credentials). When set, the proxy sends the real token as x-amz-security-token on re-signed requests and adds it to the signed header set if the client did not.
                 */
                sessionTokenVar?: string;
            }[];
            /**
             * Policies for AWS SigV4 request shapes the proxy cannot re-sign (streaming, presigned, sigv4a) when they reference a masked credential pair: `deny` (default) or `passthrough`. Only honored from user, managed/policy, or CLI (`--settings`) settings — project settings (.claude/settings.json and .claude/settings.local.json) are ignored.
             */
            sigv4?: {
                /**
                 * Policy for aws-chunked streaming uploads (x-amz-content-sha256: STREAMING-*): per-chunk signatures chain off the seed signature, so re-signing would require rewriting the body. `deny` (default) fails closed with a 403; `passthrough` forwards the request unre-signed (the upstream will reject its signature).
                 */
                streaming?: 'deny' | 'passthrough';
                /**
                 * Policy for presigned URLs (X-Amz-Algorithm/X-Amz-Signature in the query, no Authorization header): the signature lives in the URL itself. `deny` (default) or `passthrough`.
                 */
                presigned?: 'deny' | 'passthrough';
                /**
                 * Policy for SigV4A (AWS4-ECDSA-P256-SHA256) asymmetric signatures: there is no shared-key HMAC to recompute. `deny` (default) or `passthrough`.
                 */
                sigv4a?: 'deny' | 'passthrough';
            };
        };

        /**
         * Sandbox violations to leave unreported: a map of command patterns ("*" for every command) to the filesystem paths whose violations are ignored. Merged across settings sources. When managed settings or a --settings file set allowUnsandboxedCommands: false, or managed settings set network.allowManagedDomainsOnly: true, values from project settings (.claude/settings.json and .claude/settings.local.json) are ignored.
         */
        ignoreViolations?: {
            [k: string]: string[];
        };
        /**
         * Linux only: Run without the fresh /proc mount, for hosts such as unprivileged Docker containers that cannot create one. **Reduces security** — the host /proc stays readable by sandboxed commands. Default: false. When managed settings or a --settings file set allowUnsandboxedCommands: false, or managed settings set network.allowManagedDomainsOnly: true, true from project settings (.claude/settings.json and .claude/settings.local.json) is ignored (false there still applies).
         */
        enableWeakerNestedSandbox?: boolean;
        /**
         * Linux/WSL only: Let sandboxed commands create user namespaces of their own, which the sandbox refuses by default. Needed by tools that sandbox themselves that way, such as Chromium's and Electron's sandbox, a nested bubblewrap, and `unshare`. **Removes code-execution isolation** — in any folder a hostile command may write, it can then bypass filesystem.denyWrite, filesystem.denyRead, credentials.files entries and the paths the sandbox always write-protects (such as .claude/settings.json, git hooks and git config), and so plant code that later runs outside the sandbox; while autoAllowBashIfSandboxed is on, the command that plants it needs no approval. Default: false. Only honored from user, managed/policy, or CLI (--settings) settings — true from project settings (.claude/settings.json and .claude/settings.local.json) is ignored (false there still applies).
         */
        allowNestedUserNamespaces?: boolean;
        /**
         * macOS only: Allow access to com.apple.trustd.agent in the sandbox. Needed for Go-based CLI tools (gh, gcloud, terraform, etc.) to verify TLS certificates when using httpProxyPort with a MITM proxy and custom CA. **Reduces security** — opens a potential data exfiltration vector through the trustd service. Default: false. When managed settings or a --settings file set allowUnsandboxedCommands: false, or managed settings set network.allowManagedDomainsOnly: true, true from project settings (.claude/settings.json and .claude/settings.local.json) is ignored (false there still applies).
         */
        enableWeakerNetworkIsolation?: boolean;
        /**
         * macOS only: Allow sandboxed commands to send Apple Events (and look up the appleeventsd Mach service). Needed for `open`, `osascript`, and browser-based auth flows that open URLs. **Removes code-execution isolation** — sandboxed commands can launch other applications unsandboxed with no user prompt, and can script running apps (e.g. Terminal) subject to the user's per-app TCC automation consent. Only honored from user, managed/policy, or CLI (--settings) settings — project settings (.claude/settings.json and .claude/settings.local.json) are ignored. Default: false
         */
        allowAppleEvents?: boolean;
        /**
         * Command patterns (Bash permission-rule syntax) for commands to run outside the sandbox. An entry takes a call out of the sandbox only when every command in the call matches an entry: in a Bash pipe or a chain such as `a && b`, each part needs its own match. Some calls stay sandboxed whatever the entries, such as one with a `cd`, a command substitution, or a redirect other than a file-descriptor duplication like `2>&1`, a heredoc included. A convenience, not a security boundary: excluded commands still go through the permission flow. Merged across settings sources. When managed settings or a --settings file set allowUnsandboxedCommands: false, or managed settings set network.allowManagedDomainsOnly: true, values from project settings (.claude/settings.json and .claude/settings.local.json) are ignored.
         */
        excludedCommands?: string[];
        /**
         * Custom ripgrep configuration for bundled ripgrep support. Only honored from user, managed/policy, or CLI (--settings) settings — project settings (.claude/settings.json and .claude/settings.local.json) are ignored.
         */
        ripgrep?: {
            command: string;
            args?: string[];
        };
        /**
         * Linux/WSL only: Absolute path to the bwrap (bubblewrap) binary. Overrides auto-detection via PATH. Only honored from admin-controlled managed settings.
         */
        bwrapPath?: string;
        /**
         * Linux/WSL only: Absolute path to the socat binary used for the sandbox network proxy. Overrides auto-detection via PATH. Only honored from admin-controlled managed settings.
         */
        socatPath?: string;
        [k: string]: unknown;
    };
    /**
     * Probability (0–1) that the session quality survey appears when eligible. 0.05 is a reasonable starting point.
     */
    feedbackSurveyRate?: number;
    /**
     * Model-drafted feedback (the SendFeedback tool). "notify" (default) shows a one-line notice when a draft is queued; "quiet" shows only the footer counter; "off" disables the tool entirely so drafts are never queued.
     */
    feedbackDrafts?: 'notify' | 'quiet' | 'off';
    /**
     * Whether to show tips in the spinner
     */
    spinnerTipsEnabled?: boolean;

    /**
     * Customize spinner verbs. mode: "append" adds verbs to defaults, "replace" uses only your verbs.
     */
    spinnerVerbs?: {
        mode: 'append' | 'replace';
        verbs: string[];
    };
    /**
     * Add your organization's own tips to the spinner tip rotation. tips: strings or {id, text, cooldownSessions?, priority?} objects; tipsFile: a JSON file of the same; label: prefix shown before your tips; excludeDefault: if true, only show your tips (default: false).
     */
    spinnerTipsOverride?: {
        excludeDefault?: boolean;
        tips?: (string | {
            [k: string]: unknown;
        })[];
        /**
         * Absolute or ~/ local path to a JSON file holding an array of tips (same shapes as `tips`); honored from user, --settings and on-disk managed settings only. Read once per CLI process (restart to pick up edits).
         */
        tipsFile?: string;
        /**
         * Prefix shown before your tips in the spinner (default "Tip")
         */
        label?: string;
        [k: string]: unknown;
    };
    /**
     * Whether to disable syntax highlighting in diffs
     */
    syntaxHighlightingDisabled?: boolean;
    /**
     * Maximum width, in terminal columns, of the prose in Claude's responses (paragraphs, headings, lists, blockquotes). In a wider terminal the prose wraps at this width while tables and code blocks keep the full width; only the display wraps, the response text itself gains no line breaks. Minimum 40. Unset (the default) uses the full terminal width.
     */
    maxProseWidth?: number;
    /**
     * Underline misspelled words in the prompt input as you type, using an installed aspell, hunspell or ispell (off unless "enabled" is true; does nothing if none is installed). Read from user, flag and managed settings only (the whole block from the highest-precedence of those applies); ignored in project .claude/settings.json and .claude/settings.local.json.
     */
    spellcheck?: {
        /**
         * Turn on spell checking of the prompt input (default: false)
         */
        enabled?: boolean;
        /**
         * Which spell checker to run: "aspell", "hunspell", "ispell", or "auto" (default) for the first of those found on PATH
         */
        checker?: string;
        /**
         * Dictionary to use, passed to the checker as-is (aspell --lang, hunspell -d, ispell -d), e.g. "en_GB"; names are checker-specific (letters, digits and _ - . , only). Default: the checker's own default
         */
        language?: string;
        /**
         * Color of misspelled words (they are also underlined): a terminal color name such as "red" or "magenta", "#rrggbb", "rgb(r,g,b)", "ansi256(n)" or "ansi:<name>". Default: the theme's error color
         */
        color?: string;
        [k: string]: unknown;
    };
    /**
     * Whether /rename updates the terminal tab title (defaults to true). Set to false to keep auto-generated topic titles.
     */
    terminalTitleFromRename?: boolean;
    /**
     * Prompt cache TTL for the main conversation (interactive, -p and SDK turns, plus the helpers that run inline with it): "5m" or "1h". Unset = automatic: 1 hour on a Claude subscription within its usage limits, 5 minutes on an API key, Bedrock, Vertex or Foundry. 1-hour cache writes are billed at a higher rate; the cache stays warm across longer breaks. The CLAUDE_CODE_PROMPT_CACHE_TTL environment variable takes precedence.
     */
    promptCacheTtl?: '5m' | '1h';
    /**
     * Prompt cache TTL for everything outside the main conversation — subagents, workflows, background and helper requests: "5m" or "1h". Unset = automatic (5 minutes unless ENABLE_PROMPT_CACHING_1H=1). The CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL environment variable takes precedence.
     */
    subagentPromptCacheTtl?: '5m' | '1h';
    /**
     * When false, thinking is disabled. When absent or true, thinking is enabled automatically for supported models.
     */
    alwaysThinkingEnabled?: boolean;
    /**
     * Persisted effort level for supported models.
     */
    effortLevel?: 'low' | 'medium' | 'high' | 'xhigh';
    /**
     * Maximum effort level. Anything above it (an /effort or /model pick, --effort, CLAUDE_CODE_EFFORT_LEVEL, a model default) is clamped to it, on every provider including Bedrock, Vertex and Foundry. Combines with an organization's per-model effort cap by taking the lower of the two; across settings files the lowest value wins, and modelSettings.<model>.maxEffortLevel replaces it per model. Enforced client-side: an effort supplied through CLAUDE_CODE_EXTRA_BODY is not clamped.
     */
    maxEffortLevel?: 'low' | 'medium' | 'high' | 'xhigh' | 'max';
    /**
     * Per-model settings keyed by canonical model name.
     */
    modelSettings?: {
        [k: string]: {
            /**
             * Persisted effort level for this model.
             */
            effortLevel?: 'low' | 'medium' | 'high' | 'xhigh';
            /**
             * Maximum effort level for this model. Within one settings file it replaces the top-level maxEffortLevel for the model ("max" exempts it); across settings files the lowest applicable value wins. Keyed like effortLevel: the canonical model name also matches its dated, [1m], Bedrock and Vertex spellings.
             */
            maxEffortLevel?: 'low' | 'medium' | 'high' | 'xhigh' | 'max';
            /**
             * Auto-compact window for this model, in tokens (at least 100000), or "auto" for the window tuned for the model. Within one settings file it replaces the top-level autoCompactWindow for the model. /autocompact saves here. The canonical model name as key also matches its dated, [1m], Bedrock and Vertex spellings.
             */
            autoCompactWindow?: 'auto' | number;
            [k: string]: unknown;
        };
    };
    /**
     * Enable ultracode for the session: standing dynamic-workflow orchestration at any effort level. Session-scoped — typically provided via --settings or the apply_flag_settings control request; interactive toggles never persist it. Requires workflows to be enabled and a model that supports ultracode.
     */
    ultracode?: boolean;
    /**
     * Auto-compact window size
     */
    autoCompactWindow?: number;
    /**
     * Advisor model for the server-side advisor tool.
     */
    advisorModel?: string;
    /**
     * When true, fast mode is enabled. When absent or false, fast mode is off. On Vertex a saved value is ignored: use /fast each session.
     */
    fastMode?: boolean;
    /**
     * When true, fast mode does not persist across sessions. Each session starts with fast mode off.
     */
    fastModePerSessionOptIn?: boolean;
    /**
     * When false, prompt suggestions are disabled. When absent or true, prompt suggestions are enabled.
     */
    promptSuggestionEnabled?: boolean;
    /**
     * When false, the :emoji: shortcode typeahead (the suggestion popup and the :name: inline replacement) is disabled. When absent or true, it is enabled.
     */
    emojiCompletionEnabled?: boolean;


    /**
     * When true, the plan-approval dialog offers a "clear context" option. Defaults to false.
     */
    showClearContextOnPlanAccept?: boolean;
    /**
     * Idle time before Claude's questions in the terminal auto-continue with any answers selected so far. When unset, the terminal does not auto-continue. The Claude desktop and web apps show Claude's questions in their own interface and may move on from some unanswered ones after a wait the app sets. Claude is then told that nobody answered and uses its best judgment. In sessions that read this setting, only "never" stops the apps from moving on. Leaving it unset does not. Cloud sessions and Cowork tasks do not read your user settings file (~/.claude/settings.json), and managed settings do not reach all of them. This setting is ignored in a project's settings files.
     */
    askUserQuestionTimeout?: '60s' | '5m' | '10m' | 'never';
    /**
     * Max time a permission/user dialog forwarded to a remote client stays parked awaiting an answer, and how long a HELD cross-session message awaits approval, before either resolves to its safe no-action default (cancelled / dropped-with-denial). Defaults to 5m to match the long-standing remote-dialog deadline; "never" disables the deadline. Local-only permission prompts (no remote client) are unaffected. The CLAUDE_CODE_USER_DIALOG_TIMEOUT_MS env var, when set, overrides this. Read from trusted sources only (never a checked-in repo settings file).
     */
    dialogExpiry?: '60s' | '5m' | '10m' | 'never';
    /**
     * Name of an agent (built-in or custom) to use for the main thread. Applies the agent's system prompt, tool restrictions, and model.
     */
    agent?: string;

    /**
     * Company announcements to display at startup (one will be randomly selected if multiple are provided)
     */
    companyAnnouncements?: string[];
    /**
     * Per-plugin configuration including MCP server user configs, keyed by plugin ID (plugin\@marketplace format)
     */
    pluginConfigs?: {
        [k: string]: {
            /**
             * User configuration values for MCP servers keyed by server name
             */
            mcpServers?: {
                [k: string]: {
                    [k: string]: string | number | boolean | string[];
                };
            };
            /**
             * Non-sensitive option values from plugin manifest userConfig, keyed by option name. Sensitive values go to secure storage instead.
             */
            options?: {
                [k: string]: string | number | boolean | string[];
            };
        } | {
            [k: string]: unknown;
        };
    };
    /**
     * Cloud session configuration
     */
    remote?: {
        /**
         * Default environment ID to use for cloud sessions
         */
        defaultEnvironmentId?: string;
    };
    /**
     * Release channel for auto-updates (latest or stable)
     */
    autoUpdatesChannel?: 'latest' | 'stable' | 'rc';
    /**
     * Minimum version to stay on - prevents downgrades when switching to stable channel
     */
    minimumVersion?: string;
    /**
     * Minimum Claude Code version required to start. If the running version is older, Claude Code exits at startup with instructions to update. Only enforced from managed (policy) settings.
     */
    requiredMinimumVersion?: string;
    /**
     * Maximum Claude Code version allowed to start. If the running version is newer, Claude Code exits at startup with instructions to install an approved version. Only enforced from managed (policy) settings.
     */
    requiredMaximumVersion?: string;
    /**
     * Custom directory for plan files, relative to project root. If not set, defaults to ~/.claude/plans/
     */
    plansDirectory?: string;
    /**
     * Terminal UI renderer. "fullscreen" uses the flicker-free alt-screen renderer with virtualized scrollback (equivalent to CLAUDE_CODE_NO_FLICKER=1). "default" uses the classic main-screen renderer.
     */
    tui?: 'default' | 'fullscreen';
    /**
     * Voice mode settings (hold-to-talk / tap-to-toggle dictation)
     */
    voice?: {
        enabled?: boolean;
        /**
         * 'hold' (default): hold to talk. 'tap': tap to start, tap to stop+submit.
         */
        mode?: 'hold' | 'tap';
        /**
         * Submit the prompt when hold-to-talk is released (hold mode only)
         */
        autoSubmit?: boolean;
    };
    /**
     * Managed-org opt-in for channel notifications (MCP servers with the claude/channel capability pushing inbound messages). claude.ai Teams/Enterprise: default off. Console: default on unless managed settings exist. Set true to allow; users then select servers via --channels.
     */
    channelsEnabled?: boolean;
    /**
     * Managed-org allowlist of channel plugins. When set, replaces the default Anthropic allowlist — admins decide which plugins may push inbound messages. Undefined falls back to the default. Requires channelsEnabled: true.
     */
    allowedChannelPlugins?: {
        marketplace: string;
        plugin: string;
    }[];
    /**
     * Reduce or disable animations for accessibility (spinner shimmer, flash effects, etc.)
     */
    prefersReducedMotion?: boolean;
    /**
     * Clock format for times shown in the UI: "auto" (default, follows the locale), "12-hour", "24-hour", "24-hour-utc" ("18:05Z"), or a strftime pattern such as "%H:%M" (any value containing "%"; other values read as "auto"). A pattern replaces the time everywhere; message timestamps show only the pattern, so include %Y-%m-%d for the date. /config offers the presets; a pattern is set here.
     */
    timeFormat?: ('auto' | '12-hour' | '24-hour' | '24-hour-utc') | string;
    /**
     * IANA time zone for times shown in the UI, e.g. "UTC" or "Europe/Dublin". Default: the system time zone. An unknown name falls back to the system time zone.
     */
    timeZone?: string;




    /**
     * Enable auto-memory for this project. When false, Claude will not read from or write to the auto-memory directory.
     */
    autoMemoryEnabled?: boolean;
    /**
     * Custom directory path for auto-memory storage. Supports ~/ prefix for home directory expansion. Ignored if set in projectSettings (checked-in .claude/settings.json) for security. When unset, defaults to ~/.claude/projects/<sanitized-cwd>/memory/.
     */
    autoMemoryDirectory?: string;
    /**
     * Enable background memory consolidation (auto-dream). When set, overrides the server-side default.
     */
    autoDreamEnabled?: boolean;
    /**
     * Request API-side thinking summaries and show them in the conversation and in the transcript view (ctrl+o). Set explicitly to override the default for your install.
     */
    showThinkingSummaries?: boolean;
    /**
     * Whether the user has accepted the bypass permissions mode dialog
     */
    skipDangerousModePermissionPrompt?: boolean;

    /**
     * Disable auto mode
     */
    disableAutoMode?: 'disable';

    /**
     * SSH connection configurations for remote environments. Typically set in managed settings by enterprise administrators to pre-configure SSH connections for team members.
     */
    sshConfigs?: {
        /**
         * Unique identifier for this SSH config. Used to match configs across settings sources.
         */
        id: string;
        /**
         * Display name for the SSH connection
         */
        name: string;
        /**
         * SSH host in format "user\@hostname" or "hostname", or a host alias from ~/.ssh/config
         */
        sshHost: string;
        /**
         * SSH port (default: 22)
         */
        sshPort?: number;
        /**
         * Path to SSH identity file (private key)
         */
        sshIdentityFile?: string;
        /**
         * Default working directory on the remote host. Supports tilde expansion (e.g. ~/projects). If not specified, defaults to the remote user home directory. Can be overridden by the [dir] positional argument in `claude ssh <config> [dir]`.
         */
        startDirectory?: string;
    }[];
    /**
     * SSH connections in Claude Desktop whose host comes from a command. A list of entries, each with `id`, `name` and `command`, and optionally `sshIdentityFile` and `startDirectory`. Desktop runs `command` on this computer when you create the connection or another host for it, not each time you connect. `command` is a program name or absolute path (single-quote a path with spaces), then plain arguments. Nothing else can be quoted. For pipes, variables or a leading `~`, use a script. On Windows, the program must be a full path from a drive letter, such as `C:/tools/acme.exe`, ending in `.exe`, `.cmd` or `.bat`. Quoted paths and Windows need Claude Desktop v4.16336.0 or later. The command must print only the host on standard output: `host` or `user\@host` on one line, or a JSON object with `sshHost` and, optionally, `sshPort` and `startDirectory`. Desktop reads this key only from user settings and from this computer's managed settings. Claude Code itself does not use it.
     */
    sshHostCommands?: unknown[];
    /**
     * CLAUDE.md-style instructions injected as organization-managed memory. Only honored from managed/policy settings.
     */
    claudeMd?: string;
    /**
     * Glob patterns or absolute paths of CLAUDE.md files to exclude from loading. Patterns are matched against absolute file paths using picomatch. Only applies to User, Project, and Local memory types (Managed/policy files cannot be excluded). Examples: "/home/user/monorepo/CLAUDE.md", "** /code/CLAUDE.md", "** /some-dir/.claude/rules/**"
     */
    claudeMdExcludes?: string[];
    /**
     * Custom message to append to the plugin trust warning shown before installation. Only read from policy settings (managed-settings.json / MDM). Useful for enterprise administrators to add organization-specific context (e.g., "All plugins from our internal marketplace are vetted and approved.").
     */
    pluginTrustMessage?: string;
    /**
     * Color theme for the UI
     */
    theme?: ('auto' | 'dark' | 'light' | 'light-daltonized' | 'dark-daltonized' | 'light-ansi' | 'dark-ansi') | string;
    /**
     * Key binding mode for the prompt input
     */
    editorMode?: 'normal' | 'vim';
    /**
     * Deprecated: no longer has any effect. The prompt's word-editing keys always follow Bash (readline) conventions.
     */
    keybindingFlavor?: 'classic' | 'readline';
    /**
     * Vim INSERT-mode key-sequence remaps, e.g. {"jj": "<Esc>"}. Each key is exactly two printable characters typed in sequence; "<Esc>" (return to NORMAL mode) is the only supported target. Applies when editorMode is "vim".
     */
    vimInsertModeRemaps?: {
        [k: string]: unknown;
    };
    /**
     * Show full tool output instead of truncated summaries
     */
    verbose?: boolean;
    /**
     * Preferred OS notification channel
     */
    preferredNotifChannel?: 'auto' | 'iterm2' | 'terminal_bell' | 'iterm2_with_bell' | 'kitty' | 'ghostty' | 'notifications_disabled';
    /**
     * Automatically compact conversation when context fills
     */
    autoCompactEnabled?: boolean;
    /**
     * Precompute the compaction summary in the background before it is needed. Only applies when auto-compact is on.
     */
    precomputeCompactionEnabled?: boolean;



    /**
     * Set to false to stop Claude Code from compacting a long conversation while the session is idle. Defaults to true.
     */
    idleCompaction?: boolean;
    /**
     * When safeguards flag a message, automatically switch to a different model to keep chatting. When off, your session will pause instead.
     */
    switchModelsOnFlag?: boolean;
    /**
     * When a claude.ai usage limit stops your session, wait for the limit to reset and continue the task automatically. When off, the limit dialog offers the wait as a choice instead.
     */
    autoContinueAtUsageLimit?: boolean;
    /**
     * Auto-scroll the conversation view to bottom (fullscreen mode only)
     */
    autoScrollEnabled?: boolean;
    /**
     * Ramp mouse-wheel scroll speed during fast scrolls (fullscreen mode only)
     */
    wheelScrollAccelerationEnabled?: boolean;
    /**
     * Snapshot files before edits so /rewind can restore them
     */
    fileCheckpointingEnabled?: boolean;
    /**
     * Show "Cooked for Nm Ns" after each assistant turn
     */
    showTurnDuration?: boolean;
    /**
     * Stamp each message with its arrival time
     */
    showMessageTimestamps?: boolean;
    /**
     * Emit OSC 9;4 progress sequences during long operations
     */
    terminalProgressBarEnabled?: boolean;
    /**
     * Enable the todo / task tracking panel
     */
    todoFeatureEnabled?: boolean;
    /**
     * How spawned teammates execute (tmux, iterm2, in-process, auto)
     */
    teammateMode?: 'auto' | 'tmux' | 'iterm2' | 'in-process';
    /**
     * Start Remote Control bridge automatically each session
     */
    remoteControlAtStartup?: boolean;

    /**
     * Require explicit approval before SendMessage can reach a peer session on another machine via Remote Control
     */
    isolatePeerMachines?: boolean;
    /**
     * When no background service is running: 'transient' spawns one for this login session; 'ask' offers to install it persistently
     */
    daemonColdStart?: 'transient' | 'ask';
    /**
     * Inbound cross-session peer messages (SendMessage from your other sessions): 'accept' delivers them, 'hold' parks them for your review without letting Claude act, 'refuse' opts this session out. An explicit value always wins. Unset (mode parity): a message auto-delivers only when the sending session's permission-mode class matches yours (bypass↔bypass or prompting↔prompting); a mismatched sender's message is held for your approval; a sender that asserts no class is held only while this session bypasses permission prompts.
     */
    crossSessionInbound?: 'accept' | 'hold' | 'refuse';

    /**
     * Mirror local sessions to claude.ai as view-only (no remote control)
     */
    autoUploadSessions?: boolean;
    /**
     * Push to mobile when a permission prompt or question is waiting
     */
    inputNeededNotifEnabled?: boolean;
    /**
     * Allow Claude to push proactive mobile notifications
     */
    agentPushNotifEnabled?: boolean;
    /**
     * Whether the user has accepted the auto mode opt-in dialog
     */
    skipAutoPermissionPrompt?: boolean;
    /**
     * Whether plan mode uses auto mode semantics when auto mode is available (default: true)
     */
    useAutoModeDuringPlan?: boolean;
    /**
     * Auto mode classifier prompt customization
     */
    autoMode?: {
        /**
         * Rules for the auto mode classifier allow section. Include the literal string "$defaults" to inherit the built-in rules at that position.
         */
        allow?: string[];
        /**
         * Rules for the auto mode classifier SOFT BLOCK section — destructive/irreversible actions that user intent can clear. Include the literal string "$defaults" to inherit the built-in rules at that position.
         */
        soft_deny?: string[];
        /**
         * Rules for the auto mode classifier HARD BLOCK section — security boundaries that user intent does NOT clear. Include the literal string "$defaults" to inherit the built-in rules at that position.
         */
        hard_deny?: string[];
        /**
         * Entries for the auto mode classifier environment section. Include the literal string "$defaults" to inherit the built-in entries at that position.
         */
        environment?: string[];
        /**
         * When true, every Bash/PowerShell allow rule is suspended while auto mode is active so all shell commands are routed through the classifier (higher safety, more classifier calls). Default: false.
         */
        classifyAllShell?: boolean;
    };
    /**
     * Prevent claude-cli:// protocol handler registration with the OS
     */
    disableDeepLinkRegistration?: 'disable';
    /**
     * Enable voice mode (hold-to-talk dictation)
     */
    voiceEnabled?: boolean;
    /**
     * Default transcript view: chat (SendUserMessage checkpoints only) or transcript (full)
     */
    defaultView?: 'chat' | 'transcript';
    [k: string]: unknown;
}

/**
 * Source for loading filesystem-based settings. 'user' - Global user settings (~/.claude/settings.json). 'project' - Project settings (.claude/settings.json). 'local' - Local settings (.claude/settings.local.json).
 */
export declare type SettingSource = 'user' | 'project' | 'local';

export declare type SetupHookInput = BaseHookInput & {
    hook_event_name: 'Setup';
    trigger: 'init' | 'maintenance';
};

export declare type SetupHookSpecificOutput = {
    hookEventName: 'Setup';
    additionalContext?: string;
};

/**
 * Information about an available skill (invoked via /command syntax).
 */
export declare type SlashCommand = {
    /**
     * Skill name (without the leading slash)
     */
    name: string;
    /**
     * Description of what the skill does
     */
    description: string;
    /**
     * Hint for skill arguments (e.g., "<file>")
     */
    argumentHint: string;
    /**
     * Alternate names that resolve to this command (e.g., /cost and /stats both resolve to /usage)
     */
    aliases?: string[];
    /**
     * True when the command is Claude Code's own; absent for a command defined by a user, project, plugin or MCP server. Rows can share a name: when a marked row carries it, /name runs that one, and an unmarked row is the one /name runs only when no marked row shares its name. The marker describes the row's name, not its aliases: a typed alias runs a command that has it as its name, when one exists, whatever this marker says.
     */
    builtin?: boolean;

};

/**
 * A parked, fully started Claude Code process that is not yet any session
 * (see {@link prewarm}). `claim()` binds it to a session and sends the first
 * message; `close()` discards it. Single use.
 * @alpha
 */
export declare interface SpareProcess extends AsyncDisposable {
    /**
     * Bind the spare to a session and send its first message. Synchronous, like
     * `query()`: it writes the claim, the per-session settings and the prompt
     * to the waiting process and returns the Query; consume the Query's messages
     * as usual (a claim with a `settings` overlay sends the prompt one round
     * trip later, once the overlay is accepted — see {@link ClaimOptions}). Can
     * only be called once.
     *
     * If the process cannot honour the claim (see {@link ClaimOptions}),
     * {@link SpareProcess.claimed} rejects with the reason, a prompt already
     * sent is answered with an error result whose text starts with
     * `not_claimed` (the Query then ends as any query with an error result
     * does), and the process is let go: it exits once it has answered. Start
     * the session with `query()` instead. `close()` is not needed for the
     * process to go away, but it releases what the spare holds in this process
     * — in-process (`type: 'sdk'`) MCP server instances, hook and tool
     * callbacks — at once rather than at exit, so call it first if the
     * fallback `query()` reuses those same objects.
     *
     * The returned Query's `initializationResult()`, `supportedCommands()`,
     * `supportedAgents()`, `supportedModels()` and `accountInfo()` wait for the
     * claim's answer and then describe the claimed session — the folder's
     * agents, commands and output styles, the claimed permission mode — as they
     * would after a cold `query()` in that folder (the folder's `availableModels`
     * narrows the model list as it does there). One limit: that snapshot is
     * taken as part of the claim, before `model` and the `settings` keys that
     * follow it are applied, so fields they decide (for example
     * `fast_mode_state`, `output_style`, the remote-control defaults, an
     * `availableModels` in the overlay) may not reflect them yet. After a refused claim the reads
     * keep describing the parked process; after `option_not_applied`, or a
     * `settings_not_applied` that carries `.claim`, they describe the claimed
     * session.
     *
     * @throws when called a second time, when the spare was closed or has
     * exited, or when `options.settings` carries a key that governs hooks (see
     * {@link ClaimOptions}) — in that last case nothing has been sent and the
     * spare stays parked, so it can still be claimed.
     */
    claim(params: {
        prompt: string | AsyncIterable<SDKUserMessage>;
        options: ClaimOptions;
    }): Query;
    /**
     * Settles once the process has answered the claim AND the per-session
     * settings sent with it: resolves with the canonical working directory, the
     * session id and how long the spare was parked. Rejects — and the host
     * should start the session with `query()` instead — when the claim is
     * refused (`not_a_spare`, `env_key_not_claimable`, `cwd_not_found`,
     * `project_settings_not_claimable`, `permission_mode_not_claimable`, …; a
     * prompt already sent gets the `not_claimed` error result and the process
     * exits), when the claim broke after it began (`claim_failed`; likewise),
     * when the spare exited or was closed before a claim (`spare_exited` /
     * `spare_closed`), or when the `settings` overlay was refused
     * (`settings_not_applied: …`; the prompt was never sent and the process
     * goes away). In all of those your prompt has not run. The one rejection
     * after which it does run is `option_not_applied: …`: `model` or
     * `maxThinkingTokens` was not accepted and the session runs without it.
     * `option_not_applied` carries `.claim` with the claim info, and so does a
     * `settings_not_applied` for a key sent behind the claim; one that stopped
     * the claim does not.
     * `permissionMode` is part of the claim itself and fails closed: see
     * {@link ClaimOptions}.
     */
    readonly claimed: Promise<{
        cwd: string;
        sessionId: string;
        parkedMs?: number;
        sdkMcpSettled: boolean;
    }>;
    /** Settles when the spare's process exits, claimed or not — a parked spare that dies should be replaced. */
    readonly exited: Promise<void>;

    /**
     * Terminate the process. Before a claim this discards the spare (and
     * rejects `claimed`); after one it is the same as closing the Query.
     */
    close(): void;
}

/**
 * Represents a spawned process with stdin/stdout streams and lifecycle management.
 * Implementers provide this interface to abstract the process spawning mechanism.
 * ChildProcess already satisfies this interface.
 */
export declare interface SpawnedProcess {
    /** Writable stream for sending data to the process stdin */
    stdin: Writable;
    /** Readable stream for receiving data from the process stdout */
    stdout: Readable;
    /** Whether the process has been killed */
    readonly killed: boolean;
    /** Exit code if the process has exited, null otherwise */
    readonly exitCode: number | null;
    /**
     * Signal that terminated the process, if any. Optional: ChildProcess
     * provides it; custom spawners may omit it (signal exits then read as
     * still-running until their 'exit' event delivers the signal).
     */
    readonly signalCode?: NodeJS.Signals | null;
    /**
     * Kill the process with the given signal
     * @param signal - The signal to send (e.g., 'SIGTERM', 'SIGKILL')
     */
    kill(signal: NodeJS.Signals): boolean;
    /**
     * Register a callback for when the process exits
     * @param event - Must be 'exit'
     * @param listener - Callback receiving exit code and signal
     *
     * ProcessTransport's built-in local spawn delivers this only after the
     * child's stderr has also closed (bounded by a short grace), so exit
     * consumers see a complete stderr tail in exit errors. Custom
     * `spawnClaudeCodeProcess` implementations emit plain process exit.
     */
    on(event: 'exit', listener: (code: number | null, signal: NodeJS.Signals | null) => void): void;
    /**
     * Register a callback for process errors
     * @param event - Must be 'error'
     * @param listener - Callback receiving the error
     */
    on(event: 'error', listener: (error: Error) => void): void;
    /**
     * Register a one-time callback for when the process exits
     */
    once(event: 'exit', listener: (code: number | null, signal: NodeJS.Signals | null) => void): void;
    once(event: 'error', listener: (error: Error) => void): void;
    /**
     * Remove an event listener
     */
    off(event: 'exit', listener: (code: number | null, signal: NodeJS.Signals | null) => void): void;
    off(event: 'error', listener: (error: Error) => void): void;
}

/**
 * Options passed to the spawn function.
 */
export declare interface SpawnOptions {
    /** Command to execute */
    command: string;
    /** Arguments to pass to the command */
    args: string[];
    /** Working directory */
    cwd?: string;
    /** Environment variables */
    env: {
        [envVar: string]: string | undefined;
    };
    /**
     * Abort signal for cancellation.
     *
     * This is a **forwarded** signal owned by `ProcessTransport`, not the
     * caller's `Options.abortController.signal` directly. It aborts only
     * after the SDK's graceful-close path has run: stdin EOF →
     * `GRACEFUL_EXIT_TIMEOUT_MS` (~2 s) grace window. Anything you hang on
     * it (Node `spawn({signal})` → `child.kill()`, VM/container teardown,
     * fetch cancellation) fires **after** the child has had a chance to
     * shut down cleanly via stdin close.
     *
     * Why: passing the caller's raw signal to Node `spawn()` registers
     * Node's own abort listener that calls `child.kill()` — on Windows
     * that's `TerminateProcess` (instant, uncatchable), and AbortSignal
     * listeners fire synchronously in registration order, so it would race
     * ahead of the SDK's stdin-EOF + grace path and the CLI's
     * `gracefulShutdown` would never run.
     *
     * If you need the caller's *immediate* signal (no grace), it's the
     * `AbortController` you passed to `Options.abortController` — capture
     * it in closure.
     */
    signal: AbortSignal;
}

/**
 * Pre-warms the CLI subprocess so the first `query()` resolves immediately.
 * Returns a {@link WarmQuery} handle.
 */
export declare function startup(_params?: {
    options?: Options;
    /**
     * The most time, in milliseconds, that startup() counts while it waits for
     * the subprocess to initialize; when that time is used up, the promise
     * rejects with a timeout error. Defaults to 60000. When no value is passed,
     * time in which the subprocess reports a SessionStart or Setup hook running
     * is not counted, for at most 10 minutes in total. A value that is passed
     * counts throughout.
     */
    initializeTimeoutMs?: number;
}): Promise<WarmQuery>;

/**
 * Everything the CLI writes to its output stream (stdout in stream-json mode): exactly one StdoutMessage per line, as a single JSON object. Besides the SDKMessage members this includes the control protocol - control requests the CLI originates, control responses to the client's requests, cancellations and keep-alives.
 */
declare type StdoutMessage = coreTypes.SDKMessage | coreTypes.SDKActiveGoalMessage | SDKControlResponse | SDKControlRequest | SDKControlCancelRequest | SDKKeepAliveMessage;

export declare type StopFailureHookInput = BaseHookInput & {
    hook_event_name: 'StopFailure';
    error: SDKAssistantMessageError;
    error_details?: string;
    last_assistant_message?: string;
};

export declare type StopHookInput = BaseHookInput & {
    hook_event_name: 'Stop';
    stop_hook_active: boolean;
    /**
     * Text content of the last assistant message before stopping. Avoids the need to read and parse the transcript file.
     */
    last_assistant_message?: string;
    /**
     * In-flight background work (running/pending + backgrounded) registered in this session. Lets hooks distinguish "session is done" from "session is paused waiting for background work to wake it". Empty array when nothing is in flight.
     */
    background_tasks?: BackgroundTaskSummary[];
    /**
     * Session-scoped cron tasks (CronCreate, ScheduleWakeup, /loop) that will wake this session later. Empty array when none are scheduled.
     */
    session_crons?: SessionCronSummary[];


};

/**
 * Hook-specific output for the Stop event. additionalContext is non-error feedback delivered to the model; the conversation continues so the model can act on it.
 */
export declare type StopHookSpecificOutput = {
    hookEventName: 'Stop';
    additionalContext?: string;
};

export declare type SubagentStartHookInput = BaseHookInput & {
    hook_event_name: 'SubagentStart';
    agent_id: string;
    agent_type: string;
};

export declare type SubagentStartHookSpecificOutput = {
    hookEventName: 'SubagentStart';
    additionalContext?: string;
};

export declare type SubagentStopHookInput = BaseHookInput & {
    hook_event_name: 'SubagentStop';
    stop_hook_active: boolean;
    agent_id: string;
    agent_transcript_path: string;
    agent_type: string;
    /**
     * Text content of the last assistant message before stopping. Avoids the need to read and parse the transcript file.
     */
    last_assistant_message?: string;
    /**
     * In-flight background work (running/pending + backgrounded) registered in this session. Lets hooks distinguish "session is done" from "session is paused waiting for background work to wake it". Empty array when nothing is in flight.
     */
    background_tasks?: BackgroundTaskSummary[];
    /**
     * Session-scoped cron tasks (CronCreate, ScheduleWakeup, /loop) that will wake this session later. Empty array when none are scheduled.
     */
    session_crons?: SessionCronSummary[];


};

/**
 * Hook-specific output for the SubagentStop event. additionalContext is non-error feedback delivered to the subagent; the subagent continues so it can act on it.
 */
export declare type SubagentStopHookSpecificOutput = {
    hookEventName: 'SubagentStop';
    additionalContext?: string;
};

export declare type SyncHookJSONOutput = {
    continue?: boolean;
    suppressOutput?: boolean;
    stopReason?: string;
    decision?: 'approve' | 'block';
    systemMessage?: string;
    /**
     * A terminal escape sequence (e.g. OSC 9 / OSC 777 desktop-notification) for Claude Code to emit on your behalf. Only notification/title OSCs (0, 1, 2, 9, 99, 777) and BEL are permitted; anything else is dropped.
     */
    terminalSequence?: string;
    reason?: string;


    hookSpecificOutput?: PreToolUseHookSpecificOutput | UserPromptSubmitHookSpecificOutput | UserPromptExpansionHookSpecificOutput | SessionStartHookSpecificOutput | SetupHookSpecificOutput | PreModelSwitchHookSpecificOutput | PostModelSwitchHookSpecificOutput | SubagentStartHookSpecificOutput | PostToolUseHookSpecificOutput | PostToolUseFailureHookSpecificOutput | PostToolBatchHookSpecificOutput | StopHookSpecificOutput | SubagentStopHookSpecificOutput | PermissionDeniedHookSpecificOutput | NotificationHookSpecificOutput | PermissionRequestHookSpecificOutput | ElicitationHookSpecificOutput | ElicitationResultHookSpecificOutput | CwdChangedHookSpecificOutput | FileChangedHookSpecificOutput | WorktreeCreateHookSpecificOutput | MessageDisplayHookSpecificOutput;
};

/**
 * Marker string that splits a custom `systemPrompt` into a static prefix
 * (eligible for cross-session prompt caching) and a dynamic suffix
 * (session-specific, not globally cached). Include it as a standalone
 * element of a `string[]` `systemPrompt`, or as a line of its own in a
 * `--system-prompt` string, to opt in; content before it gets global
 * cache scope, content after does not. See `splitSysPromptPrefix` in
 * `src/services/api/requestAttribution.ts`.
 */
export declare const SYSTEM_PROMPT_DYNAMIC_BOUNDARY = "__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__";

/**
 * Tag a session. Pass null to clear the tag.
 * @param sessionId - UUID of the session
 * @param tag - Tag string, or null to clear
 * @param options - `{ dir?: string }` project path; omit to search all projects
 */
export declare function tagSession(_sessionId: string, _tag: string | null, _options?: SessionMutationOptions): Promise<void>;

export declare type TaskCompletedHookInput = BaseHookInput & {
    hook_event_name: 'TaskCompleted';
    task_id: string;
    task_subject: string;
    task_description?: string;
    teammate_name?: string;
    /**
     * @deprecated Sessions have a single implicit team; this carries the session-derived team name and will be removed in a future release.
     */
    team_name?: string;
};

export declare type TaskCreatedHookInput = BaseHookInput & {
    hook_event_name: 'TaskCreated';
    task_id: string;
    task_subject: string;
    task_description?: string;
    teammate_name?: string;
    /**
     * @deprecated Sessions have a single implicit team; this carries the session-derived team name and will be removed in a future release.
     */
    team_name?: string;
};

export declare type TeammateIdleHookInput = BaseHookInput & {
    hook_event_name: 'TeammateIdle';
    teammate_name: string;
    /**
     * @deprecated Sessions have a single implicit team; this carries the session-derived team name and will be removed in a future release.
     */
    team_name: string;
};

/**
 * Why the query loop terminated. Unset when the loop was bypassed (local slash command).
 */
export declare type TerminalReason = 'blocking_limit' | 'rapid_refill_breaker' | 'prompt_too_long' | 'image_error' | 'model_error' | 'api_error' | 'malformed_tool_use_exhausted' | 'aborted_streaming' | 'aborted_tools' | 'stop_hook_prevented' | 'hook_stopped' | 'tool_deferred' | 'max_turns' | 'background_requested' | 'completed' | 'budget_exhausted' | 'structured_output_retry_exhausted' | 'tool_deferred_unavailable' | 'turn_setup_failed';

/**
 * Claude decides when and how much to think (Opus 4.6+).
 */
export declare type ThinkingAdaptive = {
    type: 'adaptive';
    display?: 'summarized' | 'omitted';
};

/**
 * Controls Claude's thinking/reasoning behavior. When set, takes precedence over the deprecated maxThinkingTokens.
 */
export declare type ThinkingConfig = ThinkingAdaptive | ThinkingEnabled | ThinkingDisabled;

/**
 * No extended thinking
 */
export declare type ThinkingDisabled = {
    type: 'disabled';
};

/**
 * Fixed thinking token budget (older models)
 */
export declare type ThinkingEnabled = {
    type: 'enabled';
    budgetTokens?: number;
    display?: 'summarized' | 'omitted';
};

export declare function tool<Schema extends AnyZodRawShape>(_name: string, _description: string, _inputSchema: Schema, _handler: (args: InferShape<Schema>, extra: unknown) => Promise<CallToolResult>, _extras?: {
    annotations?: ToolAnnotations;
    searchHint?: string;
    alwaysLoad?: boolean;
}): SdkMcpToolDefinition<Schema>;

/**
 * Per-tool configuration for built-in tools. Allows SDK consumers to
 * customize tool behavior that the CLI hardcodes.
 */
export declare type ToolConfig = {
    askUserQuestion?: {
        /**
         * Content format for the `preview` field on question options.
         * Controls what the model is instructed to emit and how the field is
         * described in the tool schema.
         *
         * - `'markdown'` — Markdown/ASCII content (CLI default, rendered in a monospace box)
         * - `'html'` — Self-contained HTML fragments (for web-based SDK consumers)
         *
         * @default 'markdown'
         */
        previewFormat?: 'markdown' | 'html';


    };
};

/**
 * Transport interface for Claude Code SDK communication
 * Abstracts the communication layer to support both process and WebSocket transports
 */
export declare interface Transport {
    /**
     * Write data to the transport
     * May be async for network-based transports
     */
    write(data: string): void | Promise<void>;
    /**
     * Close the transport connection and clean up resources
     * This also closes stdin if still open (eliminating need for endInput)
     */
    close(): void;
    /**
     * Check if transport is ready for communication
     */
    isReady(): boolean;
    /**
     * Read and parse messages from the transport
     * Each transport handles its own protocol and error checking
     */
    readMessages(): AsyncGenerator<StdoutMessage, void, unknown>;
    /**
     * Register a request_id whose control_response the caller will await
     * out-of-band via Query.awaitControlResponse. Transports that see
     * per-frame source (multi-client fan-out) SHOULD drop non-worker
     * control_responses matching this id — only the worker may answer.
     */
    expectControlResponse?(requestId: string): void;
    /**
     * Called by Query immediately before it yields `message` to the SDK
     * consumer. Transports that keep a consumer-facing delivery cursor
     * (BrowserSSETransport's getLastSequenceNum()) advance it here, so the
     * cursor covers exactly the messages the consumer was handed — not ones
     * still buffered between the transport and the consumer.
     */
    markDelivered?(message: object): void;
    /**
     * End the input stream
     */
    endInput(): void;
    /**
     * Await the underlying subprocess's exit. Only meaningful for
     * subprocess-backed transports (ProcessTransport); WebSocket / SSE /
     * Bun Worker transports leave this undefined. Query.performCleanup()
     * awaits it (bounded) so .return() / asyncDispose don't resolve while
     * the child is still draining the stdin EOF that close() just sent.
     */
    waitForExit?(): Promise<void>;
    /**
     * Optional Disposable support. All built-in transports implement this
     * (delegating to close()), so `using transport = new ProcessTransport(...)`
     * works. Kept optional on the interface to avoid a breaking change for
     * external `implements Transport` consumers.
     */
    [Symbol.dispose]?(): void;
}

/**
 * Unarchive a session, so that `listSessions` returns it with
 * `archived: false`.
 *
 * Throws if the session is not found, or if `sessionStore` is passed (see
 * {@link archiveSession}).
 *
 * @param sessionId - UUID of the session
 * @param options - `{ dir?: string }` project path; omit to search all projects
 */
export declare function unarchiveSession(_sessionId: string, _options?: SessionMutationOptions): Promise<void>;

/**
 * Messages meaning "a usage limit was genuinely reached" — the error-path
 * outputs of getLimitReachedText (rateLimitMessages.ts) and
 * getUsageCreditsOnlyModelRejectionContent (api/errors.ts).
 *
 * @alpha
 */
export declare const USAGE_LIMIT_ERROR_PREFIXES: readonly ["You've hit your", "You've reached your", "You're out of usage credits", 'Your org is out of usage · add funds to continue', 'Your org is out of usage · contact your admin', "Your seat type doesn't include usage credits", "Your seat type doesn't include usage", 'Your usage allocation has been disabled by your admin', "Your group's usage limit is set to $0", 'Fable 5 requires usage credits', "You're out of extra usage", "Your seat type doesn't include extra usage"];

/**
 * Overage-transition notifications ("now drawing from credits"). Toast only;
 * these never arrive as API errors.
 *
 * @alpha
 */
export declare const USAGE_TRANSITION_PREFIXES: readonly ["You're now using usage credits", "You're now using your usage allocation", 'Now using your usage allocation', 'Now using usage credits', 'Now using credits', "You're now using extra usage", 'Now using extra usage'];

/**
 * Approaching-limit warnings (severity:'warning'). Footer/toast only; these
 * never arrive as API errors. ("Approaching …" and "Over N% of your … used"
 * warnings are deliberately unregistered — they render in the footer without
 * <RateLimitMessage> styling; see the generator-coverage tests.)
 *
 * @alpha
 */
export declare const USAGE_WARNING_PREFIXES: readonly ["You've used", "You're close to"];

/**
 * A `request_user_dialog` control request from the CLI, asking the SDK
 * consumer to render a blocking dialog and return the user's choice.
 * Each `dialogKind` defines its own payload and result shape; the protocol
 * transports both opaquely.
 */
export declare type UserDialogRequest = {
    /**
     * Identifier for the dialog the host should render. Open string union —
     * new kinds may be added without a protocol bump, so hosts must answer
     * unrecognized kinds with `{behavior: 'cancelled'}`.
     */
    dialogKind: string;
    /** Dialog-specific data for the host renderer; shape is defined per dialogKind. */
    payload: Record<string, unknown>;
    /**
     * Present when the dialog is tied to a specific tool invocation. Same
     * value as the `toolUseID` passed to `canUseTool`.
     */
    toolUseID?: string;
};

/**
 * The host's answer to a {@link UserDialogRequest}. On `cancelled`, the CLI
 * applies the dialog's default behavior.
 */
export declare type UserDialogResult = {
    behavior: 'completed';
    result: unknown;
} | {
    behavior: 'cancelled';
};

export declare type UserPromptExpansionHookInput = BaseHookInput & {
    hook_event_name: 'UserPromptExpansion';
    expansion_type: 'slash_command' | 'mcp_prompt';
    command_name: string;
    command_args: string;
    command_source?: string;
    prompt: string;
};

export declare type UserPromptExpansionHookSpecificOutput = {
    hookEventName: 'UserPromptExpansion';
    additionalContext?: string;
    /**
     * When decision is "block", omit the original prompt from the block message
     */
    suppressOriginalPrompt?: boolean;
};

export declare type UserPromptSubmitHookInput = BaseHookInput & {
    hook_event_name: 'UserPromptSubmit';
    prompt: string;
    /**
     * Who authored/injected the prompt: `user` = submitted from the interactive composer, `sdk` = non-interactive entrypoint (`-p` / Agent SDK), `loop_wakeup` = dynamic /loop wakeup, `schedule_wakeup` = scheduled-task fire (CronCreate or a cloud scheduled task), `system` = other machine-injected turns (peer/channel messages, task notifications, auto-continuation), `poll_event` = the poll-event channel enqueue-time pass (the hook fires when the host submits an event, before its delivery ack exists — a blocking verdict rejects the event). Payloads may omit it while the field rolls out.
     */
    source?: 'user' | 'sdk' | 'system' | 'loop_wakeup' | 'schedule_wakeup' | 'poll_event';
    session_title?: string;
};

export declare type UserPromptSubmitHookSpecificOutput = {
    hookEventName: 'UserPromptSubmit';
    additionalContext?: string;
    sessionTitle?: string;
    /**
     * When decision is "block", omit the original prompt from the block message
     */
    suppressOriginalPrompt?: boolean;
};

/**
 * A pre-warmed query handle returned by `startup()`. The subprocess has
 * already been spawned and completed its initialize handshake, so calling
 * `query()` writes the prompt directly to a ready process — no startup
 * latency.
 */
export declare interface WarmQuery extends AsyncDisposable {
    /**
     * Send a prompt to the pre-warmed subprocess and return the Query.
     * Can only be called once per WarmQuery.
     */
    query(prompt: string | AsyncIterable<SDKUserMessage>): Query;
    /**
     * Close the subprocess without sending a prompt. Use this to discard a
     * warm query you no longer need.
     */
    close(): void;
}

export declare type WorktreeCreateHookInput = BaseHookInput & {
    hook_event_name: 'WorktreeCreate';
    name: string;
};

/**
 * Hook-specific output for the WorktreeCreate event. Provides the absolute path to the created worktree directory. Command hooks print the path on stdout instead.
 */
export declare type WorktreeCreateHookSpecificOutput = {
    hookEventName: 'WorktreeCreate';
    worktreePath: string;
};

export declare type WorktreeRemoveHookInput = BaseHookInput & {
    hook_event_name: 'WorktreeRemove';
    worktree_path: string;
};

export { }
