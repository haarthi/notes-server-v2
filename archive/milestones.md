# Notes App v0.2 — Milestone Plan

**Status:** Draft proposal — 2026-05-12
**Source:** [product_spec.md](./product_spec.md) (v0.2)
**Ordering:** Save → Retrieve → Lifecycle/Misc (per your direction)

---

## How to read this

Each milestone is **releasable on its own** — at the end of it, you have a working capability you could rely on without the later milestones. Each milestone is **fully testable** — explicit acceptance criteria, plus a test plan describing the fixtures, unit tests, and integration tests needed to verify it.

Where a milestone reuses logic from a prior one (e.g. `process_inbox` reuses the save-time decision tree), the dependency is called out explicitly.

---

---

## Suggested build order

Group the work into milestones. Each milestone delivers a capability you could rely on without the next one. Within a milestone, the listed order is the recommended path.

### Milestone 1 — One tool reachable end-to-end (I1 → S1 → I2 → I3)

The path that pays back fastest: get a single tool callable from claude.ai over the internet before going deep on anything else. This is where the project goes from "Python code" to "thing I actually use."

1. **I1 skeleton.** One day. Stubs everywhere; deployable surface.
2. **S1 `write_note`.** One day. Get one tool actually working.
3. **I2 OAuth + I3 quick tunnel.** Two days. Now you can call S1 from claude.ai over the internet.

End of M1: you can save a pre-formatted note from chat. ~4 focused days.

### Milestone 2 — Full Read (R1 → R2 → R3 → R4)

Save is useless without retrieval. M2 lights up the entire Read track so you can list, search, ask questions, and fall back when category inference is ambiguous. Each step is independently usable — R1 alone gives you enumeration; R2 adds ranked search; R3 adds prose answers with citations; R4 widens scope when needed.

4. **R1 List & Read.** One day. Enumerate notes and read full content.
5. **R2 Search + Recency Ranking.** One–two days. Keyword search with `topic_match + recency_boost`.
6. **R3 Synthesized Q&A.** One day for the plumbing, plus prompt iteration during real use. Prose answers with strict `Sources:` footer.
7. **R4 Cross-category Fallback.** Half a day. Kicks in when the inferred category is ambiguous; top-10 cap across all categories.

End of M2: working save-and-retrieve loop. Capture pre-formatted notes, search later, ask natural-language questions, get cited answers.

### Milestone 3 — Smart save (S2 → S3)

With Read working and S1 proven, add the intelligence layer on the save side.

8. **S2 placement + similarity.** Two days. Build with a fake scorer first to nail the decision tree; swap in the real Claude call last.
9. **S3 `save_conversation` tool + prompt iteration.** One day for the tool, plus a few days of prompt iteration while you actually use it.

End of M3: `@save` works end-to-end.

### Milestone 4 — Persistence + inbox (I4 → X1)

10. **I4 named tunnel + launchd.** Half a day. Do this once everything works on the quick tunnel and the URL drift starts annoying you — that's the right forcing function.
11. **X1 `process_inbox` + archival.** One day. Reuses S2's structuring + decision tree against `raw.md` entries.

### Milestone 5 — Lifecycle polish (X2 → X3 → X4)

12. **X2 `move_note`.** Half a day. Lazy correction across categories.
13. **X3 category lifecycle.** One day. Chat command + SIGHUP hot reload.
14. **X4 subfolder grouping.** Half a day.

## Milestone summary

