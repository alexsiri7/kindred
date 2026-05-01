-- Kindred initial schema.
--
-- NOTE: PRD specifies an IVFFlat index on entry_embeddings.embedding. We use
-- HNSW instead because IVFFlat requires data before index creation (its lists
-- are trained from existing rows); HNSW works on empty tables and is the modern
-- pgvector default for production-grade recall. See PR description for context.
--
-- The vector extension lives in the `extensions` schema per Supabase convention.

create extension if not exists vector with schema extensions;
create extension if not exists pgcrypto;

-- ----------------------------------------------------------------------------
-- entries: one row per journaling session
-- ----------------------------------------------------------------------------
create table entries (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references auth.users(id) on delete cascade,
    date        date not null,
    summary     text not null,
    transcript  jsonb,
    mood        text,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);
create index entries_user_date_idx on entries (user_id, date desc);

-- ----------------------------------------------------------------------------
-- patterns: a recurring HCB cycle, named by the user
-- ----------------------------------------------------------------------------
create table patterns (
    id                  uuid primary key default gen_random_uuid(),
    user_id             uuid not null references auth.users(id) on delete cascade,
    name                text not null,
    description         text,
    typical_thoughts    text,
    typical_emotions    text,
    typical_behaviors   text,
    typical_sensations  text,
    created_at          timestamptz not null default now(),
    last_seen_at        timestamptz not null default now(),
    occurrence_count    int not null default 0
);
create unique index patterns_user_lower_name_idx on patterns (user_id, lower(name));

-- ----------------------------------------------------------------------------
-- pattern_occurrences: a specific instance of a pattern in a specific entry
-- ----------------------------------------------------------------------------
create table pattern_occurrences (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references auth.users(id) on delete cascade,
    pattern_id  uuid not null references patterns(id) on delete cascade,
    entry_id    uuid not null references entries(id) on delete cascade,
    date        date not null,
    thoughts    text,
    emotions    text,
    behaviors   text,
    sensations  text,
    intensity   int,
    trigger     text,
    notes       text,
    created_at  timestamptz not null default now()
);
create index pattern_occurrences_pattern_date_idx on pattern_occurrences (pattern_id, date desc);
create index pattern_occurrences_entry_idx on pattern_occurrences (entry_id);
create index pattern_occurrences_user_date_idx on pattern_occurrences (user_id, date desc);

-- ----------------------------------------------------------------------------
-- entry_embeddings: pgvector sidecar for semantic search
-- ----------------------------------------------------------------------------
create table entry_embeddings (
    entry_id   uuid primary key references entries(id) on delete cascade,
    user_id    uuid not null references auth.users(id) on delete cascade,
    embedding  extensions.vector(1536) not null,
    content    text not null
);
create index entry_embeddings_hnsw_idx
    on entry_embeddings using hnsw (embedding extensions.vector_cosine_ops);

-- ----------------------------------------------------------------------------
-- connector_tokens: long-lived bearer tokens minted from /connect for Claude.ai
-- ----------------------------------------------------------------------------
create table connector_tokens (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references auth.users(id) on delete cascade,
    token       text unique not null,
    created_at  timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- Row-level security
-- ----------------------------------------------------------------------------
alter table entries enable row level security;
alter table patterns enable row level security;
alter table pattern_occurrences enable row level security;
alter table entry_embeddings enable row level security;
alter table connector_tokens enable row level security;

-- entries
create policy "entries owner select" on entries for select using (auth.uid() = user_id);
create policy "entries owner insert" on entries for insert with check (auth.uid() = user_id);
create policy "entries owner update" on entries for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "entries owner delete" on entries for delete using (auth.uid() = user_id);

-- patterns
create policy "patterns owner select" on patterns for select using (auth.uid() = user_id);
create policy "patterns owner insert" on patterns for insert with check (auth.uid() = user_id);
create policy "patterns owner update" on patterns for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "patterns owner delete" on patterns for delete using (auth.uid() = user_id);

-- pattern_occurrences
create policy "occurrences owner select" on pattern_occurrences for select using (auth.uid() = user_id);
create policy "occurrences owner insert" on pattern_occurrences for insert with check (auth.uid() = user_id);
create policy "occurrences owner update" on pattern_occurrences for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "occurrences owner delete" on pattern_occurrences for delete using (auth.uid() = user_id);

-- entry_embeddings
create policy "embeddings owner select" on entry_embeddings for select using (auth.uid() = user_id);
create policy "embeddings owner insert" on entry_embeddings for insert with check (auth.uid() = user_id);
create policy "embeddings owner update" on entry_embeddings for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "embeddings owner delete" on entry_embeddings for delete using (auth.uid() = user_id);

-- connector_tokens: only owner-select (inserts/lookups go through the
-- service-role key from the backend; users never write tokens client-side).
create policy "connector_tokens owner select" on connector_tokens for select using (auth.uid() = user_id);

-- ----------------------------------------------------------------------------
-- match_entries RPC: cosine similarity search over entry_embeddings.
-- security invoker so RLS evaluates with the caller's identity (the
-- user-scoped anon-key client passes their JWT through PostgREST).
-- ----------------------------------------------------------------------------
create or replace function match_entries(
    query_embedding extensions.vector(1536),
    match_count int default 5
)
returns table (entry_id uuid, similarity float, content text)
language sql
stable
security invoker
set search_path = extensions, public
as $$
    select
        e.entry_id,
        1 - (e.embedding <=> query_embedding) as similarity,
        e.content
    from entry_embeddings e
    order by e.embedding <=> query_embedding
    limit match_count;
$$;
