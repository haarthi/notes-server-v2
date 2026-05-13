"""Integration: MCP `tools/list` advertises all seven tools."""

from __future__ import annotations

import pytest
from mcp.server.fastmcp import FastMCP

from notes_mcp.tools import register_tools


EXPECTED_TOOLS = {
    "write_note",
    "list_notes",
    "read_note",
    "search_notes",
    "move_note",
    "process_inbox",
    "save_conversation",
}


@pytest.mark.asyncio
async def test_all_seven_tools_registered(settings, categories):
    mcp = FastMCP("test")
    register_tools(mcp, settings=settings, categories=categories)
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert names == EXPECTED_TOOLS, f"missing: {EXPECTED_TOOLS - names}, extra: {names - EXPECTED_TOOLS}"


@pytest.mark.asyncio
async def test_stubs_return_typed_response(settings, categories):
    mcp = FastMCP("test")
    register_tools(mcp, settings=settings, categories=categories)
    for name in EXPECTED_TOOLS - {"write_note"}:
        tool = mcp._tool_manager.get_tool(name)
        # Each stub must be callable with no required args (or minimal args)
        # and return a dict — no 500s.
        kwargs = {}
        if name == "read_note":
            kwargs["path"] = "x"
        elif name == "search_notes":
            kwargs["query"] = "x"
        elif name == "move_note":
            kwargs["source_path"] = "x"
            kwargs["target_category"] = "y"
        out = tool.fn(**kwargs)
        assert isinstance(out, dict)
        assert "ok" in out
