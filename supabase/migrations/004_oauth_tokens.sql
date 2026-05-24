-- OAuth 2.1 durable token stores (issue #125)
--
-- refresh_tokens: MCP server's issued refresh tokens (30-day TTL)
-- registered_clients: RFC 7591 dynamic client registrations (no TTL)
--
-- Both tables are owned by the MCP server process (service-role inserts/deletes)
-- and have no RLS user-scoped policy — tokens are server-managed, not user-editable.

create table oauth_refresh_tokens (
    token        text primary key,
    user_id      text not null,
    email        text,
    client_id    text not null,
    scope        text not null default 'mcp',
    expires_at   timestamptz not null,
    access_token_issued_at timestamptz,
    created_at   timestamptz not null default now()
);

create index oauth_refresh_tokens_user_id_idx on oauth_refresh_tokens (user_id);
create index oauth_refresh_tokens_expires_at_idx on oauth_refresh_tokens (expires_at);

create table oauth_registered_clients (
    client_id          text primary key,
    client_secret      text not null,
    redirect_uris      jsonb not null default '[]',
    client_name        text not null default '',
    grant_types        jsonb not null default '["authorization_code"]',
    response_types     jsonb not null default '["code"]',
    token_endpoint_auth_method text not null default 'client_secret_post',
    scope              text not null default 'mcp',
    created_at         timestamptz not null default now()
);

-- RLS enabled with no user-scoped policies — access is restricted to service-role key only.
-- The MCP server never exposes raw token values to clients.
alter table oauth_refresh_tokens enable row level security;
alter table oauth_registered_clients enable row level security;
-- Service-role key bypasses RLS; no additional policies needed for server writes.
