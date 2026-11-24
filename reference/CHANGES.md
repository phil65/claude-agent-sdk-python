# SDK reference changes: 0.3.330 → 0.3.331

## sdk.d.ts

### Changed (4)

- `type ResolveSettingsOptions`
    - `+` `registryPolicyFingerprint?:()=>{hklm:string|null;hkcu:string|null;}|undefined`
- `type SDKControlMcpCallRequest`
    - `+` `soft_error_result?:boolean`
- `type SDKStartupFailureReason`
    - `+` `'sideload_flags_disabled'`
- `interface Settings`
    - `+` `downloadsMirrorUrl?:string`

## sdk-tools.d.ts

### Changed (1)

- `type ArtifactOutput`
    - `+` `{artifacts:{title:string;url:string;favicon?:string;updatedAt?:string;rel?:"mine"|"shared";external?:true;role?:"editor"|"commenter"|"reader"|"viewer";outsider…`
    - `-` `{artifacts:{title:string;url:string;favicon?:string;updatedAt?:string;rel?:"mine"|"shared";external?:true;role?:"editor"|"commenter"|"reader"|"viewer";outsider…`
