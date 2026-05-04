-- Connector token lifecycle (#41).
--
-- Adds expiry, revocation, and last-used tracking to connector_tokens so a
-- leaked token no longer grants indefinite access. The lookup RPC filters
-- expired/revoked rows and stamps last_used_at atomically inside a CTE.

-- ----------------------------------------------------------------------------
-- connector_tokens: lifecycle columns
-- ----------------------------------------------------------------------------
alter table connector_tokens
    add column if not exists expires_at   timestamptz,
    add column if not exists last_used_at timestamptz,
    add column if not exists revoked_at   timestamptz;

-- Backfill expiry on existing rows so they keep working for 90 days from
-- migration time (rather than auto-expiring by creation date, which would
-- surprise current users).
update connector_tokens
   set expires_at = now() + interval '90 days'
 where expires_at is null;

-- Partial index on the lookup hot path; revoked rows fall out so the index
-- stays small as revocations accumulate.
create index if not exists connector_tokens_token_active_idx
    on connector_tokens (token)
    where revoked_at is null;

-- ----------------------------------------------------------------------------
-- RLS: allow a user to revoke (update) their own tokens
-- ----------------------------------------------------------------------------
create policy "connector_tokens owner update" on connector_tokens
    for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- ----------------------------------------------------------------------------
-- lookup_connector_token: filter expired/revoked + stamp last_used_at
-- ----------------------------------------------------------------------------
-- Single round-trip: the UPDATE inside the CTE atomically validates the token
-- and records the use, returning user_id only on a successful hit. NULL is
-- returned for expired, revoked, or unknown tokens — all three collapse to
-- the same constant-shape miss to avoid leaking which case applied.
--
-- Note: changes from `stable` to `volatile` because it now writes. The
-- `volatile` keyword (or omitting it — volatile is the default) is required
-- so the planner doesn't assume the function is read-only.
create or replace function lookup_connector_token(p_token text)
returns uuid
language sql
volatile
security definer
set search_path = public
as $$
    with hit as (
        update connector_tokens
           set last_used_at = now()
         where token = p_token
           and revoked_at is null
           and (expires_at is null or expires_at > now())
        returning user_id
    )
    select user_id from hit limit 1;
$$;
revoke all on function lookup_connector_token(text) from public;
grant execute on function lookup_connector_token(text) to anon, authenticated;
