#!/usr/bin/env bash
set -euo pipefail

echo "=== Kindred gates ==="

# Shared lib (must run first so subsequent backends can import it)
if [ -d "lib" ]; then
  echo "--- lib: install ---"
  pip install -q -e ./lib
  echo "--- lib: lint ---"
  cd lib
  pip install -q -r requirements-dev.txt
  ruff check .
  echo "--- lib: typecheck ---"
  mypy .
  echo "--- lib: test ---"
  pytest -q
  cd ..
fi

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

echo "--- service-role boundary check (#44) ---"
# Per #44, service_role / service_client must not appear in request-handling
# code (mcp/, web/backend/, lib/). Tests legitimately reference them for
# historical context so are excluded.
if grep -rn --include='*.py' --exclude-dir=tests -E 'service_role|service_client' mcp/ web/backend/ lib/; then
  echo "FAIL: service_role / service_client reference found in request-handling code."
  echo "      Per #44, these are only allowed under scripts/ and supabase/."
  exit 1
fi

echo "=== All gates passed ==="
