# M5 — Lifecycle polish

**Status:** Not started
**Estimated effort:** ~2 focused days
**Depends on:** M2 (R1 for post-move retrieval verification), M1 (S1 for `.categories.yaml` reads)
**Unlocks:** v0.2 feature-complete
**Source spec:** [../product_spec.md → Subfolder creation](../product_spec.md#subfolder-creation), [../product_spec.md → Adding New Categories](../product_spec.md#adding-new-categories)

End state: notes can be moved across categories with lazy correction; new categories can be added via chat or direct file edit; clusters of related files can be grouped into subfolders.

---

## Build order within M5

1. **X2 `move_note`** — lazy correction across categories.
2. **X3 Category Lifecycle** — chat command + SIGHUP hot reload.
3. **X4 Subfolder Grouping** — move matching files into a subfolder via chat command. Reuses X2's move semantics.

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

**Dependencies.** R1 (M2) for post-move verification.

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

**Dependencies.** S1 (M1) — everything reads `.categories.yaml`.

**Out of scope.** Auto-proposing categories from misfit clusters (P1 in PRD roadmap).

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

## M5 exit checklist

- [ ] `move_note` correctly relocates files and updates frontmatter
- [ ] Post-move, R1 + R2 find files at the new path
- [ ] Chat command adds a category and `write_note` works against it immediately
- [ ] SIGHUP picks up a direct `.categories.yaml` edit without restart
- [ ] Subfolder grouping moves only matching files and leaves frontmatter `category` untouched
