# Railway deploy runbook

Two services deploy from this repo via Railway's GitHub integration.
Both build at the repo-root build context so they can `COPY` the
shared `lib/` package.

## Service: mcp

- **Root Directory**: `/`
- **Config-as-code Path**: `railway.toml` (default)
- **Dockerfile**: `mcp/Dockerfile`

## Service: web

- **Root Directory**: `/`
- **Config-as-code Path**: `web/railway.toml`
- **Dockerfile**: `web/Dockerfile`
- **Required build args** (set in Railway → Variables → Build):
  - `VITE_SUPABASE_URL`
  - `VITE_SUPABASE_ANON_KEY`
  - `VITE_API_BASE_URL`
  - `VITE_SENTRY_DSN`

## Why both services use repo-root build context

Both services depend on the shared `lib/` package via
`COPY lib/ /lib/` + `pip install -e /lib`. `lib/` lives at the
repo root, so the build context must include it. The web service
also copies `web/frontend/...` and `web/backend/...`, and the MCP
service copies `mcp/...` and `prompts/...` — all of which assume
build context = repo root.

Leaving the web service's **Config-as-code Path** blank causes
Railway to pick up the root-level `railway.toml` (which is the
MCP service config) and deploy `mcp/Dockerfile` to the web URL.
Always set it explicitly to `web/railway.toml`.

## When changing service layout

If you move, rename, or split a service directory, **also update**:

1. The service's `dockerfilePath` in its `railway.toml`.
2. The Railway dashboard `Config-as-code Path` if the toml file moved.
3. Any `COPY <path>` lines in the Dockerfile.
4. Any service-specific `Root Directory` in the Railway dashboard.

CI (`scripts/gates.sh`) does not build Docker images, so these
mismatches will not fail until the next prod deploy.

## Diagnosing a failed deploy

If a Railway deploy fails within ~60s of starting, suspect a
build-context mismatch (a `COPY` line referencing a path that
isn't reachable from the configured Root Directory). Check:

```bash
gh api repos/<owner>/<repo>/deployments?per_page=5 \
  | jq '.[] | {id, sha, env: .environment, created_at}'

gh api repos/<owner>/<repo>/deployments/<id>/statuses \
  | jq '.[] | {state, created_at}'
```

A sub-minute `failure` status almost always means the Dockerfile
couldn't `COPY` something it expected. Verify the service's
**Root Directory** and **Config-as-code Path** match the table
above before retrying.
