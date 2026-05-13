"""Integration: write_note covers all file_unit patterns + error paths.

These tests call into the tool function directly via the FastMCP registry
rather than going through the MCP HTTP transport. That keeps tests fast
and unambiguous about which layer is under test.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from mcp.server.fastmcp import FastMCP

from notes_mcp.frontmatter import parse_note
from notes_mcp.tools.write_note import register_write_note


@pytest.fixture
def write_note(settings, categories):
    """Return a callable `write_note(...)` bound to the test settings."""
    mcp = FastMCP("test")
    register_write_note(mcp, settings=settings, categories=categories)
    # FastMCP stores tools in an internal manager; grab the function.
    tool = mcp._tool_manager.get_tool("write_note")
    return tool.fn


def test_writes_topic_based_finance(write_note, notes_home: Path):
    res = write_note(
        category="Finance",
        topic="refinancing",
        content="Spoke with broker.",
        date="2026-05-11",
    )
    assert res["ok"] is True
    p = notes_home / "Finance" / "refinancing.md"
    assert p.exists()
    parsed = parse_note(p)
    assert parsed.metadata["category"] == "Finance"
    assert "# refinancing" in parsed.body.lower()
    assert "## 2026-05-11" in parsed.body
    assert "Spoke with broker." in parsed.body


def test_writes_monthly_reflection(write_note, notes_home: Path):
    res = write_note(
        category="Reflection",
        content="Reflecting on the month.",
        date="2026-05-11",
    )
    assert res["ok"] is True
    p = notes_home / "Reflection" / "2026-05.md"
    assert p.exists()


def test_writes_topic_products_ideas(write_note, notes_home: Path):
    res = write_note(
        category="ProductsIdeas",
        topic="notes-app",
        content="The notes app idea.",
        date="2026-05-11",
    )
    assert res["ok"] is True
    assert (notes_home / "ProductsIdeas" / "notes-app.md").exists()


def test_writes_professionaldev_article(write_note, notes_home: Path):
    res = write_note(
        category="ProfessionalDev",
        title="RAG Eval Article",
        content="Summary paragraph.",
        date="2026-05-11",
        entry_type="article",
    )
    assert res["ok"] is True
    p = notes_home / "ProfessionalDev" / "2026-05-11-rag-eval-article.md"
    assert p.exists()
    parsed = parse_note(p)
    # Entry-based notes are flat — no dated H2.
    assert "## " not in parsed.body


def test_writes_professionaldev_thread(write_note, notes_home: Path):
    res = write_note(
        category="ProfessionalDev",
        topic="MCP deep dive",
        content="Thread body.",
        date="2026-05-11",
        entry_type="thread",
    )
    assert res["ok"] is True
    p = notes_home / "ProfessionalDev" / "mcp-deep-dive.md"
    assert p.exists()


def test_rejects_unknown_category(write_note):
    res = write_note(category="NotARealCategory", content="x")
    assert res["ok"] is False
    assert "unknown category" in res["error"].lower()


def test_rejects_existing_file(write_note, notes_home: Path):
    args = dict(
        category="Finance",
        topic="refinancing",
        content="first",
        date="2026-05-11",
    )
    res1 = write_note(**args)
    assert res1["ok"] is True
    res2 = write_note(**args)
    assert res2["ok"] is False
    assert "already exists" in res2["error"].lower()


def test_kebab_filenames(write_note, notes_home: Path):
    write_note(
        category="Finance",
        topic="Backyard Redesign Plans",
        content="x",
        date="2026-05-11",
    )
    # File name is kebab-case, no spaces, no caps.
    assert (notes_home / "Finance" / "backyard-redesign-plans.md").exists()


def test_frontmatter_required_fields(write_note, notes_home: Path):
    write_note(
        category="Finance",
        topic="taxes",
        content="x",
        date="2026-05-11",
        tags=["w2", "deductions"],
        source="direct",
    )
    parsed = parse_note(notes_home / "Finance" / "taxes.md")
    for field in ("created", "last_updated", "category", "tags", "source"):
        assert field in parsed.metadata
    assert parsed.metadata["source"] == "direct"
    assert parsed.metadata["tags"] == ["w2", "deductions"]
