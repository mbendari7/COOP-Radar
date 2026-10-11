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

## Open work

1. ~~Merge everything into `main`~~ (done 2026-10-10).
2. First live run with real API keys; run `python -m app.ingest.embed` so matching has vectors to search.
3. Add a real public job-board source (check its terms + robots.txt; document it in the plan).
4. Remaining spec-004 scope: agent tools + MCP server + `agent_runs` + YAML eval runner (see the agent-tools skill).
5. Deploy it (`docs/DEPLOY.md`) and put the live link at the top of the README.
6. Observability: error tracking and a small usage dashboard.

## History

- Phase 0 (2026-10-10): repo skeleton, CLAUDE.md, constitution.
- Features 001–004 implemented with the Spec Kit loop (specs in `specs/`).
- 2026-10-10 review: see the latest entry in `docs/agentic-workflow.md` for the full list of fixes.
