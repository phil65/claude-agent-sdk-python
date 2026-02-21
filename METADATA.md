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
