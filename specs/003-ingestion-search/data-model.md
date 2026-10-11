# Data Model: Real Postings Ingestion & Semantic Search

**Feature**: 003-ingestion-search
**Date**: 2026-10-10

---

## New Tables

### `ingest_sources`

Represents a configured ingestion source (public API, RSS feed, etc.).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK, default gen_random_uuid() | |
| `name` | TEXT | NOT NULL | Human-readable label, e.g. "Shopify Careers API" |
| `adapter_type` | TEXT | NOT NULL, CHECK IN ('json_api','rss','csv','manual') | Determines which adapter class handles this source |
| `config` | JSONB | NOT NULL, default '{}' | Adapter-specific config: base_url, auth headers, field mappings |
| `enabled` | BOOLEAN | NOT NULL, default TRUE | Admin can disable without deleting |
| `auto_paused` | BOOLEAN | NOT NULL, default FALSE | Set TRUE after 3 consecutive failures (FR-015) |
| `consecutive_failures` | INTEGER | NOT NULL, default 0 | Reset to 0 on success |
| `last_run_at` | TIMESTAMPTZ | nullable | Timestamp of last completed run |
| `created_at` | TIMESTAMPTZ | NOT NULL, server_default NOW() | |

**Indexes**: `idx_ingest_sources_enabled` on `(enabled, auto_paused)`.

---

### `ingest_runs`

One row per ingestion attempt for one source.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK, default gen_random_uuid() | |
| `source_id` | UUID | FK → ingest_sources.id ON DELETE CASCADE, NOT NULL | |
| `started_at` | TIMESTAMPTZ | NOT NULL | |
| `finished_at` | TIMESTAMPTZ | nullable | NULL while running |
| `status` | TEXT | NOT NULL, CHECK IN ('running','success','partial','failed') | |
| `added` | INTEGER | NOT NULL, default 0 | Postings inserted |
| `updated` | INTEGER | NOT NULL, default 0 | Postings updated |
| `closed` | INTEGER | NOT NULL, default 0 | Postings marked closed |
| `errors` | INTEGER | NOT NULL, default 0 | Row-level or network errors |
| `error_log` | TEXT[] | NOT NULL, default '{}' | Up to 100 error messages |

**Indexes**: `idx_ingest_runs_source_id` on `(source_id)`, `idx_ingest_runs_started_at DESC` on `(started_at DESC)`.

---

### `skills`

The fixed skill taxonomy (~150 entries), editable by admins.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK, default gen_random_uuid() | |
| `name` | TEXT | NOT NULL, UNIQUE | Canonical skill name, e.g. "Python" |
| `aliases` | TEXT[] | NOT NULL, default '{}' | Alternative spellings/abbreviations for regex matching |
| `category` | TEXT | nullable | e.g. "Language", "Framework", "Tool" |
| `created_at` | TIMESTAMPTZ | NOT NULL, server_default NOW() | |

**Indexes**: `idx_skills_name` (unique) on `name`, GIN index on `aliases`.

---

### `posting_embeddings`

Stores the pgvector embedding for each posting. Separate table keeps the heavy vector column out of the hot `postings` path.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `posting_id` | UUID | PK, FK → postings.id ON DELETE CASCADE | 1:1 with posting |
| `embedding` | vector(1536) | NOT NULL | text-embedding-3-small output |
| `model` | TEXT | NOT NULL | Model name used, e.g. "text-embedding-3-small" |
| `generated_at` | TIMESTAMPTZ | NOT NULL, server_default NOW() | |

**Indexes**: HNSW index `idx_posting_embeddings_hnsw` using `vector_cosine_ops`, `m=16`, `ef_construction=64`.

---

## Modified Tables

### `postings` (additions)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `source_id` | UUID | FK → ingest_sources.id ON DELETE SET NULL, nullable | NULL for manually-entered postings |
| `source_ref` | TEXT | nullable | Source's own identifier for dedup across runs |
| `closed_at` | TIMESTAMPTZ | nullable | Set when posting disappears from source |
| `low_confidence_fields` | JSONB | NOT NULL, default '{}' | Map of field → confidence score for admin display |

**New index**: `idx_postings_closed_at` on `closed_at` (for filtering closed postings).
**New index**: `idx_postings_source_ref` on `(source_id, source_ref)` UNIQUE WHERE source_ref IS NOT NULL (fast dedup lookup).

---

### `users` (additions)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `is_admin` | BOOLEAN | NOT NULL, default FALSE | Admin flag; promoted via seed/SQL |

---

## Entity Relationships

```
ingest_sources ──< ingest_runs          (one source → many runs)
ingest_sources ──< postings             (one source → many postings; nullable)
postings       ──> posting_embeddings   (one-to-one; embedding generated async)
skills                                  (standalone taxonomy; referenced by extraction logic)
users          (is_admin added)
```

---

## State Machine: Posting Lifecycle

```
ACTIVE (default)  ──[source run: posting absent]──>  CLOSED (closed_at set)
CLOSED            ──[source run: posting reappears]──>  ACTIVE (closed_at cleared)
```

Students see only ACTIVE postings by default; the toggle to show expired also shows CLOSED.

---

## State Machine: IngestSource Auto-Pause

```
ENABLED (consecutive_failures = 0..2)
  ──[run fails]──>  consecutive_failures += 1
  ──[run succeeds]──>  consecutive_failures = 0

ENABLED (consecutive_failures = 3)
  ──[run fails for 3rd time]──>  auto_paused = TRUE (FR-015)

AUTO_PAUSED
  ──[admin re-enables]──>  auto_paused = FALSE, consecutive_failures = 0
```
