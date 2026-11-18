# Implementation Plan: One Command Run and Free Hosting

**Branch**: `006-one-command-free-hosting` | **Date**: 2026-10-11 to 2026-10-31 (written up 2026-11-17) | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/006-one-command-free-hosting/spec.md`

## Summary

Replace Docker Compose (Postgres, Redis, API, RQ worker, nginx) with a single stdlib Python script, `start.py`,
that runs a private Postgres from the `pgserver` pip package. Move sessions and counters into a Postgres
`kv_store` table behind a small `Store` interface, and run background work as asyncio tasks in the API process.
Deploy on Render's native Python runtime with a Neon database, put Vercel in front as an option, and add a cached
snapshot endpoint so the first page shows instantly on a sleeping server.

## Technical Context

**Language/Version**: Python 3.12 (stdlib only for `start.py`), TypeScript 5

**Primary Dependencies**: `pgserver` (Postgres 16 plus pgvector as a pip package, local only, in the `local`
extra). `rq` and `redis` removed from the required list (Redis stays optional)

**Storage**: Postgres 16. Migration 0008 adds `kv_store`. Local data lives in `~/.coopradar`, outside OneDrive

**Testing**: `tests/api/test_store_and_jobs.py` for the store and jobs, `tests/api/test_hosting.py` for hosted
mode, the Vercel rewrite and cache headers. CI `website` job runs the real build and start and smoke tests it.
Playwright against the started site

**Target Platform**: Windows, macOS, Linux locally. Render free web service, Neon free Postgres, optional Vercel

**Project Type**: Web app

**Performance Goals**: Restart about 12 seconds. First page of jobs in about a second while the server wakes

**Constraints**: Neon counts every byte read. Render sleeps after about 15 minutes idle and has 750 free hours a
month. Only replies that are the same for everyone may be cached at the edge

**Scale/Scope**: About 1,700 sources to import every 6 hours on a server that sleeps

## Constitution Check

| # | Principle | How this feature meets it | Result |
|---|---|---|---|
| I | Correctness first | Store, jobs, hosting and rewrite all have tests. CI runs the real start command | PASS |
| II | Data stays in the database | List queries defer descriptions and `search_vector`. Sessions move into Postgres too | PASS |
| III | Fast on free hosting | This feature is most of it: port first, seed skip, snapshot, gzip, long lived asset caching | PASS |
| IV | Matching works without AI | Unchanged | PASS |
| V | Honest AI | N/A | PASS |
| VI | Keys and data | Snapshot holds no per visitor data. `is_saved` lists stay uncached | PASS |
| VII | Job collection | Imports keep their polite limits, now 3 at a time across different sites | PASS |
| VIII | Accessible | The waking up note is plain text in the page, not a popup | PASS |
| IX | Small changes | Docs updated in the same change (README, DEPLOY, guides, CLAUDE.md) | PASS |
| X | Simple | Fewer moving parts than before: one process, one database | PASS |

## Project Structure

### Documentation (this feature)

```text
specs/006-one-command-free-hosting/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/api.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
start.py                          # new: venv, packages, build, database, migrate, seed, serve; --dev and --hosted
render.yaml                       # native Python runtime, DATABASE_URL from Neon, no Redis
vercel.json                       # pages from the CDN, /api rewritten to Render, only the snapshot cached
.github/workflows/ci.yml          # website job replaces the Docker job
.github/workflows/refresh-jobs.yml  # keep awake pings when SITE_URL is set
backend/app/
├── store.py                      # new: Store protocol, PostgresStore, Redis when REDIS_URL is set
├── jobs.py                       # new: enqueue(), scheduler(), delete_old_closed()
├── main.py                       # lifespan starts the scheduler, gzip, mount_frontend with caching rules
├── api/postings.py               # GET /api/postings/snapshot
└── services/postings.py          # defer description, cached filter menus
backend/seed/__main__.py          # fingerprint skip, boards loaded in two statements
backend/alembic/versions/0008_add_kv_store.py
frontend/src/
├── api/postings.ts               # useSnapshot, saved in localStorage
└── pages/PostingsListPage.tsx    # snapshot as placeholder data, useTakingLong note
frontend/vite.config.ts           # vendor chunk for React and TanStack
```

Removed: every `Dockerfile`, `.dockerignore`, both compose files, `app/worker.py`, `app/redis.py`,
`scripts/start.sh`, the nginx frontend image.

**Structure Decision**: `start.py` sits at the repo root so the one command is easy to find. Everything else
stays in the existing folders.

## Complexity Tracking

| Breaks which rule | Why it is needed | Simpler option and why it was not enough |
|---|---|---|
| A cached reply (`/snapshot`) | The free server sleeps and the first call can take 30 seconds | Caching the normal list would leak `is_saved` between visitors |
