# Tasks: Browse & Search Postings

**Input**: Design documents from `specs/001-browse-search-postings/`

**Prerequisites**: plan.md, spec.md, data-model.md, contracts/api.md, research.md, quickstart.md

**Tests**: Included — spec explicitly requires pytest (backend) and Vitest + Testing Library (frontend).

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US5)
- Exact file paths included in all descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Scaffold the full monorepo so both backend and frontend can be started and tested.

- [X] T001 Create `docker-compose.yml` with four services: `db` (postgres:16 + pgvector), `redis`, `api` (FastAPI), `web` (Vite); expose ports 5432, 6379, 8000, 5173; pass env vars from `.env`
- [X] T002 Create `backend/Dockerfile` (python:3.12-slim, install deps, run uvicorn)
- [X] T003 [P] Create `backend/pyproject.toml` with ruff, mypy (strict), pytest, pytest-asyncio config; list all backend dependencies (fastapi, pydantic[email], sqlalchemy[asyncio], asyncpg, alembic, httpx, pytest, pytest-asyncio, ruff, mypy)
- [X] T004 [P] Create `frontend/Dockerfile` (node:20-alpine, npm ci, vite build or dev server)
- [X] T005 [P] Create `frontend/package.json` with all frontend deps: react 18, vite 6, @tanstack/react-query v5, @tanstack/react-table v8, tailwindcss v3, react-router-dom v6, vitest, @testing-library/react, openapi-typescript; add scripts: dev, build, lint, typecheck, test, gen:api
- [X] T006 [P] Create `frontend/vite.config.ts`, `frontend/tailwind.config.ts`, `frontend/tsconfig.json`
- [X] T007 Create `.env.example` with: DATABASE_URL, REDIS_URL, VITE_API_URL, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
- [X] T008 [P] Create `.github/workflows/ci.yml` with two matrix jobs: backend (ruff check, mypy --strict app, pytest -q inside docker) and frontend (eslint, tsc --noEmit, vitest run)

**Checkpoint**: `docker compose up --build` starts all four services without errors.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core backend infrastructure — DB connection, ORM model, migration, seed data — that ALL user stories depend on.

**CRITICAL**: No user story work begins until this phase is complete.

- [X] T009 Create `backend/app/config.py` using pydantic-settings: reads DATABASE_URL, REDIS_URL, CORS_ORIGINS from env; singleton `get_settings()` function
- [X] T010 Create `backend/app/db.py`: async SQLAlchemy engine (`create_async_engine`), `AsyncSession` factory, `get_db` dependency, `Base` declarative base
- [X] T011 Create `backend/app/models/posting.py`: `WorkMode` str enum (onsite/hybrid/remote); `Posting` mapped class with all 14 columns per `data-model.md`; all 11 indexes; `CheckConstraint("duration_months IN (4,8,12,16)")`; `search_vector` as `TSVECTOR` mapped column (GENERATED ALWAYS AS stored expression wired in migration, not here)
- [X] T012 Create `backend/alembic.ini` and `backend/alembic/env.py` (async-compatible; reads DATABASE_URL from env; imports `Base.metadata` for autogenerate)
- [X] T013 Create `backend/alembic/versions/0001_create_postings.py`: `upgrade()` creates `work_mode_enum` type, `postings` table with all columns, `search_vector` GENERATED ALWAYS AS expression, all 11 indexes; `downgrade()` drops table then type
- [X] T014 Create `backend/seed/__init__.py`: ~60 `Posting` rows covering cities (Toronto, Mississauga, Waterloo, Kitchener, Guelph, Hamilton, Ottawa, Vancouver + some remote), terms (Winter 2027 x20, Summer 2027 x25, Fall 2027 x15), durations (mix of 4/8/12/16), work modes, skills from ~25-skill taxonomy (Python, Java, React, TypeScript, SQL, C++, Go, AWS, Docker, Kubernetes, Node.js, PostgreSQL, Django, FastAPI, Spring, .NET, Redis, Terraform, Figma, Machine Learning, Data Analysis, Tableau, Rust, Swift, Kotlin); deadlines mix of future and past; run via `python -m seed`

