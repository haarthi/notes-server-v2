# Notes App — Product Spec
**Status:** v0.2 spec (refined) — v0.1 build complete
**Owner:** Adit
**Last Updated:** 2026-05-11

---

## Problem Statement

Personal notes and thoughts are scattered across Evernote, iPhone Notes, text messages, and other tools. There is no unified system, no AI layer to structure raw thoughts, and no way to surface past notes in conversation. Every tool added feels like "yet another place to store things with lack of ability to read"

---

## Goal

A personal knowledge base with an AI layer on top. Capture raw thoughts with zero friction, have Claude structure and file them automatically, and surface relevant notes naturally in conversation — all without leaving Claude.

---

## Users

- **Primary:** Haarthi (personal use)
- **Work:** Work Notes — separate instance (`~/Work-Notes/`), separate MCP server, separate OAuth, separate `.categories.yaml`. Both instances run concurrently; content is routed to one or the other based on entity/context.

---

## Topic Categories

Personal instance (`~/Notes/`) seed categories. Categories are extensible — see [Adding New Categories](#adding-new-categories).

| Category | Description |
|---|---|
| `Finance` | taxes, investing, refinancing, financial planning |
| `HomeImprovement` | Gardening, home fixes, contractor notes |
| `Reflection` | Journalling, capturing long-term goals |
| `ProductsIdeas` | Products, ideas, professional improvement |
| `ProfessionalDev` | AI tools, training, skills, workflows, articles, links |

---

## Architecture

### System Overview

```
Capture Sources
  iPhone Notes (iCloud) │ raw.md (manual) │ Claude conversations (@save)
                        ↓
              ~/Notes/_inbox/raw.md
                        ↓
              Notes MCP Server (local, port 8765)
              FastAPI + MCP layer + OAuth 2.0
                        ↓
              Cloudflare Tunnel (HTTPS exposure)
                        ↓
              claude.ai (chat interface, desktop + mobile)
                        ↓
              ~/Notes/{Category}/*.md (source of truth)
                        ↓
              Obsidian (human reading interface)
```

### Folder Structure

Two independent instances. Each has its own server, OAuth, `.categories.yaml`, and `_inbox/`.

```
~/Notes/                         ← personal instance
  .categories.yaml               ← source of truth for categories in this instance
  _inbox/
    raw.md                       ← raw capture lands here
    processed/
      2026-05.md                 ← monthly archive of processed entries
  Finance/
  HomeImprovement/
  Reflection/
  ProductsIdeas/
  ProfessionalDev/
  1on1s/                         ← example user-added category (entity-based)
    sarah-chen.md
    alex-mentor.md

~/Work-Notes/                    ← work instance (Work)
  .categories.yaml
  _inbox/
  1on1s/                         ← same category name, different entities
    manager.md
    direct-report-1.md
  Clients/
    acme-corp.md
  Meetings/
    weekly-platform-sync.md

~/.notes-registry/
  entities.yaml                  ← cross-instance entity → instance mapping
```

---

## Notes Schema (v0.2)

### Per-category file unit

Different categories have different default file granularity. Claude uses the category's default at save time unless it finds a strong semantic match against an existing file.

| Category | Default unit | Examples |
|---|---|---|
| `Finance` | Topic-based rolling file | `refinancing.md`, `taxes-2026.md`, `investing-thesis.md` |
| `HomeImprovement` | Topic-based rolling file | `backyard.md`, `kitchen-reno.md`, `contractor-jensen.md` |
| `Reflection` | Monthly time-bucket | `2026-05.md`, `2026-06.md` |
| `ProductsIdeas` | Topic-based, one file per idea/product | `notes-app.md`, `running-coach-app.md` |
| `ProfessionalDev` | Mixed — entry-based for articles/links, topic-based for skill threads | `2026-05-11-rag-eval-article.md`, `mcp-deep-dive.md` |
| `1on1s` *(example, user-added)* | Entity-based rolling file (per person) | `sarah-chen.md`, `alex-mentor.md` |
| `Clients` *(example, user-added)* | Entity-based rolling file (per client/account) | `acme-corp.md`, `globex.md` |
| `Meetings` *(example, user-added)* | Entity-based rolling file (per meeting series); entry-based for one-offs | `weekly-platform-sync.md`, `2026-05-11-acme-discovery.md` |

The four file-unit patterns are:

- **Topic-based rolling** — one file per topic (refinancing, backyard), reverse-chron dated H2 appends
- **Time-bucketed** — one file per period (monthly, weekly)
- **Entry-based** — one file per discrete capture, named by date+slug
- **Entity-based rolling** — one file per entity (person, client, meeting series). Same body shape as topic-based, but matched by entity name. Adds `entity:` and `entity_type:` to frontmatter.

### Naming conventions

- Topic files: `lowercase-kebab-case.md` (e.g. `refinancing.md`, `backyard-redesign.md`)
- Entry files: `YYYY-MM-DD-slug.md` (e.g. `2026-05-11-rag-eval-article.md`)
- Time-bucket files: `YYYY-MM.md` (e.g. `2026-05.md`)

### Frontmatter

Every note carries YAML frontmatter that stays stable across appends:

```markdown
---
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
category: Finance
topic: refinancing                # set on topic-based files; null otherwise
entity: null                      # set on entity-based files (e.g. "Sarah Chen", "Acme Corp")
entity_type: null                 # person | client | meeting-series — set when entity is set
tags: [tag1, tag2]
source: inbox | claude-conversation | direct
---
```

Either `topic` or `entity` is set, depending on the file unit. Time-bucketed and entry-based files leave both null.

### Body format

**Rolling files (topic-based and time-bucketed):** reverse-chronological, dated H2 sections — newest at top.

```markdown
---
created: 2026-03-02
last_updated: 2026-05-11
category: Finance
topic: refinancing
tags: [rates, jumbo, primary-residence]
source: claude-conversation
---

# Refinancing

## 2026-05-11
Spoke with broker — current 30yr at 6.125%. Below 5.75% is the trigger to act.

### Key Points
- Broker recommends locking when 10yr Treasury drops 25bps further
- Closing costs estimated $4.2k

### Actions
- [ ] Pull updated quote in 2 weeks

## 2026-04-18
Pulled latest statement. Current rate 7.0%, balance $XXX.
...
```

**Entry-based files (one capture per file):** flat structure under a single H1.

```markdown
---
created: 2026-05-11
last_updated: 2026-05-11
category: ProfessionalDev
tags: [rag, evals, llm]
source: inbox
---

# RAG Eval Article — key takeaways

Summary paragraph.

## Key Points
- ...

## Actions
- [ ] action item
```

### Subfolder creation

Flat by default. When a category accumulates 5+ files on a related sub-theme, Claude proposes grouping into a subfolder (e.g. *"You have 6 files about NotesApp under ProductsIdeas — group into `ProductsIdeas/NotesApp/`?"*). User confirms.

---

## Adding New Categories

### Source of truth

Each instance has a `.categories.yaml` at its root that defines every category the server knows about, its file-unit pattern, and any required frontmatter. The server reads this on startup and on `SIGHUP`.

```yaml
# ~/Notes/.categories.yaml (personal instance)
instance: personal
categories:
  Finance:           { file_unit: topic-based }
  HomeImprovement:   { file_unit: topic-based }
  Reflection:        { file_unit: monthly-bucket }
  ProductsIdeas:     { file_unit: topic-based }
  ProfessionalDev:
    file_unit: mixed
    rules:
      articles: entry-based
      threads:  topic-based
  1on1s:
    file_unit: entity-based
    entity_types: [person]
```

```yaml
# ~/Work-Notes/.categories.yaml (work instance)
instance: work
categories:
  1on1s:    { file_unit: entity-based, entity_types: [person] }
  Clients:  { file_unit: entity-based, entity_types: [client] }
  Meetings: { file_unit: entity-based, entity_types: [meeting-series] }
  Projects: { file_unit: topic-based }
```

### Creation flow

Three ways to add a category — two user-initiated, one Claude-initiated. **Every path requires explicit user acceptance before the category is created.**

**1. Chat command (user-initiated, explicit).**
*"Add a new category called `1on1s` in personal, entity-based, person-typed."* Claude updates `.categories.yaml`, creates the folder, confirms.

**2. Direct file edit (user-initiated, explicit).**
Open `.categories.yaml`, add the entry. Server picks up the change on restart or reload.

**3. Claude proposes (auto-detected, requires user confirmation).**
During `process_inbox`, Claude flags entries whose best semantic match against every existing category is below the "no match" threshold — these are *misfits*. When 3+ misfits cluster around a shared theme within a single processing run (or rolling across recent runs), Claude proposes a new category at the end of processing:

> *"I noticed 3 inbox entries about coaching conversations — career chats with mentors, an advisory call, notes from a leadership coaching session. None fit your existing categories. Want me to create a new category `Coaching`, entity-based, person-typed, in the personal instance?"*

The user must accept (`yes`, or a corrected proposal like *"yes, but call it `1on1s` and keep it flat for now"*) before:

- `.categories.yaml` is updated
- The folder is created
- The flagged misfit entries are filed into it

If the user declines, the flagged entries stay in `_inbox/` marked `[unmatched]` and the cluster threshold resets. Claude won't re-propose the same cluster — the entries need to be manually filed or the user can revisit later.

**Proposal heuristic (initial parameters; tune during v0.2 build):**
- Misfit = below-threshold match against all existing categories' file names + topic/entity fields
- Cluster = 3+ misfits with high pairwise semantic similarity to each other
- Suggested file-unit = inferred from cluster shape (per-person → entity-based, per-event → entry-based, etc.)
- Suggested instance = inferred from entity registry membership of mentioned names

### Cross-instance entity routing

When a save mentions an entity (person, client, meeting series) for the first time, Claude consults the entity registry at `~/.notes-registry/entities.yaml`. If the entity is unknown, Claude asks once in chat:

> *"Is `Sarah Chen` a work or personal contact?"*

The answer is recorded in the registry and used for all future saves involving that entity — no re-asking. The note is then written to the correct instance.

```yaml
# ~/.notes-registry/entities.yaml
entities:
  - name: Sarah Chen
    type: person
    instance: work
    category: 1on1s
  - name: Alex Mentor
    type: person
    instance: personal
    category: 1on1s
  - name: Acme Corp
    type: client
    instance: work
    category: Clients
```

### Removing or renaming categories

- **Rename:** edit `.categories.yaml`, rename the folder. The category name in existing note frontmatter is *not* auto-rewritten — a one-shot migration tool handles bulk frontmatter updates.
- **Remove:** edit `.categories.yaml` to remove the entry. Files stay on disk but become read-only via the MCP server until reassigned. Prevents accidental data loss.

---

## What Gets Saved & How

### Save triggers (all user-initiated)

| Source | Trigger | Notes |
|---|---|---|
| iPhone Notes | iCloud sync to Mac → user appends to `raw.md` | P1 iOS Shortcut reduces to one tap |
| `raw.md` direct | Manual paste into `~/Notes/_inbox/raw.md`; entries separated by `---` or two blank lines | |
| Claude chat | User types `@save` at end of conversation | No proactive suggestions, no auto-save |

### Save contents

- **`@save` from chat:** Claude generates a structured note in the schema format — title, 1–2 paragraph summary, key points, action items, any links/references mentioned. No raw transcript appended.
- **`process_inbox`:** each entry in `raw.md` gets the same structured treatment.
- **`write_note`:** pre-formatted content goes straight to disk.

### Categorization & tags (silent inference)

Claude infers category and 2–5 tags with no save-time confirmation. The category determines the file unit per the hybrid map above. Errors get corrected lazily — user says *"move this note to ProductsIdeas"* or *"retag with #jumbo"* when noticed.

### Save-time decision tree (append vs. new file)

For every incoming note:

1. Infer the category from content.
2. List existing files in that category; read frontmatter + first H2 of each.
3. Score semantic similarity between the new note and each existing file.
4. Branch on confidence:
   - **High match** → append to that file under a new dated H2 at the top; no confirmation.
   - **Medium / ambiguous** → reply in chat: *"This looks related to `refinancing.md` — append there, or create new?"* One-line confirmation.
   - **No match** → create a new file using the category's default unit.

### Inbox archival (non-destructive)

After `process_inbox` completes, each processed entry is appended to `~/Notes/_inbox/processed/YYYY-MM.md` with a pointer to the destination:

```markdown
## 2026-05-11 14:32
[Filed to: Finance/refinancing.md]

Original raw text here, verbatim.
```

`raw.md` is then cleared. Full audit trail preserved for recovery if categorization was wrong.

### Idempotency & error handling

`@save` and `process_inbox` are per-entry atomic. Failed entries stay in `raw.md` (or in chat for `@save`); succeeded entries move to archive. Re-running `@save` checks for a same-day note with the same inferred title and skips duplicates.

---

## What Gets Retrieved & How

### Explicit retrieval (Level 1 — current scope)

User asks Claude directly, e.g.:
- "What have I noted about refinancing?"
- "Show me my home improvement backlog"
- "Pull up my reflection notes from last month"

### Response shape

Claude reads the matching notes and **synthesizes a direct prose answer to the question**, ending with a `Sources:` line citing the notes used:

> *"You're tracking a refi trigger at 5.75% on the 30yr. As of 5/11 the broker quoted 6.125%, and you're planning to pull a fresh quote in two weeks. Closing costs estimated at $4.2k.*
>
> *Sources: `Finance/refinancing.md`"*

### Ranking — recency-weighted relevance

When multiple notes match a query, ranking is `topic_match_strength + recency_boost`. Newer notes win ties. This fits the living-doc model: the latest entry on a rolling topic file is usually the one that matters.

### Cross-category queries

If the inferred category is ambiguous (e.g. "what do I think about X" might span Reflection + ProductsIdeas), Claude searches across all categories and includes the best matches regardless of folder.

### Passive retrieval (Level 2)

**Deferred.** Will revisit after the explicit flow has been used enough to know what signals actually matter. Avoids over-designing before there's real usage data.

---

## MCP Tools

Six tools exposed to Claude via the MCP server:

| Tool | What it does |
|---|---|
| `search_notes` | Keyword search across all notes or within a category; recency-weighted ranking |
| `list_notes` | List notes, optionally filtered by category |
| `read_note` | Read full content of a specific note |
| `write_note` | Write a note directly (no inbox processing) |
| `process_inbox` | Process `raw.md` — structure, categorize, append-or-create per save-time decision tree, archive to `_inbox/processed/YYYY-MM.md`, clear `raw.md` |
| `save_conversation` | Summarize current Claude conversation and save as note following the schema |

---

## Key UX Decisions

- **Interface:** Claude chat window (desktop + mobile). No separate app.
- **Viewer:** Obsidian, pointed at `~/Notes/`. Read-only interface over the same files.
- **Mobile:** Capture-only for now (iPhone Notes → inbox). Processing requires Mac to be awake.
- **Trigger model:** On-demand ("process my inbox", `@save`). Not fully automatic.
- **Note format:** Markdown. Plain files, no vendor lock-in, readable forever.
- **Metadata:** Silently inferred by Claude at save time; corrected lazily by the user.

---

## Infrastructure

| Component | Choice | Rationale |
|---|---|---|
| Storage | Local `~/Notes/` markdown files | Full ownership, no vendor lock-in, Obsidian-compatible |
| Server | FastAPI + FastMCP (Python) | Lightweight, familiar, MCP-compatible |
| Tunnel | Cloudflare Quick Tunnel | Free, zero config, exposes local server to claude.ai |
| Auth | OAuth 2.0 + PKCE (trust-all stubs) | Required by claude.ai for remote MCP connections |
| AI processing | Anthropic API (claude-sonnet-4) | Structures notes, infers categories, summarizes conversations |

---

## Current State (v0.1 build)

### Working
- [x] Notes MCP server running locally on port 8765
- [x] Cloudflare tunnel exposing server to claude.ai
- [x] OAuth 2.0 + PKCE handshake with claude.ai
- [x] All 5 category folders created at `~/Notes/`
- [x] `search_notes`, `list_notes`, `read_note`, `write_note` tools working
- [x] `process_inbox` tool working (destructive clear — pre-v0.2)
- [x] `save_conversation` (@save) working
- [x] Obsidian pointed at `~/Notes/`

### Known Issues
- [ ] Cloudflare quick tunnel URL rotates on every server restart — requires re-adding URL to claude.ai settings each session

---

## v0.2 Build Items (from this spec refinement)

**Schema & save:**
- [ ] Implement per-category file-unit defaults (hybrid map)
- [ ] Implement entity-based file-unit pattern (`entity` + `entity_type` frontmatter, entity-name matching)
- [ ] Implement semantic-match append decision tree in `process_inbox` and `save_conversation`
- [ ] Implement medium-confidence confirmation prompt
- [ ] Implement reverse-chronological dated H2 append format
- [ ] Implement inbox archival to `_inbox/processed/YYYY-MM.md` (replace destructive clear)
- [ ] Add `last_updated` frontmatter field; update on every append

**Retrieval:**
- [ ] Implement recency-weighted ranking in `search_notes`
- [ ] Update retrieval responses to cite source notes
- [ ] Add `entity:` filter to `search_notes` / `list_notes`

**Categories & instances:**
- [ ] Add `~/Notes/.categories.yaml` as source of truth; server reads on startup + SIGHUP
- [ ] Chat command to create category (updates `.categories.yaml`, creates folder)
- [ ] Claude-proposes-new-category flow during `process_inbox`: cluster-detection on misfits, propose at end of processing, require user confirmation before commit
- [ ] `[unmatched]` flag on declined-cluster inbox entries; threshold reset logic
- [ ] Subfolder-grouping proposal when threshold (5 files) hit on related sub-theme
- [ ] Stand up second instance: `~/Work-Notes/` with its own server, OAuth, `.categories.yaml`
- [ ] Build `~/.notes-registry/entities.yaml` and one-time entity-to-instance prompt flow
- [ ] One-shot migration tool for renaming categories (rewrites frontmatter)

---

## Enhancements Backlog

### P0 — Immediate
- **Persistent server URL:** Replace Cloudflare quick tunnel with a named tunnel (or ngrok static domain). Combine with macOS launchd auto-start so server runs on boot. One-time setup, permanent fix.

### P1 — Next
- **iPhone shortcut:** iOS Shortcut that appends typed/dictated text directly to `~/Notes/_inbox/raw.md` via iCloud. Reduces capture friction to one tap.
- **Inbox auto-processing:** Optional cron job to process inbox on a schedule (e.g. nightly) rather than requiring manual trigger.

### P2 — Future
- **Scoped passive retrieval (Level 2):** Claude auto-queries notes on personal context signals without explicit ask. Deferred pending Level 1 usage data.
- **Cowork integration:** Scheduled Cowork tasks for weekly note summaries, action item digests, monthly reviews.
- **Work notes instance:** Separate `~/Notes/Work/` instance with work-specific categories, different MCP registration.
- **Vector search:** Replace keyword search with semantic/embedding search for better retrieval on fuzzy queries.
- **Mobile processing:** Cloud relay so iPhone can trigger inbox processing even when Mac is asleep.

---

## Considered & Rejected

| Option | Why rejected |
|---|---|
| Notion as storage | "Yet another tool" feeling; vendor lock-in; less flexible for AI layer |
| Obsidian + iCloud sync (capture) | Requires habit of opening specific app; breaks down to old defaults |
| Claude Code as agent | Terminal-only; loses chat-window integration and @save; no mobile |
| Fully automatic passive retrieval | Too noisy; over-retrieval on every message; hard to tune |
| OpenClaw | Young project; creator left for OpenAI; adds complexity before workflow is validated |
| Entry-based default for all categories | Fragments living-doc topics (refinancing, backyard) across many small files — solved by hybrid map |
| Always-ask metadata confirmation | Adds save-time friction on every entry; resolved by silent inference + lazy correction |
| Destructive inbox clear | No recovery from miscategorization; replaced by `_inbox/processed/YYYY-MM.md` archive |
| Proactive `@save` suggestions from Claude | Risk of noise and false positives; explicit `@save` only for now |
| Claude auto-creates new categories without confirmation | Risk of taxonomy sprawl from one-off saves; Claude may propose but user must accept before any category is created |
| Treating entity-based content as topic-based | Loses `entity` as a first-class field — no easy way to query "all 1:1s with anyone" or "all clients I talked to this month" |
| One unified instance for personal + work | Work compliance separation requires hard boundary; two-instance split is cheap once entity registry exists |
| Per-save `@save work` / `@save personal` flag | Adds friction on every save; one-time entity-to-instance decision (recorded in registry) is friction-free thereafter |

---

## Open Questions

- Should the `@save` command accept flags like `@save Finance` or `@save #tag` as an explicit override on top of silent inference?
- What's the right review cadence for Reflection notes — weekly Cowork prompt? Tied to Reflection's monthly time-bucket structure.
- Semantic-match confidence thresholds: what's "high" vs "medium" empirically? Tune during v0.2 build.
- For ProfessionalDev mixed mode (entry vs topic-based), is the trigger article-vs-thread keyword detection, or something more reliable?
- **Entity disambiguation:** two contacts with the same first name — how does Claude prompt? (e.g. *"Did you mean Sarah Chen or Sarah Liu?"*)
- **Cross-instance retrieval:** when you ask "what are my open action items from 1:1s this week", does Claude query both instances and merge, or do you specify? Default behavior + override.
- **Entity registry lifecycle:** what happens when an entity changes role (e.g. someone moves from a client to a personal friend)? Manual edit of `entities.yaml`, or a chat command?
- **Meeting one-offs:** when a meeting has no recurring series, does the entry-based `YYYY-MM-DD-slug.md` go in `Meetings/` flat, or in a `Meetings/one-offs/` subfolder?
- **Category-proposal tuning:** what's the right misfit cluster threshold — 3 entries, 5, more? What's the right "below-threshold" match score to flag an entry as misfit? Calibrate empirically during v0.2 build.
- **Repeated declines:** if you decline the same proposed category twice, should Claude permanently suppress that cluster, or keep re-asking when the cluster grows further?
