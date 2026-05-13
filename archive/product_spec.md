# Notes App — Product Spec
**Status:** v0.2 spec (refined) — v0.1 build complete
**Owner:** Haarthi
**Last Updated:** 2026-05-11

---

## Problem Statement

Personal notes and thoughts are scattered across Evernote, iPhone Notes, text messages, and other tools. There is no unified system, no AI layer to structure raw thoughts, and no way to surface past notes in conversation. Every tool added feels like "yet another place to store things with lack of ability to read"

---

## Goal

A personal knowledge base with an AI layer on top. Capture raw thoughts with zero friction, have Claude structure and file them automatically, and surface relevant notes naturally in conversation — all without leaving Claude.

---

## Users

- **Personal:** Haarthi (personal use) (`~/Notes/`)

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

Create an independent instance with its ownserver, OAuth, `.categories.yaml`, and `_inbox/`.

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

The three file-unit patterns are:

- **Topic-based rolling** — one file per topic (refinancing, backyard), reverse-chron dated H2 appends
- **Time-bucketed** — one file per period (monthly, weekly)
- **Entry-based** — one file per discrete capture, named by date+slug

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
tags: [tag1, tag2]
source: inbox | claude-conversation | direct
---
```

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

Flat by default. Two ways to create a subfolder in v0.2 — both user-initiated, explicit:

**1. Chat command.** *"Group my NotesApp files under `ProductsIdeas/NotesApp/`."* Claude moves the matching files into the subfolder. Frontmatter `category` stays the same (subfolders are within-category organization, not new categories).

**2. Direct file edit.** Move files manually in Finder, Obsidian, or via shell. The server picks up the new path on next read.

Claude-proposes-cluster (auto-suggesting a subfolder when 5+ files share a sub-theme) is deferred — see [P1: AutoCreation of Subfolders](#p1--next).

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
```

### Creation flow

Two ways to add a category in v0.2 — both user-initiated, explicit:

**1. Chat command.** *"Add a new category called `Travel`, topic-based."* Claude updates `.categories.yaml`, creates the folder, confirms.

**2. Direct file edit.** Open `.categories.yaml`, add the entry. Server picks up the change on restart or `SIGHUP`.

