"""Shared fixtures: a tmp ~/Notes/ tree, seeded settings, a built FastAPI app."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from notes_mcp import auth as auth_mod
from notes_mcp.config import Settings, load_categories
from notes_mcp.server import create_app

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def notes_home(tmp_path: Path) -> Path:
    """A clean notes-home with the default categories seeded."""
    home = tmp_path / "Notes"
    home.mkdir()
    shutil.copy(FIXTURES / "categories.yaml", home / ".categories.yaml")
    return home


@pytest.fixture
def settings(notes_home: Path) -> Settings:
    return Settings(notes_home=notes_home, host="testserver", port=8765)


@pytest.fixture
def categories(notes_home: Path):
    return load_categories(notes_home)


@pytest.fixture
def app(settings: Settings, categories):
    auth_mod._reset_for_tests()
    return create_app(settings, categories=categories)


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient

    return TestClient(app)
