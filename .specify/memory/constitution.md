# CoopRadar Constitution

These are the rules every CoopRadar feature gets checked against. The plan for a feature has a Constitution
Check section and it has to pass before any code gets written. If a plan needs to break a rule it says why in
its Complexity Tracking table, or the rule gets changed here first.

The first version (1.0.0) was written on 2026-10-09 before any code existed. This version was rewritten on
2026-11-17 after features 001 to 008 were built, so it matches how the project actually works now: no Docker, no
sign up needed, bring your own AI key, free hosting and real jobs from public career boards.

## Core Principles

### I. Correctness First

Every backend endpoint MUST have a Pydantic schema for what comes in and what goes out, plus at least one test for
the happy path and one for a bad request. Every bug fix MUST come with a regression test that fails without the
fix. The checks in the Quality Gates section MUST all pass before anything lands on `main`. A red check is a
blocker, not a warning.

Tests MUST NOT touch the network. Career board replies are recorded fixtures played back with `respx`, and every
AI call is mocked (`mock_claude_create`, `mock_claude_stream`, `mock_embedding`). If a test only passes when the
internet is up, it is a broken test.

### II. Data Stays in the Database

Searching, filtering, sorting and paging MUST happen in SQL, never in Python lists and never in the browser. List
endpoints take `sort`, `order`, `page` and `page_size` and return `{items, total, page, page_size}`. Sortable and
filterable columns MUST be whitelisted in the service (`_SORT_MAP` style). User input MUST NOT be put into SQL
text. Use ORM operators or bound parameters only, no f strings inside `text()`.

The free database plan counts every byte read, so list queries MUST NOT load columns the page does not show
(`defer(Posting.description)`, the deferred `search_vector`). Things that change slowly, like filter menus and the
skills list, MAY be cached in memory for a short time.

### III. Fast on Free Hosting

List and search endpoints MUST answer in under 300 ms at p95 on 10,000 postings. The perf test
(`pytest -q -m perf -s`) proves it and has to stay green. Every new sortable or filterable column MUST ship with an
index, and that index MUST exist in both the migration and the model so `alembic check` stays clean.

The site runs on a free host that falls asleep. The first page MUST show real jobs right away, even while the
server is waking up. That is what `GET /api/postings/snapshot` and the copy saved in the browser are for. Startup
MUST open the port first and do slow work (seeding, importing) after.

### IV. Matching Works Without AI

Resume matching MUST work with no AI key at all. SQL skill coverage plus student fit (student title, program,
grad year, term, length, keywords) is the base and every visitor gets it for free. AI only adds to it: a review, a
re-rank, tailoring, a cover letter, cited answers. If an AI call fails, the page MUST still work and show the free
results with a clear message about what went wrong.

### V. Honest AI

The assistant MUST only claim things it can back with the resume text or the posting it was given. When it can not
tell, it MUST say "I don't have enough information to answer that." and not guess. It MUST NOT invent experience
for a resume. Posting and resume text sent to a model is data, not instructions. It MUST be wrapped in tags and
the prompt MUST say so. The code MUST check what comes back (drop made up posting ids, clamp scores, cut long
fields) before saving or showing it. Nothing a model says is ever allowed to write data without the user clicking
something first.

A change to a prompt MUST be run against `tests/resume` and `tests/eval` and the before and after noted in
`docs/agentic-workflow.md`.

### VI. Visitors Own Their Keys and Their Data

All AI calls MUST go through `app/ai.py`. Visitor keys come in on `X-AI-*` headers for one request and
MUST NOT be stored, logged or echoed back, not even in error messages. AI routes use `Depends(ai_credentials(...))`
and only call `consume_ai_quota` when the owner's key is the one being used.

A resume file is never kept, only the text pulled out of it, and the visitor can delete it any time. A temporary
account and everything in it is deleted after 7 days unless the visitor keeps it. Deleting an account removes all
of its data right away. Passwords are hashed with argon2id. Sessions live in an HTTP only cookie with a 7 day
rolling expiry. Secrets only come from environment variables and `.env.example` MUST list every one of them.

### VII. Respectful Job Collection

