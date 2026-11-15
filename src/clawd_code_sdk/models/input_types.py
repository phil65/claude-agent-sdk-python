"""Tool input type definitions for Claude Code built-in tools.

These TypedDicts define the input schemas for all built-in Claude Code tools.
They represent the JSON wire format and can be used for type-safe tool interactions.
"""

from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict

from pydantic import ConfigDict, with_config

from clawd_code_sdk.models.base import (  # noqa: TC001
    ModelName,
    PermissionMode,
    ReasoningEffort,
    ToolName,
)


_extra_allow = with_config(ConfigDict(extra="allow"))

TaskStatus = Literal["pending", "in_progress", "completed"]


@_extra_allow
class AgentInput(TypedDict):
    """Input for the Task tool. Launches a new agent to handle complex, multi-step tasks."""

    description: str
    """A short (3-5 word) description of the task."""
    prompt: str
    """The task for the agent to perform."""
    subagent_type: NotRequired[str]
    """The type of specialized agent to use for this task."""
    model: NotRequired[ModelName]
    """Optional model override for this agent.

    Takes precedence over the agent definition's model frontmatter.
    If omitted, uses the agent definition's model, or inherits from the parent."""
    # resume: NotRequired[str]
    # """Optional agent ID to resume from in order to continue from the previous exec transcript."""
    run_in_background: NotRequired[bool]
    """Whether to run the agent in the background."""
    name: NotRequired[str]
    """Name for the spawned agent."""
    team_name: NotRequired[str]
    """Team name for spawning. Uses current team context if omitted."""
    mode: NotRequired[PermissionMode]
    """Deprecated; ignored. Subagents inherit the parent session's permission mode."""
    effort: NotRequired[ReasoningEffort]
    """Reasoning effort for this agent."""
    isolation: NotRequired[Literal["worktree", "remote"]]
    """Isolation mode.

    "worktree" creates a temporary git worktree; "remote" launches the agent in a
    remote cloud environment (always runs in background)."""


@_extra_allow
class AskUserQuestionOption(TypedDict):
    """A single option for a user question."""

    label: str
    """Display text for this option (1-5 words)."""
    description: str
    """Explanation of what this option means."""
    preview: NotRequired[str]
    """Optional preview content rendered when this option is focused."""


@_extra_allow
class AskUserQuestion(TypedDict):
    """A single question to ask the user."""

    question: str
    """The complete question to ask. Should be clear, specific, and end with a question mark."""
    header: str
    """Very short label displayed as a chip/tag (max 12 chars)."""
    options: list[AskUserQuestionOption]
    """The available choices (2-4 options). An "Other" option is automatically provided."""
    multiSelect: bool
    """Set to true to allow multiple selections."""


@_extra_allow
class AskUserQuestionInput(TypedDict):
    """Input for the AskUserQuestion tool."""

    questions: list[AskUserQuestion]
    """Questions to ask the user (1-4 questions)."""
    answers: NotRequired[dict[str, str]]
    """User answers populated by the permission system.

    Maps question text to selected option label(s).
    Multi-select answers are comma-separated.
    """


@_extra_allow
class BashInput(TypedDict):
    """Input for the Bash tool. Executes bash commands in a persistent shell session."""

    command: str
    """The command to execute."""
    timeout: NotRequired[int]
    """Optional timeout in milliseconds (max 600000)."""
    description: NotRequired[str]
    """Clear, concise description of what this command does in 5-10 words."""
    run_in_background: NotRequired[bool]
    """Set to true to run this command in the background."""


@_extra_allow
class BashOutputInput(TypedDict):
    """Input for the BashOutput tool. Retrieves output from a background bash shell."""

    bash_id: str
    """The ID of the background shell to retrieve output from."""
    filter: NotRequired[str]
    """Optional regex to filter output lines."""


@_extra_allow
class FileEditInput(TypedDict):
    """Input for the Edit tool. Performs exact string replacements in files."""

    file_path: str
    """The absolute path to the file to modify."""
    old_string: str
    """The text to replace."""
    new_string: str
    """The text to replace it with (must be different from old_string)."""
    replace_all: NotRequired[bool]
    """Replace all occurrences of old_string (default false)."""


@_extra_allow
class FileReadInput(TypedDict):
    """Input for the Read tool. Reads files including text, images, PDFs, and notebooks."""

    file_path: str
    """The absolute path to the file to read."""
    offset: NotRequired[int]
    """The line number to start reading from.

    Only provide if the file is too large to read at once."""
    limit: NotRequired[int]
    """The number of lines to read. Only provide if the file is too large to read at once"""
    pages: NotRequired[str]
    """Page range for PDF files (e.g., "1-5", "3", "10-20"). Only applicable to PDF files.

    Maximum 20 pages per request."""
    allow_large: NotRequired[bool]
    """Read a text file (or line range) that is over the usual size limits."""


