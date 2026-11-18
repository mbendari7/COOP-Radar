# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]

**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: `/speckit-plan` fills this in. This is the HOW. The spec already says what and why.

## Summary

[In a few sentences: what the spec asks for and how CoopRadar will do it]

## Technical Context

<!--
  The CoopRadar defaults are filled in below. Keep them unless this feature changes something, and add what is
  new for this feature (new libraries, new tables, new sources). Mark anything you do not know yet as
  NEEDS CLARIFICATION and research.md will answer it.
-->

**Language/Version**: Python 3.12 (backend), TypeScript 5 with React 18 (frontend)

**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2.0 async with typed `Mapped[]`, Alembic, httpx;
Vite 6, TanStack Query and Table, React Router, Tailwind, dnd-kit. AI through `app/ai.py` only (official
`anthropic`, `openai`, `google-genai` SDKs). [New ones for this feature, each with a reason]

**Storage**: PostgreSQL 16 with pgvector. Locally `start.py` runs one from the `pgserver` package in
`~/.coopradar`. Online it is Neon's free plan through `DATABASE_URL`. Sessions and counters in the `kv_store`
table (Redis only if `REDIS_URL` is set). [New tables or columns, and the migration number they get]

**Testing**: pytest with recorded fixtures and `respx`, AI calls mocked, `-m perf` for the latency budget;
Vitest and Testing Library; Playwright against a running site (`frontend/e2e/*.e2e.ts`)

**Target Platform**: One Uvicorn process that serves the API and the built site. Render free plan (sleeps when
idle), optional Vercel in front with `/api` proxied to Render. Windows, macOS and Linux for local runs

**Project Type**: Web app (FastAPI backend and React single page app in one repo)

**Performance Goals**: List and search under 300 ms p95 on 10,000 postings. First page shows jobs within 2
seconds, even while the server wakes up. [Anything this feature adds]

**Constraints**: No Docker, no separate worker or queue (background jobs are asyncio tasks in `app/jobs.py`, 3 at
a time). Neon counts data transfer, so do not load columns a page does not show. Matching works with no AI key.
Visitor keys are never stored. [Anything this feature adds]

**Scale/Scope**: About 1,700 career boards and feeds, about 30,000 open jobs live, a handful of visitors at a
time. [What this feature changes]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

<!--
  Answer each one for this feature with PASS, or explain it in Complexity Tracking below.
  The rules are in .specify/memory/constitution.md.
-->

| # | Principle | How this feature meets it | Result |
|---|---|---|---|
| I | Correctness first: schema and tests for every endpoint, a regression test for every fix, no network in tests | [answer] | [PASS] |
| II | Data stays in the database: filter, sort and page in SQL, whitelisted columns, no user input in SQL text | [answer] | [PASS] |
| III | Fast on free hosting: 300 ms p95, index for every new sort or filter column, port opens first | [answer] | [PASS] |
| IV | Matching works without AI, AI only adds | [answer] | [PASS] |
| V | Honest AI: cites, says when it does not know, tagged data, output checked | [answer or N/A] | [PASS] |
| VI | Visitors own their keys and data: keys never stored, resumes deletable, secrets in env | [answer] | [PASS] |
| VII | Respectful job collection: public APIs only, robots.txt and terms linked here, polite requests | [answer or N/A] | [PASS] |
| VIII | Accessible and easy to read: 375 px, keyboard, labels, AA contrast, plain words | [answer] | [PASS] |
| IX | Small honest changes: conventional commits, no AI attribution, log entry, docs numbers updated | [answer] | [PASS] |
| X | Keep it simple: one process, one database, every new dependency has a reason | [answer] | [PASS] |

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan)
├── research.md          # Phase 0: decisions and why (/speckit-plan)
├── data-model.md        # Phase 1: tables, columns, migration (/speckit-plan)
├── quickstart.md        # Phase 1: how to try it by hand (/speckit-plan)
├── contracts/           # Phase 1: API contracts (/speckit-plan)
│   └── api.md
├── checklists/          # /speckit-specify and /speckit-checklist
└── tasks.md             # Phase 2 (/speckit-tasks, not made by /speckit-plan)
```

### Source Code (repository root)

<!--
  This is the real CoopRadar layout. Keep the folders this feature touches, add the new files with their real
  names, and delete the lines it does not touch.
-->

```text
backend/
├── app/
│   ├── api/            # thin routers, one per area (postings, auth, me, saved, resume, admin, ai, meta)
│   ├── services/       # the logic and the SQL, owns commit()
│   ├── schemas/        # Pydantic models for requests and replies
│   ├── models/         # SQLAlchemy tables
│   ├── ingest/         # one adapter per source type, runner, dedup, extraction, embeddings
│   ├── agent/          # streamed tailor, cover letter and Q&A
│   ├── ai.py           # every AI call goes through here
│   ├── jobs.py         # background jobs and the import scheduler
│   ├── store.py        # sessions and counters
│   ├── deps.py         # auth dependencies
│   └── main.py         # app, lifespan, error handler, serves the built site
├── alembic/versions/   # 0001 to 0016 so far, next is [00NN]
├── seed/               # skills, job_boards.py, discovered_boards.json, sample postings
└── tests/              # api/, ingest/, resume/, eval/, perf/, fixtures/

frontend/
├── src/
│   ├── api/            # client.ts plus one TanStack Query hook file per area
│   ├── pages/
│   └── components/
├── tests/              # Vitest
└── e2e/                # Playwright, *.e2e.ts

start.py                # one command run (venv, packages, build, database, migrate, seed, serve)
render.yaml             # Render Blueprint
vercel.json             # optional Vercel front
.github/workflows/      # ci.yml, refresh-jobs.yml
```

**Structure Decision**: [Which of the folders above this feature touches and the new files it adds]

## Complexity Tracking

> **Fill this in only if the Constitution Check has something that needs a reason**

| Breaks which rule | Why it is needed | Simpler option and why it was not enough |
|-----------|------------|-------------------------------------|
| [for example a new dependency] | [the real need] | [why the stdlib or an existing library would not do] |
| [for example a second background loop] | [the problem] | [why the existing scheduler in jobs.py could not do it] |
