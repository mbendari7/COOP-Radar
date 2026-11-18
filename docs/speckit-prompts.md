# CoopRadar: Spec Kit Prompt Pack

Paste each block into Claude Code, run from the repo root. One block at a time. **Read what it generates before running the next one.**

Where things live: Spec Kit config, templates, and the constitution are in `.specify/`; feature specs in `specs/NNN-*/`;
the `/speckit-*` and project skills in `.claude/skills/`. Features 001 to 004 below were run through the full loop.
Features 005 to 008 were built straight from chat and their specs written afterwards, so their blocks below are the
prompts you would use to run them properly. Use any of them as the model for Feature 009 and up. `.specify/README.md`
explains the folder and the loop.

- Run the **Constitution once**.
- Then run each **Feature** (001 to 008) through the full loop below. Finish and merge one feature before you start the next.

```
/speckit-specify → /speckit-clarify → /speckit-plan → /speckit-checklist → /speckit-tasks
→ /speckit-analyze → /speckit-implement → /speckit-converge (repeat implement/converge until "Converged")
→ /log-agentic-work → commit/PR
```

Rule of thumb: **specify = WHAT and WHY (no tech)**. **plan = HOW (stack, libraries)**.

---

## 0. Constitution (run once)

This is the prompt that made version 1.0.0 on 2026-10-09. On 2026-11-17 the constitution was rewritten to 2.0.0
(10 principles) to match how the project works now: no Docker, matching without AI, bring your own key, free
hosting. Read `.specify/memory/constitution.md` for the current rules.

```
/speckit-constitution
CoopRadar is a portfolio-grade full-stack app that helps university co-op students find, track, and apply to co-op postings, with an AI assistant that matches a student's resume to postings.

Principles:
1. Correctness first: every backend endpoint has request/response schemas and automated tests; CI (lint, type checks, tests, agent evals) must pass before merge.
2. Data stays in the database layer: searching, filtering, sorting and pagination run in SQL, never in the browser. Sortable/filterable fields are whitelisted; user input is never interpolated into queries.
3. Performance budgets: list/search endpoints return in under 300 ms p95 on 10,000 postings; pages show useful content within 2 seconds on a normal laptop connection.
4. Honest AI: the assistant only makes claims it can back with posting IDs or resume text, says "not enough information" instead of guessing, never takes an action that writes data without the user confirming, and changes to prompts or tools must not drop the eval pass rate below 80%.
5. Privacy and security: resumes and personal data belong to the user, are never sent anywhere except the configured AI provider, and can be deleted by the user. Secrets live only in environment variables. Passwords are hashed; sessions expire.
6. Responsible data collection: postings come only from public APIs/feeds, user uploads, or manual entry. Respect robots.txt and site terms; never scrape pages behind a login.
7. Accessible, mobile-first UI: keyboard navigable, visible focus, labelled controls, WCAG AA contrast, usable at 375 px width.
8. Small, reviewable changes: conventional commits, one feature per branch, and docs/agentic-workflow.md updated after each feature describing what the AI did and what I reviewed.
9. Simplicity: prefer boring, well-documented tools; no new dependency without a stated reason in the plan.
```

---

## Feature 001: Browse & search postings (MVP)

```
/speckit-specify
Students need one place to browse co-op postings instead of checking many sites.

Users can:
- See a list of co-op postings showing title, company, city/province, work mode (onsite, hybrid, remote), term (e.g. "Summer 2027"), duration in months, application deadline, and posted date.
- Search postings by keyword across title, company, skills and description.
- Filter by city, province, term, work mode, duration, and one or more required skills; combine filters freely and clear them in one click.
- Sort by posted date, deadline, company name, or title, ascending or descending.
- Page through results and choose page size (10, 25, 50).
- Open a posting to see the full description, required skills, and a link to the original posting.
- Share or bookmark a view: the current search, filters, sort, and page are kept in the page address.
- See clear loading, empty ("no postings match, clear filters"), and error states.

Postings whose deadline has passed are hidden by default, with a toggle to show them.

Out of scope for this feature: user accounts, saving postings, importing real postings, AI features. Use about 60 realistic sample postings across Toronto, Mississauga, Waterloo, Kitchener, Guelph, Hamilton, Ottawa and Vancouver, for Winter, Summer and Fall 2027 terms.

Success: a student can narrow 60 postings to the 3 to 5 that fit them in under 30 seconds.
```

**Likely `/speckit-clarify` questions and good answers**
- *Keyword search matching?* Match whole words and prefixes, case-insensitive, and rank title matches above description matches.
- *Multiple skills filter?* The posting must have **all** selected skills.
- *Default sort?* Newest posted first.
- *Remote postings and the city filter?* Remote postings always show unless the user turns on "exclude remote".

