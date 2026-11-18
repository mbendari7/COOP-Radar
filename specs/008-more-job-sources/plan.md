# Implementation Plan: Jobs From Every Field, From Public Sources

**Branch**: `008-more-job-sources` | **Date**: 2026-10-11 to 2026-11-15 (written up 2026-11-17) | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/008-more-job-sources/spec.md`

## Summary

Add one adapter per hiring system or feed under `backend/app/ingest/`, all on the existing `BaseAdapter` and
runner from feature 003. Seed employer boards from `seed/job_boards.py` (hand picked) and
`seed/discovered_boards.json` (found by `seed/discover_boards.py` from Common Crawl and the student lists' apply
links). Teach the runner rolling windows, estimated deadlines and re reading term, location and education on every
import. Fix location and country reading so filters can be trusted.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: httpx (already there) with retries and timeouts, `feedparser` for Job Bank's Atom feeds.
No new ones

**Storage**: Postgres 16. Each new adapter type is added to the `ingest_sources.adapter_type` CHECK constraint:
0007 `greenhouse`, `lever`, `ashby`; 0010 `smartrecruiters`; 0011 `workday`, `adzuna`; 0012 `workable`; 0013
`simplify`; 0014 `recruitee`, `bamboohr`, `rippling`, `oracle`, `github_list`; 0015 `themuse`, `himalayas`; 0016
`jobbank`

**Testing**: One test file per adapter with recorded replies played back by `respx` (`tests/ingest/test_boards.py`,
`test_workday.py`, `test_workable.py`, `test_simplify.py`, `test_more_sources.py`, `test_job_apis.py`,
`test_jobbank.py`), plus `test_runner.py`, `test_dedup.py` and `test_seed.py`. No live calls in tests

**Target Platform**: The importer runs inside the API process on the scheduler from feature 006

**Project Type**: Web app

**Performance Goals**: A full pass of 1,700 sources inside the hours the free server is awake. 3 sources at a time

**Constraints**: robots.txt and terms for every source. Job Bank asks for 5 seconds between calls. The Muse allows
500 calls an hour. Neon counts data transfer, so re imports skip unchanged descriptions

**Scale/Scope**: About 1,700 sources, about 30,000 open jobs

## Constitution Check

| # | Principle | How this feature meets it | Result |
|---|---|---|---|
| I | Correctness first | Every adapter has recorded reply tests. Every location bug got a regression test | PASS |
| II | Data stays in the database | Boards load in two `jsonb_to_recordset` statements. A source's jobs load in one query | PASS |
| III | Fast on free hosting | Greenhouse and SmartRecruiters list first and fetch descriptions only for kept jobs | PASS |
| IV | Matching works without AI | Extraction is rules first. Claude is only used if the owner set a key and confidence is low | PASS |
| V | Honest AI | Estimated deadlines are flagged in `low_confidence_fields` | PASS |
| VI | Keys and data | Adzuna keys only from env, off by default | PASS |
| VII | Job collection | Sources and their terms are in research.md. LinkedIn, Indeed, Glassdoor and Google Jobs turned down | PASS |
| VIII | Accessible | N/A, backend only | PASS |
| IX | Small changes | One adapter per commit area, each logged | PASS |
| X | Simple | One adapter class per system, same base class, same runner | PASS |

## Project Structure

### Documentation (this feature)

```text
specs/008-more-job-sources/
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
backend/app/ingest/
├── boards.py         # Greenhouse, Lever, Ashby, SmartRecruiters, choose_location(), location parser
├── workday.py        # public /wday/cxs JSON, Canada and province splits over 2,000
├── ats.py            # Recruitee, BambooHR, Rippling
├── oracle.py         # Oracle Cloud career sites
├── workable.py       # jobs.workable.com public search
├── simplify.py       # Simplify and vanshb03 listings.json
├── github_lists.py   # README tables (negarprh Canadian tech internships)
├── themuse.py        # The Muse internship level
├── himalayas.py      # remote jobs open to Canada
├── jobbank.py        # Government of Canada Job Bank Atom feeds
├── adzuna.py         # optional, paid keys
├── terms.py          # term and length (feature 007)
├── registry.py       # adapter_type to class
└── runner.py         # rolling_window, estimated deadlines, re read fields on every import
backend/app/jobs.py   # scheduler: 3 at a time, never run first then oldest first, delete_old_closed()
backend/seed/
├── job_boards.py            # 185 hand picked employers plus the feeds
├── discovered_boards.json   # about 1,500 discovered boards
└── discover_boards.py       # owner run script: Common Crawl and --lists
backend/alembic/versions/0007, 0010 to 0016
```

**Structure Decision**: One file per system so each can be tested and turned off on its own.

## Complexity Tracking

| Breaks which rule | Why it is needed | Simpler option and why it was not enough |
|---|---|---|
| Rolling window in the runner | Job Bank feeds only show two days | Closing jobs that left the feed would close almost all of them within two days |
