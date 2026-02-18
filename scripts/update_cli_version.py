#!/usr/bin/env python3
"""Update Claude Code CLI version in _cli_version.py."""

from pathlib import Path
import re
import sys


def update_cli_version(new_version: str) -> None:
    """Update CLI version in _cli_version.py."""
    # Update _cli_version.py
    version_path = Path("src/clawd_code_sdk/__init__.py")
    content = version_path.read_text()

    content = re.sub(
        r'__cli_version__ = "[^"]+"',
        f'__cli_version__ = "{new_version}"',
        content,
        count=1,
        flags=re.MULTILINE,
    )

    version_path.write_text(content)
    print(f"Updated {version_path} to {new_version}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/update_cli_version.py <version>")
        sys.exit(1)

    update_cli_version(sys.argv[1])
