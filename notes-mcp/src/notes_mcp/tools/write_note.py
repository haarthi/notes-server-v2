"""S1 — `write_note`.

Writes a pre-formatted note to the correct location with proper frontmatter,
file naming, and file-unit handling. Errors if the target file already exists
(smart-append is S2's job, M3).
"""

from __future__ import annotations

import os
import tempfile
from datetime import date as _date
from pathlib import Path
from typing import Literal

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from notes_mcp.config import CategoriesConfig, Settings
from notes_mcp.frontmatter import render_note
from notes_mcp.paths import filename_for


class WriteNoteResult(BaseModel):
    ok: bool
    path: str | None = None
    error: str | None = None


def _today() -> _date:
    return _date.today()


def _atomic_write(path: Path, content: str) -> None:
    """Write to a sibling tempfile then os.replace into place.

    Avoids half-written files if the process is killed mid-write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def _resolve_path(
    *,
    notes_home: Path,
    categories: CategoriesConfig,
    category: str,
    topic: str | None,
    title: str | None,
    date_iso: str | None,
    entry_type: str | None,
) -> tuple[Path, _date]:
    if category not in categories.categories:
        raise ValueError(
            f"unknown category {category!r} — not in .categories.yaml"
        )
    cfg = categories.categories[category]
    d = _date.fromisoformat(date_iso) if date_iso else _today()

    # Slug for entry-based files prefers explicit title, else topic.
    slug = title or topic

    filename = filename_for(
        cfg.file_unit,
        topic=topic,
        date_=d,
        slug=slug,
        entry_type=entry_type,  # type: ignore[arg-type]
    )
    return notes_home / category / filename, d


def register_write_note(
    mcp: FastMCP,
    *,
    settings: Settings,
    categories: CategoriesConfig,
) -> None:
    @mcp.tool()
    def write_note(
        category: str,
        content: str,
        title: str | None = None,
        topic: str | None = None,
        tags: list[str] | None = None,
        date: str | None = Field(default=None, description="ISO date YYYY-MM-DD; defaults to today"),
        source: Literal["direct", "inbox", "claude-conversation"] = "direct",
        entry_type: Literal["article", "thread"] | None = None,
    ) -> dict:
        """Write a pre-formatted note. Errors if the target file already exists.

        For topic-based categories: pass `topic`.
        For monthly-bucket categories (Reflection): pass nothing special; date routes the file.
        For entry-based categories: pass `title` (used as slug).
        For mixed (ProfessionalDev): pass `entry_type` ("article" or "thread").
        """
        try:
            path, d = _resolve_path(
                notes_home=settings.notes_home,
                categories=categories,
                category=category,
                topic=topic,
                title=title,
                date_iso=date,
                entry_type=entry_type,
            )
        except ValueError as exc:
            return WriteNoteResult(ok=False, error=str(exc)).model_dump()

        if path.exists():
            return WriteNoteResult(
                ok=False,
                error=(
                    f"target already exists: {path}. "
                    f"Smart append is not part of M1 (lives in S2 / M3)."
                ),
            ).model_dump()

        # For entry-based notes the spec is "flat under a single H1" — no H2.
        cfg = categories.categories[category]
        if cfg.file_unit == "entry-based" or (cfg.file_unit == "mixed" and entry_type == "article"):
            section_date = None
        else:
            section_date = d

        display_title = title or topic or category
        rendered = render_note(
            title=display_title,
            body=content,
            category=category,
            tags=tags,
            source=source,
            created=d,
            last_updated=d,
            section_date=section_date,
        )
        _atomic_write(path, rendered)
        return WriteNoteResult(ok=True, path=str(path)).model_dump()