@_extra_allow
class FileWriteInput(TypedDict):
    """Input for the Write tool. Writes a file to the local filesystem."""

    file_path: str
    """The absolute path to the file to write."""
    content: str
    """The content to write to the file."""


@_extra_allow
class GlobInput(TypedDict):
    """Input for the Glob tool. Fast file pattern matching."""

    pattern: str
    """The glob pattern to match files against."""
    path: NotRequired[str]
    """The directory to search in (defaults to cwd)."""


# GrepInput uses the functional TypedDict form because the TypeScript interface
# uses ripgrep-style flag names ("-i", "-n", "-B", "-A", "-C") that are not
# valid Python identifiers.
GrepInput = TypedDict(
    "GrepInput",
    {
        "pattern": str,
        "path": NotRequired[str],
        "glob": NotRequired[str],
        "type": NotRequired[str],
        "output_mode": NotRequired[Literal["content", "files_with_matches", "count"]],
        "-i": NotRequired[bool],
        "-n": NotRequired[bool],
        "-o": NotRequired[bool],
        "-B": NotRequired[int],
        "-A": NotRequired[int],
        "-C": NotRequired[int],
        "head_limit": NotRequired[int],
        "multiline": NotRequired[bool],
    },
)
"""Input for the Grep tool. Powerful search built on ripgrep with regex support."""
GrepInput.__pydantic_config__ = ConfigDict(extra="allow")  # type: ignore[attr-defined]


@_extra_allow
class KillShellInput(TypedDict):
    """Input for the KillBash tool. Kills a running background bash shell."""

    shell_id: str
    """The ID of the background shell to kill."""


@_extra_allow
class NotebookEditInput(TypedDict):
    """Input for the NotebookEdit tool. Edits cells in Jupyter notebook files."""

    notebook_path: str
    """The absolute path to the Jupyter notebook file."""
    new_source: str
    """The new source for the cell."""
    cell_id: NotRequired[str]
    """The ID of the cell to edit."""
    cell_type: NotRequired[Literal["code", "markdown"]]
    """The type of the cell (code or markdown)."""
    edit_mode: NotRequired[Literal["replace", "insert", "delete"]]
    """The type of edit (replace, insert, delete)."""


@_extra_allow
class WebFetchInput(TypedDict):
    """Input for the WebFetch tool. Fetches content from a URL and processes it with AI."""

    url: str
    """The URL to fetch content from."""
    prompt: str
    """The prompt to run on the fetched content."""
    offset: NotRequired[int]
    """Character position in the page text to start reading from."""


@_extra_allow
class WebSearchInput(TypedDict):
    """Input for the WebSearch tool. Searches the web and returns formatted results."""

    query: str
    """The search query to use."""
    allowed_domains: NotRequired[list[str]]
    """Only include results from these domains."""
    blocked_domains: NotRequired[list[str]]
    """Never include results from these domains."""


@_extra_allow
class TodoItem(TypedDict):
    """A single todo item."""

    content: str
    """The task description."""
    status: TaskStatus
    """The task status."""
    activeForm: str
    """Active form of the task description."""


@_extra_allow
class TodoWriteInput(TypedDict):
    """Input for the TodoWrite tool. Creates and manages a structured task list."""

    todos: list[TodoItem]
    """The updated todo list."""


@_extra_allow
class EnterWorktreeInput(TypedDict):
    """Input for the EnterWorktree tool."""

    name: NotRequired[str]
    """Optional name for the worktree. A random name is generated if not provided."""
    path: NotRequired[str]
    """Path to an existing worktree of the current repo to switch into instead of creating new one.

    Must appear in `git worktree list` for the current repo. Mutually exclusive with `name`.
    """


@_extra_allow
class ExitWorktreeInput(TypedDict):
    """Input for the ExitWorktree tool."""

    action: Literal["keep", "remove"]
    """'keep' leaves the worktree and branch on disk; 'remove' deletes both."""
    discard_changes: NotRequired[bool]
    """Required true when action is 'remove' and worktree has uncommitted files / unmerged commits.

    The tool will refuse and list them otherwise."""


@_extra_allow
class SkillInput(TypedDict):
    """Input for the Skill tool. Invokes a named skill (slash command).

    Not part of the official SDK ToolInputSchemas as of SDK v0.2.62.
    Shape derived from empirical testing.
    """

    skill: str
    """The skill name (e.g., "commit", "review", "debug")."""
    args: NotRequired[str]
    """Optional arguments for the skill."""


@_extra_allow
class ToolSearchInput(TypedDict):
    """Input for the ToolSearch tool. Searches for and selects tools by name or query."""

    query: str
    """Search query or 'select:<tool_name>' to select a specific tool."""
    max_results: NotRequired[int]
    """Maximum number of tool references to return."""


