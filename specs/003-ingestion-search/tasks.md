# Tasks: Real Postings Ingestion & Semantic Search

**Input**: Design documents from `/specs/003-ingestion-search/`

**Prerequisites**: plan.md ✓ spec.md ✓ research.md ✓ data-model.md ✓ contracts/api.md ✓

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add new dependencies and wire up shared infrastructure.

- [x] T001 Add `rq>=1.16`, `rq-scheduler>=0.13`, `openai>=1.30`, `pgvector>=0.3`, `python-multipart>=0.0.9`, `feedparser>=6.0` to `[project.dependencies]` in `backend/pyproject.toml`; add `respx>=0.21` to `[project.optional-dependencies] dev`
- [x] T002 [P] Add `worker` service to `docker-compose.yml`: `image: coopradar-api`, `command: rq worker --url redis://redis:6379 ingest`, depends on `redis` and `db`; add `EMBED_MODEL` and `OPENAI_API_KEY` to env vars block
- [x] T003 [P] Create `backend/tests/fixtures/ingest/` directory with a `.gitkeep` placeholder (fixture files added in later tasks)
- [x] T004 [P] Create `backend/app/ingest/__init__.py` — empty package marker

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: ORM models, migration, base adapter ABC, and admin dependency — must complete before any user story.

⚠️ CRITICAL: No user story work can begin until this phase is complete.

- [x] T005 Create `backend/app/models/ingest_source.py` — `IngestSource` mapped class: `id UUID PK default gen_random_uuid()`, `name TEXT NOT NULL`, `adapter_type TEXT NOT NULL CHECK IN ('json_api','rss','csv','manual')`, `config JSONB NOT NULL default '{}'`, `enabled BOOLEAN NOT NULL default TRUE`, `auto_paused BOOLEAN NOT NULL default FALSE`, `consecutive_failures INTEGER NOT NULL default 0`, `last_run_at TIMESTAMPTZ nullable`, `created_at TIMESTAMPTZ server_default NOW()`; `runs` relationship back_populates; import into `backend/app/models/__init__.py`
- [x] T006 [P] Create `backend/app/models/ingest_run.py` — `IngestRun` mapped class: `id UUID PK`, `source_id UUID FK→ingest_sources.id ON DELETE CASCADE NOT NULL`, `started_at TIMESTAMPTZ NOT NULL`, `finished_at TIMESTAMPTZ nullable`, `status TEXT NOT NULL CHECK IN ('running','success','partial','failed')`, `added/updated/closed/errors INTEGER NOT NULL default 0`, `error_log ARRAY(Text) NOT NULL default '{}'`; `source` relationship; import into `backend/app/models/__init__.py`
- [x] T007 [P] Create `backend/app/models/skill.py` — `Skill` mapped class: `id UUID PK`, `name TEXT UNIQUE NOT NULL`, `aliases ARRAY(Text) NOT NULL default '{}'`, `category TEXT nullable`, `created_at TIMESTAMPTZ server_default NOW()`; import into `backend/app/models/__init__.py`
- [x] T008 [P] Create `backend/app/models/posting_embedding.py` — `PostingEmbedding` mapped class: `posting_id UUID PK FK→postings.id ON DELETE CASCADE`, `embedding Vector(1536) NOT NULL` (from `pgvector.sqlalchemy`), `model TEXT NOT NULL`, `generated_at TIMESTAMPTZ server_default NOW()`; import into `backend/app/models/__init__.py`
- [x] T009 Create `backend/alembic/versions/0004_add_ingestion.py` — upgrade: (1) enable pgvector extension `CREATE EXTENSION IF NOT EXISTS vector`, enable fuzzystrmatch `CREATE EXTENSION IF NOT EXISTS fuzzystrmatch`; (2) add `is_admin BOOLEAN NOT NULL DEFAULT FALSE` to `users`; (3) add `source_id UUID FK→ingest_sources.id SET NULL nullable`, `source_ref TEXT nullable`, `closed_at TIMESTAMPTZ nullable`, `low_confidence_fields JSONB NOT NULL DEFAULT '{}'` to `postings`; (4) create `skills`, `ingest_sources`, `ingest_runs`, `posting_embeddings` tables with all indexes from data-model.md; (5) HNSW index on `posting_embeddings.embedding` using `vector_cosine_ops` with `m=16, ef_construction=64`; downgrade drops all in reverse
- [x] T010 [P] Create `backend/app/ingest/base.py` — `RawPosting` dataclass: `title str`, `company str`, `city str`, `work_mode str | None`, `term str`, `deadline date | None`, `description str | None`, `skills list[str]`, `source_ref str | None`, `source_url str | None`; `BaseAdapter` ABC with `async def fetch(self, source: IngestSource) -> list[RawPosting]` abstract method and `user_agent` class attribute
- [x] T011 [P] Update `backend/app/deps.py` — add `get_admin_user(current_user: User = Depends(get_current_user)) -> User`: checks `current_user.is_admin`, raises `HTTP 403 {"detail":"Forbidden","code":"FORBIDDEN"}` if false; returns user if admin

