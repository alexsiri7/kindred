---
id: "003"
title: "Semantic search across entries"
status: "done"
github_issue: 120
updated: "2026-05-12"
---

## Why

Keyword search fails for emotional content — a user asking "when did I feel hopeless about work?" won't match entries that say "utterly burnt out at the office." Semantic search over vector embeddings closes this gap, letting users (and Claude) find thematically related entries regardless of exact wording.

## What

Every saved entry has its summary embedded via OpenAI `text-embedding-3-small` (1536 dimensions, routed through the Requesty gateway) and stored in an `entry_embeddings` table with a pgvector `vector(1536)` column and an HNSW index for cosine similarity. Search runs through a Postgres RPC `match_entries` that computes `1 - (embedding <=> query_embedding)` and returns the top-N entries above a similarity threshold. The `search_entries` MCP tool and the `/search` web endpoint both invoke `lib/services/entries.search_entries()`, which embeds the query then calls the RPC.
