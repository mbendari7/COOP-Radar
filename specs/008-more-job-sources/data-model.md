# Data Model: Jobs From Every Field, From Public Sources

**Feature**: 008-more-job-sources
**Migrations**: 0007, 0010, 0011, 0012, 0013, 0014, 0015, 0016

No new tables. This feature fills the `ingest_sources`, `ingest_runs` and `postings` tables from feature 003.

## `ingest_sources.adapter_type` CHECK constraint

| Migration | Adds |
|---|---|
| 0004 (feature 003) | `json_api`, `rss`, `csv`, `manual` |
| 0007 | `greenhouse`, `lever`, `ashby` |
| 0010 | `smartrecruiters` |
| 0011 | `workday`, `adzuna` |
| 0012 | `workable` |
| 0013 | `simplify` |
| 0014 | `recruitee`, `bamboohr`, `rippling`, `oracle`, `github_list` |
| 0015 | `themuse`, `himalayas` |
| 0016 | `jobbank` |

The model's constraint and the latest migration list the same values so `alembic check` stays clean.

## `ingest_sources.config` by adapter

| Adapter | Config keys |
|---|---|
| career boards (Greenhouse, Lever, Ashby, SmartRecruiters and the others) | `board`, optional `company` and extra settings from the fourth tuple item |
| `workday` | `board` as `<tenant>.<wdN>/<site>`, `company`, `scope` (auto, all, students), optional `city` and `province` |
| `oracle` | `board` as `<host>/<site number>` |
| `simplify` | `repo` and `branch`. `{summer}` in the repo name moves to next year's list |
| `github_list` | `repo`, `branch`, `file`, `country` |
| `workable` | `location`, `queries`, `pages` |
| `themuse` | `levels`, `pages`, `max_age_days` (90) |
| `himalayas` | `query`, `pages`, `worldwide` |
| `jobbank` | `queries`, a `\|` separated list of filters and search words (`DEFAULT_QUERIES` when missing) |

## Seed files

| File | What |
|---|---|
| `seed/job_boards.py` | `(company, adapter_type, board)` tuples, an optional fourth item for config. 185 hand picked |
| `seed/discovered_boards.json` | About 1,500 boards found by `discover_boards.py` |

The seed loads both in two SQL statements with `jsonb_to_recordset`. A board that moved hiring systems is
repointed instead of duplicated.

## `postings` fields the runner keeps up to date

On every import, not just the first: title, location, `country`, `term`, `duration_months`, `fields_of_study`,
`grad_years`, and the estimated `deadline` (flagged in `low_confidence_fields`). `source_ref` is unique per source
so re runs update instead of adding.

## Adapter class attribute

| Attribute | Default | Notes |
|---|---|---|
| `rolling_window` | none | When set (Job Bank: 21 days), jobs that left the feed stay open until they are that old |