**Checkpoint**: Models, migration, and base adapter ready — user story implementation can now begin.

---

## Phase 3: User Story 1 — Scheduled Ingestion from Public Sources (Priority: P1) 🎯 MVP

**Goal**: Postings imported automatically every 6 hours via JSON API and RSS adapters; runs recorded in ingest_runs.

**Independent Test**: Trigger a run with a fixture-backed source; confirm 5 postings added; re-run same fixtures, confirm 0 added; remove one posting from fixture, re-run, confirm closed_at set on that posting.

### Implementation

- [x] T012 [US1] Create `backend/app/ingest/json_api.py` — `JsonApiAdapter(BaseAdapter)`: `async def fetch(source)` uses `httpx.AsyncClient(timeout=30.0, headers={"User-Agent": self.user_agent})` with `httpx_retry` (max_retries=3, backoff_factor=0.5); maps response fields via `source.config["field_map"]` to `RawPosting`; raises `AdapterError` on non-200 responses
- [x] T013 [P] [US1] Create `backend/app/ingest/rss.py` — `RssAdapter(BaseAdapter)`: `async def fetch(source)` wraps `feedparser.parse(source.config["url"])` in `asyncio.to_thread`; extracts title, link (source_url), author (company), published (deadline), summary (description) from feed entries; returns `list[RawPosting]`
- [x] T014 [P] [US1] Create `backend/app/ingest/registry.py` — `adapter_for(source: IngestSource) -> BaseAdapter` factory: maps `"json_api" → JsonApiAdapter`, `"rss" → RssAdapter`; raises `ValueError` for unknown adapter_type
- [x] T015 [US1] Create `backend/app/ingest/dedup.py` — `async def duplicate_exists(db, company, title, city) -> bool`: query `SELECT 1 FROM postings WHERE company = :company AND city = :city AND (1 - levenshtein(title, :title)::float / GREATEST(length(title), length(:title))) > 0.85 LIMIT 1` using `op.func.levenshtein`; requires fuzzystrmatch extension (enabled in 0004)
- [x] T016 [US1] Create `backend/app/ingest/runner.py` — `async def run_source(source_id: UUID)`: opens DB session; loads `IngestSource`; creates `IngestRun(status='running')`; calls `adapter.fetch(source)`; for each `RawPosting`: call `duplicate_exists` → skip if duplicate, upsert otherwise (counts added/updated); find postings with `source_id` and `source_ref NOT IN` current batch → set `closed_at=NOW()` (counts closed); on any exception: log to `error_log`, set `status='partial'` or `'failed'`; update `source.consecutive_failures` and `auto_paused` per FR-015 (auto_paused=True after 3 failures); commit `IngestRun(finished_at=NOW(), status='success')`
- [x] T017 [US1] Create `backend/app/worker.py` — `create_queue()` returning `rq.Queue('ingest', connection=redis_sync_conn)`; `schedule_sources()` using `rq_scheduler.Scheduler` to enqueue `run_source` for each enabled non-paused source every 6 hours; `if __name__ == '__main__': rq.Worker([queue]).work()`
- [x] T018 [US1] Create `backend/tests/fixtures/ingest/acme_jobs.json` — JSON array with 5 sample postings (title, company, city, term, deadline, description, skills); field names match JsonApiAdapter default field_map
- [x] T019 [P] [US1] Create `backend/tests/fixtures/ingest/shopify_rss.xml` — valid Atom/RSS feed with 3 `<entry>` elements containing title, author, link, published, summary
- [x] T020 [US1] Create `backend/tests/ingest/test_json_api_adapter.py` — use `respx.mock` to intercept httpx: happy path (5 RawPostings returned matching fixture), HTTP 500 from source raises `AdapterError`, empty array response returns `[]`
- [x] T021 [P] [US1] Create `backend/tests/ingest/test_dedup.py` — exact match rejected; near-duplicate title (Levenshtein similarity 0.90) rejected; different city not duplicate; different company not duplicate
- [x] T022 [P] [US1] Create `backend/tests/ingest/test_runner.py` — using fixture-backed adapter mock: first run adds 5; second run (same data) adds 0, updates 0; run with one posting removed → `closed_at` set; adapter HTTP error → IngestRun status='failed', consecutive_failures incremented; 3rd consecutive failure → auto_paused=True

