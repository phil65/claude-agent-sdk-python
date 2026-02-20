"""Minimal MCP server that returns image content for wire-format testing."""

from __future__ import annotations

from pathlib import Path

from fastmcp import FastMCP
from fastmcp.utilities.types import Image


mcp = FastMCP("Image Test Server")


@mcp.tool
async def get_test_image() -> Image:
    """Return a small test PNG image."""
    png_path = Path(__file__).parent / "test_image.png"
    return Image(data=png_path.read_bytes(), format="png")


if __name__ == "__main__":
    mcp.run(show_banner=False, log_level="error")
