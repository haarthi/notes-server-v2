# M3 — Smart Save: append-or-new + `@save`

**Status:** Not started
**Estimated effort:** ~3 focused days plus a few days of prompt iteration during real use
**Depends on:** M1 (S1 `write_note`)
**Unlocks:** M4 (X1 `process_inbox` reuses S2's structuring + decision tree)
**Source spec:** [../product_spec.md → What Gets Saved & How](../product_spec.md#what-gets-saved--how)

End state: `@save` works end-to-end. Type `@save` in a Claude chat; the conversation gets structured, routed to the right file (appended if related, new file if not), and stored under the correct frontmatter and naming.

---

## Build order within M3

1. **S2 Smart Placement** — build with a fake scorer first to nail the decision tree; swap in the real Claude call last.
2. **S3 `@save`** — token detection, snapshot, structuring, then hand off to S2.

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

**Out of scope.** Extracting structured content from raw text — caller provides a structured note already. Conversation parsing lives in S3, inbox parsing in X1 (M4).

### Open question — similarity scoring approach

Single batched Claude call vs. embeddings vs. N classifier calls? Latency budget for `@save` should be ~1–3s; with 5 files per category that's easy, with 30 files the design matters. **Recommendation:** single batched Claude call for now, revisit per the P2 "Save-flow performance tuning" item in the PRD roadmap.

### Open question — idempotency window

S2's `skipped_duplicate` check is "same-day note with same inferred title." Should "same inferred title" be exact match, or fuzzy? **Recommendation:** exact for v0.2; fuzzy adds a whole rabbit hole.

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
- Unit test for token detector — positive/negative cases, casing variations, token inside code blocks (see open question below).
- Integration tests via simulated conversation fixtures:
  - single-topic
  - multi-topic (expect clarification)
  - content after `@save` (expect it ignored)
  - two `@save`s same topic (expect append)
  - two `@save`s different topics (expect new file)
- Manual end-to-end test in claude.ai chat against the personal instance — capture a real conversation, confirm file location and shape in Obsidian.

**Dependencies.** S1, S2.

**Out of scope.** `@save Finance` flag overrides (P2 in PRD roadmap). Proactive save suggestions (rejected — see PRD's "Considered & Rejected"). Auto-save heuristics (rejected).

### Open question — structured-note generator location

S3 (`@save`) and X1 (M4 `process_inbox`) both need to turn raw text into the schema. **Recommendation:** extract it as a shared module (`structuring.py` per [../architecture.md](../architecture.md)) called by both, rather than duplicating prompt logic. Worth deciding *before* S3 lands so M4 doesn't have to refactor it.

### Open question — `@save` inside code blocks

Does triple-backtick context suppress the token? Spec says "literal match anywhere"; **recommendation:** honor that and don't parse markdown structure. Easy to revisit if it gets annoying in real usage.

---

## M3 exit checklist

- [ ] S2 routes correctly across all three branches (high / medium / no match) against a seeded fixture
- [ ] S2 idempotency: same content twice in one day is a no-op
- [ ] `@save` in a single-topic conversation produces a structured note in the right file
- [ ] `@save` in a multi-topic conversation asks the one-line clarification
- [ ] Structured-note generator lives in a shared module reusable by M4 (open question above)
- [ ] Similarity-scoring approach decision is logged (open question above)