| # | Name | Track | Goal | Depends on |
|---|---|---|---|---|
| I1 | Server + MCP layer | Infra | FastAPI + FastMCP process serving the seven MCP tools over loopback | — |
| I2 | OAuth 2.0 + PKCE | Infra | Trust-all auth stubs satisfying claude.ai's remote-MCP requirements | I1 |
| I3 | Public tunnel (quick) | Infra | Cloudflare Quick Tunnel exposing the local server to claude.ai over HTTPS | I1, I2 |
| I4 | Persistent server URL (P0) | Infra | Named tunnel + launchd auto-start for a stable, boot-resilient URL | I3 |
| S1 | `write_note` | Save | Direct write of a pre-formatted note to the right location with correct frontmatter, naming, and file-unit handling | — |
| S2 | Smart Placement | Save | Append-vs-new-file decision tree with idempotency | S1 |
| S3 | `@save` | Save | Detect token, snapshot conversation, structure, route via Smart Placement | S1, S2 |
| R1 | List & Read | Retrieve | `list_notes` + `read_note` — basic enumeration | — |
| R2 | Search + Recency Ranking | Retrieve | `search_notes` with `topic_match + recency_boost` ranking | R1 |
| R3 | Synthesized Q&A | Retrieve | Prose answer + `Sources:` line for natural-language questions | R1, R2 |
| R4 | Cross-category Fallback | Retrieve | Ambiguous queries search all categories, top-10 cap | R2, R3 |
| X1 | `process_inbox` + Archival | Misc | Parse `raw.md`, route each entry, archive non-destructively, clear inbox | S1, S2 |
| X2 | `move_note` | Misc | Lazy correction — move note to different category, rename, update frontmatter | R1 |
| X3 | Category Lifecycle | Misc | Add categories via chat command and via direct `.categories.yaml` edit (SIGHUP) | S1 |
| X4 | Subfolder Grouping | Misc | Move matching files into a subfolder via chat command | X2 |

---

# Infrastructure

The infra track delivers the foundation everything else stands on: the MCP server process, the auth handshake claude.ai requires for remote MCP, the HTTPS tunnel, and the upgrade from "quick tunnel that drifts" to a persistent URL that survives reboots. v0.1 is already built, so I1–I3 largely describe regression-test surface plus any hardening; I4 is the P0 from the spec's roadmap and is net-new.

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
- Document the known weakness: URL changes on every restart — that's what I4 fixes.

**Acceptance criteria.**
1. Tunnel start command prints a public HTTPS URL.
2. `curl <public_url>/health` succeeds from off-machine.
3. claude.ai connects through the tunnel URL and completes the OAuth flow.
4. End-to-end: call any tool from claude.ai → reaches the server → returns expected response.
5. Runbook step lets the user re-establish the connection after a tunnel restart.

**Test plan.**
- Smoke test: start tunnel, curl `/health` from a phone hotspot.
- E2E: connect from claude.ai, list tools, invoke `list_notes` (once S/R milestones exist; stub response is fine for I3 alone).

**Dependencies.** I1, I2.

**Out of scope.** Persistence across reboots, stable URL (both covered by I4).

---

## I4 — Persistent server URL (P0)

**Goal.** Replace the quick tunnel with a named tunnel (or ngrok static domain) and add macOS launchd auto-start so the server + tunnel come up on boot. The URL is stable across restarts; claude.ai never needs to be re-pasted.

**Scope.**
- Cloudflare named tunnel (or ngrok reserved domain) on a stable hostname like `notes.haarthi.dev`.
- Tunnel credentials/config stored in `~/.cloudflared/` (or equivalent).
- Two launchd plists at `~/Library/LaunchAgents/`:
  - one for the Notes MCP server
  - one for `cloudflared` running the named tunnel
- Both plists set `KeepAlive=true` and `RunAtLoad=true`.
- Logs land in a predictable path (e.g. `~/Library/Logs/notes-mcp/*.log`).
- One-time setup script or runbook that installs the plists and DNS record.

**Acceptance criteria.**
1. The public URL is the same before and after a Mac reboot.
2. After `sudo reboot`, both processes start automatically within ~30s of login (or earlier if user is set to auto-login).
3. `launchctl list | grep notes` shows both services running.
4. Killing either process triggers a launchd restart within seconds.
5. Logs accumulate at the documented path with rotation or size cap to prevent disk fill.
6. claude.ai connector configured against the stable URL keeps working across reboots with no user intervention.

