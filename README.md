# CoopRadar

**Drop in your resume. See what it's good at, what employers want that it's missing, how to tailor it, and which
real co-op jobs to apply for.** CoopRadar imports live postings from Canadian employers' own career boards, matches
them to a student's resume in SQL for free, and layers on bring-your-own-key AI (Claude, ChatGPT, or Gemini) for
reviews, tailoring plans, and cover letter openers.

[![CI](https://github.com/mbendari7/COOP-Radar/actions/workflows/ci.yml/badge.svg)](https://github.com/mbendari7/COOP-Radar/actions/workflows/ci.yml)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/mbendari7/COOP-Radar)

**🌐 Live site:** _add your link after deploying_ · **New here or not a developer?** Read the
**[User Guide](docs/USER_GUIDE.md)**: how to use it, get it online without Docker, and tips.

---

## What it does

| | |
|---|---|
| 📄 **Resume in, no sign-up** | Drag and drop a PDF or DOCX. A private temporary account is created (kept 7 days). Keep it any time with an email and password. |
| ✅ **What your resume shows** | Skills found on the resume that real postings ask for. Free, computed in SQL. |
| 📈 **What you're missing** | The most-requested skills across open postings that the resume doesn't show, with how many jobs ask for each. |
| 🤖 **AI resume review** | Strengths, fixes, tailoring tips, roles to search, and honest keywords to add. Uses the visitor's own key; cached per resume. |
| 💼 **Jobs to apply for** | Top 20 open jobs ranked for a *student*: skill coverage, senior roles demoted, co-op and intern roles boosted, each with a data-backed reason. Optional AI re-rank. |
| ✏️ **Per-job assistant** | One click for a tailoring plan (what to lead with, bullet rewrites, keywords, gaps) or a cover letter opener, plus cited Q&A. Streams live. |
| 🔎 **Real jobs** | About 800 Canadian postings from 27 employers via public Greenhouse, Lever, and Ashby job-board APIs, refreshed every 6 h. Search, filter (city includes remote), and "Co-op & intern only". |
| 🗂️ **Tracker** | Save jobs, move them through 7 statuses with dated notes, board or table view, deadlines this week, CSV export. |

## How it works

```mermaid
flowchart LR
    subgraph Site["One container (Dockerfile)"]
      UI["React SPA<br/>(built, served by FastAPI)"]
      API["FastAPI /api"]
      WK["Worker<br/>RQ + 6 h scheduler"]
    end
    DB[("PostgreSQL 16<br/>postings · users · resumes<br/>full-text · skill overlap · pgvector")]
    RD[("Redis<br/>sessions · rate limits · queue")]
    BOARDS["Employer career boards<br/>Greenhouse · Lever · Ashby<br/>(public JSON APIs)"]
    AI["Visitor's AI<br/>Claude · ChatGPT · Gemini<br/>(their key, per request)"]

    UI -->|"/api, HTTP-only cookie"| API
    API --> DB
    API --> RD
    WK --> RD
    WK -->|import, parse, dedup, tag skills| DB
    WK -->|fetch| BOARDS
    API -->|"review · re-rank · tailor · Q&A"| AI
```

1. **Ingest**: per employer, an adapter fetches the board's JSON, keeps Canadian locations, parses `City, Province`,
   de-duplicates (same company and city with title similarity above 0.85), tags skills with context rules (C, R,
   Go, Spring), and sets an estimated apply-by date when none is published. Vanished jobs are closed; failing
   boards auto-pause.
2. **Resume**: upload creates a guest session if needed. Text is extracted with pypdf or python-docx; the file isn't kept.
3. **Free matching (SQL)**: coverage = matched ÷ max(listed skills, 3), then student fit (×0.5 for
   senior/lead/manager titles, +0.25 for co-op/intern/new-grad titles). The top 20 are stored with reasons like
   *"You have Python, SQL; it also asks for Go."*
4. **Insights**: skills found, plus in-demand skills missing from `unnest(skills) GROUP BY` over open postings. The
   optional AI review is strict JSON, validated, and cached in `resumes.insights`.
5. **AI (bring your own key)**: the key is kept in the browser and sent as `X-AI-*` headers. `app/ai.py` wraps the
   official Anthropic, OpenAI, and Google GenAI SDKs behind `complete()` and `stream()` with normalized errors.
   Prompts treat documents as data, never invent experience, and require citations or "not enough information".

Full walkthrough and talking points: **[docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md)**.

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async, typed `Mapped[]`), asyncpg |
| Database | PostgreSQL 16: generated `tsvector` + GIN (weighted keyword search), array skill matching, JSONB, **pgvector** (optional smart search) |
| Migrations | Alembic `0001`–`0007` (round-trip + `alembic check` in CI) |
| Jobs | Redis + RQ worker with a built-in scheduler; httpx adapters for Greenhouse / Lever / Ashby, plus JSON API, RSS, and CSV |
| Auth | argon2id, opaque session tokens in Redis, HTTP-only Secure cookies, temporary (guest/demo) accounts with claim |
| AI | Bring your own key: `anthropic`, `openai`, `google-genai` SDKs behind one module; streaming SSE; optional owner keys (Claude fallback with a daily limit, OpenAI embeddings) |
| Frontend | React 18, TypeScript 5, Vite 6, TanStack Query v5, TanStack Table v8, React Router v6, Tailwind CSS v3, dnd-kit |
| Testing | pytest + pytest-asyncio (**234**, incl. a 10k-row latency budget), Vitest + Testing Library (**27**) |
| Quality | ruff, mypy `--strict`, eslint, `tsc --noEmit` |
| Delivery | GitHub Actions (tests + production-image boot and smoke test), one-container `Dockerfile`, Render Blueprint, Compose + Caddy HTTPS |

## Run it

**Online, no Docker:** click **Deploy to Render** above, then **Apply** (details and free-tier caveats in
[docs/DEPLOY.md](docs/DEPLOY.md)). Real jobs import within minutes of going live.

**On your machine** (Docker Desktop):
```bash
git clone https://github.com/mbendari7/COOP-Radar.git && cd COOP-Radar
cp .env.example .env                                  # set POSTGRES_PASSWORD; AI keys are optional
docker compose -f docker-compose.prod.yml up --build  # the website → http://localhost:8080
```

**Develop** (hot reload):
```bash
docker compose up --build                 # web :5173 · api :8000 (docs at /docs) · worker · db · redis
docker compose exec api python -m seed    # skills, career boards, sample postings (see SEED_* flags)
```

| Task | Command |
|---|---|
| Backend lint / types / tests | `docker compose exec api ruff check . && docker compose exec api mypy app && docker compose exec api pytest -q` |
| Perf budget (p95 on 10k postings) | `docker compose exec api pytest -q -m perf -s` |
| Frontend | `cd frontend && npm install && npm run lint && npm run typecheck && npm test && npm run build` |
| New migration | `docker compose exec api alembic revision --autogenerate -m "…"`, review it, then `alembic upgrade head` |
| Import jobs now | Admin page → **Run now**, or wait for the worker (runs on start, then every `INGEST_INTERVAL_HOURS`) |
| Reset local data | `docker compose down -v` |

## Configuration

All settings are environment variables, documented in [`.env.example`](.env.example).

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` · `REDIS_URL` | set by compose / host | Postgres (`postgres://` URLs are normalized) · Redis |
| `DEMO_ENABLED` | `true` | "Try the demo" + upload without an account (temporary accounts, 7 days) |
| `ANTHROPIC_API_KEY` | empty | Optional shared Claude key for visitors without one, capped by `AI_DAILY_LIMIT` (default 20/day) |
| `OPENAI_API_KEY` | empty | Optional: smart (semantic) search, similar postings, embedding shortlist |
| `SEED_JOB_BOARDS` · `SEED_SAMPLE_POSTINGS` · `SEED_DEV_SOURCES` | `true` | What the seed loads (prod configs turn samples and dev sources off) |
| `INGEST_INTERVAL_HOURS` · `INGEST_LOCATION_FILTER` | `6` · Canada | Import cadence · location regex (`.*` = everywhere) |
| `AGENT_MODEL` · `FAST_MODEL` | `claude-opus-5-5` · `claude-haiku-5-5` | Models for the owner's Claude key (visitors pick their own) |
| `COOKIE_SECURE` | `true` | Keep on for HTTPS |

## API

| Method & path | Auth | Purpose |
|---|---|---|
| `GET /api/postings` | optional | Search, filter, sort, paginate: `q`, `search_mode`, `city`, `province`, `term`, `work_mode`, `duration`, `skills`, `students_only`, `show_expired`, `sort`, `order`, `page`, `page_size` → `{items, total, page, page_size}` |
| `GET /api/postings/{id}` · `/{id}/similar` · `/meta/filters` | — | Detail · similar · filter values |
| `POST /api/auth/register` · `login` · `logout` · `demo` · `guest` | — | Sessions; `demo` = pre-filled temporary account, `guest` = empty one |
| `GET/PATCH/DELETE /api/me` · `POST /api/me/claim` | user | Profile, password, delete · keep a temporary account |
| `POST/GET/DELETE /api/resume` | user | Upload (AI optional) / metadata / delete |
| `GET /api/resume/matches` · `POST /api/resume/rematch` | user | Stored matches · AI re-rank |
| `GET/POST /api/resume/insights` | user | Free insights + cached AI review · generate the AI review |
| `POST /api/resume/matches/{id}/ask` | user | SSE stream; `mode`: `question` · `tailor` · `cover_letter` |
| `GET/POST /api/saved…` | user | Tracker: save, status + history, stats, CSV export |
| `POST /api/postings` · `/upload` | user | Manual posting · CSV import |
| `GET/POST/PATCH /api/admin/sources…` | admin | Import sources, runs, run now, re-enable |
| `POST /api/ai/check` · `GET /api/config` · `GET /api/health` | — | Verify a key + list its models · feature flags · liveness |

AI routes read `X-AI-Provider`, `X-AI-Key`, and `X-AI-Model`. Every error is `{"detail": "…", "code": "SNAKE_CASE"}`.

## Project structure

```
COOP-Radar/
├── README.md                     This file (technical)
├── docs/
│   ├── USER_GUIDE.md             Simple guide: use it, put it online without Docker, AI keys, tips
│   ├── HOW_IT_WORKS.md           Plain-language walkthrough + how to explain/pitch it
│   ├── DEPLOY.md                 Render (one click) · VPS + HTTPS · any Docker host · env vars
│   ├── PROJECT_GUIDE.md          Deep dive: every module, data model, testing, recipes
│   ├── progress.md · agentic-workflow.md · speckit-prompts.md · history/
├── Dockerfile · render.yaml · docker-compose.yml · docker-compose.prod.yml · .env.example
├── backend/
│   ├── app/
│   │   ├── main.py · config.py · db.py · redis.py · deps.py · worker.py
│   │   ├── ai.py                 Bring-your-own-key: Claude / ChatGPT / Gemini behind complete() + stream()
│   │   ├── api/                  Routers: postings, auth, me, saved, resume, ai, admin, meta
│   │   ├── services/             postings, resume (matching), insights, demo (temporary accounts), auth, saved, usage, ingest
│   │   ├── ingest/               boards.py (Greenhouse/Lever/Ashby), runner, dedup, skill_match, extract, json_api, rss, embed
│   │   ├── agent/resume_qa.py    Streaming tailor / cover letter / cited Q&A
│   │   ├── schemas/ · models/
│   ├── alembic/versions/         0001–0007
│   ├── seed/                     skills · job_boards (27 employers) · sample postings
│   ├── scripts/start.sh          Production start: migrate → seed → worker → web
│   └── tests/                    api/ · ingest/ · resume/ · eval/ · perf/
├── frontend/src/
│   ├── pages/                    Jobs, posting detail, My resume, Tracker, AI key, Account, Admin
│   ├── components/               Table, filters, tracker board, per-job assistant, rich text, banners
│   └── api/                      apiFetch client + TanStack Query hooks
├── specs/                        Spec Kit feature specs 001–004
├── .specify/                     Constitution, templates, scripts
└── .claude/                      Claude Code settings + skills
```

## Security and privacy

- Visitors' AI keys stay in their browser and are forwarded per request only: never stored, logged, or echoed.
- Resumes are stored as text in the user's account and are deletable any time. Temporary accounts expire after 7 days.
- Passwords are hashed with argon2id. Sessions use HTTP-only Secure cookies. Login, demo/guest creation, CSV upload,
  and key checks are rate-limited.
- SQL takes only bound parameters and whitelisted sort columns. Prompts treat resume and posting text as data, not
  instructions.
- Jobs come only from public job-board APIs meant for syndication. No logins, no scraping, and every posting links
  to the employer.

## Built with Spec Kit + Claude Code

Features were specified and built with the [Spec Kit](https://github.com/github/spec-kit) loop in Claude Code,
governed by `.specify/memory/constitution.md`:
`/speckit-specify → /speckit-clarify → /speckit-plan → /speckit-checklist → /speckit-tasks → /speckit-analyze →
/speckit-implement → /speckit-converge`. Project skills in `.claude/skills/` encode the conventions:

| Skill | Use it for |
|---|---|
| `api-conventions` | Endpoints, schemas, services, safe SQL, error shape, tests |
| `frontend-tables` | Pages, tables, forms, hooks, URL state, accessibility |
| `agent-tools` | Anything AI: providers, prompts, injection guards, fallbacks, evals |
| `db-migration` | Safe Alembic migrations (autogenerate → review → round-trip → `alembic check`) |
| `log-agentic-work` | Append an entry to `docs/agentic-workflow.md` |

Rules from the constitution: filtering, sorting, and paging happen in SQL; every endpoint has schemas and tests;
p95 under 300 ms on 10k postings; AI cites sources or says it doesn't know; secrets only in env vars; respectful,
public-API-only data collection; accessible, mobile-first UI. Commits are conventional (`feat:`, `fix:`, …) with
no AI attribution.

## Roadmap

- [x] Browse & search · accounts & tracker · ingestion & semantic search · AI resume matcher
- [x] One-container website, Render Blueprint, bring-your-own-key for Claude / ChatGPT / Gemini
- [x] Real jobs from 27 employers' career boards; resume-first site with insights, tailoring, guest accounts
- [ ] Email alerts for new matches · more boards and school feeds · per-school location presets
- [ ] Tool-using assistant (search / compare / save with confirmation) exposed over MCP

## License

MIT