@_extra_allow
class EnterPlanModeInput(TypedDict):
    """Input for the EnterPlanMode tool. Enters planning mode.

    Not part of the official SDK ToolInputSchemas as of SDK v0.2.62.
    Shape derived from empirical testing.
    """


@_extra_allow
class ExitPlanModeInput(TypedDict):
    """Input for the ExitPlanMode tool. Exits planning mode for user approval."""

    plan: str
    """The plan to run by the user for approval."""


@_extra_allow
class ListMcpResourcesInput(TypedDict):
    """Input for the ListMcpResources tool. Lists available MCP resources."""

    server: NotRequired[str]
    """Optional server name to filter resources by."""


@_extra_allow
class ReadMcpResourceInput(TypedDict):
    """Input for the ReadMcpResource tool. Reads a specific MCP resource from a server."""

    server: str
    """The MCP server name."""
    uri: str
    """The resource URI to read."""


# ---------------------------------------------------------------------------
# Tools added in SDK 0.3.x
# ---------------------------------------------------------------------------


@_extra_allow
class TaskStopInput(TypedDict):
    """Input for the TaskStop tool."""

    task_id: NotRequired[str]
    """The ID of the background task to stop.

    Agent-team teammates and named background agents are also accepted by agent ID or name.
    """
    shell_id: NotRequired[str]
    """Deprecated: use task_id instead"""


@_extra_allow
class RefreshMcpToolsInput(TypedDict):
    """Input for the RefreshMcpTools tool."""

    server: NotRequired[str]
    """Optional server name: refresh only this server. Omit to refresh all connected servers."""


@_extra_allow
class ReadMcpResourceDirInput(TypedDict):
    """Input for the ReadMcpResourceDir tool."""

    server: str
    """The MCP server name"""
    uri: str
    """The directory resource URI to list"""


@_extra_allow
class ReportFindingsFinding(TypedDict):
    """``finding`` entry of ReportFindings."""

    file: str
    """Repo-relative path of the file the finding is in"""
    line: NotRequired[int]
    """1-indexed line the finding anchors to"""
    summary: str
    """One-sentence statement of the defect"""
    short_summary: NotRequired[str]
    """Compressed label for compact UI (≤60 chars): the claim alone, no rationale or consequence
    clause
    """
    failure_scenario: str
    """Concrete inputs/state → wrong output/crash"""
    category: NotRequired[str]
    """Short kebab-case slug of the finding type, e.g.

    "correctness", "simplification", "efficiency", "test-coverage"
    """
    verdict: NotRequired[Literal["CONFIRMED", "PLAUSIBLE"]]
    """Set when a verify pass ran; absent on inline-only reviews"""
    outcome: NotRequired[Literal["fixed", "skipped", "no_change_needed"]]
    """Set ONLY when re-reporting after applying fixes: what happened to this finding"""


@_extra_allow
class ReportFindingsInput(TypedDict):
    """Input for the ReportFindings tool."""

    level: NotRequired[Literal["low", "medium", "high", "xhigh", "max"]]
    """Effort level the review ran at"""
    findings: list[ReportFindingsFinding]
    """Verified findings, most-severe first; empty if none survived @maxItems 32"""


@_extra_allow
class SendFeedbackInput(TypedDict):
    """Input for the SendFeedback tool."""

    type: Literal["bug", "idea", "missing_capability"]
    """What kind of feedback this is."""
    title: str
    """Short, specific one-line summary of the issue."""
    details: str
    """Labeled bullets, in order: **What happened:** (observed vs.

    expected, exact error text if short); **What the user said:** (quoted, or "User didn't comment;
    observed by the model."); **Repro:** (minimal steps); **Evidence:** (request IDs, timestamps,
    paths, versions; omit if none); optionally a final **Cause:** only if verified in-session. One
    to three lines per bullet. No narrative paragraphs, no speculation, no secrets.
    """
    area: NotRequired[str]
    """Optional short tag naming the part of Claude Code this is about (e.g.

    "hooks config", "/help", "file editing"). Leave blank if unclear.
    """
    failure_mode: NotRequired[
        Literal[
            "instruction_following",
            "destructive_actions",
            "code_quality",
            "repetition_and_looping",
            "model_regression",
            "overconfidence_and_hallucination",
            "context_and_memory",
            "overeager",
            "over_correction",
            "stopping_short",
            "dispute_or_decline",
            "subagent_overspawn",
            "tone_or_preachiness",
            "excessive_questions",
            "unwanted_scope",
            "other",
        ]
    ]
    """When the report is about MODEL BEHAVIOR (not a product bug), the closest failure mode, or
    `other` when it is a model-behavior issue that fits no listed value.

    Omit only when the report is a product/tool bug with no model-behavior component.
    """
    task_category: NotRequired[
        Literal["code_edit", "debug", "explain", "plan", "shell", "search", "review", "other"]
    ]
    """What kind of task the session was doing when the issue occurred, or `other` when it is a
    clear task that fits no listed value.

    Omit only if genuinely unclear.
    """


