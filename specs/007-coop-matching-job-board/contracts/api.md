# API Contracts: Co-op Matching and a Job Board Layout

**Feature**: 007-coop-matching-job-board
**Date**: 2026-10-12 to 2026-10-25 (written up 2026-11-17)

## `GET /api/postings` (changed)

New query parameters. Every one is a SQL `WHERE` and lists are OR within the field and AND across fields.

| Parameter | Type | Notes |
|---|---|---|
| `season` | list of winter, summer, fall | Only terms not yet under way |
| `duration` | list of ints | Real months, grouped in the UI (about 8 months is 6 to 9) |
| `include_unstated` | bool, default false (the site sends true) | Keeps jobs that do not say their term or length, after the ones that do |
| `category` | list of job type keys | Title patterns |
| `company` | list of text | |
| `posted_within` | int days | |
| `added_since` | datetime | For new since your last visit |
| `country` | list of CA, US | |
| `program` | program key | Jobs that name it or whose title suits it |
| `grad_year` | int | |

New sorts: `duration_months`, `term_start`, `first_seen_at`, next to `posted_at`, `deadline`, `company`, `title`.
Anything else is a 422. `page_size` is one of 10, 25, 50 or 100.

## `GET /api/postings/meta/filters` (changed)

Adds counts by job type, country, work mode, season and length, plus the employer list and the open job total.
Cached in memory for 2 minutes.

## `GET /api/postings/feed.rss`

Takes the same query parameters as the list and returns an RSS 2.0 feed of the newest jobs for that search.

## `PUT /api/resume/preferences`

**Body**: `JobPreferences` (see data-model.md). Saves them and matches again using only the visitor's own key,
never the owner's quota.

**200**: `UploadResponse` with the resume, the new matches, the preferences and the detected education

## `POST /api/resume` (changed)

Takes an optional `preferences` form field. The reply now includes `preferences` and `education` (program, program
label, degree and grad year read from the resume).

## `GET /api/resume/matches` (changed)

Each match now has `matched_skills`, `missing_skills` and `fit_notes` (the "why it fits" lines). Up to 60 matches.

## `GET /api/resume/align/{posting_id}`

Free, no AI. How to make the resume fit one job.

**200**: `ResumeAlignment` with `checks`, `tips` (edits in order), `matched_skills` and `missing_skills`, and
`keywords_found` and `keywords_missing` (the job's words the resume has, and ones worth adding if true)
**404**: no resume, or the job does not exist
