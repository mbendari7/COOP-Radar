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


---

## 2026-10-11 — Bring your own AI key (Claude, ChatGPT, Gemini)

**What the AI assistant did**:
- `app/ai.py`: one interface (`complete`, `stream`, `list_models`) over the official anthropic, openai, and
  google-genai SDKs; visitor credentials from `X-AI-*` headers (owner key as optional, daily-limited fallback);
  provider errors normalized to clear codes; key hidden from repr/logs/errors.
- `POST /api/ai/check` (rate-limited) lists the models a key can use and recommends one.
- Resume matching: stage 1 is now SQL skill overlap (no AI or embeddings needed); stage 2 uses the visitor's model;
  a rejected key is reported instead of silently falling back. Q&A streams through the visitor's provider.
- Frontend: AI key page with per-provider how-to, key stored only in session/localStorage, ✓ indicator in the
  header, Matches page prompt, smart search hidden unless the host enables it.
- Docs: `docs/README.md` rewritten as a one-page "start here" (run, understand, explain), new `docs/AI_KEYS.md`,
  all guides updated.

**Results (actual runs)**: backend 177 passed (incl. perf); ruff + mypy --strict clean; frontend 23 passed, lint/tsc
clean, build OK. Live check with deliberately fake keys against the real Anthropic, OpenAI, and Google APIs: all
three return `AI_KEY_INVALID` with the key never echoed (this caught Google's 400 + `API_KEY_INVALID` shape, now
handled and tested). Not run: real answers from each provider with valid keys.

**What I reviewed / changed**: _(fill in after reviewing the diff)_


---

## 2026-10-11 — No Docker: one-command website (`python start.py`)

**What the AI assistant did**:
- `start.py` (repo root, stdlib only): creates `backend/.venv` (uv if present, else venv + pip), installs
  `backend[local]` only when `pyproject.toml` changes, builds the React site only when sources change, starts a
  private PostgreSQL 16 + pgvector via `pgserver` in `~/.coopradar` (outside OneDrive sync), migrates, seeds, serves
  site + API on one port, opens the browser. `--dev` adds Vite HMR + uvicorn reload; `--hosted` is the host mode.
  Waits out Postgres crash recovery; stops the database on exit.
- `app/store.py`: `Store` protocol + `PostgresStore` on a new `kv_store` table (migration 0008) for sessions and
  rate-limit/AI-quota counters, with Redis-like expiry; Redis used instead when `REDIS_URL` is set. All routes and
  services moved from `aioredis.Redis`/`get_redis` to `Store`/`get_store`.
- `app/jobs.py`: in-process background jobs replace RQ (`enqueue`, max 3 concurrent, errors logged) and a scheduler
  task in the app lifespan (imports due boards one at a time every 10 min, purges expired sessions, backfills
  embeddings when an OpenAI key is set). Admin "Run now" now commits the run row *before* starting the job.
- Removed `Dockerfile`s, `.dockerignore`s, both compose files, `app/worker.py`, `app/redis.py`, `scripts/start.sh`,
  and the `rq` dependency. Seed defaults: sample postings and dev sources off (real jobs only).
- `render.yaml` uses the native Python runtime (build: pip + npm; start: `python start.py --hosted`), no Redis
  service. CI's Docker job became a `website` job that runs the same build/start and smoke-tests it (incl. a
  guest session on the next request).
- Tests: `tests/api/test_store_and_jobs.py` (store round-trip, counters, expiry, purge; job run, failure isolation,
  scheduler). Docs: README, USER_GUIDE, DEPLOY, HOW_IT_WORKS, PROJECT_GUIDE, CLAUDE.md, `.env.example`, skills.

**Results (actual runs)**: ruff + mypy --strict clean; backend 243 passed + perf (p95 44 ms); migrations
0001→0008 up/down/up and `alembic check` clean; frontend lint/tsc clean, 29 passed; OpenAPI + generated types
refreshed. `python start.py` on Windows from a clean checkout: venv + packages + build + DB + 791 real jobs
imported in the background; guest session persisted; restart 12 s; restart after a hard kill OK; `--dev` serves
:5173 with the API proxied; database stopped cleanly on exit. Not run here: the Render build and the CI `website` job.

**What I reviewed / changed**: _(fill in after reviewing the diff)_


---

## 2026-10-12 — Redesign, job preferences, detailed filters, Vercel option

**What the AI assistant did**:
- Visual redesign (palette remap in `tailwind.config.ts`, Public Sans, `components/Icons.tsx`, new header/footer,
  `WelcomeHero`, `PostingCard`), removed emoji and em dashes from UI text.
