# M2 — Full Read: list, search, ask

**Status:** Not started
**Estimated effort:** ~3–4 focused days plus prompt iteration during real use
**Depends on:** M1 (Foundation)
**Unlocks:** Working save-and-retrieve loop alongside M1's S1
**Source spec:** [../product_spec.md → What Gets Retrieved & How](../product_spec.md#what-gets-retrieved--how)

End state: capture pre-formatted notes (from M1), then search later, ask natural-language questions, get cited prose answers. Cross-category fallback handles ambiguous queries.

---

## Build order within M2

1. **R1 List & Read** — plumbing first.
2. **R2 Search + Recency Ranking** — keyword search with `topic_match + recency_boost`.
3. **R3 Synthesized Q&A** — prose answers + `Sources:` footer.
4. **R4 Cross-category Fallback** — kicks in when category is ambiguous.

Each step is independently usable. R1 alone gives you enumeration; R2 adds ranked search; R3 adds prose answers with citations; R4 widens scope when needed.

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

### Open question — `Sources:` line shape

Strict `Sources:` line at end (with bullet list?) vs. inline citations? **Recommendation:** strict footer-only for v0.2 to keep the retrieval contract simple. Worth confirming with how it actually reads in chat — revisit after the first week of using R3 against real notes.

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

## M2 exit checklist

- [ ] `list_notes` returns all notes from a seeded fixture and respects category filter
- [ ] `search_notes` ranks ties by recency
- [ ] A natural-language question in claude.ai returns a prose answer with a correct `Sources:` line
- [ ] An ambiguous query produces multi-category matches without manual scope hints
- [ ] R3 `Sources:` line shape decision is logged (open question above)