```
/speckit-plan
Follow CLAUDE.md. Monorepo with Docker Compose (postgres 16 + pgvector image, redis, api, web).
Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 async, Alembic, pytest. Postgres tsvector column with a GIN index for keyword search; B-tree indexes on every sortable/filterable column; skills stored as text[] with a GIN index.
Frontend: React + TypeScript + Vite, TanStack Query, TanStack Table in manual (server-side) sorting/filtering/pagination mode, Tailwind, Vitest + Testing Library. API types generated from FastAPI's OpenAPI schema.
CI: GitHub Actions running ruff, mypy, pytest, eslint, tsc, vitest.
Include a seed script, a Mermaid architecture diagram in the README, and a quick performance test proving the 300 ms p95 budget on 10,000 generated postings.
Follow the api-conventions and frontend-tables skills.
```

```
/speckit-checklist
Focus on: filter and sort combinations, URL state round-tripping, empty/error states, accessibility of the table and filter bar, and the performance budget.
```

Then run `/speckit-tasks`, `/speckit-analyze`, `/speckit-implement`, and `/speckit-converge`.

---

## Feature 002: Accounts & application tracker

```
/speckit-specify
Students want to keep track of which postings they saved and where each application stands.

Users can:
- Create an account with email and password, log in, log out, and delete their account and all their data.
- Save a posting from the list or detail view, and unsave it.
- Track each saved posting through statuses: Saved, Applying, Applied, Interview, Offer, Rejected, Withdrawn.
- See their applications on a board grouped by status (drag a card to change status) and as a sortable, filterable table (by status, deadline, company, last updated).
- Add private notes and a date to each status change (e.g. interview date).
- See a "deadlines this week" panel and simple stats: total applied, interview rate, offers.
- Export their tracker as a CSV file.

Each user only ever sees their own saved postings and notes. Guests can still browse postings without an account.

Out of scope: password reset by email, social login, AI features.

Success: a student can replace their spreadsheet tracker with CoopRadar for a full co-op search season.
```

**Likely clarify answers**
- *Status history?* Keep a full timestamped history and show it on the card.
- *Session length?* 7 days, sliding.
- *Account deletion?* Immediate and permanent, behind a confirmation dialog.

```
/speckit-plan
Same stack as feature 001. Auth with hashed passwords (argon2) and HTTP-only secure cookie sessions or short-lived JWT + refresh; rate-limit login. New tables: users, saved_postings, application_events (status history). Every query scoped by user_id with tests proving one user cannot read another's data. Frontend: protected routes, a drag-and-drop board (dnd-kit), and the tracker table reusing the shared table component. CSV export generated server-side with pandas.
```

```
/speckit-checklist
Focus on: authorization (cross-user access), account deletion completeness, status-transition rules, CSV correctness, and keyboard-accessible drag and drop.
```

Then the usual loop.

---

## Feature 003: Real postings ingestion & semantic search

```
/speckit-specify
Sample data isn't useful for a real job hunt; CoopRadar needs real, fresh postings.

The system can:
- Import postings on a schedule from public company job boards that publish open APIs or feeds, for a configurable list of companies.
- Let a user import postings by uploading a CSV (for postings copied from their school's co-op portal) or by adding one manually through a form.
- Detect and merge duplicates of the same posting from different sources.
- Automatically pull out city, work mode, term, duration and required skills from each posting's text, and flag low-confidence fields for review.
- Mark postings closed when they disappear from their source.
- Show an admin "Sources" page: each source's last run time, postings added/updated/closed, and errors.

Users can:
- Search by meaning as well as keywords (e.g. "embedded firmware" also finds "microcontroller C developer"), with a toggle between keyword and smart search.
- See "similar postings" on a posting's detail page.

Postings are only collected from public sources, uploads or manual entry; never from pages behind a login, and each source's terms and robots.txt are respected.

Success: at least 200 real, de-duplicated postings with correct locations and terms after the first scheduled run.
```

**Likely clarify answers**
- *Run frequency?* Every 6 hours, plus a manual "run now" button for admins.
- *Duplicate rule?* Same company, a near-identical title, and the same city.
- *Skill list?* A fixed taxonomy of about 150 skills, editable by an admin.

