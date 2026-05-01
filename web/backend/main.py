"""FastAPI app: read-only entry/pattern routes plus settings/connect mutations."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import connect, entries, patterns, search
from routes import settings as settings_route

app = FastAPI(title="Kindred Web Backend")

# TODO: read CORS allow_origins from env once Railway config lands.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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
