# CoopRadar

**A free job board for co-op students that reads your resume and tells you which jobs fit, and why.**

CoopRadar imports real co-op, internship, student and entry level jobs in every field from about 1,700 employers'
own career pages and the Government of Canada's Job Bank. It reads each job description for the programs of study,
graduation years, work term and skills it asks for. A student drops in a resume (no sign up) and gets the jobs that
fit their program, graduation year, term and skills, each with plain "why it fits" notes. Matching runs in SQL, so
it is free and instant. An optional bring your own key AI layer (Claude, ChatGPT or Gemini) adds resume reviews,
tailoring and cover letters.

[![CI](https://github.com/mbendari7/COOP-Radar/actions/workflows/ci.yml/badge.svg)](https://github.com/mbendari7/COOP-Radar/actions/workflows/ci.yml)

**Live site:** [COOPRadar](https://coop-radar-qdrc.vercel.app/) ·
**Students:** [Using CoopRadar](guides/using-coopradar/README.md) ·
**Builders and interviews:** [How it works](guides/how-it-works/README.md) ·
**Running the site:** [Owner's handbook](guides/owner-handbook/README.md)

```bash
python start.py      # sets everything up the first time, then opens http://localhost:8000
```

![Find jobs: search row, filter sidebar, the results list and the picked job's details with its postmark](docs/images/jobs.png)

| Matches that explain themselves | Make your resume fit a job (free, no AI) |
|---|---|
| ![Resume matches with a score stamp, why it fits, and skills on the resume or worth adding](docs/images/matches.png) | ![Checks, edits to make in order, and skills split into ones you have and ones worth adding](docs/images/fit.png) |
| **Application tracker** | **On a phone** |
| ![Tracker board with a column per stage and deadlines this week](docs/images/tracker.png) | <img src="docs/images/phone.png" alt="Jobs page on a phone" width="260"> |

---

## Contents

1. [Which document do I read?](#which-document-do-i-read)
2. [What it does](#what-it-does)
3. [Where the jobs come from](#where-the-jobs-come-from)
4. [How it works](#how-it-works)
5. [Tech stack](#tech-stack)
6. [Run it on your computer](#run-it-on-your-computer)
7. [Host it for free](#host-it-for-free)
8. [Make it load fast](#make-it-load-fast)
9. [Configuration](#configuration)
10. [API](#api)
11. [Project structure](#project-structure)
12. [Testing and quality](#testing-and-quality)
13. [Security and privacy](#security-and-privacy)
14. [Built with Spec Kit and Claude Code](#built-with-spec-kit-and-claude-code)
15. [Roadmap](#roadmap)

---

## Which document do I read?

This README is the front door. Everything else is one click away.

| You are... | Read | What's in it |
|---|---|---|
| A student or anyone who just wants to use it | [Using CoopRadar](guides/using-coopradar/README.md) | Find jobs, match your resume, the tracker, a free AI key, tips, fixes. No code |
| The owner keeping the site running | [Owner's handbook](guides/owner-handbook/README.md) | Weekly checks, free plan limits, adding employers, updating, before you commit, fixing a broken site |
| Learning the build or preparing for an interview | [How it works](guides/how-it-works/README.md) | The stack piece by piece, the flow step by step, how to explain it, interview answers |
| Changing or debugging the code | [Project guide](docs/PROJECT_GUIDE.md) | Every module, the database, feature deep dives, recipes, testing |
| Hosting somewhere other than Render | [Deploy](docs/DEPLOY.md) | Render + Neon in detail, Vercel in front, other hosts, your own server |
| Looking at the design | [DESIGN.md](DESIGN.md) · [PRODUCT.md](PRODUCT.md) | The postal look and why · who it is for |
| Curious how AI helped build it | [Agentic workflow log](docs/agentic-workflow.md) · [Progress](docs/progress.md) | What the AI did each session, what was checked |

All guides are also listed in [guides/README.md](guides/README.md).

---

## What it does

| | |
|---|---|
| **Opens fast** | The first page of jobs comes from a copy a CDN keeps and the browser saves, so it shows in about a second even while the free server wakes up. A short note says when fresher jobs are on the way. See [Make it load fast](#make-it-load-fast). |
| **Real jobs, every field** | About 13,700 open jobs in a full import: every job in Canada that the sources list (about 5,400), plus US co-op, internship, new grad and entry level roles (about 8,300). Software and engineering, but also nursing, teaching, early childhood education, trades, hospitality, business, banks, hospitals, cities and small local employers. Refreshed every 6 hours. |
| **Job search** | A What / Where search row and a filter sidebar that is always in view (it folds open in place on phones): work term, length, level, country, province or state, city, work mode, job type, program, graduation year, date posted, company and skills. Results list beside a details panel. Every filter lives in the URL, so a search is a link you can share. |
| **Term and length** | Each job's term season (Winter, Spring, Summer, Fall) and length (4, 8, 12 or 16 months) are read from its title and description and shown on every row. Jobs that don't say are marked "Not stated", never guessed, and still shown unless you ask for only exact matches. |
| **Reads the job description** | At import, each description is read for the programs of study it names ("Bachelor's in Computer Science, Engineering...") and the graduation years it wants ("graduating in December 2027 or 2028"). |
| **Reads the resume** | Upload a PDF or Word file with no sign up. The student's program, degree and graduation year come from the education section; they can correct them. |
| **Lenient co-op matching** | Students apply widely, so matching only filters on hard choices (job types, place, country, level). Program, graduation year, term and length move jobs up or down instead of hiding them. Up to 60 matches, each with a score stamp and "why it fits" reasons. |
| **Make your resume fit** | For any job, free and with no AI: yes or no checks (program, grad year, availability line, numbers in bullets), the edits to make in order, and the job's skills and words split into ones the resume has and ones worth adding if true. |
| **Resume feedback** | The skills employers can see on the resume, and the most requested skills it is missing. Free. |
| **AI, bring your own key** | Resume review, AI re-ranking, per job tailoring plans, cover letter openers and cited answers to questions, streamed word by word. The key stays in the visitor's browser. |
| **New jobs and alerts** | "New since your last visit" for any search, a "Newly added" sort, and an RSS feed for any search that a feed reader or feed to email service can follow. |
| **Tracker** | Save jobs, move them through stages with dated notes, see deadlines this week, export to CSV. List view or drag and drop board. |

---

## Where the jobs come from

Only public job board APIs and feeds that exist so jobs can be shown on other sites. No logins, no scraping of
pages, robots.txt respected, and every job links to the employer (or Job Bank) to apply.

| Source | What it brings | Code |
|---|---|---|
| **Employer career boards** on Greenhouse, Lever, Ashby, SmartRecruiters, Workday, Recruitee, BambooHR, Rippling and Oracle Cloud | About 1,700 employers: 185 hand picked (`job_boards.py`) plus about 1,500 found through Common Crawl's free URL index (`discovered_boards.json`). Workday covers most big employers outside tech: banks, insurers, energy, health, retail, universities | `ingest/boards.py`, `workday.py`, `ats.py`, `oracle.py` |
| **Government of Canada Job Bank** | Its student and apprentice jobs, plus about 30 searches for programs with co-ops: nursing, personal support, early childhood education, teaching, social work, trades, cooking, engineering technology, accounting, marketing and more | `ingest/jobbank.py` |
| **Workable** job search | Every Canadian job and US student roles from thousands of small employers | `ingest/workable.py` |
| **Simplify** and other public GitHub lists | Thousands of internship and new grad roles, each with its terms | `ingest/simplify.py`, `github_lists.py` |
| **The Muse** | Internships (mostly US), up to 90 days old | `ingest/themuse.py` |
| **Himalayas** | Remote jobs open to people in Canada | `ingest/himalayas.py` |
| **Adzuna** (optional, paid key) | Student jobs Adzuna gathers from employer sites | `ingest/adzuna.py` |

LinkedIn, Indeed, Glassdoor and Google Jobs are not used: their terms forbid automated collection, and most of
their listings are reposts of jobs on the employers' own career pages, which CoopRadar reads directly.

---

## How it works

```mermaid
flowchart LR
    B["Browser<br/>React + TypeScript"] -->|"/api (JSON, HTTP-only cookie)"| API
    CDN["Vercel CDN<br/>pages + job snapshot"] -.->|"cached copy while the server sleeps"| B
    subgraph Server["One Python process (python start.py)"]
      API["FastAPI<br/>routers → services → SQL"]
      JOBS["Background importer<br/>every 6 h, 3 sources at a time"]
    end
    API --> DB[("PostgreSQL 16<br/>full-text · arrays · JSONB · pgvector")]
    JOBS --> DB
    JOBS -->|"public JSON APIs and feeds"| SRC["~1,700 career boards + job feeds<br/>Greenhouse · Lever · Workday · Job Bank · ..."]
    API -->|"visitor's own key, per request"| AI["Claude · ChatGPT · Gemini"]
```

1. **Import** (`backend/app/ingest/`). One adapter per job board system or feed. Keeps every Canadian job and US
   student roles, reads locations ("Hybrid - New York" is New York, NY; "Vancouver, WA" is not Canada), fetches
   descriptions only for kept jobs (some boards are 30 MB), skips duplicates, tags skills, and reads the term,
   length, programs and graduation years. Feeds that only show the newest days, like Job Bank's, keep their jobs
   open for 21 days after they leave the feed.
2. **Search** (`GET /api/postings`). Every filter is a SQL clause in one query, sorted and paged in Postgres. Job
   types are title patterns; programs use array overlap; graduation year keeps jobs that name it or don't say.
   `GET /api/postings/snapshot` is the unfiltered first page in one reply that is the same for everyone, so a CDN
   can cache it.
3. **Resume**. Text comes out with pypdf or python-docx; the program, degree and graduation year are read from the
   education lines. The student's own choices win over what was read.
4. **Matching** (`backend/app/services/resume.py`). One SQL expression scores every open job out of 100:

   | Skills on the resume (senior titles count half) | Co-op, intern or new grad title | Names their program | Names their grad year | Their term | Their length | Their keywords | Asks for another grad year |
   |---|---|---|---|---|---|---|---|
   | 65 | 15 | 10 | 5 | 5 | 5 | +20 | minus 10 |

   Capped at 100. Only hard choices filter (job types, countries, location with remote always counting, work mode,
   level); everything else moves a job up or down. Each match gets "why it fits" notes built from the same data.
   The weights are the `_W_*` constants at the top of `resume.py`.
5. **AI (optional)**. `backend/app/ai.py` wraps the official Anthropic, OpenAI and Google GenAI SDKs behind
   `complete()` and `stream()`. Prompts treat the resume and posting as data, never invent experience, and cite
   their sources.

The full walkthrough is in **[How it works](guides/how-it-works/README.md)**; every module is in the
**[Project guide](docs/PROJECT_GUIDE.md)**.

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | **React 18**, **TypeScript**, **Vite 6**, **Tailwind CSS**, **TanStack Query** and **TanStack Table**, **React Router**, dnd-kit; API types generated from the OpenAPI schema |
| Backend | **Python 3.12**, **FastAPI**, **Pydantic v2**, **SQLAlchemy 2.0** (async, typed `Mapped[]`), asyncpg, httpx, argon2, pypdf, python-docx |
| Database | **PostgreSQL 16**: generated `tsvector` + GIN full-text search, array overlap, title regex, generated term columns, JSONB, **pgvector** (optional smart search); **Alembic** migrations `0001` to `0016` |
| Background work | asyncio tasks inside the web process (`app/jobs.py`): a scheduler imports 3 sources at a time, oldest first, starting a minute after the server, and deletes jobs closed over 30 days ago. No separate worker or queue |
| Sessions | HTTP-only cookie → a Postgres `kv_store` table (or Redis if `REDIS_URL` is set), 7 day rolling expiry |
| AI | Bring your own key: Claude, ChatGPT or Gemini through their official SDKs; Server-Sent Events streaming |
| Testing | **pytest** (457 tests, including a p95 under 300 ms budget on 10,000 jobs), **Vitest** + Testing Library (72), **Playwright** in a real browser (9) |
| Quality | ruff, mypy `--strict`, ESLint, `tsc`; OpenAPI types checked for drift; `alembic check` |
| Delivery | **GitHub Actions** CI; **Render** web service + **Neon** Postgres, both free; optional **Vercel** front; a scheduled workflow keeps the free site awake |

---

## Run it on your computer

You need **Python 3.12+** and **Node.js 20+**. No Docker and no database to install.

```bash
git clone https://github.com/mbendari7/COOP-Radar.git
cd COOP-Radar
python start.py          # first run takes a few minutes, then opens http://localhost:8000
```

The first run creates `backend/.venv`, installs packages (with [uv](https://docs.astral.sh/uv/) if you have it),
builds the React site, and starts a private PostgreSQL 16 + pgvector in `~/.coopradar` using the
[`pgserver`](https://pypi.org/project/pgserver/) package. Then it migrates, seeds, serves the site and API on one
port, and imports real jobs in the background (the first jobs show within minutes; a full pass over every source
takes about an hour). Next time it starts in seconds.

| Task | Command |
|---|---|
| Develop with live reload | `python start.py --dev` → site on :5173 (Vite HMR), API on :8000 (docs at `/docs`) |
| Start without importing jobs | `BACKGROUND_JOBS=false python start.py --no-browser --port 8123` |
| Run like a host does | `python start.py --hosted` (needs `DATABASE_URL`; serves on `$PORT`) |
| Backend checks | in `backend/`, venv active, `pip install -e ".[dev]"`, `DATABASE_URL` = a throwaway Postgres with pgvector: `ruff check . && mypy app && pytest -q -m "not perf" && alembic check` |
| Speed budget | `pytest -q -m perf -s` |
| Frontend checks | `cd frontend && npm run lint && npm run typecheck && npm test && npm run build` |
| Browser tests | start the site, then `cd frontend && npx playwright install chromium && npm run test:e2e` (`E2E_BASE_URL` if not on :8000, `E2E_CHANNEL=msedge` to use Edge) |
| New database migration | the `/db-migration` skill in Claude Code (autogenerate, review, round trip, `alembic check`) |
| Reset local data | stop the site and delete `~/.coopradar` |

---

## Host it for free

| Piece | Service (free plan) | Why this one |
|---|---|---|
| Website + API | **[Render](https://render.com)** web service | Runs Python directly; `render.yaml` configures everything |
| Database | **[Neon](https://neon.tech)** Postgres | Doesn't expire (Render's free database is deleted after 30 days), includes pgvector |
| Awake and fresh | **GitHub Actions** (`refresh-jobs.yml`) | Render's free server sleeps after about 15 idle minutes and only imports while awake; this pings it every 10 minutes from 7 am to 1 am Eastern |
| Fast front (recommended) | **[Vercel](https://vercel.com)** | Serves the pages from a CDN, keeps a copy of the first page of jobs so it opens at once, and forwards `/api` to Render (`vercel.json`) |

**Steps (about 15 minutes, all in the browser, no credit card):**

1. **Database.** Sign up at [neon.tech](https://neon.tech) and create a project in the region nearest you. Click
   **Connect**, turn *Connection pooling* off and copy the connection string
   (`postgresql://user:password@ep-xxx.region.aws.neon.tech/neondb?sslmode=require`).
2. **Website.** Sign up at [render.com](https://render.com) with GitHub. Click **New**, then **Blueprint**, and pick
   your copy of this repo. Render reads `render.yaml`.
3. Paste the Neon string into **`DATABASE_URL`**. Leave `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` blank: visitors
   bring their own AI key. Click **Apply**.
4. Wait 5 to 10 minutes for the first build. Your site is at `https://coopradar-xxxx.onrender.com`. The first jobs
   arrive within minutes.
5. **Keep it awake.** On GitHub: your repo, **Settings**, **Secrets and variables**, **Actions**, **Variables**,
   **New repository variable**: name `SITE_URL`, value your Render address (no trailing slash). Free for public
   repositories; for a private one point [UptimeRobot](https://uptimerobot.com) or
   [cron-job.org](https://cron-job.org) at `https://<your-site>.onrender.com/api/health` every 10 minutes.
6. **Vercel (recommended).** In `vercel.json`, set the `/api` `destination` to your Render address **and keep
   `/api/:path*` on the end**, like `"https://coopradar-xxxx.onrender.com/api/:path*"`. Push, then at
   [vercel.com](https://vercel.com): **Add New**, **Project**, import the repo, **Deploy**.
7. **Check it.** Open `https://<your-project>.vercel.app/api/postings?page_size=10`. You should see JSON with
   `items`. A web page instead means the `/api/:path*` ending is missing.

**What "free" means here.** Overnight Render puts the server to sleep and waking it takes about a minute; with the
Vercel front visitors still see jobs at once. Neon's free plan has 0.5 GB of storage, a monthly compute allowance
and 5 GB of data transfer a month, so check its usage page now and then (the
[Owner's handbook](guides/owner-handbook/README.md) says what to do if it gets close). For an always on site,
Render's paid instance is a few dollars a month. Why not Vercel alone? Vercel runs code only for a moment per
request, but CoopRadar needs a server that keeps running to import jobs. Other hosts and a VPS are in
[docs/DEPLOY.md](docs/DEPLOY.md).

---

## Make it load fast

The slow first load on a free plan is Render waking its sleeping server (30 to 60 seconds), not the database or
the code. CoopRadar works around it in layers, all free:

| Layer | What it does | Where |
|---|---|---|
| Ready made first page | `GET /api/postings/snapshot` is the same for everyone: the first 25 co-op jobs, the filter choices and the first job's details. Vercel's CDN keeps it for 5 minutes, then keeps serving its copy for up to a week while it fetches a new one | `backend/app/api/postings.py`, `vercel.json` |
| Saved in the browser | Each visit saves the snapshot, so a returning visitor sees jobs before any reply comes back | `frontend/src/api/postings.ts` (`useSnapshot`) |
| Honest waiting | If the server hasn't answered after 4 seconds, a short note says it is waking up | `frontend/src/pages/PostingsListPage.tsx` |
| Awake through the day | Pinged every 10 minutes from 7 am to 1 am Eastern: about 560 of Render's 750 free hours a month | `.github/workflows/refresh-jobs.yml` |
| Fast wake up | Startup skips reloading the career boards when nothing changed (a fingerprint in `kv_store`), loads them in two SQL statements when it does, serves visitors before seeding, and waits a minute before importing | `start.py`, `backend/seed/__main__.py`, `backend/app/jobs.py` |
| Small replies | Replies over 1 KB are gzipped, hashed JS and CSS are cached for a year, fonts don't block the page | `backend/app/main.py`, `frontend/vite.config.ts`, `frontend/index.html` |
| Light on the database | Job lists and imports leave out descriptions and the search column they don't show, filter menus are cached for 2 minutes, and the skills list for an hour, which keeps Neon's free data transfer low | `services/postings.py`, `ingest/runner.py`, `ingest/extract.py` |

---

## Configuration

Environment variables (or a `.env` file), all documented in [`.env.example`](.env.example). None are needed on
your own computer.

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | local database from `start.py` | Postgres. `postgres://`, `?sslmode=` and Neon's `channel_binding` are handled. Required on a host |
| `INGEST_US_JOBS` | `students` | US jobs to import: `students` (co-op, intern, new grad, junior, entry level), `all` (tens of thousands, too big for a free database), or `none` |
| `INGEST_LOCATION_FILTER` | Canada | Regex for the locations to keep (`.*` = everywhere) |
| `INGEST_INTERVAL_HOURS` | `6` | How often each source is re-imported. `12` halves the database work |
| `INGEST_START_DELAY_SECONDS` | `60` | Wait after start before the first import, so a site that just woke up answers quickly |
| `BACKGROUND_JOBS` | `true` | Run the importer inside the web server |
| `SEED_ON_START` · `SEED_FORCE` | `true` · `false` | Load skills and sources at start (skipped when nothing changed) · load even if unchanged |
| `SEED_JOB_BOARDS` · `SEED_SAMPLE_POSTINGS` · `SEED_DEV_SOURCES` | `true` · `false` · `false` | Real sources · about 55 made up jobs (handy offline) · two Admin page fixtures |
| `DEMO_ENABLED` | `true` | "Try the demo" and uploading without an account (temporary accounts, 7 days) |
| `ANTHROPIC_API_KEY` · `OPENAI_API_KEY` | empty | Optional owner keys: shared Claude fallback (capped by `AI_DAILY_LIMIT`, models from `AGENT_MODEL` / `FAST_MODEL`) · smart search and similar jobs |
| `ADZUNA_APP_ID` · `ADZUNA_APP_KEY` | empty | Optional, paid: also import Adzuna's student jobs |
| `REDIS_URL` | empty | Optional: sessions and rate limits in Redis instead of Postgres |
| `COOKIE_SECURE` | `true` | Keep on for HTTPS (`start.py` turns it off locally) |

---

## API

Interactive docs at `/docs` on any running copy.

| Method and path | Auth | Purpose |
|---|---|---|
| `GET /api/postings` | optional | Search, filter, sort, page: `q`, `category`, `country`, `program`, `grad_year`, `province`, `city`, `work_mode`, `posted_within`, `term`, `season`, `duration`, `include_unstated`, `company`, `skills`, `students_only`, `hide_senior`, `show_expired`, `sort`, `order`, `page`, `page_size` → `{items, total, page, page_size}` |
| `GET /api/postings/{id}` · `/{id}/similar` · `/meta/filters` | | Detail · similar jobs · filter choices with counts |
| `GET /api/postings/snapshot` | | Unfiltered first page, filter choices and first job's details in one cacheable reply |
| `GET /api/postings/feed.rss` | | RSS feed of new jobs for any search |
| `POST /api/auth/register` · `login` · `logout` · `demo` · `guest` | | Sessions; `demo` = pre-filled temporary account, `guest` = empty one |
| `GET/DELETE /api/me` · `PATCH /api/me/password` · `POST /api/me/claim` | user | Account and delete · change password · keep a temporary account |
| `POST/GET/DELETE /api/resume` | user | Upload (with `preferences`) / details / delete |
| `PUT /api/resume/preferences` | user | Save program, degree, grad year, term, countries, job types, place, work mode, level, keywords and re-match (free) |
| `GET /api/resume/matches` · `POST /api/resume/rematch` | user | Stored matches with `fit_notes` · AI re-rank |
| `GET /api/resume/align/{id}` | user | Make your resume fit this job (free, no AI) |
| `GET/POST /api/resume/insights` | user | Free feedback + cached AI review · make the AI review |
| `POST /api/resume/matches/{id}/ask` | user | SSE stream: `question` · `tailor` · `cover_letter` |
| `POST /api/ai/check` | | Check a visitor's AI key and list the models it can use |
| `/api/saved…` | user | Tracker: list, save, unsave, change status, events, CSV export |
| `/api/admin/sources…` | admin | Import sources, run history, run now, turn on or off |
| `GET /api/health` · `/api/config` | | Health check · public settings |

Errors are always `{"detail": "...", "code": "SNAKE_CASE"}`. AI routes read the `X-AI-Provider`, `X-AI-Key` and
`X-AI-Model` headers.

---

## Project structure

```
COOP-Radar/
├── README.md                    You are here: the overview and map of every doc
├── CLAUDE.md                    Rules and commands for Claude Code sessions
├── PRODUCT.md · DESIGN.md       Who it's for · the postal design system
├── start.py                     One command: set up, migrate, seed, serve (local, --dev, --hosted)
├── render.yaml · vercel.json    Free hosting: Render Blueprint · Vercel front
├── .env.example                 Every setting, explained
├── guides/
│   ├── using-coopradar/         For students and visitors
│   ├── owner-handbook/          For the owner: keep the site running and change it safely
│   └── how-it-works/            For builders and interviews: stack, flow, how to explain it
├── docs/
│   ├── PROJECT_GUIDE.md         Every module, recipes, testing, troubleshooting
│   ├── DEPLOY.md                Hosting in detail and other hosts
│   ├── agentic-workflow.md      Log of what AI did each session
│   ├── progress.md · speckit-prompts.md · history/
│   └── images/                  README screenshots
├── .github/workflows/           ci.yml (every check + Playwright) · refresh-jobs.yml (keeps the site awake)
├── .claude/skills/              Spec Kit skills + project skills (api-conventions, frontend-tables, ...)
├── .specify/ · specs/           Spec Kit config, constitution and the feature specs 001 to 004
├── backend/
│   ├── app/
│   │   ├── main.py · config.py · db.py · deps.py · store.py · jobs.py · ai.py · llm.py
│   │   ├── api/                 Routers: postings, resume, auth, me, saved, ai, admin, meta
│   │   ├── services/            Logic + SQL: postings, resume (matching), align (resume fit), education,
│   │   │                        categories, insights, feed, saved_postings, auth, demo, usage, ingest
│   │   ├── ingest/              Adapters (boards, workday, ats, oracle, jobbank, workable, simplify,
│   │   │                        github_lists, themuse, himalayas, adzuna), runner, terms, dedup,
│   │   │                        skill_match, extract, embed
│   │   ├── agent/               Streamed tailor, cover letter and Q&A
│   │   ├── schemas/ · models/   Pydantic schemas · SQLAlchemy tables
│   ├── alembic/versions/        Migrations 0001 to 0016
│   ├── seed/                    skills · job_boards.py + discovered_boards.json · discover_boards.py · samples
│   └── tests/                   api/ · ingest/ · resume/ · eval/ · perf/
└── frontend/
    ├── src/
    │   ├── pages/               Jobs, job details, resume, tracker, AI key, account, sign in, add, admin
    │   ├── components/          Filter sidebar, job row, details, postmark, resume fit, tracker board, ...
    │   └── api/                 client.ts + one TanStack Query hook per endpoint
    ├── tests/                   Vitest
    └── e2e/                     Playwright (*.e2e.ts)
```

---

## Testing and quality

| Level | What | Count |
|---|---|---|
| Backend | Every endpoint, every importer (recorded responses, never the live internet), education reading, term reading, matching and scoring, hosting config, plus a speed test: p95 under 300 ms on 10,000 jobs | 457 pytest |
| Frontend | Filters, job rows and details, resume page, AI key, dates, the API client | 72 Vitest |
| End to end | A real browser on the running site: search, filters, details panel, upload a resume and see the program read from it, phone layout | 9 Playwright |

**CI** (`.github/workflows/ci.yml`) runs on every push: ruff, mypy `--strict`, migrations up, down and up again,
`alembic check`, pytest and the speed budget; ESLint, `tsc`, Vitest and the build; then it builds and starts the
real site exactly like Render does, smoke tests it, and runs Playwright against it.

---

## Security and privacy

- Visitors' AI keys stay in their browser and are forwarded per request only: never stored, logged or echoed.
- Resumes are stored as text only, in the user's account, and can be deleted any time. Temporary accounts expire
  after 7 days.
- Passwords use argon2id; sessions are HTTP-only Secure cookies; sign in, account creation, uploads and key checks
  are rate limited.
- SQL uses only bound parameters and whitelisted sort columns. Prompts treat resume and posting text as data, not
  instructions.
- Jobs come only from public job board APIs and feeds meant for sharing, with robots.txt respected (including Job
  Bank's 5 second pause).

---

## Built with Spec Kit and Claude Code

Features were specified and built with the [Spec Kit](https://github.com/github/spec-kit) loop in Claude Code
(`specs/001` to `004`), governed by `.specify/memory/constitution.md`: filter in SQL, every endpoint has schemas
and tests, p95 under 300 ms on 10,000 jobs, AI cites sources or says it doesn't know, secrets only in environment
variables. Project skills in `.claude/skills/` hold the conventions, and every session is logged in
[docs/agentic-workflow.md](docs/agentic-workflow.md).

---

## Roadmap

- [x] Search, tracker, importing, resume matching, bring your own key AI
- [x] One command to run, free hosting (Render + Neon + GitHub Actions), optional Vercel front
- [x] Matching by program, graduation year, term and length; resume fit; about 1,700 employers; US student roles
- [x] Postal look, full width jobs page with a filter sidebar, no popups
- [x] Instant first load, Job Bank jobs for every program, new jobs and RSS feeds, lighter database use
- [ ] Email alerts for new matches
- [ ] School job boards with public feeds
- [ ] Learning from which jobs students save; a tool using assistant and evals (spec 004)

## License

MIT