@_extra_allow
class ClaudeDesignInput(TypedDict):
    """Input for the ClaudeDesign tool."""

    operation: str
    """Claude Design action to perform.

    Call with "list" first to discover the available operations and their argument schemas.
    """
    arguments: dict[str, Any]
    """Action input object (server-validated). Pass {} for operations that take no input."""


@_extra_allow
class ProjectsInput(TypedDict):
    """Input for the Projects tool."""

    method: Literal[
        "project_info",
        "project_read",
        "project_search",
        "project_write",
        "project_delete",
        "project_memory_list",
        "project_memory_read",
    ]
    path: NotRequired[str]
    """project_read/project_write/project_delete: doc path.

    project_write: an existing path is replaced in place; a new bare filename (no "/") is namespaced
    to "claude/<name>". project_memory_read: memory file path as listed by project_memory_list.
    """
    content: NotRequired[str]
    """project_write: inline doc text.

    Mutually exclusive with local_path. Use local_path for anything you have on disk.
    """
    local_path: NotRequired[str]
    """project_write: a file inside the working directory to upload.

    The tool reads, encodes, and uploads directly — contents never enter your context. Mutually
    exclusive with content.
    """
    present_to_user: NotRequired[bool]
    """project_write: true marks this doc as the file the user needs to see — the deliverable they
    asked for or must act on.

    Defaults to false; leave it unset for routine saves, notes, and bulk writes.
    """
    query: NotRequired[str]
    """project_search: knowledge-base query"""
    n: NotRequired[int]
    """project_search: number of hits (default 5)"""


@_extra_allow
class TaskCreateInput(TypedDict):
    """Input for the TaskCreate tool."""

    subject: str
    """A brief title for the task"""
    description: str
    """What needs to be done"""
    activeForm: NotRequired[str]
    """Present continuous form shown in spinner when in_progress (e.g., "Running tests")"""
    metadata: NotRequired[dict[str, Any]]
    """Arbitrary metadata to attach to the task"""


@_extra_allow
class TaskGetInput(TypedDict):
    """Input for the TaskGet tool."""

    taskId: str
    """The ID of the task to retrieve"""


@_extra_allow
class TaskUpdateInput(TypedDict):
    """Input for the TaskUpdate tool."""

    taskId: str
    """The ID of the task to update"""
    subject: NotRequired[str]
    """New subject for the task"""
    description: NotRequired[str]
    """New description for the task"""
    activeForm: NotRequired[str]
    """Present continuous form shown in spinner when in_progress (e.g., "Running tests")"""
    status: NotRequired[Literal["deleted", "pending", "in_progress", "completed"]]
    """New status for the task"""
    addBlocks: NotRequired[list[str]]
    """Task IDs that this task blocks"""
    addBlockedBy: NotRequired[list[str]]
    """Task IDs that block this task"""
    owner: NotRequired[str]
    """New owner for the task"""
    metadata: NotRequired[dict[str, Any]]
    """Metadata keys to merge into the task. Set a key to null to delete it."""


@_extra_allow
class TaskListInput(TypedDict):
    """Input for the TaskList tool."""


@_extra_allow
class WorkflowInput(TypedDict):
    """Input for the Workflow tool."""

    script: NotRequired[str]
    """Self-contained workflow script.

    Must begin with `export const meta = { name, description, phases }` (pure literal, no computed
    values) followed by the script body using agent()/parallel()/pipeline()/phase().
    """
    name: NotRequired[str]
    """Name of a predefined workflow (built-in or from .claude/workflows/).

    Resolves to a self-contained script.
    """
    description: NotRequired[str]
    """Ignored — set the workflow description in the script's `meta` block."""
    title: NotRequired[str]
    """Ignored — set the workflow title in the script's `meta` block."""
    args: NotRequired[dict[str, Any]]
    """Optional input value exposed to the script as the global `args`, verbatim.

    Pass arrays/objects as actual JSON values, NOT as a JSON-encoded string — a stringified list
    breaks `args.filter`/`args.map` in the script. Use for parameterized named workflows (e.g. a
    research question).
    """
    scriptPath: NotRequired[str]
    """Path to a workflow script file on disk.

    Every Workflow invocation persists its script under the session directory and returns the path
    in the tool result. To iterate, edit that file with Write/Edit and re-invoke Workflow with the
    same `scriptPath` instead of re-sending the full script. Takes precedence over `script` and
    `name`.
    """
    resumeFromRunId: NotRequired[str]
    """Run ID of a prior Workflow invocation to resume from.

    Completed agent() calls with unchanged (prompt, opts) return their cached results instantly;
    only edited or new calls re-run. Same-session only. Stop the prior run first (TaskStop) before
    resuming.
    """


