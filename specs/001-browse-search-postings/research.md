# Research: Browse & Search Postings

**Feature**: `001-browse-search-postings` | **Date**: 2026-10-09

---

## Decision 1: Keyword Search Backend — tsvector vs. Elasticsearch vs. LIKE

**Decision**: PostgreSQL `tsvector` + GIN index via a generated column.

**Rationale**: At 10,000 postings, PostgreSQL full-text search delivers well under 300 ms p95
on a B2/t3.small class instance with zero additional infrastructure. The GIN index on
`search_vector` makes ranked lookups (`ts_rank`) efficient. The `websearch_to_tsquery` function
handles prefix matching and AND/OR operators without custom parsing. Elasticsearch would add
operational complexity for no gain at this scale.

**Alternatives considered**:
- `ILIKE '%term%'` — no index support, full table scan; rejected.
- Elasticsearch — justified only above ~1M docs or when multi-index federation needed; rejected.
- Typesense — lighter than ES but an extra service; rejected (constitution: no dep without reason).

---

## Decision 2: Skills Storage — text[] vs. Join Table vs. JSONB

**Decision**: `TEXT[]` column with a GIN index on the `postings` table.

**Rationale**: Skills are read-heavy and always fetched with the posting. A GIN index on
`TEXT[]` supports `&&` (overlap) and `@>` (contains-all) operators natively in PostgreSQL.
The contains-all (`@>`) operator directly implements the AND-logic multi-skill filter from
FR-004. A join table would require an extra JOIN on every list query and complicate pagination
counts. Skills are not first-class entities in this feature (no CRUD).

**Alternatives considered**:
- Normalised `skills` + `posting_skills` join table — more flexible, heavier queries; deferred to Feature 003 if a skill taxonomy is needed.
- JSONB — slightly more expressive but `TEXT[]` is simpler and equally indexed.

---

## Decision 3: Duration Filter Shape — Fixed Checkboxes vs. Range Slider

**Decision**: Fixed checkboxes for 4, 8, 12, and 16 months; multiple selections are OR'd.

**Rationale**: Canadian co-op programs standardise on 4-month terms (4, 8, 12, or 16 months
for 1–4 terms). Discrete checkboxes are faster to interact with than a range slider and
simpler to encode in the URL (`duration=4,8`). OR-logic for duration is correct because a
student looking for "4 or 8 month" roles wants either, not positions that are simultaneously 4
AND 8 months long.

**Alternatives considered**:
- Min/max range slider — appropriate when values are continuous; rejected (4 discrete values).
- Single dropdown — prevents multi-select; rejected.

---

## Decision 4: API Type Generation — openapi-typescript vs. manual types

**Decision**: `openapi-typescript` (CLI) generates `src/api/types.gen.ts` from FastAPI's
`/openapi.json` endpoint at build time (`npm run gen:api`).

**Rationale**: FastAPI auto-generates a fully typed OpenAPI 3.1 schema from Pydantic models.
`openapi-typescript` (v7) is the industry-standard codegen tool for this purpose — zero runtime
overhead, no class-instance wrapping, pure type output. This satisfies the frontend-tables skill
requirement: "never hand-write response types."

**Alternatives considered**:
- `openapi-typescript-codegen` — older package, generates classes; rejected (types only preferred).
- Manual types — violates frontend-tables skill; rejected.

---

## Decision 5: URL State Management — React Router searchParams vs. custom hook

**Decision**: React Router v6 `useSearchParams` hook wrapping all filter/sort/page state.

**Rationale**: React Router v6 is the standard routing library for React + Vite. `useSearchParams`
provides a stable API to read/write query parameters that survives refresh and is shareable by
copy-pasting the URL. The frontend-tables skill specifies "URL query string" for all state; this
is the canonical way to implement it.

**Alternatives considered**:
- Zustand/Redux for state + manual URL sync — more moving parts; rejected.
- Native `window.location.search` — bypasses React Router; rejected.

---

## Decision 6: Performance Budget Validation — how to test 300 ms p95 at 10,000 rows

**Decision**: A Python script `backend/tests/perf/test_perf.py` generates 10,000 postings via
SQLAlchemy `bulk_insert_mappings`, then fires 50 concurrent requests to `GET /api/postings`
using `httpx.AsyncClient`, records p50/p95/p99 latencies, and asserts p95 ≤ 300 ms. Runs in CI
against the Docker Compose stack (`pytest -m perf`).

**Rationale**: Reproduces real-world load without an external tool. httpx async allows 50 parallel
requests, which is representative of a small demo environment. The test is deterministic because
the seed data is fixed.

**Alternatives considered**:
- k6 / Locust — correct tools for sustained load testing but require extra install and CI setup; deferred to Feature 005 (Deploy & Observability).
- Single-request timing — does not capture p95; rejected.

---

## Decision 7: Monorepo Layout — top-level backend/ + frontend/ vs. single src/

**Decision**: Web-app option from the plan template: `backend/` + `frontend/` at repo root,
orchestrated by `docker-compose.yml`.

**Rationale**: Backend (Python/FastAPI) and frontend (TypeScript/React) have different toolchains,
dependency managers, and Docker images. Separating them at the top level is the standard
full-stack monorepo layout and makes CI matrix jobs straightforward.

---

## Resolved NEEDS CLARIFICATION

All items from Technical Context were fully specified in the user input. No NEEDS CLARIFICATION
markers remain.
