# Implementation Plan: Bring Your Own AI Key and a Resume First Site

**Branch**: `005-byok-resume-first` | **Date**: 2026-10-11 (written up 2026-11-17) | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-byok-resume-first/spec.md`

## Summary

Put every AI call behind one small module, `app/ai.py`, that speaks to Claude, ChatGPT and Gemini through their
official SDKs and takes the visitor's key from request headers. Change resume matching so the first stage is plain
SQL skill overlap, which needs no AI or embeddings, and make the AI stage optional. Add guest and demo accounts so
nobody has to sign up, and rebuild the site around the Match my resume page.

## Technical Context

**Language/Version**: Python 3.12, TypeScript 5 with React 18

**Primary Dependencies**: Existing stack plus `openai` and `google-genai` next to `anthropic`. All three are the
official SDKs. No LangChain or similar wrapper (see research.md)

**Storage**: PostgreSQL 16. Migration 0006 adds `users.is_demo`. Migration 0007 adds `resumes.insights` (jsonb) and
the career board adapter types. Daily AI counters live in the session store

**Testing**: pytest with `mock_claude_create`, `mock_claude_stream` and fakes for the other two SDKs. Vitest for
the AI key store, the AI key page and the resume page

**Target Platform**: Same single process web app

**Project Type**: Web app

**Performance Goals**: Free matching answers in a few seconds on about 3,000 jobs. The SQL shortlist stays inside
the 300 ms budget

**Constraints**: Keys never stored or logged. Matching works with no key. AI errors never hide the free results

**Scale/Scope**: About 15 endpoints touched, one new module, three new pages or panels

## Constitution Check

| # | Principle | How this feature meets it | Result |
|---|---|---|---|
| I | Correctness first | Each new endpoint has schema and tests. Provider errors tested per SDK | PASS |
| II | Data stays in the database | Skill coverage ranking is one SQL query with `unnest` and `cardinality` | PASS |
| III | Fast on free hosting | Shortlist query covered by the perf test | PASS |
| IV | Matching works without AI | This feature is what makes it true | PASS |
| V | Honest AI | Q&A prompt forces `Resume:` and `Posting:` citations and the "not enough information" line. Rerank output is checked (unknown ids dropped, scores clamped) | PASS |
| VI | Keys and data | Keys only on `X-AI-*` headers, hidden from `repr()`, never in errors. Temporary accounts deleted after 7 days | PASS |
| VII | Job collection | N/A | PASS |
| VIII | Accessible | AI key page and resume page labelled and keyboard friendly | PASS |
| IX | Small changes | Nine commits, each one area | PASS |
| X | Simple | One module for all providers instead of a framework | PASS |

## Project Structure

### Documentation (this feature)

```text
specs/005-byok-resume-first/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/api.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
backend/app/
├── ai.py                     # new: complete(), stream(), list_models(), ai_credentials(), error mapping
├── api/ai.py                 # new: POST /api/ai/check
├── api/meta.py               # new: GET /api/config
├── api/auth.py               # demo and guest accounts
├── api/me.py                 # claim a temporary account
├── api/resume.py             # upload with optional AI, rematch, insights, ask with modes
├── services/demo.py          # new: temporary accounts and cleanup
├── services/usage.py         # new: daily limit on the owner's key
├── services/insights.py      # new: free insights and the cached AI review
├── services/resume.py        # two stage matching, SQL first
└── agent/resume_qa.py        # streams through ai.stream(), modes question, tailor, cover_letter
backend/alembic/versions/0006_add_demo_users.py
backend/alembic/versions/0007_job_boards_and_insights.py

frontend/src/
├── api/aiKey.ts              # new: key kept in session or local storage, aiHeaders()
├── pages/AiKeyPage.tsx       # new: provider how to steps, check, model picker
├── pages/ResumePage.tsx      # rebuilt as the main page of the site
└── components/               # DemoButton, DemoBanner, ClaimAccountForm, ConversationPanel, RichText
```

**Structure Decision**: Backend logic stays in services, the new provider code sits in one file at the top of
`app/` because every AI route imports it.

## Complexity Tracking

| Breaks which rule | Why it is needed | Simpler option and why it was not enough |
|---|---|---|
| Two new dependencies (`openai`, `google-genai`) | Visitors have keys for different providers | Raw HTTP for each provider would mean writing streaming and error handling three times |
