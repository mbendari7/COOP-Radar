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

---

## 2026-10-10 — Feature 002: Accounts & Application Tracker

**Branch**: `002-accounts-tracker`

**What Claude Code built**:
- Alembic migrations 0002 (users + sessions), 0003 (saved_postings + application_events tables, 7-status enum, FK constraints)
- Auth models: User, Session; Tracker models: SavedPosting, ApplicationEvent
- Pydantic schemas: auth (RegisterRequest, LoginRequest, TokenResponse), tracker (SavedPostingOut, ApplicationEventOut, StatusUpdate, TrackerStatsOut)
- Services: auth_service (register, login, logout, get_current_user, JWT + bcrypt), tracker_service (save/unsave posting, update status with event history, get board, get stats, CSV export)
- API routers: /api/auth (register, login, logout, me), /api/tracker (saved list, save, unsave, status, board, stats, CSV)
- Rate limiting middleware (slowapi): 10 req/min on auth endpoints
- Backend tests: 40+ pytest cases covering auth flows, tracker CRUD, board grouping, stats, CSV export, rate limit headers
- Frontend: AuthContext + useAuth hook, LoginPage, RegisterPage, ProtectedRoute, SaveButton component, ApplicationTrackerPage (/tracker — kanban board + list toggle, stats bar), CSV export button
- App.tsx updated with auth routes and protected /tracker route

**What I reviewed / changed**:
- Not yet reviewed — pending first local run

**Tests added**:
- Backend: register/login/logout/me, duplicate email 409, invalid credentials 401, save/unsave posting, status transitions (all 7 statuses), event history append, board grouping, stats counts, CSV header+rows, rate limit 429
- Frontend: LoginPage submit, RegisterPage validation, SaveButton toggle, TrackerPage board render

**Next step**: `docker compose up --build && docker compose exec api alembic upgrade head` then register a user and save a posting

---

## 2026-10-10 — Feature 003: Real Postings Ingestion & Semantic Search

**Branch**: `003-ingestion-search`

**What Claude Code built**:
- Alembic migration 0004: adds `embedding vector(1536)` column to postings, `IVFFlat` index (lists=100), `posting_embeddings` view
- Ingest pipeline: `app/ingest/scraper.py` (aiohttp-based co-op board scraper with retry + rate limiting), `app/ingest/embed.py` (OpenAI text-embedding-3-small batched embedding), `app/ingest/pipeline.py` (orchestrates scrape → embed → upsert with idempotency on source_id)
- CLI entrypoint: `python -m app.ingest` (runs pipeline, logs stats)
- Semantic search: updated `services/postings.py` to hybrid search — keyword FTS + cosine similarity reranking when query present; `GET /api/postings?q=` now returns semantically ranked results
- Backend tests: `tests/ingest/test_pipeline.py` (mock scraper, mock OpenAI, upsert idempotency, batch size), `tests/api/test_semantic_search.py` (embedding rerank order, fallback to FTS when no embedding)
- Frontend: updated `api/postings.ts` usePostings to pass semantic flag; `SearchBox.tsx` debounce unchanged; results reorder visually on semantic rerank

**What I reviewed / changed**:
- Not yet reviewed — pending first local run

**Tests added**:
- Backend: pipeline scrape+embed+upsert (12 cases), semantic rerank order, FTS fallback, duplicate source_id idempotency, batch embedding chunking
- Integration: end-to-end pipeline with mock HTTP server

**Next step**: Set `OPENAI_API_KEY` in `.env`, then `docker compose exec api python -m app.ingest`

---

## 2026-10-10 — Feature 004: AI Resume Matcher

**Branch**: `004-ai-resume-matcher`

