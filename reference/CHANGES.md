# SDK reference changes: 0.3.331 → 0.3.332

## sdk.d.ts

### Added (3)

- `type PreSkillShellCommandHookInput`
    - `hook_event_name:'PreSkillShellCommand'`
    - `tool_name:string`
    - `tool_input:{command:string;}`
    - `tool_use_id:string`
    - `command_name:string`
    - `command_source?:string`
    - `invoked_by:'user'|'claude'|'other'`
- `type PreSkillShellCommandHookSpecificOutput`
    - `hookEventName:'PreSkillShellCommand'`
    - `permissionDecision?:HookPermissionDecision`
    - `permissionDecisionReason?:string`
    - `updatedInput?:Record<string,unknown>`
- `type SDKControlSetPermissionModeResponse`
    - `mode?:coreTypes.PermissionMode`

### Changed (6)

- `const HOOK_EVENTS`
    - old: `export declare const HOOK_EVENTS:readonly['PreToolUse','PostToolUse','PostToolUseFailure','PostToolBatch','Notification','UserPromptSubmit','UserPromptExpansion','SessionStart','SessionEnd','Stop','StopFailure','SubagentStart','SubagentStop','PreCompact','PostCompact','PreModelSwitch','PostModelSwi…`
    - new: `export declare const HOOK_EVENTS:readonly['PreToolUse','PostToolUse','PostToolUseFailure','PostToolBatch','Notification','UserPromptSubmit','UserPromptExpansion','SessionStart','SessionEnd','Stop','StopFailure','SubagentStart','SubagentStop','PreCompact','PostCompact','PreModelSwitch','PostModelSwi…`
- `type HookEvent`
    - `+` `'PreSkillShellCommand'`
- `type HookInput`
    - `+` `PreSkillShellCommandHookInput`
- `interface Query`
    - `~` `setPermissionMode(mode:PermissionMode):Promise<void>` → `setPermissionMode(mode:PermissionMode):Promise<SDKControlSetPermissionModeResponse|undefined>`
- `type ResolvedSettings`
    - `~` `machinePolicy?:{didNotLoad:false|Array<'profile'|'registry'|'file'>;}` → `machinePolicy?:{didNotLoad:false|Array<'profile'|'registry'|'file'>;registryPolicyDifferedFromFingerprint?:true;}`
- `type SyncHookJSONOutput`
    - `~` `hookSpecificOutput?:PreToolUseHookSpecificOutput|UserPromptSubmitHookSpecificOutput|UserPromptExpansionHookSpecificOutput|SessionStartHookSpecificOutput|SetupH…` → `hookSpecificOutput?:PreToolUseHookSpecificOutput|UserPromptSubmitHookSpecificOutput|UserPromptExpansionHookSpecificOutput|SessionStartHookSpecificOutput|SetupH…`

## sdk-tools.d.ts

_No declaration changes._
