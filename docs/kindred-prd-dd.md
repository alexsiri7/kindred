# Kindred — PRD & Design Doc

> Codename: **Kindred**. Single combined PRD + design document. Hand to an implementation agent.

## Summary

Kindred is an AI reflective journaling assistant. Users journal by talking to Claude (or another MCP-capable host) — Claude provides the conversation; Kindred provides the memory, structure, and reflection scaffolding via an MCP server. A read-only web app lets users browse their entries, see their named patterns, and manage their data.

The core insight: Claude.ai already does voice + text conversation well, ships with safety layers, and is something many target users already pay for. Kindred doesn't compete with that — it gives Claude the right tools and prompts to be a good journal companion, and stores what comes out.

## Goals

- A low-friction journaling practice that feels like talking to a friend, not filling out a form
- Validation-first stance: emotional support before cognitive analysis
- Capture journal entries as narrative, and recurring patterns as named structures
- Make past entries retrievable by feeling and theme, not just by date
- Reuse stack and patterns from the existing reli project where they make sense

## Non-goals (v1)

- Building our own chat UI or owning the conversation engine — Claude.ai is the surface
- Mood scores, sentiment dashboards, gamification
- Active crisis intervention — defer to Claude.ai's existing safety layers; Kindred adds nothing on top in v1
- AI-volunteered pattern surveillance ("you've felt this way 5 Sundays in a row") — user-pulled retrieval only at v1
- Multi-tenant, multi-org, or anything resembling a B2B product
- Editing entries from the web app

---

## Architecture

Two Railway services backed by one Supabase project.

```
┌───────────────────┐      ┌──────────────────────┐
│  Claude.ai (host) │─────▶│  Kindred MCP Server  │──┐
└───────────────────┘ MCP  │  (FastAPI, Railway)  │  │
                           └──────────────────────┘  │
                                                     ▼
┌───────────────────┐      ┌──────────────────────┐  │   ┌──────────────────┐
│  Browser          │─────▶│  Kindred Web App     │  │   │   Supabase       │
│  (Google login)   │ HTTPS│  (FastAPI + React,   │──┼──▶│   - Postgres     │
└───────────────────┘      │   Railway)           │  │   │   - Auth (Google)│
                           └──────────────────────┘  │   │   - pgvector     │
                                                     └──▶│   - RLS policies │
                                                         └──────────────────┘
```

### Stack

- **MCP server**: Python 3.12, FastAPI, official MCP Python SDK, Uvicorn
- **Web app frontend**: React 19 + TypeScript + Vite + Tailwind + Zustand (matches reli)
- **Web app backend**: FastAPI, separate Railway service from the MCP server
- **Database**: Supabase Postgres with `pgvector` extension
- **Auth**: Supabase Auth with Google as the OAuth provider (web); MCP OAuth 2.1 flow for Claude.ai
- **Embeddings**: OpenAI `text-embedding-3-small` via Requesty gateway (matches reli)
- **Deployment**: Railway (two services), one Supabase project
- **CI**: GitHub Actions, mirroring reli's `./scripts/gates.sh` discipline (test, lint, typecheck)

### Why two Railway services, not one

The MCP server and the web app have different access patterns, scaling concerns, and security boundaries. The MCP server is invoked by an LLM host with an OAuth bearer token; the web app is a user-facing site with browser sessions. Mixing them invites confusion. Separate services, shared Supabase, shared schema. Monorepo is fine; split deploys.

---

## Auth

### Web app — Supabase Auth + Google

User clicks "Sign in with Google" on the web app. Supabase Auth handles the OAuth dance and issues a Supabase JWT. The frontend stores the session via the Supabase JS client; the backend (where used) validates the JWT against Supabase. Row-Level Security policies on every table use `auth.uid() = user_id`, so users can only see their own data — application code never has to re-implement ownership checks.

**Why Supabase Auth and not reli's hand-rolled OAuth + JWT**: RLS integration. The `auth.uid()` Postgres function only resolves correctly with Supabase-issued JWTs. Using reli's tokens would mean either disabling RLS and checking ownership in app code (a tax paid forever) or bridging two identity systems. From the user's point of view, the experience is identical to "Google login everywhere" — they never see Supabase branding.

### MCP server — MCP OAuth 2.1

