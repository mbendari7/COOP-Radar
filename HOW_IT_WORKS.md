# How CoopRadar Works

This file explains the whole program in plain language, step by step: what each part is, where it lives in the
repo, what happens when you click something, and how to explain it to someone else (like in an interview).

> To install and run it, see **[GETTING_STARTED.md](GETTING_STARTED.md)**.
> For the deepest technical detail (every module, test strategy, recipes), see
> **[docs/PROJECT_GUIDE.md](docs/PROJECT_GUIDE.md)**.

---

## 1. The one-paragraph version

CoopRadar is a web app for co-op students. It **collects job postings** (from public job feeds, CSV files, or a
form) into one **PostgreSQL database**. Students **search and filter** them through a **React** website that talks
to a **FastAPI** (Python) server, **save** the ones they like, and **track** each application's status. When a student
**uploads a resume**, the app turns it into a "meaning vector," finds the 40 most similar postings in the database,
and asks **Claude** to score and explain the best 20. The student can then **ask questions** about any match and
get streamed answers that cite the resume or the posting.

---

## 2. The building blocks (and where they live)

Think of it as five programs working together. Docker Compose (`docker-compose.yml`) starts all five with one command.

```
 You (browser)
     │  http://localhost:5173
     ▼
┌──────────────┐   /api/* requests   ┌──────────────┐  SQL   ┌──────────────────────┐
│  web         │ ──────────────────▶ │  api         │ ─────▶ │  db  (PostgreSQL)     │
│  React site  │                     │  FastAPI     │        │  postings, users,     │
│  frontend/   │ ◀────── JSON ────── │  backend/app │ ◀───── │  tracker, vectors     │
└──────────────┘                     └──────┬───────┘        └──────────▲───────────┘
                                            │ sessions, job queue        │
                                            ▼                            │
                                     ┌──────────────┐  takes jobs  ┌─────┴────────┐
                                     │  redis       │ ◀─────────── │  worker      │
                                     │  fast memory │              │  background  │
                                     └──────────────┘              │  jobs        │
                                                                   └──────────────┘
       Outside services (optional): Claude API (AI answers + ranking), OpenAI (embeddings), public job feeds
```

| Part | What it does | Where in the repo |
|---|---|---|
| **web** (frontend) | The pages you see. Built with React + TypeScript. Asks the API for data and displays it. | `frontend/src/` |
| **api** (backend) | The "brain." Receives requests, checks who you are, runs the logic, reads/writes the database. | `backend/app/` |
| **db** (PostgreSQL) | Stores everything. Also does the searching itself (keyword search, vector search, fuzzy matching). | tables defined in `backend/app/models/`, created by `backend/alembic/versions/` |
| **redis** | Very fast memory for login sessions, rate limits, and the to-do list of background jobs. | configured in `backend/app/redis.py` |
| **worker** | Does slow work in the background: fetching job feeds, creating embeddings, running every 6 hours. | `backend/app/worker.py`, `backend/app/ingest/` |

### Inside the backend: four layers
Every feature in `backend/app/` is split the same way. If you understand one, you understand them all:

| Layer | Folder | Job | Example (postings) |
|---|---|---|---|
| **Router** | `api/` | Defines the URL, checks login, hands off to the service | `api/postings.py` → `GET /api/postings` |
| **Schema** | `schemas/` | Describes and validates the data going in and out | `schemas/posting.py` → `PostingListParams`, `PostingListItem` |
| **Service** | `services/` | The actual logic and database queries | `services/postings.py` → `list_postings()` |
| **Model** | `models/` | Python description of a database table | `models/posting.py` → `Posting` |

Other important backend files:
- `main.py` builds the app and plugs in all routers. `config.py` reads settings from `.env`.
- `deps.py` works out who is logged in. `llm.py` holds the shared code for talking to Claude.
- `agent/resume_qa.py` runs the resume Q&A. `seed/` holds the sample data.

