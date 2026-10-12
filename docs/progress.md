# CoopRadar — Progress Log

## Current status (2026-10-10)

| Feature | Status |
|---|---|
| 001 Browse & Search | Done |
| 002 Accounts & Application Tracker | Done |
| 003 Real Postings Ingestion & Semantic Search | Done |
| 004 AI Resume Matcher | Core done (upload, match, cited Q&A); tool-use agent, MCP server, YAML evals not built |

Everything is on `main` (PR #1 merged 2026-10-10; the superseded per-feature branches and PRs #2–#4 were closed).
New work: branch from `main`, open a PR, merge when CI is green.

## Verification (2026-10-10 full-repo review)

Run against Postgres 16 + pgvector, Python 3.12, Node 24:

- Backend: `ruff` clean · `mypy --strict` clean · **141 tests pass** (incl. 10k-posting perf test: p95 ≈ 55 ms)
- Migrations: `upgrade head → downgrade base → upgrade head` succeeds; `alembic check` reports no drift
- Seed: `python -m seed` idempotent (55 postings, 106 skills, 2 dev sources)
- Frontend: eslint clean · `tsc` clean · **17 tests pass** · production build succeeds

Not verified here: a full `docker compose up` (Docker wasn't available) and live Claude/OpenAI calls
(all AI calls are mocked in tests). Do those first — see "Your first run" in `docs/PROJECT_GUIDE.md`.

## Hosting (2026-10-11)

The repo is now a deployable website: one production image (root `Dockerfile`) serves the site and API,
sets itself up on start, and offers a one-click demo account. See `docs/DEPLOY.md`.
Verified locally: built site + API in one process against real Postgres (pages, client-side routes, demo account
with 6 tracker items and 20 matches). The Docker image build itself is verified by the new CI `docker` job.

## Bring your own AI key (2026-10-11)

Visitors add their own Claude, ChatGPT, or Gemini key on the **AI key** page; it stays in their browser and is
forwarded per request (never stored). The host needs no AI keys. Resume matching's shortlist now uses SQL skill
overlap, so it works without embeddings. Verified: backend 177 tests, frontend 23 tests, and a live check of fake
keys against the real Anthropic, OpenAI, and Google APIs (all reported as "key rejected", key never echoed).
Not verified: a full answer from each provider with a real key (needs paid/free keys).

## No Docker: one command (2026-10-11)

Docker, Redis, and the separate RQ worker are no longer needed. `python start.py` sets up `backend/.venv`, builds
the site, runs a private PostgreSQL + pgvector (`pgserver` package, data in `~/.coopradar`), migrates, seeds, and
serves everything on http://localhost:8000. Sessions and rate limits live in a Postgres `kv_store` table (Redis is
optional via `REDIS_URL`); imports and embeddings run as in-process background jobs (`app/jobs.py`). Render
deploys on its native Python runtime (`python start.py --hosted`). All Dockerfiles and compose files are removed.
Verified on Windows: first run from scratch, 791 real jobs imported in the background, guest session across
requests, restart in ~12 s, recovery after a hard kill, `--dev` mode, clean database shutdown; backend 244 tests
(incl. perf), frontend 29 tests. Not verified here: the Render build itself and the new CI `website` job (run on push).

## Redesign, job preferences, detailed filters, Vercel option (2026-10-12)

New look: one pine-green accent on warm neutrals (Tailwind palette remap), Public Sans, flat bordered cards, SVG
icons instead of emoji, no em dashes in UI copy. Jobs page: filter sidebar (job type with counts, level, province
and city, work mode, date posted, term and length, company, skills, past deadlines), sort dropdown, cards or table,
removable chips. Resume page: step 1 "What are you looking for?" (job types, keywords, province, work modes,
level), step 2 upload, then tabs "Jobs that fit your resume" (skills on your resume / worth adding) and "Resume
feedback". Backend: job types inferred from titles (`services/categories.py`), `category`/`company`/`posted_within`
filters, filter meta with job type counts, employers and open-job total (counts cached 2 min), `resumes.preferences`
(migration 0009) applied in matching, `PUT /api/resume/preferences`. `vercel.json` serves the site from Vercel and
proxies `/api` to Render. Verified: backend 255 passed (perf p95 34 ms), migrations round-trip + `alembic check`,
frontend 36 passed + lint/tsc/build, real upload with preferences in Edge. Not verified: an actual Vercel deploy.

## Job-board look, co-op matching by program and graduation year, more jobs, free hosting (2026-10-12)

Look: job-board layout (What / Where search band, quick filters for level, country and work mode, an *All filters*
drawer, results list beside a details panel, `?job=` in the URL), one blue accent on white and neutral greys.
Defaults: co-op & internships in Canada. Jobs: ~120 employer boards (was 27), new SmartRecruiters adapter, US
student roles (`INGEST_US_JOBS`), Greenhouse descriptions fetched only for kept jobs; 2,904 open jobs locally.
Matching: `services/education.py` reads programs of study and graduation years from postings (migration 0010:
`country`, `fields_of_study`, `grad_years`) and program / degree / graduation year from resumes; preferences gained
program, degree, grad year, term, countries; job types default to the program's; jobs for other grad years are
filtered out; scoring rebalanced (skills 65, student 15, program 10, grad year 5, term 5, keywords +20); each
match has "why it fits" notes. Docs: `guides/using-coopradar/` (visitors), `guides/how-it-works/` (stack +
interview prep), README rewritten (screenshots, free hosting: Render + Neon + `refresh-jobs.yml`, optional Vercel).
`render.yaml` no longer creates a Render database. Playwright e2e (7 tests) added to CI. Verified: backend 292
passed (perf p95 47 ms), migrations round-trip + `alembic check`, frontend 42 passed + lint/tsc/build, Playwright
7/7 against the local site, screenshots in Edge. Not verified: Render + Neon deploy, the CI Playwright job on
GitHub, the refresh workflow.

## Open work

1. ~~Merge everything into `main`~~ (done 2026-10-10).
2. First live run with real API keys; run `python -m app.ingest.embed` so matching has vectors to search.
3. Add a real public job-board source (check its terms + robots.txt; document it in the plan).
4. Remaining spec-004 scope: agent tools + MCP server + `agent_runs` + YAML eval runner (see the agent-tools skill).
5. Deploy it (README "Host it for free": Render + Neon) and put the live link at the top of the README.
6. Observability: error tracking and a small usage dashboard.

## History

- Phase 0 (2026-10-10): repo skeleton, CLAUDE.md, constitution.
- Features 001–004 implemented with the Spec Kit loop (specs in `specs/`).
- 2026-10-10 review: see the latest entry in `docs/agentic-workflow.md` for the full list of fixes.
