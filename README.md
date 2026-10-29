# CoopRadar

**A job board for co-op students that knows who you are.** CoopRadar imports real co-op, internship and
entry-level jobs in every field from about 1,700 employers' own career pages and the Government of Canada's Job
Bank, reads what each job description asks for (programs of study, graduation years, skills), and matches them to a
student's resume: their program, graduation year, wanted term and skills. Every match says why it fits. Matching runs in SQL, so it's free and instant; an optional
bring-your-own-key AI layer (Claude, ChatGPT or Gemini) adds resume reviews, tailoring and cover letters.

[![CI](https://github.com/mbendari7/COOP-Radar/actions/workflows/ci.yml/badge.svg)](https://github.com/mbendari7/COOP-Radar/actions/workflows/ci.yml)

**Live site:** _add your link after deploying_ ·
**Not a developer?** Read [Using CoopRadar](guides/using-coopradar/README.md) ·
**How it's built and how to explain it:** [How it works](guides/how-it-works/README.md)

```bash
python start.py      # sets everything up the first time, then opens http://localhost:8000
```

![Jobs page: search bar, quick filters, the results list and the selected job's details](docs/images/jobs.png)

| Matches that explain themselves | On a phone |
|---|---|
| ![Resume matches with "why it fits" reasons and skills](docs/images/matches.png) | ![Jobs page on a phone](docs/images/phone.png) |

---

## Features

| | |
|---|---|
| **Opens fast** | The first page of jobs comes from a copy a CDN keeps and the browser saves, so it shows in under a second even while the free server is waking up. A short note says when fresher jobs are on the way. A free GitHub workflow keeps the server awake through the day. See [Make it load fast](#make-it-load-fast). |
| **Real jobs, every field** | Jobs from ~1,700 employers' own career sites via the public Greenhouse, Lever, Ashby, SmartRecruiters and Workday job-board APIs, plus Workable's job search, The Muse's internships, Himalayas' remote jobs open to Canada, Simplify's public internship and new grad lists and the Government of Canada's **Job Bank** (its student and apprentice jobs, and searches for each kind of program: nursing, personal support, teaching, early childhood education, social work, trades, hospitality, engineering technology, accounting, marketing and more), imported every 6 hours: tech, banks, insurers, energy, health and pharma, aerospace, accounting, food, retail, universities, hospitals, cities and small local employers. Every job in Canada, plus US co-op, internship, new grad and entry level roles. Each job shows its work term, when it runs and how long it is, kept apart from the graduation year it asks for. New jobs since your last visit, and an RSS feed for any search. Optional Adzuna key adds student jobs it gathers from employer sites in every field. |
| **Term and length** | Each job's term season (Winter, Spring, Summer, Fall) and length (4, 8, 12 or 16 months) are read from its title and description. Filter by season and length, sort by term start or by length, and see both on every row. Jobs that don't say are marked "Not stated" instead of guessed. |
| **Job-board search** | What / Where search and a filter sidebar that is always in view (it folds open in place on phones): level, country, on-site / hybrid / remote, job type, program or major, graduation year, province or state, city, date posted, term, length, company, skills. Results list beside a details panel; everything lives in the URL. |
| **Reads the job description** | At import, each description is parsed for the programs of study it names ("Bachelor's in Computer Science, Engineering...") and the graduation years it wants ("graduating in December 2027 or 2028"). |
| **Reads the resume** | Upload a PDF or Word file with no sign-up. CoopRadar finds the student's program, degree and graduation year in the education section; the student can correct them. |
| **Co-op matching, lenient** | Students apply to lots of co-ops, so matching only filters on hard choices (picked job types, place, country, level). Program, graduation year, term and length move jobs up or down instead of hiding them. Up to 60 matches, each with plain "why it fits" reasons, and a fair warning when a job asks for another graduation year. |
| **Make your resume fit** | For any job, free and with no AI: yes or no checks (program, grad year, availability line, French, numbers in bullets), the edits to make in order, and the job's skills and words split into ones the resume has and ones worth adding if true. |
| **Resume feedback** | Skills employers can see on the resume, and the most-requested skills it's missing. Free. |
| **AI, bring your own key** | Resume review, AI re-ranking, per-job tailoring plans, cover letter openers and cited Q&A, streamed. The key stays in the visitor's browser. |
| **Tracker** | Save jobs, move them through statuses with dated notes, deadlines this week, CSV export. List or drag and drop board. |

## Design

CoopRadar looks like a Canadian post office, not a template job board, kept clean and modern: a postal red top bar,
airmail blue for links and anything picked, soft rounded corners, pill shaped chips, white cards on a light grey
page, Inter for reading and Archivo for titles. Every job's details wear a round **postmark** with its city and the
day it was posted, which stamps red when you pick the job. Match scores use the same stamp, and the time left to
apply is drawn as a bar to scale.

The tokens live in `frontend/tailwind.config.ts`, the shared buttons, fields and chips in `frontend/src/index.css`,
and the reasons behind each choice in [`DESIGN.md`](DESIGN.md). Product facts the design worked from are in
[`PRODUCT.md`](PRODUCT.md).

## How it works

```mermaid
flowchart LR
    B["Browser<br/>React + TypeScript"] -->|"/api (JSON, HTTP-only cookie)"| API
    subgraph Server["One Python process (python start.py)"]
      API["FastAPI<br/>routers → services → SQL"]
      JOBS["Background importer<br/>every 6 h"]
    end
    API --> DB[("PostgreSQL 16<br/>full-text · arrays · JSONB · pgvector")]
    JOBS --> DB
    JOBS -->|"public JSON APIs and feeds"| BOARDS["~1,700 career boards + job feeds<br/>Greenhouse · Lever · Ashby · Workday · Job Bank · ..."]
    CDN["Vercel CDN<br/>pages + job snapshot"] -.->|"cached copy while the server sleeps"| B
    API -->|"visitor's own key, per request"| AI["Claude · ChatGPT · Gemini"]
```

1. **Import** (`backend/app/ingest/`): one adapter per job-board system or feed. Keeps Canadian jobs and US student roles,
   parses locations ("Hybrid - New York" → New York, NY; "Vancouver, WA" is not Canada), fetches descriptions only
   for kept jobs (some boards are 30 MB), de-duplicates, tags skills, and extracts `fields_of_study` and
   `grad_years` from degree and graduation sentences (`backend/app/services/education.py`). Feeds that only show
   the newest days, like Job Bank's, keep their jobs open for 21 days after they leave the feed.
2. **Search** (`GET /api/postings`): every filter is a SQL clause in one query, sorted and paged in Postgres. Job
   types are constant title regexes; programs use array overlap; graduation year keeps jobs that name it or don't
   say. `GET /api/postings/snapshot` gives the unfiltered first page, the filter choices and the first job's
   details in one reply that is the same for everyone, so a CDN can cache it.
3. **Resume**: text extracted with pypdf / python-docx; program, degree and graduation year detected from the
   education lines; the student's own choices override them.
4. **Matching** (`backend/app/services/resume.py`), one SQL expression out of 100:

   | Skills on the resume (senior titles count half) | Co-op / intern / new-grad title | Names their field | Names their grad year | Their term | Their keywords |
   |---|---|---|---|---|---|
   | 65 | 15 | 10 | 5 | 5 | +20 |

   Plus filters: their job types (or their program's), countries, location (remote always counts), work mode,
   level, and no jobs asking for a different graduation year. Each match gets "why it fits" notes built from the
   same data.
5. **AI (optional)**: `backend/app/ai.py` wraps the official Anthropic, OpenAI and Google GenAI SDKs behind
   `complete()` and `stream()`. Prompts treat documents as data, never invent experience, and cite sources.

The full walkthrough is in **[How it works](guides/how-it-works/README.md)**.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | **React 18**, **TypeScript**, **Vite**, **Tailwind CSS**, **TanStack Query** and **TanStack Table**, **React Router**, dnd-kit, types generated from the API's OpenAPI schema |
| Backend | **Python 3.12**, **FastAPI**, **Pydantic v2**, **SQLAlchemy 2.0** (async, typed), asyncpg, httpx, argon2, pypdf, python-docx |
| Database | **PostgreSQL 16**: generated `tsvector` + GIN full-text search, array overlap, title regex, JSONB, **pgvector** (optional smart search); **Alembic** migrations `0001` to `0016` |
| Background work | asyncio tasks inside the web process with a 6-hourly scheduler (3 boards at a time, oldest first, starting a minute after the server, old closed jobs deleted after 30 days); no separate worker or queue |
| AI | Bring your own key: Claude, ChatGPT or Gemini via their official SDKs; Server-Sent Events streaming |
| Testing | **pytest** (~440 tests, incl. a p95 < 300 ms budget on 10,000 jobs), **Vitest** + Testing Library (69), **Playwright** end-to-end in a real browser (7) |
| Quality | ruff, mypy `--strict`, ESLint, `tsc`; OpenAPI types checked for drift |
| Delivery | **GitHub Actions** CI (lint, types, migration round-trip, tests, then boots the real site and runs Playwright against it); **Render** + **Neon** free hosting; optional **Vercel** front |

## Run it yourself

You need **Python 3.12+** and **Node.js 20+**. No Docker and no database to install.

```bash
git clone https://github.com/mbendari7/COOP-Radar.git && cd COOP-Radar
python start.py          # first run takes a few minutes, then → http://localhost:8000
```

The first run creates `backend/.venv`, installs packages (with [uv](https://docs.astral.sh/uv/) if you have it),
builds the React site, and starts a private PostgreSQL 16 + pgvector in `~/.coopradar` using the
[`pgserver`](https://pypi.org/project/pgserver/) package. Then it migrates, seeds, serves the site and API on one
port, and imports real jobs in the background (the first full pass over ~1,700 boards takes about an hour).

| Task | Command |
|---|---|
| Develop with live reload | `python start.py --dev` → site on :5173 (Vite HMR), API on :8000 (docs at `/docs`) |
| Run like a host does | `python start.py --hosted` (needs `DATABASE_URL`; serves on `$PORT`) |
| Backend checks | in `backend/` with the venv active and `pip install -e ".[dev]"`: `ruff check . && mypy app && pytest -q -m "not perf"` (needs `DATABASE_URL` for a throwaway database) |
| Speed budget | `pytest -q -m perf -s` |
| Frontend checks | `cd frontend && npm run lint && npm run typecheck && npm test && npm run build` |
| Browser tests | start the site, then `cd frontend && npx playwright install chromium && npm run test:e2e` (`E2E_BASE_URL` if not on :8000) |
| Reset local data | stop the site and delete `~/.coopradar` |

## Host it for free

The best free setup, at no cost and with no credit card:

| Piece | Service (free plan) | Why this one |
|---|---|---|
| Website + API | **[Render](https://render.com)** web service | Runs Python directly; `render.yaml` configures everything |
| Database | **[Neon](https://neon.tech)** Postgres | Doesn't expire (Render's free database is deleted after 30 days), 0.5 GB is about 10x what CoopRadar needs, includes pgvector |
| Awake and fresh | **GitHub Actions** (`.github/workflows/refresh-jobs.yml`) | Render's free server sleeps after ~15 idle minutes, takes up to a minute to wake and only imports while awake; this pings it every 10 minutes from 7 am to 1 am Eastern |
| Fast front (recommended) | **[Vercel](https://vercel.com)** | Serves the pages from a CDN, keeps a copy of the first page of jobs so it opens at once, and forwards `/api` to Render (`vercel.json`) |

**Steps (about 15 minutes, all in the browser):**

1. **Database.** Sign up at [neon.tech](https://neon.tech) and create a project (any name, the region nearest
   you). On the dashboard click **Connect** and copy the connection string (turn *Connection pooling* off). It
   looks like `postgresql://user:password@ep-xxx.region.aws.neon.tech/neondb?sslmode=require`.
2. **Website.** Sign up at [render.com](https://render.com) with GitHub. Click **New**, then **Blueprint**, and pick
   your copy of this repo. Render reads `render.yaml`.
3. When it asks for settings, paste the Neon string into **`DATABASE_URL`**. Leave `ANTHROPIC_API_KEY` and
   `OPENAI_API_KEY` blank: visitors bring their own AI key. Click **Apply**.
4. Wait about 5 to 10 minutes for the first build. Your site is at `https://coopradar-xxxx.onrender.com`. Within a few
   minutes it imports ~2,800 jobs.
5. **Keep it awake and fresh.** On GitHub: your repo, **Settings**, **Secrets and variables**, **Actions**,
   **Variables**, **New repository variable**: name `SITE_URL`, value your Render address (no trailing slash). The
   *Keep the site awake* workflow then pings it every 10 minutes through the day. Free for public repositories; for
   a private one use [UptimeRobot](https://uptimerobot.com) or [cron-job.org](https://cron-job.org) on
   `https://<your-site>.onrender.com/api/health` every 10 minutes instead.
6. **Vercel (recommended, it makes the first load instant).** In `vercel.json`, change the `/api` `destination` to your Render address **and keep
   `/api/:path*` on the end**, for example `"destination": "https://coopradar-xxxx.onrender.com/api/:path*"`.
   Commit and push. At [vercel.com](https://vercel.com), **Add New**, **Project**, import the repo, **Deploy**.
   Visitors use the `*.vercel.app` address and `/api` is forwarded to Render, so logins keep working.
7. **Check it.** Open `https://<your-project>.vercel.app/api/postings?page_size=10`. You should see JSON with
   `items`. If you see a web page instead, the `/api/:path*` ending is missing and the jobs page will say the jobs
   didn't load.

**What "free" means here:** overnight, or without the workflow, Render puts the server to sleep and waking it takes
about a minute. With the Vercel front visitors still see jobs at once (see below); only searching and opening other
jobs waits for the server. For an always-on site, Render's paid instance is a few dollars a month. Why not Vercel
alone? Vercel runs code only for a moment per request, but
CoopRadar needs a server that keeps running to import jobs and a database. Other hosts and a VPS setup are in
[docs/DEPLOY.md](docs/DEPLOY.md).

## Make it load fast

The slow first load on a free plan is Render waking its sleeping server (30 to 60 seconds), not the database or
the code. CoopRadar works around it in layers, all free:

| Layer | What it does | Where |
|---|---|---|
| Ready made first page | `GET /api/postings/snapshot` is the same for every visitor: the first 25 co-op jobs, the filter choices and the first job's details. Vercel's CDN keeps it for 5 minutes and then keeps serving its copy for up to a week while it fetches a new one, so a sleeping server never holds up the first page | `backend/app/api/postings.py`, `vercel.json` |
| Saved in the browser | Each visit saves the snapshot, so a returning visitor sees jobs before any reply comes back | `frontend/src/api/postings.ts` (`useSnapshot`) |
| Honest waiting | If the server still hasn't answered after 4 seconds, a short note says it is waking up instead of showing a blank page | `frontend/src/pages/PostingsListPage.tsx` |
| Awake through the day | The *Keep the site awake* workflow pings it every 10 minutes from 7 am to 1 am Eastern. That is about 560 hours a month, inside Render's 750 free hours, and it sleeps at night so the importer leaves room in Neon's free database time | `.github/workflows/refresh-jobs.yml` |
| Fast wake up | Startup skips reloading the 1,700 career boards when nothing changed (a fingerprint in `kv_store`), loads them in two SQL statements when it does, serves visitors before seeding, and waits a minute before importing | `start.py`, `backend/seed/__main__.py`, `backend/app/jobs.py` |
| Small, cached files | Replies over 1 KB are gzipped (a page of jobs is about 6 times smaller), the hashed JS and CSS are cached for a year with React in its own file, and fonts load without blocking the page | `backend/app/main.py`, `frontend/vite.config.ts`, `frontend/index.html` |

If Neon's dashboard shows the database close to its monthly compute limit, set `INGEST_INTERVAL_HOURS=12` on
Render so the importer runs half as often.

## Configuration

Environment variables (or a `.env` file), documented in [`.env.example`](.env.example). None are required on your
own computer.

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | local database from `start.py` | Postgres. `postgres://`, `?sslmode=` and Neon's `channel_binding` are handled. Required on a host |
| `INGEST_US_JOBS` | `students` | US jobs to import: `students` (co-op, intern, new grad, junior, entry level), `all` (can be tens of thousands), or `none` |
| `INGEST_LOCATION_FILTER` | Canada | Regex for the Canadian locations to keep |
| `INGEST_INTERVAL_HOURS` | `6` | How often each board is re-imported |
| `INGEST_START_DELAY_SECONDS` | `60` | Wait after the server starts before the first import, so a site that just woke up answers quickly |
| `SEED_FORCE` | `false` | Load the skills and career boards on start even when nothing changed |
| `DEMO_ENABLED` | `true` | "Try the demo" and uploading without an account (temporary accounts, 7 days) |
| `ANTHROPIC_API_KEY` · `OPENAI_API_KEY` | empty | Optional owner keys: shared Claude fallback (capped by `AI_DAILY_LIMIT`) · smart search |
| `REDIS_URL` | empty | Optional: sessions and rate limits in Redis instead of Postgres |
| `SEED_JOB_BOARDS` · `SEED_SAMPLE_POSTINGS` | `true` · `false` | Real career boards · made-up sample postings |
| `COOKIE_SECURE` | `true` | Keep on for HTTPS (`start.py` turns it off locally) |

## API

| Method & path | Auth | Purpose |
|---|---|---|
| `GET /api/postings` | optional | Search, filter, sort, paginate: `q`, `category`, `country`, `program`, `grad_year`, `province`, `city`, `work_mode`, `posted_within`, `term`, `duration`, `company`, `skills`, `students_only`, `hide_senior`, `show_expired`, `sort`, `order`, `page`, `page_size` → `{items, total, page, page_size}`; each item has `role`, `country`, `grad_years`, `fields_of_study` |
| `GET /api/postings/{id}` · `/{id}/similar` · `/meta/filters` | | Detail · similar · filter values with counts (job types, countries, work modes, programs) |
| `GET /api/postings/snapshot` | | The unfiltered first page, filter values and the first job's details in one cacheable reply |
| `POST /api/auth/register` · `login` · `logout` · `demo` · `guest` | | Sessions; `demo` = pre-filled temporary account, `guest` = empty one |
| `POST/GET/DELETE /api/resume` | user | Upload (`preferences` JSON form field) / metadata / delete |
| `PUT /api/resume/preferences` | user | Save program, degree, graduation year, term, countries, job types, location, work mode, level, keywords and re-match (free) |
| `GET /api/resume/matches` · `POST /api/resume/rematch` | user | Stored matches with `fit_notes` and the detected `education` · AI re-rank |
| `GET/POST /api/resume/insights` | user | Free insights + cached AI review · generate the AI review |
| `POST /api/resume/matches/{id}/ask` | user | SSE stream: `question` · `tailor` · `cover_letter` |
| `GET/POST /api/saved…` · `/api/me…` · `/api/admin/sources…` | user / admin | Tracker · account · import sources |

Errors are always `{"detail": "...", "code": "SNAKE_CASE"}`. AI routes read `X-AI-Provider`, `X-AI-Key` and
`X-AI-Model`.

## Project structure

```
COOP-Radar/
├── README.md                     This file
├── PRODUCT.md · DESIGN.md        Who it's for · the postal design system
├── guides/
│   ├── using-coopradar/          For visitors: use it, run it, troubleshoot
│   └── how-it-works/             For the builder: stack, flow, testing, hosting, interview prep
├── docs/                         DEPLOY (other hosts) · PROJECT_GUIDE (every module) · images · logs
├── start.py                      One command: set up, migrate, seed, serve (local, --dev, --hosted)
├── render.yaml · vercel.json · .env.example
├── .github/workflows/            ci.yml (all checks + Playwright) · refresh-jobs.yml (keeps the free site awake and fresh)
├── backend/
│   ├── app/
│   │   ├── api/                  Routers
│   │   ├── services/             postings, resume (matching), education, categories, insights, auth, ...
│   │   ├── ingest/               boards.py (Greenhouse/Lever/Ashby/SmartRecruiters), workday.py, jobbank.py, workable, themuse, himalayas, simplify, adzuna, terms.py (term and length), runner, dedup, skill_match
│   │   ├── schemas/ · models/ · agent/ · ai.py · jobs.py · store.py
│   ├── alembic/versions/         0001 to 0016
│   ├── seed/                     skills · job_boards (~1,700 employers + job feeds) · sample postings
│   └── tests/                    api/ · ingest/ · resume/ · eval/ · perf/
└── frontend/
    ├── src/                      pages/ · components/ · api/ (client + TanStack Query hooks)
    ├── tests/                    Vitest
    └── e2e/                      Playwright
```

## Security and privacy

- Visitors' AI keys stay in their browser and are forwarded per request only: never stored, logged or echoed.
- Resumes are stored as text in the user's account and can be deleted any time. Temporary accounts expire after 7 days.
- Passwords use argon2id; sessions are HTTP-only Secure cookies; login, account creation, CSV uploads and key checks are rate-limited.
- SQL takes only bound parameters and whitelisted sort columns. Prompts treat resume and posting text as data.
- Jobs come only from public job-board APIs and feeds meant for sharing: no logins, no scraping, robots.txt respected (Job Bank's 5 second pause included), every job links to the employer or Job Bank.

## Built with Spec Kit + Claude Code

Features were specified and built with the [Spec Kit](https://github.com/github/spec-kit) loop in Claude Code,
governed by `.specify/memory/constitution.md` (filter in SQL, every endpoint has schemas and tests, p95 under
300 ms on 10,000 postings, AI cites sources or says it doesn't know, secrets only in env vars). Project skills in
`.claude/skills/` encode the conventions; the log is in `docs/agentic-workflow.md`.

## Roadmap

- [x] Search and tracker · ingestion · resume matching · bring-your-own-key AI
- [x] One command to run (`python start.py`), free hosting (Render + Neon + GitHub Actions), optional Vercel front
- [x] Job-board redesign; co-op matching by program, graduation year and term; ~170 employers; US internships; Playwright
- [x] Postal look (postmarks, no card boxes, Archivo), plain language comments across the code
- [x] Instant first load (CDN snapshot, browser copy, keep awake), Job Bank jobs for every program, quieter scroll bars
- [ ] Email alerts for new matches · school job boards with public feeds · learning from which jobs students save

## License

MIT