The current MCP spec supports OAuth 2.1 between MCP clients and servers. When a user adds the Kindred connector to Claude.ai, Claude.ai initiates an OAuth flow against the MCP server. The MCP server delegates to Supabase: it redirects the user to a `/mcp/oauth/authorize` page, which checks for a Supabase session (logging the user in via Google if needed), then issues an OAuth code + access token bound to that Supabase user.

On every MCP tool call, the server validates the bearer token, resolves the Supabase user, and queries Postgres with that user's identity in scope (so RLS applies).

**Fallback**: if MCP OAuth turns out to be more setup than is worth doing on day one, ship a connector-token flow instead — the web app has a `/connect` page that mints a long-lived token bound to the user's `user_id`, the user pastes it into Claude.ai's connector config, the MCP server validates it on each call. Document this fallback. Plan to migrate to proper OAuth in step 8 of the build order.

---

## Data model

Three primary tables plus an embeddings sidecar. RLS on all four: `user_id = auth.uid()`.

### `entries`

One row per journaling session.

| column | type | notes |
|---|---|---|
| `id` | `uuid` | primary key |
| `user_id` | `uuid` | fk → `auth.users` |
| `date` | `date` | user-local date of the session |
| `summary` | `text` | written by `save_entry`, in user's own language |
| `transcript` | `jsonb` | full conversation, optional, user can disable |
| `mood` | `text` | nullable, freeform — user's own word, not a score |
| `created_at` | `timestamptz` | |
| `updated_at` | `timestamptz` | |

Index on `(user_id, date desc)`.

### `patterns`

A recurring HCB cycle, named by the user.

| column | type | notes |
|---|---|---|
| `id` | `uuid` | pk |
| `user_id` | `uuid` | fk |
| `name` | `text` | user-given, e.g. "Sunday dread", "the letting-people-down spiral" |
| `description` | `text` | nullable, user's own description |
| `typical_thoughts` | `text` | the *typical* shape — what usually shows up |
| `typical_emotions` | `text` | |
| `typical_behaviors` | `text` | |
| `typical_sensations` | `text` | |
| `created_at` | `timestamptz` | |
| `last_seen_at` | `timestamptz` | denormalised; updated on each new occurrence |
| `occurrence_count` | `int` | denormalised; ditto |

Unique index on `(user_id, lower(name))` — case-insensitive uniqueness so "Sunday dread" and "sunday dread" don't collide.

### `pattern_occurrences`

A specific instance of a pattern showing up in a specific entry. Many-to-many: an entry can have multiple occurrences (multiple patterns showed up); a pattern has many occurrences (it recurs).

| column | type | notes |
|---|---|---|
| `id` | `uuid` | pk |
| `user_id` | `uuid` | fk |
| `pattern_id` | `uuid` | fk |
| `entry_id` | `uuid` | fk |
| `date` | `date` | redundant with `entries.date` but cheap to query |
| `thoughts` | `text` | this time's specifics |
| `emotions` | `text` | |
| `behaviors` | `text` | |
| `sensations` | `text` | |
| `intensity` | `int` | nullable, 1–5, only if the user offers it |
| `trigger` | `text` | nullable, what set this off this time |
| `notes` | `text` | nullable |
| `created_at` | `timestamptz` | |

Indexes: `(pattern_id, date desc)`, `(entry_id)`, `(user_id, date desc)`.

### `entry_embeddings`

| column | type | notes |
|---|---|---|
| `entry_id` | `uuid` | pk, fk → `entries` |
| `embedding` | `vector(1536)` | from `text-embedding-3-small` |
| `content` | `text` | the text that was embedded (the summary) |

`ivfflat` index on `embedding` for cosine similarity.

### Why these three tables and not more

Separating Entries (narrative), Patterns (recurring shapes), and Occurrences (this-time specifics) is what makes the queries that matter cheap: "show me every time the X pattern came up", "which pattern is most active lately", "has the body sensation changed over time". Collapsing into a single "journal entry" table makes those queries either impossible or expensive.

We deliberately do **not** model Emotions, Triggers, or Behaviors as their own tables. They're text fields. Premature normalisation here would mean asking the user to tag from a fixed vocabulary, which kills the self-compassion vibe. If later we want emotion-keyed retrieval at scale, we can promote.

