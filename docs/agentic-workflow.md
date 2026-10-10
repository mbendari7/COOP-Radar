# Agentic Workflow Log

---

## 2026-10-10 — Feature 001: Browse & Search Postings (full implementation)

**Branch**: `001-browse-search-postings`

**What Claude Code built**:
- All 8 Phase 1 setup files: docker-compose.yml, backend Dockerfile + pyproject.toml, frontend Dockerfile + package.json + vite/tailwind/tsconfig, .env.example, GitHub Actions CI workflow
- All 6 Phase 2 foundational files: config.py (pydantic-settings), db.py (async SQLAlchemy engine + session factory), posting.py model (WorkMode enum, 11 indexes, search_vector), alembic.ini + env.py (async-compatible), migration 0001_create_postings.py (work_mode_enum, GENERATED search_vector, all indexes, round-trip downgrade), seed/__init__.py (~62 realistic postings across 8 cities, 3 terms, mixed durations/work modes/deadlines)
- All backend US1–US4 files: schemas/posting.py (PostingListItem, PostingDetail, PostingsPage, FilterMeta, PostingListParams), services/postings.py (list_postings, get_posting, get_filter_meta — all SQL, no Python-side filtering), api/postings.py (thin router, route order puts /meta/filters before /{id}), main.py (app factory, CORS, lifespan DB check)
- All frontend files: main.tsx (QueryClientProvider + BrowserRouter), App.tsx (routes), api/postings.ts (usePostings, usePosting, useFilterMeta, typed params), utils/format.ts, SearchBox.tsx (300ms debounce), FilterBar.tsx (all filter controls, chips, clear-all, mobile collapse), PostingsTable.tsx (TanStack Table manual mode, sort indicators, skeleton, empty/error states, keyboard nav), PostingCard.tsx (mobile layout), PostingsListPage.tsx (owns all URL state via useSearchParams), PostingDetailPage.tsx (full detail, conditional source link)
- Test files: tests/conftest.py (rolled-back sessions), tests/api/test_postings.py (16 tests covering US1–US4 and filter meta), tests/perf/test_perf.py (10k row p95 assertion), frontend tests/setup.ts, tests/PostingsTable.test.tsx, tests/FilterBar.test.tsx
- docs/agentic-workflow.md (this file)

**What I reviewed / changed**:
- Not yet reviewed — pending first local run

**Tests added**:
- Backend: 16 pytest cases (list shape, show_expired, page_size, keyword search, skills AND logic, city+remote FR-004a, duration OR logic, sort asc/desc, invalid sort 422, invalid page_size 422, detail full fields, 404 for unknown ID, filter meta distinct/sorted values)
- Frontend: PostingsTable (empty state, error+retry, renders rows, sort click, sort toggle), FilterBar (renders controls, chips, clear-all, chip removal)
- Perf: 50 concurrent requests at 10k rows, p95 ≤ 300ms

**Next step**: `docker compose up --build && docker compose exec api alembic upgrade head && docker compose exec api python -m seed` then open http://localhost:5173
