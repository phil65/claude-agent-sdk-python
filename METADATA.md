https://raw.githubusercontent.com/jimmc414/claude_metrics/b9251aa66fd2155d18c72166f4ab7f25c1f82fe7/docs/CLAUDE_CODE_METRICS_CATALOG.md

# Claude Code Metadata & Metrics Catalog

## Complete Exhaustive Reference

This document catalogs every piece of raw metadata stored by Claude Code locally and the fields that can be extracted from each data source.

**Related Documents:**
- **[CLAUDE_CODE_DATA_SOURCES.md](CLAUDE_CODE_DATA_SOURCES.md)** - Quick reference guide to data locations
- **[DERIVED_METRICS_CATALOG.md](DERIVED_METRICS_CATALOG.md)** - 592 derived/computed metrics with types

---

## Document Structure

| Part | Content | Focus |
|------|---------|-------|
| 1 | Raw Data Sources | Schema definitions for 16 data files |
| 2 | Tool Input Schemas | Parameters for each Claude Code tool |
| 3 | Extractable Metrics | Direct extraction from raw data |
| 4 | Deep Scan Addendum | Newly discovered fields |
| 5-12 | Derived Metrics | **→ See [DERIVED_METRICS_CATALOG.md](DERIVED_METRICS_CATALOG.md)** |

---

# PART 1: RAW DATA SOURCES

## 1. `~/.claude/stats-cache.json`
**Purpose:** Pre-aggregated statistics cache
**Size:** ~8 KB
**Update frequency:** Daily

### Schema:
```
version                                    [int]      - Cache format version
lastComputedDate                          [str]      - ISO date of last computation

dailyActivity[]                           [list]     - Daily activity records
  .date                                   [str]      - ISO date (YYYY-MM-DD)
  .messageCount                           [int]      - Total messages that day
  .sessionCount                           [int]      - Number of sessions
  .toolCallCount                          [int]      - Total tool invocations

dailyModelTokens[]                        [list]     - Daily token usage by model
  .date                                   [str]      - ISO date
  .tokensByModel                          [dict]     - Model name → token count

modelUsage.<model_name>                   [dict]     - Cumulative model statistics
  .inputTokens                            [int]      - Total input tokens
  .outputTokens                           [int]      - Total output tokens
  .cacheReadInputTokens                   [int]      - Tokens read from cache
  .cacheCreationInputTokens               [int]      - Tokens used to create cache
  .webSearchRequests                      [int]      - Web search count
  .costUSD                                [int]      - Cost (always 0 currently)
  .contextWindow                          [int]      - Context window used

hourCounts                                [dict]     - Activity by hour (0-23 → count)

totalSessions                             [int]      - All-time session count
totalMessages                             [int]      - All-time message count
firstSessionDate                          [str]      - ISO timestamp of first use

longestSession                            [dict]     - Longest session record
  .sessionId                              [str]      - Session UUID
  .duration                               [int]      - Duration in milliseconds
  .messageCount                           [int]      - Messages in that session
  .timestamp                              [str]      - ISO timestamp
```

---

## 2. `~/.claude/history.jsonl`
**Purpose:** User input history (readline-style)
**Size:** ~1.6 MB
**Format:** JSON Lines (one entry per line)

### Schema:
```
display                                   [str]      - User input text (what they typed)
pastedContents                            [dict]     - Any pasted content (files, etc.)
timestamp                                 [int]      - Unix timestamp in milliseconds
project                                   [str]      - Working directory path
```

---

## 3. `~/.claude/projects/<project>/<session>.jsonl`
**Purpose:** Complete conversation transcripts
**Size:** Up to 45+ MB per session
**Location:** Project name is path with `/` → `-` (e.g., `-mnt-c-python-myproject`)

### Message Entry Schema:
```
uuid                                      [str]      - Unique message ID
parentUuid                                [str|null] - Parent message (for threading)
sessionId                                 [str]      - Session UUID
timestamp                                 [str]      - ISO timestamp
type                                      [str]      - "user" | "assistant" | "file-history-snapshot"
cwd                                       [str]      - Working directory
userType                                  [str]      - "external" (human) | "internal" (agent)
version                                   [str]      - Claude Code version
gitBranch                                 [str]      - Current git branch
isSidechain                               [bool]     - Sidechain/alternate exploration

message                                   [dict]     - The actual message content
  .role                                   [str]      - "user" | "assistant"
  .model                                  [str]      - Model ID used (for assistant)
  .id                                     [str]      - API message ID
  .stop_reason                            [str|null] - Why generation stopped
  .usage                                  [dict]     - Token usage for this message
    .input_tokens                         [int]
    .output_tokens                        [int]
    .cache_read_input_tokens              [int]
    .cache_creation_input_tokens          [int]
    .cache_creation.ephemeral_1h_input_tokens  [int]
    .cache_creation.ephemeral_5m_input_tokens  [int]
    .service_tier                         [str]

  .content[]                              [list]     - Content blocks
    (for text blocks)
    .type                                 [str]      - "text"
    .text                                 [str]      - The text content

    (for thinking blocks)
    .type                                 [str]      - "thinking"
    .thinking                             [str]      - Extended thinking content
    .signature                            [str]      - Thinking signature

    (for tool_use blocks)
    .type                                 [str]      - "tool_use"
    .id                                   [str]      - Tool use ID
    .name                                 [str]      - Tool name (Bash, Read, Edit, etc.)
    .input                                [dict]     - Tool parameters
      # Varies by tool - see Tool Input Schemas below

    (for tool_result blocks)
    .type                                 [str]      - "tool_result"
    .tool_use_id                          [str]      - Corresponding tool_use ID
    .content                              [str|list] - Result content
    .is_error                             [bool]     - Whether tool failed

thinkingMetadata                          [dict]     - Thinking configuration
  .level                                  [str]      - Thinking level
  .disabled                               [bool]     - Whether thinking disabled
  .triggers[]                             [list]     - What triggered thinking
    .text                                 [str]      - Trigger text
    .start                                [int]      - Start position
    .end                                  [int]      - End position

requestId                                 [str]      - API request ID

toolUseResult                             [dict|str] - Tool execution result
  .type                                   [str]      - Result type
  .status                                 [str]      - "success" | "error"
  .durationMs                             [int]      - Execution time
  .totalDurationMs                        [int]      - Total time including overhead
  .interrupted                            [bool]     - Whether interrupted
  .truncated                              [bool]     - Whether output truncated

  # For Bash tool:
  .stdout                                 [str]      - Standard output
  .stderr                                 [str]      - Standard error

  # For Read tool:
  .file                                   [dict]
    .filePath                             [str]      - File path read
    .content                              [str]      - File content
    .numLines                             [int]      - Lines returned
    .startLine                            [int]      - Starting line
    .totalLines                           [int]      - Total file lines
  .isImage                                [bool]     - Whether file is image

  # For Edit tool:
  .filePath                               [str]      - Edited file
  .oldString                              [str]      - Text replaced
  .newString                              [str]      - Replacement text
  .replaceAll                             [bool]     - Whether replaced all
  .originalFile                           [str|null] - Original content
  .structuredPatch[]                      [list]     - Diff hunks
    .oldStart                             [int]
    .oldLines                             [int]
    .newStart                             [int]
    .newLines                             [int]
    .lines[]                              [list]     - Diff lines
  .userModified                           [bool]     - Whether user modified

  # For Write tool:
  .filePath                               [str]      - Written file
  .numLines                               [int]      - Lines written

  # For Glob tool:
  .filenames[]                            [list]     - Matching files
  .numFiles                               [int]      - Count of matches

  # For Grep tool:
  .mode                                   [str]      - Search mode
  .filenames[]                            [list]     - Files with matches
  .numFiles                               [int]      - File count
  .numLines                               [int]      - Line count
  .content                                [str]      - Search results

  # For Task tool:
  .agentId                                [str]      - Spawned agent ID
  .totalTokens                            [int]      - Tokens used by agent
  .totalToolUseCount                      [int]      - Tools used by agent
  .usage                                  [dict]     - Token breakdown

  # For AskUserQuestion tool:
  .questions[]                            [list]     - Questions asked
    .question                             [str]
    .header                               [str]
    .multiSelect                          [bool]
    .options[]                            [list]
      .label                              [str]
      .description                        [str]
  .answers                                [dict]     - User responses

  # For WebFetch tool:
  .prompt                                 [str]      - Extraction prompt
  .content                                [str]      - Extracted content
```

### File History Snapshot Schema:
```
type                                      [str]      - "file-history-snapshot"
messageId                                 [str]      - Associated message ID
isSnapshotUpdate                          [bool]     - Is this an update?

snapshot                                  [dict]
  .messageId                              [str]
  .timestamp                              [str]      - ISO timestamp
  .trackedFileBackups                     [dict]     - File → backup info
    .<filepath>                           [dict]
      .backupFileName                     [str|null] - Backup file in file-history
      .backupTime                         [str]      - Backup timestamp
      .version                            [int]      - Version number
```

### Agent Session Entries (agent-*.jsonl):
```
agentId                                   [str]      - Agent identifier
level                                     [str]      - Nesting level
subtype                                   [str]      - Agent subtype
summary                                   [str]      - Conversation summary
leafUuid                                  [str]      - Latest message UUID
slug                                      [str]      - Agent slug
isMeta                                    [bool]     - Meta agent flag
```

---

## 4. `~/.claude/todos/<session-agent>.json`
**Purpose:** Task/todo lists per session
**Size:** 0-2 KB typically
**Count:** ~1,765 files

### Schema:
```
[]                                        [list]     - Array of todos
  .id                                     [str]      - Todo ID
  .content                                [str]      - Task description
  .status                                 [str]      - "pending" | "in_progress" | "completed"
  .priority                               [str]      - "high" | "medium" | "low"
  .activeForm                             [str]      - Present tense description (optional)
```

---

## 5. `~/.claude/plans/<creative-name>.md`
**Purpose:** Implementation plan documents
**Size:** 1-96 KB
**Count:** 43 files
**Naming:** Alliterative creative names (e.g., "dreamy-floating-newell.md")

### Content Structure:
- Markdown format
- Contains: objectives, deliverables, implementation steps
- May include code blocks, file structures, dependencies
- Headers indicate structure depth

---

## 6. `~/.claude/__store.db` (SQLite)
**Purpose:** Structured message storage
**Size:** ~2.2 MB

### Tables:

#### `base_messages`
```
uuid                    TEXT     [PK]    - Message UUID
parent_uuid             TEXT             - Parent message
session_id              TEXT     [NOT NULL] - Session UUID
timestamp               INTEGER  [NOT NULL] - Unix timestamp (ms)
message_type            TEXT     [NOT NULL] - "user" | "assistant"
cwd                     TEXT     [NOT NULL] - Working directory
user_type               TEXT     [NOT NULL] - "external" | "internal"
version                 TEXT     [NOT NULL] - Claude Code version
isSidechain             INTEGER  [NOT NULL] - Boolean flag
```

#### `user_messages`
```
uuid                    TEXT     [PK]    - Message UUID
message                 TEXT     [NOT NULL] - Full message JSON
tool_use_result         TEXT             - Tool result if any
timestamp               INTEGER  [NOT NULL] - Unix timestamp
```

#### `assistant_messages`
```
uuid                    TEXT     [PK]    - Message UUID
cost_usd                REAL     [NOT NULL] - API cost
duration_ms             INTEGER  [NOT NULL] - Response time
message                 TEXT     [NOT NULL] - Full message JSON
is_api_error_message    INTEGER  [NOT NULL] - Error flag
timestamp               INTEGER  [NOT NULL] - Unix timestamp
model                   TEXT     [NOT NULL] - Model used
```

#### `conversation_summaries`
```
leaf_uuid               TEXT     [PK]    - Latest message UUID
summary                 TEXT     [NOT NULL] - Conversation summary
updated_at              INTEGER  [NOT NULL] - Last update timestamp
```

---

## 7. `~/.claude/debug/<session-id>.txt`
**Purpose:** Debug/diagnostic logs
**Size:** 10 KB - 1.6 MB per session
**Count:** ~1,707 files
**Format:** Timestamped log lines

### Log Entry Format:
```
YYYY-MM-DDTHH:MM:SS.mmmZ [LEVEL] Message
```

### Log Levels:
- `[DEBUG]` - Detailed diagnostic info
- `[ERROR]` - Error conditions
- `[WARN]` - Warnings

### Key Log Events:
- Settings file watching
- LSP server initialization
- Plugin loading/discovery
- Permission updates
- Skill loading
- Shell snapshot creation
- File write operations
- Git operations
- Stats cache updates
- Marketplace updates
- Slow operation detection

---

## 8. `~/.claude/file-history/<session-id>/`
**Purpose:** File backup/versioning
**Size:** ~45.7 MB total
**Count:** ~3,946 files across ~126 sessions

### Filename Format:
```
<hash>@v<version>
```
- `<hash>` - 16-character hex hash of file path
- `<version>` - Sequential version number (1, 2, 3...)

### Content:
- Full file content at that version
- Preserves permissions (file mode)

---

## 9. `~/.claude/settings.json`
**Purpose:** User preferences
**Size:** ~1.8 KB

### Schema:
```
model                                     [str]      - Default model
alwaysThinkingEnabled                     [bool]     - Extended thinking on/off
gitAttribution                            [bool]     - Git author attribution
includeCoAuthoredBy                       [bool]     - Co-author in commits

permissions                               [dict]
  .defaultMode                            [str]      - "ask" | "allow" | "deny"
  .allow[]                                [list]     - Auto-allowed tools/patterns
  .deny[]                                 [list]     - Denied tools/patterns
  .ask[]                                  [list]     - Always-ask tools/patterns

env                                       [dict]     - Environment variables
  .MAX_THINKING_TOKENS                    [str]      - Thinking budget

hooks                                     [dict]     - Hook configurations

statusLine                                [dict]
  .type                                   [str]      - "command"
  .command                                [str]      - Status line command
```

---

## 10. `~/.claude/shell-snapshots/`
**Purpose:** Shell environment snapshots
**Size:** ~0.3 MB total
**Count:** ~81 files

### Filename Format:
```
snapshot-<shell>-<timestamp>-<random>.sh
```

### Content:
- Shell aliases (base64 encoded)
- Shell functions (base64 encoded)
- Shell options (shopt settings)
- Environment reconstruction script

---

## 11. `~/.claude/agents/`
**Purpose:** Custom agent definitions
**Size:** ~64 KB total
**Count:** 9 files

### File Format:
- Markdown files (`<agent-name>.md`)
- Contains agent prompts and instructions

### Known Agents:
- adversarial-generator.md
- adversarial-orchestrator.md
- adversarial-validator.md
- new-hire.md
- parallel-integrate.md
- parallel-monitor.md
- parallel-setup.md
- repo_architect.md
- therapist.md

---

## 12. `~/.claude/commands/`
**Purpose:** Custom slash command definitions
**Size:** ~44 KB
**Count:** 9 files

### File Format:
- Markdown files (`<command-name>.md`)
- Contains command prompts

### Known Commands:
- backup.md
- describe.md
- github.md
- github-private.md
- plancompact.md
- pull.md
- push.md
- sync.md

---

## 13. `~/.claude/skills/`
**Purpose:** Custom skill libraries
**Size:** ~0.3 MB
**Count:** 51 files across subdirectories

### Structure:
```
skills/
├── <skill-name>/
│   ├── SKILL.md           - Skill definition
│   ├── CHEATSHEET.md      - Quick reference
│   ├── reference.md       - Detailed docs
│   ├── configs/           - Configuration files
│   ├── scripts/           - Python scripts
│   └── templates/         - Template files
```

---

## 14. `~/.claude/plugins/`
**Purpose:** Plugin management
**Size:** ~0.5 MB

### Key Files:
```
config.json                - Plugin configuration
installed_plugins.json     - Installed plugin registry
known_marketplaces.json    - Marketplace registry
marketplaces/              - Downloaded marketplace catalogs
repos/                     - Plugin repositories
```

### known_marketplaces.json Schema:
```
<marketplace-name>                        [dict]
  .source                                 [dict]
    .source                               [str]      - "github"
    .repo                                 [str]      - GitHub repo path
  .installLocation                        [str]      - Local path
  .lastUpdated                            [str]      - ISO timestamp
```

---

## 15. `~/.claude/statsig/`
**Purpose:** Feature flag/experiment cache
**Size:** ~0.1 MB
**Count:** 14 files

### Content:
- Statsig SDK cache files
- Feature flag evaluations
- Experiment assignments

---

## 16. `~/.claude/session-env/<session-id>/`
**Purpose:** Session environment data
**Size:** Minimal (often empty)
**Count:** ~104 directories

---

# PART 2: COMPLETE TOOL INPUT SCHEMAS

## Bash Tool
```
command                                   [str]      - Command to execute
description                               [str]      - 5-10 word description
timeout                                   [int]      - Timeout in ms (max 600000)
run_in_background                         [bool]     - Run asynchronously
dangerouslyDisableSandbox                 [bool]     - Override sandbox
```

## Read Tool
```
file_path                                 [str]      - Absolute file path
offset                                    [int]      - Starting line number
limit                                     [int]      - Number of lines
```

## Edit Tool
```
file_path                                 [str]      - Absolute file path
old_string                                [str]      - Text to replace
new_string                                [str]      - Replacement text
replace_all                               [bool]     - Replace all occurrences
```

## Write Tool
```
file_path                                 [str]      - Absolute file path
content                                   [str]      - File content
```

## Glob Tool
```
pattern                                   [str]      - Glob pattern
path                                      [str]      - Search directory
```

## Grep Tool
```
pattern                                   [str]      - Regex pattern
path                                      [str]      - Search path
output_mode                               [str]      - "content" | "files_with_matches" | "count"
glob                                      [str]      - File filter pattern
type                                      [str]      - File type filter
-A, -B, -C                                [int]      - Context lines
-i                                        [bool]     - Case insensitive
-n                                        [bool]     - Show line numbers
multiline                                 [bool]     - Multiline matching
head_limit                                [int]      - Limit results
offset                                    [int]      - Skip results
```

## Task Tool
```
prompt                                    [str]      - Task description
subagent_type                             [str]      - Agent type
description                               [str]      - Short description
model                                     [str]      - "sonnet" | "opus" | "haiku"
resume                                    [str]      - Agent ID to resume
run_in_background                         [bool]     - Background execution
```

## WebFetch Tool
```
url                                       [str]      - URL to fetch
prompt                                    [str]      - Extraction prompt
```

## WebSearch Tool
```
query                                     [str]      - Search query
allowed_domains[]                         [list]     - Whitelist domains
blocked_domains[]                         [list]     - Blacklist domains
```

## TodoWrite Tool
```
todos[]                                   [list]     - Todo items
  .content                                [str]      - Task description
  .status                                 [str]      - Task status
  .activeForm                             [str]      - Present tense form
```

## AskUserQuestion Tool
```
questions[]                               [list]     - Up to 4 questions
  .question                               [str]      - Question text
  .header                                 [str]      - Short label (≤12 chars)
  .multiSelect                            [bool]     - Allow multiple selections
  .options[]                              [list]     - 2-4 options
    .label                                [str]      - Option text
    .description                          [str]      - Option explanation
```

---

# PART 3: EXTRACTABLE METRICS

## Category 1: Time & Activity Metrics

### Raw Metrics (Direct Extraction)
| # | Metric | Source | Field/Derivation |
|---|--------|--------|------------------|
| 1 | Total messages all-time | stats-cache.json | `totalMessages` |
| 2 | Total sessions all-time | stats-cache.json | `totalSessions` |
| 3 | First session date | stats-cache.json | `firstSessionDate` |
| 4 | Daily message count | stats-cache.json | `dailyActivity[].messageCount` |
| 5 | Daily session count | stats-cache.json | `dailyActivity[].sessionCount` |
| 6 | Daily tool call count | stats-cache.json | `dailyActivity[].toolCallCount` |
| 7 | Hourly activity distribution | stats-cache.json | `hourCounts` |
| 8 | Longest session duration | stats-cache.json | `longestSession.duration` |
| 9 | Longest session message count | stats-cache.json | `longestSession.messageCount` |
| 10 | User input timestamps | history.jsonl | `timestamp` |
| 11 | Message timestamps | session JSONL | `timestamp` |
| 12 | Session start time | session JSONL | First message timestamp |
| 13 | Session end time | session JSONL | Last message timestamp |

### Derived Metrics (Computed)
| # | Metric | Calculation |
|---|--------|-------------|
| 14 | Active coding hours (daily) | Gap-based session detection from history.jsonl |
| 15 | Active coding hours (weekly) | Sum of daily active hours |
| 16 | User inter-message gap time | Time between consecutive user messages |
| 17 | Average session duration | (end - start) per session, averaged |
| 18 | Session frequency | Sessions per day/week/month |
| 19 | Peak productivity hours | Top 3 hours by activity |
| 20 | Work style classification | Night owl vs early bird based on hourCounts |
| 21 | Activity streaks (current) | Consecutive days with activity |
| 22 | Activity streaks (longest) | Maximum consecutive active days |
| 23 | Days with activity | Count of unique dates in dailyActivity |
| 24 | Average daily messages | totalMessages / days with activity |
| 25 | Weekend vs weekday ratio | Activity by day of week |
| 26 | Morning/afternoon/evening split | Activity by time period |
| 27 | Session time distribution | Histogram of session start times |
| 28 | Idle time patterns | Gaps > threshold between sessions |

---

## Category 2: Tool Usage Metrics

### Raw Metrics
| # | Metric | Source | Field/Derivation |
|---|--------|--------|------------------|
| 29 | Total tool calls per tool | session JSONL | Count tool_use by name |
| 30 | Bash command count | session JSONL | tool_use where name="Bash" |
| 31 | Read operations count | session JSONL | tool_use where name="Read" |
| 32 | Edit operations count | session JSONL | tool_use where name="Edit" |
| 33 | Write operations count | session JSONL | tool_use where name="Write" |
| 34 | Grep search count | session JSONL | tool_use where name="Grep" |
| 35 | Glob search count | session JSONL | tool_use where name="Glob" |
| 36 | Task/agent spawn count | session JSONL | tool_use where name="Task" |
| 37 | Web fetch count | session JSONL | tool_use where name="WebFetch" |
| 38 | Web search count | session JSONL | tool_use where name="WebSearch" |
| 39 | AskUserQuestion count | session JSONL | tool_use where name="AskUserQuestion" |
| 40 | TodoWrite count | session JSONL | tool_use where name="TodoWrite" |
| 41 | Skill invocation count | session JSONL | tool_use where name="Skill" |
| 42 | SlashCommand count | session JSONL | tool_use where name="SlashCommand" |
| 43 | EnterPlanMode count | session JSONL | tool_use where name="EnterPlanMode" |
| 44 | ExitPlanMode count | session JSONL | tool_use where name="ExitPlanMode" |
| 45 | KillShell count | session JSONL | tool_use where name="KillShell" |
| 46 | MCP tool invocations | session JSONL | tool_use where name starts with "mcp__" |
| 47 | Tool execution duration | session JSONL | toolUseResult.durationMs |
| 48 | Tool total duration | session JSONL | toolUseResult.totalDurationMs |

