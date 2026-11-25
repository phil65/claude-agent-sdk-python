#!/usr/bin/env bash
# List upstream (anthropics/claude-agent-sdk-python) commits that touch src/ since the
# last reviewed one (recorded in AGENTS.md, "Upstream Python SDK" row), oldest first.
# CLI-version bumps and release commits are left out.
#
# Usage: scripts/upstream_since.sh [<sha>]   (default: the sha recorded in AGENTS.md)
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
if ! git remote get-url upstream >/dev/null 2>&1; then
  echo "No 'upstream' remote. Add it (fetch only):" >&2
  echo "  git remote add upstream https://github.com/anthropics/claude-agent-sdk-python.git" >&2
  echo "  git remote set-url --push upstream no_push" >&2
  exit 1
fi
since=${1:-$(sed -nE 's/.*last reviewed `([0-9a-f]{7,40})`.*/\1/p' AGENTS.md | head -n1)}
if [[ -z $since ]]; then
  echo "No 'last reviewed \`<sha>\`' found in AGENTS.md; pass a sha." >&2
  exit 1
fi
git fetch -q upstream main
git log --no-merges --reverse --format='%h %cs %s' "$since"..upstream/main -- src |
  command grep -vE 'bump bundled CLI|chore: release' || true
echo "--- since $since; upstream/main is $(git log -1 --format='%h (%cs)' upstream/main)"
