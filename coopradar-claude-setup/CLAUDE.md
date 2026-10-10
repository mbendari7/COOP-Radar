# CoopRadar

Full-stack app that ingests co-op/internship postings, stores them in Postgres, lets users
search/sort/filter them, and uses an LLM agent to match a resume to postings and explain gaps.

## Stack
- Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 (typed `Mapped[]` style), Alembic
- DB: PostgreSQL 16 + pgvector (embeddings live in the same DB)
- Jobs: RQ + Redis for ingestion and embedding jobs
- Frontend: React + TypeScript + Vite, TanStack Query (data), TanStack Table (tables), Tailwind
- Agent: Anthropic Python SDK with tool use; agent tools also exposed as an MCP server
- Infra: Docker Compose for local dev, GitHub Actions CI, pytest, ruff, mypy, eslint, vitest

## Layout
- `backend/app/` — `api/` routers, `models/` ORM, `schemas/` Pydantic, `services/` business logic,
  `ingest/` source adapters, `agent/` LLM tools + prompts, `mcp/` MCP server
- `backend/tests/` — pytest; `backend/evals/` — agent eval cases + runner
- `frontend/src/` — `pages/`, `components/`, `api/` (typed client + query hooks)

## Commands
- Start everything: `docker compose up --build`
- Backend tests: `docker compose exec api pytest -q`
- Lint/type: `ruff check . && mypy app` (backend), `npm run lint && npm run typecheck` (frontend)
- New migration: `alembic revision --autogenerate -m "<msg>"` then review it before `alembic upgrade head`
- Agent evals: `python -m evals.run`

## Rules
- Sorting, filtering and pagination happen in SQL, never in the browser. List endpoints take
  `sort`, `order`, `page`, `page_size` and return `{items, total, page, page_size}`.
- Whitelist sortable columns; never interpolate user input into SQL.
- Every new endpoint ships with a Pydantic schema and at least one pytest.
- Secrets only from env vars (`.env`, never committed). Keep `.env.example` current.
- Ingestion uses public job-board APIs/feeds first; respect robots.txt and site terms; no scraping behind logins.
- Small commits with conventional messages (`feat:`, `fix:`, `test:`, `chore:`).
- Keep `docs/agentic-workflow.md` updated: what Claude Code did, what I reviewed/changed.