### Derived Metrics
| # | Metric | Calculation |
|---|--------|-------------|
| 49 | Tool usage distribution | Percentage of each tool type |
| 50 | Tool calls per session | totalToolCalls / totalSessions |
| 51 | Tool calls per message | totalToolCalls / totalMessages |
| 52 | Read/Write ratio | Read count / Write count |
| 53 | Edit vs Write ratio | Edit count / Write count |
| 54 | Search intensity | (Grep + Glob) / session |
| 55 | Agent delegation ratio | Task count / total tools |
| 56 | Average tool execution time | Mean of durationMs |
| 57 | Slowest tool operations | Top N by durationMs |
| 58 | Tool success rate | Successful / total per tool |
| 59 | Tool co-occurrence | Tools frequently used together |

---

## Category 3: File Operation Metrics

### Raw Metrics
| # | Metric | Source | Field/Derivation |
|---|--------|--------|------------------|
| 60 | Files read (unique) | session JSONL | Unique file_path in Read tools |
| 61 | Files edited (unique) | session JSONL | Unique file_path in Edit tools |
| 62 | Files written (unique) | session JSONL | Unique file_path in Write tools |
| 63 | Read count per file | session JSONL | Count per file_path |
| 64 | Edit count per file | session JSONL | Count per file_path |
| 65 | Lines read per operation | session JSONL | toolUseResult.file.numLines |
| 66 | Lines written per file | session JSONL | toolUseResult.numLines |
| 67 | File versions in history | file-history | Count of @v* per hash |
| 68 | Max versions per file | file-history | Max version number |
| 69 | Backup file sizes | file-history | File sizes |
| 70 | Tracked file count | session JSONL | snapshot.trackedFileBackups keys |

### Derived Metrics
| # | Metric | Calculation |
|---|--------|-------------|
| 71 | Most read files | Top N by read count |
| 72 | Most edited files | Top N by edit count |
| 73 | Most written files | Top N by write count |
| 74 | File churn rate | Edits per file over time |
| 75 | File iteration intensity | Avg versions per modified file |
| 76 | Files with high revision count | Files with >5 versions |
| 77 | File type distribution | Extensions of modified files |
| 78 | Code vs config ratio | .py,.js vs .json,.yaml |
| 79 | Documentation touch rate | .md files / total files |
| 80 | File co-modification | Files edited together |
| 81 | Read-before-edit ratio | Reads preceding edits |

---

## Category 4: Model & Token Metrics

### Raw Metrics
| # | Metric | Source | Field/Derivation |
|---|--------|--------|------------------|
| 82 | Model used per message | session JSONL | message.model |
| 83 | Input tokens per message | session JSONL | message.usage.input_tokens |
| 84 | Output tokens per message | session JSONL | message.usage.output_tokens |
| 85 | Cache read tokens | session JSONL | message.usage.cache_read_input_tokens |
| 86 | Cache creation tokens | session JSONL | message.usage.cache_creation_input_tokens |
| 87 | Ephemeral cache tokens (5m) | session JSONL | message.usage.cache_creation.ephemeral_5m_input_tokens |
| 88 | Ephemeral cache tokens (1h) | session JSONL | message.usage.cache_creation.ephemeral_1h_input_tokens |
| 89 | Service tier | session JSONL | message.usage.service_tier |
| 90 | Daily tokens by model | stats-cache.json | dailyModelTokens[].tokensByModel |
| 91 | Total input tokens by model | stats-cache.json | modelUsage.*.inputTokens |
| 92 | Total output tokens by model | stats-cache.json | modelUsage.*.outputTokens |
| 93 | Total cache read tokens | stats-cache.json | modelUsage.*.cacheReadInputTokens |
| 94 | Total cache creation tokens | stats-cache.json | modelUsage.*.cacheCreationInputTokens |
| 95 | Web search request count | stats-cache.json | modelUsage.*.webSearchRequests |

### Derived Metrics
| # | Metric | Calculation |
|---|--------|-------------|
| 96 | Model usage distribution | Percentage by model |
| 97 | Tokens per message | outputTokens / messageCount |
| 98 | Tokens per session | Total tokens / sessionCount |
| 99 | Tokens per day | Sum of daily tokens |
| 100 | Cache hit ratio | cacheRead / (cacheRead + input) |
| 101 | Cache efficiency | cacheRead / cacheCreation |
| 102 | Estimated API cost (Opus) | outputTokens * $75/M |
| 103 | Estimated API cost (Sonnet) | outputTokens * $15/M |
| 104 | Estimated API cost (Haiku) | outputTokens * $1.25/M |
| 105 | Total estimated cost | Sum of model costs |
| 106 | Cost per session | Total cost / sessions |
| 107 | Cost per day | Daily token-based cost |
| 108 | Model preference trend | Model usage over time |
| 109 | Token consumption trend | Daily/weekly token growth |

---

## Category 5: Conversation Pattern Metrics

### Raw Metrics
| # | Metric | Source | Field/Derivation |
|---|--------|--------|------------------|
| 110 | User message count | session JSONL | type="user" count |
| 111 | Assistant message count | session JSONL | type="assistant" count |
| 112 | User message text | session JSONL | message.content (string) |
| 113 | User message length | session JSONL | len(message.content) |
| 114 | Assistant response length | session JSONL | len(text content) |
| 115 | Thinking block count | session JSONL | content.type="thinking" |
| 116 | Thinking block length | session JSONL | len(thinking content) |
| 117 | Code block count | session JSONL | Count of ``` in text |
| 118 | Conversation depth | session JSONL | Messages per session |
| 119 | Sidechain count | session JSONL | isSidechain=true count |
| 120 | Stop reason | session JSONL | message.stop_reason |
| 121 | Parent-child threading | session JSONL | parentUuid chains |

### Derived Metrics
| # | Metric | Calculation |
|---|--------|-------------|
| 122 | Questions asked by user | Messages containing "?" |
| 123 | Commands given by user | Messages starting with verbs |
| 124 | Code pastes by user | Messages with ``` or len>500 |
| 125 | Error reports by user | Messages with "error", "traceback" |
| 126 | Gratitude expressions | Messages with "thanks", "perfect" |
| 127 | Frustration indicators | Messages with "wrong", "still not" |
| 128 | User/assistant message ratio | User count / assistant count |
| 129 | Average thinking length | Mean of thinking block sizes |
| 130 | Extended thinking usage rate | Sessions with thinking / total |
| 131 | Conversation complexity | Thinking length * frequency |
| 132 | Back-and-forth density | Messages per time unit |
| 133 | User message verbosity | Avg user message length |
| 134 | Response verbosity | Avg assistant response length |
| 135 | Topic classification | Keyword-based topic detection |
| 136 | Sentiment trajectory | Frustration/gratitude over time |

---

## Category 6: Task Management Metrics

### Raw Metrics
| # | Metric | Source | Field/Derivation |
|---|--------|--------|------------------|
| 137 | Todo files count | todos/ | File count |
| 138 | Todos per session | todos/*.json | Array length per file |
| 139 | Todo status | todos/*.json | status field |
| 140 | Todo priority | todos/*.json | priority field |
| 141 | Todo content | todos/*.json | content field |

### Derived Metrics
| # | Metric | Calculation |
|---|--------|-------------|
| 142 | Total todos created | Sum of all todo items |
| 143 | Completed todos | status="completed" count |
| 144 | In-progress todos | status="in_progress" count |
| 145 | Pending todos | status="pending" count |
| 146 | Overall completion rate | completed / total |
| 147 | Session completion rate | completed / session total |
| 148 | Abandoned task rate | in_progress with no completion |
| 149 | High priority task ratio | high / total |
| 150 | Average tasks per session | Total todos / sessions with todos |
| 151 | Max tasks in single session | Max todo array length |
| 152 | Task complexity estimate | Avg word count in todo content |

---

## Category 7: Planning Metrics

### Raw Metrics
| # | Metric | Source | Field/Derivation |
|---|--------|--------|------------------|
| 153 | Plan files count | plans/ | File count |
| 154 | Plan file sizes | plans/ | File sizes |
| 155 | Plan content | plans/*.md | File content |
| 156 | Plan creation dates | plans/ | File timestamps |

### Derived Metrics
| # | Metric | Calculation |
|---|--------|-------------|
| 157 | Total plans created | Count of plan files |
| 158 | Average plan size | Mean file size |
| 159 | Largest plan | Max file size |
| 160 | Plan line count | Lines per plan |
| 161 | Code blocks in plans | Count of ``` in plans |
| 162 | Headers in plans | Count of # lines |
| 163 | Structure depth | Max header level |
| 164 | Technologies mentioned | Keyword extraction |
| 165 | Action word frequency | "create", "implement", "fix" counts |
| 166 | Plan complexity score | Size * headers * code blocks |
| 167 | Planning frequency | Plans per week |

---

## Category 8: Agent/Subagent Metrics

### Raw Metrics
| # | Metric | Source | Field/Derivation |
|---|--------|--------|------------------|
| 168 | Agent session files | projects/*/agent-*.jsonl | File count |
| 169 | Main session files | projects/*/*.jsonl (non-agent) | File count |
| 170 | Subagent type used | session JSONL | Task input.subagent_type |
| 171 | Agent tokens used | session JSONL | toolUseResult.totalTokens |
| 172 | Agent tool use count | session JSONL | toolUseResult.totalToolUseCount |
| 173 | Agent ID | session JSONL | toolUseResult.agentId |

### Derived Metrics
| # | Metric | Calculation |
|---|--------|-------------|
| 174 | Agent usage ratio | Agent sessions / total sessions |
| 175 | Subagent type distribution | Count by subagent_type |
| 176 | Most used subagent | Top subagent_type |
| 177 | Agent token efficiency | Tokens per agent task |
| 178 | Agent tool efficiency | Tools per agent task |
| 179 | Agent parallelization | Concurrent agent sessions |
| 180 | Agent delegation depth | Nested agent spawns |

---

## Category 9: Project Metrics

### Raw Metrics
| # | Metric | Source | Field/Derivation |
|---|--------|--------|------------------|
| 181 | Project directories | projects/ | Folder names |
| 182 | Sessions per project | projects/<project>/ | Files per folder |
| 183 | Project working directory | session JSONL | cwd field |
| 184 | Git branch | session JSONL | gitBranch field |
| 185 | Git remote URL | debug logs | "Git remote URL" entries |

### Derived Metrics
| # | Metric | Calculation |
|---|--------|-------------|
| 186 | Most active projects | Sessions per project |
| 187 | Project time allocation | Time per project |
| 188 | Project message volume | Messages per project |
| 189 | Branch frequency | Count by branch name |
| 190 | Feature branch activity | Non-main branches |
| 191 | Project switching frequency | cwd changes per session |
| 192 | Multi-project sessions | Sessions spanning projects |

---

## Category 10: Error & Recovery Metrics

### Raw Metrics
| # | Metric | Source | Field/Derivation |
|---|--------|--------|------------------|
| 193 | Tool errors | session JSONL | is_error=true or toolUseResult.type="error" |
| 194 | API errors | __store.db | is_api_error_message=1 |
| 195 | Bash exit codes | session JSONL | stderr patterns |
| 196 | Edit conflicts | session JSONL | "not found in file" patterns |
| 197 | File read failures | session JSONL | ENOENT patterns |
| 198 | Permission errors | session JSONL | "permission denied" patterns |
| 199 | Interrupted operations | session JSONL | toolUseResult.interrupted=true |
| 200 | Truncated outputs | session JSONL | toolUseResult.truncated=true |

### Derived Metrics
| # | Metric | Calculation |
|---|--------|-------------|
| 201 | Overall error rate | Errors / total tool calls |
| 202 | Error rate by tool | Errors / calls per tool |
| 203 | Recovery success rate | Errors followed by success |
| 204 | Retry frequency | Repeated tool calls |
| 205 | Error clustering | Errors per session |
| 206 | Error time patterns | Errors by hour/day |

---

## Category 11: Code Generation Metrics

### Raw Metrics
| # | Metric | Source | Field/Derivation |
|---|--------|--------|------------------|
| 207 | Code blocks by language | session JSONL | ```language patterns |
| 208 | Code block content | session JSONL | Text between ``` |
| 209 | Edit old_string | session JSONL | Edit tool input.old_string |
| 210 | Edit new_string | session JSONL | Edit tool input.new_string |
| 211 | Write content | session JSONL | Write tool input.content |
| 212 | Structured patches | session JSONL | toolUseResult.structuredPatch |

### Derived Metrics
| # | Metric | Calculation |
|---|--------|-------------|
| 213 | Total code generated (KB) | Sum of code block sizes |
| 214 | Code by language | Size per language |
| 215 | Python code volume | Python blocks |
| 216 | JavaScript code volume | JS/TS blocks |
| 217 | Bash command volume | Bash blocks |
| 218 | Functions defined | def/function patterns |
| 219 | Classes defined | class patterns |
| 220 | Imports added | import/require patterns |
| 221 | Average code block size | Mean block length |
| 222 | Largest code block | Max block length |
| 223 | Net lines added | Patch analysis |
| 224 | Net lines removed | Patch analysis |
| 225 | Code churn | Added + removed |
| 226 | Code density | Code / total output |

---

## Category 12: Web Research Metrics

### Raw Metrics
| # | Metric | Source | Field/Derivation |
|---|--------|--------|------------------|
| 227 | Web searches performed | session JSONL | WebSearch tool count |
| 228 | Search queries | session JSONL | WebSearch input.query |
| 229 | Domains searched | session JSONL | allowed_domains, blocked_domains |
| 230 | Pages fetched | session JSONL | WebFetch tool count |
| 231 | URLs fetched | session JSONL | WebFetch input.url |
| 232 | Fetch prompts | session JSONL | WebFetch input.prompt |

### Derived Metrics
| # | Metric | Calculation |
|---|--------|-------------|
| 233 | Search frequency | Searches per session |
| 234 | Search topics | Query keyword extraction |
| 235 | Most fetched domains | Domain frequency |
| 236 | Documentation sites | docs.*, github.com frequency |
| 237 | Research intensity | (Search + Fetch) / session |
| 238 | External dependency | Web tools / total tools |

---

## Category 13: Settings & Configuration Metrics

### Raw Metrics
| # | Metric | Source | Field/Derivation |
|---|--------|--------|------------------|
| 239 | Default model | settings.json | model |
| 240 | Thinking enabled | settings.json | alwaysThinkingEnabled |
| 241 | Permission rules | settings.json | permissions.allow/deny/ask |
| 242 | Hooks configured | settings.json | hooks |
| 243 | Environment variables | settings.json | env |
| 244 | Custom agents | agents/*.md | File list |
| 245 | Custom commands | commands/*.md | File list |
| 246 | Custom skills | skills/*/ | Directory list |
| 247 | Installed plugins | plugins/installed_plugins.json | plugins |
| 248 | Known marketplaces | plugins/known_marketplaces.json | marketplaces |

### Derived Metrics
| # | Metric | Calculation |
|---|--------|-------------|
| 249 | Configuration complexity | Count of custom configs |
| 250 | Automation level | Auto-allow rules |
| 251 | Security posture | Deny rules / total rules |
| 252 | Customization score | Agents + commands + skills |

---

## Category 14: Debug & Diagnostic Metrics