**Checkpoint**: Ingestion pipeline runs, deduplicates, closes stale postings, and handles errors. Run log recorded.

---

## Phase 4: User Story 2 — CSV Upload and Manual Entry (Priority: P2)

**Goal**: Authenticated students can bulk-import postings from a CSV and add single postings via form.

**Independent Test**: Upload sample_postings.csv (5 rows) → 5 added; upload again → 5 skipped; upload with error row → 4 added + 1 error; upload oversized file → 413; add manual posting → 201; duplicate manual → 409.

### Implementation

- [x] T023 [US2] Create `backend/app/ingest/csv_validator.py` — `RowError(row: int, column: str, message: str)` dataclass; `validate_csv_row(row: dict, row_num: int) -> list[RowError]`: checks required columns title/company/city/term/deadline present and non-empty; validates deadline is parseable as YYYY-MM-DD date; validates `work_mode` if present is one of onsite/hybrid/remote; `CsvUploadResult(added: int, skipped_duplicates: int, errors: list[RowError])`
- [x] T024 [P] [US2] Update `backend/app/services/postings.py` — add `upload_csv(db, user_id, file_bytes) -> CsvUploadResult`: read file_bytes with pandas `pd.read_csv(io.BytesIO(file_bytes))`; reject if rows > 1,000 (FR-008); validate each row; dedup check; batch insert valid non-duplicate rows with source_id=None; return CsvUploadResult
- [x] T025 [P] [US2] Update `backend/app/services/postings.py` — add `create_manual(db, user_id, data: ManualPostingIn) -> Posting`: validate required fields; call `duplicate_exists`; if duplicate raise HTTP 409; insert posting with source_id=None; return new Posting
- [x] T026 [P] [US2] Update `backend/app/schemas/posting.py` — add `ManualPostingIn(title: str, company: str, city: str, term: str, deadline: date, province: str | None, work_mode: WorkMode | None, duration_months: int | None, description: str | None, skills: list[str] = [], source_url: str | None)`; add `RowError(row: int, column: str, message: str)`; add `CsvUploadResult(added: int, skipped_duplicates: int, errors: list[RowError])`
- [x] T027 [US2] Update `backend/app/api/postings.py` — add `POST /api/postings/upload`: `UploadFile = File(...)`, multipart/form-data; read file bytes; rate-limit check (3/hour via Redis INCR key `csv_upload:{user_id}` with 1-hour TTL); call `upload_csv` service; return `CsvUploadResult`; raises 413 if pandas detects > 1000 rows; raises 400 if CSV unparseable; raises 429 if rate limited; add `POST /api/postings`: body `ManualPostingIn`; calls `create_manual`; returns 201 `PostingListItem`
- [x] T028 [US2] Create `backend/tests/fixtures/ingest/sample_postings.csv` — 5 valid rows with title, company, city, term, deadline (YYYY-MM-DD), work_mode, skills
- [x] T029 [P] [US2] Create `backend/tests/fixtures/ingest/sample_postings_with_error.csv` — 5 rows where row 3 has an invalid deadline format
- [x] T030 [US2] Create `backend/tests/ingest/test_csv_upload.py` — test_valid_csv (5 added, 0 errors); test_csv_with_error_row (4 added, 1 error with row=3 and column="deadline"); test_duplicate_csv (0 added, 5 skipped); test_oversized_csv (413 FILE_TOO_LARGE); test_rate_limit (4th upload in 1 hour returns 429 RATE_LIMITED); test_manual_entry_201; test_manual_duplicate_409
- [x] T031 [P] [US2] Create `frontend/src/components/CsvUploadForm.tsx` — file input (accept=".csv"), upload button, progress spinner during mutation, result summary (added/skipped counts), per-row error table (row number, column, message); uses `POST /api/postings/upload`
- [x] T032 [P] [US2] Create `frontend/src/components/ManualPostingForm.tsx` — form with required fields (title, company, city, term, deadline) and optional fields (province, work_mode, duration_months, description, skills comma-separated, source_url); inline validation with accessible error messages; on submit calls `POST /api/postings`; shows success toast or duplicate error
- [x] T033 [P] [US2] Update `frontend/src/App.tsx` — add `/upload` (CsvUploadForm) and `/submit` (ManualPostingForm) routes behind authenticated guard

