# How CoopRadar Works (and how to explain it)

Plain language, step by step: what each part is, where it lives, what happens when someone uses the site, and how
to explain it in a pitch or an interview.

> Using or sharing the site: [USER_GUIDE.md](USER_GUIDE.md) · Hosting it: [DEPLOY.md](DEPLOY.md) ·
> Every module in depth: [PROJECT_GUIDE.md](PROJECT_GUIDE.md)

---

## 1. The one-paragraph version

CoopRadar is a website for co-op students. A background job **imports real jobs** from Canadian employers' own
career pages (the public Greenhouse, Lever, and Ashby job-board APIs) into a **PostgreSQL** database. A student
**drops in their resume**, with no sign-up needed. In SQL, the app finds which in-demand skills the resume shows and
which it's missing, and ranks the open jobs that fit a *student* best. With the student's **own AI key** (Claude,
ChatGPT, or Gemini), it adds a full resume review, per-job tailoring plans, and cover letter openers. Students can
also search every job and track applications on a board.

---

## 2. The building blocks

```
 Student's browser ──▶  one website (FastAPI serves the React app + the /api)
                              │                              │
                         PostgreSQL                     the student's AI
                  (jobs, users, resumes,           (Claude / ChatGPT / Gemini,
                   sessions, search)                their own key, per request)
                              ▲
              background jobs ── every 6 h ──▶ employers' public career-board APIs
              (inside the same server)
```

| Part | What it does | Where |
|---|---|---|
| **Website** (frontend) | Pages: Jobs, My resume, Tracker, AI key. React + TypeScript. | `frontend/src/` |
| **API** (backend) | Checks who you are, runs the logic, talks to the database. FastAPI (Python). | `backend/app/` |
| **Database** | Stores everything **and** does the searching (full-text, skill overlap, optional vectors). | `backend/app/models/`, migrations in `backend/alembic/versions/` |
| **Session store** | Remembers who's logged in, plus rate-limit counters. A small Postgres table by default; Redis if `REDIS_URL` is set. | `backend/app/store.py` |
| **Background jobs** | Import jobs from career boards every 6 hours (and create search vectors if enabled), inside the web server. | `backend/app/jobs.py`, `backend/app/ingest/` |

All of this is **one server process plus one database**. On your computer, `python start.py` sets up and runs it
(it even runs the database for you). Online, Render creates both from `render.yaml` with one click.

### Inside the backend: four layers (same for every feature)
| Layer | Folder | Job | Example |
|---|---|---|---|
| Router | `api/` | URL, login check, hand off | `api/resume.py` → `GET /api/resume/insights` |
| Schema | `schemas/` | Validate data in and out | `schemas/insights.py` → `ResumeInsights` |
| Service | `services/` | Logic + SQL | `services/insights.py` → `free_insights()` |
| Model | `models/` | A database table | `models/resume.py` → `Resume` |

---

## 3. What happens, step by step

### 3.1 Jobs arrive (the importer)
`backend/app/ingest/` · sources listed in `backend/seed/job_boards.py`
1. On start-up and every 6 hours, the scheduler runs one import per employer, one after another (`jobs.py`).
2. The **adapter** for that employer's job board (`boards.py`: Greenhouse, Lever, or Ashby) downloads the
   company's public job list as JSON. These APIs exist so companies can show their jobs on other sites. No keys,
   no scraping, and every job links back to the employer.
3. **Location filter**: only jobs in Canada are kept (`INGEST_LOCATION_FILTER`). A job listed as
   "London" + "Remote, Canada" is shown as the Canadian option, never mistaken for London, Ontario.
4. **Location parsing**: free text like "SEA, SF, NY, Toronto" becomes `Toronto, ON` (`parse_location`).
5. For each job (`runner.py`):
   - **Seen before?** Update it (re-open it if it came back).
   - **Near-duplicate** of another posting (same company and city, title more than 85% similar)? Skip it (`dedup.py`).
   - **New?** Detect skills from a 106-skill list (`skill_match.py`), which knows "Spring 2027" is a season and
     "Go to market" is not the Go language. It also guesses the term ("Winter 2027"). Most boards publish no
     deadline, so an **estimated apply-by date** is set and marked as estimated.
6. Jobs that **disappeared** from a board are marked closed. A board that fails 3 times in a row is auto-paused.

