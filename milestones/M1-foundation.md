# M1 — Foundation: One tool reachable end-to-end

**Status:** Not started
**Estimated effort:** ~4 focused days
**Depends on:** —
**Unlocks:** M2 (Read), M3 (Smart Save)
**Source spec:** [../product_spec.md](../product_spec.md)

End state: you can save a pre-formatted note from claude.ai chat. The server is up, OAuth works, the tunnel is reachable, and `write_note` produces a correctly-shaped file on disk.

---

## Build order within M1

1. **I1 skeleton** — FastAPI + FastMCP boots, all seven tools registered as typed stubs.
2. **S1 `write_note`** — first real tool, replaces I1's stub.
3. **I2 OAuth + I3 quick tunnel** — exposes the server to claude.ai. Done last so you've got a working tool to validate against.

---

## I1 — Server + MCP layer

**Goal.** A FastAPI + FastMCP process that serves the seven MCP tools (`search_notes`, `list_notes`, `read_note`, `write_note`, `move_note`, `process_inbox`, `save_conversation`) over a local port.

**Scope.**
- FastAPI app with FastMCP mounted; bind to `localhost:8765`.
- Tool registration for the seven MCP tools — at this milestone they can be stubs that return well-typed placeholder responses. The S/R/X milestones replace stubs with real implementations.
- `.categories.yaml` loader on startup, with clear error if missing/malformed.
- Structured logging (request id, tool name, duration).
- A `GET /health` endpoint returning `{ok: true, version, categories_loaded: N}`.
- Process exits non-zero on fatal config errors.

**Acceptance criteria.**
1. `uvicorn`/equivalent boots the server on port 8765 and stays up.
2. `GET /health` returns 200 with the expected payload.
3. The MCP `tools/list` endpoint advertises all seven tools with correct names + schemas.
4. Calling each tool stub returns a typed response (no 500s).
5. Missing `.categories.yaml` → process logs a clear error and exits non-zero.
6. Malformed `.categories.yaml` → same.
7. Logs include request id, tool name, duration in ms.

**Test plan.**
- Boot test: start process in CI against a fixture `~/Notes/`, hit `/health`, hit `tools/list`, hit each tool stub.
- Negative tests: missing yaml, malformed yaml — both produce non-zero exit + readable error.
- Schema test: assert MCP tool schemas match the contracts described in the spec.

**Out of scope.** Real tool behavior (covered by S/R/X tracks). Auth (I2). External exposure (I3).

---

## S1 — `write_note`

**Goal.** Provide a single MCP tool that writes a pre-formatted note to the correct location with proper frontmatter, file naming, and file-unit handling.

**Scope.**
- `write_note` MCP tool. Inputs: `category`, `content` (markdown body), optional `title`, `topic`, `tags`, `date`, `source`, `entry_type` (for `ProfessionalDev`).
- Loads `.categories.yaml` to look up the category's `file_unit`.
- Generates the correct file path per pattern:
  - `topic-based` → `{category}/{kebab-topic}.md`
  - `monthly-bucket` → `{category}/YYYY-MM.md`
  - `entry-based` → `{category}/YYYY-MM-DD-{kebab-slug}.md`
  - `mixed` (ProfessionalDev) → switch on `entry_type`: `articles` → entry-based, `threads` → topic-based.
- Renders frontmatter (`created`, `last_updated`, `category`, `tags`, `source`) with sensible defaults (`source: direct` if not supplied).
- For a new file: H1 title + an H2 dated section + body.
- For an existing file: error out — smart append is S2's job (M3).

**Acceptance criteria.**
1. `write_note(category=Finance, topic="refinancing", content=...)` creates `~/Notes/Finance/refinancing.md` with correct frontmatter and H1.
2. `write_note(category=Reflection, content=..., date=2026-05-11)` creates `~/Notes/Reflection/2026-05.md`.
3. `write_note(category=ProductsIdeas, topic="notes-app", content=...)` creates `~/Notes/ProductsIdeas/notes-app.md`.
4. `write_note(category=ProfessionalDev, entry_type="article", title="RAG Eval...", date=2026-05-11, content=...)` creates `~/Notes/ProfessionalDev/2026-05-11-rag-eval-article.md`.
5. Frontmatter always contains `created`, `last_updated`, `category`, `tags` (possibly empty), `source`.
6. File names are kebab-case (no spaces, no caps).
7. Calling `write_note` when the target file already exists returns a clear error referencing the existing path. (Smart append lives in S2.)
8. Calling `write_note` with a category not in `.categories.yaml` returns a clear error.

