# Kindred — Per-client setup

Kindred is provider-agnostic: any MCP-capable AI assistant can be the
conversation surface. The flow is the same for every client:

1. Mint a connector token at `/app/connect`.
2. Add the Kindred MCP server (`https://kindred-mcp.interstellarai.net/mcp`)
   to your AI assistant, with the token as the bearer.
3. Paste the one-liner custom instruction so the assistant reads
   `kindred://guide` on connect:

   > When connected to Kindred, read the kindred://guide resource before doing anything else.

4. Say "Hi, I'd like to journal" — expect a gentle open question.

The rest of this page covers the three clients that work today. The shape is
identical across them; differences are only in where the MCP server and
custom instruction get pasted.

---

## Token lifecycle

Connector tokens expire 90 days after they're minted. An expired or revoked
token returns 401 — same response as an unknown one — so the AI client just
stops working until you reissue.

Manage your tokens at `/app/settings` → **Connector tokens**:

- **Active** tokens show created date, last-used time, and expiry.
- **Revoke** disables a token immediately (next MCP request → 401).
- **Revoke and reissue** does both in one step and shows the new token once
  — copy it into your AI client's connector config before navigating away.

Tip: revoke any token you've pasted into chat, screenshots, or shared docs.
Anyone with the value can read your journal until you do.

---

## Claude Projects

### Add the MCP server

In Claude.ai, open Settings → Connectors → Add custom connector. Paste the
MCP URL above and your connector token from `/app/connect`.

### Paste the one-liner

Create a Project. In its instructions, paste:

> When connected to Kindred, read the kindred://guide resource before doing anything else.

### Test it

Open the project and say "Hi, I'd like to journal." You should get one
gentle open question, no advice. Then say "Let's save this session" and
confirm the assistant calls `save_entry`.

### Troubleshooting

- **Connector greyed out** — re-mint the token at `/app/connect` and paste
  it again.
- **AI ignores the one-liner** — paste the contents of `kindred-guide.md`
  directly into the project instructions instead.
- **Tool calls fail with 401** — the token has expired (default 90-day TTL),
  been revoked from `/app/settings`, or been replaced by a re-mint. Check
  the row at `/app/settings` → **Connector tokens**: if it shows Expired or
  Revoked, use **Revoke and reissue** to mint a replacement and paste the
  new value into your AI client.
- **Tool calls fail with 429 / "rate_limited"** — Kindred caps tool calls
  per user per minute (60 total, 10 for `search_entries`) to keep the
  service affordable. Wait the number of seconds in the `retry_after`
  field and try again. This rarely affects normal journaling; if it keeps
  happening, you may have a runaway loop in the assistant — start a new
  conversation.

---

## ChatGPT

### Add the MCP server

Create a Custom GPT. In Configure → Actions, add the MCP URL above with the
connector token as the bearer credential.

### Paste the one-liner

In the Custom GPT instructions, paste:

> When connected to Kindred, read the kindred://guide resource before doing anything else.

### Test it

In the GPT, say "Hi, I'd like to journal." Expect one open question.
Then say "Let's save this session" and confirm `save_entry` runs.

### Troubleshooting

- **401 unauthorized** — the token has expired (default 90-day TTL), been
  revoked from `/app/settings`, or been replaced by a re-mint. Check the
  row at `/app/settings` → **Connector tokens**: if it shows Expired or
  Revoked, use **Revoke and reissue** to mint a replacement and update the
  GPT's auth.
- **Tool calls fail with 429 / "rate_limited"** — Kindred caps tool calls
  per user per minute (60 total, 10 for `search_entries`) to keep the
  service affordable. Wait the number of seconds in the `retry_after`
  field and try again. This rarely affects normal journaling; if it keeps
  happening, you may have a runaway loop in the assistant — start a new
  conversation.
- **Tool not invoked** — add a stronger instruction, e.g. "Always call
  Kindred tools when the user asks to save or search."
- **One-liner not respected** — some surfaces don't auto-read MCP resources.
  Paste the `kindred-guide.md` contents directly into the instructions.

---

## Gemini Gems

### Add the MCP server

Create a Gem. In its custom instructions / extensions, register the MCP
server above with the bearer token.

### Paste the one-liner

In the Gem instructions, paste:

> When connected to Kindred, read the kindred://guide resource before doing anything else.

### Test it

Open the Gem and say "Hi, I'd like to journal." Confirm the AI asks one
open question. Say "Let's save this session" and confirm the entry is saved.

### Troubleshooting

- **Gem can't see the MCP server** — some Gemini surfaces don't yet support
  arbitrary MCP servers. Use a client that does, or follow the
  `/kindred-start` prompt manually.
- **Tool calls fail with 429 / "rate_limited"** — Kindred caps tool calls
  per user per minute (60 total, 10 for `search_entries`) to keep the
  service affordable. Wait the number of seconds in the `retry_after`
  field and try again. This rarely affects normal journaling; if it keeps
  happening, you may have a runaway loop in the assistant — start a new
  conversation.
- **One-liner ignored** — paste `kindred-guide.md` directly into the Gem
  instructions.

---

## Adding another client

The on-page tabs at `/app/connect` are driven by a `CLIENTS` array in
`web/frontend/src/pages/Connect.tsx`. Adding a fourth client is a one-file
change — append a new entry. Mirror the same section here once it works.