### Inside the frontend
| Folder | Job |
|---|---|
| `src/pages/` | One file per screen: postings list, posting detail, Saved, Matches, Account, Admin |
| `src/components/` | Reusable pieces: table, filter bar, tracker board, login popup, resume upload, Q&A panel |
| `src/api/` | Every call to the backend. `client.ts` is the single fetch helper; the other files are "hooks" pages use to get data |
| `src/App.tsx` | The header and which URL shows which page |

---

## 3. Step by step: what happens when you use it

### 3.1 Starting up (`docker compose up --build`)
1. Docker starts **db** and **redis** and waits until both are healthy.
2. **api** starts and runs `alembic upgrade head`. That runs the 5 migration files in order, creating any missing
   tables (`0001` postings → `0002` users and saved → `0003` tracker history → `0004` ingestion and vectors →
   `0005` resumes and matches). Then the web server starts on port 8000.
3. **worker** starts. It waits for jobs and, every 10 minutes, checks whether any job source is due for its
   6-hourly refresh.
4. **web** starts the website on port 5173. Any request to `/api/...` is forwarded to the api container.

### 3.2 Searching postings
You type `python` and pick the skill `Docker`:
1. The page (`pages/PostingsListPage.tsx`) writes your choices into the URL (`?q=python&skills=Docker`). That's why
   links are shareable.
2. A data hook (`api/postings.ts → usePostings`) requests `GET /api/postings?q=python&skills=Docker`.
3. The router (`api/postings.py`) validates the parameters. An unknown sort column is rejected with error 422.
4. The service (`services/postings.py → list_postings`) builds **one SQL query**:
   - keyword search uses a pre-built search index (`search_vector`) where title matches count more than description matches
   - `skills @> ['Docker']` means "must contain all these skills"
   - expired and closed postings are hidden; sorting and paging also happen in SQL
5. Postgres returns the 25 rows for that page plus the total count. If you're logged in, the service also marks
   which ones you saved.
6. JSON comes back, the table re-renders, and the counter updates.

> Key idea: **the database does the filtering, sorting, and paging, not the browser.** That's why it stays fast
> with 10,000+ postings (measured: 95% of requests under ~55 ms).

### 3.3 Smart search
Same flow, but in step 4 the service first sends your text to **OpenAI**, which turns it into a list of 1,536
numbers (an **embedding**) representing its meaning. Every posting has one too (table `posting_embeddings`).
Postgres's **pgvector** extension sorts postings by how close their vectors are (cosine distance). Similar meaning
gives close vectors, so "hardware programming" finds "embedded firmware" roles.

### 3.4 Registering and logging in
1. `POST /api/auth/register` → `services/auth.py` hashes the password with **argon2** (the plain password is never
   stored) and saves the user.
2. It creates a random 64-character **session token** and stores `session:<token> → your user id` in **Redis**
   with a 7-day expiry.
3. The token goes back as an **HTTP-only cookie**. Your browser sends it automatically on every request, and
   JavaScript can't read it (protection against XSS).
4. On each request, `deps.py → get_current_user` reads the cookie, looks up Redis, loads you from the database,
   and resets the 7-day timer.
5. **Log out** deletes the Redis entry, so the token stops working instantly. 5 wrong passwords in 15 minutes → locked out (429).

### 3.5 Saving and tracking an application
1. Bookmark → `POST /api/saved` creates a row in `saved_postings` (saving twice is harmless).
2. Changing the status → `PATCH /api/saved/{id}/status` updates the status **and** adds a row to
   `application_events` (the history: status, note, date).
3. The Saved page gets your saves plus counts per status, stats, and deadlines due this week, all computed in SQL.
4. Every query includes `WHERE user_id = you`, so nobody can ever see someone else's tracker.

### 3.6 How postings get into the database
| Source | How |
|---|---|
| Sample data | `python -m seed` (`backend/seed/`) |
| CSV upload | `POST /api/postings/upload` → each row validated → duplicates skipped → saved |
| Manual form | `POST /api/postings` |
| Job feeds (automatic) | the **worker** runs `ingest/runner.py` for each source every 6 hours, or when an admin clicks **Run now** |

