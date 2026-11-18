# Data Model: Bring Your Own AI Key and a Resume First Site

**Feature**: 005-byok-resume-first
**Migrations**: 0006 and 0007

## Changed tables

### `users` (migration 0006)

| Column | Type | Notes |
|---|---|---|
| `is_demo` | boolean, not null, default false | True for demo and guest accounts. They get a random password nobody knows |

Temporary accounts older than 7 days are deleted whenever a new one is made. The delete cascades to saved
postings, status changes, the resume and its matches.

### `resumes` (migration 0007)

| Column | Type | Notes |
|---|---|---|
| `insights` | jsonb, nullable | The cached AI review: summary, strengths, improvements, tailoring tips, roles, keywords. Each field is checked and cut to length before it is saved. Cleared on a new upload |

### `ingest_sources.adapter_type` (migration 0007)

The CHECK constraint gains `greenhouse`, `lever` and `ashby` so real employer career boards can be seeded (see
feature 008 for the rest of the sources).

## Not stored on purpose

| Thing | Where it lives instead |
|---|---|
| Visitor AI keys | The visitor's browser. Sent on `X-AI-*` headers for one request |
| The resume file | Nowhere. Only the extracted text is kept |

## Counters in the session store

| Key | What it counts | Expires |
|---|---|---|
| `ai_usage:<user id>:<date>` | AI actions on the owner's key today | End of the day |
| rate limit keys for `/api/auth/demo`, `/api/auth/guest`, `/api/ai/check` | Requests per network | 1 hour |

## Rules

- A resume upload replaces the old resume and its matches in one transaction. If ranking fails with a key error
  the transaction rolls back and the old resume stays
- Match scores are 0 to 100. Up to 60 are kept per resume (it was 20 when this feature shipped, raised in 007)
