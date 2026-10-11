# CoopRadar — Progress Log

## Current status (2026-10-10)

| Feature | Branch | Status |
|---|---|---|
| 001 Browse & Search | `001-browse-search` | Done |
| 002 Accounts & Application Tracker | `002-accounts-tracker` | Done |
| 003 Real Postings Ingestion & Semantic Search | `003-ingestion-search` | Done |
| 004 AI Resume Matcher | `004-ai-resume-matcher` | Core done (upload, match, cited Q&A); tool-use agent, MCP server, YAML evals not built |

All four branches build on each other; `004-ai-resume-matcher` contains everything. `main` still holds only the
repo skeleton — merge the feature work into `main` via a pull request when ready.

## Verification (2026-10-10 full-repo review)

Run against Postgres 16 + pgvector, Python 3.12, Node 24:

- Backend: `ruff` clean · `mypy --strict` clean · **141 tests pass** (incl. 10k-posting perf test: p95 ≈ 55 ms)
- Migrations: `upgrade head → downgrade base → upgrade head` succeeds; `alembic check` reports no drift
- Seed: `python -m seed` idempotent (55 postings, 106 skills, 2 dev sources)
- Frontend: eslint clean · `tsc` clean · **17 tests pass** · production build succeeds

Not verified here: a full `docker compose up` (Docker wasn't available) and live Claude/OpenAI calls
(all AI calls are mocked in tests). Do those first — see "Your first run" in `docs/PROJECT_GUIDE.md`.

## Open work

1. Merge `004-ai-resume-matcher` → `main` (PR), so CI and the GitHub contributors graph reflect the real code.
2. First live run with real API keys; run `python -m app.ingest.embed` so matching has vectors to search.
3. Add a real public job-board source (check its terms + robots.txt; document it in the plan).
4. Remaining spec-004 scope: agent tools + MCP server + `agent_runs` + YAML eval runner (see the agent-tools skill).
5. Optional Feature 005: deploy + observability (see `docs/speckit-prompts.md`).

## History

- Phase 0 (2026-10-10): repo skeleton, CLAUDE.md, constitution.
- Features 001–004 implemented with the Spec Kit loop (specs in `specs/`).
- 2026-10-10 review: see the latest entry in `docs/agentic-workflow.md` for the full list of fixes.