```
/speckit-plan
Ingestion as source adapters in backend/app/ingest (one class per source type: public job-board JSON APIs, RSS, CSV upload, manual), run by RQ workers with a scheduler, using httpx with retries, timeouts and a polite user agent. Extraction: rules + regex first, LLM fallback only for low-confidence fields. Embeddings stored in pgvector with an HNSW index; hybrid search = tsvector rank combined with cosine similarity. pandas for CSV validation and cleaning. Record every run in an ingest_runs table. Tests use recorded fixture responses, never live network calls.
```

```
/speckit-checklist
Focus on: source terms compliance, idempotent re-runs, duplicate handling, CSV validation errors shown to the user, and search relevance with 10 example queries.
```

Then the usual loop.

---

## Feature 004: AI resume matcher & assistant

```
/speckit-specify
Students struggle to tell which postings they're actually qualified for and how to tailor their applications.

Users can:
- Upload a resume (PDF or DOCX) and see the skills, education, and experience CoopRadar extracted, and correct them.
- See a fit score (0 to 100) on each posting with a short explanation: matched skills, missing skills, and why.
- Sort and filter postings by fit score.
- Chat with an assistant that can search postings, compare postings, explain gaps, and draft tailored resume bullet points or a short cover-letter opening for a chosen posting. Every claim cites the posting(s) it is based on.
- Ask the assistant to save a posting or change a tracker status; it always asks for confirmation first.
- See which steps the assistant took (searched postings, opened posting X, scored fit) for each answer.
- Delete their resume at any time.

The assistant must say when it lacks information instead of guessing and must never invent postings, companies or skills.

The same assistant capabilities are also available to external AI tools through a standard tool protocol, so a student can use them from their own AI app.

Success: on a test set of 25 realistic questions, at least 80% of answers use the right tools, cite correct postings, and contain no invented facts.
```

**Likely clarify answers**
- *Fit score formula?* 60% required skills, 25% preferred skills or semantic similarity, 15% program and term eligibility. Show the breakdown.
- *Chat history?* Kept per user for 30 days, and deletable.
- *Usage cap?* 50 assistant messages per user per day.

```
/speckit-plan
Anthropic Python SDK with tool use; models from AGENT_MODEL / FAST_MODEL env vars (defaults claude-opus-5-5 / claude-haiku-5-5) via app/llm.py. Tools in backend/app/agent/tools.py with Pydantic inputs (search_postings, get_posting, score_fit, compare_postings, save_posting, update_status), calling the service layer. Write tools require a confirmation round-trip in the UI. Resume parsing with pypdf/python-docx, then structured extraction into a Pydantic model. Streaming chat over Server-Sent Events. Log every run to agent_runs (tool calls, tokens, latency, cost). MCP server in backend/app/mcp reusing the same tools. Evals in backend/evals (25 YAML cases, a runner that reports pass rate/tokens/latency and fails CI under 80%). Follow the agent-tools skill.
```

```
/speckit-checklist
Focus on: hallucination guards, confirmation before writes, prompt-injection from posting text, resume privacy and deletion, eval coverage, and cost limits.
```

Then the usual loop. After this feature, also try `/claude-api build-eval` to strengthen the eval set.

---

## Feature 005: Bring your own AI key and a resume first site

Spec written after the code: `specs/005-byok-resume-first/`.

```
/speckit-specify
Hosting AI for everyone costs the owner money, and students should not need an account just to see which jobs fit them.

Visitors can:
- Drop a PDF or DOCX resume without signing up (a temporary account is made and deleted after 7 days unless they keep it).
- See skills found, the most asked for skills they are missing, and ranked matches with a reason, with no AI key at all.
- Add their own Claude, ChatGPT or Gemini key, check it, and pick a model the key can use. The key stays in their browser.
- With a key: get an AI review of the resume, re-rank matches, tailor the resume to one job, draft a cover letter, and ask cited questions about one job.
- Try a demo account with a filled tracker, and turn any temporary account into a real one.

The owner can optionally offer a few AI actions a day on their own key. Student roles rank above senior ones.

Success: a signed out visitor sees ranked matches within 10 seconds of dropping a resume, with no key.
```

```
/speckit-plan
Same stack. One app/ai.py module over the official anthropic, openai and google-genai SDKs, with complete(), stream(), list_models() and clear error codes. Keys on X-AI-Provider, X-AI-Key and X-AI-Model headers, never stored or logged. Stage 1 matching is SQL skill overlap, stage 2 is the visitor's model. Guest and demo accounts flagged is_demo. Cached AI review in resumes.insights. Follow the agent-tools skill.
```

```
/speckit-checklist
Focus on: keys never stored or echoed, every provider error case, the no key path, prompt injection in resume and posting text, and temporary account cleanup.
```

---

## Feature 006: One command run and free hosting

Spec written after the code: `specs/006-one-command-free-hosting/`.

