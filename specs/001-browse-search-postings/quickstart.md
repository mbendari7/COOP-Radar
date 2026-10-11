# Quickstart: Browse & Search Postings

**Feature**: `001-browse-search-postings` | **Date**: 2026-10-09

This guide validates that the feature works end-to-end. Run these steps after the initial
implementation is complete.

---

## Prerequisites

- Docker Desktop running
- `docker compose` v2 available
- `node` ≥ 20, `npm` ≥ 10
- `python` 3.12 (for type-check outside Docker if needed)

---

## 1. Start the stack

```bash
docker compose up --build -d
```

Expected: four containers running — `db` (postgres:16), `redis`, `api` (FastAPI on :8000), `web` (Vite on :5173).

---

## 2. Apply migrations and seed

```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m seed
```

Expected: `alembic upgrade head` prints `Running upgrade ... -> <rev>`. The seed script prints
`Seeded 60 postings.`

---

## 3. Verify backend

```bash
# List postings (first page)
curl -s "http://localhost:8000/api/postings" | python3 -m json.tool | head -40
```

Expected: JSON with `"total": 60` (approximate), `"items"` array of 25 postings, each with
`id`, `title`, `company`, `city`, `province`, `work_mode`, `term`, `duration_months`,
`deadline`, `posted_at`, `skills`.

```bash
# Keyword search
curl -s "http://localhost:8000/api/postings?q=python" | python3 -m json.tool | grep '"title"'
```

Expected: Only titles/postings relevant to Python appear.

```bash
# Skills AND filter
curl -s "http://localhost:8000/api/postings?skills=React&skills=TypeScript" | python3 -m json.tool | grep '"skills"'
```

Expected: Every `"skills"` array contains both `"React"` and `"TypeScript"`.

```bash
# Sort by deadline ascending
curl -s "http://localhost:8000/api/postings?sort=deadline&order=asc" | python3 -m json.tool | grep '"deadline"'
```

Expected: Deadline dates are in ascending order.

```bash
# Show expired toggle
curl -s "http://localhost:8000/api/postings?show_expired=true" | python3 -m json.tool | grep '"total"'
```

Expected: `total` ≥ 60 (includes expired seed postings if any were seeded with past deadlines).

```bash
# Filter metadata
curl -s "http://localhost:8000/api/postings/meta/filters" | python3 -m json.tool
```

Expected: Object with `cities`, `provinces`, `terms`, `skills` arrays populated.

```bash
# Posting detail
FIRST_ID=$(curl -s "http://localhost:8000/api/postings" | python3 -c "import sys,json; print(json.load(sys.stdin)['items'][0]['id'])")
curl -s "http://localhost:8000/api/postings/$FIRST_ID" | python3 -m json.tool | grep '"description"'
```

Expected: `"description"` field present with non-empty text.

---

## 4. Verify frontend

Open `http://localhost:5173` in a browser.

| Scenario | Steps | Expected |
|----------|-------|----------|
| Browse | Page loads | Table shows postings with all columns; "Show expired" toggle is off |
| Search | Type "python" in search box | List narrows to Python-related postings |
| Filter city | Select "Waterloo" | Only Waterloo (and remote) postings shown |
| Filter skills | Select "React" and "TypeScript" | Only postings with both skills shown |
| Clear all | Click "Clear all" | Full list returns |
| Sort | Click "Deadline" header | Rows re-sort; clicking again reverses |
| Page size | Select "50" | Up to 50 rows shown |
| URL state | Apply filters + sort, copy URL, open in incognito | Same state reproduced |
| Detail | Click any row | Detail view shows description + skills + "Original posting" link |
| Back button | Navigate to detail, press Back | Returns to same filtered list |
| Mobile | Resize to 375 px | Table collapses to cards; filters accessible |
| Error state | Stop the `api` container, reload | Error state with "Try again" button shown |

---

## 5. Run automated tests

```bash
# Backend tests
docker compose exec api pytest -q

# Frontend tests
docker compose exec web npm run test -- --run

# Performance test (requires seeded 10k postings)
docker compose exec api pytest -q -m perf
```

Expected:
- Backend: all tests pass, no warnings.
- Frontend: all tests pass.
- Performance: `p95 <= 300ms` assertion passes.

---

## 6. Generate frontend types

```bash
docker compose exec web npm run gen:api
```

Expected: `src/api/types.gen.ts` is regenerated. Running `tsc --noEmit` afterwards produces no errors.