- Jobs page: `FilterBar` sidebar + `ActiveFilterChips` (`components/filters.ts`), sort dropdown, cards/table view.
- Backend: `services/categories.py` (9 job types from title regexes, tuned against the 791 live titles),
  `category`/`company`/`posted_within` filters, richer `/meta/filters`, `JobPreferences` saved on the resume
  (migration 0009), `preference_filters()` + keyword boost in matching, `PUT /api/resume/preferences`, matched /
  missing skills on each match. Job type counts cached 2 minutes after the perf test caught a 374 ms p95.
- Resume page rebuilt as steps (preferences, upload) and result tabs. `vercel.json` (Vercel CDN, `/api` → Render).
- Tests: `tests/resume/test_preferences.py` (7), 4 new postings filter tests, FilterBar tests rewritten, a
  ResumePage test that preferences are sent with the upload.

**Results (actual runs)**: ruff + mypy clean; backend 255 passed incl. perf (p95 34 ms); 0008↔0009 round-trip and
`alembic check` clean; frontend lint/tsc/build clean, 36 passed; screenshots in Edge of the jobs page, a filtered
view, phone width, and a real DOCX upload with Data & AI + Software + Ontario. Not run: a Vercel deploy.

**What I reviewed / changed**: _(fill in after reviewing the diff)_


---

## 2026-10-12 — Job-board look, co-op matching, ~120 employers, guides, free hosting

**What the AI assistant did**:
- Found more employers: took the employer links behind a public internship list as leads only, then probed each
  employer's own Greenhouse / Lever / Ashby / SmartRecruiters API (plus ~250 guessed Canadian employers) and kept
  boards with Canadian jobs or US student roles. Jobs are imported only from the employers' official APIs.
- Ingest: `SmartRecruitersAdapter`, Greenhouse list-then-details fetching (30 MB boards), `choose_location()`
  (Canada always, US per `INGEST_US_JOBS`, "Vancouver, WA" excluded), US location parsing, work-mode words ignored
  in locations, location/country/education refreshed on re-import, a moved board repointed by the seed.
- `services/education.py`: fields of study (degree sentences only) and graduation years from postings; program,
  degree and graduation year from resumes. Migration 0010 (`country`, `fields_of_study`, `grad_years`, adapter
  check constraint). Postings API: `country`, `program`, `grad_year` filters, `role`, counts by country and work
  mode. Matching: program-derived job types, grad-year filter, rebalanced weights, `fit_notes`, detected education
  in responses.
- Frontend: job-board jobs page (search band, quick filters, `FilterDrawer`, `PostingDetailView` panel), compact
  `PostingCard` with role badges, resume page "About you" step, "why it fits" on matches, blue/neutral palette.
