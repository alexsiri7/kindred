-- Service-role boundary audit (#44).
--
-- Eliminates the remaining request-path uses of SUPABASE_SERVICE_ROLE_KEY by
-- moving the privileged operations into RLS policies + security-definer
-- functions. After this migration the MCP server and web backend can talk to
-- Supabase using the anon key + the user's JWT only.

-- ----------------------------------------------------------------------------
-- connector_tokens: allow self-mints under RLS
-- ----------------------------------------------------------------------------
-- Lets POST /connect/token write its own row through user_client(jwt) instead
-- of bypassing RLS with the service-role key.
create policy "connector_tokens owner insert" on connector_tokens
    for insert with check (auth.uid() = user_id);

-- ----------------------------------------------------------------------------
-- lookup_connector_token: anon-callable token resolution
-- ----------------------------------------------------------------------------
-- The MCP middleware needs to map a bearer token → user_id BEFORE it knows who
-- the caller is, so an unauthenticated (anon) RPC is the only viable shape.
-- Granted to anon AND authenticated; security definer + a constant-shape
-- response (NULL on miss) avoids leaking timing/error oracles. Tokens are
-- 32-byte URL-safe random, so enumeration is not a concern.
create or replace function lookup_connector_token(p_token text)
returns uuid
language sql
stable
security definer
set search_path = public
as $$
    select user_id from connector_tokens where token = p_token limit 1;
$$;
revoke all on function lookup_connector_token(text) from public;
grant execute on function lookup_connector_token(text) to anon, authenticated;

-- ----------------------------------------------------------------------------
-- delete_my_account: self-service account deletion
-- ----------------------------------------------------------------------------
-- Replaces auth.admin.delete_user(user_id) in the web backend's DELETE
-- /account route. The function deletes auth.users for auth.uid() (the caller
-- can never specify another user's id) and the existing on-delete-cascade FKs
-- propagate to every app table.
create or replace function delete_my_account()
returns void
language plpgsql
security definer
set search_path = public, auth
as $$
begin
    if auth.uid() is null then
        raise exception 'must be authenticated';
    end if;
    delete from auth.users where id = auth.uid();
end;
$$;
revoke all on function delete_my_account() from public;
grant execute on function delete_my_account() to authenticated;
