-- Restrict OAuth RPC execution to the server role.
--
-- The MCP server now calls these functions with a server-only client
-- (mcp/services/oauth_store.py), so they no longer need to be executable by
-- the anon / authenticated API roles.

revoke execute on function public.load_oauth_refresh_tokens() from public, anon, authenticated;
revoke execute on function public.load_oauth_registered_clients() from public, anon, authenticated;
revoke execute on function public.upsert_oauth_refresh_token(text, text, text, text, text, timestamptz, timestamptz) from public, anon, authenticated;
revoke execute on function public.upsert_oauth_registered_client(text, text, jsonb, text, jsonb, jsonb, text, text) from public, anon, authenticated;
revoke execute on function public.delete_oauth_refresh_token(text) from public, anon, authenticated;

grant execute on function public.load_oauth_refresh_tokens() to service_role;
grant execute on function public.load_oauth_registered_clients() to service_role;
grant execute on function public.upsert_oauth_refresh_token(text, text, text, text, text, timestamptz, timestamptz) to service_role;
grant execute on function public.upsert_oauth_registered_client(text, text, jsonb, text, jsonb, jsonb, text, text) to service_role;
grant execute on function public.delete_oauth_refresh_token(text) to service_role;
