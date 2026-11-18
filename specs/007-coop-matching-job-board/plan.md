# Implementation Plan: Co-op Matching and a Job Board Layout

**Branch**: `007-coop-matching-job-board` | **Date**: 2026-10-12 to 2026-10-25 (written up 2026-11-17) | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/007-coop-matching-job-board/spec.md`

## Summary

Add two small reading modules: `services/education.py` (programs and grad years from resumes and job text) and
`ingest/terms.py` (work term and length from job text). Store what they find on each posting, make term season
and start date generated columns so filters and sorts stay in SQL, and fold all of it into a weighted student fit
score with plain notes. Group titles into job types with `services/categories.py`. Rebuild the jobs page as a list
beside a details panel with a filter sidebar, and add a free resume fit check and a new jobs feed.

## Technical Context

**Language/Version**: Python 3.12, TypeScript 5

**Primary Dependencies**: No new ones. Regular expressions in Python and Postgres `~*` for title patterns.
`feedparser` already exists for reading feeds, the RSS output is built by hand

**Storage**: Postgres 16. Migrations 0009 (`resumes.preferences`), 0010 (`postings.country`, `fields_of_study`,
`grad_years`), 0011 (generated `season` and `term_start`, nullable `duration_months`), 0013 (`first_seen_at`,
real lengths)

**Testing**: `tests/ingest/test_education.py`, `tests/ingest/test_terms.py`, `tests/resume/test_preferences.py`,
`tests/resume/test_coop_matching.py`, `tests/resume/test_align.py`, `tests/api/test_terms_api.py`,
`tests/api/test_updates_api.py`; Vitest for FilterBar, PostingCard and ResumePage; Playwright for the sidebar,
details panel and phone layout

**Target Platform**: Same web app

**Project Type**: Web app

**Performance Goals**: Filtered list under 300 ms p95 with every filter. Filter counts cached 2 minutes

**Constraints**: Lenient matching, nothing hidden for program or grad year. All filters in SQL. No popups

**Scale/Scope**: About 3,000 jobs when it started, about 13,700 by the end

## Constitution Check

| # | Principle | How this feature meets it | Result |
|---|---|---|---|
| I | Correctness first | Each reader has its own test file with real titles that broke it before | PASS |
| II | Data stays in the database | Season and term start are generated columns. Job types are SQL `~*` patterns. Fit score is a SQL `case` sum | PASS |
| III | Fast on free hosting | Indexes on `country`, `season`, `term_start`, `first_seen_at`. Counts cached after the perf test caught 374 ms | PASS |
| IV | Matching works without AI | All of it is free. Resume fit needs no AI | PASS |
| V | Honest AI | N/A, no new AI | PASS |
| VI | Keys and data | Preferences saved with the resume and deleted with it | PASS |
| VII | Job collection | N/A here (sources are feature 008) | PASS |
| VIII | Accessible | Sidebar filters are labelled checkboxes and selects, details panel keyboard reachable, phone layout tested in Playwright | PASS |
| IX | Small changes | Done in five sessions, each logged | PASS |
| X | Simple | Regex readers instead of an AI extraction step | PASS |

## Project Structure

### Documentation (this feature)

```text
specs/007-coop-matching-job-board/
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
├── services/education.py     # new: PROGRAMS, detect_education(), fields and grad years from job text
├── services/categories.py    # new: CATEGORIES title patterns, category_clause()
├── services/align.py         # new: free Make your resume fit
├── services/feed.py          # new: RSS for any search
├── services/resume.py        # JobPreferences, preference_filters(), _student_fit weights, fit_notes()
├── services/postings.py      # new filters and sorts, include_unstated, filter counts
├── ingest/terms.py           # new: term and length from text
├── ingest/runner.py          # stores fields, grad years, term, length, country on every import
└── api/resume.py, api/postings.py
backend/alembic/versions/0009_resume_preferences.py
backend/alembic/versions/0010_postings_country_education.py
backend/alembic/versions/0011_term_season_workday.py
backend/alembic/versions/0013_real_lengths_simplify.py

frontend/src/
├── pages/PostingsListPage.tsx   # search row, sidebar, list beside details, ?job= in the URL
├── pages/ResumePage.tsx         # About you, What are you looking for, upload, tabs
├── pages/SignInPage.tsx         # no popup sign in
├── components/FilterBar.tsx, filters.ts, PostingCard.tsx, PostingDetailView.tsx, ResumeFitPanel.tsx,
│   JobUpdates.tsx, terms.ts, roles.ts, Postmark.tsx
└── utils/visits.ts
DESIGN.md, PRODUCT.md
```

**Structure Decision**: Readers that run on import live in `ingest/`, readers also used on resumes live in
`services/`.

## Complexity Tracking

| Breaks which rule | Why it is needed | Simpler option and why it was not enough |
|---|---|---|
| Generated columns for season and term start | Filter and sort by term in SQL | Working it out in Python would mean sorting in memory, which the constitution forbids |
