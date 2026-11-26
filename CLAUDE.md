Spec versions this SDK targets (Claude Code CLI, TS SDK types, settings schema): see `AGENTS.md`.

# Workflow

```bash
uv sync --all-extras

# Lint and style (versions pinned in the `lint` dependency group)
uv run ruff check . --fix
uv run ruff format .

# Typecheck (only src/, see [tool.ty.src])
uv run ty check

# Unit tests (the default selection, same as CI)
uv run pytest

# Run specific test file
uv run pytest tests/test_client.py

# e2e tests (real Claude CLI + API key): override the marker selection
uv run pytest -m e2e tests/e2e
```

# Codebase Structure

- `src/clawd_code_sdk/` - Main package
  - `client.py` - ClaudeSDKClient for interactive sessions
  - `query.py` - One-shot query function
  - `types.py` - Type definitions
  - `_internal/` - Internal implementation details
    - `transport/subprocess_cli.py` - CLI subprocess management
    - `message_parser.py` - Message parsing logic