### Raw Metrics
| # | Metric | Source | Field/Derivation |
|---|--------|--------|------------------|
| 253 | Debug log entries | debug/*.txt | Line count |
| 254 | Error log entries | debug/*.txt | [ERROR] lines |
| 255 | Warning log entries | debug/*.txt | [WARN] lines |
| 256 | Slow operations | debug/*.txt | [SLOW OPERATION] lines |
| 257 | Plugin load events | debug/*.txt | Plugin-related entries |
| 258 | LSP events | debug/*.txt | LSP-related entries |
| 259 | Skill load events | debug/*.txt | Skill-related entries |

### Derived Metrics
| # | Metric | Calculation |
|---|--------|-------------|
| 260 | Error frequency | Errors per session |
| 261 | Slow operation frequency | Slow ops per session |
| 262 | System health score | 1 - (errors / total) |
| 263 | Startup time patterns | Time to first message |

---

## Category 15: Advanced Derived Metrics

### Productivity Scores
| # | Metric | Calculation |
|---|--------|-------------|
| 264 | Focus score | Deep sessions (>30min) / total |
| 265 | Iteration index | Avg file versions per task |
| 266 | Self-sufficiency ratio | Tasks without errors / total |
| 267 | Code velocity | KB generated per hour |
| 268 | Pair programming score | Message density per session |

### Efficiency Scores
| # | Metric | Calculation |
|---|--------|-------------|
| 269 | Context efficiency | Cache hit rate |
| 270 | Tool efficiency | Successful tools / total |
| 271 | Token efficiency | Output tokens / input tokens |
| 272 | Time efficiency | Work done / time spent |

### Learning & Growth
| # | Metric | Calculation |
|---|--------|-------------|
| 273 | Error rate trend | Error rate over time |
| 274 | Complexity handling | Thinking length trend |
| 275 | Feature discovery | New tools/features used |
| 276 | Skill progression | Completion rate trend |

### Work Patterns
| # | Metric | Calculation |
|---|--------|-------------|
| 277 | Consistency score | Std dev of daily activity |
| 278 | Deep work ratio | Long sessions / total |
| 279 | Context switching | Project changes per day |
| 280 | Burnout indicators | Late night + declining activity |

### Collaboration Indicators
| # | Metric | Calculation |
|---|--------|-------------|
| 281 | Question/answer ratio | Questions / total messages |
| 282 | Clarification frequency | AskUserQuestion / session |
| 283 | Plan approval rate | ExitPlanMode / EnterPlanMode |

### Quality Metrics
| # | Metric | Calculation |
|---|--------|-------------|
| 284 | Documentation debt | Code / docs ratio |
| 285 | Test coverage proxy | pytest mentions / code volume |
| 286 | Refactoring frequency | "refactor" in conversations |
| 287 | Code review engagement | review-related queries |

---

## Category 16: Temporal Analysis Metrics

| # | Metric | Calculation |
|---|--------|-------------|
| 288 | Week-over-week message change | (This week - last week) / last week |
| 289 | Week-over-week session change | Session count comparison |
| 290 | Week-over-week tool change | Tool usage comparison |
| 291 | Monthly active days | Days with activity per month |
| 292 | Quarterly trends | 3-month rolling averages |
| 293 | Seasonal patterns | Activity by month |
| 294 | Growth trajectory | Activity trendline |

---

## Category 17: Cross-Reference Metrics

| # | Metric | Calculation |
|---|--------|-------------|
| 295 | Tool-to-file mapping | Which tools touch which files |
| 296 | Error-to-recovery mapping | Error → successful retry |
| 297 | Search-to-implementation | Search → code generation |
| 298 | Plan-to-completion | Plan creation → task completion |
| 299 | Agent-to-outcome | Agent spawn → result quality |
| 300 | Session-to-commit | Sessions resulting in git commits |

---

# SUMMARY

## Data Sources: 16+
## Raw Fields: 250+
## Extractable Metrics: 300+

### Storage Footprint (Your Instance)
| Source | Size | Records |
|--------|------|---------|
| stats-cache.json | 8 KB | - |
| history.jsonl | 1.6 MB | ~2,500 inputs |
| projects/ | 352 MB | 4,514 sessions |
| todos/ | <1 MB | 1,765 files |
| plans/ | 0.4 MB | 43 plans |
| debug/ | 65 MB | 1,707 logs |
| file-history/ | 46 MB | 3,946 versions |
| __store.db | 2.2 MB | 512 messages |
| **TOTAL** | **~467 MB** | - |

---

# PART 4: DEEP SCAN ADDENDUM (Newly Discovered Fields)

**Scan Statistics:**
- Files scanned: 4,477 session files
- Lines parsed: 83,006 JSONL entries
- Unique field paths discovered: 339 (excluding dynamic file paths)

This section documents fields discovered through deep scanning that were not in the initial catalog.

---

## New Top-Level Message Fields

### Conversation Compaction
```
compactMetadata                           [dict]     - Metadata about conversation compaction
  .preTokens                              [int]      - Token count before compaction
  .trigger                                [str]      - "manual" | "auto" - what triggered compaction

isCompactSummary                          [bool]     - Whether this entry is a compact summary
isVisibleInTranscriptOnly                 [bool]     - Only visible in transcript view
logicalParentUuid                         [str]      - Logical parent for compacted messages
content                                   [str]      - "Conversation compacted" or similar
```

### Hook Execution Data
```
hookCount                                 [int]      - Number of hooks executed
hookErrors                                [list]     - Errors from hook execution
hookInfos                                 [list]     - Hook execution details
  [].command                              [str]      - Full hook command executed

hasOutput                                 [bool]     - Whether hook produced output
preventedContinuation                     [bool]     - Whether hook prevented continuation
stopReason                                [str]      - Reason for stopping (hook-related)
sourceToolUseID                           [str]      - Source tool use ID for hook
toolUseID                                 [str]      - Tool use ID that triggered hook
```

### API Error Handling
```
error                                     [str]      - Error type: "invalid_request" | "unknown"
isApiErrorMessage                         [bool]     - Whether this is an API error message
```

### Session Metadata
```
slug                                      [str]      - Creative session name (e.g., "wild-meandering-sonnet")
subtype                                   [str]      - Message subtype: "compact_boundary" | "local_command"
summary                                   [str]      - Conversation summary text
operation                                 [str]      - Queue operation: "enqueue" | "remove"
isMeta                                    [bool]     - Whether this is a meta-message
leafUuid                                  [str]      - UUID of the leaf message in thread
level                                     [str]      - Log level: "info" | "suggestion"
```

---

## New Message Content Fields

### Context Management
```
message.context_management                [dict|null] - Applied context optimizations
  .applied_edits                          [list]     - Edits applied to manage context
    [].type                               [str]      - Edit type (e.g., "clear_thinking_20251015")
    [].cleared_input_tokens               [int]      - Input tokens cleared
    [].cleared_thinking_turns             [int]      - Thinking turns cleared
```

### Server-Side Tool Usage
```
message.usage.server_tool_use             [dict]     - Server-side tool tracking
  .web_fetch_requests                     [int]      - Server web fetch count
  .web_search_requests                    [int]      - Server web search count

message.container                         [null]     - Container info (reserved/future)
```

### Image/PDF Content in Messages
```
message.content[].source                  [dict]     - For embedded media
  .type                                   [str]      - "base64"
  .media_type                             [str]      - "image/png" | "application/pdf"
  .data                                   [str]      - Base64-encoded content

message.content[].content[].source        [dict]     - Nested media in tool results
  .type                                   [str]      - "base64"
  .media_type                             [str]      - "image/png"
  .data                                   [str]      - Base64-encoded image data
```

---

## New Tool Input Parameters

### Grep Tool Extensions
```
message.content[].input.-A                [int]      - Lines after match (context)
message.content[].input.-B                [int]      - Lines before match (context)
message.content[].input.-C                [int]      - Lines around match (context)
message.content[].input.-i                [bool]     - Case insensitive search
message.content[].input.-n                [bool]     - Show line numbers
message.content[].input.multiline         [bool]     - Enable multiline matching
message.content[].input.filter            [str]      - Output filter regex
message.content[].input.context           [int]      - Additional context lines
message.content[].input.type              [str]      - File type filter (e.g., "py", "md")
message.content[].input.head_limit        [int]      - Limit results count
```

### Task/Agent Tool Extensions
```
message.content[].input.agentId           [str]      - Resume specific agent by ID
message.content[].input.bash_id           [str]      - Background bash shell ID
message.content[].input.shell_id          [str]      - Shell ID for KillShell
message.content[].input.task_id           [str]      - Task ID for TaskOutput
message.content[].input.wait_up_to        [int]      - Max wait time in seconds
message.content[].input.block             [bool]     - Whether to block for result
```

### Plan Mode Extensions
```
message.content[].input.plan              [str]      - Full plan content for ExitPlanMode
message.content[].input.launchSwarm       [bool]     - Whether to launch parallel swarm
message.content[].input.teammateCount     [int]      - Number of parallel workers
```

### Skill/Command Extensions
```
message.content[].input.skill             [str]      - Skill name to invoke
message.content[].input.answer            [int]      - Numeric answer selection
message.content[].input.guess             [list]     - Guess values (for games/puzzles)
message.content[].input.test              [str]      - Test input string
```

---

## New Tool Result Fields

### Agent Results
```
toolUseResult.agentId                     [str]      - Spawned agent's ID
toolUseResult.totalTokens                 [int]      - Total tokens used by agent
toolUseResult.totalToolUseCount           [int]      - Total tool calls by agent
toolUseResult.usage                       [dict]     - Detailed token breakdown
```

### User Question Answers
```
toolUseResult.answers                     [dict]     - User responses to questions
  .<question_text>                        [str]      - Answer for each question
```

**Sample answer keys found (100+):**
- "Which Claude model would you like to test?"
- "How should we proceed with the Phase 2 enhancements?"
- "What testing approach do you want for the async changes?"
- "Should I also create the GitHub Actions CI/CD workflow?"
- ... (questions are captured verbatim as keys)

---

## New Thinking Metadata

```
thinkingMetadata                          [dict]     - Extended thinking configuration
  .disabled                               [bool]     - Whether thinking is disabled
  .level                                  [str]      - "high" | "none" | other levels
  .triggers                               [list]     - What triggered extended thinking
    [].text                               [str]      - Trigger text (e.g., "ULTRATHINK")
    [].start                              [int]      - Start position in input
    [].end                                [int]      - End position in input
```

---

## New Snapshot/Backup Fields

### Tracked File Backups
```
snapshot.trackedFileBackups               [dict]     - File backup tracking
  .<filepath>                             [dict]     - Per-file backup info
    .backupFileName                       [str|null] - Backup file name (hash@version)
    .backupTime                           [str]      - ISO timestamp of backup
    .version                              [int]      - Version number (1, 2, 3...)
```

**Common tracked file patterns:**
- `.claude/agents/*.md` - Agent definitions
- `.claude/commands/*.md` - Command definitions
- `.claude/skills/*` - Skill files
- `README.md`, `Dockerfile`, `Makefile` - Project files
- Source code files being edited

---

## Additional Metrics Enabled by New Fields

### Compaction Metrics (NEW)
| # | Metric | Source |
|---|--------|--------|
| 301 | Conversation compaction events | `isCompactSummary` count |
| 302 | Tokens saved by compaction | `compactMetadata.preTokens` |
| 303 | Auto vs manual compaction ratio | `compactMetadata.trigger` |
| 304 | Compaction frequency | Compactions per session |

### Hook Execution Metrics (NEW)
| # | Metric | Source |
|---|--------|--------|
| 305 | Hooks executed per session | `hookCount` |
| 306 | Hook error rate | `hookErrors` count / total |
| 307 | Hooks preventing continuation | `preventedContinuation` true count |
| 308 | Most common hook commands | `hookInfos[].command` |

### Context Management Metrics (NEW)
| # | Metric | Source |
|---|--------|--------|
| 309 | Thinking turns cleared | `context_management.applied_edits[].cleared_thinking_turns` |
| 310 | Input tokens cleared | `context_management.applied_edits[].cleared_input_tokens` |
| 311 | Context optimization frequency | `context_management` presence |

### User Question Metrics (NEW)
| # | Metric | Source |
|---|--------|--------|
| 312 | Question-answer pairs captured | `toolUseResult.answers` keys |
| 313 | Most common decision points | Question text frequency |
| 314 | User decision patterns | Answer text analysis |

### Session Naming Metrics (NEW)
| # | Metric | Source |
|---|--------|--------|
| 315 | Creative session names | `slug` values |
| 316 | Session naming patterns | Slug word analysis |

### Extended Thinking Metrics (NEW)
| # | Metric | Source |
|---|--------|--------|
| 317 | ULTRATHINK trigger count | `thinkingMetadata.triggers[].text` |
| 318 | Thinking level distribution | `thinkingMetadata.level` |
| 319 | Thinking disabled rate | `thinkingMetadata.disabled` |

### Media Content Metrics (NEW)
| # | Metric | Source |
|---|--------|--------|
| 320 | Images shared in sessions | `message.content[].source.media_type` = image |
| 321 | PDFs analyzed in sessions | `message.content[].source.media_type` = pdf |
| 322 | Total embedded media size | `message.content[].source.data` length |

---

## Updated Summary

### Data Sources: 16+
### Raw Fields: 339 (core session fields, excluding dynamic file paths)
### Total Unique Field Paths: 4,234+ (including all file backup entries)
### Extractable Metrics: 322+

The deep scan revealed significant additional metadata around:
1. **Conversation compaction** - How Claude Code manages long conversations
2. **Hook system** - Pre/post execution hooks and their outcomes
3. **Context management** - Automatic context optimization
4. **User decision capture** - Full Q&A pairs from AskUserQuestion
5. **Media handling** - Images and PDFs embedded in conversations
6. **Extended thinking triggers** - What causes deep reasoning


---

# PART 5: COMPREHENSIVE DERIVED METRICS CATALOG

This section documents all possible derived, computed, and analytical metrics that can be calculated from the raw data.

---

## Category A: Time & Productivity Metrics

### A1. Active Time Calculations
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D001 | Active coding hours (daily) | Gap-based session detection from timestamps; gaps >15min = new session | Daily time tracking |
| D002 | Active coding hours (weekly) | Sum of daily active hours for 7-day window | Weekly reports |
| D003 | Active coding hours (monthly) | Sum of daily active hours for 30-day window | Monthly reports |
| D004 | User thinking time | Time between user messages within session | Implementation time estimate |
| D005 | Claude response time | Time from user message to assistant response | Latency tracking |
| D006 | Session duration | Last timestamp - first timestamp per session | Session length analysis |
| D007 | Average session duration | Mean of all session durations | Typical work session length |
| D008 | Median session duration | Median of session durations | Robust session length |
| D009 | Session duration variance | Standard deviation of session durations | Consistency measure |
| D010 | Time to first tool use | Time from session start to first tool call | Warm-up time |

### A2. Temporal Patterns
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D011 | Peak productivity hour | Hour with highest message count | Optimal work time |
| D012 | Peak productivity day | Day of week with highest activity | Weekly patterns |
| D013 | Morning activity ratio | Messages 6am-12pm / total | Work schedule analysis |
| D014 | Afternoon activity ratio | Messages 12pm-6pm / total | Work schedule analysis |
| D015 | Evening activity ratio | Messages 6pm-12am / total | Work schedule analysis |
| D016 | Night activity ratio | Messages 12am-6am / total | Night owl detection |
| D017 | Weekend vs weekday ratio | Weekend messages / weekday messages | Work-life balance |
| D018 | Work style classification | "Night Owl" vs "Early Bird" based on hourCounts | Personal pattern |
| D019 | Session start time distribution | Histogram of session start hours | When work begins |
| D020 | Session end time distribution | Histogram of session end hours | When work ends |

### A3. Streaks & Consistency
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D021 | Current activity streak | Consecutive days with activity ending today | Motivation tracking |
| D022 | Longest activity streak | Maximum consecutive active days | Achievement tracking |
| D023 | Average streak length | Mean of all streak lengths | Consistency measure |
| D024 | Days since last activity | Today - last active date | Gap detection |
| D025 | Activity consistency score | 1 - (std dev of daily activity / mean) | Regularity measure |
| D026 | Weekly active days | Days with activity in past 7 days | Weekly engagement |
| D027 | Monthly active days | Days with activity in past 30 days | Monthly engagement |
| D028 | Activity density | Messages per active day | Intensity measure |

---

## Category B: Tool Usage Metrics

### B1. Tool Frequency Analysis
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D029 | Tool usage distribution | Percentage of each tool type | Tool preferences |
| D030 | Tool calls per session | Total tool calls / session count | Automation level |
| D031 | Tool calls per message | Tool calls / message count | Tool density |
| D032 | Tool calls per hour | Tool calls / active hours | Productivity rate |
| D033 | Most used tool | Tool with highest count | Primary workflow |
| D034 | Least used tool | Tool with lowest count | Underutilized features |
| D035 | Tool diversity score | Unique tools used / total tools available | Feature adoption |
| D036 | Daily tool call trend | Tool calls over time (slope) | Usage trajectory |

### B2. Tool Efficiency Metrics
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D037 | Tool success rate | Successful calls / total calls | Reliability |
| D038 | Tool error rate | Failed calls / total calls | Problem areas |
| D039 | Tool success rate by type | Success rate per tool | Per-tool reliability |
| D040 | Average tool execution time | Mean of durationMs | Performance |
| D041 | Median tool execution time | Median of durationMs | Robust performance |
| D042 | Slowest tool type | Tool with highest avg durationMs | Bottleneck ID |
| D043 | Tool timeout rate | Timeouts / total calls | Reliability issues |
| D044 | Tool retry rate | Repeated calls / total calls | Error recovery |

### B3. Tool Co-occurrence
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D045 | Read-before-Edit ratio | Read calls preceding Edit / total Edits | Best practice adherence |
| D046 | Grep-then-Read pattern | Grep followed by Read count | Search workflow |
| D047 | Tool sequence patterns | Common tool call sequences | Workflow analysis |
| D048 | Tool clustering | Tools frequently used together | Feature grouping |

---

## Category C: File Operation Metrics

### C1. File Access Patterns
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D049 | Unique files touched | Count of distinct file paths | Project scope |
| D050 | Files per session | Unique files / session count | Session complexity |
| D051 | Most read files | Top N by read count | Reference hotspots |
| D052 | Most edited files | Top N by edit count | Change hotspots |
| D053 | Most written files | Top N by write count | Creation hotspots |
| D054 | File read/write ratio | Read count / (Edit + Write count) | Read vs modify |
| D055 | Edit vs Write ratio | Edit count / Write count | Modify vs create |
| D056 | Files read but never edited | Read-only files | Reference-only files |
| D057 | Files edited without reading | Edits without prior Read | Risky edits |

### C2. File Type Analysis
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D058 | File type distribution | Count by file extension | Language focus |
| D059 | Python file ratio | .py files / total | Python focus |
| D060 | JavaScript file ratio | .js/.ts files / total | JS/TS focus |
| D061 | Markdown file ratio | .md files / total | Documentation focus |
| D062 | Config file ratio | .json/.yaml/.toml / total | Configuration work |
| D063 | Code vs config ratio | Code files / config files | Work type |
| D064 | Test file ratio | *test*.py, *spec*.js / total | Testing focus |

### C3. File Revision Metrics
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D065 | Average versions per file | Mean of version numbers | Iteration intensity |
| D066 | Max versions for any file | Highest version number | Most iterated file |
| D067 | Files with 5+ revisions | Count of highly revised files | Refinement areas |
| D068 | Files with 10+ revisions | Count of very highly revised | Iteration hotspots |
| D069 | Revision rate over time | Versions created per day | Editing velocity |
| D070 | File churn rate | (Creates + Edits) / time period | Change velocity |

### C4. File Co-modification
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D071 | Files modified together | Files changed in same session | Coupling detection |
| D072 | File dependency graph | Co-modification network | Architecture insight |
| D073 | Module coupling score | Cross-module co-modifications | Design quality |

---

## Category D: Model & Token Metrics

### D1. Model Usage Patterns
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D074 | Model usage distribution | Percentage by model | Model preferences |
| D075 | Opus usage ratio | Opus calls / total | Premium model usage |
| D076 | Sonnet usage ratio | Sonnet calls / total | Standard model usage |
| D077 | Haiku usage ratio | Haiku calls / total | Fast model usage |
| D078 | Model switching frequency | Model changes per session | Flexibility |
| D079 | Model preference trend | Model usage over time | Preference shifts |
| D080 | Agent model distribution | Model usage by subagent type | Agent optimization |

### D2. Token Economics
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D081 | Tokens per message | Output tokens / message count | Verbosity |
| D082 | Tokens per session | Total tokens / session count | Session cost |
| D083 | Tokens per hour | Total tokens / active hours | Hourly consumption |
| D084 | Tokens per tool call | Tokens / tool calls | Tool token cost |
| D085 | Input/output token ratio | Input tokens / output tokens | Prompt efficiency |
| D086 | Daily token consumption | Sum of tokens per day | Daily spend |
| D087 | Weekly token consumption | 7-day rolling token sum | Weekly spend |
| D088 | Token growth rate | Daily token trend (slope) | Consumption trajectory |

### D3. Cache Efficiency
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D089 | Cache hit ratio | Cache read / (cache read + input) | Cache effectiveness |
| D090 | Cache creation ratio | Cache creation / total tokens | Cache investment |
| D091 | Cache efficiency score | Cache read / cache creation | ROI on caching |
| D092 | Ephemeral cache usage | Ephemeral tokens / total cache | Short-term caching |
| D093 | Cache savings estimate | Cache read tokens * price differential | Cost savings |

### D4. Cost Estimation
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D094 | Estimated Opus cost | Opus output * $75/M | Opus spending |
| D095 | Estimated Sonnet cost | Sonnet output * $15/M | Sonnet spending |
| D096 | Estimated Haiku cost | Haiku output * $1.25/M | Haiku spending |
| D097 | Total estimated cost | Sum of model costs | Total spending |
| D098 | Cost per session | Total cost / sessions | Per-session cost |
| D099 | Cost per hour | Total cost / active hours | Hourly rate |
| D100 | Cost per day | Daily token costs | Daily spending |
| D101 | Projected monthly cost | Daily avg * 30 | Budget projection |
| D102 | Cost trend | Cost over time (slope) | Spending trajectory |

---

## Category E: Conversation Analysis Metrics

### E1. Message Patterns
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D103 | User/assistant message ratio | User messages / assistant messages | Conversation balance |
| D104 | Average user message length | Mean chars of user messages | User verbosity |
| D105 | Average assistant response length | Mean chars of assistant text | Response verbosity |
| D106 | User message length variance | Std dev of user message lengths | Consistency |
| D107 | Longest user message | Max user message length | Complex requests |
| D108 | Shortest user message | Min user message length (>0) | Quick commands |
| D109 | Messages per session | Total messages / sessions | Session depth |
| D110 | Conversation depth | Max message chain length | Thread complexity |

### E2. Content Classification
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D111 | Questions asked by user | Messages containing "?" | Inquiry rate |
| D112 | Question ratio | Questions / total user messages | Exploration mode |
| D113 | Commands given | Imperative messages ("do X") | Directive mode |
| D114 | Code pastes by user | Messages with ``` or len > 500 | Context provision |
| D115 | Error reports by user | Messages with "error", "traceback" | Debugging frequency |
| D116 | Frustration indicators | "wrong", "still not", "doesn't work" | Pain points |
| D117 | Gratitude expressions | "thanks", "perfect", "great" | Satisfaction |
| D118 | Frustration/gratitude ratio | Frustration / gratitude count | Sentiment balance |

### E3. Topic Analysis
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D119 | Bug-related messages | Messages with bug/error/fix keywords | Debugging work |
| D120 | Feature-related messages | Messages with add/create/implement keywords | Feature work |
| D121 | Refactor-related messages | Messages with refactor/clean/improve | Maintenance work |
| D122 | Test-related messages | Messages with test/pytest/coverage | Testing work |
| D123 | Docs-related messages | Messages with document/readme/comment | Documentation work |
| D124 | Debug-related messages | Messages with debug/why/trace | Investigation work |
| D125 | Review-related messages | Messages with review/check/examine | Review work |
| D126 | Topic distribution | Percentage by topic category | Work focus |
| D127 | Topic trend over time | Topic frequency over sessions | Focus shifts |

---

## Category F: Thinking & Complexity Metrics

### F1. Extended Thinking Analysis
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D128 | Sessions with thinking | Sessions containing thinking blocks / total | Thinking usage |
| D129 | Thinking blocks per session | Thinking block count / sessions | Thinking intensity |
| D130 | Average thinking length | Mean chars of thinking content | Reasoning depth |
| D131 | Median thinking length | Median of thinking lengths | Typical reasoning |
| D132 | Max thinking length | Longest thinking block | Deepest reasoning |
| D133 | Thinking token percentage | Thinking tokens / total output | Reasoning investment |
| D134 | ULTRATHINK trigger count | Triggers with text="ULTRATHINK" | Deep thinking requests |
| D135 | Thinking level distribution | Count by thinkingMetadata.level | Thinking modes |
| D136 | Thinking disabled rate | disabled=true / total | Thinking opt-out |

### F2. Problem Complexity Indicators
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D137 | Thinking length trend | Thinking length over time | Complexity trend |
| D138 | Sidechain exploration rate | isSidechain=true / total | Alternative exploration |
| D139 | Conversation compaction rate | Compaction events / sessions | Long conversation rate |
| D140 | Context clearing frequency | Context management events / sessions | Context pressure |
| D141 | Tokens cleared per compaction | Mean cleared_input_tokens | Context savings |
| D142 | Multi-turn problem rate | Sessions with >20 messages | Complex problems |

---

## Category G: Task Management Metrics

### G1. Todo Completion
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D143 | Total todos created | Sum of all todo items | Task volume |
| D144 | Completed todos | status="completed" count | Completion volume |
| D145 | Overall completion rate | Completed / total todos | Success rate |
| D146 | In-progress (abandoned) | status="in_progress" never completed | Abandonment |
| D147 | Pending (never started) | status="pending" count | Unstarted work |
| D148 | Abandonment rate | In-progress / (completed + in-progress) | Follow-through |
| D149 | Average tasks per session | Todos / sessions with todos | Task granularity |
| D150 | Max tasks in session | Highest todo count in one session | Most complex session |
| D151 | High priority ratio | High priority / total | Urgency level |

### G2. Planning Metrics
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D152 | Plans created | Count of plan files | Planning frequency |
| D153 | Average plan size | Mean plan file size | Plan complexity |
| D154 | Plan complexity score | Headers * code blocks * size | Overall complexity |
| D155 | Technologies per plan | Unique tech keywords per plan | Tech breadth |
| D156 | Action words per plan | Implementation verbs count | Action density |
| D157 | Plan approval rate | ExitPlanMode / EnterPlanMode | Plan acceptance |
| D158 | Planning to execution ratio | Plans / features implemented | Planning overhead |

---

## Category H: Agent & Delegation Metrics

### H1. Subagent Usage
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D159 | Agent sessions | Count of agent-*.jsonl files | Agent usage |
| D160 | Main vs agent ratio | Main sessions / agent sessions | Delegation level |
| D161 | Agent usage percentage | Agent sessions / total | Delegation rate |
| D162 | Subagent type distribution | Count by subagent_type | Agent preferences |
| D163 | Most used subagent | Highest subagent_type count | Primary agent |
| D164 | Explore agent usage | Explore type count | Research delegation |
| D165 | Plan agent usage | Plan type count | Planning delegation |
| D166 | Custom agent usage | Non-built-in agent count | Custom agent adoption |

### H2. Agent Efficiency
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D167 | Tokens per agent task | Agent totalTokens / agent calls | Agent token cost |
| D168 | Tools per agent task | Agent totalToolUseCount / agent calls | Agent tool usage |
| D169 | Agent success rate | Successful agent completions / total | Agent reliability |
| D170 | Agent resume rate | Resume parameter usage / total agents | Continuation rate |
| D171 | Parallel agent frequency | Multiple Task calls in one message | Parallelization |
| D172 | Agent depth | Nested agent spawns | Delegation depth |

---

## Category I: Project Metrics

### I1. Project Activity
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D173 | Total projects | Unique cwd values | Project count |
| D174 | Sessions per project | Session count by cwd | Project activity |
| D175 | Most active project | Highest session count | Primary project |
| D176 | Messages per project | Message count by cwd | Project engagement |
| D177 | Time per project | Active hours by cwd | Project investment |
| D178 | Tools per project | Tool calls by cwd | Project complexity |

### I2. Git Activity
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D179 | Branches worked on | Unique gitBranch values | Branch diversity |
| D180 | Main/master activity | Activity on main branches | Core work |
| D181 | Feature branch activity | Activity on non-main branches | Feature work |
| D182 | Branch switching frequency | Branch changes per session | Context switching |
| D183 | Empty branch sessions | gitBranch="" count | Untracked work |

### I3. Project Complexity
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D184 | Files per project | Unique files by project | Project scope |
| D185 | Tool diversity per project | Unique tools by project | Work variety |
| D186 | Session depth per project | Avg messages per session by project | Engagement depth |
| D187 | Multi-project sessions | Sessions spanning multiple cwd | Cross-project work |
| D188 | Project switching frequency | cwd changes per day | Project juggling |

---

## Category J: Error & Recovery Metrics

### J1. Error Rates
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D189 | Overall error rate | Errors / total tool calls | Reliability |
| D190 | Bash error rate | Bash errors / Bash calls | Command reliability |
| D191 | Edit conflict rate | Edit errors / Edit calls | Edit reliability |
| D192 | Read failure rate | Read errors / Read calls | File access issues |
| D193 | Permission error rate | Permission errors / total | Access issues |
| D194 | API error rate | isApiErrorMessage / total | API reliability |

### J2. Recovery Patterns
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D195 | Error recovery rate | Errors followed by success / errors | Recovery ability |
| D196 | Retry success rate | Successful retries / total retries | Retry effectiveness |
| D197 | Errors per session | Total errors / sessions | Session reliability |
| D198 | Error clustering | Sessions with multiple errors | Problem sessions |
| D199 | Time to recovery | Time from error to success | Recovery speed |

### J3. Interruption Metrics
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D200 | Interrupted operations | interrupted=true count | Interruption rate |
| D201 | Truncated outputs | truncated=true count | Output limits hit |
| D202 | Killed shells | KillShell count | Manual interrupts |
| D203 | Hook prevention rate | preventedContinuation / hook executions | Hook blocking |

---

## Category K: Code Generation Metrics

### K1. Code Volume
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D204 | Total code generated (KB) | Sum of code block sizes | Code volume |
| D205 | Code blocks generated | Count of ``` blocks | Code frequency |
| D206 | Average code block size | Mean block size | Typical code size |
| D207 | Largest code block | Max block size | Biggest generation |
| D208 | Code per session | Code KB / sessions | Session output |
| D209 | Code per hour | Code KB / active hours | Code velocity |

### K2. Language Distribution
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D210 | Python code ratio | Python blocks / total | Python focus |
| D211 | JavaScript code ratio | JS blocks / total | JS focus |
| D212 | TypeScript code ratio | TS blocks / total | TS focus |
| D213 | Bash code ratio | Bash blocks / total | Scripting focus |
| D214 | JSON code ratio | JSON blocks / total | Data focus |
| D215 | Markdown code ratio | MD blocks / total | Docs focus |
| D216 | Language diversity | Unique languages used | Language breadth |

### K3. Code Quality Proxies
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D217 | Functions defined | def/function pattern matches | Function creation |
| D218 | Classes defined | class pattern matches | Class creation |
| D219 | Functions per session | Functions / sessions | Session complexity |
| D220 | Classes per session | Classes / sessions | OOP usage |
| D221 | Import statements | import/require matches | Dependency usage |
| D222 | Comment density | Comment lines / code lines | Documentation |
| D223 | Docstring presence | Docstring patterns / functions | Documentation rate |

### K4. Edit Analysis
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D224 | Net lines added | Lines in new_string - old_string | Code growth |
| D225 | Net lines removed | Lines in old_string - new_string | Code reduction |
| D226 | Code churn | Added + removed lines | Change volume |
| D227 | Replace all usage | replace_all=true count | Bulk changes |
| D228 | Average edit size | Mean (new_string - old_string) size | Edit granularity |

---

## Category L: Web Research Metrics

### L1. Search Patterns
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D229 | Web searches per session | WebSearch / sessions | Research intensity |
| D230 | Web fetches per session | WebFetch / sessions | Documentation access |
| D231 | Research intensity | (Search + Fetch) / session | Overall research |
| D232 | External dependency | Web tools / total tools | External reliance |
| D233 | Search topics | Query keyword extraction | Research areas |

### L2. Domain Analysis
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D234 | Documentation site ratio | docs.* fetches / total | Official docs usage |
| D235 | GitHub ratio | github.com fetches / total | GitHub reliance |
| D236 | Stack Overflow ratio | stackoverflow.com / total | Community help |
| D237 | Domain diversity | Unique domains fetched | Source variety |
| D238 | Most accessed domain | Highest fetch count domain | Primary source |

---

## Category M: Hook & Customization Metrics

### M1. Hook Usage
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D239 | Sessions with hooks | hookCount > 0 sessions | Hook adoption |
| D240 | Average hooks per session | Mean hookCount | Hook intensity |
| D241 | Hook error rate | hookErrors count / total hooks | Hook reliability |
| D242 | Hook prevention rate | preventedContinuation / hooks | Blocking hooks |
| D243 | Unique hook commands | Distinct hookInfos.command | Hook variety |

### M2. Customization Level
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D244 | Custom agents defined | Count of agents/*.md | Agent customization |
| D245 | Custom commands defined | Count of commands/*.md | Command customization |
| D246 | Custom skills defined | Count of skills/*/ | Skill customization |
| D247 | Total customizations | Agents + commands + skills | Customization level |
| D248 | Permission rules defined | Count of allow/deny rules | Security config |
| D249 | Auto-allow rules | Allow rules count | Automation level |