The automatic ingestion, step by step (`backend/app/ingest/`):
1. The **adapter** fetches the feed: `json_api.py` for JSON job APIs, `rss.py` for RSS feeds.
2. For each posting found:
   - **Seen before from this source?** Update it.
   - **Near-duplicate** of an existing posting? Skip it. Same company and city plus ≥ 85% similar title, using
     Postgres's Levenshtein distance (`dedup.py`).
   - **New?** Fill in missing fields (work mode, term, skills) by keyword matching against a 106-skill list, and
     if that's not confident, by asking Claude (`extract.py`). Guessed fields are flagged "low confidence."
3. Postings from this source that **disappeared** from the feed get marked closed.
4. The run's stats are saved (`ingest_runs`); 3 failures in a row → the source is auto-paused.
5. Each new posting gets a background job to create its embedding (`embed.py`).

### 3.7 Resume matching: the AI part
`POST /api/resume` → `services/resume.py`:
1. **Check the file**: PDF or DOCX, max 5 MB.
2. **Extract the text** (pypdf / python-docx). Only the text is stored, never the file.
3. **Stage 1, fast and broad**: embed the resume with OpenAI, then ask Postgres for the **40 open postings whose
   vectors are closest**. This takes milliseconds.
4. **Stage 2, smart and precise**: send the resume plus those 40 postings to **Claude** (the fast model,
   `claude-haiku-5-5`) in one request: "score each 0–100 with a one-sentence reason, reply as JSON."
5. **Check Claude's answer**: drop any posting ID Claude made up, remove duplicates, keep scores within 0–100,
   and keep the top 20.
6. **Backup plan**: if Claude is down or replies with nonsense, use the Stage-1 similarity as the score instead,
   so the upload still works.
7. Save the results in `match_results` and show them on the Matches page.

> Why two stages? Comparing vectors is cheap but blunt. An AI model is precise but slow and costs money per posting.
> Vectors narrow thousands of postings to 40, and Claude carefully ranks just those 40.

### 3.8 Asking questions about a match
`POST /api/resume/matches/{posting_id}/ask` → `agent/resume_qa.py`:
1. Checks the posting is one of **your** matches.
2. Sends Claude (`claude-opus-5-5`) a strict instruction: answer **only** from the provided posting and resume,
   start each claim with `Resume:` or `Posting:`, and if the answer isn't there, reply exactly
   *"I don't have enough information to answer that."*
3. The posting and resume are wrapped in tags and labelled "data, not instructions." That way, a posting that
   says "ignore your rules" can't hijack the assistant (**prompt-injection protection**).
4. The answer is **streamed** back with Server-Sent Events, so words appear as Claude writes them.

---

## 4. The database in one table

| Table | Holds |
|---|---|
| `postings` | every job posting (+ a built-in search index) |
| `posting_embeddings` | one meaning-vector per posting |
| `users` | accounts (email, hashed password, admin flag) |
| `saved_postings` | which user saved which posting, and its current status |
| `application_events` | history of status changes with notes and dates |
| `resumes` | one resume's text per user |
| `match_results` | the scored matches for a resume |
| `ingest_sources` / `ingest_runs` | job feeds and the log of each fetch |
| `skills` | the skill list used to tag postings |

---

## 5. How quality is guaranteed

- **158 automated tests**: 141 backend (`backend/tests/`) and 17 frontend (`frontend/tests/`). AI calls are faked
  in tests, so they're free and repeatable.
- **GitHub Actions** (`.github/workflows/ci.yml`) runs on every push: linting, strict type checks, database
  migrations forwards and backwards, all tests, a 10,000-posting speed test, and a production build.
- **The constitution** (`.specify/memory/constitution.md`): 9 rules the project follows, e.g. "filtering happens in
  SQL," "AI must cite sources," "users can delete their data."