**Test plan.**
- Reboot test: configure, reboot, verify URL still serves `/health` within 30s of login.
- Process-kill test: `kill -9` the server, verify launchd restarts it.
- Long-run test: leave running for a week, verify still up and log rotation worked.
- Manual end-to-end after each test: claude.ai still calls tools successfully.

**Dependencies.** I3.

**Out of scope.** Hosting the server on a remote machine (defeats the local-files architecture). Reverse-proxying multiple instances (the work-notes instance, P2, will need its own tunnel/host).

---

# Use Case: Save Content

The save track delivers the core capture pipeline: somebody pre-formats and writes (S1), the system can decide where new content goes relative to existing files (S2), and Claude can save mid-conversation (S3). At the end of this track, capture from chat works end-to-end. Inbox processing is intentionally pushed to X1 because it reuses S1 + S2 but adds the parsing/archival concerns.

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
- For an existing file: error out — smart append is S2's job.

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

## S2 — Smart Placement (append-vs-new decision tree)

**Goal.** Given pre-structured content plus an inferred category, decide whether to append to an existing file or create a new one, and handle the three cases (high match / medium match / no match) per the spec.

**Scope.**
- Internal `route_note(category, structured_note)` function (or exposed as an MCP tool — your call) implementing the save-time decision tree.
- Steps:
  1. List existing files in `category`. Read frontmatter + first H2 of each.
  2. Score semantic similarity between the new note and each file. (Implementation detail — embeddings, single-batched Claude call, or N classifier calls.)
  3. Branch:
     - **High** → prepend a new dated H2 to the matched file's body (newest at top), preserve frontmatter, bump `last_updated`.
     - **Medium / ambiguous** → return a `needs_clarification` result with the candidate file path(s). Caller (e.g. `@save`) asks the user.
     - **No** → call `write_note` to create a new file.
- Idempotency: before appending, compare the new note's inferred title + same-day H2 in the matched file. If both match, return `skipped_duplicate` without writing.
- High match always bumps `last_updated` in frontmatter to today.

**Acceptance criteria.**
1. Seeded `Finance/refinancing.md` + new content semantically about refinancing → new dated H2 is prepended above the existing one. Frontmatter intact, `last_updated` bumped.
2. Seeded `Finance/refinancing.md` only + new content about taxes → new file `Finance/taxes-{slug}.md` is created via `write_note`.
3. Two seeded Finance files of comparable strength → returns `needs_clarification` with both paths.
4. Re-running with identical content same day → `skipped_duplicate`, no file change.
5. Append preserves prior dated sections and frontmatter exactly.
6. Append placement is at the top of the body, after frontmatter and H1.

**Test plan.**
- Unit tests for the scorer with mocked classifier returning each tier (high/medium/no).
- Integration tests: seed category with N files, run placement with various inputs, snapshot resulting files.
- Idempotency test: run twice, second call is no-op.
- Frontmatter test: confirm `last_updated` changes on append, `created` does not.

**Dependencies.** S1 (uses `write_note` for the no-match branch).

**Out of scope.** Extracting structured content from raw text — caller provides a structured note already. Conversation parsing lives in S3, inbox parsing in X1.

---

## S3 — `@save` in chat

**Goal.** Detect `@save` in a Claude message, snapshot the conversation, structure it into a note, and route it via Smart Placement.

**Scope.**
- Token detection: literal case-insensitive match on `@save` anywhere in the user's most recent message. No intent inference, no paraphrase detection.
- Snapshot semantics: capture content up to and including the message containing the token; ignore content after.
- Dominant-topic extraction: Claude reads the conversation and identifies the primary topical thread.
- Multi-topic clarification: if 2+ distinct topics, Claude asks one-line *"save as one note or two?"* before writing anything.
- Structured note generation per schema: H1 title, 1–2 paragraph summary, **Key Points**, **Actions** with checkbox items, any links/refs. No raw transcript.
- Silent inference: category and 2–5 tags.
- Calls into S2 (`route_note`) with the structured note.
- Multiple `@save`s per conversation: each call re-runs the decision tree against current content. S2 idempotency handles the "no new content" case.
- `source: claude-conversation` in frontmatter.