---

## Category N: User Interaction Metrics

### N1. Question/Answer Analysis
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D250 | Questions asked by Claude | AskUserQuestion count | Clarification needs |
| D251 | Questions per session | AskUserQuestion / sessions | Interaction rate |
| D252 | Multi-select questions | multiSelect=true count | Complex choices |
| D253 | Unique question topics | Distinct question headers | Decision areas |
| D254 | Most common decisions | Frequent question patterns | Key decision points |
| D255 | Answer capture rate | Questions with answers / total | Response rate |

### N2. User Decision Patterns
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D256 | "Yes" response rate | Affirmative answers / total | Approval rate |
| D257 | "Other" response rate | Custom answers / total | Custom choices |
| D258 | First option selection rate | First option chosen / total | Default acceptance |
| D259 | Decision time estimate | Time before answer / questions | Decision speed |

---

## Category O: Advanced Derived Metrics

### O1. Productivity Scores
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D260 | Focus score | Deep sessions (>30min) / total | Deep work ratio |
| D261 | Iteration index | Avg file versions per task | Perfectionism measure |
| D262 | Self-sufficiency ratio | Tasks without errors / total | Independence |
| D263 | Code velocity | KB generated per active hour | Output speed |
| D264 | Pair programming score | Message density per session | Interaction intensity |
| D265 | Context efficiency | Cache hits / total context | Memory efficiency |

### O2. Quality Indicators
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D266 | Documentation debt ratio | Code generated / docs generated | Docs balance |
| D267 | Test coverage proxy | Test file touches / code file touches | Testing culture |
| D268 | Refactoring frequency | Refactor messages / total | Maintenance habit |
| D269 | Code review engagement | Review messages / total | Review culture |
| D270 | Error learning curve | Error rate trend over time | Skill improvement |

### O3. Behavioral Patterns
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D271 | Consistency score | 1 - (std dev daily activity / mean) | Regularity |
| D272 | Deep work ratio | Sessions >1hr / total sessions | Focus time |
| D273 | Context switching rate | Project changes per hour | Multitasking |
| D274 | Burnout indicators | Late night + high activity + declining | Health warning |
| D275 | Flow state indicator | Long sessions + low errors + high output | Optimal state |

### O4. Comparative Metrics
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D276 | Week-over-week message change | (This week - last week) / last week | Trend |
| D277 | Week-over-week session change | Session count comparison | Trend |
| D278 | Week-over-week tool change | Tool usage comparison | Trend |
| D279 | Week-over-week cost change | Cost comparison | Trend |
| D280 | Month-over-month growth | Monthly activity comparison | Growth |

### O5. Predictive Metrics
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D281 | Projected monthly tokens | Daily avg * 30 | Budget forecast |
| D282 | Projected monthly cost | Daily cost avg * 30 | Cost forecast |
| D283 | Session completion likelihood | Historical completion rate | Success prediction |
| D284 | Error probability | Error rate trends | Risk assessment |
| D285 | Feature adoption score | New tools used / available | Adoption prediction |

---

## Category P: Cross-Reference Metrics

### P1. Tool-to-Outcome Mapping
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D286 | Search-to-implementation ratio | Code after WebSearch / searches | Research effectiveness |
| D287 | Plan-to-completion ratio | Completed plans / created plans | Planning effectiveness |
| D288 | Agent-to-outcome ratio | Successful agent results / spawns | Agent effectiveness |
| D289 | Read-to-edit ratio | Edits after reads / reads | Read utilization |
| D290 | Error-to-recovery time | Avg time from error to success | Recovery efficiency |

### P2. Session Classification
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D291 | Debugging sessions | Sessions with high error messages | Session typing |
| D292 | Feature sessions | Sessions with create/implement | Session typing |
| D293 | Research sessions | Sessions with high WebSearch | Session typing |
| D294 | Refactoring sessions | Sessions with refactor keywords | Session typing |
| D295 | Documentation sessions | Sessions with high .md touches | Session typing |

### P3. Efficiency Correlations
| # | Metric | Calculation | Use Case |
|---|--------|-------------|----------|
| D296 | Thinking-to-success correlation | Success rate vs thinking usage | Thinking value |
| D297 | Planning-to-completion correlation | Completion vs planning usage | Planning value |
| D298 | Agent-to-speed correlation | Time saved with agents | Agent value |
| D299 | Cache-to-cost correlation | Cost reduction vs cache usage | Cache value |
| D300 | Error-to-time correlation | Time impact of errors | Error cost |

---

## Summary Statistics

| Category | Count | Description |
|----------|-------|-------------|
| A. Time & Productivity | 28 | Active hours, patterns, streaks |
| B. Tool Usage | 20 | Frequency, efficiency, co-occurrence |
| C. File Operations | 25 | Access, types, revisions, coupling |
| D. Model & Tokens | 29 | Usage, economics, cache, cost |
| E. Conversation | 27 | Messages, content, topics |
| F. Thinking & Complexity | 15 | Extended thinking, complexity |
| G. Task Management | 16 | Todos, planning |
| H. Agent & Delegation | 14 | Subagent usage, efficiency |
| I. Project | 16 | Activity, git, complexity |
| J. Error & Recovery | 15 | Rates, patterns, interruptions |
| K. Code Generation | 25 | Volume, languages, quality |
| L. Web Research | 10 | Search, domains |
| M. Hook & Customization | 11 | Hooks, customization |
| N. User Interaction | 10 | Questions, decisions |
| O. Advanced Derived | 25 | Productivity, quality, behavioral, predictive |
| P. Cross-Reference | 15 | Mappings, classifications, correlations |
| **TOTAL** | **300** | **Derived metrics** |

---

## Grand Total

| Type | Count |
|------|-------|
| Raw data sources | 16+ |
| Raw field paths | 339 |
| Total field paths (with file backups) | 4,234+ |
| Direct extractable metrics | 322 |
| Derived/computed metrics | 300 |
| **TOTAL METRICS** | **622+** |


---

# PART 6: DATA TYPES & FORMATS REFERENCE

This section provides precise format specifications, type definitions, enum values, and examples for all data fields.

---

## 1. Primitive Types

### String Formats

| Format Name | Pattern | Example | Fields Using |
|-------------|---------|---------|--------------|
| `uuid` | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` | `"7e8f679d-e4be-4764-a696-85785cdf23e8"` | uuid, parentUuid, sessionId, messageId, leafUuid |
| `short_id` | `[a-f0-9]{6,8}` | `"ba912b75"` | agentId, bash_id, shell_id |
| `iso_datetime` | `YYYY-MM-DDTHH:MM:SS.sssZ` | `"2025-12-12T18:27:04.423Z"` | timestamp (in sessions), snapshot.timestamp |
| `iso_date` | `YYYY-MM-DD` | `"2025-12-12"` | dailyActivity[].date, lastComputedDate |
| `file_path` | Absolute POSIX path | `"/mnt/c/python/project/file.py"` | cwd, file_path, path |
| `url` | Full URL with protocol | `"https://docs.anthropic.com/..."` | input.url |
| `model_id` | `claude-{tier}-{version}-{date}` | `"claude-opus-4-5-20251101"` | message.model |
| `request_id` | `req_[A-Za-z0-9]{24}` | `"req_011CVFtYSbevvEUqrbMpYxcJ"` | requestId |
| `tool_use_id` | `toolu_[A-Za-z0-9]{24}` | `"toolu_01H76ykEFeah4RKfXMcoqPrA"` | message.content[].id, tool_use_id |
| `message_id` | `msg_[A-Za-z0-9]{24}` | `"msg_01S52ewqVpyRqKCEvXZbW1wB"` | message.id |
| `backup_file` | `[a-f0-9]{16}@v[0-9]+` | `"d801d63c5ca66400@v1"` | backupFileName |
| `slug` | `adjective-verb-noun` | `"wild-meandering-sonnet"` | slug |
| `base64` | Base64-encoded binary | `"iVBORw0KGgoAAAANSUhEU..."` | source.data |
| `glob_pattern` | Shell glob syntax | `"**/*.py"`, `"*.{ts,tsx}"` | input.pattern (Glob), input.glob |
| `regex_pattern` | Rust regex syntax | `"def\\s+\\w+"`, `"[Kk]osmos"` | input.pattern (Grep) |

### Numeric Formats

| Format Name | Type | Range | Unit | Example | Fields Using |
|-------------|------|-------|------|---------|--------------|
| `unix_ms` | int | 0 - 2^53 | milliseconds since epoch | `1765613453279` | history.jsonl timestamp |
| `unix_s` | int | 0 - 2^32 | seconds since epoch | `1733000000` | (rare) |
| `duration_ms` | int | 0 - 600000 | milliseconds | `15234` | durationMs, totalDurationMs, timeout |
| `token_count` | int | 0 - ~200000 | tokens | `158`, `10954` | input_tokens, output_tokens, etc. |
| `line_number` | int | 1 - ~1000000 | 1-indexed | `185` | offset, limit, startLine |
| `version_num` | int | 1 - ~100 | sequential | `5` | snapshot version |
| `hour_24` | int | 0 - 23 | hour of day | `14` | hourCounts keys |
| `count` | int | 0 - ~1000000 | items | `67155` | messageCount, sessionCount, etc. |
| `cost_usd` | float | 0.0 - ~1000.0 | USD | `0.0` | cost_usd (currently always 0) |

### Boolean Values

| Value | Meaning | Fields Using |
|-------|---------|--------------|
| `true` | Affirmative | isSidechain, isSnapshotUpdate, is_error, interrupted, etc. |
| `false` | Negative | Same fields |

---

## 2. Enum Types (All Possible Values)

### Message Types
```
type: "user" | "assistant" | "file-history-snapshot"
```

### User Types
```
userType: "external"   # Human user
        | "internal"   # Agent/subagent
```

### Message Roles
```
message.role: "user" | "assistant"
```

### Stop Reasons
```
message.stop_reason: "end_turn"      # Normal completion
                   | "tool_use"      # Stopped to use a tool
                   | "max_tokens"    # Hit token limit
                   | null            # In progress or error
```

### Todo Status
```
status: "pending"      # Not started
      | "in_progress"  # Currently working
      | "completed"    # Finished
```

### Todo Priority
```
priority: "high" | "medium" | "low"
```

### Tool Names
```
name: "Bash"
    | "Read"
    | "Edit"
    | "Write"
    | "Glob"
    | "Grep"
    | "Task"
    | "TaskOutput"
    | "TodoWrite"
    | "WebFetch"
    | "WebSearch"
    | "AskUserQuestion"
    | "EnterPlanMode"
    | "ExitPlanMode"
    | "KillShell"
    | "Skill"
    | "SlashCommand"
    | "NotebookEdit"
    | "StructuredOutput"
    | "BashOutput"
    | "mcp__*"          # MCP tool prefix
```

### Subagent Types
```
subagent_type: "Explore"
             | "Plan"
             | "claude-code-guide"
             | "statusline-setup"
             | "general-purpose"
             | "parallel-setup"
             | "parallel-monitor"
             | "parallel-integrate"
             | "repo_architect"
             | "adversarial-generator"
             | "adversarial-validator"
             | "adversarial-orchestrator"
             | (custom agent names)
```

### Model IDs
```
message.model: "claude-opus-4-5-20251101"
             | "claude-sonnet-4-5-20250929"
             | "claude-haiku-4-5-20251001"
             | "claude-opus-4-1-20250805"
             | "<synthetic>"              # Internal/synthetic
```

### Grep Output Modes
```
output_mode: "content"            # Show matching lines
           | "files_with_matches" # Show file paths only
           | "count"              # Show match counts
```

### Thinking Levels
```
thinkingMetadata.level: "high"
                      | "none"
                      | "low"
                      | "medium"
```

### Compaction Triggers
```
compactMetadata.trigger: "manual"  # User triggered
                       | "auto"    # Automatic
```

### Operation Types
```
operation: "enqueue" | "remove"
```

### Message Subtypes
```
subtype: "compact_boundary"
       | "local_command"
```

### Log Levels
```
level: "info" | "suggestion" | "warning" | "error"
```

### Error Types
```
error: "invalid_request"
     | "unknown"
     | "rate_limit"
     | "server_error"
```

### Service Tiers
```
message.usage.service_tier: "standard"
                          | null
```

### Media Types
```
source.media_type: "image/png"
                 | "image/jpeg"
                 | "image/gif"
                 | "image/webp"
                 | "application/pdf"
```

### Source Types
```
source.type: "base64"
```

### Context Edit Types
```
applied_edits[].type: "clear_thinking_20251015"
```

---

## 3. Complex Object Schemas

### Tool Use Object
```typescript
{
  type: "tool_use",
  id: string,           // toolu_xxx format
  name: string,         // Tool name enum
  input: {              // Varies by tool - see Tool Input Schemas
    [key: string]: any
  }
}
```

### Tool Result Object
```typescript
{
  type: "tool_result",
  tool_use_id: string,  // Matches tool_use.id
  content: string | ContentBlock[],
  is_error: boolean
}
```

### Thinking Block
```typescript
{
  type: "thinking",
  thinking: string,     // Extended thinking content
  signature: string     // Verification signature
}
```

### Text Block
```typescript
{
  type: "text",
  text: string          // Response text
}
```

### Usage Object
```typescript
{
  input_tokens: number,
  output_tokens: number,
  cache_read_input_tokens: number,
  cache_creation_input_tokens: number,
  cache_creation: {
    ephemeral_1h_input_tokens: number,
    ephemeral_5m_input_tokens: number
  },
  service_tier: string | null,
  server_tool_use?: {
    web_fetch_requests: number,
    web_search_requests: number
  }
}
```

### File Backup Object
```typescript
{
  backupFileName: string | null,  // hash@version or null if not backed up
  backupTime: string,             // ISO datetime
  version: number                 // 1, 2, 3...
}
```

### Hook Info Object
```typescript
{
  command: string       // Full shell command executed
}
```

### Question Object (AskUserQuestion)
```typescript
{
  question: string,     // Full question text
  header: string,       // Short label (≤12 chars)
  multiSelect: boolean, // Allow multiple selections
  options: Array<{
    label: string,      // Option text
    description: string // Option explanation
  }>
}
```

### Structured Patch Object
```typescript
{
  oldStart: number,     // Starting line in old file
  oldLines: number,     // Lines in old version
  newStart: number,     // Starting line in new file
  newLines: number,     // Lines in new version
  lines: string[]       // Diff lines with +/- prefixes
}
```

---

## 4. Nullable Fields

Fields that can be `null`:

| Field | When Null |
|-------|-----------|
| `parentUuid` | First message in session (root) |
| `message.stop_reason` | Message in progress or errored |
| `message.stop_sequence` | No stop sequence triggered |
| `message.container` | Reserved/not used |
| `message.context_management` | No context optimization applied |
| `message.usage.service_tier` | Not specified |
| `backupFileName` | File not yet backed up |
| `originalFile` | New file (no original) |
| `toolUseResult.originalFile` | New file creation |

---

## 5. Array Field Specifications

| Field | Item Type | Typical Length | Max Observed |
|-------|-----------|----------------|--------------|
| `dailyActivity[]` | DailyActivity | 30-365 | ~365 |
| `dailyModelTokens[]` | DailyTokens | 30-365 | ~365 |
| `message.content[]` | ContentBlock | 1-50 | ~200 |
| `todos[]` | Todo | 0-20 | ~50 |
| `hookInfos[]` | HookInfo | 0-5 | ~10 |
| `hookErrors[]` | string | 0-5 | ~10 |
| `questions[]` | Question | 1-4 | 4 |
| `options[]` | Option | 2-4 | 4 |
| `applied_edits[]` | Edit | 0-10 | ~50 |
| `triggers[]` | Trigger | 0-5 | ~10 |
| `structuredPatch[]` | Patch | 1-20 | ~100 |

---

## 6. Size Constraints

| Field | Min | Max | Unit |
|-------|-----|-----|------|
| `question` text | 10 | 500 | chars |
| `header` | 1 | 12 | chars |
| `description` | 1 | 200 | chars |
| `label` | 1 | 50 | chars |
| `command` (Bash) | 1 | 10000 | chars |
| `content` (Write) | 0 | 1000000 | chars |
| `pattern` (Grep) | 1 | 1000 | chars |
| `thinking` | 0 | 65000 | chars |
| `text` | 0 | 100000 | chars |
| `timeout` | 1000 | 600000 | ms |
| `limit` (Read) | 1 | 10000 | lines |
| `offset` (Read) | 0 | 1000000 | lines |
| `-A`, `-B`, `-C` | 0 | 100 | lines |
| `head_limit` | 1 | 10000 | results |

---

## 7. File Format Specifications

### JSONL Files (history.jsonl, session files)
```
Format: JSON Lines (newline-delimited JSON)
Encoding: UTF-8
Line terminator: LF (\n)
Each line: Valid JSON object
Max line length: ~10MB (observed up to 5MB)
```

### JSON Files (settings.json, todos, stats-cache)
```
Format: Standard JSON
Encoding: UTF-8
Pretty-printed: Yes (2-space indent)
```

### SQLite Database (__store.db)
```
SQLite version: 3.x
Encoding: UTF-8
Tables: 5 (see schema in Part 1)
```

### Markdown Files (plans, agents, commands, skills)
```
Format: GitHub-Flavored Markdown
Encoding: UTF-8
```

### Debug Logs (debug/*.txt)
```
Format: Timestamped log lines
Pattern: YYYY-MM-DDTHH:MM:SS.mmmZ [LEVEL] Message
Encoding: UTF-8
```

### Shell Snapshots
```
Format: Bash script
Encoding: UTF-8
Contains: Base64-encoded functions, shopt settings
```

### File History Backups
```
Naming: <16-char-hex-hash>@v<version-number>
Content: Raw file content (any encoding)
Permissions: Preserved from original
```

---

## 8. Timestamp Reference

| Source | Field | Format | Timezone | Precision |
|--------|-------|--------|----------|-----------|
| history.jsonl | timestamp | Unix ms (int) | Local | Milliseconds |
| session files | timestamp | ISO 8601 (str) | UTC | Milliseconds |
| stats-cache | firstSessionDate | ISO 8601 | UTC | Milliseconds |
| stats-cache | longestSession.timestamp | ISO 8601 | UTC | Milliseconds |
| stats-cache | dailyActivity[].date | ISO date | UTC | Day |
| snapshot | timestamp | ISO 8601 | UTC | Milliseconds |
| backup | backupTime | ISO 8601 | UTC | Milliseconds |
| debug logs | prefix | ISO 8601 | UTC | Milliseconds |
| __store.db | timestamp | Unix ms (int) | UTC | Milliseconds |

### Timestamp Conversion Examples
```python
# history.jsonl (Unix ms) to datetime
from datetime import datetime
ts = 1765613453279
dt = datetime.fromtimestamp(ts / 1000)  # Local time
dt_utc = datetime.utcfromtimestamp(ts / 1000)  # UTC

# ISO string to datetime
from datetime import datetime
iso = "2025-12-12T18:27:04.423Z"
dt = datetime.fromisoformat(iso.replace('Z', '+00:00'))
```

---

## 9. Data Relationships

### Primary Keys
| Table/File | Primary Key |
|------------|-------------|
| base_messages | uuid |
| user_messages | uuid |
| assistant_messages | uuid |
| conversation_summaries | leaf_uuid |
| Session files | uuid (per entry) |
| Todo files | session-agent ID (filename) |
| Plan files | slug (filename) |

### Foreign Keys / References
| From | To | Relationship |
|------|----|--------------| 
| parentUuid | uuid | Message threading |
| tool_use_id | message.content[].id | Tool result → tool call |
| sessionId | Session filename | Message → session |
| agentId | Agent session file | Agent reference |
| backupFileName | file-history file | Backup reference |
| leaf_uuid | uuid | Summary → latest message |

### Hierarchies
```
Session
└── Messages (linked by parentUuid)
    ├── User message
    │   └── Content (text)
    └── Assistant message
        └── Content blocks
            ├── Thinking block
            ├── Text block
            ├── Tool use block
            └── Tool result block