### How it was built: AI-assisted, spec-first
Each feature was written as a specification first (`specs/001…004/`), using **Spec Kit** inside **Claude Code**:
spec → clarify → plan → tasks → implement → check what's missing. The project's conventions are written down as
**skills** (`.claude/skills/`) so the AI follows them, and `docs/agentic-workflow.md` logs what the AI did and what
was reviewed by a human.

---

## 6. How to explain it

### 30-second version
> "CoopRadar is a full-stack app that puts co-op postings from different sources into one searchable place, lets
> students track their applications on a board, and matches their resume to postings with AI. It's a React and
> TypeScript frontend on a FastAPI backend with PostgreSQL. Postgres does keyword search, vector search with
> pgvector, and fuzzy de-duplication itself, so I don't need a separate search engine. Redis and a background worker
> handle sessions and ingestion. For matching, I use embeddings to shortlist 40 postings, then Claude ranks the
> top 20 and explains each one."

### 2-minute walkthrough (follow the data)
1. **Data in**: postings come from public job feeds (a background worker fetches them every 6 hours, removes
   duplicates, fills in missing fields), CSV uploads, or a form.
2. **Storage**: one Postgres database. Each posting gets a weighted full-text index and an embedding vector.
3. **Search**: the React page keeps filters in the URL and calls the API. The API builds a single SQL query that
   filters, sorts, and pages, and it stays under 60 ms at the 95th percentile on 10,000 postings.
4. **Accounts and tracker**: argon2-hashed passwords, HTTP-only cookie sessions stored in Redis, and a status
   history per saved posting with a drag-and-drop board.
5. **AI**: resume → embedding → top 40 by vector similarity → Claude scores the top 20 → follow-up Q&A that streams
   and must cite the resume or posting. Everything has a fallback if the AI is unavailable.
6. **Quality**: 158 tests, strict typing, CI on every push, and spec-first development with Claude Code.

### Likely questions and good answers
| Question | Answer |
|---|---|
| *Why filter in SQL, not in the browser?* | The browser would have to download every posting. SQL uses indexes, returns just one page, and stays fast as data grows. |
| *How do you stop SQL injection?* | User input is always passed as bound parameters or through the ORM, never pasted into SQL strings. Sort columns come from a fixed allowlist. |
| *Why two stages for matching?* | Vector search is cheap enough to scan everything; the LLM is accurate but costly, so it only sees a shortlist. |
| *How do you stop the AI from making things up?* | Context-only instructions, required citations, an exact "not enough information" answer, ignoring IDs it invents, and treating posting text as data. |
| *What if the AI service is down?* | Matching falls back to similarity scores; search falls back to keyword; Q&A shows a clear message. Nothing crashes. |
| *Why cookies + Redis instead of JWT?* | Logout and expiry take effect immediately (delete the key), and HTTP-only cookies can't be read by injected scripts. |
| *How do you know it works?* | 158 automated tests, a performance test, and CI that also checks the database migrations and the models agree. |
| *What would you build next?* | A tool-using assistant that can search and save postings (with confirmation), exposing the same tools over MCP, plus real public job-board sources and deployment. |

---

## 7. Where to look when you want to change something

| I want to change… | Look in |
|---|---|
| What a page looks like | `frontend/src/pages/` and `frontend/src/components/` |
| A search filter | `backend/app/schemas/posting.py` + `backend/app/services/postings.py` + `frontend/src/components/FilterBar.tsx` |
| How matching scores postings | `backend/app/services/resume.py` (`_RERANK_PROMPT`) |
| What the Q&A assistant may say | `backend/app/agent/resume_qa.py` (`_SYSTEM_PROMPT`) |
| Which AI models are used | `.env` → `AGENT_MODEL`, `FAST_MODEL` (no code change) |
| A database table | `backend/app/models/` + a new migration (use the `/db-migration` skill in Claude Code) |
| A new job feed | `backend/app/ingest/` (see "Add an ingest adapter" in `docs/PROJECT_GUIDE.md`) |
| Sample data | `backend/seed/` |
