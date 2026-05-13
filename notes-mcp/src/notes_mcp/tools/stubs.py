"""M1 stubs for the six MCP tools that aren't yet implemented.

Each returns a typed, well-formed response with a clear message. Lets
claude.ai's tools/list show the full surface area and gives Claude
something safe to call without 500s. Real implementations land in M2–M5.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP


_NOT_IMPLEMENTED = {
    "ok": False,
    "error": "not implemented in M1 — see milestones/ for the milestone that lands this tool",
}


def register_stubs(mcp: FastMCP) -> None:
    @mcp.tool()
    def list_notes(category: str | None = None) -> dict:
        """List notes, optionally filtered by category. (M2 / R1.)"""
        return _NOT_IMPLEMENTED | {"milestone": "M2/R1"}

    @mcp.tool()
    def read_note(path: str) -> dict:
        """Read full content of a specific note. (M2 / R1.)"""
        return _NOT_IMPLEMENTED | {"milestone": "M2/R1"}

    @mcp.tool()
    def search_notes(query: str, category: str | None = None, limit: int = 10) -> dict:
        """Keyword search with recency-weighted ranking. (M2 / R2.)"""
        return _NOT_IMPLEMENTED | {"milestone": "M2/R2"}

    @mcp.tool()
    def move_note(
        source_path: str,
        target_category: str,
        new_name: str | None = None,
    ) -> dict:
        """Move a note to a different category, optionally rename. (M5 / X2.)"""
        return _NOT_IMPLEMENTED | {"milestone": "M5/X2"}

    @mcp.tool()
    def process_inbox() -> dict:
        """Structure every entry in `_inbox/raw.md` and route via S2. (M4 / X1.)"""
        return _NOT_IMPLEMENTED | {"milestone": "M4/X1"}

    @mcp.tool()
    def save_conversation() -> dict:
        """Summarize current Claude conversation and save as a structured note. (M3 / S3.)"""
        return _NOT_IMPLEMENTED | {"milestone": "M3/S3"}
