"""FastAPI app: read-only entry/pattern routes plus settings/connect mutations."""

from __future__ import annotations

import os
from pathlib import Path

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routes import connect, entries, patterns, search
from routes import settings as settings_route
from settings import settings

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=0.1,
        environment="production",
    )

app = FastAPI(title="Kindred Web Backend")

_origins_raw = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173")
_origins = [o.strip() for o in _origins_raw.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (
    entries.router,
    patterns.router,
    search.router,
    settings_route.router,
    connect.router,
):
    app.include_router(r)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


# Serve the built React frontend for all non-API routes.
_static = Path(__file__).parent / "static"
if _static.exists():
    app.mount("/", StaticFiles(directory=_static, html=True), name="frontend")