**Checkpoint**: CSV upload and manual entry both work; duplicates detected; per-row errors shown; rate limiting enforced.

---

## Phase 5: User Story 3 — Semantic ("Smart") Search (Priority: P3)

**Goal**: Search mode toggle switches between keyword (tsvector) and semantic (cosine similarity) ranking; detail page shows 5 similar postings.

**Independent Test**: Index 50 seeded postings with embeddings. Query "embedded firmware" in semantic mode; confirm results include microcontroller postings. Open detail page; confirm similar postings sidebar shows ≤ 5 entries, none being the current posting.

### Implementation

- [x] T034 [US3] Create `backend/app/ingest/extract.py` — `ExtractedFields(city: str | None, work_mode: str | None, term: str | None, duration_months: int | None, skills: list[str], confidence_map: dict[str, float])`; `async def extract_fields(db, text: str) -> ExtractedFields`: (1) load skill taxonomy from DB `SELECT name, aliases FROM skills`; (2) regex/keyword match against name + aliases → confidence = matched_fields/total_fields; (3) if confidence < 0.6: call Anthropic claude-haiku-4-5 with prompt `"Extract: city, work_mode, term, duration_months, skills (from list: {taxonomy}) as JSON from: {text}"`, parse JSON response; (4) return `ExtractedFields`
- [x] T035 [P] [US3] Create `backend/app/ingest/embed.py` — `async def generate_embedding(text: str) -> list[float]`: call `openai.AsyncOpenAI().embeddings.create(model=os.getenv("EMBED_MODEL","text-embedding-3-small"), input=text)`; return `embedding.data[0].embedding`; `async def store_embedding(db, posting_id, embedding)`: upsert into `posting_embeddings`; `async def enqueue_embed_job(posting_id)`: push `store_embedding` job to RQ queue
- [x] T036 [US3] Update `backend/app/services/postings.py` — add `search_mode: Literal['keyword','semantic'] = 'keyword'` parameter to `list_postings`; when `search_mode='semantic'` and `q` provided: call `generate_embedding(q)` to get query vector, order by `PostingEmbedding.embedding <=> query_vec` (require JOIN on posting_embeddings); when `search_mode='keyword'`: existing tsvector rank unchanged
- [x] T037 [P] [US3] Update `backend/app/services/postings.py` — add `async def similar_postings(db, posting_id: UUID, limit: int = 5) -> list[PostingListItem]`: fetch target embedding from `posting_embeddings`; if not found return `[]`; SELECT from `posting_embeddings` ORDER BY `embedding <=> target` LIMIT limit WHERE `posting_id != target`; JOIN `postings`; return list
- [x] T038 [P] [US3] Update `backend/app/schemas/posting.py` — add `search_mode: Literal['keyword','semantic'] = 'keyword'` to query params; add `SimilarPostingOut(id: UUID, title: str, company: str, city: str, province: str, work_mode: WorkMode | None, term: str, deadline: datetime | None, similarity: float)`; add `SimilarPostingsResponse(items: list[SimilarPostingOut])`
- [x] T039 [US3] Update `backend/app/api/postings.py` — add `search_mode: Literal['keyword','semantic'] = Query(default='keyword')` to `GET /api/postings`; add `GET /api/postings/{id}/similar` → calls `similar_postings` service, returns `SimilarPostingsResponse`; returns 404 if posting not found; returns 200 with empty items if no embeddings yet
- [x] T040 [P] [US3] Create `backend/tests/ingest/test_extract.py` — test_known_skill_extracted ("Python developer" → skills contains "Python"); test_llm_fallback_triggered (text with no taxonomy matches → mock Anthropic call made); test_work_mode_extraction ("remote position" → work_mode="remote")
- [x] T041 [P] [US3] Create `frontend/src/components/SearchModeToggle.tsx` — two-button toggle (Keyword / Smart); `aria-pressed` per button; on click: update URL param `search_mode`; styled consistently with view toggle in SavedPostingsPage
- [x] T042 [P] [US3] Create `frontend/src/components/SimilarPostings.tsx` — fetches `GET /api/postings/{id}/similar`; renders up to 5 posting cards with title/company/similarity percentage; skeleton loader; "No similar postings found" empty state; each card links to the posting detail
- [x] T043 [P] [US3] Update `frontend/src/pages/PostingDetailPage.tsx` — add `SimilarPostings` sidebar in a right-column layout (full-width on mobile, two-column on md+)
- [x] T044 [P] [US3] Update `frontend/src/api/postings.ts` — add `search_mode?: 'keyword' | 'semantic'` to `PostingListParams`; add `fetchSimilar(postingId: string) -> SimilarPostingOut[]`; add `useSimilarPostings(postingId)` hook

