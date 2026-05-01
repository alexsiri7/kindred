# Kindred

AI reflective journaling via MCP. Claude.ai is the conversation; Kindred is the memory and structure.

See [docs/kindred-prd-dd.md](docs/kindred-prd-dd.md) for the full PRD and design doc.

## Structure

```
mcp/           # MCP server (FastAPI, Python 3.12)
web/
  backend/     # Web app API (FastAPI, Python 3.12)
  frontend/    # React 19 + TypeScript + Vite + Tailwind + Zustand
prompts/       # MCP prompt definitions (/kindred-start, /kindred-hcb, /kindred-close)
supabase/
  migrations/  # SQL migrations
scripts/
  gates.sh     # CI: lint + typecheck + test
```

## Development

```bash
./scripts/gates.sh   # run all checks
```
