# Notes App — To-Do

Project status, build items, and enhancement backlog. For the requirements/design, see [`product_spec.md`](./product_spec.md).

**Last Updated:** 2026-05-11

---

## Status

### v0.1 — Initial Build Complete

**Working**

- [x] Notes MCP server running locally on port 8765
- [x] Cloudflare tunnel exposing server to claude.ai
- [x] OAuth 2.0 + PKCE handshake with claude.ai
- [x] All 5 category folders created at `~/Notes/`
- [x] `search_notes`, `list_notes`, `read_note`, `write_note` tools working
- [x] `process_inbox` tool working (destructive clear — pre-v0.2)
- [x] `save_conversation` (@save) working
- [x] Obsidian pointed at `~/Notes/`

**Known Issues**

- [ ] Cloudflare quick tunnel URL rotates on every server restart — requires re-adding URL to claude.ai settings each session

---

## v0.2 — Next Build (from spec refinement)

**Schema & save**

- [ ] Implement per-category file-unit defaults (hybrid map)
- [ ] Implement entity-based file-unit pattern (`entity` + `entity_type` frontmatter, entity-name matching)
- [ ] Implement semantic-match append decision tree in `process_inbox` and `save_conversation`
- [ ] Implement medium-confidence confirmation prompt
- [ ] Implement reverse-chronological dated H2 append format
- [ ] Implement inbox archival to `_inbox/processed/YYYY-MM.md` (replace destructive clear)
- [ ] Add `last_updated` frontmatter field; update on every append

**Retrieval**

- [ ] Implement recency-weighted ranking in `search_notes`
- [ ] Update retrieval responses to cite source notes
- [ ] Add `entity:` filter to `search_notes` / `list_notes`

**Categories & instances**

- [ ] Add `~/Notes/.categories.yaml` as source of truth; server reads on startup + SIGHUP
- [ ] Chat command to create category (updates `.categories.yaml`, creates folder)
- [ ] Claude-proposes-new-category flow during `process_inbox`: cluster-detection on misfits, propose at end of processing, require user confirmation before commit
- [ ] `[unmatched]` flag on declined-cluster inbox entries; threshold reset logic
- [ ] Subfolder-grouping proposal when threshold (5 files) hit on related sub-theme
- [ ] One-shot migration tool for renaming categories (rewrites frontmatter)