Claude-proposes-cluster (auto-suggesting a new category when 3+ misfit entries cluster during `process_inbox`) is deferred — see [P1: AutoCreation of Categories](#p1--next).

---

## What Gets Saved & How

### Save triggers (all user-initiated)

| Source | Trigger | Notes |
|---|---|---|
| iPhone Notes | iCloud sync to Mac → user appends to `raw.md` | P1 iOS Shortcut reduces to one tap |
| `raw.md` direct | Manual paste into `~/Notes/_inbox/raw.md`; entries separated by `---` or two blank lines | |
| Claude chat | User types `@save` in a message | No proactive suggestions, no auto-save. See `@save` semantics below. |

### `@save` semantics

**Trigger:** literal string match on the token `@save` (case-insensitive) anywhere in the user's most recent message. No intent inference, no paraphrase detection — Claude does nothing unless the literal token appears. 

**Scope of save:** Claude reads the whole conversation, identifies the *dominant topical thread*, and writes one structured note about it per the schema. If the conversation spans 2+ distinct topics, Claude asks a one-line clarification before writing — e.g. *"This covers refinancing and backyard work — save as one note or two?"*.

**Snapshot, not end-marker.** `@save` captures content up to and including the message containing the token. Content after is ignored. The conversation continues normally; `@save` has no side effects on the chat state beyond the file write.

**Multiple `@save`s in one conversation.** Each `@save` re-runs the full save decision tree against current content. So `@save` → keep talking about refinancing → `@save` again usually means append a new dated H2 to the same `refinancing.md` (high match). If the topic has shifted, the second save creates a new file. Treat `@save` as a punctuation mark — "this is worth keeping, mark it now" — rather than a session-end signal.


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

If the inferred category is ambiguous (e.g. "what do I think about X" might span Reflection + ProductsIdeas), Claude searches across all categories and includes the best matches regardless of folder. **Capped at top 10 results** by combined `topic_match_strength + recency_boost`. Prevents context-window blowout on broad queries that touch many notes; user can ask for more if 10 isn't enough.

### Passive retrieval (Level 2)

**Deferred.** Will revisit after the explicit flow has been used enough to know what signals actually matter. Avoids over-designing before there's real usage data.

---

## MCP Tools

Seven tools exposed to Claude via the MCP server:

| Tool | What it does |
|---|---|
| `search_notes` | Keyword search across all notes or within a category; recency-weighted ranking |
| `list_notes` | List notes, optionally filtered by category |
| `read_note` | Read full content of a specific note |
| `write_note` | Write a note directly (no inbox processing) |
| `move_note` | Move a note to a different category (and/or rename the file). Updates `category` in frontmatter, bumps `last_updated`, and relocates the file. Powers lazy correction (*"move this note to ProductsIdeas"*) without manual file shuffling. |
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

## Future Roadmap

### P0 — Immediate
- **Persistent server URL:** Replace Cloudflare quick tunnel with a named tunnel (or ngrok static domain). Combine with macOS launchd auto-start so server runs on boot. One-time setup, permanent fix.

### P1 — Next

- **Inbox auto-processing:** Optional cron job to process inbox on a schedule (e.g. nightly) rather than requiring manual trigger.
- **Cowork integration:** Scheduled Cowork tasks for weekly note summaries, action item digests, monthly reviews.
- **AutoCreation of Categories (Claude-proposes flow):** Adds a third path on top of the two user-initiated paths already in v0.2 (chat command, direct file edit). During `process_inbox`, Claude flags entries whose best semantic match against every existing category is below the "no match" threshold — these are *misfits*. When 3+ misfits cluster around a shared theme within a single processing run (or rolling across recent runs), Claude proposes a new category at the end of processing, e.g. *"I noticed 3 inbox entries about coaching conversations — none fit your existing categories. Want me to create a new category `Coaching`?"* User must accept before `.categories.yaml` is updated and the folder is created. Declined clusters get flagged `[unmatched]` in `_inbox/` and the threshold resets — same cluster isn't re-proposed.
- **AutoCreation of Subfolders (Claude-proposes flow):** Adds a third path on top of the two user-initiated paths already in v0.2 (chat command, direct file edit). When a category accumulates 5+ files on a related sub-theme, Claude proposes grouping into a subfolder (e.g. *"You have 6 files about NotesApp under ProductsIdeas — group into `ProductsIdeas/NotesApp/`?"*). User confirms before any files move.


### P2 — Future

- **Scoped passive retrieval (Level 2):** Claude auto-queries notes on personal context signals without explicit ask. Deferred pending Level 1 usage data.
- **Mobile (iPhone) shortcut:** iOS Shortcut that appends typed/dictated text directly to `~/Notes/_inbox/raw.md` via iCloud. Reduces capture friction to one tap. Cloud relay so iPhone can trigger inbox processing even when Mac is asleep.
- **Work notes instance:** Separate `~/Notes/Work/` instance with work-specific categories, different MCP registration.
- **Entity-based file unit:** Add a fourth file-unit pattern — one file per entity (person, client, meeting series), matched by entity name with `entity:` and `entity_type:` frontmatter fields. Enables categories like `1on1s` (entity-based, person-typed) where each person gets a rolling file. When the work-notes instance also lands, pair this with a registry at `~/.notes-registry/entities.yaml` to route entities to the right instance and resolve the lifecycle question (e.g. when someone moves from client → personal friend) via manual edit or chat command.
- **Save-flow performance tuning:** The save-time decision tree (infer category → list files → read frontmatter + first H2 of each → score semantic similarity) is fine at 5 notes per category and unworkable at 50. Set a latency budget for `@save`, define a max-file fanout, and decide whether scoring is a single batched prompt or N-of-K calls. Revisit once any category crosses ~30 files in practice.
- **Backup strategy (Git):** `~/Notes/` is the single source of truth — local markdown. Add a git-based backup: init the directory as a repo, auto-commit on `process_inbox` and `save_conversation` completion (and/or a periodic launchd job), push to a private remote. Gives version history, off-machine durability, and one-command rollback if categorization or a move ever corrupts a file. Alternatives considered: Time Machine (no off-machine), iCloud Drive (no version history beyond a few days).
- **`@save` flag overrides:** Accept `@save Finance` or `@save #tag` as an explicit override on top of silent inference. Useful when Claude's inferred category is consistently off for a given content type.
- **Reflection weekly review prompt:** Weekly Cowork scheduled task that prompts a Reflection review — surfaces the current month's `Reflection/YYYY-MM.md` for re-reading or augmentation. Extends the P1 Cowork integration item.
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
| One unified instance for personal + work | Work compliance separation requires hard boundary; two-instance split is cheaper than retrofitting access controls later |

---