**Checkpoint**: Semantic search returns relevant results; toggle preserved in URL; similar postings sidebar populated.

---

## Phase 6: User Story 4 — Admin Sources Page (Priority: P4)

**Goal**: Admin users can view ingestion sources, run history, trigger manual runs, and re-enable paused sources.

**Independent Test**: Log in as admin; GET /api/admin/sources returns sources list; POST /api/admin/sources/{id}/run returns 202; GET /api/admin/sources/{id}/runs returns run history; non-admin gets 403 on all admin endpoints.

### Implementation

- [x] T045 [P] [US4] Create `backend/app/schemas/ingest.py` — `IngestSourceOut(id, name, adapter_type, enabled, auto_paused, last_run_at, last_run_status, last_run_added, last_run_updated, last_run_closed, last_run_errors)`; `IngestRunOut(id, started_at, finished_at, status, added, updated, closed, errors, error_log: list[str])`; `RunsPage(items: list[IngestRunOut], total: int, page: int, page_size: int)`; `SourcePatchIn(enabled: bool | None, auto_paused: bool | None)`; `TriggerRunOut(run_id: UUID, message: str)`
- [x] T046 [P] [US4] Create `backend/app/services/ingest.py` — `list_sources(db) -> list[IngestSourceOut]`: SELECT ingest_sources LEFT JOIN latest ingest_run; `list_runs(db, source_id, page, page_size) -> RunsPage`; `trigger_run(db, redis, source_id) -> TriggerRunOut`: check not already running (status='running'), enqueue `run_source(source_id)` to RQ queue, return run_id; `patch_source(db, source_id, data) -> IngestSourceOut`: update enabled/auto_paused; if auto_paused set to False also reset consecutive_failures=0
- [x] T047 [US4] Create `backend/app/api/admin.py` — all routes require `get_admin_user` dep; `GET /api/admin/sources`; `GET /api/admin/sources/{id}/runs?page&page_size`; `POST /api/admin/sources/{id}/run` → 202; `PATCH /api/admin/sources/{id}` body `SourcePatchIn`; mount with prefix `/api` tag `admin`
- [x] T048 [P] [US4] Update `backend/app/main.py` — import and mount `admin_router` with prefix `/api`; add `PUT` to CORS allowed methods
- [x] T049 [P] [US4] Create `backend/tests/ingest/test_admin_api.py` — test_non_admin_gets_403 (GET /api/admin/sources without admin flag); test_admin_lists_sources (returns sources list); test_trigger_run_returns_202; test_patch_source_re_enables (auto_paused False resets consecutive_failures); test_trigger_already_running_409
- [x] T050 [US4] Create `frontend/src/api/ingest.ts` — `useAdminSources()` query; `useTriggerRun()` mutation; `useRunHistory(sourceId)` query; `usePatchSource()` mutation; all with `credentials: 'include'`
- [x] T051 [P] [US4] Create `frontend/src/pages/AdminSourcesPage.tsx` — grid of source cards: name, adapter_type badge, last-run timestamp, counts (added/updated/closed), error count (red badge when > 0), auto-paused badge; "Run now" button (disabled while running); "Re-enable" button for paused sources; expandable run history panel; accessible table on mobile
- [x] T052 [P] [US4] Update `frontend/src/App.tsx` — add `/admin/sources` route; guard: redirect to `/` if `!me?.is_admin`; add "Admin" nav link visible only when is_admin

