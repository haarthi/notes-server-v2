"""Register all seven MCP tools on a FastMCP instance.

In M1, only `write_note` is implemented. The other six return typed
not-implemented responses. Later milestones replace them in-place — each
tool lives in its own file once it's real (search_notes, list_notes, etc.).
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from notes_mcp.config import CategoriesConfig, Settings
from notes_mcp.tools.stubs import register_stubs
from notes_mcp.tools.write_note import register_write_note


def register_tools(
    mcp: FastMCP,
    *,
    settings: Settings,
    categories: CategoriesConfig,
) -> None:
    """Idempotent registration of all seven tools."""
    register_write_note(mcp, settings=settings, categories=categories)
    register_stubs(mcp)
