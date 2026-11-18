# Data Model: One Command Run and Free Hosting

**Feature**: 006-one-command-free-hosting
**Migration**: 0008

## New table

### `kv_store` (migration 0008)

| Column | Type | Notes |
|---|---|---|
| `key` | text, primary key | For example `session:<token>`, `ai_usage:<user>:<date>`, `seed:fingerprint` |
| `fields` | jsonb, not null, default `{}` | Hash fields, like `user_id` for a session |
| `counter` | bigint, not null, default 0 | For `incr()` style rate limits |
| `expires_at` | timestamptz, nullable | Rows past this are treated as missing and purged by the scheduler |

Index on `expires_at` so the purge is cheap.

## What goes in it

| Key | Fields or counter | Expires |
|---|---|---|
| `session:<token>` | `user_id` | 7 days, pushed forward on every request |
| login failures per email | counter | 15 minutes |
| guest, demo and AI check limits per network | counter | 1 hour |
| `ai_usage:<user id>:<date>` | counter | end of the day |
| `seed:fingerprint` | hash of the seed files and settings | never |

## Changed behaviour on `postings`

- `description` is deferred in list queries and `search_vector` is deferred in the model, so neither is read
  unless a detail page asks
- Imported jobs with `closed_at` or a deadline more than 30 days ago are deleted by `delete_old_closed()` unless a
  `saved_postings` row points at them

## Local files (not in the database)

| Path | What |
|---|---|
| `~/.coopradar/` | The local Postgres data folder made by `pgserver` |
| `backend/.venv/` | The Python environment `start.py` makes |
| `frontend/dist/` | The built site that FastAPI serves |