**Checkpoint**: `alembic upgrade head` succeeds; `python -m seed` inserts ~60 rows; `SELECT count(*) FROM postings;` returns 60.

---

## Phase 3: User Story 1 - Browse the Postings List (Priority: P1) MVP

**Goal**: Paginated list of active postings loads on the home page with columns title, company, city/province, work mode, term, duration, deadline, posted date. "Show expired" toggle. No search or filtering yet.

**Independent Test**: Open `http://localhost:5173`. A table of postings loads within 2 seconds. Pagination controls change rows. "Show expired" toggle reveals past-deadline postings.

### Backend — US1

- [X] T015 [P] [US1] Create `backend/app/schemas/posting.py`: `PostingListItem` (id, title, company, city, province, work_mode, term, duration_months, deadline, posted_at, is_active bool); `PostingsPage` = `Page[PostingListItem]` with items, total, page, page_size; `PostingListParams` (page: int = 1, page_size: Literal[10,25,50] = 25, show_expired: bool = False)
- [X] T016 [US1] Create `backend/app/services/postings.py`: `list_postings(params, db)` — SELECT postings with optional `deadline >= CURRENT_DATE` filter when `show_expired=False`; ORDER BY posted_at DESC; LIMIT/OFFSET; separate COUNT query; return `PostingsPage`
- [X] T017 [US1] Create `backend/app/api/postings.py`: thin FastAPI `APIRouter`; `GET /postings` reads `PostingListParams` via `Depends`, calls `list_postings`, returns `PostingsPage`
- [X] T018 [US1] Create `backend/app/main.py`: `create_app()` factory; CORS middleware (origins from settings); mount router at `/api`; lifespan event to test DB connection
- [X] T019 [US1] Create `backend/tests/conftest.py`: async test DB fixture using a separate test database; `async_session` fixture; `client` fixture using `httpx.AsyncClient` against the app
- [X] T020 [US1] Create `backend/tests/api/test_postings.py` (US1 cases): GET /api/postings returns 200 with `Page` shape; `total` equals seeded count; `page_size=10` returns 10 items; `show_expired=false` hides past-deadline rows; `show_expired=true` includes them; page beyond last page returns last valid page

### Frontend — US1

- [X] T021 [P] [US1] Create `frontend/src/main.tsx`: mount React app with `QueryClientProvider` (TanStack Query) and `BrowserRouter` (React Router)
- [X] T022 [P] [US1] Create `frontend/src/App.tsx`: define routes — `/` → `PostingsListPage`, `/postings/:id` → `PostingDetailPage`
- [X] T023 [US1] Create `frontend/src/api/postings.ts`: `usePostings(params)` hook — TanStack Query `useQuery`; fetches `GET /api/postings`; manual mode; typed with generated types (use inline types until T049 generates types.gen.ts)
- [X] T024 [US1] Create `frontend/src/pages/PostingsListPage.tsx`: owns `useSearchParams`; manages page/page_size/show_expired state from URL; renders `PostingsTable`; renders pagination controls (prev/next, page size selector); renders "Show expired" toggle
- [X] T025 [US1] Create `frontend/src/components/PostingsTable.tsx`: TanStack Table in `manualSorting`, `manualFiltering`, `manualPagination` mode; columns: title, company, city/province, work_mode, term, duration_months, deadline, posted_at; skeleton rows while loading (8 rows x shimmer); empty state "No postings match"; error state with "Try again" button; clicking a row navigates to `/postings/:id`
- [X] T026 [US1] Create `frontend/src/components/PostingCard.tsx`: card layout for mobile (`<md`); shows same fields as table row; keyboard accessible

**Checkpoint**: Home page loads paginated list; pagination and "Show expired" work; all US1 backend tests pass.

---

## Phase 4: User Story 2 - Search and Filter Postings (Priority: P2)

**Goal**: Keyword search box + filter bar (city, province, term, work mode, duration, skills). All filters combinable. Clear individually or all at once. Active filters visible as chips.

**Independent Test**: Type "Python" in search; only Python postings appear. Add "Remote" work mode; results narrow. Click "Clear all"; full list returns.

