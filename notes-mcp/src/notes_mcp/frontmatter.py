"""Render and parse YAML frontmatter.

The render side dumps YAML with `sort_keys=False` so the canonical field
order (`created`, `last_updated`, `category`, `tags`, `source`) is preserved
across writes. This avoids spurious `git diff` churn on every append.

The parse side uses `python-frontmatter` since reading is straightforward
and order doesn't matter on the in-memory side.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import frontmatter
import yaml

# Canonical field order. Anything in `extra` lands after these.
_CANONICAL_ORDER = ("created", "last_updated", "category", "tags", "source")


def render_note(
    *,
    title: str,
    body: str,
    category: str,
    tags: list[str] | None = None,
    source: str = "direct",
    created: date | None = None,
    last_updated: date | None = None,
    section_date: date | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    """Render a fresh note as a full markdown string.

    Layout:
        ---
        <frontmatter>
        ---

        # {title}

        ## {section_date}
        {body}

    `section_date` defaults to `created`. For entry-based files, callers can
    pass section_date=None to skip the H2 (entry-based notes are flat under
    the H1 per the spec).
    """
    created = created or date.today()
    last_updated = last_updated or created

    fm: dict[str, Any] = {
        "created": created.isoformat(),
        "last_updated": last_updated.isoformat(),
        "category": category,
        "tags": list(tags or []),
        "source": source,
    }
    if extra:
        for k, v in extra.items():
            if k not in fm:
                fm[k] = v

    yaml_str = yaml.dump(
        fm,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
    )

    parts = ["---\n", yaml_str, "---\n", "\n", f"# {title}\n", "\n"]
    if section_date is not None:
        parts.append(f"## {section_date.isoformat()}\n")
        parts.append(body.rstrip() + "\n")
    else:
        parts.append(body.rstrip() + "\n")

    return "".join(parts)


@dataclass
class ParsedNote:
    metadata: dict[str, Any]
    body: str


def parse_note(path: Path) -> ParsedNote:
    """Parse a note file into its frontmatter + body."""
    post = frontmatter.loads(path.read_text())
    return ParsedNote(metadata=dict(post.metadata), body=post.content)
