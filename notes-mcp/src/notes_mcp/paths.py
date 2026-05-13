"""Filename generation per `file_unit` pattern.

Pure functions, no I/O. The three patterns and the `mixed` dispatcher
implement the spec's Notes Schema:
  - topic-based     → {kebab-topic}.md
  - monthly-bucket  → YYYY-MM.md
  - entry-based     → YYYY-MM-DD-{kebab-slug}.md
  - mixed           → dispatches on entry_type
"""

from __future__ import annotations

import re
from datetime import date
from typing import Literal

EntryType = Literal["article", "thread"]


def kebab(text: str) -> str:
    """Lowercase, ASCII-strip, hyphen-collapse. Never empty."""
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "untitled"


def topic_filename(topic: str) -> str:
    return f"{kebab(topic)}.md"


def monthly_filename(d: date) -> str:
    return f"{d:%Y-%m}.md"


def entry_filename(d: date, slug: str) -> str:
    return f"{d:%Y-%m-%d}-{kebab(slug)}.md"


def filename_for(
    file_unit: str,
    *,
    topic: str | None = None,
    date_: date | None = None,
    slug: str | None = None,
    entry_type: EntryType | None = None,
) -> str:
    """Dispatch on `file_unit`. Raises ValueError on bad args.

    For `mixed`, the caller must supply `entry_type` ("article" or "thread").
    """
    if file_unit == "topic-based":
        if topic is None:
            raise ValueError("topic-based file_unit requires `topic`")
        return topic_filename(topic)

    if file_unit == "monthly-bucket":
        if date_ is None:
            raise ValueError("monthly-bucket file_unit requires `date_`")
        return monthly_filename(date_)

    if file_unit == "entry-based":
        if date_ is None or slug is None:
            raise ValueError("entry-based file_unit requires `date_` and `slug`")
        return entry_filename(date_, slug)

    if file_unit == "mixed":
        if entry_type == "article":
            if date_ is None or slug is None:
                raise ValueError("mixed/article requires `date_` and `slug`")
            return entry_filename(date_, slug)
        if entry_type == "thread":
            if topic is None:
                raise ValueError("mixed/thread requires `topic`")
            return topic_filename(topic)
        raise ValueError(
            f"mixed file_unit requires entry_type in ('article','thread'), got {entry_type!r}"
        )

    raise ValueError(f"unknown file_unit: {file_unit!r}")
