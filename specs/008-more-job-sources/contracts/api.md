# API Contracts: Jobs From Every Field, From Public Sources

**Feature**: 008-more-job-sources
**Date**: 2026-10-11 to 2026-11-15 (written up 2026-11-17)

This feature adds no new endpoints. It uses the admin endpoints from feature 003 and adds settings.

## Admin endpoints it relies on (admin only, 403 otherwise)

| Method and path | What |
|---|---|
| `GET /api/admin/sources` | Every source with its type, last run, health and whether it paused itself |
| `GET /api/admin/sources/{id}/runs` | Run history: added, updated, closed, errors |
| `POST /api/admin/sources/{id}/run` | Start a run now. **202** with the run id. **503** `QUEUE_UNAVAILABLE` if the job could not start |
| `PATCH /api/admin/sources/{id}` | Turn a source on or off, or back on after it paused itself |

## `GET /api/postings` (changed meaning)

`students_only` now also finds Job Bank student and apprentice jobs, because their titles get "(student)" or
"(apprentice)". "Student Success Manager" style titles and US recruiter roles no longer count as student jobs.

## Settings (env vars)

| Name | Default | What |
|---|---|---|
| `SEED_JOB_BOARDS` | true | Seed the career boards and feeds |
| `INGEST_INTERVAL_HOURS` | 6 | How often each source is imported |
| `INGEST_START_DELAY_SECONDS` | 60 | Wait after start before the first pass |
| `INGEST_LOCATION_FILTER` | Canada | Which locations to keep (blank means the built in Canada filter) |
| `INGEST_US_JOBS` | students | `students` (student and early career titles), `all` or `none` |
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | blank | Turn on the two Adzuna sources (paid plan) |

## Owner script

```bash
cd backend
python -m seed.discover_boards          # Common Crawl for each hiring system
python -m seed.discover_boards --lists  # only the apply links on the GitHub student lists
```

Adds what it finds to `seed/discovered_boards.json`. Not run by `start.py`.