---

## MCP surface

### Tools

```
save_entry(date: date, summary: text, mood: text?, transcript: jsonb?) -> entry_id
get_entry(date: date | id: uuid) -> entry
list_recent_entries(limit: int = 10) -> [entry_summary]
search_entries(query: text, limit: int = 5) -> [entry_match]   # semantic, via pgvector

list_patterns(active_since: date?) -> [pattern]
get_pattern(name_or_id: text) -> pattern
log_occurrence(
  pattern_name: text,        # creates pattern if it doesn't exist
  entry_id: uuid,
  thoughts: text,
  emotions: text,
  behaviors: text,
  sensations: text,
  intensity: int?,
  trigger: text?,
  notes: text?
) -> occurrence_id
list_occurrences(pattern_name_or_id: text, since: date?) -> [occurrence]
```

`log_occurrence` is the smart one: if `pattern_name` doesn't match an existing pattern (case-insensitive), it creates a new pattern using the occurrence's quadrants as the initial "typical" shape. This means the user can say "let's log this as the Sunday dread one" and it works whether or not Sunday dread exists yet.

`save_entry` also computes and stores the embedding for the summary as a side effect.

### Prompts (user-invoked slash commands)

These set the session's stance and walk specific protocols. **The actual prompt text is the product design** — treat the versions below as v0, expect heavy iteration based on real usage. Keep them in `prompts/` in the repo, version them, and revise after each real session.

#### `/kindred-start`

```
You are Kindred, a reflective journaling companion.

Your stance, in this order:
1. Be with the user. Acknowledge how they are arriving today before anything else.
2. Listen. Use open-ended questions. Avoid advice.
3. Validate. Negative emotions don't need fixing — they need to be heard.
4. Do not introduce frameworks, exercises, or analysis unless the user
   asks for them or invokes /kindred-hcb.
5. Avoid toxic positivity. Don't reframe pain as opportunity. Don't end on a
   silver lining unless the user gets there themselves.

Begin with a single, gentle, open question — something like "How are you
arriving today?" or "What's here for you right now?" Choose what feels right;
don't repeat the same opener every time.

When the user is ready to close, suggest /kindred-close. Don't push it.
If the user wants to examine something more structurally, they can invoke
/kindred-hcb. Don't push that either.

Use search_entries and list_recent_entries only when the user asks about past
entries. Do not surface past entries unprompted.
```

#### `/kindred-hcb`

```
The user wants to examine a thought or pattern using the Hot Cross Bun
framework. The four quadrants:
- Thoughts (what was I telling myself?)
- Emotions (how did I feel?)
- Behaviors (what did I do?)
- Physical sensations (what did I feel in my body?)

Walk them gently, in whatever order feels natural to the conversation.
Don't make it feel like a form.

When you have a sense of the four quadrants:
1. Call list_patterns() to see if the user has named a pattern this might
   belong to.
2. Ask the user: "Does this feel like [closest existing pattern], or
   something new?"
3. If existing: call log_occurrence with the existing pattern name.
4. If new: ask the user to name it in their own words. Do not suggest
   clinical labels. Then call log_occurrence with the new name.

The user owns the vocabulary. Your job is to ask, not to classify.

When done, return to the conversation. The user may want to keep talking
or invoke /kindred-close.
```

#### `/kindred-close`

```
The session is ending. Your tasks:
1. Offer a brief, warm summary of what you heard. One paragraph. In the
   user's language, not clinical.
2. Ask the user if there's anything they want to add or change before saving.
3. Call save_entry with:
   - date: today (user's local date)
   - summary: your one-paragraph summary
   - mood: a single word the user chose, or null if they didn't
   - transcript: the full conversation as a list of {role, content} objects
4. Acknowledge that the entry is saved. Close gently. Do not moralise,
   advise, or assign homework.
```

---

## Web app surface

Read-only. Browser-only. The web app exists to give the user a window onto their data — not a second editor.

