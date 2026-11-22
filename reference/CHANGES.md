# SDK reference changes: 0.3.325 → 0.3.330

## sdk.d.ts

### Added (1)

- `const PublishedSandboxSettingsSchema`
    - `declare const PublishedSandboxSettingsSchema:()=>z.ZodObject<{enabled:z.ZodOptional<z.ZodBoolean>;failIfUnavailable:z.ZodOptional<z.ZodBoolean>;autoAllowBashIfSandboxed:z.ZodOptional<z.ZodBoolean>;allowUnsandboxedCommands:z.ZodOptional<z.ZodBoolean>;network:z.ZodOptional<z.ZodObject<{allowedDomains:z.ZodOptional<z.ZodArray<z.ZodString>>;deniedDomains:z.ZodOptional<z.ZodArray<z.ZodString>>;strictA…`

### Removed (1)

- `const SandboxSettingsSchema`

### Changed (8)

- `const BUILTIN_TOOL_NAMES`
    - old: `export declare const BUILTIN_TOOL_NAMES:readonly['Agent','Artifact','AskUserQuestion','Bash','ClaudeDesign','CronCreate','CronDelete','CronList','Edit','EndConversation','EnterPlanMode','EnterWorktree','ExitPlanMode','ExitWorktree','Glob','Grep','ListAgents','ListMcpResourcesTool','LSP','Monitor','…`
    - new: `export declare const BUILTIN_TOOL_NAMES:readonly['Agent','Artifact','AskUserQuestion','Bash','ClaudeDesign','CronCreate','CronDelete','CronList','Edit','EndConversation','EnterPlanMode','EnterWorktree','ExitPlanMode','ExitWorktree','Glob','Grep','ListAgents','ListMcpResourcesTool','LSP','Monitor','…`
- `type Options`
    - `+` `mcpServersDelivery?:'argv'|'initialize'`
- `type SDKControlInitializeRequest`
    - `+` `mcpServers?:Record<string,coreTypes.McpServerConfigForProcessTransport>`
- `type SDKControlInitializeResponse`
    - `+` `mcp_servers_applied?:boolean`
- `type SDKMessageOrigin`
    - `+` `{kind:'task-notification';subkind?:'scheduled-trigger'|'peer-send-message'|'projects-relay'|'session-inbox'|'external-event';fireReason?:string;runId?:string;}`
    - `-` `{kind:'task-notification';subkind?:'scheduled-trigger'|'peer-send-message'|'projects-relay'|'session-inbox';fireReason?:string;runId?:string;}`
- `type SDKStartupFailureReason`
    - `+` `'initialize_fields_not_delivered'`
- `type SandboxSettings`
    - old: `export declare type SandboxSettings=z.infer<ReturnType<typeof SandboxSettingsSchema>>`
    - new: `export declare type SandboxSettings=z.infer<ReturnType<typeof PublishedSandboxSettingsSchema>>`
- `interface Settings`
    - `+` `allowNestedModelAccessUnderForceLogin?:boolean`
    - `+` `desktopMcpServersListScope?:string`
    - `~` `hooks?:{[k:string]:{matcher?:string;hooks:({type:'command';command:string;args?:string[];if?:string;shell?:'bash'|'powershell';timeout?:number;onFailure?:'cont…` → `hooks?:{[k:string]:{matcher?:string;hooks:({type:'command';command:string;args?:string[];if?:string;shell?:'bash'|'powershell';timeout?:number;onFailure?:'cont…`
    - `~` `permissions?:{allow?:string[];deny?:string[];ask?:string[];defaultMode?:'acceptEdits'|'auto'|'bypassPermissions'|'default'|'dontAsk'|'plan';disableBypassPermis…` → `permissions?:{allow?:string[];deny?:string[];ask?:string[];defaultMode?:'acceptEdits'|'auto'|'bypassPermissions'|'default'|'dontAsk'|'plan';disableBypassPermis…`

## sdk-tools.d.ts

### Changed (5)

- `type ArtifactOutput`
    - `+` `{url:string;path:string;artifact_id?:string;title?:string;version?:string;capabilities?:unknown;stored?:{contract:string;preferredContract?:string;capabilities…`
    - `-` `{url:string;path:string;artifact_id?:string;title?:string;version?:string;capabilities?:unknown;stored?:{contract:string;preferredContract?:string;capabilities…`
- `interface CronCreateOutput`
    - `+` `maxAgeMs?:number`
    - `+` `otherOneShots?:{id:string;humanSchedule:string;prompt:string;}[]`
- `interface MonitorOutput`
    - `+` `keptInSandboxByCheck?:boolean`
- `interface ReportFindingsInput`
    - `~` `findings:{file:string;line?:number;summary:string;short_summary?:string;failure_scenario:string;category?:string;verdict?:"CONFIRMED"|"PLAUSIBLE";outcome?:"fix…` → `findings:{file:string;line?:number;summary:string;short_summary?:string;failure_scenario:string;category?:string;severity?:"important"|"pre_existing"|"nit";ver…`
- `interface ReportFindingsOutput`
    - `~` `findings:{file:string;line?:number;summary:string;short_summary?:string;failure_scenario:string;category?:string;verdict?:"CONFIRMED"|"PLAUSIBLE";outcome?:"fix…` → `findings:{file:string;line?:number;summary:string;short_summary?:string;failure_scenario:string;category?:string;severity?:"important"|"pre_existing"|"nit";ver…`
