# Kindred

AI reflective journaling via MCP. Your AI assistant is the conversation; Kindred is the memory and structure. Works with any MCP-capable client (Claude Projects, ChatGPT, Gemini Gems, and others).

See [docs/kindred-prd-dd.md](docs/kindred-prd-dd.md) for the full PRD and design doc.

## Structure

```
mcp/           # MCP server (FastAPI, Python 3.12)
web/
  backend/     # Web app API (FastAPI, Python 3.12)
  frontend/    # React 19 + TypeScript + Vite + Tailwind + Zustand
prompts/       # MCP prompt definitions (/kindred-start, /kindred-hcb, /kindred-close) + host-level guide (kindred://guide)
supabase/
  migrations/  # SQL migrations
scripts/
  gates.sh     # CI: lint + typecheck + test
```

## Quickstart

```bash
cp .env.example .env                                 # fill in Supabase + Requesty keys
supabase db push                                     # apply migrations to your project

# MCP server (port 8000)
cd mcp && pip install -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port 8000

# Web backend (port 8001)
cd web/backend && pip install -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port 8001

# Web frontend (Vite dev server, port 5173)
cd web/frontend && npm install && npm run dev
```

## Setup

See [docs/setup.md](docs/setup.md) for client-specific setup (Claude Projects, ChatGPT, Gemini Gems).

## Development

```bash
./scripts/gates.sh   # run lint + typecheck + test across all three trees
```
