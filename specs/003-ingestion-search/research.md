# Research: Real Postings Ingestion & Semantic Search

**Feature**: 003-ingestion-search
**Date**: 2026-10-10

---

## Decision 1: Background Job Queue — RQ vs Celery

**Decision**: Use **RQ (Redis Queue)** with **rq-scheduler** for scheduled and on-demand ingestion.

**Rationale**: RQ is simpler and uses the same Redis instance already present in the stack (Feature 002). It requires no additional broker, has a minimal API surface, and integrates cleanly with FastAPI's lifespan pattern via the `rq` Python package. Celery would require a separate broker configuration (AMQP or Redis with Celery-specific channels) and adds significant setup complexity for a small number of job types.

**Alternatives considered**:
- **Celery**: Full-featured, but heavy. The overhead is unjustified for ~5 job types and a single-node deployment. Constitution IX (Simplicity) favours RQ.
- **APScheduler**: No Redis-backed persistence; jobs lost on restart.
- **Custom asyncio loop**: Fragile, hard to observe, not production-grade.

---

## Decision 2: Vector Index Type — HNSW vs IVFFlat

**Decision**: Use **HNSW** (Hierarchical Navigable Small World) index in pgvector.

**Rationale**: HNSW provides better query-time recall at the 10,000-posting scale without requiring a training step. IVFFlat requires a `CLUSTER` phase with a minimum number of rows before it delivers good recall, making it awkward for incremental ingestion. HNSW builds incrementally and stays accurate as new embeddings are inserted. At 10,000 vectors of dimension 1536, the HNSW index fits comfortably in PostgreSQL shared memory.

**Parameters**: `m = 16`, `ef_construction = 64` (pgvector defaults — adequate at this scale, Constitution IX).

**Alternatives considered**:
- **IVFFlat with `lists = 100`**: Works well but requires `ANALYZE` / periodic re-clustering as data grows. More operational burden.
- **No index (sequential scan)**: Acceptable under 5,000 rows but exceeds the 2-second budget at 10,000.

---

## Decision 3: Duplicate Detection — Levenshtein Similarity

**Decision**: Use **PostgreSQL `levenshtein()` from `fuzzystrmatch`** for title similarity. Threshold: similarity > 0.85 (`1 - levenshtein(title_a, title_b) / GREATEST(len_a, len_b)`).

**Rationale**: `fuzzystrmatch` ships with PostgreSQL and requires no extra dependencies (Constitution IX). The 0.85 threshold catches minor wording differences ("Software Developer Co-op" vs "Software Developer Coop") while avoiding false positives across genuinely different roles. Duplicate check runs on ingest only — not on every search — so O(n) cost per batch is acceptable.

**Alternatives considered**:
- **trigram similarity (`pg_trgm`)**: Good alternative; `fuzzystrmatch` was preferred to avoid enabling another extension. Both are valid; can be swapped if `fuzzystrmatch` proves slow on large batches.
- **Exact title match only**: Too strict — misses "Co-op" vs "Coop" variations common in job postings.
- **ML-based deduplication**: Overkill for 200–10,000 postings.

---

## Decision 4: Embedding Model — text-embedding-3-small

**Decision**: Use **OpenAI `text-embedding-3-small`** (1536 dimensions) as the default embedding model; configurable via `EMBED_MODEL` env var.

**Rationale**: `text-embedding-3-small` offers a strong balance of quality, speed, and cost at $0.02/million tokens. The 1536-dimension vector fits in pgvector's supported range and matches the dimension used in the `posting_embeddings` table. Swapping to a self-hosted model (e.g., `sentence-transformers/all-MiniLM-L6-v2`) later is possible by changing `EMBED_MODEL` and the dimension, requiring a new migration.

**Alternatives considered**:
- **text-embedding-ada-002**: Older model, same dimension, slightly lower quality at similar cost.
- **sentence-transformers (local)**: Eliminates OpenAI dependency but requires GPU or high CPU. Blocked by Constitution IX (prefer well-documented, widely-used tools).
- **text-embedding-3-large (3072 dims)**: 2x cost and storage with marginal quality gain at co-op posting scale.

---

## Decision 5: HTTP Mocking in Tests — respx

**Decision**: Use **respx** to record and replay httpx responses in tests.

**Rationale**: The adapters use `httpx.AsyncClient` for all outbound requests. `respx` intercepts httpx calls at the transport level, requiring no monkey-patching and no live network calls (FR-016). Fixture responses are stored as JSON files under `backend/tests/fixtures/ingest/`. `respx` is actively maintained and purpose-built for httpx.

**Alternatives considered**:
- **responses (for `requests`)**: Not compatible with httpx async.
- **aioresponses**: Works with aiohttp, not httpx.
- **VCR.py**: Heavier cassette format; overkill for simple API responses.

---

## Decision 6: Skill Extraction Pipeline

**Decision**: Two-stage extraction: **regex/keyword matching** against the DB taxonomy first; **Anthropic Claude API** (claude-haiku-4-5 for cost) fallback when confidence < 0.6.

**Rationale**: The taxonomy covers ~150 known skills. Regex matching is deterministic, fast, and free. The LLM fallback handles edge cases (novel skill names, non-standard phrasing) with a tightly scoped prompt that returns only JSON. Claude Haiku is used for extraction (not the assistant model) to keep cost low (Constitution III — performance budgets include cost). A confidence score of 0.6 triggers the fallback; scores are derived from the fraction of extracted fields that matched the taxonomy unambiguously.

**Alternatives considered**:
- **Pure regex only**: Misses non-standard skill names in job descriptions.
- **LLM for everything**: Slow and expensive per-posting at scale.
- **spaCy NER**: Adds a heavy model dependency (Constitution IX).

---

## Decision 7: Hybrid Search Weighting

**Decision**: Hybrid search combines **tsvector rank (BM25-like)** and **cosine similarity** with configurable weights. Default: `keyword_weight=0.0, semantic_weight=1.0` for semantic mode; `keyword_weight=1.0, semantic_weight=0.0` for keyword mode. Weights stored in the query parameter `search_mode=keyword|semantic`.

**Rationale**: The toggle model (full keyword vs full semantic) is simpler to explain to users than a blended weight. The URL parameter preserves the mode across page loads (FR-011 / Feature 001 URL-state requirement). A blended mode can be added later without a schema change.

**SQL pattern**:
```sql
-- Semantic mode
ORDER BY embedding <=> query_embedding ASC
-- Keyword mode (existing)
ORDER BY ts_rank(search_vector, query) DESC
```

---

## Decision 8: Admin Flag — Boolean Column

**Decision**: Add `is_admin BOOLEAN NOT NULL DEFAULT FALSE` to the `users` table in migration 0004. No separate admin role table.

**Rationale**: A single boolean is sufficient for a portfolio project with one admin role. Constitution IX (Simplicity) rules out a full RBAC system. If multiple admin roles are needed later, the boolean can be migrated to an enum without data loss.

**Note**: The initial admin account is promoted via a one-off SQL statement or a seed script, not through a UI flow.