- Hosting: `render.yaml` uses a Neon `DATABASE_URL` (Neon's `channel_binding` handled), `refresh-jobs.yml`.
- Tests: education, US/SmartRecruiters adapters, filters, co-op matching, runner, URL normalization (backend);
  filters, cards, resume page (Vitest); Playwright e2e in CI.
- Docs: `guides/` (visitor guide, builder guide with stack and interview Q&A), README, DEPLOY, PROJECT_GUIDE,
  CLAUDE.md; screenshots in `docs/images/`.

**Results (actual runs)**: ruff + mypy clean; backend 292 passed incl. perf (p95 47 ms); 0009↔0010 round-trip and
`alembic check` clean; frontend lint/tsc/build clean, 42 passed; Playwright 7/7 against the local site; all 122
boards imported with no failures (2,904 open jobs, 48 MB database). Caught along the way: scores bunching at 100
(rebalanced), "Hybrid" parsed as a city, and degree detection matching "Employee Stock Purchase Program". Not run:
a real Render + Neon deploy, CI on GitHub.

**What I reviewed / changed**: _(fill in after reviewing the diff)_


---

## 2026-10-13. Vercel fix, postal redesign, plain language comments

**What the AI assistant did**:
- Found why jobs would not load on Vercel. The `/api` rewrite in `vercel.json` had lost its `/api/:path*` ending, so
  every API call got the Render home page back. Fixed it and added a backend test that checks the rewrite.
- Redesigned the whole frontend with the Impeccable design skill. Wrote `PRODUCT.md`, rolled design directions, and
  the developer picked "Registered Mail". Built it: postal red bar, airmail blue, square corners, Archivo, rows split
  by rules instead of cards, a postmark on every job, stage stamps in the tracker, a days left bar, an envelope style
  upload box. A separate finish reviewer subagent ran two rounds and the fixes it asked for were applied. A
  documenter subagent wrote `DESIGN.md` and `.impeccable/design.json`.
- Fixed bugs found along the way: deadlines showing a day early in Canada (plain dates read as UTC), Greenhouse board
  labels showing as employer names, and the job page spilling sideways on phones. Each got a test.
- Rewrote every code comment and docstring in the backend and frontend in short plain words with no dashes, and
  updated README, both guides, DEPLOY, PROJECT_GUIDE, CLAUDE.md and `.env.example` to match.

**Results (actual runs)**: ruff and mypy clean; backend 293 passed; `alembic upgrade head` and `alembic check` clean;
frontend lint, tsc and build clean, 45 passed; Playwright jobs and phone tests 5 of 5 against a local dev site
proxied to the live Render API. Not run: the resume upload e2e test (it creates accounts on the live site), a
redeploy, and a fresh import, so live employer names update only after the next deploy and import.

**What I reviewed / changed**: _(fill in after reviewing the diff)_


---

## 2026-10-13. Term season and length, every field, lenient matching, resume fit, readable design

**What the AI assistant did**:
- Term and length. New `app/ingest/terms.py` reads the term ("Summer 2027", "Fall '27", "S27", "(January 2027)" in a
  title, "May to August", "Work Term: Winter") and the length ("4 month co-op", "12 week internship", "one year
  contract") from each job, on import and again on every re-import. Migration 0011 adds generated `season` and
  `term_start` columns and makes `duration_months` nullable, since imported jobs had all been given a made up 4 months.
  The jobs page got season and length menus, season and length filters with counts, and sorts by term start and by
  length. Rows lead with "Summer 2027 · 4 months" and a season dot.
- Every field. A Workday adapter (`app/ingest/workday.py`) reads the public JSON behind myworkdayjobs.com careers
  pages (robots.txt allows them). About 50 employers were probed and checked live before being added: banks,
  insurers, energy, mining, aerospace, pharma and health, accounting, food, retail and universities. An optional
  Adzuna adapter runs only when the owner sets its keys. New job types (Health and science, Government education and
  nonprofit, Trades and technicians), five new programs, and about 75 non tech skills.
- Lenient matching. Program and grad year now rank jobs instead of hiding them, a job for other grad years shows with
  a "check before you apply" note, a wanted length ranks higher, and up to 60 matches come back instead of 20.
- Make your resume fit. `GET /api/resume/align/{id}` with no AI: checks, ordered edits and the job's words split into
  ones the resume has and ones worth adding if true. Shown on job details and under each match.
- Readability. Labels are sentence case at 13px instead of tiny narrow capitals, headings are wider, section rules
  are thin grey lines, and the postmark moved off list rows to the details panel. DESIGN.md records it.
- Did not add LinkedIn, Indeed or Glassdoor: their terms forbid automated collection and the project rules require
  public APIs and feeds.

**Results (actual runs)**: ruff and mypy clean; backend 363 passed; `alembic upgrade`, `check`, downgrade to 0010 and
upgrade again clean; frontend lint, tsc, build clean, 52 passed; Playwright 8 of 8 against a local site on a scratch
database. Live Workday check: the adapter pulled real jobs from every listed employer (for example Desjardins 201
Canadian jobs, BDO 230, IKO 117, every big bank 9 to 33 student roles). Not run: a deploy, and a full import cycle
finishing locally (38 of 174 sources had run with no failures when checked).

**What I reviewed / changed**: _(fill in after reviewing the diff)_

## 2026-10-16. Work term kept apart from grad year, real lengths, ~1,700 employers, job updates

**What the AI assistant did**:
- Grad year vs work term. `grad_years_in_posting` matched "graduat" inside "undergraduate", so "Undergraduate students
  for the Summer 2027 term" saved 2027 as a grad year. Now whole words only, "graduate students" is skipped as a level
  of study, and work term phrases are cut out first. Resumes: "Expected co-op term: Summer 2027" and "Seeking a co-op
  from May 2027" no longer read as the graduation year. Cards say "Grad year 2027", apart from the term chip.
- Term start and length on every job: "Summer 2027 · May to Aug · 4 months" on cards, a Work term column with dates
  in the table, start and end on details. Lengths are now the real months (6 stays 6, was rounded to 8); filters
  group them (About 8 months = 6 to 9). "Term starting soonest" puts terms already under way last.
- More jobs: every Canadian Workday job is kept (big sites kept only student roles before), US filter widened to
  early career titles, new `simplify` adapter for Simplify's public internship and new grad lists, and
  `discover_boards.py` re-run twice: ~1,500 new boards (it also had a case bug giving duplicate Workday boards).
- Updates: `first_seen_at` column, `added_since` filter, "Newly added" sort, "N new since your last visit" bar,
  and `GET /api/postings/feed.rss` with a Get updates panel. Migration 0013 covers lengths, the column and the source.
- Not added: Google Jobs. It has no public API and its terms forbid automated collection.

**Results (actual runs)**: ruff, mypy clean; backend 406 passed; `alembic upgrade`, downgrade to 0012, upgrade and
`check` clean; frontend lint, tsc, build clean, 61 passed. Live: Simplify 4,332 internships and 2,619 new grad roles
fetched, CIBC Workday 358 Canadian jobs; local import added 5,932 jobs (2,900 to 8,816 open). Playwright 8 of 8. Not run:
a deploy, a full import of all 1,675 sources.

**What I reviewed / changed**: _(fill in after reviewing the diff)_

## 2026-10-17. More jobs per filter, new job sources, faster imports, a more modern look

**What the AI assistant did**:
- Why filters showed so few jobs: most employers never write the term, so Winter or Summer hid them, and the live
  importer went through ~1,700 boards one at a time while the free host slept after ~20 minutes, so most boards were
  never imported (4,771 jobs live). Fixes: `include_unstated` (on by default in the site, with a switch) keeps jobs that
  don't say their term or length after the ones that do; a season only matches terms not yet under way; the
  scheduler runs 3 boards at a time, never run and oldest first; the runner loads a source's jobs in one query; the
  wake up workflow keeps the site up ~55 minutes; jobs closed over 30 days are deleted unless saved (free 0.5 GB DB).
- New sources (migration 0014): `recruitee`, `bamboohr`, `rippling` (`ingest/ats.py`), `oracle` Oracle Cloud career
  sites (`ingest/oracle.py`, e.g. Nokia 92 Canadian jobs), `github_list` for README tables (negarprh's Canadian tech
  internships, 270 open rows), vanshb03's internship list; season only lists get a year, entries untouched for 180
  days are skipped. `discover_boards.py` now also finds SmartRecruiters, Recruitee, BambooHR, Rippling and Oracle
  boards, retries Common Crawl, reads 4,109 boards from the student lists' apply links (`--lists`) and adds to the file.
- 100 jobs per page. Look: rounded corners, pill chips, white cards on a grey page, Inter for text (DESIGN.md updated).

**Results (actual runs)**: ruff, mypy clean; backend 418 passed before the last API tests were added, `tests/api` 134
passed after; alembic upgrade, downgrade to 0013, upgrade and `check` clean; frontend lint, tsc, build clean, 61
Vitest passed plus the new feed URL test; Playwright 8 of 8. Local: open jobs 10,667 to 13,651 during the import; Canada
co-op Winter with computer engineering 155 to 297 with the new switch. Not finished: the board search was stopped by
the machine running low on memory before checking the boards it found, so `discovered_boards.json` is unchanged.

**What I reviewed / changed**: _(fill in after reviewing the diff)_

## 2026-10-25. Less cluttered jobs page, full width, no popups, two more job sources

**What the AI assistant did**:
- Feedback from a tester: the site was good but felt cluttered. The jobs page had seven bands stacked above the list
  (search, a strip of quick filter menus, the resume bar, the count row, filter chips, the term notice, the new jobs
  bar) and its filters lived in a popup drawer.
- Full width: header, footer, temporary account strip, jobs page, tracker and job page drop the 7xl cap.
- One search row with the resume shortcut on its right. Every filter now sits in a sidebar on the left, always in view
  on laptops and up. Work term, length, level, location, work mode and job type are open; studies, date posted,
  company and skills and the rest fold open in place. The "also show jobs that don't say their term" switch and the
  feed link moved into it. On phones a Filters button opens the same sidebar above the results. Chips show only on
  phones. The details pane shows from 1280 px wide (`splitViewVisible`).
- No popups: the filter drawer is gone, Get updates opens in place, and the sign in popup became a `/sign-in` page
  (`?next=` back to where you were, only paths on this site) plus an inline form on the resume page.
- Job rows are three lines: title, employer and place, then season dot, term, dates, length, role, New and posted
  time. Skills and grad years stay on the details panel.
- New sources (migration 0015): `themuse` (internships, posted in the last 90 days) and `himalayas` (remote jobs open
  to Canada). Checked live: The Muse 33 of 40 kept on 2 pages, Himalayas 24 of 40. Fixed the country count showing 0
  while loading.

**Results (actual runs)**: ruff, mypy clean; backend 429 passed (plus the new stale post test, 10 of 10 in its file);
alembic upgrade, downgrade to 0014, upgrade and `check` clean on an empty DB; frontend lint, tsc, build clean, 69
Vitest passed; Playwright 9 of 9 against a local site. Screenshots checked at 1366, 1920 and 390 px wide. Not run: a
deploy, a full import of the new sources.

**What I reviewed / changed**: _(fill in after reviewing the diff)_