```

---

## 10. Example Records

### Complete User Message Entry
```json
{
  "uuid": "67d93b26-dbb6-468a-894a-fdb7e904ac91",
  "parentUuid": null,
  "sessionId": "2496bf3b-a7a4-4a69-948e-e9859541610a",
  "timestamp": "2025-12-13T10:10:53.735Z",
  "type": "user",
  "cwd": "/mnt/c/python/claude-hooks-manager",
  "userType": "external",
  "version": "2.0.69",
  "gitBranch": "master",
  "isSidechain": false,
  "message": {
    "role": "user",
    "content": "What metrics can we extract from Claude Code data?"
  }
}
```

### Complete Assistant Message Entry
```json
{
  "uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "parentUuid": "67d93b26-dbb6-468a-894a-fdb7e904ac91",
  "sessionId": "2496bf3b-a7a4-4a69-948e-e9859541610a",
  "timestamp": "2025-12-13T10:11:15.234Z",
  "type": "assistant",
  "cwd": "/mnt/c/python/claude-hooks-manager",
  "userType": "external",
  "version": "2.0.69",
  "gitBranch": "master",
  "isSidechain": false,
  "requestId": "req_011CVFtYSbevvEUqrbMpYxcJ",
  "thinkingMetadata": {
    "level": "high",
    "disabled": false,
    "triggers": []
  },
  "message": {
    "id": "msg_01S52ewqVpyRqKCEvXZbW1wB",
    "type": "message",
    "role": "assistant",
    "model": "claude-opus-4-5-20251101",
    "stop_reason": "end_turn",
    "stop_sequence": null,
    "content": [
      {
        "type": "thinking",
        "thinking": "Let me analyze the available data sources...",
        "signature": "EsIGCkYIChgCKkAnYw0w1aXG..."
      },
      {
        "type": "text",
        "text": "I can extract numerous metrics from Claude Code's local data..."
      }
    ],
    "usage": {
      "input_tokens": 1500,
      "output_tokens": 850,
      "cache_read_input_tokens": 45000,
      "cache_creation_input_tokens": 0,
      "cache_creation": {
        "ephemeral_1h_input_tokens": 0,
        "ephemeral_5m_input_tokens": 0
      },
      "service_tier": "standard"
    }
  }
}
```

### Complete Tool Use Entry
```json
{
  "type": "tool_use",
  "id": "toolu_01H76ykEFeah4RKfXMcoqPrA",
  "name": "Read",
  "input": {
    "file_path": "/mnt/c/python/project/src/main.py",
    "offset": 1,
    "limit": 100
  }
}
```

### Complete Tool Result Entry
```json
{
  "toolUseResult": {
    "type": "success",
    "status": "success",
    "file": {
      "filePath": "/mnt/c/python/project/src/main.py",
      "content": "#!/usr/bin/env python3\n\ndef main():\n    print('Hello')\n",
      "numLines": 4,
      "startLine": 1,
      "totalLines": 4
    },
    "isImage": false,
    "durationMs": 15,
    "totalDurationMs": 23,
    "truncated": false,
    "interrupted": false
  }
}
```

### Complete Stats Cache Entry
```json
{
  "version": 1,
  "lastComputedDate": "2025-12-12",
  "dailyActivity": [
    {
      "date": "2025-12-12",
      "messageCount": 2283,
      "sessionCount": 15,
      "toolCallCount": 638
    }
  ],
  "dailyModelTokens": [
    {
      "date": "2025-12-12",
      "tokensByModel": {
        "claude-opus-4-5-20251101": 306529
      }
    }
  ],
  "modelUsage": {
    "claude-opus-4-5-20251101": {
      "inputTokens": 1323946,
      "outputTokens": 4392800,
      "cacheReadInputTokens": 2088483094,
      "cacheCreationInputTokens": 133285299,
      "webSearchRequests": 0,
      "costUSD": 0,
      "contextWindow": 0
    }
  },
  "totalSessions": 1513,
  "totalMessages": 67155,
  "hourCounts": {
    "0": 61, "1": 55, "2": 32, "13": 168, "14": 177, "21": 278, "22": 115, "23": 300
  },
  "longestSession": {
    "sessionId": "b8421125-9602-4f2c-969e-cb47e6e47599",
    "duration": 510062881,
    "messageCount": 6113,
    "timestamp": "2025-11-07T05:12:31.430Z"
  },
  "firstSessionDate": "2025-11-06T20:18:40.075Z"
}
```


---

# PART 7: ADDITIONAL DATA SOURCES (Previously Missed)

Deep audit revealed several significant data sources not in the original catalog.

---

## 17. `~/.claude.json` (Global State)
**Purpose:** Global Claude Code state and per-project statistics
**Size:** ~50-200 KB (grows with projects)
**Critical:** Contains extensive per-project metrics!

### Global Fields:
```
numStartups                               [int]      - Total times Claude Code started (e.g., 292)
installMethod                             [str]      - "native" | "npm" | etc.
autoUpdates                               [bool]     - Auto-update enabled
verbose                                   [bool]     - Verbose mode
autoCompactEnabled                        [bool]     - Auto-compact conversations

hasSeenTasksHint                          [bool]     - UI hint tracking
hasSeenStashHint                          [bool]     - UI hint tracking
hasCompletedOnboarding                    [bool]     - Onboarding status
lastOnboardingVersion                     [str]      - Version when onboarded (e.g., "2.0.67")

memoryUsageCount                          [int]      - Memory feature usage
promptQueueUseCount                       [int]      - Prompt queue usage (e.g., 195)

userID                                    [str]      - Hashed user identifier (64 chars)
```

### Tips History (Feature Discovery Tracking):
```
tipsHistory                               [dict]     - Tip name → times shown
  .new-user-warmup                        [int]      
  .plan-mode-for-complex-tasks            [int]      
  .terminal-setup                         [int]      
  .theme-command                          [int]      
  .status-line                            [int]      
  .prompt-queue                           [int]      
  .todo-list                              [int]      
  .install-github-app                     [int]      
  .permissions                            [int]      
  .drag-and-drop-images                   [int]      
  .double-esc                             [int]      
  .continue                               [int]      
  .custom-commands                        [int]      
  .shift-tab                              [int]      
  .image-paste                            [int]      
  .custom-agents                          [int]      
  .git-worktrees                          [int]      
  .tab-toggle-thinking                    [int]      
  .ultrathink-keyword                     [int]      
  .stickers-command                       [int]      
  .rename-conversation                    [int]      
  .config-thinking-mode                   [int]      
  .frontend-design-plugin                 [int]      
  # ... more tips
```

### Custom API Key Responses:
```
customApiKeyResponses                     [dict]
  .approved                               [list]     - Approved API keys
  .rejected                               [list]     - Rejected API keys
```

### Feature Flags (Cached):
```
cachedStatsigGates                        [dict]     - Feature flag states
  .tengu_disable_bypass_permissions_mode  [bool]
  .tengu_use_file_checkpoints             [bool]
  .tengu_web_tasks                        [bool]
  .tengu_glob_with_rg                     [bool]
  .tengu_halloween                        [bool]     
  .tengu_sumi                             [bool]
  .tengu_thinkback                        [bool]
  # ... many more feature flags

cachedDynamicConfigs                      [dict]     - Dynamic config values
  .tengu-top-of-feed-tip                  [dict]
    .tip                                  [str]
    .color                                [str]
```

### Model Configuration:
```
statsigModel                              [dict]     - Model mappings by provider
  .bedrock                                [str]      - AWS Bedrock model ID
  .vertex                                 [str]      - GCP Vertex model ID  
  .firstParty                             [str]      - Anthropic API model ID
```

### Per-Project Statistics (MAJOR):
```
projects                                  [dict]     - Project path → project data
  .<project_path>                         [dict]

    # Trust & Permissions
    .allowedTools                         [list]     - Project-specific allowed tools
    .hasTrustDialogAccepted               [bool]     - Trust dialog accepted
    .dontCrawlDirectory                   [bool]     - Skip directory crawling

    # MCP Configuration
    .mcpServers                           [dict]     - MCP server configs
    .mcpContextUris                       [list]     - MCP context URIs
    .enabledMcpjsonServers                [list]     - Enabled MCP JSON servers
    .disabledMcpjsonServers               [list]     - Disabled MCP JSON servers
    .enableAllProjectMcpServers           [bool]     - Enable all project MCP

    # Onboarding
    .projectOnboardingSeenCount           [int]      - Times onboarding shown
    .hasCompletedProjectOnboarding        [bool]     - Onboarding completed

    # Example Files (Auto-discovered)
    .exampleFiles                         [list]     - Discovered example files
    .exampleFilesGeneratedAt              [int]      - Unix ms when generated

    # Ignore Patterns
    .ignorePatterns                       [list]     - Custom ignore patterns

    # Claude.md Handling
    .hasClaudeMdExternalIncludesApproved  [bool]     - External includes approved
    .hasClaudeMdExternalIncludesWarningShown [bool]  - Warning shown

    # React Vulnerability Detection
    .reactVulnerabilityCache              [dict]
      .detected                           [bool]
      .package                            [str|null]
      .packageName                        [str|null]
      .version                            [str|null]
      .packageManager                     [str|null]

    # Last Session Statistics (PER PROJECT!)
    .lastSessionId                        [str]      - Last session UUID
    .lastCost                             [float]    - Last session cost USD
    .lastAPIDuration                      [int]      - Last API duration ms
    .lastAPIDurationWithoutRetries        [int]      - API duration excluding retries
    .lastToolDuration                     [int]      - Tool execution time ms
    .lastDuration                         [int]      - Total session duration ms
    .lastLinesAdded                       [int]      - Lines added in last session
    .lastLinesRemoved                     [int]      - Lines removed in last session
    .lastTotalInputTokens                 [int]      - Input tokens
    .lastTotalOutputTokens                [int]      - Output tokens
    .lastTotalCacheCreationInputTokens    [int]      - Cache creation tokens
    .lastTotalCacheReadInputTokens        [int]      - Cache read tokens
    .lastTotalWebSearchRequests           [int]      - Web searches

    # Last Session Model Breakdown (PER MODEL!)
    .lastModelUsage                       [dict]     - Model → usage stats
      .<model_id>                         [dict]
        .inputTokens                      [int]
        .outputTokens                     [int]
        .cacheReadInputTokens             [int]
        .cacheCreationInputTokens         [int]
        .webSearchRequests                [int]
        .costUSD                          [float]
```

---

## 18. `~/.claude/.credentials.json`
**Purpose:** OAuth authentication tokens
**Size:** ~0.5 KB
**Sensitivity:** HIGH - contains tokens

### Schema:
```
claudeAiOauth                             [dict]
  .accessToken                            [str]      - OAuth access token
  .refreshToken                           [str]      - OAuth refresh token
  .expiresAt                              [int]      - Expiration Unix ms
  .scopes                                 [list]     - Granted scopes
    - "user:inference"
    - "user:profile"  
    - "user:sessions:claude_code"
  .subscriptionType                       [str]      - "max" | "pro" | "free"
  .rateLimitTier                          [str]      - Rate limit tier name
```

---

## 19. `~/.config/claude/claude_code_config.json`
**Purpose:** System-level MCP configuration
**Size:** ~0.2 KB

### Schema:
```
mcpServers                                [dict]     - Global MCP servers
  .<server_name>                          [dict]
    .command                              [str]      - Server command
    .args                                 [list]     - Command arguments
```

---

## 20. `~/.claude/settings.local.json`
**Purpose:** Local settings overrides
**Size:** ~0.1 KB

### Schema:
```
enableAllProjectMcpServers                [bool]     - Global MCP toggle
# Other local overrides
```

---

## 21. `~/.local/share/claude/versions/`
**Purpose:** Installed Claude Code versions
**Size:** ~1.4 GB total

### Contents:
```
<version_number>                          [file]     - Executable binary
  - Filename: Version string (e.g., "2.0.69")
  - Size: ~200-210 MB each
  - Permissions: Executable
  - Timestamp: Installation date
```

---

## Additional Metrics from New Sources

### Startup & Usage Metrics
| # | Metric | Source | Calculation |
|---|--------|--------|-------------|
| D301 | Total startups | ~/.claude.json | numStartups |
| D302 | Prompt queue usage | ~/.claude.json | promptQueueUseCount |
| D303 | Memory feature usage | ~/.claude.json | memoryUsageCount |
| D304 | Onboarding completion | ~/.claude.json | hasCompletedOnboarding |

### Feature Discovery Metrics
| # | Metric | Source | Calculation |
|---|--------|--------|-------------|
| D305 | Tips seen | ~/.claude.json | Count of tipsHistory keys |
| D306 | Feature discovery rate | ~/.claude.json | Tips seen / available tips |
| D307 | Most shown tip | ~/.claude.json | Max value in tipsHistory |
| D308 | Tip exposure ratio | ~/.claude.json | Total tip shows / startups |

### Feature Flag Metrics
| # | Metric | Source | Calculation |
|---|--------|--------|-------------|
| D309 | Enabled feature flags | ~/.claude.json | Count true in cachedStatsigGates |
| D310 | Feature flag ratio | ~/.claude.json | Enabled / total flags |

### Per-Project Metrics (NEW - Very Valuable!)
| # | Metric | Source | Calculation |
|---|--------|--------|-------------|
| D311 | Total projects tracked | ~/.claude.json | Count of projects keys |
| D312 | Projects with MCP | ~/.claude.json | Projects with mcpServers defined |
| D313 | Trusted projects | ~/.claude.json | hasTrustDialogAccepted = true |
| D314 | Project-level cost | ~/.claude.json | lastCost per project |
| D315 | Total cost across projects | ~/.claude.json | Sum of all lastCost |
| D316 | Most expensive project | ~/.claude.json | Max lastCost |
| D317 | Project lines impact | ~/.claude.json | lastLinesAdded + lastLinesRemoved |
| D318 | Project code velocity | ~/.claude.json | Lines / duration per project |
| D319 | Project API efficiency | ~/.claude.json | Tokens / cost per project |
| D320 | React vulnerability exposure | ~/.claude.json | Projects with detected=true |

### Subscription Metrics
| # | Metric | Source | Calculation |
|---|--------|--------|-------------|
| D321 | Subscription type | credentials.json | subscriptionType |
| D322 | Rate limit tier | credentials.json | rateLimitTier |
| D323 | Token expiration | credentials.json | expiresAt - now |

### Version Metrics
| # | Metric | Source | Calculation |
|---|--------|--------|-------------|
| D324 | Installed versions | versions/ | Count of version files |
| D325 | Version disk usage | versions/ | Total size of versions |
| D326 | Version update frequency | versions/ | Version timestamps |
| D327 | Current version | ~/.claude.json | lastOnboardingVersion |

---

## Updated Grand Total

| Type | Count |
|------|-------|
| Raw data sources | **21** (was 16) |
| Raw field paths | **450+** (was 339) |
| Direct extractable metrics | 322 |
| Derived/computed metrics | **327** (was 300) |
| **TOTAL METRICS** | **649+** |


---

## 22. Project-Level `.claude/` Directories
**Purpose:** Per-project configuration and customizations
**Location:** `<project>/.claude/`

### Structure:
```
<project>/.claude/
├── settings.local.json          - Project-level permission overrides
├── agents/                      - Project-specific agent definitions
│   └── *.md
├── commands/                    - Project-specific slash commands
│   └── *.md
├── skills/                      - Project-specific skills
│   └── <skill-name>/
└── hooks/                       - Project-specific hooks
    ├── pre/
    └── post/
```

### settings.local.json Schema:
```
permissions                               [dict]
  .allow                                  [list]     - Project-allowed tools/patterns
  .deny                                   [list]     - Project-denied tools/patterns
  .ask                                    [list]     - Project-ask tools/patterns
```

---

## 23. `CLAUDE.md` Files
**Purpose:** Project instructions for Claude Code
**Location:** `<project>/CLAUDE.md`
**Format:** Markdown with instructions

### Content:
- Custom instructions for Claude behavior in this project
- Commit guidelines
- Code style preferences
- Project-specific context

### Metrics from CLAUDE.md:
| # | Metric | Calculation |
|---|--------|-------------|
| D328 | Projects with CLAUDE.md | Count of CLAUDE.md files |
| D329 | CLAUDE.md size | File sizes |
| D330 | Instruction complexity | Line/word count |

---

## 24. `.mcp.json` Files
**Purpose:** MCP server configuration per project
**Location:** `<project>/.mcp.json` or `<project>/mcp.json`

### Schema:
```
mcpServers                                [dict]
  .<server_name>                          [dict]
    .type                                 [str]      - "stdio" | "http"
    .command                              [str]      - Server command
    .args                                 [list]     - Command arguments
    .cwd                                  [str]      - Working directory
    .env                                  [dict]     - Environment variables
```

---

## 25. Environment Variables
**Purpose:** Runtime configuration
**Source:** Process environment

### Claude Code Variables:
```
CLAUDECODE                                [str]      - "1" when running in Claude Code
CLAUDE_CODE_ENTRYPOINT                    [str]      - Entry point (e.g., "cli")
ANTHROPIC_API_KEY                         [str]      - API key (if set)
CLAUDE_PROJECT_DIR                        [str]      - Current project directory
```

---

## Additional Project-Level Metrics

| # | Metric | Source | Calculation |
|---|--------|--------|-------------|
| D331 | Projects with custom agents | .claude/agents/ | Count of project agent dirs |
| D332 | Projects with custom commands | .claude/commands/ | Count of project command dirs |
| D333 | Projects with custom skills | .claude/skills/ | Count of project skill dirs |
| D334 | Projects with MCP servers | .mcp.json | Count of .mcp.json files |
| D335 | Custom permission rules | settings.local.json | Count per project |
| D336 | MCP servers defined | .mcp.json | Total across projects |
| D337 | Project customization score | Agents + commands + skills + CLAUDE.md | Per project |

---

## FINAL Updated Grand Total

| Type | Count |
|------|-------|
| Raw data sources | **25** |
| Raw field paths | **480+** |
| Direct extractable metrics | 322 |
| Derived/computed metrics | **337** |
| **TOTAL METRICS** | **659+** |

---

## Confidence Assessment

### Definitely Complete:
- `~/.claude/` directory structure
- `~/.claude.json` global state
- Session file schemas (deep scanned 4,477 files)
- All tool input/output schemas

### Likely Complete:
- Project-level configurations
- Environment variables

### Possibly Missing:
- Undocumented feature flags
- Future/beta features not yet in use
- Platform-specific locations (macOS Keychain, Windows Credential Manager)
- Temporary runtime state in /tmp

### Cannot Access:
- Server-side data (usage history on Anthropic's servers)
- Telemetry sent to Anthropic
- Rate limiting state on API side


---

## 26. `~/.cache/claude/`
**Purpose:** Claude Code cache directory
**Location:** `~/.cache/claude/`

### Contents:
```
staging/                                  [dir]      - Staging area for operations
```

---

## 27. `~/.cache/claude-cli-nodejs/`
**Purpose:** MCP server logs per project
**Location:** `~/.cache/claude-cli-nodejs/<project>/mcp-logs-<server>/`

### Structure:
```
<project-path>/
└── mcp-logs-<server-name>/
    └── YYYY-MM-DDTHH-MM-SS-mmmZ.txt     - MCP server logs
```

### Log File Contents:
- Server startup/shutdown events
- MCP protocol messages
- Error traces
- Request/response logs

### Metrics:
| # | Metric | Calculation |
|---|--------|-------------|
| D338 | MCP server log count | Count of log files per server |
| D339 | MCP server usage frequency | Logs per server per day |
| D340 | MCP errors | Error patterns in logs |

---

## 28. Statusline Input JSON (Runtime)
**Purpose:** Real-time session data passed to statusline command
**Access:** Via `settings.json` statusLine.command

### Schema (passed to command stdin):
```
{
  "model": {
    "display_name": string         - Human-readable model name
  },
  "workspace": {
    "current_dir": string          - Current working directory
    "project_dir": string          - Project root directory
  },
  "version": string                - Claude Code version
  "cost": {
    "total_cost_usd": float        - Session cost so far
    "total_lines_added": int       - Lines added in session
    "total_lines_removed": int     - Lines removed in session
  },
  "exceeds_200k_tokens": boolean   - Whether context exceeds 200k
}
```

### Metrics:
| # | Metric | Calculation |
|---|--------|-------------|
| D341 | Real-time session cost | cost.total_cost_usd |
| D342 | Real-time lines changed | lines_added + lines_removed |
| D343 | Context overflow indicator | exceeds_200k_tokens |

---

## FINAL Grand Total

| Type | Count |
|------|-------|
| **Raw data sources** | **28** |
| **Raw field paths** | **500+** |
| **Direct extractable metrics** | **322** |
| **Derived/computed metrics** | **343** |
| **TOTAL METRICS** | **665+** |

---

## Final Confidence Assessment

| Category | Confidence | Verified By |
|----------|------------|-------------|
| ~/.claude/ directory | **98%** | Full recursive scan (12,204 files) |
| ~/.claude.json | **99%** | Complete JSON parse |
| Session file schemas | **95%** | Deep scan of 4,477 files |
| Cache directories | **95%** | XDG standard locations checked |
| Project-level configs | **90%** | Multiple projects checked |
| Environment variables | **80%** | Known documented vars |
| Runtime data | **85%** | Statusline schema extracted |

### What Could Still Be Missing:
1. **Undocumented environment variables**
2. **Platform-specific paths** (macOS vs Linux differences)
3. **Very rare session events** (edge cases in <0.1% of sessions)
4. **Future/beta features** behind disabled feature flags
5. **Server-side data** (not locally stored)
6. **Encrypted/binary data** we can't parse

### Exhaustiveness Claim:
**This catalog documents 95%+ of the locally-accessible Claude Code metadata.**


---

# PART 8: NEW DATA SOURCES - COMPLETE TYPE DEFINITIONS

This section provides complete type definitions, schemas, and derived metrics for sources 17-28.

---

## Source 17: `~/.claude.json` - Complete Schema

### Global Settings
```typescript
{
  // Usage Tracking
  numStartups: number,                    // Total Claude Code launches (e.g., 292)
  installMethod: "native" | "npm" | "brew" | string,
  autoUpdates: boolean,
  verbose: boolean,
  autoCompactEnabled: boolean,

  // Onboarding State
  hasCompletedOnboarding: boolean,
  lastOnboardingVersion: string,          // Semver (e.g., "2.0.67")
  hasSeenTasksHint: boolean,
  hasSeenStashHint: boolean,

  // Feature Usage
  memoryUsageCount: number,               // Times memory feature used
  promptQueueUseCount: number,            // Times prompt queue used (e.g., 195)

  // User Identity
  userID: string,                         // SHA-256 hash (64 hex chars)
}
```

### Tips History (Feature Discovery Tracking)
```typescript
tipsHistory: {
  [tipName: string]: number               // Tip name → times shown
}
```

**Known Tip Names (30+):**
| Tip Name | Category | What It Teaches |
|----------|----------|-----------------|
| `new-user-warmup` | Onboarding | Initial introduction |
| `plan-mode-for-complex-tasks` | Workflow | Planning feature |
| `terminal-setup` | Setup | Terminal configuration |
| `theme-command` | Customization | Theme switching |
| `status-line` | UI | Status line feature |
| `prompt-queue` | Workflow | Queuing prompts |
| `todo-list` | Workflow | Task tracking |
| `install-github-app` | Integration | GitHub app |
| `permissions` | Security | Permission system |
| `drag-and-drop-images` | Input | Image handling |
| `double-esc` | Shortcuts | Escape key |
| `continue` | Workflow | Continue feature |
| `custom-commands` | Customization | Slash commands |
| `shift-tab` | Shortcuts | Tab behavior |
| `image-paste` | Input | Pasting images |
| `custom-agents` | Customization | Custom agents |
| `git-worktrees` | Workflow | Parallel work |
| `tab-toggle-thinking` | UI | Thinking toggle |
| `ultrathink-keyword` | Features | Deep thinking |
| `stickers-command` | Fun | Stickers |
| `rename-conversation` | UI | Renaming |
| `colorterm-truecolor` | Setup | Color support |
| `config-thinking-mode` | Settings | Thinking config |
| `frontend-design-plugin` | Plugins | Frontend plugin |
| `default-permission-mode-config` | Security | Permissions |
| `double-esc-code-restore` | Shortcuts | Code restore |
| `# for memory` | Features | Memory syntax |
| `enter-to-steer-in-relatime` | UI | Real-time steering |