@_extra_allow
class CronCreateInput(TypedDict):
    """Input for the CronCreate tool."""

    cron: str
    """Standard 5-field cron expression in local time: "M H DoM Mon DoW" (e.g.

    "* /5 * * * *" = every 5 minutes, "30 14 28 2 *" = Feb 28 at 2:30pm local once).
    """
    prompt: str
    """The prompt to enqueue at each fire time."""
    recurring: NotRequired[bool]
    """true (default) = fire on every cron match until deleted or auto-expired after 7 days.

    false = fire once at the next match, then auto-delete. Use false for "remind me at X" one-shot
    requests with pinned minute/hour/dom/month.
    """
    durable: NotRequired[bool]
    """true = persist to .claude/scheduled_tasks.json and survive restarts.

    false (default) = in-memory only, dies when this Claude session ends. Use true only when the
    user asks the task to survive across sessions.
    """


@_extra_allow
class CronDeleteInput(TypedDict):
    """Input for the CronDelete tool."""

    id: str
    """Job ID returned by CronCreate."""


@_extra_allow
class CronListInput(TypedDict):
    """Input for the CronList tool."""


@_extra_allow
class ScheduleWakeupInput(TypedDict):
    """Input for the ScheduleWakeup tool."""

    delaySeconds: NotRequired[float]
    """Seconds from now to wake up.

    Clamped to [60, 3600] by the runtime. Required unless `stop` is true.
    """
    reason: NotRequired[str]
    """One short sentence explaining the chosen delay.

    Goes to telemetry and is shown to the user. Be specific. Required unless `stop` is true.
    """
    prompt: NotRequired[str]
    """The /loop input to fire on wake-up.

    Pass the same /loop input verbatim each turn so the next firing re-enters the skill and
    continues the loop. For autonomous /loop (no user prompt), pass the literal sentinel
    `<<autonomous-loop-dynamic>>` instead (the dynamic-pacing variant, not the CronCreate-mode
    `<<autonomous-loop>>`). Required unless `stop` is true.
    """
    stop: NotRequired[bool]
    """Set to true to end the dynamic loop immediately instead of scheduling another wakeup.

    When true, all other fields are ignored and no further wakeups fire.
    """
    noop: NotRequired[bool]
    """true = nothing changed (you checked and there is nothing to report).

    false = something happened worth keeping (edited a file, posted a message, advanced state,
    surfaced a finding). Consecutive noop:true ticks are collapsed in the user's terminal view and
    tracked as a streak. Required unless `stop` is true.
    """


@_extra_allow
class RemoteTriggerInput(TypedDict):
    """Input for the RemoteTrigger tool."""

    action: Literal[
        "list",
        "get",
        "create",
        "update",
        "run",
        "create_webhook_trigger",
        "list_runs",
        "get_run_log",
    ]
    trigger_id: NotRequired[str]
    """Required for get, update, run, and list_runs"""
    session_id: NotRequired[str]
    """Required for get_run_log: a run session id (cse_… or session_…, from list_runs)"""
    cursor: NotRequired[str]
    """The next_cursor from the previous page of the same listing (list_runs with the same
    trigger_id, or get_run_log with the same session_id), passed back unchanged.

    Not an offset, a count or an event number.
    """
    body: NotRequired[dict[str, Any]]
    """Required for create and update; optional for run"""


@_extra_allow
class ShowOnboardingRolePickerInput(TypedDict):
    """Input for the ShowOnboardingRolePicker tool."""


@_extra_allow
class OfferChromeSetupInput(TypedDict):
    """Input for the OfferChromeSetup tool."""

    reason: NotRequired[str]
    """A short phrase naming what the task needs the user's own browser for."""


@_extra_allow
class ReadNotificationsInput(TypedDict):
    """Input for the ReadNotifications tool."""


@_extra_allow
class MonitorWs(TypedDict):
    """``ws`` entry of Monitor."""

    url: str
    protocols: NotRequired[list[str]]


@_extra_allow
class MonitorInput(TypedDict):
    """Input for the Monitor tool."""

    description: str
    """Short human-readable description of what you are monitoring (shown in notifications)."""
    timeout_ms: float
    """Kill the monitor after this deadline.

    Default 300000ms. Deadlines above 1800000ms are capped to 1800000ms. You are notified at expiry
    and can re-arm.
    """
    command: NotRequired[str]
    """Shell command or script. Each stdout line is an event; exit ends the watch."""
    ws: NotRequired[MonitorWs]
    """WebSocket to open.

    Each text frame is an event; binary frames are reported as a placeholder line. Socket close ends
    the watch. Cannot be combined with command.
    """