**Checkpoint**: Admin Sources page shows all sources, run history, and allows manual runs; students cannot access /admin routes.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] T053 [P] Update `backend/app/schemas/posting.py` — `PostingOut` gains `closed_at: datetime | None = None`; `low_confidence_fields` included for admin users only (add `low_confidence_fields: dict[str, float] | None = None` and strip in service layer for non-admin)
- [x] T054 [P] Update `frontend/src/api/postings.ts` — add `closed_at: string | null` and `is_closed: boolean` (derived) to `PostingListItem`; update `PostingDetailItem` similarly
- [x] T055 [P] Update `backend/app/api/auth.py` — update `UserOut` to include `is_admin: bool` so frontend knows to show admin nav
- [x] T056 [P] Update `frontend/src/api/auth.ts` — add `is_admin: boolean` to `UserOut` type
- [x] T057 Create `backend/seed/skills.py` — seed 150-skill taxonomy: Python, Java, C, C++, C#, Go, Rust, Swift, Kotlin, TypeScript, JavaScript, React, Vue, Angular, Node.js, Django, FastAPI, Spring, SQL, PostgreSQL, MySQL, MongoDB, Redis, Docker, Kubernetes, Git, Linux, AWS, GCP, Azure, Machine Learning, TensorFlow, PyTorch, Pandas, NumPy, Embedded Systems, RTOS, PCB Design, Verilog, VHDL, FPGA, Matlab, Simulink, Automotive, CAN Bus, ROS, Computer Vision, NLP, REST API, GraphQL, Agile, JIRA (and ~100 more); INSERT … ON CONFLICT DO NOTHING
- [x] T058 [P] Create `backend/seed/ingest_sources.py` — seed 2 fixture-backed dev sources: one JsonApiAdapter pointing to `tests/fixtures/ingest/acme_jobs.json` path (for local dev), one RssAdapter pointing to `tests/fixtures/ingest/shopify_rss.xml`
- [x] T059 [P] Update `docs/agentic-workflow.md` — add Feature 003 entry: what AI implemented, what was developer-reviewed, tests added and their results (Constitution VIII)
- [x] T060 [P] Manual validation gate: run `docker compose exec api pytest -q -m "not perf"` green; run `docker compose exec web npm run typecheck && npm test` green; execute all quickstart.md scenarios; confirm semantic search returns results and similar postings sidebar populates

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories
- **Phase 3 (US1 — Ingestion)**: Depends on Phase 2 — first to implement; also unblocks US2/US3/US4 since it defines the posting ingest pipeline
- **Phase 4 (US2 — CSV/Manual)**: Depends on Phase 2 (models and dedup) and US1 runner pattern — can proceed in parallel with US3 after Phase 2
- **Phase 5 (US3 — Semantic Search)**: Depends on Phase 2 (embedding model, vector index); independent of US2
- **Phase 6 (US4 — Admin)**: Depends on Phase 3 (IngestSource, IngestRun, runner) — parallel with US2/US3
- **Phase 7 (Polish)**: Depends on all user story phases complete