### Custom API Key Responses
```typescript
customApiKeyResponses: {
  approved: string[],                     // Approved API key patterns
  rejected: string[]                      // Rejected API key patterns
}
```

### Feature Flags (Cached Statsig Gates)
```typescript
cachedStatsigGates: {
  [gateName: string]: boolean
}
```

**Known Feature Flags:**
| Flag Name | Type | Purpose |
|-----------|------|---------|
| `tengu_disable_bypass_permissions_mode` | bool | Permission bypass |
| `tengu_use_file_checkpoints` | bool | File checkpointing |
| `tengu_tool_pear` | bool | Pear tool |
| `tengu_migrate_ignore_patterns` | bool | Ignore migration |
| `tengu_halloween` | bool | Seasonal theme |
| `tengu_glob_with_rg` | bool | Glob implementation |
| `tengu_web_tasks` | bool | Web task feature |
| `tengu_log_1p_events` | bool | Event logging |
| `tengu_enable_versioned_plugins` | bool | Plugin versioning |
| `code_slack_app_install_banner` | bool | Slack integration |
| `tengu_sumi` | bool | Sumi feature |
| `tengu_react_vulnerability_warning` | bool | React security |
| `tengu_tool_result_persistence` | bool | Result caching |
| `tengu_c4w_usage_limit_notifications_enabled` | bool | Usage limits |
| `tengu_thinkback` | bool | Thinkback feature |

### Dynamic Configs
```typescript
cachedDynamicConfigs: {
  "tengu-top-of-feed-tip": {
    tip: string,                          // Tip text to show
    color: string                         // Display color
  }
}
```

### Model Configuration
```typescript
statsigModel: {
  bedrock: string,                        // AWS Bedrock model ID
  vertex: string,                         // GCP Vertex model ID
  firstParty: string                      // Anthropic API model ID
}
```

### Per-Project Statistics (CRITICAL DATA SOURCE)
```typescript
projects: {
  [projectPath: string]: {
    // Trust & Security
    allowedTools: string[],               // Project-allowed tool patterns
    hasTrustDialogAccepted: boolean,
    dontCrawlDirectory: boolean,

    // MCP Configuration
    mcpServers: {
      [serverName: string]: McpServerConfig
    },
    mcpContextUris: string[],
    enabledMcpjsonServers: string[],
    disabledMcpjsonServers: string[],
    enableAllProjectMcpServers: boolean,

    // Onboarding
    projectOnboardingSeenCount: number,   // Times onboarding shown
    hasCompletedProjectOnboarding: boolean,

    // File Discovery
    exampleFiles: string[],               // Auto-discovered example files
    exampleFilesGeneratedAt: number,      // Unix ms timestamp

    // Patterns
    ignorePatterns: string[],             // Custom ignore patterns

    // Claude.md Handling
    hasClaudeMdExternalIncludesApproved: boolean,
    hasClaudeMdExternalIncludesWarningShown: boolean,

    // Security Scanning
    reactVulnerabilityCache: {
      detected: boolean,
      package: string | null,
      packageName: string | null,
      version: string | null,
      packageManager: string | null
    },

    // Last Session Statistics (HIGH VALUE!)
    lastSessionId: string,                // UUID of last session
    lastCost: number,                     // Cost in USD (e.g., 22.113691)
    lastAPIDuration: number,              // API time in ms
    lastAPIDurationWithoutRetries: number, // API time excluding retries
    lastToolDuration: number,             // Tool execution time ms
    lastDuration: number,                 // Total session duration ms
    lastLinesAdded: number,               // Lines of code added
    lastLinesRemoved: number,             // Lines of code removed
    lastTotalInputTokens: number,
    lastTotalOutputTokens: number,
    lastTotalCacheCreationInputTokens: number,
    lastTotalCacheReadInputTokens: number,
    lastTotalWebSearchRequests: number,

    // Per-Model Breakdown (GRANULAR!)
    lastModelUsage: {
      [modelId: string]: {
        inputTokens: number,
        outputTokens: number,
        cacheReadInputTokens: number,
        cacheCreationInputTokens: number,
        webSearchRequests: number,
        costUSD: number                   // Cost for this model
      }
    }
  }
}
```

---

## Source 18: `~/.claude/.credentials.json` - Complete Schema

```typescript
{
  claudeAiOauth: {
    accessToken: string,                  // OAuth access token (sk-ant-oat01-...)
    refreshToken: string,                 // OAuth refresh token (sk-ant-ort01-...)
    expiresAt: number,                    // Expiration Unix ms
    
    scopes: string[],                     // Granted scopes
    // Known scopes:
    // - "user:inference"
    // - "user:profile"
    // - "user:sessions:claude_code"
    
    subscriptionType: "max" | "pro" | "free" | string,
    rateLimitTier: string                 // e.g., "default_claude_max_20x"
  }
}
```

---

## Source 19: `~/.config/claude/claude_code_config.json`

```typescript
{
  mcpServers: {
    [serverName: string]: {
      command: string,                    // Server command
      args: string[]                      // Command arguments
    }
  }
}
```

---

## Source 20-22: Project-Level Configurations

### `<project>/.claude/settings.local.json`
```typescript
{
  permissions: {
    allow: string[],                      // Allowed tool patterns
    deny: string[],                       // Denied tool patterns
    ask: string[]                         // Always-ask patterns
  }
}
```

### `<project>/.claude/agents/*.md`
```
Markdown files defining custom agents
- Filename: Agent name
- Content: Agent prompt/instructions
```

### `<project>/.claude/commands/*.md`
```
Markdown files defining slash commands
- Filename: Command name (without /)
- Content: Command prompt template
```

### `<project>/.claude/skills/<skill-name>/`
```
SKILL.md                                  - Skill definition
CHEATSHEET.md                             - Quick reference (optional)
reference.md                              - Detailed docs (optional)
configs/                                  - Config files (optional)
scripts/                                  - Helper scripts (optional)
templates/                                - Template files (optional)
```

---

## Source 23: `CLAUDE.md` Files

```markdown
# Project instructions for Claude Code
- Markdown format
- Read by Claude at session start
- Contains: coding standards, commit rules, project context
```

**Common Sections:**
- Commit guidelines
- Code style preferences
- Project-specific instructions
- External includes (with approval)

---

## Source 24: `.mcp.json` Files

```typescript
{
  mcpServers: {
    [serverName: string]: {
      type: "stdio" | "http",
      command: string,
      args: string[],
      cwd: string,                        // Working directory
      env: {                              // Environment variables
        [key: string]: string
      }
    }
  }
}
```

---

## Source 25: Environment Variables

| Variable | Type | Description |
|----------|------|-------------|
| `CLAUDECODE` | "1" | Indicates running in Claude Code |
| `CLAUDE_CODE_ENTRYPOINT` | string | Entry point ("cli") |
| `CLAUDE_PROJECT_DIR` | string | Current project directory |
| `ANTHROPIC_API_KEY` | string | API key (if using custom) |
| `CLAUDE_MODEL` | string | Model override |
| `CLAUDE_CONFIG_DIR` | string | Config directory override |

---

## Source 26-27: Cache Directories

### `~/.cache/claude/staging/`
```
Temporary staging area for file operations
- Usually empty between operations
- May contain partial downloads/uploads
```

### `~/.cache/claude-cli-nodejs/<project>/mcp-logs-<server>/`

**Log File Format:** `YYYY-MM-DDTHH-MM-SS-mmmZ.txt` or `.jsonl`

**Log Contents:**
```
[timestamp] [level] message
- Server startup events
- MCP protocol messages (initialize, tools/list, etc.)
- Tool invocations
- Error traces
- Server shutdown
```

---

## Source 28: Statusline Input JSON

**Real-time data passed to statusline command via stdin:**

```typescript
{
  model: {
    display_name: string,                 // e.g., "Claude Opus 4.5"
    id: string                            // e.g., "claude-opus-4-5-20251101"
  },
  workspace: {
    current_dir: string,                  // Current working directory
    project_dir: string                   // Project root
  },
  version: string,                        // Claude Code version
  cost: {
    total_cost_usd: number,               // Session cost so far
    total_lines_added: number,            // Lines added
    total_lines_removed: number           // Lines removed
  },
  exceeds_200k_tokens: boolean,           // Context overflow warning
  session_id: string,                     // Current session UUID
  git_branch: string                      // Current git branch
}
```

---

# PART 9: DERIVED METRICS FROM NEW SOURCES

## Category Q: Startup & Usage Metrics

| # | Metric | Source | Calculation | Insight |
|---|--------|--------|-------------|---------|
| D344 | Total startups | ~/.claude.json | numStartups | Overall usage |
| D345 | Startups per day | ~/.claude.json | numStartups / days since first | Usage frequency |
| D346 | Startup trend | ~/.claude.json | numStartups change over time | Adoption curve |
| D347 | Prompt queue adoption | ~/.claude.json | promptQueueUseCount / numStartups | Feature adoption |
| D348 | Memory feature adoption | ~/.claude.json | memoryUsageCount / numStartups | Feature adoption |

## Category R: Feature Discovery Metrics

| # | Metric | Source | Calculation | Insight |
|---|--------|--------|-------------|---------|
| D349 | Tips seen count | ~/.claude.json | len(tipsHistory) | Feature awareness |
| D350 | Tips available | ~/.claude.json | Total known tips (~30) | Potential discovery |
| D351 | Feature discovery rate | ~/.claude.json | Tips seen / tips available | % features discovered |
| D352 | Most shown tip | ~/.claude.json | max(tipsHistory values) | What's reinforced |
| D353 | Least engaged tip | ~/.claude.json | Tips with count=1 | Ignored features |
| D354 | Tip engagement score | ~/.claude.json | avg(tipsHistory values) | Engagement depth |
| D355 | Advanced feature discovery | ~/.claude.json | Custom agents + commands tips | Power user indicator |
| D356 | Shortcut awareness | ~/.claude.json | double-esc + shift-tab tips | Efficiency potential |
| D357 | Feature category adoption | ~/.claude.json | Tips grouped by category | Feature area focus |

## Category S: Feature Flag Metrics

| # | Metric | Source | Calculation | Insight |
|---|--------|--------|-------------|---------|
| D358 | Enabled flags count | ~/.claude.json | Count true in cachedStatsigGates | Feature access |
| D359 | Disabled flags count | ~/.claude.json | Count false in cachedStatsigGates | Restricted features |
| D360 | Feature flag ratio | ~/.claude.json | enabled / total | Access level |
| D361 | Beta feature access | ~/.claude.json | Specific beta flags enabled | Early adopter status |
| D362 | Security flags enabled | ~/.claude.json | Security-related flags | Security posture |

## Category T: Per-Project Analytics (HIGH VALUE)

### Cost Analysis
| # | Metric | Source | Calculation | Insight |
|---|--------|--------|-------------|---------|
| D363 | Total cost all projects | ~/.claude.json | sum(projects.*.lastCost) | Overall spending |
| D364 | Most expensive project | ~/.claude.json | max(projects.*.lastCost) | Cost hotspot |
| D365 | Least expensive project | ~/.claude.json | min(projects.*.lastCost) | Efficient projects |
| D366 | Cost per project | ~/.claude.json | lastCost per project | Project spending |
| D367 | Cost variance | ~/.claude.json | std dev of lastCost | Spending consistency |
| D368 | Cost percentile rank | ~/.claude.json | Project cost percentile | Relative spending |

### Code Impact Analysis
| # | Metric | Source | Calculation | Insight |
|---|--------|--------|-------------|---------|
| D369 | Total lines added all projects | ~/.claude.json | sum(lastLinesAdded) | Total code generated |
| D370 | Total lines removed all projects | ~/.claude.json | sum(lastLinesRemoved) | Total code removed |
| D371 | Net code impact | ~/.claude.json | Added - removed | Code growth |
| D372 | Code churn by project | ~/.claude.json | Added + removed per project | Change intensity |
| D373 | Lines per dollar | ~/.claude.json | Lines / cost per project | Cost efficiency |
| D374 | Most productive project | ~/.claude.json | Highest lines/cost ratio | Best ROI |

### Time Analysis
| # | Metric | Source | Calculation | Insight |
|---|--------|--------|-------------|---------|
| D375 | Longest session project | ~/.claude.json | max(lastDuration) | Deep work location |
| D376 | API time ratio | ~/.claude.json | lastAPIDuration / lastDuration | API vs thinking |
| D377 | Tool time ratio | ~/.claude.json | lastToolDuration / lastDuration | Automation level |
| D378 | Retry overhead | ~/.claude.json | APIDuration - APIDurationWithoutRetries | Retry cost |
| D379 | Time efficiency | ~/.claude.json | Lines / duration per project | Productivity rate |

### Token Analysis by Project
| # | Metric | Source | Calculation | Insight |
|---|--------|--------|-------------|---------|
| D380 | Input/output ratio by project | ~/.claude.json | Input / output tokens | Prompt efficiency |
| D381 | Cache efficiency by project | ~/.claude.json | CacheRead / (CacheRead + Input) | Cache hits |
| D382 | Token density | ~/.claude.json | Tokens / duration | Token rate |
| D383 | Model mix by project | ~/.claude.json | lastModelUsage breakdown | Model preferences |
| D384 | Opus vs Sonnet ratio by project | ~/.claude.json | Model token comparison | Quality vs speed |

### Security & Trust
| # | Metric | Source | Calculation | Insight |
|---|--------|--------|-------------|---------|
| D385 | Trusted projects count | ~/.claude.json | Count hasTrustDialogAccepted=true | Trust adoption |
| D386 | Untrusted projects | ~/.claude.json | Count hasTrustDialogAccepted=false | Trust resistance |
| D387 | Projects with vulnerabilities | ~/.claude.json | reactVulnerabilityCache.detected=true | Security issues |
| D388 | Crawl-disabled projects | ~/.claude.json | dontCrawlDirectory=true count | Privacy-sensitive |

### MCP Adoption
| # | Metric | Source | Calculation | Insight |
|---|--------|--------|-------------|---------|
| D389 | Projects with MCP servers | ~/.claude.json | Count with mcpServers defined | MCP adoption |
| D390 | Total MCP servers | ~/.claude.json | Sum of mcpServers across projects | MCP scale |
| D391 | MCP servers per project | ~/.claude.json | Avg mcpServers count | MCP intensity |
| D392 | Most MCP-heavy project | ~/.claude.json | Max mcpServers count | Integration hub |

### Onboarding Analysis
| # | Metric | Source | Calculation | Insight |
|---|--------|--------|-------------|---------|
| D393 | Onboarding completion rate | ~/.claude.json | Completed / total projects | Adoption success |
| D394 | Onboarding friction score | ~/.claude.json | Avg onboardingSeenCount | Adoption difficulty |
| D395 | High-friction projects | ~/.claude.json | onboardingSeenCount > 3 | Problem projects |

## Category U: Subscription & Rate Limit Metrics

| # | Metric | Source | Calculation | Insight |
|---|--------|--------|-------------|---------|
| D396 | Subscription tier | credentials.json | subscriptionType | Plan level |
| D397 | Rate limit tier | credentials.json | rateLimitTier | Rate limit level |
| D398 | Token freshness | credentials.json | expiresAt - now | Time until refresh |
| D399 | Scope count | credentials.json | len(scopes) | Permission breadth |

## Category V: Project Customization Metrics

| # | Metric | Source | Calculation | Insight |
|---|--------|--------|-------------|---------|
| D400 | Projects with CLAUDE.md | File scan | Count of CLAUDE.md files | Instruction adoption |
| D401 | CLAUDE.md total size | File scan | Sum of file sizes | Instruction depth |
| D402 | Avg CLAUDE.md size | File scan | Mean file size | Typical complexity |
| D403 | Projects with custom agents | .claude/agents/ | Count with agent dirs | Agent adoption |
| D404 | Custom agents defined | .claude/agents/*.md | Total agent count | Agent scale |
| D405 | Projects with custom commands | .claude/commands/ | Count with command dirs | Command adoption |
| D406 | Custom commands defined | .claude/commands/*.md | Total command count | Command scale |
| D407 | Projects with custom skills | .claude/skills/ | Count with skill dirs | Skill adoption |
| D408 | Custom skills defined | .claude/skills/*/ | Total skill count | Skill scale |
| D409 | Projects with .mcp.json | File scan | Count of .mcp.json files | MCP config adoption |
| D410 | Project customization score | Multiple | Agents + commands + skills + CLAUDE.md | Customization depth |
| D411 | Permission rules per project | settings.local.json | Count of allow/deny rules | Security granularity |

## Category W: MCP Server Log Metrics

| # | Metric | Source | Calculation | Insight |
|---|--------|--------|-------------|---------|
| D412 | MCP log files count | cache logs | Total log files | MCP activity |
| D413 | MCP servers used | cache logs | Unique server names | MCP diversity |
| D414 | MCP logs per day | cache logs | Log files by date | MCP intensity |
| D415 | MCP error rate | cache logs | Error patterns / total | MCP reliability |
| D416 | Longest MCP session | cache logs | Max log file size | Deep MCP usage |
| D417 | MCP server popularity | cache logs | Logs per server | Server preferences |

## Category X: Real-Time Session Metrics (Statusline)

| # | Metric | Source | Calculation | Insight |
|---|--------|--------|-------------|---------|
| D418 | Live session cost | statusline JSON | cost.total_cost_usd | Current spend |
| D419 | Live lines changed | statusline JSON | lines_added + lines_removed | Current impact |
| D420 | Context overflow events | statusline JSON | exceeds_200k_tokens occurrences | Context pressure |
| D421 | Model in use | statusline JSON | model.display_name | Current model |
| D422 | Session cost velocity | statusline JSON | Cost / session time | Spend rate |
| D423 | Lines per minute | statusline JSON | Lines / session time | Output rate |

## Category Y: Cross-Source Correlation Metrics

| # | Metric | Source | Calculation | Insight |
|---|--------|--------|-------------|---------|
| D424 | Tip-to-feature correlation | tips + sessions | Tip shown → feature used | Tip effectiveness |
| D425 | Customization-to-cost | customization + cost | Cost for customized vs not | Customization ROI |
| D426 | Trust-to-productivity | trust + output | Lines for trusted vs not | Trust impact |
| D427 | MCP-to-efficiency | MCP + metrics | Output with MCP vs without | MCP value |
| D428 | Subscription-to-usage | subscription + usage | Usage patterns by tier | Tier utilization |
| D429 | Onboarding-to-retention | onboarding + sessions | Sessions after onboarding | Onboarding quality |
| D430 | Flag-to-behavior | flags + sessions | Behavior with flags on/off | Flag impact |

## Category Z: Behavioral Pattern Metrics

### Learning & Growth
| # | Metric | Source | Calculation | Insight |
|---|--------|--------|-------------|---------|
| D431 | Feature adoption velocity | tips over time | Tips discovered per week | Learning rate |
| D432 | Customization growth | customization over time | New agents/commands per week | Sophistication growth |
| D433 | Efficiency improvement | lines/cost over time | Trend in productivity | Skill development |
| D434 | Error rate decline | errors over time | Error trend | Mastery curve |

### Engagement Patterns
| # | Metric | Source | Calculation | Insight |
|---|--------|--------|-------------|---------|
| D435 | Project diversity index | projects visited | Unique projects / sessions | Focus vs variety |
| D436 | Project loyalty | sessions per project | Concentration measure | Project commitment |
| D437 | New project rate | new projects over time | New projects per week | Exploration rate |
| D438 | Return rate | return visits | Returns / unique projects | Project stickiness |

### Cost Behavior
| # | Metric | Source | Calculation | Insight |
|---|--------|--------|-------------|---------|
| D439 | Cost consciousness | model choices | Haiku vs Opus ratio over time | Cost awareness |
| D440 | Spending trajectory | cost over time | Cost trend | Budget trajectory |
| D441 | Cost per feature | cost by activity | Cost by task type | Feature economics |
| D442 | Peak spend timing | cost by hour/day | When most is spent | Spend patterns |

---

## Updated Final Totals

| Type | Previous | Added | New Total |
|------|----------|-------|-----------|
| Raw data sources | 28 | 0 | **28** |
| Raw field paths | 500+ | 100+ | **600+** |
| Direct metrics | 322 | 0 | **322** |
| Derived metrics | 343 | 99 | **442** |
| **TOTAL METRICS** | 665 | 99 | **764+** |

---

## Metric Categories Summary

| Category | Range | Count | Focus Area |
|----------|-------|-------|------------|
| A | D001-D028 | 28 | Time & Activity |
| B | D029-D048 | 20 | Tool Usage |
| C | D049-D073 | 25 | File Operations |
| D | D074-D109 | 36 | Model & Tokens |
| E | D110-D136 | 27 | Conversation |
| F | D137-D142 | 6 | Thinking & Complexity |
| G | D143-D158 | 16 | Task Management |
| H | D159-D172 | 14 | Agent & Delegation |
| I | D173-D188 | 16 | Project Activity |
| J | D189-D203 | 15 | Error & Recovery |
| K | D204-D228 | 25 | Code Generation |
| L | D229-D238 | 10 | Web Research |
| M | D239-D252 | 14 | Hooks & Customization |
| N | D253-D259 | 7 | User Interaction |
| O | D260-D300 | 41 | Advanced Derived |
| P | D301-D343 | 43 | Previous Additions |
| Q | D344-D348 | 5 | Startup & Usage |
| R | D349-D357 | 9 | Feature Discovery |
| S | D358-D362 | 5 | Feature Flags |
| T | D363-D395 | 33 | Per-Project Analytics |
| U | D396-D399 | 4 | Subscription |
| V | D400-D411 | 12 | Project Customization |
| W | D412-D417 | 6 | MCP Server Logs |
| X | D418-D423 | 6 | Real-Time Session |
| Y | D424-D430 | 7 | Cross-Source Correlation |
| Z | D431-D442 | 12 | Behavioral Patterns |
| **TOTAL** | | **442** | |