### Backend — US2

- [X] T027 [P] [US2] Extend `backend/app/schemas/posting.py`: add to `PostingListParams` — `q: str | None`, `city: str | None`, `province: str | None`, `term: str | None`, `work_mode: WorkMode | None`, `duration_months: list[int] | None`, `skills: list[str] | None`; add `FilterMeta` schema (cities, provinces, terms, skills as sorted lists of strings)
- [X] T028 [US2] Extend `backend/app/services/postings.py`: add keyword search with `search_vector @@ websearch_to_tsquery('english', q)` when `q` is provided; add city/province/term/work_mode filters as equality predicates; add duration_months as `IN (...)` when list provided; add skills as `skills @> ARRAY[...] :: TEXT[]` (AND logic per FR-004); add `get_filter_meta(db)` that returns distinct sorted values for FilterMeta
- [X] T029 [US2] Extend `backend/app/api/postings.py`: add `GET /postings/meta/filters` route; returns `FilterMeta`
- [X] T030 [US2] Extend `backend/tests/api/test_postings.py` (US2 cases): `q=Python` returns only Python postings; `skills=React&skills=TypeScript` (AND) returns only postings with both; `city=Waterloo` with remote posting still returns remote posting (FR-004a); unknown `sort` value → 422; `duration_months=4&duration_months=8` returns postings of either duration (OR logic)

### Frontend — US2

- [X] T031 [P] [US2] Create `frontend/src/components/SearchBox.tsx`: uncontrolled text input with 300 ms debounce; calls `onSearch(value)` after debounce; clears on "Clear all"; keyboard accessible with visible focus ring
- [X] T032 [US2] Create `frontend/src/components/FilterBar.tsx`: city dropdown, province dropdown, term dropdown (populated from FilterMeta), work_mode chip group (onsite/hybrid/remote), duration checkboxes (4/8/12/16 months), skills multi-select; shows each active filter as removable chip/badge; "Clear all" button removes everything; collapses to off-canvas panel at `<md`
- [X] T033 [P] [US2] Add `useFilterMeta()` hook to `frontend/src/api/postings.ts`: fetches `GET /api/postings/meta/filters` with TanStack Query; stale time 5 min
- [X] T034 [US2] Extend `frontend/src/pages/PostingsListPage.tsx`: integrate SearchBox + FilterBar; wire q/city/province/term/work_mode/duration/skills to URL params; pass all params to `usePostings`
- [X] T035 [US2] Create `frontend/tests/FilterBar.test.tsx`: renders city dropdown, province dropdown, term dropdown, work mode chips, duration checkboxes, skills multi-select; clicking "Clear all" resets all URL params; removing a chip removes just that filter

**Checkpoint**: Filter bar visible; keyword search narrows results; "Clear all" works; empty state shows when no results; all US2 backend tests pass.

---

## Phase 5: User Story 3 - Sort Postings (Priority: P3)

**Goal**: Clicking a column header (posted date, deadline, company, title) sorts the list. Second click reverses direction. Sort state in URL.

**Independent Test**: Click "Deadline" header; rows sort by deadline ascending. Click again; descending. Refresh; sort preserved via URL.

### Backend — US3

- [X] T036 [P] [US3] Extend `backend/app/schemas/posting.py`: add `sort: Literal['posted_at','deadline','company','title'] = 'posted_at'` and `order: Literal['asc','desc'] = 'desc'` to `PostingListParams`
- [X] T037 [US3] Extend `backend/app/services/postings.py`: add `SORT_MAP = {'posted_at': Posting.posted_at, 'deadline': Posting.deadline, 'company': Posting.company, 'title': Posting.title}`; apply `ORDER BY SORT_MAP[sort] ASC|DESC`; unknown sort value already produces 422 via `Literal` at Pydantic layer
- [X] T038 [US3] Extend `backend/tests/api/test_postings.py` (US3 cases): `sort=deadline&order=asc` returns rows in ascending deadline order; `sort=posted_at&order=desc` is the default; `sort=invalid` → 422

### Frontend — US3

