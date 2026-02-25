"""Minimal MCP server that returns image content for wire-format testing."""

from __future__ import annotations

from pathlib import Path

import anyio
from fastmcp import Context, FastMCP
from fastmcp.utilities.types import Image


mcp = FastMCP("Image Test Server")


@mcp.tool
async def get_test_image() -> Image:
    """Return a small test PNG image."""
    png_path = Path(__file__).parent / "test_image.png"
    return Image(data=png_path.read_bytes(), format="png")


@mcp.tool
async def test_progress(ctx: Context, message: str) -> str:
    """Test progress reporting with the given message."""
    await ctx.report_progress(0, 100, "first step")
    await anyio.sleep(0.5)
    await ctx.report_progress(50, 100, "second step")
    await anyio.sleep(0.5)
    await ctx.report_progress(99, 100, "third step")
    await anyio.sleep(0.5)
    return f"Progress test completed with message: {message}"


if __name__ == "__main__":
    mcp.run(show_banner=False, log_level="error")
