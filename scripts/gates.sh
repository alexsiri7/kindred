#!/usr/bin/env bash
set -euo pipefail

echo "=== Kindred gates ==="

# MCP server
if [ -d "mcp" ]; then
  echo "--- mcp: lint ---"
  cd mcp
  pip install -q -r requirements-dev.txt
  ruff check .
  echo "--- mcp: typecheck ---"
  mypy .
  echo "--- mcp: test ---"
  pytest -q
  cd ..
fi

# Web app backend
if [ -d "web/backend" ]; then
  echo "--- web/backend: lint ---"
  cd web/backend
  pip install -q -r requirements-dev.txt
  ruff check .
  echo "--- web/backend: typecheck ---"
  mypy .
  echo "--- web/backend: test ---"
  pytest -q
  cd ../..
fi

# Web app frontend
if [ -d "web/frontend" ]; then
  echo "--- web/frontend: lint + typecheck ---"
  cd web/frontend
  npm ci --silent
  npm run lint
  npm run typecheck
  echo "--- web/frontend: test ---"
  npm test -- --run
  cd ../..
fi

echo "=== All gates passed ==="