- [X] T039 [US3] Extend `frontend/src/components/PostingsTable.tsx`: sortable column headers on posted_at, deadline, company, title; clicking header sets `sort` and `order` URL params; shows sort direction indicator (arrow); second click toggles `order` between asc/desc
- [X] T040 [US3] Create `frontend/tests/PostingsTable.test.tsx`: renders column headers; clicking "Deadline" header sets `sort=deadline` URL param; second click changes `order` to desc; refresh preserves sort from URL

**Checkpoint**: All four columns sortable; sort state in URL; all US3 backend tests pass.

---

## Phase 6: User Story 4 - View Posting Detail (Priority: P4)

**Goal**: Clicking a row opens a full detail page with description, skills list, and link to original posting. Browser back returns to same list state.

**Independent Test**: Click any row; detail page shows title, company, full description, skills, and source link in new tab. Back button returns to filtered/sorted list.

### Backend — US4

- [X] T041 [P] [US4] Add `PostingDetail` schema to `backend/app/schemas/posting.py`: all `PostingListItem` fields plus `description: str`, `skills: list[str]`, `source_url: str | None`
- [X] T042 [US4] Add `get_posting(id: UUID, db)` to `backend/app/services/postings.py`: SELECT by id; raise `HTTPException(404, detail="Posting not found", code="POSTING_NOT_FOUND")` if missing
- [X] T043 [US4] Add `GET /postings/{id}` to `backend/app/api/postings.py`: route MUST be declared before `GET /postings/meta/filters` to avoid path conflict; returns `PostingDetail`
- [X] T044 [US4] Extend `backend/tests/api/test_postings.py` (US4 cases): GET /api/postings/{id} returns 200 with full PostingDetail including description and skills; GET with unknown UUID returns 404

### Frontend — US4

- [X] T045 [P] [US4] Add `usePosting(id)` hook to `frontend/src/api/postings.ts`: TanStack Query `useQuery`; fetches `GET /api/postings/:id`
- [X] T046 [US4] Create `frontend/src/pages/PostingDetailPage.tsx`: displays title, company, city/province, work_mode, term, duration_months, deadline, posted_at, full description, skills as tag list, conditional "View original posting" link (opens new tab, hidden if source_url is null); skeleton while loading; error state with back link; keyboard accessible

**Checkpoint**: Clicking a row navigates to detail page; all detail fields shown; source link opens new tab; back returns to list; all US4 backend tests pass.

---

## Phase 7: User Story 5 - Shareable / Bookmarkable Views (Priority: P5)

**Goal**: Every combination of search, filters, sort, page, and page_size is encoded in the URL. Pasting the URL in another browser reproduces the exact view.

**Independent Test**: Apply keyword + two filters + sort + page 2. Copy URL. Paste in incognito. Identical state loads.

- [X] T047 [US5] Audit `frontend/src/pages/PostingsListPage.tsx`: verify ALL state (q, city, province, term, work_mode, duration_months, skills, sort, order, page, page_size, show_expired) is read from and written to `useSearchParams`; no state lives only in React state; ensure `usePostings` is called only after URL params are parsed on first render (no flash of unfiltered data)
- [X] T048 [US5] Extend `frontend/tests/PostingsTable.test.tsx`: write URL round-trip test — render PostingsListPage with a pre-set URL containing all params; assert `usePostings` is called with the correct params derived from URL; assert that navigating to the page with the copied URL produces the same query

**Checkpoint**: Copy URL with active state; paste in new tab; identical results load.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Performance validation, type generation, CI readiness, documentation.

