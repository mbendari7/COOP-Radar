---

description: "Task list for one command run and free hosting"
---

# Tasks: One Command Run and Free Hosting

**Input**: Design documents from `/specs/006-one-command-free-hosting/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md

**Tests**: Included. The store, jobs, hosted mode and the Vercel rewrite all have tests, and CI runs the real
start command.

**Organization**: Grouped by user story. Written after the code, so finished work is ticked.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Add `pgserver` to a `local` extra in `backend/pyproject.toml` and drop `rq` from the required list
- [X] T002 [P] Add `BACKGROUND_JOBS`, `REDIS_URL` (optional), `SEED_*`, `INGEST_INTERVAL_HOURS` and
  `INGEST_START_DELAY_SECONDS` to `backend/app/config.py` and `.env.example`

---

## Phase 2: Foundational

- [X] T003 Migration `backend/alembic/versions/0008_add_kv_store.py` for the `kv_store` table
- [X] T004 `backend/app/store.py`: `Store` protocol, `PostgresStore`, `create_store()` that picks Redis when
  `REDIS_URL` is set, `get_store` dependency
- [X] T005 Move every route and service from `get_redis` to `get_store`
- [X] T006 `backend/app/jobs.py`: `enqueue()` with at most 3 running, errors logged, and `scheduler()` in the app
  lifespan
- [X] T007 [P] Tests for the store (round trip, counters, expiry, purge) and jobs (run, failure kept apart,
  scheduler) in `backend/tests/api/test_store_and_jobs.py`
- [X] T008 Admin Run now commits the run row before starting the job, in `backend/app/api/admin.py`

**Checkpoint**: The backend runs with no Redis and no worker

---

## Phase 3: User Story 1 - One command (Priority: P1) 🎯 MVP

- [X] T009 [US1] `start.py`: venv (uv if present), install only when `pyproject.toml` changes, build only when
  sources change, start `pgserver` in `~/.coopradar`, migrate, seed, serve, open the browser, stop the database
  on exit
- [X] T010 [US1] `--dev` mode with Vite on :5173 and uvicorn reload
- [X] T011 [US1] Wait out Postgres crash recovery after a hard kill
- [X] T012 [US1] `main.py → mount_frontend` serves the built site with a page fallback and path traversal guard
- [X] T013 [US1] Remove the Dockerfiles, compose files, `app/worker.py`, `app/redis.py`, `scripts/start.sh`
- [X] T014 [US1] Seed defaults: real jobs only, sample postings and dev sources off

**Checkpoint**: Clean Windows machine to jobs on screen with `python start.py`

---

## Phase 4: User Story 2 - Free hosting (Priority: P2)

- [X] T015 [P] [US2] Hosted mode and Vercel rewrite tests in `backend/tests/api/test_hosting.py`
- [X] T016 [US2] `render.yaml` on the native Python runtime with `python start.py --hosted`
- [X] T017 [US2] Use a Neon `DATABASE_URL` and stop making a Render database (`channel_binding` handled in config)
- [X] T018 [US2] `vercel.json` with pages from the CDN and `/api/:path*` rewritten to Render
- [X] T019 [US2] `.github/workflows/refresh-jobs.yml` pinging every 10 minutes from 7 am to 1 am Eastern when
  `SITE_URL` is set
- [X] T020 [US2] CI `website` job: Render build command, `start.py --hosted`, smoke test, guest session on the next
  request, then Playwright
- [X] T021 [US2] Scheduler runs 3 sources at a time, never run first then oldest first
- [X] T022 [US2] `delete_old_closed()` for jobs closed or past deadline over 30 days, unless saved
- [ ] T023 [US2] Set the `SITE_URL` repository variable on GitHub so the keep awake workflow runs (found unset on
  2026-11-15, owner action)

---

## Phase 5: User Story 3 - Instant first page (Priority: P3)

- [X] T024 [P] [US3] Snapshot reply and cache header tests in `backend/tests/api/test_postings.py` and
  `backend/tests/api/test_hosting.py`
- [X] T025 [US3] `GET /api/postings/snapshot` in `backend/app/api/postings.py` with the public cache header
- [X] T026 [US3] Cache only the snapshot path in `vercel.json`
- [X] T027 [US3] `useSnapshot` in `frontend/src/api/postings.ts` saved in localStorage, used as placeholder data in
  `frontend/src/pages/PostingsListPage.tsx`, first job's details seeded
- [X] T028 [US3] `useTakingLong` note after 4 seconds
- [X] T029 [US3] Seed fingerprint skip and `SEED_FORCE` in `backend/seed/__main__.py`, boards in two statements
- [X] T030 [US3] `--hosted` opens the port first, importer waits `INGEST_START_DELAY_SECONDS`
- [X] T031 [US3] Gzip over 1 KB, a year of caching for hashed assets, `no-cache` on index.html, `vendor` chunk in
  `frontend/vite.config.ts`, non blocking fonts, snapshot preloaded in `index.html`

---

## Phase N: Polish

- [X] T032 Neon data transfer: defer descriptions and `search_vector`, cache filter menus 2 minutes and skills an
  hour
- [X] T033 [P] Docs: README (run, host, make it load fast), `docs/DEPLOY.md`, the guides, CLAUDE.md
- [X] T034 Log entries in `docs/agentic-workflow.md`
- [ ] T035 Check the Vercel edge cache and the keep awake workflow on the real hosts (not checked yet)

---

## Dependencies & Execution Order

- Phase 2 (store and jobs) blocks everything, since Redis and RQ go away
- Story 2 needs Story 1's `start.py --hosted`
- Story 3 can be built any time after Story 2

## Notes

- T023 and T035 are left open on purpose so `/speckit-converge` can pick them up