---

# Part 10: Advanced Behavioral & Psychological Metrics (D443-D542)

This section adds **100 advanced derived metrics** focusing on behavioral psychology, cognitive economics, trust calibration, architectural health, and novel analytical dimensions.

---

## Category AA: Behavioral Psychology & Cognitive State (D443-D447)

These metrics infer cognitive and emotional states from interaction patterns.

| # | Metric | Category | Calculation | Data Sources | Type | Insight |
|---|--------|----------|-------------|--------------|------|---------|
| D443 | Hesitation Index | Cognitive Load | `median(time_delta(AskUserQuestion→tool_result)) / question_char_count` | session.jsonl | Ratio | Rising index suggests cognitive depletion or AI questions exceeding user's mental model |
| D444 | Blind Faith Ratio (Skim Rate) | Trust Calibration | `(next_user_action_time - assistant_msg_end) / output_tokens` for code blocks >10 lines | session.jsonl | Ratio | If <4ms/token, user is skimming not verifying. High values = dangerous blind trust |
| D445 | Decision Fatigue Slope | Cognitive Decline | `P(option_0_selected) ~ session_duration` regression | session.jsonl | Trend | Rising Option 0 selection over time indicates decision fatigue |
| D446 | Frustration Typing Signature | Emotional State | After tool_error: `(msg_length_decrease) + (capitalization_ratio) + (punctuation_density)` | session.jsonl | Compound | High scores correlate with imminent session abandonment |
| D447 | Panic Spiral Probability | Stress Response | `count(tool_error → user_msg<10s containing "fix"/"error"/"no") / tool_errors` | session.jsonl | Ratio | Rapid short responses after errors indicate panic coding |

---

## Category AB: Learning, Mastery & Feature Discovery (D448-D452)

These metrics track skill development and feature adoption patterns.

| # | Metric | Category | Calculation | Data Sources | Type | Insight |
|---|--------|----------|-------------|--------------|------|---------|
| D448 | Feature Stubbornness Score | Tool Mastery | `tipsHistory[tip].count / (actual_usage_count + 1)` | ~/.claude.json, session.jsonl | Ratio | Features repeatedly shown but not adopted. High = UX friction or strong habits |
| D449 | Tip Conversion Velocity | Learning Curves | `days_between(tip_first_shown, feature_first_used)` | ~/.claude.json, session.jsonl | Lag | Measures teachability - how fast user adopts after prompt |
| D450 | Native Feature Adoption Velocity | Skill Evolution | `days_between(firstSessionDate, first_advanced_feature_use)` | stats-cache.json, session.jsonl | Lag | Differentiates power users (fast) from CLI-only users (slow) |
| D451 | Command Sophistication Curve | Skill Plateaus | `(Task+EnterPlanMode+Glob) / (Read+Edit+Bash)` over 30-day windows | session.jsonl | Trend | Flat = skill plateau. Rising = evolving from editor to orchestrator |
| D452 | Manual Compactor Rate | Meta-Cognition | `count(compactMetadata.trigger="manual") / count(compactMetadata)` | session.jsonl | Ratio | High = aware of context hygiene. Low = passive resource management |

---

## Category AC: Collaboration & Workflow Patterns (D453-D457)

These metrics measure the quality and nature of human-AI collaboration.

| # | Metric | Category | Calculation | Data Sources | Type | Insight |
|---|--------|----------|-------------|--------------|------|---------|
| D453 | Micromanagement Index | Collaboration Quality | `user_input_tokens / tool_call_count` per session | session.jsonl | Ratio | High = detailed instructions (low trust). Low = high-leverage prompting |
| D454 | Hook Dependency Score | Workflow Optimization | `sessions_with_hookCount>0 / total_sessions` | session.jsonl | Ratio | Measures reliance on invisible automation. High = mature environment |
| D455 | Hook Friction Coefficient | Governance | `count(preventedContinuation=true) / count(hookCount>0)` | session.jsonl | Ratio | High = AI struggling to meet project standards |
| D456 | Skepticism Loop Intensity | Trust Calibration | `count(Edit→Bash(test/lint)→Edit same_file)` | session.jsonl | Sequence | High = healthy "trust but verify" behavior |
| D457 | Ghost Session Rate | Anomaly Detection | `sessions(duration>10min AND user_msgs=0 AND cost=0) / total_sessions` | session.jsonl | Ratio | Technical issues or user distraction |

---

## Category AD: Code Quality & Architectural Health (D458-D462)

These metrics assess codebase health and technical debt.

| # | Metric | Category | Calculation | Data Sources | Type | Insight |
|---|--------|----------|-------------|--------------|------|---------|
| D458 | AI Technical Debt (Bus Factor Risk) | Knowledge Dependency | `count(files_only_modified_by_Edit AND never_in_history.jsonl)` | session.jsonl, history.jsonl | Count | Code never touched by human hands |
| D459 | Zombie Code Index | Code Quality Proxies | `count(files_Read>3_times AND Edited=0_times)` | session.jsonl | Count | Confusing but fragile code - frequently referenced, never modified |
| D460 | Spaghetti Coupling Factor | Architectural Coherence | `avg(distinct_files_modified_per_assistant_turn)` | session.jsonl | Average | High = high coupling/low cohesion |
| D461 | TDD Adherence Score | Best Practices | `P(test_file_edited_before_impl_file)` per session | session.jsonl | Probability | High = Test-Driven Development. Low = Test-After or No-Test |
| D462 | Vulnerability Ignorance Window | Security Risk | `sessions_elapsed_while(reactVulnerabilityCache.detected=true)` | ~/.claude.json, session.jsonl | Duration | Time vulnerability remains unaddressed |

---

## Category AE: Economic & Efficiency Metrics (D463-D467)

These metrics optimize cost-effectiveness and resource usage.

| # | Metric | Category | Calculation | Data Sources | Type | Insight |
|---|--------|----------|-------------|--------------|------|---------|
| D463 | Haiku Optimization Opportunity | Token Economics | `sum(opus_sonnet_cost WHERE session_tools ⊆ {Read, WebSearch})` | session.jsonl | Sum | Expensive models for low-complexity read-only tasks |
| D464 | Context Bankruptcy Rate | Resource Management | `count(exceeds_200k_tokens OR large_cleared_input) / active_hours` | session.jsonl, statusline | Rate | High = poor context management, high costs |
| D465 | Ephemeral Cache Waste ("The Leak") | Efficiency | `sum(cache_creation.ephemeral_5m WHERE next_msg_delay > 5min)` | session.jsonl | Sum | Paid for cache that expired unused |
| D466 | Cost of Correction ("Undo Tax") | Economics | `sum(cost WHERE next_action = git_checkout OR revert_Edit)` | session.jsonl | Sum | Direct monetary cost of bad AI code |
| D467 | Project Sunk Cost | Behavioral Economics | `lastCost WHERE no_successful_git_commit` | ~/.claude.json, session.jsonl | Sum | Spending without resolution |

---

## Category AF: Problem-Solving Patterns (D468-D471)

These metrics characterize problem-solving approaches and blocks.