- [X] T049 [P] Run `npm run gen:api` (openapi-typescript v7) to generate `frontend/src/api/types.gen.ts` from FastAPI's `/openapi.json`; update all hooks in `frontend/src/api/postings.ts` to use generated types instead of inline types; add `gen:api` to CI frontend job
- [X] T050 [P] Create `backend/tests/perf/test_perf.py` (mark with `pytest.mark.perf`): insert 10,000 postings via bulk insert; fire 50 concurrent `GET /api/postings?q=python&city=Waterloo` requests using `httpx.AsyncClient`; assert p95 latency ≤ 300 ms; assert total count is correct
- [X] T051 [P] Verify mobile layout: open DevTools at 375 px width; confirm table is replaced by `PostingCard` list; confirm `FilterBar` collapses to off-canvas/drawer panel; fix any overflow or overlap issues
- [X] T052 Verify accessibility: tab through all interactive elements in PostingsListPage and PostingDetailPage; confirm visible focus ring on every control; confirm all form controls have accessible labels; confirm color contrast meets WCAG AA (use browser a11y audit tool)
- [X] T053 Create `docs/agentic-workflow.md` with initial entry for Feature 001 (what Claude Code built, what was reviewed, tests added and results)
- [X] T054 Run full test suite: `docker compose exec api pytest -q` (all backend tests including perf); `npm run test` (vitest run); confirm CI green locally before push

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately; T002–T008 all parallelizable
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories; T009–T014 must run in order (config → db → model → alembic → migration → seed)
- **Phase 3–7 (User Stories)**: All depend on Phase 2 completion; US1 must precede US2/US3 (extends same service/schema); US4 depends on US1 backend
- **Phase 8 (Polish)**: Depends on all user stories complete

### User Story Dependencies

| Story | Depends On | Can Parallelize Backend/Frontend? |
|-------|------------|-----------------------------------|
| US1 | Phase 2 | Yes — T015–T018 (BE) parallel with T021–T022 (FE) after T019 done |
| US2 | US1 backend endpoints live | Yes — T027–T030 (BE) parallel with T031–T034 (FE) |
| US3 | US1 backend (extends schemas/service) | Yes — T036–T037 (BE) parallel with T039 (FE) |
| US4 | US1 backend (extends router) | Yes — T041–T043 (BE) parallel with T045–T046 (FE) |
| US5 | US1–US4 frontend complete | No parallelism needed — audit only |

### Within Each User Story

- Backend schemas → services → router (sequential)
- Frontend hooks → pages → components (sequential within story)
- Backend and frontend implementation can run in parallel once schemas are stable

---

## Parallel Opportunities by Phase

```bash
# Phase 1 — all parallel after T001:
T002, T003, T004, T005, T006, T007, T008

# Phase 3 — backend and frontend in parallel after T019 (conftest):
Backend: T015, T016, T017, T018 (then T019, T020)
Frontend: T021, T022 (then T023, T024, T025, T026)

# Phase 4 — backend and frontend in parallel after T027:
Backend: T028, T029, T030
Frontend: T031, T032, T033, T034, T035

# Phase 5 — parallel:
Backend: T036, T037, T038
Frontend: T039, T040
```

---

## Implementation Strategy

### MVP (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP & VALIDATE**: Table loads, pagination works, "Show expired" works
5. Demo: `docker compose up --build` → open `http://localhost:5173`

### Incremental Delivery

1. Phase 1 + 2 → Foundation
2. Phase 3 (US1) → MVP: working table
3. Phase 4 (US2) → Search & Filter
4. Phase 5 (US3) → Sortable columns
5. Phase 6 (US4) → Detail page
6. Phase 7 (US5) → URL state audit
7. Phase 8 → Perf test + CI green + docs

---

## Task Count Summary

| Phase | Tasks | MVP? |
|-------|-------|------|
| Phase 1: Setup | T001–T008 (8) | Required |
| Phase 2: Foundational | T009–T014 (6) | Required |
| Phase 3: US1 Browse | T015–T026 (12) | MVP |
| Phase 4: US2 Search/Filter | T027–T035 (9) | |
| Phase 5: US3 Sort | T036–T040 (5) | |
| Phase 6: US4 Detail | T041–T046 (6) | |
| Phase 7: US5 URL State | T047–T048 (2) | |
| Phase 8: Polish | T049–T054 (6) | |
| **Total** | **54** | |

> 2026-10-11: T049 types generated from OpenAPI (`frontend/src/api/types.gen.ts`, drift-checked in CI); T051/T052 verified in Edge via Playwright (375 px no overflow, cards + filter drawer; axe WCAG AA clean, focus rings everywhere); T054 backend 235 passed incl. perf, frontend 29 passed.
