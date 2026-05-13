# notes-mcp

Personal notes MCP server. Markdown source of truth at `~/Notes/`, exposed to claude.ai via OAuth 2.0 + a Cloudflare tunnel.

This repo implements **Milestone 1** of the v0.2 plan:

- **I1** — FastAPI + FastMCP serving the seven MCP tools (real `write_note`, stubs for the rest)
- **I2** — OAuth 2.0 + PKCE trust-all stubs satisfying claude.ai's remote-MCP requirements
- **I3** — Cloudflare Quick Tunnel runbook to expose the server over HTTPS
- **S1** — `write_note` real implementation across all `file_unit` patterns

See [../milestones/M1-foundation.md](../milestones/M1-foundation.md) for the full scope and acceptance criteria.

---

## Quick start

```bash
# Install dependencies + create venv
uv sync

# Copy env defaults
cp .env.example .env

# Seed a dev notes directory with the default categories
mkdir -p dev-notes
cp tests/fixtures/categories.yaml dev-notes/.categories.yaml

# Run tests
uv run pytest

# Run the server
uv run notes-mcp
# → server on http://localhost:8765
# → GET /health  → 200 {ok: true, ...}
# → MCP at /mcp (requires bearer token via OAuth flow)
```

## Expose to claude.ai

See [runbook/quick-tunnel.md](runbook/quick-tunnel.md) for the I3 path (cloudflared quick tunnel + connector setup in claude.ai).

The persistent URL upgrade (named tunnel + launchd) is **M4 / I4**, not M1.

## Layout

```
src/notes_mcp/
  __main__.py        # entry point
  server.py          # FastAPI app, /health, MCP mount, startup
  config.py          # Settings + .categories.yaml loader
  paths.py           # filename generation per file_unit
  frontmatter.py     # render + parse YAML frontmatter
  auth.py            # OAuth 2.0 + PKCE + bearer middleware (trust-all)
  tools/
    __init__.py      # register all 7 tools on the FastMCP server
    write_note.py    # S1 — real
    stubs.py         # 6 typed stubs (replaced in later milestones)
```

Architecture notes: [../architecture.md](../architecture.md).