### 3.2 Browsing jobs
`GET /api/postings` → `services/postings.py`. Every filter, the sort, and the page live in the URL (shareable), and
the database does all filtering, sorting, and paging in **one SQL query**. **Co-op & intern roles only** adds a
title regex (`intern | co-op | student | new grad | apprentice`, whole words, so "Internal" doesn't match). The city
filter always includes remote jobs.

### 3.3 Uploading a resume, with no account needed
1. The student drops a file on **My resume** (`pages/ResumePage.tsx`).
2. Not signed in? The page first calls `POST /api/auth/guest`, which creates a **private temporary account**
   (`services/demo.py`, `is_demo = true`, kept 7 days, rate-limited per network) and sets a session cookie.
3. `POST /api/resume` → `services/resume.py`: check the type and size, extract the text (pypdf / python-docx). Only
   the text is stored.

### 3.4 Matching, free and without AI
1. **Which skills does the resume show?** Every skill that appears in a posting is checked against the resume text
   (whole words, with the same rules for C, R, Go, and Spring).
2. **Shortlist in SQL** (`_candidates_by_skills`): for each open job, *coverage* = matched skills ÷ the job's
   listed skills, with at least 3 in the denominator so a one-skill posting can't score 100.
3. **Student fit** (`_student_fit`): senior, staff, lead, or manager titles count **half**, and co-op, intern, or
   new-grad titles get **+25**.
4. The top 20 are saved, each with a reason built from the data: *"You have Python, SQL; it also asks for Go."*

### 3.5 Insights: what the resume says
`GET /api/resume/insights` → `services/insights.py`
- **Skills found** (free): the resume's skills that real postings ask for.
- **In demand, missing** (free): the most-requested skills across open postings, counted in SQL with
  `unnest(skills)` and `GROUP BY`, minus the ones the resume has.
- **AI review** (`POST`, the student's key): the resume plus those market numbers go to their AI. A strict prompt
  asks for JSON (summary, strengths, fixes, tailoring tips, roles to search, keywords) and forbids inventing
  experience. The reply is validated, then **cached on the resume row** so it's generated once per upload.

### 3.6 Smarter ranking with AI (optional)
**Re-rank with my AI** (`POST /api/resume/rematch`) sends the resume plus the ~40 shortlisted jobs to the student's
AI in one request: "score each 0–100 with a one-sentence reason, as JSON; score senior roles low for students."
The app drops any job ID the AI invented, removes duplicates, and clamps scores. A rejected key is reported clearly.
If the reply is garbage, it falls back to the free ranking.

### 3.7 Tailor, cover letter, ask
`POST /api/resume/matches/{id}/ask` with `mode` = `tailor`, `cover_letter`, or `question` → `agent/resume_qa.py`.
- Each mode has its own prompt. **Tailor** returns Fit / Lead with / Rewrite these bullets / Keywords / Gaps.
  **Cover letter** returns a 4–5 sentence opener. **Question** answers with `Resume:` / `Posting:` citations, or
  says exactly "I don't have enough information to answer that."
- Every prompt says the resume and posting are **data, not instructions** (prompt-injection protection) and never
  to invent experience.
- Answers **stream** word by word (Server-Sent Events). If the provider fails mid-answer, an in-band error event
  explains why.

### 3.8 Bring your own AI key
- The **AI key** page (`pages/AiKeyPage.tsx`) explains how to get a key, then calls `POST /api/ai/check`, which asks
  the provider which models the key can use.
- The key is kept **only in the browser** (`api/aiKey.ts`) and sent as `X-AI-*` headers on AI requests only.
- `app/ai.py` exposes `complete()` and `stream()`. Inside, it uses each official SDK (`anthropic`, `openai`,
  `google-genai`) and maps their errors to clear messages. The key is never stored, logged, or echoed.

### 3.9 Accounts, keeping a temporary account, and the tracker
- Passwords are hashed with **argon2id**. Sessions are random tokens in the session store (7-day rolling expiry), sent as
  **HTTP-only cookies**.
- **Keep my account** → `POST /api/me/claim` adds an email and password to a temporary account and clears
  `is_demo`. Everything stays.
- **Tracker**: save a job, then move it through statuses with dated notes. Every query is scoped to `user_id`, so
  nobody sees anyone else's data.

---

## 4. The database in one table

| Table | Holds |
|---|---|
| `postings` | every job (+ a weighted full-text index) and its source |
| `ingest_sources` / `ingest_runs` | the 27 career boards and a log of each import |
| `skills` | the skill list (names and aliases) used to tag postings and read resumes |
| `users` | accounts (argon2 hash, admin flag, temporary flag) |
| `resumes` | one resume's text per user + the cached AI review (`insights`, JSONB) |
| `match_results` | the scored matches for a resume |
| `saved_postings` / `application_events` | the tracker and its history |
| `posting_embeddings` | optional meaning-vectors (only when the owner sets an OpenAI key) |

---

## 5. How quality is guaranteed

- **264 automated tests**: 235 backend (`backend/tests/`) and 29 frontend (`frontend/tests/`). AI providers and job
  boards are mocked, so tests are free and offline.
- **CI** (`.github/workflows/ci.yml`) on every push: ruff, mypy `--strict`, eslint, tsc, migrations up, down, and
  up again plus a drift check, all tests, a 10,000-posting latency budget, and a **production-image smoke test**
  (build, boot, hit the pages, create demo and guest accounts).
- **Constitution** (`.specify/memory/constitution.md`): rules like "filter in SQL," "AI must cite or say it doesn't
  know," and "users can delete their data."
- Built spec-first with **Spec Kit + Claude Code**. The log is in `docs/agentic-workflow.md`.

---

## 6. How to explain it

### 30-second pitch (to students)
> "Drop in your resume and CoopRadar tells you what it's good at, which in-demand skills you're missing, and which
> real co-op and intern jobs from Canadian companies you should apply to. With a free Gemini key it'll also review
> your resume and write a tailoring plan and cover letter opener for any job. No sign-up needed."

### 30-second version (to an engineer or employer)
> "It's a full-stack app: React and TypeScript on FastAPI with PostgreSQL. A background scheduler imports real jobs from
> employers' public Greenhouse, Lever, and Ashby APIs every six hours, with location parsing and de-duplication. Resume
> matching runs in SQL first. Skill coverage plus a student-fit adjustment ranks jobs for free. Then an optional
> bring-your-own-key layer uses Claude, ChatGPT, or Gemini for reviews, re-ranking, and streamed tailoring. One
> command to run it (`python start.py`, no Docker), one click to host it on Render, 273 tests, CI that starts
> the real site and smoke-tests it."

### 2-minute walkthrough (follow the data)
1. **Data in**: a background job pulls about 800 Canadian jobs from 27 employers' public job-board APIs, filters to
   Canada, parses locations, de-duplicates, and tags skills.
2. **Resume in**: drop a file and you get a temporary account. Text is extracted, and only the text is stored.
3. **Free intelligence**: SQL finds skills found and missing (`unnest` and `GROUP BY` over all open jobs) and ranks
   jobs by skill coverage with a student-fit adjustment.
4. **AI layer (their key)**: review, re-rank, tailor, cover letter, and cited Q&A. Prompts treat documents as data,
   replies are validated, results are cached, and answers stream.
5. **Product details**: no sign-up, keep the account later, a tracker board, mobile-friendly, keys never leave the
   browser except per request.
6. **Quality**: 273 tests, strict typing, CI that starts the real site the way the host does.

### Likely questions
| Question | Answer |
|---|---|
| *Where do the jobs come from? Is it scraping?* | No. Greenhouse, Lever, and Ashby offer public JSON APIs specifically so companies' jobs can be shown elsewhere. No logins, no HTML scraping, and every job links back to the employer to apply. |
| *Why match in SQL before AI?* | SQL compares the resume with every open job instantly, for free, and works for users without a key. AI is precise but slow and costs money per token, so it only sees a 40-job shortlist. |
| *Why did senior roles stop showing up first?* | Raw skill overlap ranked "Senior Engineer II" at 100 for a student. A one-skill posting can't hit 100 now, and title-based student fit halves senior roles and boosts intern and co-op ones. There's a test for it. |
| *How do you stop the AI making things up?* | Context-only prompts, required citations, an exact "not enough information" reply, never inventing experience, discarding IDs it invents, and treating resume and posting text as data. |
| *Why bring-your-own-key?* | Hosting stays free, users control their own spend, and they pick the provider they trust. The key stays in their browser. |
| *How does "no sign-up" work securely?* | A temporary account with a random password nobody knows and a normal HTTP-only session, rate-limited per network and deleted after 7 days unless claimed with an email and password. |
| *What breaks if a job board changes?* | Only that source. The run is logged, it auto-pauses after 3 failures, and the other 26 keep working. Adapters are tested against recorded responses. |
| *How would it scale?* | Search is indexed SQL (p95 about 55 ms on 10,000 postings in CI). The AI cost sits with users. Imports run as bounded background jobs; under heavy load they can move to a separate worker, and sessions can move to Redis by setting `REDIS_URL`. |
| *What's next?* | More employers and schools' public feeds, email alerts for new matches, a tool-using assistant exposed over MCP, and per-school location presets. |

---

## 7. Where to change things

| I want to change… | Look in |
|---|---|
| Which employers are imported | `backend/seed/job_boards.py` |
| Which locations are kept | `INGEST_LOCATION_FILTER` (`backend/app/config.py`) |
| How free matching scores jobs | `backend/app/services/resume.py` (`_MIN_SKILLS`, `_student_fit`, `SENIOR_TITLE_PATTERN`) |
| The AI review | `backend/app/services/insights.py` (`_INSIGHTS_PROMPT`) |
| Tailor / cover letter / Q&A prompts | `backend/app/agent/resume_qa.py` |
| The skill list | `backend/seed/skills.py` (re-seeding updates aliases) |
| The resume page | `frontend/src/pages/ResumePage.tsx` |
| The per-job assistant | `frontend/src/components/ConversationPanel.tsx` |
| Home page hero | `frontend/src/components/WelcomeHero.tsx` |
| AI providers and key handling | `backend/app/ai.py`, `frontend/src/api/aiKey.ts`, `pages/AiKeyPage.tsx` |
| A database table | `backend/app/models/` + a migration (the `/db-migration` skill) |
| Running and hosting | `start.py`, `render.yaml`, `docs/DEPLOY.md` |