| # | Metric | Category | Calculation | Data Sources | Type | Insight |
|---|--------|----------|-------------|--------------|------|---------|
| D468 | Rabbit Hole Depth | Focus/Progress | `max(consecutive WebSearch→Read WITHOUT Edit/Task)` | session.jsonl | Sequence | Deep = research stuck. Shallow = research→action flow |
| D469 | Plan Adherence Ratio | Planning | `count(plan_steps_marked_[x]) / total_plan_steps` per EnterPlanMode session | plans/*.md, session.jsonl | Ratio | Low = planning failure or distraction |
| D470 | YOLO Coding Rate | Risk Taking | `count(Write/Edit WITHOUT preceding Read of same file)` / total_writes | session.jsonl | Ratio | High = guess-driven coding, hallucination risk |
| D471 | Echo Chamber Effect | Stuck Patterns | `count(consecutive WebSearch with Levenshtein(query_i, query_i+1) < threshold)` | session.jsonl | Sequence | Asking same question repeatedly without progress |

---

## Category AG: Meta-Cognitive & Input Metrics (D472-D475)

These metrics analyze user input patterns and communication quality.

| # | Metric | Category | Calculation | Data Sources | Type | Insight |
|---|--------|----------|-------------|--------------|------|---------|
| D472 | Paste Dump Ratio | Prompt Engineering | `user_tokens_that_are_code / total_user_tokens` | session.jsonl | Ratio | High = manual context management vs trusting AI to Read |
| D473 | Instruction Entropy | Communication Quality | `vocabulary_diversity(user_messages)` | session.jsonl | Entropy | Low = lazy prompting ("fix it", "continue") → higher error rates |
| D474 | Screenshot Development Rate | Multimodal Usage | `count(image/* messages → frontend_edits)` | session.jsonl | Sequence | Visual-driven development trend |
| D475 | Prompt Correction Density | Misalignment | `count(user_msgs containing "no"/"stop"/"wrong") / total_user_msgs` | session.jsonl | Ratio | High = poor prompt engineering or struggling model |

---

## Category AH: Network & Graph Metrics (D476-D478)

These metrics analyze structural relationships in usage patterns.

| # | Metric | Category | Calculation | Data Sources | Type | Insight |
|---|--------|----------|-------------|--------------|------|---------|
| D476 | Knowledge Silo Index | Project Graph | `count(disconnected_clusters in file_co-modification_graph)` | session.jsonl | Count | Isolated file clusters = knowledge silos |
| D477 | Agent Fan-Out Factor | Agent Delegation | `avg(unique_subagents_per_parent_session)` | session.jsonl | Average | High = architect workflow. Zero = lone wolf |
| D478 | Agent Recursion Risk | Complexity | `max(Task_call_nesting_depth)` | session.jsonl, agent-*.jsonl | Max | Deep = trust in complex autonomous reasoning |

---

## Category AI: Security & Permissions (D479-D481)

These metrics assess security posture and permission management.

| # | Metric | Category | Calculation | Data Sources | Type | Insight |
|---|--------|----------|-------------|--------------|------|---------|
| D479 | Permission Creep Rate | Security Posture | `d(allowedTools.length) / d(sessions)` | ~/.claude.json | Rate | Linear growth = progressively disabling safety rails |
| D480 | Click-Through Rate | Security Psychology | `count(permission_approval < 1s)` for dangerous tools | session.jsonl | Ratio | Low latency = permission fatigue, clicking without reading |
| D481 | Shadow IT Detector | Security | `count(WebFetch to non-whitelisted domains or unusual ports)` | session.jsonl | Count | Exfiltration risk or unapproved sources |

---

## Category AJ: Temporal Dynamics (D482-D484)

These metrics analyze time-based patterns and rhythms.

| # | Metric | Category | Calculation | Data Sources | Type | Insight |
|---|--------|----------|-------------|--------------|------|---------|
| D482 | Monday Morning Cold Start | Temporal Patterns | `error_rate[first_session_of_week] / avg(error_rate[mid_week])` | stats-cache.json, session.jsonl | Ratio | Quantifies context loading cost after breaks |
| D483 | Session Momentum Curve | Flow State | `d(lines_generated) / d(time)` over session | session.jsonl | Derivative | Accelerating = flow. Decelerating = fatigue/blocker |
| D484 | Circadian Error Vulnerability | Quality Control | `correlation(hour_24, tool_error_rate)` | stats-cache.json, session.jsonl | Correlation | Detects fatigue-driven errors (2 AM spike?) |

---

## Category AK: Customization & Environment (D485-D488)

These metrics evaluate customization investment and returns.

| # | Metric | Category | Calculation | Data Sources | Type | Insight |
|---|--------|----------|-------------|--------------|------|---------|
| D485 | Customization ROI | Tool Efficiency | `(lastLinesAdded/lastCost)[with_custom] / (lastLinesAdded/lastCost)[without]` | ~/.claude.json, .claude/ | Ratio | Does investing in custom agents pay off? |
| D486 | Slow Machine Frustration Index | Hardware/UX | `correlation([SLOW OPERATION] logs, user_cancel_commands)` | debug/*.txt, session.jsonl | Correlation | Hardware limitations causing task abandonment |
| D487 | MCP Value-Add | Tool Utility | `success_rate(mcp__*) / success_rate(WebSearch+Bash)` for similar queries | session.jsonl | Ratio | Justifies MCP setup cost |
| D488 | Instruction Adherence Impact | Configuration Value | `correlation(CLAUDE.md_size, correction_loop_intensity)` | CLAUDE.md, session.jsonl | Correlation | Do project instructions reduce churn? |

---

## Category AL: Counterfactual Metrics (D489-D492)

These metrics measure what didn't happen or was abandoned.

| # | Metric | Category | Calculation | Data Sources | Type | Insight |
|---|--------|----------|-------------|--------------|------|---------|
| D489 | Road Not Taken (Plan Abandonment) | Planning | `count(plans/*.md never Read in subsequent sessions)` | plans/, session.jsonl | Count | Wasted planning effort |
| D490 | Ghost Tool Rate | Tool Efficiency | `count(tool_result="interrupted"/"error" AND never retried)` | session.jsonl | Ratio | Gave up on action without retry |
| D491 | Undo Reflex (Regret Rate) | Code Quality | `count(Edit WHERE next_Edit_same_file restores old_string)` | session.jsonl | Ratio | Direct measure of false starts |
| D492 | Tip Ignorance Score | Feature Discovery | `count(tips WHERE shown>3 AND feature_unused)` | ~/.claude.json | Count | Actively ignoring vs haven't discovered |

---

# Part 11: Novel Analytical Dimensions (D493-D542)

These 50 additional metrics explore entirely new analytical dimensions derived through deep analysis.

---

## Category AM: Biological & Physiological Proxies (D493-D497)

Infer physical and mental states from behavioral patterns.

| # | Metric | Category | Calculation | Data Sources | Type | Insight |
|---|--------|----------|-------------|--------------|------|---------|
| D493 | Fatigue Fingerprint | Physical State | `variance(response_times)` within session | session.jsonl | Volatility | High variance late in session = fatigue |
| D494 | Circadian Alignment Score | Biological Rhythm | `productivity(current_hour) / avg(productivity[typical_active_hours])` | stats-cache.json, session.jsonl | Ratio | Working outside optimal hours? |
| D495 | Second Wind Detection | Recovery Pattern | `productivity_spike > 1.5x avg AFTER gap > 30min` | session.jsonl | Binary | Productivity surge after breaks |
| D496 | Attention Span Proxy | Cognitive Stamina | `avg(time_before_context_switch_or_new_topic)` | session.jsonl | Duration | Sustained focus capability |
| D497 | Typing Cadence Regularity | Physiological State | `coefficient_of_variation(inter_message_time)` | session.jsonl | CV | High CV = distracted/interrupted. Low = focused |

---

## Category AN: Information Theory Metrics (D498-D502)

Apply information theory to measure efficiency and diversity.

| # | Metric | Category | Calculation | Data Sources | Type | Insight |
|---|--------|----------|-------------|--------------|------|---------|
| D498 | Prompt Compression Ratio | Communication Efficiency | `output_tokens / input_tokens` per exchange | session.jsonl | Ratio | How much work per instruction token? |
| D499 | Context Entropy | Topic Diversity | `Shannon_entropy(topics_per_session)` | session.jsonl | Entropy | High = many diverse topics. Low = focused |
| D500 | Information Gain per Dollar | Economic Value | `novel_outputs / cost` | session.jsonl | Ratio | New information generated per spend |
| D501 | Redundancy Index | Waste Detection | `count(repeated_Read_same_file + repeated_similar_WebSearch)` | session.jsonl | Count | Redundant operations indicating poor context tracking |
| D502 | Compression Efficiency | Context Management | `useful_context_preserved / total_context_before_compact` | session.jsonl | Ratio | How well does compaction preserve value? |

---

## Category AO: Predictive Metrics (D503-D507)

Early signals that predict future outcomes.

| # | Metric | Category | Calculation | Data Sources | Type | Insight |
|---|--------|----------|-------------|--------------|------|---------|
| D503 | Churn Risk Score | Project Abandonment | `P(no_session_next_7d) based on (declining_frequency + rising_errors + stale_project)` | session.jsonl, ~/.claude.json | Probability | Predict project abandonment |
| D504 | Success Predictor | Session Outcome | Features from first 5 min that predict `git_commit` in session | session.jsonl | Model | Early signals of productive sessions |
| D505 | Blocker Detection | Roadblock Warning | `count(WebSearch→WebSearch→WebSearch) + count(same_file_edited>5x)` | session.jsonl | Compound | Patterns indicating upcoming roadblock |
| D506 | Scope Creep Predictor | Planning Risk | `variance(files_touched_per_session)` increasing over project lifetime | session.jsonl | Trend | Early scope creep detection |
| D507 | Burnout Risk Score | Health Warning | `(session_length_increasing) + (error_rate_increasing) + (night_work_increasing)` | session.jsonl, stats-cache.json | Compound | Unsustainable work patterns |

---

## Category AP: Game Theory & Strategic Metrics (D508-D511)

Model strategic interactions between user and AI.

| # | Metric | Category | Calculation | Data Sources | Type | Insight |
|---|--------|----------|-------------|--------------|------|---------|
| D508 | Bargaining Efficiency | Agreement Speed | `iterations_to_reach_approach_agreement` in EnterPlanMode | session.jsonl | Count | How quickly user and AI align on strategy |
| D509 | Trust Calibration Accuracy | Calibration | `correlation(user_trust_level, actual_AI_reliability)` | session.jsonl | Correlation | Is trust appropriately calibrated to performance? |
| D510 | Delegation Optimality | Task Assignment | `success_rate(delegated_tasks) vs success_rate(direct_tasks)` | session.jsonl | Comparison | Are delegation decisions optimal? |
| D511 | Strategic Patience Score | Long-term Thinking | `count(explicit_planning_before_action) / count(immediate_action)` | session.jsonl | Ratio | Investment in planning vs rushing |

---

## Category AQ: Developmental Psychology Metrics (D512-D515)

Track skill development stages and growth patterns.

| # | Metric | Category | Calculation | Data Sources | Type | Insight |
|---|--------|----------|-------------|--------------|------|---------|
| D512 | Maturity Stage Classification | Skill Level | Feature-based classification into Novice/Intermediate/Expert | session.jsonl, ~/.claude.json | Category | Current skill tier |
| D513 | Growth Velocity | Development Speed | `d(sophistication_score) / d(time)` | session.jsonl | Rate | Rate of skill acquisition |
| D514 | Plateau Detection | Stagnation | `sessions_since(last_new_feature_adopted)` | session.jsonl | Duration | Growth stall detection |
| D515 | Regression Risk | Skill Decay | `sophisticated_feature_usage_declining` over time | session.jsonl | Trend | Losing previously acquired skills |

---

## Category AR: Systems Theory Metrics (D516-D519)

Analyze feedback loops and emergent behaviors.

| # | Metric | Category | Calculation | Data Sources | Type | Insight |
|---|--------|----------|-------------|--------------|------|---------|
| D516 | Feedback Loop Intensity | Iteration Patterns | `count(Edit→Error→Edit cycles)` / session | session.jsonl | Ratio | Strength of correction feedback loops |
| D517 | Emergent Behavior Detection | Anomaly | `distance(current_patterns, historical_patterns)` | session.jsonl | Distance | Unusual patterns not matching history |
| D518 | System Stability Index | Equilibrium | `1 / variance(session_characteristics)` over time | session.jsonl | Inverse | Stable, predictable usage vs chaotic |
| D519 | Positive Feedback Spiral | Amplification | `productivity → more_usage → more_productivity` detection | session.jsonl | Binary | Virtuous cycle detection |

---

## Category AS: Comparative & Benchmark Metrics (D520-D524)

Compare against baselines and optimal patterns.

| # | Metric | Category | Calculation | Data Sources | Type | Insight |
|---|--------|----------|-------------|--------------|------|---------|
| D520 | Efficiency Percentile | Self-Benchmark | `percentile(current_efficiency, historical_efficiency)` | session.jsonl | Percentile | Current vs personal best |
| D521 | Cost Percentile | Self-Benchmark | `percentile(current_cost, historical_cost)` | session.jsonl | Percentile | Spending relative to history |
| D522 | Optimal Session Length | Benchmarking | `session_length WHERE efficiency is maximized` | session.jsonl | Duration | Sweet spot for session duration |
| D523 | Best Practice Adherence | Compliance | `count(TDD + Planning + Testing) / possible_opportunities` | session.jsonl | Ratio | Following engineering best practices |
| D524 | Peak Performance Baseline | Target Setting | `95th_percentile(productivity_score)` | session.jsonl | Benchmark | What "great" looks like for this user |

---

## Category AT: Ecosystem & Meta-System Metrics (D525-D529)

Analyze the overall Claude Code ecosystem usage.

| # | Metric | Category | Calculation | Data Sources | Type | Insight |
|---|--------|----------|-------------|--------------|------|---------|
| D525 | Ecosystem Diversity Score | Breadth | `count(MCP_servers + hooks + agents + commands + skills)` | All config sources | Count | Total customization breadth |
| D526 | Ecosystem Growth Rate | Evolution | `d(Ecosystem_Diversity_Score) / d(time)` | All config sources | Rate | Speed of ecosystem development |
| D527 | Ecosystem Health Index | Maintenance | `(customizations_actively_used / total_customizations)` | Config + session.jsonl | Ratio | Are customizations being maintained? |
| D528 | Integration Depth | Connectivity | `count(cross-tool_dependencies)` (e.g., hook calls MCP) | All config sources | Count | How interconnected is the setup? |
| D529 | Configuration Debt | Maintenance Risk | `count(configured_but_unused_for_30d)` | All config sources | Count | Stale configurations needing cleanup |

---

## Category AU: Quality Assurance Metrics (D530-D534)

Track code quality improvements from AI assistance.

| # | Metric | Category | Calculation | Data Sources | Type | Insight |
|---|--------|----------|-------------|--------------|------|---------|
| D530 | Test Coverage Delta | QA Impact | `test_coverage_after - test_coverage_before` per session | session.jsonl, git data | Delta | AI contribution to test coverage |
| D531 | Linting Score Delta | Code Quality | `lint_score_after - lint_score_before` per session | session.jsonl, hook results | Delta | AI contribution to code quality |
| D532 | Type Safety Delta | Type Coverage | `typed_lines_after - typed_lines_before` per session | session.jsonl | Delta | AI contribution to type safety |
| D533 | Documentation Delta | Docs Quality | `doc_coverage_after - doc_coverage_before` per session | session.jsonl | Delta | AI contribution to documentation |
| D534 | Bug Introduction Rate | Quality Risk | `bugs_introduced / lines_generated` (inferred from quick fixes) | session.jsonl | Ratio | AI-introduced defect density |

---

## Category AV: Workflow Optimization Metrics (D535-D539)

Identify opportunities for workflow improvements.

| # | Metric | Category | Calculation | Data Sources | Type | Insight |
|---|--------|----------|-------------|--------------|------|---------|
| D535 | Bottleneck Detection | Workflow Analysis | `tool/step with highest wait_time / iteration_count` | session.jsonl | Identification | Where does workflow slow down? |
| D536 | Parallelization Potential | Optimization | `count(independent_tasks_run_sequentially)` | session.jsonl | Count | Tasks that could run in parallel |
| D537 | Automation Candidates | Improvement | `count(repeated_identical_sequences > 3x)` | session.jsonl | Count | Patterns that should be automated |
| D538 | Context Loading Overhead | Efficiency | `time(first_productive_action) - session_start` | session.jsonl | Duration | Time wasted on context establishment |
| D539 | Tool Selection Optimality | Decision Quality | `count(tool_switched_after_failure) / count(first_tool_success)` | session.jsonl | Ratio | First attempt tool selection accuracy |

---

## Category AW: Communication Dynamics Metrics (D540-D542)

Analyze communication patterns between human and AI.

| # | Metric | Category | Calculation | Data Sources | Type | Insight |
|---|--------|----------|-------------|--------------|------|---------|
| D540 | Clarification Burden | Communication Overhead | `count(AskUserQuestion) / total_tool_calls` | session.jsonl | Ratio | How often does AI need clarification? |
| D541 | Instruction Precision | Prompt Quality | `successful_outcomes / total_instructions` without revision | session.jsonl | Ratio | First-attempt instruction clarity |
| D542 | Conversation Convergence Rate | Alignment | `1 / iterations_to_acceptable_output` | session.jsonl | Inverse | Speed of reaching agreement |

---

## Updated Final Totals

| Type | Previous | Added | New Total |
|------|----------|-------|-----------|
| Raw data sources | 28 | 0 | **28** |
| Raw field paths | 600+ | 0 | **600+** |
| Direct metrics | 322 | 0 | **322** |
| Derived metrics | 442 | 100 | **542** |
| **TOTAL METRICS** | 764 | 100 | **864+** |

---

## Updated Metric Categories Summary

| Category | Range | Count | Focus Area |
|----------|-------|-------|------------|
| A | D001-D028 | 28 | Time & Activity |
| B | D029-D048 | 20 | Tool Usage |
| C | D049-D073 | 25 | File Operations |
| D | D074-D109 | 36 | Model & Tokens |
| E | D110-D136 | 27 | Conversation |
| F | D137-D142 | 6 | Thinking & Complexity |
| G | D143-D158 | 16 | Task Management |
| H | D159-D172 | 14 | Agent & Delegation |
| I | D173-D188 | 16 | Project Activity |
| J | D189-D203 | 15 | Error & Recovery |
| K | D204-D228 | 25 | Code Generation |
| L | D229-D238 | 10 | Web Research |
| M | D239-D252 | 14 | Hooks & Customization |
| N | D253-D259 | 7 | User Interaction |
| O | D260-D300 | 41 | Advanced Derived |
| P | D301-D343 | 43 | Previous Additions |
| Q | D344-D348 | 5 | Startup & Usage |
| R | D349-D357 | 9 | Feature Discovery |
| S | D358-D362 | 5 | Feature Flags |
| T | D363-D395 | 33 | Per-Project Analytics |
| U | D396-D399 | 4 | Subscription |
| V | D400-D411 | 12 | Project Customization |
| W | D412-D417 | 6 | MCP Server Logs |
| X | D418-D423 | 6 | Real-Time Session |
| Y | D424-D430 | 7 | Cross-Source Correlation |
| Z | D431-D442 | 12 | Behavioral Patterns |
| AA | D443-D447 | 5 | Behavioral Psychology |
| AB | D448-D452 | 5 | Learning & Mastery |
| AC | D453-D457 | 5 | Collaboration Quality |
| AD | D458-D462 | 5 | Code Quality/Architecture |
| AE | D463-D467 | 5 | Economic Efficiency |
| AF | D468-D471 | 4 | Problem-Solving |
| AG | D472-D475 | 4 | Meta-Cognitive |
| AH | D476-D478 | 3 | Network/Graph |
| AI | D479-D481 | 3 | Security/Permissions |
| AJ | D482-D484 | 3 | Temporal Dynamics |
| AK | D485-D488 | 4 | Customization ROI |
| AL | D489-D492 | 4 | Counterfactual |
| AM | D493-D497 | 5 | Biological Proxies |
| AN | D498-D502 | 5 | Information Theory |
| AO | D503-D507 | 5 | Predictive |
| AP | D508-D511 | 4 | Game Theory |
| AQ | D512-D515 | 4 | Developmental Psychology |
| AR | D516-D519 | 4 | Systems Theory |
| AS | D520-D524 | 5 | Comparative/Benchmark |
| AT | D525-D529 | 5 | Ecosystem/Meta-System |
| AU | D530-D534 | 5 | Quality Assurance |
| AV | D535-D539 | 5 | Workflow Optimization |
| AW | D540-D542 | 3 | Communication Dynamics |
| **TOTAL** | | **542** | |

---

## New Exploration Directions Identified

### Direction 13: Psychological Safety & Trust Dynamics

The metrics in categories AA-AC reveal a rich dimension of **human-AI trust dynamics**:

- **Trust Calibration**: D444 (Blind Faith), D456 (Skepticism Loop), D509 (Trust Accuracy)
- **Cognitive Load**: D443 (Hesitation), D445 (Decision Fatigue), D446 (Frustration)
- **Collaboration Quality**: D453 (Micromanagement), D508 (Bargaining Efficiency)

**Unexplored potential:**
- Trust recovery patterns after AI failures
- Trust development trajectories over months
- Optimal trust level for different task types
- Trust asymmetries (user trusts some tools more than others)

### Direction 14: Economic Behavior & Decision Making

Metrics in categories AE and AO reveal **behavioral economics** patterns:

- **Sunk Cost Effects**: D467 shows spending without resolution
- **Loss Aversion**: D466 (Cost of Correction) reveals avoidance of admitting mistakes
- **Opportunity Cost**: D463 (Haiku Optimization) reveals suboptimal resource allocation

**Unexplored potential:**
- Willingness to pay for quality vs speed tradeoffs
- Risk tolerance in model selection
- Investment patterns in learning vs producing

### Direction 15: Skill Development & Mastery Curves

Metrics in categories AB and AQ reveal **learning trajectories**:

- **Adoption Curves**: D448-D450 track feature discovery
- **Plateau Detection**: D514 identifies skill stagnation
- **Regression Risk**: D515 tracks skill decay

**Unexplored potential:**
- Learning style classification (exploratory vs structured)
- Optimal challenge level for skill growth
- Transfer learning (skills from one project help another)

### Direction 16: Code Archaeology & Technical Debt

Metrics in category AD reveal **technical debt dynamics**:

- **AI Debt**: D458 tracks code only AI has touched
- **Zombie Code**: D459 identifies fragile, confusing areas
- **Coupling**: D460 measures architectural health

**Unexplored potential:**
- Debt accumulation rate over project lifecycle
- Debt-to-value ratio (is the debt worth what it enables?)
- Refactoring ROI prediction

### Direction 17: Multi-Modal Interaction Patterns

D474 (Screenshot Development) opens up **visual-driven development**:

**Unexplored potential:**
- Image-to-code conversion efficiency
- UI fidelity (does generated code match the image?)
- Design system inference from screenshots
- Visual regression detection

### Direction 18: Collective Intelligence (Anonymized Aggregates)

If anonymized across users, these metrics could reveal:

- **Optimal patterns**: What do highly effective users do differently?
- **Common pitfalls**: What mistakes do most users make?
- **Feature utilization**: Which features provide most value?
- **Model effectiveness**: Which models work best for which tasks?

### Direction 19: AI Self-Improvement Signals

Metrics that could help Claude Code improve itself:

- **Confusion signals**: D471 (Echo Chamber), D505 (Blocker Detection)
- **Quality signals**: D530-D534 (QA deltas)
- **Efficiency signals**: D535-D539 (Workflow optimization)

### Direction 20: Resilience & Recovery Patterns

How do users and AI recover from problems?

- **Recovery time**: Time from error to resolution
- **Recovery strategy**: What approaches work best?
- **Resilience building**: Do recovery skills improve over time?
- **Breaking points**: What types of errors lead to abandonment?

---

# Part 12: Hybrid, Meta, and Philosophical Metrics (D543-D592)

These 50 additional metrics explore cross-category hybrids, meta-metrics about the metrics themselves, and philosophical/epistemological dimensions of human-AI interaction.

---

## Category AX: Hybrid Cross-Category Metrics (D543-D552)

Combine insights from multiple analytical dimensions for deeper understanding.

| # | Metric | Categories Combined | Calculation | Data Sources | Type | Insight |
|---|--------|---------------------|-------------|--------------|------|---------|
| D543 | Cognitive-Economic Efficiency | Cognitive + Economic | `(lines_generated / thinking_time) × (1 - cost_per_line)` | session.jsonl | Compound | Balance of mental effort, output, and cost |
| D544 | Trust-Performance Calibration Gap | Trust + Quality | `abs(expected_reliability - actual_reliability)` | session.jsonl | Delta | Mismatch between user trust and AI capability |
| D545 | Learning Efficiency Ratio | Learning + Economic | `skill_gain / (time + cost + cognitive_effort)` | session.jsonl, ~/.claude.json | Ratio | ROI on skill development |
| D546 | Resilience Index | Error + Recovery | `(recovery_rate × recovery_quality) / (error_frequency × error_severity)` | session.jsonl | Compound | Ability to bounce back from problems |
| D547 | Flow-Cost Tradeoff | Flow + Economic | `flow_state_duration × productivity / cost` | session.jsonl | Ratio | Optimal balance of flow and spending |
| D548 | Autonomy-Quality Ratio | Collaboration + Quality | `(tasks_completed_autonomously × quality_score) / total_tasks` | session.jsonl | Ratio | Does more AI autonomy mean better outcomes? |
| D549 | Context-Efficiency Tradeoff | Context + Efficiency | `output_quality / context_tokens_used` | session.jsonl | Ratio | Lean context vs thoroughness |
| D550 | Velocity-Stability Score | Speed + Quality | `development_speed × (1 - regression_rate)` | session.jsonl | Compound | Fast development without breaking things |
| D551 | Exploration-Exploitation Balance | Research + Action | `time_researching / time_implementing` per session | session.jsonl | Ratio | Balance between learning and doing |
| D552 | Mastery-Complexity Alignment | Skill + Difficulty | `correlation(user_skill_level, task_complexity)` | session.jsonl | Correlation | Are tasks matched to skill level? |

---

## Category AY: Meta-Metrics (Metrics About Metrics) (D553-D562)

Analyze the characteristics and reliability of the metrics themselves.

| # | Metric | Category | Calculation | Data Sources | Type | Insight |
|---|--------|----------|-------------|--------------|------|---------|
| D553 | Metric Stability Index | Reliability | `1 / variance(key_metrics)` over time | session.jsonl | Inverse | Are patterns consistent or noisy? |
| D554 | Self-Awareness Score | Meta-Cognition | `correlation(user_perceived_patterns, actual_patterns)` | session.jsonl | Correlation | Does user understand their own behavior? |
| D555 | Prediction Accuracy | Validation | `correct_predictions / total_predictions` from early signals | session.jsonl | Ratio | Do early signals actually predict outcomes? |
| D556 | Dimension Coverage | Completeness | `count(active_metric_categories) / total_categories` | session.jsonl | Ratio | How many metric dimensions are active? |
| D557 | Data Richness Score | Quality | `count(non-null_fields) / total_possible_fields` per session | session.jsonl | Ratio | Completeness of captured data |
| D558 | Metric Correlation Matrix Entropy | Independence | `Shannon_entropy(correlation_matrix)` | All metrics | Entropy | Are metrics providing independent information? |
| D559 | Outlier Concentration | Distribution | `count(metrics > 2σ) / total_metric_values` | All metrics | Ratio | How often are extreme values occurring? |
| D560 | Metric Trend Consistency | Reliability | `count(metrics_trending_same_direction) / total_trending_metrics` | All metrics | Ratio | Are indicators aligned or contradictory? |
| D561 | Signal-to-Noise Ratio | Quality | `variance(meaningful_patterns) / variance(random_fluctuations)` | session.jsonl | Ratio | Clarity of behavioral signals |
| D562 | Metric Actionability Score | Utility | `count(metrics_with_clear_action) / total_metrics` | All metrics | Ratio | How many metrics suggest concrete actions? |

---

## Category AZ: Epistemological Metrics (How Users Know) (D563-D572)

Analyze how users acquire, validate, and apply knowledge.

| # | Metric | Category | Calculation | Data Sources | Type | Insight |
|---|--------|----------|-------------|--------------|------|---------|
| D563 | First Principles Ratio | Reasoning Style | `explanatory_requests / directive_requests` | session.jsonl | Ratio | Understanding vs just doing |
| D564 | Abstraction Preference | Conceptual Level | `abstract_queries / concrete_example_requests` | session.jsonl | Ratio | High-level vs hands-on learning |
| D565 | Certainty Calibration | Epistemic Accuracy | `correlation(expressed_certainty, actual_correctness)` | session.jsonl | Correlation | Are confidence levels appropriate? |
| D566 | Knowledge Source Preference | Learning Style | Distribution of `docs_requests : example_requests : explanation_requests` | session.jsonl | Distribution | Preferred way to learn |
| D567 | Verification Depth | Epistemics | `count(secondary_verification_attempts) / count(initial_outputs)` | session.jsonl | Ratio | How thoroughly are outputs checked? |
| D568 | Hypothesis Testing Behavior | Scientific Method | `count(test→observe→revise cycles)` | session.jsonl | Count | Systematic experimentation patterns |
| D569 | Mental Model Alignment | Understanding | `prediction_accuracy(user_about_AI_behavior)` | session.jsonl | Accuracy | Does user understand how AI works? |
| D570 | Knowledge Integration Rate | Learning | `count(new_concepts_applied_in_context) / concepts_introduced` | session.jsonl | Ratio | Transfer from learning to application |
| D571 | Uncertainty Tolerance | Epistemics | `count(proceed_despite_ambiguity) / count(ambiguous_situations)` | session.jsonl | Ratio | Comfort with incomplete information |
| D572 | Belief Update Velocity | Learning | `d(expressed_opinions_about_tool) / d(evidence_encountered)` | session.jsonl | Rate | How quickly do beliefs change with evidence? |

---

## Category BA: Narrative & Story Metrics (D573-D582)

Treat sessions as stories with arcs, characters, and themes.

| # | Metric | Category | Calculation | Data Sources | Type | Insight |
|---|--------|----------|-------------|--------------|------|---------|
| D573 | Session Arc Coherence | Narrative Structure | `topic_continuity_score` throughout session | session.jsonl | Score | Does session have a clear through-line? |
| D574 | Plot Twist Detection | Narrative Events | `count(major_direction_changes_mid_session)` | session.jsonl | Count | Unexpected pivots in approach |
| D575 | Climax Identification | Narrative Peak | `timestamp(peak_effort_or_complexity_point)` | session.jsonl | Time | When does the session peak? |
| D576 | Resolution Completeness | Narrative Closure | `count(open_threads_at_end) / count(threads_started)` | session.jsonl | Inverse Ratio | How many story threads are resolved? |
| D577 | Character Development Score | User Growth | `skill_level_end - skill_level_start` per session | session.jsonl | Delta | User growth within single session |
| D578 | Conflict Intensity | Drama | `max(error_rate × correction_density)` per session | session.jsonl | Peak | Most challenging moment |
| D579 | Pacing Consistency | Rhythm | `variance(activity_intensity)` throughout session | session.jsonl | Variance | Even pace vs dramatic swings |
| D580 | Theme Coherence | Focus | `semantic_similarity(start_topic, end_topic)` | session.jsonl | Similarity | Does session stay on theme? |
| D581 | Subplot Detection | Complexity | `count(parallel_threads_active)` per session | session.jsonl | Count | Multiple simultaneous concerns |
| D582 | Denouement Quality | Ending | `productivity(last_15min) / avg(productivity)` | session.jsonl | Ratio | Does session end well? |

---

## Category BB: Phenomenological Metrics (Subjective Experience Proxies) (D583-D592)

Infer subjective experience from behavioral signals.

| # | Metric | Category | Calculation | Data Sources | Type | Insight |
|---|--------|----------|-------------|--------------|------|---------|
| D583 | Flow State Probability | Experience | `P(flow)` from `(low_errors AND consistent_pace AND low_interruptions)` | session.jsonl | Probability | Likelihood of being in flow |
| D584 | Frustration Accumulation | Affect | `integral(frustration_signals)` over session | session.jsonl | Cumulative | Total frustration burden |
| D585 | Satisfaction Proxy | Affect | `(completed_tasks × quality) / (effort + errors)` | session.jsonl | Ratio | Inferred satisfaction level |
| D586 | Engagement Intensity | Experience | `(activity_rate × session_duration) / context_switches` | session.jsonl | Compound | Deep engagement vs distracted |
| D587 | Curiosity Index | Experience | `count(exploratory_queries + voluntary_learning) / total_queries` | session.jsonl | Ratio | Intrinsic vs instrumental motivation |
| D588 | Boredom Detection | Affect | `(repetitive_patterns + declining_complexity + increasing_breaks)` | session.jsonl | Compound | Signs of disengagement |
| D589 | Accomplishment Markers | Experience | `count(task_completions + positive_language + session_closures)` | session.jsonl | Count | Sense of achievement signals |
| D590 | Overwhelm Indicators | Affect | `(context_overflow + error_clustering + retreat_to_simpler_tasks)` | session.jsonl | Compound | Signs of cognitive overload |
| D591 | Intrinsic Motivation Score | Experience | `voluntary_exploration / required_work` | session.jsonl | Ratio | Self-directed vs assigned work |
| D592 | Presence Quality | Experience | `1 / (avg_response_time × distraction_frequency)` | session.jsonl | Inverse | How "present" is the user? |

---

## Updated Final Totals (Part 12)

| Type | Previous | Added | New Total |
|------|----------|-------|-----------|
| Raw data sources | 28 | 0 | **28** |
| Raw field paths | 600+ | 0 | **600+** |
| Direct metrics | 322 | 0 | **322** |
| Derived metrics | 542 | 50 | **592** |
| **TOTAL METRICS** | 864 | 50 | **914+** |

---

## Extended Categories Summary (Parts 10-12)

| Category | Range | Count | Focus Area |
|----------|-------|-------|------------|
| AA | D443-D447 | 5 | Behavioral Psychology |
| AB | D448-D452 | 5 | Learning & Mastery |
| AC | D453-D457 | 5 | Collaboration Quality |
| AD | D458-D462 | 5 | Code Quality/Architecture |
| AE | D463-D467 | 5 | Economic Efficiency |
| AF | D468-D471 | 4 | Problem-Solving |
| AG | D472-D475 | 4 | Meta-Cognitive |
| AH | D476-D478 | 3 | Network/Graph |
| AI | D479-D481 | 3 | Security/Permissions |
| AJ | D482-D484 | 3 | Temporal Dynamics |
| AK | D485-D488 | 4 | Customization ROI |
| AL | D489-D492 | 4 | Counterfactual |
| AM | D493-D497 | 5 | Biological Proxies |
| AN | D498-D502 | 5 | Information Theory |
| AO | D503-D507 | 5 | Predictive |
| AP | D508-D511 | 4 | Game Theory |
| AQ | D512-D515 | 4 | Developmental Psychology |
| AR | D516-D519 | 4 | Systems Theory |
| AS | D520-D524 | 5 | Comparative/Benchmark |
| AT | D525-D529 | 5 | Ecosystem/Meta-System |
| AU | D530-D534 | 5 | Quality Assurance |
| AV | D535-D539 | 5 | Workflow Optimization |
| AW | D540-D542 | 3 | Communication Dynamics |
| AX | D543-D552 | 10 | Hybrid Cross-Category |
| AY | D553-D562 | 10 | Meta-Metrics |
| AZ | D563-D572 | 10 | Epistemological |
| BA | D573-D582 | 10 | Narrative/Story |
| BB | D583-D592 | 10 | Phenomenological |
| **TOTAL (Parts 10-12)** | | **150** | |

---

## Additional Novel Exploration Directions

### Direction 21: Linguistic Fingerprinting & Communication Evolution

Track how user communication style evolves over time:

- **Formality Shifts**: Is language becoming more casual or professional?
- **Technical Vocabulary Growth**: Expansion of domain-specific language
- **Pronoun Patterns**: "I" (individual) vs "we" (collaborative) vs "you" (directive to AI)
- **Imperative vs Interrogative**: Commands vs questions ratio
- **Hedging Language**: "maybe", "perhaps", "I think" frequency

### Direction 22: Attention Economics

Beyond time spent, what captures and holds attention?

- **Dwell Time Analysis**: Time spent on different output types
- **Re-read Patterns**: Which outputs are revisited?
- **Selective Attention**: What parts of responses are engaged with?
- **Attention Fragmentation**: How often is attention interrupted?

### Direction 23: Social Dynamics in Solo Use

Even individual use has social dimensions:

- **Attribution Behavior**: Does user claim credit or acknowledge AI?
- **Documentation for Others**: Comments/docs written for teammates
- **Sharing Patterns**: Exports, screenshots, copy-paste patterns
- **Professional Identity**: How does AI use affect self-perception?

### Direction 24: Ecological Integration

Relationship with broader development environment:

- **IDE Integration Depth**: How deeply integrated is Claude Code?
- **Tool Chain Position**: Where does Claude Code fit in workflow?
- **External Tool Correlation**: What other tools are used alongside?
- **Team Context Signals**: Solo vs collaborative project patterns

### Direction 25: Temporal Memory & Context Persistence

How does context carry across sessions?

- **Cross-Session Callbacks**: References to previous sessions
- **Memory Degradation Patterns**: How quickly is context lost?
- **Context Reconstruction Cost**: Effort to re-establish context
- **Long-Term Memory Efficiency**: Retention of key learnings

### Direction 26: Emergent Complexity

Patterns that only appear from aggregating simple behaviors:

- **Self-Organizing Workflows**: Patterns that emerge without explicit design
- **Attractor States**: Common stable patterns users converge to
- **Phase Transitions**: Sudden qualitative changes in usage
- **Feedback Loop Dynamics**: Reinforcing vs dampening patterns

### Direction 27: Ethical & Values Alignment

Signals about user values and ethical considerations:

- **Safety-Speed Tradeoffs**: Prioritization when they conflict
- **Quality vs Quantity Choices**: What matters more?
- **Transparency Preferences**: Documentation and explanation requests
- **Responsibility Attribution**: Who is accountable for AI output?

### Direction 28: Future-State Prediction

Use current patterns to predict future states:

- **Trajectory Modeling**: Where is the user heading?
- **Intervention Points**: When should recommendations be made?
- **Risk Horizon**: How far ahead can problems be predicted?
- **Opportunity Detection**: Upcoming chances for improvement
