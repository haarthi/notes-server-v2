# I3 — Quick tunnel runbook

How to expose the local notes-mcp server to claude.ai over HTTPS for the first time. This is the M1 / I3 path — *quick* tunnel, URL changes on restart. The persistent URL (named tunnel + launchd) is **M4 / I4**.

## Prereqs

- `cloudflared` installed (`brew install cloudflared`)
- notes-mcp running locally and responding to `GET /health` on `localhost:8765`

## Steps

1. **Start the server.**
   ```bash
   cd notes-mcp
   uv run notes-mcp
   ```
   Confirm: `curl http://localhost:8765/health` returns 200.

2. **Start the quick tunnel.**
   ```bash
   cloudflared tunnel --url http://localhost:8765
   ```
   Watch the output. A line like this will print:
   ```
   Your quick Tunnel has been created! Visit it at:
   https://random-words-1234.trycloudflare.com
   ```
   Copy that URL.

3. **Smoke-test the tunnel.**
   From any device (phone hotspot is a good off-machine test):
   ```bash
   curl https://random-words-1234.trycloudflare.com/health
   ```
   Should return the same payload as the local `/health`.

4. **Add the connector in claude.ai.**
   - Open claude.ai → Settings → Connectors → Add custom connector.
   - Paste `https://random-words-1234.trycloudflare.com` as the server URL.
   - Claude will discover OAuth via `/.well-known/oauth-authorization-server`, register a client at `/register`, redirect through `/authorize`, exchange the code at `/token`, and store the bearer.
   - Confirm the seven tools appear in the connector's tool list (`write_note`, `list_notes`, `read_note`, `search_notes`, `move_note`, `process_inbox`, `save_conversation`).

5. **Exercise `write_note`** from a Claude chat — that's the only tool fully wired in M1. Example prompt:
   > "Use the notes-mcp connector to write a note in ProductsIdeas about the notes app idea. Content: 'Testing M1 end-to-end.'"

   Verify the file lands at `${NOTES_HOME}/ProductsIdeas/notes-app.md` (or wherever your `NOTES_HOME` points).

## Known weaknesses (fixed in M4 / I4)

- **URL changes on every `cloudflared` restart.** You'll have to re-paste it into claude.ai each time. M4 swaps in a named tunnel on a stable hostname.
- **No auto-start.** Both the server and the tunnel die when the terminal closes. M4 adds launchd plists with `KeepAlive=true` + `RunAtLoad=true`.

## Recovery

If the tunnel restarts and you get a new URL:
1. Copy the new URL from the cloudflared output.
2. In claude.ai → Settings → Connectors → notes-mcp → edit the URL.
3. Re-authorize (claude.ai prompts the OAuth flow against the new origin).

If the server itself died, restart it (`uv run notes-mcp`) before re-pointing claude.ai.