**Acceptance criteria.**
1. Message containing literal `@save` (any casing) triggers the flow; messages without it do not.
2. Single-topic conversation → structured note with all schema sections, routed by S2.
3. Multi-topic conversation → Claude asks one-line clarification; no file change until user replies.
4. Snapshot: content authored after the `@save` message is not included in the saved note.
5. `@save` → keep talking on the same topic → `@save` again → appends new dated H2 to the same file (S2 high-match).
6. `@save` → conversation shifts topic → `@save` again → new file (S2 no-match) or clarifies (S2 medium).
7. Re-issuing `@save` with no new content is a no-op (S2 `skipped_duplicate`).

**Test plan.**
- Unit test for token detector — positive/negative cases, casing variations, token inside code blocks (decide: still triggers? recommended yes, per the spec's "literal match anywhere").
- Integration tests via simulated conversation fixtures:
  - single-topic
  - multi-topic (expect clarification)
  - content after `@save` (expect it ignored)
  - two `@save`s same topic (expect append)
  - two `@save`s different topics (expect new file)
- Manual end-to-end test in claude.ai chat against the personal instance — capture a real conversation, confirm file location and shape in Obsidian.

**Dependencies.** S1, S2.

**Out of scope.** `@save Finance` flag overrides (P2). Proactive save suggestions (rejected). Auto-save heuristics (rejected).

---

# Use Case — Retrieve Content

The retrieve track delivers explicit retrieval (Level 1). Order is: plumbing (R1) → keyword search (R2) → prose synthesis (R3) → cross-category fallback (R4). Each step is independently usable.

---

## R1 — List & Read

**Goal.** Allow Claude to enumerate notes and read full content of a specific note.

**Scope.**
- `list_notes` MCP tool. Optional `category` filter. Returns array of `{path, title, category, last_updated, tags, source}`.
- `read_note` MCP tool. Accepts `path` (or `category` + `name`). Returns full markdown content.
- Both respect `.categories.yaml` folder structure.

**Acceptance criteria.**
1. `list_notes()` with no filter returns all notes across all categories.
2. `list_notes(category=Finance)` returns only Finance notes.
3. Each list entry's metadata reflects the file's actual frontmatter.
4. `read_note(path)` returns content byte-identical to the file on disk.
5. `read_note` on a non-existent path returns a clean error.
6. `list_notes` ignores `_inbox/` and other non-category directories.

**Test plan.**
- Integration tests against a seeded `~/Notes/` with 2–3 categories and 4–6 files.
- Frontmatter metadata extraction test — including notes that lack optional fields.
- Negative tests: missing path, invalid category.

**Out of scope.** Search, ranking, synthesis.

---

## R2 — Search with Recency Ranking

**Goal.** Keyword search across notes with recency-weighted ranking.

**Scope.**
- `search_notes` MCP tool. Inputs: `query` (string), optional `category`, optional `limit` (default 10).
- Searches body, title, tags. Case-insensitive.
- Ranking: `topic_match_strength + recency_boost`. Newer notes win ties.
- Returns `[{path, title, snippet, score, last_updated}]`.
- Top 10 cap by default (matches the cross-category cap in spec).

**Acceptance criteria.**
1. Query matching a title returns that note with high score.
2. Query matching a tag returns notes carrying that tag.
3. Body match returns the note with a snippet around the match.
4. Two notes with equal topic strength: newer `last_updated` ranks first.
5. `category=Finance` scopes results to that folder.
6. Returns ≤ `limit` results (default 10).
7. Empty query returns a clean error (don't dump every note).

**Test plan.**
- Seed notes with controlled keywords and explicit `last_updated` values to drive ranking tests.
- Ties test: two notes identical except for date → newer first.
- Category-scope test.
- Cap test: seed 20 matching notes → only 10 returned.
- Snippet test: snippet contains the matched keyword.

**Out of scope.** Synthesized prose answer (R3). Cross-category fallback (R4).

---

## R3 — Synthesized Q&A

**Goal.** When the user asks a natural-language question, Claude reads matching notes and produces a synthesized prose answer ending with a `Sources:` line citing only the notes it used.

**Scope.**
- This is Claude-side behavior using R1 + R2 tools — likely a system-prompt or tool-orchestration instruction rather than a new MCP tool. Decide which during build.
- Response shape: 1–2 paragraph prose answer + `Sources: path1, path2`.
- Cite only the notes whose content materially informed the answer.
- If no notes match, say so plainly — don't fabricate.

**Acceptance criteria.**
1. "What have I noted about refinancing?" → prose answer citing `Finance/refinancing.md`.
2. `Sources:` line lists only notes whose content shows up in the answer.
3. If query has no matches → answer states that, no `Sources:` line or empty line.
4. Answer is grounded in the retrieved content — no facts beyond what the notes contain.

**Test plan.**
- Canned Q&A fixtures: question + seeded notes + rubric-graded expected answer (use Claude-as-judge or human spot-check; exact-match is too brittle here).
- Negative test: query for content that doesn't exist → polite "no notes" response.
- Citation accuracy: assert every path on the `Sources:` line appears in the retrieval result set.
- Manual smoke tests in claude.ai against real notes.

**Dependencies.** R1, R2.

**Out of scope.** Passive retrieval (P2). Cross-category fallback (R4).

---

## R4 — Cross-category Fallback

**Goal.** When the inferred category is ambiguous, search across all categories and return top 10 by combined score.

**Scope.**
- Triggered when Claude can't confidently scope the query to one category.
- Fall back to all-category search via R2 with no category filter.
- Top 10 cap by combined `topic_match_strength + recency_boost`.
- Feeds into R3's synthesis step.

**Acceptance criteria.**
1. Query like "what do I think about X" with relevant content in Reflection + ProductsIdeas returns matches from both.
2. Top 10 enforced regardless of total matches.
3. R3 synthesis still cites correctly across categories.
4. If the user later refines to a specific category, the search re-scopes (no stuck state).

**Test plan.**
- Seed notes across 3 categories with related content.
- Category-ambiguous query → assert results span categories.
- Stress test with 20+ matching notes → assert exactly 10 returned, ordered.
- Pair with R3 fixtures: cross-category answer has multi-category `Sources:` line.

**Dependencies.** R2, R3.

**Out of scope.** Passive retrieval (P2).

---

# Additional Use Cases — Lifecycle & Misc

Once save and retrieve work, this track adds the operational features: inbox flow, lazy correction, category management, and within-category organization.

---

## X1 — `process_inbox` + Inbox Archival

**Goal.** Process every entry in `raw.md` through the save pipeline, archive the original non-destructively, and clear `raw.md` once all entries succeed.

**Scope.**
- `process_inbox` MCP tool.
- Parse `~/Notes/_inbox/raw.md` into entries split on `---` or two blank lines.
- For each entry:
  1. Structure the content into the schema (same generator as `@save`).
  2. Route via S2 (Smart Placement). `source: inbox` in frontmatter.
  3. On success, append the original raw text to `~/Notes/_inbox/processed/YYYY-MM.md` with header `## YYYY-MM-DD HH:MM` and `[Filed to: {path}]` pointer.
- Per-entry atomicity: failures don't affect successes.
- After the run:
  - If all entries succeeded → clear `raw.md`.
  - If any failed → leave only the failed entries in `raw.md`, report which.
- Re-running on empty `raw.md` is a no-op.
- For `medium` placement results from S2: defer to the user — write a per-entry note in the chat output and leave that entry in `raw.md`. Don't pick a side silently.

**Acceptance criteria.**
1. `raw.md` with 3 entries (separated by `---`) → 3 routed notes after processing.
2. Each routed entry has a corresponding line in `_inbox/processed/YYYY-MM.md` with the correct `[Filed to: path]` pointer.
3. Archive header has timestamp; original raw text is verbatim under the header.
4. After a fully successful run, `raw.md` is empty.
5. If entry #2 fails (e.g. classifier throws), entries #1 and #3 still succeed and only #2 remains in `raw.md`.
6. Archive path is `_inbox/processed/YYYY-MM.md` for the current month — creates the file if missing, appends if present.
7. Re-processing the same raw entry produces an S2 `skipped_duplicate` and the entry is removed from `raw.md` (idempotent).
8. A medium-match entry leaves the entry in `raw.md` and surfaces the candidate file(s) in the tool response.

**Test plan.**
- Fixture `raw.md` files for each case: single entry, three entries, ambiguous entry, failing entry.
- Verify final state of `raw.md`, all destination files, and the archive file.
- Inject a failure in entry #2 → assert atomicity.
- Empty-raw run → no-op assertion.
- Idempotency: process same `raw.md` twice → second run is a no-op (no duplicates, no archive double-writes).

**Dependencies.** S1, S2.

**Out of scope.** Scheduled/cron processing (P1). Auto-creation of categories from misfit clusters (P1).

---

## X2 — `move_note`

**Goal.** Move a note to a different category (and/or rename it), updating frontmatter and relocating the file.

**Scope.**
- `move_note` MCP tool. Inputs: `source_path`, `target_category`, optional `new_name`.
- Updates `category` in frontmatter; bumps `last_updated`.
- Relocates the file to `~/Notes/{target_category}/`.
- Optionally renames file (must remain kebab-case for topic-based; `YYYY-MM-DD-slug.md` for entry-based; `YYYY-MM.md` for time-bucket).
- If new name conflicts with existing file → return clear error, do not overwrite.
- Body content is otherwise unchanged.

**Acceptance criteria.**
1. `move_note(Finance/refinancing.md, ProductsIdeas)` → file now at `ProductsIdeas/refinancing.md`. Frontmatter `category: ProductsIdeas`. `last_updated` bumped.
2. With `new_name="loan-refi-thinking"` → file at `ProductsIdeas/loan-refi-thinking.md`.
3. Body content (everything below frontmatter) is unchanged.
4. Move to non-existent category → clean error.
5. Target name conflict → clean error, source file untouched.
6. After move, retrieval (R1 + R2) finds the file at the new path.

**Test plan.**
- Move a topic-based file to a topic-based category — verify path, frontmatter, content.
- Move with rename — verify naming.
- Negative tests: bad target category, name conflict.
- Cross-pattern move (entry-based file to topic-based category) — document and test the chosen behavior (suggest: keep name as-is unless user renames).
- Post-move retrieval test: `list_notes(category=ProductsIdeas)` and `search_notes(query=...)` find the moved file.

**Dependencies.** R1 (for post-move verification).

**Out of scope.** Bulk moves (could be a thin wrapper later). Auto-suggesting moves.

---

## X3 — Category Lifecycle (chat command + hot reload)

**Goal.** Two user-initiated paths to add a category, both fully testable: chat command, and direct `.categories.yaml` edit picked up via SIGHUP.

**Scope.**
- Chat command: e.g. *"Add a new category called Travel, topic-based"* → Claude parses, updates `.categories.yaml`, creates folder, confirms.
- Direct edit: user edits `.categories.yaml`; server picks up on `SIGHUP` or restart.
- SIGHUP handler in the FastAPI/FastMCP process.
- `.categories.yaml` validation on read: reject malformed entries, keep prior in-memory config, log the error.
- Adding a duplicate category → no-op with a clear message.

**Acceptance criteria.**
1. Chat command adds the new category to `.categories.yaml` with correct `file_unit` and creates `~/Notes/{Category}/`.
2. After the chat command, `write_note` for the new category succeeds.
3. Editing `.categories.yaml` directly and sending SIGHUP → server recognizes the new category without restart.
4. Malformed YAML on reload → server logs an error and keeps the previous in-memory config (no crash).
5. Duplicate category → clean message, no destructive change.
6. Validation rejects unknown `file_unit` values.

**Test plan.**
- Integration test for the chat command path: simulate the parsed command, verify yaml + folder + `write_note` works.
- SIGHUP test: edit yaml in a fixture dir, send signal, assert new category is now usable.
- Negative tests: malformed yaml, unknown `file_unit`, duplicate category.

**Dependencies.** S1 (everything reads `.categories.yaml`).

**Out of scope.** Auto-proposing categories from misfit clusters (P1).

---

## X4 — Subfolder Grouping

**Goal.** Move a set of files in a category into a subfolder via chat command.

**Scope.**
- Chat command: *"Group my NotesApp files under ProductsIdeas/NotesApp/."*
- Claude identifies matching files (filename match or content match), confirms the list with the user, then moves them into the subfolder.
- Frontmatter `category` stays the same — subfolders are within-category organization, not new categories.
- New saves do NOT automatically route into the subfolder. (User can manually `move_note` later.)

**Acceptance criteria.**
1. Command moves only the matching files into the new subfolder.
2. Frontmatter (including `category`) is unchanged.
3. `list_notes` and `search_notes` still find the moved files.
4. Subfolder is created if missing.
5. Existing files in the subfolder are not overwritten — name conflict surfaces an error.
6. Claude confirms the file list with the user before moving (one-line confirmation).

**Test plan.**
- Seed `ProductsIdeas/` with `notes-app.md` and 2 related files.
- Issue the command (simulated parsed intent).
- Verify file paths and frontmatter.
- Verify retrieval finds the moved files.
- Name-conflict negative test.

**Dependencies.** X2 (reuses move semantics — likely the same underlying file mover).

**Out of scope.** Auto-proposing subfolders from clustering (P1). Routing new saves into subfolders.

---

# Open questions worth nailing down before build

A few decisions that affect milestone implementation but aren't fixed by the spec:

1. **Where does the structured-note generator live?** S3 (`@save`) and X1 (`process_inbox`) both need to turn raw text into the schema. Recommend extracting it as a shared module called by both, rather than duplicating prompt logic. Worth deciding before S3 lands.
2. **Similarity scoring in S2 — single batched Claude call vs. embeddings vs. N classifier calls?** Latency budget for `@save` should be ~1–3s; with 5 files per category that's easy, with 30 files the design matters. Recommend single batched Claude call for now, revisit per the P2 "Save-flow performance tuning" item.
3. **`@save` inside code blocks** — does triple-backtick context suppress the token? Spec says "literal match anywhere"; recommend honoring that and not parsing markdown structure. Easy to revisit if it gets annoying.
4. **Idempotency window** — S2's `skipped_duplicate` check is "same-day note with same inferred title." Should "same inferred title" be exact match, or fuzzy? Recommend exact for v0.2; fuzzy adds a whole rabbit hole.
5. **R3 response shape** — strict `Sources:` line at end (with bullet list?) vs. inline citations? Recommend strict footer-only for v0.2 to keep the retrieval contract simple. Worth confirming with how it actually reads in chat.

---

# Implementation walkthrough

This section is the "how" complement to the milestone definitions above. It describes the project layout, the substantive code in each milestone, the gotchas, and a suggested build order that interleaves the two tracks for fastest feedback.

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

**Stack.** Python 3.12, FastAPI, the official `mcp` Python SDK (FastMCP), Pydantic v2, PyYAML + `python-frontmatter`, the `anthropic` SDK, `pytest` + `httpx` for integration tests, `structlog` for JSON logs.



---