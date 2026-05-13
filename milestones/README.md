# Notes App v0.2 — Milestone Plan

**Status:** Active — last updated 2026-05-12
**Source of truth:** [../product_spec.md](../product_spec.md) (v0.2)
**Architecture reference:** [../architecture.md](../architecture.md)

This folder breaks the v0.2 build into five releasable milestones. Each milestone is **shippable on its own** — at the end of it, you have a working capability you could rely on without the later milestones. Each milestone file contains its own goal, scope, acceptance criteria, test plan, and any open questions that block it.

---

## How to read this

- **One file per milestone.** Mark things done and archive completed milestones without scrolling past them.
- **Acceptance criteria live with milestones, not the PRD.** The PRD says *"users can save notes from chat"*; this folder says *"`@save` token detection is case-insensitive and triggers within 200ms"*.
- **Work items keep their existing labels** (I1, S1, R1, X1, etc.) inside each milestone file, so cross-references from the PRD's roadmap still resolve.
- **Open questions are inlined** next to the work they block. The "decisions to nail down before build" list from the original milestone doc now lives in M2 (one question) and M3 (four questions).

---

## Milestones

| # | File | Track focus | What it unlocks |
|---|---|---|---|
| M1 | [M1-foundation.md](./M1-foundation.md) | Infra + first Save tool | One tool callable from claude.ai over the internet — capture pre-formatted notes from chat |
| M2 | [M2-read.md](./M2-read.md) | Full Read track | List, search, ask questions, get cited prose answers; cross-category fallback |
| M3 | [M3-smart-save.md](./M3-smart-save.md) | Smart Save | `@save` works end-to-end with append-vs-new decision tree |
| M4 | [M4-persistence-inbox.md](./M4-persistence-inbox.md) | Persistence + inbox | Stable URL across reboots; inbox processing with non-destructive archival |
| M5 | [M5-lifecycle.md](./M5-lifecycle.md) | Lifecycle polish | Move notes, add categories, group into subfolders |

---

## Suggested build order

Within each milestone, the listed order is the recommended path. The grouping below is the order I'd ship them in.

### M1 — Foundation (~4 focused days)

The path that pays back fastest: get a single tool callable from claude.ai over the internet before going deep on anything else. This is where the project goes from "Python code" to "thing I actually use."

1. **I1 skeleton.** One day. Stubs everywhere; deployable surface.
2. **S1 `write_note`.** One day. Get one tool actually working.
3. **I2 OAuth + I3 quick tunnel.** Two days. Now you can call S1 from claude.ai over the internet.

End of M1: you can save a pre-formatted note from chat.

### M2 — Full Read

Save is useless without retrieval. M2 lights up the entire Read track so you can list, search, ask questions, and fall back when category inference is ambiguous. Each step is independently usable — R1 alone gives you enumeration; R2 adds ranked search; R3 adds prose answers with citations; R4 widens scope when needed.

1. **R1 List & Read.** One day. Enumerate notes and read full content.
2. **R2 Search + Recency Ranking.** One–two days. Keyword search with `topic_match + recency_boost`.
3. **R3 Synthesized Q&A.** One day for the plumbing, plus prompt iteration during real use. Prose answers with strict `Sources:` footer.
4. **R4 Cross-category Fallback.** Half a day. Kicks in when the inferred category is ambiguous; top-10 cap across all categories.

End of M2: working save-and-retrieve loop.

### M3 — Smart save

With Read working and S1 proven, add the intelligence layer on the save side.

1. **S2 placement + similarity.** Two days. Build with a fake scorer first to nail the decision tree; swap in the real Claude call last.
2. **S3 `save_conversation` tool + prompt iteration.** One day for the tool, plus a few days of prompt iteration while you actually use it.

End of M3: `@save` works end-to-end.

### M4 — Persistence + inbox

1. **I4 named tunnel + launchd.** Half a day. Do this once everything works on the quick tunnel and the URL drift starts annoying you — that's the right forcing function.
2. **X1 `process_inbox` + archival.** One day. Reuses S2's structuring + decision tree against `raw.md` entries.

### M5 — Lifecycle polish

1. **X2 `move_note`.** Half a day. Lazy correction across categories.
2. **X3 category lifecycle.** One day. Chat command + SIGHUP hot reload.
3. **X4 subfolder grouping.** Half a day.

---

## Work-item dependency map

This is the same content as the original "Milestone summary" table — kept here for quick scanning across all 14 work items without having to open each milestone file.

| # | Name | Track | Goal | Depends on | Lives in |
|---|---|---|---|---|---|
| I1 | Server + MCP layer | Infra | FastAPI + FastMCP process serving the seven MCP tools over loopback | — | M1 |
| I2 | OAuth 2.0 + PKCE | Infra | Trust-all auth stubs satisfying claude.ai's remote-MCP requirements | I1 | M1 |
| I3 | Public tunnel (quick) | Infra | Cloudflare Quick Tunnel exposing the local server to claude.ai over HTTPS | I1, I2 | M1 |
| I4 | Persistent server URL (P0) | Infra | Named tunnel + launchd auto-start for a stable, boot-resilient URL | I3 | M4 |
| S1 | `write_note` | Save | Direct write of a pre-formatted note to the right location with correct frontmatter, naming, and file-unit handling | — | M1 |
| S2 | Smart Placement | Save | Append-vs-new-file decision tree with idempotency | S1 | M3 |
| S3 | `@save` | Save | Detect token, snapshot conversation, structure, route via Smart Placement | S1, S2 | M3 |
| R1 | List & Read | Retrieve | `list_notes` + `read_note` — basic enumeration | — | M2 |
| R2 | Search + Recency Ranking | Retrieve | `search_notes` with `topic_match + recency_boost` ranking | R1 | M2 |
| R3 | Synthesized Q&A | Retrieve | Prose answer + `Sources:` line for natural-language questions | R1, R2 | M2 |
| R4 | Cross-category Fallback | Retrieve | Ambiguous queries search all categories, top-10 cap | R2, R3 | M2 |
| X1 | `process_inbox` + Archival | Misc | Parse `raw.md`, route each entry, archive non-destructively, clear inbox | S1, S2 | M4 |
| X2 | `move_note` | Misc | Lazy correction — move note to different category, rename, update frontmatter | R1 | M5 |
| X3 | Category Lifecycle | Misc | Add categories via chat command and via direct `.categories.yaml` edit (SIGHUP) | S1 | M5 |
| X4 | Subfolder Grouping | Misc | Move matching files into a subfolder via chat command | X2 | M5 |