| route | purpose |
|---|---|
| `/login` | Google login button (Supabase Auth) |
| `/` | Recent entries (date + first line of summary), search bar |
| `/entries/:id` | Full entry: summary, mood, occurrences linked to it, expandable transcript |
| `/patterns` | List of named patterns, sorted by `last_seen_at` |
| `/patterns/:id` | Pattern details, all occurrences chronologically, the four "typical" quadrants |
| `/search?q=...` | Semantic search results across entries |
| `/settings` | Timezone, transcript on/off, export all data, delete account |
| `/connect` | "Connect to Claude.ai" page — mints connector token (fallback) or initiates MCP OAuth |

**No editing. No write paths.** The only mutations the web app exposes: account deletion, data export, settings toggles. Entries and patterns are written exclusively through the MCP server, which means exclusively through the journaling conversation. One write path.

---

## Design principles

Non-negotiable in v1; the implementation should not regress on any of these.

1. **Validation before analysis.** Default stance is being-with, not problem-solving. Frameworks (HCB) are explicitly user-invoked, never AI-driven.
2. **The user owns the vocabulary.** Patterns are named by the user, in their words. The AI suggests, never imposes.
3. **No surveillance.** AI does not volunteer past patterns or entries unprompted in v1. Retrieval is user-pulled.
4. **One write path.** Entries are created through the journaling conversation only. The web app reads.
5. **Boring privacy claims, kept honest.** We say "encrypted at rest, no training, you can delete everything." We do **not** say "end-to-end encrypted" — the LLM has to see the content to respond.
6. **Defer crisis handling.** Claude.ai already has safety layers for self-harm content. Kindred adds nothing on top in v1; this is a noted, deliberate gap to revisit with real usage data.

---

## Privacy & data handling

- All user data scoped by RLS to `auth.uid()`. Cross-user reads are physically impossible from app code, even if a query forgets a `WHERE` clause.
- Supabase Postgres encryption at rest is on by default.
- No use of user data for training. We don't train models, but we explicitly select embedding/LLM providers with no-training policies. Verify per provider in `.env.example`.
- `/settings` exposes data export (full JSON dump of entries + patterns + occurrences) and account deletion (hard delete cascading across all tables).
- Transcripts are optional per user (toggle in settings). Default: on, because they're useful for retrieval; user can flip to summary-only.

---

## Build order

Each step is a usable, deployable increment. Don't skip ahead.

1. **Supabase setup**: project, schema migrations, RLS policies on all tables, `pgvector` enabled, Google provider configured.
2. **Web app skeleton**: Login → empty entries list. Validates auth end-to-end before any MCP work.
3. **MCP server v0**: `save_entry`, `get_entry`, `list_recent_entries`. Connector-token auth (the fallback) — get it working in Claude.ai with a hardcoded user_id first, then the token.
4. **Prompts v0**: ship `/kindred-start` and `/kindred-close`. Run a real journaling session. Notice what's awkward. Iterate the prompt text — this is where the real product work happens.
5. **Patterns**: schema usage, `list_patterns`, `log_occurrence`, `/kindred-hcb` prompt. Run a session that examines a pattern.
6. **Web app reads**: entry detail, pattern list, pattern detail.
7. **Embeddings + search**: `search_entries`, `/search` route. Needs ~5+ real entries to be meaningful — don't build before then.
8. **MCP OAuth**: replace the connector-token fallback with proper OAuth.
9. **Settings**: export, delete, transcript toggle.

---

## Open questions (deliberately deferred)

These are open by design. Make a defensible choice when you hit them, and revisit once there's real usage data.

- **Same-day re-entry.** Append to today's entry, or allow multiple entries per day? Default: append.
- **Timezone edges.** 2am entries, travel days. Use user-local date and ignore the edges.
- **Pattern detection from data.** AI noticing recurring shapes the user hasn't named yet. Out of scope for v1; will need careful design to avoid surveillance feel.
- **Weekly / monthly retrospective reports.** Mentioned in original PRD; out of scope for v1. Easy to add once entries and patterns are flowing.
- **Voice transcripts.** Claude.ai handles voice; the transcript that lands in `save_entry` is text. Whether to mark transcripts as voice-originated is unspecified — probably doesn't matter at v1.
- **Mood as freeform vs. categorical.** Currently freeform text. May want categorisation later for retrospectives — defer.
- **Multi-user sharing.** Out of scope. Don't design for it; don't preclude it.
- **Crisis protocol.** Out of scope for v1. Revisit once we know what real usage looks like.
