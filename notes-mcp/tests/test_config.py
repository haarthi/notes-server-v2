"""Unit tests for config loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from notes_mcp.config import load_categories


def test_load_categories_happy_path(notes_home: Path):
    cfg = load_categories(notes_home)
    assert cfg.instance == "personal"
    assert "Finance" in cfg.categories
    assert cfg.categories["Finance"].file_unit == "topic-based"
    assert cfg.categories["Reflection"].file_unit == "monthly-bucket"
    assert cfg.categories["ProfessionalDev"].file_unit == "mixed"
    assert cfg.categories["ProfessionalDev"].rules == {
        "articles": "entry-based",
        "threads": "topic-based",
    }


def test_load_categories_missing(tmp_path: Path):
    home = tmp_path / "Notes"
    home.mkdir()
    with pytest.raises(FileNotFoundError):
        load_categories(home)


def test_load_categories_malformed_yaml(tmp_path: Path):
    home = tmp_path / "Notes"
    home.mkdir()
    (home / ".categories.yaml").write_text("instance: personal\ncategories: : :\n")
    with pytest.raises(ValueError):
        load_categories(home)


def test_load_categories_bad_file_unit(tmp_path: Path):
    home = tmp_path / "Notes"
    home.mkdir()
    (home / ".categories.yaml").write_text(
        "instance: personal\n"
        "categories:\n"
        "  Whatever:\n"
        "    file_unit: not-a-real-unit\n"
    )
    with pytest.raises(Exception):
        load_categories(home)
