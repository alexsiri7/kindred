# Kindred

AI reflective journaling via MCP. Your AI assistant is the conversation; Kindred is the memory and structure. Works with any MCP-capable client (Claude Projects, ChatGPT, Gemini Gems, and others).

See [docs/kindred-prd-dd.md](docs/kindred-prd-dd.md) for the full PRD and design doc.

## Structure

```
lib/           # Shared Python package: db helpers, embeddings, services
mcp/           # MCP server (FastAPI, Python 3.12)
web/
  backend/     # Web app API (FastAPI, Python 3.12)
  frontend/    # React 19 + TypeScript + Vite + Tailwind + Zustand
prompts/       # kindred-guide.md — behavioural guide served as the kindred://guide MCP resource
supabase/
  migrations/  # SQL migrations
scripts/
  gates.sh     # CI: lint + typecheck + test
```

## Quickstart

```bash
cp .env.example .env                                 # fill in Supabase + Requesty keys
supabase db push                                     # apply migrations to your project

# First time only: install the shared lib in editable mode
pip install -e ./lib

# MCP server (port 8000)
cd mcp && pip install -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port 8000

# Web backend (port 8001)
cd web/backend && pip install -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port 8001

# Web frontend (Vite dev server, port 5173)
cd web/frontend && npm install && npm run dev
```

## Setup

See [docs/setup.md](docs/setup.md) for client-specific setup (Claude Projects, ChatGPT, Gemini Gems).

## Deployment

Both services deploy to Railway via CI: every merge to `main` that passes all CI checks triggers `.github/workflows/deploy.yml`, which runs `railway up` from the repo root. Deploying from the repo root means the Railway dashboard **Root Directory** setting is irrelevant — `lib/` is always reachable.

Before changing any `Dockerfile`, `railway.toml`, or the `lib/` layout, see [docs/runbook-railway.md](docs/runbook-railway.md) for the per-service Railway dashboard contract and CI-driven deploy setup steps.

CI also runs a `docker-build` gate that builds both `mcp/Dockerfile` and `web/Dockerfile` at repo-root context on every PR, catching build-context mismatches before they reach prod.

## Development

```bash
./scripts/gates.sh   # run lint + typecheck + test across all three trees
```

## GitHub Actions secrets

Three secrets must be added in the repo's **Settings → Secrets and variables → Actions**:

| Secret | Workflow | Description |
|---|---|---|
| `SUPABASE_ACCESS_TOKEN` | migrate.yml | Supabase personal access token (create at https://supabase.com/dashboard/account/tokens) |
| `SUPABASE_DB_PASSWORD` | migrate.yml | Production database password for your Supabase project |
| `RAILWAY_TOKEN` | deploy.yml | Railway API token — generate in Railway → (your project) → Settings → Tokens. Without this secret, the deploy workflow **hard-fails** on every `main` push (by design). See [docs/runbook-railway.md](docs/runbook-railway.md) for setup steps. |
