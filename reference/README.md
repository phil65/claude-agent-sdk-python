# SDK Reference Files

TypeScript declaration files extracted from the `@anthropic-ai/claude-agent-sdk` npm package.
These serve as the source of truth when updating the Python SDK models.

**Not included in the published Python package.**

## Updating

```bash
# Latest version
python scripts/update_sdk_reference.py

# Specific version
python scripts/update_sdk_reference.py --version 0.2.51
```

## Files

- `sdk.d.ts` — Core SDK types (messages, options, sessions, etc.)
- `sdk-tools.d.ts` — Tool input/output schemas
- `VERSION.json` — Tracks which npm package version these were extracted from
