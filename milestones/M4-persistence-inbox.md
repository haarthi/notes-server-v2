# M4 — Persistence + Inbox

**Status:** Not started
**Estimated effort:** ~1.5 focused days
**Depends on:** M1 (I3 quick tunnel), M3 (S1 + S2 — X1 reuses both)
**Unlocks:** Stable URL across reboots; inbox flow for bulk capture
**Source spec:** [../product_spec.md → Infrastructure](../product_spec.md#infrastructure), [../product_spec.md → Inbox archival](../product_spec.md#inbox-archival-non-destructive)

End state: server + tunnel come up automatically on Mac boot under a stable URL; `process_inbox` routes every entry in `raw.md` through the save pipeline with non-destructive archival.

---

## Build order within M4

1. **I4 named tunnel + launchd** — half a day. Do this once everything works on the quick tunnel and the URL drift starts annoying you — that's the right forcing function.
2. **X1 `process_inbox` + archival** — one day. Reuses S2's structuring + decision tree against `raw.md` entries.

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

**Dependencies.** I3 (from M1).

**Out of scope.** Hosting the server on a remote machine (defeats the local-files architecture). Reverse-proxying multiple instances (the work-notes instance, P2, will need its own tunnel/host).

> **Gotcha:** under launchd, anonymous stdout goes to `/dev/null` unless redirected. Set `StandardOutPath` and `StandardErrorPath` in both plists. See [../architecture.md → Cross-cutting gotchas](../architecture.md#cross-cutting-gotchas).

---

## X1 — `process_inbox` + Inbox Archival

**Goal.** Process every entry in `raw.md` through the save pipeline, archive the original non-destructively, and clear `raw.md` once all entries succeed.

**Scope.**
- `process_inbox` MCP tool.
- Parse `~/Notes/_inbox/raw.md` into entries split on `---` or two blank lines.
- For each entry:
  1. Structure the content into the schema (same generator as `@save` — see M3's open question on shared module).
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

**Dependencies.** S1, S2 (both M3).

**Out of scope.** Scheduled/cron processing (P1 in PRD roadmap). Auto-creation of categories from misfit clusters (P1).

---

## M4 exit checklist

- [ ] Server + tunnel survive a Mac reboot under the same URL
- [ ] launchd restarts the server within seconds of a kill
- [ ] `process_inbox` against a 3-entry fixture leaves `raw.md` empty and produces 3 routed notes + 3 archive entries
- [ ] Per-entry atomicity verified: injected failure on entry #2 doesn't block #1 and #3
- [ ] Same `raw.md` processed twice → second run is a no-op
