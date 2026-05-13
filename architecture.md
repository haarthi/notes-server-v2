# Notes App — Architecture & Implementation Reference

**Status:** Stable reference — last updated 2026-05-12
**Companion to:** [product_spec.md](./product_spec.md) (the "what & why") and [milestones/](./milestones/) (the "how & when")

This document is the "how" complement to the product spec. It describes the project skeleton, the stack, where each substantive piece of logic lives, and the cross-milestone gotchas. Individual milestones reference this file rather than re-describing the layout.

---

## Project skeleton

```
notes-mcp/
  pyproject.toml
  src/notes_mcp/
    server.py            # FastAPI + FastMCP wiring, /health, startup hook
    config.py            # .categories.yaml loader + Pydantic models
    paths.py             # filename generation per file_unit
    frontmatter.py       # parse + render YAML frontmatter (python-frontmatter)
    placement.py         # S2: route_note decision tree
    similarity.py        # S2: classifier (Anthropic API)
    structuring.py       # raw text → schema (used by @save + process_inbox)
    auth/
      oauth.py           # /authorize, /token, /register, discovery
      pkce.py            # SHA256 verifier check
      tokens.py          # bearer middleware, in-memory token store
    tools/               # one file per MCP tool
  tests/
    fixtures/notes/      # seeded ~/Notes/ trees
    unit/  integration/
  scripts/install-launchd.sh
  launchd/*.plist
```

---

## Stack

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.12 | |
| Web framework | FastAPI | Hosts MCP endpoints + OAuth routes + `/health` |
| MCP layer | Official `mcp` Python SDK (FastMCP) | Tool registration, schema generation |
| Models | Pydantic v2 | Tool input/output validation, `.categories.yaml` parsing |
| YAML + frontmatter | PyYAML + `python-frontmatter` | Parse and render note frontmatter without losing field order |
| AI calls | `anthropic` SDK | Structuring, similarity scoring, conversation summarization |
| Tests | `pytest` + `httpx` | Unit + integration; integration tests boot the FastAPI app with a fixture `~/Notes/` |
| Logging | `structlog` | JSON logs with request id, tool name, duration |

The infrastructure choices at the spec level (Cloudflare tunnel, OAuth 2.0 + PKCE, local markdown storage) are documented in [product_spec.md → Infrastructure](./product_spec.md#infrastructure). This file covers the *code-level* choices behind those.

---

## Where each piece of logic lives

| Concern | Module | First introduced in |
|---|---|---|
| FastAPI app, startup hook, `/health` | `server.py` | M1 (I1) |
| `.categories.yaml` parsing + validation | `config.py` | M1 (I1) |
| Filename generation per `file_unit` | `paths.py` | M1 (S1) |
| Frontmatter render / parse | `frontmatter.py` | M1 (S1) |
| OAuth 2.0 + PKCE + token middleware | `auth/` | M1 (I2) |
| Append-vs-new decision tree | `placement.py` | M3 (S2) |
| Similarity scoring (classifier) | `similarity.py` | M3 (S2) |
| Raw text → schema (structured note generator) | `structuring.py` | M3 (S3); reused by M4 (X1) |
| Per-tool handlers | `tools/<name>.py` | One per MCP tool, introduced with that tool's milestone |
| Launchd plists + tunnel config | `scripts/` + `launchd/` | M4 (I4) |

---

## Cross-cutting gotchas

A handful of issues that surface in multiple milestones — capturing them once here so the milestone files don't repeat them.

### `python-frontmatter` field order

`python-frontmatter` preserves field order on parse but the default dump alphabetizes. Use `frontmatter.dumps(post, sort_keys=False)` or wrap with a custom YAML dumper. Without this, every save reshuffles `created` / `last_updated` / `category` and produces churn in `git diff`.

### File-write atomicity

All file writes (write_note, smart-append in S2, archive append in X1, move_note) should write to a tempfile in the same directory and `os.replace` into place. Avoids half-written files if the process is killed mid-write.

### `last_updated` vs `created`

`created` is set on first write and **never changes**. `last_updated` bumps on every append, move, or rename. The S2 smart-append path is the most common offender — easy to forget when prepending a new H2.

### Newest-at-top H2 ordering

Rolling files use reverse-chron H2 sections. The append in S2 must insert the new H2 *after* the H1 title and *before* the previous newest H2 — not at end of file. Snapshot tests catch the simple cases; the gotcha is when the H1 has trailing content (intro paragraph) before the first H2.

### Stdout in launchd

Under launchd, anonymous stdout goes to `/dev/null` unless redirected in the plist. Always set `StandardOutPath` and `StandardErrorPath` in the plists (M4 / I4) — otherwise debugging "why didn't it start on boot" requires rerunning manually.

---

## Testing strategy

| Layer | What it covers | Where |
|---|---|---|
| Unit | Pure functions: filename generation, frontmatter render, similarity tier branching with mocked classifier | `tests/unit/` |
| Integration | FastAPI app booted against a fixture `~/Notes/` tree; full tool calls through HTTP | `tests/integration/` |
| Fixtures | Seeded `~/Notes/` trees per scenario (empty, populated, with `_inbox/`, with subfolders) | `tests/fixtures/notes/` |
| Manual | End-to-end against claude.ai after each milestone — connect, list tools, exercise the new capability | Runbook |

Anthropic API calls are mocked in unit tests, real in integration tests (gated behind an env var so CI can run without an API key by default).

---

## Build-order rationale

The milestone order (M1 → M2 → M3 → M4 → M5) is described in [milestones/README.md](./milestones/README.md). The rationale lives there because it's a milestone-track concern, not an architecture concern.
