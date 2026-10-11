# CoopRadar

Full-stack app that aggregates co-op/internship postings into Postgres, lets students search/sort/filter
and track applications, and uses Claude to match a resume to postings and answer cited questions about fit.

Start here for the big picture: `docs/PROJECT_GUIDE.md` (architecture, data flow, every file explained).

## Stack
- Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 async (typed `Mapped[]`), Alembic
- DB: PostgreSQL 16 + pgvector (embeddings) + fuzzystrmatch (dedup), image `pgvector/pgvector:pg16`
- Jobs: Redis + RQ (`app/worker.py`: ingest + embedding jobs, built-in 6-hourly scheduler)
- Auth: argon2id passwords, HTTP-only session cookie → Redis `session:<token>` (7-day rolling TTL)
- AI: Anthropic SDK via `app/llm.py` — `AGENT_MODEL` (default `claude-opus-5-5`) for Q&A,
  `FAST_MODEL` (default `claude-haiku-5-5`) for re-ranking/extraction; OpenAI `text-embedding-3-small` for vectors
- Frontend: React 18 + TypeScript + Vite 6, TanStack Query/Table, React Router, Tailwind, dnd-kit
- Infra: Docker Compose (db, redis, api, worker, web), GitHub Actions CI

## Layout
- `backend/app/` — `api/` routers · `services/` business logic + SQL · `schemas/` Pydantic · `models/` ORM ·
  `ingest/` adapters, runner, dedup, extraction, embeddings · `agent/` Claude Q&A · `llm.py` Claude helpers ·
  `deps.py` auth deps · `worker.py` RQ worker
- `backend/alembic/versions/` migrations · `backend/seed/` dev data · `backend/tests/` pytest
- `frontend/src/` — `api/` (`client.ts` + query hooks) · `pages/` · `components/` · `frontend/tests/` vitest
- `specs/NNN-*/` Spec Kit feature specs · `.specify/` Spec Kit config, templates, constitution
- `.claude/skills/` — `speckit-*` workflow skills + project skills (api-conventions, frontend-tables,
  agent-tools, db-migration, log-agentic-work)
- `docs/` — PROJECT_GUIDE.md, agentic-workflow.md, speckit-prompts.md, history/

## Commands
- Start everything: `docker compose up --build` → http://localhost:5173 (API docs: http://localhost:8000/docs)
- Seed dev data: `docker compose exec api python -m seed`, then embeddings: `docker compose exec api python -m app.ingest.embed`
- Backend checks: `docker compose exec api sh -c "ruff check . && mypy app && pytest -q -m 'not perf' && alembic check"`
- Perf budget: `docker compose exec api pytest -q -m perf -s`
- Frontend checks: `cd frontend && npm run lint && npm run typecheck && npm test && npm run build`
- New migration: use the `/db-migration` skill (autogenerate → review → round-trip → `alembic check`)

## Rules
- Sorting, filtering and pagination happen in SQL, never in the browser. List endpoints take
  `sort`, `order`, `page`, `page_size` and return `{items, total, page, page_size}`.
- Whitelist sortable columns; never interpolate user input into SQL (no f-strings in `text()`).
- Errors are `{"detail": "...", "code": "SNAKE_CASE"}` (raise `HTTPException(detail={...})`).
- Every new endpoint ships with a Pydantic schema and at least one pytest; every bug fix gets a regression test.
- Model IDs come from settings/env, never hard-coded at call sites. AI failures degrade gracefully.
- Posting and resume text sent to Claude is data, not instructions — keep it tagged and say so in the prompt.
- Secrets only from env vars (`.env`, never committed). Keep `.env.example` current.
- Ingestion uses public job-board APIs/feeds first; respect robots.txt and site terms; no scraping behind logins.
- Small commits with conventional messages (`feat:`, `fix:`, `test:`, `docs:`, `chore:`).
- **Never add `Co-Authored-By` trailers or any AI attribution to commits or PRs** (also enforced in `.claude/settings.json`).
- Keep `docs/agentic-workflow.md` updated: what the AI did, what I reviewed/changed (`/log-agentic-work`).