### User Story Dependencies

- **US1 (P1)**: After Foundational — no story dependencies
- **US2 (P2)**: After Foundational — independent of US1 beyond shared dedup logic
- **US3 (P3)**: After Foundational (embedding model) — independent of US1/US2
- **US4 (P4)**: After US1 (needs IngestSource, IngestRun, runner service) — independent of US2/US3

### Parallel Opportunities

- T005 + T006 + T007 + T008 (all ORM models) — different files
- T010 + T011 (base.py + deps.py) — different files
- T012 + T013 + T014 (adapters) — different files
- T018 + T019 (fixture files) — different files
- T020 + T021 + T022 (ingestion tests) — different files
- T031 + T032 + T033 (CSV form + manual form + routes) — different files
- T041 + T042 + T043 + T044 (frontend search/similar components) — different files
- T045 + T046 (ingest schemas + service) — different files

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T004)
2. Complete Phase 2: Foundational (T005–T011)
3. Complete Phase 3: US1 Ingestion (T012–T022)
4. **STOP and VALIDATE**: trigger a run; confirm 5 postings imported; run again, confirm 0 added
5. Deploy/demo if ready

### Incremental Delivery

1. Phase 1 + Phase 2 → infrastructure ready
2. Phase 3 (US1) → ingestion pipeline running → Demo checkpoint
3. Phase 4 (US2) → CSV upload and manual entry → Demo checkpoint
4. Phase 5 (US3) → semantic search + similar postings → Demo checkpoint
5. Phase 6 (US4) → admin sources page → Demo checkpoint
6. Phase 7 → polish, docs, full validation

---

## Notes

- [P] tasks touch different files — safe to parallelize within a phase
- US2 and US3 can be developed in parallel once Phase 2 is done
- US4 must wait for US1 (runner and IngestRun model)
- `respx.mock` must wrap all httpx calls in tests — no live network calls (FR-016)
- pgvector `<=>` operator for cosine distance requires the HNSW index to be created in migration 0004
- `generate_embedding` must be called asynchronously and not block ingestion (FR-010)
- Rate limiting on CSV upload uses the same Redis counter pattern as login rate limiting (Feature 002)
- Admin flag promoted via one-off SQL: `UPDATE users SET is_admin = true WHERE email = '<admin-email>';`
- T057 (skills seed) can contain placeholder entries for the full 150; exact list refined during implementation
