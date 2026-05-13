"""FastAPI app wiring: /health, OAuth routes, MCP mount, bearer middleware.

This is the composition root for the server. It pulls together:
  - Settings + categories config
  - The MCP server (FastMCP) with all seven tools registered
  - The OAuth routes + bearer middleware
  - A /health endpoint for smoke testing
"""

from __future__ import annotations

import logging
import time
import uuid

import structlog
from fastapi import FastAPI, Request
from mcp.server.fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from notes_mcp import __version__
from notes_mcp.auth import build_auth_router, require_bearer
from notes_mcp.config import CategoriesConfig, Settings, load_categories
from notes_mcp.tools import register_tools

_MCP_PATH = "/mcp"


def _configure_logging(level: str) -> None:
    logging.basicConfig(level=level.upper(), format="%(message)s")
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )


class RequestLogMiddleware(BaseHTTPMiddleware):
    """Attach a request id and log tool/duration on every request."""

    def __init__(self, app, logger):
        super().__init__(app)
        self.logger = logger

    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        start = time.perf_counter()
        response: Response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        self.logger.info(
            "request",
            request_id=req_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=elapsed_ms,
        )
        response.headers["x-request-id"] = req_id
        return response


def create_app(
    settings: Settings,
    categories: CategoriesConfig | None = None,
) -> FastAPI:
    """Build the FastAPI app. Categories can be preloaded (tests) or lazy-loaded."""
    _configure_logging(settings.log_level)
    logger = structlog.get_logger("notes_mcp")

    if categories is None:
        categories = load_categories(settings.notes_home)
    logger.info(
        "startup",
        version=__version__,
        notes_home=str(settings.notes_home),
        categories_loaded=len(categories.categories),
    )

    # Build the MCP server and register tools. The MCP app gets mounted under /mcp.
    mcp = FastMCP("notes-mcp")
    register_tools(mcp, settings=settings, categories=categories)

    app = FastAPI(title="notes-mcp", version=__version__)
    app.state.settings = settings
    app.state.categories = categories

    # Health — no auth required.
    @app.get("/health")
    def health() -> dict:
        return {
            "ok": True,
            "version": __version__,
            "categories_loaded": len(categories.categories),
        }

    # OAuth endpoints — no bearer required (they ISSUE bearers).
    app.include_router(build_auth_router(settings))

    # MCP mount — guarded by the bearer middleware below.
    app.mount(_MCP_PATH, mcp.streamable_http_app())

    # Bearer enforcement on /mcp/* only.
    @app.middleware("http")
    async def enforce_bearer(request: Request, call_next):
        if request.url.path.startswith(_MCP_PATH):
            error = require_bearer(request)
            if error is not None:
                return JSONResponse(
                    {"error": error}, status_code=401,
                    headers={"www-authenticate": 'Bearer realm="notes-mcp"'},
                )
        return await call_next(request)

    app.add_middleware(RequestLogMiddleware, logger=logger)
    return app
