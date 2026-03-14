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

import json
from pathlib import Path
import re
import subprocess
import sys


# URLs and paths
SCHEMA_URL = "https://json.schemastore.org/claude-code-settings.json"
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_FILE = PROJECT_ROOT / "src" / "clawd_code_sdk" / "models" / "settings.py"
TEMP_SCHEMA = "/tmp/claude-code-settings.json"
TEMP_SCHEMA_TITLED = "/tmp/claude-code-settings-titled.json"

# Titles injected into anyOf/oneOf variants that lack a "title" field.
# Maps JSON pointer path -> list of (discriminator_parent_name, variants_key).
# The script derives each variant's title from the const discriminator value
# (e.g., source="github" -> MarketplaceSourceGithub) or from the first
# required property (e.g., serverName -> AllowedMcpServerByServerName).
_UNION_TITLE_MAP: dict[str, tuple[str, str]] = {
    "$defs.hookCommand": ("HookConfig", "anyOf"),
    "properties.allowedMcpServers.items": ("AllowedMcpServer", "anyOf"),
    "properties.deniedMcpServers.items": ("DeniedMcpServer", "anyOf"),
    "properties.extraKnownMarketplaces.additionalProperties.properties.source": (
        "MarketplaceSource",
        "anyOf",
    ),
    "properties.strictKnownMarketplaces.items": ("StrictMarketplace", "anyOf"),
    "properties.blockedMarketplaces.items": ("BlockedMarketplace", "anyOf"),
}


def _to_pascal(s: str) -> str:
    """Convert a camelCase or snake_case string to PascalCase."""
    if "_" not in s and s[0].islower():
        return s[0].upper() + s[1:]
    return "".join(w.capitalize() for w in s.split("_"))


def _resolve_path(schema: dict, dotted_path: str) -> dict:
    """Resolve a dotted key path like 'properties.foo.items' into the schema."""
    obj = schema
    for part in dotted_path.split("."):
        obj = obj[part]
    return obj


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


def preprocess_schema() -> None:
    """Add title fields to unnamed anyOf/oneOf variants for better class names.

    datamodel-codegen generates numbered suffixes (Source1, Source2, ...) for
    unnamed union variants. By injecting a title derived from the discriminator
    const value or unique required property, we get descriptive class names
    (MarketplaceSourceGithub, HookConfigCommand, etc.) when combined with
    --use-title-as-name.
    """
    print("Pre-processing schema (adding titles to union variants)...")
    with Path(TEMP_SCHEMA).open() as f:
        schema = json.load(f)

    titled_count = 0
    for path, (parent_name, union_key) in _UNION_TITLE_MAP.items():
        node = _resolve_path(schema, path)
        for item in node[union_key]:
            if not isinstance(item, dict) or "properties" not in item or "title" in item:
                continue
            # Strategy 1: Use const discriminator value
            for pval in item["properties"].values():
                if "const" in pval:
                    item["title"] = f"{parent_name}{_to_pascal(pval['const'])}"
                    titled_count += 1
                    break
            else:
                # Strategy 2: Use first required property name
                req = item.get("required", [])
                if req:
                    item["title"] = f"{parent_name}By{_to_pascal(req[0])}"
                    titled_count += 1

    with Path(TEMP_SCHEMA_TITLED).open("w") as f:
        json.dump(schema, f, indent=2)
    print(f"  Added {titled_count} titles, saved to {TEMP_SCHEMA_TITLED}")


def generate_models() -> None:
    """Generate Pydantic models using datamodel-codegen."""
    print("Generating Pydantic models...")

    cmd = [
        "uvx",
        "--python",
        "3.13",
        "--from",
        "datamodel-code-generator==0.54.1",
        "datamodel-codegen",
        "--input",
        TEMP_SCHEMA_TITLED,
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
        "--use-title-as-name",
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


def post_process() -> None:
    """Fix known datamodel-codegen issues in the generated file."""
    print("Post-processing generated models...")
    content = OUTPUT_FILE.read_text()
    original = content

    # Replace constr(pattern=...) with str in dict key positions.
    # datamodel-codegen emits constr() for constrained dict keys, but mypy
    # doesn't understand the con* functional forms. Pydantic doesn't validate
    # dict key patterns at runtime anyway, so plain str is equivalent.
    content = re.sub(r"constr\(pattern=r?['\"][^'\"]*['\"]\)", "str", content)

    # Remove unused constr import if no constr() usages remain outside imports
    non_import_lines = [
        line for line in content.splitlines() if not line.strip().startswith(("from ", "import "))
    ]
    if "constr" not in "\n".join(non_import_lines):
        content = re.sub(r",\s*constr", "", content)
        content = re.sub(r"constr,\s*", "", content)
        content = content.replace("from pydantic import constr\n", "")

    if content != original:
        OUTPUT_FILE.write_text(content)
        print("  Fixed constr() dict key annotations")
    else:
        print("  No post-processing needed")


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
        preprocess_schema()
        generate_models()
        post_process()
        verify_output()

        print("\n" + "=" * 60)
        print("Success! Models generated successfully.")
        print("=" * 60)
        print(f"\nGenerated models: {OUTPUT_FILE}")

    except subprocess.CalledProcessError as e:
        print(f"\nError: Command failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
