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
5. The Service tables in this runbook (`docs/runbook-railway.md`).
6. The web service's `Required build args` list (here and the `ARG`
   lines in `web/Dockerfile`) if a `VITE_*` variable is added or removed.

CI builds both Dockerfiles at repo-root context (the `docker-build`
job in `.github/workflows/ci.yml`), so build-context mismatches in
the Dockerfiles themselves now fail at PR time. The Railway
dashboard's `Root Directory` and `Config-as-code Path` are still
implicit and not exercised by CI — drift in those settings will
still only fail at the next prod deploy.

## CI-driven deploy (recommended)

`.github/workflows/deploy.yml` runs `railway up` from the repo root after every
CI pass on `main`. Because `railway up` uploads files directly rather than
triggering Railway's GitHub integration, the dashboard **Root Directory** setting
is irrelevant — Railway always receives the full repo context including `lib/`.

### One-time operator setup

1. **Railway dashboard → both services → Settings → Source**:
   - Disable **Deploy on push** (Railway's GitHub auto-deploy) first, before
     adding `RAILWAY_TOKEN`, to prevent a brief window where both Railway
     auto-deploy and CI-deploy fire simultaneously on the next push.

2. **GitHub secret**: `RAILWAY_TOKEN` — generate a project-scoped token in
   Railway → (your project) → Settings → Tokens (not Account → Tokens, to
   limit blast radius to this project), then add it in GitHub Settings →
   Secrets and variables → Actions. The workflow skips silently when the
   secret is absent.

3. **Railway dashboard → `web` service → Settings → Source**:
   - Set **Config-as-code Path**: `web/railway.toml`
     (so `railway up --service web` picks `web/Dockerfile`, not the root MCP config)

`VITE_*` build variables stay in Railway — no changes needed there.

### After setup

Every merge to `main` that passes CI triggers one CI-managed deploy per service.
The Root Directory dashboard setting is no longer on the critical path; drift
there cannot break production deploys.

### Rotating RAILWAY_TOKEN

If the token is compromised or expired:

1. Generate a new project-scoped token in Railway → (your project) → Settings → Tokens.
2. Update the GitHub secret: Settings → Secrets and variables → Actions → `RAILWAY_TOKEN` → Update.
3. Revoke the old token in Railway → (your project) → Settings → Tokens.

Deploys will fail with an auth error while the token is invalid; they resume automatically on the next push after the secret is updated.

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
