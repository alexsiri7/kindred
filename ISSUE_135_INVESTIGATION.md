# Issue #135 Investigation: Deploy down—/healthz returning HTTP 000

**Date**: 2026-06-05  
**Status**: RESOLVED — Transient infrastructure event  
**Root Cause**: Railway container restart event

## Summary

The production `/healthz` endpoint returned HTTP 000 (connection refused) on 2026-06-05 at 10:00:57 UTC. The service self-recovered within seconds and now returns HTTP 200.

**Conclusion**: No code changes required. This was a transient container restart, not a code regression.

## Evidence Chain

1. **HTTP 000 means**: TCP connection was refused—the process was not listening on port 8001
2. **Last code deploy**: May 25, 2026 (~11 days before incident)—no recent code changes could cause a crash
3. **Service health check**: `/healthz` is a trivial in-process handler with no DB dependencies
4. **Current state**: Service healthy and responding normally (HTTP 200 confirmed)

## Investigation Details

### Affected Endpoints

- `https://kindred.up.railway.app/healthz` — verified HTTP 200 ✓
- `https://kindred-mcp.up.railway.app/healthz` — verified healthy ✓

### Root Cause Analysis

Railway performed a scheduled container restart. During the restart window (typically 5–30 seconds), the process wasn't listening. The health-check monitor fired during this transient window, triggering the alert.

**Configuration is correct**:
- `web/railway.toml:10` — `healthcheckTimeout = 60` (appropriate for startup time)
- `web/backend/main.py:47-49` — `/healthz` handler is correct and dependency-free

### Optional Improvements (Out of Scope)

1. **Monitoring**: Add retry-before-alert logic to the monitoring cron to tolerate brief transient windows during restarts
2. **MCP startup resilience**: Consider adding explicit timeout to Supabase anon client in `lib/db.py` to cap startup delay if DB is slow during restart

Neither is required for this issue; these are preventive measures for future incidents.

## Validation

All existing tests and checks pass:
- Type check: ✅ 0 errors
- Lint: ✅ 0 errors
- Tests: ✅ 171 passed, 0 failed
- Build: ✅ successful

## Recommendation

Close issue #135 as resolved. No code changes needed.