@_extra_allow
class ProposeSkillsProposalEdit(TypedDict):
    """``edit`` entry of ProposeSkillsProposal."""

    old_string: str
    """Text to replace. It must occur exactly once in that SKILL.md"""
    new_string: str
    """Text to put in its place"""


@_extra_allow
class ProposeSkillsProposal(TypedDict):
    """``proposal`` entry of ProposeSkills."""

    name: str
    """kebab-case skill slug; must not contain "claude" or "anthropic"; at most 64 characters for a
    new skill
    """
    kind: Literal["new", "improvement"]
    target: NotRequired[str]
    """Name of the existing skill to update. Required when kind is 'improvement'; omit for 'new'."""
    description: str
    """One short sentence saying when to use this skill: aim for under 200 characters, never more
    than 1024, and no angle brackets.

    Shown on the review card and saved as the skill's description, which is what decides when the
    skill is used. For an improvement, reuse the existing skill's description unless the change
    alters when the skill applies.
    """
    evidence: NotRequired[list[str]]
    """memory file paths where this procedure was observed"""
    edits: NotRequired[list[ProposeSkillsProposalEdit | list[ProposeSkillsProposalEdit]]]
    """For an improvement, in place of skillMd: your changes to the skill's SKILL.md, applied in
    order.

    They apply to that file as it is now, not to an earlier proposal of yours. The card shows the
    whole updated file. The name and description come from the fields above, not from the
    frontmatter. @minItems 1 @maxItems 100
    """
    skillMd: NotRequired[str]
    """For a new skill or a full rewrite.

    The complete SKILL.md exactly as it should be saved: frontmatter plus the full body. When the
    user saves, the body below the frontmatter becomes the skill's entire instructions and the name
    and description come from the fields above; other frontmatter keys are not kept. For an
    improvement this replaces the existing skill's SKILL.md entirely, so read that skill's current
    SKILL.md first and include everything worth keeping, not only the changes.
    """


@_extra_allow
class ProposeSkillsInput(TypedDict):
    """Input for the ProposeSkills tool."""

    proposals: list[ProposeSkillsProposal]
    """@minItems 1 @maxItems 3"""


@_extra_allow
class ProposeGoalInput(TypedDict):
    """Input for the ProposeGoal tool."""

    condition: str
    """The completion condition to propose, written so a separate evaluator can verify it from the
    conversation (e.g.

    "all tests in test/auth pass (bun test exits 0)"). At most 500 characters — the user must be
    able to read the whole condition in the approval dialog.
    """
    ask_user: NotRequired[bool]
    """Whether to ask the user for approval before the goal is set.

    Defaults to true — an approval dialog is shown. Set false ONLY when the user's own words in this
    conversation stated this outcome as what they want; the goal is then set directly, with a
    visible notice in the transcript, and the user can clear it with /goal clear.
    """


