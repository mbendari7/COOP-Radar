# Data Model: Co-op Matching and a Job Board Layout

**Feature**: 007-coop-matching-job-board
**Migrations**: 0009, 0010, 0011, 0013

## `resumes` (migration 0009)

| Column | Type | Notes |
|---|---|---|
| `preferences` | jsonb, nullable | `JobPreferences` below. Kept across a new upload when none is sent |

### `JobPreferences`

| Field | Type | Default | Notes |
|---|---|---|---|
| `categories` | list of job type keys | `[]` | Empty means the job types that suit the program |
| `keywords` | text up to 100 | `""` | Adds 20 points when it matches |
| `province`, `city` | text | `""` | Remote jobs always pass |
| `work_modes` | list of onsite, hybrid, remote | `[]` | |
| `level` | entry, students, all | entry | |
| `program` | program key | `""` | Filled from the resume when blank |
| `degree` | degree | `""` | Filled from the resume when blank |
| `grad_year` | 2000 to 2100 | null | Filled from the resume when blank |
| `term` | text like "Summer 2027" | `""` | |
| `durations` | any of 4, 8, 12, 16 | `[]` | |
| `countries` | CA, US | `["CA"]` | |

## `postings`

| Column | Migration | Type | Notes |
|---|---|---|---|
| `country` | 0010 | char(2), default CA | `province` holds the state for US jobs. Indexed |
| `fields_of_study` | 0010 | text[] | Program keys read from the description |
| `grad_years` | 0010 | smallint[] | Years read after "graduating" or "class of" |
| `season` | 0011 | text, generated from `term` | winter, summer, fall. Indexed |
| `term_start` | 0011 | date, generated from `term` | For "term starting soonest". Indexed |
| `duration_months` | 0011, 0013 | smallint, now nullable | Real months, null when the job does not say |
| `first_seen_at` | 0013 | timestamptz | When the importer first saw it. Powers new since last visit, Newly added and RSS. Indexed |

Generated columns can only use IMMUTABLE functions, so the SQL for `season` and `term_start` lives in the
migration and the model uses the same expression.

## Not stored

- Job types are worked out from the title at query time with `category_clause()`
- Fit notes are built when matches are read, from the same parts as the score
- The last visit time lives in the visitor's browser (`utils/visits.ts`)
