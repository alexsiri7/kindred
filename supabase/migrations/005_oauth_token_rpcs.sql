-- OAuth token CRUD via security-definer RPCs (#44 boundary compliance).
--
-- Replaces direct service-role-key access in mcp/services/oauth_store.py with
-- SECURITY DEFINER functions callable by the anon key. Mirrors the pattern
-- established by lookup_connector_token in 002_service_role_audit.sql.

-- ----------------------------------------------------------------------------
-- upsert_oauth_refresh_token
-- ----------------------------------------------------------------------------
create or replace function upsert_oauth_refresh_token(
    p_token                  text,
    p_user_id                text,
    p_email                  text,
    p_client_id              text,
    p_scope                  text,
    p_expires_at             timestamptz,
    p_access_token_issued_at timestamptz
) returns void
language sql
volatile
security definer
set search_path = public
as $$
    insert into oauth_refresh_tokens
        (token, user_id, email, client_id, scope, expires_at, access_token_issued_at)
    values
        (p_token, p_user_id, p_email, p_client_id, p_scope, p_expires_at, p_access_token_issued_at)
    on conflict (token) do update set
        user_id                  = excluded.user_id,
        email                    = excluded.email,
        client_id                = excluded.client_id,
        scope                    = excluded.scope,
        expires_at               = excluded.expires_at,
        access_token_issued_at   = excluded.access_token_issued_at;
$$;
revoke all on function upsert_oauth_refresh_token(text, text, text, text, text, timestamptz, timestamptz) from public;
grant execute on function upsert_oauth_refresh_token(text, text, text, text, text, timestamptz, timestamptz) to anon, authenticated;

-- ----------------------------------------------------------------------------
-- delete_oauth_refresh_token
-- ----------------------------------------------------------------------------
create or replace function delete_oauth_refresh_token(p_token text)
returns void
language sql
volatile
security definer
set search_path = public
as $$
    delete from oauth_refresh_tokens where token = p_token;
$$;
revoke all on function delete_oauth_refresh_token(text) from public;
grant execute on function delete_oauth_refresh_token(text) to anon, authenticated;

-- ----------------------------------------------------------------------------
-- load_oauth_refresh_tokens
-- ----------------------------------------------------------------------------
create or replace function load_oauth_refresh_tokens()
returns setof oauth_refresh_tokens
language sql
stable
security definer
set search_path = public
as $$
    select * from oauth_refresh_tokens where expires_at > now();
$$;
revoke all on function load_oauth_refresh_tokens() from public;
grant execute on function load_oauth_refresh_tokens() to anon, authenticated;

-- ----------------------------------------------------------------------------
-- upsert_oauth_registered_client
-- ----------------------------------------------------------------------------
create or replace function upsert_oauth_registered_client(
    p_client_id                  text,
    p_client_secret              text,
    p_redirect_uris              jsonb,
    p_client_name                text,
    p_grant_types                jsonb,
    p_response_types             jsonb,
    p_token_endpoint_auth_method text,
    p_scope                      text
) returns void
language sql
volatile
security definer
set search_path = public
as $$
    insert into oauth_registered_clients
        (client_id, client_secret, redirect_uris, client_name, grant_types,
         response_types, token_endpoint_auth_method, scope)
    values
        (p_client_id, p_client_secret, p_redirect_uris, p_client_name, p_grant_types,
         p_response_types, p_token_endpoint_auth_method, p_scope)
    on conflict (client_id) do update set
        client_secret              = excluded.client_secret,
        redirect_uris              = excluded.redirect_uris,
        client_name                = excluded.client_name,
        grant_types                = excluded.grant_types,
        response_types             = excluded.response_types,
        token_endpoint_auth_method = excluded.token_endpoint_auth_method,
        scope                      = excluded.scope;
$$;
revoke all on function upsert_oauth_registered_client(text, text, jsonb, text, jsonb, jsonb, text, text) from public;
grant execute on function upsert_oauth_registered_client(text, text, jsonb, text, jsonb, jsonb, text, text) to anon, authenticated;

-- ----------------------------------------------------------------------------
-- load_oauth_registered_clients
-- ----------------------------------------------------------------------------
create or replace function load_oauth_registered_clients()
returns setof oauth_registered_clients
language sql
stable
security definer
set search_path = public
as $$
    select * from oauth_registered_clients;
$$;
revoke all on function load_oauth_registered_clients() from public;
grant execute on function load_oauth_registered_clients() to anon, authenticated;