@_extra_allow
class ArtifactInput(TypedDict):
    """Input for the Artifact tool."""

    action: NotRequired[
        Literal[
            "publish",
            "list",
            "read",
            "list_types",
            "watch",
            "unwatch",
            "status",
            "upload_asset",
            "list_assets",
            "read_asset",
            "delete_asset",
            "pin",
            "unpin",
        ]
    ]
    """Omit (or 'publish') to publish file_path.

    'list' enumerates artifacts — the user's own by default, see `scope`; only `limit`, `scope` and
    `page_token` may accompany it. 'read' returns the content of the published artifact at `url`
    (raw HTML for the user's own; an isolated summary, steered by the optional `prompt`, for one
    someone else owns, though a page published in this session's own Slack channel can come back in
    full as untrusted content) — see **Calls**. 'watch', 'unwatch', and 'status' manage live-update
    subscriptions through which a session keeps track of new versions of an artifact published
    elsewhere, and those aren't available in this session: 'watch' only reports that — this session
    does not keep track of new versions — and 'status' lists this session's artifact watches (pass
    `url` to check one). 'upload_asset' adds one local media, PDF, font, or text file to an existing
    artifact — pass `url` and `file_path` (or `file_paths` for several in one call). 'list_assets'
    lists the files in an artifact's asset store (pass `url`; `after` continues a listing),
    'read_asset' saves one of them to a local file named by its id (pass `url` and `asset_id`,
    optionally `out_dir`), and 'delete_asset' permanently removes one (pass `url` and `asset_id`).
    See **Artifact assets** above. 'pin' adds the artifact at `url` to the user's pinned list in
    their claude.ai sidebar and 'unpin' removes it (nothing else may accompany either) — private to
    the user, reversible, and no change to who can see the artifact.
    """
    file_path: NotRequired[str]
    """Path to the .html file to render.

    Required to publish (the default action). Use a short, distinctive basename — it is the last-
    resort title when the HTML has no <title> and no `title` parameter is given. For 'upload_asset',
    the local image, video, PDF, font, stylesheet (CSS), script (JS), or text (CSV, Markdown, JSON,
    plain text) file to upload.
    """
    favicon: NotRequired[str]
    """Deprecated; omit it. Use `icon`."""
    icon: NotRequired[str]
    """One short generic word for the artifact's browser-tab icon, such as chart, calendar, recipe,
    code or map — a plain signifier, not a product or brand name.

    Include it on every page's first publish; omit when republishing to keep the current icon, and
    pass a new one only when the user asks.
    """
    limit: NotRequired[int]
    """list only: maximum artifacts to return (default 25)."""
    page_token: NotRequired[str]
    """list only: the `next_page_token` a listing of the same scope gave, to list the artifacts
    after it.
    """
    scope: NotRequired[Literal["mine", "shared", "all"]]
    """list only: 'mine' (default) lists artifacts the user owns; 'shared' lists artifacts other
    people shared with the user; 'all' lists both.

    Rows are labeled (mine)/(shared) whenever scope is not 'mine'.
    """
    title: NotRequired[str]
    """Title for the artifact — the name shown in the browser tab and gallery.

    A short, distinctive noun-phrase name — not a generic label, a summary, or a name with an
    appended explainer. Prefer a <title> tag at the top of the HTML itself; this parameter fills in
    only when the file lacks one in the first 8KB of the file, and never overrides the tag. HTML
    publishes only — Markdown pages keep their filename identity. Content always comes from
    file_path — there is no inline content parameter.
    """
    description: NotRequired[str]
    """One-sentence subtitle shown on the gallery card. Say what the page is or does."""
    label: NotRequired[str]
    """A short name for this publish, max 60 chars (e.g.

    "Draft to legal"). Optional — a few words, not a description.
    """
    url: NotRequired[str]
    """An existing artifact's claude.ai link (claude.ai/artifact/{id} or
    claude.ai/code/artifact/{uuid}; a chat, project or session link is not one) to update in
    place.

    Pass whenever the user wants to update an artifact this conversation did not publish — "update
    my artifact", "keep the same link", a pasted artifact URL — and find the URL with action: "list"
    or ask the user for the link if you don't have it; without this, the publish creates a separate
    artifact instead of updating the existing one. Omit for new artifacts and same-conversation
    redeploys. Must be an artifact the user owns or was given edit access to (a read of it says
    "writer"). Before publishing to an artifact this conversation has neither read nor published,
    read it (action: "read") and build on what comes back; a publish sent without that read is
    refused. A refusal that hands you the live version counts as that read: merge your edits into
    that version and publish that; never resend the refused content unchanged. For 'read' and the
    other url-addressed actions: the artifact to act on.
    """
    prompt: NotRequired[str]
    """read only: what to extract from an artifact shared with the user — its content reaches you as
    an isolated summary answering this.

    Ignored for artifacts the user owns and for a page published in this session's own Slack channel
    (raw content is returned); optional.
    """
    force: NotRequired[bool]
    """Last-resort overwrite that DISCARDS the newer published version's page — another session's
    publish, or someone's save from a page that can publish new versions of itself.

    On a conflict the fix is to merge your changes onto the newer content (handed to you in the
    rejection, or re-read) and publish again — not force. Pass force:true only when the user has
    explicitly said to discard that specific version; never to get past a conflict on your own
    judgment. The tracked baseVersion is still sent; with force:true the server treats it as
    informational and overwrites, unless it refuses force over a version saved from inside the page.
    Omit (or false) so a concurrent write conflicts instead of being silently clobbered.
    """
    pin: NotRequired[bool]
    """publish only: true also pins the published artifact to the user's claude.ai sidebar once it
    is published — pass it only when the user asked for that; a pin that fails never fails the
    publish (the result says so).
    """
    out_dir: NotRequired[str]
    """read_asset: directory to save into — default: this artifact's folder in your scratchpad
    directory, where saving needs no approval and which you can Read from.

    read_asset names the file by the asset id plus the extension for its type; saving to any
    directory other than the default is an ordinary file save the user may be asked to approve.
    """
    file_paths: NotRequired[list[list[str] | str]]
    """upload_asset: several local image, video, PDF, font, stylesheet or script files in place of
    `file_path`, up to 25 in one call, all into the artifact that `url` names; one approval
    covers the call, and the result lists each file's id and url, or why it was not uploaded.

    A CSV, Markdown, JSON or plain-text file, a symbolic or hard link, and a file outside the
    working directory each go in a call of their own with `file_path`. @minItems 1 @maxItems 25
    """
    asset_id: NotRequired[str]
    """read_asset and delete_asset: the asset's id (32 hex characters), from a list_assets or
    upload_asset result.
    """
    after: NotRequired[str]
    """list_assets only: the `next` value from a previous list_assets result, to continue that
    listing.
    """
    capabilities: NotRequired[dict[str, Any]]
    """Runtime capabilities this page declares, as {name: config}.

    The control plane is the authority on valid names and config shapes. An empty object clears any
    previously stored declaration; omit the field on a redeploy to carry the stored declaration
    forward unchanged. Before declaring any capability, load the `artifact-capabilities` skill for
    the current contract and per-capability guidance.
    """
    contract: NotRequired[Literal["latest"] | str]  # noqa: PYI051
    """The artifact's runtime version.

    Omit to keep its current version (the default); 'latest' to upgrade; a specific version to pin
    or roll back. Changing it changes how the published page behaves — pass only when the author
    explicitly intends the change, never as a side effect of editing.
    """