```
/speckit-specify
Running CoopRadar needs Docker, Redis and a separate worker, which most students and reviewers do not have.

- Anyone with Python and Node runs it with one command. It sets itself up, keeps its own database outside synced folders, and restarts in seconds.
- The owner hosts it for free and it keeps importing jobs on its own every 6 hours.
- The free server sleeps when idle, so the first page of jobs must show right away anyway, with a note if the rest is still on its way.
- Old closed jobs are cleaned up so the free database does not fill.

Success: clone to jobs on screen with one command, and jobs visible in about a second while the server wakes up.
```

```
/speckit-plan
start.py at the repo root (stdlib only) with --dev and --hosted. pgserver for a local Postgres 16 + pgvector in ~/.coopradar. Sessions and counters in a kv_store table behind a Store protocol, Redis only if REDIS_URL is set. Background jobs as asyncio tasks in app/jobs.py, 3 at a time, with a scheduler in the lifespan. Render native Python runtime, Neon database, optional Vercel with /api proxied. A GET /api/postings/snapshot reply cached at the edge and in the browser. Seed fingerprint so restarts skip the seed. Remove every Dockerfile and compose file.
```

```
/speckit-checklist
Focus on: what may and may not be cached at the edge, restart and crash recovery, free plan limits, and the server sleeping halfway through an import.
```

---

## Feature 007: Co-op matching and a job board layout

Spec written after the code: `specs/007-coop-matching-job-board/`.

```
/speckit-specify
Matching only looks at skills, but a co-op student cares about their program, their graduation year and which work term a job is for.

- Read program, degree and graduation year from the resume and let the student fix them.
- Read the programs, graduation years, work term and length each job asks for.
- Ask what the student is looking for (job types, keywords, place, work mode, level, term, length, countries) and rank by all of it. Never hide a job just for program or grad year, rank it lower with a note.
- Each match says why it fits in plain words.
- The jobs page works like a real job board: one search row, a filter sidebar with counts (term, length, level, place, work mode, job type, program, grad year, date, company, skills), a list beside a details panel, everything in the address, no popups.
- A free "make your resume fit this job" check, and "new since your last visit" with an RSS feed for any search.

Success: for a resume that names a program, at least 8 of the top 10 matches suit it.
```

```
/speckit-plan
Rules, not AI: services/education.py for programs and grad years, ingest/terms.py for term and length, services/categories.py for job types as title patterns. Generated season and term_start columns. A weighted student fit score in SQL with fit_notes(). JobPreferences saved on the resume. include_unstated for jobs that do not say their term. Design with the Impeccable skill into DESIGN.md. Follow the api-conventions and frontend-tables skills.
```

```
/speckit-checklist
Focus on: grad year versus work term confusion, lenient matching, every filter combination in the URL, the 375 px layout, and the perf budget with every filter on.
```

---

## Feature 008: Jobs from every field, from public sources

Spec written after the code: `specs/008-more-job-sources/`.

```
/speckit-specify
Bring in real jobs from as many employers as possible, in every field that has co-ops, not only tech: nursing, trades, early childhood education, business, hospitality.

- Read each employer's own careers board for the hiring systems most employers use.
- Read the Government of Canada Job Bank student, apprentice and program feeds.
- Read the public student internship and new grad lists, keeping each role's term.
- Make sure every job lands in the right city and country.
- Use only public APIs and feeds that allow it. Never LinkedIn, Indeed, Glassdoor or Google Jobs.

Success: about 1,700 sources and about 30,000 open jobs, and no import stopped by one broken source.
```

```
/speckit-plan
One adapter per system in backend/app/ingest/ on the existing BaseAdapter and runner: Greenhouse, Lever, Ashby, SmartRecruiters, Workday, Recruitee, BambooHR, Rippling, Oracle, Workable, Simplify, GitHub lists, The Muse, Himalayas, Job Bank, optional Adzuna. Each adapter type added to the CHECK constraint in a migration. Recorded replies with respx in tests. seed/job_boards.py plus seed/discovered_boards.json from seed/discover_boards.py. rolling_window for feeds that only show a few days. Link every source's robots.txt and terms in research.md.
```

```
/speckit-checklist
Focus on: terms and robots.txt for every source, re running twice, country and location rules, rate limits, and one bad source not stopping the rest.
```

---

## Feature 009 and up

Ideas waiting for a spec: the rest of 004 (tool using assistant with a confirm step, MCP server, `agent_runs`,
YAML evals), an Admin form to add sources and review low confidence fields, error tracking and a usage dashboard,
unsave from the jobs list, and showing the fit score broken into its parts.
