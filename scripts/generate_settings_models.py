"""Generate Pydantic models from the Claude Code settings JSON Schema.

This script downloads the JSON schema from schemastore.org
and generates Pydantic models using datamodel-codegen.

Requirements:
    uv tool install datamodel-code-generator

Usage:
    python scripts/generate_settings_models.py
    # Or with uv:
    uv run python scripts/generate_settings_models.py
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


# URLs and paths
SCHEMA_URL = "https://json.schemastore.org/claude-code-settings.json"
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_FILE = PROJECT_ROOT / "src" / "clawd_code_sdk" / "models" / "settings_file.py"
TEMP_SCHEMA = "/tmp/claude-code-settings.json"


def download_schema() -> None:
    """Download the JSON Schema specification."""
    print(f"Downloading JSON Schema from {SCHEMA_URL}...")
    result = subprocess.run(
        ["curl", "-fsSL", SCHEMA_URL, "-o", TEMP_SCHEMA],
        check=True,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Error downloading schema: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(f"  Downloaded to {TEMP_SCHEMA}")


def generate_models() -> None:
    """Generate Pydantic models using datamodel-codegen."""
    print("Generating Pydantic models...")

    cmd = [
        "uv",
        "tool",
        "run",
        "--from",
        "datamodel-code-generator",
        "datamodel-codegen",
        "--input",
        TEMP_SCHEMA,
        "--input-file-type",
        "jsonschema",
        "--output",
        str(OUTPUT_FILE),
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--target-python-version",
        "3.13",
        "--target-pydantic-version",
        "2",
        "--use-standard-collections",
        # "--use-annotated",
        "--use-standard-primitive-types",
        "--snake-case-field",
        "--field-constraints",
        "--use-schema-description",
        "--use-field-description",
        "--use-double-quotes",
        "--reuse-model",
        "--enum-field-as-literal",
        "all",
        "--use-one-literal-as-default",
        "--collapse-root-models",
        "--base-class",
        "clawd_code_sdk.models.base.ClaudeCodeBaseModel",
        "--formatters",
        "ruff-check",
        "ruff-format",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        print(f"Error generating models: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    # Show warnings but don't fail
    if result.stderr:
        print(f"Warnings: {result.stderr}")

    print(f"  Generated models to {OUTPUT_FILE}")


def verify_output() -> None:
    """Verify the generated file exists and has content."""
    if not OUTPUT_FILE.exists():
        print(f"Error: Output file {OUTPUT_FILE} not found!", file=sys.stderr)
        sys.exit(1)

    content = OUTPUT_FILE.read_text()
    lines = content.count("\n")
    print(f"  Verified: {lines} lines generated")

    model_count = content.count("class ")
    print(f"  Generated {model_count} model classes")


def main() -> None:
    """Main entry point."""
    print("=" * 60)
    print("Claude Code Settings Model Generation")
    print("=" * 60)

    try:
        download_schema()
        generate_models()
        verify_output()

        print("\n" + "=" * 60)
        print("Success! Models generated successfully.")
        print("=" * 60)
        print(f"\nGenerated models: {OUTPUT_FILE}")

    except subprocess.CalledProcessError as e:
        print(f"\nError: Command failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:  # noqa: BLE001
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
