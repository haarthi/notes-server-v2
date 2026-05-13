"""Unit tests for filename generation per `file_unit` pattern."""

from __future__ import annotations

from datetime import date

import pytest

from notes_mcp.paths import (
    entry_filename,
    filename_for,
    kebab,
    monthly_filename,
    topic_filename,
)


def test_kebab_basic():
    assert kebab("Refinancing") == "refinancing"
    assert kebab("Notes App") == "notes-app"
    assert kebab("RAG Eval — Key Takeaways") == "rag-eval-key-takeaways"
    assert kebab("  multiple   spaces  ") == "multiple-spaces"
    assert kebab("___underscores___") == "underscores"


def test_kebab_empty_fallback():
    assert kebab("") == "untitled"
    assert kebab("!!!") == "untitled"


def test_topic_filename():
    assert topic_filename("Refinancing") == "refinancing.md"
    assert topic_filename("Backyard Redesign") == "backyard-redesign.md"


def test_monthly_filename():
    assert monthly_filename(date(2026, 5, 11)) == "2026-05.md"
    assert monthly_filename(date(2026, 12, 1)) == "2026-12.md"


def test_entry_filename():
    assert (
        entry_filename(date(2026, 5, 11), "RAG Eval Article")
        == "2026-05-11-rag-eval-article.md"
    )


# ---- filename_for dispatcher ------------------------------------------------


def test_filename_for_topic():
    assert filename_for("topic-based", topic="Refinancing") == "refinancing.md"


def test_filename_for_monthly():
    assert filename_for("monthly-bucket", date_=date(2026, 5, 11)) == "2026-05.md"


def test_filename_for_entry():
    assert (
        filename_for("entry-based", date_=date(2026, 5, 11), slug="thoughts")
        == "2026-05-11-thoughts.md"
    )


def test_filename_for_mixed_article():
    assert (
        filename_for(
            "mixed",
            date_=date(2026, 5, 11),
            slug="RAG Eval Article",
            entry_type="article",
        )
        == "2026-05-11-rag-eval-article.md"
    )


def test_filename_for_mixed_thread():
    assert (
        filename_for("mixed", topic="MCP deep dive", entry_type="thread")
        == "mcp-deep-dive.md"
    )


def test_filename_for_unknown_unit():
    with pytest.raises(ValueError):
        filename_for("not-a-real-unit", topic="x")


def test_filename_for_mixed_requires_entry_type():
    with pytest.raises(ValueError):
        filename_for("mixed", topic="x")
