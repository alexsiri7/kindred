"""Requesty-routed OpenAI embeddings (duplicated from mcp/embeddings.py).

The two services deploy independently per PRD §Architecture, so we duplicate
the 8-line helper rather than introduce a shared package.
"""

from __future__ import annotations

from functools import lru_cache

from openai import OpenAI

from settings import settings

EMBEDDING_MODEL = "openai/text-embedding-3-small"
EMBEDDING_DIM = 1536


@lru_cache(maxsize=1)
def _client() -> OpenAI:
    return OpenAI(base_url=settings.requesty_base_url, api_key=settings.requesty_api_key)


def embed(text: str) -> list[float]:
    if not text.strip():
        raise ValueError("cannot embed empty text")
    resp = _client().embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
        encoding_format="float",
    )
    return list(resp.data[0].embedding)