**Test plan.**
- Unit tests for each filename generator (one per `file_unit` pattern, plus mixed-mode).
- Unit tests for frontmatter rendering — required fields present, dates formatted `YYYY-MM-DD`.
- Integration tests using a temp `~/Notes/` fixture with a seeded `.categories.yaml`. Walk every category, assert file path + content shape.
- Negative tests: unknown category, target file already exists, malformed inputs.

**Out of scope.** Append-to-existing, similarity scoring, conversation parsing, structured note generation.

---

## I2 — OAuth 2.0 + PKCE (trust-all stubs)

**Goal.** Implement the OAuth 2.0 + PKCE handshake claude.ai requires for remote MCP connections, with trust-all stubs (this is a personal instance — no real user separation needed yet, but the protocol shape must be correct).

**Scope.**
- Endpoints: `/.well-known/oauth-authorization-server`, `/authorize`, `/token`, `/register` (dynamic client registration).
- PKCE code-challenge / code-verifier round-trip per RFC 7636.
- Trust-all: any registration succeeds, any authorize request returns a code, any token exchange returns a long-lived bearer token.
- All MCP tool endpoints require `Authorization: Bearer <token>`; missing/invalid → 401.

**Acceptance criteria.**
1. claude.ai can complete the full add-connector flow against the server — discovery → register → authorize → token → tool list.
2. A request to any tool endpoint without a valid bearer token returns 401.
3. A request with a valid bearer token reaches the tool stub.
4. PKCE: a token request whose `code_verifier` doesn't hash to the prior `code_challenge` returns 400.
5. Discovery doc at `/.well-known/oauth-authorization-server` returns the expected fields (issuer, authorization_endpoint, token_endpoint, code_challenge_methods_supported including `S256`).

**Test plan.**
- Integration test simulating the OAuth flow end-to-end with a test client.
- PKCE round-trip — valid and invalid verifier.
- Negative tests on tool endpoints (missing/expired/garbage token).
- Manual end-to-end: connect to the server from claude.ai, confirm tools appear.

**Dependencies.** I1.

**Out of scope.** Real multi-user auth, token revocation UX, per-instance scoping. (Not needed for a personal instance.)

---

## I3 — Public tunnel (Cloudflare quick)

**Goal.** Cloudflare Quick Tunnel exposes the local server to claude.ai over HTTPS. Sufficient to validate the full Mac → tunnel → claude.ai → tool-call path.

**Scope.**
- `cloudflared tunnel --url http://localhost:8765` running as a foreground process or simple LaunchAgent.
- README/runbook step: how to start the tunnel, where the URL prints, how to paste it into claude.ai.
- Document the known weakness: URL changes on every restart — that's what I4 (M4) fixes.

**Acceptance criteria.**
1. Tunnel start command prints a public HTTPS URL.
2. `curl <public_url>/health` succeeds from off-machine.
3. claude.ai connects through the tunnel URL and completes the OAuth flow.
4. End-to-end: call any tool from claude.ai → reaches the server → returns expected response.
5. Runbook step lets the user re-establish the connection after a tunnel restart.

**Test plan.**
- Smoke test: start tunnel, curl `/health` from a phone hotspot.
- E2E: connect from claude.ai, list tools, invoke `list_notes` (once R milestones exist; stub response is fine for I3 alone).

**Dependencies.** I1, I2.

**Out of scope.** Persistence across reboots, stable URL (both covered by I4 in M4).

---

## M1 exit checklist

- [ ] `/health` returns 200 from the public tunnel URL
- [ ] claude.ai completes the add-connector OAuth flow against the tunnel URL
- [ ] All seven tools appear in claude.ai's tool list
- [ ] `write_note` produces a correctly-shaped file on disk for at least one example per `file_unit` pattern
- [ ] Runbook documents how to restart the tunnel and update claude.ai with the new URL
