"""Extract TypeScript declarations from @anthropic-ai/claude-agent-sdk npm package.

Downloads the latest (or a specific version of the) npm package and extracts
sdk.d.ts and sdk-tools.d.ts into the reference/ directory for use as a
source-of-truth when updating the Python SDK models.

These files are NOT included in the published Python package.

Usage:
    # Latest version
    python scripts/update_sdk_reference.py

    # Specific version
    python scripts/update_sdk_reference.py --version 0.2.51
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile


NPM_PACKAGE = "@anthropic-ai/claude-agent-sdk"
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "reference"

# Files to extract from the npm tarball (tarball paths are prefixed with "package/")
FILES_TO_EXTRACT = [
    "package/sdk.d.ts",
    "package/sdk-tools.d.ts",
]


def get_latest_version() -> str:
    """Query npm for the latest version of the package."""
    result = subprocess.run(
        ["npm", "view", NPM_PACKAGE, "version"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def download_tarball(version: str, dest: Path) -> Path:
    """Download the npm tarball for a specific version."""
    print(f"Downloading {NPM_PACKAGE}@{version}...")
    result = subprocess.run(
        ["npm", "pack", f"{NPM_PACKAGE}@{version}", "--pack-destination", str(dest)],
        capture_output=True,
        text=True,
        check=True,
    )
    # npm pack prints the filename to stdout
    tarball_name = result.stdout.strip().splitlines()[-1]
    tarball_path = dest / tarball_name
    if not tarball_path.exists():
        print(f"Error: Expected tarball at {tarball_path}", file=sys.stderr)
        sys.exit(1)
    print(f"  Downloaded {tarball_path.name}")
    return tarball_path


def extract_files(tarball_path: Path, version: str) -> list[Path]:
    """Extract the declaration files from the tarball."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []

    with tarfile.open(tarball_path, "r:gz") as tar:
        members = tar.getnames()
        for target in FILES_TO_EXTRACT:
            if target not in members:
                print(f"  Warning: {target} not found in tarball", file=sys.stderr)
                continue

            member = tar.getmember(target)
            fileobj = tar.extractfile(member)
            if fileobj is None:
                print(f"  Warning: Could not read {target}", file=sys.stderr)
                continue

            content = fileobj.read()
            # Strip the "package/" prefix for the output filename
            output_name = target.removeprefix("package/")
            output_path = OUTPUT_DIR / output_name
            output_path.write_bytes(content)
            extracted.append(output_path)
            print(f"  Extracted {output_name} ({len(content):,} bytes)")

    # Write metadata
    metadata = {
        "package": NPM_PACKAGE,
        "version": version,
        "files": [p.name for p in extracted],
    }
    metadata_path = OUTPUT_DIR / "VERSION.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"  Wrote {metadata_path.name}")

    return extracted


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract TypeScript declarations from the Claude Agent SDK npm package.",
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Specific package version to download (default: latest)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Claude Agent SDK Reference Update")
    print("=" * 60)

    version: str = args.version or get_latest_version()
    print(f"Target version: {version}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tarball_path = download_tarball(version, Path(tmpdir))
        extracted = extract_files(tarball_path, version)

    if not extracted:
        print("\nError: No files were extracted!", file=sys.stderr)
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Success!")
    print("=" * 60)
    print(f"\nReference files in: {OUTPUT_DIR}")
    for path in extracted:
        print(f"  {path.name}")


if __name__ == "__main__":
    main()