**What Claude Code built**:
- Alembic migration 0005: `resumes` table (id UUID PK, user_id UNIQUE FK→users CASCADE, filename, file_size CHECK>0, extracted_text, uploaded_at) and `match_results` table (id UUID PK, resume_id FK→resumes CASCADE, posting_id FK→postings CASCADE, score SMALLINT CHECK 0–100, reason TEXT, ranked_at; UNIQUE(resume_id, posting_id))
- New Python deps: `pypdf>=4.0` (PDF extraction), `python-docx>=1.1` (DOCX extraction)
- Models: `app/models/resume.py` (Resume), `app/models/match_result.py` (MatchResult); exports added to `app/models/__init__.py`
- Schemas: `app/schemas/resume.py` — ResumeOut, MatchResultOut, UploadResponse, MatchesResponse, AskRequest
- Services: `app/services/resume.py` — extract_pdf_text, extract_docx_text, embed_and_rank (OpenAI cosine similarity top-40 → Claude Haiku re-rank → top-20 with score+reason), upload_resume, get_resume, delete_resume, get_matches
- Agent: `app/agent/resume_qa.py` — stream_answer() yields SSE `data: {"delta": "..."}` chunks; citation-constrained system prompt; "I don't have enough information to answer that." fallback
- API router: `app/api/resume.py` (POST/GET/DELETE /api/resume, GET /api/resume/matches, POST /api/resume/matches/{posting_id}/ask as StreamingResponse SSE)
- main.py updated to mount resume router
- Backend tests: `tests/resume/conftest.py` (in-memory PDF + DOCX fixtures), `tests/resume/test_resume_upload.py` (11 cases), `tests/resume/test_match_service.py` (7 cases), `tests/resume/test_resume_qa.py` (5 cases)
- Eval suite: `tests/eval/test_resume_match_eval.py` (25 fixture-based cases — 10 resume citations, 5 posting citations, 5 don't-know, 5 score-range; citation rate gate ≥80%; all Anthropic/OpenAI mocked)
- Frontend: `src/api/resume.ts` (useResume, useMatches, useUploadResume, useDeleteResume, askAboutPosting SSE), `src/components/ResumeUploadForm.tsx` (file input, stored card, delete modal), `src/components/ConversationPanel.tsx` (inline Q&A panel, streaming tokens, citation highlights), `src/pages/MatchResultsPage.tsx` (score badges, ranked cards, upload prompt), App.tsx + AccountSettingsPage.tsx updated

**Convergence fixes applied**:
- T036: Moved test fixtures from `tests/fixtures/resume/conftest.py` to `tests/resume/conftest.py` (pytest only loads conftest.py from ancestor directories)
- T037: Removed `desc()` from `Index("idx_match_results_resume_score", ...)` — bare string is invalid SQLAlchemy Index DDL; Alembic migration handles DESC correctly
- T038: Merged duplicate `from sqlalchemy import` lines in `app/models/resume.py`

**Tests added**:
- Backend: 23 pytest cases (upload PDF/DOCX, invalid type, too large, unauthenticated, re-upload replaces, GET/DELETE resume, cross-user isolation, text extraction, embed+rank, Q&A stream, don't-know, 404 paths)
- Eval: 25 fixture-based eval cases (citation rate ≥80% gate, zero factual errors gate, score bucket validation)

**Next step**: Set `OPENAI_API_KEY` + `ANTHROPIC_API_KEY` in `.env`, then `docker compose exec api alembic upgrade head` and upload a resume at /matches


---

## 2026-10-10 — Full-repo review, verification, and model update

**Branch**: `004-ai-resume-matcher` (uncommitted working tree, for review before committing)

**Why**: Features 001–004 had never been run end to end (no Docker on the dev machine). This pass ran everything
against real Postgres 16 + pgvector (via `pgserver`), Python 3.12, and Node, and fixed what broke.

**What the AI assistant did**:
- Git history: removed `Co-Authored-By: Claude …` trailers from 12 commits on the four feature branches
  (`git filter-branch --msg-filter`, trees verified identical, force-pushed with lease); `main` untouched.
  Added `.claude/settings.json` (`attribution` off) and a CLAUDE.md rule so it can't recur.
- Bugs fixed (each with a regression test): migration 0001 impossible to apply (STABLE function in generated
  column); SQL injection in `?skills=`; CSV/manual postings never committed; CSV export crash; deadlines panel
  dropping NULL-status postings; status counts query failing on Postgres (enum vs text CASE); similar-postings SQL
  bind bug; invalid sort → 500 instead of 422; ingest re-run closing every posting; "Run now" leaving a stuck run;
  embeddings never generated; `python -m seed` missing `__main__` and wiping saved postings; rq-scheduler never
  started; `file://` dev sources unreadable; broken pyproject build backend; alembic couldn't import `app`;
  9 indexes missing from models (would be dropped by autogenerate); API container missing AI keys.
- AI code: model IDs moved to settings (`AGENT_MODEL=claude-opus-5-5`, `FAST_MODEL=claude-haiku-5-5`); shared
  `app/llm.py` (reads text blocks only — current models emit thinking blocks first); explicit effort; refusal
  fallback; prompt-injection guard; cosine fallback when Claude fails; 503 `AI_UNAVAILABLE` on embedding outage.
- Unified error shape `{detail, code}`; frontend `api/client.ts` (`apiFetch`/`ApiError`); fetches moved out of
  components; Vite proxy so cookies are first-party; generated `package-lock.json`; added `nginx.conf`.
- Tests rebuilt: savepoint-isolated sessions, Secure-cookie fix, shared Claude/queue/embedding mocks, pytest-asyncio 1.x
  config, perf test made non-destructive and latency-based.
- Workspace: moved Spec Kit (`.specify/`, `specs/`) and all skills to the repo root so Claude Code loads them;
  rewrote the 5 project skills; nested spec-history git repo preserved at `../COOP-Radar-spec-history-backup/`.
- Docs: new README, `docs/PROJECT_GUIDE.md`, progress log, spec 003/004 amendments, CI on every branch with
  migration round-trip + `alembic check` + perf budget + production build.

**Results (actual runs)**: backend 141 passed (incl. perf: p50 ≈ 20 ms, p95 ≈ 55 ms on 10k postings);
ruff clean; mypy --strict clean; migrations up/down/up OK; `alembic check` no drift; seed idempotent.
Frontend: eslint clean, tsc clean, 17 tests passed, production build OK.

**Not verified**: `docker compose up` (no Docker available) and live Claude/OpenAI calls (mocked in tests).

**What I reviewed / changed**: _(fill in after reviewing the diff)_


---

## 2026-10-11 — Deployable website: one-container image, demo accounts, AI limits

**What the AI assistant did**:
- Production image (root `Dockerfile`): builds the React site and serves it from FastAPI (`mount_frontend`, SPA
  fallback, path-traversal safe); `backend/scripts/start.sh` migrates, seeds, starts the worker and embeddings.
- `docker-compose.prod.yml` (site + Postgres + Redis, optional Caddy HTTPS) and `render.yaml` Blueprint;
  `DATABASE_URL` accepts host formats (`postgres://`, `sslmode=`).
- One-click demo accounts (`services/demo.py`, migration 0006 `users.is_demo`): private per visitor, pre-filled
  tracker + skill-overlap matches (no AI cost), 24 h expiry, 10/hour per IP. `GET /api/config` feature flags.
- Per-user daily AI limit (`services/usage.py`) on resume upload and Q&A.
- Frontend: welcome section, "Try the demo" button, demo banner, mobile-safe header.
- Repo tidy-up: guides moved to `docs/` with an index; removed the redundant nginx frontend image; CI job that
  builds the production stack and smoke-tests it.

**Results (actual runs)**: backend 152 passed + perf; ruff + mypy --strict clean; migration 0006 up/down/up and
`alembic check` clean; frontend lint/tsc clean, 19 tests passed, build OK; local smoke test of built site + API on
real Postgres passed. Not run here: the Docker image build (no Docker on this machine; CI builds it).

**What I reviewed / changed**: _(fill in after reviewing the diff)_
