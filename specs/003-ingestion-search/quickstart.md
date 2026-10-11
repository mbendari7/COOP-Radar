# Quickstart Validation: Real Postings Ingestion & Semantic Search

**Feature**: 003-ingestion-search
**Date**: 2026-10-10

## Prerequisites

- Docker Compose stack running: `docker compose up --build`
- Migrations applied: `docker compose exec api alembic upgrade head`
- Seeds loaded: `docker compose exec api python backend/seed/run.py`
- API accessible at `http://localhost:8000`
- Frontend at `http://localhost:5173`

---

## Scenario 1 — Scheduled Ingestion (US1)

### Setup

The stack starts an RQ worker and scheduler. A fixture-backed "Acme JSON API" source is pre-seeded via `backend/seed/ingest_sources.py`.

### Steps

```bash
# 1. Confirm source exists
curl http://localhost:8000/api/admin/sources \
  -H "Cookie: session=<admin-session>" | jq .

# 2. Trigger a manual run
curl -X POST http://localhost:8000/api/admin/sources/<source-id>/run \
  -H "Cookie: session=<admin-session>"

# 3. Poll until finished (status != "running")
curl http://localhost:8000/api/admin/sources/<source-id>/runs \
  -H "Cookie: session=<admin-session>" | jq '.items[0]'

# Expected: status="success", added > 0
```

### Expected outcome

- Run status is `"success"` with `added >= 1`.
- `GET /api/postings` returns the imported postings.
- Running the same source again produces `added=0, updated=0`.

---

## Scenario 2 — CSV Upload (US2)

### Setup

Download the sample CSV: `backend/tests/fixtures/ingest/sample_postings.csv`

### Steps

```bash
# Upload valid CSV
curl -X POST http://localhost:8000/api/postings/upload \
  -H "Cookie: session=<user-session>" \
  -F "file=@sample_postings.csv"

# Expected response:
# { "added": 5, "skipped_duplicates": 0, "errors": [] }

# Upload with one invalid row
curl -X POST http://localhost:8000/api/postings/upload \
  -H "Cookie: session=<user-session>" \
  -F "file=@sample_postings_with_error.csv"

# Expected response:
# { "added": 4, "skipped_duplicates": 0, "errors": [{"row":3,"column":"deadline","message":"..."}] }

# Upload same file again — duplicates detected
curl -X POST http://localhost:8000/api/postings/upload \
  -H "Cookie: session=<user-session>" \
  -F "file=@sample_postings.csv"
# Expected: { "added": 0, "skipped_duplicates": 5, "errors": [] }
```

---

## Scenario 3 — Semantic Search (US3)

### Setup

Run the embedding worker to generate embeddings for seeded postings:
```bash
docker compose exec worker python -m app.ingest.embed_worker --all
```

### Steps

```bash
# Keyword search (baseline)
curl "http://localhost:8000/api/postings?q=firmware&search_mode=keyword" | jq '.total'

# Semantic search — should find "microcontroller C developer" posts
curl "http://localhost:8000/api/postings?q=embedded+firmware&search_mode=semantic" | jq '.items[].title'

# Similar postings
curl "http://localhost:8000/api/postings/<posting-id>/similar" | jq '.items | length'
# Expected: 5 (or fewer if dataset is small)
```

**Frontend**: Navigate to `/` → type "embedded firmware" in the search box → toggle to "Smart search" → verify semantically related postings appear.

---

## Scenario 4 — Admin Sources Page (US4)

### Steps

```bash
# Non-admin access is forbidden
curl http://localhost:8000/api/admin/sources -H "Cookie: session=<student-session>"
# Expected: 403 FORBIDDEN

# Admin sees all sources
curl http://localhost:8000/api/admin/sources -H "Cookie: session=<admin-session>" | jq .

# Auto-pause after 3 failures (manual test)
# Set the source URL to an unreachable endpoint and run 3 times
# After 3rd failure: auto_paused=true in GET /api/admin/sources
```

**Frontend**: Navigate to `/admin/sources` as admin → verify source cards show last-run stats → click "Run now" → confirm run log updates.

---

## Scenario 5 — Manual Posting Entry

```bash
curl -X POST http://localhost:8000/api/postings \
  -H "Cookie: session=<user-session>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Firmware Co-op",
    "company": "StartupCo",
    "city": "Waterloo",
    "term": "Summer 2027",
    "deadline": "2027-03-15"
  }'
# Expected: 201 with posting object

# Try duplicate
curl -X POST http://localhost:8000/api/postings \
  -H "Cookie: session=<user-session>" \
  -H "Content-Type: application/json" \
  -d '{"title":"Firmware Co-op","company":"StartupCo","city":"Waterloo","term":"Summer 2027","deadline":"2027-03-15"}'
# Expected: 409 DUPLICATE
```

---

## Automated Test Commands

```bash
# Backend unit + integration tests (uses fixture responses, no live network)
docker compose exec api pytest -q -m "not perf"

# Frontend type check + tests
docker compose exec web npm run typecheck && npm test

# Ingestion-specific tests
docker compose exec api pytest -q backend/tests/ingest/
```