@_extra_allow
class PushNotificationInput(TypedDict):
    """Input for the PushNotification tool."""

    message: str
    """The notification body. Keep it under 200 characters; mobile OSes truncate."""
    status: NotRequired[Literal["proactive"]]


ToolInput = (
    AgentInput
    | AskUserQuestionInput
    | BashInput
    | BashOutputInput
    | FileEditInput
    | FileReadInput
    | FileWriteInput
    | GlobInput
    | GrepInput
    | KillShellInput
    | NotebookEditInput
    | WebFetchInput
    | WebSearchInput
    | TodoWriteInput
    | EnterWorktreeInput
    | ExitWorktreeInput
    | ExitPlanModeInput
    | ListMcpResourcesInput
    | ReadMcpResourceInput
    | SkillInput
    | EnterPlanModeInput
    | ToolSearchInput
    | TaskStopInput
    | RefreshMcpToolsInput
    | ReadMcpResourceDirInput
    | ReportFindingsInput
    | SendFeedbackInput
    | ClaudeDesignInput
    | ProjectsInput
    | TaskCreateInput
    | TaskGetInput
    | TaskUpdateInput
    | TaskListInput
    | WorkflowInput
    | CronCreateInput
    | CronDeleteInput
    | CronListInput
    | ScheduleWakeupInput
    | RemoteTriggerInput
    | ShowOnboardingRolePickerInput
    | OfferChromeSetupInput
    | ReadNotificationsInput
    | MonitorInput
    | ProposeSkillsInput
    | ProposeGoalInput
    | ArtifactInput
    | PushNotificationInput
)

#: Mapping from tool name to its input type.
TOOL_INPUT_TYPES: dict[ToolName, type[ToolInput]] = {
    "Task": AgentInput,
    "AskUserQuestion": AskUserQuestionInput,
    "Bash": BashInput,
    "BashOutput": BashOutputInput,
    "Edit": FileEditInput,
    "Read": FileReadInput,
    "Write": FileWriteInput,
    "Glob": GlobInput,
    "Grep": GrepInput,
    "KillBash": KillShellInput,
    "NotebookEdit": NotebookEditInput,
    "WebFetch": WebFetchInput,
    "WebSearch": WebSearchInput,
    "TodoWrite": TodoWriteInput,
    "EnterWorktree": EnterWorktreeInput,
    "ExitWorktree": ExitWorktreeInput,
    "ExitPlanMode": ExitPlanModeInput,
    "ListMcpResources": ListMcpResourcesInput,
    "ReadMcpResource": ReadMcpResourceInput,
    "Skill": SkillInput,
    "EnterPlanMode": EnterPlanModeInput,
    "ToolSearch": ToolSearchInput,
    # Current (0.3.x) tool names
    "Agent": AgentInput,
    "TaskStop": TaskStopInput,
    "ListMcpResourcesTool": ListMcpResourcesInput,
    "ReadMcpResourceTool": ReadMcpResourceInput,
    "ReadMcpResourceDirTool": ReadMcpResourceDirInput,
    "ReportFindings": ReportFindingsInput,
    "SendFeedback": SendFeedbackInput,
    "ClaudeDesign": ClaudeDesignInput,
    "Projects": ProjectsInput,
    "TaskCreate": TaskCreateInput,
    "TaskGet": TaskGetInput,
    "TaskUpdate": TaskUpdateInput,
    "TaskList": TaskListInput,
    "Workflow": WorkflowInput,
    "CronCreate": CronCreateInput,
    "CronDelete": CronDeleteInput,
    "CronList": CronListInput,
    "ScheduleWakeup": ScheduleWakeupInput,
    "RemoteTrigger": RemoteTriggerInput,
    "ShowOnboardingRolePicker": ShowOnboardingRolePickerInput,
    "OfferChromeSetup": OfferChromeSetupInput,
    "ReadNotifications": ReadNotificationsInput,
    "Monitor": MonitorInput,
    "propose_skills": ProposeSkillsInput,
    "ProposeGoal": ProposeGoalInput,
    "Artifact": ArtifactInput,
    "PushNotification": PushNotificationInput,
}
