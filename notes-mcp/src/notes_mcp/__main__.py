"""Entry point: `python -m notes_mcp` or `notes-mcp` (via project.scripts)."""

from __future__ import annotations

import sys

import uvicorn

from notes_mcp.config import Settings, load_categories
from notes_mcp.server import create_app


def main() -> None:
    try:
        settings = Settings()  # reads env + .env
        # Eager load + validate categories so missing/malformed exits non-zero
        # before the server starts taking requests.
        load_categories(settings.notes_home)
    except Exception as exc:  # noqa: BLE001 — top-level startup guard
        print(f"[notes-mcp] fatal startup error: {exc}", file=sys.stderr)
        sys.exit(1)

    app = create_app(settings)
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