Jobs MUST only come from public job board APIs and feeds, files a user uploads, or manual entry. Every source
MUST respect its robots.txt and terms, and the plan that adds it MUST link to both. Nothing behind a login is ever
collected. Sites whose terms forbid automated collection (LinkedIn, Indeed, Glassdoor, Google Jobs) are not added,
even if it would mean more jobs. Requests go out with a polite user agent, timeouts, retries with backoff, and the
delay a site asks for (Job Bank asks for 5 seconds).

A source that fails 3 times in a row pauses itself. One broken board MUST NOT stop the rest of an import.

### VIII. Accessible and Easy to Read

Every page MUST work at 375 px wide with no sideways scrolling. Everything you can click MUST be reachable by
keyboard with a visible focus ring. Form controls MUST have labels. Colour contrast MUST meet WCAG AA (4.5 to 1
for normal text, 3 to 1 for large text). The design rules live in `DESIGN.md` and new UI follows them.

Words on the site are short and plain. No em dashes and no emoji in the UI text. Code comments and docs follow the
same idea: say what it does in normal words.

### IX. Small, Honest Changes

Commits use Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`) and stay small. Commits and pull
requests MUST NOT carry `Co-Authored-By` lines or any AI attribution. After each piece of work
`docs/agentic-workflow.md` gets an entry (`/log-agentic-work`) with what the AI did, what the developer reviewed
or changed, and the real test results. Things that were not checked are written down as not checked.

When sources, tests or migrations change, the numbers in `README.md`, the three guides, `docs/PROJECT_GUIDE.md`
and `docs/DEPLOY.md` MUST be updated in the same change.

### X. Keep It Simple

One server process and one Postgres database. No Docker, no separate worker, no queue, no Redis needed
(it is optional through `REDIS_URL`). Background work runs as asyncio tasks in `app/jobs.py`. A new dependency
MUST have a reason written in the plan. Pick well known, well documented libraries. Do not add helpers or settings
for something that might be needed one day. Three similar lines beat a clever abstraction.

## Quality Gates

These MUST pass on every change that goes to `main`. CI (`.github/workflows/ci.yml`) runs all of them.

- **Backend** (in `backend/`): `ruff check .`, `mypy app` (strict), `pytest -q -m 'not perf'`, the perf budget
  `pytest -q -m perf`, migrations up then down then up, and `alembic check`
- **Frontend** (in `frontend/`): `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`
- **Website**: the Render build command, `python start.py --hosted` on a fresh Postgres, a smoke test of the site
  and API (including a guest session on the next request), then the Playwright tests against it

A failing gate can only be skipped with a written reason in the pull request and a follow up issue to fix it.

## Development Workflow

1. Branch from `main`: `git checkout -b NNN-short-name`
2. Run the Spec Kit loop. `.specify/README.md` explains each step.
   - `/speckit-specify` what and why, no tech
   - `/speckit-clarify` answer the open questions
   - `/speckit-plan` how, with the stack and the Constitution Check
   - `/speckit-checklist` a review checklist for the risky parts
   - `/speckit-tasks` ordered tasks with file paths
   - `/speckit-analyze` make sure spec, plan and tasks agree
   - `/speckit-implement` build it
   - `/speckit-converge` find what is still missing, repeat implement and converge until it says Converged
   - `/log-agentic-work` write the log entry
3. Use the project skills while building: `api-conventions` for backend work, `frontend-tables` for pages and
   tables, `agent-tools` for anything AI, `db-migration` for schema changes.
4. Run the Quality Gates locally, open a pull request, merge when CI is green.

Features so far, in the order they were built: 001 Browse and search, 002 Accounts and tracker, 003 Real jobs
and smart search, 004 AI resume matcher, 005 Bring your own AI key and resume first site, 006 One command run and
free hosting, 007 Co-op matching and job board redesign, 008 More job sources and instant first load.

## Governance

This constitution wins over every other practice in the repo. `CLAUDE.md` is the short version that every Claude
Code session reads, and the two MUST say the same thing.

Changing it takes a pull request that edits this file and bumps the version:

- **MAJOR** when a principle is removed or changed in meaning
- **MINOR** when a principle is added or a lot of guidance is added
- **PATCH** for wording and small fixes

The pull request says which features and docs the change touches, and those get updated before it merges. Every
review checks new work against these rules.

**Version**: 2.0.0 | **Ratified**: 2026-10-09 | **Last Amended**: 2026-11-17
