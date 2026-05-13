"""Unit tests for frontmatter render + parse."""

from __future__ import annotations

from datetime import date

from notes_mcp.frontmatter import parse_note, render_note


def test_render_canonical_field_order():
    out = render_note(
        title="Refinancing",
        body="Some content.",
        category="Finance",
        tags=["rates", "jumbo"],
        source="claude-conversation",
        created=date(2026, 3, 2),
        last_updated=date(2026, 5, 11),
        section_date=date(2026, 5, 11),
    )
    # Frontmatter block should preserve canonical order — created first.
    lines = out.splitlines()
    assert lines[0] == "---"
    # The first five YAML keys in order:
    yaml_keys = [
        line.split(":", 1)[0]
        for line in lines[1:]
        if ":" in line and not line.startswith(" ")
    ][:5]
    assert yaml_keys == ["created", "last_updated", "category", "tags", "source"]


def test_render_contains_h1_and_section():
    out = render_note(
        title="Refinancing",
        body="Spoke with broker.",
        category="Finance",
        section_date=date(2026, 5, 11),
    )
    assert "# Refinancing" in out
    assert "## 2026-05-11" in out
    assert "Spoke with broker." in out


def test_render_entry_style_has_no_section():
    out = render_note(
        title="RAG Eval Article",
        body="Summary paragraph.",
        category="ProfessionalDev",
        section_date=None,
    )
    assert "# RAG Eval Article" in out
    assert "## " not in out  # no dated H2
    assert "Summary paragraph." in out


def test_render_iso_dates():
    out = render_note(
        title="x",
        body="y",
        category="Finance",
        created=date(2026, 1, 2),
        last_updated=date(2026, 3, 4),
    )
    assert "created: '2026-01-02'" in out or "created: 2026-01-02" in out
    assert "last_updated: '2026-03-04'" in out or "last_updated: 2026-03-04" in out


def test_render_parse_roundtrip(tmp_path):
    out = render_note(
        title="Refinancing",
        body="Some content.",
        category="Finance",
        tags=["rates", "jumbo"],
        created=date(2026, 3, 2),
        last_updated=date(2026, 5, 11),
        section_date=date(2026, 5, 11),
    )
    p = tmp_path / "refinancing.md"
    p.write_text(out)
    parsed = parse_note(p)
    assert parsed.metadata["category"] == "Finance"
    assert parsed.metadata["tags"] == ["rates", "jumbo"]
    # python-frontmatter may parse ISO strings or keep them as strings — accept either.
    assert str(parsed.metadata["created"]) == "2026-03-02"
    assert "# Refinancing" in parsed.body
